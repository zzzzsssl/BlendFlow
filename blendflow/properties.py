import bpy

CATEGORIES = (('ALL', 'All Issues', ''), ('SCALE', 'Unapplied Scale', ''),
              ('EMPTY', 'Empty Mesh', ''), ('IMAGE', 'Missing Images', ''))


def update_category(self, context):
    self.index = next((i for i, item in enumerate(self.issues)
                       if self.category == 'ALL' or item.category == self.category), -1)

class BF_Issue(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty()
    image: bpy.props.PointerProperty(type=bpy.types.Image)
    severity: bpy.props.StringProperty()
    title: bpy.props.StringProperty()
    detail: bpy.props.StringProperty()
    target: bpy.props.PointerProperty(type=bpy.types.Object)


class BF_State(bpy.types.PropertyGroup):
    page: bpy.props.EnumProperty(items=(('INSPECT', 'Smart Inspector', 'Inspect and resolve scene issues'), ('PREVIEW', 'Smart Thumb Preview', 'Generate asset thumbnails'), ('EXPORT', 'Export Guard', 'Preflight and safe static mesh export')), default='INSPECT')
    locate_status: bpy.props.StringProperty()
    category: bpy.props.EnumProperty(items=CATEGORIES, default='ALL', update=update_category)
    issues: bpy.props.CollectionProperty(type=BF_Issue)
    index: bpy.props.IntProperty(default=0)
    status: bpy.props.StringProperty(default='Not scanned')
    scene: bpy.props.PointerProperty(type=bpy.types.Scene)
