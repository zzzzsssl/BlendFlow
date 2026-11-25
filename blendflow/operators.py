import bpy
from .scanner import scan
from .properties import update_category


class BF_OT_scan(bpy.types.Operator):
    bl_idname = 'blendflow.scan'
    bl_label = 'Scan Scene'
    bl_description = 'Read-only inspection; results are a snapshot'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        results = scan(context.scene)
        state = context.window_manager.blendflow
        state.issues.clear()
        state.locate_status = ""
        for severity, title, target, detail in results:
            item = state.issues.add()
            item.severity, item.title, item.target, item.detail = severity, title, target, detail
            item.category = ('SCALE' if title == 'Unapplied scale' else
                             'EMPTY' if title == 'Empty mesh' else 'IMAGE')
            if item.category == 'IMAGE':
                item.image = bpy.data.images.get(title.removeprefix('Missing image: '))
        update_category(state, context)
        state.scene = context.scene
        state.status = f'{len(results)} issues | Snapshot: rescan after edits'
        return {'FINISHED'}


class BF_OT_locate(bpy.types.Operator):
    bl_idname = 'blendflow.locate'
    bl_label = 'Select Object'
    bl_description = 'Select and frame the object; report hidden or locked targets'
    issue_index: bpy.props.IntProperty(default=-1)
    frame: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        state = context.window_manager.blendflow
        if self.issue_index >= 0:
            if self.issue_index >= len(state.issues):
                return {'CANCELLED'}
            state.index = self.issue_index

        def fail(message):
            state.locate_status = message
            self.report({'WARNING'}, message)
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            return fail('Switch to Object Mode first')
        if state.scene != context.scene or not 0 <= state.index < len(state.issues):
            return fail('Rescan the current scene first')
        obj = state.issues[state.index].target
        if state.issues[state.index].category == 'IMAGE':
            state.locate_status = 'Image selected; use Relink This Image below'
            return {'FINISHED'}
        if not obj:
            return fail('Object no longer exists; rescan')
        if obj.name not in context.view_layer.objects:
            return fail('Object excluded from current View Layer')
        if not obj.visible_get(view_layer=context.view_layer, viewport=context.space_data if context.area and context.area.type == 'VIEW_3D' else None):
            return fail('Object hidden or outside Local View; reveal it first')
        if obj.hide_select or obj not in context.selectable_objects:
            return fail('Selection disabled on object or collection')
        previous = list(context.selected_objects)
        active = context.view_layer.objects.active
        try:
            for selected in previous:
                selected.select_set(False)
            obj.select_set(True)
            context.view_layer.objects.active = obj
            if not obj.select_get():
                raise RuntimeError('Blender did not select the object')
        except RuntimeError as exc:
            for selected in previous:
                selected.select_set(True)
            context.view_layer.objects.active = active
            return fail(str(exc))
        state.locate_status = 'Selected: ' + obj.name
        if self.frame and context.area and context.area.type == 'VIEW_3D':
            region = next((r for r in context.area.regions if r.type == 'WINDOW'), None)
            if region:
                with context.temp_override(region=region):
                    if bpy.ops.view3d.view_selected.poll():
                        bpy.ops.view3d.view_selected(use_all_regions=False)
            context.area.tag_redraw()
        self.report({'INFO'}, state.locate_status)
        return {'FINISHED'}
