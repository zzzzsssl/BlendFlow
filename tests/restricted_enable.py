import bpy, sys, pathlib, tempfile, addon_utils
from _bpy_restrict_state import RestrictBlend
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import blendflow
from blendflow import export_presets
with tempfile.TemporaryDirectory() as folder:
 export_presets.folder=lambda settings: folder
 with RestrictBlend():
  blendflow.register()
  assert blendflow.initialize_presets()==0.1
 blendflow.initialize_presets()
 with RestrictBlend():
  blendflow.unregister()
 errors=[]
 addon_utils.enable('blendflow', default_set=False, handle_error=lambda: errors.append(True))
 assert not errors
 assert addon_utils.check('blendflow')[1]
 blendflow.initialize_presets()
 addon_utils.disable('blendflow', default_set=False)
 assert not hasattr(bpy.types.WindowManager,'blendflow_export')
 assert not bpy.app.timers.is_registered(blendflow.initialize_presets)
print('RESTRICTED_ENABLE_PASS')

