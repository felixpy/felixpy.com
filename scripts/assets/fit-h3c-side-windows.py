from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.references/06-工坊与工具/三维打印与模型/Bambu Lab H3C/Blender/h3c-side-windows.blend'
COLLECTION = 'H3C · left and right side windows'


def retired_surface(finish, points):
    side = 1 if points[0].x > 0 else -1
    def in_box(xmin, xmax, ymin, ymax, zmin, zmax):
        return all(xmin-.00004 <= p.x*side <= xmax+.00004 and ymin-.00004 <= p.z <= ymax+.00004
                   and zmin-.00004 <= -p.y <= zmax+.00004 for p in points)

    if finish == 'alloy':
        return (in_box(.2465,.2465,.013,.585,-.258,.242) and
                all(min(abs(p.z - y) for y in (.013,.585)) < .00004 and
                    min(abs(p.y - y) for y in (-.242,.258)) < .00004 for p in points) and
                max(p.y for p in points)-min(p.y for p in points) > .49)
    if finish == 'black':
        return in_box(.2448,.2488,.3955,.5185,-.2335,.1975)
    return (in_box(.222,.228,.014,.556,-.264,.192) or
            in_box(.24825,.24995,.4135,.5005,-.215,.186))


def fit(scene):
    mounted = scene.objects.get(COLLECTION)
    if mounted:
        assert mounted.instance_collection.name == COLLECTION and len(mounted.instance_collection.objects) == 40
        return len(mounted.instance_collection.objects)
    printer = scene.objects.get('Bambu Lab H3C with AMS 3H')
    inverse = printer.matrix_world.inverted() if printer else Matrix.Identity(4)
    prefix = 'H3C frame-' if printer else 'frame-'
    removals = []
    for finish in ('alloy','black','graphite'):
        obj = scene.objects[prefix+finish]
        transform = inverse @ obj.matrix_world
        points = [transform @ v.co for v in obj.data.vertices]
        faces = [p.index for p in obj.data.polygons if retired_surface(finish, [points[i] for i in p.vertices])]
        removals.append((obj, faces))
    if not removals[0][1] or len(removals[2][1]) < 100:
        pane = scene.objects[prefix+'smoke']
        transform = inverse @ pane.matrix_world
        points = [transform @ v.co for v in pane.data.vertices]
        assert sum(abs(abs(v.x) - .2441) < .00004 and .415 < v.z < .56 for v in points) > 250, 'Missing side windows'
        return 40
    assert len(removals[0][1]) in (2,4) and all(len(faces)>80 for _,faces in removals[1:]), 'Unexpected H3C side shell'
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (available, loaded):
        assert COLLECTION in available.collections
        loaded.collections = [COLLECTION]
    windows = loaded.collections[0]
    assert len(windows.objects) == 40
    for obj, faces in removals:
        data = obj.data.copy() if obj.data.users>1 or obj.data.library else obj.data
        if data != obj.data:
            obj.data = data
        mesh = bmesh.new()
        try:
            mesh.from_mesh(data)
            mesh.faces.ensure_lookup_table()
            bmesh.ops.delete(mesh, geom=[mesh.faces[i] for i in faces], context='FACES')
            mesh.to_mesh(data)
        finally:
            mesh.free()
    mounted = bpy.data.objects.new(COLLECTION,None)
    (printer.users_collection[0] if printer else scene.collection).objects.link(mounted)
    mounted.parent = printer
    mounted.instance_type = 'COLLECTION'
    mounted.instance_collection = windows
    return len(windows.objects)
