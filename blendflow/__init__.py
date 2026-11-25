import bpy
from bpy.app.handlers import persistent
from .properties import BF_Issue, BF_State
from .operators import BF_OT_scan, BF_OT_locate
from .actions import BF_OT_fix, BF_OT_relink
from .ui import BF_UL_issues, BF_PT_inspector, BF_PT_smart_preview, BF_PT_export_guard
from .export_presets import BF_OT_preset, load_platform

from .preview import BF_PreviewSettings, BF_OT_preview

from .export_guard import BF_ExportIssue, BF_ExportSettings, BF_OT_export, BF_OT_export_locate, BF_UL_export

from .smart_render import BF_RenderSettings, BF_OT_smart_render, BF_PT_smart_render

CLASSES = (BF_RenderSettings, BF_OT_smart_render, BF_PT_smart_render, BF_OT_preset, BF_ExportIssue, BF_ExportSettings, BF_OT_export, BF_OT_export_locate, BF_UL_export, BF_PreviewSettings, BF_OT_preview, BF_Issue, BF_State, BF_OT_scan, BF_OT_locate, BF_UL_issues, BF_PT_inspector, BF_PT_smart_preview, BF_PT_export_guard, BF_OT_fix, BF_OT_relink)

_pending_timers = globals().get('_pending_timers', [])


def initialize_presets():
    if not hasattr(bpy.types.WindowManager, 'blendflow_export'):
        return None
    managers = getattr(bpy.data, 'window_managers', None)
    if managers is None:
        return 0.1
    for wm in managers:
        load_platform(wm.blendflow_export)
    return None


@persistent
def clear_results(_):
    for wm in bpy.data.window_managers:
        wm.blendflow.issues.clear()
        wm.blendflow.status = 'Not scanned'
        wm.blendflow.scene = None
        load_platform(wm.blendflow_export)


def registered_class(cls):
    # Operators are not reliably exposed as bpy.types.<Python class name>.
    for base in cls.__bases__:
        lookup = getattr(base, 'bl_rna_get_subclass_py', None)
        if lookup:
            found = lookup(cls.__name__, None)
            if not found and issubclass(cls, bpy.types.Operator):
                namespace, name = cls.bl_idname.split('.', 1)
                found = lookup(namespace.upper() + '_OT_' + name, None)
            if found:
                return found
    return None


def cleanup():
    for callback in _pending_timers:
        if bpy.app.timers.is_registered(callback):
            bpy.app.timers.unregister(callback)
    _pending_timers.clear()
    for handler in list(bpy.app.handlers.load_post):
        if getattr(handler, '__module__', '') == __name__ and getattr(handler, '__name__', '') == 'clear_results':
            bpy.app.handlers.load_post.remove(handler)
    for name in ('blendflow_render', 'blendflow_export', 'blendflow_preview', 'blendflow'):
        if hasattr(bpy.types.WindowManager, name):
            delattr(bpy.types.WindowManager, name)
    for cls in reversed(CLASSES):
        old = registered_class(cls)
        if old and old.__module__.rsplit('.', 1)[0] == __package__:
            bpy.utils.unregister_class(old)


def register():
    cleanup()
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
        bpy.types.WindowManager.blendflow = bpy.props.PointerProperty(type=BF_State, options={'SKIP_SAVE'})
        bpy.types.WindowManager.blendflow_preview = bpy.props.PointerProperty(type=BF_PreviewSettings)
        bpy.types.WindowManager.blendflow_export = bpy.props.PointerProperty(type=BF_ExportSettings)
        bpy.types.WindowManager.blendflow_render = bpy.props.PointerProperty(type=BF_RenderSettings)
        bpy.app.handlers.load_post.append(clear_results)
        _pending_timers.append(initialize_presets)
        bpy.app.timers.register(initialize_presets, first_interval=0.1)
    except Exception:
        cleanup()
        raise


def unregister():
    cleanup()
