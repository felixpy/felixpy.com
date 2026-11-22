from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

product = (
    Path(__file__).resolve().parents[2]
    / ".references/05-摄影与陈列/相机与镜头/Nikon Z8/Blender"
)
source = product / "body-signatures.blend"
collection = "Nikon Z 8 · model signatures"

carrier = [
    (123, 67),
    (362, 67),
    (362, 106),
    (296, 181),
    (296, 207),
    (366, 207),
    (366, 261),
    (123, 261),
    (123, 221),
    (215, 123),
    (123, 123),
]
outline = [
    (143, 85),
    (342, 85),
    (342, 98),
    (227, 224),
    (344, 224),
    (344, 242),
    (139, 242),
    (139, 225),
    (255, 102),
    (143, 102),
]
window = [(279, 102), (312, 102), (203, 224), (170, 224)]


def inside(point, ring):
    x, y = point
    hit = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (
            b[1] - a[1]
        ) + a[0]:
            hit = not hit
    return hit


def silhouette(name, rings, thickness, place, mat):
    vertices = []
    edges = []
    for ring in rings:
        offset = len(vertices)
        vertices.extend(Vector(p) for p in ring)
        edges.extend(
            (offset + i, offset + (i + 1) % len(ring)) for i in range(len(ring))
        )
    v, _, tri, *_ = delaunay_2d_cdt(vertices, edges, [], 0, 1e-7)
    faces = []
    for t in tri:
        center = sum((v[i] for i in t), Vector((0, 0))) / 3
        if sum(inside(center, ring) for ring in rings) % 2:
            faces.append(tuple(t))
    idx = {tuple(p): i for i, p in enumerate(v)}
    count = len(v)
    polygons = list(faces) + [tuple(i + count for i in reversed(t)) for t in faces]
    for a, b in edges:
        i, j = idx[tuple(vertices[a])], idx[tuple(vertices[b])]
        polygons.append((i, j, j + count, i + count))
    m = bpy.data.meshes.new(name)
    m.from_pydata([place(x, y, z) for z in thickness for x, y in v], [], polygons)
    m.update()
    obj = bpy.data.objects.new(name, m)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def material(name, rgb, metal, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    node = m.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*rgb, 1)
    node.inputs["Metallic"].default_value = metal
    node.inputs["Roughness"].default_value = rough
    return m


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    work = bpy.data.collections.new(collection)
    bpy.context.scene.collection.children.link(work)
    grey = material("Z 8 · charcoal enamel carrier", (0.008, 0.009, 0.010), 0.27, 0.36)
    metal = material("Z 8 · satin plated alloy", (0.67, 0.69, 0.68), 0.62, 0.31)
    ink = material("Z 8 · light grey shoulder ink", (0.64, 0.65, 0.63), 0.04, 0.55)

    def front(px, py, lift):
        u = (px - 244.5) * 0.028
        v = (164 - py) * 0.028
        d = (
            17.723
            - 0.108 * u
            - 0.0033 * u * u
            - (0.090 * v if v > -0.38 else -0.0342 + 0.015 * (v + 0.38))
        )
        return ((54 + u) * 0.001, -(d + lift) * 0.001, (30.3 + v) * 0.001)

    def top(px, py, lift):
        return (
            (-59.38 - (px - 241.5) * 0.0195) * 0.001,
            (18.78 + (py - 163.5) * 0.0195) * 0.001,
            (42.975 + lift) * 0.001,
        )

    silhouette("Front · enamel Z-shaped seat", [carrier], (-0.12, 0.09), front, grey)
    silver = silhouette(
        "Front · open-diagonal satin Z", [outline, window], (0.075, 0.28), front, metal
    )
    bevel = silver.modifiers.new("Coined edge", "BEVEL")
    bevel.width = 0.000032
    bevel.segments = 3
    bpy.context.view_layer.objects.active = silver
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    silhouette(
        "Shoulder · double-stroke Z", [outline, window], (0.008, 0.032), top, ink
    )
    curve = bpy.data.curves.new("Shoulder model numeral", "FONT")
    curve.body = "8"
    curve.resolution_u = 10
    obj = bpy.data.objects.new("Shoulder · eight", curve)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    mins = [min(v.co[i] for v in obj.data.vertices) for i in range(2)]
    maxs = [max(v.co[i] for v in obj.data.vertices) for i in range(2)]
    for v in obj.data.vertices:
        u, h = [(v.co[i] - mins[i]) / (maxs[i] - mins[i]) for i in range(2)]
        v.co = ((-61.91 - u * 1.22) * 0.001, (20.31 - h * 1.69) * 0.001, 0.043007)
    obj.data.materials.append(ink)
    for part in list(bpy.context.scene.objects):
        for old in list(part.users_collection):
            old.objects.unlink(part)
        work.objects.link(part)
        part["studioOccluder"] = False
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)


if __name__ == "__main__":
    build()
