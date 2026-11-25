import bpy, sys, pathlib, importlib, tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow import export_presets
with tempfile.TemporaryDirectory() as folder:
 export_presets.folder=lambda settings: folder
 blendflow.register()
 blendflow.register()
 importlib.reload(export_presets)
 export_presets.folder=lambda settings: folder
 importlib.reload(blendflow)
 blendflow.register()
 assert len([h for h in bpy.app.handlers.load_post if h.__module__=='blendflow'])==1
 blendflow.unregister()
 blendflow.unregister()
 assert not hasattr(bpy.types.WindowManager,'blendflow')
 bpy.utils.register_class(blendflow.BF_OT_preset)
 blendflow.register()
 blendflow.unregister()
 assert all(blendflow.registered_class(cls) is None for cls in blendflow.CLASSES)
print('LIFECYCLE_PASS')
