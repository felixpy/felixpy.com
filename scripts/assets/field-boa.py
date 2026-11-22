import math
from mathutils import Vector


def build_closure(
    part, hand, shape, cable, tongue, overlay, lining, stitch, ink, dialpt
):
    tongue_part = part("padded tongue and woven keeper")
    widths = [
        (-46, 0.14),
        (-45, 0.34),
        (-42, 0.50),
        (-38, 0.58),
        (-33, 0.615),
        (-24, 0.61),
        (0, 0.605),
        (22, 0.595),
        (41, 0.59),
        (58, 0.555),
        (64, 0.42),
        (66, 0.23),
    ]

    def surface(d, angle, height=0):
        return Vector(shape(d, abs(angle), -1 if angle < 0 else 1, height))

    def padding(d):
        toe = max(0, min(1, (d - 39) / 24))
        return (
            2.3 + 2.1 * max(0, min(1, (-31 - d) / 13)) - 1.95 * toe**2 * (3 - 2 * toe)
        )

    def tongue_surface(d, angle):
        return surface(d, angle, padding(d))

    def width(d):
        for (a, wa), (b, wb) in zip(widths, widths[1:]):
            if d <= b:
                t = (d - a) / (b - a)
                return wa + (wb - wa) * t
        return widths[-1][1]

    samples = sorted({d for d, _ in widths} | {float(d) for d in range(-46, 67, 2)})
    across = [i / 12 for i in range(-12, 13)]
    face = [[tongue_surface(d, width(d) * a) for a in across] for d in samples]
    backing = [[p - Vector((0, 2.45, 0)) for p in row] for row in face]
    for rows, material in [(face, tongue), (backing, lining)]:
        n = len(across)
        tongue_part.add(
            [p for row in rows for p in row],
            [
                (i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1)
                for i in range(len(rows) - 1)
                for j in range(n - 1)
            ],
            material,
        )
    perimeter = (
        face[0]
        + [r[-1] for r in face[1:]]
        + list(reversed(face[-1][:-1]))
        + [r[0] for r in reversed(face[1:-1])]
    )
    tongue_part.rings(
        [perimeter, [p - Vector((0, 2.45, 0)) for p in perimeter]], lining, close=False
    )
    for side in (-1, 1):
        tongue_part.pipe(
            [tongue_surface(d, width(d) * side) for d in samples], 0.5, tongue, 8
        )

    def lace_point(d, angle):
        dd = surface(d + 0.10, angle) - surface(d - 0.10, angle)
        da = surface(d, angle + 0.003) - surface(d, angle - 0.003)
        normal = dd.cross(da).normalized()
        return (
            surface(d, angle, padding(d) if abs(angle) < 0.62 else 1.95) + normal * 0.56
        )

    wire = part("BOA routed lace and fairleads")
    carriers = part("textile seams and cable guides")
    levels = [
        (-37, 12.8, 0.685),
        (-19, 12.4, 0.695),
        (0.5, 11.8, 0.694),
        (20.3, 10.8, 0.683),
        (40, 10.3, 0.655),
    ]
    path = [dialpt(-6.0, 4.0, -1.7), lace_point(-40, 0.78 * hand)]
    for i, (d, bow, span) in enumerate(levels):
        side = hand if i % 2 == 0 else -hand
        if i:
            prev, _, last_span = levels[i - 1]
            for k in range(1, 17):
                u = k / 17
                angle = (
                    last_span + (span - last_span) * u + 0.08 * math.sin(math.pi * u)
                )
                path.append(lace_point(prev + (d - prev) * u, side * angle))
        for j in range(41):
            t = j / 40
            span_angle = side * span * math.cos(math.pi * t)
            depth = d + bow * math.sin(math.pi * t) + 0.85 * side * (2 * t - 1)
            path.append(lace_point(depth, span_angle))
        for side_guide in (-1, 1):
            rows = []
            for dd, scale in [
                (-2.7, 0.58),
                (-2.15, 0.88),
                (-1.5, 1.0),
                (1.5, 1.0),
                (2.15, 0.88),
                (2.7, 0.58),
            ]:
                row = []
                for a, rise in [
                    (-0.088, 0.18),
                    (-0.055, 0.50),
                    (-0.032, 1.28),
                    (0, 1.59),
                    (0.033, 1.20),
                    (0.06, 0.46),
                    (0.094, 0.15),
                    (0.094, -0.45),
                    (-0.088, -0.45),
                ]:
                    row.append(
                        surface(
                            d + dd, side_guide * (span + a * scale), 1.95 + rise * scale
                        )
                    )
                rows.append(row)
            carriers.rings(rows, overlay)
    for k in range(1, 9):
        t = k / 8
        path.append(
            surface(40.85 + 4.1 * t, -hand * (0.655 + 0.029 * t), 2.25 - 3.6 * t)
        )
    for k in range(1, 35):
        t = k / 34
        path.append(
            surface(
                44.95 + 8.1 * math.sin(t * math.pi),
                -hand * 0.684 * math.cos(t * math.pi),
                -1.35,
            )
        )
    for k in range(1, 49):
        t = k / 48
        path.append(
            surface(
                44.95 - 81.95 * t, hand * (0.684 + 0.15 * math.sin(math.pi * t)), -1.35
            )
        )
    path.append(dialpt(6.0, -4.2, -2.0))
    wire.pipe(path, 0.56, cable, 10)

    def tongue_tab(x, d, rise):
        radius = abs(shape(d, math.pi / 2, 1)[0] - shape(d, math.pi / 2, -1)[0]) / 2
        a = math.asin(min(0.9, abs(x) / radius))
        return surface(d, math.copysign(a, x), padding(d) + rise)

    toe_keeper = []
    for d, half, lift in [
        (47.6, 3.5, -0.30),
        (48.2, 5.0, 0.28),
        (49.1, 5.6, 1.34),
        (51.0, 5.6, 1.55),
        (52.4, 5.4, 0.65),
        (53.4, 4.7, -0.25),
    ]:
        toe_keeper.append(
            [tongue_tab(x * half, d, lift) for x in (-1, -0.5, 0, 0.5, 1)]
        )
    carriers.add(
        [p for row in toe_keeper for p in row],
        [
            (j * 5 + i, j * 5 + i + 1, (j + 1) * 5 + i + 1, (j + 1) * 5 + i)
            for j in range(len(toe_keeper) - 1)
            for i in range(4)
        ],
        overlay,
    )
    carriers.pipe(
        [
            tongue_tab(x, 50.1 + y, 1.69)
            for x, y in [
                (-2.5, 0),
                (-0.8, 0.72),
                (-0.12, -0.36),
                (0.76, 0.65),
                (2.4, -0.26),
            ]
        ],
        0.24,
        ink,
        7,
    )

    tag = []
    for d, half in [
        (-44, 3.0),
        (-42.5, 5.3),
        (-40.5, 5.9),
        (-26, 5.9),
        (-19, 5.7),
        (-17.8, 4.6),
    ]:
        tag.append([tongue_tab(a * half, d, 0.40) for a in (-1, -0.5, 0, 0.5, 1)])
    tongue_part.add(
        [p for row in tag for p in row],
        [
            (i * 5 + j, i * 5 + j + 1, (i + 1) * 5 + j + 1, (i + 1) * 5 + j)
            for i in range(len(tag) - 1)
            for j in range(4)
        ],
        overlay,
    )
    for edge in (0, -1):
        tongue_part.pipe([row[edge] for row in tag], 0.23, stitch, 6)
    part("technical markings").label(
        "KAILAS", 4.5, lambda x, y: tongue_tab(y, -31 + x, 0.62), ink
    )
