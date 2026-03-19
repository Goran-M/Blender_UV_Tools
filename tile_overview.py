"""Feature 2: UDIM Tile Overview Panel.

Shows all occupied UDIM tiles in a grid layout with per-tile statistics:
face count, UV coverage percentage, and texel density. Click a tile to
jump the UV editor to that tile's coordinate range.

Works with multiple selected mesh objects, using evaluated depsgraph data.
"""

import bpy
import bmesh
from bpy.props import IntProperty
from .utils import gather_tile_data, tile_offsets, calc_texel_density
from .preferences import get_prefs


# ---- Cached tile data to avoid recomputing every draw ----

_tile_cache = {
    'key': None,
    'data': {},
}


def invalidate_cache():
    _tile_cache['key'] = None
    _tile_cache['data'] = {}


def _cache_key(context):
    """Build a cache key from selected objects and their mesh state."""
    objects = [o for o in context.selected_objects if o.type == 'MESH']
    if not objects and context.active_object and context.active_object.type == 'MESH':
        objects = [context.active_object]
    if not objects:
        return None
    # Key on object names, active UV layer names, and vertex counts
    parts = []
    for obj in sorted(objects, key=lambda o: o.name):
        mesh = obj.data
        uv_name = mesh.uv_layers.active.name if mesh.uv_layers.active else ""
        parts.append((obj.name, uv_name, len(mesh.vertices),
                       len(mesh.polygons)))
    return tuple(parts)


def get_cached_tile_data(context):
    """Return tile data, recomputing only when selection or mesh state changes."""
    key = _cache_key(context)
    if key is None:
        return {}

    if key != _tile_cache['key']:
        _tile_cache['key'] = key
        _tile_cache['data'] = gather_tile_data(context)

    return _tile_cache['data']


# ---- Operator: Jump to UDIM Tile ----

class UDIM_OT_jump_to_tile(bpy.types.Operator):
    bl_idname = "uv.udim_jump_to_tile"
    bl_label = "Jump to UDIM Tile"
    bl_description = "Center the UV editor on the selected UDIM tile"
    bl_options = {'INTERNAL'}

    tile_id: IntProperty()

    def execute(self, context):
        u_off, v_off = tile_offsets(self.tile_id)

        # Find the UV/Image editor space
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                for space in area.spaces:
                    if space.type == 'IMAGE_EDITOR':
                        space.cursor_location = (u_off + 0.5, v_off + 0.5)
                break

        # If we have a UDIM image, set the active tile
        if context.area and context.area.type == 'IMAGE_EDITOR':
            space = context.area.spaces.active
            if space.image and space.image.source == 'TILED':
                for tile in space.image.tiles:
                    if tile.number == self.tile_id:
                        space.image.tiles.active = tile
                        break

        return {'FINISHED'}


# ---- Operator: Refresh Tile Data ----

class UDIM_OT_refresh_tiles(bpy.types.Operator):
    bl_idname = "uv.udim_refresh_tiles"
    bl_label = "Refresh Tile Data"
    bl_description = "Force recalculation of UDIM tile statistics"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        invalidate_cache()
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.tag_redraw()
        self.report({'INFO'}, "Tile data refreshed")
        return {'FINISHED'}


# ---- Operator: Select Faces by Tile ----

class UDIM_OT_select_tile_faces(bpy.types.Operator):
    bl_idname = "uv.udim_select_tile_faces"
    bl_label = "Select Tile Faces"
    bl_description = "Select all faces belonging to this UDIM tile"
    bl_options = {'REGISTER', 'UNDO'}

    tile_id: IntProperty()

    def execute(self, context):
        tile_data = get_cached_tile_data(context)
        if self.tile_id not in tile_data:
            return {'CANCELLED'}

        face_map = tile_data[self.tile_id]['faces']  # {obj_name: set}

        for obj in context.selected_objects:
            if obj.type != 'MESH' or obj.name not in face_map:
                continue

            face_indices = face_map[obj.name]

            # Need to be in edit mode on this object to select faces
            context.view_layer.objects.active = obj
            if obj.mode != 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')

            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            for f in bm.faces:
                f.select = f.index in face_indices

            bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'}


# ---- Panel ----

class UDIM_PT_tile_overview(bpy.types.Panel):
    bl_label = "UDIM Tile Overview"
    bl_idname = "UDIM_PT_tile_overview"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "UDIM"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH'
                and obj.data.uv_layers.active is not None)

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # Header
        mesh_count = sum(1 for o in context.selected_objects
                         if o.type == 'MESH')
        row = layout.row(align=True)
        if mesh_count > 1:
            row.label(text=f"{mesh_count} objects", icon='MESH_DATA')
        else:
            row.label(text=obj.name, icon='MESH_DATA')
        row.label(text=f"UV: {obj.data.uv_layers.active.name}")
        row.operator("uv.udim_refresh_tiles", text="", icon='FILE_REFRESH')

        tile_data = get_cached_tile_data(context)

        if not tile_data:
            layout.label(text="No UDIM tiles found", icon='INFO')
            return

        prefs = get_prefs()
        tex_res = prefs.texture_resolution if prefs else 4096

        # Summary row
        total_faces = sum(t['face_count'] for t in tile_data.values())
        total_uv_area = sum(t['uv_area'] for t in tile_data.values())
        box = layout.box()
        row = box.row()
        row.label(text=f"Tiles: {len(tile_data)}")
        row.label(text=f"Faces: {total_faces}")
        row.label(text=f"Total UV: {total_uv_area:.1%}")

        # Determine grid bounds
        sorted_tiles = sorted(tile_data.keys())
        min_u = min((t - 1001) % 10 for t in sorted_tiles)
        max_u = max((t - 1001) % 10 for t in sorted_tiles)
        min_v = min((t - 1001) // 10 for t in sorted_tiles)
        max_v = max((t - 1001) // 10 for t in sorted_tiles)

        # Draw from top row to bottom (highest V first)
        for v in range(max_v, min_v - 1, -1):
            tile_row = layout.box()
            grid = tile_row.grid_flow(
                row_major=True,
                columns=max_u - min_u + 1,
                even_columns=True,
                even_rows=True,
                align=True,
            )

            for u in range(min_u, max_u + 1):
                tile_id = 1001 + u + (v * 10)
                col = grid.column(align=True)

                if tile_id in tile_data:
                    td = tile_data[tile_id]
                    coverage = td['uv_area']
                    density = calc_texel_density(
                        td['uv_area'], td['world_area'], tex_res
                    )

                    # Tile header: click to jump
                    op = col.operator(
                        "uv.udim_jump_to_tile",
                        text=str(tile_id),
                        icon='TEXTURE',
                    )
                    op.tile_id = tile_id

                    # Stats
                    col.label(text=f"{td['face_count']} faces")
                    col.label(text=f"{coverage:.1%} coverage")
                    if density > 0:
                        col.label(text=f"{density:.1f} px/u")

                    # Select faces button
                    op = col.operator(
                        "uv.udim_select_tile_faces",
                        text="Select",
                        icon='RESTRICT_SELECT_OFF',
                    )
                    op.tile_id = tile_id
                else:
                    col.label(text=str(tile_id))
                    col.label(text="empty")

        # Density mismatch warning
        densities = {}
        for tid, td in tile_data.items():
            d = calc_texel_density(td['uv_area'], td['world_area'], tex_res)
            if d > 0:
                densities[tid] = d

        if len(densities) >= 2:
            min_d = min(densities.values())
            max_d = max(densities.values())
            if min_d > 0 and (max_d / min_d) > 2.0:
                warn = layout.box()
                warn.label(
                    text="Texel density mismatch detected",
                    icon='ERROR',
                )
                warn.label(
                    text=f"Range: {min_d:.1f} - {max_d:.1f} px/unit "
                         f"({max_d / min_d:.1f}x ratio)"
                )


# ---- Wireframe Export Sub-panel ----

class UDIM_PT_wireframe_export(bpy.types.Panel):
    bl_label = "Wireframe Export"
    bl_idname = "UDIM_PT_wireframe_export"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "UDIM"
    bl_parent_id = "UDIM_PT_tile_overview"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator("uv.udim_export_wireframes", icon='EXPORT')


classes = (
    UDIM_OT_jump_to_tile,
    UDIM_OT_refresh_tiles,
    UDIM_OT_select_tile_faces,
    UDIM_PT_tile_overview,
    UDIM_PT_wireframe_export,
)
