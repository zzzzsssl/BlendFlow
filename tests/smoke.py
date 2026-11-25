"""Run in a fresh background Blender, never in a production scene."""
import pathlib
import sys
import bpy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow.scanner import scan

blendflow.register()
scene = bpy.context.scene
mesh = bpy.data.meshes.new('BF_test_mesh')
obj = bpy.data.objects.new('BF_test', mesh)
scene.collection.objects.link(obj)
obj.scale = (2, 1, 1)
image = bpy.data.images.new('BF_missing', width=1, height=1)
image.source = 'FILE'
image.filepath = '//__blendflow_missing_test__.png'
before = (tuple(obj.scale), len(mesh.vertices), tuple(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
results = scan(scene)
assert any(r[1] == 'Unapplied scale' and r[2] == obj for r in results)
assert any(r[1] == 'Empty mesh' and r[2] == obj for r in results)
assert any(r[1] == 'Missing image: BF_missing' for r in results)
assert before == (tuple(obj.scale), len(mesh.vertices), tuple(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
assert bpy.ops.blendflow.scan() == {'FINISHED'}
state = bpy.context.window_manager.blendflow
for category in ('SCALE', 'EMPTY', 'IMAGE'):
    state.category = category
    assert state.index >= 0
    assert state.issues[state.index].category == category
state.category = 'ALL'
state.index = next(i for i, r in enumerate(state.issues) if r.target == obj)
assert bpy.ops.blendflow.locate() == {'FINISHED'}
assert bpy.context.view_layer.objects.active == obj
assert obj.select_get()
obj.select_set(False)
assert bpy.ops.blendflow.locate(issue_index=state.index, frame=False) == {'FINISHED'}
assert obj.select_get()
obj.hide_select = True
assert bpy.ops.blendflow.locate() == {'CANCELLED'}
assert 'Selection disabled' in state.locate_status
obj.hide_select = False
obj.hide_set(True)
assert bpy.ops.blendflow.locate() == {'CANCELLED'}
assert 'hidden' in state.locate_status
obj.hide_set(False)
bpy.data.objects.remove(obj, do_unlink=True)
assert state.issues[state.index].target is None
blendflow.unregister()
blendflow.register()
blendflow.unregister()
print('BLENDFLOW_SMOKE_PASS')
