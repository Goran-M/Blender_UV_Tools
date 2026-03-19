"""Feature 1: Batch wireframe export per UDIM tile.

Supports multiple selected mesh objects. Merges all selected meshes into a
temporary combined bmesh, exports per-tile wireframes, then cleans up without
touching the originals.
"""

import bpy
import bmesh
import os
from bpy.props import IntProperty, StringProperty, EnumProperty
from .preferences import get_prefs


class UDIM_OT_export_wireframes(bpy.types.Operator):
    bl_idname = "uv.udim_export_wireframes"
    bl_label = "Export UDIM Wireframes"
    bl_description = "Export UV wireframe layout for each occupied UDIM tile"
    bl_options = {'REGISTER', 'UNDO'}

    resolution: IntProperty(
        name="Resolution",
        default=4096,
        min=256,
        max=8192,
        description="Output image resolution"
    )

    output_dir: StringProperty(
        name="Output Directory",
        default="//udim_wireframes/",
        subtype='DIR_PATH',
        description="Where to save the wireframe images"
    )

    export_format: EnumProperty(
        name="Format",
        items=[
            ('PNG', 'PNG', 'Raster wireframe'),
            ('SVG', 'SVG', 'Vector wireframe'),
        ],
        default='PNG'
    )

    def execute(self, context):
        # Gather all selected mesh objects
        mesh_objects = [o for o in context.selected_objects if o.type == 'MESH']

        if not mesh_objects:
            self.report({'ERROR'}, "Select at least one mesh object")
            return {'CANCELLED'}

        # Ensure object mode to read evaluated meshes
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Build a combined bmesh from all selected objects
        combined_bm = bmesh.new()
        combined_uv = combined_bm.loops.layers.uv.new("UVMap")

        depsgraph = context.evaluated_depsgraph_get()

        for obj in mesh_objects:
            eval_obj = obj.evaluated_get(depsgraph)
            temp_mesh = eval_obj.to_mesh()

            if not temp_mesh or not temp_mesh.uv_layers.active:
                eval_obj.to_mesh_clear()
                continue

            src_uv = temp_mesh.uv_layers.active
            vert_offset = len(combined_bm.verts)

            # Copy vertices in world space
            for v in temp_mesh.vertices:
                combined_bm.verts.new(obj.matrix_world @ v.co)
            combined_bm.verts.ensure_lookup_table()

            # Copy faces and UV data
            for poly in temp_mesh.polygons:
                try:
                    verts = [combined_bm.verts[vert_offset + i]
                             for i in poly.vertices]
                    face = combined_bm.faces.new(verts)
                    for j, loop in enumerate(face.loops):
                        src_loop_idx = poly.loop_start + j
                        loop[combined_uv].uv = (
                            src_uv.data[src_loop_idx].uv.copy()
                        )
                except ValueError:
                    pass  # skip duplicate faces

            eval_obj.to_mesh_clear()

        if not combined_bm.faces:
            combined_bm.free()
            self.report({'ERROR'}, "No UV data found on selected objects")
            return {'CANCELLED'}

        # Find occupied UDIM tiles
        tiles = set()
        for face in combined_bm.faces:
            for loop in face.loops:
                uv = loop[combined_uv].uv
                u_tile = int(uv.x)
                v_tile = int(uv.y)
                tile_id = 1001 + u_tile + (v_tile * 10)
                tiles.add(tile_id)

        if not tiles:
            combined_bm.free()
            self.report({'ERROR'}, "No UDIM tiles found")
            return {'CANCELLED'}

        # Create a temporary mesh and object from the combined data
        temp_mesh_data = bpy.data.meshes.new("_udim_export_temp")
        combined_bm.to_mesh(temp_mesh_data)

        temp_obj = bpy.data.objects.new("_udim_export_temp", temp_mesh_data)
        context.collection.objects.link(temp_obj)

        combined_bm.free()

        # Select only the temp object and enter edit mode
        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        output_path = bpy.path.abspath(self.output_dir)
        os.makedirs(output_path, exist_ok=True)

        ext = '.svg' if self.export_format == 'SVG' else '.png'

        for tile in sorted(tiles):
            u_offset = (tile - 1001) % 10
            v_offset = (tile - 1001) // 10

            # Shift into 0-1 space
            bm = bmesh.from_edit_mesh(temp_mesh_data)
            uv_layer = bm.loops.layers.uv.active
            for face in bm.faces:
                for loop in face.loops:
                    loop[uv_layer].uv.x -= u_offset
                    loop[uv_layer].uv.y -= v_offset
            bmesh.update_edit_mesh(temp_mesh_data)

            filepath = os.path.join(output_path, f"uv_wireframe_{tile}{ext}")

            bpy.ops.uv.export_layout(
                filepath=filepath,
                size=(self.resolution, self.resolution),
                opacity=0.0,
                mode=self.export_format
            )

            # Shift back
            bm = bmesh.from_edit_mesh(temp_mesh_data)
            uv_layer = bm.loops.layers.uv.active
            for face in bm.faces:
                for loop in face.loops:
                    loop[uv_layer].uv.x += u_offset
                    loop[uv_layer].uv.y += v_offset
            bmesh.update_edit_mesh(temp_mesh_data)

        # Clean up temp object and mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.delete()
        if temp_mesh_data.users == 0:
            bpy.data.meshes.remove(temp_mesh_data)

        # Restore original selection
        for o in mesh_objects:
            if o:
                o.select_set(True)
        context.view_layer.objects.active = mesh_objects[0]

        self.report({'INFO'},
                    f"Exported {len(tiles)} UDIM tiles to {output_path}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Pull defaults from preferences
        prefs = get_prefs()
        if prefs:
            self.resolution = prefs.default_resolution
            self.output_dir = prefs.default_output_dir
            self.export_format = prefs.default_format
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "resolution")
        layout.prop(self, "output_dir")
        layout.prop(self, "export_format")


def menu_func(self, context):
    self.layout.operator(UDIM_OT_export_wireframes.bl_idname)


classes = (
    UDIM_OT_export_wireframes,
)
