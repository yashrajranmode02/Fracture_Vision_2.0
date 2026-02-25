"""
3D fracture mesh generation: angle mesh, Poisson solidification, image patch.
"""
import math
import tempfile
import os
import numpy as np
import open3d as o3d
import cv2


# ── geometry helpers ──────────────────────────────────────────────────────────

def angle_from_negative_x(p1, p2, center=(0, 0)):
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
    total_height = y_top - y_bottom
    if total_height == 0:
        return 0.5
    return 1 - (y_top - y_split) / total_height


def get_bone_region_size_px(head_pt, tail_pt):
    return abs(tail_pt[0] - head_pt[0]), abs(tail_pt[1] - head_pt[1])


def get_patch_size_from_bone_region(head_pt, tail_pt, fracture_size_px, mesh):
    bone_w_px, bone_h_px = get_bone_region_size_px(head_pt, tail_pt)
    frac_w, frac_h = fracture_size_px
    if bone_w_px == 0 or bone_h_px == 0:
        return 0.01, 0.01
    bbox = mesh.get_axis_aligned_bounding_box()
    min_b, max_b = bbox.get_min_bound(), bbox.get_max_bound()
    mesh_w = max_b[0] - min_b[0]
    mesh_h = max_b[1] - min_b[1]
    return mesh_w * (frac_w / bone_w_px), mesh_h * (frac_h / bone_h_px)


# ── mesh operations ───────────────────────────────────────────────────────────

def create_angle_mesh(mesh, angles, split_ratio):
    vertices = np.asarray(mesh.vertices)
    min_y, max_y = vertices[:, 1].min(), vertices[:, 1].max()
    mid_y = min_y + (max_y - min_y) * split_ratio

    # Select indices for top and bottom parts
    indices = np.arange(len(vertices))
    top_indices = indices[vertices[:, 1] >= mid_y].tolist()
    bottom_indices = indices[vertices[:, 1] < mid_y].tolist()

    # Use select_by_index to preserve UVs, textures, and materials
    top_mesh = mesh.select_by_index(top_indices)
    bottom_mesh = mesh.select_by_index(bottom_indices)

    def rotate_mesh_part(part, angle_deg, center_y):
        if not part.has_vertices():
            return part
        
        angle_rad = np.radians(angle_deg)
        R = part.get_rotation_matrix_from_axis_angle([0, 0, angle_rad])
        
        # Calculate rotation center (mean X, mid Y, mean Z)
        part_vertices = np.asarray(part.vertices)
        center = [part_vertices[:, 0].mean(), center_y, part_vertices[:, 2].mean()]
        
        # Apply transformation
        part.rotate(R, center=center)
        return part

    top_rotated = rotate_mesh_part(top_mesh, angles[0], mid_y)
    bottom_rotated = rotate_mesh_part(bottom_mesh, angles[1], mid_y)

    return top_rotated + bottom_rotated


def make_solid(mesh, points=20000, depth=10):
    pcd = mesh.sample_points_poisson_disk(points)
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30)
    )
    pcd.orient_normals_consistent_tangent_plane(100)
    solid, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth
    )
    densities_np = np.asarray(densities)
    solid.remove_vertices_by_mask(densities_np < densities_np.mean() * 0.5)
    solid.remove_duplicated_vertices()
    solid.remove_degenerate_triangles()
    solid.remove_non_manifold_edges()
    solid.remove_unreferenced_vertices()
    solid.compute_vertex_normals()
    return solid


def make_fracture_image_patch(mesh, split_ratio, fracture_size_px,
                               head_pt, tail_pt, fracture_img,
                               texture_resolution=256):
    patch_w, patch_h = get_patch_size_from_bone_region(
        head_pt, tail_pt, fracture_size_px, mesh
    )
    bbox = mesh.get_axis_aligned_bounding_box()
    min_b, max_b = bbox.get_min_bound(), bbox.get_max_bound()
    y = min_b[1] + split_ratio * (max_b[1] - min_b[1])
    x = (min_b[0] + max_b[0]) / 2
    z = max_b[2] + 0.005  # Increased to prevent Z-fighting in web viewers
    hw, hh = patch_w / 2, patch_h / 2
    vertices = np.array([
        [x - hw, y - hh, z], [x + hw, y - hh, z],
        [x + hw, y + hh, z], [x - hw, y + hh, z],
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
    tex = cv2.resize(fracture_img, (texture_resolution, texture_resolution),
                     interpolation=cv2.INTER_LINEAR)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, tex)
    tmp.close()
    patch.textures = [o3d.io.read_image(tmp.name)]
    os.unlink(tmp.name)
    return patch
