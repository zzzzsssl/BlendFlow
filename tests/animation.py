import bpy, sys, pathlib, tempfile, struct, json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from blendflow.export_guard import safe_export
from blendflow.export_presets import DEFAULT
obj=bpy.data.objects['Cube']
obj.keyframe_insert('location',frame=1)
obj.location.x=3
obj.keyframe_insert('location',frame=10)
bpy.context.scene.frame_end=10
bpy.context.scene.frame_set(1)
original=set(bpy.data.actions)
with tempfile.TemporaryDirectory() as folder:
 for fmt in ('GLB','FBX'):
  path=str(pathlib.Path(folder)/('animated.'+fmt.lower()))
  safe_export(bpy.context,[obj],path,fmt,dict(DEFAULT, animation=True, smoothing='FACE'))
  if fmt=='GLB':
   data=pathlib.Path(path).read_bytes()
   length=struct.unpack_from('<I',data,12)[0]
   doc=json.loads(data[20:20+length])
   assert doc.get('animations')
 assert set(bpy.data.actions)==original
print('ANIMATION_EXPORT_PASS')
