import json
import math
import runpy
from pathlib import Path

import bpy


def carbon_laminate(material):
    size = 256
    image = bpy.data.images.new(
        "Harpe · compacted 2×2 fibre tows", width=size, height=size
    )
    pixels = []
    for y in range(size):
        for x in range(size):
            u = (x + y + 0.5) / 32
            v = (y - x + 0.5) / 32
            i, j = math.floor(u), math.floor(v)
            warp = (i - j) % 4 < 2
            across, along = (u, v) if warp else (v, u)
            edge = math.sin(math.pi * (across % 1)) ** 0.28
            crossing = math.cos(math.pi * (along % 2 - 0.78))
            filaments = math.cos(
                across * math.tau * 8 + 0.65 * math.sin(along * math.pi / 2)
            )
            grey = (0.115 if warp else 0.085) + edge * (
                0.059 + 0.014 * crossing + 0.008 * filaments
            )
            pixels.extend((grey * 0.985, grey, grey * 1.02, 1))
    image.pixels.foreach_set(pixels)
    image.pack()
    nodes = material.node_tree.nodes
    sampler = nodes.new("ShaderNodeTexImage")
    sampler.image = image
    material.node_tree.links.new(
        sampler.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"]
    )
    return material


def build(Sculpture, make, tools):
    parts = []

    def part(name):
        item = Sculpture(name)
        parts.append(item)
        return item

    frame = part("Injection-moulded USB and sensor chassis")
    obj = frame
    disk, slab, patch, eye = [tools[k] for k in ("disk", "slab", "patch", "eye")]
    twill = carbon_laminate(
        make("Harpe · hand-laid carbon twill", "333438", 0.13, 0.48, 0.12)
    )
    seam = make("Harpe · thermoplastic subframe", "0c0d0f", 0.025, 0.83)
    trim = make("Harpe · hard graphite", "28292c", 0.1, 0.57)
    grip = make("Harpe · stippled lateral grip", "202226", 0.01, 0.78)
    light = make("Harpe wheel light", "7771aa", 0.08, 0.42, 0, 0.45)
    wheel = make("Harpe · translucent wheel rubber", "747283", 0.01, 0.53)
    wheel.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.31
    wheel.surface_render_method = "BLENDED"
    metal = make("Harpe · pewter transfer", "787b7d", 0.49, 0.42)
    skate = make("Harpe · competition PTFE", "e0dfd8", 0.01, 0.42)
    optic = make("Harpe · AimPoint Pro lens", "33434c", 0.25, 0.15, 0.75)
    steel = make("Harpe · connector shield", "7c8182", 0.74, 0.36)
    profile = [
        (-63.75, 0.8, 9.55),
        (-63.50, 6.46, 10.14),
        (-62.50, 12.41, 12.9),
        (-60, 20.57, 15.15),
        (-56, 27.52, 17.7),
        (-50, 31.06, 21.19),
        (-44, 31.0, 24.5),
        (-38, 30.79, 27.0),
        (-32, 30.57, 29.54),
        (-25, 30.36, 32.0),
        (-18, 30.16, 35.27),
        (-9, 30.08, 37.93),
        (0, 30.05, 39.25),
        (7, 30.22, 39.47),
        (16, 30.57, 39.0),
        (23, 31.21, 37.98),
        (29, 31.72, 36.68),
        (35, 31.52, 34.80),
        (40, 30.43, 32.75),
        (45, 28.30, 30.12),
        (50, 25.32, 26.76),
        (54, 22.06, 23.10),
        (58, 17.59, 18.28),
        (60, 14.33, 14.92),
        (62, 9.86, 11.12),
        (63, 6.46, 8.20),
        (63.50, 4.26, 6.74),
        (63.75, 0.72, 5.27),
    ]

    def dimensions(z):
        i = next((i for i, row in enumerate(profile) if row[0] >= z), len(profile) - 1)
        if i == 0:
            return profile[0][1:]
        a, b = profile[i - 1 : i + 1]
        c, d = profile[max(0, i - 2)], profile[min(len(profile) - 1, i + 1)]
        t = max(0, min(1, (z - a[0]) / (b[0] - a[0])))

        def value(k):
            m = (b[k] - c[k]) / (b[0] - c[0])
            n = (d[k] - a[k]) / (d[0] - a[0])
            return (
                (2 * t**3 - 3 * t * t + 1) * a[k]
                + (t**3 - 2 * t * t + t) * m * (b[0] - a[0])
                + (-2 * t**3 + 3 * t * t) * b[k]
                + (t**3 - t * t) * n * (b[0] - a[0])
            )

        return value(1), value(2)

    def shell(z, t, lift=0):
        w, high = dimensions(z)
        a = t * math.pi * 0.5
        c = max(0, math.cos(a))
        s = math.sin(a)
        y = 4.45 + (high - 4.45) * c**0.64
        return ((w + lift) * s, y + lift * c, z)

    zs = sorted(
        set([p[0] for p in profile] + [-63.75 + 127.5 * i / 50 for i in range(51)])
    )
    rows = []
    for z in zs:
        rows.append(
            [
                shell(
                    z,
                    j / 18,
                    -0.7
                    - 2.1
                    * math.exp(-((j / 2.8125) ** 4))
                    * max(0, min(1, (-z - 16) / 6)),
                )
                for j in range(-18, 19)
            ]
            + [
                (s * dimensions(z)[0] * k, h, z)
                for s, k, h in [
                    (1, 0.982, 3.22),
                    (1, 0.955, 1.95),
                    (1, 0.916, 1.05),
                    (-1, 0.916, 1.05),
                    (-1, 0.955, 1.95),
                    (-1, 0.982, 3.22),
                ]
            ]
        )
    obj.rings(rows, seam)

    def button_end(t):
        u = abs(t)
        return -25.7 + 9 * min(1, max(0, (u - 0.095) / 0.12)) + 3.55 * (u / 0.78) ** 1.8

    def nose_depth(x):
        a, b = -63.75, -50.0
        for _ in range(18):
            mid = (a + b) * 0.5
            if dimensions(mid)[0] < x:
                a = mid
            else:
                b = mid
        return b

    for side in (-1, 1):
        obj = part("Primary switch paddle · " + ("left" if side == -1 else "right"))
        rr = []
        for i in range(41):
            q = i / 40
            row = []
            for j in range(22):
                f = j / 21
                t = 0.088 + f * 0.69
                x = 4.4 + f * 23.7
                start = nose_depth(x + 0.60)
                start += 0.65
                z = start + (button_end(t) - start) * q
                u = (
                    4.28 / dimensions(z)[0] * (1 - f)
                    + math.sin(0.778 * math.pi / 2) * f
                )
                t = math.asin(min(0.99, u)) * 2 / math.pi
                row.append(shell(z, side * t, 0.41))
            rr.append(row)
        patch(obj, rr, twill)
        underside = [[(x * 0.994, h - 0.68, z) for x, h, z in row] for row in rr]
        patch(obj, list(reversed(underside)), trim)
        for j in [0, -1]:
            patch(obj, [[top[j], bottom[j]] for top, bottom in zip(rr, underside)], trim)
        for i in [0, -1]:
            patch(obj, [rr[i], underside[i]], trim)
        obj = part(
            "Moulded diagonal side grip · " + ("left" if side == -1 else "right")
        )
        sidewall = []
        for i in range(46):
            u = i / 45
            row = []
            for j in range(9):
                f = j / 8
                z = -60.8 + u * (70 + 12.5 * f)
                row.append(shell(z, side * (0.795 + 0.205 * f), -0.05))
            sidewall.append(row)
        patch(obj, sidewall, grip)
        for k in range(43):
            z = -54.2 + k * 1.48
            rib = []
            for n in range(8):
                f = n / 7
                rib.append(
                    [
                        shell(
                            z + 4.8 * f + dz,
                            side * (0.833 + 0.158 * f),
                            -0.04 + rise * math.sin(math.pi * (0.05 + 0.9 * f)) ** 0.35,
                        )
                        for dz, rise in [
                            (-0.34, 0),
                            (-0.18, 0.14),
                            (0.02, 0.23),
                            (0.19, 0.15),
                            (0.32, 0),
                        ]
                    ]
                )
            patch(obj, rib, trim)
    obj = part("Hand-laid carbon palm shell")
    rows = []
    for i in range(61):
        q = i / 60
        row = []
        for j in range(65):
            t = (j - 32) / 32
            s = abs(t)
            start = button_end(t) + 1.05 if s < 0.79 else 8 + (s - 0.79) * 65
            end = 63.70
            row.append(shell(start + (end - start) * q, t, 0.13))
        rows.append(row)
    patch(obj, rows, twill)

    def palm(x, y):
        z = 47 + y * 15.4
        return shell(z, math.asin(x * 23 / dimensions(z)[0]) * 2 / math.pi, 0.35)

    eye(obj, palm, make("Harpe palm light guide", "a1aab3", 0.08, 0.47, 0, 0.5))

    def thumb_profile(a, b, lift, center):
        z = center + a + 0.33 * b
        return shell(z, -(0.819 - 0.0155 * b - 0.0011 * a), lift)

    for center, title in [
        (-17.6, "Forward thumb switch"),
        (-3.1, "Backward thumb switch"),
    ]:
        obj = part(title)
        rows = []
        for w, h, r, lift in [
            (13.8, 6.22, 1.65, -0.32),
            (13.8, 6.22, 1.65, 0.17),
            (13.35, 5.81, 1.44, 0.79),
            (12.76, 5.25, 1.31, 1.17),
            (11.70, 4.38, 1.16, 1.26),
        ]:
            rows.append(
                [
                    thumb_profile(a, b, lift, center)
                    for a, b in tools["corners"](w, h, r, 6)
                ]
            )
        obj.rings(rows, trim, close=False)
        obj.add(rows[-1], [tuple(range(len(rows[-1])))], trim, False)
    obj = part("Tactile roller and Aura light guide")
    wheelz = -35.85
    wheely = 21.35
    for roller_sections, mat in [
        ([(-4.25, 4.5), (4.25, 4.5)], trim),
        (
            [
                (-3.52, 6.9),
                (-3.47, 8.2),
                (-3.28, 9.15),
                (-2.97, 9.55),
                (-2.61, 9.62),
                (2.61, 9.62),
                (2.97, 9.55),
                (3.28, 9.15),
                (3.47, 8.2),
                (3.52, 6.9),
            ],
            light,
        ),
        (
            [
                (-2.84, 9.46),
                (-2.65, 9.70),
                (-2.34, 9.80),
                (2.34, 9.80),
                (2.65, 9.70),
                (2.84, 9.46),
            ],
            wheel,
        ),
    ]:
        obj.rings(
            [
                [
                    (
                        x,
                        wheely + r * math.sin(i * math.tau / 64),
                        wheelz + r * math.cos(i * math.tau / 64),
                    )
                    for i in range(64)
                ]
                for x, r in roller_sections
            ],
            mat,
        )
    for i in range(42):
        phi = i * math.tau / 42
        obj.pipe(
            [
                (
                    x,
                    wheely + math.sin(phi + x * 0.037) * 9.83,
                    wheelz + math.cos(phi + x * 0.037) * 9.83,
                )
                for x in [-2.5, -1.1, 1.3, 2.5]
            ],
            0.19,
            wheel,
            5,
        )
    nose = part("Fixed carbon nose and roller bridge")
    rim = []
    for i in range(89):
        x = 29.0 * (i - 44) / 44
        row = []
        for rise, offset in [(0, 0.08), (0.20, 0.16), (1.48, 0.13), (1.65, 0.02)]:
            h = 8.21 + 2.22 * (abs(x) / 29) ** 1.65 + rise
            a, b = -63.75, -45.0
            for _ in range(19):
                mid = (a + b) / 2
                w, high = dimensions(mid)
                side = min(1, abs(x) / max(0.10, w - 0.7))
                c = math.sqrt(max(0, 1 - side * side))
                surf = 4.45 + (high - 4.45) * c**0.64 - 0.7 * c
                if surf < h or w < abs(x) + 0.7:
                    a = mid
                else:
                    b = mid
            row.append((x, h, max(-63.75, b - offset)))
        rim.append(row)
    patch(nose, rim, twill)
    for z0, z1 in [(-63.12, -45.9), (-25.5, -16.75)]:
        rows = []
        for j in range(13):
            z = z0 + (z1 - z0) * j / 12
            w = dimensions(z)[0]
            rows.append(
                [
                    shell(z, math.asin(3.63 * i / 8 / w) * 2 / math.pi, -0.24)
                    for i in range(-8, 9)
                ]
            )
        patch(nose, rows, twill)

    for s in (-1, 1):
        rows = []
        for j in range(37):
            z = -59.8 + 66.9 * j / 36
            rows.append(
                [shell(z, s * (0.787 + k * 0.052 / 5), -0.09) for k in range(6)]
            )
        patch(nose, rows, twill)

    corners = tools["corners"]
    cuts = []

    def port_ring(w, h, r, z):
        return [(x, 5.42 + y, z + 0.018 * x * x) for x, y in corners(w, h, r, 7)]

    def cutter(rings, name):
        tool = Sculpture(name)
        tool.rings(rings, seam)
        cuts.append(tool.finalize())

    cutter(
        [port_ring(10.28, 4.68, 2.02, z) for z in (-66.0, -55.8)],
        "Front socket aperture",
    )
    usb = part("USB Type-C receptacle")
    usb.rings(
        [
            port_ring(w, h, r, z)
            for w, h, r, z in [
                (10.22, 4.62, 2.0, -62.95),
                (9.97, 4.37, 1.89, -63.08),
                (9.23, 3.75, 1.51, -63.08),
                (9.04, 3.57, 1.41, -62.82),
                (9.04, 3.57, 1.41, -57.35),
            ]
        ],
        seam,
        close=False,
    )
    usb.rings(
        [
            port_ring(w, h, r, z)
            for w, h, r, z in [
                (9.16, 3.68, 1.46, -62.86),
                (8.96, 3.48, 1.36, -62.96),
                (8.47, 3.05, 1.23, -62.91),
                (8.37, 2.95, 1.18, -62.59),
                (8.37, 2.95, 1.18, -57.30),
            ]
        ],
        steel,
        close=False,
    )
    usb.rings(
        [
            [(x, 5.42 + y, z) for x, y in corners(6.6, 0.7, 0.3)]
            for z in (-61.86, -57.20)
        ],
        trim,
    )
    usb.add(port_ring(8.37, 2.95, 1.18, -57.23), [tuple(range(32))], seam, False)
    contact = make("Harpe · contact plating", "b5a473", 0.71, 0.32)
    for i in range(12):
        x = (i - 5.5) * 0.47
        for h in (5.055, 5.785):
            usb.add(
                [
                    (x + d, h, z)
                    for d, z in [
                        (-0.10, -61.38),
                        (0.10, -61.38),
                        (0.10, -58.15),
                        (-0.10, -58.15),
                    ]
                ],
                [(0, 1, 2, 3)],
                contact,
                False,
            )

    def chaikin(points):
        return [
            ((1 - t) * x + t * u, (1 - t) * z + t * v)
            for (x, z), (u, v) in zip(points, points[1:] + points[:1])
            for t in (0.2, 0.8)
        ]

    def bottom_pad(obj, outline):
        cx = sum(x for x, z in outline) / len(outline)
        cz = sum(z for x, z in outline) / len(outline)
        outline = chaikin(chaikin(outline))
        obj.rings(
            [
                [(cx + (x - cx) * k, h, cz + (z - cz) * k) for x, z in outline]
                for k, h in [(0.975, 1.06), (1, 0.64), (0.988, 0.20), (0.948, 0)]
            ],
            skate,
        )

    pad_outlines = {
        "fore": [
            (10.1, -41.0),
            (12.8, -45.5),
            (17.8, -53.5),
            (20.4, -54.1),
            (25.7, -48.6),
            (27.2, -43.6),
            (26.6, -39.8),
            (24.1, -37.6),
            (12.0, -37.4),
        ],
        "aft": [
            (13.0, 35.7),
            (24.7, 35.7),
            (27.1, 37.0),
            (27.4, 39.6),
            (25.6, 43.1),
            (20.2, 49.9),
            (17.1, 51.9),
            (14.6, 50.4),
            (11.9, 43.8),
            (11.4, 39.1),
        ],
    }
    for end, outline in pad_outlines.items():
        for s, side in [(-1, "left"), (1, "right")]:
            bottom_pad(
                part(f"Small PTFE foot · {end} {side}"),
                [(s * x, z) for x, z in outline],
            )

    sensor_z = -2.2

    def annulus(obj, profile, material):
        obj.rings(
            [
                [
                    (
                        r * math.cos(i * math.tau / 64),
                        h,
                        sensor_z + r * math.sin(i * math.tau / 64),
                    )
                    for i in range(64)
                ]
                for r, h in profile
            ],
            material,
            close=False,
        )

    cutter(
        [
            [(x, h, sensor_z + z) for x, z in corners(7.6, 8.4, 1.25, 6)]
            for h in (-1.2, 6.6)
        ],
        "Optical tracking aperture",
    )
    optics = part("AimPoint Pro tracking lens and sensor skate")
    annulus(
        optics,
        [
            (8.48, 1.07),
            (8.28, 0.25),
            (7.94, 0.04),
            (6.54, 0.04),
            (6.28, 0.27),
            (6.28, 1.10),
        ],
        skate,
    )
    annulus(optics, [(6.27, 1.02), (6.15, 0.72), (5.9, 0.7), (5.85, 1.33)], trim)
    optics.rings(
        [
            [(x, h, sensor_z + z) for x, z in corners(w, d, r, 6)]
            for w, d, r, h in [
                (7.6, 8.4, 1.25, 1.08),
                (6.95, 7.75, 1.05, 2.05),
                (5.9, 6.7, 0.69, 3.75),
            ]
        ],
        trim,
        close=False,
    )
    optics.form((0, 3.2, sensor_z + 0.55), (2.1, 0.85, 2.85), optic)
    optics.form((0, 3.62, sensor_z - 2.35), (1.04, 0.6, 0.66), optic)

    label = part("Underbody pad printing")
    print_art = json.loads(Path(__file__).with_name("harpe-base-print.json").read_text(encoding="utf-8"))
    inlay = tools["inlay"]
    for stamp in print_art["body"]:
        inlay(label, stamp, lambda u, v: (-u, 0.87, v), metal)
    for x, z, word in [(16.5, -10, "DPI"), (16.5, 4.7, "PAIR")]:
        key = part(word + " underside button")
        disk(key, x, z, [(4.02, 1.08), (4.02, 0.79), (3.76, 0.71), (3.61, 0.74)], trim)
        disk(key, x, z, [(3.49, 0.8), (3.44, 0.46), (2.97, 0.42)], seam)
        inlay(key, print_art[word], lambda u, v: (x - u, 0.40, z + v), metal)
    selector = part("Three-position connection selector")
    slab(selector, -16.5, -2.2, 7.4, 13.1, 3.6, [(0.99, 0.0), (0.63, 0.24)], trim)
    slab(selector, -16.5, -2.2, 6.25, 11.55, 3.02, [(0.61, 0.0), (0.59, 0.2)], seam)
    slab(selector, -16.5, -4.94, 5.65, 5.3, 1.8, [(0.6, 0), (0.25, 0.13)], trim)
    for z in [-6.25, -5.05, -3.85]:
        selector.pipe([(-18.29, 0.20, z), (-14.71, 0.20, z)], 0.17, seam, 6, 0.65)
    guide = part("Underside service panel joint")
    panel = [
        (x * ((25.7 if z < 0 else 28.2) / 26), z) for x, z in corners(52, 71.9, 3.45, 6)
    ]
    guide.pipe(
        [(x, 0.98, z - 2.95) for x, z in [*panel, panel[0]]], 0.14, trim, 6, 0.50
    )

    products = [
        item.finalize(40, [twill]) if twill in item.materials else item.finalize()
        for item in parts
    ]
    chassis = products[0]
    electronics = runpy.run_path(str(Path(__file__).with_name("harpe-electronics.py")))
    carrier = electronics["split_housing"](chassis)
    products.append(carrier)
    bpy.context.view_layer.objects.active = chassis
    for cut in cuts:
        difference = chassis.modifiers.new(cut.name, "BOOLEAN")
        difference.operation = "DIFFERENCE"
        difference.solver = "MANIFOLD"
        difference.object = cut
        bpy.ops.object.modifier_apply(modifier=difference.name)
        if not chassis.data.polygons:
            raise ValueError(f"Chassis lost its surface after cutting {cut.name}")
        bpy.data.objects.remove(cut, do_unlink=True)
    for face in chassis.data.polygons:
        if face.normal.z < -0.95:
            face.use_smooth = False
    products.append(electronics["lighten_tray"](chassis, Sculpture, seam, dimensions))
    roller_slot = Sculpture("Roller opening tool")
    roller_slot.rings(
        [[(x, h, wheelz + z) for x, z in corners(8.75, 21.6, 1.18)] for h in (15, 38)],
        seam,
    )
    roller_tool = roller_slot.finalize()
    bpy.context.view_layer.objects.active = carrier
    difference = carrier.modifiers.new("Wheel opening", "BOOLEAN")
    difference.operation = "DIFFERENCE"
    difference.solver = "EXACT"
    difference.object = roller_tool
    bpy.ops.object.modifier_apply(modifier=difference.name)
    if not carrier.data.polygons:
        raise ValueError("Missing upper shell carrier")
    bpy.data.objects.remove(roller_tool, do_unlink=True)
    products.extend(electronics["internals"](Sculpture, make, tools))
    for item in products:
        if twill.name not in item.data.materials or not item.data.uv_layers.active:
            continue
        uv = item.data.uv_layers.active
        mirror = -1 if item.name.endswith("right") else 1
        for poly in item.data.polygons:
            if item.data.materials[poly.material_index] != twill:
                continue
            for index in poly.loop_indices:
                point = item.data.vertices[item.data.loops[index].vertex_index].co
                _, high = dimensions(-point.y * 1000)
                drop = max(0, high / 1000 - point.z)
                u = math.copysign(math.hypot(point.x, drop) + 0.16 * drop, point.x)
                v = point.y + 0.075 * point.z
                uv.data[index].uv = (mirror * u * 40, v * 40)
    return products
