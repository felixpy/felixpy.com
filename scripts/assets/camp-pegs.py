import math
import runpy
from pathlib import Path

import bpy


def eye(shape, center, hole, depth, outer, metal):
    x, h = center
    verts = []
    count = len(outer)
    angles = [math.atan2(oh - h, ox - x) for ox, oh in outer]
    for ring in [
        [(ox, oh, depth) for ox, oh in outer],
        [(x + hole * math.cos(a), h + hole * math.sin(a), depth) for a in angles],
        [(x + hole * math.cos(a), h + hole * math.sin(a), -depth) for a in angles],
        [(ox, oh, -depth) for ox, oh in outer],
    ]:
        verts.extend(ring)
    faces = []
    for j in range(4):
        for i in range(count):
            a = j * count + i
            b = j * count + (i + 1) % count
            k = ((j + 1) % 4) * count
            faces.append((a, b, k + (i + 1) % count, k + i))
    shape.add(verts, faces, metal, False)


def model_pegs(sculpture, finish, place, textile, grain, hammer_only=False):
    steel = finish(
        "Snow Peak · black electrodeposited forged steel",
        "313331",
        metal=0.7,
        rough=0.42,
    )
    copper = finish(
        "PRO.C · replaceable solid copper head", "bb7a53", metal=0.85, rough=0.33
    )
    hardware = finish("PRO.C · steel pins and eyelet", "9e9d96", metal=0.9, rough=0.29)
    wood = finish("PRO.C · oiled oak", "ba935f", rough=0.71)
    grain(wood, "Oiled oak", (194, 153, 103), "oak")
    branding = finish("PRO.C · burnt maker stamp", "4b330e", rough=0.8)
    red = textile(
        finish("PRO.C · red webbing", "b73527", rough=0.9), "Red wrist webbing"
    )
    canvas = textile(
        finish("Stakes · waxed field canvas", "7e7863", rough=0.95),
        "Canvas plain weave",
    )
    thread = finish("Stakes · ecru topstitch", "b3a88b", rough=0.92)
    black = finish("Field rack · powder coated steel", "393a37", metal=0.53, rough=0.54)
    hammer = sculpture("PRO.C · oiled oak shaft and maker stamp")
    grips = [
        (-273, 13.4, 10),
        (-272, 15.2, 11.2),
        (-268, 15.4, 11.9),
        (-226, 15.2, 11.9),
        (-180, 15.5, 12.2),
        (-141, 15.2, 12.1),
        (-107, 13.5, 11.2),
        (-80, 12.9, 10.7),
        (-49, 13, 10.5),
        (-30, 13.5, 10.6),
        (-16, 14, 11),
        (12, 12.6, 9.8),
    ]

    def handle(x, h, d, a):
        s, c = math.sin(a), math.cos(a)
        return (
            x * math.copysign(abs(s) ** 0.74, s),
            h,
            d * math.copysign(abs(c) ** 0.74, c),
        )

    hammer.rings(
        [[handle(w, h, d, i * math.tau / 48) for i in range(48)] for h, w, d in grips],
        wood,
    )
    for side in [-1, 1]:
        for angle in [0, math.pi / 3, math.pi * 2 / 3]:
            dx, dy = 4.1 * math.sin(angle), 4.1 * math.cos(angle)
            hammer.pipe(
                [(-dx, -245 - dy, 11.98 * side), (dx, -245 + dy, 11.98 * side)],
                0.74,
                branding,
                6,
            )

    perimeter = [
        (71, -8),
        (72, -7),
        (70, -3),
        (61, 5),
        (53, 13),
        (45, 20),
        (42, 22),
        (39, 23),
        (35, 22.4),
        (31, 20),
        (27, 17),
        (21, 14),
        (18, 9),
        (18, -7),
        (21, -12),
        (25, -13),
        (30, -9),
        (34, -4),
        (39, -2),
        (44, -2),
        (54, -4),
        (63, -9),
        (69, -9),
    ]
    oak = place(hammer, (0, 0, 0), uv=19)
    fork = sculpture("Forged extraction beak")
    fork.rings([[(x, h, d) for x, h in perimeter] for d in [-5.7, 5.7]], steel, False)
    joint = runpy.run_path(str(Path(__file__).with_name("peg-hammer-head.py")))["copper_joint"]
    head = joint(sculpture, place, steel, copper, hardware, fork, oak)
    hammer = sculpture("PRO.C · wrist loop and split ring")
    eyelet = [
        (13, -47, 0),
        (16, -48, 1),
        (18, -47, 1),
        (19, -45, 1),
        (18, -42, 0),
        (15, -40, 0),
        (13, -41, 0),
    ]
    hammer.pipe(eyelet, 1.3, hardware, 10)
    hammer.pipe(
        [
            (
                26 + 9 * math.cos(a * math.tau / 32),
                -52 + 9 * math.sin(a * math.tau / 32),
                1 + 1.4 * math.sin(a * math.tau / 32),
            )
            for a in range(33)
        ],
        1.12,
        hardware,
        9,
    )
    spans = [
        (24, -58, 3, 4.5),
        (24, -67, 4, 6),
        (25, -82, 5, 6.3),
        (26, -100, 6, 6.3),
        (30, -145, 9, 6.2),
        (34, -193, 11, 6.2),
        (40, -241, 15, 6.2),
        (49, -280, 16, 6.2),
        (54, -295, 16, 5.8),
        (56, -300, 15, 4),
        (55, -302, 12, 3.5),
        (43, -302, 10, 3.5),
        (36, -297, 9, 4.3),
        (32, -281, 6, 5.8),
        (28, -239, 4, 6),
        (29, -179, 2, 6),
        (29, -126, 1, 6),
        (24, -69, -0.8, 4.8),
    ]
    hammer.rings(
        [
            [
                (x - w, h, d - 0.5),
                (x + w, h, d - 0.5),
                (x + w, h, d + 0.5),
                (x - w, h, d + 0.5),
            ]
            for x, h, d, w in spans
        ],
        red,
        False,
    )
    hammer.form((24, -71, 5), (2.6, 2.6, 1.4), black)
    hammer.label(
        "snow peak",
        7,
        lambda x, y: (28 - y, -122 + x, 7.5 + (122 - x - 100) * 0.07),
        thread,
    )
    strap = place(hammer, (0, 0, 0), uv=19)
    parts = [oak, *head, strap]
    if hammer_only:
        return parts
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = oak
    bpy.ops.object.join()
    for layer in list(oak.data.uv_layers):
        if layer.name != "Surface scale":
            oak.data.uv_layers.remove(layer)
    oak.name = oak.data.name = "Snow Peak Peg Hammer PRO.C N-001"
    oak.location = (0.298, -0.104, 1.982)
    oak.rotation_mode = "XYZ"
    oak.rotation_euler.z = 0.29
    rack = sculpture("Equipment wall · hammer head saddle")
    for x in [279.4, 304.8]:
        rack.pipe(
            [
                (x, 1986.4, 43),
                (x, 1980.4, 47),
                (x, 1978.4, 57),
                (x, 1964, 63),
                (x, 1962, 111),
                (x, 1964, 117),
                (x, 1968, 119),
            ],
            2.5,
            black,
            12,
        )
        rack.pipe([(x, 1962, 89), (x, 1962, 110), (x, 1963, 113)], 3.2, black, 12)
    place(rack, (0, 0, 0))
    holder = sculpture("Field rack · three stitched stake channels")
    row_x = [410, 445, 480]
    for j, cx in enumerate(row_x):
        peg = sculpture("Snow Peak Solid Stake 20 R-102 · " + str(j + 1))
        peg.loft(
            [
                (0, -200, 0, 0.72, 0.75),
                (0, -196, 0, 1.5, 1.5),
                (0, -183, 0, 3, 3),
                (0, -36, 0, 3.1, 3.05),
                (0, -26, 0, 3.65, 3.5),
                (0, -7, 0, 4.15, 3.8),
                (0, -4, 0, 5, 4.1),
            ],
            steel,
            28,
        )
        peg.turn(
            [(-6, 4.1), (-5.3, 5.8), (-4.6, 6.0), (-0.8, 6.0), (0, 5.3)], steel, 40
        )
        hole = (6.0, -11.4)
        profile = [
            (12.3, -13),
            (12.2, -7.4),
            (10.5, -5.2),
            (6.8, -4.2),
            (3, -4.8),
            (0, -5.7),
            (-2, -8),
            (-2, -15),
            (0, -18),
            (3.3, -18),
            (5.3, -17.3),
            (7.5, -17.3),
            (9, -18),
            (10, -22),
            (12.3, -22),
        ]
        eye(peg, hole, 2.85, 2.5, profile, steel)
        peg.loft(
            [
                (11.1, -35, 0, 0.8, 1.4),
                (11, -34, 0, 1.25, 2.3),
                (11, -25, 0, 1.4, 2.6),
                (10.9, -17.9, 0, 1.55, 2.7),
            ],
            steel,
            16,
        )
        place(peg, (cx, 1990 - 2 * j, 84), yaw=[-0.24, 0.22, -0.1][j], uv=45)
    back = [
        (391, 1919, 78),
        (498, 1919, 78),
        (498, 1786, 78),
        (496, 1781, 78),
        (392, 1781, 78),
        (390, 1786, 78),
    ]
    holder.plate(back, canvas, 3.3, 0.2)
    for cx in row_x:
        for h1, h2 in [(1804, 1850), (1879, 1906)]:
            coords = [
                (cx - 14.4, 81),
                (cx - 7, 81.8),
                (cx - 3.8, 85.7),
                (cx, 88.3),
                (cx + 3.8, 85.7),
                (cx + 7, 81.8),
                (cx + 14.4, 81),
            ]
            nodes = [(x, h, d) for h in [h1, h1 + 1.1, h2 - 1.1, h2] for x, d in coords]
            holder.add(
                nodes,
                [
                    (row * 7 + k, row * 7 + k + 1, row * 7 + k + 8, row * 7 + k + 7)
                    for row in range(3)
                    for k in range(6)
                ],
                canvas,
            )
            for e in [-1, 1]:
                for y in range(h1 + 1, h2 - 1, 3):
                    holder.pipe(
                        [(cx + e * 12.8, y, 81.6), (cx + e * 12.8, y + 1.7, 81.6)],
                        0.34,
                        thread,
                        4,
                    )
    for cx in [406.4, 482.6]:
        holder.pipe(
            [
                (cx, 1956, 44),
                (cx, 1953, 54),
                (cx, 1936, 61),
                (cx, 1934, 77),
                (cx, 1941, 81),
            ],
            2.15,
            black,
            10,
        )
        holder.pipe(
            [
                (cx - 4, 1916, 78),
                (cx - 4, 1926, 75),
                (cx - 3, 1934, 73),
                (cx, 1937, 75),
                (cx + 3, 1934, 78),
                (cx + 4, 1926, 79),
                (cx + 4, 1916, 78),
            ],
            2.0,
            canvas,
            8,
            0.65,
        )
    place(holder, (0, 0, 0), uv=34)
