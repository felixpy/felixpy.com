import json
from pathlib import Path
import runpy

from mathutils import Vector
from blender_parts import block

assets = Path(__file__).resolve().parent
letters = runpy.run_path(str(assets / "vitrine-sculpt.py"))["letters"]
signature = json.loads((assets / "samsung-870-wordmark.json").read_text())


def wiring(shell, name, route, width, thickness):
    nodes = [Vector(p) for p in route]
    path = []
    for i, a in enumerate(nodes[:-1]):
        b = nodes[i + 1]
        length = (b - a).length
        m = (b - nodes[max(0, i - 1)]).normalized() * length
        n = (nodes[min(i + 2, len(nodes) - 1)] - a).normalized() * length
        for t in (0, 0.25, 0.5, 0.75):
            path.append(
                (1 + 2 * t) * (1 - t) ** 2 * a
                + t * (1 - t) ** 2 * m
                + t * t * (3 - 2 * t) * b
                - t * t * (1 - t) * n
            )
    path.append(nodes[-1])
    w, h = width / 2, thickness / 2
    r = min(0.38, h * 0.55)
    profile = [
        (-w + r, h),
        (w - r, h),
        (w, h - r),
        (w, -h + r),
        (w - r, -h),
        (-w + r, -h),
        (-w, -h + r),
        (-w, h - r),
    ]
    vertices, faces = [], []
    for index, point in enumerate(path):
        tangent = (
            path[min(index + 1, len(path) - 1)] - path[max(index - 1, 0)]
        ).normalized()
        across = Vector((1, 0, 0)).cross(tangent)
        if across.length_squared < 0.00001:
            across = Vector((0, 0, 1)).cross(tangent)
        across.normalize()
        depth = tangent.cross(across)
        vertices.extend(tuple(point + across * s + depth * d) for s, d in profile)
        if index:
            prev = (index - 1) * 8
            for j in range(8):
                k = (j + 1) % 8
                faces.append((prev + j, prev + k, prev + k + 8, prev + j + 8))
    faces.extend(
        [tuple(range(7, -1, -1)), tuple(range(len(vertices) - 8, len(vertices)))]
    )
    return shell(name, vertices, faces)


def build(shell, sheet, parts):
    def solid(key, name, dims, center, radius=0.4):
        obj = block(name, dims, center, radius)
        parts[key].append(obj)
        return obj

    def stamping(name, path, surface):
        parts["print"].append(sheet(name, path, [], surface, 0.045))

    def cable(name, route, width, thick):
        parts["wire"].append(wiring(shell, name, route, width, thick))

    y = 262 - (423 - 122) * 0.974
    end = y - 50
    for i, sled in enumerate((666, 746)):
        z = 193 - (sled - 267) * 0.907
        drive = f"Samsung SSD 870 EVO · sled {i + 1}"
        solid(
            "polymer",
            drive + " · folded underside",
            (1.02, 99.7, 69.5),
            (96.18, y, z),
            0.45,
        )
        solid(
            "drive",
            drive + " · anodised aluminium cover",
            (5.90, 100, 69.85),
            (99.52, y, z),
            0.8,
        )

        def front(u, v, depth):
            return (102.50 + depth, y - u, z - v)

        for index, outline in enumerate(signature):
            stamping(drive + f" · transfer {index + 1}", outline, front)
        points, faces = letters("Solid State Drive", False)
        scale = 26 / (max(p[0] for p in points) - min(p[0] for p in points))
        parts["print"].append(
            shell(
                drive + " · product line",
                [front(a * scale, b * scale - 6.3, 0) for a, b in points],
                faces,
            )
        )
        stamping(
            drive + " · silver square",
            [(a, b - 28) for a, b in [(-5, -5), (5, -5), (5, 5), (-5, 5)]],
            front,
        )
        stamping(
            drive + " · connector direction",
            [(44.6, -1.5), (46.3, 0), (44.6, 1.5)],
            front,
        )

        for data, width, offset in ((True, 14.0, -20.3), (False, 23.2, 1.4)):
            kind = "7-pin data" if data else "15-pin power"
            c = z + offset
            solid(
                "polymer",
                drive + " · keyed " + kind + " socket",
                (4.25, 2.0, width + 1.2),
                (99.1, end - 0.5, c),
                0.32,
            )
            solid(
                "wire",
                drive + " · " + kind + " plug",
                (5.55, 10.1, width),
                (99.2, end - 5.9, c),
                0.65,
            )
            solid(
                "polymer",
                drive + " · " + kind + " strain relief",
                (4.15, 4.6, width - 1.0),
                (99.2, end - 11.5, c),
                0.6,
            )
            if data:
                solid(
                    "print",
                    drive + " · steel latch",
                    (0.45, 6.6, 5.4),
                    (102.10, end - 6.1, c),
                    0.25,
                )
                terminal_y = -6 - i * 14
                passage_z = -37.45 - i * 128
                route = [
                    (99.2, end - 13.4, c),
                    (99.4, end - 21, c),
                    (111.5, end - 32 - i * 5, c + 8),
                    (112.5, -127 - i * 4, c + 36),
                    (104 + i * 3, -129.8, passage_z - 14),
                    (98, -128.2, passage_z - 1),
                    (93, -128.2, passage_z),
                    (78, -128.2, passage_z),
                    (68, -127.2, passage_z + 2),
                    (64 - i * 2, -119, passage_z + 10),
                    (71.2 - 8 * i, -99, -43 - i * 4),
                    (71.2 - 8 * i, -68, -14 - i * 18),
                    (71.2 - 6 * i, terminal_y - 13, -6 - i * 10),
                    (71.2, terminal_y, -27.0),
                    (71.2, terminal_y, -34.8),
                ]
                cable(drive + " · slim SATA data cable", route, 3.4, 2.8)
                solid(
                    "polymer",
                    drive + " · motherboard SATA plug",
                    (5.75, 13.3, 12.1),
                    (71.2, terminal_y, -39.9),
                    0.64,
                )
                solid(
                    "wire",
                    drive + " · motherboard strain relief",
                    (4.9, 9.7, 3.2),
                    (71.2, terminal_y, -34.1),
                    0.47,
                )
                continue
            socket_x = -58 + 20 * i
            socket_y = -240.5
            route = [
                (99.2, end - 13.4, c),
                (99.2, end - 25, c - 4 + 4 * i),
                (103 + i * 3, -145, c - 16 + 24 * i),
                (104 + i * 2, -185 - i * 13, -145 - i * 38),
                (102, -222 - i * 15, -113 - i * 20),
                (98, -233 - i * 13, -88 - i * 10),
                (79, -233 - i * 13, -71 - i * 9),
                (34, -230 - i * 19, -50 - i * 13),
                (socket_x + 13, socket_y + 7 - i * 15, -49 - i * 11),
                (socket_x, socket_y, -64.5),
                (socket_x, socket_y, -73),
            ]
            cable(drive + " · sleeved SATA supply", route, 6.8, 5.3)
            solid(
                "wire",
                drive + " · five-way heat shrink",
                (8.5, 11, 6.3),
                (socket_x, socket_y, -73.9),
                1.1,
            )
            for strand in range(5):
                tip_x = socket_x + ((strand % 2) - 0.5) * 3.9
                tip_y = socket_y + (strand // 2 - 1) * 3.9
                route = [
                    (
                        socket_x + (tip_x - socket_x) * 0.8,
                        socket_y + (tip_y - socket_y) * 0.8,
                        -76.6,
                    ),
                    (tip_x, tip_y, -84),
                    (tip_x, tip_y, -90.3),
                ]
                cable(drive + f" · SATA supply wire {strand + 1}", route, 1.75, 1.75)
            solid(
                "polymer",
                drive + " · PSU peripheral six-way plug",
                (9.1, 12.9, 13.2),
                (socket_x, socket_y, -95.9),
                0.55,
            )
            solid(
                "wire",
                drive + " · PSU peripheral latch",
                (1.45, 5.9, 7.4),
                (socket_x + 4.65, socket_y, -94.65),
                0.32,
            )

    for pins, x, y in ((18, -58, -215), (10, -40, -208)):
        height = (pins // 2 - 1) * 3.9 + 5.1
        solid(
            "polymer",
            f"Motherboard harness · {pins}-way PSU plug",
            (9.4, height, 13.3),
            (x, y, -95.85),
            0.6,
        )
        solid(
            "wire",
            f"Motherboard harness · {pins}-way locking catch",
            (1.48, 6.6, 8.3),
            (x + 4.8, y, -95.3),
            0.28,
        )
