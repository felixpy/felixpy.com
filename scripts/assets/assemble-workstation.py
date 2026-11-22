import argparse
import json
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARTS = ROOT / ".review/atelier/pc-components"
INTERCHANGE = PARTS / "interchange"
NATIVE = PARTS / "native"
AXES = Matrix.Rotation(math.pi / 2, 4, "X")
sys.path.insert(0, str(HERE))
from product_workshop import Product


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"


def native_sources():
    NATIVE.mkdir(exist_ok=True)

    def persist(key, members):
        coll = bpy.data.collections.new(key)
        for obj in members:
            coll.objects.link(obj)
        bpy.data.libraries.write(str(NATIVE / (key + ".blend")), {coll}, compress=True)
        bpy.data.collections.remove(coll)

    def capture(product, destination):
        if product.name not in {
            "astral-casting",
            "astral-impeller",
            "ryuo-housing",
            "ryuo-radiator",
            "astral-harness",
            "strix-fan",
        }:
            return
        for key, objs in product.parts.items():
            persist(product.name + "-" + key, objs)

    original = Product.export
    Product.export = capture
    try:
        runpy.run_path(str(HERE / "model-case-fittings.py"))
        reset()
        runpy.run_path(str(HERE / "model-astral-harness.py"))["build"](save=False)
        reset()
        p = Product("strix-fan")
        runpy.run_path(str(HERE / "model-strix-fan.py"))["impeller"](p)
        capture(p, None)
    finally:
        Product.export = original
    for builder in ["power_harness", "cooling"]:
        reset()
        factory = runpy.run_path(str(HERE / "build-pc-internals.py"))[builder]
        for key, objs in factory().items():
            persist(key, objs)
    bpy.ops.wm.open_mainfile(filepath=str(PARTS / "machined-interfaces.blend"))
    keys = {
        obj["nativePart"] for obj in bpy.context.scene.objects if "nativePart" in obj
    }
    for key in keys:
        persist(
            key,
            [obj for obj in bpy.context.scene.objects if obj.get("nativePart") == key],
        )


def collection_from_library(source, name, link):
    with bpy.data.libraries.load(str(source), link=link, relative=link) as (src, dst):
        if name not in src.collections:
            raise ValueError(f"Missing collection {name} in {source}")
        dst.collections = [name]
    return dst.collections[0]


def from_array(array):
    m = Matrix([array[i : i + 4] for i in range(0, 16, 4)]).transposed()
    return AXES @ m @ AXES.inverted()


def instance(data, name, matrix, destination):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.011
    obj.instance_type = "COLLECTION"
    obj.instance_collection = data
    destination.objects.link(obj)
    obj.matrix_world = matrix
    return obj


def link_part(part, parent):
    data = collection_from_library(PARTS / (part["key"] + ".blend"), part["name"], True)
    for i, array in enumerate(part["offsets"]):
        labels = part["labels"]
        suffix = " • " + labels[i] if labels else ""
        instance(data, part["name"] + suffix, from_array(array), parent)


def replace_batched(pool, main):
    nodes = [obj for obj in list(main.all_objects) if obj.get("nativePart") in pool]
    for obj in nodes:
        key = obj["nativePart"]
        source = pool[key]
        if isinstance(source, Path):
            source = collection_from_library(source, key, False)
            pool[key] = source
        material = obj.material_slots[0].material if obj.material_slots else None
        anchor = bpy.data.objects.new(key, None)
        main.objects.link(anchor)
        anchor.parent = obj.parent
        anchor.matrix_local = obj.matrix_local.copy()
        anchor.empty_display_size = 0.002
        for original in source.objects:
            item = original.copy()
            main.objects.link(item)
            item.parent = anchor
            if material and key != "aio-braid" and item.type in {"MESH", "CURVE"}:
                if not item.data.materials:
                    item.data.materials.append(material)
                for slot in item.material_slots:
                    slot.link = "OBJECT"
                    slot.material = material
        bpy.data.objects.remove(obj, do_unlink=True)
    for source in pool.values():
        if isinstance(source, bpy.types.Collection):
            for obj in list(source.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(source)


def save_part(part, children):
    reset()
    bpy.ops.import_scene.gltf(filepath=str(INTERCHANGE / (part["key"] + ".glb")))
    scene = bpy.context.scene
    main = bpy.data.collections.new(part["name"])
    scene.collection.children.link(main)
    for obj in list(scene.objects):
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        main.objects.link(obj)
    replace_batched({p.stem: p for p in NATIVE.glob("*.blend")}, main)
    for child in children:
        link_part(child, main)
    scene.name = part["name"]
    for obj in scene.objects:
        if obj.type == "EMPTY":
            obj.empty_display_size = 0.004
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.clip_start = 0.0004
                space.overlay.show_floor = False
                space.overlay.show_extras = False
                space.region_3d.view_distance = (
                    0.72 if part["key"] == "hyperion-gr701" else 0.27
                )
                space.shading.color_type = "MATERIAL"
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(PARTS / (part["key"] + ".blend")), compress=True
    )


def assembly(entries, allow_pending):
    reset()
    scene = bpy.context.scene
    scene.name = "ROG workstation • installed"
    main = bpy.data.collections.new("GR701 • individually mounted components")
    scene.collection.children.link(main)
    for part in entries:
        if not part["owner"]:
            link_part(part, main)
    source = PARTS / "strix-z890-a.blend"
    if source.exists():
        board = collection_from_library(source, "ROG Strix Z890-A Gaming WiFi S", True)
        tr = Matrix.Translation((0.077, 0.289, 0.194)) @ Matrix.Rotation(
            -math.pi / 2, 4, "Z"
        )
        instance(board, board.name, tr, main)
        cpu = collection_from_library(
            PARTS / "lga1851-processor.blend", "LGA1851 processor package", True
        )
        datum = next(
            obj for obj in board.all_objects if obj.name.startswith("CPU contact")
        )
        instance(cpu, cpu.name, tr @ Matrix.Translation(datum.location), main)
    elif not allow_pending:
        raise FileNotFoundError(source)
    install = bpy.data.collections.new("Installation datums")
    scene.collection.children.link(install)
    for label, (x, y, z) in {
        "CPU contact": (0.0695, 0.111, -0.155),
        "PCIEX16 centreline": (0.069, 0.014, -0.2056),
        "GPU I/O bulkhead": (0.004, -0.008, -0.3029),
        "Upper radiator manifold": (0.062, 0.231, -0.188),
        "Lower harness grommet": (-0.043, -0.181, 0.081),
        "24 pin tray grommet": (0.087, 0.13, 0.012),
    }.items():
        datum = bpy.data.objects.new(label, None)
        install.objects.link(datum)
        datum.location = (x, -z, y)
        datum.empty_display_type = "PLAIN_AXES"
        datum.empty_display_size = 0.0075
    scene["Installed DIMMs"] = 4
    scene["Radiator fans"] = 3
    scene["Case fans"] = 4
    scene["GPU fans"] = 4
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.overlay.show_extras = False
                area.spaces.active.region_3d.view_distance = 1.03
                area.spaces.active.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(
        filepath=str(PARTS / "gr701-workstation.blend"), compress=True
    )


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--assemble-only", action="store_true")
    args.add_argument("--allow-pending-board", action="store_true")
    options = args.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    manifest = json.loads((INTERCHANGE / "assembly.json").read_text(encoding="utf-8"))
    if not options.assemble_only:
        native_sources()
        for component in sorted(manifest, key=lambda item: not bool(item["owner"])):
            if component["key"] in {"xpg-d50-fubuki", "rog-herculx-xh01"}:
                continue
            save_part(
                component,
                [child for child in manifest if child["owner"] == component["key"]],
            )
    assembly(manifest, options.allow_pending_board)


if __name__ == "__main__":
    main()
