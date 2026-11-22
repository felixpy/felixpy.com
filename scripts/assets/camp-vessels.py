import math


def cookset(Sculpture, pose, curved_path, titanium, wire, bright):
    for label, radius, column, row, reach, yaw, pitch in [
        ("large", 76.2, 4, 19, 167, 0.55, 1.40),
        ("small", 66.65, 13, 14, 140, -0.30, 1.36),
    ]:
        pan = Sculpture("Snow Peak SCS-020T · " + label + " frypan")
        r = radius
        pan.turn(
            [
                (0, 0.01),
                (0, 0.70 * r),
                (0.45, 0.76 * r),
                (2.1, 0.81 * r),
                (5, 0.86 * r),
                (9, 0.90 * r),
                (13.3, 0.91 * r),
                (21.8, 0.928 * r),
                (23.2, 0.945 * r),
                (24.7, 0.970 * r),
                (28.8, 0.982 * r),
                (30.7, 0.991 * r),
                (31.2, r),
                (31.75, r - 0.12),
                (31.85, r - 0.63),
                (31.4, r - 1.0),
                (30, r - 1.1),
                (29, 0.974 * r),
                (24.4, 0.965 * r),
                (22.9, 0.941 * r),
                (21.4, 0.92 * r),
                (13, 0.90 * r),
                (8.3, 0.88 * r),
                (5, 0.85 * r),
                (2.1, 0.79 * r),
                (0.85, 0.73 * r),
                (0.85, 0.01),
            ],
            titanium,
            88,
        )
        tip = r + 83.0
        ends = [
            (-14.7, 20.5, -r * 0.931),
            (-17.6, 20.5, -r * 0.937),
            (-18.6, 21, -r * 0.976),
            (-18.4, 21.8, -r - 8),
            (-15, 22.0, -tip + 7),
            (-14.4, 22.0, -tip + 2),
            (-12.3, 22.1, -tip),
            (0, 22.1, -tip),
            (12.2, 22.1, -tip),
            (14.4, 22.0, -tip + 2),
            (15, 22.0, -tip + 7),
            (18.4, 21.8, -r - 8),
            (18.6, 21, -r * 0.976),
            (17.6, 20.5, -r * 0.937),
            (14.7, 20.5, -r * 0.931),
        ]
        curved_path(pan, ends, 1.65, wire)
        for side in (-1, 1):
            center = side * 13.8
            z = -math.sqrt((r * 0.93) ** 2 - center**2)
            pan.plate(
                [
                    (center - 5.0, 11, z),
                    (center + 5.0, 11, z),
                    (center + 5.0, 22.3, z - 0.7),
                    (center - 5.0, 22.3, z - 0.7),
                ],
                titanium,
                1,
                0.38,
                0.09,
            )
            pan.pipe(
                [(center - 2.8, 20.6, z - 1), (center + 2.8, 20.6, z - 1)],
                2.55,
                wire,
                12,
            )
            pan.form((center, 14.4, z - 0.45), (2.0, 2.0, 0.88), bright)
        pose(
            pan,
            (column * 25.4, 1572 + row * 25.4 - 24, reach - 3),
            pitch,
            yaw,
            yaw * 0.11,
            (0, 22.1, -tip),
        )


def open_spout(vessel, profile, material, outermost):
    low, high, lower_radius, upper_radius, half_width = profile
    rows = []
    for inside in (False, True):
        heights = (0, 0.055, 0.14, 0.31, 0.60, 0.85, 0.97, 1)
        for v in reversed(heights) if inside else heights:
            y = low + (high - low) * v
            body = lower_radius + (upper_radius - lower_radius) * v
            width = half_width * (0.13 + 0.87 * math.sqrt(v))
            lip = (outermost - upper_radius) * (0.025 + 0.975 * v**0.68)
            row = []
            for i in range(35):
                u = i / 34 * 2 - 1
                d = u * width
                belly = max(0, 1 - abs(u) ** 1.65)
                x = -math.sqrt(body**2 - d**2) - lip * belly + 0.55
                row.append((x + (0.66 if inside else 0), y - 3.0 * v * belly, d))
            rows.append(row)
    n = len(rows[0])
    faces = []
    for j in range(len(rows) - 1):
        for i in range(n - 1):
            a = j * n + i
            faces.append((a, a + 1, a + n + 1, a + n))
    vessel.add([pt for row in rows for pt in row], faces, material)


def snow_stamp(vessel, radius_at, y, material, size=9):
    def project(x, h):
        r = radius_at(h) + 0.07
        return r * math.sin(x / r), h, r * math.cos(x / r)

    vessel.label("snow peak", size, lambda x, h: project(x, y + h), material)
    for i in range(3):
        angle = i * math.pi / 3
        dx, dh = math.sin(angle), math.cos(angle)
        mark = [
            project(s * 5.5 * dx + t * 0.92 * dh, y + 11 + s * 5.5 * dh - t * 0.92 * dx)
            for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        vessel.add(mark, [(0, 1, 2, 3)], material, False)


def lid_with_ports(vessel, radius, height, material):
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt

    xy, edges = [], []
    holes = [(-30, -10, 1.95), (-32, 0, 1.95), (-30, 10, 1.95)]
    for x, d, r, n in [(0, 0, radius, 96), *((x, d, r, 20) for x, d, r in holes)]:
        first = len(xy)
        for i in range(n):
            angle = math.tau * i / n
            xy.append(Vector((x + r * math.cos(angle), d + r * math.sin(angle))))
            edges.append((first + i, first + (i + 1) % n))
    points, _, faces, *_ = delaunay_2d_cdt(xy, edges, [], 0, 0.0001)
    valid = []
    for face in faces:
        x, d = sum((points[i] for i in face), Vector((0, 0))) / len(face)
        if all((x - hx) ** 2 + (d - hd) ** 2 > r * r for hx, hd, r in holes):
            valid.append(tuple(reversed(face)))
    vessel.add([(p.x, height, p.y) for p in points], valid, material, False)
    for x, d, r in holes:
        vessel.rings(
            [
                [
                    (
                        x + r * math.cos(i * math.tau / 20),
                        y,
                        d + r * math.sin(i * math.tau / 20),
                    )
                    for i in range(20)
                ]
                for y in (height - 0.9, height)
            ],
            material,
            True,
            False,
        )


def coffee_kettle(Sculpture, curve, steel, turned, wire, brass, wood, ink):
    vessel = Sculpture("Snow Peak CS-115R · Field Barista Kettle")
    bottom, neck, lip, radius, mouth = 62.5, 47.5, 148.3, 47.4, 87.5
    knob_top, mount, low_grip, high_grip, x_end = 180, 130, 44, 152, 117.5
    profile = [
        (0, 0.005),
        (0, bottom - 5),
        (0.4, bottom - 3.6),
        (1.3, bottom - 2.4),
        (3.2, bottom - 1),
        (5.1, bottom - 0.30),
        (7, bottom),
        (10, bottom),
        (lip - 3, neck),
        (lip - 1.45, neck + 0.18),
        (lip - 0.9, neck + 0.61),
        (lip, neck + 0.65),
        (lip + 0.52, neck + 0.17),
        (lip + 0.50, neck - 0.50),
        (lip - 0.4, neck - 0.9),
        (lip - 3, neck - 0.82),
        (10, bottom - 0.82),
        (5, bottom - 1.3),
        (1.05, bottom - 5),
        (1.05, 0.005),
    ]
    vessel.turn(profile, steel, 96)

    def body_at(h):
        t = max(0, min(1, (h - 10) / (lip - 13)))
        return bottom * (1 - t) + neck * t

    y0, y1 = 58, 139
    open_spout(
        vessel,
        (y0, y1, body_at(y0), body_at(y1), 23.6),
        steel,
        mouth,
    )
    vessel.turn(
        [
            (148.4, 46.3),
            (148.9, 47.25),
            (149.7, radius),
            (156.9, radius),
            (157.9, 47.1),
            (158.35, 46.4),
            (158.45, 45.30),
        ],
        steel,
        96,
    )
    lid_with_ports(vessel, 45.30, 158.45, steel)
    vessel.turn(
        [
            (158.45, 0.01),
            (158.45, 11.3),
            (159.1, 12.1),
            (160, 12.5),
            (162, 13.7),
            (164, 14.1),
            (177.8, 14.05),
            (179, 13.7),
            (179.8, 12.2),
            (knob_top, 10.1),
            (knob_top, 0.01),
        ],
        wood,
        72,
    )
    rear = body_at(mount)
    for d in (-6.8, 6.8):
        curve(
            vessel,
            [
                (rear - 0.8, mount - 7, d),
                (rear + 1.8, mount - 7, d),
                (rear + 2.3, mount + 4, d),
                (rear + 2.4, high_grip - 5, d),
                (rear + 4.0, high_grip - 1, d),
                (rear + 8.5, high_grip, d),
                (x_end - 13, high_grip + 3.6, d),
                (x_end - 8.8, high_grip + 2.0, d),
                (x_end - 7.0, high_grip - 1.7, d),
                (x_end - 1.8, low_grip + 7.2, d),
                (x_end - 1.9, low_grip + 3.3, d * 0.86),
                (x_end - 2, low_grip + 0.8, d * 0.52),
                (x_end - 2.1, low_grip, 0),
            ],
            2.05,
            wire,
            14,
        )
    vessel.pipe([(rear - 1, mount, 0), (rear + 4.4, mount, 0)], 7.25, turned, 32)
    vessel.pipe(
        [
            (rear + 4.2, mount, 0),
            (rear + 6.1, mount, 0),
            (rear + 6.5, mount, 0),
            (rear + 9.5, mount, 0),
            (rear + 10.1, mount, 0),
        ],
        [5.5, 5.8, 6.7, 6.7, 6.2],
        brass,
        56,
    )
    for i in range(30):
        a = math.tau * i / 30
        h, d = mount + 6.57 * math.cos(a), 6.57 * math.sin(a)
        vessel.pipe([(rear + 6.7, h, d), (rear + 9.3, h, d)], 0.22, brass, 5)
    snow_stamp(vessel, body_at, 74, ink, 10.2)
    return vessel

