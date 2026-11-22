import math


def packed_tent(Sculpture, finish, textile):
    case = Sculpture("Snow Peak SD-641 · Land Breeze Pro.1 carry bag")
    shell = textile(
        finish("SD-641 · olive taupe woven shell", "766d59", 0, 0.73), "Tent case weave"
    )
    webbing = textile(
        finish("SD-641 · black basket webbing", "262624", 0, 0.83), "Carry strap weave"
    )
    red = textile(finish("SD-641 · garnet zip tape", "9d2036", 0, 0.74), "Zipper tape")
    thread = finish("SD-641 · bound seam thread", "655f51", 0, 0.76)
    teeth = finish("SD-641 · graphite coil", "35312c", 0.10, 0.55)
    alloy = finish("SD-641 · plated slider", "888880", 0.70, 0.37)
    print_ink = finish("SD-641 · warm white print", "e9e7db", 0, 0.77)

    def signed_power(n, p):
        return math.copysign(abs(n) ** p, n)

    def panel(x, a, lift=0):
        end = max(0, (abs(x) - 258) / 47)
        s, c = math.sin(a), math.cos(a)
        top = signed_power(s, 0.65)
        side = signed_power(c, 0.64)
        height = 109 + 4 * math.cos(x / 69) - 10 * end**2
        waist = sum(math.exp(-(((x - at) / 21) ** 2)) for at in (-144, 145))
        shoulder = 1 - 0.20 * end**2 - 0.055 * waist
        crease = math.sin(x / 28 + 3 * s) * math.cos(3 * a + x / 117)
        wrinkle = 2.8 * crease + end * 2.6 * math.sin(5 * a + x / 13)
        for at, slope, reach in [
            (-213, 49, 5.6),
            (-183, -36, 4.2),
            (176, -47, 6.2),
            (225, 38, 5.0),
        ]:
            wrinkle -= (
                reach
                * math.exp(-(((x - at - slope * s) / 10) ** 2))
                * (1 - 0.6 * abs(s))
            )
        d = (91.8 + 4.4 * top) * shoulder * side + wrinkle * c
        h = 112 + height * top - 4.9 * waist * max(0, top) + wrinkle * s
        h = max(0.3, h - 3.5 * max(0, -top) ** 3)
        return (x, h + lift * s, d + lift * c)

    def sheet(rows, mat):
        verts = [p for pair in rows for p in pair]
        case.add(
            verts, [(i, i + 1, i + 3, i + 2) for i in range(0, len(verts) - 2, 2)], mat
        )

    xs = [-305 + 610 * i / 76 for i in range(77)]
    angles = [math.tau * i / 52 for i in range(52)]
    rows = [[panel(x, a) for a in angles] for x in xs]
    for side, end in [(-1, 0), (1, -1)]:
        x = xs[end]
        rim = rows[end]
        for r in (0.9, 0.69, 0.43, 0.19, 0.009):
            inner = [
                (
                    x + side * (1 - r) * (-4 + 1.8 * math.sin(3 * a)),
                    112 + (h - 112) * r,
                    d * r,
                )
                for (_, h, d), a in zip(rim, angles)
            ]
            if side < 0:
                rows.insert(0, inner)
            else:
                rows.append(inner)
        case.pipe(
            [panel(side * 302, a, 0.5) for a in angles + [angles[0]]], 1.5, thread, 6
        )
    case.rings(rows, shell)
    for a in (0.44, math.pi - 0.44):
        case.pipe(
            [panel(x, a + 0.016 * math.sin(x / 63), 0.9) for x in xs], 0.72, thread, 6
        )

    for x in (-144, 145):
        angles = [-math.pi * 1.15 + i * math.pi * 1.30 / 52 for i in range(53)]

        def anchor(a):
            return x + 3.2 * math.sin(1.3 * a + x / 96)

        for l, r in [(-12.5, -4.2), (-4.2, 4.2), (4.2, 12.5)]:
            sheet(
                [[panel(anchor(a) + w, a, 3.1) for w in (l, r)] for a in angles],
                webbing,
            )
        for w in (-10.8, 10.8):
            case.pipe([panel(anchor(a) + w, a, 3.48) for a in angles], 0.36, teeth, 5)

    def front(x, h, offset=1.45):
        lo, hi = -1.57, 1.57
        for _ in range(13):
            mid = (lo + hi) / 2
            if panel(x, mid)[1] < h:
                lo = mid
            else:
                hi = mid
        return (x, h, panel(x, (lo + hi) / 2)[2] + offset)

    for side in (-1, 1):
        points = []
        for i in range(61):
            t = i / 60
            phase = math.pi * t
            x = -144 + 289 * (1 - math.cos(phase)) / 2
            arc = math.sin(phase)
            h = 166 + 81 * arc**0.89 - 11 * arc**3 + 4.5 * math.sin(3 * phase)
            d = side * max(front(x, h, 4.1)[2], 89 - 52 * arc**1.4) + 1.3 * math.sin(
                phase * 2
            )
            points.append((x, h, d))
        loop = []
        for i, (x, h, d) in enumerate(points):
            prev = points[max(0, i - 1)]
            nex = points[min(len(points) - 1, i + 1)]
            tx, ty = nex[0] - prev[0], nex[1] - prev[1]
            norm = math.hypot(tx, ty)
            loop.append(
                [
                    (x - sign * 12.5 * ty / norm, h + sign * 12.5 * tx / norm, d)
                    for sign in (-1, 1)
                ]
            )
        sheet(loop, webbing)
        for j in (0, 1):
            case.pipe([pair[j] for pair in loop], 0.62, teeth, 5)

    for a1, a2, mat, offset in [(1.39, 1.75, red, 1.45), (1.558, 1.584, teeth, 1.88)]:
        sheet([[panel(x, a, offset) for a in (a1, a2)] for x in xs], mat)
    for x, direction in ((143, -1), (156, 1)):
        _, h, d = panel(x, math.pi / 2, 2.8)
        case.form((x, h, d), (6.1, 2.2, 3.2), alloy)
        loop = [
            (
                x + direction * (7.5 + 8.3 * math.cos(t * math.tau / 20)),
                h + 2.3 + 0.9 * math.cos(t * math.tau / 20),
                d + 2.15 * math.sin(t * math.tau / 20),
            )
            for t in range(21)
        ]
        case.pipe(loop, 0.90, alloy, 6)

    case.label("snow peak", 32, lambda x, y: front(x, 39 + y), print_ink)
    case.label(
        "outdoor lifestyle creator since 1958",
        5.8,
        lambda x, y: front(x, 23 + y),
        print_ink,
    )
    for i in range(3):
        a = math.pi / 2 + i * math.pi / 3
        rows = []
        for index in range(13):
            u = -21 + 3.5 * index
            rows.append(
                [
                    front(
                        u * math.cos(a) - v * math.sin(a),
                        85 + u * math.sin(a) + v * math.cos(a),
                    )
                    for v in (-3.7, 3.7)
                ]
            )
        sheet(rows, print_ink)
    obj = case.finalize(27, (shell, webbing, red))
    obj.location = (-0.19, -0.194, 0.12773)
    return obj
