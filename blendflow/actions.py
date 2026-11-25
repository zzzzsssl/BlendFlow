"""Explicit, undoable resolution actions; scanning itself remains read-only."""
import os
import bpy


def issues(context, category, batch):
    state = context.window_manager.blendflow
    if state.scene != context.scene:
        return []
    rows = list(state.issues) if batch else list(state.issues[state.index:state.index + 1]) if state.index >= 0 else []
    return [row for row in rows if row.category == category]


class BF_OT_fix(bpy.types.Operator):
    bl_idname = 'blendflow.fix'
    bl_label = 'Confirm Resolution'
    bl_options = {'REGISTER', 'UNDO'}
    category: bpy.props.StringProperty()
    batch: bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=460)

    def draw(self, context):
        count = len(issues(context, self.category, self.batch))
        self.layout.label(text=f'{count} candidates; ineligible objects will be skipped')
        self.layout.label(text='Apply scale to mesh data' if self.category == 'SCALE' else 'Delete empty mesh objects from this scene')
        self.layout.label(text='Scale: skips shared data, children, animation and constraints')
        self.layout.label(text='Delete: skips modifiers, children and multi-scene objects')
        self.layout.label(text='Undo available with Ctrl+Z')

    def execute(self, context):
        targets = [r.target for r in issues(context, self.category, self.batch)]
        selected = list(context.selected_objects)
        active = context.view_layer.objects.active
        done = 0
        for obj in targets:
            if not obj or obj.library or obj.override_library or obj.name not in context.view_layer.objects:
                continue
            if obj.type != 'MESH' or obj.data.library or obj.children:
                continue
            if self.category == 'EMPTY':
                if len(obj.data.vertices) or obj.modifiers or len(obj.users_scene) != 1:
                    continue
                bpy.data.objects.remove(obj, do_unlink=True)
                done += 1
            elif self.category == 'SCALE':
                if obj not in context.selectable_objects or obj.data.users > 1 or obj.animation_data or obj.constraints or obj.data.shape_keys:
                    continue
                if not any(abs(v - 1) > 1e-5 for v in obj.scale):
                    continue
                for selected_obj in list(context.selected_objects):
                    selected_obj.select_set(False)
                obj.select_set(True)
                context.view_layer.objects.active = obj
                context.view_layer.update()
                with context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
                    try:
                        result = bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                        context.view_layer.update()
                        done += result == {'FINISHED'} and all(abs(v - 1) <= 1e-5 for v in obj.scale)
                    except RuntimeError:
                        continue
        # Deleted RNA references cannot be inspected; restore by identity of survivors.
        context.view_layer.update()
        survivors = [obj for obj in context.view_layer.objects if obj]
        for obj in survivors:
            obj.select_set(obj in selected)
        context.view_layer.objects.active = active if active in survivors else None
        bpy.ops.blendflow.scan()
        message = f'Completed {done}; skipped {len(targets) - done} (unsupported or protected)'
        context.window_manager.blendflow.locate_status = message
        self.report({'INFO'}, message)
        return {'FINISHED'}


class BF_OT_relink(bpy.types.Operator):
    bl_idname = 'blendflow.relink'
    bl_label = 'Relink Missing Images'
    bl_options = {'REGISTER', 'UNDO'}
    batch: bpy.props.BoolProperty()
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        self.layout.label(text='Batch: search selected folder recursively by exact filename')
        self.layout.label(text='Duplicate matches are skipped; files are not moved')

    def execute(self, context):
        rows = issues(context, 'IMAGE', self.batch)
        matches = {}
        if self.batch:
            if not os.path.isdir(self.directory):
                self.report({'WARNING'}, 'Choose an existing folder')
                return {'CANCELLED'}
            for folder, _, names in os.walk(self.directory):
                for name in names:
                    matches.setdefault(name, []).append(os.path.join(folder, name))
        elif not os.path.isfile(self.filepath):
            self.report({'WARNING'}, 'Choose an existing image file')
            return {'CANCELLED'}
        done = 0
        for row in rows:
            image = row.image
            if not image or image.library or image.packed_file:
                continue
            paths = matches.get(os.path.basename(image.filepath), []) if self.batch else [self.filepath]
            if len(paths) != 1:
                continue
            old = image.filepath
            try:
                image.filepath = paths[0]
                image.reload()
                done += 1
            except RuntimeError:
                image.filepath = old
        bpy.ops.blendflow.scan()
        message = f'Relinked {done}; skipped {len(rows) - done}'
        context.window_manager.blendflow.locate_status = message
        self.report({'INFO'}, message)
        return {'FINISHED'}

