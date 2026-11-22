import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


def split_housing(frame):
    upper = frame.copy()
    upper.data = frame.data.copy()
    upper.name = "Carbon shell backing and paddle carrier"
    bpy.context.collection.objects.link(upper)
    for piece, lower, thickness in [(frame, True, 0.00085), (upper, False, 0.00062)]:
        bm = bmesh.new()
        bm.from_mesh(piece.data)
        bmesh.ops.bisect_plane(
            bm,
            geom=[*bm.verts, *bm.edges, *bm.faces],
            dist=0.0000001,
            plane_co=(0, 0, 0.00785),
            plane_no=(0, 0, 1),
            clear_outer=lower,
            clear_inner=not lower,
        )
        bm.to_mesh(piece.data)
        bm.free()
        shell = piece.modifiers.new("Moulded wall thickness", "SOLIDIFY")
        shell.thickness = thickness
        shell.offset = -1
        bpy.context.view_layer.objects.active = piece
        bpy.ops.object.modifier_apply(modifier=shell.name)
        for vertex in piece.data.vertices:
            vertex.co.y = max(-0.06375, min(0.06375, vertex.co.y))
    return upper


def lighten_tray(tray, sculpture, material, dimensions):
    pockets = sculpture("Core pins for weight relief")
    rows = [
        (-50, (16,)),
        (-47, (14, 18)),
        (-44, (12, 16, 20)),
        (-27, (5, 10, 15, 20)),
        (-22, (5, 10, 15, 20)),
        (-17, (5, 10, 15, 20)),
        (8, (3, 8, 13, 18, 23)),
        (13, (3, 8, 13, 18, 23)),
        (18, (3, 8, 13, 18, 23)),
        (36, (14, 18, 22)),
        (40, (16, 20)),
        (44, (17,)),
    ]
    for z, columns in rows:
        for x in columns:
            for side in (-1, 1):
                pockets.rings(
                    [
                        [
                            (
                                side * x + 1.18 * math.cos(i * math.tau / 16),
                                h,
                                z + 1.18 * math.sin(i * math.tau / 16),
                            )
                            for i in range(16)
                        ]
                        for h in (0.63, 2.52)
                    ],
                    material,
                )
    cutter = pockets.finalize()
    bpy.context.view_layer.objects.active = tray
    modifier = tray.modifiers.new("Moulded weight relief in floor", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    covers = sculpture("Backing film behind undertray perforations")
    for first, last in [(-51.8, -42.1), (-28.8, -15.2), (6.2, 19.8), (34.2, 45.8)]:
        hull = [
            (s * (dimensions(z)[0] * 0.87), z)
            for s, levels in [
                (1, (first, (first + last) / 2, last)),
                (-1, (last, (first + last) / 2, first)),
            ]
            for z in levels
        ]
        covers.rings(
            [[(x, h, z) for x, z in hull] for h in (0.96, 1.02)], material, False
        )
    return covers.finalize()


def internals(sculpture, finish, tools):
    parts = []
    mask = finish("P718 · black solder mask", "242724", 0.14, 0.44)
    laminate = finish("P718 · machined FR4 edge", "827650", 0.08, 0.67)
    graphite = finish("P718 · switch housing", "242526", 0.08, 0.48)
    silver = finish("P718 · solder and stamped contacts", "aaaba5", 0.76, 0.33)
    ceramic = finish("P718 · capacitor ceramic", "9e8b70", 0.06, 0.64)
    screen = finish("P718 · white legend ink", "dedbc9", 0.01, 0.63)
    blue = finish("P718 · encoder dust cover", "3c80b0", 0.06, 0.51)
    red = finish("P718 · optical switch plungers", "a43738", 0.04, 0.53)
    film = finish("P718 · pouch edge tape", "c79837", 0.31, 0.32)
    foil = finish("P718 · aluminium polyester pouch", "aca9a3", 0.66, 0.35)
    yellow = finish("P718 · thermistor lead", "e6ad41", 0.01, 0.53)

    def component(name):
        part = sculpture(name)
        parts.append(part)
        return part

    def block(part, x, z, width, depth, low, high, mat, radius=0.25):
        tools["slab"](part, x, z, width, depth, radius, [(low, 0), (high, 0)], mat)

    def board_coordinates(x, y):
        return (x - 515) / 4.12, (y - 966) / 4.10 - 2.2

    board = component("P718 · milled main PCB with wheel aperture")
    outer = [
        (495, 759),
        (534, 759),
        (536, 786),
        (592, 790),
        (599, 796),
        (599, 860),
        (579, 860),
        (576, 873),
        (575, 919),
        (586, 922),
        (590, 932),
        (589, 1018),
        (586, 1023),
        (538, 1023),
        (536, 1041),
        (488, 1041),
        (488, 1021),
        (448, 1021),
        (430, 1008),
        (426, 995),
        (429, 880),
        (407, 860),
        (405, 824),
        (413, 815),
        (435, 817),
        (438, 793),
        (491, 787),
    ]
    window = [
        (482, 805),
        (493, 799),
        (504, 799),
        (507, 818),
        (521, 818),
        (524, 800),
        (544, 800),
        (551, 807),
        (550, 837),
        (556, 840),
        (554, 906),
        (551, 910),
        (524, 910),
        (523, 884),
        (521, 879),
        (511, 879),
        (509, 883),
        (508, 910),
        (481, 910),
        (478, 905),
        (479, 849),
        (485, 845),
    ]

    def board_loop(points):
        return [board_coordinates(x, y) for x, y in points]

    outline, opening = board_loop(outer), board_loop(window)
    loops = [outline, opening]
    for cx, cy in [(448, 854), (585, 854), (513, 1021)]:
        x, z = board_coordinates(cx, cy)
        loops.append(
            [
                (
                    x + 1.46 * math.cos(i * math.tau / 20),
                    z + 1.46 * math.sin(i * math.tau / 20),
                )
                for i in range(20)
            ]
        )

    contours = []
    for index, points in enumerate(loops):
        signed = sum(
            x * v - z * u for (x, z), (u, v) in zip(points, points[1:] + points[:1])
        )
        ring = list(reversed(points)) if (signed > 0) != (index == 0) else points
        contours.append([Vector((x, z, 0)) for x, z in ring])
        board.rings(
            [[(x, h, z) for x, z in ring] for h in (5.00, 5.94)], laminate, False, False
        )
    triangles = tessellate_polygon(contours)
    for h in (5.00, 5.94):
        board.add(
            [(p.x, h, p.y) for ring in contours for p in ring], triangles, mask, False
        )

    for x, side in [(-16.1, "left"), (17.2, "right")]:
        switch = component("ROG optical micro switch · " + side)
        block(switch, x, -40.3, 5.65, 12.4, 5.95, 11.6, graphite, 0.65)
        block(switch, x, -41.8, 3.35, 2.35, 11.6, 12.8, red, 0.42)
        for y in (-44.5, -37):
            block(switch, x, y, 4.6, 0.66, 11.55, 11.74, silver, 0.15)

    encoder = component("TTC Gold · wheel encoder and through axle")
    block(encoder, -9.25, -35.85, 2.6, 10.4, 5.94, 23.7, silver, 0.38)
    block(encoder, -9.27, -35.85, 2.78, 8.8, 8.0, 23.4, blue, 0.58)
    encoder.pipe([(-10.8, 21.35, -35.85), (-3.3, 21.35, -35.85)], 0.97, graphite, 8)
    encoder.pipe([(3.3, 21.35, -35.85), (13.0, 21.35, -35.85)], 1.43, graphite, 12)
    for z in (-38.25, -33.45):
        block(encoder, 12.75, z, 2.0, 1.45, 5.94, 22.7, graphite, 0.35)
    block(encoder, 12.75, -35.85, 2.0, 4.8, 18.5, 20.0, graphite)

    chip = component("AimPoint Pro · sensor package, leads and radio")
    block(chip, 0, -2.2, 10.8, 16.2, 5.94, 8.22, graphite, 0.48)
    block(chip, 0, -2.2, 9.6, 15.0, 8.22, 8.30, silver, 0.62)
    tools["disk"](chip, 0, -4.8, [(1.72, 8.30), (1.65, 8.36)], mask)
    tools["disk"](chip, 0, 1.72, [(2.08, 8.30), (1.97, 8.36)], mask)
    for side in (-1, 1):
        for i in range(8):
            block(
                chip, side * 5.9, -8.9 + 1.92 * i, 1.3, 0.65, 5.95, 6.68, silver, 0.09
            )
    block(chip, -12.7, -11.4, 7.0, 7.0, 5.94, 6.95, graphite)
    block(chip, -12.7, -11.4, 5.8, 5.8, 6.95, 7.0, mask)
    chip.label("N52840", 0.87, lambda a, b: (-12.7 + a, 7.02, -11.4 - b), screen)
    antenna = component("P718 · folded edge antenna, USB tails and mounting bosses")
    block(antenna, -24, -33.6, 1.55, 9.7, 4.8, 5.01, silver)
    for x in (-5.0, 5.0):
        block(antenna, x, -55.95, 1.35, 5.5, 5.07, 5.9, silver)
    for x, y in [(448, 854), (585, 854), (513, 1021)]:
        a, b = board_coordinates(x, y)
        tools["disk"](
            antenna, a, b, [(2.12, 1.96), (2.12, 5.00), (1.42, 5.00)], graphite
        )
        tools["disk"](
            antenna,
            a,
            b,
            [(1.06, 3.9), (1.06, 5.95), (1.97, 5.95), (1.95, 6.31), (1.65, 6.48)],
            silver,
        )
        for w, d in [(1.97, 0.47), (0.48, 1.93)]:
            block(antenna, a, b, w, d, 6.47, 6.50, graphite, 0.11)
    passives = component("P718 · SMT passives, LED and board printing")
    for cx, cy, count in [
        (457, 976, 6),
        (547, 984, 6),
        (459, 1006, 5),
        (541, 945, 5),
        (490, 924, 6),
        (445, 891, 3),
        (557, 896, 3),
    ]:
        x, z = board_coordinates(cx, cy)
        for i in range(count):
            px = x + (i % 3) * 2.15
            pz = z + (i // 3) * 1.45
            block(passives, px, pz, 1.33, 0.66, 5.94, 6.25, ceramic, 0.11)
            for end in (-0.53, 0.53):
                block(passives, px + end, pz, 0.25, 0.68, 5.94, 6.27, silver, 0.06)
    block(passives, 0, -22.05, 2.2, 2.1, 5.94, 6.45, screen)
    passives.label("P718  MAIN PCB", 1.18, lambda a, b: (a, 5.96, -46.1 - b), screen)
    for text, x, z in [
        ("U4", -17, -16),
        ("U6", -7, -9),
        ("J3", -17, 6),
        ("LED1", 1.8, -19),
        ("2024/05/24", 0, -13.1),
    ]:
        passives.label(text, 0.82, lambda a, b, x=x, z=z: (x + a, 5.97, z - b), screen)
    battery = component("P718 · lithium polymer cell, label and keyed plug")
    block(battery, 0, 22.2, 30.4, 19.1, 2.16, 7.65, film, 1.34)
    block(battery, 0, 22.2, 29.3, 18.0, 7.64, 7.9, foil, 1.02)
    block(battery, 0.25, 22.2, 26.9, 15.8, 7.90, 7.99, screen, 0.45)
    for x, z, w in [
        (-3, 19, 15),
        (-4.3, 20.4, 12.3),
        (-5.5, 22.7, 10.1),
        (-5.9, 24.0, 9.2),
    ]:
        block(battery, x, z, w, 0.23, 7.99, 8.012, graphite, 0.09)
    block(battery, -12.6, 8.5, 5.7, 2.8, 5.95, 8.2, screen)
    for i, mat in enumerate((red, graphite, yellow)):
        battery.pipe(
            [
                (-14.8, 5.7 + i * 0.45, 28 + i * 0.52),
                (-16.6, 5.3, 28.5 + i * 0.4),
                (-19.6 - i * 0.65, 4.3, 24.6),
                (-23.3 - i * 0.55, 4.4, 15.9),
                (-24.6 - i * 0.47, 5, 11.4),
                (-23.9 - i * 0.52, 6.2, 8.6),
                (-20.5, 6.9, 7.6 + i * 0.5),
                (-15.4, 7.1, 7.6 + i * 0.6),
            ],
            0.34,
            mat,
            8,
        )
    products = [p.finalize() for p in parts]
    mesh = products[0].data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.00000001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    for ob in products:
        ob["productEnclosed"] = True
    return products
