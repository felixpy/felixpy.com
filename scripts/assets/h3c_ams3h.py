import math

import bpy

from product_workshop import finish_material


def cover(part):
    profile = [
        (0.815, 0.234),
        (0.837, 0.233),
        (0.862, 0.229),
        (0.887, 0.222),
        (0.911, 0.210),
        (0.934, 0.194),
        (0.955, 0.170),
        (0.970, 0.143),
        (0.981, 0.111),
        (0.987, 0.070),
        (0.989, 0.016),
        (0.989, -0.105),
        (0.986, -0.146),
        (0.979, -0.176),
        (0.967, -0.198),
        (0.948, -0.214),
        (0.922, -0.224),
        (0.891, -0.229),
        (0.854, -0.230),
        (0.815, -0.230),
    ]

    def lip(x, drop, inset):
        return [
            (x, 0.815 + (y - 0.815) * (1.138 - drop), z * (1 - inset))
            for y, z in profile
        ]

    sides = [
        (0.208, 0, 0),
        (0.220, 0.004, 0.002),
        (0.227, 0.016, 0.007),
        (0.232, 0.035, 0.015),
        (0.236, 0.067, 0.027),
        (0.238, 0.090, 0.040),
    ]
    arch = [lip(-x, dy, dz) for x, dy, dz in reversed(sides)] + [
        lip(x, dy, dz) for x, dy, dz in sides
    ]
    panels(
        part,
        "AMS 3H · formed smoke cover and rolled shoulders",
        "canopy",
        arch,
        reverse=True,
    )
    for sign in (-1, 1):
        gasket = [
            lip(sign * 0.2380, 0.087, 0.040),
            lip(sign * 0.2385, 0.094, 0.045),
            lip(sign * 0.2389, 0.116, 0.057),
            lip(sign * 0.2384, 0.128, 0.061),
        ]
        panels(
            part, "AMS 3H · stepped end window seal", "black", gasket, reverse=sign > 0
        )
        cap = lip(sign * 0.2384, 0.128, 0.061)
        part.surface(
            "AMS 3H · side inspection window",
            "smoke",
            cap,
            [tuple(range(len(cap))) if sign < 0 else tuple(reversed(range(len(cap))))],
        )
        for z in (-0.139, -0.123, -0.107):
            part.rod(
                "AMS 3H · grip flute on side glass",
                "smoke",
                (sign * 0.2391, 0.838, z),
                (sign * 0.2391, 0.869, z + 0.004),
                0.00075,
                sides=8,
            )
    for z in (-0.228, 0.233):
        part.block(
            "AMS 3H · cover gasket",
            "black",
            (0, 0.815, z),
            (0.465, 0.004, 0.008),
            0.0018,
        )
    part.block(
        "AMS 3H · central cover grip",
        "graphite",
        (0, 0.824, 0.2345),
        (0.191, 0.017, 0.012),
        0.005,
    )
    for x in (-0.132, 0.132):
        part.block(
            "AMS 3H · lid hinge",
            "graphite",
            (x, 0.819, -0.228),
            (0.038, 0.018, 0.010),
            0.004,
        )


def panels(part, name, finish, rows, reverse=False, closed=False):
    count = len(rows[0])
    faces = []
    for j in range(len(rows) - 1):
        for i in range(count if closed else count - 1):
            n = (i + 1) % count
            ring = (
                j * count + i,
                j * count + n,
                (j + 1) * count + n,
                (j + 1) * count + i,
            )
            faces.append(ring[::-1] if reverse else ring)
    return part.surface(
        name, finish, [point for row in rows for point in row], faces, True
    )


def front_depth(height):
    return 0.264 - 0.033 * min(1, max(0, (height - 0.587) / 0.225))


def width(height):
    t = max(0, min(1, (height - 0.587) / 0.228))
    return 0.245 - 0.008 * t - 0.014 * math.sin(math.pi * t) ** 1.4


def carrier(part, rounded_rectangle):
    for side in (-1, 1):
        z_fractions = [
            0,
            0.008,
            0.023,
            0.056,
            0.10,
            0.19,
            0.31,
            0.43,
            0.56,
            0.69,
            0.81,
            0.9,
            0.965,
            0.990,
            1,
        ]

        def shell_row(level, offset=0):
            row = []
            for u in z_fractions:
                shoulder = math.sin(math.pi * u) ** 0.9
                seam = 0.699 + 0.068 * u - 0.007 * math.sin(math.pi * u)
                y = level(seam, shoulder)
                retreat = 0.007 * (1 - shoulder) ** 8
                x = width(y) - retreat + offset * shoulder
                z = (1 - u) * (front_depth(y) - 0.010) - u * (
                    0.263 - 0.033 * (y - 0.587) / 0.229
                )
                row.append((side * x, y, z))
            return row

        base = shell_row(lambda h, q: 0.587)
        lower = [
            base,
            shell_row(lambda h, q: 0.591),
            shell_row(lambda h, q: 0.617),
            shell_row(lambda h, q: h - 0.009 * q),
            shell_row(lambda h, q: h - 0.005 * q),
        ]
        middle = [
            lower[-1],
            shell_row(lambda h, q: h - 0.003 * q, -0.0011),
            shell_row(lambda h, q: h + 0.0003 * q, -0.0055),
            shell_row(lambda h, q: h + 0.003 * q, -0.0062),
            shell_row(lambda h, q: h + 0.0065 * q, -0.0018),
        ]
        upper = [
            middle[-1],
            shell_row(lambda h, q: h + 0.009 * q),
            shell_row(lambda h, q: 0.788),
            shell_row(lambda h, q: 0.810),
            shell_row(lambda h, q: 0.815),
        ]
        panels(
            part, "AMS 3H · sweeping lower support", "graphite", lower, reverse=side < 0
        )
        panels(
            part,
            "AMS 3H · recessed diagonal side reveal",
            "black",
            middle,
            reverse=side < 0,
        )
        panels(part, "AMS 3H · upper dryer fascia", "graphite", upper, reverse=side < 0)
        inside = [
            [(x - side * 0.009, y, z) for x, y, z in r] for r in (base, upper[-1])
        ]
        panels(
            part, "AMS 3H · sidewall inner return", "black", inside, reverse=side > 0
        )
        for rows in ((inside[0], base), (upper[-1], inside[1])):
            panels(
                part, "AMS 3H · structural return", "graphite", rows, reverse=side < 0
            )
        for end in (0, -1):
            outer = [r[end] for r in lower + middle[1:] + upper[1:]]
            inner = [(x - side * 0.009, y, z) for x, y, z in outer]
            panels(
                part,
                "AMS 3H · hemmed front and rear edges",
                "graphite",
                [outer, inner],
                reverse=(end == 0) == (side < 0),
            )

    def rail(w, bottom, top, r, z_offset=0):
        result = []
        for x, y in rounded_rectangle(0, (bottom + top) / 2, w, top - bottom, r, 8):
            edge = abs(x / (w / 2))
            result.append(
                (x * width(y) / 0.237, y, front_depth(y) - 0.011 * edge**12 + z_offset)
            )
        return result

    outer = (0.469, 0.587, 0.815, 0.0065)
    opening = (0.398, 0.591, 0.739, 0.012)
    front = [
        rail(*outer, -0.011),
        rail(*outer, -0.002),
        rail(*outer),
        rail(0.465, 0.5874, 0.812, 0.0072),
        rail(0.434, 0.589, 0.776, 0.010),
        rail(0.402, 0.5906, 0.742, 0.0132),
        rail(*opening),
        rail(*opening, -0.007),
    ]
    panels(
        part,
        "AMS 3H · radiused front portal and broad brow",
        "graphite",
        front,
        closed=True,
    )
    panels(
        part,
        "AMS 3H · feed access return",
        "black",
        [rail(*opening, -0.007), rail(0.392, 0.592, 0.736, 0.010, -0.014)],
        closed=True,
    )
    part.block(
        "AMS 3H · portal header liner",
        "black",
        (0, 0.755, 0.131),
        (0.407, 0.009, 0.162),
        0.003,
    )
    for x in (-0.172, 0.166):
        part.block(
            "AMS 3H · rear chamber hinge housing",
            "black",
            (x, 0.806, -0.224),
            (0.064, 0.018, 0.020),
            0.004,
        )
    marking = bpy.data.curves.new("AMS 3H front identification", type="FONT")
    marking.body = "AMS 3H"
    marking.size = 0.0083
    marking.space_character = 1.12
    marking.resolution_u = 3
    obj = bpy.data.objects.new("AMS 3H · front satin model lettering", marking)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.129, -front_depth(0.783) - 0.00035, 0.783)
    obj.rotation_euler.x = math.pi / 2 - math.atan(0.033 / 0.225)
    part.parts["satin"].append(obj)


def feeding_bay(part, outline):
    deck = outline(0, -0.004, 0.472, 0.525, 0.026, 9)
    top = [(x, 0.589, z) for x, z in deck]
    underside = [(x, 0.585, z) for x, z in deck]
    panels(
        part,
        "AMS 3H · deck rolled perimeter",
        "graphite",
        [top, underside],
        closed=True,
    )
    part.surface(
        "AMS 3H · sealed platform beneath feed tubes",
        "graphite",
        top,
        [tuple(reversed(range(len(top))))],
    )
    outline_xy = [
        (0.018, 0.586),
        (0.222, 0.586),
        (0.229, 0.590),
        (0.230, 0.600),
        (0.223, 0.793),
        (0.218, 0.802),
        (-0.186, 0.802),
        (-0.188, 0.798),
        (-0.186, 0.791),
        (-0.145, 0.754),
        (-0.093, 0.708),
        (-0.051, 0.668),
        (-0.020, 0.634),
        (0.004, 0.601),
    ]

    def depth(y):
        return -0.170 + 0.059 * (y - 0.586) / 0.216

    front = [(x, y, depth(y)) for x, y in outline_xy]
    back = [(x, y, -0.235) for x, y in outline_xy]
    part.surface(
        "AMS 3H · angled dryer service bulkhead",
        "graphite",
        front,
        [tuple(range(len(front)))],
    )
    panels(
        part,
        "AMS 3H · return along the open feed chamber",
        "black",
        [front, back],
        closed=True,
    )
    for index in range(15):
        x = 0.004 + index * 0.0134
        part.rod(
            "AMS 3H · molded service rib",
            "graphite",
            (x, 0.622, depth(0.622) + 0.0009),
            (x + 0.024, 0.676, depth(0.676) + 0.0009),
            0.0012,
            sides=8,
        )
    for i in range(5):
        x = (i - 2) * 0.084
        part.block(
            "AMS 3H · first-stage feeder",
            "black",
            (x, 0.836, 0.203),
            (0.040, 0.030, 0.029),
            0.005,
        )
        part.rod(
            "AMS 3H · loading funnel",
            "graphite",
            (x, 0.836, 0.212),
            (x, 0.849, 0.216),
            0.0085,
            0.0068,
            sides=20,
        )
        part.rod(
            "AMS 3H · entry bushing",
            "brass",
            (x, 0.846, 0.215),
            (x, 0.8495, 0.2164),
            0.0057,
            0.0055,
            sides=20,
        )
        part.rod(
            "AMS 3H · bushing throat",
            "black",
            (x, 0.8494, 0.2163),
            (x, 0.8496, 0.2165),
            0.0035,
            sides=16,
        )


def editable_source(part, directory):
    group = bpy.data.collections.new("AMS 3H · canopy and carrier")
    scene = bpy.data.scenes.new("AMS 3H component workshop")
    scene.collection.children.link(group)
    for finish, objects in part.parts.items():
        for obj in objects:
            if not obj.name.startswith("AMS 3H ·"):
                continue
            obj.data.materials.append(finish_material(finish))
            group.objects.link(obj)
    bpy.data.libraries.write(
        str(directory / "ams-3h-editable.blend"), {scene}, fake_user=True, compress=True
    )
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(group)
