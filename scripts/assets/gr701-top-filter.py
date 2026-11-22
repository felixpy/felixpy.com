import json
import math
import runpy
from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
base = runpy.run_path(str(HERE / "model-gr701-fascia.py"))
from blender_parts import barrel, block, export_batch

PRODUCT = base["PRODUCT"]
SOURCE = PRODUCT / "Blender/gr701-top-filter.blend"
COLLECTION = "GR701 · removable roof filter"
FINISHES = {
    "plate": ("Graphite anodized decorative plate", "696b71", 0.61, 0.43),
    "frame": ("Charcoal moulded roof carrier", "36383d", 0.17, 0.51),
    "weave": ("Black filter gauze", "383b40", 0.23, 0.76),
    "hardware": ("Black zinc rear latch and fasteners", "42444a", 0.52, 0.51),
}


def chamfer(left, bottom, right, top, cut):
    return [
        (left + cut, bottom),
        (right - cut, bottom),
        (right, bottom + cut),
        (right, top - cut),
        (right - cut, top),
        (left + cut, top),
        (left, top - cut),
        (left, bottom + cut),
    ]


def plane(name, outline, holes, y, thickness, edge=0):
    return base["sheet"](
        name, outline, holes, lambda x, z, d: (x, y + d, z), thickness, edge
    )


def opening(x, z, width):
    cut, depth = 2.65, 5.2
    end = z + (width - cut) * math.tan(math.radians(28))
    return [
        (x, z),
        (x + width - cut, end),
        (x + width, end - 0.57),
        (x + width, end - 0.57 - depth),
        (x + cut, z - 0.57 - depth),
        (x, z - depth),
    ]


def gauze(name, xyz, uv):
    obj = base["shell"](name, xyz, [tuple(range(4))])
    layer = obj.data.uv_layers.active
    for loop in obj.data.loops:
        layer.data[loop.index].uv = uv[loop.vertex_index]
    return obj


def build():
    parts = {k: [] for k in FINISHES}
    pattern = json.loads((HERE / "gr701-roof-apertures.json").read_text())
    openings = [opening(*s) for s in pattern]
    parts["plate"].append(
        plane(
            "Brushed slot plate · 108 staggered apertures",
            chamfer(-76, -226, 76, 226, 1),
            openings,
            12.5,
            1.7,
        )
    )
    parts["frame"].append(
        plane(
            "Carrier · raised continuous perimeter",
            chamfer(-83, -235, 83, 235, 4),
            [chamfer(-75, -225, 75, 225, 1)],
            12.05,
            4.7,
            0.24,
        )
    )
    parts["weave"].append(
        gauze(
            "Removable full-length upper filter cloth",
            [
                (-75.6, 6.1, -226),
                (75.6, 6.1, -226),
                (75.6, 6.1, 226),
                (-75.6, 6.1, 226),
            ],
            [(0, 0), (114, 0), (114, 342), (0, 342)],
        )
    )
    parts["frame"].append(
        plane(
            "Fine filter cassette rim",
            chamfer(-78.5, -228, 78.5, 228, 2),
            [chamfer(-74, -224, 74, 224, 1)],
            6.8,
            2.1,
            0.13,
        )
    )
    for side, name in [(-1, "Port"), (1, "Starboard")]:

        def cheek(z, y, d):
            return side * (83 + (12.05 - y) * 0.58 + d), y, z

        openings = [chamfer(-186, -1.5, 182, 8.3, 2)]
        parts["frame"].append(
            base["sheet"](
                name + " side · open folded cover",
                chamfer(-235, -4.4, 235, 12.05, 2.8),
                openings,
                cheek,
                1.5,
                0.16,
            )
        )
        side_mesh_coords = [
            cheek(z, y, -2.0)
            for z, y in [(-189, -2.1), (185, -2.1), (185, 9.4), (-189, 9.4)]
        ]
        parts["weave"].append(
            gauze(
                name + " side mesh strip",
                side_mesh_coords,
                [(0, 0), (283, 0), (283, 8.7), (0, 8.7)],
            )
        )
        for z in [-107, 0, 107]:
            parts["frame"].append(
                base["sheet"](
                    name + " · gauze stiffening rib",
                    chamfer(z - 1.2, -1.75, z + 1.2, 8.53, 0.42),
                    [],
                    cheek,
                    0.88,
                    0.13,
                )
            )
        for z in [-173, 0, 173]:
            parts["hardware"].append(
                barrel(
                    name + " · swaged panel post",
                    (side * 78.2, 7.4, z),
                    (side * 78.2, 10.6, z),
                    2.15,
                    12,
                )
            )
    rear_profile = chamfer(-90, -4.4, 90, 12.05, 4.0)
    rear_slot = chamfer(-43, -0.75, 43, 7.0, 1.85)
    parts["frame"].append(
        base["sheet"](
            "Rear pull face · open finger recess",
            rear_profile,
            [rear_slot],
            lambda x, y, d: (x, y, -235 + d),
            1.7,
            0.2,
        )
    )
    parts["frame"].append(
        base["sheet"](
            "Front seating wall",
            rear_profile,
            [],
            lambda x, y, d: (x, y, 234 + d),
            1.6,
            0.2,
        )
    )
    parts["frame"].append(
        block(
            "Finger recess · blind inner wall", (88, 8.4, 1.2), (0, 2.95, -228.2), 0.3
        )
    )
    for y in [-0.95, 6.95]:
        parts["frame"].append(
            block("Finger recess · return", (86, 1.2, 6.7), (0, y, -231.8), 0.25)
        )
    parts["hardware"].append(
        block("Underside rear release tongue", (48, 2.5, 6.5), (0, -3.9, -238.1), 0.68)
    )
    parts["hardware"].append(
        block("Latch spring bridge", (53, 1.5, 15.6), (0, -3.3, -228.5), 0.28)
    )
    for x in [-21, 21]:
        parts["hardware"].append(
            barrel("Latch fastener · T3", (x, -4.65, -222), (x, -2.65, -222), 1.9, 12)
        )
    return parts


def finish(key):
    label, color, metal, rough = FINISHES[key]
    material = bpy.data.materials.new(label)
    material.use_nodes = True
    rgb = [int(color[i : i + 2], 16) / 255 for i in [0, 2, 4]]
    material.diffuse_color = tuple(((v + 0.055) / 1.055) ** 2.4 for v in rgb) + (1,)
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    for socket, value in [
        ("Base Color", material.diffuse_color),
        ("Metallic", metal),
        ("Roughness", rough),
    ]:
        bsdf.inputs[socket].default_value = value
    if key == "weave":
        tex = bpy.data.images.new(
            "Nylon mesh · warp and weft", width=32, height=32, alpha=True
        )
        tex.pixels = [
            v
            for y in range(32)
            for x in range(32)
            for v in (1, 1, 1, float(x < 8 or y < 8))
        ]
        tex.pack()
        source = nodes.new("ShaderNodeTexImage")
        source.image = tex
        material.node_tree.links.new(source.outputs["Alpha"], bsdf.inputs["Alpha"])
    return material


def fit(scene):
    mount = scene.objects["Removable top dust filter"]
    current = mount.instance_collection
    if (
        current
        and current.library
        and Path(bpy.path.abspath(current.library.filepath)).samefile(SOURCE)
    ):
        return mount
    old = list(mount.children)
    if (
        current
        or len(old) not in [2, 5]
        or any(o.type != "MESH" or o.library or o.children for o in old)
    ):
        raise ValueError("Unexpected roof filter mounting assembly")
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
        available,
        wanted,
    ):
        if COLLECTION not in available.collections:
            raise ValueError("Missing GR701 roof filter")
        wanted.collections = [COLLECTION]
    mount.instance_type = "COLLECTION"
    mount.instance_collection = wanted.collections[0]
    for part in old:
        bpy.data.objects.remove(part, do_unlink=True)
    return mount


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    for key, parts in build().items():
        material = finish(key)
        for part in parts:
            part.data.materials.append(material)
            collection.objects.link(part)
            scene.collection.objects.unlink(part)
        bpy.context.view_layer.update()
        shipped = [
            o
            for o in parts
            if "fastener" not in o.name
            and "swaged" not in o.name
            and "spring bridge" not in o.name
        ]
        export_batch(
            key,
            shipped,
            HERE.parents[1]
            / "public/media/models"
            / ("gr701-top-filter-" + key + ".mesh"),
        )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True)


if __name__ == "__main__":
    main()
