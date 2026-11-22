import json
import math
import runpy
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
review = root / ".review/atelier"
destination = root / "public/media/models/ryuo-mf12c"
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
tools = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))
write_mesh = runpy.run_path(str(scripts / "blender_mesh.py"))["write_mesh"]
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
corners, eye = tools["corners"], tools["eye"]
tau = math.tau
parts = defaultdict(list)


def circle(x, y, r, count):
    return [
        (x + r * math.cos(i * tau / count), y + r * math.sin(i * tau / count))
        for i in range(count)
    ]


def cap(shape, outside, holes, project, mat):
    verts, loops = [], []
    for loop in [outside, *holes]:
        if sum(x * v - u * y for (x, y), (u, v) in zip(loop, loop[1:] + loop[:1])) < 0:
            loop = list(reversed(loop))
        loops.append(list(range(len(verts), len(verts) + len(loop))))
        verts.extend(Vector(point) for point in loop)
    pts, _, faces, _, _, origins = delaunay_2d_cdt(verts, [], loops, 1, 0.000001)
    shape.add(
        [project(x, y) for x, y in pts],
        [face for face, ids in zip(faces, origins) if list(ids) == [0]],
        mat,
        False,
    )


def connect(shape, profiles, mat, smooth=False):
    shape.rings(
        [[(x, y, z) for x, y in loop] for loop, z in profiles], mat, smooth, False
    )


def axial(shape, x, y, profiles, mat, count=48):
    rings = [(circle(x, y, r, count), z) for r, z in profiles]
    connect(shape, rings, mat, True)
    for loop, z in (rings[0], rings[-1]):
        shape.add([(u, v, z) for u, v in loop], [tuple(range(len(loop)))], mat, False)


def solid(shape, outline, z0, z1, mat, holes=()):
    for z in (z0, z1):
        cap(shape, outline, holes, lambda x, y: (x, y, z), mat)
    for loop in [outline, *holes]:
        connect(shape, [(loop, z0), (loop, z1)], mat)


def register(shape, key):
    obj = shape.finalize()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000000024)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj["fanPart"] = key
    parts[key].append(obj)
    return obj


def perimeter(width):
    r = 3.2
    return [
        (width - r, width),
        (-width + r, width),
        (-width, width - r),
        (-width, -width + r),
        (-width + r, -width),
        (width - r, -width),
        (width, -width + r),
        (width, width - r),
    ]


def side_panel_point(side, px, py, depth=60.13):
    return (depth * side, (436 - px) * side / 12, 12.8 + (py - 110) / 12)


def side_vents():
    return [
        (col, row) for col, rows in [
            (922, (110,)), (947, (92, 128)), (972, (74, 110, 146)),
            (997, (92, 128)), (1022, (74, 110, 146)),
        ] for row in rows
    ]


def motor_frame(white):
    shell = Sculpture(
        "Injection moulding • open screw posts, bellmouth and interlock pockets"
    )
    outer = perimeter(60)
    bores = [circle(x, y, 2.27, 16) for x in (-52.5, 52.5) for y in (-52.5, 52.5)]
    for z in (0.55, 24.42):
        cap(
            shell,
            outer,
            [circle(0, 0, 56.94, 96), *bores],
            lambda x, y: (x, y, z),
            white,
        )
    connect(
        shell,
        [
            (circle(0, 0, r, 96), z)
            for r, z in [
                (56.94, 0.55),
                (56.35, 1.5),
                (55.95, 3.8),
                (55.95, 20.4),
                (56.22, 22.5),
                (56.94, 24.42),
            ]
        ],
        white,
        True,
    )
    for bore in bores:
        connect(shell, [(bore, 0.55), (bore, 24.42)], white, True)
    for i, (x, y) in enumerate(outer):
        u, v = outer[(i + 1) % len(outer)]
        if y == v and abs(y) == 60:
            direction = 1 if y > 0 else -1
            outline = [(-56.8, 0.55), (56.8, 0.55), (56.8, 24.42), (-56.8, 24.42)]
            ports = [
                [
                    (a, b)
                    for a, b in [
                        (c - w / 2, z0),
                        (c + w / 2, z0),
                        (c + w / 2, z1),
                        (c - w / 2, z1),
                    ]
                ]
                for c, w, z0, z1 in [
                    (-45, 9, 6.7, 18.3),
                    (45, 9, 6.7, 18.3),
                    (31.8, 16, 8.8, 16.4),
                ]
            ]
            cap(shell, outline, ports, lambda a, b: (a, y, b), white)
            for port in ports:
                mouth = [(a, y, b) for a, b in port]
                floor = [(a, y - 3.4 * direction, b) for a, b in port]
                shell.rings([mouth, floor], white, False, False)
                shell.add(floor, [(0, 1, 2, 3)], white, False)
        elif x == u and abs(x) == 60:
            side = 1 if x > 0 else -1
            mouths = []
            for px, py in side_vents():
                _, cy, cz = side_panel_point(side, px, py)
                mouths.append(circle(cy, cz, 0.48, 12))
            cap(shell, [(y, 0.55), (v, 0.55), (v, 24.42), (y, 24.42)],
                mouths, lambda a, b: (x, a, b), white)
            for mouth in mouths:
                shell.rings([[(x - side * d, a, b) for a, b in mouth] for d in (0, 2.1)],
                            white, False, False)
        else:
            shell.add(
                [(x, y, 0.55), (u, v, 0.55), (u, v, 24.42), (x, y, 24.42)],
                [(0, 1, 2, 3)],
                white,
                False,
            )
    register(shell, "chassis")


def corner_details(pad, ink):
    outline = [
        (35.6, 58.9),
        (54.1, 58.9),
        (58.9, 54.1),
        (58.9, 35.6),
        (57.7, 34.4),
        (55.9, 34.5),
        (52.5, 40.2),
        (47.9, 46.2),
        (42.9, 50.4),
        (35.0, 55.8),
        (34.5, 57.5),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            for rear in (True, False):
                name = f"{sx:+d}, {sy:+d} • {'exhaust' if rear else 'intake'}"
                part = Sculpture("Isolation pad " + name)
                pts = [(sx * x, sy * y) for x, y in outline]
                bore = circle(sx * 52.5, sy * 52.5, 2.5, 20)
                solid(
                    part, pts, 0 if rear else 24.42, 0.55 if rear else 25, pad, [bore]
                )
                register(part, "pads")
                detail = Sculpture("Moulded pad chevrons " + name)
                z = -0.015 if rear else 25.015
                for loop in [
                    [(39, 56.8), (46.2, 56.8), (47.4, 55.8), (40, 55.8)],
                    [(56.8, 39), (56.8, 46.2), (55.8, 47.4), (55.8, 40)],
                ]:
                    detail.add(
                        [(sx * x, sy * y, z) for x, y in loop],
                        [(0, 1, 2, 3)],
                        ink,
                        False,
                    )
                register(detail, "grey")
            fastener = Sculpture(
                f"Radiator screw {sx:+d}, {sy:+d} • recessed Phillips drive"
            )
            x, y = sx * 52.5, sy * 52.5
            cross = [
                (-0.48, 1.55),
                (0.48, 1.55),
                (0.48, 0.48),
                (1.55, 0.48),
                (1.55, -0.48),
                (0.48, -0.48),
                (0.48, -1.55),
                (-0.48, -1.55),
                (-0.48, -0.48),
                (-1.55, -0.48),
                (-1.55, 0.48),
                (-0.48, 0.48),
            ]
            opening = [(x + a, y + b) for a, b in cross]
            floor = [(x + a * 0.72, y + b * 0.72) for a, b in cross]
            radii = [
                (1.50, -2.45),
                (1.82, -2.1),
                (1.82, 24.72),
                (3.48, 25.02),
                (3.55, 25.28),
                (3.27, 25.72),
                (2.64, 25.98),
            ]
            connect(fastener, [(circle(x, y, r, 24), z) for r, z in radii], ink, True)
            fastener.add(
                [(a, b, -2.45) for a, b in circle(x, y, 1.50, 24)],
                [tuple(range(24))],
                ink,
                False,
            )
            cap(
                fastener,
                circle(x, y, 2.64, 24),
                [opening],
                lambda a, b: (a, b, 25.98),
                ink,
            )
            connect(fastener, [(opening, 25.98), (floor, 24.98)], ink)
            fastener.add(
                [(a, b, 24.98) for a, b in floor],
                [tuple(range(len(floor)))],
                ink,
                False,
            )
            register(fastener, "screws")


def stator(white, graphite, mark):
    for i in range(4):
        arm = Sculpture(
            f"Motor suspension {i + 1}" + (" • harness channel" if i == 0 else "")
        )
        angle = math.pi / 4 + i * math.pi / 2

        def point(x, y, z):
            return (
                x * math.cos(angle) - y * math.sin(angle),
                x * math.sin(angle) + y * math.cos(angle),
                z,
            )

        width = 4.55 if i == 0 else 2.55
        for z, scale in [(0.78, 0.87), (1.05, 1), (3.45, 1), (3.72, 0.87)]:
            row = [
                point(x, y * scale + offset, z)
                for x, y, offset in [
                    (12, -width, -7.2),
                    (36, -width, -4.3),
                    (56.4, -width, 0),
                    (56.4, width, 0),
                    (36, width, -4.3),
                    (12, width, -7.2),
                ]
            ]
            if z == 0.78:
                rows = []
            rows.append(row)
        arm.rings(rows, white, False)
        register(arm, "chassis")
        if i == 0:
            wire = Sculpture("Four sleeved motor leads under two retention bridges")
            for trace in range(4):
                y = (trace - 1.5) * 0.77
                wire.pipe(
                    [
                        point(x, o + y, z)
                        for x, o, z in [
                            (16, -7, 0.61),
                            (34, -4.8, 0.55),
                            (45, -2.5, 0.52),
                            (54, -0.25, 0.69),
                        ]
                    ],
                    0.32,
                    graphite,
                    6,
                )
            register(wire, "grey")
            clips = Sculpture("Strain relief bridges")
            for x, offset in [(30, -5.1), (47, -2.35)]:
                clips.rings(
                    [
                        [
                            point(x + a, offset + b, z)
                            for a, b in [
                                (-1.4, -3.4),
                                (1.4, -3.4),
                                (1.4, 3.4),
                                (-1.4, 3.4),
                            ]
                        ]
                        for z in (0.06, 0.8)
                    ],
                    white,
                    False,
                )
            register(clips, "chassis")
    boot = Sculpture("Motor base and service label land")
    axial(
        boot,
        0,
        0,
        [(17.3, 0.68), (18.5, 1.12), (18.6, 2.75), (17.9, 3.65), (14.5, 4.2)],
        white,
        72,
    )
    register(boot, "chassis")
    label = Sculpture("Motor label and typography")
    axial(label, 0, 0, [(15.55, 0.58), (15.55, 0.70)], graphite, 64)
    register(label, "grey")
    text = Sculpture("Motor identification • rear")
    eye(text, lambda u, v: (-11 * u, 7 + 11 * v, 0.53), mark)
    for caption, y, scale in [
        ("ROG RYUO IV MF-12C ARGB", 0.15, 1.92),
        ("12V DC   2650 RPM", -3.0, 1.64),
        ("CE    UKCA", -7.3, 2.65),
    ]:
        text.label(caption, scale, lambda u, v: (-u, v + y, 0.525), mark)
    register(text, "chassis")


def impeller(opal, medal, ink):
    for index in range(7):
        blade = Sculpture(f"Tapered axial impeller vane {index + 1:02}")
        verts, faces = [], []
        nr, nc = 15, 8

        def idx(side, i, j):
            return (side * (nr + 1) + i) * (nc + 1) + j

        for side in (0, 1):
            for i in range(nr + 1):
                r = i / nr
                for j in range(nc + 1):
                    u = j / nc
                    reach = (
                        16.5
                        + 38.45 * r
                        - (
                            1.8 * (max(0, (0.28 - u) / 0.28) ** 2)
                            + 3.1 * max(0, (u - 0.77) / 0.23) ** 2
                        )
                        * r**3
                    )
                    angle = (
                        index * tau / 7
                        + 0.62 * r * r
                        - (0.85 - 0.23 * r) * u
                        - 0.12 * math.sin(math.pi * r)
                    )
                    z = (
                        13.3
                        + (u - 0.5) * (8.0 + 8.25 * r)
                        + 2.65 * math.sin(u * math.pi) * math.sin(0.4 + r * 1.8)
                        + 1.3 * r
                    )
                    z += (side - 0.5) * (
                        0.45 + 0.64 * (1 - r) + 0.33 * math.sin(math.pi * u)
                    )
                    verts.append((reach * math.cos(angle), reach * math.sin(angle), z))
        for side in (0, 1):
            for i in range(nr):
                for j in range(nc):
                    faces.append(
                        tuple(
                            idx(side, a, b)
                            for a, b in [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                        )
                    )
        boundary = (
            [(0, j) for j in range(nc + 1)]
            + [(i, nc) for i in range(1, nr + 1)]
            + [(nr, j) for j in range(nc - 1, -1, -1)]
            + [(i, 0) for i in range(nr - 1, 0, -1)]
        )
        for k, (i, j) in enumerate(boundary):
            a, b = boundary[(k + 1) % len(boundary)]
            faces.append((idx(0, i, j), idx(0, a, b), idx(1, a, b), idx(1, i, j)))
        blade.add(verts, faces, opal)
        obj = register(blade, "vanes")
        uv = obj.data.uv_layers.new(name="Hub light falloff")
        for loop in obj.data.loops:
            x, z, y = obj.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = (
                (math.hypot(x, y) * 1000 - 16.5) / 38.45,
                (-z * 1000 - 6) / 18,
            )
    cup = Sculpture("Impeller hub, rolled intake lip and seal")
    axial(
        cup,
        0,
        0,
        [
            (15.5, 4.28),
            (17.25, 4.9),
            (17.7, 7.4),
            (17.9, 19.8),
            (17.63, 22.75),
            (17.0, 23.61),
            (15.55, 23.93),
        ],
        medal,
        80,
    )
    register(cup, "medallion")
    mark = Sculpture("Rotor medallion • ROG eye and divided concentric foil lines")
    z = 23.966
    for r in [12.99, 14.75]:
        count = 80
        outer, inner = circle(0, 0, r, count), circle(0, 0, r - 0.26, count)
        mark.add(
            [(x, y, z) for x, y in outer + inner],
            [
                (i, (i + 1) % count, (i + 1) % count + count, i + count)
                for i in range(count)
            ],
            ink,
            False,
        )
    for i in range(4):
        a = i * math.pi / 2
        mark.add(
            [
                (r * math.cos(a + d), r * math.sin(a + d), z)
                for r, d in [(13, -0.014), (14.6, -0.014), (14.6, 0.014), (13, 0.014)]
            ],
            [(0, 1, 2, 3)],
            ink,
            False,
        )
    eye(mark, lambda u, v: (21.8 * u, -21.8 * v, z), ink)
    register(mark, "rotor-foil")


def side_finish(white, graphite, gold, luminous):
    connector = Sculpture("Male and female contact banks • six positions")
    carrier = Sculpture("Insulating contact bed and shrouded latch land")
    for side in [-1, 1]:
        plane = 60 * side
        for n in range(6):
            x = 31.8 + (n - 2.5) * 2.06
            if side > 0:
                connector.pipe(
                    [
                        (x, plane - 2.95, 13),
                        (x, plane - 0.57, 13),
                        (x, plane + 0.34, 13),
                    ],
                    [0.72, 0.68, 0.39],
                    gold,
                    12,
                )
            else:
                connector.rings(
                    [
                        [
                            (x + u, plane + depth, 13 + v)
                            for u, v in corners(1.34, 4.52, 0.2, 2)
                        ]
                        for depth in [0.34, 0.43]
                    ],
                    gold,
                    False,
                )
        carrier.rings(
            [
                [
                    (31.8 + x, plane - layer * side, 12.6 + z)
                    for x, z in corners(15.4, 6.9, 0.55, 2)
                ]
                for layer in [3.34, 2.91 if side > 0 else 0.43]
            ],
            graphite,
            False,
        )
    register(connector, "contacts")
    register(carrier, "grey")
    tabs = Sculpture("Keyed linking tabs • opposite faces accept tongue")
    for c in [-45, 45]:
        for x in [c - 2.55, c + 2.55]:
            tabs.rings(
                [
                    [(x + u, y, 12.5 + v) for u, v in corners(width, height, 0.28, 2)]
                    for y, width, height in [
                        (57.15, 2.4, 6.3),
                        (60.2, 2.4, 6.3),
                        (61.98, 2.9, 5.7),
                        (62.55, 2.0, 5.1),
                    ]
                ],
                white,
                False,
            )
    register(tabs, "chassis")
    masks = json.loads((scripts / "ryuo-side-guides.json").read_text(encoding="utf-8"))
    for key, islands in masks.items():
        light = Sculpture("Side light mask • " + key)
        for side in (-1, 1):
            for outline, *cutouts in islands:
                cap(light, outline, cutouts, lambda u, v: side_panel_point(side, u, v), luminous)
        panel = register(light, key)
        for face in panel.data.polygons:
            if face.center.x * face.normal.x < 0:
                face.flip()
        panel.data.update()
    bezel = Sculpture("Double-sided diffuser • gasket, vent partition and recessed bores")
    for side in (-1, 1):
        def project(u, v):
            return side_panel_point(side, u, v, 60.075)

        outer = [(u+540, v+113) for u, v in corners(1060, 210, 6, 3)]
        inner = [(u+540, v+113) for u, v in corners(1053, 203, 4, 3)]
        cap(bezel, outer, [inner], project, graphite)
        cap(bezel, [(866, 11), (870, 11), (870, 215), (866, 215)], [], project, graphite)
        for px, py in side_vents():
            cap(bezel, circle(px, py, 5.76, 12), [],
                lambda u, v: side_panel_point(side, u, v, 57.86), graphite)
    panel = register(bezel, "grey")
    for face in panel.data.polygons:
        if face.center.x * face.normal.x < 0:
            face.flip()
    panel.data.update()


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    white = finish("Bone white • injection moulded frame", "e5e5e7", 0.06, 0.4)
    pad = finish("Porcelain white • isolation elastomer", "f1f1ef", 0, 0.72)
    grey = finish("Neutral grey pad print and mouldings", "85878b", 0.22, 0.44)
    black = finish("Graphite • Phillips steel", "45474a", 0.74, 0.35)
    opal = finish("Opal white • diffusing blades", "d4d9e1", 0.055, 0.36)
    medal = finish("Warm white • rotor medallion", "ecece9", 0.16, 0.3)
    foil = finish("Satin silver • printed ROG mark", "97999d", 0.46, 0.37)
    light = finish("Microprismatic side light guide", "b7e3f3", 0.06, 0.33, glow=0.7)
    gold = finish("Daisy chain • gold flash contacts", "cba059", 0.78, 0.32)
    motor_frame(white)
    corner_details(pad, black)
    stator(white, grey, white)
    impeller(opal, medal, foil)
    side_finish(white, grey, gold, light)
    collection = bpy.data.collections.new("ROG MF-12C 120 mm")
    centre_collection = bpy.data.collections.new("ROG MF-12C 120 mm • centre rail")
    bpy.context.scene.collection.children.link(collection)
    centre_collection.use_fake_user = True
    rotor = bpy.data.objects.new("Fan rotor", None)
    rotor.empty_display_type = "PLAIN_AXES"
    rotor.empty_display_size = 0.008
    collection.objects.link(rotor)
    centre_collection.objects.link(rotor)
    for key, objs in parts.items():
        for obj in objs:
            if key in ("vanes", "rotor-foil", "medallion"):
                obj.parent = rotor
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            if key != "stripes":
                collection.objects.link(obj)
            if key != "eye":
                centre_collection.objects.link(obj)
    review.mkdir(exist_ok=True, parents=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(review / "ryuo-mf12c.blend"), compress=True
    )
    bpy.context.scene.collection.children.link(centre_collection)
    for key, objs in parts.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        print(key, write_mesh(objs[0], destination / (key + ".mesh")))


if __name__ == "__main__":
    main()
