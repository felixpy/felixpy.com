import math


def model_gloves(sculpture, finish, place, grain):
    hide = finish("Fireside · brushed chestnut split cowhide", "795042", rough=0.93)
    grain(hide, "Suede nap", (113, 72, 58), "suede")
    lining = finish("Fireside · charcoal removable liner", "353333", rough=0.98)
    welt = finish("Fireside · suede seam allowance", "593a30", rough=0.93)
    cord = finish("Fireside · aramid topstitch", "9b7766", rough=0.89)
    patch = finish("Fireside · woven black maker label", "242323", rough=0.91)
    print_color = finish("Fireside · ivory woven lettering", "dfd9cc", rough=0.87)
    sections = [
        (0, 68, 26),
        (-5, 68.6, 26.2),
        (-22, 66.4, 26),
        (-55, 64, 24.6),
        (-93, 58.2, 21.5),
        (-121, 52.1, 18.9),
        (-140, 51.8, 18.8),
        (-144, 52.4, 19.2),
        (-159, 54.9, 20.2),
        (-183, 57.8, 20.4),
        (-207, 60, 19.4),
        (-225, 59.4, 17),
        (-244, 56, 13.1),
        (-255, 53, 9.5),
        (-260, 47, 7.1),
    ]

    def skin(h, width, depth, a, inset=0):
        s, c = math.sin(a), math.cos(a)
        dent = math.sin(a * 5 + h / 57) * 0.8 + math.sin(a * 3 - h / 66) * 1.4
        y = h + 2.2 * s - 1.6 * math.cos(a * 2.0 + h / 42)
        side = math.copysign(abs(s) ** 0.86, s)
        face = math.copysign(abs(c) ** 0.49, c)
        wrinkle = 2.8 * math.sin(h / 6.1 + s * 3.1) * math.exp(-(((h + 151) / 22) ** 2))
        wrinkle += (
            2.6
            * math.cos(s * 12 + h / 32)
            * min(1, abs(h / 15))
            * math.exp(-(((h + 65) / 83) ** 2))
        )
        wrinkle += 1.8 * math.sin(s * 10 - h / 15) * math.exp(-(((h + 207) / 32) ** 2))
        return (
            side * (width + dent - inset),
            y,
            face * (depth + dent + wrinkle - inset),
        )

    for side in [-1, 1]:
        hand = sculpture(
            "Fire Side Glove UG-023BR · "
            + ("left back" if side == -1 else "right palm")
        )
        angles = [math.tau * i / 56 for i in range(56)]
        palm = [[skin(h, w, d, a) for a in angles] for h, w, d in sections]
        hand.rings(palm, hide, close=False)
        hand.rings(
            [
                [skin(h, w, d, a, k) for a in angles]
                for h, w, d, k in [
                    (0, 68, 26, 0),
                    (0.5, 68, 26, 0.6),
                    (-0.25, 68, 26, 2.3),
                    (-2, 68, 26, 3.5),
                    (-8, 68, 26, 3.8),
                ]
            ],
            welt,
            close=False,
        )
        inner = [[skin(h, w, d, a, 4) for a in angles] for h, w, d in sections[:5]]
        hand.rings(inner, lining, close=False)
        hand.add(inner[-1], [tuple(range(len(angles)))], lining)

        def cross_seam(h, w, d, r, material):
            path = [skin(h, w, d, a, -0.35) for a in angles]
            hand.pipe(path + path[:1], r, material, 6)

        cross_seam(-4, 68.2, 26, 0.63, cord)
        cross_seam(-139, 52, 19.1, 1.2, welt)
        cross_seam(-142.5, 52.1, 18.95, 0.5, cord)
        for a in [math.pi / 2, 3 * math.pi / 2]:
            hand.pipe([skin(h, w, d, a) for h, w, d in sections[:-2]], 1.05, welt)
        digits = [
            (-42, -247, 57, 13.2, -9),
            (-15, -250, 80, 14, -5),
            (13, -252, 86, 14, 0),
            (40, -247, 74, 13.5, 6),
        ]
        for n, (x, h, length, w, spread) in enumerate(digits):
            stations = []
            for u, fac in [
                (-0.18, 0.55),
                (-0.09, 0.89),
                (0, 0.99),
                (0.15, 1),
                (0.31, 0.98),
                (0.53, 0.96),
                (0.68, 0.91),
                (0.84, 0.84),
                (0.93, 0.72),
                (0.98, 0.46),
                (1, 0.17),
            ]:
                stations.append(
                    (
                        x + u * spread,
                        h - u * length,
                        1.4 + 2 * math.sin(math.pi * u) - 11 * u * u,
                        w * fac,
                        (10.3 + 1.5 * math.sin(u * math.pi)) * fac,
                    )
                )
            hand.loft(stations, hide, 24, 0.78)
            for edge in [-1, 1]:
                hand.pipe(
                    [
                        (cx + edge * width * 0.96, hh, dd + deep * 0.24)
                        for cx, hh, dd, width, deep in stations
                    ],
                    0.93,
                    welt,
                    6,
                )
        thumb = [
            (39, -164, 4, 13, 9),
            (49, -182, 7, 18, 14),
            (57, -201, 10, 19, 15),
            (65, -220, 12, 15, 14),
            (70, -235, 11, 13, 12),
            (74, -249, 9, 11.5, 10),
            (75, -257, 7, 8.4, 8),
            (74, -261, 6, 3, 3),
        ]
        hand.loft(thumb, hide, 28)
        hand.pipe(
            [
                (39, -165, 15),
                (26, -178, 20),
                (22, -193, 22),
                (32, -209, 23),
                (48, -220, 22),
                (64, -232, 22),
                (69, -251, 15),
            ],
            1.1,
            welt,
        )

        def logo_face(x, h):
            target = h
            for _ in range(4):
                for (hi, w, d), (lo, nw, nd) in zip(sections, sections[1:]):
                    if lo <= target <= hi:
                        f = (hi - target) / (hi - lo)
                        w, d = w + (nw - w) * f, d + (nd - d) * f
                        break
                a = math.asin(math.copysign(abs(x / w) ** (1 / 0.86), x))
                _, height, depth = skin(target, w, d, a)
                target += h - height
            return depth + 1.1

        if side == -1:
            label_verts = [
                (x, h, logo_face(x, h))
                for h in [-43, -38, -33, -28, -23, -18, -13]
                for x in range(-28, 25, 4)
            ]
            hand.add(
                label_verts,
                [
                    (i, i + 1, i + 15, i + 14)
                    for row in range(6)
                    for col in range(13)
                    for i in [row * 14 + col]
                ],
                patch,
            )
            for h in [-15.5, -40.5]:
                for x in range(-25, 23, 4):
                    hand.pipe(
                        [
                            (x, h, logo_face(x, h) + 0.28),
                            (x + 2.2, h, logo_face(x + 2, h) + 0.28),
                        ],
                        0.31,
                        cord,
                        4,
                    )
            for angle in [0, math.pi / 3, math.pi * 2 / 3]:
                dx, dy = 4.8 * math.sin(angle), 4.8 * math.cos(angle)
                hand.pipe(
                    [
                        (-2 - dx, -32 - dy, logo_face(-2 - dx, -32 - dy) + 0.45),
                        (-2 + dx, -32 + dy, logo_face(-2 + dx, -32 + dy) + 0.45),
                    ],
                    0.72,
                    print_color,
                    5,
                )
            hand.label(
                "snow peak",
                5.9,
                lambda x, y: (-x - 2, -22 - y, logo_face(-x - 2, -22 - y) + 0.55),
                print_color,
            )
        loop = [
            (-52, -22, -8),
            (-65, -11, -4),
            (-74, 3, 0),
            (-73, 12, 3),
            (-66, 15, 4),
            (-59, 12, 4),
            (-57, 5, 1),
            (-54, -12, -5),
        ]
        hand.pipe(loop, 3.4, welt, 8, 0.45)
        obj = place(
            hand,
            (-406.4 + (2.7 if side == 1 else -3), 1674, 88 + (3 if side == -1 else -3)),
            yaw=-0.36 if side == -1 else 3.29,
            roll=0.35 if side == -1 else -0.28,
            eye=(-69, 13, 3),
            uv=26,
        )
        obj["model"] = "Snow Peak Fire Side Gloves UG-023BR"
