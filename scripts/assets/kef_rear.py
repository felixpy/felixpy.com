import math

from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


def rounded(width, height, radius, steps=8):
    path = []
    for quadrant, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for i in range(steps + 1):
            a = (quadrant + i / steps) * math.pi / 2
            p = (
                sx * (width / 2 - radius) + radius * math.cos(a),
                sy * (height / 2 - radius) + radius * math.sin(a),
            )
            if not path or math.dist(path[-1], p) > 1e-7:
                path.append(p)
    if math.dist(path[0], path[-1]) < 1e-7:
        path.pop()
    return path


def offset(path, x, y):
    return [(x + u, y + v) for u, v in path]


def ring(radius, sides=32):
    return [
        (
            radius * math.cos(i * math.tau / sides),
            radius * math.sin(i * math.tau / sides),
        )
        for i in range(sides)
    ]


class RearAssembly:
    def __init__(self, build, variant):
        self.build = build
        self.variant = variant

    def mesh(self, name, finish, points, faces, smooth=False):
        obj = self.build(
            name,
            self.variant + "-" + finish,
            [(-x, y, -d) for x, y, d in points],
            faces,
            smooth,
        )
        obj["speakerPart"] = self.variant
        obj["surfaceFinish"] = finish
        return obj

    def loft(self, name, finish, sections, smooth=True):
        n = len(sections[0][0])
        if any(len(path) != n for path, _ in sections):
            raise ValueError(f"Cross sections do not match in {name}")
        points = [(x, y, d) for path, d in sections for x, y in path]
        faces = [
            (k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i)
            for k in range(len(sections) - 1)
            for i in range(n)
        ]
        return self.mesh(name, finish, points, faces, smooth)

    def plate(self, name, finish, outline, holes, front, back):
        paths = [outline, *holes]
        points, loops = [], []
        for path in paths:
            loops.append(list(range(len(points), len(points) + len(path))))
            points.extend(Vector(p) for p in path)
        coords, _, triangles, _, _, original = delaunay_2d_cdt(
            points, [], loops, 0, 1e-6
        )
        surface = [t for t, ids in zip(triangles, original) if set(ids) == {0}]
        n = len(coords)
        vertices = [(p.x, p.y, depth) for depth in (front, back) for p in coords]
        faces = [*surface, *(tuple(i + n for i in reversed(t)) for t in surface)]
        index = {(round(p.x, 4), round(p.y, 4)): i for i, p in enumerate(coords)}
        for k, path in enumerate(paths):
            ids = [index[(round(p.x, 4), round(p.y, 4))] for p in map(Vector, path)]
            for i, a in enumerate(ids):
                b = ids[(i + 1) % len(ids)]
                wall = (a, a + n, b + n, b)
                faces.append(wall[::-1] if k else wall)
        return self.mesh(name, finish, vertices, faces)


def stadium(x, y, r, straight):
    return offset(rounded(2 * r, 2 * (r + straight), r, 16), x, y)


def cooling(a):
    cx, cy = -45.5, 67.5
    mounting = stadium(cx, cy, 40.8, 12)
    a.plate(
        "Recessed thermal chassis and open port mounting aperture",
        "alloy",
        rounded(195, 296, 18),
        [mounting],
        130.5,
        128.5,
    )
    perimeter = rounded(195, 296, 18)
    a.loft(
        "Cabinet rear rebate and perimeter return",
        "alloy",
        [(perimeter, 130), (perimeter, 148.8), (rounded(191.8, 292.8, 16.4), 149)],
    )
    xs = sorted(
        {-94.5 + 189 * i / 250 for i in range(251)}
        | {cx + 42.3 * math.cos(i * math.pi / 80) for i in range(81)}
    )

    def limits(x):
        u = min(1, abs(x) / 94.5)
        inset = max(0, abs(x) - 78.5)
        corner = 16 - math.sqrt(max(0, 16**2 - inset**2))
        return -47.2 - 13.4 * u**2.4 - corner * 0.36, 146 - corner

    def depth(x):
        return (
            155.65
            - 3.9 * (abs(x) / 94.5) ** 4
            + 1.45 * math.cos((x + 2.4) * math.tau / 12.1)
        )

    vertices, indices, strips = [], {}, []
    for x in xs:
        low, high = limits(x)
        u = (x - cx) / 42.3
        gap = 12 + 42.3 * math.sqrt(max(0, 1 - u * u)) if abs(u) <= 1.0000001 else 0
        row = []
        for y in [low, cy - gap, cy + gap, high]:
            p = (x, y, depth(x))
            if p not in indices:
                indices[p] = len(vertices)
                vertices.append(p)
            row.append(indices[p])
        strips.append(row)
    front = [
        (left[j], right[j], right[j + 1], left[j + 1])
        for left, right in zip(strips, strips[1:])
        for j in (0, 2)
    ]
    a.mesh(
        "Continuous fluted amplifier heat sink face", "heatsink", vertices, front, True
    )
    back = [(x, y, d - 1.6) for x, y, d in vertices]
    a.mesh(
        "Inner face of amplifier extrusion",
        "heatsink",
        back,
        [f[::-1] for f in front],
        True,
    )
    edges = set()
    for face in front:
        for i, v in enumerate(face):
            w = face[(i + 1) % 4]
            if (w, v) in edges:
                edges.remove((w, v))
            else:
                edges.add((v, w))
    n = len(vertices)
    a.mesh(
        "Exposed top bottom and port cut edges",
        "heatsink",
        vertices + back,
        [(w, v, v + n, w + n) for v, w in edges],
    )
    for i in range(17):
        x = (i - 8) * 11.35
        low, high = limits(x)
        bottom = low - max(2, 13 * (1 - (abs(x) / 95) ** 2.6))
        spans = [(bottom, high)]
        if abs(x - cx) < 43.5:
            gap = 13 + math.sqrt(43.5**2 - (x - cx) ** 2)
            spans = [(bottom, cy - gap), (cy + gap, high)]
        for number, (lo, hi) in enumerate(spans):
            if hi - lo < 1:
                continue
            face = [(x - 0.95, lo), (x + 0.95, lo), (x + 0.95, hi), (x - 0.95, hi)]
            a.plate(
                f"Extrusion thermal web {i + 1:02d}.{number + 1}",
                "heatsink",
                face,
                [],
                depth(x) - 1.45,
                130.3,
            )

    def profile(r, half, d):
        return stadium(cx, cy, r, half), d

    bell = [
        (42.9, 12, 152.9),
        (43.15, 12, 157.45),
        (42.75, 12, 157.85),
        (39.2, 12, 157.55),
        (36.6, 11.8, 156.5),
        (33.4, 11.7, 153.9),
        (30.4, 11.4, 149.1),
        (27.4, 11, 142),
        (23.4, 10.6, 131),
        (19.3, 10.2, 117),
        (16.3, 9.8, 101),
        (15.6, 9.5, 94),
    ]
    a.loft(
        "Copper-colour flared port mouth and throat",
        "copper",
        [profile(*v) for v in bell],
    )
    duct = [
        (15.6, 9.5, 94),
        (15.1, 9.3, 79),
        (15, 9, 48),
        (15.2, 9, 16),
        (15.9, 9.2, -3),
        (17.3, 9.5, -14),
        (20.5, 10, -23),
        (25, 10.6, -30),
        (29, 11, -32.4),
        (30.7, 11, -31.9),
        (30.4, 11, -30),
        (26.2, 10.6, -27.6),
        (22.2, 10, -20.5),
        (19, 9.5, -12),
        (17.6, 9.2, -2),
        (17, 9, 16),
        (16.8, 9, 48),
        (16.9, 9.3, 80),
        (17.4, 9.5, 94),
        (15.6, 9.5, 94),
    ]
    a.loft(
        "Closed-cell port sleeve and internal bell",
        "lining",
        [profile(*v) for v in duct],
    )
    a.plate(
        "Absorbent lining on the inside of the front baffle",
        "lining",
        offset(rounded(184, 86, 8), 0, 95),
        [],
        -100,
        -103,
    )


def io_panel(a, primary):
    def rounded_at(x, y, w, h, r):
        return offset(rounded(w, h, r, 4), x, y)

    def circle(x, y, r):
        return offset(ring(r), x, y)

    holes = []
    surface = 148.95

    def socket(name, x, y, outline, finish, rim, recess=8):
        contour = offset(outline, x, y)
        large = offset([(px * rim, py * rim) for px, py in outline], x, y)
        holes.append(contour)
        a.loft(
            name + " rim",
            finish,
            [
                (large, surface + 0.2),
                (large, surface + 1.1),
                (contour, surface + 1.1),
                (contour, surface + 0.15),
            ],
            False,
        )
        a.loft(
            name + " insulating throat",
            "lining",
            [(contour, surface + 0.15), (contour, surface - recess)],
            False,
        )
        a.plate(
            name + " socket well",
            "lining",
            contour,
            [],
            surface - recess,
            surface - recess - 0.6,
        )

    def blade(name, x, y, w, h, d):
        a.plate(
            name, "contact", rounded_at(x, y, w, h, min(0.13, w * 0.2)), [], d, d - 2.7
        )

    def rj45(x, y, label):
        shape = [
            (-7, -3),
            (-3, -3),
            (-3, -5.1),
            (3, -5.1),
            (3, -3),
            (7, -3),
            (7, 5),
            (-7, 5),
        ]
        socket(label, x, y, shape, "metal", 1.14, 10)
        for i in range(8):
            blade(
                label + f" contact {i + 1}",
                x + (i - 3.5) * 1.02,
                y + 3.4,
                0.43,
                1.6,
                surface - 5,
            )

    def jack(x, y, name, outer, inner, finish):
        holes.append(circle(x, y, inner))
        a.loft(
            name,
            finish,
            [
                (circle(x, y, outer), surface),
                (circle(x, y, outer), surface + 2.9),
                (circle(x, y, inner), surface + 3),
                (circle(x, y, inner), surface - 4),
            ],
        )
        a.plate(
            name + " insulator",
            "lining",
            circle(x, y, inner),
            [],
            surface - 4,
            surface - 5,
        )

    def button(x, y, name):
        a.plate(name, "alloy", circle(x, y, 2.3), [], surface + 1.3, surface)
        a.plate(
            name + " status light",
            "metal",
            circle(x, y + 7.1, 0.66),
            [],
            surface + 0.25,
            surface,
        )

    if primary:
        y = -86.7
        hdmi = [
            (-6.9, 2.5),
            (-6.9, -0.3),
            (-5.3, -2.5),
            (5.3, -2.5),
            (6.9, -0.3),
            (6.9, 2.5),
        ]
        socket("HDMI eARC", -60.6, y, hdmi, "metal", 1.12, 6.5)
        blade("HDMI contact tongue", -60.6, y + 0.65, 10.4, 0.72, surface - 1.4)
        socket(
            "TOSLINK optical input", -40.5, y, rounded(9, 8.6, 0.55), "alloy", 1.17, 3.1
        )
        a.plate(
            "Spring-loaded optical dust door",
            "alloy",
            rounded_at(-40.5, y, 7.3, 7, 0.6),
            [],
            surface - 0.7,
            surface - 1,
        )
        jack(-20.2, y, "Coaxial S/PDIF", 4.1, 2.25, "contact")
        jack(0, y, "AUX 3.5 mm", 3.1, 1.75, "alloy")
        for x, n in [
            (20.2, "Reset"),
            (40.5, "Primary secondary pairing"),
            (60.7, "Bluetooth pairing"),
        ]:
            button(x, y, n)
    y = -116
    rj45(-58, y, "Inter-speaker Ethernet")
    jack(-33, y, "Subwoofer RCA", 4.15, 2.25, "contact")
    socket("USB service", -7.5, y, rounded(5.5, 13, 0.45), "metal", 1.2, 8)
    blade("USB service tongue", -8.3, y, 1.25, 10.7, surface - 1.6)
    if primary:
        rj45(18, y, "Network Ethernet")
    else:
        button(18, y, "Primary secondary pairing")
    mains = [(-10.9, -7), (10.9, -7), (10.9, 3), (7, 7), (-7, 7), (-10.9, 3)]
    socket("Recessed two-pole AC inlet", 54, y, mains, "alloy", 1.21, 10.5)
    for i in (-1, 1):
        blade("AC terminal " + str(i), 54 + i * 6.5, y - 1.4, 1.2, 4.3, surface - 2)
    fixes = [(-78, -128), (78, -128), (-74, -103), (34, -103)]
    if primary:
        fixes.extend([(-74, -86.5), (74, -86.5)])
    for i, (x, y) in enumerate(fixes):
        outer = circle(x, y, 2.8)
        hexagon = offset(ring(1.35, 6), x, y)
        a.plate(
            f"Socket-head fixing {i + 1}",
            "alloy",
            outer,
            [hexagon],
            surface + 1.7,
            surface,
        )
    outline = rounded_at(0, -104, 189, 79, 12)
    a.plate(
        "Primary connector plate" if primary else "Secondary connector plate",
        "alloy",
        outline,
        holes,
        surface,
        146.8,
    )
    a.plate(
        "Dark enclosure below the heat sink",
        "alloy",
        rounded_at(0, -57.4, 189, 25, 4),
        [],
        141,
        139,
    )
