import math
import bpy
from mathutils import Vector


def build_jieshan(
    Sculpture, make, textile, build_outsole, build_tread, build_heel, build_closure
):
    knit = textile(
        make("KAILAS · ash grey woven upper", "bab8aa", 0.0, 0.93),
        "Fine shoe warp",
        True,
        0.82,
        0.47,
    )
    tongue = textile(
        make("KAILAS · padded tongue", "c1bfb3", 0.01, 0.88),
        "Fine shoe warp",
        True,
        0.78,
        0.44,
    )
    overlay = make("KAILAS · laminated waterproof eyestay", "c6c4b7", 0.08, 0.63)
    embossed = textile(
        make("KAILAS · textured midfoot TPU support", "b5b5a8", 0.02, 0.73),
        "Quarter panel microperforations",
        True,
        0.64,
        0.33,
    )
    border = make("KAILAS · welded olive underlay", "9b9a87", 0.12, 0.74)
    heel_cage = make(
        "KAILAS · smoked translucent heel stabilizer", "9c9f91", 0.37, 0.27, 0.38
    )
    stitch = make("KAILAS · grey braided stitching", "aca99b", 0, 0.89)
    dial_face = make("BOA · embossed dial face", "414244", 0.27, 0.42)
    midsole = make("KAILAS · warm grey EVA", "c5c3ba", 0.02, 0.84)
    bumper = make("KAILAS · protective toe rand", "aaa99a", 0.05, 0.72)
    lining = textile(
        make("KAILAS · heel lining", "6e6d62", 0.0, 0.94),
        "Collar micro liner",
        True,
        0.59,
    )
    rubber = make("Vibram · carbon rubber", "282a29", 0.04, 0.88)
    dial = make("BOA · overmolded dial", "232525", 0.19, 0.52)
    cable = make("BOA · coated lace cable", "303234", 0.15, 0.46)
    ink = make("Footwear · graphite markings", "494b46", 0.08, 0.67)
    yellow = make("Vibram · yellow badge", "f3b63b", 0.02, 0.62)
    fine = make("KAILAS · rolled seams", "dfdcd0", 0.02, 0.83)
    stations = [
        (-130, 12, 107, 33),
        (-126, 23, 110, 34),
        (-116, 35, 116, 35),
        (-97, 41, 120, 36),
        (-76, 44, 121, 37),
        (-54, 44, 131, 37),
        (-37, 43, 139, 36),
        (-19, 44, 128, 34),
        (3, 49, 107, 31),
        (24, 52, 88, 29),
        (47, 56, 70, 27),
        (70, 57, 59, 27),
        (92, 54, 53, 29),
        (112, 45, 49, 32),
        (127, 31, 43, 35),
        (136, 13, 42, 39),
        (139, 1.1, 40, 40),
    ]

    def section(d):
        k = next(
            (i for i, row in enumerate(stations) if row[0] >= d), len(stations) - 1
        )
        a = stations[max(0, k - 1)]
        b = stations[k]
        t = 0 if b[0] == a[0] else (d - a[0]) / (b[0] - a[0])
        result = []
        for j in range(1, 4):
            if not k:
                result.append(a[j])
                continue
            before = stations[max(0, k - 2)]
            after = stations[min(len(stations) - 1, k + 1)]
            slope = (b[j] - a[j]) / (b[0] - a[0])

            def tangent(left, right):
                return 0 if left * right <= 0 else 2 * left * right / (left + right)

            m = (
                tangent(slope, (a[j] - before[j]) / (a[0] - before[0]))
                if a[0] != before[0]
                else slope
            )
            n = (
                tangent(slope, (after[j] - b[j]) / (after[0] - b[0]))
                if b[0] != after[0]
                else slope
            )
            span = b[0] - a[0]
            result.append(
                (2 * t**3 - 3 * t * t + 1) * a[j]
                + (t**3 - 2 * t * t + t) * m * span
                + (-2 * t**3 + 3 * t * t) * b[j]
                + (t**3 - t * t) * n * span
            )
        return result

    def opening(d):
        return 0.78 * math.sin(math.pi * max(0, min(1, (d + 124) / 94))) ** 0.65

    ds = sorted(
        set([d for d, _, _, _ in stations] + [-130 + i * 269 / 56 for i in range(57)])
    )

    def bandpatch(obj, side, fn, grid, mat, lift=0, nt=12):
        samples = []
        for a, b in zip(grid, grid[1:]):
            steps = max(1, math.ceil((b[0] - a[0]) / 2.2))
            for i in range(steps):
                samples.append(tuple(x + (y - x) * i / steps for x, y in zip(a, b)))
        grid = samples + grid[-1:]
        verts = []
        for d, t1, t2 in grid:
            for k in range(nt + 1):
                verts.append(fn(d, t1 + (t2 - t1) * k / nt, side, lift))
        rows = len(grid)
        width = nt + 1
        obj.add(
            verts,
            [
                (
                    j * width + i,
                    j * width + i + 1,
                    (j + 1) * width + i + 1,
                    (j + 1) * width + i,
                )
                for j in range(rows - 1)
                for i in range(nt)
            ],
            mat,
        )

    for hand in [-1, 1]:
        name = "KAILAS Jieshan GTX BOA · " + ("right" if hand < 0 else "left")
        pieces = {}

        def part(title):
            if title not in pieces:
                pieces[title] = Sculpture(name + " · " + title)
            return pieces[title]

        def shape(d, t, side, lift=0):
            w, top, base = section(d)
            shift = hand * (
                -4.2 * max(0, d / 139) ** 2 + 2.2 * math.exp(-(((d - 35) / 39) ** 2))
            )
            return (
                shift + side * (w + lift) * math.sin(t),
                base + (top - base + lift) * max(0, math.cos(t)) ** 0.81,
                d,
            )

        for s in [-1, 1]:
            obj = part("woven upper")
            bandpatch(
                obj, s, shape, [(d, opening(d), math.pi / 2) for d in ds], knit, nt=16
            )
            obj = part("collar and sockliner")
            collar_depths = sorted({-124.0, -30.0, *(d for d in ds if -124 < d < -30)})
            collar = [shape(d, opening(d), s, 0.55) for d in collar_depths]
            obj.pipe(
                collar,
                [
                    2.65 + 1.2 * math.sin(j * math.pi / (len(collar) - 1))
                    for j in range(len(collar))
                ],
                tongue,
                10,
            )
            if s == 1:
                rim = [shape(d, opening(d), -1) for d in collar_depths] + [
                    shape(d, opening(d), 1) for d in reversed(collar_depths[1:-1])
                ]
                inner = [
                    (
                        x * 0.77,
                        59 + 2.5 * math.cos((d + 78) * math.pi / 93),
                        -77 + (d + 77) * 0.83,
                    )
                    for x, h, d in rim
                ]
                rows = [
                    [(x, h - 0.3, d) for x, h, d in rim],
                    [(x * 0.95, h - 3.0, -77 + (d + 77) * 0.96) for x, h, d in rim],
                    [(x * 0.87, h - 14, -77 + (d + 77) * 0.90) for x, h, d in rim],
                    inner,
                ]
                obj.rings(rows, lining, close=False)
                floor = [
                    (x * 0.94, h - 1.45, -77 + (d + 77) * 0.93) for x, h, d in inner
                ]
                obj.rings([inner, floor], lining, close=False)
                obj.add(
                    [(0, 58, -77)] + floor,
                    [(0, i + 1, (i + 1) % len(floor) + 1) for i in range(len(floor))],
                    lining,
                )
            obj = part("rear quarter overlays")
            heel_outline = [
                (-130, 0, 1.57),
                (-126, 0.28, 1.57),
                (-116, 0.61, 1.57),
                (-98, 0.80, 1.57),
                (-81, 0.90, 1.57),
                (-70, 0.87, 1.57),
                (-54, 0.72, 1.57),
                (-43, 0.58, 1.57),
                (-34, 0.57, 1.57),
                (-28, 0.59, 1.57),
            ]
            bandpatch(obj, s, shape, heel_outline, overlay, 1.8, 18)
            bandpatch(
                obj,
                s,
                shape,
                [
                    (-97, 1.12, 1.27),
                    (-88, 1.08, 1.36),
                    (-75, 1.01, 1.47),
                    (-61, 0.96, 1.54),
                    (-45, 0.93, 1.52),
                    (-36, 0.97, 1.45),
                    (-29, 1.04, 1.28),
                ],
                embossed,
                2.32,
                13,
            )
            obj = part("welded eyestays and sidewall overlays")
            frame = [
                (-28, 0.59, 1.24, 1.24),
                (-24, 0.59, 1.18, 1.25),
                (-16, 0.58, 0.98, 1.27),
                (-6, 0.58, 0.85, 1.31),
                (6, 0.60, 0.83, 1.36),
                (17, 0.60, 0.87, 1.40),
                (25, 0.64, 0.83, 1.41),
                (35, 0.65, 0.88, 1.45),
                (46, 0.66, 0.89, 1.47),
                (56, 0.65, 0.95, 1.50),
                (65, 0.69, 1.04, 1.51),
                (74, 0.76, 1.23, 1.51),
                (79, 0.88, 1.46, 1.50),
            ]
            bandpatch(
                obj, s, shape, [(d, a, b) for d, a, b, c in frame], overlay, 1.80, 9
            )
            bandpatch(
                obj,
                s,
                shape,
                [(d, c - 0.032, 1.57) for d, a, b, c in frame],
                border,
                1.60,
                8,
            )
            bandpatch(
                obj,
                s,
                shape,
                [(d, c + 0.028, 1.57) for d, a, b, c in frame],
                overlay,
                2.0,
                8,
            )
            grid = [(d, a, c) for d, a, b, c in frame]
            sewing = part("textile seams and cable guides")
            for d in range(-25, 78, 3):
                ends = []
                for pos in [d, d + 1.62]:
                    j = next(j for j, r in enumerate(frame) if r[0] >= pos)
                    a, b = frame[j - 1 : j + 1]
                    ratio = (pos - a[0]) / (b[0] - a[0])
                    t = a[2] + (b[2] - a[2]) * ratio - 0.020
                    ends.append(shape(pos, t, s, 2.02))
                sewing.pipe(ends, 0.24, stitch, 6)
            obj = part("toe bumper")
            bandpatch(
                obj,
                s,
                shape,
                [
                    (72, 1.42, 1.56),
                    (85, 1.18, 1.55),
                    (99, 0.96, 1.55),
                    (110, 0.77, 1.55),
                    (121, 0.4, 1.56),
                    (129, 0.05, 1.56),
                    (136, 0, 1.56),
                    (139, 0, 1.56),
                ],
                bumper,
                1.3,
                9,
            )
            obj = part("textile seams and cable guides")
            obj.pipe(
                [shape(d, b - 0.016, s, 2.0) for d, a, b in grid][3:], 0.56, fine, 5
            )
        build_outsole(
            part, hand, ds, section, shape, midsole, rubber, yellow, ink, build_tread
        )
        build_heel(
            part, hand, section, shape, knit, overlay, heel_cage, stitch, ink, rubber
        )
        for side in [-1, 1]:
            obj = part("rear quarter overlays")
            bandpatch(
                obj,
                side,
                shape,
                [
                    (d, t - 0.035, t + 0.034)
                    for d, t in [
                        (-125, 0.58),
                        (-118, 0.69),
                        (-107, 0.87),
                        (-93, 1.02),
                        (-81, 1.09),
                        (-70, 1.06),
                        (-59, 0.94),
                        (-46, 0.83),
                    ]
                ],
                fine,
                2.35,
                4,
            )
            for d in range(-115, -62, 3):
                obj.pipe(
                    [
                        shape(d, 0.82 + (d + 115) * 0.006, side, 2.25),
                        shape(d + 1.6, 0.83 + (d + 115) * 0.006, side, 2.25),
                    ],
                    0.26,
                    border,
                    5,
                )
        obj = part("BOA rotary assembly")
        root = Vector(shape(-42, 0.86, hand, 1.85))
        normal = Vector((hand * 0.87, 0.49, 0.04)).normalized()
        tangent = Vector((0, 0, -hand))
        level = normal.cross(tangent).normalized()

        def dialpt(x, y, d):
            return root + tangent * x + level * y + normal * d

        def saddle_point(radius, angle, gap):
            across = radius * math.cos(angle)
            up = radius * math.sin(angle)
            lo, hi = -24.0, 14.0
            for _ in range(14):
                offset = (lo + hi) * 0.5
                q = dialpt(across, up, offset)
                w, h, low = section(q.z)
                edge = shape(q.z, math.pi / 2, hand, 1.8)
                center = edge[0] - hand * (w + 1.8)
                radial = ((q.x - center) / (w + 1.8)) ** 2
                radial += max(0, (q.y - low) / (h - low + 1.8)) ** (2 / 0.81)
                if radial > 1:
                    hi = offset
                else:
                    lo = offset
            return dialpt(across, up, (lo + hi) * 0.5 + gap)

        seat = []
        for radius, gap in [(18.7, -0.45), (19.0, 0.24), (18.6, 0.7), (16.9, 1.15)]:
            seat.append(
                [saddle_point(radius, i * math.tau / 72, gap) for i in range(72)]
            )
        seat.append(
            [
                dialpt(
                    15.65 * math.cos(i * math.tau / 72),
                    15.65 * math.sin(i * math.tau / 72),
                    0.4,
                )
                for i in range(72)
            ]
        )
        obj.rings(seat, overlay)
        rows = []
        for radius, out in [
            (17.0, -4.8),
            (16.8, 0.4),
            (15.8, 2.2),
            (15.8, 5.0),
            (14.5, 6.2),
            (12.8, 6.4),
        ]:
            rows.append(
                [
                    dialpt(
                        radius * math.cos(a * math.tau / 72),
                        radius * math.sin(a * math.tau / 72),
                        out,
                    )
                    for a in range(72)
                ]
            )
        obj.rings(rows, dial)

        def dial_ring(shape, profile, material):
            shape.rings(
                [
                    [
                        dialpt(
                            r * math.cos(i * math.tau / 72),
                            r * math.sin(i * math.tau / 72),
                            z,
                        )
                        for i in range(72)
                    ]
                    for r, z in profile
                ],
                material,
            )

        dial_ring(
            obj,
            [
                (15.1, 5.05),
                (14.6, 6.15),
                (13.7, 6.44),
                (12.4, 6.42),
                (11.9, 6.92),
                (9, 7.33),
                (0.09, 7.37),
            ],
            dial,
        )
        for i in range(10):
            center = i * math.tau / 10
            crown = []
            for da, z, r in [
                (-0.17, 2.4, 15.9),
                (-0.14, 4.8, 16.55),
                (-0.09, 6.0, 15.7),
                (0.01, 6.08, 14.2),
                (0.105, 5.0, 15.7),
                (0.133, 2.64, 15.9),
            ]:
                crown.append(
                    dialpt(r * math.cos(center + da), r * math.sin(center + da), z)
                )
            obj.add(crown, [tuple(range(6))], dial_face)
        obj.pipe(
            [
                dialpt(
                    13.1 * math.cos(j * math.tau / 60),
                    13.1 * math.sin(j * math.tau / 60),
                    6.52,
                )
                for j in range(61)
            ],
            0.24,
            dial_face,
            6,
        )
        build_closure(
            part, hand, shape, cable, tongue, overlay, lining, stitch, ink, dialpt
        )
        obj = part("BOA rotary assembly")
        for k in range(16):
            a = k * math.tau / 16
            obj.pipe(
                [
                    dialpt(15.8 * math.cos(a), 15.8 * math.sin(a), 2.7),
                    dialpt(15.6 * math.cos(a + 0.045), 15.6 * math.sin(a + 0.045), 4.8),
                ],
                [0.75, 0.75],
                ink,
                5,
            )
        obj.label("BOA", 6.0, lambda x, y: dialpt(x, y, 7.49), dial_face)
        obj = part("technical markings")
        obj.label(
            "GORE-TEX",
            4.0,
            lambda x, y: shape(-3 - hand * x, 0.75 - y * 0.010, hand, 3.25),
            ink,
        )
        diamond = [(-11, 0.75), (-9.4, 0.716), (-7.8, 0.75), (-9.4, 0.784), (-11, 0.75)]
        obj.pipe(
            [shape(-3 - hand * x, t, hand, 3.25) for x, t in diamond], 0.24, ink, 6
        )
        obj.label(
            "Vibram",
            3.8,
            lambda x, y: (
                shape(-58 - hand * x, math.pi / 2, hand, 2.1)[0],
                13 + y,
                -58 - hand * x,
            ),
            yellow,
        )
        result = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(result)
        for item in pieces.values():
            item.finalize(48).parent = result
        result["fieldItem"] = name
        result.location = (
            0.394 if hand > 0 else 0.248,
            -(0.197 if hand > 0 else 0.184),
            0.12392,
        )
        result.rotation_euler.z = math.radians(6 if hand > 0 else -7)
