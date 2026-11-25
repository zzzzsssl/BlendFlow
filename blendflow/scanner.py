"""Read-only checks. No operators, selection changes or datablock writes."""
import os
import bpy


def scan(scene):
    issues = []
    for obj in scene.objects:
        if any(abs(v - 1.0) > 1e-5 for v in obj.scale):
            issues.append(('WARNING', 'Unapplied scale', obj, 'Review scale before physics or export.'))
        if obj.type == 'MESH' and len(obj.data.vertices) == 0:
            issues.append(('WARNING', 'Empty mesh', obj, 'Base mesh has no vertices; modifiers may generate geometry.'))
    # Image checks deliberately cover the entire blend file, including unused images.
    for image in bpy.data.images:
        if image.source != 'FILE' or image.packed_file or image.packed_files:
            continue
        path = bpy.path.abspath(image.filepath, library=image.library)
        if not image.filepath or not os.path.isfile(path):
            issues.append(('ERROR', 'Missing image: ' + image.name, None, path or '(empty path)'))
    return issues
