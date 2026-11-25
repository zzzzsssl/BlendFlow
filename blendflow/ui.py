import bpy
from .properties import CATEGORIES


class BF_UL_issues(bpy.types.UIList):
    def filter_items(self, context, data, propname):
        flags = [self.bitflag_filter_item if data.category == 'ALL' or item.category == data.category
                 else 0 for item in getattr(data, propname)]
        return flags, []

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        label = item.title + (' | ' + item.target.name if item.target else '')
        op = layout.operator('blendflow.locate', text=label, emboss=False, icon='RESTRICT_SELECT_OFF')
        op.issue_index = index
        op.frame = False


def note(layout, text):
    import textwrap
    width = max(22, int(bpy.context.region.width / 7) - 7) if bpy.context.region else 40
    for line in textwrap.wrap(text, width=width):
        layout.label(text=line)


class BF_PT_inspector(bpy.types.Panel):
    bl_label = 'Smart Inspector'
    bl_idname = 'BF_PT_inspector'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendFlow'

    def draw(self, context):
        layout = self.layout.box()
        state = context.window_manager.blendflow
        card = layout.box()
        card.label(text='Scene Inspector', icon='VIEWZOOM')
        scope = card.column(align=True)
        scope.label(text='Objects: Entire Scene')
        scope.label(text='External Images: Entire File')
        card.separator()
        primary = card.row()
        primary.scale_y = 1.7
        primary.operator('blendflow.scan', text='Scan Scene', icon='VIEWZOOM')
        if context.mode != 'OBJECT':
            note(card, 'Switch to Object Mode to scan.')
        layout.separator()
        if not state.scene:
            empty = layout.box()
            empty.label(text='Ready to inspect your scene', icon='VIEWZOOM')
            note(empty, 'Check object scale, empty meshes and missing external images.')
            note(layout, 'Scanning is read-only. Changes require a separate action.')
            return
        if state.scene != context.scene:
            note(layout, 'Scene changed. Rescan before resolving issues.')
        results = layout.box()
        results.label(text='Inspection Results', icon='PRESET')
        note(results, state.status)
        grid = results.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        for key, label, _ in CATEGORIES:
            count = sum(1 for item in state.issues if key == 'ALL' or item.category == key)
            grid.prop_enum(state, 'category', key, text=f'{label} ({count})')
        count = sum(1 for item in state.issues if state.category == 'ALL' or item.category == state.category)
        if count:
            results.template_list('BF_UL_issues', '', state, 'issues', state, 'index', rows=5)
        else:
            results.label(text='No issues in this category', icon='CHECKMARK')
        if 0 <= state.index < len(state.issues):
            issue = state.issues[state.index]
            if state.category == 'ALL' or issue.category == state.category:
                detail = layout.box()
                detail.label(text=issue.title, icon='INFO')
                note(detail, issue.detail)
                if issue.target:
                    detail.operator('blendflow.locate', text='Select & Frame Object', icon='RESTRICT_SELECT_OFF')
                detail.separator()
                actions = detail.column(align=True)
                actions.enabled = context.mode == 'OBJECT' and state.scene == context.scene
                if issue.category in {'SCALE', 'EMPTY'}:
                    label = 'Apply Scale' if issue.category == 'SCALE' else 'Delete Empty Mesh'
                    for batch, suffix in ((False, 'This'), (True, 'All in Category')):
                        op = actions.operator('blendflow.fix', text=label + ' - ' + suffix)
                        op.category = issue.category
                        op.batch = batch
                elif issue.category == 'IMAGE':
                    actions.operator('blendflow.relink', text='Relink This Image').batch = False
                    actions.operator('blendflow.relink', text='Find All Missing in Folder').batch = True
        if state.locate_status:
            note(layout.box(), state.locate_status)


class BF_PT_smart_preview(bpy.types.Panel):
    bl_label = 'Smart Thumb Preview'
    bl_idname = 'BF_PT_smart_preview'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendFlow'
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        from .preview import draw_preview
        draw_preview(self.layout.box(), context)


class BF_PT_export_guard(bpy.types.Panel):
    bl_label = 'Export Guard'
    bl_idname = 'BF_PT_export_guard'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendFlow'
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        from .export_guard import draw_export
        draw_export(self.layout.box(), context)
