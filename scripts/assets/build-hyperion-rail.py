import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mesh import write_mesh


def make_casting():
    stations = [
        (116.5, 302, -318, 13.3, 13, 0),
        (117.4, 303, -308, 14.1, 13.8, 0),
        (117.4, 303.8, -276, 14.1, 13.8, 0.1),
        (117.4, 304.1, -222, 14, 13.5, 0.85),
        (117.4, 304.1, 107, 14, 13.5, 0.85),
        (117.4, 304, 164, 14.2, 13.8, 0.1),
        (117.3, 303.4, 182, 14.4, 14.2, 0),
        (115.5, 300, 195, 14.8, 14.6, 0),
        (111.6, 290, 204, 15, 14.8, 0),
        (101.8, 266, 217, 14.4, 14.8, 0),
        (47, 143, 276, 13.7, 15.9, 0),
        (17.2, 83.5, 305, 11, 15.2, 0),
        (11.1, 71.3, 310.1, 9, 14.7, 0),
        (9.8, 62.7, 311.8, 8.5, 14.4, 0),
        (9.8, 51, 312, 8.5, 14.4, 0),
        (9.8, -51, 312, 8.5, 14.4, 0),
        (9.8, -62.7, 311.8, 8.5, 14.4, 0),
        (11.1, -71.3, 310.1, 9, 14.7, 0),
        (17.2, -83.5, 305, 11, 15.2, 0),
        (47, -143, 276, 13.7, 15.9, 0),
        (101.8, -266, 217, 14.4, 14.8, 0),
        (111.6, -290, 204, 15, 14.8, 0),
        (115.5, -300, 195, 14.8, 14.6, 0),
        (117.3, -303.4, 182, 14.4, 14.2, 0),
        (117.4, -304, 164, 14.2, 13.8, 0),
        (117.4, -304, -272, 14.1, 13.8, 0),
        (117.4, -303.4, -308, 14.1, 13.8, 0),
        (116.5, -302, -318, 13.3, 13, 0),
    ]
    centers = [Vector(s[:3]) * 0.001 for s in stations]
    tangents = []
    for i, point in enumerate(centers):
        before = (point - centers[max(i - 1, 0)]).normalized()
        after = (centers[min(i + 1, len(centers) - 1)] - point).normalized()
        tangents.append((before + after).normalized())
    sections = []
    for i, (a, b) in enumerate(zip(centers, centers[1:])):
        length = (a - b).length
        count = max(1, min(5, math.ceil(length / 0.045)))
        for j in range(count):
            t = j / count
            h = t * t * (3 - 2 * t)
            point = (
                a * (1 - h)
                + b * h
                + length
                * (t * (1 - t) ** 2 * tangents[i] - t * t * (1 - t) * tangents[i + 1])
            )
            shape = [
                s + (e - s) * h for s, e in zip(stations[i][3:], stations[i + 1][3:])
            ]
            sections.append((point, *shape))
    sections.append((centers[-1], *stations[-1][3:]))
    vertices, faces, distance = [], [], [0.0]
    for i, (point, width, depth, grip) in enumerate(sections):
        tangent = (
            sections[min(i + 1, len(sections) - 1)][0] - sections[max(0, i - 1)][0]
        ).normalized()
        across = Vector((1, 0, 0))
        across = (across - across.dot(tangent) * tangent).normalized()
        outside = tangent.cross(across)
        contour = [
            (-0.85, -0.90),
            (-0.64, -0.99),
            (-0.47, -0.99 + 0.32 * grip),
            (0.37, -0.99 + 0.32 * grip),
            (0.64, -0.99),
            (0.86, -0.92),
            (0.99, -0.69),
            (1, 0.57),
            (0.79, 0.86),
            (0.60, 0.985),
            (-0.49, 1),
            (-0.88, 0.78),
            (-1, 0.52),
            (-1, -0.63),
        ]
        for u, v in contour:
            p = point + (0.001 * width * u) * across + (0.001 * depth * v) * outside
            vertices.append((p.x, -p.z, p.y))
        n = len(contour)
        if i:
            distance.append(distance[-1] + (point - sections[i - 1][0]).length)
            for k in range(n):
                prev = (i - 1) * n
                faces.append(
                    (prev + k, prev + (k + 1) % n, prev + n + (k + 1) % n, prev + n + k)
                )
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple(range(len(vertices) - n, len(vertices))))
    data = bpy.data.meshes.new("GR701 variable casting sections")
    data.from_pydata(vertices, [], faces)
    data.update()
    casting = bpy.data.objects.new("Hyperion load-bearing casting", data)
    bpy.context.collection.objects.link(casting)
    uv = data.uv_layers.new(name="Brushed along casting")
    for poly in data.polygons:
        poly.use_smooth = True
        for loop in poly.loop_indices:
            row, col = divmod(data.loops[loop].vertex_index, n)
            uv.uv[loop].vector = (col / n, distance[row] / distance[-1])
    bevel = casting.modifiers.new("Die parting edges and soft-touch bevel", "BEVEL")
    bevel.width = 0.00115
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(18)
    bevel.harden_normals = True
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0351, -0.2195, -0.153))
    relief = bpy.context.object
    relief.dimensions = (0.0702, 0.0263, 0.1405)
    bpy.context.view_layer.objects.active = casting
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    pocket = casting.modifiers.new("Lower intake fan installation pocket", "BOOLEAN")
    pocket.operation = "DIFFERENCE"
    pocket.object = relief
    bpy.ops.object.modifier_apply(modifier=pocket.name)
    bpy.data.objects.remove(relief, do_unlink=True)
    normal = casting.modifiers.new("Broad cast face normals", "WEIGHTED_NORMAL")
    normal.weight = 45
    normal.keep_sharp = True
    return casting


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out", type=Path, default=Path("public/media/models/gr701-rail.mesh")
    )
    parser.add_argument("--blend", type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    casting = make_casting()
    bpy.context.view_layer.update()
    print(write_mesh(casting, args.out))
    if args.blend:
        twin = casting.copy()
        twin.name = "Hyperion load-bearing casting · opposite side"
        twin.scale.x = -1
        bpy.context.collection.objects.link(twin)
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))


if __name__ == "__main__":
    main()
