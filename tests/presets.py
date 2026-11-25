import bpy, sys, pathlib, tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow import export_presets as presets
with tempfile.TemporaryDirectory() as folder:
 presets.folder=lambda settings: folder
 blendflow.register()
 s=bpy.context.window_manager.blendflow_export
 s.profile='UNITY'
 s.global_scale=2.5
 expected=presets.values(s)
 assert bpy.ops.blendflow.export_preset(action='SAVE')=={'FINISHED'}
 s.profile='GODOT'
 assert s.format=='GLB'
 s.profile='UNITY'
 assert presets.values(s)==expected
 s.global_scale=3
 bpy.ops.blendflow.export_preset(action='SAVE')
 blendflow.unregister()
 blendflow.register()
 s=bpy.context.window_manager.blendflow_export
 s.profile='UNITY'
 assert s.global_scale==3
 bpy.ops.blendflow.export_preset(action='BUILTIN')
 assert s.global_scale==1
 s.profile='GODOT'
 s.profile='UNITY'
 assert s.global_scale==1
 blendflow.unregister()
print('PLATFORM_OVERRIDE_PASS')
