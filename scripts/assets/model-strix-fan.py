import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product


def impeller(part):
    segments, sections = 16, 8
    for blade in range(7):
        pts, faces, coords = [], [], []
        for side in (0, 1):
            for row in range(segments + 1):
                t = row / segments
                for col in range(sections + 1):
                    u = col / sections
                    narrow = (abs(u - 0.5) * 2) ** 2
                    r = 20.4 + 42.7 * t - 2.5 * narrow * t**8
                    sweep = blade * math.tau / 7 + 0.75 * (1 - t) ** 1.55
                    chord = 0.765 - 0.42 * t + 0.218 * math.sin(math.pi * t)
                    theta = sweep + (u - 0.5) * chord
                    z = (
                        4.6
                        + (u - 0.5) * (9.2 + 4.4 * t)
                        + 1.7 * math.sin(u * math.pi)
                        - side * 0.80
                    )
                    pts.append(
                        (
                            r * 0.001 * math.cos(theta),
                            r * 0.001 * math.sin(theta),
                            z * 0.001,
                        )
                    )
                    coords.append((t, u))
            start = side * (segments + 1) * (sections + 1)
            for row in range(segments):
                for col in range(sections):
                    a = start + row * (sections + 1) + col
                    vertices = [a, a + sections + 1, a + sections + 2, a + 1]
                    faces.append(tuple(reversed(vertices)) if side else vertices)
        rear = (segments + 1) * (sections + 1)
        for row in range(segments):
            for col in (0, sections):
                a, b = row * (sections + 1) + col, (row + 1) * (sections + 1) + col
                faces.append(
                    (a, a + rear, b + rear, b)
                    if col == 0
                    else (a, b, b + rear, a + rear)
                )
        obj = part.surface(
            "Forward-swept moulded light guide", "opal", pts, faces, True
        )
        uv = obj.data.uv_layers.active
        for face in obj.data.polygons:
            for index in face.loop_indices:
                uv.uv[index].vector = coords[obj.data.loops[index].vertex_index]
    rings = [
        (62.4, -2.2),
        (63.8, -2.2),
        (64.1, -1.8),
        (64.1, 7.1),
        (63.9, 7.5),
        (63.05, 7.6),
        (62.75, 7.3),
        (62.75, -1.9),
        (62.4, -2.2),
    ]
    pts = [
        (
            r * math.cos(i * math.tau / 96) / 1000,
            r * math.sin(i * math.tau / 96) / 1000,
            z / 1000,
        )
        for r, z in rings
        for i in range(96)
    ]
    faces = [
        (
            j * 96 + i,
            j * 96 + (i + 1) % 96,
            (j + 1) * 96 + (i + 1) % 96,
            (j + 1) * 96 + i,
        )
        for j in range(len(rings) - 1)
        for i in range(96)
    ]
    rim = part.surface(
        "Continuous axial blade-tip barrier ring", "opal", pts, faces, True
    )
    for item in rim.data.uv_layers.active.uv:
        item.vector = (0.86, 0.55)
    part.rod(
        "Co-moulded central carrier",
        "white",
        (0, 0, -0.001),
        (0, 0, 0.008),
        0.021,
        0.0213,
        72,
    )
    part.rod(
        "Dark manufacturer badge",
        "graphite",
        (0, 0, 0.008),
        (0, 0, 0.00875),
        0.0186,
        0.0183,
        72,
    )


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    product = Product("strix-fan")
    impeller(product)
    project = Path(__file__).resolve().parents[2]
    product.export(project / "public/media/models")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(project / ".review/atelier/strix-140-argb.blend")
    )
