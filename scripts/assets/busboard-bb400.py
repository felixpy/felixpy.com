from itertools import pairwise

from product_solids import block, combine, mesh


def divisions(centres, low, high):
    return [low, *[(a + b) / 2 for a, b in pairwise(centres)], high]


def housing(name, columns, rows, bounds, ivory):
    x0, x1, z0, z1 = bounds
    xs, zs = divisions(columns, x0, x1), divisions(rows, z0, z1)
    vertices, faces = [], []

    def ring(left, right, near, far, y):
        start = len(vertices)
        vertices.extend(
            [(left, y, near), (left, y, far), (right, y, far), (right, y, near)]
        )
        return list(range(start, start + 4))

    def rim(outside, inside):
        for i in range(4):
            j = (i + 1) % 4
            faces.append((outside[i], outside[j], inside[j], inside[i]))

    for i, x in enumerate(columns):
        for j, z in enumerate(rows):
            tile = ring(xs[i], xs[i + 1], zs[j], zs[j + 1], 8.5)
            mouth = ring(x - 0.81, x + 0.81, z - 0.81, z + 0.81, 8.5)
            throat = ring(x - 0.48, x + 0.48, z - 0.48, z + 0.48, 7.9)
            neck = ring(x - 0.48, x + 0.48, z - 0.48, z + 0.48, 7.02)
            rim(tile, mouth)
            rim(mouth, throat)
            rim(throat, neck)
            bottom = ring(xs[i], xs[i + 1], zs[j], zs[j + 1], 7.02)
            rim(neck, bottom)
    upper = ring(x0, x1, z0, z1, 8.5)
    lower = ring(x0, x1, z0, z1, 0.9)
    rim(lower, upper)
    return mesh(name, vertices, faces, ivory)


def comb(name, sockets, bus, nickel):
    vertices, faces = [], []

    def strip(profile, x, z):
        start = len(vertices)
        for along in (-0.55, 0.55):
            for sideways, h in profile:
                dx, dz = (sideways, along) if bus else (along, sideways)
                vertices.append((x + dx, h, z + dz))
        n = len(profile)
        for i in range(n):
            j = (i + 1) % n
            faces.append((start + i, start + j, start + n + j, start + n + i))
        faces.extend(
            [
                tuple(start + i for i in range(n - 1, -1, -1)),
                tuple(start + n + i for i in range(n)),
            ]
        )

    for x, z in sockets:
        for side in (-1, 1):
            strip(
                [
                    (side * d, h)
                    for d, h in [
                        (0.63, 2.0),
                        (0.69, 5.0),
                        (0.32, 6.4),
                        (0.54, 6.86),
                        (0.46, 6.91),
                        (0.21, 6.41),
                        (0.56, 5.0),
                        (0.50, 2.0),
                    ]
                ],
                x,
                z,
            )
    first, last = sockets[0], sockets[-1]
    link = block(
        name + " tie",
        (first[0] + last[0]) / 2,
        2.0,
        (first[1] + last[1]) / 2,
        abs(last[0] - first[0]) + 1.4,
        0.18,
        abs(last[1] - first[1]) + 1.4,
        0.08,
        nickel,
    )
    return combine(name, [mesh(name, vertices, faces, nickel), link])


def build(m, label):
    rows = [(i - 14.5) * 2.54 for i in range(30)]
    busrows = [z + 1.27 for i, z in enumerate(rows) if i % 6 != 5]
    block("Peelable foam backing", 0, 0.45, 0, 53.85, 0.9, 83.5, 0.48, m["foam"])
    block("Recessed IC channel floor", 0, 3.95, 0, 2.5, 6.1, 83.8, 0.13, m["abs"])
    for side in (-1, 1):
        columns = sorted([side * (3.81 + i * 2.54) for i in range(5)])
        rails = sorted([side * 20.32, side * 22.86])
        bounds = sorted([side * 1.25, side * 17.48])
        housing(
            "Five way IC terminal bank", columns, rows, (*bounds, -41.9, 41.9), m["abs"]
        )
        bounds = sorted([side * 17.62, side * 27.15])
        housing(
            "Twin power rail housing", rails, busrows, (*bounds, -41.9, 41.9), m["abs"]
        )
        for i, z in enumerate(rows, 1):
            comb(
                f"Terminal clip {side:+} row {i}",
                [(x, z) for x in columns],
                False,
                m["contact"],
            )
        for x in rails:
            comb(
                f"Continuous supply clip {x:.2f}",
                [(x, z) for z in busrows],
                True,
                m["contact"],
            )
        for i in [1, 5, 10, 15, 20, 25, 30]:
            label(str(i), side * 15.85, 8.515, rows[i - 1], 1.27, m["ink"], 90)
        for j, x in enumerate(columns):
            label(
                "ABCDEFGHIJ"[j + (5 if side > 0 else 0)],
                x,
                8.515,
                -39.1,
                1.25,
                m["ink"],
                90,
            )
        positive, negative = (25.05, 18.42) if side < 0 else (18.42, 25.05)
        for dx, ink, mark in [(positive, "red", "+"), (negative, "ink", "–")]:
            block(
                "Power rail polarity ruling",
                side * dx,
                8.512,
                0,
                0.23,
                0.016,
                72.9,
                0.06,
                m[ink],
            )
            for z in (-39.4, 39.4):
                label(mark, side * dx, 8.527, z, 1.8, m[ink], 90)
    label("BusBoard.com", -8.9, 8.515, 39.6, 1.26, m["ink"])
    label("BB400", 8.9, 8.515, 39.6, 1.45, m["ink"])
