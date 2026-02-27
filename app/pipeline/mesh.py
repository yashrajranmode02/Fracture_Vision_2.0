"""
Mesh loading, preprocessing, and splitting into ulna / radius.
Extracted from deployable.py for use as a backend pipeline module.
"""
import numpy as np
import open3d as o3d


def load_and_preprocess_mesh(path: str):
    import trimesh
    # Load as scene to preserve separate geometries
    scene = trimesh.load(path)
    
    # Filter for geometries that look like bones (high vertex count) 
    # and exclude small debris or vein-like structures (low vertex/face count)
    bone_meshes = []
    
    # Iterate through geometries in the scene
    for name, geometry in scene.geometry.items():
        # Bones typically have thousands of vertices. Veins/lines are usually much smaller.
        if len(geometry.vertices) > 2000:
            bone_meshes.append(geometry)
    
    if not bone_meshes:
        # Fallback: if filtering fails, take the largest mesh by vertex count
        all_geoms = list(scene.geometry.values())
        if all_geoms:
            bone_meshes = [max(all_geoms, key=lambda g: len(g.vertices))]
        else:
            # Last resort: open3d default load
            mesh = o3d.io.read_triangle_mesh(path)
            return mesh

    # Merge bone meshes
    merged_trimesh = trimesh.util.concatenate(bone_meshes)
    
    # Convert to Open3D
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(merged_trimesh.vertices)
    mesh.triangles = o3d.utility.Vector3iVector(merged_trimesh.faces)
    
    # Preprocess
    mesh.remove_duplicated_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()

    mesh.scale(
        1 / np.max(mesh.get_max_bound() - mesh.get_min_bound()),
        center=mesh.get_center()
    )
    mesh.translate(-mesh.get_center())
    mesh.compute_vertex_normals()

    R2 = mesh.get_rotation_matrix_from_axis_angle([0, -np.pi / 2, 0])
    mesh.rotate(R2, center=(0, 0, 0))
    return mesh 

def split_mesh(mesh):
    """Split the forearm mesh into ulna and radius using a tilted plane."""
    bbox = mesh.get_axis_aligned_bounding_box()
    min_bound = bbox.get_min_bound()
    max_bound = bbox.get_max_bound()
    size = max_bound - min_bound

    plane_height, plane_depth = size[1], size[2]
    plane_thickness = 0.001

    vertical_plane = o3d.geometry.TriangleMesh.create_box(
        width=plane_thickness, height=plane_height, depth=plane_depth
    )
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
