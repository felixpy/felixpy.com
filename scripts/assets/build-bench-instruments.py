import math
import runpy
import subprocess
from pathlib import Path

import bpy


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
shared = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = shared["Sculpture"], shared["finish"]
rubber = finish("Instrument · charcoal TPE", "292c2e", rough=0.8)
plastic = finish("Instrument · satin charcoal ABS", "44484a", rough=0.54)
chrome = finish("Hardware · turned stainless", "a7aaaa", metal=0.86, rough=0.27)
printing = finish("Instrument · warm white print", "deded6", rough=0.74)
ink = finish("Instrument · carbon black ink", "262627", rough=0.85)
clear = finish("Sampler · optical acrylic", "c9d1cf", rough=0.23, coat=0.36)
clear_bsdf = clear.node_tree.nodes.get("Principled BSDF")
clear_bsdf.inputs["Alpha"].default_value = 0.34
clear.diffuse_color = (0.76, 0.82, 0.8, 0.34)
cap = finish("Sampler · translucent milky R4 cap", "d4d7d2", rough=0.58)
grip_red = finish("Knipex · red two-component handle", "b92d2f", rough=0.62)
grip_blue = finish("Knipex · blue non-slip inserts", "304b85", rough=0.84)
forged = finish("Knipex · burnished tool steel", "343637", metal=0.72, rough=0.48)
ground = finish("Knipex · ground cutting faces", "9ca39f", metal=0.89, rough=0.28)


def rounded(w, h, r, n=5):
    return [
        (
            sx * (w / 2 - r) + r * math.cos((i + j / n) * math.pi / 2),
            sy * (h / 2 - r) + r * math.sin((i + j / n) * math.pi / 2),
        )
        for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)])
        for j in range(n + 1)
    ]


def pad(shape, x, h, d, w, height, thick, r, mat, deck=False, lip=0.3):
    def pts(a, b, c):
        return (x + a, h + c, d + b) if deck else (x + a, h + b, d + c)

    shape.rings(
        [
            [
                pts(a, b, c)
                for a, b in rounded(
                    w - 2 * shrink, height - 2 * shrink, max(0.08, r - shrink)
                )
            ]
            for c, shrink in [
                (-thick / 2, lip),
                (-thick / 2 + min(lip, thick * 0.24), 0),
                (thick / 2 - min(lip, thick * 0.24), 0),
                (thick / 2, lip),
            ]
        ],
        mat,
    )


def dial(shape, x, h, profile, mat, teeth=0, ribs=0):
    count = max(48, teeth * 3)
    shape.rings(
        [
            [
                (
                    x
                    + (
                        r
                        + ribs
                        * (0.5 + 0.5 * math.cos(i * math.tau * teeth / count)) ** 2
                    )
                    * math.cos(i * math.tau / count),
                    h
                    + (
                        r
                        + ribs
                        * (0.5 + 0.5 * math.cos(i * math.tau * teeth / count)) ** 2
                    )
                    * math.sin(i * math.tau / count),
                    d,
                )
                for i in range(count)
            ]
            for r, d in profile
        ],
        mat,
        close=False,
    )


meter, meter_parts = runpy.run_path(str(scripts / "fluke-115.py"))["build_fluke"](
    Sculpture, finish, rounded, pad, dial
)

cutters, cutter_parts = runpy.run_path(str(scripts / "knipex-snips.py"))["build_snips"](
    Sculpture, dial, forged, ground, chrome, grip_red, grip_blue, ink
)

tester, tester_parts, enclosed, tester_collection = runpy.run_path(str(scripts / "glanaut-tester.py"))["build"](
    Sculpture, finish, rounded, pad, clear, cap, rubber, ink
)

bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.preferences.filepaths.save_version = 0
collection_name = tester_collection.name
bpy.ops.wm.save_as_mainfile(
    filepath=str(root / ".review/atelier/bench-instruments.blend")
)
target = root / "public/media/models/bench-instruments.glb"
for part in enclosed:
    bpy.data.objects.remove(part, do_unlink=True)
for item, parts in [(meter, meter_parts), (cutters, cutter_parts), (tester, tester_parts)]:
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    combined = bpy.context.object
    combined.parent = None
    combined["benchInstrument"] = item["benchInstrument"]
    name = item.name
    bpy.data.objects.remove(item, do_unlink=True)
    combined.name = name
    combined.data.name = name
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_extras=True,
    export_animations=False,
    export_cameras=False,
    export_lights=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
)
product_path = root / ".references/06-工坊与工具/电子测量与实验/Mechanical switch tester/Blender"
if product_path.is_dir():
    bpy.ops.wm.open_mainfile(filepath=str(root / ".review/atelier/bench-instruments.blend"))
    assembly = bpy.data.collections[collection_name]
    room = bpy.context.scene.collection
    for collection in list(room.children):
        if collection != assembly:
            room.children.unlink(collection)
    for obj in list(room.objects):
        room.objects.unlink(obj)
    bpy.data.orphans_purge(do_recursive=True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.clip_start = 0.0002
                view.region_3d.view_location = (0, 0, 0.010)
                view.region_3d.view_distance = 0.14
                view.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str(product_path / "mechanical-switch-tester.blend"), compress=True)
