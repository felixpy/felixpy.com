import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product, finishes


def model_aj_floor(output):
    unit = Product("aj-floor")
    finishes["polish"] = ("d8dcdd", 0.097, 1.0)
    finishes["porcelain"] = ("eeebe4", 0.52, 0.0)
    finishes["lining"] = ("f1eee8", 0.40, 0.05)
    n = 96
    angles = [math.tau * i / n for i in range(n)]

    def shell(name, material, rings, inward=False):
        vertices = [tuple(value / 1000 for value in p) for ring in rings for p in ring]
        faces = []
        count = len(rings[0])
        for j in range(len(rings) - 1):
            for i in range(count):
                k = (i + 1) % count
                face = (
                    j * count + i,
                    j * count + k,
                    (j + 1) * count + k,
                    (j + 1) * count + i,
                )
                faces.append(tuple(reversed(face)) if inward else face)
        return unit.surface(name, material, vertices, faces, True)

    def rim(inner, inset, level):
        row = []
        for angle in angles:
            c, s = math.cos(angle), math.sin(angle)
            if inner:
                x, z = 49 + (76.5 + inset) * c, (72.4 + inset) * s
            else:
                x = (137.5 - inset) * c
                z = (87.9 - inset) * s * (1 + 0.154 * c)
            height = 19.1 - 0.082 * x
            h = 2.0 + level if level >= 0 else height + level + 1.0
            row.append((x, h, z))
        return row

    shell(
        "Cast steel shoe · inclining crown and pierced toe",
        "polish",
        [
            rim(False, 2.2, 0),
            rim(False, 0.6, 0.6),
            rim(False, 0, 1.5),
            rim(False, 0, -3.0),
            rim(False, 0.5, -1.6),
            rim(False, 1.65, -1),
            rim(True, 1.35, -1),
            rim(True, 0.35, -1.4),
            rim(True, 0, -2.4),
            rim(True, 0, 1.15),
            rim(True, 0.65, 0.20),
            rim(True, 1.5, 0),
            rim(False, 2.2, 0),
        ],
        inward=True,
    )
    sole_outer = [(x, 0, z) for x, _, z in rim(False, 3.9, 0)]
    sole_inner = [(x, 0, z) for x, _, z in rim(True, 2.3, 0)]
    shell(
        "Recessed non-marking annular sole",
        "black",
        [
            [(x, 2.1, z) for x, _, z in sole_outer],
            sole_outer,
            sole_inner,
            [(x, 2.1, z) for x, _, z in sole_inner],
        ],
    )

    def tube(name, material, a, b, radius, radius_end=None, sides=48):
        unit.rod(
            name,
            material,
            [v / 1000 for v in a],
            [v / 1000 for v in b],
            radius / 1000,
            None if radius_end is None else radius_end / 1000,
            sides,
        )

    foot = Vector((-106.5, 26.8, 0))
    pivot = Vector((-3.5, 1201, 0))
    upright = (pivot - foot).normalized()
    tube("Foot ferrule", "polish", foot - upright, foot + upright * 4.6, 6.15, 5.7)
    tube("Inclined stainless stem", "polish", foot + upright * 1.8, pivot, 4.8)
    tube(
        "Socket swivel neck",
        "polish",
        pivot - upright * 11.2,
        pivot + upright * 0.8,
        5.65,
    )
    tube("Inboard trunnion", "steel", (-3.0, 1201, -12), (-3.0, 1201, 12), 6.1)

    axis = Vector((1, -1, 0)).normalized()
    radial = Vector((1, 1, 0)).normalized()
    tail = Vector((-57, 1284.0, 0))
    shoulder = tail + axis * 146.0
    mouth = Vector((110.0, 1067.0, 0))

    def round_ring(center, r):
        return [
            center + r * (radial * math.cos(a) + Vector((0, 0, math.sin(a))))
            for a in angles
        ]

    def lip(height, rx, rz):
        return [(mouth.x + rx * math.cos(a), height, rz * math.sin(a)) for a in angles]

    start = round_ring(shoulder, 22.5)
    end = [Vector(p) for p in lip(mouth.y + 1.0, 79.5, 72.5)]
    shell(
        "Spun AJ shade · offset flared horn",
        "polish",
        [
            round_ring(tail + axis * 0.7, 21.9),
            round_ring(tail + axis * 1.25, 22.4),
            round_ring(tail + axis * 2.3, 22.5),
            round_ring(shoulder - axis * 1.8, 22.5),
            start,
            [p.lerp(q, 0.022) for p, q in zip(start, end)],
            [p.lerp(q, 0.975) for p, q in zip(start, end)],
            end,
            lip(mouth.y + 0.24, 79.2, 72.22),
            lip(mouth.y, 78.67, 71.65),
            lip(mouth.y + 0.20, 78.23, 71.23),
        ],
    )
    shell(
        "White lacquer · reflector interior",
        "lining",
        [
            lip(mouth.y + 0.18, 78.24, 71.24),
            lip(mouth.y + 0.85, 78.15, 71.13),
            round_ring(shoulder, 21.45),
            round_ring(shoulder - axis * 21, 21.4),
            round_ring(shoulder - axis * 22, 12.45),
        ],
    )
    shell(
        "Hairline rear closure",
        "steel",
        [
            round_ring(tail, 20.55),
            round_ring(tail + axis * 0.8, 21.9),
        ],
    )
    shell(
        "Pressed rear end cap",
        "polish",
        [
            round_ring(tail + axis * 0.18, 0.01),
            round_ring(tail + axis * 0.18, 19.8),
            round_ring(tail, 20.55),
        ],
    )
    socket = shoulder - axis * 8
    tube(
        "E27 porcelain socket", "porcelain", socket - axis * 24, socket + axis * 5, 15.2
    )
    for step in range(4):
        a = socket + axis * (3.7 + step * 2.6)
        tube("Nickel Edison base", "steel", a, a + axis * 1.9, 12.75)
    profile = [
        (11, 10.5),
        (15, 12.4),
        (20, 13.3),
        (28, 15.5),
        (35, 18.7),
        (43, 21.1),
        (50, 21.8),
        (58, 20.6),
        (64, 17.3),
        (69, 12.3),
        (72, 7.6),
        (73.4, 0.3),
    ]
    shell(
        "Opaline A45 lamp",
        "opal",
        [round_ring(socket + axis * pos, r) for pos, r in profile],
    )
    unit.export(output)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model_aj_floor(root / "public/media/models/fixtures")
    bpy.ops.wm.save_as_mainfile(filepath=str(root / ".review/atelier/aj-floor.blend"))
