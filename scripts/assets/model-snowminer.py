import math
import runpy
import subprocess
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
library = (
    root / ".references/07-户外装备/营地照明与供电/Snow Peak SnowMiner ES-020/Blender"
)
library.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
helpers = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = helpers["Sculpture"], helpers["finish"]
ivory = finish("ES-020 glazed ivory ABS", "e3e2d7", 0, 0.32, 0.18)
amber = finish("ES-020 marigold acetal", "f29813", 0, 0.4, 0.12)
rubber = finish("ES-020 charcoal elastomer", "4c4c49", 0, 0.7)
steel = finish("Rack bent stainless steel", "abab9a", 0.77, 0.3)
contacts = finish("Stamped nickel battery contacts", "bfc2b6", 0.82, 0.26)
opal = finish("SnowMiner expanded silicone diffuser", "e5e4d2", 0, 0.54)
opal.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.12
optic = finish("SnowMiner central PMMA lens", "fbfaf4", 0, 0.063, 0.34)
optic.node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 1.49
optic.node_tree.nodes["Principled BSDF"].inputs[
    "Transmission Weight"
].default_value = 0.94
yarn = finish("SnowMiner black and ecru woven headband", "28272a", 0, 0.91)
yarn.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.24
axis = Vector((0, -0.966, 0.259)).normalized()
across = Vector((0, axis.z, -axis.y))
centre = Vector((0, -134, 59))


def local(x, y, depth):
    return centre + Vector((x, 0, 0)) + y * across + depth * axis


def world(point):
    x, h, d = point
    return (x * 0.001, -d * 0.001, h * 0.001)


def turn(name, profile, material, segments=72, close=True):
    part = Sculpture(name)
    part.rings(
        [
            [
                local(
                    radius * math.cos(i * math.tau / segments),
                    radius * math.sin(i * math.tau / segments),
                    depth,
                )
                for i in range(segments)
            ]
            for radius, depth in profile
        ],
        material,
        True,
        close,
    )
    return part.finalize()


def axial_box(part, x, y, z, w, h, length, material):
    part.rings(
        [
            [
                local(x + a * w / 2, y + b * h / 2, d)
                for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            ]
            for d in (z, z + length)
        ],
        material,
        False,
    )


def eyelet(part, centre, w, h, radius, depth, thickness, material):
    x, height, z = centre

    def loop(inset, depth_offset):
        row = []
        r = max(0.5, radius - inset)
        for mx, my, angle in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
            cx, cy = mx * (w / 2 - radius), my * (h / 2 - radius)
            for j in range(7):
                a = math.radians(angle + 90 * j / 6)
                row.append(
                    (
                        x + cx + r * math.cos(a),
                        height + cy + r * math.sin(a),
                        z + depth_offset,
                    )
                )
        return row

    part.rings(
        [
            loop(0.35, 0),
            loop(0, 0.6),
            loop(0, depth - 0.6),
            loop(0.35, depth),
            loop(thickness, depth),
            loop(thickness, 0),
            loop(0.35, 0),
        ],
        material,
        True,
        False,
    )


def webbing():
    w, h = 768, 144
    coverage = np.zeros((h, w), dtype=bool)
    pts, faces = helpers["letters"]("snow peak", False)
    for tri in faces:
        a, b, c = [
            np.array((w * 0.57 + pts[i][0] * 92, h * 0.51 + pts[i][1] * 92))
            for i in tri
        ]
        x0, y0 = np.maximum(np.floor(np.minimum(np.minimum(a, b), c)), 0).astype(int)
        x1, y1 = np.minimum(np.ceil(np.maximum(np.maximum(a, b), c)), (w, h)).astype(
            int
        )
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.ogrid[y0:y1, x0:x1]
        sides = [
            (q[0] - p[0]) * (yy + 0.5 - p[1]) - (q[1] - p[1]) * (xx + 0.5 - p[0])
            for p, q in [(a, b), (b, c), (c, a)]
        ]
        coverage[y0:y1, x0:x1] |= (np.minimum.reduce(sides) >= 0) | (
            np.maximum.reduce(sides) <= 0
        )
    yy, xx = np.mgrid[:h, :w]
    for angle in (math.pi / 2, math.pi / 6, -math.pi / 6):
        dx, dy = xx - 100, yy - 72
        stripe = (np.abs(dx * math.cos(angle) + dy * math.sin(angle)) < 45) & (
            np.abs(dy * math.cos(angle) - dx * math.sin(angle)) < 6.2
        )
        coverage[stripe] = 1
    weave = 0.035 * np.cos(
        2 * math.pi * xx / 5 + 1.4 * np.sin(yy * math.pi / 3)
    ) + 0.025 * np.sin(yy * math.pi / 2)
    panel = np.clip(0.098 + 0.72 * coverage + weave, 0.01, 1)
    reverse = np.clip(0.77 - 0.64 * coverage + weave, 0.02, 1)
    reverse[(yy < 6) | (yy >= h - 6)] = 0.10
    pixels = np.ones((h * 2, w, 4), dtype=np.float32)
    textile = np.concatenate((panel, reverse))
    pixels[:, :, :3] = np.stack(
        (textile * 0.98, textile * 0.976, textile * 0.947), axis=-1
    )
    image = bpy.data.images.new(
        "Snow Peak two-colour woven repeat", w, h * 2, alpha=False
    )
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    tex = yarn.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    yarn.node_tree.links.new(
        tex.outputs["Color"],
        yarn.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )


def ribbon(sign):
    obj = Sculpture("SnowMiner jacquard headband " + ("L" if sign < 0 else "R"))
    rows = []
    path_length = [0.0]
    control = [
        Vector((x * sign, h, d))
        for x, h, d in [
            (24, -135, 58.6),
            (30, -118, 58.6),
            (11, -42, 53 + sign * 2.5),
            (0.5, -21, 55 + sign * 2.6),
        ]
    ]
    control[0] = local(22.6 * sign, 0, 1.6)
    control[1] = local(22.6 * sign, 0, -9.3)
    for i in range(43):
        t = i / 42
        s = 1 - t
        p = (
            s**3 * control[0]
            + 3 * t * s * s * control[1]
            + 3 * t * t * s * control[2]
            + t**3 * control[3]
        )
        tangent = (
            s * s * (control[1] - control[0])
            + 2 * s * t * (control[2] - control[1])
            + t * t * (control[3] - control[2])
        ).normalized()
        twist = math.radians(65 - 48 * math.sin(math.pi * t) - 64 * t)
        width = Vector((math.cos(twist), 0, -math.sin(twist) * sign))
        if t < 0.18:
            width = (across * -sign).lerp(width, t / 0.18).normalized()
        thickness = tangent.cross(width).normalized()
        width = thickness.cross(tangent).normalized()
        rows.append(
            [
                p + width * w + thickness * d
                for w, d in [(-8.6, -0.6), (8.6, -0.6), (8.6, 0.6), (-8.6, 0.6)]
            ]
        )
        if i:
            path_length.append(path_length[-1] + (p - last).length)
        last = p
    obj.rings(rows, yarn)
    band = obj.finalize()
    for edge in band.data.edges:
        a, b = edge.vertices
        edge.use_edge_sharp = (a % 4 == b % 4) or (
            a // 4 == b // 4 and a // 4 in (0, len(rows) - 1)
        )
    uv = band.data.uv_layers.new(name="Warp and weft")
    for poly in band.data.polygons:
        sides = {band.data.loops[k].vertex_index % 4 for k in poly.loop_indices}
        offset = 0.5 if sides == {2, 3} else 0
        for loop in poly.loop_indices:
            row, col = divmod(band.data.loops[loop].vertex_index, 4)
            edge = 0.01 if (col in (0, 3)) == bool(offset) else 0.49
            uv.data[loop].uv = (path_length[row] / 94 + 0.16, offset + edge)


def threaded_strap():
    path = [
        (-22.6, 1.6),
        (-22.58, 1.98),
        (-22.14, 2.00),
        (-21.3, 1.57),
        (-20.5, 1.51),
        (-13.0, 1.51),
        (0, 1.51),
        (13.0, 1.51),
        (20.5, 1.51),
        (21.3, 1.57),
        (22.14, 2.00),
        (22.58, 1.98),
        (22.6, 1.6),
    ]
    band = Sculpture("Jacquard strap feed across articulated carrier")
    rows = []
    lengths = [0.0]
    for i, (x, z) in enumerate(path):
        p0 = Vector(path[max(0, i - 1)])
        p1 = Vector(path[min(i + 1, len(path) - 1)])
        dx, dz = (p1 - p0).normalized()
        rows.append(
            [
                local(x - dz * t, y, z + dx * t)
                for y, t in [(-8.6, -0.44), (8.6, -0.44), (8.6, 0.44), (-8.6, 0.44)]
            ]
        )
        if i:
            lengths.append(lengths[-1] + (Vector(path[i]) - Vector(path[i - 1])).length)
    band.rings(rows, yarn, False)
    data = band.finalize().data
    uv = data.uv_layers.new(name="Cross-feed woven repeat")
    for poly in data.polygons:
        for i in poly.loop_indices:
            row, side = divmod(data.loops[i].vertex_index, 4)
            uv.data[i].uv = (lengths[row] / 94 + 0.43, 0.51 if side in (0, 3) else 0.99)


def battery_compartment():
    def contour(rad, half_width, half_height, depth):
        row = []
        for index in range(144):
            angle = math.tau * index / 144
            c, s = math.cos(angle), math.sin(angle)
            r = min(
                rad, half_width / max(abs(c), 1e-8), half_height / max(abs(s), 1e-8)
            )
            row.append(local(r * c, r * s, depth))
        return row

    frame = Sculpture("White polycarbonate housing and silicone seat")
    frame.rings(
        [
            contour(r, w, h, d)
            for r, w, h, d in [
                (26.6, 25, 18.0, 2.25),
                (27.1, 27.1, 27.1, 3.9),
                (27.7, 27.7, 27.7, 5.9),
                (27.8, 27.8, 27.8, 16.5),
                (28, 28, 28, 18.1),
                (27.3, 27.3, 27.3, 19.5),
                (25.7, 25.7, 25.7, 20.2),
                (6.1, 6.1, 6.1, 20.2),
                (6.1, 6.1, 6.1, 18.2),
                (25.9, 25.9, 25.9, 18.2),
                (25.9, 24.1, 17.1, 14.1),
                (25.9, 24.1, 17.1, 4.2),
                (26.1, 24.35, 17.4, 3.15),
                (26.6, 25, 18.0, 2.25),
            ]
        ],
        ivory,
        True,
        False,
    )
    frame.finalize()["product"] = "Snow Peak SnowMiner ES-020"
    door = Sculpture("Snap-in battery door with return lip")
    door.rings(
        [
            contour(r, w, h, z)
            for r, w, h, z in [
                (26.15, 24.4, 17.3, 2.05),
                (26.3, 24.7, 17.65, 2.25),
                (26.2, 24.6, 17.55, 3.10),
                (25.5, 23.8, 16.6, 3.5),
                (25.1, 23.35, 16.1, 3.5),
                (25.0, 23.25, 16.0, 3.05),
            ]
        ],
        ivory,
    )
    for x in (-11, 11):
        axial_box(door, x, -17.4, 2.55, 3.2, 1.55, 0.64, ivory)
    for x in (-3.45, 3.45):
        axial_box(door, x, 18.5, 2.6, 1.55, 5.0, 1.05, ivory)
    axial_box(door, 0, 20.48, 2.6, 8.45, 1.2, 1.05, ivory)
    door.finalize()
    tray = Sculpture("Three scalloped AAA battery wells")
    for y in (-10.8, 0, 10.8):
        section = (
            [(-5.47, 4.3), (-5.47, 8.7)]
            + [
                (
                    -5.40 * math.cos(a * math.pi / 20),
                    8.7 + 5.40 * math.sin(a * math.pi / 20),
                )
                for a in range(21)
            ]
            + [
                (5.47, 8.7),
                (5.47, 4.3),
                (5.61, 4.3),
                (5.61, 14.9),
                (-5.61, 14.9),
                (-5.61, 4.3),
            ]
        )
        tray.rings(
            [
                [
                    local(
                        sign * min(22.9, math.sqrt(25.85**2 - (y + yy) ** 2)), y + yy, d
                    )
                    for yy, d in section
                ]
                for sign in (-1, 1)
            ],
            ivory,
        )
        tray.label(
            "AAA / LR03  1.5V",
            0.98,
            lambda x, h, y=y: local(x, y + h, 14.03 - h * h / 10.8),
            ivory,
        )
    tray.finalize()["insideBatteryDoor"] = True
    nickel = Sculpture("Six folded nickel battery terminals")
    for row, y in enumerate((-10.8, 0, 10.8)):
        for end in (-1, 1):
            positive = end == (1 if row == 1 else -1)
            spring = [
                (22.98, 4.5),
                (22.98, 11.5),
                (22.8, 12.0),
                (22.45, 11.7),
                (22.12 if positive else 21.62, 8.7),
                (22.4, 5.9),
            ]
            for x, d in zip(spring, spring[1:]):
                nickel.rings(
                    [
                        [
                            local(end * u + dx, y + dy, v)
                            for dx, dy in [
                                (-0.09, -1.5),
                                (0.09, -1.5),
                                (0.09, 1.5),
                                (-0.09, 1.5),
                            ]
                        ]
                        for u, v in (x, d)
                    ],
                    contacts,
                    False,
                )
    nickel.finalize()["insideBatteryDoor"] = True
    screw = Sculpture("Four recessed cruciform fasteners")
    recess = finish("ES-020 screw drive shadow", "585b57", 0.53, 0.46)
    for x in (-11.5, 11.5):
        for y in (-12.4, 12.4):
            depth = 8.7 + math.sqrt(5.4**2 - 1.6**2)
            rings = [
                [
                    local(
                        x + r * math.cos(i * math.tau / 24),
                        y + r * math.sin(i * math.tau / 24),
                        z,
                    )
                    for i in range(24)
                ]
                for r, z in (
                    (1.23, depth + 0.2),
                    (1.23, depth - 0.06),
                    (0.98, depth - 0.26),
                )
            ]
            screw.rings(rings, contacts)
            cross = [
                (0.18, 0.18),
                (0.72, 0.18),
                (0.72, -0.18),
                (0.18, -0.18),
                (0.18, -0.72),
                (-0.18, -0.72),
                (-0.18, -0.18),
                (-0.72, -0.18),
                (-0.72, 0.18),
                (-0.18, 0.18),
                (-0.18, 0.72),
                (0.18, 0.72),
            ]
            screw.add(
                [local(x + xx, y + yy, depth - 0.28) for xx, yy in cross],
                [tuple(range(len(cross)))],
                recess,
                False,
            )
    screw.finalize()["insideBatteryDoor"] = True
    sleeve = finish("Neutral charcoal alkaline-cell sleeve", "4d5050", 0.28, 0.38)
    insulation = finish("Alkaline-cell insulating shoulder", "e1dccf", 0.0, 0.50)
    for index, y in enumerate((-10.8, 0, 10.8), start=1):
        polarity = 1 if index == 2 else -1
        cell = Sculpture(f"AAA LR03 cell {index}")

        def surface(x, radius):
            return [
                local(
                    x * polarity,
                    y + radius * math.cos(i * math.tau / 48),
                    8.55 + radius * math.sin(i * math.tau / 48),
                )
                for i in range(48)
            ]

        for material, profile in [
            (
                contacts,
                [(-21.62, 3.45), (-21.58, 4.72), (-21.37, 5.02), (-21.15, 5.02)],
            ),
            (sleeve, [(-21.15, 5.02), (-20.98, 5.12), (20.0, 5.12), (20.32, 4.98)]),
            (insulation, [(20.32, 4.98), (20.55, 4.81), (20.55, 2.07)]),
            (contacts, [(20.55, 2.07), (20.64, 1.93), (21.92, 1.83), (22.1, 1.59)]),
        ]:
            cell.rings([surface(x, r) for x, r in profile], material, close=False)
        cell.add(surface(-21.62, 3.45), [tuple(range(48))], contacts, False)
        cell.add(surface(22.1, 1.59), [tuple(range(48))], contacts, False)
        item = cell.finalize()
        item["batteryType"] = "IEC LR03 / AAA"
        item["insideBatteryDoor"] = True


def build():
    pin = Sculpture("Rack removable pin with bent rear tang and toe")
    pin.pipe(
        [
            (0, 8, -2.8),
            (0, 7, -5.7),
            (0, 4, -7),
            (0, 0, -5),
            (0, 0, 1.5),
            (0, -2.5, 4),
            (0, -2.5, 9),
            (0, -2.5, 19),
            (0, -2.5, 56),
            (0, -2.1, 60),
            (0, 1, 63),
            (0, 5.8, 63.5),
        ],
        2.0,
        steel,
        16,
    )
    pin.pipe([(0, -2.4, 5), (0, -8, 4), (0, -12, 1.8)], 1.85, steel, 14)
    pin_mesh = pin.finalize().data
    shade = pin_mesh.color_attributes.new(
        name="Peg socket occlusion", type="BYTE_COLOR", domain="POINT"
    )
    base = steel.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
    colour = tuple(base.default_value)[:3]
    for vertex in pin_mesh.vertices:
        depth = max(0, -vertex.co.y)
        exposure = 1 - 0.57 * math.exp(-depth / 0.004)
        shade.data[vertex.index].color = (*[c * exposure for c in colour], 1)
    color_node = steel.node_tree.nodes.new("ShaderNodeVertexColor")
    color_node.layer_name = shade.name
    steel.node_tree.links.new(color_node.outputs["Color"], base)
    hook = Sculpture("Marigold folding J-hook and headband guide")
    eyelet(hook, (0, -22, 52), 23, 9, 3.8, 7.4, 2.1, amber)
    shape = [
        (6, -19),
        (9, -14),
        (10, -8),
        (9.7, -3),
        (8.2, 0.4),
        (5.5, 2.65),
        (2.2, 3.95),
        (-1.8, 4),
        (-5.4, 2.4),
        (-7.8, -0.7),
        (-8.4, -3.7),
        (-7.5, -5.9),
    ]
    hook.pipe(
        [(x, h - 2.05, 55.7) for x, h in shape],
        [2.5, 2.5, 2.6, 2.6, 2.55, 2.5, 2.5, 2.45, 2.4, 2.35, 2.2, 1.7],
        amber,
        18,
        1.55,
    )
    hook.finalize()
    webbing()
    ribbon(-1)
    ribbon(1)
    threaded_strap()
    slide = Sculpture("Marigold double-slot tension slide")
    eyelet(slide, (-15.9, -76, 57.6), 21.2, 13, 3, 2.3, 1.7, amber)
    slide.pipe([(-24.3, -76, 59), (-7.4, -76, 59)], 1.1, amber, 12)
    for x in range(-22, -8, 2):
        slide.pipe(
            [(x, -77.65, 59.3), (x, -76.7, 60.5), (x, -75.2, 60.7), (x, -74.5, 59.8)],
            0.58,
            amber,
            10,
        )
    slide.finalize()
    cradle = turn(
        "Marigold articulated cradle",
        [
            (19, -3.9),
            (25.2, -3.45),
            (27, -1.9),
            (27.5, -0.7),
            (27.2, 0.25),
            (24.4, 1.0),
        ],
        amber,
    )
    slots = []
    for sign in (-1, 1):
        cutter = Sculpture("Webbing passage")
        axial_box(cutter, sign * 22.6, 0, -6.5, 3.65, 18.9, 9.1, ivory)
        slots.append(cutter.finalize())
    solids = runpy.run_path(str(scripts / "product_solids.py"))
    solids["subtract"](cradle, slots)
    battery_compartment()
    pivot = Sculpture("Hinged cradle pivot and carriers")
    for x in (-13, 13):
        pivot.pipe(
            [local(x, -14, 0), local(x, -17, 3), local(x, -19, 6)], 2.7, amber, 20
        )
    pivot.pipe([local(-17, -18, 5.4), local(17, -18, 5.4)], 2.2, amber, 18)
    pivot.finalize()
    turn(
        "Expanded silicone dome and retaining bead",
        [
            (25.4, 18),
            (27, 18.3),
            (27.7, 18.9),
            (27.9, 20),
            (27.55, 22),
            (26.9, 25),
            (25.7, 28.4),
            (23.7, 32.1),
            (20.9, 35.5),
            (17.3, 38.8),
            (13.7, 41),
            (10.9, 42.6),
            (10.25, 42.7),
            (9.9, 42.55),
            (9.85, 41.65),
            (10.5, 41.55),
            (16.7, 37.95),
            (22.9, 31.6),
            (25.9, 24.8),
            (26.7, 19.85),
            (25.4, 18),
        ],
        opal,
        close=False,
    )
    ferrule = finish(
        "SnowMiner champagne magnetic retaining seat", "d2bf93", 0.62, 0.29
    )
    turn(
        "Optic collar and magnetic retaining seat",
        [
            (9.78, 40.7),
            (9.93, 41.65),
            (9.42, 41.93),
            (8.94, 41.90),
            (8.85, 41.66),
            (7.85, 41.65),
            (7.74, 41.88),
            (6.32, 41.85),
            (6.12, 42.12),
            (5.50, 42.12),
            (5.38, 41.90),
            (5.38, 40.7),
            (9.78, 40.7),
        ],
        ferrule,
        close=False,
    )
    turn(
        "Transparent bezel and annular seal",
        [
            (10.1, 41.6),
            (10.32, 42.3),
            (10.10, 42.82),
            (9.87, 42.96),
            (9.45, 42.96),
            (9.25, 42.67),
            (8.93, 42.63),
            (8.76, 42.54),
            (6.35, 42.62),
            (6.12, 43.01),
            (5.73, 43.06),
            (5.43, 42.89),
            (5.37, 42.3),
            (5.37, 42.13),
            (9.50, 42.04),
            (10.1, 41.6),
        ],
        optic,
        close=False,
    )
    for side in (-1, 1):
        lug = Sculpture(f"Translucent optic retention lug {side:+d}")
        lug.rings(
            [
                [
                    local(side * x, y, z)
                    for x, y in [
                        (9.4, -1.7),
                        (10.8, -1.95),
                        (11.65, -1.25),
                        (11.9, 0),
                        (11.65, 1.25),
                        (10.8, 1.95),
                        (9.4, 1.7),
                    ]
                ]
                for z in (41.6, 42.6)
            ],
            optic,
        )
        lug.finalize()
    turn(
        "Clear optic insert and concentric lens",
        [
            (5.37, 41.45),
            (5.49, 42.6),
            (5.40, 43.05),
            (4.60, 43.35),
            (4.25, 43.80),
            (3.85, 44.24),
            (3.2, 44.7),
            (1.9, 45.15),
            (0.1, 45.25),
        ],
        optic,
    )
    diode = Sculpture("LED ceramic package and phosphor emitter")
    ceramic = finish("LED ceramic package", "e6dfc5", 0, 0.48)
    phosphor = finish("LED phosphor", "f0cd77", 0, 0.42)
    axial_box(diode, 0, 0, 19.8, 4.4, 4.4, 0.72, ceramic)
    axial_box(diode, 0, 0, 20.53, 2.65, 2.65, 0.25, phosphor)
    diode.finalize()
    key = Sculpture("Elastomer push button with moulded asterisk")
    key.rings(
        [
            [
                local(
                    5.5 * r * math.cos(a * math.tau / 40),
                    y,
                    11.7 + 4.0 * r * math.sin(a * math.tau / 40),
                )
                for a in range(40)
            ]
            for r, y in [(0.94, 26.9), (1, 27.42), (0.86, 27.78)]
        ],
        rubber,
    )
    for a in (0, math.pi / 3, 2 * math.pi / 3):
        key.pipe(
            [
                local(-1.9 * math.cos(a), 27.86, 11.7 - 1.9 * math.sin(a)),
                local(1.9 * math.cos(a), 27.86, 11.7 + 1.9 * math.sin(a)),
            ],
            0.17,
            rubber,
            8,
        )
    key.finalize()
    for name, position in [
        ("SnowMiner optical exit", local(0, 0, 46.5)),
        ("SnowMiner throw axis", local(0, 0, 246.5)),
    ]:
        marker = bpy.data.objects.new(name, None)
        marker.empty_display_size = 0.002
        marker.location = world(position)
        bpy.context.collection.objects.link(marker)


build()
scene = bpy.context.scene
scene.name = "Snow Peak SnowMiner ES-020 • hanging lantern"
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_location = (0, -0.06, -0.09)
            space.region_3d.view_distance = 0.30
            space.region_3d.view_rotation = Vector((-0.23, -1, -0.15)).to_track_quat(
                "Z", "Y"
            )
            space.overlay.show_overlays = False
            space.shading.type = "MATERIAL"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(
    filepath=str(library / "snowminer-es-020.blend"), compress=True
)
optic.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0
optic.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.43
optic.surface_render_method = "BLENDED"
product = root / "public/media/models/snowminer-es-020.glb"
bpy.ops.export_scene.gltf(
    filepath=str(product),
    export_apply=True,
    export_extras=True,
    export_image_format="WEBP",
    export_image_quality=94,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(product)], check=True
)
