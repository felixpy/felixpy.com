import math


def polar(radius, height, angle):
    return (radius * math.sin(angle), height, radius * math.cos(angle))


def windowed_barrel(shape, profile, radius, center, width, height, material, segments):
    lo, hi = center - height / 2, center + height / 2
    half_angle = math.asin(width / 2 / radius(center))
    angles = {(i / segments - 0.5) * math.tau for i in range(segments)}
    angles = sorted(angles | {-half_angle, half_angle})
    levels = sorted({lo, hi, *(z for z, _ in profile)})
    points = [polar(radius(z), z, a) for z in levels for a in angles]
    count = len(angles)
    faces = []
    for j, z in enumerate(levels[:-1]):
        for i, a in enumerate(angles):
            if lo <= z < hi and -half_angle <= a < half_angle:
                continue
            k = (i + 1) % count
            faces.append((j * count + i, j * count + k, (j + 1) * count + k, (j + 1) * count + i))
    shape.add(points, faces, material)


def recessed_display(shape, radius, center, width, height, screen_width, screen_height, shell, trim, glass):
    center_radius = radius(center)
    edge_depth = math.sqrt(center_radius ** 2 - (width / 2) ** 2)
    depth = (center_radius + edge_depth) / 2

    def perimeter(w, h, corner_radius, offset, curved):
        def surface_point(x, z):
            base = math.sqrt(radius(z) ** 2 - x ** 2) if curved else depth
            return x, z, base + offset

        row = []
        for i, (sx, sz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            for j in range(6):
                a = (i + j / 5) * math.pi / 2
                x = sx * (w / 2 - corner_radius) + corner_radius * math.cos(a)
                z = center + sz * (h / 2 - corner_radius) + corner_radius * math.sin(a)
                row.append(surface_point(x, z))
            end_x, end_z, _ = row[-1]
            next_x = -end_x if i % 2 == 0 else end_x
            next_z = end_z if i % 2 == 0 else 2 * center - end_z
            for j in range(1, 9):
                x = end_x + (next_x - end_x) * j / 9
                z = end_z + (next_z - end_z) * j / 9
                row.append(surface_point(x, z))
        return row

    shoulder = perimeter(width - 1.2, height - 1.2, 0.95, 0.22, False)
    shape.rings([
        perimeter(width + 0.16, height + 0.16, 0.13, 0.032, True),
        perimeter(width - 0.23, height - 0.23, 1.22, 0.06, True),
        perimeter(width - 0.48, height - 0.48, 1.10, 0.12, False),
        shoulder,
    ], shell, False, False)
    shape.rings([
        shoulder,
        perimeter(width - 1.64, height - 1.64, 0.79, 0.29, False),
        perimeter(screen_width + 0.35, screen_height + 0.35, 0.43, 0.29, False),
        perimeter(screen_width, screen_height, 0.34, -0.30, False),
    ], trim, False, False)
    face = perimeter(screen_width, screen_height, 0.34, -0.30, False)
    shape.add(face, [tuple(range(len(face)))], glass, False)


def dot(shape, xyz, az, z, radius, material):
    pts = [
        xyz(
            az + math.cos(i * math.tau / 24) * radius / 34.5,
            z + math.sin(i * math.tau / 24) * radius,
            0.42,
        )
        for i in range(24)
    ]
    shape.add(pts, [tuple(range(24))], material, False)


def panel(shape, radius, z, az, width, height, lift, material):
    rows = []
    for offset, inset in [(lift - 0.5, 0.14), (lift - 0.14, 0), (lift, 0.14)]:
        w, h = width / 2 - inset, height / 2 - inset
        bend = min(w, h, 1.3)
        row = []
        for i, (sign_u, sign_v) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
            for j in range(5):
                t = (i + j / 4) * math.pi / 2
                u = sign_u * (w - bend) + bend * math.cos(t)
                v = sign_v * (h - bend) + bend * math.sin(t)
                row.append(polar(radius(z + v) + offset, z + v, az + u / radius(z)))
        rows.append(row)
    shape.rings(rows, material, False)


def button(shape, radius, z, az, size, ext, bezel, rubber):
    def loop(rr, lift):
        result = []
        for i in range(40):
            a = i * math.tau / 40
            zz = z + rr * math.sin(a)
            result.append(
                polar(radius(zz) + lift, zz, az + rr * math.cos(a) / radius(z))
            )
        return result

    shape.rings(
        [
            loop(size + 0.38, -0.15),
            loop(size + 0.42, 0.32),
            loop(size + 0.12, 0.75),
            loop(size - 0.23, 0.79),
        ],
        bezel,
    )
    shape.rings(
        [
            loop(size - 0.29, 0.6),
            loop(size - 0.35, ext - 0.36),
            loop(size - 0.65, ext),
            loop(size * 0.75, ext + 0.08),
        ],
        rubber,
    )


def switch(shape, radius, mark, z, az, labels, rim, grip):
    panel(shape, radius, z, az, 10.9, 4.1, 0.64, rim)
    panel(shape, radius, z, az + 0.051, 5.0, 3.6, 1.29, grip)
    for dx in [-1.05, -0.35, 0.35, 1.05]:
        panel(shape, radius, z, az + 0.051 + dx / radius(z), 0.23, 2.5, 1.4, rim)
    mark(labels[0], z + 4.0, az - 0.11, 2.05)
    mark(labels[1], z + 4.0, az + 0.11, 2.05)


def petal(shape, bottom, height, radius, material):
    rows = []
    for phase, radius_delta in [
        (0, -0.15),
        (0.09, 0.14),
        (0.94, 0.20),
        (1, 0.05),
        (1, -1.05),
        (0.94, -1.22),
        (0, -1.28),
    ]:
        row = []
        for i in range(160):
            a = math.tau * i / 160
            crown = (
                max(0, math.cos(2 * a)) ** 1.2 + 0.51 * max(0, -math.cos(2 * a)) ** 1.6
            )
            z = bottom + phase * (1.0 + (height - bottom - 1) * crown)
            row.append(polar(radius + radius_delta, z, a))
        rows.append(row)
    shape.rings(rows, material, True, False)


def tripod(shape, radius, z, shell, enamel, satin, gray, mark):
    shape.turn(
        [
            (29.1, 38.1),
            (30.7, 40.7),
            (34.3, 41.2),
            (58.5, 41.2),
            (61.2, 40.7),
            (62.0, 39.7),
        ],
        shell,
        112,
    )
    for end in (31, 60.1):
        shape.turn([(end - 0.35, 40.6), (end, 41.15), (end + 0.29, 40.8)], enamel, 112)
    button(shape, lambda _: 41.2, z, -1.46, 5.9, 5.8, satin, enamel)
    for y in (35.6, 39.1, 42.6, 46.1, 49.6, 53.1):
        mark("|", y, 0.46, 2.2, gray, lift=2.0)
    neck = [
        (33.3, -38.6),
        (57.2, -38.6),
        (55, -46),
        (53, -49.8),
        (55, -54.5),
        (74, -55.1),
        (74, -58),
        (35, -58),
        (35, -53),
        (37, -50),
        (37, -45),
    ]

    def extrusion(outline, halfwidth, mat):
        rows = []
        for x0, scale in [
            (-halfwidth, 0.974),
            (-halfwidth + 0.8, 1),
            (halfwidth - 0.8, 1),
            (halfwidth, 0.974),
        ]:
            midz = sum(zz for zz, _ in outline) / len(outline)
            midd = sum(dd for _, dd in outline) / len(outline)
            rows.append(
                [
                    (x0, midz + (zz - midz) * scale, midd + (dd - midd) * scale)
                    for zz, dd in outline
                ]
            )
        shape.rings(rows, mat, False)

    extrusion(neck, 9.8, shell)
    sole = [
        (24, -54.9),
        (88, -54.9),
        (91, -56.7),
        (91, -59.1),
        (88.5, -61.4),
        (26.7, -61.4),
        (23.4, -59.4),
        (22.6, -57),
    ]
    extrusion(sole, 17.8, enamel)
    for x0 in (-10.7, 10.7):
        shape.pipe([(x0, 29, -61.4), (x0, 84.5, -61.4)], 0.44, enamel, 8)


def signature(shape, xyz, z, az, material):
    strokes = [
        [
            (-9, -2.4),
            (-8.1, -1.9),
            (-7.1, 0.1),
            (-5.4, 2.7),
            (-5.6, 2.6),
            (-7.3, -0.6),
            (-8.3, -2.6),
        ],
        [
            (-8.5, 0.9),
            (-7.3, 2),
            (-5, 2.9),
            (-3.6, 2.7),
            (-3.4, 1.9),
            (-4.5, 1.0),
            (-6.25, 0.45),
            (-6.8, 0.48),
        ],
        [
            (-5.5, -1.35),
            (-4, -0.85),
            (-2.2, 1.15),
            (-1.2, 2.72),
            (-1.3, 3),
            (-2.1, 2.6),
            (-3.1, 0.95),
            (-3.75, -0.85),
            (-3.3, -1.4),
            (-1.9, -0.97),
            (-0.4, -0.1),
            (-0.5, 0.65),
            (-1.15, 0.6),
            (-1.95, -0.2),
            (-2, -0.98),
            (-1.21, -1.39),
            (0.36, -0.93),
            (1.38, 0.52),
            (0.43, -1.17),
            (1.51, 0.03),
            (2.42, 0.54),
            (2.75, 0.36),
            (2.01, -0.98),
            (2.3, -1.22),
            (3.22, -0.99),
            (4.66, 0.35),
            (5.52, 0.43),
            (5.55, -0.15),
            (4.34, -1.26),
            (3.68, -1.16),
            (3.64, -0.52),
            (4.67, 0.42),
            (5.64, 0.55),
            (5.15, -0.68),
            (5.21, -1.27),
            (6.35, -1.0),
            (7.24, -0.4),
        ],
    ]
    for stroke in strokes:
        points = []
        for i in range(len(stroke) - 1):
            p0, p1, p2, p3 = [
                stroke[min(len(stroke) - 1, max(0, j))]
                for j in (i - 1, i, i + 1, i + 2)
            ]
            for j in range(5):
                t = j / 5
                a, b = [
                    0.5
                    * (
                        2 * v1
                        + (-v0 + v2) * t
                        + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t * t
                        + (-v0 + 3 * v1 - 3 * v2 + v3) * t * t * t
                    )
                    for v0, v1, v2, v3 in zip(p0, p1, p2, p3)
                ]
                points.append(xyz(az + a / 45, z + b, 0.37))
        a, b = stroke[-1]
        points.append(xyz(az + a / 45, z + b, 0.37))
        shape.pipe(points, 0.145, material, 6, 0.70)


def diaphragm(shape, count, z, outer, inner, material, edge):
    for i in range(count):
        angle = i * math.tau / count
        delta = math.tau / count

        def point(u, v):
            r0 = inner * (1 - 0.35 * (1 - math.cos(delta / 2)) * math.sin(math.pi * u))
            r = r0 + (outer - r0) * v
            return polar(r, z - 0.14 * v, angle + delta * u + 0.63 * v - 0.15 * v * v)

        pts = [point(k / 8, j / 6) for j in range(7) for k in range(9)]
        faces = [
            (j * 9 + k, j * 9 + k + 1, (j + 1) * 9 + k + 1, (j + 1) * 9 + k)
            for j in range(6)
            for k in range(8)
        ]
        shape.add(pts, faces, material, True)
        seam = [point(0, j / 8) for j in range(9)]
        shape.pipe([(x, h + 0.015, d) for x, h, d in seam], 0.048, edge, 5)
