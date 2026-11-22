import argparse
import gzip
import math
import random
import struct
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import export_batch, xyz
from kinto_luna import build_vase, export_sections

parts = defaultdict(list)
rng = random.Random(73537)
tau = math.tau
up = Vector((0, 1, 0))


def mesh(name, key, vertices, faces, tex=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(v) for v in vertices], [], faces)
    data.update()
    for poly in data.polygons:
        poly.use_smooth = True
    if tex:
        uv = data.uv_layers.new()
        for poly in data.polygons:
            for loop in poly.loop_indices:
                uv.data[loop].uv = tex[data.loops[loop].vertex_index]
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    parts[key].append(obj)
    return obj


def strand(name, key, points, radii, steps=4, sides=8):
    path = [Vector(p) for p in points]
    data = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        before = path[max(0, i - 1)]
        after = path[min(len(path) - 1, i + 2)]
        for j in range(steps):
            t = j / steps
            position = (
                2 * a
                + (-before + b) * t
                + (2 * before - 5 * a + 4 * b - after) * t * t
                + (-before + 3 * a - 3 * b + after) * t * t * t
            ) * 0.5
            data.append((position, radii[i] + (radii[i + 1] - radii[i]) * t))
    data.append((path[-1], radii[-1]))
    vertices = []
    faces = []
    axis = None
    for i, (p, r) in enumerate(data):
        tangent = (
            data[min(i + 1, len(data) - 1)][0] - data[max(i - 1, 0)][0]
        ).normalized()
        if axis is None:
            axis = tangent.cross(
                up if abs(tangent.dot(up)) < 0.94 else Vector((1, 0, 0))
            ).normalized()
        axis = (axis - tangent * axis.dot(tangent)).normalized()
        cross = tangent.cross(axis).normalized()
        for j in range(sides):
            a = tau * j / sides
            vertices.append(p + r * (axis * math.cos(a) + cross * math.sin(a)))
            if i:
                k = i * sides + j
                m = i * sides + (j + 1) % sides
                faces.append((k - sides, m - sides, m, k))
    faces.extend(
        [
            tuple(reversed(range(sides))),
            tuple(range(len(vertices) - sides, len(vertices))),
        ]
    )
    return mesh(name, key, vertices, faces)


def turned(name, key, profile, ripple=0):
    vertices = []
    faces = []
    uv = []
    n = 64
    for j, (h, r) in enumerate(profile):
        for i in range(n + 1):
            a = i * tau / n
            rad = r * (
                1
                + ripple
                * (
                    0.55 * math.sin(3 * a + 0.02 * h)
                    + 0.32 * math.sin(5 * a - 0.019 * h)
                    + 0.14 * math.cos(7 * a)
                )
            )
            vertices.append((rad * math.cos(a), h, rad * math.sin(a)))
            uv.append((i / n, h / 100))
            if i and j:
                k = j * (n + 1) + i
                faces.append((k - n - 2, k - 1, k, k - n - 1))
    return mesh(name, key, vertices, faces, uv)


def bead(name, key, center, radii, rotation=0, rough=0, rings=6, sides=10):
    center = Vector(center)
    verts = []
    faces = []
    for j in range(rings + 1):
        lat = math.pi * (j / rings - 0.5)
        for i in range(sides):
            a = tau * i / sides
            k = 1 + rough * (
                math.sin(a * 3 + lat * 1.2) + 0.5 * math.cos(a * 5 - lat * 2.1)
            )
            x = math.cos(lat) * math.cos(a) * radii[0] * k
            z = math.cos(lat) * math.sin(a) * radii[2] * k
            verts.append(
                center
                + Vector(
                    (
                        x * math.cos(rotation) - z * math.sin(rotation),
                        radii[1] * math.sin(lat) * k,
                        x * math.sin(rotation) + z * math.cos(rotation),
                    )
                )
            )
            if j:
                p = j * sides + i
                q = j * sides + (i + 1) % sides
                faces.append((p - sides, p, q, q - sides))
    return mesh(name, key, verts, faces)


def pot():
    turned(
        "Low catcher with concave well",
        "clay",
        [
            (0.2, 0.2),
            (0.2, 47),
            (0.4, 49.5),
            (2, 51.5),
            (3, 54),
            (6.8, 58.5),
            (9.1, 59.6),
            (10.2, 59.2),
            (10.5, 58.1),
            (10.05, 56.9),
            (7.3, 54.6),
            (5, 51),
            (4.5, 47),
            (4.5, 0.2),
        ],
        0.005,
    )
    turned(
        "Trimmed unglazed foot and lower earthenware",
        "clay",
        [
            (4.5, 3.8),
            (4.5, 39),
            (4.9, 40.1),
            (7, 40.6),
            (8.8, 40.4),
            (9.2, 41.9),
            (11, 43.1),
            (16, 44.5),
            (30, 47.4),
            (46, 50.1),
            (60, 52.9),
            (63.1, 53.4),
        ],
        0.007,
    )
    turned(
        "Olive ash glaze with returned lip",
        "glaze",
        [
            (61.3, 53.2),
            (62.4, 53.7),
            (66, 54.2),
            (74, 55.2),
            (81.5, 56),
            (85.5, 56.7),
            (88, 57.2),
            (89.2, 57.05),
            (90, 56.35),
            (90.24, 55.05),
            (89.7, 54.1),
            (88.3, 53.7),
            (82, 53.2),
            (71, 51.7),
            (65.3, 50.7),
        ],
        0.006,
    )
    vertices = []
    faces = []
    n = 44
    for j in range(8):
        for i in range(n):
            a = tau * i / n
            r = 52.2 * j / 7
            h = (
                80.3
                + 1.4 * math.sin(a * 2 + r * 0.09)
                + 1.1 * math.cos(a * 3 + r * 0.12)
                + 0.45 * math.sin(5 * a + r)
                + 0.5 * (j / 7) ** 3
            )
            vertices.append((r * math.cos(a), h, r * math.sin(a)))
            if j:
                k = j * n + i
                q = j * n + (i + 1) % n
                faces.append((k - n, q - n, q, k))
    mesh("Uneven potting medium", "soil", vertices, faces)
    for i in range(63):
        a = rng.random() * tau
        r = 50 * rng.random() ** 0.5
        x, z = r * math.cos(a), r * math.sin(a)
        h = 81.15 + 1.4 * math.sin(a * 2 + r * 0.09) + 1.1 * math.cos(a * 3 + r * 0.12)
        bead(
            "Bark chip" if i % 6 else "Porous perlite",
            "bark" if i % 6 else "grit",
            (x, h, z),
            (rng.uniform(0.9, 3.2), rng.uniform(0.7, 1.8), rng.uniform(1.2, 4.5)),
            a,
            0.24,
            3,
            6,
        )


def curve_interp(values, t):
    for i in range(1, len(values)):
        a, lo = values[i - 1]
        b, hi = values[i]
        if t <= b:
            f = (t - a) / (b - a)
            return lo + (hi - lo) * f
    return values[-1][1]


def heartleaf(origin, azimuth, length, hwidth, droop, twist, stage):
    origin = Vector(origin)
    out = Vector((math.cos(azimuth), 0, math.sin(azimuth)))
    side = out.cross(up).normalized()
    phase = rng.random() * tau
    lean = rng.uniform(-0.09, 0.09)

    def surface(t, u):
        width = curve_interp(
            [
                (0, 0.65),
                (0.06, 0.84),
                (0.17, 0.982),
                (0.28, 1),
                (0.43, 0.94),
                (0.58, 0.76),
                (0.73, 0.51),
                (0.85, 0.31),
                (0.94, 0.114),
                (1, 0.006),
            ],
            t,
        )
        lobe = (0.19 * math.sin(math.pi * abs(u)) ** 1.2 - 0.026 * u * u) * (1 - t) ** 4
        axis = length * (t - lobe)
        across = (
            u
            * width
            * hwidth
            * (1 + lean * u + 0.026 * math.sin(4 * math.pi * t + phase) * u)
        )
        angle = twist * (t - 0.32) + 0.12 * math.sin(math.pi * t + phase)
        travel = axis * (0.82 - 0.18 * droop * t)
        drop = length * (0.205 * math.sin(math.pi * t) - droop * t**1.55)
        cup = hwidth * (0.19 * abs(u) ** 1.45 - 0.24 * abs(u) ** 4) * width
        ripple = hwidth * 0.028 * u * u * math.sin(t * math.pi * 4 + phase) * width
        rib_radius = 0.63 * (1 - t) ** 0.82 + 0.04
        rib = rib_radius * math.exp(-0.69 * (across / rib_radius) ** 2)
        lateral = side * math.cos(angle) + up * math.sin(angle)
        return (
            origin
            + out * (travel + across * 0.035 * u)
            + up * (drop + cup + ripple + rib)
            + lateral * across
            + side * length * lean * t * t
        )

    vertices = []
    faces = []
    uv = []
    rows, cols = 17, 16
    for j in range(rows + 1):
        t = j / rows
        for i in range(cols + 1):
            signed = i / cols * 2 - 1
            u = math.copysign(abs(signed) ** 1.8, signed)
            vertices.append(surface(t, u))
            uv.append((0.5 + 0.5 * u, 1 - t))
            if j and i:
                k = j * (cols + 1) + i
                faces.append((k - cols - 2, k - cols - 1, k, k - 1))
    mesh("Cordate blade with recurved acumen", "leaf-" + stage, vertices, faces, uv)


def foliage():
    vines = [
        (
            [
                (-14, 76, -3),
                (-19, 105, -5),
                (-27, 129, -6),
                (-24, 154, 2),
                (-32, 178, 11),
                (-22, 196, 20),
            ],
            [
                (1, 185, 64, 24, 0.53),
                (2, 275, 80, 33, 0.59),
                (3, 134, 83, 34, 0.37),
                (4, 238, 75, 31, 0.39),
                (5, 132, 60, 24, 0.19),
            ],
        ),
        (
            [
                (1, 77, 9),
                (2, 103, 13),
                (14, 126, 22),
                (22, 149, 26),
                (32, 169, 34),
                (38, 182, 42),
            ],
            [
                (1, 79, 83, 33, 0.64),
                (2, 4, 90, 35, 0.67),
                (3, 102, 87, 36, 0.49),
                (4, 31, 79, 32, 0.44),
                (5, 82, 65, 24, 0.27),
            ],
        ),
        (
            [
                (-5, 78, -12),
                (0, 100, -18),
                (8, 115, -35),
                (24, 126, -50),
                (39, 116, -64),
                (49, 98, -69),
            ],
            [
                (1, 230, 71, 29, 0.55),
                (2, 300, 77, 31, 0.49),
                (3, 209, 76, 32, 0.59),
                (4, 320, 75, 29, 0.76),
                (5, 29, 61, 26, 0.83),
            ],
        ),
        (
            [
                (10, 78, 1),
                (14, 97, 2),
                (24, 112, -3),
                (36, 127, -3),
                (40, 146, -10),
                (43, 156, -14),
            ],
            [
                (2, 51, 74, 28, 0.52),
                (3, 152, 71, 29, 0.48),
                (4, 341, 79, 30, 0.48),
                (5, 275, 59, 22, 0.28),
            ],
        ),
    ]
    for points, leaves in vines:
        strand(
            "Pliant main vine",
            "petiole",
            points,
            [2.55, 2.2, 1.95, 1.6, 1.31, 0.85],
            4,
            8,
        )
        for j, angle, length, width, droop in leaves:
            n = Vector(points[j])
            a = math.radians(angle)
            heading = Vector((math.cos(a), 0, math.sin(a)))
            reach = rng.uniform(16, 27)
            insertion = n + heading * reach + up * rng.uniform(16, 30)
            neck = insertion - heading * 2 - up * 1.5
            strand(
                "Sheathed petiole with swollen geniculum",
                "petiole",
                [
                    n,
                    n + heading * 4 + up * 3,
                    n + heading * (reach * 0.63) + up * 12,
                    neck,
                    insertion,
                ],
                [1.64, 1.49, 1.06, 1.11, 0.81],
                3,
                7,
            )
            if j in (2, 4):
                start = n - heading * 1.3 + up * 2
                strand(
                    "Papery cataphyll and aerial-root nub",
                    "bark",
                    [
                        start,
                        start - heading * 2 + up * 0.4,
                        start - heading * 3.2 - up * 3.7,
                    ],
                    [1.15, 0.87, 0.28],
                    3,
                    7,
                )
            stage = (
                "young"
                if j == len(points) - 1
                else "olive"
                if rng.random() < 0.35
                else "green"
            )
            heartleaf(
                insertion, a, length, width, droop, rng.uniform(-0.56, 0.54), stage
            )


def blossom(center, face, radius, closed=False):
    center = Vector(center)
    face = Vector(face).normalized()
    side = face.cross(up).normalized()
    vertical = side.cross(face).normalized()
    bead("Green receptacle", "q-sepal", center - face * 2.1, (2.6, 2.8, 2.7), 0, 0.05)
    start = rng.random() * tau
    phase = rng.random() * tau
    for j in range(5):
        a = start + j * tau / 5
        radial = side * math.cos(a) + vertical * math.sin(a)
        tangent = face.cross(radial)
        size = radius * rng.uniform(0.9, 1.06)
        verts = []
        faces = []
        uv = []
        for row in range(10):
            t = row / 9
            width = size * 0.63 * (math.sin(math.pi * (0.012 + 0.975 * t)) ** 0.56)
            for col in range(11):
                u = col / 5 - 1
                r = (t * (0.6 if closed else 0.98) + 0.10 * (1 - u * u) * t**3) * size
                depth = size * (
                    0.24 * t
                    + 0.27 * t * t
                    + (0.43 * t * t if closed else 0)
                    + 0.17 * u * u * math.sin(math.pi * t)
                )
                p = (
                    center
                    + radial * r
                    + tangent * (u * width)
                    + face * (depth + 0.35 * math.sin(phase + j + u * 2 + t * 4))
                )
                verts.append(p)
                uv.append(((u + 1) / 2, 1 - t))
                if row and col:
                    k = row * 11 + col
                    faces.append((k - 12, k - 1, k, k - 11))
        mesh("Cupped quince petal", "q-blush" if j % 3 else "q-rose", verts, faces, uv)
    for i in range(18 if not closed else 10):
        a = tau * i / 18 + rng.uniform(-0.2, 0.2)
        length = radius * rng.uniform(0.34, 0.58)
        direction = side * math.cos(a) + vertical * math.sin(a)
        stem = center + direction * 1.2
        tip = center + direction * length * 0.52 + face * length
        strand(
            "Quince filament",
            "q-filament",
            [stem, stem + face * length * 0.55 + direction * 0.8, tip],
            [0.18, 0.135, 0.095],
            1,
            4,
        )
        bead("Golden anther", "q-pollen", tip, (0.48, 0.37, 0.58), a, 0.04, 2, 6)


def quince():
    twig = [
        (-9, 5, 4),
        (-5, 43, 2),
        (0, 69, 0),
        (6, 101, -3),
        (10, 133, -11),
        (5, 167, -17),
        (12, 195, -20),
        (21, 221, -33),
        (20, 252, -44),
        (30, 276, -48),
    ]
    strand(
        "Cut stem through the brass flower frog",
        "q-wood",
        twig,
        [2.45, 2.38, 2.26, 2.10, 1.91, 1.61, 1.48, 1.10, 0.95, 0.58],
        4,
        11,
    )
    sprays = [
        (
            [
                (9, 128, -10),
                (-2, 144, -5),
                (-15, 155, 0),
                (-22, 170, 4),
                (-35, 184, 2),
                (-46, 198, 8),
            ],
            [1.55, 1.37, 1.14, 0.99, 0.76, 0.43],
        ),
        (
            [
                (7, 171, -17),
                (16, 181, -11),
                (29, 187, -8),
                (40, 197, -10),
                (48, 211, -8),
            ],
            [1.34, 1.21, 1.06, 0.80, 0.45],
        ),
        (
            [(18, 216, -31), (8, 225, -42), (0, 240, -52), (-5, 253, -57)],
            [1.10, 0.86, 0.63, 0.32],
        ),
    ]
    for path, sizes in sprays:
        strand("Short woody lateral spur", "q-wood", path, sizes, 4, 9)
    blossoms = [
        ((-18, 164, 2), (0.76, 0.44, 0.38), 13, False),
        ((-34, 183, 3), (0.6, 0.04, -0.8), 12.8, False),
        ((36, 194, -9), (0.91, 0.25, 0.2), 14.5, False),
        ((11, 195, -20), (0.1, 0.77, 0.65), 10, True),
        ((18, 241, -40), (0.82, 0.4, -0.48), 12.7, False),
        ((-1, 242, -51), (0.7, 0.65, 0.25), 9, True),
    ]
    for pos, normal, r, closed in blossoms:
        tip = Vector(pos) + Vector(normal).normalized() * 3.8
        strand("Flower pedicel", "q-sepal", [pos, tip], [1, 0.72], 2, 7)
        blossom(tip, normal, r, closed)
    for i, p in enumerate(
        [
            (-46, 198, 8),
            (-22, 170, 4),
            (48, 211, -8),
            (20, 252, -44),
            (30, 276, -48),
            (-5, 253, -57),
            (7, 168, -17),
        ]
    ):
        p = Vector(p)
        tilt = Vector(
            (rng.uniform(-0.6, 0.6), 0.7, rng.uniform(-0.5, 0.5))
        ).normalized()
        bead(
            "Closed blush bud",
            "q-rose",
            p + tilt * 2.8,
            (2.8, 3.9, 2.75),
            0,
            0.035,
            7,
            10,
        )
        bead("Persistent calyx", "q-sepal", p + tilt * 0.9, (1.9, 2.2, 1.9), 0, 0.035)
    for point in twig[3:-1]:
        q = Vector(point) + Vector((1.4, 1, 0))
        bead("Bark lenticel", "q-sepal", q, (0.37, 0.8, 0.63), 0.25, 0.2, 3, 6)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path)
    parser.add_argument(
        "--out", type=Path, default=Path("public/media/models/sill-botanicals.mesh.gz")
    )
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pot()
    foliage()
    quince()
    vessel = build_vase()
    export_sections(vessel, Path(__file__).resolve().parents[2] / "src/scene/kinto-luna-sections.json")
    parts["v-mark"] = vessel["v-mark"]
    bpy.context.view_layer.update()
    bundle = bytearray(b"BPK1")
    with tempfile.TemporaryDirectory() as tmp:
        for key, items in parts.items():
            path = Path(tmp) / (key + ".mesh")
            report = export_batch(key, items, path)
            data = path.read_bytes()
            name = key.encode("ascii")
            bundle.extend(struct.pack("<BI", len(name), len(data)) + name + data)
            print(key, report, flush=True)
    args.out.write_bytes(gzip.compress(bundle, 9, mtime=0))
    if args.blend:
        parts.update(vessel)
        for key, items in parts.items():
            if key.startswith(("q-", "v-")):
                for obj in items:
                    obj.location += xyz((0, 0, 420))
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))


if __name__ == "__main__":
    main()
