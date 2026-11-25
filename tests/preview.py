import bpy, sys, pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow.preview import render_preview
blendflow.register()
scene=bpy.context.scene
objects=set(bpy.data.objects)
meshes=set(bpy.data.meshes)
settings=(scene.render.engine,scene.render.filepath,scene.camera)
path=str(pathlib.Path(__file__).resolve().parents[2]/'preview-example.png')
render_preview(bpy.context,[bpy.data.objects['Cube']],path,256)
assert objects==set(bpy.data.objects)
assert meshes==set(bpy.data.meshes)
assert settings==(scene.render.engine,scene.render.filepath,scene.camera)
image=bpy.data.images.load(path)
assert tuple(image.size)==(256,256)
assert image.channels==4
assert image.pixels[3]==0
bpy.data.images.remove(image)
blendflow.unregister()
print('PREVIEW_PASS')
