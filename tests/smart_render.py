import bpy, sys, pathlib, tempfile, json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow.smart_render import optimize, compose
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
blendflow.register()
scene=bpy.context.scene
scene.render.engine='CYCLES'
s=bpy.context.window_manager.blendflow_render
s.size=64
before=(scene.camera,scene.cycles.samples,scene.render.resolution_x,scene.render.resolution_y,scene.render.filepath)
with tempfile.TemporaryDirectory() as folder:
 s.directory=folder
 optimize(bpy.context,s)
 report=json.loads((pathlib.Path(s.last_output)/'comparison.json').read_text())
 assert len(report['comparisons'])==6
 assert report['reference_samples']==4096
 assert not list(pathlib.Path(s.last_output).glob('*denoise_1_difference_x4.png'))
 assert len(list(pathlib.Path(s.last_output).glob('*denoise_0_difference_x4.png')))==3
 assert 'denoise_1_difference_x4.png' not in (pathlib.Path(s.last_output)/'comparison.html').read_text()
 assert s.recommended_samples in (512,1024,2048)
 s.position='LEFT'
 compose(bpy.context,s)
 cameras=[o for o in scene.objects if o.name.startswith('BF Composition')]
 assert len(cameras)==3
 for camera in cameras:
  temp=scene.copy()
  temp.render.resolution_x=camera['blendflow_resolution_x']
  temp.render.resolution_y=camera['blendflow_resolution_y']
  for corner in bpy.data.objects['Cube'].bound_box:
   p=world_to_camera_view(temp,camera,bpy.data.objects['Cube'].matrix_world @ Vector(corner))
   assert -0.01<=p.x<=1.01 and -0.01<=p.y<=1.01, (camera.name,tuple(p))
  bpy.data.scenes.remove(temp)
 assert before==(scene.camera,scene.cycles.samples,scene.render.resolution_x,scene.render.resolution_y,scene.render.filepath)
blendflow.unregister()
print('SMART_RENDER_PASS')
