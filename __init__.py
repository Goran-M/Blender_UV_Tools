"""UDIM Power Tools - Professional UDIM workflow add-on for Blender."""

bl_info = {
    "name": "UDIM Power Tools",
    "author": "Leading Edge Simulations",
    "version": (1, 0, 1),
    "blender": (4, 2, 0),
    "location": "UV Editor > N-Panel > UDIM",
    "description": "Professional UDIM workflow tools: tile overview, wireframe export, heatmaps, texel density",
    "category": "UV",
}

import bpy
from . import preferences
from . import wireframe_export
from . import tile_overview


_modules = [
    preferences,
    wireframe_export,
    tile_overview,
]


def register():
    for mod in _modules:
        for cls in mod.classes:
            bpy.utils.register_class(cls)

    # Add wireframe export to UV menu
    bpy.types.IMAGE_MT_uvs.append(wireframe_export.menu_func)


def unregister():
    bpy.types.IMAGE_MT_uvs.remove(wireframe_export.menu_func)

    for mod in reversed(_modules):
        for cls in reversed(mod.classes):
            bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
