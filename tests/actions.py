import sys, pathlib, bpy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
blendflow.register()
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.object
obj.scale=(2,3,4)
bpy.context.view_layer.update()
before=[obj.matrix_world @ v.co for v in obj.data.vertices]
bpy.ops.blendflow.scan()
assert bpy.ops.blendflow.fix(category='SCALE', batch=True)=={'FINISHED'}
assert tuple(obj.scale)==(1,1,1)
bpy.context.view_layer.update()
assert all((a-(obj.matrix_world @ v.co)).length < 1e-5 for a,v in zip(before,obj.data.vertices))
m=bpy.data.meshes.new('empty')
o=bpy.data.objects.new('empty',m)
bpy.context.scene.collection.objects.link(o)
bpy.ops.blendflow.scan()
bpy.ops.blendflow.fix(category='EMPTY',batch=True)
assert bpy.data.objects.get('empty') is None
blendflow.unregister()
print('ACTIONS_PASS')
