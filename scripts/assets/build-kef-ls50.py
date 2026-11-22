import argparse
import math
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import export_batch, xyz
from kef_rear import RearAssembly, cooling, io_panel

TAU = math.tau
parts = {}
palette = {
    "cabinet": ("Carbon Black painted cabinet", (0.039, 0.043, 0.044), 0.10, 0.40),
    "baffle": ("Satin charcoal composite baffle", (0.044, 0.047, 0.047), 0.12, 0.47),
    "trim": ("Precision mounting ring", (0.029, 0.032, 0.032), 0.20, 0.44),
    "rubber": ("Z-Flex elastomer suspension", (0.018, 0.016, 0.017), 0, 0.49),
    "shadow": ("Driver gap and optical receiver", (0.008, 0.009, 0.009), 0.05, 0.52),
    "cone": ("Copper finished aluminium-magnesium", (0.49, 0.209, 0.103), 0.76, 0.36),
    "guide": ("Tangerine waveguide petals", (0.46, 0.184, 0.084), 0.78, 0.31),
    "glass": ("Flush smoke glass", (0.012, 0.015, 0.016), 0.22, 0.14),
}

rear_finishes = {
    "alloy": ("Satin black amplifier chassis", (0.034, 0.036, 0.037), 0.5, 0.45),
    "heatsink": (
        "Graphite anodised aluminium extrusion",
        (0.085, 0.088, 0.091),
        0.72,
        0.37,
    ),
    "lining": ("Acoustic foam and socket interiors", (0.012, 0.011, 0.012), 0.03, 0.84),
    "copper": ("Copper-coloured port moulding", (0.39, 0.145, 0.068), 0.35, 0.45),
    "metal": ("Nickel-plated sockets", (0.48, 0.51, 0.52), 0.84, 0.38),
    "contact": ("Connector contacts", (0.53, 0.32, 0.092), 0.77, 0.35),
}


def build_mesh(name, key, points, faces, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(p) for p in points], [], faces)
    data.update()
    if key in ("cone", "guide"):
        uv = data.uv_layers.new(name="Driver face")
        for loop in data.loops:
            x, y, _ = points[loop.vertex_index]
            uv.uv[loop.index].vector = (0.5 + x / 96, 0.5 + y / 96)
    if key.endswith(("-copper", "-lining")):
        uv = data.uv_layers.new(name="Cavity depth")
        for loop in data.loops:
            _, _, z = points[loop.vertex_index]
            uv.uv[loop.index].vector = (max(0, min(1, (-z - 92) / 66)), 0.5)
    item = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(item)
    material_name, color, metallic, roughness = (
        palette[key] if key in palette else rear_finishes[key.split("-")[-1]]
    )
    material = bpy.data.materials.get(material_name)
    if not material:
        material = bpy.data.materials.new(material_name)
        material.diffuse_color = (*color, 1)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    data.materials.append(material)
    for poly in data.polygons:
        poly.use_smooth = smooth
    parts.setdefault(key, []).append(item)
    item["kefSurface"] = key
    return item


def skin(name, key, loops, flip=False, skip=None):
    count = len(loops[0])
    faces = []
    for row in range(len(loops) - 1):
        for i in range(count):
            j = (i + 1) % count
            if skip and skip(row, loops[row][i], loops[row][j]):
                continue
            face = (
                row * count + i,
                row * count + j,
                (row + 1) * count + j,
                (row + 1) * count + i,
            )
            faces.append(face[::-1] if flip else face)
    return build_mesh(name, key, [p for ring in loops for p in ring], faces)


def rectangle(w, h, r, corner_steps=9, edge_steps=8):
    points = []
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
        cx, cy = sx * (w - r), sy * (h - r)
        first = i * math.pi / 2
        for j in range(corner_steps + 1):
            a = first + j * math.pi / (2 * corner_steps)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        x0, y0 = points[-1]
        nx, ny = [(-1, 1), (-1, -1), (1, -1), (1, 1)][i]
        x1 = nx * (w - r) + r * math.cos(first + math.pi / 2)
        y1 = ny * (h - r) + r * math.sin(first + math.pi / 2)
        for j in range(1, edge_steps):
            t = j / edge_steps
            points.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return points


def circle(r, z, n, center=(0, 0)):
    return [
        (
            center[0] + r * math.cos(TAU * i / n),
            center[1] + r * math.sin(TAU * i / n),
            z,
        )
        for i in range(n)
    ]


def lathe(name, key, profile, n=108, center=(0, 0)):
    return skin(name, key, [circle(r, z, n, center) for r, z in profile], flip=True)


def cabinet():
    profile = rectangle(100, 150, 20, 12, 12)

    def seam(y):
        return 126 - 31 * (y / 150) ** 2

    def endcap(x, y):
        return 154.5 - 27 * (y / 150) ** 2 - 6 * (x / 100) ** 4

    layers = []
    for inset, depth in [
        (3, -150),
        (1.4, -149.7),
        (0.4, -149),
        (0, -147.5),
        (0, None),
        (0.24, None),
    ]:
        layers.append(
            [
                (
                    x * (1 - inset / 100),
                    y * (1 - inset / 150),
                    (seam(y) - (0.9 if inset == 0 else 0.66))
                    if depth is None
                    else depth,
                )
                for x, y in profile
            ]
        )
    skin(
        "Rounded cabinet walls with recessed control-panel opening",
        "cabinet",
        layers,
        skip=lambda i, a, b: i == 3 and min(a[1], b[1]) > 149.999,
    )
    outer = [(x, y, seam(y) - 0.66) for x, y in profile]
    inner = [(x * 0.9983, y * 0.9988, seam(y) - 0.14) for x, y in profile]
    skin("Baffle perimeter joint", "shadow", [outer, inner])
    edge_rows = []
    for inset, t in [
        (0.16, 0),
        (0, 0.04),
        (0, 0.45),
        (0, 0.83),
        (0.1, 0.93),
        (0.45, 0.975),
        (1, 0.993),
        (1.8, 1),
    ]:
        edge_rows.append(
            [
                (
                    x * (1 - inset / 100),
                    y * (1 - inset / 150),
                    seam(y) + (endcap(x, y) - seam(y)) * t,
                )
                for x, y in profile
            ]
        )
    skin("Return around the sculpted baffle shoulders", "baffle", edge_rows)
    rings = []
    for t in [0, 0.045, 0.12, 0.25, 0.45, 0.65, 0.82, 0.94, 0.98, 1]:
        row = []
        for (x, y), edge in zip(profile, edge_rows[-1]):
            a = math.atan2(y, x)
            px = (1 - t) * 75.2 * math.cos(a) + t * edge[0]
            py = (1 - t) * 75.2 * math.sin(a) + t * edge[1]
            z = (
                (1 - t**1.72) * 154.8
                + t**1.72 * edge[2]
                + 0.9 * math.sin(math.pi * t) ** 2
            )
            row.append((px, py, z))
        rings.append(row)
    skin("Continuous compound front face", "baffle", rings, True)
    control_top()


def control_top():
    opening = rectangle(58.6, 12.3, 3.6, 5, 6)
    inner = [(x, 51 + z) for x, z in opening]
    angles = sorted(
        set(math.atan2(z - 51, x) for x, z in inner)
        | set(
            math.atan2(z - 51, x)
            for x, z in [(-80, -147.5), (80, -147.5), (80, 94.1), (-80, 94.1)]
        )
    )

    def intersect(a, polygon):
        dx, dz = math.cos(a), math.sin(a)
        for i, (x, z) in enumerate(polygon):
            u, v = polygon[(i + 1) % len(polygon)]
            ex, ez = u - x, v - z
            det = dx * ez - dz * ex
            if abs(det) < 1e-10:
                continue
            t = (x * ez - (z - 51) * ex) / det
            s = (x * dz - (z - 51) * dx) / det
            if t > 0 and -0.000001 <= s <= 1.000001:
                return (t * dx, 150, 51 + t * dz)
        raise ValueError("Incomplete control panel edge")

    outer = [(-80, -147.5), (80, -147.5), (80, 94.1), (-80, 94.1)]
    ring = [intersect(a, inner) for a in angles]
    skin(
        "Flat cabinet top cut for the touch glass",
        "cabinet",
        [ring, [intersect(a, outer) for a in angles]],
    )
    glass_edge = [(0.994 * x, 149.94, 51 + (z - 51) * 0.982) for x, _, z in ring]
    skin("Control glass perimeter gasket", "shadow", [ring, glass_edge], True)
    pts = [*glass_edge, (0, 149.94, 51)]
    n = len(ring)
    build_mesh(
        "Recessed smoked touch glass",
        "glass",
        pts,
        [(n, (i + 1) % n, i) for i in range(n)],
        False,
    )


def driver():
    lathe(
        "Recess around the driver trim",
        "shadow",
        [(73, 153.6), (74.7, 153.6), (75.22, 154.82)],
    )
    lathe(
        "Contoured mounting flange",
        "trim",
        [
            (60.6, 152.8),
            (61.2, 154.0),
            (61.8, 154.75),
            (63, 155.15),
            (69, 155.45),
            (73.7, 155.06),
            (74.65, 154.65),
            (74.85, 154.05),
        ],
    )
    lathe(
        "Recessed infrared sensor",
        "shadow",
        [(0.01, 155.59), (2.7, 155.59), (3.35, 155.49), (3.58, 155.1)],
        32,
        (0, -68.4),
    )
    suspension = []
    for t in [0, 0.055, 0.13, 0.26, 0.39, 0.53, 0.68, 0.82, 0.93, 1]:
        row = []
        for i in range(288):
            a = TAU * i / 288
            r = 47.35 + 13.95 * t
            fold = (0.5 + 0.5 * math.cos(36 * a - 2.2 * t)) ** 4.4
            hump = math.sin(math.pi * t) ** 0.84
            z = 152.6 + 0.32 * t + hump * (2.85 - 2.4 * fold)
            row.append((r * math.cos(a), r * math.sin(a), z))
        suspension.append(row)
    skin("Thirty-six pleated Z-Flex suspension sectors", "rubber", suspension, True)
    lathe(
        "Copper cone outer rolled rim",
        "cone",
        [(46.65, 152.65), (47.3, 153.02), (47.7, 152.8), (47.85, 152.45)],
    )
    cone = []
    for t in [0, 0.035, 0.12, 0.27, 0.44, 0.62, 0.8, 0.95, 1]:
        r = 24.65 + 22.65 * t
        cone.append(circle(r, 140.35 + 12.59 * t**1.15, 108))
    skin("Deep magnesium aluminium cone", "cone", cone, True)
    for k in range(9):
        points = []
        for i in range(9):
            t = i / 8
            r = 28.0 + 17.2 * t
            w = (math.sin(math.pi * t) ** 0.75 * 0.85 + 0.05) * (1 - 0.33 * t)
            y = 140.35 + 12.59 * ((r - 24.65) / 22.65) ** 1.15
            a = math.pi / 2 + TAU * k / 9
            for s in [-1, -0.28, 0.16, 1]:
                dx = w * s
                crown = max(0, 1 - abs(s)) * 0.83 * math.sin(math.pi * t) ** 0.7
                points.append(
                    (
                        r * math.cos(a) - dx * math.sin(a),
                        r * math.sin(a) + dx * math.cos(a),
                        y + crown + 0.04,
                    )
                )
        faces = [
            (i * 4 + j, (i + 1) * 4 + j, (i + 1) * 4 + j + 1, i * 4 + j + 1)
            for i in range(8)
            for j in range(3)
        ]
        build_mesh("Raised radial cone stiffener %02d" % (k + 1), "cone", points, faces)
    lathe(
        "Floating tweeter annular clearance",
        "shadow",
        [(23.85, 139.95), (24.3, 140.12), (24.72, 140.39)],
    )
    lathe(
        "Continuous tweeter waveguide throat",
        "cone",
        [
            (12.25, 132.7),
            (13.0, 133.0),
            (14.0, 133.7),
            (17.0, 135.5),
            (20.8, 138.0),
            (24.17, 140.20),
            (24.34, 140.12),
        ],
    )
    lathe(
        "Shadow behind the waveguide",
        "shadow",
        [(0.01, 132.5), (12.6, 132.5), (13.3, 133.2)],
    )
    lathe(
        "Vented aluminium dome",
        "guide",
        [
            (0.03, 138.7),
            (3.4, 138.48),
            (6.1, 137.94),
            (9.1, 136.8),
            (11.0, 135.5),
            (12.45, 133.4),
        ],
        72,
    )
    for k in range(9):
        loops = []
        for t in [0.014, 0.09, 0.23, 0.4, 0.59, 0.76, 0.9, 1]:
            angle = math.pi / 2 + k * TAU / 9
            spread = (0.1 + 0.9 * t) ** 0.68
            radius = 0.1 + 17.7 * t
            tip = 147.35 - 2.0 * t - 3.4 * t * t
            root = 138.85 - 6.35 * t
            curve = -0.105 * math.sin(math.pi * t)
            points = []
            for f, h, rscale in [
                (-0.035, 0, 0.70),
                (-0.018, 0.62, 0.88),
                (0.01, 1, 1),
                (0.055, 0.87, 0.946),
                (0.265, 0.43, 0.79),
                (0.445, 0.13, 0.68),
                (0.45, 0, 0.66),
            ]:
                a = angle + curve + f * spread
                r = radius * rscale
                points.append(
                    (r * math.cos(a), r * math.sin(a), root + (tip - root) * h)
                )
            loops.append(points)
        skin("Folded Tangerine waveguide vane %02d" % (k + 1), "guide", loops, True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path)
    parser.add_argument("--out", type=Path, default=Path("public/media/models/kef"))
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cabinet()
    driver()
    cooling(RearAssembly(build_mesh, "rear"))
    for variant in ("primary", "secondary"):
        collection = bpy.data.collections.new(variant.title() + " amplifier panel")
        bpy.context.scene.collection.children.link(collection)
        io_panel(RearAssembly(build_mesh, variant), variant == "primary")
        for key, objects in parts.items():
            if key.startswith(variant + "-"):
                for obj in objects:
                    collection.objects.link(obj)
                    bpy.context.scene.collection.objects.unlink(obj)
    bpy.context.view_layer.update()
    for name, objects in parts.items():
        print(name, export_batch(name, objects, args.out / (name + ".mesh")))
    if args.blend:
        for objects in parts.values():
            for obj in objects:
                if obj.get("speakerPart") == "secondary":
                    obj.hide_set(True)
                    obj.hide_render = True
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))


if __name__ == "__main__":
    main()
