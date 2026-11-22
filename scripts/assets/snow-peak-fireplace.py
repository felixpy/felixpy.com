import math
import runpy
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


part_id = "snow-peak-st033r"
perimeter = [
    (5, 181),
    (5, 425),
    (7, 434),
    (11, 442),
    (17, 446),
    (25, 447),
    (33, 444),
    (247, 293),
    (253, 286),
    (255, 277),
    (254, 268),
    (249, 261),
    (240, 257),
    (11, 180),
]
vents = [(49 + 32.5 * i, 378 - 23.4 * i) for i in range(5)]


def interior(ratio):
    return [(86 + (x - 86) * ratio, 294 + (h - 294) * ratio) for x, h in perimeter]


def steel_surface(material):
    size = 256
    y, x = np.indices((size, size), dtype=float) / size
    field = (
        0.38
        + 0.29 * np.sin(math.tau * (x * 0.78 + y * 0.91) - 1.05)
        + 0.20 * np.cos(math.tau * (x * 1.8 - y * 0.72))
        + 0.12 * np.sin(math.tau * (x * 3.8 + y * 2.3) + 1.9)
        + 0.045 * np.cos(math.tau * (x * 9.4 - y * 4.8))
    )
    tone = np.clip(field, 0, 1)
    knots = [0, 0.25, 0.64, 0.84, 1]
    colors = [
        (0.77, 0.76, 0.73),
        (0.72, 0.70, 0.65),
        (0.68, 0.59, 0.48),
        (0.60, 0.49, 0.46),
        (0.53, 0.50, 0.53),
    ]
    tint = np.stack(
        [np.interp(tone, knots, [c[i] for c in colors]) for i in range(3)], axis=-1
    )
    grain = runpy.run_path(str(Path(__file__).with_name("product-grain.py")))
    bitmap = grain["image"]("ST-033R annealed skin", tint)
    bitmap.colorspace_settings.name = "sRGB"
    graph = material.node_tree
    tex = graph.nodes.new("ShaderNodeTexImage")
    tex.image = bitmap
    uv = graph.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "Stamp blank"
    graph.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    graph.links.new(
        tex.outputs["Color"], graph.nodes["Principled BSDF"].inputs["Base Color"]
    )
    grain["coat_grain"]("ST-033R fine rolling grain", [(material, 0.10)], True)


def press(shape, side, front, material):
    direction = 1 if front else -1
    depth = 13.1 if front else 0

    def project(x, h, rise):
        return (side * x, h, depth + 1.1 * x / 255 + direction * rise)

    holes = [
        [
            (
                x + 4.72 * math.cos(i * math.tau / 28),
                h + 4.72 * math.sin(i * math.tau / 28),
            )
            for i in range(28)
        ]
        for x, h in vents
    ]
    outline = interior(0.891)
    verts, faces, keys = [], [], {}

    def index(x, h, z):
        key = (round(x, 4), round(h, 4), round(z, 4))
        if key not in keys:
            keys[key] = len(verts)
            verts.append(project(x, h, z))
        return keys[key]

    def ring(points, z):
        return [index(x, h, z) for x, h in points]

    def join(a, b):
        for i in range(len(a)):
            n = (i + 1) % len(a)
            faces.append((a[i], a[n], b[n], b[i]))

    points, constraints, domains = [], [], []
    for polygon in [outline, *holes]:
        if (
            sum(
                x * h2 - x2 * h
                for (x, h), (x2, h2) in zip(polygon, polygon[1:] + polygon[:1])
            )
            < 0
        ):
            polygon = list(reversed(polygon))
        start = len(points)
        points.extend(polygon)
        indices = list(range(start, len(points)))
        constraints.extend(zip(indices, indices[1:] + indices[:1]))
        domains.append(indices)
    vertices, _, triangles, originals, _, memberships = delaunay_2d_cdt(
        [Vector(p) for p in points], constraints, domains, 0, 0.00001
    )
    profiles = [
        (1, -2.1),
        (0.92, -2.1),
        (0.910, -1.84),
        (0.900, -0.48),
        (0.895, -0.12),
        (0.891, 0),
    ]
    for skin in (0, -1.5):
        mapped = [
            index(*(points[ids[0]] if ids else v), skin)
            for v, ids in zip(vertices, originals)
        ]
        for tri, members in zip(triangles, memberships):
            if list(members) == [0]:
                faces.append(tuple(mapped[i] for i in tri))
        loops = [ring(interior(r), z + skin) for r, z in profiles]
        for a, b in zip(loops, loops[1:]):
            join(a, b)
    for hole in holes:
        join(ring(hole, 0), ring(hole, -1.5))
    join(ring(perimeter, -2.1), ring(perimeter, -3.6))
    shape.add(verts, faces, material, False)
    panel = shape.finalize(32)
    if sum(face.area for face in panel.data.polygons) < 0.053:
        raise ValueError(f"Missing pressed sheet surface for {panel.name}")
    uv = panel.data.uv_layers.new(name="Stamp blank")
    for loop in panel.data.loops:
        v = panel.data.vertices[loop.vertex_index].co
        u = abs(v.x) / 0.276
        uv.data[loop.index].uv = (u if side < 0 else 0.97 - u, (v.z - 0.160) / 0.314)
    return panel


def sleeve(shape, start, end, inner, outer, mat):
    a, b = Vector(start), Vector(end)
    axis = (b - a).normalized()
    u = axis.cross(Vector((0, 0, 1))).normalized()
    v = axis.cross(u)
    rows = []
    for origin, radius in (
        (a, inner),
        (a, outer - 0.23),
        (a + axis * 0.24, outer),
        (b - axis * 0.24, outer),
        (b, outer - 0.23),
        (b, inner),
        (a, inner),
    ):
        rows.append(
            [
                origin
                + radius
                * (u * math.cos(i * math.tau / 22) + v * math.sin(i * math.tau / 22))
                for i in range(22)
            ]
        )
    shape.rings(rows, mat, close=False)


def build(sculpture, finish, bend):
    steel = finish("ST-033R · heat-tinted pressed stainless", "b7afa3", 0.94, 0.34)
    rail = finish("ST-033R · drawn stainless rod", "cfcdc7", 0.96, 0.24)
    weld = finish("ST-033R · pickled weld and rolled hinge", "aba398", 0.91, 0.32)
    steel_surface(steel)
    root = bpy.data.objects.new("Snow Peak TAKIBI M ST-033R · folded", None)
    bpy.context.collection.objects.link(root)
    root["product"] = part_id
    for side in (-1, 1):
        for front in (False, True):
            name = (
                "ST-033R "
                + ("left" if side < 0 else "right")
                + (" front" if front else " rear")
            )
            panel = press(sculpture(name + " pressed shell"), side, front, steel)
            panel.parent = root
            direction = 1 if front else -1
            wire_depth = 13.2 if front else -0.8

            def edge(x, h, offset=0):
                return (side * x, h, wire_depth + 1.1 * x / 255 + direction * offset)

            short = (side > 0) == front
            rail_outline = [
                (5, 426),
                (6.9, 434),
                (12, 442),
                (18.8, 446.4),
                (25, 447),
                (33, 444),
                (246, 293.4),
                (251.9, 287),
                (255, 279),
                (255.1, 272.5),
                (252.9, 267),
                (250, 263),
            ]
            if short:
                lower = [
                    (248, 261),
                    (231, 255),
                    (1, 179),
                    (-126, 135.5),
                    (-142.5, 133.6),
                    (-153, 135),
                    (-163, 139.2),
                    (-171, 147.6),
                    (-175.3, 157.7),
                    (-174.2, 168),
                    (-169.8, 177.6),
                    (3, 423),
                    (5, 426),
                ]
            else:
                lower = [
                    (247, 258),
                    (70.5, 22.6),
                    (60.8, 11.9),
                    (51, 6),
                    (39, 3.5),
                    (28, 5.8),
                    (19.1, 12.1),
                    (12.4, 21.9),
                    (8.2, 34),
                    (6.7, 45),
                    (5, 180),
                    (5, 426),
                ]
            rod = sculpture(name + " continuous bent support")
            track = [edge(x, h, 2.45) for x, h in rail_outline]
            for i, (x, h) in enumerate(lower):
                rise = 6.15 if short and 3 <= i <= 11 else 2.45
                track.append(edge(x, h, rise))
            bend(rod, track, 2.5, rail, 16, tolerance=0.075)
            rod.finalize(5).parent = root

            cheeks = sculpture(name + " rolled journals and spot welds")
            edge_low = Vector(edge(7.5, 180.5, 2.45))
            edge_high = Vector(edge(250, 263, 2.45))
            axis = edge_high - edge_low
            a, b = Vector(edge(5, 180, 2.45)), Vector(edge(5, 426, 2.45))
            if short:
                cheeks.pipe([a, b], 2.50, rail, 16)
            else:
                cheeks.pipe([edge_low, edge_high], 2.50, rail, 16)
            bore_segments = [
                (edge_low + axis * 0.105, edge_low + axis * 0.395),
                (edge_low + axis * 0.51, edge_low + axis * 0.808),
                (a + (b - a) * 0.25, a + (b - a) * 0.88),
            ]
            for p, q in bore_segments:
                sleeve(cheeks, p, q, 2.58, 3.56, weld)
                axis2d = (q - p).normalized()
                inward = (
                    Vector((side, 0, 0))
                    if abs(axis2d.y) > 0.95
                    else Vector((-side * 0.32, 0.95, 0))
                )
                z = Vector((0, 0, direction))
                p = p + axis2d * 1.6
                q = q - axis2d * 1.6
                contour = [
                    inward * 1.85 - z * 2.75,
                    inward * 2.5 - z * 4.6,
                    inward * 6.1 - z * 4.7,
                    inward * 6.1 - z * 3.9,
                    inward * 3.3 - z * 3.9,
                    inward * 2.5 - z * 2.3,
                ]
                cheeks.rings(
                    [[pt + offset for offset in contour] for pt in (p, q)], weld, False
                )
            for x, h in [
                (7.4, 208),
                (7.3, 413),
                (17, 442),
                (47, 432),
                (107, 390),
                (165, 349),
                (221, 309),
                (251, 277),
                (222, 255.4),
                (153, 232),
                (81, 207),
                (18, 186),
            ]:
                p = edge(x, h, -1.0)
                cheeks.pipe([p, edge(x, h, 1.15)], [2.4, 1.35], weld, 12)
            cheeks.finalize(5).parent = root

            lettering = sculpture(name + " die stamp")
            angle = -0.622 * side

            def stamp(x, h):
                u = 84 + side * (x * math.cos(angle) - h * math.sin(angle))
                height = 285 + x * math.sin(angle) + h * math.cos(angle)
                return (
                    side * u,
                    height,
                    (13.1 if front else 0) + 1.1 * u / 255 + direction * 0.34,
                )

            def polyline(path, radius):
                lettering.pipe([stamp(x, h) for x, h in path], radius, rail, 8)

            border = [
                (-24, -11),
                (24, -11),
                (25, -10),
                (25, 14),
                (24, 15),
                (-24, 15),
                (-25, 14),
                (-25, -10),
                (-24, -11),
            ]
            polyline(border, 0.45)
            for i in range(3):
                a = i * math.pi / 3 + math.pi / 6
                x, h = 4.05 * math.cos(a), 4.05 * math.sin(a)
                polyline([(-x, 6.9 - h), (x, 6.9 + h)], 0.50)
            lettering.label("snow peak", 9, lambda x, h: stamp(x, h - 4.3), rail)
            lettering.label("MADE IN JAPAN", 2.7, lambda x, h: stamp(x, h - 14.6), rail)
            lettering.finalize().parent = root
    return root


def fit(atelier):
    scene = bpy.context.scene
    (installed,) = [obj for obj in scene.objects if obj.get("product") == part_id]
    path = Path(atelier) / "takibi-m/st-033r.blend"
    with bpy.data.libraries.load(str(path), link=False) as (library, loaded):
        loaded.objects = list(library.objects)
    (native,) = [obj for obj in loaded.objects if obj.get("product") == part_id]
    native_parts = list(native.children)
    if len(native_parts) != 16 or set(loaded.objects) != {native, *native_parts}:
        raise ValueError(
            "The TAKIBI M requires four shells, supports, journals and die stamps"
        )
    occluder = any(
        obj.get("studioOccluder", False) for obj in installed.children_recursive
    )
    for old in reversed(installed.children_recursive):
        bpy.data.objects.remove(old, do_unlink=True)
    for item in native_parts:
        scene.collection.objects.link(item)
        item.parent = installed
        item["studioOccluder"] = occluder
    bpy.data.objects.remove(native, do_unlink=True)
