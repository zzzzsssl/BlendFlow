import bpy, sys, pathlib, tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow.export_guard import safe_export, check
blendflow.register()
obj=bpy.data.objects['Cube']
obj.scale=(2,1,1)
bpy.context.view_layer.update()
before=(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.data.materials),obj.matrix_world.copy(),bpy.context.scene,bpy.context.view_layer.objects.active)
with tempfile.TemporaryDirectory() as folder:
 for fmt in ('GLB','FBX'):
  path=str(pathlib.Path(folder)/('cube.'+fmt.lower()))
  safe_export(bpy.context,[obj],path,fmt)
  assert pathlib.Path(path).stat().st_size>20
  try: safe_export(bpy.context,[obj],path,fmt)
  except FileExistsError: pass
  else: raise AssertionError('overwrite allowed')
assert before==(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.data.materials),obj.matrix_world.copy(),bpy.context.scene,bpy.context.view_layer.objects.active)
obj.modifiers.new('Test','BEVEL')
assert any(r[0]=='ERROR' for r in check([obj]))
blendflow.unregister()
print('EXPORT_GUARD_PASS')
