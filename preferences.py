"""Add-on preferences."""

import bpy
from bpy.props import IntProperty, EnumProperty, FloatProperty, StringProperty


class UDIMPowerToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    default_resolution: IntProperty(
        name="Default Export Resolution",
        default=4096,
        min=256,
        max=8192,
        description="Default resolution for wireframe exports"
    )

    default_format: EnumProperty(
        name="Default Export Format",
        items=[
            ('PNG', 'PNG', 'Raster wireframe'),
            ('SVG', 'SVG', 'Vector wireframe'),
        ],
        default='PNG'
    )

    default_margin: FloatProperty(
        name="Default UV Margin",
        default=0.002,
        min=0.0,
        max=0.1,
        precision=4,
        description="Default margin for UV operations"
    )

    texture_resolution: IntProperty(
        name="Assumed Texture Resolution",
        default=4096,
        min=256,
        max=8192,
        description="Texture resolution used for texel density calculations"
    )

    default_output_dir: StringProperty(
        name="Default Output Directory",
        default="//udim_exports/",
        subtype='DIR_PATH',
        description="Default directory for exports"
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="Export Defaults")
        box = layout.box()
        box.prop(self, "default_resolution")
        box.prop(self, "default_format")
        box.prop(self, "default_output_dir")

        layout.label(text="UV Defaults")
        box = layout.box()
        box.prop(self, "default_margin")
        box.prop(self, "texture_resolution")


def get_prefs():
    """Get add-on preferences, or None if not available."""
    addon = bpy.context.preferences.addons.get(__package__)
    if addon:
        return addon.preferences
    return None


classes = (
    UDIMPowerToolsPreferences,
)
