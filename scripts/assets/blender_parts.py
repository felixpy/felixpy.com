import math

import bpy
from mathutils import Vector

from blender_mesh import write_mesh


def xyz(point):
    x, y, z = point
    return Vector((x, -z, y)) * 0.001


def bevel(obj, width, count=2):
    if width:
        modifier = obj.modifiers.new("Machined edge radius", "BEVEL")
        modifier.width = width * 0.001
        modifier.segments = count
        modifier.harden_normals = True
        modifier.limit_method = "ANGLE"
        normal = obj.modifiers.new("Broad face normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return obj


def block(name, size, point, radius=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz(point))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(n * 0.001 for n in (size[0], size[2], size[1]))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return bevel(obj, radius)


def barrel(name, a, b, radius, vertices=32, radius_b=None):
    start, end = xyz(a), xyz(b)
    direction = end - start
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius * 0.001,
        radius2=(radius if radius_b is None else radius_b) * 0.001,
        depth=direction.length,
        location=(start + end) * 0.5,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def spun(name, center, steps, profile):
    vertices = []
    faces = []
    for y, r in profile:
        for i in range(steps):
            a = i * 2 * math.pi / steps
            vertices.append(
                xyz((center[0] + math.cos(a) * r, y, center[1] + math.sin(a) * r))
            )
    for j in range(len(profile) - 1):
        for i in range(steps):
            k = j * steps + i
            next = j * steps + (i + 1) % steps
            faces.append((k, k + steps, next + steps, next))
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for poly in data.polygons:
        poly.use_smooth = True
    return obj


def pipe(name, points, radius):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 8
    data.bevel_depth = radius * 0.001
    data.bevel_resolution = 2
    data.use_fill_caps = True
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = xyz(point)
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def sample_bezier(curve, error_mm):
    nodes = curve.data.splines[0].bezier_points
    points = [nodes[0].co.copy()]
    tolerance = error_mm * 0.001

    def split(a, b, c, d):
        chord = (d - a).normalized()
        deviation = max((control - a).cross(chord).length for control in (b, c))
        if deviation <= tolerance:
            points.append(d.copy())
            return
        ab, bc, cd = a.lerp(b, 0.5), b.lerp(c, 0.5), c.lerp(d, 0.5)
        left, right = ab.lerp(bc, 0.5), bc.lerp(cd, 0.5)
        mid = left.lerp(right, 0.5)
        split(a, ab, left, mid)
        split(mid, right, cd, d)

    for a, b in zip(nodes, list(nodes)[1:]):
        split(a.co, a.handle_right, b.handle_left, b.co)
    return points


def export_batch(name, objects, output):
    graph = bpy.context.evaluated_depsgraph_get()
    copies = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        data = bpy.data.meshes.new_from_object(evaluated, depsgraph=graph)
        data.transform(evaluated.matrix_world)
        copy = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(copy)
        copies.append(copy)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in copies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    if len(copies) > 1:
        bpy.ops.object.join()
    result = write_mesh(copies[0], output)
    bpy.data.objects.remove(copies[0], do_unlink=True)
    return result
