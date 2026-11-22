import math


def build_heel(part, hand, section, shape, knit, overlay, cage, stitch, ink, rubber):
    def grid(obj, fn, material, n=32, m=12):
        rows = [[fn(i / n, j / m) for i in range(n + 1)] for j in range(m + 1)]
        obj.add(
            [p for row in rows for p in row],
            [
                (
                    j * (n + 1) + i,
                    j * (n + 1) + i + 1,
                    (j + 1) * (n + 1) + i + 1,
                    (j + 1) * (n + 1) + i,
                )
                for j in range(m)
                for i in range(n)
            ],
            material,
        )

    def flank(d, h, s, lift=0):
        _, top, low = section(d)
        t = math.acos(max(0, min(1, (h - low) / max(0.05, top - low))) ** (1 / 0.81))
        return shape(d, t, s, lift)

    def rear(x, h, lift=0):
        s = -1 if x < 0 else 1
        rim = abs(flank(-130, h, s)[0])
        if abs(x) <= rim:
            return (x, h, -130 - 2.7 * (1 - (abs(x) / max(0.01, rim)) ** 2) - lift)
        a, b = -130, -87
        for _ in range(12):
            m = (a + b) * 0.5
            if abs(flank(m, h, s)[0]) < abs(x):
                a = m
            else:
                b = m
        return (x, h, (a + b) * 0.5 - lift)

    sh = part("sculpted heel counter and bonded TPU cradle")

    def end(d, mat):
        def point(u, v):
            t = (1 - v) * math.pi / 2
            a, b = [shape(d, t, s, 0) for s in [-1, 1]]
            x = a[0] * (1 - u) + b[0] * u
            return (
                x,
                a[1],
                d
                + (-1 if d < 0 else 1)
                * 2.7
                * (math.sin(math.pi * u) ** 2)
                * math.sin(t),
            )

        grid(sh, point, mat, 16, 16)

    end(-130, knit)
    end(139, rubber)

    def panel_point(u, v, offset):
        x = 56 * (u - 0.5)
        top = 89 + 3.1 * math.cos(2.23 * x / 28)
        return rear(x, 33 + (top - 33) * v, offset)

    grid(sh, lambda u, v: panel_point(u, v, 1.32), overlay, 45, 20)
    for edge in (0, 1):
        grid(sh, lambda u, v: panel_point(u, edge, -0.35 + 1.67 * v), overlay, 45, 2)
        grid(sh, lambda u, v: panel_point(edge, v, -0.35 + 1.67 * u), overlay, 2, 20)
    for s in [-1, 1]:
        sh.pipe(
            [
                rear(s * (0.4 + 0.25 * math.sin(i * 0.3)), 46 + i * 2.56, 1.51)
                for i in range(22)
            ],
            0.30,
            stitch,
            7,
        )
        for i in range(11):
            h = 91 + i * 1.15
            sh.pipe(
                [rear(s * 0.5, h, 0.6), rear(s * 0.5, h + 0.73, 0.61)], 0.23, ink, 6
            )
    for i in range(-18, 18):
        sh.pipe(
            [
                rear((i + t) * 1.45, 89 + 2.8 * math.cos((i + t) * 0.131), 1.54)
                for t in [0, 0.64]
            ],
            0.27,
            stitch,
            6,
        )

    def station(d):
        samples = [
            (-130, 39, 62),
            (-125, 39, 62),
            (-115, 39, 61),
            (-99, 35, 54),
            (-87, 31, 45),
            (-76, 29, 38),
            (-64, 28, 36),
            (-56, 28, 37),
            (-46, 27, 36),
            (-34, 27, 32),
            (-23, 27, 29),
        ]
        for (a, l1, h1), (b, l2, h2) in zip(samples, samples[1:]):
            if d <= b:
                t = (d - a) / (b - a)
                return l1 + (l2 - l1) * t, h1 + (h2 - h1) * t
        return samples[-1][1:]

    def quarter(d, s, v, inset):
        lo, hi = station(d)
        h = lo + (hi - lo) * v
        side = flank(d, h, s)
        left, right = max(-130, d - 0.24), min(-23, d + 0.24)
        delta = (flank(right, h, s)[0] - flank(left, h, s)[0]) / (right - left)
        length = math.hypot(1, delta)
        lift = inset + 1.0 * math.sin(v * math.pi)
        return (side[0] + s * lift / length, h, d - s * delta * lift / length)

    def cradle(u, v, inset):
        if u < 0.435:
            return quarter(-23 - 107 * u / 0.435, -1, v, inset)
        if u > 0.565:
            return quarter(-130 + 107 * (u - 0.565) / 0.435, 1, v, inset)
        q = (u - 0.435) / 0.13
        a, b = quarter(-130, -1, v, inset), quarter(-130, 1, v, inset)
        return (
            a[0] + (b[0] - a[0]) * q,
            a[1],
            a[2] + (b[2] - a[2]) * q - 3.1 * math.sin(math.pi * q),
        )

    section_profile = [
        (0.0, -0.9),
        (0.0, 1.4),
        (0.018, 2.15),
        (0.055, 2.43),
        (0.26, 2.56),
        (0.68, 2.55),
        (0.93, 2.38),
        (0.982, 2.12),
        (1.0, 1.52),
        (1.0, -0.9),
    ]
    sh.rings(
        [
            [cradle(i / 194, v, inset) for v, inset in section_profile]
            for i in range(195)
        ],
        cage,
    )

    nose = part("toe bumper")

    def rock_guard(u, v, bond=2.05):
        chord = 2 * u - 1
        x = chord * (18 - 5 * v)
        a, b = 107.0, 139.0
        for _ in range(13):
            d = (a + b) * 0.5
            if section(d)[0] > abs(x):
                a = d
            else:
                b = d
        front = min(139.0, (a + b) * 0.5)
        t = max(0, (v - 0.41) / 0.59)
        d = front - t * (12.4 - 5.9 * abs(chord) ** 1.6)
        w, _, base = section(d)
        angle = math.asin(min(1, abs(x) / w))
        roll = math.sin(0.5 * math.pi * min(1, v / 0.41))
        px, h, _ = shape(d, angle, -1 if x < 0 else 1, bond * roll)
        if v < 0.41:
            h = base - (1 - v / 0.41) * 13
        return (px, h, d + bond * (1 - t) * roll - 1.25 * (1 - roll))

    grid(nose, rock_guard, rubber, 40, 24)
    for edge in (0, 1):
        grid(nose, lambda u, v: rock_guard(edge, v, -0.65 + 2.70 * u), rubber, 2, 24)
        grid(nose, lambda u, v: rock_guard(u, edge, -0.65 + 2.70 * v), rubber, 40, 2)
    for k in range(4):
        v = 0.32 + k * 0.159
        nose.pipe(
            [rock_guard(0.05 + i * 0.9 / 30, v) for i in range(31)], 0.47, rubber, 7
        )
    mark = part("technical markings")
    mark.label("KAILAS", 4.4, lambda x, y: rear(-7.3 - x, 73 + y, 1.64), ink)
    cx = -7.3
    mark.pipe(
        [
            rear(
                cx + 2.33 * math.cos(i * math.tau / 22),
                80 + 2.33 * math.sin(i * math.tau / 22),
                1.62,
            )
            for i in range(23)
        ],
        0.45,
        ink,
        7,
    )
    for i in range(7):
        theta = i * math.tau / 7 + 0.22
        mark.pipe(
            [
                rear(cx + r * math.cos(theta + a), 80 + r * math.sin(theta + a), 1.64)
                for r, a in [(3.7, -0.14), (4.8, -0.05), (4.9, 0.13)]
            ],
            0.49,
            ink,
            7,
        )
