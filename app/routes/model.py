"""
GET /api/model/{session_id} — Serve the generated fractured .glb model.
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.session_store import get_session

router = APIRouter()


@router.get("/model/{session_id}")
async def get_model(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    glb_path = session.get("output_glb_path")
    if not glb_path or not os.path.exists(glb_path):
        raise HTTPException(status_code=404, detail="3D model not yet generated. Run the pipeline first.")

    return FileResponse(
        glb_path,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'inline; filename="fractured_model_{session_id}.glb"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/model/download/{session_id}")
async def download_model(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    glb_path = session.get("output_glb_path")
    if not glb_path or not os.path.exists(glb_path):
        raise HTTPException(status_code=404, detail="3D model not yet generated.")

    return FileResponse(
        glb_path,
        media_type="model/gltf-binary",
        filename=f"fractured_forearm_{session_id}.glb",
        headers={"Content-Disposition": f'attachment; filename="fractured_forearm_{session_id}.glb"'}
    )
