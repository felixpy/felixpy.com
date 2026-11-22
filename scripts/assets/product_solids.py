import runpy
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

corners = runpy.run_path(str(Path(__file__).with_name("rog-peripheral-tools.py")))[
    "corners"
]


def vertex(x, y, z):
    return x * 0.001, -z * 0.001, y * 0.001


def mesh(name, vertices, faces, material):
    data = bpy.data.meshes.new(name)
    data.from_pydata([vertex(*point) for point in vertices], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    return obj


def apply(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def block(name, x, h, z, w, height, depth, r, mat):
    points = corners(w, depth, min(r, w * 0.48, depth * 0.48), 7)
    n = len(points)
    vs = [(x + u, h + v, z + d) for v in (-height / 2, height / 2) for u, d in points]
    fs = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    fs += [(i, i + n, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    return mesh(name, vs, fs, mat)


def edge(obj, amount, segments=3):
    mod = obj.modifiers.new("Moulded edge", "BEVEL")
    mod.width = amount * 0.001
    mod.segments = segments
    mod.harden_normals = True
    apply(obj, mod)
    normal = obj.modifiers.new("Tooling normals", "WEIGHTED_NORMAL")
    apply(obj, normal)
    return obj


def subtract(obj, cutters):
    bpy.ops.object.select_all(action="DESELECT")
    for cutter in cutters:
        cutter.select_set(True)
    tool = cutters[0]
    bpy.context.view_layer.objects.active = tool
    if len(cutters) > 1:
        bpy.ops.object.join()
    mod = obj.modifiers.new("Open mould pockets", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = tool
    apply(obj, mod)
    bpy.data.objects.remove(tool, do_unlink=True)


def pin(name, start, end, radius, mat, sides=36):
    a, b = Vector(vertex(*start)), Vector(vertex(*end))
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=sides,
        radius=radius * 0.001,
        depth=(b - a).length,
        location=(a + b) / 2,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def combine(name, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    objects[0].name = name
    return objects[0]


letters = runpy.run_path(str(Path(__file__).with_name("vitrine-sculpt.py")))["letters"]


def engraving(label, x, y, z, height, mat):
    points, faces = letters(label, False)
    return mesh(
        label, [(x + a * height, y + b * height, z) for a, b in points], faces, mat
    )


def frame(origin, right, up, outward):
    def axis(direction):
        x, h, z = direction
        return Vector((x, -z, h))

    axes = Matrix((axis(right), -axis(outward), axis(up))).transposed().to_4x4()
    axes.translation = Vector(vertex(*origin))
    return axes


def placed(obj, transform):
    bpy.context.view_layer.update()
    obj.matrix_world = transform @ obj.matrix_world
    return obj


def front_plate(name, x, h, d, w, height, depth, radius, mat):
    obj = block(name, 0, 0, 0, w, depth, height, radius, mat)
    transform = frame((x, h, d), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    return placed(obj, transform)


def outline(name, coords, d, thickness, material):
    vs = [(x, h, z) for z in (d, d + thickness) for x, h in coords]
    n = len(coords)
    area = sum(
        coords[i][0] * coords[(i + 1) % n][1] - coords[(i + 1) % n][0] * coords[i][1]
        for i in range(n)
    )
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    if area < 0:
        faces = [f[::-1] for f in faces]
    return mesh(name, vs, faces, material)
