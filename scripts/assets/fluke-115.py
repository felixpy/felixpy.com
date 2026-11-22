import math
import random
from pathlib import Path

import bpy
from mathutils import Vector, geometry


def circle(x, y, r, count=48):
    return [
        (x + r * math.cos(i * math.tau / count), y + r * math.sin(i * math.tau / count))
        for i in range(count)
    ]


def curved(points, steps=4):
    result = []
    for i, p in enumerate(points):
        a, b, c = (points[(i + step) % len(points)] for step in (-1, 1, 2))
        for j in range(steps):
            t = j / steps
            result.append(
                tuple(
                    (
                        (2 * p[k])
                        + (b[k] - a[k]) * t
                        + (2 * a[k] - 5 * p[k] + 4 * b[k] - c[k]) * t * t
                        + (3 * p[k] - a[k] - 3 * b[k] + c[k]) * t * t * t
                    )
                    / 2
                    for k in (0, 1)
                )
            )
    return result


def inside(p, ring):
    x, y = p
    crosses = 0
    for (a, b), (c, d) in zip(ring, ring[1:] + ring[:1]):
        if (b > y) != (d > y) and x < a + (c - a) * (y - b) / (d - b):
            crosses += 1
    return crosses % 2


def panel(shape, outline, holes, z, material):
    rings = [outline, *holes]
    points = [Vector(p) for ring in rings for p in ring]
    edges = []
    start = 0
    for ring in rings:
        edges.extend((start + i, start + (i + 1) % len(ring)) for i in range(len(ring)))
        start += len(ring)
    vertices, _, faces, *_ = geometry.delaunay_2d_cdt(points, edges, [], 1, 0.00001)
    kept = []
    for face in faces:
        center = sum((vertices[i] for i in face), Vector((0, 0))) / len(face)
        if inside(center, outline) and not any(inside(center, hole) for hole in holes):
            kept.append(face)
    if not kept:
        raise ValueError(f"Empty panel in {shape.name}")
    shape.add(
        [(x, y, z(x, y) if callable(z) else z) for x, y in vertices],
        kept,
        material,
        False,
    )


def mold_grain(materials):
    size = 64
    randomizer = random.Random(115)
    relief = [randomizer.random() for _ in range(size * size)]
    pixels = []
    for y in range(size):
        for x in range(size):

            def sample(dx, dy):
                return relief[((y + dy) % size) * size + (x + dx) % size]

            normal = Vector(
                (sample(-1, 0) - sample(1, 0), sample(0, -1) - sample(0, 1), 1.8)
            ).normalized()
            pixels.extend([*(0.5 + n * 0.5 for n in normal), 1])
    image = bpy.data.images.new(
        "115 · micro-peened tool finish", size, size, alpha=False
    )
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels)
    image.pack()
    for material in materials:
        nodes = material.node_tree.nodes
        grain = nodes.new("ShaderNodeTexImage")
        grain.image = image
        normal = nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value = 0.32
        material.node_tree.links.new(grain.outputs["Color"], normal.inputs["Color"])
        material.node_tree.links.new(
            normal.outputs["Normal"], nodes.get("Principled BSDF").inputs["Normal"]
        )


def build_fluke(sculpture, finish, rounded, pad, dial):
    yellow = finish("115 · safety yellow elastomer", "f3af14", rough=0.67)
    gray = finish("115 · stippled graphite PC/ABS", "42464a", rough=0.64)
    charcoal = finish("115 · button and stand thermoplastic", "2c2f32", rough=0.64)
    seam = finish("115 · interior and parting shadows", "15181a", rough=0.85)
    blue = finish("115 · lavender elastomer HOLD key", "6d78a2", rough=0.64)
    red = finish("115 · insulated socket sleeves", "a32139", rough=0.62)
    metal = finish(
        "115 · recessed nickel input contacts", "918f83", metal=0.83, rough=0.44
    )
    lcd = finish("115 · unpowered reflective LCD", "acb0a2", rough=0.37, coat=0.32)
    white = finish("115 · white pad ink", "efeee1", rough=0.7)
    amber = finish("115 · secondary-function ink", "e2ac2f", rough=0.72)
    raised = finish("115 · molded instruction legends", "1d2021", rough=0.73)
    ochre = finish("115 · molded hanger legends", "cc8d0c", rough=0.7)
    collection = bpy.data.collections.new("Fluke 115")
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new("Fluke 115 True RMS multimeter", None)
    collection.objects.link(root)
    root["benchInstrument"] = "meter"
    parts = []
    textured = [gray, charcoal]
    mold_grain(textured)

    def keep(shape, *, parent=root, enclosed=False):
        uses_grain = any(material in shape.materials for material in textured)
        obj = shape.finalize(uv_scale=146 if uses_grain else 0, uv_materials=textured)
        mesh = obj.data
        uv = mesh.uv_layers.active or mesh.uv_layers.new(
            name="Surface scale", do_init=False
        )
        for polygon in mesh.polygons:
            if mesh.materials[polygon.material_index] not in textured:
                for index in polygon.loop_indices:
                    uv.data[index].uv = (0, 0)
        bpy.context.collection.objects.unlink(obj)
        collection.objects.link(obj)
        obj.parent = parent
        if enclosed:
            obj["servicePart"] = True
        else:
            parts.append(obj)
        return obj

    def offset(outline, x, y):
        return [(u + x, v + y) for u, v in outline]

    def rows(shape, profiles, mat, smooth=True):
        shape.rings(
            [
                [(x, y, depth(x, y) if callable(depth) else depth) for x, y in ring]
                for ring, depth in profiles
            ],
            mat,
            smooth,
            close=False,
        )

    def inset(outline, x_scale, y_scale):
        return [(x * x_scale, 83.5 + (y - 83.5) * y_scale) for x, y in outline]

    def text(shape, s, size, x, y, d, mat):
        shape.label(s, size, lambda u, v: (x + u, y + v, d), mat)

    def profile(half):
        return curved(half + [(-x, y) for x, y in reversed(half[1:-1])])

    shell = profile(
        [
            (0, 0),
            (24, 0.6),
            (33, 2.1),
            (37.5, 5.5),
            (39.1, 11),
            (38.6, 34),
            (37.6, 67),
            (38.1, 91),
            (41.1, 123),
            (41.9, 150),
            (40.9, 160),
            (38.1, 164.5),
            (30, 166.2),
            (0, 167),
        ]
    )
    w, low, high = (
        max(x for x, y in shell),
        min(y for x, y in shell),
        max(y for x, y in shell),
    )
    shell = [(x * 42 / w, (y - low) * 167 / (high - low)) for x, y in shell]
    front = profile(
        [
            (0, 5),
            (26, 5.8),
            (31, 7),
            (33.4, 10.2),
            (34, 20),
            (33.7, 63),
            (34.7, 92),
            (37, 126),
            (36.4, 153),
            (35.8, 159),
            (32.6, 161),
            (25, 161.8),
            (0, 162.2),
        ]
    )
    rear_open = profile(
        [
            (0, 21),
            (20, 21.6),
            (23.5, 23.3),
            (23.4, 29.2),
            (21.2, 66),
            (20.4, 113),
            (20, 119),
            (17.5, 120.8),
            (17.1, 126.9),
            (15.4, 129),
            (10.6, 129.4),
            (0, 129.6),
        ]
    )
    hanger = [(x, 152.5) for x in (-14.5, 14.5)] + [
        (14.5 * math.cos(a * math.pi / 32), 150.7 - 11.6 * math.sin(a * math.pi / 32))
        for a in range(33)
    ]
    hanger_slot = offset(rounded(35.2, 2.85, 0.65), 0, 162.15)
    lip = lambda x, y: 13.05 + 0.4 * (abs(x) / 42) ** 2
    back = lambda x, y: -15.6 - 2.5 * min(1, max(0, (y - 100) / 28))
    boot = sculpture("115 · open front and rear protective holster")
    rows(
        boot,
        [
            (inset(shell, 0.973, 0.990), back),
            (inset(shell, 0.989, 0.997), lambda x, y: back(x, y) + 0.65),
            (shell, -5.5),
            (inset(shell, 0.999, 0.999), -5.24),
            (inset(shell, 0.995, 0.999), -4.93),
            (inset(shell, 0.998, 0.999), -4.6),
            (shell, 6),
            (inset(shell, 0.993, 0.998), 11.5),
            (inset(shell, 0.974, 0.993), lip),
        ],
        yellow,
    )
    panel(boot, inset(shell, 0.974, 0.993), [front], lip, yellow)
    rows(boot, [(front, lip), (inset(front, 0.996, 0.998), 11.42)], yellow)
    hanger_lip = offset(rounded(37.1, 4.8, 1.05), 0, 162.15)
    panel(
        boot, inset(shell, 0.973, 0.990), [rear_open, hanger, hanger_lip], back, yellow
    )
    rows(boot, [(rear_open, back), (inset(rear_open, 0.987, 0.993), -12.7)], yellow)
    rows(boot, [(hanger, back), (hanger, -12)], yellow)
    rows(
        boot, [(hanger_lip, back), (hanger_slot, -19.05), (hanger_slot, -12.4)], yellow
    )
    for sign in (-1, 1):
        for bottom, top in [(112.5, 128.2), (130.4, 163.6)]:
            sections = []
            for h, scale in [
                (bottom, 0.82),
                (bottom + 0.8, 0.96),
                (bottom + 2.5, 1),
                (top - 0.8, 1),
                (top, 0.95),
            ]:
                section = []
                for x, d in [
                    (-7.6, -18),
                    (-7.6, -24.4),
                    (-7.1, -26.7),
                    (-6.5, -27.25),
                    (-5.6, -27.25),
                ]:
                    section.append((x, d))
                section += [
                    (
                        5.6 * math.sin(a * math.pi / 32 - math.pi / 2),
                        -26.7 + 5.6 * math.cos(a * math.pi / 32 - math.pi / 2),
                    )
                    for a in range(33)
                ]
                section += [(6.5, -27.25), (7.1, -26.7), (7.6, -24.4), (7.6, -18)]
                sections.append(
                    [
                        (sign * (31.2 + x * scale), h, -18 + (d + 18) * scale)
                        for x, d in section
                    ]
                )
            boot.rings(sections, yellow)
    for i, line in enumerate(["USE WITH", "FLUKE MAGNETIC HANGING", "ACCESSORY"]):
        boot.label(
            line, 1.68, lambda u, v, i=i: (-u, 159.12 - i * 2.05 + v, -18.17), ochre
        )
    keep(boot)

    body = sculpture("115 · perforated front housing and rear case")
    outline = inset(front, 1.01, 1.004)
    port_centers = [-19.4, 0, 19.4]
    cx, cy = -10.35, 69.55
    screen = offset(rounded(65.9, 29.6, 2.2, 7), 0, 132.3)
    holes = [circle(x, 17.25, 5.65) for x in port_centers] + [
        circle(cx, cy, 23.4, 96),
        screen,
    ]
    panel(body, outline, holes, 11.87, gray)
    rows(
        body,
        [(outline, 11.87), (outline, 10.7), (inset(outline, 0.977, 0.988), -10.7)],
        gray,
    )
    well = offset(rounded(30.6, 56.4, 1.9), 0, 94.7)
    panel(body, inset(outline, 0.977, 0.988), [well], -10.7, charcoal)
    for radius in (2.85, 2.58):
        ring = circle(0, 146.1, radius, 40)
        body.pipe([(-x, y, -10.79) for x, y in [*ring, ring[0]]], 0.10, raised)
    for s, x, y, size in [
        ("ETL", 0, 146.25, 2.15),
        ("c", -4.1, 143.8, 1.5),
        ("us", 4.5, 143.8, 1.5),
    ]:
        body.label(s, size, lambda u, v, x=x, y=y: (-x - u, y + v, -10.80), raised)
    for i, s in enumerate(
        ["FLUKE CORPORATION", "EVERETT, WA 98203 USA", "www.fluke.com", "MADE IN CHINA"]
    ):
        body.label(s, 2.13, lambda u, v, i=i: (-u, 46 - i * 2.78 + v, -10.78), raised)
    for hole in holes:
        rows(body, [(hole, 11.87), (hole, 9.2)], seam)
    case_object = keep(body)

    window = sculpture("115 · sunken LCD and polished display surround")
    bezel = offset(rounded(70.7, 43.6, 2.3, 8), 0, 137.1)
    rows(
        window,
        [(bezel, 11.88), (bezel, 12.4), (inset(bezel, 0.995, 0.999), 12.65)],
        charcoal,
    )
    panel(window, inset(bezel, 0.995, 0.999), [screen], 12.65, charcoal)
    rows(
        window,
        [
            (screen, 12.65),
            (screen, 12.25),
            (offset(rounded(64, 28, 1.9, 7), 0, 132.3), 10.55),
        ],
        gray,
    )
    glass = offset(rounded(64.1, 28.1, 1.9, 7), 0, 132.3)
    panel(window, glass, [], 10.55, lcd)
    pad(window, -22.6, 152.6, 12.74, 18.3, 4.4, 0.13, 0.18, yellow, lip=0.035)
    text(window, "FLUKE", 4.8, -22.6, 152.65, 12.92, seam)
    text(window, "115", 4.15, -9.1, 152.65, 12.89, white)
    text(window, "TRUE RMS MULTIMETER", 3.23, 11.4, 152.65, 12.89, white)
    keep(window)

    keys = sculpture("115 · function keypad and backlight switch")
    for x, s, m in [
        (-23.3, "HOLD", blue),
        (-7.8, "MINMAX", charcoal),
        (7.8, "RANGE", charcoal),
        (23.4, "", yellow),
    ]:
        pad(keys, x, 107.7, 12.03, 13.4, 7.6, 0.52, 1.5, seam, lip=0.18)
        pad(keys, x, 107.8, 12.98, 12.4, 6.7, 2.17, 1.4, m, lip=0.54)
        if s:
            text(keys, s, 2.55, x, 107.8, 14.11, white)
    dial(
        keys,
        22.1,
        95.7,
        [
            (0.05, 11.9),
            (4.1, 11.9),
            (4.35, 12.6),
            (4.07, 13.5),
            (3.7, 13.97),
            (0.04, 13.97),
        ],
        charcoal,
    )

    def stroke(shape, coords, mat=white, r=0.20):
        shape.pipe(coords, r, mat, 7)

    def line(shape, coords, z, mat=white, r=0.20):
        pts = [Vector(p) for p in coords]
        verts = []
        for i, p in enumerate(pts):
            tangent = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            normal = Vector((-tangent.y, tangent.x)) * r
            verts.extend(
                [
                    (p.x + normal.x, p.y + normal.y, z),
                    (p.x - normal.x, p.y - normal.y, z),
                ]
            )
        shape.add(
            verts,
            [(j, j + 1, j + 3, j + 2) for j in range(0, len(verts) - 2, 2)],
            mat,
            False,
        )

    line(keys, circle(22.1, 95.7, 1.2, 24) + [(23.3, 95.7)], 14.03, r=0.17)
    for i in range(8):
        a = i * math.tau / 8
        line(
            keys,
            [(22.1 + v * math.cos(a), 95.7 + v * math.sin(a)) for v in (1.85, 2.48)],
            14.03,
            r=0.15,
        )
    keep(keys)

    knob = sculpture("115 · flush thumbwheel with 52 rim notches and OFF index")

    def wheelrow(radius, depth, cut):
        return [
            (
                cx
                + (radius - cut * ([0, 1, 1, 0][i % 4])) * math.cos(i * math.tau / 208),
                cy
                + (radius - cut * ([0, 1, 1, 0][i % 4])) * math.sin(i * math.tau / 208),
                depth,
            )
            for i in range(208)
        ]

    disk = [
        wheelrow(r, d, cut)
        for r, d, cut in [
            (23.05, 9.3, 0.46),
            (23.06, 11.96, 0.65),
            (22.91, 12.5, 0.70),
            (22.46, 12.66, 0.62),
            (21.47, 12.68, 0),
            (20.9, 12.68, 0),
        ]
    ]
    knob.rings(disk, gray, close=False)
    top = disk[-1]
    knob.add(top, [tuple(range(len(top)))], gray, False)

    def pointer(x, y, d):
        return (cx + x, cy + y, d)

    knob.rings(
        [
            [pointer(x, y, d) for x, y in rounded(w, h, r, 6)]
            for w, h, r, d in [
                (9.9, 43.4, 1.9, 12.62),
                (9.8, 43.1, 2, 13.1),
                (8.0, 40.8, 1.58, 18.15),
                (7.4, 40.2, 1.48, 18.65),
            ]
        ],
        charcoal,
    )
    px, py, _ = pointer(0, 15.6, 0)
    dial(knob, px, py, [(1.64, 18.66), (1.62, 18.75), (1.24, 18.75)], seam)
    dial(
        knob,
        px,
        py,
        [(1.24, 18.75), (1.18, 18.80), (0.04, 18.80)],
        white,
    )
    keep(knob)

    sockets = sculpture("115 · three stepped 4 mm safety input sockets")
    for x in port_centers:
        for sleeve, mat in [
            (
                [
                    (5.65, 11.86),
                    (5.45, 11.71),
                    (4.91, 11.25),
                    (4.44, 10.35),
                    (4.07, 8.8),
                    (4.03, 5.4),
                ],
                charcoal,
            ),
            (
                [
                    (4.05, 5.41),
                    (3.94, 8.63),
                    (3.79, 9.65),
                    (3.43, 9.83),
                    (2.81, 9.86),
                    (2.5, 9.51),
                    (2.1, 8.9),
                    (2.08, 2.4),
                ],
                red if x else seam,
            ),
            ([(2.075, 2.4), (1.96, 2.1), (1.93, -0.1)], metal),
            ([(1.96, -0.1), (0.04, -0.1)], seam),
        ]:
            dial(sockets, x, 17.25, sleeve, mat)
    keep(sockets)

    marks = sculpture("115 · primary and alternate function printing")
    d = 11.96

    def printat(s, x, y, size=4.4, mat=white):
        text(marks, s, size, x, y, d, mat)

    def sign(coords, mat=white, r=0.2):
        line(marks, coords, d, mat, r)

    def ac(x, y):
        sign(
            [(x + v * 0.21, y + 0.45 * math.sin(v * math.pi / 8)) for v in range(-8, 9)]
        )

    def dc(x, y, mat=white):
        sign([(x - 1.65, y + 0.46), (x + 1.65, y + 0.46)], mat)
        for t in [-1.15, 0, 1.15]:
            sign([(x + t - 0.33, y - 0.46), (x + t + 0.33, y - 0.46)], mat, 0.16)

    def waves(x, y, scale=1):
        for rr in [2.4, 3.3, 4.2, 5.1]:
            sign(
                [
                    (
                        x + scale * (rr * math.cos(a * 0.088) - 2.2),
                        y + scale * rr * math.sin(a * 0.088),
                    )
                    for a in range(-5, 6)
                ],
                r=0.17 * scale,
            )

    def diode(x, y, scale=1):
        def pts(values):
            return [(x + a * scale, y + b * scale) for a, b in values]

        sign(pts([(-2.2, 0), (1.8, 0)]))
        sign(pts([(-0.95, 1.24), (1, 0), (-0.95, -1.24), (-0.95, 1.24)]))
        sign(pts([(1.1, -1.25), (1.1, 1.25)]))

    def capacitor(x, y, mat, scale=1):
        for a in [-1, 1]:
            sign([(x + a * 2 * scale, y), (x + a * 0.46 * scale, y)], mat)
            sign(
                [
                    (x + a * 0.46 * scale, y - 1.23 * scale),
                    (x + a * 0.46 * scale, y + 1.23 * scale),
                ],
                mat,
            )

    printat("OFF", cx, 95.4, 3.65)
    for x, y, s in [
        (-0.7, 92.8, "V"),
        (8.8, 87.3, "V"),
        (17.6, 79.6, "mV"),
        (18.5, 69.1, "Ω"),
        (4.5, 42.1, "A"),
        (-10.0, 40.5, "A"),
    ]:
        printat(s, x, y)
    ac(-1.8, 96.5)
    printat("Hz", 4, 96, 3, amber)
    dc(8.8, 90.7)
    ac(17.7, 83.1)
    dc(23.4, 79.6, amber)
    waves(16.3, 57.3)
    diode(9.6, 48.6)
    capacitor(14.9, 47.5, amber)
    ac(4.5, 45.4)
    printat("Hz", 9.7, 41.8, 2.8, amber)
    dc(-10, 44)
    for x, s in [(-19.4, "A"), (0, "COM"), (17.5, "V Ω")]:
        printat(s, x, 28.1, 3.35)
    waves(21.7, 28.1, 0.65)
    diode(20.9, 24.4, 0.72)
    capacitor(16.8, 24.4, white, 0.71)
    printat("10 A", -10.2, 12.8, 2.8)
    printat("FUSED", -10.2, 10.4, 2.65)
    printat("CAT III", 10.2, 12.9, 2.7)
    printat("600 V", 10.2, 10.2, 2.7)
    sign([(8.35, 15.6), (10.1, 18.65), (11.85, 15.6), (8.35, 15.6)], r=0.16)
    printat("!", 10.1, 16.75, 1.82)
    for x, toward in [(-18.5, 1), (-0.8, -1), (0.8, 1), (18.5, -1)]:
        sign(
            [
                (x, 11.5),
                (x + 0.62 * toward, 10.8),
                (x + 3 * toward, 10.8),
            ],
            r=0.15,
        )
    for i, w in enumerate([2, 1.34, 0.7]):
        sign([(10.1 - w, 7.75 - i * 0.55), (10.1 + w, 7.75 - i * 0.55)], r=0.14)
    sign([(10.1, 8.7), (10.1, 7.8)], r=0.15)
    keep(marks)

    door = sculpture("115 · rear 9 V battery door, finger lip and single screw")
    flange = offset(rounded(36.6, 64.0, 2.1, 8), 0, 94.7)
    rim = offset(rounded(35.8, 63.2, 1.85, 8), 0, 94.7)
    rows(
        door, [(rim, -13.5), (flange, -13.0), (flange, -11.1), (rim, -10.74)], charcoal
    )
    panel(door, rim, [], -13.5, charcoal)
    panel(door, rim, [], -10.74, charcoal)
    for x in (-13.5, 13.5):
        pad(door, x, 123.7, -13.9, 2.0, 6.8, 1.3, 0.62, charcoal)
    pad(door, 0, 128, -14.1, 24.2, 7.5, 3.7, 1.0, charcoal)
    bx, by = 0, 128.65
    dial(
        door,
        bx,
        by,
        [(0.04, -15.98), (2.25, -15.98), (2.45, -15.7), (2.76, -15.4)],
        seam,
    )
    dial(door, bx, by, [(0.04, -16.12), (1.55, -16.12), (1.84, -15.97)], gray)
    for a in (0.76, 0.76 + math.pi / 2):
        stroke(
            door,
            [
                (bx + t * math.cos(a), by + t * math.sin(a), -16.18)
                for t in (-1.13, 1.13)
            ],
            seam,
            0.24,
        )
    for side in (-1, 1):
        door.pipe(
            [(side * 12.5, 128, -14.25), (side * 17, 128, -14.25)], 2.35, charcoal, 24
        )
    door_object = keep(door)

    stand = sculpture("115 · pivoted easel with flared foot and molded options")
    top = (128, -14.4)
    foot = (27.95, -77.45)
    length = math.dist(top, foot)
    dy, dz = (top[0] - foot[0]) / length, (top[1] - foot[1]) / length

    def stand_point(x, t, thick):
        return (x, foot[0] + t * dy + thick * dz, foot[1] + t * dz - thick * dy)

    outline = profile(
        [
            (0, 0),
            (17.7, 0.3),
            (20.4, 0.9),
            (21.05, 2.2),
            (20.5, 8.5),
            (19.15, 46),
            (18.15, 92),
            (17.85, length - 8),
            (15.5, length - 5.6),
            (13.8, length - 5.3),
            (13.4, length - 1),
            (12.4, length),
            (8.5, length),
            (7.9, length - 5.7),
            (6.9, length - 6.4),
            (0, length - 6.4),
        ]
    )
    stand.rings(
        [[stand_point(x, t, z) for x, t in outline] for z in [-0.7, -0.45, 1.15, 1.43]],
        charcoal,
        False,
    )
    for side in (-1, 1):
        stand.pipe(
            [
                stand_point(side * w, t, -0.9)
                for w, t in [(19, 4), (18.2, 23), (17, 62), (16.3, 104)]
            ],
            0.74,
            charcoal,
            10,
        )
    for side in (-1, 1):
        stand.pipe(
            [stand_point(x * side, length, 0.1) for x in (8.6, 12.6)], 1.9, charcoal, 24
        )

    sole = offset(rounded(39, 12, 1.8), 0, 8)
    stand.rings(
        [
            [stand_point(x, t, 1.39 + z * (1 - (t - 2) / 13)) for x, t in sole]
            for z in (0, 1.08)
        ],
        charcoal,
        False,
    )
    frame = offset(rounded(31.6, 83.6, 1.4, 9), 0, 61)
    stand.pipe(
        [stand_point(x, t, 1.47) for x, t in [*frame, frame[0]]], 0.15, charcoal, 8
    )

    def mold(s, t, size=2.05):
        stand.label(s, size, lambda u, v: stand_point(-u, t + v, 1.49), raised)

    def engraved(pts):
        stroke(stand, [stand_point(x, t, 1.49) for x, t in pts], raised, 0.15)

    for t in (99, 53):
        engraved([(-1.7, t), (0, t + 3.1), (1.7, t), (-1.7, t)])
    for s, t in [
        ("POWER-UP OPTIONS", 94),
        ("PRESS BUTTON WHILE", 91.3),
        ("TURNING METER ON", 88.6),
        ("AUTO-V  LoZ", 46.5),
        ("AUTOMATIC V SELECTION", 42),
        ("WITH LOW INPUT IMPEDANCE", 39),
        ("(MODELS 110 PLUS,", 34),
        ("114, 116 & 117)", 31),
    ]:
        mold(s, t)
    for t, first, second in [
        (81, "DISABLE", "BEEPER"),
        (73, "DISABLE", "AUTO POWER OFF"),
        (65, "DISABLE", "AUTO BACKLIGHT OFF"),
    ]:
        for s, y in [(first, t + 1.05), (second, t - 1.2)]:
            stand.label(
                s, 1.65, lambda u, v, y=y: stand_point(-4.2 - u, y + v, 1.49), raised
            )
        icon = (
            circle(10.6, t, 2.35, 20)
            if t == 65
            else offset(rounded(8.4, 4.65, 0.6), 10.6, t)
        )
        engraved([*icon, icon[0]])
        if t == 81:
            stand.label(
                "MIN MAX",
                1.36,
                lambda u, v: stand_point(10.6 - u, 81 + v, 1.49),
                raised,
            )
        if t == 65:
            glow = circle(10.6, t, 0.88, 12)
            engraved([*glow, glow[0]])
    engraved([(-15, 59), (15, 59)])
    stand.label(
        "FLUKE",
        4.3,
        lambda u, v: stand_point(-u, 7 + v, 2.36 - (7 + v - 2) * 1.08 / 13),
        raised,
    )
    keep(stand)
    source = (
        Path(__file__).resolve().parents[2]
        / ".references/06-工坊与工具/电子测量与实验/Fluke 115 multimeter/Blender/fluke-115-multimeter.blend"
    )
    if source.parent.is_dir():
        service = []

        def internal(shape, parent):
            obj = keep(shape, parent=parent, enclosed=True)
            service.append(obj)
            return obj

        graphite = finish("115 · 6LR61 insulated jacket", "323a44", rough=0.44)
        foam = finish("115 · cell shock absorber foam", "2e3031", rough=0.95)
        ceramic = finish("115 · 803293 ceramic barrel", "e4dfcc", rough=0.57)
        tray = sculpture("115 · 2525575 integral battery tray and terminal dividers")
        for side in (-1, 1):
            pad(
                tray,
                side * 13.67,
                93.15,
                -1.0,
                0.96,
                53.4,
                18.8,
                0.42,
                charcoal,
                lip=0.22,
            )
        pad(tray, 0, 66.85, -1.0, 27.5, 1.0, 18.8, 0.42, charcoal, lip=0.22)
        for x, width in [(-11.9, 3.5), (0, 3.0), (11.9, 3.5)]:
            pad(tray, x, 119.35, -2, width, 1.05, 16.8, 0.40, charcoal, lip=0.22)
        pad(tray, 0, 65.2, -9.6, 13.4, 3.0, 1.3, 0.55, charcoal)
        internal(tray, door_object)

        cushion = sculpture("115 · 878983 cell shock absorber")
        pad(cushion, 0, 68.31, -1.12, 23.1, 1.86, 13.2, 0.83, foam, lip=0.30)
        internal(cushion, door_object)
        cell = sculpture("115 · 614487 9 V 6LR61 alkaline cell")
        pad(cell, 0, 91.65, -1.25, 26.0, 44.8, 17.0, 1.42, graphite, lip=0.33)
        pad(cell, 0, 113.99, -1.25, 25.5, 0.34, 16.52, 0.16, seam, lip=0.08)
        cell.label("9V   ALKALINE", 3.1, lambda u, v: (u, 95 + v, 7.32), white)
        cell.label("6LR61", 2.4, lambda u, v: (u, 87 + v, 7.32), white)
        for x, sign in [(-6.35, "+"), (6.35, "-")]:
            cell.label(sign, 2.7, lambda u, v, x=x: (x + u, 109 + v, 7.32), white)
            n = 48 if x < 0 else 6
            radii = (2.93, 2.56, 2.48) if x < 0 else (4.02, 3.81, 3.26)
            cell.rings(
                [
                    [
                        (
                            x + r * math.cos(i * math.tau / n),
                            y,
                            -1.25 + r * math.sin(i * math.tau / n),
                        )
                        for i in range(n)
                    ]
                    for y, r in [
                        (114.10, radii[0]),
                        (114.46, radii[0]),
                        (114.70, radii[1]),
                        (117.10, radii[1]),
                        (117.25, radii[2]),
                        (115.25, radii[2]),
                    ]
                ],
                metal,
                x < 0,
            )
        internal(cell, door_object)

        well_walls = sculpture("115 · molded battery compartment in the lower housing")
        rows(well_walls, [(well, -10.7), (well, 8.7)], charcoal)
        panel(well_walls, well, [], 8.7, charcoal)
        internal(well_walls, case_object)
        blades = sculpture("115 · two sprung battery contacts")
        for x in (-6.35, 6.35):
            outline = [
                (120.4, 6.1),
                (119.9, 6.5),
                (116.7, 5.2),
                (116.1, 2.9),
                (117.36, 0),
                (117.12, -1.2),
                (116.75, -1.14),
                (116.98, 0),
                (115.73, 2.9),
                (116.4, 5.53),
                (119.9, 6.91),
                (120.6, 6.38),
            ]
            blades.rings(
                [[(x + w, y, d) for y, d in outline] for w in [-1.16, 1.16]],
                metal,
                False,
            )
        internal(blades, case_object)

        fuse = sculpture("115 · 803293 11 A 1000 V ceramic cartridge fuse")

        def barrel(a, b, r, mat):
            fuse.rings(
                [
                    [
                        (
                            x,
                            42.0 + rad * math.sin(i * math.tau / 36),
                            -1.5 + rad * math.cos(i * math.tau / 36),
                        )
                        for i in range(36)
                    ]
                    for x, rad in [
                        (a, r - 0.18),
                        (a + 0.2, r),
                        (b - 0.2, r),
                        (b, r - 0.18),
                    ]
                ],
                mat,
            )

        barrel(-28.55, -21.7, 5.156, metal)
        barrel(-21.7, 2.7, 4.96, ceramic)
        barrel(2.7, 9.55, 5.156, metal)
        internal(fuse, case_object)
        clip = sculpture("115 · two cartridge fuse clips")
        for x in (-25.2, 6.25):
            arc = [
                (42 - r * math.sin(a), -1.5 + r * math.cos(a))
                for r, angles in [
                    (5.20, range(-118, 119, 4)),
                    (5.56, range(118, -119, -4)),
                ]
                for a in map(math.radians, angles)
            ]
            clip.rings(
                [[(x + w, y, d) for y, d in arc] for w in (-1.85, 1.85)], metal, False
            )
        internal(clip, case_object)

        for material in {
            mat
            for obj in collection.objects
            if obj.type == "MESH"
            for mat in obj.data.materials
        }:
            shader = material.node_tree.nodes.get("Principled BSDF")
            material.diffuse_color = shader.inputs["Base Color"].default_value[:]
        native = bpy.context.scene
        if set(native.objects) == set(collection.objects):
            title, units = native.name, native.unit_settings.system
            native.name = "Fluke 115 multimeter"
            native.unit_settings.system = "METRIC"
            bpy.context.preferences.filepaths.save_version = 0
            bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True, copy=True)
            native.name, native.unit_settings.system = title, units
        else:
            product = bpy.data.scenes.new("Fluke 115 multimeter")
            product.unit_settings.system = "METRIC"
            product.collection.children.link(collection)
            bpy.data.libraries.write(
                str(source), {product}, path_remap="RELATIVE", compress=True
            )
            bpy.data.scenes.remove(product)
        for obj in service:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)
    return root, parts
