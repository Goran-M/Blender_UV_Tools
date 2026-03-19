# UDIM Power Tools

Professional UDIM workflow add-on for Blender 4.2+. Built for 3D artists working with UDIM tile sets for game assets, film props, and flight sim aircraft.

## Features

- **Tile Overview Panel** - Per-tile statistics, navigation, and face selection
- **Wireframe Export** - Batch export UV wireframe layouts per UDIM tile as PNG or SVG
- **Tile Occupancy Heatmap** - Color-coded UV space utilization overlay (coming soon)
- **Texel Density Checker** - Per-tile density analysis with mismatch warnings (coming soon)
- **Island Migration** - Move UV islands between tiles with one click (coming soon)
- **Tile Statistics Export** - Summary reports for documentation and QA (coming soon)

## Installation

1. Download the latest release `.zip`
2. In Blender: **Edit > Preferences > Add-ons > Install from Disk**
3. Select the `.zip` file
4. Enable **UDIM Power Tools** in the add-on list

## Requirements

- Blender 4.2 or later
- One or more mesh objects with UV maps

## Getting Started

All tools live in the UV Editor's side panel. Open the UV Editor, press **N** to show the side panel, and select the **UDIM** tab.

The add-on works with **multiple selected objects**. Select all the meshes you want to analyze or export, and the panel will combine their UV data automatically.

## Tile Overview Panel

The overview panel shows every occupied UDIM tile in a grid that matches your actual tile layout.

### What You See

Each tile displays:

| Stat | Meaning |
|------|---------|
| **Tile ID** | The UDIM number (1001, 1002, etc.). Click it to jump the UV editor to that tile. |
| **Faces** | Number of mesh faces whose UV centroid falls within this tile. |
| **Coverage** | Percentage of the tile's UV space occupied by geometry. 100% means every pixel has geometry behind it. Low values mean wasted texture space. |
| **px/u** | Texel density in pixels per world unit. This tells you how many texture pixels map to each unit of 3D surface area. Higher means more detail. |

Empty tile slots (tiles within the grid bounds that have no geometry) show as "empty" so you can see gaps in your layout.

### Summary Row

At the top of the grid, a summary shows the total tile count, total face count across all tiles, and total UV area usage.

### Density Mismatch Warning

If any two tiles differ in texel density by more than 2x, a warning appears at the bottom with the actual range and ratio. This catches the common problem where one tile has twice the detail of another, which causes visible seams or wasted resolution in the final texture.

### Refresh

The panel caches its calculations to stay fast. It recalculates automatically when you change your selection or switch UV layers. If you've edited UVs and need to force an update, click the refresh icon in the panel header.

### Select Faces

Each tile has a **Select** button that switches to edit mode and selects all faces belonging to that tile. Useful for isolating geometry by tile when you need to adjust UVs or check what's mapped where.

### Multi-Object Support

Select multiple mesh objects in the 3D viewport before opening the UV Editor. The panel combines UV data from all selected meshes, and face selection works across objects. This is how the add-on is designed to be used when your model is split across multiple objects sharing a UDIM tile set.

## Wireframe Export

Exports a UV wireframe image for each occupied UDIM tile. Available from the panel (under the collapsible **Wireframe Export** section) or from **UV Editor > UV > Export UDIM Wireframes**.

### How It Works

1. Select the mesh objects you want to export
2. Run the operator (panel button or UV menu)
3. Set your options in the dialog:
   - **Resolution** - Output image size in pixels (square). Default: 4096
   - **Output Directory** - Where to save. Default: `//udim_wireframes/` (relative to .blend file)
   - **Format** - PNG (raster) or SVG (vector)
4. Click OK

The exporter creates one file per occupied tile, named `uv_wireframe_1001.png`, `uv_wireframe_1002.png`, etc.

### What Happens Internally

The exporter merges all selected meshes into a temporary combined object (evaluated through the depsgraph, so modifiers are applied). For each tile, it shifts UVs into 0-1 space, exports the wireframe using Blender's built-in UV export, then shifts back. The temporary object is deleted when done. Your original objects are never modified.

### Use Cases

- Texture painting reference in external apps (Photoshop, Substance Painter)
- Documentation of UV layouts for team handoffs
- QA verification that islands are correctly placed per tile

## Add-on Preferences

**Edit > Preferences > Add-ons > UDIM Power Tools** lets you set defaults that carry across sessions:

| Setting | What It Does |
|---------|-------------|
| **Default Export Resolution** | Starting resolution for wireframe exports (256-8192) |
| **Default Export Format** | PNG or SVG |
| **Default Output Directory** | Where exports go by default |
| **Default UV Margin** | Margin value for UV operations (reserved for future features) |
| **Assumed Texture Resolution** | Resolution used for texel density calculations. Set this to match your actual texture size for accurate px/u readings. |

## License

GPL-3.0-or-later (required for Blender add-on distribution)

## Author

Leading Edge Simulations
