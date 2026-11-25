import json
import os
import re
import tempfile
import bpy

FIELDS = ('smoothing', 'animation', 'format', 'axis_forward', 'axis_up', 'global_scale', 'apply_unit_scale', 'gltf_yup', 'export_materials', 'polygon_limit', 'warn_scale', 'prefix')
DEFAULT = dict(smoothing='OFF', animation=False, format='GLB', axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True, gltf_yup=True, export_materials=True, polygon_limit=100000, warn_scale=True, prefix='')
BUILTINS = {'GENERIC': DEFAULT, 'UNITY': dict(DEFAULT, format='FBX'), 'UNREAL': dict(DEFAULT, format='FBX', axis_forward='-Y', axis_up='Z'), 'GODOT': dict(DEFAULT)}


def values(settings):
    return {key: getattr(settings, key) for key in FIELDS}


def folder(settings):
    return os.path.join(bpy.utils.user_resource('CONFIG'), 'presets', 'blendflow', 'platforms')


def path_for(settings):
    return os.path.join(folder(settings), settings.profile.lower() + '.json')


def load_platform(settings, context=None):
    try:
        path = path_for(settings)
        data = BUILTINS[settings.profile]
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                payload = json.load(handle)
            if payload.get('schema') != 1:
                raise ValueError('Unsupported preset version')
            data = dict(DEFAULT, **payload['settings'])
        validate(data)
        for key, value in data.items():
            setattr(settings, key, value)
        settings.status = 'Platform loaded: ' + settings.profile
    except (OSError, ValueError, KeyError, TypeError) as exc:
        for key, value in BUILTINS[settings.profile].items():
            setattr(settings, key, value)
        settings.status = 'Defaults loaded; saved preset unreadable: ' + str(exc)


def validate(data):
    if data.get('smoothing') not in {'OFF','FACE','EDGE'} or type(data.get('animation')) is not bool:
        raise ValueError('Invalid smoothing or animation')
    if set(data) != set(FIELDS):
        raise ValueError('Invalid preset fields')
    if data['format'] not in {'GLB','FBX'} or data['axis_forward'] not in {'X','Y','Z','-X','-Y','-Z'} or data['axis_up'] not in {'X','Y','Z','-X','-Y','-Z'}:
        raise ValueError('Invalid format or axes')
    if data['axis_forward'][-1] == data['axis_up'][-1]:
        raise ValueError('Forward and up axes must differ')
    if type(data['global_scale']) not in (float,int) or not 0.001 <= data['global_scale'] <= 1000:
        raise ValueError('Invalid scale')
    if type(data['polygon_limit']) is not int or not 1 <= data['polygon_limit'] <= 10000000:
        raise ValueError('Invalid polygon limit')
    for key in ('apply_unit_scale','gltf_yup','export_materials','warn_scale'):
        if type(data[key]) is not bool:
            raise ValueError('Invalid boolean')
    if not isinstance(data['prefix'], str):
        raise ValueError('Invalid prefix')


class BF_OT_preset(bpy.types.Operator):
    bl_idname = 'blendflow.export_preset'
    bl_label = 'Export Preset'
    action: bpy.props.EnumProperty(items=(('BUILTIN','Load Platform Defaults',''),('SAVE','Save Preset',''),('LOAD','Load Preset','')))

    def invoke(self, context, event):
        if self.action in {'SAVE', 'BUILTIN'}:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        settings = context.window_manager.blendflow_export
        try:
            if self.action == 'BUILTIN':
                data = BUILTINS[settings.profile]
                path = path_for(settings)
                if os.path.exists(path):
                    os.unlink(path)
            elif self.action == 'LOAD':
                load_platform(settings, context)
                return {'FINISHED'}
            else:
                data = values(settings)
                validate(data)
                path = path_for(settings)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                        json.dump({'schema':1, 'settings':data}, handle, indent=2)
                    os.replace(temporary, path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
                settings.status = 'Platform preset saved: ' + settings.profile
                return {'FINISHED'}
            validate(data)
            for key, value in data.items():
                setattr(settings, key, value)
            settings.status = 'Preset loaded; parameters are editable'
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}
