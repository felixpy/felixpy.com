import math

import bpy
from mathutils import Vector


def build_talon(Sculpture, make, textile, build_harness):
    pieces = []

    def part(name):
        item = Sculpture(name)
        pieces.append(item)
        return item

    def fabric(name, color, lattice=False):
        return textile(
            make(name, color, 0, 0.94 if lattice else 0.88),
            name,
            lattice,
            0.54 if lattice else 0.38,
        )

    shell = fabric("Talon · Phantom Grey 100D nylon", "52565a")
    hood = fabric("Talon · Phantom Grey upper facing", "606469")
    pocket = fabric("Talon · fine graphite stretch weave", "515559", True)
    base = fabric("Talon · Dark Charcoal reinforced base", "34383c")
    lining = fabric("Talon · shaded cavity liner", "262a2c")
    mesh = fabric("Talon · harness spacer knit", "33373a", True)
    web = fabric("Talon · recycled charcoal webbing", "34383b")
    piping = make("Talon · graphite lockstitch", "464a4d", 0, 0.87)
    ink = make("Osprey · black embroidered detail", "232529", 0, 0.86)
    print_ink = make("Talon · black transfer outline", "282a2c", 0, 0.94)
    hardware = make("Osprey · dark acetal adjusters", "2a2d30", 0.02, 0.51)
    stations = [
        (0, 47, 35, -6),
        (8, 92, 64, -5),
        (22, 110, 79, -3),
        (46, 119, 91, 0),
        (84, 123, 96, 3),
        (128, 124, 100, 5),
        (197, 128, 105, 6),
        (278, 136, 109, 6),
        (351, 141, 113, 5),
        (398, 142, 114, 0),
        (438, 138, 109, -3),
        (473, 128, 99, -8),
        (496, 114, 85, -12),
        (511, 91, 66, -14),
        (521, 62, 46, -16),
        (525, 33, 28, -16),
        (527, 6, 7, -16),
    ]

    def fit(h):
        idx = next((i for i, s in enumerate(stations) if s[0] >= h), len(stations) - 1)
        a, b = stations[max(0, idx - 1)], stations[idx]
        t = 0 if a == b else max(0, min(1, (h - a[0]) / (b[0] - a[0])))
        return tuple(j + (k - j) * t for j, k in zip(a[1:], b[1:]))

    def skin(h, a, extra=0):
        w, r, d = fit(h)
        lower = math.exp(-(((h - 37) / 42) ** 2))
        fold = (1.45 + 2.7 * lower) * math.cos(7 * a + 0.014 * h) + 1.2 * math.sin(
            12 * a - 0.021 * h
        )
        s, c = math.sin(a), math.cos(a)
        return (
            math.copysign(abs(s) ** 0.90, s) * (w + fold + extra),
            h,
            math.copysign(abs(c) ** 0.88, c) * (r + fold * 0.68 + extra) + d,
        )

    def grid(piece, rows, material):
        size = len(rows[0])
        faces = [
            (j * size + i, j * size + i + 1, (j + 1) * size + i + 1, (j + 1) * size + i)
            for j in range(len(rows) - 1)
            for i in range(size - 1)
        ]
        piece.add([p for row in rows for p in row], faces, material)

    def grid_fn(piece, n, m, sample, material):
        grid(
            piece,
            [[sample(i / n, j / m) for i in range(n + 1)] for j in range(m + 1)],
            material,
        )

    def front(x, h, offset=0):
        w = fit(h)[0]
        return skin(
            h, math.asin(math.copysign(min(0.99, abs(x / w)) ** (1 / 0.90), x)), offset
        )

    body = part("Talon 26 · shaped bucket and reinforced boot")
    heights = sorted(
        set([row[0] for row in stations] + [j * 527 / 50 for j in range(51)])
    )
    grid(
        body, [[skin(h, i * math.tau / 72) for i in range(73)] for h in heights], shell
    )
    for h in [0, 527]:
        rim = [skin(h, i * math.tau / 64) for i in range(64)]
        body.add(
            [(0, h, fit(h)[2])] + rim,
            [(0, i + 1, (i + 1) % 64 + 1) for i in range(64)],
            shell,
        )

    def boot_top(a):
        return (
            34
            + 28 * (math.cos(a) ** 4 if math.cos(a) > 0 else 0.18)
            + 9 * math.sin(2 * a + 0.4)
        )

    grid_fn(
        body,
        72,
        9,
        lambda u, v: skin(1 + (boot_top(u * math.tau) - 1) * v, u * math.tau, 0.85),
        base,
    )

    def interpolate(stops, t):
        for (a, b), (c, d) in zip(stops, stops[1:]):
            if t <= c:
                f = max(0, min(1, (t - a) / (c - a)))
                return b + (d - b) * f
        return stops[-1][1]

    cap = part("Talon 26 · sculpted upper yoke and bucket zipper")

    def hem(a):
        t = abs((a + math.pi) % math.tau - math.pi)
        return interpolate(
            [
                (0, 399),
                (0.35, 398),
                (0.47, 395),
                (0.55, 386),
                (0.64, 363),
                (0.77, 333),
                (0.84, 326),
                (0.98, 350),
                (1.35, 377),
                (1.75, 403),
                (2.25, 424),
                (math.pi, 465),
            ],
            t,
        )

    def cap_pt(a, v, relief=0):
        h = hem(a) + (527 - hem(a)) * v
        extra = (
            2
            + 2.4 * math.sin(math.pi * v)
            + 0.8 * math.sin(9 * a + 0.035 * h) * math.sin(v * math.pi)
            + 2.25
            * math.exp(-(((abs(math.sin(a)) - 0.64) / 0.27) ** 2))
            * math.sin(16 * a + 8 * v)
            * math.exp(-5 * v)
        )
        return skin(h, a, max(2.65, extra) + relief)

    def cap_skin(h, a, relief=0):
        v = (h - hem(a)) / (527 - hem(a))
        return cap_pt(a, v, relief)

    grid_fn(cap, 96, 20, lambda u, v: cap_pt(u * math.tau, v), hood)
    for s in [-1, 1]:
        cap.pipe([cap_pt(s * i * math.pi / 100, 0) for i in range(101)], 1.0, hood, 7)
        for start, rise, rad, mat in [
            (346, 128, 1.24, base),
            (349, 128, 0.54, piping),
            (379, 112, 0.64, piping),
        ]:
            cap.pipe(
                [
                    cap_skin(
                        start + rise * (i / 55) ** 0.69,
                        s * (0.89 + 1.97 * i / 55),
                        0.44,
                    )
                    for i in range(56)
                ],
                rad,
                mat,
                7,
            )

    def zippoint(t):
        a = t * 2.43 - 1.23
        return cap_skin(498 + 11 * math.cos(a), a, 0.58)

    cap.pipe([zippoint(i / 50) for i in range(51)], 1.3, web, 7)

    def pull(piece, xyz, width, drop):
        x, h, d = xyz
        shape = [
            (0, 0, 0),
            (-0.65, -0.16, 0.20),
            (-1, -0.5, 0.35),
            (-0.9, -0.86, 0.56),
            (-0.5, -1, 0.60),
            (0.06, -0.84, 0.49),
            (0.12, -0.44, 0.26),
            (0, 0, 0),
        ]
        piece.pipe(
            [(x + w * width, h + v * drop, d + z * width) for w, v, z in shape],
            1.22,
            web,
            8,
        )
        piece.form(
            (x - 0.58 * width, h - drop * 0.91, d + width * 0.53),
            (2.15, 3.9, 2.2),
            hardware,
            0.18,
        )

    pull(cap, zippoint(0.12), 11, 12)
    pull(cap, cap_pt(1.02, 0.15), 9, 18)
    collar = part("Talon 26 · dark recessed mouth and folded elastic binding")
    grid_fn(
        collar,
        48,
        12,
        lambda u, v: skin(
            319 + v * (hem((u - 0.5) * 1.74) - 318), (u - 0.5) * 1.74, 1.2
        ),
        lining,
    )

    frontpanel = part("Talon 26 · tapered stretch stash and printed gills")

    def top(a):
        return 354 + 6 * math.cos(a * 2) - 2 * math.sin(3 * a)

    def panel(u, v, extra=0):
        width = interpolate(
            [
                (0, 0.53),
                (0.06, 0.68),
                (0.18, 0.84),
                (0.45, 0.88),
                (0.82, 0.88),
                (1, 0.83),
            ],
            v,
        )
        a = u * width
        bottom = 42 + 19 * u * u
        h = bottom + (top(a) - bottom) * v
        swell = (
            3.4
            + 4.6 * math.sin(math.pi * v) * math.cos(a) ** 2
            + 2.1 * math.exp(-(((v - 0.14) / 0.18) ** 2)) * math.cos(a * 14 + v * 7)
        )
        return skin(h, a, swell + extra)

    grid_fn(frontpanel, 48, 38, lambda u, v: panel(2 * u - 1, v), pocket)
    frontpanel.pipe([panel(i / 30, 1, 0.45) for i in range(-30, 31)], 1.3, pocket, 8)
    for s in [-1, 1]:
        frontpanel.pipe([panel(s, j / 40, 0.45) for j in range(41)], 0.75, piping, 6)
        outline = [
            (0.76, 0.81),
            (0.74, 0.71),
            (0.505, 0.625),
            (0.56, 0.737),
            (0.76, 0.81),
        ]
        for shift in [0, 0.213, 0.422]:
            coords = []
            for (x, y), (x2, y2) in zip(outline, outline[1:]):
                coords.extend(
                    [
                        panel(
                            s * (x + (x2 - x) * k / 9),
                            y + (y2 - y) * k / 9 - shift,
                            0.73,
                        )
                        for k in range(9)
                    ]
                )
            coords.append(coords[0])
            frontpanel.pipe(coords, 0.88, print_ink, 6, 0.28)
        frontpanel.pipe(
            [
                panel(s * u, v, 0.69)
                for u, v in [(0.95, 0.98), (0.64, 0.88), (0.50, 0.80), (0.50, 0.644)]
            ],
            0.71,
            print_ink,
            6,
            0.25,
        )
    trim = part("Talon 26 · lower doubled blinker tab and embroidery")

    def patch_uv(x, h):
        v = (h - 42) / (top(0) - 42)
        return front(
            x,
            h,
            4.75
            + 4.8 * math.sin(math.pi * v)
            + 2.1
            * math.exp(-(((v - 0.14) / 0.18) ** 2))
            * math.cos(14 * math.asin(x / fit(h)[0]) + v * 7),
        )

    rows = []
    for j in range(12):
        v = j / 11
        count = 23
        row = []
        for i in range(count):
            u = i / (count - 1) * 2 - 1
            half = interpolate(
                [(0, 37), (0.10, 50), (0.33, 58), (0.80, 61), (1, 50)], v
            )
            x = u * half
            h = 43 + 7 * u * u + v * (61 + 3.4 * math.cos(u * 4 + 0.6))
            row.append(patch_uv(x, h))
        rows.append(row)
    grid(trim, rows, base)
    for h in [61, 73]:
        trim.pipe(
            [
                tuple(Vector(patch_uv(x, h + math.cos(x / 12))) + Vector((0, 0, 0.82)))
                for x in range(-9, 10, 2)
            ],
            1.4,
            ink,
            8,
            0.33,
        )
    trim.label("TALON 26", 8, lambda x, y: front(x + 19, 117 + y, 11.2), ink)
    trim.label(
        "OSPREY", 13.2, lambda x, y: front(x, 458 + y - 0.0043 * x * x, 6.3), ink
    )
    for s in [-1, 1]:
        trim.pipe(
            [
                front(s * x, h, 6.3)
                for x, h in [(1, 438), (7, 437), (16, 438), (24, 441), (28, 445)]
            ],
            0.72,
            ink,
            8,
            0.46,
        )
        for i in range(11):
            x = 2 + i * 2.28
            h = 437 + 0.009 * x * x
            trim.pipe(
                [
                    front(s * x, h, 6.35),
                    front(s * (x + 0.8), h - 2.3, 6.35),
                    front(s * (x + 1.6), h - 3.52 + 0.07 * i, 6.35),
                ],
                [0.53, 0.42, 0.21],
                ink,
                6,
            )
        trim.pipe(
            [front(s * x, h, 6.3) for x, h in [(1, 441), (1, 435), (3, 430), (5, 429)]],
            0.55,
            ink,
            6,
        )
    sides = part("Talon 26 · gussets, side sleeves and compression straps")
    for s in [-1, 1]:

        def side(u, v):
            a = 0.84 + u * 1.90
            lower = boot_top(s * a)
            upper = hem(s * a) + 1
            return skin(lower + (upper - lower) * v, s * a, 1.75)

        grid_fn(sides, 24, 32, side, base)

        def bottle(u, v):
            a = 1.12 + u * 1.46
            lo = boot_top(s * a) + 2.2
            hi = interpolate(
                [(0, 77), (0.09, 114), (0.23, 143), (0.59, 201), (1, 235)], u
            )
            return skin(
                lo + (hi - lo) * v,
                s * a,
                4.8
                + 2.1 * math.sin(math.pi * v)
                + 1.1 * math.cos(u * 9 + 0.7) * math.exp(-v * 4),
            )

        grid_fn(sides, 34, 16, bottle, shell)
        sides.pipe([bottle(i / 36, 1) for i in range(37)], 1.4, piping, 8)

        def band(u, dy=0):
            a = 1.05 + 1.50 * u
            return skin(227 - 63 * u + 4 * math.sin(math.pi * u) + dy, s * a, 7.30)

        grid_fn(sides, 22, 2, lambda u, v: band(u, 11 * (v - 0.5)), web)
        for edge in [-1, 1]:
            sides.pipe([band(i / 28, edge * 5.4) for i in range(29)], 0.54, web, 6)
        verts = [band(0.24, -6), band(0.31, -6), band(0.31, 6), band(0.24, 6)]
        sides.pipe(verts + [verts[0]], 1.5, hardware, 8)
        sides.pipe([band(0.272, -6), band(0.272, 6)], 1.15, hardware, 8)
    loops = part("Talon 26 · carry web, side tie and ice tool attachment")

    def flatloop(points, width):
        loops.rings(
            [
                [
                    (x - width * 0.5, h, d - 0.85),
                    (x + width * 0.5, h, d - 0.85),
                    (x + width * 0.5, h, d + 0.85),
                    (x - width * 0.5, h, d + 0.85),
                ]
                for x, h, d in points
            ],
            web,
        )

    flatloop(
        [
            (-20, 484, -55),
            (-18, 518, -72),
            (-5, 556, -78),
            (1, 560, -78),
            (8, 551, -75),
            (19, 518, -69),
            (23, 486, -54),
        ],
        9,
    )
    flatloop(
        [
            (91, 76, 72),
            (109, 56, 79),
            (124, 24, 83),
            (132, 2, 87),
            (130, -2, 87),
            (124, 3, 86),
            (112, 36, 80),
            (93, 73, 71),
        ],
        4.6,
    )
    tie = skin(281, 1.01, 5)
    pull(loops, tie, 10, 37)
    build_harness(part, make, textile, fit, skin, shell, mesh, web, piping, hardware)
    root = bpy.data.objects.new(
        "Osprey Talon 26 · Phantom Grey and Dark Charcoal", None
    )
    bpy.context.collection.objects.link(root)
    root["fieldItem"] = root.name
    root.location = (-0.363, -0.215, 0.468)
    root.rotation_euler.z = 0.085
    for shape in pieces:
        shape.finalize(30).parent = root


def build_hook(Sculpture, make):
    obj = Sculpture("Talon · under-shelf carry loop hook")
    metal = make("Brushed steel shelf hook", "6c6e69", 0.78, 0.38)
    obj.pipe(
        [
            (-369, 1054, 127),
            (-369, 1039, 127),
            (-369, 1028, 136),
            (-369, 1026, 143),
            (-369, 1029, 153),
            (-369, 1034, 153),
        ],
        2.7,
        metal,
        12,
    )
    obj.loft(
        [(-369, 1052.6, 127, 12, 10), (-369, 1054.9, 127, 12, 10)], metal, 16, 0.72
    )
    obj.finalize()
