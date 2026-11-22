import math
import runpy
import sys
from pathlib import Path

from mathutils import Vector

assets = Path(__file__).resolve().parent
sys.path.insert(0, str(assets))
from product_solids import corners

sculpt = runpy.run_path(str(assets / "vitrine-sculpt.py"))
Sculpture = sculpt["Sculpture"]
finish = sculpt["finish"]


def materials():
    return {
        name: finish("OLED G6 / " + name, color, metal, rough)
        for name, color, metal, rough in (
            ("Power board", "DDD0A4", 0, 0.64),
            ("Logic board", "205F45", 0, 0.43),
            ("Laminate", "A28B5E", 0, 0.62),
            ("Etched green", "3B795B", 0.1, 0.53),
            ("Silver", "B9C0C1", 0.78, 0.32),
            ("Stamping", "A7ACAC", 0.77, 0.42),
            ("Contacts", "B89B53", 0.65, 0.33),
            ("Copper", "AA632F", 0.7, 0.28),
            ("Carbon", "25282A", 0.03, 0.59),
            ("Ferrite", "414044", 0.17, 0.43),
            ("Insulator", "D9D5BE", 0, 0.47),
            ("Legend", "ECE9D6", 0, 0.66),
            ("Blue", "267BB0", 0.04, 0.42),
            ("Film", "DFB63B", 0, 0.42),
            ("Brown", "856555", 0, 0.52),
            ("Black cloth", "272728", 0, 0.88),
            ("Speaker", "333638", 0.07, 0.50),
            ("Rubber", "171A1B", 0, 0.72),
            ("FFC", "ECE5D5", 0.15, 0.50),
            ("Polyimide", "CEA066", 0.29, 0.53),
            ("Cable red", "9B433F", 0, 0.57),
            ("Cable blue", "434F78", 0, 0.59),
        )
    }


def plate(part, outline, face, thick, mat):
    part.rings(
        [[(x, h, z) for x, h in outline] for z in (face, face + thick)],
        mat,
        smooth=False,
    )


def rect(part, x, h, w, height, face, thick, mat, rounding=0):
    if rounding:
        rim = corners(w, height, min(rounding, w * 0.48, height * 0.48), 3)
    else:
        rim = [
            (-w / 2, -height / 2),
            (w / 2, -height / 2),
            (w / 2, height / 2),
            (-w / 2, height / 2),
        ]
    plate(part, [(x + dx, h + dy) for dx, dy in rim], face, thick, mat)


def circle(part, x, h, profile, mat, steps=24):
    part.rings(
        [
            [
                (
                    x + r * math.cos(i * math.tau / steps),
                    h + r * math.sin(i * math.tau / steps),
                    z,
                )
                for i in range(steps)
            ]
            for z, r in profile
        ],
        mat,
        True,
    )


def ink(part, text, x, h, z, size, mat):
    part.label(text, size, lambda a, b: (x - a, h + b, z), mat)


def stripe(part, points, width, z, mat):
    rows = []
    for i, (x, h) in enumerate(points):
        a, b = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        direction = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        dx, dh = -direction.y * width * 0.5, direction.x * width * 0.5
        rows.extend([(x - dx, h - dh, z), (x + dx, h + dh, z)])
    part.add(
        rows, [(i, i + 1, i + 3, i + 2) for i in range(0, len(rows) - 2, 2)], mat, False
    )


def screw(part, x, h, z, m):
    circle(part, x, h, [(z + 1.3, 3.8), (z + 0.5, 4.1), (z, 3.4)], m["Silver"], 16)
    rect(part, x, h, 3.9, 1, z - 0.08, 0.08, m["Carbon"])
    rect(part, x, h, 1, 3.9, z - 0.10, 0.08, m["Carbon"])


def substrate(part, outline, holes, mask, m):
    plate(part, outline, -9.6, 1.6, m["Laminate"])
    plate(part, outline, -9.72, 0.12, mask)
    for x, h in holes:
        circle(part, x, h, [(-8, 4.4), (-6, 4.4)], m["Stamping"], 16)
        circle(part, x, h, [(-9.8, 5.4), (-9.73, 5.4)], m["Contacts"], 20)
        screw(part, x, h, -11, m)


def board_parts(make, m):
    power = make("Power supply / laminate and service markings")

    def pos(u, v):
        return 474 - 0.475 * v, -166 + 0.475 * u

    outline = [
        (10, 136),
        (94, 136),
        (104, 118),
        (104, 2),
        (396, 2),
        (406, 13),
        (406, 600),
        (396, 608),
        (13, 608),
        (5, 600),
        (5, 145),
    ]
    substrate(
        power,
        [pos(*p) for p in outline],
        [
            pos(*p)
            for p in [
                (112, 13),
                (390, 15),
                (18, 146),
                (195, 399),
                (18, 592),
                (390, 590),
            ]
        ],
        m["Power board"],
        m,
    )
    for u, v, text, size in [
        (75, 319, "PRIMARY", 2.6),
        (368, 310, "SECONDARY", 2.6),
        (180, 581, "48G6 / POWER", 2.4),
        (40, 151, "AC", 2),
    ]:
        ink(power, text, *pos(u, v), -9.85, size, m["Carbon"])
    for points in [
        [(20, 269), (91, 269), (110, 250), (173, 250), (199, 276), (363, 276)],
        [(26, 369), (78, 369), (101, 392), (183, 392)],
        [(90, 147), (134, 147), (145, 136), (365, 136)],
        [(190, 337), (222, 337), (250, 309), (366, 309)],
        [(34, 497), (123, 497), (140, 480), (166, 480)],
    ]:
        stripe(power, [pos(*p) for p in points], 0.56, -9.86, m["Brown"])

    for index, (u, v, w, height) in enumerate(
        [
            (129, 427, 91, 115),
            (315, 424, 90, 102),
            (345, 240, 90, 85),
            (247, 292, 134, 49),
            (219, 67, 72, 79),
            (310, 67, 72, 79),
            (154, 358, 29, 57),
            (349, 357, 33, 61),
            (133, 72, 58, 96),
        ]
    ):
        x, h = pos(u, v)
        border = corners(0.475 * height, 0.475 * w, 1.2, 2)
        stripe(
            power,
            [(x + dx, h + dh) for dx, dh in [*border, border[0]]],
            0.38,
            -9.82,
            m["Brown"],
        )
        ink(
            power,
            ("T", "T", "T", "C", "L", "L", "C", "C", "U")[index] + str(index + 1),
            x - 0.475 * height / 2 - 2.3,
            h,
            -9.87,
            1.8,
            m["Carbon"],
        )
    for u, v in [
        (28, 280),
        (96, 285),
        (67, 360),
        (174, 338),
        (196, 329),
        (279, 339),
        (287, 380),
        (94, 525),
        (229, 482),
        (361, 438),
        (43, 260),
        (363, 245),
        (247, 176),
        (226, 359),
    ]:
        x, h = pos(u, v)
        for k in range(3):
            cx = x + k * 2.2
            for side in (-1, 1):
                rect(power, cx, h + side * 1.1, 1.35, 0.8, -10.17, 0.4, m["Silver"])
            rect(power, cx, h, 1, 1.6, -10.48, 0.75, m["Carbon"])

    for index, (u, v, length) in enumerate(
        [(291, 134, 112), (137, 195, 103), (111, 527, 96), (322, 503, 67)]
    ):
        x, h = pos(u, v)
        sink = make("Power supply / folded aluminium heatsink " + str(index + 1))
        rect(sink, x, h, 12, length, -11.7, 2.0, m["Silver"])
        rect(sink, x + 5.1, h, 1.8, length, -29.6, 18.1, m["Stamping"])
        rect(sink, x - 1.9, h, 15.8, length, -31.0, 1.6, m["Silver"], 0.65)
        for dh in (-length * 0.28, length * 0.28):
            rect(sink, x + 2.5, h + dh, 3.5, 7.2, -22, 11.2, m["Carbon"])
            for k in (-1, 0, 1):
                sink.pipe(
                    [(x + 2, h + dh + k * 2.1, -12), (x - 1, h + dh + k * 2.1, -10)],
                    0.41,
                    m["Silver"],
                    5,
                )

    for index, (u, v) in enumerate([(219, 68), (309, 68)]):
        x, h = pos(u, v)
        coil = make("Power supply / copper common-mode choke " + str(index + 1))
        rect(coil, x, h, 25, 25, -13.5, 3.8, m["Insulator"], 1.4)
        for dh in (-8.3, 8.3):
            rect(coil, x, h + dh, 22, 5.4, -26, 12.6, m["Ferrite"], 1)
        for dx in (-5.7, 5.7):
            points = []
            for i in range(73):
                a = i * math.tau / 9
                points.append(
                    (
                        x + dx + 3.8 * math.cos(a),
                        h - 6.7 + i * 13.4 / 72,
                        -19.4 + 4.5 * math.sin(a),
                    )
                )
            coil.pipe(points, 0.85, m["Copper"], 6)

    for index, (u, v, width, height) in enumerate(
        [(337, 236, 31, 26), (130, 426, 39, 34), (315, 426, 36, 30)]
    ):
        x, h = pos(u, v)
        xf = make("Power supply / insulated transformer " + str(index + 1))
        rect(xf, x, h, width + 2, height + 1.5, -13, 3.3, m["Ferrite"], 1.3)
        rect(xf, x, h, width - 3, height - 2, -27, 14, m["Brown"], 2)
        for s in (-1, 1):
            rect(
                xf, x + s * (width / 2 - 3), h, 6, height, -29, 15.9, m["Ferrite"], 0.7
            )
        rect(xf, x, h, width * 0.52, height + 1, -29.4, 15.8, m["Insulator"], 0.8)
        ink(xf, "T" + str(index + 1), x, h, -29.55, 3, m["Carbon"])

    components = make("Power supply / capacitors rectifier and passives")
    x, h = pos(256, 298)
    components.pipe([(x, h - 24, -20.7), (x, h + 24, -20.7)], 9.8, m["Carbon"], 28)
    components.pipe([(x, h + 24, -20.7), (x, h + 24.7, -20.7)], 8.9, m["Silver"], 28)
    for dx in (-4.1, 4.1):
        components.pipe(
            [(x + dx, h - 24, -18), (x + dx, h - 28, -17), (x + dx, h - 28, -9.8)],
            0.65,
            m["Silver"],
            8,
        )
    ink(components, "400 V", x, h + 1, -30.55, 2.8, m["Legend"])
    for u, v, radius in [
        (34, 587, 4.7),
        (78, 585, 5.7),
        (270, 579, 5),
        (285, 548, 3.3),
        (226, 396, 3.7),
        (82, 346, 2.5),
        (348, 539, 3),
    ]:
        x, h = pos(u, v)
        circle(
            components,
            x,
            h,
            [(-9.8, radius), (-11, radius * 1.03), (-18, radius)],
            m["Carbon"],
        )
        circle(
            components,
            x,
            h,
            [(-18, radius * 0.89), (-18.5, radius * 0.86)],
            m["Silver"],
        )
        stripe(
            components,
            [(x - radius * 0.6, h), (x + radius * 0.6, h)],
            0.35,
            -18.6,
            m["Carbon"],
        )
    for u, v in [
        (128, 73),
        (139, 57),
        (251, 11),
        (291, 17),
        (344, 9),
        (363, 23),
        (56, 234),
        (73, 240),
        (388, 386),
        (119, 358),
        (207, 443),
        (240, 420),
    ]:
        x, h = pos(u, v)
        components.form((x, h, -14.4), (3.5, 1.5, 4.9), m["Blue"])
    for u, v in [(155, 356), (347, 351)]:
        rect(components, *pos(u, v), 15.5, 5, -19.3, 9.6, m["Film"], 0.85)
    for u, v in [(127, 59), (376, 98), (278, 209), (270, 244)]:
        rect(components, *pos(u, v), 15, 12, -21, 11.3, m["Carbon"], 0.6)
    for u, v in [
        (79, 173),
        (159, 255),
        (166, 326),
        (343, 328),
        (255, 373),
        (111, 552),
        (61, 439),
        (206, 462),
        (196, 489),
        (314, 539),
        (233, 331),
        (125, 374),
        (45, 382),
        (223, 285),
    ]:
        x, h = pos(u, v)
        components.pipe([(x - 4.5, h, -13), (x + 4.5, h, -13)], 1.4, m["Brown"], 8)
        for dx in (-2.8, -1.5, 2.7):
            components.pipe(
                [(x + dx, h, -13), (x + dx + 0.48, h, -13)], 1.5, m["Carbon"], 8
            )
        for sign in (-1, 1):
            components.pipe(
                [
                    (x + sign * 4.5, h, -13),
                    (x + sign * 6, h, -13),
                    (x + sign * 6, h, -9.8),
                ],
                0.34,
                m["Silver"],
                5,
            )


def socket(part, x, h, w, height, m):
    rect(part, x, h, w, height, -15, 5.3, m["Insulator"], 0.65)
    rect(part, x, h, w * 0.89, height * 0.5, -15.55, 0.6, m["Carbon"])


def logic_board(make, m):
    pcb = make("Mainboard / signal routing and mounting lands")

    def pos(u, v):
        return -154 - 0.467 * v, -166 + 0.467 * u

    outline = [
        (23, 71),
        (401, 71),
        (412, 82),
        (412, 606),
        (404, 614),
        (25, 614),
        (20, 606),
        (20, 80),
    ]
    substrate(
        pcb,
        [pos(*pt) for pt in outline],
        [
            pos(*pt)
            for pt in [
                (36, 80),
                (400, 90),
                (399, 218),
                (400, 607),
                (35, 611),
                (35, 241),
            ]
        ],
        m["Logic board"],
        m,
    )
    smd = make("Mainboard / logic ICs and soldered passives")
    for u, v, sz in [
        (100, 127, 10),
        (128, 108, 9),
        (140, 131, 8),
        (106, 155, 8),
        (140, 155, 9),
        (51, 297, 4.5),
        (86, 320, 4),
        (107, 301, 3.6),
        (132, 319, 6),
        (241, 149, 5.5),
        (316, 164, 7),
        (332, 124, 6),
        (335, 189, 3.5),
        (95, 210, 8),
    ]:
        x, h = pos(u, v)
        rect(smd, x, h, sz, sz, -12.3, 2.6, m["Carbon"], 0.28)
        for s in (-1, 1):
            for i in range(5):
                dh = (i - 2) * sz * 0.15
                rect(
                    smd,
                    x + s * (sz * 0.5 + 0.32),
                    h + dh,
                    0.7,
                    0.35,
                    -10.5,
                    0.75,
                    m["Silver"],
                )
        for j in range(3):
            dy = (j - 1) * 1.2
            stripe(
                pcb,
                [
                    (x + sz * 0.5, h + dy),
                    (x + sz * 0.5 + 2, h + dy),
                    (x + sz * 0.5 + 4, h + dy + 2),
                    (x + sz * 0.5 + 5.4, h + dy + 2),
                ],
                0.3,
                -9.79,
                m["Etched green"],
            )
    for u, v, orientation, count in [
        (208, 148, 1, 9),
        (305, 186, 1, 10),
        (55, 140, 0, 9),
        (73, 285, 0, 8),
        (140, 178, 0, 6),
        (46, 360, 1, 10),
        (157, 590, 1, 9),
        (240, 594, 1, 11),
        (375, 128, 0, 6),
    ]:
        x, h = pos(u, v)
        for i in range(count):
            dx = x + (i * 2 if orientation else 0)
            dh = h + (0 if orientation else i * 2)
            for end in (-1, 1):
                rect(smd, dx, dh + end * 0.7, 0.91, 0.35, -10.5, 0.75, m["Silver"])
            rect(
                smd,
                dx,
                dh,
                0.92,
                1.09,
                -10.65,
                0.85,
                m["Brown"] if i % 3 else m["Carbon"],
            )

    for u, v, count, run, bend in [
        (169, 111, 9, 13, 4),
        (241, 127, 11, 18, 5),
        (309, 122, 8, 16, 6),
        (354, 170, 10, 12, 5),
        (69, 268, 7, 8, 3),
        (131, 360, 10, 21, 5),
        (129, 429, 11, 20, 6),
        (129, 487, 7, 16, 4),
        (263, 581, 9, 16, 5),
    ]:
        x, h = pos(u, v)
        for j in range(count):
            ch = h + j * 0.68
            stripe(
                pcb,
                [
                    (x, ch),
                    (x - run, ch),
                    (x - run - bend, ch + bend),
                    (x - run - bend - 4, ch + bend),
                ],
                0.27,
                -9.8,
                m["Etched green"],
            )
            circle(
                pcb,
                x - run - bend - 4,
                ch + bend,
                [(-9.87, 0.36), (-9.8, 0.36)],
                m["Contacts"],
                8,
            )
    for u, v, w, height in [(95, 389, 58, 49), (91, 216, 37, 27), (144, 109, 25, 22)]:
        x, h = pos(u, v)
        for sign in (-1, 1):
            for j in range(14):
                rect(
                    pcb,
                    x + sign * height * 0.2335,
                    h + (j - 6.5) * 1.6,
                    0.9,
                    0.75,
                    -9.87,
                    0.1,
                    m["Contacts"],
                )
        for du, dv in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            ax, ah = x + du * height * 0.24, h + dv * w * 0.24
            stripe(
                pcb,
                [(ax - du * 2.9, ah), (ax, ah), (ax, ah - dv * 2.9)],
                0.4,
                -9.93,
                m["Legend"],
            )
    for u, v, text in [
        (78, 345, "J3"),
        (126, 273, "CN"),
        (219, 185, "MAIN"),
        (257, 109, "P2"),
    ]:
        ink(pcb, text, *pos(u, v), -9.95, 2.3, m["Legend"])

    shield = make("Mainboard / vented stamped RF shield")
    x0, x1 = pos(0, 219)[0], pos(0, 574)[0]
    h0, h1 = pos(164, 0)[1], pos(400, 0)[1]
    vents = [pos(0, v)[0] for v in (360, 389, 418, 446)]
    vent_h = pos(342, 0)[1]

    def sheet(ax, bx, ah, bh):
        rect(
            shield,
            (ax + bx) / 2,
            (ah + bh) / 2,
            abs(ax - bx),
            abs(ah - bh),
            -20,
            0.75,
            m["Stamping"],
        )

    lo, hi = min(x0, x1), max(x0, x1)
    sheet(lo, hi, h0, vent_h - 13)
    sheet(lo, hi, vent_h + 13, h1)
    cursor = lo
    for x in sorted(vents):
        sheet(cursor, x - 4.1, vent_h - 13, vent_h + 13)
        cursor = x + 4.1
    sheet(cursor, hi, vent_h - 13, vent_h + 13)
    for x in (lo, hi):
        rect(shield, x, (h0 + h1) / 2, 1.1, h1 - h0, -20, 10, m["Stamping"])
    for h in (h0, h1):
        rect(shield, (lo + hi) / 2, h, hi - lo, 1.1, -20, 10, m["Stamping"])
    for v in (301, 514):
        x, h = pos(282, v)
        rect(shield, x, h, 2.2, 95, -21.35, 1.4, m["Silver"], 0.9)
    x, h = pos(258, 413)
    for w, ht, z in [(36, 37, -20.65), (31, 32, -21.2), (13, 14, -21.85)]:
        rect(shield, x, h, w, ht, z, 0.7, m["Stamping"], 2.2)
    for u, v in [(183, 321), (184, 510), (350, 327)]:
        x, h = pos(u, v)
        circle(shield, x, h, [(-20, 5.8), (-21.6, 4.8)], m["Silver"])
        screw(shield, x, h, -22.5, m)
    ink(shield, "TOP", *pos(300, 263), -20.3, 4.3, m["Legend"])
    for u, v in [(185, 79), (279, 79)]:
        socket(smd, *pos(u, v), 6, 31, m)
    socket(smd, *pos(48, 177), 23, 7, m)


def ribbon(part, path, width, m, tracks=9):
    normals = []
    for i in range(len(path)):
        a, b = path[max(0, i - 1)], path[min(i + 1, len(path) - 1)]
        normal = Vector((b[1] - a[1], a[0] - b[0])).normalized()
        normals.append(normal)

    def lanes(offset, w, drop, material):
        vertices = []
        for (x, h, z), axis in zip(path, normals):
            vertices.extend(
                [
                    (
                        x + axis[0] * (offset + s * w / 2),
                        h + axis[1] * (offset + s * w / 2),
                        z + drop,
                    )
                    for s in (-1, 1)
                ]
            )
        part.add(
            vertices,
            [(i, i + 1, i + 3, i + 2) for i in range(0, len(vertices) - 2, 2)],
            material,
            False,
        )

    lanes(0, width, 0, m["FFC"])
    for i in range(tracks):
        lanes(width * ((i + 0.5) / tracks - 0.5), 0.22, -0.04, m["Polyimide"])
    for (x, h, z), normal in ((path[0], normals[0]), (path[-1], normals[-1])):
        tangent = Vector((-normal.y, normal.x))
        rim = [
            (x + normal.x * a + tangent.x * b, h + normal.y * a + tangent.y * b)
            for a, b in (
                (-width / 2, -2.1),
                (width / 2, -2.1),
                (width / 2, 2.1),
                (-width / 2, 2.1),
            )
        ]
        plate(part, rim, z - 0.21, 0.19, m["Blue"])


def timing_and_looms(make, m):
    control = make("Timing controller / board shield and sockets")
    outline = [
        (-114, -23),
        (-109, -19),
        (113, -19),
        (115, -24),
        (115, -92),
        (110, -95),
        (-114, -95),
    ]
    substrate(control, outline, [(-102, -28), (103, -87)], m["Logic board"], m)
    rect(control, 0, -57, 197, 56, -19.3, 8.5, m["Carbon"], 2.3)
    for x in (-61, 46):
        socket(control, x, -91, 53, 6, m)
        rect(control, x, -37, 43, 4, -20.1, 0.9, m["Carbon"], 0.7)
    for h in (-43, -81):
        socket(control, -110, h, 6, 29, m)
    rect(control, -48, -54, 34, 26, -20.2, 1, m["Ferrite"], 1.5)
    screw(control, 12, -56, -20.6, m)
    for x in (78, 92, 102):
        rect(control, x, -54, 2, 31, -20.2, 1, m["Ferrite"], 0.5)

    for i, (h, end_h) in enumerate([(-43, -35.7), (-81, -79.6)]):
        ffc = make("Panel harness / mainboard link " + str(i + 1))
        ribbon(
            ffc,
            [
                (-111, h, -14.9),
                (-124, h, -17),
                (-133, h + 0.6, -19.7),
                (-147, h + 1.4, -20),
                (-170, end_h, -17),
                (-191, end_h, -15.2),
            ],
            25,
            m,
            12,
        )
    for i, x in enumerate((-61, 46)):
        flex = make("Panel harness / bonded source ribbon " + str(i + 1))
        ribbon(
            flex,
            [
                (x, -91, -14.8),
                (x, -105, -14.9),
                (x - 2, -134, -13),
                (x - 2, -222, -11),
                (x - 1, -257, -10.5),
                (x, -279, -9.6),
            ],
            51,
            m,
            18,
        )

    ties = make("Panel harness / retaining cloth and power conductors")
    for h in (-143, -199):
        rect(ties, -5, h, 194, 14, -16.5, 0.42, m["Black cloth"], 1)
    for start, mat in [(0, "Carbon"), (2.2, "Cable red"), (4.4, "Cable blue")]:
        ties.pipe(
            [
                (189, -128 + start, -14.8),
                (153, -143 + start, -15.2),
                (139, -155 + start, -13.1),
                (119, -168 + start, -13),
                (-102, -168 + start, -13),
                (-176, -153 + start, -14.1),
                (-235, -145 + start, -14.8),
            ],
            0.84,
            m[mat],
            8,
        )
    socket(ties, 190, -126, 8, 13, m)
    for x in (-61, 46):
        rect(ties, x, -280, 60, 4, -12, 3.9, m["Carbon"], 0.6)
        rect(ties, x, -281, 56, 1, -12.3, 0.4, m["Contacts"])
    for sign in (-1, 1):
        for offset, color in [(0, "Cable red"), (1.5, "Carbon")]:
            ties.pipe(
                [
                    (sign * 156, -195 + offset, -20),
                    (sign * 145, -186 + offset, -18),
                    (sign * 138, -175 + offset, -17),
                    (-178, -175 + offset, -17),
                    (-196, -158 + offset, -15.8),
                    (-197, -148 + offset, -15),
                ],
                0.62,
                m[color],
                7,
            )
        rect(ties, sign * 156, -195, 6, 5, -20.4, 5, m["Insulator"], 0.45)
    socket(ties, -197, -148, 8, 5, m)


def speaker(make, sign, m):
    part = make(
        "Audio / " + ("right" if sign > 0 else "left") + " down-firing enclosure"
    )
    cx = sign * 289
    h = -241
    outline = [
        (-149, -46),
        (-142, -54),
        (125, -54),
        (135, -50),
        (149, -50),
        (149, 40),
        (143, 50),
        (36, 50),
        (32, 54),
        (-142, 54),
        (-149, 47),
    ]
    rows = []
    for z, scale in [(-7, 0.965), (-9, 0.99), (-29, 0.996), (-32, 0.98)]:
        rows.append([(cx + sign * x * scale, h + dh * scale, z) for x, dh in outline])
    part.rings(rows, m["Speaker"], False)
    for offset in (-96, 83):
        rect(part, cx + sign * offset, h, 9, 102, -34, 2.5, m["Rubber"], 1.4)
    for offset, level in [(-46, 38), (68, -36)]:
        x = cx + sign * offset
        rect(part, x, h + level, 41, 7, -32.8, 1, m["Carbon"], 1.8)
        rect(part, x, h + level + 1.7, 32, 1.6, -33.1, 1, m["Silver"], 0.5)
    x = cx - sign * 19
    circle(part, x, h - 8, [(-32, 20.4), (-33.6, 19.6), (-35.2, 17.7)], m["Rubber"], 36)
    circle(
        part,
        x,
        h - 8,
        [(-35.2, 16.1), (-36.3, 15.7), (-37.2, 12.1), (-36.8, 8.7)],
        m["Stamping"],
        36,
    )
    ink(part, "R" if sign > 0 else "L", cx - sign * 117, h + 26, -32.2, 6, m["Legend"])
    rect(part, cx + sign * 113, h - 3, 21, 11, -32.3, 0.35, m["Insulator"], 0.4)
    for j in range(14):
        rect(
            part,
            cx + sign * (106 + j),
            h - 3,
            0.3 if j % 3 else 0.7,
            6,
            -32.72,
            0.4,
            m["Carbon"],
        )
    rect(part, cx, h - 53.2, 103, 1.8, -29, 16, m["Carbon"], 0.5)
    for j in range(20):
        rect(part, cx + (j - 9.5) * 4.7, h - 53.8, 0.85, 1.4, -29, 16, m["Speaker"])


def receivers(make, m):
    wifi = make("Wireless / Wi-Fi module and snap carrier")
    x, h = -484, -264
    rect(wifi, x, h, 65, 34, -18.6, 11.2, m["Carbon"], 2.4)
    rect(wifi, x, h, 54, 25, -20.3, 1.6, m["Logic board"], 1.2)
    rect(wifi, x + 3, h, 25, 15, -22, 1.7, m["Stamping"], 0.8)
    rect(wifi, x + 3, h, 20, 10, -22.35, 0.35, m["Legend"])
    ink(wifi, "WLAN", x + 3, h, -22.45, 2.4, m["Carbon"])
    rect(wifi, x + 17, h + 10, 9, 4, -22.6, 2.4, m["Insulator"], 0.5)
    ribbon(
        wifi,
        [
            (x + 17, h + 10, -22.7),
            (-467, -239, -20),
            (-459, -215, -16),
            (-455, -184, -14),
            (-453, -163, -14),
            (-444, -155, -14),
            (-435, -145, -15),
        ],
        7,
        m,
        4,
    )
    socket(wifi, -435, -145, 8, 7, m)
    for dx in (-27, 27):
        screw(wifi, x + dx, h - 9, -20.4, m)
    sensor = make("Front controls / infrared receiver and joystick carrier")
    rect(sensor, 0, -294, 70, 17, -15.3, 7.4, m["Carbon"], 2)
    rect(sensor, 0, -295, 40, 9.5, -16.9, 1.6, m["Logic board"])
    for dx in (-27, 27):
        circle(sensor, dx, -294, [(-15.5, 4.8), (-17.3, 4)], m["Rubber"], 18)
    rect(sensor, -7, -296, 7, 5, -19.8, 3, m["Carbon"], 0.7)
    circle(sensor, 4, -295, [(-16.9, 3.2), (-19.2, 2.4)], m["Carbon"], 16)
    ribbon(
        sensor,
        [
            (0, -288, -15),
            (0, -276, -15),
            (0, -240, -14),
            (0, -196, -13),
            (-2, -187, -13.1),
            (-11, -180, -13.1),
            (-144, -180, -13),
            (-179, -177, -13),
            (-200, -169, -14),
            (-208, -157, -14.5),
            (-208, -148, -15),
        ],
        7,
        m,
        4,
    )
    socket(sensor, -208, -148, 9, 5, m)


def build():
    parts = []

    def make(name):
        part = Sculpture("OLED48G6 / " + name)
        parts.append(part)
        return part

    palette = materials()
    board_parts(make, palette)
    logic_board(make, palette)
    timing_and_looms(make, palette)
    for sign in (-1, 1):
        speaker(make, sign, palette)
    receivers(make, palette)
    return [part.finalize() for part in parts]
