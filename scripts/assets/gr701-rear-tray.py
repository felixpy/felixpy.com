import itertools
import math

from mathutils import Vector

ROG_FOIL = (
    ((0, 14), (5, 18), (13, 21), (6, 16)),
    ((7, 15), (14, 17), (32, 4), (47, 0), (34, 8), (16, 22), (13, 22)),
    ((17, 20), (47, 5), (40, 18), (34, 20), (39, 11), (24, 19), (29, 20), (22, 22)),
)


def position(u, v, depth):
    return (depth, 262 - (v - 122) * 0.974, 193 - (u - 267) * 0.907)


def rectangle(u0, v0, u1, v1, radius=1):
    r = min(radius, (u1 - u0) / 2.1, (v1 - v0) / 2.1)
    return [
        (u0 + r, v0),
        (u1 - r, v0),
        (u1, v0 + r),
        (u1, v1 - r),
        (u1 - r, v1),
        (u0 + r, v1),
        (u0, v1 - r),
        (u0, v0 + r),
    ]


def circle(u, v, r, sides=12):
    return [
        (u + r * math.cos(i * math.tau / sides), v + r * math.sin(i * math.tau / sides))
        for i in range(sides)
    ]


def mounting_plates(plate):
    mount = rectangle(333, 158, 480, 595, 5)
    eyelets = []
    for v in (182, 294, 421, 548):
        for u in (350, 461):
            eyelets.append(rectangle(u - 2, v, u + 2, v + 24, 1.8))
    eyelets.extend(
        circle(u, v, 1.85, 8)
        for u, v in ((356, 238), (356, 535), (437, 535), (438, 254))
    )
    plate(
        "steel", "Removable vertical equipment plate", mount, 93.1, 2.1, eyelets, 0.35
    )
    stiffener = [
        (344, 212),
        (354, 202),
        (354, 181),
        (359, 176),
        (456, 176),
        (456, 182),
        (362, 182),
        (361, 207),
        (349, 220),
        (349, 279),
        (345, 284),
    ]
    plate("steel", "Upper swage on vertical plate", stiffener, 95, 2.2, edge=0.4)
    for u in (348, 458):
        for v, end in ((289, 412), (417, 542)):
            plate(
                "steel",
                f"Stamped vertical rib {u} {v}",
                [
                    (u, v + 5),
                    (u + 5, v),
                    (u + 6, v + 42),
                    (u + 2, v + 48),
                    (u + 2, end - 7),
                    (u + 6, end - 2),
                    (u + 3, end),
                    (u - 2, end - 6),
                ],
                94.7,
                2,
                edge=0.25,
            )
    plate(
        "steel",
        "Lower swage on vertical plate",
        [
            (344, 549),
            (349, 547),
            (349, 568),
            (354, 574),
            (451, 574),
            (459, 565),
            (463, 566),
            (454, 580),
            (351, 580),
            (344, 573),
        ],
        94.9,
        2,
        edge=0.3,
    )
    for u in (666, 746):
        outline = [
            (u - 31, 377),
            (u - 23, 377),
            (u - 10, 362),
            (u + 10, 362),
            (u + 23, 377),
            (u + 33, 377),
            (u + 33, 474),
            (u + 25, 474),
            (u + 17, 485),
            (u - 19, 485),
            (u - 26, 476),
            (u - 31, 476),
        ]
        holes = [
            rectangle(u - 21, 395, u - 18, 457, 1),
            rectangle(u + 17, 395, u + 20, 457, 1),
        ]
        plate("steel", f"Rear 2.5-inch SSD sled {u}", outline, 94.2, 1.6, holes, 0.35)
        for s in (-1, 1):
            rib = [
                (u + s * a, b)
                for a, b in (
                    (3, 467),
                    (9, 467),
                    (22, 453),
                    (22, 408),
                    (10, 393),
                    (10, 387),
                    (27, 405),
                    (27, 457),
                    (13, 473),
                    (3, 473),
                )
            ]
            plate(
                "steel", f"SSD sled stiffening press {u} {s}", rib, 95.6, 1.7, edge=0.35
            )
        plate(
            "polymer",
            f"SSD sled thumb screw {u}",
            circle(u + 8, 371, 3.4),
            97.0,
            3.0,
            edge=0.3,
        )


def cable(shell, name, controls, radius):
    path = [Vector(position(*point)) for point in controls]
    centres = []
    for i, (a, b) in enumerate(itertools.pairwise(path)):
        prev = path[max(0, i - 1)]
        nxt = path[min(len(path) - 1, i + 2)]
        m = (b - prev).normalized() * (b - a).length
        n = (nxt - a).normalized() * (b - a).length
        for t in (0, 1 / 3, 2 / 3):
            t2, t3 = t * t, t * t * t
            centres.append(
                (2 * t3 - 3 * t2 + 1) * a
                + (t3 - 2 * t2 + t) * m
                + (-2 * t3 + 3 * t2) * b
                + (t3 - t2) * n
            )
    centres.append(path[-1])
    vertices, faces = [], []
    sides = 7
    for i, p in enumerate(centres):
        tangent = (
            centres[min(len(centres) - 1, i + 1)] - centres[max(0, i - 1)]
        ).normalized()
        through = Vector((1, 0, 0))
        lateral = through.cross(tangent).normalized()
        normal = tangent.cross(lateral)
        for j in range(sides):
            angle = j * math.tau / sides
            vertices.append(
                tuple(
                    p + radius * (lateral * math.cos(angle) + normal * math.sin(angle))
                )
            )
    for i in range(len(centres) - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    caps = [
        tuple(reversed(range(sides))),
        tuple(range(len(vertices) - sides, len(vertices))),
    ]
    obj = shell(name, vertices, [*faces, *caps])
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def harness(shell, plate, parts):
    knots = [
        (304, 154),
        (318, 147),
        (408, 147),
        (466, 150),
        (507, 166),
        (546, 193),
        (573, 226),
        (578, 294),
        (577, 389),
        (580, 476),
        (591, 530),
        (586, 573),
        (565, 612),
        (571, 650),
    ]
    for strand in range(11):
        spread = (strand - 5) * 2.15
        points = [
            (310 + spread * 0.08, 201 + spread * 0.30, 90.5),
            (311 + spread * 0.22, 185 + spread * 0.3, 95.1),
        ]
        for idx, (u, v) in enumerate(knots):
            rise = min(1, idx / 6)
            u += spread * rise + (
                2.6 * math.sin(idx * 0.57 + strand * 0.6) if idx > 8 else 0
            )
            v += spread * (1 - rise) * 0.55
            points.append((u, v, 98.4 + 0.85 * math.sin(strand * 2.5 + idx * 0.35)))
        points.append((570 + spread * 0.75, 657 + spread * 0.19, 91.0))
        obj = cable(
            shell, f"Power and signal loom · conductor {strand + 1:02d}", points, 0.83
        )
        parts["wire"].append(obj)
    for u, v in ((578, 234), (578, 297), (580, 386), (580, 470)):
        section = [
            (-29, 94.8),
            (-26, 99.3),
            (-21, 101.4),
            (-13, 102.25),
            (13, 102.25),
            (22, 101.4),
            (25, 99.3),
            (29, 94.8),
        ]
        vertices = []
        for du, x in section:
            vertices.extend(
                position(u + du, v + dv, x + d)
                for dv, d in ((-5.8, 0), (5.8, 0), (5.8, -0.70), (-5.8, -0.70))
            )
        faces = [(0, 1, 2, 3), tuple(range(len(vertices) - 4, len(vertices)))]
        for i in range(len(section) - 1):
            for j in range(4):
                k = (j + 1) % 4
                faces.append((4 * i + j, 4 * i + k, 4 * i + 4 + k, 4 * i + 4 + j))
        parts["polymer"].append(
            shell(f"Hook-and-loop cable strap at {v}", vertices, faces, 0.2)
        )
        for side in (-1, 1):
            left = u + side * 27
            plate(
                "steel",
                f"Strap anchor {v} {side}",
                rectangle(left - 2, v - 9, left + 2, v + 9),
                96.2,
                4.6,
                edge=0.4,
            )
        for i, contour in enumerate(ROG_FOIL):
            plate(
                "print",
                f"Woven ROG strap emblem {v} {i + 1}",
                [(u - 13 + a * 0.27, v - 3 + b * 0.27) for a, b in contour],
                102.34,
                0.04,
            )


def hub(plate, shell, parts):
    left, top, right, bottom = 648, 586, 773, 645
    fixings = [(682, 630), (711, 605), (747, 629)]
    plate(
        "polymer",
        "ARGB and PWM controller PCB",
        rectangle(left, top, right, bottom, 2),
        94.6,
        1.45,
        [circle(u, v, 2.1, 10) for u, v in fixings],
        0.12,
    )
    for u, v in fixings:
        plate(
            "steel",
            f"Controller mounting boss {u}",
            circle(u, v, 3.6),
            94.25,
            4.25,
            edge=0.25,
        )
        cross = [
            (-1, -0.37),
            (-0.37, -0.37),
            (-0.37, -1),
            (0.37, -1),
            (0.37, -0.37),
            (1, -0.37),
            (1, 0.37),
            (0.37, 0.37),
            (0.37, 1),
            (-0.37, 1),
            (-0.37, 0.37),
            (-1, 0.37),
        ]
        plate(
            "polymer",
            f"Controller cross-drive screw {u}",
            circle(u, v, 2.9),
            95.9,
            1.6,
            [[(u + 1.5 * i, v + 1.5 * j) for i, j in cross]],
            0.12,
        )
    for edge, sign, row in ((top, -1, "top"), (bottom, 1, "bottom")):
        for i in range(6):
            u = left + 9 + i * 15.15
            offsets = (0, 2, 3) if i % 2 == 0 else (0, 1, 2, 3)
            family = "ARGB" if i % 2 == 0 else "PWM"
            plate(
                "polymer",
                f"{row} {family} socket {i // 2 + 1}",
                rectangle(u - 5.3, edge - 2.1, u + 5.3, edge + 2.1, 0.45),
                97.2,
                2.8,
                edge=0.12,
            )
            for j in offsets:
                x = u + (j - 1.5) * 2.4
                y0, y1 = sorted((edge + 1.9 * sign, edge + 6.7 * sign))
                plate(
                    "contact",
                    f"{row} {family} contact {i} {j}",
                    rectangle(x - 0.27, y0, x + 0.27, y1, 0.13),
                    95.9,
                    0.52,
                )
    for i, (u, v, sign, count) in enumerate(
        ((left, 608, -1, 3), (left, 627, -1, 3), (right, 611, 1, 4), (right, 628, 1, 3))
    ):
        plate(
            "polymer",
            f"Controller side header {i + 1}",
            rectangle(u - 1.6, v - 4.9, u + 1.6, v + 4.9, 0.4),
            97.1,
            2.6,
            edge=0.15,
        )
        for pin in (0, 1, 3) if count == 3 else (0, 1, 2, 3):
            y = v + (pin - 1.5) * 2.3
            u0, u1 = sorted((u + 1.35 * sign, u + 5.1 * sign))
            plate(
                "contact",
                f"Side header pin {i} {pin}",
                rectangle(u0, y - 0.23, u1, y + 0.23, 0.1),
                95.9,
                0.52,
            )
    for i, u in enumerate((750, 764)):
        plate(
            "polymer",
            f"Electrolytic capacitor {i}",
            circle(u, 601, 3.9),
            101.5,
            6.9,
            edge=0.24,
        )
        plate(
            "contact",
            f"Capacitor scored end {i}",
            circle(u, 601, 2.95),
            101.6,
            0.20,
            edge=0.08,
        )
        plate(
            "contact",
            f"Solder lands for controller fuse {i}",
            rectangle(u - 1.7, 607, u + 1.7, 613.1, 0.3),
            95.1,
            0.60,
        )
        plate(
            "polymer",
            f"Controller resettable fuse {i}",
            rectangle(u - 1.3, 608.1, u + 1.3, 612.1, 0.2),
            96.0,
            1.0,
        )
    for i, contour in enumerate(ROG_FOIL):
        plate(
            "contact",
            f"Controller gold ROG foil {i + 1}",
            [(693 + u * 0.95, 611 + v * 0.88) for u, v in contour],
            94.69,
            0.04,
        )
    for index, u in enumerate((674, 703, 733)):
        knots = [
            (574 + index * 3, 642, 97),
            (584 + index * 3, 601, 98.2),
            (610 + index * 4, 568, 98.2),
            (643 + index * 5, 558 - index * 2, 99.2),
            (u - 9, 562 - index * 2, 99),
            (u, 575, 97.9),
            (u, 584, 96.6),
        ]
        parts["wire"].append(
            cable(shell, f"Fan lead to controller {index + 1}", knots, 1.00)
        )


def build(shell, sheet):
    parts = {key: [] for key in ("steel", "polymer", "wire", "contact", "print")}

    def plate(finish, name, contour, depth, thickness, holes=(), edge=0):
        obj = sheet(
            name,
            contour,
            list(holes),
            lambda u, v, d: position(u, v, depth + d),
            thickness,
            edge,
        )
        parts[finish].append(obj)
        return obj

    mounting_plates(plate)
    harness(shell, plate, parts)
    hub(plate, shell, parts)
    return parts
