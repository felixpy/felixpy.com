import math
import runpy
from pathlib import Path


def build_harness(part, make, textile, fit, surface, nylon, dark, web, trim, hardware):
    airscape = runpy.run_path(str(Path(__file__).with_name("field-airscape.py")))
    spacer = airscape["spacer_mesh"](
        make("AirScape · open graphite warp knit", "484b50", 0, 0.94)
    )
    foam = textile(
        make("AirScape · black pressure relief foam", "282b2e", 0, 0.95),
        "Die cut face",
        True,
    )
    binding = make("BioStretch · folded charcoal binding", "26282b", 0, 0.90)
    markings = make("AirScape · size adjustment graduations", "929196", 0, 0.88)

    def rear(x, h, lift=0):
        w = fit(h)[0]
        a = math.pi - math.asin(math.copysign(min(0.97, abs(x / w)) ** (1 / 0.90), x))
        x, h, d = surface(h, a)
        return (x, h, d - lift)

    def sheet(obj, rows, mat):
        stride = len(rows[0])
        obj.add(
            [p for row in rows for p in row],
            [
                (
                    j * stride + i,
                    (j + 1) * stride + i,
                    (j + 1) * stride + i + 1,
                    j * stride + i + 1,
                )
                for j in range(len(rows) - 1)
                for i in range(stride - 1)
            ],
            mat,
        )

    def smooth(knots, n=5):
        out = []
        for i, (b, c) in enumerate(zip(knots, knots[1:])):
            a, d = knots[max(0, i - 1)], knots[min(i + 2, len(knots) - 1)]
            for j in range(n):
                t = j / n
                out.append(
                    tuple(
                        0.5
                        * (
                            2 * B
                            + (-A + C) * t
                            + (2 * A - 5 * B + 4 * C - D) * t * t
                            + (-A + 3 * B - 3 * C + D) * t**3
                        )
                        for A, B, C, D in zip(a, b, c, d)
                    )
                )
        return out + [knots[-1]]

    def ribbon(obj, path, material, thick, edge=False):
        rings = []
        outer = []
        for i, (x, h, d, w) in enumerate(path):
            a, c = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
            dh, dd = c[1] - a[1], c[2] - a[2]
            length = math.hypot(dh, dd)
            nh, nd = -dd / length, dh / length
            outer.append((x, h + nh * thick * 0.45, d + nd * thick * 0.45, w))
            rings.append(
                [
                    (x + w * q, h + nh * thick * k, d + nd * thick * k)
                    for q, k in [
                        (-0.99, 0.41),
                        (-1, 0),
                        (-0.93, -0.64),
                        (-0.66, -0.96),
                        (0, -1),
                        (0.66, -0.96),
                        (0.93, -0.64),
                        (1, 0),
                        (0.99, 0.41),
                        (0.72, 0.90),
                        (0, 1),
                        (-0.72, 0.90),
                    ]
                ]
            )
        obj.rings(rings, material)
        if edge:
            for sign in [-1, 1]:
                obj.pipe(
                    [(x + sign * 0.97 * w, h, d) for x, h, d, w in outer],
                    1.12,
                    binding,
                    7,
                )

    def buckle(obj, x, h, d, w, hh):
        perimeter = [
            (-w + 2, -hh),
            (w - 2, -hh),
            (w, -hh + 2),
            (w, hh - 2),
            (w - 2, hh),
            (-w + 2, hh),
            (-w, hh - 2),
            (-w, -hh + 2),
            (-w + 2, -hh),
        ]
        obj.pipe([(x + a, h + b, d) for a, b in perimeter], 1.63, hardware, 8)
        obj.pipe([(x - w, h, d), (x + w, h, d)], 1.32, hardware, 8)

    frame = make("AirScape · moulded polypropylene", "2a2d30", 0, 0.80)
    airscape["backpanel"](
        part, sheet, rear, web, nylon, spacer, foam, frame, binding, markings
    )
    hardware_group = part(
        "Talon 26 · sternum and hip hardware, adjustment and lash web"
    )
    for s, side in [(-1, "left"), (1, "right")]:
        shoulder = part("Talon 26 · BioStretch " + side + " shoulder harness")
        path = smooth(
            [
                (s * x, h, d, w)
                for x, h, d, w in [
                    (38, 419, -110, 15),
                    (43, 465, -129, 22),
                    (49, 491, -161, 22),
                    (60, 481, -182, 23),
                    (70, 451, -195, 24),
                    (78, 409, -199, 24),
                    (82, 364, -198, 22),
                    (86, 327, -191, 19),
                    (94, 286, -179, 15),
                    (98, 262, -168, 11),
                    (99, 250, -162, 7),
                ]
            ]
        )
        ribbon(shoulder, path, dark, 5.15, True)
        load_path = smooth(
            [
                (s * x, h, d, w)
                for x, h, d, w in [
                    (53, 479, -92, 6.7),
                    (51, 493, -112, 6.7),
                    (47, 498, -138, 6.7),
                    (49, 496, -159, 6.7),
                    (55, 492, -172, 6.7),
                ]
            ]
        )
        ribbon(shoulder, load_path, web, 1.1)
        buckle(shoulder, s * 50, 497, -140, 7.6, 3.1)
        shoulder.pipe(
            [(s * 50 - 5, 495.7, -141), (s * 50 + 5, 495.7, -141)], 0.57, trim, 6
        )
        overlay = []
        for i, (x, h, d, w) in enumerate(path):
            if h < 430 or d > -157:
                continue
            a, c = path[i - 1], path[i + 1]
            dh, dd = c[1] - a[1], c[2] - a[2]
            length = math.hypot(dh, dd)
            overlay.append(
                [
                    (x + w * q, h - dd / length * lift, d + dh / length * lift)
                    for q, lift in [
                        (-0.86, 4.0),
                        (-0.64, 5.2),
                        (0, 5.65),
                        (0.64, 5.2),
                        (0.86, 4.0),
                    ]
                ]
            )
        sheet(shoulder, overlay, nylon)
        lower = [(i, p) for i, p in enumerate(path) if 273 < p[1] < 453 and p[2] < -173]
        mesh_face = []
        for i, (x, h, d, w) in lower:
            a, b = path[i - 1], path[i + 1]
            dh, dd = b[1] - a[1], b[2] - a[2]
            length = math.hypot(dh, dd)
            edge = min(1, (h - 269) / 34)
            row = []
            for j in range(9):
                u = (j - 4) / 4
                lift = 5.6 + 1.4 * (1 - u * u)
                bias = s * u * 6.6 * max(0, (h - 413) / 40)
                row.append(
                    (
                        x + 0.72 * w * u * edge,
                        h - dd / length * lift + bias,
                        d + dh / length * lift + bias * dd / dh,
                    )
                )
            mesh_face.append(row)
        sheet(shoulder, mesh_face, spacer)
        shoulder.pipe(mesh_face[0], 0.83, binding, 7)
        for edge in [-1, 1]:
            shoulder.pipe(
                [
                    (x + edge * w * 0.74, h, d - 5.1)
                    for x, h, d, w in path
                    if 283 < h < 449 and d < -170
                ],
                0.74,
                binding,
                7,
            )
        rail = [
            (x - s * w * 0.80, h, d - 3.9) for _, (x, h, d, w) in lower if 307 < h < 417
        ]
        shoulder.pipe(rail, 1.9, binding, 8)
        x = s * (82 - 22 * 0.80)
        buckle(hardware_group, x, 356, -202, 4.8, 8.1)
        for i in range(3, len(mesh_face) - 3, 3):
            for edge in (0, -1):
                shoulder.pipe(
                    [mesh_face[i][edge], mesh_face[i + 1][edge]], 0.35, trim, 5
                )

        def cap_mark(x, y):
            height = 466 + y
            a, b = next(
                (a, b)
                for a, b in zip(path, path[1:])
                if a[1] >= height >= b[1] and a[2] < -165
            )
            factor = (height - a[1]) / (b[1] - a[1])
            xx = a[0] + factor * (b[0] - a[0]) - x
            d = a[2] + factor * (b[2] - a[2])
            return xx, height, d - 6.6

        if s == 1:
            shoulder.label("OSPREY", 6.8, cap_mark, binding)
        ribbon(
            hardware_group,
            smooth(
                [
                    (s * 98, 257, -165, 6.2),
                    (s * 106, 220, -149, 6.5),
                    (s * 115, 174, -132, 6.5),
                    (s * 126, 117, -108, 6),
                    (s * 127, 98, -98, 6),
                ]
            ),
            web,
            1.1,
        )
        buckle(hardware_group, s * 98, 254, -170, 8, 5.4)
        wing = part("Talon 26 · " + side + " articulated hipbelt pocket")
        hip = smooth(
            [
                (s * x, h, d, w, t)
                for x, h, d, w, t in [
                    (59, 70, -70, 22, 7),
                    (89, 68, -87, 37, 10),
                    (114, 68, -103, 39, 14),
                    (133, 71, -124, 37, 14),
                    (142, 74, -157, 33, 12),
                    (140, 75, -177, 28, 10),
                    (128, 74, -193, 16, 6),
                    (119, 74, -198, 9, 4),
                ]
            ]
        )
        rows = []
        for x, h, d, w, t in hip:
            rows.append(
                [
                    (x + s * t * xx, h + w * yy, d)
                    for xx, yy in [
                        (0, -1),
                        (0.75, -0.91),
                        (1, -0.40),
                        (1, 0),
                        (0.85, 0.72),
                        (0.27, 1),
                        (-0.49, 0.96),
                        (-0.83, 0.59),
                        (-1, 0),
                        (-0.88, -0.61),
                        (-0.5, -0.93),
                    ]
                ]
            )
        wing.rings(rows, nylon)
        arc = smooth([(x + s * t * 1.02, h - 3, d) for x, h, d, w, t in hip])
        span = arc[len(arc) // 2]
        for side_sign in [-1, 1]:
            wing.pipe(
                [
                    (span[0] + s * 0.30, span[1] + v, span[2] + side_sign * k)
                    for k, v in [(0, 0), (5, -0.8), (11, 0), (19, 3.5)]
                ],
                0.58,
                binding,
                6,
            )
            for k in range(3, 17, 3):
                wing.pipe(
                    [
                        (
                            span[0] + s * 0.35,
                            span[1] + k * k * 0.008 - 1.2,
                            span[2] + side_sign * k,
                        ),
                        (
                            span[0] + s * 0.35,
                            span[1] + k * k * 0.008 - 3.2,
                            span[2] + side_sign * (k - 0.5),
                        ),
                    ],
                    0.35,
                    binding,
                    6,
                )
        wing.pipe(
            [(x + s * t * 0.43, h + 0.98 * w, d) for x, h, d, w, t in hip],
            1.5,
            binding,
            7,
        )
        wing.pipe(
            [(x - s * t * 0.63, h - 0.7 * w, d) for x, h, d, w, t in hip],
            1.3,
            binding,
            7,
        )

        def inner_pad(u, v):
            x, h, d, w, t = hip[u]
            span = 0.64 * (0.72 + 0.28 * math.sin(math.pi * (u - 2) / (len(hip) - 6)))
            crown = max(0, 1 - v * v) ** 0.64
            return (
                x - s * (t * (1 - 0.13 * abs(v)) + 1.6 + 2.1 * crown),
                h + v * w * span,
                d,
            )

        sleeve = [
            [inner_pad(i, j / 5) for j in range(-5, 6)] for i in range(2, len(hip) - 3)
        ]
        for strip, material in [(sleeve[:-5], nylon), (sleeve[-6:], spacer)]:
            sheet(wing, strip if s < 0 else [row[::-1] for row in strip], material)
        outline = (
            sleeve[0]
            + [row[-1] for row in sleeve[1:]]
            + sleeve[-1][-2::-1]
            + [row[0] for row in sleeve[-2:0:-1]]
        )
        wing.pipe(outline + [outline[0]], 0.70, binding, 7)
        for j in range(1, len(sleeve) - 2, 2):
            for edge in (1, -2):
                wing.pipe([sleeve[j][edge], sleeve[j + 1][edge]], 0.29, trim, 5)
        x, h, d, w, t = hip[-9]
        wing.pipe(
            [
                (x + s * t * 0.7, h + w * 0.92, d),
                (x + s * (t + 3), h + w * 0.75, d - 4),
                (x + s * (t + 6), h + w * 0.53, d - 7),
                (x + s * (t + 4), h + w * 0.63, d - 6),
                (x + s * t * 0.7, h + w * 0.92, d),
            ],
            1,
            hardware,
            7,
        )
        if s == 1:
            shoulder.pipe(
                smooth(
                    [
                        (89, 292, -184),
                        (95, 288, -185),
                        (102, 278, -186),
                        (101, 271, -186),
                        (95, 268, -186),
                        (90, 273, -185),
                        (90, 281, -183),
                        (92, 289, -183),
                    ],
                    3,
                ),
                1.25,
                markings,
                7,
            )
            shoulder.form((91.5, 290, -184.5), (3.9, 5.1, 2.7), hardware, -0.18)
            for dx in (-0.9, 0.9):
                shoulder.pipe(
                    smooth(
                        [
                            (92 + dx, 287, -184.2),
                            (96 + dx, 272, -185.5),
                            (98 + dx, 260, -186.5),
                            (101 + dx, 243, -185.2),
                        ],
                        3,
                    ),
                    0.69,
                    markings,
                    6,
                )
            shoulder.form((101, 242, -185.2), (1.9, 2.5, 1.45), hardware)
        for h, x, d, hh in [(356, 65, -203, 5.6), (74, 124, -200, 8.5)]:
            rows = []
            for i in range(19):
                q = i / 18
                xx = s * (x - (x - 8) * q)
                yy = h - 2.3 * math.sin(math.pi * q)
                zz = d - 3 * math.sin(math.pi * q)
                rows.append(
                    [
                        (xx, yy - hh, zz - 1),
                        (xx, yy + hh, zz - 1),
                        (xx, yy + hh, zz + 1),
                        (xx, yy - hh, zz + 1),
                    ]
                )
            hardware_group.rings(rows, web)
    for h, d, w, hh in [(356, -204, 12, 6), (74, -201, 17, 9.5)]:
        for s in (-1, 1):
            buckle(hardware_group, s * w * 0.83, h, d, w * 0.34, hh * 0.94)
        contour = [
            (-0.93, 0.44),
            (-0.9, 0.9),
            (-0.63, 1),
            (0.62, 1),
            (0.9, 0.88),
            (0.94, 0.46),
            (0.68, 0.24),
            (0.62, 0),
            (0.68, -0.24),
            (0.94, -0.46),
            (0.9, -0.88),
            (0.62, -1),
            (-0.63, -1),
            (-0.90, -0.9),
            (-0.93, -0.44),
            (-0.72, -0.28),
            (-0.68, 0),
            (-0.72, 0.28),
        ]
        rings = [
            [
                (w * 0.58 * x, h + hh * yy * scale, d + depth * (1 - 0.12 * x * x))
                for x, yy in contour
            ]
            for depth, scale in [(-3.25, 0.9), (-2.6, 1), (1.8, 1), (2.25, 0.9)]
        ]
        hardware_group.rings(rings, hardware)
        for s in (-1, 1):
            hardware_group.pipe(
                [
                    (-w * 0.56, h + s * hh * 0.66, d - 1),
                    (-w * 0.31, h + s * hh * 0.84, d - 2),
                    (w * 0.04, h + s * hh * 0.83, d - 2),
                ],
                1.0,
                binding,
                7,
            )
