"""
POST /api/landmarks — Accepts landmark coords from browser canvas,
runs the full ML pipeline in a background thread, streams progress via SSE.
"""
import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

import cv2
import numpy as np
import open3d as o3d

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.auth.router import _get_current_user
from app.supabase_client import (
    save_report_to_supabase, 
    upload_file_to_supabase, 
    get_reports_from_supabase, 
    get_report_by_session
)
from app.session_store import get_session, sessions, push_progress, push_done, push_error
from app.pipeline.mesh import load_and_preprocess_mesh, split_mesh
from app.pipeline.detection import detect_fractures
from app.pipeline.fracture import (
    angle_from_negative_x, get_split_ratio,
    create_angle_mesh, make_solid, make_fracture_image_patch,
)
from app.pipeline.rag import analyze_fracture_risk

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
MODEL_3D_PATH = os.path.join(BASE_DIR, "forearm_Bones.glb")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class LandmarkPoint(BaseModel):
    label: str   # "ulna head" | "ulna tail" | "radius head" | "radius tail"
    x: float     # pixel x on the displayed image
    y: float     # pixel y on the displayed image


class LandmarksRequest(BaseModel):
    session_id: str
    landmarks: List[LandmarkPoint]
    image_width: int    # displayed image dimensions (for centring)
    image_height: int
    groq_api_key: str = None   # optional override


def _run_pipeline(session_id: str, landmarks_px: dict, img_w: int, img_h: int,
                  groq_api_key: str = None, user_id: str = None, report_name: str = "New Analysis",
                  jwt_token: str = None):
    """Blocking pipeline — runs in a thread pool."""
    loop = asyncio.new_event_loop()

    def emit(step, msg, status="running"):
        asyncio.run_coroutine_threadsafe(
            push_progress(session_id, step, 7, msg, status), loop
        )

    async def run():
        session = get_session(session_id)
        img_orig = session["xray_image"]
        
        # Sync with deployable.py: Always work on 50% scale internally
        h_orig, w_orig = img_orig.shape[:2]
        scale = 0.5
        w_new = int(w_orig * scale)
        h_new = int(h_orig * scale)
        img = cv2.resize(img_orig, (w_new, h_new))
        
        cx, cy = w_new // 2, h_new // 2

        # Center the landmark coords (relative to 50% scale)
        Xray_landmark = {
            lbl: (int(x * scale - cx), int(cy - y * scale))
            for lbl, (x, y) in landmarks_px.items()
        }
        session["landmarks"] = Xray_landmark

        try:
            # Step 1 – Load 3D mesh
            await push_progress(session_id, 1, 7, "Loading and preprocessing 3D model…")
            mesh = load_and_preprocess_mesh(os.path.abspath(MODEL_3D_PATH))

            # Step 2 – Split mesh
            await push_progress(session_id, 2, 7, "Splitting mesh into ulna / radius…")
            mesh_ulna, mesh_radius = split_mesh(mesh)

            # Step 3 – YOLO fracture detection
            await push_progress(session_id, 3, 7, "Running YOLO fracture detection…")
            Xray_breaks, ulna_img, radius_img = detect_fractures(img)

            fracture_data = []
            geometries = []

            # Step 4 – Generate fractured 3D mesh
            await push_progress(session_id, 4, 7, "Generating fractured 3D geometry…")

            for bone, break_key, head_key, tail_key, mesh_part, crop_img in [
                ("ulna",   "ulna break",   "ulna head",   "ulna tail",   mesh_ulna,   ulna_img),
                ("radius", "radius break", "radius head", "radius tail", mesh_radius, radius_img),
            ]:
                if (break_key in Xray_breaks
                        and head_key in Xray_landmark
                        and tail_key in Xray_landmark):
                    brk = Xray_breaks[break_key]
                    split_ratio = get_split_ratio(
                        Xray_landmark[head_key], Xray_landmark[tail_key], brk["center"]
                    )
                    top_angle = angle_from_negative_x(Xray_landmark[head_key], brk["center"])
                    bot_angle = angle_from_negative_x(brk["center"], Xray_landmark[tail_key])

                    fractured = create_angle_mesh(mesh_part, [top_angle, bot_angle], split_ratio)
                    solid = make_solid(fractured)
                    solid.paint_uniform_color([0.7, 0.7, 0.7])
                    geometries.append(solid)

                    if crop_img is not None:
                        patch = make_fracture_image_patch(
                            mesh_part, split_ratio, brk["size"],
                            Xray_landmark[head_key], Xray_landmark[tail_key], crop_img
                        )
                        geometries.append(patch)

                    severity = "severe" if abs(top_angle) > 15 or abs(bot_angle) > 15 else \
                               "moderate" if abs(top_angle) > 8 or abs(bot_angle) > 8 else "mild"

                    fracture_data.append({
                        "bone": bone,
                        "damage": "crack",
                        "location": round(float(split_ratio), 3),
                        "top_angle": round(float(top_angle), 2),
                        "bottom_angle": round(float(bot_angle), 2),
                        "severity": severity
                    })
                else:
                    solid = make_solid(mesh_part)
                    solid.paint_uniform_color([0.7, 0.7, 0.7])
                    geometries.append(solid)

            session["fracture_data"] = fracture_data

            # Step 5 – Combine and save .glb
            await push_progress(session_id, 5, 7, "Finalizing 3D model package…")
            import trimesh
            from PIL import Image as PILImage
            from trimesh.visual.material import PBRMaterial
            
            scene = trimesh.Scene()
            for g in geometries:
                # Convert Open3D mesh to Trimesh
                t_mesh = trimesh.Trimesh(
                    vertices=np.asarray(g.vertices),
                    faces=np.asarray(g.triangles)
                )
                
                # Assign colors or textures
                if g.has_vertex_colors():
                    t_mesh.visual.vertex_colors = (np.asarray(g.vertex_colors) * 255).astype(np.uint8)
                elif g.has_triangle_uvs() and len(g.textures) > 0:
                    # UV Mapping bridge
                    o3d_uvs = np.asarray(g.triangle_uvs)
                    triangles = np.asarray(g.triangles)
                    num_verts = len(g.vertices)
                    vertex_uvs = np.zeros((num_verts, 2))
                    for i, tri in enumerate(triangles):
                        for j, v_idx in enumerate(tri):
                            vertex_uvs[v_idx] = o3d_uvs[i * 3 + j]
                    vertex_uvs[:, 1] = 1.0 - vertex_uvs[:, 1] # Flip V for GLB
                    
                    # Texture extraction + BGR to RGB
                    tex_img = np.asarray(g.textures[0])
                    if tex_img.dtype != np.uint8:
                        tex_img = (tex_img * 255).astype(np.uint8) if tex_img.max() <= 1.0 else tex_img.astype(np.uint8)
                    if len(tex_img.shape) == 3 and tex_img.shape[2] == 3:
                        tex_img = cv2.cvtColor(tex_img, cv2.COLOR_BGR2RGB)
                    
                    pil_img = PILImage.fromarray(tex_img).convert("RGB")
                    
                    # Create explicit PBR Material for GLB embedding
                    material = PBRMaterial(
                        baseColorTexture=pil_img,
                        doubleSided=True,
                        roughnessFactor=0.8
                    )
                    
                    t_mesh.visual = trimesh.visual.TextureVisuals(
                        uv=vertex_uvs,
                        material=material
                    )
                else:
                    # Sync with deployable.py grey [0.7, 0.7, 0.7]
                    t_mesh.visual.face_colors = [178, 178, 178, 255]
                
                scene.add_geometry(t_mesh)

            glb_path = os.path.join(OUTPUT_DIR, f"fractured_{session_id}.glb")
            # Export as GLB with embedded textures
            scene.export(glb_path, file_type='glb')
            session["output_glb_path"] = glb_path
            session["model_path"] = glb_path

            # Step 6 – Groq risk analysis
            await push_progress(session_id, 6, 7, "Running AI risk analysis (Groq)…")
            risk = analyze_fracture_risk(fracture_data, groq_api_key)
            session["risk_result"] = risk

            # Step 7 – PERSIST TO SUPABASE & CLEANUP
            await push_progress(session_id, 7, 7, "Synchronizing with clinical cloud…")
            temp_xray = os.path.join(OUTPUT_DIR, f"xray_{session_id}.jpg")
            try:
                # 1. Upload X-ray image
                xray_url = None
                if img_orig is not None:
                    cv2.imwrite(temp_xray, img_orig)
                    xray_url = upload_file_to_supabase(
                        temp_xray, "fractures", f"users/{user_id}/{session_id}/xray.jpg", jwt_token
                    )

                # 2. Upload GLB model
                model_url = upload_file_to_supabase(
                    glb_path, "fractures", f"users/{user_id}/{session_id}/model.glb", jwt_token
                )
                
                # 3. Save to reports table
                report_entry = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "report_name": report_name,
                    "xray_url": xray_url,
                    "model_url": model_url,
                    "landmarks": Xray_landmark,
                    "fracture_data": fracture_data,
                    "risk_result": session["risk_result"],
                }
                save_report_to_supabase(report_entry, jwt_token)
                
                # Update session with cloud URLs for immediate UI consistency
                session["xray_url"] = xray_url
                session["model_url"] = model_url
                print(f"[Supabase] History saved and session updated for {session_id}")
            except Exception as e:
                print(f"[Supabase] Integration error: {e}")
            finally:
                # Cleanup disabled for local debugging
                pass
                # for p in [temp_xray, glb_path]:
                #     if os.path.exists(p):
                #         try: os.remove(p)
                #         except: pass

            # Step Done
            session["status"] = "done"
            await push_done(session_id)

        except Exception as e:
            session["status"] = "error"
            await push_error(session_id, str(e))
            raise

    loop.run_until_complete(run())
    loop.close()


@router.post("/landmarks")
async def submit_landmarks(req: LandmarksRequest, user=Depends(_get_current_user)):
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["xray_image"] is None:
        raise HTTPException(status_code=400, detail="No X-ray uploaded for this session")

    expected = {"ulna head", "ulna tail", "radius head", "radius tail"}
    received = {lm.label for lm in req.landmarks}
    if received != expected:
        raise HTTPException(
            status_code=422,
            detail=f"Expected landmarks: {expected}. Got: {received}",
        )

    # Convert to dict
    landmarks_px = {lm.label: (lm.x, lm.y) for lm in req.landmarks}
    session["status"] = "processing"

    # Kick off pipeline in background thread (non-blocking)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_pipeline,
        req.session_id, landmarks_px,
        req.image_width, req.image_height,
        req.groq_api_key, 
        user.get("id"),
        session.get("report_name", "New Analysis"),
        user.get("token")
    )

    return {"status": "processing", "message": "Pipeline started. Listen to /api/progress/{session_id} for updates."}


@router.get("/report/{session_id}")
async def get_report(session_id: str):
    # 1. Try memory session first
    session = get_session(session_id)
    if session and session.get("status") == "done":
        return {
            "report_name": session.get("report_name", "New Analysis"),
            "fracture_data": session["fracture_data"],
            "risk_result": session["risk_result"],
            "model_url": session.get("model_url") or f"/api/model/{session_id}",
            "xray_url": session.get("xray_url") or f"/api/outputs/xray_{session_id}.jpg",
        }

    # 2. Check Supabase for history
    historical = get_report_by_session(session_id)
    if historical:
        return {
            "report_name": historical.get("report_name", "Untitled Report"),
            "fracture_data": historical["fracture_data"],
            "risk_result": historical["risk_result"],
            "model_url": historical["model_url"] or f"/api/model/{session_id}",
            "xray_url": historical.get("xray_url") or f"/api/outputs/xray_{session_id}.jpg",
        }

    if session:
        raise HTTPException(status_code=409, detail=f"Pipeline status: {session['status']}")
    
    raise HTTPException(status_code=404, detail="Session not found in memory or database")


@router.get("/history")
async def get_history(user=Depends(_get_current_user)):
    reports = get_reports_from_supabase(user_id=user.get("id"), jwt_token=user.get("token"))
    # Simplify the response for the dashboard
    return [{
        "id": r["id"],
        "session_id": r["session_id"],
        "report_name": r.get("report_name", "Untitled Report"),
        "created_at": r["created_at"],
        "xray_url": r.get("xray_url"),
        "summary": (r["risk_result"].get("summary") if r["risk_result"] and "summary" in r["risk_result"] else "No summary available")
    } for r in reports]

@router.delete("/history/{session_id}")
async def delete_history(session_id: str, user=Depends(_get_current_user)):
    user_id = user.get("id")
    supabase = _get_client(jwt_token=None)
    # Verify ownership
    check = supabase.table("reports").select("user_id").eq("session_id", session_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if check.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this report")
        
    supabase.table("reports").delete().eq("session_id", session_id).execute()
    return {"status": "success", "message": "Report deleted"}
