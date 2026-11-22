import math
import runpy
from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
TOOLS = runpy.run_path(str(HERE / "model-gr701-fascia.py"))
ROOT, PRODUCT = TOOLS["ROOT"], TOOLS["PRODUCT"]
sheet, shell = TOOLS["sheet"], TOOLS["shell"]
from blender_parts import block, export_batch, xyz

COLLECTION = "GR701 · front I/O module"
SOURCE = PRODUCT / "Blender/gr701-front-io.blend"
FINISHES = {
    "cover": ("Moulded graphite top housing", "45474b", 0.30, 0.51),
    "well": ("Black receptacle insulator", "15171a", 0.10, 0.62),
    "contact": ("Nickel plated shells and contacts", "aaaeb3", 0.85, 0.28),
    "key": ("Bead-textured ABS keycap", "393a3f", 0.21, 0.42),
    "print": ("Silver-grey pad printing", "adaeb1", 0.20, 0.54),
}


def rectangle(x, z, width, length, radius):
    points = []
    segments = 3 if radius < 1 else 5
    for a in range(4):
        u, v = [(1, 1), (-1, 1), (-1, -1), (1, -1)][a]
        for j in range(segments + 1):
            angle = math.pi * 0.5 * (a + j / segments)
            points.append(
                (
                    x + u * (width / 2 - radius) + radius * math.cos(angle),
                    z + v * (length / 2 - radius) + radius * math.sin(angle),
                )
            )
    return points


def circle(x, z, r):
    return [
        (x + r * math.cos(i * math.tau / 40), z + r * math.sin(i * math.tau / 40))
        for i in range(40)
    ]


def flat(name, boundary, openings, top, thickness, edge=0):
    return sheet(
        name, boundary, openings, lambda x, z, d: (x, top + d, z), thickness, edge
    )


def text(name, message, x, z, size):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body, curve.size, curve.resolution_u = message, size * 0.001, 2
    curve.align_x, curve.align_y = "CENTER", "CENTER"
    curve.space_character = 1.05
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = xyz((x, 8.45, z))
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return obj


def arc(x, z, r, t, a, b, count=24):
    return [
        (
            x + rr * math.cos(a + (b - a) * i / count),
            z + rr * math.sin(a + (b - a) * i / count),
        )
        for rr, indices in [(r, range(count + 1)), (r - t, reversed(range(count + 1)))]
        for i in indices
    ]


def build():
    parts = {k: [] for k in FINISHES}
    apertures = []
    top = 8.40
    outside = [(-53, -30), (53, -30), (59.3, 30), (-59.3, 30)]
    openings = parts["well"]

    def receptacle(name, outer, inner):
        apertures.append(outer)
        parts["contact"].append(
            flat(
                name + " · rolled mouth",
                outer,
                [inner],
                top - 0.15,
                0.52,
                0.06,
            )
        )
        openings.append(
            flat(name + " · inner socket sleeve", outer, [inner], top - 0.68, 4.99)
        )
        openings.append(flat(name + " · blind back", inner, [], top - 5.72, 1))

    def button(name, outline, cap, back):
        apertures.append(outline)
        openings.append(
            flat(name + " · separate switch pocket", outline, [], top - 0.85, 0.7)
        )
        parts["key"].append(flat(name, cap, [], back, 0.8, 0.18))

    power = [(-15.7, -26), (15.7, -26), (10.9, -16), (-10.9, -16)]
    cap = [(-14.6, -25.5), (14.6, -25.5), (10.35, -16.8), (-10.35, -16.8)]
    button("Bevelled trapezoidal power key", power, cap, 8.93)
    parts["print"].append(
        flat(
            "Power · open circle",
            arc(0, -21.2, 1.78, 0.32, -1.03, 4.17),
            [],
            9.0,
            0.035,
        )
    )
    parts["print"].append(
        block("Power · vertical stroke", (0.31, 0.035, 1.7), (0, 8.985, -22.4))
    )
    for i, x in enumerate([-43.4, -20.5, 20.5, 43.4]):
        z = -3.35
        name = f"USB-A {i + 1}"
        outer = rectangle(x, z, 14.1, 6.95, 0.75)
        inner = rectangle(x, z, 12.55, 5.43, 0.47)
        receptacle(name, outer, inner)
        openings.append(
            block(
                name + " · moulded tongue", (10.9, 4.7, 1.28), (x, 5.28, z + 1.66), 0.15
            )
        )
        for dx in [-3.7, 3.7]:
            parts["contact"].append(
                block(
                    name + " · spring contact",
                    (1.43, 2.15, 0.37),
                    (x + dx, 6.66, z - 2.49),
                    0.12,
                )
            )
        parts["print"].append(text(name + " · printed rating", "USB3.0", x, 2.59, 1.80))

    receptacle("3.5 mm headset jack", circle(0, -3.35, 3.55), circle(0, -3.35, 1.84))
    parts["print"].append(
        flat(
            "Headset pictogram · headband",
            arc(0, 2.70, 1.45, 0.25, math.pi, math.tau),
            [],
            8.46,
            0.035,
        )
    )
    for dx in [-1.25, 1.25]:
        parts["print"].append(
            block(
                "Headset pictogram · ear cup",
                (0.43, 0.035, 1.00),
                (dx, 8.445, 3.0),
                0.10,
            )
        )
    for i, x in enumerate([-20.5, 20.5]):
        z = 12.8
        name = f"USB-C {i + 1}"
        receptacle(
            name, rectangle(x, z, 10.4, 4.23, 2.01), rectangle(x, z, 8.75, 3.12, 1.48)
        )
        openings.append(
            block(
                name + " · reversible middle tongue",
                (6.7, 4.7, 0.65),
                (x, 5.28, z),
                0.25,
            )
        )
        parts["print"].append(text(name + " · legend", "TYPE C", x, 17.9, 1.8))
    button(
        "LED mode key",
        rectangle(-43.4, 12.8, 15.6, 7, 0.65),
        rectangle(-43.4, 12.8, 14.4, 5.75, 0.57),
        8.86,
    )
    parts["print"].append(text("LED · switch legend", "LED", -43.4, 18.0, 1.7))
    button(
        "Recessed reset key",
        rectangle(43.4, 12.8, 10.3, 4.35, 2.05),
        rectangle(43.4, 12.8, 9.05, 3.12, 1.50),
        8.12,
    )
    parts["print"].append(text("Reset · switch legend", "RESET", 43.4, 17.9, 1.7))
    for x, legend in [(-51.1, "MODE"), (-43.4, "COLOR"), (-35.7, "MB")]:
        window = rectangle(x, 21.5, 2.9, 1.12, 0.24)
        apertures.append(window)
        openings.append(
            flat(legend + " · recessed indicator lens", window, [], 8.1, 1.4, 0.07)
        )
        parts["print"].append(text(legend + " · status legend", legend, x, 24.1, 1.18))
    parts["cover"].append(
        flat(
            "Front connector plate · 13 through openings",
            outside,
            apertures,
            top,
            1.38,
            0.19,
        )
    )
    parts["cover"].append(
        shell(
            "Front lip · folded panel return",
            [
                (x, y, z)
                for z, half_width, y in [
                    (30, 59.3, 7.02),
                    (29.4, 59.0, 5.50),
                    (28.7, 58.9, 5.56),
                    (29.3, 59.1, 7.02),
                ]
                for x in [-half_width, half_width]
            ],
            [
                (0, 1, 3, 2),
                (2, 3, 5, 4),
                (4, 5, 7, 6),
                (6, 7, 1, 0),
                (0, 2, 4, 6),
                (1, 7, 5, 3),
            ],
            0.06,
        )
    )
    for sign, role in [(-1, "Port"), (1, "Starboard")]:
        cross = [
            (53, -30, 8.21),
            (94.8, -27, -1.5),
            (96.4, -23, -4.6),
            (90.0, 25, -7.7),
            (59.4, 30, 8.21),
        ]
        v = [(sign * x, y - d, z) for d in [0, 2] for x, z, y in cross]
        faces = [(0, 1, 2), (0, 2, 4), (2, 3, 4), (7, 6, 5), (9, 7, 5), (9, 8, 7)]
        faces.extend((i, (i + 1) % 5, 5 + (i + 1) % 5, 5 + i) for i in range(5))
        parts["cover"].append(
            shell(role + " cheek · angled outer return", v, faces, 0.32)
        )
    return parts


def fit(scene):
    anchor = scene.objects.get("Angled front I/O console")
    if anchor is None:
        anchor = next(
            o
            for o in scene.objects
            if o.name.replace("_", " ").startswith("Angled front IO console")
            and o.type == "EMPTY"
        )
    if anchor.instance_collection:
        c = anchor.instance_collection
        if (
            c.name == COLLECTION
            and c.library
            and Path(bpy.path.abspath(c.library.filepath)).samefile(SOURCE)
        ):
            return anchor
        raise ValueError("Unrecognized front I/O collection")
    old = list(anchor.children)
    if not old or any(o.type != "MESH" or o.library or o.children for o in old):
        raise ValueError("Unrecognized front I/O panel contents")
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
        available,
        loaded,
    ):
        if COLLECTION not in available.collections:
            raise ValueError("Missing native front I/O collection")
        loaded.collections = [COLLECTION]
    anchor.instance_type = "COLLECTION"
    anchor.instance_collection = loaded.collections[0]
    for obj in old:
        bpy.data.objects.remove(obj, do_unlink=True)
    return anchor


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    for key, objects in build().items():
        label, color, metal, rough = FINISHES[key]
        rgb = [int(color[i : i + 2], 16) / 255 for i in [0, 2, 4]]
        mat = bpy.data.materials.new(label)
        mat.diffuse_color = tuple(
            (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb
        ) + (1,)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = mat.diffuse_color
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        for obj in objects:
            obj.data.materials.append(mat)
            collection.objects.link(obj)
            bpy.context.scene.collection.objects.unlink(obj)
        bpy.context.view_layer.update()
        export_batch(
            "gr701-front-io-" + key,
            objects,
            ROOT / "public/media/models" / ("gr701-front-io-" + key + ".mesh"),
        )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True)


if __name__ == "__main__":
    main()
