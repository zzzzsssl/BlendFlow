# BlendFlow

**Inspect assets. Create thumbnails. Export with checks. Explore render settings.**

BlendFlow is an open-source Blender Extension with four collapsible panels in the 3D Viewport sidebar. Current version: **0.6.3 (experimental)**. Licensed under **GPL-3.0-or-later**.

## 安装 / Installation

1. Download `blendflow-0.6.3.zip` from this repository's `dist/` folder.
2. In Blender Preferences → Get Extensions, choose **Install from Disk**, select the ZIP and enable BlendFlow.
3. Open the 3D Viewport sidebar with **N** → **BlendFlow**.

Use the extension ZIP, not GitHub's **Download ZIP** source archive. If an older version failed to register, save your work and restart Blender before reinstalling.

Manifest target: Blender **4.2+**. Development checks ran on Blender 5.1 and 5.3; this is not a promise of full compatibility with every release. Start with a copy of your project.

## 功能 / Features

| Panel | Capabilities |
| --- | --- |
| Smart Inspector | Read-only checks for unapplied scale, zero-vertex meshes and missing external images; category counts, object selection, explicit resolution actions |
| Smart Thumb Preview | Object / Collection thumbnails, automatic framing, transparent PNG, four camera presets, three studio lighting presets, exposure control |
| Export Guard | Object / Collection batching, GLB and FBX, preflight checks, isolated background export, filename conflict protection and JSON reports |
| Smart Render | Cycles sample/denoise comparison reports and 16:9, 1:1, 9:16 composition cameras with previews |

### Smart Inspector

Click **Scan Scene**, filter a category, then click an issue to select its object. **Select & Frame Object** also frames it. Object checks cover the current scene; image checks cover the whole blend file. Results are snapshots: rescan after edits.

- **Apply Scale**: individual or category batch; skips shared meshes, children, animation, constraints, shape keys and unavailable objects. Success requires scale to read back as `(1, 1, 1)`.
- **Empty Mesh**: Mesh objects with zero base vertices. Deletion skips modifiers, children and objects used in multiple scenes.
- **Missing Images**: relink one image or search a folder recursively by exact filename. Duplicate matches are skipped. Packed images are excluded; UDIM, sequences and movies are not checked.

Scanning does not change scene assets. Resolution actions are explicit; review confirmations before modifying objects.

### Smart Thumb Preview

Choose selected objects or a collection, output folder, resolution, **Camera Preset**, **Lighting** and **Exposure**. Cameras: Three Quarter, Front (-Y), Side (+X), Top (+Z). Lighting: Soft, Neutral, Contrast. Soft Studio with AgX and 0 EV is the default. Original materials are retained; emissive materials can need lower exposure.

Collection mode exports one thumbnail per immediate child collection, including descendants. If there are no children, it uses the collection itself. When children exist, directly linked objects in the root are not separate jobs. Temporary render data is cleaned up, and existing output files receive numbered alternatives.

### Export Guard

Choose a scope, platform, format and output folder. Run **Preflight Check**, review issues, then **Export Assets**. Exports rerun preflight against the current selection; reselect the intended batch after locating issues.

- Generic, Unity, Unreal Engine and Godot are editable starting configurations, not certified engine integrations.
- **Save Platform** overwrites the selected platform's user configuration; **Restore Defaults** removes its override. Switching platforms loads saved settings, so save edits first.
- Settings include FBX axes, scale, units and Smoothing (Normals Only / Face / Edge), GLB Y-up, materials, Animation, warning thresholds and filename prefix.
- Supported animation: independent Mesh object Actions. Rigs, parenting, modifiers, constraints, NLA, drivers and shape keys are currently blocked.
- Exports run in a separate Blender process using copied data. Existing files are never overwritten. Atomic publication uses a same-volume hard link; unsupported filesystems fail explicitly.
- Missing textures, unsupported dependencies and filename conflicts block a batch. Scale and material compatibility can be warnings. JSON reports record results and actual preset parameters.

Files written to disk are not removed by Blender Undo. Partial batch success retains completed files.

### Smart Render

**Render Optimizer** requires Cycles and an active camera. It compares **512 / 1024 / 2048 samples**, denoise off/on, against a **4096-sample** reference. Outputs include HTML/JSON reports, images, central detail crops and non-denoised difference maps. Denoised `denoise_1_difference_x4.png` files are not generated.

Recommendations use image error and single-run elapsed time. The reference still contains noise and timing includes warm-up effects; recommendations are a guide, not a perceptual quality guarantee. **Apply Recommendation** explicitly updates the scene settings.

**Smart Composition** uses selected geometry or a subject collection and the current camera direction. It creates separate 16:9 / 1:1 / 9:16 cameras and previews, with center/left/right/top/bottom placement and adjustable space. Generated cameras store resolution as custom properties; set the matching scene resolution when using them for final renders.

## Known limitations

- Experimental release; complex production scenes and target-engine imports require manual validation.
- Rendering is synchronous and can make the UI wait. Optimizer performs seven renders.
- Preview snapshots do not fully support collection/particle instances, unrealized Geometry Nodes instances or complex external-coordinate material dependencies.
- Test renders disable compositing, sequencer and render borders. Composition disables camera shift and depth of field in generated cameras.
- No incremental export, automatic LOD, rig retargeting, custom material baking or Asset Browser synchronization.
- Native UI colors follow the Blender theme.

## Development

```text
blendflow/          Extension source and blender_manifest.toml
  scanner.py       Read-only inspection
  actions.py       Explicit resolution actions
  preview.py       Thumbnail cameras and lighting
  export_guard.py  Preflight and background export
  export_presets.py Platform configuration persistence
  smart_render.py  Render comparison and composition
  ui.py            Sidebar panels
  __init__.py      Registration and lifecycle
 tests/            Blender integration scripts
 dist/             Installable release ZIP
```

Run scripts in a fresh background Blender, never in a production scene:

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py
blender --background --factory-startup --python-exit-code 1 --python tests/restricted_enable.py
blender --background --factory-startup --python-exit-code 1 --python tests/lifecycle.py
blender --background --factory-startup --python-exit-code 1 --python tests/export_guard.py
blender --command extension validate blendflow
blender --command extension build --source-dir blendflow --output-dir dist
```

See [TESTING.md](TESTING.md) for test coverage and remaining manual checks. Blender's bundled Python/numpy is used; no pip installation is required.

## Contributing

Bug reports and pull requests are welcome. Include Blender version, operating system, reproduction steps, expected/actual result and a minimal non-confidential sample when possible. Do not upload proprietary scenes or textures. Keep scanning read-only and add regression coverage for scene-changing behavior.

## License

[GNU GPL version 3 or later](LICENSE). Contributions are distributed under the same license.
