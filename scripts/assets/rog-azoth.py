import math
import runpy
from pathlib import Path


def build(Sculpture, make, tools):
    stack = runpy.run_path(str(Path(__file__).with_name("azoth-stack.py")))
    lettering = runpy.run_path(str(Path(__file__).with_name("azoth-legends.py")))
    parts = []

    def finish(component, enclosed=False):
        textured = {
            m
            for m in component.materials
            if any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes)
        }
        part = component.finalize(50 if textured else 0, textured)
        part["productEnclosed"] = enclosed
        return part

    obj = Sculpture("Azoth | CNC lower tray")
    slab, disk, outline, eye = [tools[k] for k in ("slab", "disk", "corners", "eye")]
    alloy = make("Azoth · bead-blasted aluminum", "37383a", 0.73, 0.43)
    graphite = make("Azoth · dark anodized frame", "292b2c", 0.73, 0.43)
    bevel = make("Azoth · machined edges", "636565", 0.82, 0.30)
    black = make("Azoth · recessed well", "111213", 0.13, 0.77)
    pbt = make("Azoth · graphite doubleshot PBT", "303033", 0.02, 0.72)
    pbt_mod = make("Azoth · modifiers", "262729", 0.015, 0.69)
    silicone = make("Azoth · silicone wrist pad", "323436", 0.015, 0.84)
    rubber = make("Azoth · feet and deboss", "1e2021", 0.02, 0.88)
    steel = make("Azoth · polished plate", "a3a39f", 0.95, 0.18)
    marking = make("Azoth · silver transfer", "c0bfb4", 0.20, 0.58)
    cf = tools["carbon"](
        make("Azoth · carbon-fiber positioning plate", "242525", 0.25, 0.49, 0.12)
    )
    screen = make("Azoth · OLED touch glass", "090b12", 0.20, 0.17, 0.6)
    badge = make("Azoth OLED", "ffffff", 0.02, 0.26)
    stack["screen_art"](badge)
    highlight = make("Azoth · OLED emblem", "e9e2f4", 0, 0.29, 0, 0.42)
    legends = [
        make(f"Azoth legend {i:02d}", "c7c7c3", 0.05, 0.57, 0, 0.14) for i in range(12)
    ]
    emit = [
        make(f"Azoth diffuser {i:02d}", "66654f", 0.01, 0.58, 0, 0.12)
        for i in range(12)
    ]
    slope = 0.084
    bottom = lambda z: 1.25 + (69 - z) * 0.057
    deck = lambda z: 22.6 - z * slope
    inner = outline(322.6, 130.0, 2.75)
    lower = lambda inset: outline(330.4 - 2 * inset, 137.8 - 2 * inset, 4 - inset)
    upper = lambda inset: outline(332 - 2 * inset, 139 - 2 * inset, 4.3 - inset)
    stack["stepped_shell"](
        obj,
        lower,
        [(5.3, 1.5), (5.7, 0.6), (6.3, 0), (14.0, 0), (14.4, 0.27)],
        inner,
        graphite,
        0.057,
    )
    bay = [(x, z - 9) for x, z in outline(85.5, 55.4, 2.8)]
    stack["sheet"](obj, inner, [bay], 5.3, 6.85, graphite, 0.057)
    parts.append(finish(obj))
    obj = Sculpture("Azoth | Die-cut perimeter seam")
    seam = outline(330.5, 137.95, 4.05)
    obj.rings(
        [
            [(x, h - s * z, z) for x, z in edge]
            for edge, h, s in [
                (seam, 13.45, 0.057),
                (seam, 14.65, slope),
                (inner, 14.65, slope),
                (inner, 13.45, 0.057),
                (seam, 13.45, 0.057),
            ]
        ],
        black,
        False,
        False,
    )
    parts.append(finish(obj))
    obj = Sculpture("Azoth | Bead-blasted upper bezel")
    stack["stepped_shell"](
        obj,
        upper,
        [(13.5, 0.65), (14.4, 0.35), (15.3, 0), (23.6, 0), (24.0, 0.42)],
        inner,
        alloy,
        slope,
    )
    pitch = 19.05
    keymap = lettering["layout"]["rows"]
    function_wells = []
    for group in [keymap[0][0:1], keymap[0][1:5], keymap[0][5:9], keymap[0][9:13]]:
        left, right = group[0]["x"] - pitch / 2, group[-1]["x"] + pitch / 2
        function_wells.append(
            [
                (u + (left + right) / 2, v + group[0]["z"])
                for u, v in outline(right - left + 0.5, 19.2, 1.55)
            ]
        )
    clearance = [
        *function_wells,
        [
            (-157.35, -36.65),
            (128.9, -36.65),
            (128.9, 20.65),
            (109.85, 20.65),
            (109.85, 39.7),
            (90.8, 39.7),
            (90.8, 58.9),
            (-157.35, 58.9),
        ],
        [(135.65, -37), (155.15, -37), (155.15, 40.2), (135.65, 40.2)],
        [
            (113.52, 24.13),
            (132.86, 24.13),
            (132.86, 43.25),
            (151.90, 43.25),
            (151.90, 62.64),
            (94.45, 62.64),
            (94.45, 43.25),
            (113.52, 43.25),
        ],
    ]
    stack["sheet"](obj, inner, clearance, 21.95, 24.0, alloy, slope)
    parts.append(finish(obj))
    for shell in parts:
        stack["crop_rear"](shell)
    obj = Sculpture("Azoth | Rear I/O fascia and USB-C receptacle")
    stack["rear_io"](obj, tools, make, alloy, rubber, steel, marking)
    parts.append(finish(obj))
    obj = Sculpture("Azoth | Feet and underside hardware")
    for sign in (-1, 1):
        x = sign * 138
        disk(
            obj,
            x,
            -50,
            [
                (10.2, 9.9),
                (11.4, 9.3),
                (11.6, 8.7),
                (8.4, 5.1),
                (4.0, 0.6),
                (3.6, 0.30),
            ],
            bevel,
        )
        disk(obj, x, -50, [(4.1, 0.5), (4, 0.06)], rubber)
        for z in [56, -57]:
            slab(
                obj,
                sign * 153,
                z,
                12 if z > 0 else 5,
                4 if z > 0 else 9,
                1.8,
                [(bottom(z) - 0.52, 0.28), (bottom(z) + 0.1, 0)],
                rubber,
            )
    for x, z in [
        (-157, -64),
        (-58, -65),
        (57, -65),
        (158, -64),
        (-159, -12),
        (159, -12),
        (-155, 64),
        (-55, 64),
        (54, 64),
        (156, 64),
    ]:
        disk(obj, x, z, [(1.7, bottom(z) + 0.24), (1.61, bottom(z) - 0.16)], black)
        obj.pipe(
            [(x - 1, bottom(z) - 0.22, z), (x + 1, bottom(z) - 0.22, z)], 0.14, bevel, 5
        )
    brushed = make("Azoth · underside blasted inlays", "4b4d4e", 0.39, 0.49)
    for side in [-1, 1]:
        loops = [
            [
                (150, -38),
                (144, -34),
                (83, 28),
                (80, 31),
                (74, 31),
                (47, 3),
                (47, -30),
                (62, -52),
                (112, -54),
            ],
            [(147, -17), (147, 50), (80, 50), (75, 46), (132, -10), (142, -18)],
        ]
        for loop in loops:
            verts = [(side * x, bottom(z) - 0.32, z) for x, z in loop]
            obj.rings([verts, [(x, h + 0.45, z) for x, h, z in verts]], brushed, False)
        for k in range(13):
            x = 66 + k * 5.6
            obj.pipe(
                [
                    (side * x, bottom(-35) - 0.47, -35),
                    (side * (x - 11), bottom(-46) - 0.47, -46),
                ],
                0.19,
                alloy,
                5,
                0.32,
            )
    for i in range(-47, 48):
        line = i * 4
        lo = max(-64, -155 - line)
        hi = min(64, 155 - line)
        if hi <= lo:
            continue
        enter = max(-38, -44 - line)
        leave = min(20, 44 - line)
        spans = (
            [(lo, hi)]
            if enter >= leave
            else [(lo, min(hi, enter)), (max(lo, leave), hi)]
        )
        for start, end in spans:
            if end > start:
                obj.pipe(
                    [(line + z, bottom(z) - 0.03, z) for z in (start, end)],
                    0.19,
                    graphite,
                    6,
                    0.32,
                )
    parts.append(finish(obj))
    obj = Sculpture("Azoth | Removable polished nameplate")
    gunmetal = make("Azoth · smoked polished nameplate", "53514e", 0.87, 0.23)
    slab(
        obj,
        0,
        -9,
        84.3,
        54.2,
        2.8,
        [(4.85, 0.4), (5.12, 0), (5.6, 0.22)],
        gunmetal,
        0.057,
    )

    def underneath(x, z):
        return (-x, 4.83 - z * 0.057, z)

    eye(
        obj,
        lambda x, y: underneath(x * 36, -10 + y * 42),
        marking,
        engraving_width=0.008,
    )
    obj.add(
        [underneath(-1.65, -34), underneath(1.65, -34), underneath(0, -31.8)],
        [(0, 1, 2)],
        marking,
        False,
    )
    for sign in (-1, 1):
        for p, q in [
            ((sign * 38.4, -10), (sign * 38.4, -8)),
            ((sign * 38.4, -9), (sign * 37.25, -9)),
        ]:
            obj.pipe([underneath(*p), underneath(*q)], 0.11, marking, 6)
    for msg, z in [("R O G   A Z O T H", 6), ("E X T R E M E", 9.1)]:
        obj.label(msg, 2.55, lambda x, y: underneath(x, z - y), marking)
    for z in (-33, 15):
        for i in range(-19, 20):
            if abs(i) < (2 if z < 0 else 8):
                continue
            x = i * 1.92
            obj.add(
                [
                    underneath(x + u, z + v)
                    for u, v in [(-0.88, -0.7), (0.22, -0.7), (0.9, 0.7), (-0.2, 0.7)]
                ],
                [(0, 1, 2, 3)],
                marking,
                False,
            )
    parts.append(finish(obj))
    obj = Sculpture("Azoth | Magnetic receiver bay and gasket paddle")
    pocket = [(x, z - 9) for x, z in outline(84.9, 54.8, 2.5)]
    obj.rings(
        [[(x, h - 0.057 * z, z) for x, z in pocket] for h in (5.65, 9.2)],
        black,
        False,
        False,
    )
    stack["sheet"](
        obj,
        pocket,
        [stack["rectangle"](-14, -7, 12, 6), stack["rectangle"](14, -7, 20, 9)],
        9.2,
        10.1,
        black,
        0.057,
    )
    for x in (-33, 33):
        disk(obj, x, -10, [(2.6, 7.5), (2.6, 9.4)], steel)
    slab(
        obj, -14, -7, 6.4, 4.6, 0.6, [(6.8, 0.3), (7.25, 0), (9.5, 0)], graphite, 0.057
    )
    slab(
        obj, 14, -7, 17.9, 8.3, 0.65, [(7.2, 0.3), (7.6, 0), (10.0, 0)], graphite, 0.057
    )
    parts.append(finish(obj, True))
    obj = Sculpture("Azoth | OLED and three-way encoder")
    slab(
        obj,
        136,
        -50,
        39,
        22,
        2.0,
        [(deck(-50) + 1.22, 0.3), (deck(-50) + 2.03, 0), (deck(-50) + 2.42, 0.48)],
        black,
    )
    slab(
        obj,
        136,
        -50,
        33.7,
        17.6,
        1.8,
        [(deck(-50) + 2.44, 0), (deck(-50) + 2.65, 0.2)],
        screen,
    )
    display_height = deck(-50) + 2.65
    top_glass = len(obj.faces) - 1
    obj.materials.append(badge)
    obj.inks[top_glass] = len(obj.materials) - 1
    eye(
        obj,
        lambda x, y: (136 + x * 23.8, display_height + 0.11, -50 + y * 18.5),
        highlight,
    )
    wheel_rows = []
    for x, r, relief in [
        (154.6, 3.85, 0),
        (155.65, 4.0, 0),
        (155.9, 6.05, 0),
        (156.24, 6.52, 0),
        (156.58, 6.52, 0),
        (156.77, 6.30, 0),
        (157.12, 6.38, 0.51),
        (163.85, 6.38, 0.51),
        (164.17, 6.30, 0),
        (164.36, 6.52, 0),
        (164.65, 6.52, 0),
        (165.22, 6.02, 0),
        (165.22, 4.64, 0),
        (164.82, 4.42, 0),
    ]:
        row = []
        for j in range(112):
            angle = j * math.tau / 112
            radius = r + relief * (0, 1, 1, 0)[j % 4]
            row.append(
                (
                    x,
                    deck(-50) + 2 + radius * math.cos(angle),
                    -50 + radius * math.sin(angle),
                )
            )
        wheel_rows.append(row)
    obj.rings(wheel_rows, graphite, False, False)
    obj.pipe(
        [
            (164.82, deck(-50) + 2, -50),
            (165.33, deck(-50) + 2, -50),
            (165.6, deck(-50) + 2, -50),
        ],
        [4.38, 4.34, 4.05],
        alloy,
        48,
    )
    encoder = finish(obj)
    uv = encoder.data.uv_layers.active
    for poly in encoder.data.polygons:
        if encoder.data.materials[poly.material_index] != badge:
            continue
        if poly.normal.z < 0:
            poly.flip()
        for loop_id in poly.loop_indices:
            v = encoder.data.vertices[encoder.data.loops[loop_id].vertex_index].co
            uv.data[loop_id].uv = (
                (v.x * 1000 - 136) / 32.9 + 0.5,
                (v.y * 1000 - 50) / 16.8 + 0.5,
            )
    parts.append(encoder)
    obj = Sculpture("Azoth | Wrist rest, cast base and silicone cushion")
    wrist_z = 117.15
    slab(
        obj,
        0,
        wrist_z,
        328.0,
        94.5,
        4.9,
        [(0.55, 1), (0.9, 0.38), (1.5, 0), (4.4, 0), (4.8, 0.32)],
        graphite,
    )
    wrist_h = lambda z: 8.6 + 10.9 * (1 - max(0, (z - 70) / 96) ** 1.6)
    rows = []
    for f, h, inset in [(0, 4.5, 0.07), (0.32, 5, 0.1), (0.91, 0, 0.4), (1, 0, 1.35)]:
        rows.append(
            [
                (x, (1 - f) * h + f * wrist_h(wrist_z + d), wrist_z + d)
                for x, d in outline(327.5 - 2 * inset, 94.5 - 2 * inset, 4.7 - inset)
            ]
        )
    top_loop = rows[-1]
    for step in range(1, 14):
        scale = 1 - step / 14
        rows.append(
            [
                (
                    x * scale,
                    wrist_h(wrist_z + (z - wrist_z) * scale),
                    wrist_z + (z - wrist_z) * scale,
                )
                for x, h, z in top_loop
            ]
        )
    obj.rings(rows, silicone)
    eye(
        obj,
        lambda x, y: (80 + x * 141, wrist_h(116 + y * 105) + 0.2, 116 + y * 105),
        rubber,
        True,
    )
    obj.label(
        "ROG", 3.15, lambda x, y: (-150 + x, wrist_h(155 - y) + 0.15, 155 - y), graphite
    )
    for z in (86, 148):
        for x in (-143, -82, -32, 34, 83, 142):
            sgn = -1 if (x < 0) == (z < 100) else 1
            obj.pipe(
                [(x - sgn * 8, 0.36, z - 8), (x + sgn * 8, 0.36, z + 8)],
                1.55,
                rubber,
                8,
                0.4,
            )
    parts.append(finish(obj))
    slope_by_row = [-0.02, 0.012, 0.11, 0.132, 0.053, -0.07]
    keys_and_positions = []
    for row, keys in enumerate(keymap):
        for stamp in keys:
            key, x, z = stamp["key"], stamp["x"], stamp["z"]
            w = pitch * stamp["units"]
            keys_and_positions.append((row, key, x, z, w))
            obj = Sculpture(f"Azoth | Keycap {len(keys_and_positions):02d} {key}")
            i = min(11, max(0, int((x + 160) * 12 / 320)))
            y = deck(z) + [11.7, 10.7, 9.9, 9, 8.8, 9.0][row]
            tilt = slope_by_row[row]

            def top_height(u, v):
                dish = (
                    0.88 * (u / max(1, w * 0.5 - 2.8)) ** 2
                    if w < 70
                    else 0.7 - 0.5 * (u / (w * 0.5)) ** 2
                )
                return y + dish - tilt * v

            rings = []
            face_width, face_depth = stamp["width"], stamp["height"]
            for cap_width, zsize, rad, height in [
                (w - 1, 17.7, 1.12, -6.6),
                (w - 0.9, 17.9, 1.2, -6.15),
                (face_width + 1, 15.3, 1.38, -0.55),
                (face_width, face_depth, 1.45, 0),
            ]:
                pts = outline(cap_width, zsize, rad)
                rings.append(
                    [(x + u, top_height(u, v) + height, z + v) for u, v in pts]
                )
            cap = pbt if len(key) == 1 or key.startswith("F") else pbt_mod
            obj.rings(rings, cap, close=False)
            lining = [
                [
                    (x + (u - x) * factor, h + lift, z + (v - z) * factor)
                    for u, h, v in ring
                ]
                for ring, factor, lift in [(rings[0], 0.88, 0), (rings[-1], 0.88, -1.2)]
            ]
            obj.rings([rings[0], *lining], cap, False, False)
            obj.add(lining[-1], [tuple(range(len(lining[-1])))], cap, False)
            for mount in (
                (-50, 0, 50)
                if key == "Space"
                else ((-11.9, 0, 11.9) if w >= 38 else (0,))
            ):
                ceiling = top_height(mount, 0) - 1.12
                stack["socket_ring"](
                    obj,
                    x + mount,
                    z,
                    min(deck(z) + 5.65, ceiling - 1.4),
                    ceiling,
                    2.52,
                    cap,
                )
            rim = outline(face_width, face_depth, 1.45)
            half = face_width / 2
            stations = {round(u, 6) for u, _ in rim}
            divisions = max(10, math.ceil(half))
            stations.update(
                round((half - 1.45) * (2 * i / divisions - 1), 6)
                for i in range(divisions + 1)
            )
            lanes = []
            for u in sorted(stations):
                corner = max(0, abs(u) - (half - 1.45))
                reach = face_depth / 2 - 1.45 + math.sqrt(max(0, 1.45**2 - corner**2))
                lanes.extend(
                    [(x + u, top_height(u, v), z + v) for v in (-reach, reach)]
                )
            obj.add(
                lanes,
                [(i, i + 1, i + 3, i + 2) for i in range(0, len(lanes) - 2, 2)],
                cap,
            )

            lettering["mark"](obj, stamp, x, z, top_height, legends[i], marking, tools["inlay"])
            if key in ("F", "J"):
                obj.pipe(
                    [
                        (x + u, top_height(u, 4.35) + 0.15, z + 4.35)
                        for u in (-1.8, 1.8)
                    ],
                    0.22,
                    cap,
                    8,
                )
            cap_part = finish(obj)
            for polygon in cap_part.data.polygons:
                surface = cap_part.data.materials[polygon.material_index]
                if surface == legends[i] and polygon.normal.z < 0:
                    polygon.flip()
                elif surface == marking and polygon.normal.y > 0:
                    polygon.flip()
            cap_part.data.update()
            parts.append(cap_part)
    assert len(keys_and_positions) == 81
    lights = Sculpture("Azoth | North-facing switch light pipes")
    for row, key, x, z, w in keys_and_positions:
        band = min(11, max(0, int((x + 160) * 12 / 320)))
        slab(
            lights,
            x,
            z - 5.85,
            5.2,
            1.8,
            0.55,
            [(23.25, 0.3), (24.07, 0), (25.8, 0.18)],
            emit[band],
            slope,
        )
    parts.append(finish(lights))
    parts.extend(
        stack["add_stack"](Sculpture, make, tools, keys_and_positions, cf, finish)
    )
    return parts
