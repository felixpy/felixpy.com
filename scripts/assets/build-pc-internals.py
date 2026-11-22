import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import (
    barrel,
    bevel,
    block,
    export_batch,
    pipe,
    sample_bezier,
    spun,
    xyz,
)
from coolant_diffuser import opal_finish

SLOTS = json.loads(
    (Path(__file__).resolve().parents[2] / "src/scene/dimm-slots.json").read_text()
)
MODULE_SEAT_MM = 3.60


def board(u, v, h):
    return (77 - h, 194 - v, -289 + u)


def profile(name, face, offset, radius=0):
    points = [Vector(p) for p in face]
    depth = Vector(offset)
    n = len(points)
    vertices = [xyz(p) for p in points] + [xyz(p + depth) for p in points]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    return bevel(obj, radius)


def component(name, u, v, h, du, dv, dh, r=0):
    obj = block(name, (dh, dv, du), board(u, v, h), r if r > 0.40 else 0)
    for mod in obj.modifiers:
        if mod.type == "BEVEL":
            mod.segments = 1
    return obj


def plate(name, outline, h, t, r=0.5):
    return profile(
        name, [board(u, v, h) for u, v in outline], (-t, 0, 0), r if r >= 0.3 else 0
    )


def swept_braid(name, center, r, rings, *, diffuser=False):
    points = sample_bezier(center, 0.095 if r > 2 else 0.085)
    center.hide_render = True
    center.hide_set(True)
    verts = []
    faces = []
    length = [0.0]
    axis = Vector((1, 0, 0))
    for i, point in enumerate(points):
        before = (point - points[max(0, i - 1)]).normalized()
        after = (points[min(i + 1, len(points) - 1)] - point).normalized()
        t = (before + after).normalized()
        if abs(axis.dot(t)) > 0.97:
            axis = Vector((0, 0, 1))
        axis = (axis - t * axis.dot(t)).normalized()
        v = t.cross(axis)
        for j in range(rings):
            a = j * math.tau / rings
            verts.append(point + r * 0.001 * (math.cos(a) * axis + math.sin(a) * v))
        if i:
            length.append(length[-1] + (point - points[i - 1]).length)
            for j in range(rings):
                a = (i - 1) * rings + j
                b = (i - 1) * rings + (j + 1) % rings
                faces.append((a, b, b + rings, a + rings))
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    uv = data.uv_layers.new(name="Sleeve travel" if diffuser else "Sleeve yarn pitch")
    weave_repeats = 3 if r > 2 else 1
    for poly in data.polygons:
        poly.use_smooth = True
        seam = poly.index % rings == rings - 1
        for k in poly.loop_indices:
            row, col = divmod(data.loops[k].vertex_index, rings)
            around = 1.0 if seam and col == 0 else col / rings
            if diffuser:
                uv.uv[k].vector = (around, length[row] / length[-1])
            else:
                uv.uv[k].vector = (
                    around * weave_repeats,
                    length[row] * weave_repeats / (0.001 * math.tau * r),
                )
    return obj, points, length[-1]


def coolant_centerline(off):
    up, right = Vector((0, 1, 0)), Vector((1, 0, 0))
    radius, inlet, outlet = 17, 11.5, 14
    lean = -24 / (2 * radius)
    turn = Vector((0, math.sqrt(1 - lean**2), lean))
    start = Vector((32.5, 167, -164 + off))
    straight_in = 1.5
    straight_out = 227.9 - start.y - straight_in - inlet - 2 * radius * turn.y - outlet
    runs = 200 - straight_in - straight_out - math.pi * (radius + (inlet + outlet) / 2)
    return_x = (start.x - inlet + 62 - outlet - runs) / 2
    sections = []

    def straight(origin, direction, distance):
        end = origin + direction * distance
        sections.append((origin.lerp(end, 1 / 3), origin.lerp(end, 2 / 3), end))
        return end

    def bend(origin, entering, leaving, r):
        end = origin + r * (entering + leaving)
        handle = 4 * math.tan(math.pi / 8) * r / 3
        sections.append((origin + entering * handle, end - leaving * handle, end))
        return end

    p = straight(start, up, straight_in)
    p = bend(p, up, -right, inlet)
    p = straight(p, -right, p.x - return_x)
    p = bend(p, -right, turn, radius)
    p = bend(p, turn, right, radius)
    p = straight(p, right, 62 - outlet - p.x)
    p = bend(p, right, up, outlet)
    straight(p, up, straight_out)
    curve = pipe(
        "Ryuo FEP mandrel-formed centerline", [start, *(s[2] for s in sections)], 0
    )
    nodes = curve.data.splines[0].bezier_points
    for node in nodes:
        node.handle_left_type = node.handle_right_type = "FREE"
    for i, (a, b, _) in enumerate(sections):
        nodes[i].handle_right, nodes[i + 1].handle_left = xyz(a), xyz(b)
    return curve


def cooling():
    hoses = []
    fittings = []
    sleeves = []
    all_samples = []
    opal = opal_finish()
    for off in (-10, 10):
        hose, points, length = swept_braid(
            "Rear FEP · opal sleeve" if off < 0 else "Forward FEP · opal sleeve",
            coolant_centerline(off), 5.75, 32, diffuser=True
        )
        hoses.append(hose)
        hose.data.materials.append(opal)
        all_samples.append(points)
        if abs(0.200 - length) > 0.0015:
            raise ValueError(f"Incorrect coolant line length {length}")
        for x, z, levels in [
            (
                32.5,
                -164 + off,
                [(143.7, 155.7, 7.0), (155.7, 163.4, 7.85), (163.4, 168.2, 6.65)],
            ),
            (
                62,
                -188 + off,
                [(227, 230.5, 6.65), (230.5, 234.5, 7.45), (234.5, 237.6, 7.9)],
            ),
        ]:
            for lo, hi, r in levels:
                fittings.append(
                    barrel(
                        "Turned compression ferrule",
                        (x, lo, z),
                        (x, hi, z),
                        r,
                        48,
                        r - 0.20,
                    )
                )
            for y in (levels[1][0] + 0.25, levels[1][1] - 0.6):
                sleeves.append(
                    barrel(
                        "Compression collar groove",
                        (x, y, z),
                        (x, y + 0.45, z),
                        levels[1][2] + 0.1,
                        48,
                    )
                )
            mouth, sign = (168.2, 1) if x == 32.5 else (227, -1)
            profile = sorted(
                (mouth + sign * dy, r)
                for dy, r in [
                    (0, 6.45),
                    (0.45, 6.45),
                    (1.15, 6.22),
                    (1.7, 5.95),
                    (1.8, 5.68),
                ]
            )
            sleeves.append(spun("Radiused strain-relief lip", (x, z), 40, profile))
        for point in points:
            x, y, z = point.x * 1000, point.z * 1000, -point.y * 1000
            if y > 210 and x < 58.75:
                raise ValueError(f"Coolant braid overlaps fan housing: {x}, {y}")
            if z > -109 and y < 189:
                raise ValueError(f"Coolant braid overlaps DIMM field: {z}, {y}")
    separation = min((a - b).length for a in all_samples[0] for b in all_samples[1])
    if separation < 0.012:
        raise ValueError(f"Coolant lines overlap ({separation})")
    print(
        f"Coolant tube length {length * 1000:.1f} mm, minimum separation {separation * 1000 - 11.5:.1f} mm"
    )
    return {"aio-braid": hoses, "aio-fittings": fittings, "aio-seals": sleeves}


def power_harness():
    ivory = []
    carbon = []
    shell = []
    cuts = []
    shell.extend(
        [
            block(
                "Fully seated 24-pin keyed plug",
                (13, 50.9, 11.2),
                board(233.4, 64, 15.5),
                0.7,
            ),
            block("Locking spring clip", (9.5, 12.1, 2), board(227.2, 64, 15.5), 0.45),
        ]
    )
    for row in range(2):
        for pin in range(12):
            v = 64 + (pin - 5.5) * 4.2
            u = 233.4 + (row - 0.5) * 4.2
            shell.append(
                barrel(
                    "Crimp wire collar",
                    board(u, v, 21.6),
                    board(u, v, 24.2),
                    1.94,
                    20,
                    1.7,
                )
            )
            target = 128 + (5.5 - pin) * 3.48 + row * 0.3
            spread = (5.5 - pin) * 3.35
            layer = 103.2 + row * 3.45
            socket_x = -58 if pin < 8 else -40
            terminal_y = -215 + (pin - 3.5) * 3.9 if pin < 8 else -208 + (pin - 9.5) * 3.9
            terminal_x = socket_x + (row - .5) * 3.9
            path = [
                board(u, v, 23.8),
                board(u + 0.65, v - 0.1, 28.5),
                board(u + 5.4, v - 0.3, 36.9 + row * 4.1),
                board(255, v + 0.3, 41.2 + row * 4.0),
                board(273, v + 1.2, 36 + row * 4),
                board(283, v + 2.5, 24 + row * 4.2),
                (69.5 - row * 2.2, target + 3, -4.0 + row * 4.2),
                (88.6, target, -1.8 + row * 4.6),
                (103, target - 1.0, 3 + row * 4.6),
                (106.5, target - 6.2, 8.2 + row * 4.6),
                (layer, 82 + spread * .48, 17 + spread * .9),
                (layer, 57, 16 + spread),
                (layer, 28, 3 + spread),
                (layer, -9, -32 + spread),
                (layer, -44, -45 + spread),
                (layer, -147, -45 + spread),
                (layer, -188, -53 + spread),
                (99 + row * 3.4, terminal_y + 4, -58 + spread),
                (77, terminal_y, -58 + spread),
                (22, terminal_y, -58 + spread),
                (terminal_x + 11, terminal_y, -64 + spread * .40),
                (terminal_x, terminal_y, -78),
                (terminal_x, terminal_y, -90),
            ]
            lead, points, _ = swept_braid(
                "Individually sleeved ATX conductor",
                pipe("ATX conductor centerline", path, 0),
                1.46,
                14,
            )
            before, after = next(
                (a, b) for a, b in zip(points, points[1:]) if a.y >= 0.031 >= b.y
            )
            crosses = before.lerp(after, (0.031 - before.y) / (after.y - before.y))
            cuts.append((-1000 * crosses.y, 1000 * crosses.x, 1000 * crosses.z))
            (ivory if pin in [1, 2, 5, 6, 9, 10] else carbon).append(lead)
    xs = [p[1] for p in cuts]
    ys = [p[2] for p in cuts]
    x0, x1 = min(xs) - 2.3, max(xs) + 2.3
    y0, y1 = min(ys) - 2.2, max(ys) + 2.2
    comb = block(
        "Removable twin-row cable comb",
        (x1 - x0, y1 - y0, 2.65),
        ((x0 + x1) / 2, (y0 + y1) / 2, -31),
        0.65,
    )
    bpy.context.view_layer.objects.active = comb
    for mod in list(comb.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for _, cx, cy in cuts:
        cutter = barrel(
            "Individual conductor opening", (cx, cy, -34), (cx, cy, -28), 1.77, 20
        )
        mod = comb.modifiers.new("Slotted wire opening", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
        bpy.context.view_layer.objects.active = comb
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    eps_leads, eps_plugs = [], []
    for label, u0 in [("A", 53.5), ("B", 74)]:
        eps_plugs.extend(
            [
                block(
                    f"EPS12V {label} keyed plug",
                    (10.0, 9.1, 17.9),
                    board(u0, 4.6, 13.7),
                    0.55,
                ),
                block(
                    f"EPS12V {label} latching tab",
                    (8.0, 1.4, 6.9),
                    board(u0, -0.2, 13.8),
                    0.4,
                ),
            ]
        )
        for col in range(4):
            for row in range(2):
                u, v = u0 + (col - 1.5) * 4.2, 4.6 + (row - 0.5) * 4.2
                _, y, z = board(u, v, 0)
                height = 224.1 + (0.5 - row) * 3.5
                path = [
                    board(u, v, 19.1),
                    board(u, v, 23.5),
                    (50.5 - 3.8 * row, y + 4, z),
                    (52.2 - row * 3.7, y + 12, z),
                    (65.2, height - 10.5, z),
                    (75.5, height - 2.4, z),
                    (88.5, height, z),
                    (99.8 + 3.5 * row, height - 2.6, z),
                    (105 + 3.5 * row, height - 10, z),
                    (106 + 3.5 * row, height - 42, z),
                ]
                name = f"EPS12V {label} crimp lead {row + 1}.{col + 1}"
                eps_plugs.append(
                    barrel(
                        name + " throat",
                        board(u, v, 18.6),
                        board(u, v, 20.4),
                        1.86,
                        16,
                        1.62,
                    )
                )
                lead, _, _ = swept_braid(
                    name, pipe(name + " centerline", path, 0), 1.36, 12
                )
                eps_leads.append(lead)
    return {
        "atx-ivory": ivory,
        "atx-charcoal": carbon,
        "atx-shell": shell,
        "atx-comb": [comb],
        "eps-sleeves": eps_leads,
        "eps-plugs": eps_plugs,
    }


def regulators():
    metal = []
    ceramic = []
    black = []
    silver = []
    ceramic.append(
        plate(
            "White rear I/O armour with angled cheek",
            [(-11, 1), (6, 1), (77, 62), (77, 145), (62, 155), (-11, 155)],
            2,
            27,
            1.1,
        )
    )
    ceramic.append(
        plate(
            "Raised diagonally relieved face",
            [(-12, -12), (-3, -12), (64, 48), (64, 143), (56, 150), (-12, 95)],
            27,
            8.5,
            1.2,
        )
    )
    metal.append(
        plate(
            "Rear I/O edge return",
            [(-14, -12), (-11, -12), (-11, 149), (-14, 146)],
            1,
            32,
            0.35,
        )
    )
    for j in range(22):
        top = 99 + j * 2.05
        metal.append(
            plate(
                "Vent louvre",
                [(-10, top), (15, top + 21), (17, top + 22), (-10, top + 1.25)],
                29.4,
                1,
                0.10,
            )
        )
    for j in range(3):
        metal.append(
            plate(
                "Exposed side slashes",
                [
                    (65, 70 + j * 8),
                    (75, 79 + j * 8),
                    (75, 82 + j * 8),
                    (65, 73 + j * 8),
                ],
                29,
                2.3,
                0.2,
            )
        )
    metal.append(
        plate(
            "VRM heatsink base",
            [
                (36, 14),
                (85, 14),
                (91, 7),
                (149, 7),
                (173, 13),
                (181, 21),
                (173, 32),
                (70, 35),
                (53, 31),
            ],
            2,
            17,
            0.7,
        )
    )
    for j in range(5):
        metal.append(
            plate(
                "VRM fin stack",
                [
                    (49 + j * 0.8, 15 + j * 3),
                    (166, 10 + j * 4),
                    (177 - j, 12 + j * 4),
                    (173 - j, 13.8 + j * 4),
                    (53 + j, 16.8 + j * 3),
                ],
                18,
                4.8,
                0.25,
            )
        )
    ceramic.append(
        plate(
            "Stepped VRM crown",
            [
                (76, 14),
                (85, 14),
                (95, 3),
                (151, 3),
                (164, 16),
                (169, 17),
                (169, 22),
                (90, 23),
                (82, 20),
                (66, 20),
            ],
            21,
            4.5,
            0.65,
        )
    )
    for u, v, count, du, dv in [
        (95, 39, 9, 7.5, 0),
        (84, 57, 9, 0, 7.5),
        (202, 168, 4, 7, 0),
        (98, 131, 2, 10, 0),
    ]:
        for i in range(count):
            a, b = u + i * du, v + i * dv
            black.append(
                barrel(
                    "Polymer capacitor sleeve",
                    board(a, b, 0.2),
                    board(a, b, 7),
                    3.15,
                    15,
                )
            )
            silver.append(
                barrel(
                    "Stamped capacitor seal",
                    board(a, b, 6.9),
                    board(a, b, 7.25),
                    2.82,
                    15,
                )
            )
    for slot in SLOTS:
        u = slot["centerMm"]
        for side in (-1, 1):
            black.append(
                component(
                    "Keyed DIMM slot channel wall",
                    u + side * 2.4,
                    81,
                    4.3,
                    1.6,
                    137,
                    8.3,
                    0.32,
                )
            )
        for v in (10.9, 151.1):
            black.append(
                component("Positive retention clip", u, v, 7.2, 6.8, 5.6, 12.2, 0.58)
            )
        for side in (-1, 1):
            black.append(component("DIMM socket floor rail", u + side * 2.05, 81, 1.1, 2.4, 134, 2.1, 0.16))
        key_height = MODULE_SEAT_MM + 3.65
        black.append(component("DDR5 polarizing key", u, 77.3, key_height / 2, 5.8, 1.1, key_height, 0.12))
    return {
        "board-heatsinks": metal,
        "board-shells": ceramic,
        "board-components": black,
        "board-caps": silver,
    }


def load_memory():
    root = Path(__file__).resolve().parents[2]
    native = root / ".review/atelier/pc-components/xpg-d50-fubuki.blend"
    name = "XPG D50 ROG Strix Fubuki DDR5"
    if native.is_file():
        with bpy.data.libraries.load(str(native)) as (_, source):
            source.collections = [name]
        group = source.collections[0]
    else:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(root / "public/media/models/xpg-d50-fubuki.glb"))
        group = bpy.data.collections.new(name)
        for obj in set(bpy.data.objects) - before:
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            group.objects.link(obj)
    bpy.context.scene.collection.children.link(group)
    return group


def module_origin(slot):
    return xyz(board(slot["centerMm"], 81, MODULE_SEAT_MM))


def verify_clearances(parts, memory):
    graph = bpy.context.evaluated_depsgraph_get()

    def triangles(items):
        vertices = []
        faces = []
        for obj, offset in items:
            ev = obj.evaluated_get(graph)
            data = ev.to_mesh()
            data.calc_loop_triangles()
            first = len(vertices)
            vertices.extend(
                ev.matrix_world @ vertex.co + offset for vertex in data.vertices
            )
            faces.extend(
                tuple(first + i for i in triangle.vertices)
                for triangle in data.loop_triangles
            )
            ev.to_mesh_clear()
        return BVHTree.FromPolygons(vertices, faces, all_triangles=True), vertices

    zero = Vector((0, 0, 0))
    hose, skin = triangles([(o, zero) for o in parts["aio-braid"]])
    boards = [
        (o, zero) for name in ["board-heatsinks", "board-shells"] for o in parts[name]
    ]
    modules = [
        [
            (o, module_origin(slot)) for o in memory.all_objects if o.type == "MESH"
        ]
        for slot in SLOTS
    ]
    ram = [item for module in modules for item in module]
    for i in range(1, len(modules)):
        previous, _ = triangles(modules[i - 1])
        current, points = triangles(modules[i])
        if previous.overlap(current):
            raise ValueError("Adjacent DIMM heat spreaders intersect")
        gap = min(previous.find_nearest(v)[3] for v in points)
        print(
            f"{SLOTS[i - 1]['name']} to {SLOTS[i]['name']} module gap: {gap * 1000:.2f} mm"
        )
    for name, items in [("VRM and I/O armor", boards), ("installed DIMMs", ram)]:
        other, _ = triangles(items)
        if hose.overlap(other):
            raise ValueError("Tubing penetrates " + name)
        distance = min(other.find_nearest(point)[3] for point in skin)
        print(f"Outside tube surface to {name}: {1000 * distance:.1f} mm")
    interior = [
        (o, zero) for name in ["atx-ivory", "atx-charcoal"] for o in parts[name]
    ]
    cables, cable_points = triangles(interior)
    memory, memory_points = triangles(ram)
    socket_parts = [o for o in parts["board-components"] if o.name.startswith(
        ("Keyed DIMM", "Positive retention", "DIMM socket", "DDR5 polarizing")
    )]
    for prefix in ("Keyed DIMM", "Positive retention", "DIMM socket", "DDR5 polarizing"):
        shell, points = triangles([(o, zero) for o in socket_parts if o.name.startswith(prefix)])
        if memory.overlap(shell):
            raise ValueError("Memory penetrates " + prefix)
        distance = min(min(memory.find_nearest(p)[3] for p in points), min(shell.find_nearest(p)[3] for p in memory_points))
        print(f"{prefix} to installed D50: {1000 * distance:.2f} mm")
    if cables.overlap(memory):
        raise ValueError("ATX harness penetrates memory")
    print(
        f"ATX cable to installed modules: {1000 * min(memory.find_nearest(v)[3] for v in cable_points):.1f} mm"
    )
    processors, _ = triangles([(o, zero) for o in parts["eps-sleeves"]])
    if hose.overlap(processors):
        raise ValueError("CPU supply intersects the cooling lines")
    print(
        f"Coolant to EPS12V sleeves: {1000 * min(processors.find_nearest(v)[3] for v in skin):.1f} mm"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("public/media/models"))
    parser.add_argument("--blend", type=Path)
    parser.add_argument("--atx-outlet", action="store_true")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.atx_outlet:
        directory = (
            Path(__file__).resolve().parents[2]
            / ".references/03-电脑硬件/电源与机箱布线/ATX and EPS power cables/Blender/Components"
        )
        for name, objects in power_harness().items():
            if name not in ("atx-ivory", "atx-charcoal", "atx-comb"):
                continue
            group = bpy.data.collections.new(name)
            for obj in objects:
                group.objects.link(obj)
            bpy.data.libraries.write(
                str(directory / (name + ".blend")), {group}, compress=True
            )
            bpy.data.collections.remove(group)
            print(name, export_batch(name, objects, args.out / (name + ".mesh")))
        return
    modules = load_memory()
    parts = {**power_harness(), **cooling()}
    board_reference = regulators()
    bpy.context.view_layer.update()
    verify_clearances({**parts, **board_reference}, modules)
    bpy.context.scene.collection.children.unlink(modules)
    for name, objects in parts.items():
        print(name, export_batch(name, objects, args.out / f"{name}.mesh"))
    if args.blend:
        for slot in SLOTS:
            obj = bpy.data.objects.new("Populated DDR5 socket " + slot["name"], None)
            obj.instance_type = "COLLECTION"
            obj.instance_collection = modules
            obj.location = module_origin(slot)
            bpy.context.collection.objects.link(obj)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))


if __name__ == "__main__":
    main()
