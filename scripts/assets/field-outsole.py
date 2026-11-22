import math


def build_outsole(
    part, hand, ds, section, shape, foam, rubber, yellow, ink, build_tread
):
    def rocker(d):
        return 1.9 + 13 * max(0, (d - 57) / 82) ** 2 + 5.4 * max(0, (-d - 91) / 39) ** 2

    def foot(d, n, height):
        right = shape(d, math.pi / 2, 1)[0]
        left = shape(d, math.pi / 2, -1)[0]
        return ((left + right) / 2 + (right - left) * n / 2, rocker(d) + height, d)

    def rubber_height(d):
        joints = [
            (-130, 18),
            (-120, 13),
            (-105, 10),
            (-94, 13),
            (-86, 9),
            (-68, 9),
            (-55, 15),
            (-47, 16),
            (-44, 10),
            (-24, 11),
            (-13, 7),
            (-3, 7),
            (0, 11),
            (15, 11),
            (20, 7),
            (37, 8),
            (45, 12),
            (58, 11),
            (63, 7),
            (76, 7),
            (88, 13),
            (103, 11),
            (115, 14),
            (125, 17),
            (139, 23),
        ]
        k = next(i for i, p in enumerate(joints) if p[0] >= d)
        if k == 0:
            return joints[0][1]
        a, b = joints[k - 1], joints[k]
        return a[1] + (b[1] - a[1]) * (d - a[0]) / (b[0] - a[0])

    rubber_rows, foam_rows = [], []
    sections = sorted(
        set(
            ds
            + [
                -55,
                -47,
                -44,
                -13,
                -3,
                0,
                15,
                20,
                37,
                45,
                58,
                63,
                76,
                88,
                103,
                115,
                125,
                129,
            ]
        )
    )
    for d in sections:
        base = section(d)[2] - rocker(d)
        wall = min(rubber_height(d), base - 2)
        rubber_rows.append(
            [
                foot(d, n, h)
                for n, h in [
                    (-0.995, wall),
                    (-1.012, wall - 0.8),
                    (-1.014, 6.5),
                    (-0.991, 5.2),
                    (-0.91, 4.9),
                    (-0.64, 4.8),
                    (-0.28, 4.7),
                    (0, 4.7),
                    (0.28, 4.7),
                    (0.64, 4.8),
                    (0.91, 4.9),
                    (0.991, 5.2),
                    (1.014, 6.5),
                    (1.012, wall - 0.8),
                    (0.995, wall),
                    (0.6, wall),
                    (-0.6, wall),
                ]
            ]
        )
        foam_rows.append(
            [
                foot(d, n, h)
                for n, h in [
                    (-0.992, base + 1.3),
                    (-1.014, base - 0.3),
                    (-1.048, base - 3.1),
                    (-1.05, base - 5.4),
                    (-1.018, wall + 1.5),
                    (-1, wall - 0.4),
                    (0.998, wall - 0.4),
                    (1.018, wall + 1.5),
                    (1.05, base - 5.4),
                    (1.048, base - 3.1),
                    (1.014, base - 0.3),
                    (0.992, base + 1.3),
                ]
            ]
        )
    part("Vibram rubber foundation").rings(rubber_rows, rubber)
    join = sections.index(129)
    core = part("compression molded EVA midsole")
    core.rings(foam_rows[: join + 1], foam, close=False)
    core.add(foam_rows[0], [tuple(reversed(range(len(foam_rows[0]))))], foam)
    cap_sole = part("toe bumper")
    cap_sole.rings(foam_rows[join:], rubber, close=False)
    cap_sole.add(foam_rows[-1], [tuple(range(len(foam_rows[-1])))], rubber)
    for side in [-1, 1]:
        rows = []
        for i in range(27):
            d = 114 + i * 25 / 26
            base = section(d)[2] - rocker(d)
            bottom = min(rubber_height(d), base - 2)
            fraction = min(1, ((d - 114) / 15.2) ** 1.72)
            cap = bottom + (base + 1.5 - bottom) * fraction
            rows.append(
                [
                    foot(d, side * reach, bottom - 0.45 + (cap - bottom + 0.45) * u)
                    for u, reach in [
                        (0, 1.029),
                        (0.32, 1.054),
                        (0.72, 1.067),
                        (1, 1.056),
                    ]
                ]
            )
        part("toe bumper").add(
            [v for row in rows for v in row],
            [
                (i * 4 + j, i * 4 + j + 1, (i + 1) * 4 + j + 1, (i + 1) * 4 + j)
                for i in range(len(rows) - 1)
                for j in range(3)
            ],
            rubber,
        )
    build_tread(part, hand, foot, rubber, yellow, ink)
    obj = part("compression molded EVA midsole")
    for side in [-1, 1]:
        crease = []
        radii = []
        for i in range(74):
            t = i / 73
            d = -124 + 190 * t
            depth = section(d)[2] - rocker(d) - 5.2
            crease.append(foot(d, side * 1.048, depth))
            radii.append(0.12 + 0.78 * math.sin(t * math.pi) ** 0.65)
        obj.pipe(crease, radii, foam, 10, 0.58)
