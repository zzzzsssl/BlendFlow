"""Static mesh export with preflight, isolated data and staged commits."""
import json
import os
import re
import tempfile
import uuid
import subprocess
import bpy
from .export_presets import values, DEFAULT, validate, load_platform


def jobs_for(context, settings):
    if settings.scope == 'OBJECT':
        return [(o.name, [o]) for o in context.selected_objects]
    if settings.collection:
        root = settings.collection
        return [(c.name, list(c.all_objects)) for c in (list(root.children) or [root])]
    return []


def check(objects, options=None):
    options = options or DEFAULT
    rows = []
    def add(level, obj, message):
        rows.append((level, obj, message))
    for obj in objects:
        if obj.type != 'MESH':
            add('ERROR', obj, 'Only static Mesh supported; non-mesh or instance dependency')
            continue
        if obj.modifiers or obj.constraints or obj.data.shape_keys or obj.parent:
            add('ERROR', obj, 'Modifiers, constraints, animation, shape keys or parenting unsupported')
        if obj.animation_data and (obj.animation_data.drivers or obj.animation_data.nla_tracks):
            add('ERROR', obj, 'Drivers and NLA tracks unsupported')
        if not obj.data.polygons:
            add('ERROR', obj, 'Mesh has no faces')
        if options['warn_scale'] and any(abs(v-1) > 1e-5 for v in obj.scale):
            add('WARNING', obj, 'Unapplied scale; transform will be preserved')
        if len(obj.data.polygons) > options['polygon_limit']:
            add('WARNING', obj, 'Polygon count exceeds preset threshold')
        if not obj.material_slots:
            add('WARNING', obj, 'No material assigned')
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP':
                    add('ERROR', obj, 'Node groups require baking before static export')
                if node.type == 'TEX_IMAGE' and node.image:
                    image = node.image
                    if image.source != 'FILE':
                        add('ERROR', obj, 'Non-file image requires baking')
                    elif not image.packed_file and not os.path.isfile(bpy.path.abspath(image.filepath, library=image.library)):
                        add('ERROR', obj, 'Missing texture: ' + image.name)
            add('WARNING', obj, 'Material conversion is exporter-dependent; verify target appearance')
    return rows


def safe_export(context, sources, destination, fmt, options=None):
    options = dict(options or DEFAULT, format=fmt)
    validate(options)
    if any(level == 'ERROR' for level, _, _ in check(sources, options)):
        raise ValueError('Preflight blocked this asset')
    if not sources:
        raise ValueError('Empty asset')
    if os.path.exists(destination):
        raise FileExistsError(destination)
    scene = bpy.data.scenes.new('BF Export Temporary')
    scene.unit_settings.system = context.scene.unit_settings.system
    scene.unit_settings.scale_length = context.scene.unit_settings.scale_length
    window = context.window
    original_scene = window.scene if window else None
    objects, meshes, materials = [], [], []
    actions = []
    scene.frame_start = context.scene.frame_start
    scene.frame_end = context.scene.frame_end
    scene.render.fps = context.scene.render.fps
    scene.render.fps_base = context.scene.render.fps_base
    scene.frame_set(context.scene.frame_current)
    try:
        for source in sources:
            mesh = source.data.copy()
            meshes.append(mesh)
            obj = bpy.data.objects.new(source.name, mesh)
            objects.append(obj)
            scene.collection.objects.link(obj)
            obj.matrix_world = source.matrix_world.copy()
            if options['animation'] and source.animation_data and source.animation_data.action:
                obj.rotation_mode = source.rotation_mode
                obj.location = source.location
                obj.rotation_euler = source.rotation_euler
                obj.rotation_quaternion = source.rotation_quaternion
                obj.rotation_axis_angle = source.rotation_axis_angle
                obj.scale = source.scale
                obj.animation_data_create()
                action = source.animation_data.action.copy()
                actions.append(action)
                obj.animation_data.action = action
                if hasattr(source.animation_data, 'action_slot'):
                    slot = source.animation_data.action_slot
                    if slot:
                        obj.animation_data.action_slot = next((s for s in action.slots if s.identifier == slot.identifier), None)

            mesh.materials.clear()
            for slot in source.material_slots:
                if slot.material:
                    mat = slot.material.copy()
                    materials.append(mat)
                    mesh.materials.append(mat)
                else:
                    mesh.materials.append(None)
        layer = scene.view_layers[0]
        layer.update()
        for obj in objects:
            obj.select_set(True, view_layer=layer)
        layer.objects.active = objects[0]
        with tempfile.TemporaryDirectory(prefix='.blendflow-', dir=os.path.dirname(destination)) as folder:
            staged = os.path.join(folder, 'asset.' + fmt.lower())
            snapshot = os.path.join(folder, 'snapshot.blend')
            bpy.data.libraries.write(snapshot, {scene}, path_remap='ABSOLUTE')
            worker = os.path.join(folder, 'export_worker.py')
            code = "import bpy\nbpy.context.window.scene = bpy.data.scenes[%r]\n" % scene.name
            if fmt == 'GLB':
                kwargs = dict(filepath=staged, export_format='GLB', use_selection=False, export_animations=options['animation'], export_cameras=False, export_lights=False, export_yup=options['gltf_yup'], export_materials='EXPORT' if options['export_materials'] else 'NONE')
                code += 'bpy.ops.export_scene.gltf(**%r)\n' % kwargs
            else:
                if not options['export_materials']:
                    code += "for obj in bpy.context.scene.objects:\n    if obj.type == 'MESH': obj.data.materials.clear()\n"
                kwargs = dict(filepath=staged, use_selection=False, object_types={'MESH'}, bake_anim=options['animation'], bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, mesh_smooth_type=options['smoothing'], use_mesh_modifiers=False, path_mode='COPY', embed_textures=True, axis_forward=options['axis_forward'], axis_up=options['axis_up'], global_scale=options['global_scale'], apply_unit_scale=options['apply_unit_scale'])
                code += 'bpy.ops.export_scene.fbx(**%r)\n' % kwargs
            with open(worker, 'w', encoding='utf-8') as handle:
                handle.write(code)
            run = subprocess.run([bpy.app.binary_path, '--background', snapshot, '--python-exit-code', '1', '--python', worker], capture_output=True, text=True, timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if run.returncode:
                raise RuntimeError('Background exporter failed: ' + (run.stderr or run.stdout)[-500:])
            result = {'FINISHED'}
            if result != {'FINISHED'} or not os.path.isfile(staged) or os.path.getsize(staged) < 20:
                raise RuntimeError('Exporter did not produce a valid file')
            with open(staged, 'rb') as handle:
                magic = handle.read(23)
            if (fmt == 'GLB' and magic[:4] != b'glTF') or (fmt == 'FBX' and not magic.startswith(b'Kaydara FBX Binary')):
                raise RuntimeError('Unexpected export file header')
            # Same-volume hard link publishes a complete file without overwriting races.
            os.link(staged, destination)
    finally:
        if window:
            window.scene = original_scene
        bpy.data.scenes.remove(scene)
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            bpy.data.meshes.remove(mesh)
        for action in actions:
            bpy.data.actions.remove(action)
        for mat in materials:
            bpy.data.materials.remove(mat)


class BF_ExportIssue(bpy.types.PropertyGroup):
    severity: bpy.props.StringProperty()
    message: bpy.props.StringProperty()
    target: bpy.props.PointerProperty(type=bpy.types.Object)


class BF_ExportSettings(bpy.types.PropertyGroup):
    smoothing: bpy.props.EnumProperty(name='Smoothing', items=(('OFF','Normals Only','Export normals only'),('FACE','Face','Export face smoothing'),('EDGE','Edge','Export edge smoothing')), default='OFF')
    animation: bpy.props.BoolProperty(name='Animation', default=False)

    profile: bpy.props.EnumProperty(name='Target Platform', items=(('GENERIC','Generic / Default',''),('UNITY','Unity','Starting configuration'),('UNREAL','Unreal Engine','Starting configuration'),('GODOT','Godot','Starting configuration')), update=load_platform)
    axis_forward: bpy.props.EnumProperty(name='Forward', items=[(x,x,'') for x in ('X','Y','Z','-X','-Y','-Z')], default='-Z')
    axis_up: bpy.props.EnumProperty(name='Up', items=[(x,x,'') for x in ('X','Y','Z','-X','-Y','-Z')], default='Y')
    global_scale: bpy.props.FloatProperty(name='FBX Scale', default=1, min=0.001, max=1000)
    apply_unit_scale: bpy.props.BoolProperty(name='Apply Scene Units', default=True)
    gltf_yup: bpy.props.BoolProperty(name='glTF Y Up', default=True)
    export_materials: bpy.props.BoolProperty(name='Export Materials', default=True)
    polygon_limit: bpy.props.IntProperty(name='Polygon Warning Limit', default=100000, min=1, max=10000000)
    warn_scale: bpy.props.BoolProperty(name='Warn Unapplied Scale', default=True)

    scope: bpy.props.EnumProperty(name='Scope', items=(('OBJECT','Selected Objects','One file per selected object'),('COLLECTION','Collection Children','One file per child collection')))
    collection: bpy.props.PointerProperty(name='Collection', type=bpy.types.Collection)
    format: bpy.props.EnumProperty(name='Recipe', items=(('GLB','Generic GLB','Static mesh, glTF Y-up'),('FBX','Generic FBX','Static mesh, -Z forward / Y up')))
    directory: bpy.props.StringProperty(name='Output Folder', subtype='DIR_PATH')
    prefix: bpy.props.StringProperty(name='Filename Prefix')
    issues: bpy.props.CollectionProperty(type=BF_ExportIssue)
    index: bpy.props.IntProperty()
    status: bpy.props.StringProperty(default='Ready for preflight')


def preflight(context):
    settings = context.window_manager.blendflow_export
    settings.issues.clear()
    jobs = jobs_for(context, settings)
    paths = set()
    for name, objects in jobs:
        rows = check(objects, values(settings))
        if not objects:
            rows.append(('ERROR', None, 'Empty collection: ' + name))
        stem = re.sub(r'[^a-zA-Z0-9_-]', '_', settings.prefix + name)[:100] or 'Asset'
        path = os.path.join(bpy.path.abspath(settings.directory), 'asset_' + stem + '.' + settings.format.lower())
        if path.casefold() in paths or os.path.exists(path):
            rows.append(('ERROR', None, 'Filename conflict: ' + path))
        paths.add(path.casefold())
        for level, obj, message in rows:
            row = settings.issues.add()
            row.severity, row.target, row.message = level, obj, name + ': ' + message
    if not jobs:
        row = settings.issues.add()
        row.severity, row.message = 'ERROR', 'No assets in scope'
    settings.status = f'{len(jobs)} assets | {sum(r.severity == "ERROR" for r in settings.issues)} errors | {sum(r.severity == "WARNING" for r in settings.issues)} warnings'
    return jobs


class BF_OT_export(bpy.types.Operator):
    bl_idname = 'blendflow.export_guard'
    bl_label = 'Export Guard'
    execute_export: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def invoke(self, context, event):
        preflight(context)
        if self.execute_export:
            return context.window_manager.invoke_props_dialog(self, width=450)
        return {'FINISHED'}

    def draw(self, context):
        self.layout.label(text=context.window_manager.blendflow_export.status)
        self.layout.label(text='Warnings accepted on confirmation; errors block all exports.')
        self.layout.label(text='Existing files are never overwritten. JSON report included.')

    def execute(self, context):
        settings = context.window_manager.blendflow_export
        jobs = preflight(context)
        if not self.execute_export:
            return {'FINISHED'}
        if not settings.directory:
            self.report({'WARNING'}, 'Choose output folder')
            return {'CANCELLED'}
        folder = bpy.path.abspath(settings.directory)
        report = {'preset': values(settings), 'format': settings.format, 'issues': [{'severity': r.severity, 'message': r.message} for r in settings.issues], 'assets': []}
        try:
            os.makedirs(folder, exist_ok=True)
            blocked = any(r.severity == 'ERROR' for r in settings.issues)
            if not blocked:
                for name, objects in jobs:
                    stem = re.sub(r'[^a-zA-Z0-9_-]', '_', settings.prefix + name)[:100] or 'Asset'
                    path = os.path.join(folder, 'asset_' + stem + '.' + settings.format.lower())
                    try:
                        safe_export(context, objects, path, settings.format, values(settings))
                        report['assets'].append({'asset': name, 'path': path, 'status': 'exported'})
                    except Exception as exc:
                        report['assets'].append({'asset': name, 'status': 'failed', 'error': str(exc)})
            report['blocked'] = blocked
            report_path = os.path.join(folder, 'blendflow_report_' + uuid.uuid4().hex[:12] + '.json')
            with open(report_path, 'x', encoding='utf-8') as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
            settings.status = ('Blocked by preflight' if blocked else f'{sum(a["status"] == "exported" for a in report["assets"])} exported; {sum(a["status"] == "failed" for a in report["assets"])} failed') + ' | JSON report saved'
        except OSError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, settings.status)
        return {'FINISHED'}


class BF_OT_export_locate(bpy.types.Operator):
    bl_idname = 'blendflow.export_locate'
    bl_label = 'Select Issue Object'
    index: bpy.props.IntProperty()
    def execute(self, context):
        settings = context.window_manager.blendflow_export
        if not 0 <= self.index < len(settings.issues):
            return {'CANCELLED'}
        obj = settings.issues[self.index].target
        if context.mode != 'OBJECT' or not obj or obj not in context.selectable_objects:
            self.report({'WARNING'}, 'Object unavailable, hidden or locked')
            return {'CANCELLED'}
        for selected in context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {'FINISHED'}


class BF_UL_export(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        op = layout.operator('blendflow.export_locate', text=item.message, icon='ERROR' if item.severity == 'ERROR' else 'INFO', emboss=False)
        op.index = index


def draw_export(layout, context):
    from .ui import note
    settings = context.window_manager.blendflow_export
    card = layout.box()
    card.label(text='Export Guard', icon='EXPORT')
    card.prop(settings, 'scope')
    if settings.scope == 'COLLECTION':
        card.prop(settings, 'collection')
    card.prop(settings, 'profile')
    row = card.row(align=True)
    row.operator('blendflow.export_preset', text='Save Platform').action = 'SAVE'
    row.operator('blendflow.export_preset', text='Restore Defaults').action = 'BUILTIN'
    note(card, 'Platform defaults are editable starting points; verify in your engine.')
    card.prop(settings, 'format')
    if settings.format == 'FBX':
        card.prop(settings, 'smoothing')
        card.prop(settings, 'axis_forward')
        card.prop(settings, 'axis_up')
        card.prop(settings, 'global_scale')
        card.prop(settings, 'apply_unit_scale')
    else:
        card.prop(settings, 'gltf_yup')
    card.prop(settings, 'animation')
    note(card, 'Animation: object actions only; no rigs, NLA or drivers.')
    card.prop(settings, 'export_materials')
    card.prop(settings, 'warn_scale')
    card.prop(settings, 'polygon_limit')
    note(card, 'Switching platform loads saved settings. Save edits before switching.')
    card.prop(settings, 'directory')
    card.prop(settings, 'prefix')
    note(card, 'Static meshes / isolated scene / existing files protected')
    card.operator('blendflow.export_guard', text='Run Preflight Check', icon='VIEWZOOM')
    note(layout, settings.status)
    if settings.issues:
        layout.template_list('BF_UL_export', '', settings, 'issues', settings, 'index', rows=5)
        if 0 <= settings.index < len(settings.issues):
            note(layout.box(), settings.issues[settings.index].message)
    row = layout.row()
    row.scale_y = 1.6
    row.operator('blendflow.export_guard', text='Export Assets', icon='EXPORT').execute_export = True
    note(layout, 'Preflight is rerun before every export. Exported files are not undone by Ctrl+Z.')
