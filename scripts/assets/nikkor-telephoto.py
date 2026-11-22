import itertools
import math
import subprocess
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, geometry

FLANGE = 978
MM_PER_PIXEL = 208 / (FLANGE - 3)
SECTION = (
    (163, ((19, 23, 37), (40.5, 40.5, 41.4)), ("front positive",)),
    (158, ((45, 52, 79), (49, 60, 97)), ("front negative meniscus",)),
    (152, ((52, 63, 98), (107.5, 107.5, 107.5)), ("fluorite",)),
    (98, ((120, 121, 126), (124.5, 131.5, 153)), ("plano-concave",)),
    (90, ((202, 199, 192), (204.7, 207, 215)), ("biconcave",)),
    (90, ((212, 215, 226), (225.5, 226.5, 230)), ("convergent meniscus",)),
    (95, ((244, 241, 234), (251.5, 251.5, 251.5)), ("Super ED",)),
    (97, ((459, 465, 483), (481, 482.5, 488)), ("short-wavelength refractive",)),
    (94, ((488.5, 493, 506), (520.5, 520.3, 520)), ("aspherical ED",)),
    (
        80,
        ((569, 569.2, 571), (574, 579.5, 600), (596.5, 599.4, 607)),
        ("negative field lens", "cemented ED"),
    ),
    (
        82,
        ((609, 612, 622.5), (646, 643.3, 634.8), (650, 649, 643.5)),
        ("aspherical", "cemented companion"),
    ),
    (78, ((659.5, 662, 672), (672, 672.5, 676)), ("rear transfer meniscus",)),
    (65, ((688, 688, 689), (697.5, 697, 695.5)), ("transfer positive",)),
    (60, ((704, 704, 704), (708.5, 711, 720)), ("transfer negative",)),
    (83, ((849, 850, 853.7), (871.5, 868.5, 860)), ("rear biconvex",)),
    (86, ((900, 894, 879), (903.8, 903.1, 897.8)), ("rear aspherical",)),
)


def rounded_rectangle(width, length, z, corner):
    return [
        (
            sx * (width / 2 - corner) + corner * math.cos(a),
            z + sy * (length / 2 - corner) + corner * math.sin(a),
        )
        for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1)))
        for k in range(9)
        for a in [(i + k / 8) * math.pi / 2]
    ]


def foot(shape, shell, anodized, thread, standard):
    holes = [(104.0, 2.75), (124.0, 2.75)]
    rows = []
    for width, length, height in (
        (35.2, 80.3, -69.6),
        (37.5, 82, -70.4),
        (37.5, 82.2, -71.2),
        (32.9, 80.3, -74.0),
        (37.45, 81.1, -76.5),
        (37.45, 80.8, -77.4),
        (36.1, 79.5, -78.0),
    ):
        rows.append(
            [(x, z, height) for x, z in rounded_rectangle(width, length, 98.5, 4.9)]
        )
    shape.rings(rows, anodized, False, False)
    for row, reverse in ((rows[0], False), (rows[-1], True)):
        loops = [[(p[0], p[1]) for p in row]]
        loops.extend(standard["screw_circle"](r + 0.46, 0, z, 40) for z, r in holes)
        points, edges = [], []
        for loop in loops:
            start = len(points)
            points.extend(Vector(v) for v in loop)
            edges.extend(
                (start + i, start + (i + 1) % len(loop)) for i in range(len(loop))
            )
        vs, _, fs, _, _, _ = geometry.delaunay_2d_cdt(points, edges, [], 0, 1e-6)
        faces = []
        for face in fs:
            center = sum((vs[i] for i in face), Vector((0, 0))) / 3
            if all(math.hypot(center.x, center.y - z) > r + 0.43 for z, r in holes):
                faces.append(tuple(reversed(face)) if reverse else face)
        shape.add([(v.x, v.y, row[0][2]) for v in vs], faces, shell, False)
    for z, r in holes:
        wall = []
        for height, bore in (
            (-69.6, r + 0.46),
            (-70.12, r),
            (-77.47, r),
            (-78, r + 0.46),
        ):
            wall.append(
                [(x, y, height) for x, y in standard["screw_circle"](bore, 0, z, 40)]
            )
        shape.rings(wall, anodized, True, False)
        turns = []
        for k in range(5 * 40 + 1):
            a = k * math.tau / 40
            h = -77.02 + k / 40 * 1.27
            tip = r - 0.32 * min(1, k / 12, (200 - k) / 12)
            turns.append(
                [
                    (rr * math.sin(a), z + rr * math.cos(a), h + delta)
                    for rr, delta in (
                        (r + 0.02, -0.32),
                        (tip, -0.043),
                        (tip, 0.043),
                        (r + 0.02, 0.32),
                    )
                ]
            )
        shape.rings(turns, thread, True, False)


def collar(shape, shoe, lock, shell, anodized, trim, rubber, standard):
    shape.turn(
        [
            (27, 37.4),
            (27.7, 39.1),
            (30.2, 40.9),
            (32.1, 41.03),
            (55.9, 41.03),
            (58.8, 41.7),
            (60.1, 41.7),
            (61.6, 40.4),
            (62.4, 39.8),
        ],
        shell,
        128,
    )
    shape.turn([(26.1, 37.1), (26.7, 39.1), (28.4, 40.17), (30.2, 40.4)], anodized, 128)
    shape.turn(
        [(26.8, 38.91), (27.1, 39.22), (29.5, 40.68), (30.1, 40.70)],
        anodized,
        96,
        0.31,
        96,
    )
    for angle in (-math.pi / 2, 0, math.pi / 2):
        circle = [
            (
                41.24 * math.sin(angle + 0.012 * math.cos(i * math.tau / 18)),
                56.3 + 0.47 * math.sin(i * math.tau / 18),
                41.24 * math.cos(angle + 0.012 * math.cos(i * math.tau / 18)),
            )
            for i in range(18)
        ]
        shape.add(
            circle,
            [tuple(range(18))],
            bpy.data.materials["Nikon white silk print"],
            False,
        )
    outline = [
        (29, -31),
        (53.3, -32),
        (57, -44.8),
        (58.8, -51.5),
        (61.1, -56.6),
        (64, -60.9),
        (67.3, -64),
        (71.5, -66.6),
        (77, -68.1),
        (89.2, -69.6),
        (137.2, -69.8),
        (137.9, -71.1),
        (133, -71.5),
        (59.4, -71.3),
        (56.7, -69.3),
        (36.0, -40.8),
    ]

    def cheek(center, width, outline):
        projected = []
        for offset, fraction in (
            (-width, 0.974),
            (-width + 0.55, 1),
            (width - 0.55, 1),
            (width, 0.974),
        ):
            projected.append(
                [
                    (
                        center + offset,
                        70 + (z - 70) * fraction,
                        -53 + (h + 53) * fraction,
                    )
                    for z, h in outline
                ]
            )
        shape.rings(projected, shell, False)

    for side in (-1, 1):
        cheek(side * 13.45, 3.62, outline)
    cheek(
        0,
        10.6,
        [
            (31.6, -35),
            (50.2, -38),
            (55.1, -54),
            (59, -61.8),
            (64, -67.1),
            (72, -70.4),
            (59.8, -71.5),
            (57.6, -70.2),
            (36.4, -41.0),
        ],
    )
    foot(shoe, shell, anodized, trim, standard)
    axis = Vector((-0.91, 0, -0.415)).normalized()
    a, b = Vector((0, 1, 0)), axis.cross(Vector((0, 1, 0)))
    origin = Vector((-30.5, 42.5, -19))

    def knob(r, dist, steps, knurl=0):
        return [
            tuple(
                origin
                + axis * dist
                + (
                    a * math.sin(k * math.tau / steps)
                    + b * math.cos(k * math.tau / steps)
                )
                * (r + (knurl if k % 3 == 1 else 0))
            )
            for k in range(steps)
        ]

    lock.rings(
        [knob(r, d, 112) for r, d in ((5.3, -1), (6.3, 0.2), (6.3, 5.8), (8.95, 6.6))],
        trim,
    )
    lock.rings(
        [
            knob(r, d, 216, k)
            for r, d, k in (
                (9.3, 6.4, 0),
                (9.85, 7.2, 0.17),
                (9.85, 12.9, 0.17),
                (9.71, 13.3, 0),
                (9.12, 13.8, 0),
            )
        ],
        anodized,
        True,
    )
    lock.rings(
        [knob(r, d, 96) for r, d in ((8.5, 13.80), (8.23, 13.91), (1, 13.93))],
        shell,
        True,
    )


def knurled_finish(make):
    material = make("70-200 S II · milled control-ring diamonds", "27282b", 0.035, 0.60)
    image = bpy.data.images.new("70-200 S II · control-ring grip", 64, 64, alpha=False)
    image.colorspace_settings.name = "Non-Color"

    def height(u, v):
        def pyramid(x, y):
            dx = abs((u - x + 0.5) % 1 - 0.5)
            dy = abs((v - y + 0.5) % 1 - 0.5)
            return max(0, 1 - dx / 0.48 - dy / 0.25)

        return 0.28 * max(pyramid(0, 0.25), pyramid(0.5, 0.75))

    pixels = []
    step = 1 / 64
    for y in range(64):
        for x in range(64):
            u, v = (x + 0.5) * step, (y + 0.5) * step
            dx = (height(u + step, v) - height(u - step, v)) / (2 * step * 1.487)
            dy = (height(u, v + step) - height(u, v - step)) / (2 * step * 2.30)
            n = Vector((-dx, -dy, 1)).normalized()
            pixels.extend([*(c * 0.5 + 0.5 for c in n), 1])
    image.pixels.foreach_set(pixels)
    image.pack()
    nodes = material.node_tree.nodes
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    normal = nodes.new("ShaderNodeNormalMap")
    material.node_tree.links.new(texture.outputs["Color"], normal.inputs["Color"])
    material.node_tree.links.new(
        normal.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"]
    )
    return material


def map_knurl(mesh, material):
    index = mesh.materials.find(material.name)
    layer = mesh.uv_layers.active.data
    for poly in mesh.polygons:
        if poly.material_index != index:
            continue
        coordinates = []
        for loop in poly.loop_indices:
            x, y, z = mesh.vertices[mesh.loops[loop].vertex_index].co
            coordinates.append(
                (loop, math.atan2(x, -y) / math.tau % 1, (z - 0.069) / 0.00230)
            )
        pole = max(c[1] for c in coordinates) - min(c[1] for c in coordinates) > 0.5
        for loop, u, v in coordinates:
            layer[loop].uv = ((u + int(pole and u < 0.5)) * 180, v)


def build(spec, Sculpture, make, fittings, standard, sculpt, optics, bases):
    materials = bpy.data.materials
    shell = materials["NIKKOR barrel · black powder coat"].copy()
    shell.name = "70-200 S II · finely textured magnesium and composite"
    next(n for n in shell.node_tree.nodes if n.type == "NORMAL_MAP").inputs[
        "Strength"
    ].default_value = 0.074
    trim = materials["Lens mount collar · anodized"]
    ink = materials["Nikon white silk print"]
    gray = materials["Nikon front collar engraving"]
    grip = materials["Focus ring · charcoal elastomer"]
    gasket = materials["Gasket · carbon black"]
    cell = make("Optical cell · 70–200 baffle seats", "24282a", 0.25, 0.51)
    flock = make("Optical flock · 70-200 S II bore", "0d1011", 0, 0.91)
    blade = make(
        "Graphite diaphragm · 70-200 S II rounded blades", "23282a", 0.16, 0.62
    )
    steel = make("Telephoto Z mount · lapped stainless steel", "c4c5c4", 0.9, 0.21)
    gold = make("Telephoto Z mount · plated contacts", "c0a168", 0.81, 0.23)
    crystal = make("Telephoto optical substrate", "fbfcfa", 0, 0.011)
    shader = crystal.node_tree.nodes.get("Principled BSDF")
    shader.inputs["IOR"].default_value = 1.55
    shader.inputs["Transmission Weight"].default_value = 1
    coatings = []
    for name, base in zip(("outer", "inner", "relay", "field"), bases):
        coating = base.copy()
        coating.name = "NIKKOR glass / 70-200 S II / " + name
        coatings.append(coating)
    scene = bpy.data.scenes.new(spec["name"])
    scene.unit_settings.system = "METRIC"
    scene.cycles.transmission_bounces = 48
    scene.cycles.max_bounces = 52
    scene.world = bpy.data.worlds.new("Telephoto workshop")
    components = bpy.data.collections.new(spec["name"])
    scene.collection.children.link(components)
    categories, parts = {}, []
    runtime = Sculpture(spec["name"])

    def part(name, section, visible=True):
        if section not in categories:
            categories[section] = bpy.data.collections.new(section)
            components.children.link(categories[section])
        shape = Sculpture(name)
        parts.append((shape, categories[section], visible))
        return shape

    profile = spec["profile"]

    def radius(z):
        for (za, ra), (zb, rb) in itertools.pairwise(profile):
            if z <= zb:
                return ra + (rb - ra) * max(0, (z - za) / (zb - za))
        return profile[-1][1]

    def point(angle, z, lift):
        return fittings["polar"](radius(z) + lift, z, angle)

    def label(
        shape, text, z, az, size, side=False, material=ink, relief=0.24, italic=False
    ):
        reading = -1 if side and az > 0 else 1

        def project(x, y):
            return (
                point(az + reading * y / radius(z), z - reading * x, relief)
                if side
                else point(az + x / radius(z), z + y, relief)
            )

        shape.label(text, size, project, material, italic)

    fixed = part("Internal zoom shell and indexed flange shroud", "Lens barrel")
    fixed.turn(profile, shell, 144)
    fixed.turn(
        [(1.0, 31.9), (2.7, 33.3), (4.4, 35.11), (22.3, 35.11), (22.8, 35)], trim, 128
    )
    for z in (65.1, 77.6, 101.3, 122.4, 140.9, 178.2, 197.9):
        r = radius(z)
        fixed.turn(
            [
                (z - 0.12, r),
                (z, r + 0.13),
                (z + 0.22, r + 0.13),
                (z + 0.34, radius(z + 0.34)),
            ],
            trim,
            112,
        )
    controls = part("Focus-mode, limit and click-selection sliders", "Controls")

    def slider(z, az, left, right):
        sign = -1 if az > 0 else 1
        fittings["panel"](controls, radius, z, az, 4.0, 11.7, 0.65, trim)
        fittings["panel"](controls, radius, z + sign * 2.0, az, 3.5, 6.0, 1.08, grip)
        for dz in (-0.53, 0, 0.53):
            fittings["panel"](
                controls, radius, z + sign * (2.7 + dz), az, 3.0, 0.25, 1.28, gasket
            )
        for value, dz in ((left, 3.45), (right, -3.45)):
            label(controls, value, z + dz * sign, az + sign * 0.137, 1.80, True)
            controls.pipe(
                [
                    point(az + sign * 0.087, z + dz * sign + s, 0.34)
                    for s in (-2.1, 2.1)
                ],
                0.073,
                ink,
                5,
            )

    slider(12.15, -1.23, "A", "M")
    slider(12.15, -1.94, "FULL", "∞–5m")
    slider(89.6, 2.21, "ON", "OFF")
    label(controls, "CLICK", 89.6, 1.95, 2.05, True)
    label(controls, "Nikon", 89.6, 1.54, 3.1, True, gray, 0.29, True)
    buttons = part("Four L-Fn2 and two L-Fn buttons with independent boots", "Controls")

    def button(az, z):
        def ring(button_radius, relief):
            return [
                point(
                    az + button_radius * math.cos(a) / radius(z),
                    z + button_radius * math.sin(a),
                    relief,
                )
                for a in (i * math.tau / 48 for i in range(48))
            ]

        buttons.rings(
            [
                ring(r, v)
                for r, v in (
                    (6.50, -0.06),
                    (6.34, 0.37),
                    (5.95, 1.10),
                    (5.05, 1.38),
                    (4.72, 1.22),
                    (4.59, 0.56),
                )
            ],
            trim,
            True,
            False,
        )
        buttons.rings([ring(4.60, 0.55), ring(4.24, 0.52)], gasket, True, False)
        buttons.rings(
            [
                ring(r, v)
                for r, v in (
                    (4.25, 0.51),
                    (4.23, 1.02),
                    (3.94, 1.29),
                    (3.07, 1.40),
                    (0.02, 1.45),
                )
            ],
            grip,
            True,
        )

    for z, angles, title in (
        (132.9, (0, -math.pi / 2, math.pi / 2, math.pi), "L-Fn2"),
        (89.4, (0, -math.pi / 2), "L-Fn"),
    ):
        for az in angles:
            button(az, z)
        label(buttons, title, z, -1.36, 2.35, True)
    label(buttons, "NIKKOR", 132.9, -0.88, 2.55, True)
    sculpt["s_emblem"](buttons, point, radius, 132.9, -1.10, trim, gray)
    grips = part(
        "Manual focus, internal zoom and divided nose grips", "Control rings", False
    )
    for r, lo, hi, n, relief, split in (
        (43.0, 102.8, 121.0, 126, 0.58, 0),
        (44.0, 144.0, 176.5, 142, 0.78, 0),
        (44.65, 183.2, 192.0, 141, 0.28, 187.6),
    ):
        sculpt["axial_ribs"](grips, lo, hi, r, n, relief, grip, split)
        for a, b in [(lo, split - 0.33), (split + 0.33, hi)] if split else [(lo, hi)]:
            optics["web_grip"](runtime, r, a, b, n, relief, grip)
    control = part("Diamond-knurled assignable control ring", "Control rings", False)
    standard["control_knurl"](
        control, 42.59, 69.0, 75.9, grip, trim, rows=6, columns=180, peak=0.28
    )
    web_knurl = knurled_finish(make)
    runtime.turn(
        [
            (68.7, 42.52),
            (69.1, 42.79),
            (69.35, 42.84),
            (75.55, 42.84),
            (75.85, 42.79),
            (76.2, 42.52),
        ],
        web_knurl,
        144,
    )
    for i, txt in enumerate(("70", "85", "105", "135", "200")):
        label(fixed, txt, 140.6, -i * 0.365, 2.65)
    fixed.pipe([point(0, z, 0.28) for z in (136.8, 138.2)], 0.13, ink, 6)
    label(fixed, "NIKKOR", 14.7, 0, 2.85)
    label(fixed, "70-200/2.8 S II", 10.45, 0, 4.0)
    fittings["dot"](fixed, point, 0, 5.1, 0.95, ink)
    for angle in (0, -math.pi / 2, math.pi / 2, math.pi):
        fittings["dot"](fixed, point, angle, 65.20, 0.46, ink)
    label(fixed, "NIKKOR Z 70-200mm 1:2.8 VR S II  ø77", 195.6, 0, 2.00, material=gray)
    tripod = "Removable tripod collar"
    collar(
        part("Rotation collar and relieved split-web neck", tripod),
        part("Arca-Swiss dovetail and two threaded sockets", tripod),
        part("Knurled collar attachment screw", tripod),
        shell,
        trim,
        steel,
        gasket,
        standard,
    )
    release = part("Collar release latch on rear shoulder", tripod)

    def rear_radius(z):
        return 39.05 + (z - 26.7) * 0.59

    fittings["panel"](release, rear_radius, 28.2, 2.26, 8.0, 2.8, 0.20, gasket)
    fittings["panel"](release, rear_radius, 28.2, 2.26, 5.9, 2.35, 0.61, trim)
    nose = part(
        "M77 × 0.75 filter socket, HB-119 bayonet and retaining ring", "Optical cells"
    )
    nose.turn(
        [
            (206, 41.85),
            (207.8, 41.95),
            (208, 41.68),
            (208, 38.63),
            (207.75, 38.35),
            (203.68, 38.35),
            (203.3, 37.79),
            (203.3, 37.01),
            (202.8, 36.72),
            (200.72, 36.51),
            (200.60, 35.16),
            (200.38, 34.75),
        ],
        trim,
        128,
    )
    optics["filter_thread"](nose, gasket, 38.35, 207.36)
    for r in (36.8, 37.13, 37.45, 37.73):
        nose.turn([(203.28, r + 0.13), (203.42, r), (203.28, r - 0.12)], gasket, 112)
    for start in (14, 104, 194, 284):
        standard["arc_section"](
            nose,
            [(42.1, 201.2), (43.4, 201.1), (43.5, 200), (43.15, 199.5), (42.4, 199.45)],
            start,
            start + 40,
            trim,
        )
    mount = part("Z flange, four lugs, five screws and eleven contacts", "Mount")
    standard["mount"](mount, steel, gasket, trim, gold)
    rear = part(
        "Rear flared light shield and recessed rear-element seat", "Optical cells"
    )
    rear.turn(
        [
            (-2.03, 23),
            (-2.45, 22.5),
            (-2.39, 21.72),
            (-1.97, 21.22),
            (1.4, 20.8),
            (3.7, 19.9),
            (11.1, 19.2),
            (16.6, 18.85),
            (17.0, 18.16),
        ],
        cell,
        128,
    )
    for i in range(7):
        z = 1.0 + i * 2.15
        r = 20.63 - i * 0.26
        rear.turn(
            [(z - 0.15, r + 0.22), (z, r - 0.02), (z + 0.13, r + 0.22)], flock, 96
        )
    elements = "Optical elements · 18 in 16 groups"
    barrels = part(
        "Bored optical cells, spacers and reflection traps", "Optical cells", False
    )
    bore = []
    for n, (rim, boundaries, names) in enumerate(SECTION):
        curves = [
            optics["face_profile"](rim, s, FLANGE, MM_PER_PIXEL) for s in boundaries
        ]
        for j, name in enumerate(names):
            front, back = curves[j : j + 2]
            glass = part(f"G{n + 1:02} E{j + 1} · {name}", elements, False)
            optics["optical_face"](glass, front, crystal, True)
            optics["optical_face"](glass, back, crystal, False)
            glass.turn([back[-1], front[-1]], cell, 96)
        start, end = curves[0][-1], curves[-1][-1]
        if bore:
            z0, r0 = bore[-1]
            z1, r1 = start
            if z0 - z1 > 3:
                for i in range(1, 7):
                    t = i / 7
                    z, r = z0 + (z1 - z0) * t, r0 + (r1 - r0) * t
                    ridge = [(z + 0.18, r + 0.08), (z, r - 0.17), (z - 0.18, r + 0.08)]
                    barrels.turn(ridge, cell, 96)
                    if n in (3, 7, 9, 15) and i in (2, 4):
                        runtime.turn(ridge, cell, 80)
        bore.extend([start, end])
        if n in (0, 2, 7, 15):
            i = (0, 2, 7, 15).index(n)
            optics["optical_face"](
                runtime,
                (curves[-1] if n == 15 else curves[0])[::2],
                coatings[i],
                n != 15,
                80,
            )
    shells = [(200.38, 34.75), *bore, (17.0, 18.16)]
    barrels.turn(shells, flock, 112)
    runtime.turn(
        [
            shells[0],
            *[
                bore[i]
                for i in (
                    0,
                    1,
                    2,
                    5,
                    6,
                    7,
                    8,
                    13,
                    14,
                    17,
                    18,
                    21,
                    22,
                    27,
                    28,
                    29,
                    30,
                    31,
                )
            ],
            shells[-1],
        ],
        flock,
        72,
    )
    aperture = part(
        "Eleven rounded diaphragm leaves and stationary carrier", "Optical cells"
    )
    fittings["diaphragm"](aperture, 11, 93.1, 18.9, 12.0, blade, trim)
    pupil = make("Z70-200 entrance pupil · relayed light", "15191a", 0, 0.48)
    for z, r in ((151.5, 12.50), (92.94, 12.03)):
        window = [standard["radial"](r, z, i * math.tau / 96) for i in range(96)]
        runtime.add(window, [tuple(range(96))], pupil, False)
    scene["opticalConstruction"] = (
        "18 elements in 16 groups, 11 rounded diaphragm blades"
    )
    scene["sectionSource"] = (
        "Nikon Imaging Z 70–200mm f/2.8 VR S II construction diagram, scaled to its published 208 mm flange-to-front envelope"
    )
    scene["filterThread"] = "M77 × 0.75"
    scene["flangeToFrontMm"] = 208
    objects = []
    for shape, section, visible in parts:
        obj = shape.finalize(uv_scale=46, uv_materials=(shell, grip, trim))
        if section.name == elements:
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            bmesh.ops.remove_doubles(mesh, verts=mesh.verts, dist=1e-8)
            bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
            if (
                not all(e.is_manifold for e in mesh.edges)
                or mesh.calc_volume(signed=True) <= 0
            ):
                raise ValueError(f"Invalid optical solid: {shape.name}")
            mesh.to_mesh(obj.data)
            mesh.free()
        bpy.context.collection.objects.unlink(obj)
        section.objects.link(obj)
        objects.append(obj)
        if visible:
            standard["merge"](shape, runtime, None)
    path = (
        Path(__file__).resolve().parents[2]
        / ".review/atelier/nikon-reference/nikkor-z70-200-sii.blend"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(path), {scene}, compress=True)
    subprocess.run(
        [
            bpy.app.binary_path,
            "-b",
            str(path),
            "--python-exit-code",
            "1",
            "--python",
            __file__,
        ],
        check=True,
    )
    for obj in objects:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    bpy.data.scenes.remove(scene)
    for group in [*categories.values(), components]:
        bpy.data.collections.remove(group)
    obj = runtime.finalize(uv_scale=46, uv_materials=(shell, grip, trim))
    map_knurl(obj.data, web_knurl)
    obj["opticalVariant"] = 2
    return obj


if __name__ == "__main__":
    bpy.context.preferences.filepaths.save_version = 0
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_location = (0, 0, 0.103)
            space.region_3d.view_distance = 0.353
            space.region_3d.view_rotation = Vector((-0.95, 0.28, 0.39)).to_track_quat(
                "Z", "Y"
            )
            space.clip_start = 0.0004
            space.shading.color_type = "MATERIAL"
            space.overlay.show_floor = False
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
