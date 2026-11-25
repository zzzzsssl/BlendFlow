import bpy, sys, pathlib, tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from blendflow.preview import render_preview
with tempfile.TemporaryDirectory() as folder:
 for view in ('THREE_QUARTER','FRONT','SIDE','TOP'):
  render_preview(bpy.context,[bpy.data.objects['Cube']],str(pathlib.Path(folder)/(view+'.png')),64,view,'NEUTRAL',-0.5)
 assert len(list(pathlib.Path(folder).glob('*.png')))==4
print('CAMERA_PRESETS_PASS')
