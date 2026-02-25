import os
import json
import copy
import math
import tempfile
import argparse
from dotenv import load_dotenv

load_dotenv()  # Load .env before reading any env vars

import cv2
import numpy as np
import open3d as o3d
import requests
import faiss
import torch

# =============================================================
# PYTORCH 2.6+ COMPATIBILITY BYPASS
# This forces torch to allow loading the YOLO model's internal 
# structures which are blocked by default in newer versions.
# =============================================================
import functools
torch.load = functools.partial(torch.load, weights_only=False)

from ultralytics import YOLO
from sentence_transformers import SentenceTransformer

# =============================================================
#  CONFIGURATION – EDIT THESE PATHS / KEYS BEFORE RUNNING
# =============================================================

MODEL_3D_PATH   = "forearm_Bones.glb"          # Input 3D GLB model
IMAGE_PATH      = "test_image.jpg"              # Input X-ray image
YOLO_MODEL_PATH = "best(2).pt"                  # YOLO weights
FAISS_INDEX     = "forearm_index.faiss"         # FAISS index file
DOCUMENTS_JSON  = "documents.json"              # RAG document store

GROQ_API_KEY    = os.environ.get("GROQ_API_KEY")   # Or set in .env / creds.json
GROQ_MODEL      = "llama-3.3-70b-versatile"            # Or "llama-3.3-70b-versatile"

OUT_IMAGE_PATCH = "output_patch.jpg"             # Output annotated image
OUT_JSON        = "output_risk.json"             # Output risk JSON

# =============================================================
#  3D MESH PREPROCESSING & SPLITTING
# =============================================================

def load_and_preprocess_mesh(path):
    mesh = o3d.io.read_triangle_mesh(path)
    mesh.remove_duplicated_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()

    # Normalise size and centre
    mesh.scale(1 / np.max(mesh.get_max_bound() - mesh.get_min_bound()),
               center=mesh.get_center())
    mesh.translate(-mesh.get_center())
    mesh.compute_vertex_normals()

    # Rotate to a standard orientation
    R2 = mesh.get_rotation_matrix_from_axis_angle([0, -np.pi / 2, 0])
    mesh.rotate(R2, center=(0, 0, 0))
    return mesh


def split_mesh(mesh):
    """Split the full forearm mesh into ulna and radius using a tilted plane."""
    bbox = mesh.get_axis_aligned_bounding_box()
    min_bound = bbox.get_min_bound()
    max_bound = bbox.get_max_bound()
    size = max_bound - min_bound

    plane_height, plane_depth = size[1], size[2]
    plane_thickness = 0.001

    # Create a thin box as the splitting plane
    vertical_plane = o3d.geometry.TriangleMesh.create_box(
        width=plane_thickness, height=plane_height, depth=plane_depth)
    vertical_plane.translate((-plane_thickness / 2, -plane_height / 2, -plane_depth / 2))

    center_x = (min_bound[0] + max_bound[0]) / 2
    vertical_plane.translate((center_x, 0, 0))

    # Tilt the plane (empirical angle from the notebook)
    angle_from_x  = 94.11222884471846
    tilt_angle    = angle_from_x - 90
    angle_rad     = np.deg2rad(-tilt_angle)

    R = vertical_plane.get_rotation_matrix_from_axis_angle([0, 0, angle_rad])
    vertical_plane.rotate(R, center=vertical_plane.get_center())
    vertical_plane.translate((-0.015, 0, 0))   # fine adjustment

    plane_normal = R @ np.array([1.0, 0.0, 0.0])
    plane_normal /= np.linalg.norm(plane_normal)
    plane_center = vertical_plane.get_center()

    points = np.asarray(mesh.vertices)
    signed_dists = np.dot(points - plane_center, plane_normal)
    mask_above = signed_dists > 0
    mask_below = signed_dists <= 0

    mesh_ulna   = mesh.select_by_index(np.where(mask_above)[0].tolist())
    mesh_radius = mesh.select_by_index(np.where(mask_below)[0].tolist())

    # Colour for identification (optional)
    mesh_ulna.paint_uniform_color([0.2, 0.8, 1.0])
    mesh_radius.paint_uniform_color([1.0, 0.4, 0.4])

    return mesh_ulna, mesh_radius

# =============================================================
#  INTERACTIVE LANDMARK SELECTION ON X-RAY
# =============================================================

def get_landmarks_with_transform(img, labels):
    """
    OpenCV window with mouse callback and key controls.
    Returns: working image, pixel coordinates (original), centered coordinates.
    """
    working_img = img.copy()
    clone = working_img.copy()

    index = 0
    landmarks_px = {}
    marking_enabled = False

    def click(event, x, y, flags, param):
        nonlocal index, clone, landmarks_px
        if not marking_enabled:
            return
        if event == cv2.EVENT_LBUTTONDOWN and index < len(labels):
            label = labels[index]
            landmarks_px[label] = (x, y)
            cv2.circle(clone, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(clone, label, (x + 5, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            index += 1
            cv2.imshow("Image", clone)

    cv2.namedWindow("Image")
    cv2.setMouseCallback("Image", click)

    print("""
Controls:
 r = Rotate Right
 l = Rotate Left
 f = Flip Horizontal
 v = Flip Vertical
 c = Confirm Marking
 q = Quit
""")

    while True:
        cv2.imshow("Image", clone)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('r'):
            working_img = cv2.rotate(working_img, cv2.ROTATE_90_CLOCKWISE)
            clone = working_img.copy()
        elif key == ord('l'):
            working_img = cv2.rotate(working_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            clone = working_img.copy()
        elif key == ord('f'):
            working_img = cv2.flip(working_img, 1)
            clone = working_img.copy()
        elif key == ord('v'):
            working_img = cv2.flip(working_img, 0)
            clone = working_img.copy()
        elif key == ord('c'):
            marking_enabled = True
            print("Marking Enabled")
        elif key == ord('q'):
            break

        if index == len(labels):
            break

    cv2.destroyAllWindows()

    if len(landmarks_px) != len(labels):
        raise Exception("Not all landmarks selected!")

    h, w = working_img.shape[:2]
    cx, cy = w // 2, h // 2
    landmarks_centered = {}
    for k, (x, y) in landmarks_px.items():
        landmarks_centered[k] = (x - cx, cy - y)

    return working_img, landmarks_px, landmarks_centered

# =============================================================
#  YOLO FRACTURE DETECTION
# =============================================================

def get_fractures_with_crops(working_img, model):
    """Run YOLO, return dict of fractures and cropped images for each bone."""
    results = model(working_img)
    boxes = results[0].boxes.xyxy.cpu().numpy()

    h, w = working_img.shape[:2]
    cx = w // 2

    Xray_breaks = {}
    ulna_crop = None
    radius_crop = None

    if len(boxes) == 0:
        print("❌ No fractures detected.")
        return Xray_breaks, ulna_crop, radius_crop

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)

        fracture_w = x2 - x1
        fracture_h = y2 - y1
        fracture_size = (fracture_w, fracture_h)

        x_center = (x1 + x2) / 2
        y_center = (y1 + y2) / 2

        centered_pt = (int(x_center - cx), int((h // 2) - y_center))

        # Crop with small padding
        pad = 15
        x1p = max(0, x1 - pad)
        y1p = max(0, y1 - pad)
        x2p = min(w, x2 + pad)
        y2p = min(h, y2 + pad)
        crop = working_img[y1p:y2p, x1p:x2p]

        # Assign to bone based on horizontal position (left = radius, right = ulna)
        if x_center < cx:
            if "radius break" not in Xray_breaks:
                Xray_breaks["radius break"] = {"center": centered_pt, "size": fracture_size}
                radius_crop = crop
                print("→ radius fracture")
        else:
            if "ulna break" not in Xray_breaks:
                Xray_breaks["ulna break"] = {"center": centered_pt, "size": fracture_size}
                ulna_crop = crop
                print("→ ulna fracture")

    return Xray_breaks, ulna_crop, radius_crop


# =============================================================
#  ANGLE AND SPLIT RATIO UTILITIES
# =============================================================

def angle_from_negative_x(p1, p2, center=(0, 0)):
    """Angle in degrees between the line p1->p2 and the negative X axis."""
    x1, y1 = p1[0] - center[0], p1[1] - center[1]
    x2, y2 = p2[0] - center[0], p2[1] - center[1]
    dx, dy = x2 - x1, y2 - y1

    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad) % 360
    angle_from_neg_x = (angle_deg - 180) % 360

    if angle_from_neg_x <= 90:
        return -(90 - angle_from_neg_x)
    elif angle_from_neg_x <= 180:
        return angle_from_neg_x - 90
    elif angle_from_neg_x <= 270:
        return 270 - angle_from_neg_x
    return 360 - angle_from_neg_x


def get_split_ratio(point_top, point_bottom, split_point):
    """Fraction along the bone (0 at head, 1 at tail) where split occurs."""
    y_top, y_bottom, y_split = point_top[1], point_bottom[1], split_point[1]
    if y_top < y_bottom:
        y_top, y_bottom = y_bottom, y_top
    total_height = y_top - y_bottom
    if total_height == 0:
        return 0.5
    return 1 - (y_top - y_split) / total_height


def get_bone_region_size_px(head_pt, tail_pt):
    """Width and height (in pixels) of the bone bounding box."""
    x1, y1 = head_pt
    x2, y2 = tail_pt
    return abs(x2 - x1), abs(y2 - y1)


def get_patch_size_from_bone_region(head_pt, tail_pt, fracture_size_px, mesh):
    """Scale fracture size from pixels to mesh units using the bone's own size."""
    bone_w_px, bone_h_px = get_bone_region_size_px(head_pt, tail_pt)
    frac_w, frac_h = fracture_size_px

    if bone_w_px == 0 or bone_h_px == 0:
        return 0.01, 0.01

    bbox = mesh.get_axis_aligned_bounding_box()
    min_b = bbox.get_min_bound()
    max_b = bbox.get_max_bound()
    mesh_w = max_b[0] - min_b[0]
    mesh_h = max_b[1] - min_b[1]

    rx = frac_w / bone_w_px
    ry = frac_h / bone_h_px

    return mesh_w * rx, mesh_h * ry


# =============================================================
#  FRACTURE MODEL GENERATION
# =============================================================

def create_angle_mesh(mesh, angles, split_ratio):
    """
    Split mesh at a given ratio (along Y axis) and rotate top/bottom parts
    by the specified angles (in degrees) around Z.
    """
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)

    min_y = vertices[:, 1].min()
    max_y = vertices[:, 1].max()
    mid_y = min_y + (max_y - min_y) * split_ratio

    top_mask = vertices[:, 1] >= mid_y
    bottom_mask = ~top_mask

    def rotate_part(mask, angle_deg, center_y):
        indices = np.where(mask)[0]
        sub_vertices = np.copy(vertices[indices])

        index_map = -np.ones(len(vertices), dtype=int)
        index_map[indices] = np.arange(len(indices))

        tri_mask = np.all(mask[triangles], axis=1)
        sub_triangles = triangles[tri_mask]
        mapped_triangles = index_map[sub_triangles]

        angle_rad = np.radians(angle_deg)
        R = mesh.get_rotation_matrix_from_axis_angle([0, 0, angle_rad])
        center = [sub_vertices[:, 0].mean(), center_y, sub_vertices[:, 2].mean()]
        rotated = (R @ (sub_vertices - center).T).T + center

        sub_mesh = o3d.geometry.TriangleMesh()
        sub_mesh.vertices = o3d.utility.Vector3dVector(rotated)
        sub_mesh.triangles = o3d.utility.Vector3iVector(mapped_triangles)
        sub_mesh.compute_vertex_normals()
        return sub_mesh

    top_mesh = rotate_part(top_mask, angles[0], mid_y)
    bottom_mesh = rotate_part(bottom_mask, angles[1], mid_y)

    return top_mesh + bottom_mesh


def make_solid(mesh, points=20000, depth=10):
    """Convert a triangle mesh to a solid (watertight) mesh using Poisson reconstruction."""
    pcd = mesh.sample_points_poisson_disk(points)
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(100)

    solid, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth)
    densities_np = np.asarray(densities)
    mask = densities_np < densities_np.mean() * 0.5
    solid.remove_vertices_by_mask(mask)

    solid.remove_duplicated_vertices()
    solid.remove_degenerate_triangles()
    solid.remove_non_manifold_edges()
    solid.remove_unreferenced_vertices()
    solid.compute_vertex_normals()
    return solid


def make_fracture_image_patch(mesh, split_ratio, fracture_size_px,
                              head_pt, tail_pt, fracture_img,
                              texture_resolution=256):
    """
    Create a textured quad that shows the actual X‑ray fracture image,
    placed at the fracture location on the bone.
    """
    patch_w, patch_h = get_patch_size_from_bone_region(
        head_pt, tail_pt, fracture_size_px, mesh)

    bbox = mesh.get_axis_aligned_bounding_box()
    min_b = bbox.get_min_bound()
    max_b = bbox.get_max_bound()

    y = min_b[1] + split_ratio * (max_b[1] - min_b[1])
    x = (min_b[0] + max_b[0]) / 2
    z = max_b[2] + 0.002   # slightly in front of the bone

    hw, hh = patch_w / 2, patch_h / 2

    vertices = np.array([
        [x - hw, y - hh, z],
        [x + hw, y - hh, z],
        [x + hw, y + hh, z],
        [x - hw, y + hh, z],
    ], dtype=np.float64)

    triangles = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    uvs = np.array([
        [0.0, 1.0], [1.0, 1.0], [1.0, 0.0],
        [0.0, 1.0], [1.0, 0.0], [0.0, 0.0],
    ], dtype=np.float64)

    patch = o3d.geometry.TriangleMesh()
    patch.vertices = o3d.utility.Vector3dVector(vertices)
    patch.triangles = o3d.utility.Vector3iVector(triangles)
    patch.triangle_uvs = o3d.utility.Vector2dVector(uvs)
    patch.triangle_material_ids = o3d.utility.IntVector([0, 0])
    patch.compute_vertex_normals()

    # Resize and embed texture
    tex = cv2.resize(fracture_img, (texture_resolution, texture_resolution),
                     interpolation=cv2.INTER_LINEAR)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, tex)
    tmp.close()
    patch.textures = [o3d.io.read_image(tmp.name)]
    os.unlink(tmp.name)

    return patch


# =============================================================
#  RAG + GROQ RISK ANALYSIS
# =============================================================

def load_rag(faiss_path, docs_path):
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    index = faiss.read_index(faiss_path)
    with open(docs_path, "r", encoding="utf-8") as f:
        documents = json.load(f)
    return embedder, index, documents


def retrieve_context(fracture_list, embedder, index, documents, k=5):
    query = json.dumps(fracture_list)
    vector = embedder.encode([query]).astype("float32")
    _, I = index.search(vector, k)
    docs = [documents[i] for i in I[0]]
    return "\n\n".join(docs)


def build_prompt(context, fracture_list):
    fracture_json = json.dumps(fracture_list, indent=2)
    return f"""
You are a senior orthopedic trauma specialist AI analyzing forearm fractures.

The data is derived from 2D X-ray analysis.
Depth information is NOT available.
You must infer displacement risk using location and angulation only.

### Context:
{context}

### Fracture Data:
{fracture_json}

### Clinical Reasoning Requirements:
Use advanced anatomical reasoning including:
- Proximity of neurovascular bundles to fracture site
- Effect of angulation differences (top vs bottom angle)
- Biomechanical instability from bilateral bone involvement
- Risk of vessel compression from fragment displacement
- Risk of nerve entrapment due to angular deformity
- Compartment pressure risk if applicable

### Task:
1. Identify blood vessels and nerves at risk.
2. Estimate probability of damage (0.0 to 1.0).
3. Always return AT LEAST 3 structures.
4. Prefer structures with probability >= 0.4.
5. If fewer than 3 exceed 0.4, still include top 3 highest risks.
6. Sort by probability descending.

### Output Format (STRICT JSON ONLY):
{{
  "damaged_structures": [
    {{
      "name": "structure name",
      "probability": 0.00
    }}
  ],
  "summary": "Detailed clinical summary of 6-10 sentences explaining anatomical risk, biomechanical implications, displacement mechanics, vascular compromise mechanisms, and nerve compression pathways."
}}

### Rules:
- Minimum 3 structures required
- Summary must be detailed (minimum 6 sentences)
- Valid JSON only
- No markdown
- No extra commentary
- Double quotes only
- Probabilities must be between 0.0 and 1.0
"""


def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a clinical fracture risk assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers, json=payload, timeout=60)
    data = response.json()
    if "choices" not in data:
        raise RuntimeError(f"Groq API Error: {data}")
    return data["choices"][0]["message"]["content"].strip()


def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found in LLM output")
    return text[start:end + 1]


def validate_output(result):
    if "damaged_structures" not in result:
        raise ValueError("Invalid output format")
    structures = result["damaged_structures"]
    valid = []
    for s in structures:
        prob = float(np.clip(float(s.get("probability", 0)), 0.0, 1.0))
        valid.append({"name": s.get("name", "unknown"), "probability": round(prob, 2)})
    valid.sort(key=lambda x: x["probability"], reverse=True)
    if len(valid) < 3:
        raise ValueError("LLM returned fewer than 3 structures")
    result["damaged_structures"] = valid
    return result


def analyze_fracture_risk(fracture_list, embedder, index, documents):
    context = retrieve_context(fracture_list, embedder, index, documents)
    prompt = build_prompt(context, fracture_list)
    raw_response = call_groq(prompt)
    clean_json = extract_json(raw_response)
    result = json.loads(clean_json)
    result = validate_output(result)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    print(f"[✓] Risk JSON saved → {OUT_JSON}")
    return result


# =============================================================
#  MAIN PIPELINE
# =============================================================

def main():
    # load_dotenv() already called at module level

    print("[1/7] Loading and preprocessing 3D model...")
    mesh = load_and_preprocess_mesh(MODEL_3D_PATH)

    print("[2/7] Splitting mesh into ulna / radius...")
    mesh_ulna, mesh_radius = split_mesh(mesh)

    # Note: Landmark cylinders are NOT created or used in final visualization.

    print("[3/7] Loading X-ray image for interactive landmark selection...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {IMAGE_PATH}")
    # Resize to 50% as in notebook
    scale = 50
    w = int(img.shape[1] * scale / 100)
    h = int(img.shape[0] * scale / 100)
    resized_img = cv2.resize(img, (w, h))

    labels = ["ulna head", "ulna tail", "radius head", "radius tail"]
    working_img, px, Xray_landmark = get_landmarks_with_transform(resized_img, labels)
    print("Landmarks (centered):", Xray_landmark)

    print("[4/7] Running YOLO fracture detection...")
    model = YOLO(YOLO_MODEL_PATH)
    Xray_breaks, ulna_img, radius_img = get_fractures_with_crops(working_img, model)

    # Prepare fracture data for JSON report
    fracture_data = []

    # Process Ulna if fracture exists
    if ("ulna break" in Xray_breaks and "ulna head" in Xray_landmark and "ulna tail" in Xray_landmark):
        ulna_break_pt = Xray_breaks["ulna break"]["center"]
        split_ratio_ulna = get_split_ratio(
            Xray_landmark["ulna head"], Xray_landmark["ulna tail"], ulna_break_pt)
        top_angle_ulna = angle_from_negative_x(Xray_landmark["ulna head"], ulna_break_pt)
        bottom_angle_ulna = angle_from_negative_x(ulna_break_pt, Xray_landmark["ulna tail"])

        fractured_ulna = create_angle_mesh(
            mesh_ulna,
            angles=[top_angle_ulna, bottom_angle_ulna],
            split_ratio=split_ratio_ulna
        )
        # Make solid for better visualization
        solid_ulna = make_solid(fractured_ulna)
        solid_ulna.paint_uniform_color([0.7, 0.7, 0.7])

        # Create textured patch
        ulna_patch = make_fracture_image_patch(
            mesh_ulna,
            split_ratio=split_ratio_ulna,
            fracture_size_px=Xray_breaks["ulna break"]["size"],
            head_pt=Xray_landmark["ulna head"],
            tail_pt=Xray_landmark["ulna tail"],
            fracture_img=ulna_img
        )

        # Add to fracture data for JSON
        fracture_data.append({
            "bone": "ulna",
            "damage": "crack",
            "location": round(float(split_ratio_ulna), 3),
            "top_angle": round(float(top_angle_ulna), 2),
            "bottom_angle": round(float(bottom_angle_ulna), 2)
        })
    else:
        # If no fracture, use original mesh and make solid
        solid_ulna = make_solid(mesh_ulna)
        solid_ulna.paint_uniform_color([0.7, 0.7, 0.7])
        ulna_patch = None

    # Process Radius similarly
    if ("radius break" in Xray_breaks and "radius head" in Xray_landmark and "radius tail" in Xray_landmark):
        radius_break_pt = Xray_breaks["radius break"]["center"]
        split_ratio_radius = get_split_ratio(
            Xray_landmark["radius head"], Xray_landmark["radius tail"], radius_break_pt)
        top_angle_radius = angle_from_negative_x(Xray_landmark["radius head"], radius_break_pt)
        bottom_angle_radius = angle_from_negative_x(radius_break_pt, Xray_landmark["radius tail"])

        fractured_radius = create_angle_mesh(
            mesh_radius,
            angles=[top_angle_radius, bottom_angle_radius],
            split_ratio=split_ratio_radius
        )
        solid_radius = make_solid(fractured_radius)
        solid_radius.paint_uniform_color([0.7, 0.7, 0.7])

        radius_patch = make_fracture_image_patch(
            mesh_radius,
            split_ratio=split_ratio_radius,
            fracture_size_px=Xray_breaks["radius break"]["size"],
            head_pt=Xray_landmark["radius head"],
            tail_pt=Xray_landmark["radius tail"],
            fracture_img=radius_img
        )

        fracture_data.append({
            "bone": "radius",
            "damage": "crack",
            "location": round(float(split_ratio_radius), 3),
            "top_angle": round(float(top_angle_radius), 2),
            "bottom_angle": round(float(bottom_angle_radius), 2)
        })
    else:
        solid_radius = make_solid(mesh_radius)
        solid_radius.paint_uniform_color([0.7, 0.7, 0.7])
        radius_patch = None

    # Assemble geometries for visualization – NO LANDMARK CYLINDERS
    geometries = [solid_radius, solid_ulna]
    if ulna_patch:
        geometries.append(ulna_patch)
    if radius_patch:
        geometries.append(radius_patch)

    # Save the annotated image patch
    cv2.imwrite(OUT_IMAGE_PATCH, working_img)
    print(f"[✓] Annotated image saved → {OUT_IMAGE_PATCH}")

    # Print fracture report
    print("\n--- Fracture Report (JSON) ---")
    print(json.dumps(fracture_data, indent=4))

    print("[5/7] Running RAG + Groq risk analysis...")

    GROQ_API_KEY = None
    if os.path.exists("creds.json"):
        try:
            with open("creds.json", "r") as f:
                creds = json.load(f)
                GROQ_API_KEY = creds.get("api_key")
            if GROQ_API_KEY:
                print("[✓] Loaded Groq API key from creds.json")
            else:
                print("[!] 'api_key' not found in creds.json")
        except Exception as e:
            print(f"[!] Error reading creds.json: {e}")
    else:
        # Fallback to environment variable
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
        if GROQ_API_KEY:
            print("[✓] Loaded Groq API key from environment variable")

    # Save annotated image patch
    cv2.imwrite(OUT_IMAGE_PATCH, working_img)
    print(f"[✓] Annotated image saved → {OUT_IMAGE_PATCH}")

    # Print fracture report
    print("\n--- Fracture Report (JSON) ---")
    print(json.dumps(fracture_data, indent=4))

     # --- RISK ANALYSIS (if API key available) ---
    print("[6/7] Running RAG + Groq risk analysis...")

    # Load API key from creds.json or environment
    groq_api_key = None
    if os.path.exists("creds.json"):
        try:
            with open("creds.json", "r") as f:
                creds = json.load(f)
                groq_api_key = creds.get("api_key")
            if groq_api_key:
                print("[✓] Loaded Groq API key from creds.json")
            else:
                print("[!] 'api_key' not found in creds.json")
        except Exception as e:
            print(f"[!] Error reading creds.json: {e}")
    else:
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if groq_api_key:
            print("[✓] Loaded Groq API key from environment variable")

    GROQ_API_KEY = groq_api_key

    if GROQ_API_KEY:
        try:
            embedder, index, documents = load_rag(FAISS_INDEX, DOCUMENTS_JSON)
            risk_result = analyze_fracture_risk(fracture_data, embedder, index, documents)
            print("\n========== RISK ANALYSIS ==========")
            print(json.dumps(risk_result, indent=4))
            print("====================================")
        except Exception as e:
            print(f"❌ Risk analysis failed: {e}")
    else:
        print("⚠️  GROQ_API_KEY not set. Skipping risk analysis.")

    # --- SAVE 3D MODEL FIRST ---
    OUT_3D_MODEL = "output_fractured_model.glb"
    o3d.io.write_triangle_mesh(OUT_3D_MODEL, solid_ulna + solid_radius)
    print(f"\n[✓] Outputs saved successfully:")
    print(f"  3D Model    : {OUT_3D_MODEL}")
    print(f"  Image Patch : {OUT_IMAGE_PATCH}")
    print(f"  Risk JSON   : {OUT_JSON}")

    # --- SHOW 3D VISUALIZATION ---
    print("\n[7/7] Attempting to open 3D viewer... (If this fails, open the .glb file manually)")
    try:
        o3d.visualization.draw_geometries(geometries, window_name="Fracture Viewer")
    except Exception as e:
        print(f"⚠️  Note: Could not open 3D window ({e}). Please use the Windows 3D Viewer to open {OUT_3D_MODEL} instead.")

    print("\n✅ Pipeline finished.")


if __name__ == "__main__":
    main()