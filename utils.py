"""Shared UDIM utility functions."""

import bpy
import bmesh
import math
from mathutils import Vector


def get_udim_tile_id(u, v):
    """Convert UV coordinates to a UDIM tile ID (1001+).

    Uses floor so that UVs in [0,1) map to 1001, [1,2) to 1002, etc.
    """
    u_tile = int(math.floor(u))
    v_tile = int(math.floor(v))
    return 1001 + u_tile + (v_tile * 10)


def tile_offsets(tile_id):
    """Return (u_offset, v_offset) for a UDIM tile ID."""
    rel = tile_id - 1001
    return rel % 10, rel // 10


def gather_tile_data(context, objects=None):
    """Analyze mesh objects and return per-tile statistics.

    Works on multiple objects by evaluating through the depsgraph,
    matching the wireframe exporter's approach.

    Args:
        context: Blender context
        objects: list of mesh objects, or None for all selected meshes

    Returns a dict keyed by tile_id:
        {
            tile_id: {
                'face_count': int,
                'uv_area': float,       # total UV area in tile-local 0-1 space
                'world_area': float,     # total 3D face area in world units
                'faces': dict,           # {obj_name: set of face indices}
            }
        }
    """
    if objects is None:
        objects = [o for o in context.selected_objects if o.type == 'MESH']
        if not objects and context.active_object and context.active_object.type == 'MESH':
            objects = [context.active_object]

    if not objects:
        return {}

    depsgraph = context.evaluated_depsgraph_get()
    tiles = {}

    for obj in objects:
        eval_obj = obj.evaluated_get(depsgraph)
        temp_mesh = eval_obj.to_mesh()

        if not temp_mesh or not temp_mesh.uv_layers.active:
            eval_obj.to_mesh_clear()
            continue

        # Build bmesh from evaluated mesh for accurate area calculations
        bm = bmesh.new()
        bm.from_mesh(temp_mesh)
        bm.faces.ensure_lookup_table()
        bm.transform(obj.matrix_world)

        uv_lay = bm.loops.layers.uv.active
        if not uv_lay:
            bm.free()
            eval_obj.to_mesh_clear()
            continue

        for face in bm.faces:
            uvs = [loop[uv_lay].uv for loop in face.loops]
            if not uvs:
                continue

            # Use centroid of face UVs to determine tile
            centroid_u = sum(uv.x for uv in uvs) / len(uvs)
            centroid_v = sum(uv.y for uv in uvs) / len(uvs)
            tile_id = get_udim_tile_id(centroid_u, centroid_v)

            if tile_id not in tiles:
                tiles[tile_id] = {
                    'face_count': 0,
                    'uv_area': 0.0,
                    'world_area': 0.0,
                    'faces': {},
                }

            tiles[tile_id]['face_count'] += 1

            if obj.name not in tiles[tile_id]['faces']:
                tiles[tile_id]['faces'][obj.name] = set()
            tiles[tile_id]['faces'][obj.name].add(face.index)

            # UV area in tile-local 0-1 space
            u_off, v_off = tile_offsets(tile_id)
            local_uvs = [Vector((uv.x - u_off, uv.y - v_off)) for uv in uvs]
            tiles[tile_id]['uv_area'] += polygon_area_2d(local_uvs)

            # 3D world area (already transformed)
            tiles[tile_id]['world_area'] += face.calc_area()

        bm.free()
        eval_obj.to_mesh_clear()

    return tiles


def polygon_area_2d(verts):
    """Shoelace formula for 2D polygon area."""
    n = len(verts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += verts[i].x * verts[j].y
        area -= verts[j].x * verts[i].y
    return abs(area) / 2.0


def calc_texel_density(uv_area, world_area, texture_res):
    """Calculate texel density (pixels per world unit).

    Args:
        uv_area: UV space area (0-1 range, for one tile)
        world_area: 3D surface area in world units squared
        texture_res: texture resolution in pixels (assumes square)

    Returns:
        Texel density in pixels per world unit, or 0 if degenerate.
    """
    if world_area <= 0.0 or uv_area <= 0.0:
        return 0.0
    pixel_area = uv_area * (texture_res * texture_res)
    return math.sqrt(pixel_area / world_area)
