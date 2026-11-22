import json
import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

assets = Path(__file__).resolve().parent
root = assets.parents[1]
product = root / ".references/05-摄影与陈列/相机与镜头/Nikon Z8/Blender"
source = product / "nikon-z8-card-bay.blend"
collection_name = "Z8 dual media compartment"
sys.path.insert(0, str(assets))
from product_solids import (
    block,
    combine,
    corners,
    edge,
    letters,
    mesh,
    pin,
    subtract,
    vertex,
)

camera = runpy.run_path(str(assets / "build-nikon-z8.py"))
finish = camera["finish"]
contacts = runpy.run_path(str(assets / "cfexpress-interface.py"))["CONTACT_CENTERS"]


def smooth(a, b, n):
    t = max(0, min(1, (n - a) / (b - a)))
    return t * t * (3 - 2 * t)


def split(poly, signed):
    inside, outside = [], []
    for p, q in zip(poly, poly[1:] + poly[:1]):
        a, b = signed(p), signed(q)
        (inside if a >= 0 else outside).append(p)
        if (a < 0 < b) or (b < 0 < a):
            cross = tuple(u + (v - u) * a / (a - b) for u, v in zip(p, q))
            inside.append(cross)
            outside.append(cross)
        elif a == 0:
            outside.append(p)
    return inside, outside


def rear_limit(y):
    return -52.1 + 0.15 * (y + 2)


def cut_grip(mat):
    outline = json.loads((root / "src/scene/nikon-z8-outline.json").read_text())
    sections = json.loads((root / "src/scene/nikon-z8-grip.json").read_text())
    path = camera["contour"](outline, 4)
    distance, rings = [0], []
    for a, b in zip(path, path[1:] + path[:1]):
        distance.append(distance[-1] + (b - a).length)
    for section in sections:
        row = []
        for i, (x, z) in enumerate(path + path[:1]):
            h, scale = section["height"], section["scale"]
            belly = math.sin(math.pi * max(0, min(1, (h + 48) / 72)))
            X = x * scale - belly * smooth(55, 72, -x) * smooth(-8, 24, z) * 1.8
            Z = z * scale + smooth(35, 55, -x) * smooth(4, 34, z) * section.get(
                "fingerwell", 0
            )
            Y = h - section.get("slope", 0) * max(0, min(1, (Z - 1) / 40))
            row.append((X, Y, Z, distance[i] / 116, Y / 116 + 0.55))
        rings.append(row)
    fixed, lid = [], []
    for low, high in zip(rings, rings[1:]):
        for i in range(len(path)):
            for poly in [
                [low[i], low[i + 1], high[i]],
                [low[i + 1], high[i + 1], high[i]],
            ]:
                for plane in (
                    lambda p: -0.55 - p[2],
                    lambda p: rear_limit(p[1]) - p[0],
                    lambda p: p[1] + 32.55,
                    lambda p: 21.5 - p[1],
                ):
                    poly, offcut = split(poly, plane)
                    if len(offcut) > 2:
                        fixed.append(offcut)
                    if len(poly) < 3:
                        break
                if len(poly) > 2:
                    lid.append(poly)

    def surface(name, polygons):
        points, faces, indexes, uvs = [], [], {}, []
        for polygon in polygons:
            face = []
            for x, h, d, u, v in polygon:
                key = tuple(round(q, 6) for q in (x, h, d))
                if key not in indexes:
                    indexes[key] = len(points)
                    points.append(key)
                face.append(indexes[key])
            if len(set(face)) == len(face):
                faces.append(face)
                uvs.append([(v[3], v[4]) for v in polygon])
        obj = mesh(name, points, faces, mat)
        layer = obj.data.uv_layers.new(name="Grip overmould")
        for polygon, coords in zip(obj.data.polygons, uvs):
            polygon.use_smooth = True
            for i, coord in zip(polygon.loop_indices, coords):
                layer.data[i].uv = coord
        edges = {}
        for face in faces:
            for a, b in zip(face, face[1:] + face[:1]):
                key = tuple(sorted((a, b)))
                edges[key] = None if key in edges else (a, b)
        return obj, [
            (points[a], points[b]) for ends in edges.values() if ends for a, b in [ends]
        ]

    surface("Grip jacket around the card opening", fixed)
    return surface("Rubber thumb rest on hinged slot cover", lid)


def panel(name, x, y, z, height, width, depth, radius, mat):
    ring = [(y + v, z + u) for u, v in corners(width, height, radius, 8)]
    n = len(ring)
    points = [(t, h, d) for t in (x - depth / 2, x + depth / 2) for h, d in ring]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    faces += [(i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n)]
    return mesh(name, points, faces, mat)


def join_perimeter(name, boundary, target, mat):
    points, faces = [], []
    for a, b in boundary:
        j = len(points)
        points += [a, b, target(b), target(a)]
        faces.append((j, j + 1, j + 2, j + 3))
    return mesh(name, points, faces, mat)


def opening_return(p):
    x, y, z = p
    t = (-0.55 - z + (x + 71.4) * 0.7) / (31.6 + (rear_limit(y) + 71.4) * 0.7)
    if abs(x - rear_limit(y)) < 0.001:
        t = 1
    if abs(z + 0.55) < 0.001:
        t = 0
    return -60.4, -5.5 + (y + 5.5) * 0.95, -1.75 - max(0, min(1, t)) * 27.0


def receiver(name, h, d, length, width, end, black, steel):
    rings = []
    for x, padding in [(-60.84, 0.28), (-60.13, 0), (-59.15, 0), (end, 0)]:
        rings.append(
            [
                (x, h + b, d + a)
                for a, b in corners(width + padding, length + padding, 0.32, 6)
            ]
        )
    n = len(rings[0])
    points = sum(rings, [])
    obj = mesh(
        name + " · folded receiver walls",
        points,
        [
            (j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i)
            for j in range(3)
            for i in range(n)
        ],
        black,
    )
    obj.data.materials.append(steel)
    for face in list(obj.data.polygons)[n : 2 * n]:
        face.material_index = 1
    panel(name + " · connector floor", end + 0.3, h, d, length, width, 0.6, 0.28, black)


def stencil(text, x, h, z, size, mat):
    pts, faces = letters(text, False)
    mid_u = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    mid_v = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    return mesh(
        "Door warning · " + text,
        [(x, h + (v - mid_v) * size, z - (u - mid_u) * size) for u, v in pts],
        faces,
        mat,
    )


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(parts)
    grip = finish("Z8 card grip rubber", "ffffff", 0, 0.73)
    black = finish("Card cage graphite PPS", "43464b", 0.12, 0.48)
    deep = finish("Card throat and gasket", "2b2e31", 0.03, 0.68)
    steel = finish("Nickel plated card springs", "8e9295", 0.68, 0.41)
    gold = finish("Recessed card contact gold", "b08b48", 0.73, 0.34)
    ochre = finish("Hot card caution ink", "e6b644", 0.04, 0.59)
    cover, boundary = cut_grip(grip)
    join_perimeter("Grip opening · recessed perimeter", boundary, opening_return, deep)
    y, d = -5.5, -15.25
    sockets = [
        ("CFexpress B and XQD", 1.8, -11.1, 30.5, 4.53, -26.4),
        ("SD UHS-II", -11.3, -21.9, 24.8, 2.49, -33.1),
    ]
    escutcheon = panel(
        "Inner escutcheon · two distinct card mouths",
        -59.94,
        y,
        d,
        52.65,
        27.6,
        0.92,
        0.4,
        black,
    )
    subtract(
        escutcheon,
        [
            panel("Mouth cutter", -59.94, h, z, ln + 0.4, w + 0.4, 4, 0.32, black)
            for _, h, z, ln, w, _ in sockets
        ],
    )
    edge(escutcheon, 0.12, 2)
    for name, h, z, ln, w, end in sockets:
        receiver(name, h, z, ln, w, end, deep, steel)
    h, z = sockets[0][1:3]
    for i, offset in enumerate(contacts):
        pin(
            f"CFexpress · recessed terminal {i + 1:02}",
            (-26.7, h + offset, z + 0.14),
            (-28.25, h + offset, z + 0.12),
            0.14,
            gold,
            8,
        )
    h, z = sockets[1][1:3]
    for row, count, reach in [(1, 9, 11.4), (2, 8, 7.3)]:
        for i in range(count):
            p = h + (i - (count - 1) / 2) * 2.34
            pin(
                f"SD bank {row} · spring {i + 1:02}",
                (-33.2 - reach, p, z - 0.87),
                (-35.1 - reach, p, z - 0.55),
                0.15,
                steel,
                8,
            )
    for y in (-28.6, 16.6):
        panel(
            "Moulded cover catch receiver", -61.15, y, -25.6, 3.9, 2.3, 1.55, 0.35, deep
        )
    for y in (-17.5, 4.4):
        pin(
            "Body-side hinge knuckle",
            (-71.0, y, -0.55),
            (-71.0, y + 6.6, -0.55),
            0.86,
            black,
            20,
        )
    pin(
        "Captive steel cover pin",
        (-71.0, -24.0, -0.55),
        (-71.0, 14.6, -0.55),
        0.42,
        steel,
        20,
    )
    sd = panel(
        "Seated SD · exposed write-in edge",
        -47.0,
        -11.3,
        -21.9,
        23.85,
        2.07,
        32,
        0.45,
        black,
    )
    edge(sd, 0.19, 3)
    for h in (-20.5, -18.5, -16.5, -14.5):
        panel("SD · press surface rib", -63.05, h, -21.9, 0.27, 1.7, 0.16, 0.11, deep)
    for y in (-11.4, 10.8):
        panel(
            "CFexpress folded guide at entrance",
            -60.95,
            y,
            -13.47,
            4.6,
            0.64,
            0.72,
            0.22,
            steel,
        )
    for v in cover.data.vertices:
        x, d, h = v.co * 1000
        if d > 25:
            bump = math.exp(
                -(((x + 62 + 0.07 * h) / 5.7) ** 2) - ((h + 5.5) / 15.5) ** 2
            ) * smooth(25, 32.5, d)
            v.co.y += 0.0033 * bump
    lid_parts = {cover}
    before = set(bpy.data.objects)

    def inner(p):
        x, y, z = p
        return (x + 1.37, y, z + 1.19)

    join_perimeter("Door perimeter · wrapped elastomer edge", boundary, inner, deep)
    inside = cover.copy()
    inside.data = cover.data.copy()
    inside.name = "Door backing · moulded inside face"
    bpy.context.scene.collection.objects.link(inside)
    inside.data.materials[0] = black

    for v in inside.data.vertices:
        v.co += Vector(vertex(1.37, 0, 1.19))
    inside.data.flip_normals()
    for y in (-23.6, -5.8, 10.7):
        pin(
            "Cover-side hinge knuckle",
            (-71.0, y, -0.55),
            (-71.0, y + 3.6, -0.55),
            0.93,
            black,
            22,
        )

    def formed(name, shape, mat, lift, thickness):
        tree = BVHTree.FromPolygons(
            [v.co for v in inside.data.vertices],
            [tuple(p.vertices) for p in inside.data.polygons],
        )

        def sample(z, y, added):
            start = Vector(vertex(-45, y, z))
            loc, normal, index, dist = tree.ray_cast(start, Vector((-1, 0, 0)), 0.045)
            return ((loc.x * 1000 if loc is not None else -69.3) + added, y, z)

        n = len(shape)
        coords = [sample(z, y, t) for t in (lift, lift + thickness) for z, y in shape]
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        faces += [(j, (j + 1) % n, (j + 1) % n + n, j + n) for j in range(n)]
        return mesh(name, coords, faces, mat)

    keeper = [
        (-2.4, 8.9),
        (-12.1, 8.9),
        (-13.6, 7.4),
        (-13.6, -13.8),
        (-12.0, -15.0),
        (-2.4, -15.0),
        (-2.4, -12.5),
        (-10.6, -12.5),
        (-11.4, -11.8),
        (-11.4, 5.8),
        (-10.9, 6.5),
        (-2.4, 6.5),
    ]
    formed("Stamped keeper · U-shaped spring", keeper, steel, 0.29, 0.34)
    formed(
        "Sliding retainer",
        [(-3.0, 4.9), (-9.9, 4.9), (-9.9, -10.7), (-3.0, -10.7)],
        black,
        0.12,
        0.66,
    )
    for y in (-9.5, -5.0, -0.5, 3.4):
        formed(
            "Latch thumb rib",
            [(-3.6, y), (-8.8, y), (-8.8, y + 0.7), (-3.6, y + 0.7)],
            deep,
            0.79,
            0.47,
        )
    plate = [(-20.4 + u, 8.15 + v) for u, v in corners(7.6, 12.35, 0.48, 6)]
    sticker = formed("Heat-warning label", plate, ochre, 0.48, 0.16)
    tree = BVHTree.FromPolygons(
        [v.co for v in sticker.data.vertices],
        [tuple(p.vertices) for p in sticker.data.polygons],
    )
    for text, h, size in [
        ("CAUTION", 12.55, 1.25),
        ("HOT", 7.9, 2.4),
        ("CARD", 5.05, 2.1),
    ]:
        ink = stencil(text, -67, h, -20.4, size, deep)
        for v in ink.data.vertices:
            loc, *_ = tree.ray_cast(
                Vector((-0.045, v.co.y, v.co.z)), Vector((-1, 0, 0)), 0.045
            )
            if loc is not None:
                v.co.x = loc.x + 0.00009
    lid_parts |= set(bpy.data.objects) - before
    hinge = bpy.data.objects.new("Card door pivot", None)
    bpy.context.scene.collection.objects.link(hinge)
    hinge.location = vertex(-71.0, 0, -0.55)
    hinge.empty_display_size = 0.008
    bpy.context.view_layer.update()
    for o in lid_parts:
        o.parent = hinge
        o.matrix_parent_inverse = hinge.matrix_world.inverted()
    for obj in list(bpy.context.scene.objects):
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        parts.objects.link(obj)
    grip_images = []
    nodes = grip.node_tree.nodes
    for file, channel in [
        ("hardware-surface.webp", "Base Color"),
        ("camera-grip-normal.webp", "Normal"),
    ]:
        tex = nodes.new("ShaderNodeTexImage")
        im = bpy.data.images.load(str(root / "public/media/materials" / file))
        tex.image = im
        out = tex.outputs["Color"]
        if channel == "Normal":
            im.colorspace_settings.name = "Non-Color"
            normal = nodes.new("ShaderNodeNormalMap")
            grip.node_tree.links.new(out, normal.inputs["Color"])
            out = normal.outputs["Normal"]
        grip.node_tree.links.new(out, nodes["Principled BSDF"].inputs[channel])
        im.pack()
        grip_images.append(tex)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    for obj in list(parts.objects):
        if obj.name.startswith(("SD bank ", "SD UHS-II · connector floor")):
            bpy.data.objects.remove(obj, do_unlink=True)
    for node in grip_images:
        nodes.remove(node)
    for attached in (False, True):
        candidates = [
            o
            for o in list(parts.objects)
            if o.type == "MESH" and (o.parent == hinge) == attached
        ]
        for o in candidates:
            if attached:
                world = o.matrix_world.copy()
                o.parent = None
                o.matrix_world = world
        batches = {
            mat: [o for o in candidates if o.data.materials[0] == mat]
            for mat in (grip, black, deep, steel, gold, ochre)
        }
        for mat, grouped in batches.items():
            if not grouped:
                continue
            merged = combine(("Lid" if attached else "Bay") + " · " + mat.name, grouped)
            if attached:
                merged.parent = hinge
                merged.matrix_parent_inverse = hinge.matrix_world.inverted()
    path = root / "public/media/models/nikon-z8-card-bay.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(assets / "pack-product-geometry.mjs"), str(path)], check=True
    )


if __name__ == "__main__":
    build()
