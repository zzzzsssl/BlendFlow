"""Render comparisons and conservative camera-space multi-aspect framing."""
import bpy
import json
import math
import os
import time
import uuid
from mathutils import Vector


def output_folder(settings):
    if not settings.directory:
        raise ValueError('Choose an output folder')
    path = os.path.join(bpy.path.abspath(settings.directory), 'smart_render_' + uuid.uuid4().hex[:10])
    os.makedirs(path)
    return path


def render_copy(source):
    scene = source.copy()
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    return scene


def pixels(path):
    import numpy as np
    image = bpy.data.images.load(path, check_existing=False)
    try:
        data = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(data)
        return data.reshape(image.size[1], image.size[0], 4)[:, :, :3].copy()
    finally:
        bpy.data.images.remove(image)


def optimize(context, settings):
    import numpy as np
    source = context.scene
    if source.render.engine != 'CYCLES' or not source.camera:
        raise ValueError('Cycles and an active camera are required')
    folder = output_folder(settings)
    scene = render_copy(source)
    rows = []
    try:
        aspect = source.render.resolution_x * source.render.pixel_aspect_x / (source.render.resolution_y * source.render.pixel_aspect_y)
        scene.render.resolution_x = settings.size if aspect >= 1 else max(8, round(settings.size * aspect))
        scene.render.resolution_y = max(8, round(settings.size / aspect)) if aspect >= 1 else settings.size
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.seed = 0
        scene.cycles.use_animated_seed = False
        for samples, denoise in [(4096, False)] + [(s, d) for s in (512,1024,2048) for d in (False,True)]:
            scene.cycles.samples = samples
            scene.cycles.use_denoising = denoise
            scene.cycles.denoiser = 'OPENIMAGEDENOISE'
            path = os.path.join(folder, f'{samples}_denoise_{int(denoise)}.png')
            scene.render.filepath = path
            start = time.perf_counter()
            bpy.ops.render.render(write_still=True, scene=scene.name)
            elapsed = time.perf_counter()-start
            data = pixels(path)
            if samples == 4096:
                reference = data
                reference_time = elapsed
                continue
            error = data-reference
            h,w,_ = data.shape
            region = error[h//4:3*h//4,w//4:3*w//4]
            rmse = float(np.sqrt(np.mean(error**2)))
            detail = float(np.sqrt(np.mean(region**2)))
            # Difference image highlights discrepancies against the noisy reference.
            if not denoise:
                image = bpy.data.images.new('BF Difference', width=w, height=h)
                try:
                    rgba = np.ones((h,w,4),dtype=np.float32)
                    rgba[:,:,:3] = np.clip(np.abs(error)*4,0,1)
                    image.pixels.foreach_set(rgba.ravel())
                    image.filepath_raw = path.replace('.png','_difference_x4.png')
                    image.file_format = 'PNG'
                    image.save()
                finally:
                    bpy.data.images.remove(image)
            crop = data[h//4:3*h//4,w//4:3*w//4]
            ch,cw,_ = crop.shape
            image = bpy.data.images.new('BF Detail', width=cw, height=ch)
            try:
                rgba = np.ones((ch,cw,4),dtype=np.float32)
                rgba[:,:,:3] = crop
                image.pixels.foreach_set(rgba.ravel())
                image.filepath_raw = path.replace('.png','_detail.png')
                image.file_format = 'PNG'
                image.save()
            finally:
                bpy.data.images.remove(image)
            rows.append(dict(samples=samples, denoise=denoise, seconds=elapsed, rmse=rmse, center_detail_rmse=detail, image=path))
        best = min(r['rmse'] for r in rows)
        candidates = [r for r in rows if r['rmse'] <= best*1.15 + 0.002]
        recommended = min(candidates, key=lambda r:r['seconds'])
        report = dict(reference_samples=4096, reference_denoise=False, reference_seconds=reference_time, comparisons=rows, recommended=recommended, method='Fastest within 15% + 0.002 RMSE of best candidate; PNG linear pixels, central 50% detail region. Reference is noisy, not ground truth. One timing run includes warm-up effects.')
        with open(os.path.join(folder,'comparison.json'),'w',encoding='utf-8') as handle:
            json.dump(report,handle,indent=2)
        html = ['<meta charset="utf-8"><title>BlendFlow Render Comparison</title><style>body{background:#23262d;color:#eee;font:16px sans-serif;padding:24px}img{width:240px}td,th{padding:12px;text-align:left}</style><h1>Render Optimizer</h1>', '<p>'+report['method']+'</p>', '<p>Recommended: '+str(recommended['samples'])+' samples, denoise '+str(recommended['denoise'])+'</p><table><tr><th>Configuration</th><th>Seconds / RMSE / Detail RMSE</th><th>Render</th><th>Center detail</th><th>Difference x4</th></tr>']
        for row in rows:
            filename=os.path.basename(row['image'])
            html.append('<tr><td>'+str(row['samples'])+' / denoise '+str(row['denoise'])+'</td><td>'+str(round(row['seconds'],3))+' / '+str(round(row['rmse'],5))+' / '+str(round(row['center_detail_rmse'],5))+'</td>'+''.join('<td><img src="'+filename.replace('.png',suffix)+'"></td>' for suffix in ('.png','_detail.png'))+('<td>Not generated</td>' if row['denoise'] else '<td><img src="'+filename.replace('.png','_difference_x4.png')+'"></td>')+'</tr>')
        html.append('</table>')
        with open(os.path.join(folder,'comparison.html'),'w',encoding='utf-8') as handle:
            handle.write(''.join(html))
        settings.status = f'Recommend {recommended["samples"]} samples / denoise {recommended["denoise"]}'
        settings.last_output = folder
        settings.recommended_samples = recommended['samples']
        settings.recommended_denoise = recommended['denoise']
    finally:
        bpy.data.scenes.remove(scene)


def compose(context, settings):
    source = context.scene
    camera = source.camera
    if not camera or camera.data.type not in {'PERSP','ORTHO'}:
        raise ValueError('Perspective or orthographic active camera required')
    subjects = list(settings.collection.all_objects) if settings.collection else list(context.selected_objects)
    depsgraph = context.evaluated_depsgraph_get()
    points = []
    for obj in subjects:
        if obj.type in {'MESH','CURVE','SURFACE','FONT','META'}:
            evaluated = obj.evaluated_get(depsgraph)
            points.extend(evaluated.matrix_world @ Vector(v) for v in evaluated.bound_box)
    if not points:
        raise ValueError('Select geometry or specify a subject collection')
    folder = output_folder(settings)
    rotation = camera.matrix_world.to_quaternion()
    inverse = rotation.inverted()
    coords = [inverse @ p for p in points]
    low = Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    center = (low+high)/2
    span = high-low
    offset = {'CENTER':(0,0),'LEFT':(-1,0),'RIGHT':(1,0),'TOP':(0,1),'BOTTOM':(0,-1)}[settings.position]
    scene = render_copy(source)
    created = []
    try:
        for label, aspect in (('16x9',16/9),('1x1',1),('9x16',9/16)):
            data = camera.data.copy()
            data.animation_data_clear()
            data.shift_x = data.shift_y = 0
            data.dof.use_dof = False
            obj = bpy.data.objects.new('BF Composition '+label,data)
            source.collection.objects.link(obj)
            scene.collection.objects.link(obj)
            created.append(obj)
            obj.rotation_mode='QUATERNION'
            obj.rotation_quaternion=rotation
            width = max(span.x, span.y*aspect, 0.01)/(1-settings.margin)
            height = width/aspect
            target = center.copy()
            target.x -= offset[0] * settings.margin * width/2
            target.y -= offset[1] * settings.margin * height/2
            if data.type == 'ORTHO':
                data.ortho_scale = width if aspect >= 1 else height
                distance = max(span.length*2,1)
            else:
                data.sensor_fit='HORIZONTAL'
                distance = max(width/2*data.lens/data.sensor_width*2,0.01)+span.z/2
            target.z = center.z+distance
            obj.location = rotation @ target
            data.clip_start = max(0.0001,distance/10000)
            data.clip_end = max(distance+span.length*4,100)
            obj['blendflow_resolution_x']=settings.size if aspect>=1 else round(settings.size*aspect)
            obj['blendflow_resolution_y']=round(settings.size/aspect) if aspect>=1 else settings.size
            scene.camera=obj
            scene.render.resolution_x=obj['blendflow_resolution_x']
            scene.render.resolution_y=obj['blendflow_resolution_y']
            if scene.render.engine=='CYCLES':
                scene.cycles.samples=32
                scene.cycles.use_denoising=True
            scene.render.filepath=os.path.join(folder,label+'.png')
            bpy.ops.render.render(write_still=True,scene=scene.name)
        settings.last_output=folder
        settings.status='Created 3 cameras and aspect previews'
    except Exception:
        for obj in created:
            data=obj.data
            bpy.data.objects.remove(obj,do_unlink=True)
            bpy.data.cameras.remove(data)
        raise
    finally:
        bpy.data.scenes.remove(scene)


class BF_RenderSettings(bpy.types.PropertyGroup):
    directory: bpy.props.StringProperty(name='Output Folder',subtype='DIR_PATH')
    size: bpy.props.IntProperty(name='Preview Long Edge',default=512,min=64,max=2048)
    collection: bpy.props.PointerProperty(name='Subject Collection',type=bpy.types.Collection)
    position: bpy.props.EnumProperty(name='Subject Position',items=[(k,label,'') for k,label in (('CENTER','Center'),('LEFT','Left / space on right'),('RIGHT','Right / space on left'),('TOP','Top / space below'),('BOTTOM','Bottom / space above'))])
    margin: bpy.props.FloatProperty(name='Space Ratio',default=0.2,min=0.05,max=0.7)
    status: bpy.props.StringProperty()
    last_output: bpy.props.StringProperty(subtype='DIR_PATH')
    recommended_samples: bpy.props.IntProperty(default=0)
    recommended_denoise: bpy.props.BoolProperty()


class BF_OT_smart_render(bpy.types.Operator):
    bl_idname='blendflow.smart_render'
    bl_label='Smart Render'
    action: bpy.props.EnumProperty(items=(('OPTIMIZE','Test Render Settings',''),('COMPOSE','Generate Composition Previews',''),('APPLY','Apply Recommendation','')))
    def invoke(self,context,event):
        return context.window_manager.invoke_confirm(self,event)
    def execute(self,context):
        settings=context.window_manager.blendflow_render
        try:
            if self.action=='OPTIMIZE': optimize(context,settings)
            elif self.action=='COMPOSE': compose(context,settings)
            elif settings.recommended_samples:
                context.scene.cycles.samples=settings.recommended_samples
                context.scene.cycles.use_denoising=settings.recommended_denoise
                context.scene.cycles.denoiser='OPENIMAGEDENOISE'
                context.scene.cycles.use_adaptive_sampling=False
        except Exception as exc:
            settings.status=str(exc)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class BF_PT_smart_render(bpy.types.Panel):
    bl_label='Smart Render'
    bl_idname='BF_PT_smart_render'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='BlendFlow'
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        from .ui import note
        layout=self.layout.box()
        settings=context.window_manager.blendflow_render
        layout.prop(settings,'directory')
        layout.prop(settings,'size')
        card=layout.box()
        card.label(text='Render Optimizer')
        note(card,'Cycles: 512 / 1024 / 2048, denoise off/on + 4096 reference. Seven renders; interface waits until complete.')
        card.operator('blendflow.smart_render',text='Run Comparison').action='OPTIMIZE'
        if settings.recommended_samples:
            card.operator('blendflow.smart_render',text='Apply Recommendation').action='APPLY'
        card=layout.box()
        card.label(text='Smart Composition')
        card.prop(settings,'collection')
        note(card,'Blank collection uses selected geometry. Keeps viewing direction; creates separate cameras.')
        card.prop(settings,'position')
        card.prop(settings,'margin')
        card.operator('blendflow.smart_render',text='Generate 16:9 / 1:1 / 9:16').action='COMPOSE'
        if settings.status: note(layout,settings.status)
        if settings.last_output: layout.prop(settings,'last_output',text='Results')
