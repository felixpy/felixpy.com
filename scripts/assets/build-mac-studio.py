import math
import runpy
import subprocess
from pathlib import Path
from functools import lru_cache

import bpy
import numpy as np
from io_scene_gltf2.io.exp import meshopt
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt, interpolate_bezier


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
review = root / ".review/atelier"
bpy.ops.wm.read_factory_settings(use_empty=True)
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
tools = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))
slab, corners = tools["slab"], tools["corners"]
aluminium = finish("Bead blasted aluminum", "d4d5d6", 0.70, 0.41)
cut = finish("Chamfered port lip", "a6a8a8", 0.78, 0.33)
ink = finish("Laser etch", "646668", 0.32, 0.49)
polymer = finish("Glass-filled nylon", "222425", 0.05, 0.55)
shadow = finish("Port lining", "121415", 0.03, 0.69)
bore = finish("Shadowed vent bore", "474b4c", 0.30, 0.62)
metal = finish("Nickel plated shell", "b0b1af", 0.85, 0.31)
gold = finish("Plated contacts", "b99f62", 0.72, 0.38)
pcb = finish("Graphite solder mask", "30302e", 0.16, 0.61)
seal = finish("Non-slip foot", "393a39", 0.03, 0.83)
mark = finish("Polished black inlay", "242424", 0.45, 0.17, 0.65)
white = finish("Status light", "fbf9ee", 0.04, 0.40, 0, 0.32)
assembled = []
compact = False
vent_coverage = Sculpture("Screen filtered intake and exhaust")


@lru_cache(maxsize=1)
def rear_etch():
    w, h = 2048, 64
    ss = 3
    coverage = np.zeros((ss * h, ss * w), dtype=np.bool_)

    def fill(points):
        poly = np.asarray(points)
        x0, x1 = (
            np.clip(
                np.floor((poly[:, 0].min() + 69) / 138 * w * ss).astype(int), 0, w * ss
            ),
            np.clip(math.ceil((poly[:, 0].max() + 69) / 138 * w * ss), 0, w * ss),
        )
        y0, y1 = (
            max(0, math.floor((poly[:, 1].min() - 32) / 4 * h * ss)),
            min(h * ss, math.ceil((poly[:, 1].max() - 32) / 4 * h * ss)),
        )
        if x1 <= x0 or y1 <= y0:
            return
        x = (np.arange(x0, x1)[None, :] + 0.5) * 138 / (w * ss) - 69
        y = (np.arange(y0, y1)[:, None] + 0.5) * 4 / (h * ss) + 32
        mask = np.zeros((y1 - y0, x1 - x0), dtype=np.bool_)
        for (a, b), (c, d) in zip(points, points[1:] + points[:1]):
            if b != d:
                mask ^= ((b > y) != (d > y)) & (x < a + (y - b) * (c - a) / (d - b))
        coverage[y0:y1, x0:x1] |= mask

    def polygon(cx, points):
        fill([(cx + x, 34 + y) for x, y in points])

    def stroke(cx, points, weight=0.20):
        for (x, y), (u, v) in zip(points, points[1:]):
            angle = math.atan2(v - y, u - x)
            a, b = -math.sin(angle) * weight * 0.5, math.cos(angle) * weight * 0.5
            polygon(
                cx, [(x + a, y + b), (u + a, v + b), (u - a, v - b), (x - a, y - b)]
            )

    polygon(
        -53,
        [
            (-0.12, 1.35),
            (-1.04, -0.15),
            (-0.22, -0.15),
            (-0.54, -1.45),
            (1.04, 0.30),
            (0.16, 0.30),
            (0.75, 1.35),
        ],
    )
    for side in [-1, 1]:
        stroke(-24.2, [(side * 0.8, 0.83), (side * 1.53, 0), (side * 0.8, -0.83)])
        stroke(-24.2, [(side * 0.3, 0.83), (side * 1.03, 0), (side * 0.3, -0.83)], 0.14)
    stroke(26.9, [(-1.6, 0), (1.45, 0)])
    polygon(26.9, [(1.35, -0.42), (2.0, 0), (1.35, 0.42)])
    stroke(26.9, [(-0.77, 0), (-0.23, 0.69), (0.38, 0.69)])
    stroke(26.9, [(-0.18, 0), (0.40, -0.69), (0.86, -0.69)])
    polygon(26.9, roundhole(-1.55, 0, 0.34))
    polygon(26.9, roundhole(0.41, 0.69, 0.24))
    polygon(26.9, [(0.64, -0.91), (1.06, -0.91), (1.06, -0.47), (0.64, -0.47)])
    points, triangles = sculpt["letters"]("HDMI", True)
    for tri in triangles:
        polygon(50.4, [(points[i][0] * 2.9, points[i][1] * 2.9) for i in tri])
    stroke(
        67.1,
        [
            (
                1.10 * math.cos(i * math.pi / 20),
                0.10 + 1.10 * math.sin(i * math.pi / 20),
            )
            for i in range(21)
        ],
    )
    for x in [-0.93, 0.93]:
        polygon(67.1, oblong(x, -0.43, 0.50, 1.20, 0.18))

    alpha = coverage.reshape(h, ss, w, ss).mean(axis=(1, 3))[..., None]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = (
        (1 - alpha) * np.array([212, 213, 214]) + alpha * np.array([83, 85, 86])
    ) / 255
    image = bpy.data.images.new("Laser etched I/O key", width=w, height=h)
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    mat = finish("Laser etched aluminum", "ffffff", 0.70, 0.41)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "EXTEND"
    mat.node_tree.links.new(
        tex.outputs["Color"],
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    return mat


@lru_cache(maxsize=2)
def vent_finish(width, height, radius):
    name = "Rear vent finish" if radius > 0.6 else "Intake vent finish"
    material = finish(name, "d4d5d6", 0.70, 0.41)
    image = bpy.data.images.new(name, width=64, height=64)
    pixels = []
    for row in range(64):
        for col in range(64):
            x, y = (col - 31.5) * width / 64, (row - 31.5) * height / 64
            r = math.hypot(x, y) / radius
            t = min(1, max(0, (r - 0.91) / 0.12))
            lip = math.exp(-(((r - 0.85) / 0.08) ** 2)) * (0.55 - 0.31 * y / radius)
            pixels.extend(
                [
                    0.26 + (c - 0.26) * t + 0.24 * lip * (1 - t)
                    for c in (0.831, 0.835, 0.839)
                ]
                + [1]
            )
    image.pixels.foreach_set(pixels)
    image.pack()
    nodes = material.node_tree.nodes
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    material.node_tree.links.new(
        texture.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"]
    )
    return material


def publish(part, interior=False):
    obj = part.finalize()
    if hasattr(part, "vent_uv") or rear_etch() in part.materials:
        data = obj.data
        layer = data.uv_layers.new(name="Surface coordinates")
        for polygon in data.polygons:
            if data.materials[polygon.material_index] == rear_etch():
                for index in polygon.loop_indices:
                    p = data.vertices[data.loops[index].vertex_index].co
                    layer.data[index].uv = (
                        (69 - 1000 * p.x) / 138,
                        (1000 * p.z - 32) / 4,
                    )
                continue
            if data.materials[polygon.material_index].name not in (
                "Rear vent finish",
                "Intake vent finish",
            ):
                continue
            for index in polygon.loop_indices:
                layer.data[index].uv = part.vent_uv[data.loops[index].vertex_index]
    if not interior:
        assembled.append(obj)
    return obj


def roundhole(x, y, r, n=20):
    return [
        (x + r * math.cos(i * math.tau / n), y + r * math.sin(i * math.tau / n))
        for i in range(n)
    ]


def oblong(x, y, w, h, r):
    return [(x + a, y + b) for a, b in corners(w, h, r)]


def cap(part, outline, project, material):
    part.add(
        [project(x, y) for x, y in outline],
        [tuple(range(len(outline)))],
        material,
        False,
    )


def bored(part, edge, holes, project, material, interior_points=()):
    flat, loops = [], []
    for ring in [edge, *holes]:
        area = sum(x * b - a * y for (x, y), (a, b) in zip(ring, ring[1:] + ring[:1]))
        ring = ring if area > 0 else list(reversed(ring))
        loops.append(list(range(len(flat), len(flat) + len(ring))))
        flat.extend(Vector(p) for p in ring)
    flat.extend(Vector(p) for p in interior_points)
    vertices, _, tris, _, _, ids = delaunay_2d_cdt(flat, [], loops, 0, 0.00001)
    selected = [tri for tri, owners in zip(tris, ids) if set(owners) == {0}]
    part.add([project(v.x, v.y) for v in vertices], selected, material, False)


radius, flat = 29.5, 69.0
bend = math.pi * radius / 2
extent = 2 * flat + bend


def skin(s, h, side, depth=0):
    arc = max(0, min(bend, abs(s) - flat)) / radius
    along = min(abs(s), flat) + (radius - depth) * math.sin(arc)
    z = flat + (radius - depth) * math.cos(arc) - max(0, abs(s) - flat - bend)
    return (side * math.copysign(along, s), h, side * z)


def developed(x):
    return (
        math.copysign(flat + radius * math.asin((abs(x) - flat) / radius), x)
        if abs(x) > flat
        else x
    )


def section_face(part, start, end, h0, h1, side, grilles=()):
    if end - start < 0.001:
        return
    edge = [(start, h0), (end, h0), (end, h1), (start, h1)]
    holes = [ring for ring in grilles if start < ring[0][0] < end]
    if holes:
        curve_samples = [
            (s, y)
            for s in range(math.ceil(start), math.ceil(end), 1)
            if flat < abs(s) < flat + bend
            for y in (h0, h0 + 2, h0 + 5, (h0 + h1) * 0.5, h1 - 5, h1 - 2, h1)
        ]
        bored(
            part, edge, holes, lambda x, y: skin(x, y, side), aluminium, curve_samples
        )
    else:
        finish = (
            rear_etch()
            if side == -1
            and h0 == 32
            and h1 == 36
            and max(abs(start), abs(end)) <= flat
            else aluminium
        )
        cap(part, edge, lambda x, y: skin(x, y, side), finish)


def slotted_tile(part, bounds, opening, project, material, r, n=12):
    x0, y0, x1, y1 = bounds
    x, y = opening
    corners = [(x1, y1), (x0, y1), (x0, y0), (x1, y0)]
    coverage = part if compact else vent_coverage
    if not hasattr(coverage, "vent_uv"):
        coverage.vent_uv = {}
    for i, uv in enumerate([(1, 1), (0, 1), (0, 0), (1, 0)], len(coverage.vertices)):
        coverage.vent_uv[i] = uv
    coverage.add(
        [project(a, b, 0) for a, b in corners],
        [(0, 1, 2, 3)],
        vent_finish(round(x1 - x0, 4), round(y1 - y0, 4), r),
        False,
    )
    if compact:
        return
    ring = []
    for i in range(n):
        edge, fraction = divmod(i * 4, n)
        a, b = corners[edge], corners[(edge + 1) % 4]
        ring.append(tuple(a[j] + (b[j] - a[j]) * fraction / n for j in (0, 1)))
    inner = [
        (
            x + r * math.cos(math.pi / 4 + i * math.tau / n),
            y + r * math.sin(math.pi / 4 + i * math.tau / n),
        )
        for i in range(n)
    ]
    part.rings(
        [[project(a, b, 0) for a, b in ring], [project(a, b, 0) for a, b in inner]],
        material,
        False,
        False,
    )
    part.rings(
        [
            [project(x + (a - x) * k, y + (b - y) * k, d) for a, b in inner]
            for k, d in [(1, 0), (0.88, 0.16), (0.88, 1.15)]
        ],
        bore,
        True,
        False,
    )


def port_opening(kind, x, y, w, h):
    if kind == "AC":
        points = []
        for (ox, oy), start, end in [
            ((5.2, 2.4), -84, 140),
            ((-5.2, 2.4), 40, 264),
            ((0, -2.75), 191, 349),
        ]:
            for k in range(17):
                a = math.radians(start + (end - start) * k / 16)
                points.append((x + ox + 5.9 * math.cos(a), y + oy + 5.9 * math.sin(a)))
        return points
    if kind == "HDMI":
        return [
            (x + a * w, y + b * h)
            for a, b in [
                (-0.48, 0.5),
                (0.48, 0.5),
                (0.5, 0.40),
                (0.5, -0.12),
                (0.31, -0.49),
                (-0.31, -0.49),
                (-0.5, -0.12),
                (-0.5, 0.40),
            ]
        ]
    r = min(w, h) * 0.49 if kind in ["TB5", "Light", "Power", "Audio", "SDXC"] else 0.62
    return oblong(x, y, w, h, r)


front = [
    ("TB5", -66.5, 2.8, 8.6),
    ("TB5", -51.5, 2.8, 8.6),
    ("SDXC", -24.6, 26.8, 2.6),
    ("Light", 66.5, 2.25, 2.25),
]
back = [("TB5", i, 2.8, 8.6) for i in (-67.5, -57.9, -48.3, -38.7)] + [
    ("Ethernet", -24.2, 12.6, 10.6),
    ("AC", 0, 22.1, 16.7),
    ("USB-A", 20.7, 5.2, 12.6),
    ("USB-A", 33.1, 5.2, 12.6),
    ("HDMI", 50.4, 14.5, 4.9),
    ("Audio", 67.1, 3.8, 3.8),
    ("Power", 80.8, 8.9, 8.9),
]


def shell():
    housing = Sculpture("Machined enclosure and perforated rear grille")
    for side, specs in [(1, front), (-1, back)]:
        rings = [
            port_opening(kind, developed(x), 23.2, w, h) for kind, x, w, h in specs
        ]
        half = [0, flat] + [flat + bend * i / 28 for i in range(1, 29)] + [extent]
        intervals = sorted(set(half + [-x for x in half]))
        for a, b in zip(intervals, intervals[1:]):
            section_face(housing, a, b, 8.3, 12.8, side)
            if side == -1:
                section_face(housing, a, b, 32, 36, side)
                section_face(housing, a, b, 36, 40.8, side)
            else:
                section_face(housing, a, b, 34.5, 40.8, side)
            section_face(housing, a, b, 88.8, 94.55, side)
            for lo, hi, base, slope in [
                (8, 8.3, 0.22, -0.22),
                (94.55, 94.85, 0, 0.12),
                (94.85, 95, 0.12, 0.42),
            ]:
                housing.add(
                    [
                        skin(a, lo, side, base),
                        skin(b, lo, side, base),
                        skin(b, hi, side, base + slope),
                        skin(a, hi, side, base + slope),
                    ],
                    [(0, 1, 2, 3)],
                    aluminium,
                    True,
                )
        boundaries = [
            v
            for v in intervals
            if not any(
                min(a for a, _ in r) - 0.01 <= v <= max(a for a, _ in r) + 0.01
                for r in rings
            )
        ]
        for a, b in zip(boundaries, boundaries[1:]):
            section_face(housing, a, b, 12.8, 32 if side == -1 else 34.5, side, rings)
        if side == 1:
            for a, b in zip(intervals, intervals[1:]):
                section_face(housing, a, b, 40.8, 88.8, side)
            continue
        for j in range(27):
            h0 = 40.8 + 48 * j / 27
            h1 = h0 + 48 / 27
            left = (-43.5 + (j % 2) * 0.48) * 1.98
            right = left + 87 * 1.98
            for a, b in zip(intervals, intervals[1:]):
                if a < left:
                    section_face(housing, a, min(b, left), h0, h1, side)
                if b > right:
                    section_face(housing, max(a, right), b, h0, h1, side)
            for i in range(87):
                x0 = left + i * 1.98
                slotted_tile(
                    housing,
                    (x0, h0, x0 + 1.98, h1),
                    (x0 + 0.99, (h0 + h1) / 2),
                    lambda s, h, d: skin(s, h, side, d),
                    aluminium,
                    0.685,
                    8,
                )
    top = corners(197 - 1.08, 197 - 1.08, radius - 0.54, 28)
    cap(housing, top, lambda x, z: (x, 95, z), aluminium)
    bored(
        housing,
        corners(196.56, 196.56, radius - 0.22, 28),
        [roundhole(0, 0, 86.3, 120)],
        lambda x, z: (x, 8, z),
        aluminium,
    )
    data = publish(housing).data
    metal_faces = [
        face
        for face in data.polygons
        if data.materials[face.material_index] in (aluminium, rear_etch())
        or data.materials[face.material_index].name == "Rear vent finish"
    ]

    def outward(point):
        return Vector(
            (
                point.x - max(-0.069, min(0.069, point.x)),
                point.y - max(-0.069, min(0.069, point.y)),
                0,
            )
        )

    for face in metal_faces:
        axis = (
            Vector((0, 0, 1 if face.center.z > 0.09 else -1))
            if abs(face.normal.z) > 0.99
            else outward(face.center)
        )
        if face.normal.dot(axis) < 0:
            face.flip()
    data.update()
    normals = [(0, 0, 0)] * len(data.loops)
    for face in metal_faces:
        if abs(face.normal.z) > 0.03:
            continue
        face.use_smooth = True
        for i in face.loop_indices:
            p = data.vertices[data.loops[i].vertex_index].co
            normals[i] = outward(p).normalized()
    data.normals_split_custom_set(normals)
    logo = Sculpture("Flush black Apple inlay")
    for path in [
        [
            (128, 89),
            (109, 89, 103, 74, 79, 75),
            (35, 76, 12, 113, 15, 158),
            (18, 207, 44, 262, 70, 283),
            (84, 295, 101, 285, 118, 280),
            (135, 274, 145, 276, 161, 282),
            (183, 291, 194, 288, 208, 272),
            (225, 253, 236, 229, 241, 212),
            (215, 198, 205, 178, 205, 157),
            (205, 134, 217, 116, 235, 105),
            (217, 79, 194, 71, 168, 74),
            (150, 76, 139, 88, 128, 89),
        ],
        [(126, 71), (121, 37, 147, 7, 182, 4), (185, 35, 159, 70, 126, 71)],
    ]:
        p = Vector((*path[0], 0))
        points = []
        for a, b, c, d, e, f in path[1:]:
            last = Vector((e, f, 0))
            points.extend(
                (v.x, v.y)
                for v in interpolate_bezier(
                    p, Vector((a, b, 0)), Vector((c, d, 0)), last, 7
                )[:-1]
            )
            p = last
        cap(
            logo,
            points,
            lambda x, y: ((x - 128) * 0.23, 95.035, (y - 146) * 0.23),
            mark,
        )
    publish(logo)


def ports():
    for side, specs in [(1, front), (-1, back)]:
        for kind, offset, w, h in specs:
            u, y = developed(offset), 23.2
            part = Sculpture(
                ("Front" if side == 1 else "Rear") + " " + kind + " " + str(offset)
            )
            ring = port_opening(kind, u, y, w, h)

            def scaled(k, d):
                return [
                    skin(u + (x - u) * k, y + (b - y) * k, side, d) for x, b in ring
                ]

            part.rings(
                [scaled(1, 0), scaled(0.95, 0.38), scaled(0.95, 2.9)], cut, True, False
            )
            part.rings([scaled(0.95, 2.9), scaled(0.90, 6.0)], shadow, False, False)
            part.add(scaled(0.90, 6), [tuple(range(len(ring)))], shadow, False)

            def plate(x, dy, ww, hh, depth, mat, rad=0.15):
                cap(
                    part,
                    oblong(u + x, y + dy, ww, hh, rad),
                    lambda s, b: skin(s, b, side, depth),
                    mat,
                )

            if kind in ("TB5", "USB-A", "HDMI", "SDXC"):
                tw, th = (
                    (0.59, h * 0.78)
                    if kind == "TB5"
                    else (1.0, h * 0.83)
                    if kind == "USB-A"
                    else (w * 0.79, 0.72)
                )
                plate(-0.78 if kind == "USB-A" else 0, 0, tw, th, 1.3, polymer)
                if kind == "USB-A":
                    for j in range(4):
                        plate(-0.68, (j - 1.5) * 2.1, 0.45, 0.64, 1.27, gold)
            elif kind == "Ethernet":
                for i in range(8):
                    part.pipe(
                        [
                            skin(u + (i - 3.5) * 1.07, y - 3.9, side, 1.6),
                            skin(u + (i - 3.5) * 1.07, y - 0.8, side, 5.8),
                        ],
                        0.17,
                        gold,
                        6,
                    )
                plate(0, 3.8, 6.5, 2, 1.6, shadow)
            elif kind == "AC":
                for x, dy in [(-5, 2.3), (5, 2.3), (0, -2.6)]:
                    part.pipe(
                        [skin(u + x, y + dy, side, 5.8), skin(u + x, y + dy, side, 2)],
                        1.36,
                        metal,
                        24,
                    )
            elif kind in ("Light", "Power"):
                part.add(
                    scaled(0.966, 0.25),
                    [tuple(range(len(ring)))],
                    white if kind == "Light" else aluminium,
                    False,
                )
                if kind == "Power":
                    part.pipe(
                        [
                            skin(
                                u + 1.47 * math.sin(a * 0.1),
                                y + 1.47 * math.cos(a * 0.1),
                                side,
                                0.20,
                            )
                            for a in range(6, 58)
                        ],
                        0.13,
                        ink,
                        6,
                    )
                    part.pipe(
                        [skin(u, y + 0.12, side, 0.19), skin(u, y + 2.0, side, 0.19)],
                        0.14,
                        ink,
                        6,
                    )
            publish(part)


def intake():
    part = Sculpture("Conical intake, foot ring and bottom cover")

    def project(s, y, d):
        a = s / 82
        radius = 75 + 11.3 * (y - 1.2) / 6.9 - d
        return (radius * math.sin(a), y, radius * math.cos(a))

    length = math.tau * 82
    for row in range(5):
        for col in range(220):
            x = (col + 0.5 * (row % 2)) * length / 220
            h = 1.2 + row * 1.38
            slotted_tile(
                part,
                (x, h, x + length / 220, h + 1.38),
                (x + length / 440, h + 0.69),
                project,
                aluminium,
                0.48,
                8,
            )
    part.turn([(1.2, 75.0), (0.28, 74.6), (0, 73.1), (0, 62), (0.16, 61.9)], seal, 128)
    cap(part, roundhole(0, 0, 62.05, 100), lambda x, z: (x, 0.18, z), aluminium)
    part.label("Mac Studio", 8.4, lambda x, y: (x, 0.13, y), ink)
    publish(part)


def internals():
    board = Sculpture("Logic board, SSD sockets and I/O flex connectors")
    profile = [
        (-83, -77),
        (-53, -79),
        (-48, -71),
        (-28, -71),
        (-25, -79),
        (69, -79),
        (78, -71),
        (82, -50),
        (82, 68),
        (67, 76),
        (-68, 76),
        (-82, 64),
    ]
    board.rings([[(x, y, z) for x, z in profile] for y in (27.1, 28.45)], pcb, False)
    for x, z in [(-59, -42), (-59, 17), (58, 22), (58, -36)]:
        slab(board, x, z, 15, 12, 0.45, [(28.45, 0), (29.42, 0)], polymer)
    slab(board, 0, -5, 57, 63, 1.3, [(28.45, 0), (29.5, 0)], polymer)
    for x in [-62, 62]:
        slab(board, x, 41, 22.1, 34, 0.9, [(28.58, 0), (29.7, 0)], pcb)
        for z in (33, 48):
            slab(board, x, z, 16, 12, 0.72, [(29.7, 0), (30.7, 0)], polymer)
    publish(board, True)
    ps = Sculpture("Round power supply, insulator and bus bar")
    ps.turn(
        [
            (9.8, 0.1),
            (9.8, 71.8),
            (10.3, 74.2),
            (17.2, 74.1),
            (18.4, 73.2),
            (18.4, 0.1),
        ],
        polymer,
        96,
    )
    for a in range(4):
        t = math.pi * a / 2
        x, z = 73 * math.sin(t), 73 * math.cos(t)
        slab(ps, x, z, 7.3, 7.3, 2.3, [(10, 0), (12.5, 0)], metal)
    slab(ps, -29, -62, 16, 5.3, 1.7, [(11.5, 0), (15.6, 0)], cut)
    publish(ps, True)
    for sign in (-1, 1):
        blower = Sculpture(
            ("Left" if sign == -1 else "Right") + " centrifugal blower and duct"
        )
        x = sign * 43.8
        outer = roundhole(x, 29, 39, 72)
        bored(
            blower, outer, [roundhole(x, 29, 23, 60)], lambda a, b: (a, 84, b), polymer
        )
        blower.rings(
            [[(a, y, b) for a, b in outer] for y in (46, 84)], polymer, True, False
        )
        for i in range(51):
            a = i * math.tau / 51
            row = [
                (x + r * math.cos(a + d), 29 + r * math.sin(a + d))
                for r, d in [
                    (14, 0),
                    (22, 0.08),
                    (32.3, 0.24),
                    (32.3, 0.26),
                    (22, 0.105),
                    (14, 0.05),
                ]
            ]
            blower.rings(
                [[(u, y, v) for u, v in row] for y in (50, 80)], polymer, False
            )
        slab(blower, x, -20, 76, 41, 3.1, [(48, 0), (81, 0)], polymer)
        publish(blower, True)
    sink = Sculpture("Exhaust fin stack")
    slab(sink, 0, -60, 166, 55, 2.0, [(32, 0), (36, 0)], cut)
    for i in range(105):
        x = i * 1.56 - 81
        slab(sink, x, -64, 0.59, 48, 0.15, [(36, 0), (83.1, 0)], bore)
    publish(sink)


def export_product(filename):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in assembled:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = assembled[0]
    bpy.ops.object.join()
    output = root / "public/media/models" / filename
    old = meshopt.EXP_FILTER_BITS
    try:
        meshopt.EXP_FILTER_BITS = 17
        bpy.ops.export_scene.gltf(
            filepath=str(output),
            export_format="GLB",
            use_selection=True,
            export_animations=False,
            export_meshopt_compression_enable=True,
            export_meshopt_extension="EXT_meshopt_compression",
        )
    finally:
        meshopt.EXP_FILTER_BITS = old
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(output)], check=True
    )


def vent_surface_normal(point, rear):
    if rear:
        x = point.x - max(-0.069, min(0.069, point.x))
        return Vector((x, point.y - 0.069, 0)).normalized()
    normal = Vector((point.x, point.y, 0)).normalized()
    normal.z = -11.3 / 6.9
    return normal.normalized()


def publish_vent_coverage():
    data = publish(vent_coverage).data
    normals = [(0, 0, 0)] * len(data.loops)
    for face in data.polygons:
        rear = data.materials[face.material_index].name == "Rear vent finish"
        if face.normal.dot(vent_surface_normal(face.center, rear)) < 0:
            face.flip()
        face.use_smooth = True
        for loop in face.loop_indices:
            co = data.vertices[data.loops[loop].vertex_index].co
            normals[loop] = vent_surface_normal(co, rear)
    data.normals_split_custom_set(normals)


def main():
    global compact
    shell()
    ports()
    intake()
    internals()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.wm.save_as_mainfile(
        filepath=str(review / "mac-studio-m5-ultra.blend"), compress=True
    )
    publish_vent_coverage()
    export_product("mac-studio-m5-ultra.glb")
    assembled.clear()
    compact = True
    shell()
    ports()
    intake()
    export_product("mac-studio-m5-ultra-room.glb")


if __name__ == "__main__":
    main()
