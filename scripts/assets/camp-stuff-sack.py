import math


def model_sack(sculpture, finish, place, textile):
    nylon = textile(
        finish("BACOO · charcoal 20D ripstop", "48494a", rough=0.65), "20 denier"
    )
    hem = finish("BACOO · folded bound seam", "373738", rough=0.67)
    cord = finish("BACOO · black braided drawcord", "383739", rough=0.92)
    acetal = finish("BACOO · spring cord lock", "26282b", rough=0.45)
    sack = sculpture("Snow Peak BACOO 550 · 340 mm drawcord case")
    stations = [
        (-170, 9),
        (-169, 74),
        (-166, 89),
        (-160, 99),
        (-149, 102),
        (-122, 103),
        (-82, 104),
        (-46, 103),
        (-5, 102),
        (30, 103),
        (65, 102),
        (88, 103),
        (115, 101),
        (131, 98),
        (142, 91),
        (151, 77),
        (158, 61),
        (163, 47),
        (167, 33),
        (170, 18),
        (168, 9),
    ]

    def surface(x, r, a):
        tension = (
            0.9
            + 3.2 * math.exp(-(((x - 144) / 47) ** 2))
            + 1.3 * math.exp(-(((x + 148) / 30) ** 2))
        )
        k = tension * (math.cos(11 * a + x / 57) + 0.52 * math.sin(17 * a - x / 72))
        k += 2.4 * math.sin(4 * a + x / 72) * math.cos(x / 68 - 0.2)
        s, c = math.sin(a), math.cos(a)
        pinch = 5 * math.exp(-(((x - 67) / 29) ** 2)) * max(0, c) ** 2
        rr = r + (k - pinch) * min(1, r / 50)
        d = rr * c + 1.8 * math.cos(x / 92)
        y = rr * s
        flat = max(y, -96)
        return (x, flat, d + math.copysign(0.16 * (flat - y), d))

    angles = [math.tau * i / 96 for i in range(96)]
    rows = []
    for i, (x, r) in enumerate(stations[:-1]):
        nx, nr = stations[i + 1]
        steps = max(1, math.ceil(abs(nx - x) / 6))
        for j in range(steps):
            f = j / steps
            rows.append(
                [surface(x + f * (nx - x), r + f * (nr - r), a) for a in angles]
            )
    rows.append([surface(*stations[-1], a) for a in angles])
    sack.rings(rows, nylon)
    for x, r in [(-158.5, 99.3), (164, 43.5), (168, 28.5)]:
        path = [surface(x, r + 0.55, a) for a in angles]
        sack.pipe(path + path[:1], 0.78, hem, 6)
    for a in [-0.51, -0.54]:
        sack.pipe([surface(x, r + 0.45, a) for x, r in stations[3:-2]], 0.49, hem, 6)
    anchor = (169, 3, 9)
    sack.pipe(
        [
            anchor,
            (177, 11, 12),
            (191, 19, 16),
            (202, 24, 22),
            (211, 24, 30),
            (215, 17, 34),
            (214, 9, 31),
            (207, 3, 26),
            (189, 1, 18),
            (172, -1, 6),
        ],
        1.45,
        cord,
        8,
    )
    sack.form((180, 5, 11), (6.6, 6.1, 5.5), acetal)
    sack.form((181, 9, 12), (3.9, 3.7, 3.3), acetal)
    place(sack, (82, 550, 190), uv=35)

    steel = finish(
        "Field basket · dark enamelled wire", "464c49", metal=0.54, rough=0.44
    )
    basket = sculpture("Field bench · welded steel basket")
    for h in [3.1, 88]:
        perimeter = []
        for x, d, initial in [
            (254, 125, 0),
            (-254, 125, 90),
            (-254, -125, 180),
            (254, -125, 270),
        ]:
            for j in range(10):
                a = math.radians(initial + j * 10)
                perimeter.append((x + 14 * math.cos(a), h, d + 14 * math.sin(a)))
        basket.pipe(perimeter + perimeter[:1], 2.7, steel, 10)
    for x in [-244, -180, -98, -16, 66, 148, 225]:
        basket.pipe(
            [
                (x, 88, -139),
                (x, 14, -138),
                (x, 8, -136),
                (x, 5, -130),
                (x, 5, 130),
                (x, 8, 136),
                (x, 14, 138),
                (x, 88, 139),
            ],
            1.8,
            steel,
            8,
        )
    place(basket, (88, 447, 190))
