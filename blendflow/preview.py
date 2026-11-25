"""Isolated evaluated mesh snapshots with orthographic studio framing."""
import os
import re
import bpy
from mathutils import Vector


def render_preview(context, sources, filepath, size=512, view='THREE_QUARTER', lighting='SOFT', exposure=0.0):
    scene = bpy.data.scenes.new('BlendFlow Preview Temporary')
    objects, meshes, lights = [], [], []
    camera_data = world = None
    try:
        depsgraph = context.evaluated_depsgraph_get()
        points = []
        for source in sources:
            if source.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'} or source.hide_render:
                continue
            mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
            meshes.append(mesh)
            if not mesh.vertices:
                continue
            obj = bpy.data.objects.new(source.name, mesh)
            objects.append(obj)
            scene.collection.objects.link(obj)
            obj.matrix_world = source.matrix_world.copy()
            points.extend(obj.matrix_world @ v.co for v in mesh.vertices)
        if not points:
            raise ValueError('No renderable geometry')
        lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
        upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
        center = (lower + upper) / 2
        radius = max((upper-lower).length, 0.001)
        camera_data = bpy.data.cameras.new('BF Preview Camera')
        camera = bpy.data.objects.new('BF Preview Camera', camera_data)
        objects.append(camera)
        scene.collection.objects.link(camera)
        direction = Vector({'THREE_QUARTER':(1,-1,0.75), 'FRONT':(0,-1,0), 'SIDE':(1,0,0), 'TOP':(0,0,1)}[view]).normalized()
        camera.location = center + direction * radius * 3
        camera.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
        inverse = camera.rotation_euler.to_matrix().transposed()
        projected = [inverse @ (p-center) for p in points]
        width = max(p.x for p in projected)-min(p.x for p in projected)
        height = max(p.y for p in projected)-min(p.y for p in projected)
        shift = Vector(((max(p.x for p in projected)+min(p.x for p in projected))/2,
                        (max(p.y for p in projected)+min(p.y for p in projected))/2, 0))
        camera.location += camera.rotation_euler.to_matrix() @ shift
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = max(width, height, 0.001) * 1.2
        camera_data.clip_start = radius * 0.001
        camera_data.clip_end = radius * 10
        scene.camera = camera
        powers = {'SOFT':(180,90,180), 'NEUTRAL':(300,150,250), 'CONTRAST':(280,40,180)}[lighting]
        for position, power in zip(((-1,-2,3),(2,-1,1),(0,2,2)), powers):
            data = bpy.data.lights.new('BF Studio', 'AREA')
            lights.append(data)
            if hasattr(data, 'normalize'):
                data.normalize = True
            data.energy = power * radius * radius
            data.shape = 'DISK'
            data.size = radius * 2
            lamp = bpy.data.objects.new('BF Studio', data)
            objects.append(lamp)
            scene.collection.objects.link(lamp)
            lamp.location = center + camera.rotation_euler.to_matrix() @ Vector(position) * radius
            lamp.rotation_euler = (center-lamp.location).to_track_quat('-Z','Y').to_euler()
        world = bpy.data.worlds.new('BF Preview World')
        world.use_nodes = True
        world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0.08
        scene.world = world
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = exposure
        scene.view_settings.gamma = 1.0
        scene.view_settings.use_curve_mapping = False
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
        scene.render.resolution_x = scene.render.resolution_y = size
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True, scene=scene.name)
    finally:
        bpy.data.scenes.remove(scene)
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            bpy.data.meshes.remove(mesh)
        for light in lights:
            bpy.data.lights.remove(light)
        if camera_data:
            bpy.data.cameras.remove(camera_data)
        if world:
            bpy.data.worlds.remove(world)


class BF_PreviewSettings(bpy.types.PropertyGroup):
    view: bpy.props.EnumProperty(name='Camera Preset', items=(('THREE_QUARTER','Three Quarter',''),('FRONT','Front (-Y)',''),('SIDE','Side (+X)',''),('TOP','Top (+Z)','')))
    lighting: bpy.props.EnumProperty(name='Lighting', items=(('SOFT','Soft Studio','Lower intensity'),('NEUTRAL','Neutral Studio','Balanced key and fill'),('CONTRAST','Contrast Studio','Reduced fill')), default='SOFT')
    exposure: bpy.props.FloatProperty(name='Exposure (EV)', default=0, min=-5, max=5)

    directory: bpy.props.StringProperty(name='Output Folder', subtype='DIR_PATH')
    mode: bpy.props.EnumProperty(name='Batch', items=(('OBJECT','Selected Objects','One PNG per selected object'), ('COLLECTION','Collection Children','One PNG per immediate child, or the collection itself if no children')))
    collection: bpy.props.PointerProperty(name='Collection', type=bpy.types.Collection)
    size: bpy.props.EnumProperty(name='Resolution', items=(('256','256',''),('512','512',''),('1024','1024','')), default='512')
    status: bpy.props.StringProperty()


class BF_OT_preview(bpy.types.Operator):
    bl_idname = 'blendflow.preview'
    bl_label = 'Generate Transparent PNGs'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        settings = context.window_manager.blendflow_preview
        if not settings.directory:
            self.report({'WARNING'}, 'Choose an output folder')
            return {'CANCELLED'}
        if settings.mode == 'OBJECT':
            jobs = [(obj.name, [obj]) for obj in context.selected_objects]
        elif settings.collection:
            root = settings.collection
            jobs = [(c.name, list(c.all_objects)) for c in (list(root.children) or [root])]
        else:
            self.report({'WARNING'}, 'Choose a collection')
            return {'CANCELLED'}
        if not jobs:
            self.report({'WARNING'}, 'Select objects first')
            return {'CANCELLED'}
        folder = bpy.path.abspath(settings.directory)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        completed = 0
        failures = []
        for name, sources in jobs:
            stem = re.sub(r'[^a-zA-Z0-9_ -]', '_', name)[:80].strip() or 'Asset'
            path = os.path.join(folder, stem + '.png')
            number = 1
            while os.path.exists(path):
                path = os.path.join(folder, f'{stem}_{number:03d}.png')
                number += 1
            try:
                render_preview(context, sources, path, int(settings.size), settings.view, settings.lighting, settings.exposure)
                completed += 1
            except Exception as exc:
                failures.append(name + ': ' + str(exc))
                print('BlendFlow preview:', failures[-1])
        settings.status = f'Generated {completed}; failed {len(failures)}'
        if failures:
            settings.status += ' | ' + failures[0]
        self.report({'INFO'}, settings.status)
        return {'FINISHED'}


def draw_preview(layout, context):
    from .ui import note
    settings = context.window_manager.blendflow_preview
    card = layout.box()
    card.label(text='Smart Thumb Preview', icon='RENDER_STILL')
    card.prop(settings, 'mode')
    if settings.mode == 'COLLECTION':
        card.prop(settings, 'collection')
        note(card, 'One image per immediate child collection; otherwise the chosen collection.')
    else:
        card.label(text=f'{len(context.selected_objects)} objects selected')
    output = layout.box()
    output.label(text='Output & Style', icon='IMAGE_DATA')
    output.prop(settings, 'directory')
    output.prop(settings, 'size')
    output.prop(settings, 'view')
    output.prop(settings, 'lighting')
    output.prop(settings, 'exposure')
    note(output, 'Studio lighting / transparent PNG / automatic framing')
    primary = output.row()
    primary.scale_y = 1.7
    primary.operator('blendflow.preview', text='Generate Previews', icon='RENDER_STILL')
    layout.separator()
    status = layout.box()
    if settings.status:
        note(status, settings.status)
    else:
        status.label(text='Ready to showcase your assets', icon='IMAGE_DATA')
        note(status, 'Select objects or a collection, then choose an output folder.')
    note(layout, 'Original scene preserved. Existing PNGs kept. Rendering may take time.')
