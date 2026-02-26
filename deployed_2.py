import os
import json
import copy
import math
import tempfile
import argparse
import re
from dotenv import load_dotenv

import cv2
import numpy as np
import open3d as o3d
import trimesh
import requests
import faiss
import torch
import functools
# =============================================================
# PYTORCH 2.6+ COMPATIBILITY BYPASS
# This forces torch to allow loading the YOLO model's internal 
# structures which are blocked by default in newer versions.
# =============================================================
torch.load = functools.partial(torch.load, weights_only=False)

from ultralytics import YOLO
from sentence_transformers import SentenceTransformer

# =============================================================
#  CONFIGURATION – EDIT THESE PATHS / KEYS BEFORE RUNNING
# =============================================================

# --- Bone model & X‑ray ---
MODEL_3D_PATH          = "forearm_Bones.glb"          # Input 3D GLB model (bones)
IMAGE_PATH             = "test_image.jpg"             # Input X-ray image
YOLO_MODEL_PATH        = "best(2).pt"                 # YOLO weights
OUT_IMAGE_PATCH        = "output_patch.jpg"           # Output annotated image

# Output solid models (optional)
OUT_SOLID_ULNA         = "solid_ulna.ply"
OUT_SOLID_RADIUS       = "solid_radius.ply"
OUT_SOLID_COMBINED     = "solid_combined.ply"

# --- RAG / LLM (from deployable.py) ---
FAISS_INDEX            = "forearm_index.faiss"        # FAISS index file
DOCUMENTS_JSON         = "documents.json"             # RAG document store
GROQ_API_KEY           = "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"                   # Set via env or creds.json
GROQ_MODEL             = "llama-3.3-70b-versatile"
OUT_RISK_JSON          = "output_risk.json"           # Risk analysis output

# --- Soft‑tissue model & coloring ---
SOFT_TISSUE_MODEL_PATH = r"C:\Hackathon\3D bone mapping\VOIC_final\vanes_4.glb"
OUT_SOFT_TISSUE_COLORED = "colored_soft_tissue.glb"

# =============================================================
#  HELPER FUNCTIONS (from both files)
# =============================================================

def point_to_line_distance(pt, line_pt1, line_pt2):
    """Distance from point to line segment."""
    x0, y0 = pt
    x1, y1 = line_pt1
    x2, y2 = line_pt2
    numerator = abs((y2 - y1)*x0 - (x2 - x1)*y0 + x2*y1 - y2*x1)
    denominator = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
    if denominator == 0:
        return float("inf")
    return numerator / denominator


def get_connected_edge_image(img):
    """
    Enhanced edge detection (from deployable.py).
    Returns a binary image of connected bone edges.
    """
    img = img.copy()
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if img.dtype != np.uint8:
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        img = img.astype(np.uint8)

    clahe = cv2.createCLAHE(3.0, (8,8))
    enhanced = clahe.apply(img)
    blur = cv2.GaussianBlur(enhanced, (5,5), 1.2)
    edges = cv2.Canny(blur, 20, 80)

    kernel_d = np.ones((3,3), np.uint8)
    kernel_c = np.ones((7,7), np.uint8)
    edges = cv2.dilate(edges, kernel_d, iterations=2)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_c)
    return edges


def make_fracture_image_patch(
    mesh,
    split_ratio,
    fracture_size_px,
    head_pt,
    tail_pt,
    fracture_img,
    texture_resolution=256
):
    """
    Create a textured quad patch placed at the fracture location.
    (from deployable.py)
    """
    patch_w, patch_h = get_patch_size_from_bone_region(
        head_pt, tail_pt, fracture_size_px, mesh
    )

    bbox = mesh.get_axis_aligned_bounding_box()
    min_b = bbox.get_min_bound()
    max_b = bbox.get_max_bound()

    y = min_b[1] + split_ratio * (max_b[1] - min_b[1])
    x = (min_b[0] + max_b[0]) / 2
    z = max_b[2] + 0.002          # just in front of the bone surface

    hw, hh = patch_w / 2, patch_h / 2

    vertices = np.array([
        [x - hw, y - hh, z],   # bottom-left
        [x + hw, y - hh, z],   # bottom-right
        [x + hw, y + hh, z],   # top-right
        [x - hw, y + hh, z],   # top-left
    ], dtype=np.float64)

    triangles = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    uvs = np.array([
        [0.0, 1.0], [1.0, 1.0], [1.0, 0.0],   # triangle 0
        [0.0, 1.0], [1.0, 0.0], [0.0, 0.0],   # triangle 1
    ], dtype=np.float64)

    patch = o3d.geometry.TriangleMesh()
    patch.vertices = o3d.utility.Vector3dVector(vertices)
    patch.triangles = o3d.utility.Vector3iVector(triangles)
    patch.triangle_uvs = o3d.utility.Vector2dVector(uvs)
    patch.triangle_material_ids = o3d.utility.IntVector([0, 0])
    patch.compute_vertex_normals()

    # Resize and save texture to temporary file
    tex = cv2.resize(fracture_img, (texture_resolution, texture_resolution),
                     interpolation=cv2.INTER_LINEAR)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, tex)
    tmp.close()
    patch.textures = [o3d.io.read_image(tmp.name)]
    os.unlink(tmp.name)
    return patch


def get_points_from_nonblack_patch(patch, mesh, black_threshold=30):
    """
    Extract 3D points from the mesh that correspond to non‑black regions
    in the patch texture. (from deployable.py)
    """
    if not hasattr(patch, 'textures') or len(patch.textures) == 0:
        return np.array([])

    texture = patch.textures[0]
    tex_img = np.asarray(texture)

    if len(tex_img.shape) == 3:
        nonblack_mask = np.any(tex_img > black_threshold, axis=2)
    else:
        nonblack_mask = tex_img > black_threshold

    patch_verts = np.asarray(patch.vertices)
    min_xy = patch_verts[:, :2].min(axis=0)
    max_xy = patch_verts[:, :2].max(axis=0)
    h, w = nonblack_mask.shape[:2]

    mesh_points = np.asarray(mesh.vertices)
    selected = []
    for point in mesh_points:
        x, y = point[0], point[1]
        if x < min_xy[0] or x > max_xy[0] or y < min_xy[1] or y > max_xy[1]:
            continue
        u = (x - min_xy[0]) / (max_xy[0] - min_xy[0]) if max_xy[0] > min_xy[0] else 0
        v = 1.0 - (y - min_xy[1]) / (max_xy[1] - min_xy[1]) if max_xy[1] > min_xy[1] else 0
        u = np.clip(u, 0, 0.999)
        v = np.clip(v, 0, 0.999)
        px = int(u * w)
        py = int(v * h)
        if 0 <= px < w and 0 <= py < h and nonblack_mask[py, px]:
            selected.append(point)
    return np.array(selected)


def remove_nonblack_points_from_mesh(mesh, patch, black_threshold=30):
    """
    Remove vertices from the mesh that correspond to non‑black regions
    in the patch texture. (from deployable.py)
    """
    if not hasattr(patch, 'textures') or len(patch.textures) == 0:
        return mesh

    texture = patch.textures[0]
    tex_img = np.asarray(texture)

    if len(tex_img.shape) == 3:
        nonblack_mask = np.any(tex_img > black_threshold, axis=2)
    else:
        nonblack_mask = tex_img > black_threshold

    patch_verts = np.asarray(patch.vertices)
    min_xy = patch_verts[:, :2].min(axis=0)
    max_xy = patch_verts[:, :2].max(axis=0)
    h, w = nonblack_mask.shape[:2]

    mesh_verts = np.asarray(mesh.vertices)
    mesh_tris = np.asarray(mesh.triangles)

    keep = np.ones(len(mesh_verts), dtype=bool)
    for i, point in enumerate(mesh_verts):
        x, y = point[0], point[1]
        if x < min_xy[0] or x > max_xy[0] or y < min_xy[1] or y > max_xy[1]:
            continue
        u = (x - min_xy[0]) / (max_xy[0] - min_xy[0]) if max_xy[0] > min_xy[0] else 0
        v = 1.0 - (y - min_xy[1]) / (max_xy[1] - min_xy[1]) if max_xy[1] > min_xy[1] else 0
        u = np.clip(u, 0, 0.999)
        v = np.clip(v, 0, 0.999)
        px = int(u * w)
        py = int(v * h)
        if 0 <= px < w and 0 <= py < h and nonblack_mask[py, px]:
            keep[i] = False

    if np.all(keep):
        return mesh
    if not np.any(keep):
        return o3d.geometry.TriangleMesh()

    old_to_new = -np.ones(len(mesh_verts), dtype=int)
    old_to_new[keep] = np.arange(np.sum(keep))
    new_verts = mesh_verts[keep]
    keep_tris = np.all(keep[mesh_tris], axis=1)
    new_tris = old_to_new[mesh_tris[keep_tris]]

    new_mesh = o3d.geometry.TriangleMesh()
    new_mesh.vertices = o3d.utility.Vector3dVector(new_verts)
    new_mesh.triangles = o3d.utility.Vector3iVector(new_tris)
    if mesh.has_vertex_colors():
        colors = np.asarray(mesh.vertex_colors)
        new_mesh.vertex_colors = o3d.utility.Vector3dVector(colors[keep])
    new_mesh.compute_vertex_normals()
    return new_mesh


def visualize_removed_points(original_mesh, modified_mesh, color):
    """Create a point cloud of vertices removed from the mesh."""
    orig_verts = set(map(tuple, np.asarray(original_mesh.vertices)))
    mod_verts = set(map(tuple, np.asarray(modified_mesh.vertices)))
    removed = np.array(list(orig_verts - mod_verts))
    if len(removed) > 0:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(removed)
        pcd.paint_uniform_color(color)
        return pcd
    return None


# =============================================================
#  BONE PROCESSING FUNCTIONS (shared by both files)
# =============================================================

def load_and_preprocess_mesh(path):
    mesh = o3d.io.read_triangle_mesh(path)
    mesh.remove_duplicated_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()

    mesh.scale(1 / np.max(mesh.get_max_bound() - mesh.get_min_bound()),
               center=mesh.get_center())
    mesh.translate(-mesh.get_center())
    mesh.compute_vertex_normals()

    R2 = mesh.get_rotation_matrix_from_axis_angle([0, -np.pi / 2, 0])
    mesh.rotate(R2, center=(0, 0, 0))
    return mesh


def split_mesh(mesh):
    """Split forearm mesh into ulna and radius using a tilted plane."""
    bbox = mesh.get_axis_aligned_bounding_box()
    min_bound = bbox.get_min_bound()
    max_bound = bbox.get_max_bound()
    size = max_bound - min_bound

    plane_height, plane_depth = size[1], size[2]
    plane_thickness = 0.001

    vertical_plane = o3d.geometry.TriangleMesh.create_box(
        width=plane_thickness, height=plane_height, depth=plane_depth)
    vertical_plane.translate((-plane_thickness / 2, -plane_height / 2, -plane_depth / 2))

    center_x = (min_bound[0] + max_bound[0]) / 2
    vertical_plane.translate((center_x, 0, 0))

    angle_from_x = 94.11222884471846
    tilt_angle = angle_from_x - 90
    angle_rad = np.deg2rad(-tilt_angle)

    R = vertical_plane.get_rotation_matrix_from_axis_angle([0, 0, angle_rad])
    vertical_plane.rotate(R, center=vertical_plane.get_center())
    vertical_plane.translate((-0.015, 0, 0))

    plane_normal = R @ np.array([1.0, 0.0, 0.0])
    plane_normal /= np.linalg.norm(plane_normal)
    plane_center = vertical_plane.get_center()

    points = np.asarray(mesh.vertices)
    signed_dists = np.dot(points - plane_center, plane_normal)
    mask_above = signed_dists > 0
    mask_below = signed_dists <= 0

    mesh_ulna = mesh.select_by_index(np.where(mask_above)[0].tolist())
    mesh_radius = mesh.select_by_index(np.where(mask_below)[0].tolist())

    mesh_ulna.paint_uniform_color([0.2, 0.8, 1.0])
    mesh_radius.paint_uniform_color([1.0, 0.4, 0.4])
    return mesh_ulna, mesh_radius


def get_landmarks_with_transform(img, labels):
    """
    OpenCV window with mouse callback and key controls.
    Returns working image, pixel coordinates, centered coordinates.
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


def get_fractures_with_crops(working_img, model, Xray_landmarks):
    """
    Run YOLO and assign fractures to bones using distance to landmark lines.
    (Improved version from deployed_2.py)
    """
    results = model(working_img)[0]
    boxes = results.boxes.xyxy.cpu().numpy()
    confs = results.boxes.conf.cpu().numpy()

    h, w = working_img.shape[:2]
    cx = w // 2

    Xray_breaks = {}
    ulna_crop = None
    radius_crop = None

    if len(boxes) == 0:
        print("❌ No fractures detected.")
        return Xray_breaks, ulna_crop, radius_crop

    ulna_head = Xray_landmarks["ulna head"]
    ulna_tail = Xray_landmarks["ulna tail"]
    radius_head = Xray_landmarks["radius head"]
    radius_tail = Xray_landmarks["radius tail"]

    candidates = []
    for box, conf in zip(boxes, confs):
        if conf < 0.3:
            continue
        x1, y1, x2, y2 = map(int, box)
        width = x2 - x1
        height = y2 - y1
        x_center = (x1 + x2) / 2
        y_center = (y1 + y2) / 2
        centered_pt = (int(x_center - cx), int((h // 2) - y_center))
        d_ulna = point_to_line_distance(centered_pt, ulna_head, ulna_tail)
        d_radius = point_to_line_distance(centered_pt, radius_head, radius_tail)

        pad = 15
        x1p = max(0, x1 - pad)
        y1p = max(0, y1 - pad)
        x2p = min(w, x2 + pad)
        y2p = min(h, y2 + pad)
        crop = working_img[y1p:y2p, x1p:x2p]

        candidates.append({
            "center": centered_pt,
            "size": (width, height),
            "d_ulna": d_ulna,
            "d_radius": d_radius,
            "crop": crop
        })

    if len(candidates) == 0:
        print("❌ No fractures above confidence threshold.")
        return Xray_breaks, ulna_crop, radius_crop

    if len(candidates) == 1:
        f = candidates[0]
        if f["d_ulna"] <= f["d_radius"]:
            Xray_breaks["ulna break"] = f
            ulna_crop = f["crop"]
            print("→ Single fracture assigned to ULNA")
        else:
            Xray_breaks["radius break"] = f
            radius_crop = f["crop"]
            print("→ Single fracture assigned to RADIUS")
    else:
        f1, f2 = candidates[0], candidates[1]
        cost1 = f1["d_ulna"] + f2["d_radius"]
        cost2 = f2["d_ulna"] + f1["d_radius"]
        if cost1 <= cost2:
            ulna_choice, radius_choice = f1, f2
        else:
            ulna_choice, radius_choice = f2, f1
        Xray_breaks["ulna break"] = ulna_choice
        Xray_breaks["radius break"] = radius_choice
        ulna_crop = ulna_choice["crop"]
        radius_crop = radius_choice["crop"]
        print("→ Two fractures optimally assigned")

    return Xray_breaks, ulna_crop, radius_crop


def angle_from_negative_x(p1, p2, center=(0,0)):
    """Angle (degrees) between line p1->p2 and negative X axis."""
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
    y_top, y_bottom, y_split = point_top[1], point_bottom[1], split_point[1]
    if y_top < y_bottom:
        y_top, y_bottom = y_bottom, y_top
    total = y_top - y_bottom
    if total == 0:
        return 0.5
    return 1 - (y_top - y_split) / total


def get_bone_region_size_px(head_pt, tail_pt):
    x1, y1 = head_pt
    x2, y2 = tail_pt
    return abs(x2 - x1), abs(y2 - y1)


def get_patch_size_from_bone_region(head_pt, tail_pt, fracture_size_px, mesh):
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


def create_angle_mesh(mesh, angles, split_ratio):
    """
    Split mesh at a given ratio (along Y) and rotate top/bottom parts
    by the specified angles (degrees) around Z.
    """
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)

    min_y = vertices[:, 1].min()
    max_y = vertices[:, 1].max()
    mid_y = min_y + (max_y - min_y) * split_ratio

    top_mask = vertices[:, 1] >= mid_y
    bottom_mask = ~top_mask

    def rotate_part(mask, angle_deg, center_y):
        idx = np.where(mask)[0]
        sub_verts = np.copy(vertices[idx])
        idx_map = -np.ones(len(vertices), dtype=int)
        idx_map[idx] = np.arange(len(idx))

        tri_mask = np.all(mask[triangles], axis=1)
        sub_tris = triangles[tri_mask]
        mapped_tris = idx_map[sub_tris]

        angle_rad = np.radians(angle_deg)
        R = mesh.get_rotation_matrix_from_axis_angle([0, 0, angle_rad])
        center = [sub_verts[:, 0].mean(), center_y, sub_verts[:, 2].mean()]
        rotated = (R @ (sub_verts - center).T).T + center

        sub_mesh = o3d.geometry.TriangleMesh()
        sub_mesh.vertices = o3d.utility.Vector3dVector(rotated)
        sub_mesh.triangles = o3d.utility.Vector3iVector(mapped_tris)
        sub_mesh.compute_vertex_normals()
        return sub_mesh

    top_mesh = rotate_part(top_mask, angles[0], mid_y)
    bottom_mesh = rotate_part(bottom_mask, angles[1], mid_y)
    return top_mesh + bottom_mesh


def make_solid(mesh, points=20000, depth=10):
    """Convert mesh to watertight solid using Poisson reconstruction."""
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

# =============================================================
#  SOFT TISSUE COLORING FUNCTIONS (from deployed_2.py)
# =============================================================

def load_risk_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    structures = data.get('damaged_structures', [])
    risk_dict = {s['name'].lower(): s['probability'] for s in structures}
    print("\n[Soft tissue] Loaded risk dictionary:")
    for name, prob in risk_dict.items():
        print(f"   {name}: {prob}")
    return risk_dict


def normalize_node_name(node_name):
    # Remove trailing .001, .002, .r, .r.001 etc.
    name = re.sub(r'\.(?:r(?:\.\d+)?|\d+)$', '', node_name)
    name = re.sub(r'[()]', '', name)
    return name.replace('_', ' ').lower().strip()


def get_color_by_rank(rank, total):
    if total == 1:
        return [1, 0, 0]
    if rank == 0:
        return [1, 0, 0]
    elif rank == 1:
        return [1, 0.3, 0]
    elif rank == 2:
        return [1, 0.5, 0]
    elif rank == 3:
        return [1, 0.7, 0]
    elif rank == total - 1:
        return [0.5, 0.5, 0.5]
    else:
        factor = (rank - 1) / (total - 2) if total > 2 else 0
        g = 0.5 + 0.5 * factor
        return [1, g, 0]


def color_soft_tissue_model(soft_tissue_path, risk_dict):
    scene = trimesh.load(soft_tissue_path, force='scene')
    print(f"\nLoaded soft tissue model with {len(scene.graph.nodes_geometry)} meshes.")

    mesh_list = []  # (node_name, probability, o3d_mesh)

    for node_name in scene.graph.nodes_geometry:
        geom_name = scene.graph[node_name][1]
        transform = scene.graph.get(node_name)[0]
        mesh = scene.geometry[geom_name].copy()
        mesh.apply_transform(transform)

        o3_mesh = o3d.geometry.TriangleMesh()
        o3_mesh.vertices = o3d.utility.Vector3dVector(mesh.vertices)
        o3_mesh.triangles = o3d.utility.Vector3iVector(mesh.faces)
        o3_mesh.compute_vertex_normals()

        base_name = normalize_node_name(node_name)
        prob = risk_dict.get(base_name)
        print(f"   Node: {node_name} -> normalized: '{base_name}' -> probability: {prob}")
        mesh_list.append((node_name, prob, o3_mesh))

    risk_meshes = [(n, p, m) for n, p, m in mesh_list if p is not None]
    risk_meshes.sort(key=lambda x: x[1], reverse=True)
    print(f"\nFound {len(risk_meshes)} structures with risk data.")

    total_risk = len(risk_meshes)
    coloured = []
    for rank, (node_name, prob, o3_mesh) in enumerate(risk_meshes):
        colour = get_color_by_rank(rank, total_risk)
        o3_mesh.paint_uniform_color(colour)
        coloured.append(o3_mesh)
        print(f"   Rank {rank+1}: {node_name} (prob {prob:.2f}) -> RGB{colour}")

    non_risk_count = 0
    for node_name, prob, o3_mesh in mesh_list:
        if prob is None:
            non_risk_count += 1
            o3_mesh.paint_uniform_color([0.2, 0.2, 0.2])
            coloured.append(o3_mesh)

    print(f"Added {non_risk_count} non‑risk structures (dark gray).")
    return coloured


# =============================================================
#  RAG + GROQ RISK ANALYSIS (from deployable.py)
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


def call_groq(prompt, api_key, model):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
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


def analyze_fracture_risk(fracture_list, embedder, index, documents, api_key, model, out_json):
    context = retrieve_context(fracture_list, embedder, index, documents)
    prompt = build_prompt(context, fracture_list)
    raw_response = call_groq(prompt, api_key, model)
    clean_json = extract_json(raw_response)
    result = json.loads(clean_json)
    result = validate_output(result)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    print(f"[✓] Risk JSON saved → {out_json}")
    return result


# =============================================================
#  MAIN PIPELINE (MERGED)
# =============================================================

def main():
    load_dotenv()   # optional, for GROQ_API_KEY

    # ------------------------------------------------------------------
    # PART 1: FRACTURE DETECTION AND SOLID MODEL GENERATION
    # ------------------------------------------------------------------
    print("=" * 60)
    print("PART 1: FRACTURE DETECTION AND SOLID MODEL GENERATION")
    print("=" * 60)

    print("[1/7] Loading and preprocessing 3D model...")
    mesh = load_and_preprocess_mesh(MODEL_3D_PATH)

    print("[2/7] Splitting mesh into ulna / radius...")
    mesh_ulna, mesh_radius = split_mesh(mesh)

    # (Optional) visualize split - Commented out to prevent hang
    # o3d.visualization.draw_geometries([mesh_ulna, mesh_radius], window_name="Ulna and Radius (split)")

    print("[3/7] Loading X-ray image for interactive landmark selection...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {IMAGE_PATH}")
    scale = 50
    w = int(img.shape[1] * scale / 100)
    h = int(img.shape[0] * scale / 100)
    resized_img = cv2.resize(img, (w, h))

    labels = ["ulna head", "ulna tail", "radius head", "radius tail"]
    working_img, px, Xray_landmark = get_landmarks_with_transform(resized_img, labels)
    print("Landmarks (centered):", Xray_landmark)

    print("[4/7] Running YOLO fracture detection...")
    model = YOLO(YOLO_MODEL_PATH)
    Xray_breaks, ulna_img, radius_img = get_fractures_with_crops(working_img, model, Xray_landmark)

    fracture_data = []

    ulna_mask   = get_connected_edge_image(ulna_img) if ulna_img is not None else None
    radius_mask = get_connected_edge_image(radius_img) if radius_img is not None else None

    # --- ULNA ---
    if (
        "ulna break" in Xray_breaks and
        "ulna head" in Xray_landmark and
        "ulna tail" in Xray_landmark
    ):
        ulna_info     = Xray_breaks["ulna break"]
        ulna_break_pt = ulna_info["center"]

        split_ratio_ulna = get_split_ratio(
            Xray_landmark["ulna head"],
            Xray_landmark["ulna tail"],
            ulna_break_pt
        )

        top_angle_ulna = angle_from_negative_x(
            Xray_landmark["ulna head"],
            ulna_break_pt
        )

        bottom_angle_ulna = angle_from_negative_x(
            ulna_break_pt,
            Xray_landmark["ulna tail"]
        )

        fractured_ulna = create_angle_mesh(
            mesh_ulna,
            angles=[top_angle_ulna, bottom_angle_ulna],
            split_ratio=split_ratio_ulna
        )

        solid_ulna = make_solid(fractured_ulna)
        solid_ulna.paint_uniform_color([0.6, 0.6, 0.6])

        ulna_patch = make_fracture_image_patch(
            mesh=mesh_ulna,
            split_ratio=split_ratio_ulna,
            fracture_size_px=ulna_info["size"],
            head_pt=Xray_landmark["ulna head"],
            tail_pt=Xray_landmark["ulna tail"],
            fracture_img=ulna_mask
        )

        fracture_data.append({
            "bone": "ulna",
            "damage": "crack",
            "location": round(float(split_ratio_ulna), 3),
            "top_angle": round(float(top_angle_ulna), 2),
            "bottom_angle": round(float(bottom_angle_ulna), 2)
        })
    else:
        solid_ulna = make_solid(mesh_ulna)
        solid_ulna.paint_uniform_color([0.6, 0.6, 0.6])
        ulna_patch = None

    # --- RADIUS ---
    if (
        "radius break" in Xray_breaks and
        "radius head" in Xray_landmark and
        "radius tail" in Xray_landmark
    ):
        radius_info     = Xray_breaks["radius break"]
        radius_break_pt = radius_info["center"]

        split_ratio_radius = get_split_ratio(
            Xray_landmark["radius head"],
            Xray_landmark["radius tail"],
            radius_break_pt
        )

        top_angle_radius = angle_from_negative_x(
            Xray_landmark["radius head"],
            radius_break_pt
        )

        bottom_angle_radius = angle_from_negative_x(
            radius_break_pt,
            Xray_landmark["radius tail"]
        )

        fractured_radius = create_angle_mesh(
            mesh_radius,
            angles=[top_angle_radius, bottom_angle_radius],
            split_ratio=split_ratio_radius
        )

        solid_radius = make_solid(fractured_radius)
        solid_radius.paint_uniform_color([0.6, 0.6, 0.6])

        radius_patch = make_fracture_image_patch(
            mesh=mesh_radius,
            split_ratio=split_ratio_radius,
            fracture_size_px=radius_info["size"],
            head_pt=Xray_landmark["radius head"],
            tail_pt=Xray_landmark["radius tail"],
            fracture_img=radius_mask
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
        solid_radius.paint_uniform_color([0.6, 0.6, 0.6])
        radius_patch = None

    # --- Visualize solid fractured bones with patches ---
    print("\n--- Displaying solid fractured bones with patches ---")
    temp_geoms = [solid_ulna, solid_radius]
    if ulna_patch:
        temp_geoms.append(ulna_patch)
    if radius_patch:
        temp_geoms.append(radius_patch)
    o3d.visualization.draw_geometries(temp_geoms, window_name="Solid Fractured Bones")

    # Save solid models
    if OUT_SOLID_ULNA:
        o3d.io.write_triangle_mesh(OUT_SOLID_ULNA, solid_ulna)
        print(f"[✓] Saved solid ulna → {OUT_SOLID_ULNA}")
    if OUT_SOLID_RADIUS:
        o3d.io.write_triangle_mesh(OUT_SOLID_RADIUS, solid_radius)
        print(f"[✓] Saved solid radius → {OUT_SOLID_RADIUS}")
    if OUT_SOLID_COMBINED:
        combined = solid_ulna + solid_radius
        o3d.io.write_triangle_mesh(OUT_SOLID_COMBINED, combined)
        print(f"[✓] Saved combined solid model → {OUT_SOLID_COMBINED}")

    # Save annotated image
    cv2.imwrite(OUT_IMAGE_PATCH, working_img)
    print(f"[✓] Annotated image saved → {OUT_IMAGE_PATCH}")

    # Print fracture report
    print("\n--- Fracture Report (JSON) ---")
    print(json.dumps(fracture_data, indent=4))

    # ------------------------------------------------------------------
    # PART 2: RISK ANALYSIS (LLM + RAG)
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PART 2: RISK ANALYSIS (LLM + RAG)")
    print("=" * 60)

    # Load API key (from env or creds.json)
    groq_api_key = None
    if os.path.exists("creds.json"):
        try:
            with open("creds.json", "r") as f:
                creds = json.load(f)
                groq_api_key = creds.get("api_key")
            if groq_api_key:
                print("[✓] Loaded Groq API key from creds.json")
        except Exception as e:
            print(f"[!] Error reading creds.json: {e}")

    if not groq_api_key:
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if groq_api_key:
            print("[✓] Loaded Groq API key from environment variable")

    if groq_api_key and fracture_data:
        try:
            embedder, index, documents = load_rag(FAISS_INDEX, DOCUMENTS_JSON)
            risk_result = analyze_fracture_risk(
                fracture_data,
                embedder,
                index,
                documents,
                groq_api_key,
                GROQ_MODEL,
                OUT_RISK_JSON
            )
            print("\n========== RISK ANALYSIS ==========")
            print(json.dumps(risk_result, indent=4))
            print("====================================")
        except Exception as e:
            print(f"❌ Risk analysis failed: {e}")
    else:
        print("⚠️  GROQ_API_KEY not set or no fracture data. Skipping risk analysis.")

    # ------------------------------------------------------------------
    # PART 3: SOFT TISSUE COLORING (using risk JSON)
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PART 3: SOFT TISSUE COLORING")
    print("=" * 60)

    if os.path.exists(OUT_RISK_JSON):
        risk_dict = load_risk_json(OUT_RISK_JSON)
        coloured_soft = color_soft_tissue_model(SOFT_TISSUE_MODEL_PATH, risk_dict)

        # Display colored soft tissues alone
        print("\n--- Displaying colored soft tissue model alone ---")
        o3d.visualization.draw_geometries(coloured_soft, window_name="Colored Soft Tissues")

        if OUT_SOFT_TISSUE_COLORED:
            combined_soft = o3d.geometry.TriangleMesh()
            for m in coloured_soft:
                combined_soft += m
            o3d.io.write_triangle_mesh(OUT_SOFT_TISSUE_COLORED, combined_soft)
            print(f"\n[✓] Saved colored soft tissue model → {OUT_SOFT_TISSUE_COLORED}")
    else:
        print(f"⚠️  Risk JSON not found at {OUT_RISK_JSON}. Skipping soft tissue coloring.")
        coloured_soft = []

    # ------------------------------------------------------------------
    # PART 4: COMBINED VISUALIZATION (Bones + Soft Tissues)
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PART 4: COMBINED VISUALIZATION (Bones + Soft Tissues)")
    print("=" * 60)

    combined_geometries = [solid_ulna, solid_radius]
    if ulna_patch is not None:
        combined_geometries.append(ulna_patch)
    if radius_patch is not None:
        combined_geometries.append(radius_patch)
    combined_geometries.extend(coloured_soft)

    print("\nOpening 3D viewer with fractured bones and colored soft tissues...")
    o3d.visualization.draw_geometries(
        combined_geometries,
        window_name="Fractured Bones + Colored Soft Tissues",
        width=1024, height=768
    )

    print("\n✅ Pipeline finished successfully.")


if __name__ == "__main__":
    main()