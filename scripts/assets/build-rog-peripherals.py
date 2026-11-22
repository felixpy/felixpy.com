import argparse
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
from io_scene_gltf2.io.exp import meshopt

scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--source-dir", type=Path)
parser.add_argument(
    "--output-dir", type=Path, default=project / "public" / "media" / "models"
)
selection = parser.add_mutually_exclusive_group()
selection.add_argument("--only", choices=["azoth", "harpe"])
selection.add_argument("--assemble-only", action="store_true")
args = parser.parse_args(
    sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
)
archive = project / ".references/04-桌面设备/键鼠与控制台"


def authoring_file(folder, filename):
    directory = (
        args.source_dir.resolve() if args.source_dir else archive / folder / "Blender"
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory / filename


output = args.output_dir.resolve()
output.mkdir(parents=True, exist_ok=True)
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
tools = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))
libraries = {
    "azoth": (
        authoring_file("ROG Azoth Extreme", "rog-azoth-extreme.blend"),
        "ROG Azoth Extreme",
    ),
    "harpe": (
        authoring_file("ROG Harpe Ace Extreme", "rog-harpe-extreme.blend"),
        "ROG Harpe Ace Extreme",
    ),
}


def export_selected(target, instances=False):
    meshopt.EXP_FILTER_BITS = 22
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_gpu_instances=instances,
        use_selection=True,
        export_extras=False,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
    )
    print(f"{target.name} · {target.stat().st_size} bytes")


def build_product(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    product = runpy.run_path(str(scripts / f"rog-{name}.py"))["build"](
        sculpt["Sculpture"], sculpt["finish"], tools
    )
    parts = [product] if isinstance(product, bpy.types.Object) else list(product)
    filename = f"rog-{name}-extreme"
    source, title = libraries[name]
    collection = bpy.data.collections.new(title)
    bpy.context.scene.collection.children.link(collection)
    bpy.ops.object.select_all(action="DESELECT")
    for item in parts:
        for parent in list(item.users_collection):
            parent.objects.unlink(item)
        collection.objects.link(item)
        item.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    visible = [
        part
        for part in parts
        if part.type == "MESH" and not part.get("productEnclosed")
    ]
    stationary = [part for part in visible if not part.get("productInstanced")]
    switches = [part for part in visible if part.get("productInstanced")]
    for part in stationary:
        part.select_set(True)
    body = stationary[0]
    bpy.context.view_layer.objects.active = body
    if len(stationary) > 1:
        bpy.ops.object.join()
    body.name = title
    body.data.name = title
    export_selected(output / (filename + ".glb"))
    if switches:
        bpy.ops.object.select_all(action="DESELECT")
        mounting = bpy.data.objects.new("Installed switches", None)
        collection.objects.link(mounting)
        mounting.select_set(True)
        for part in switches:
            part.parent = mounting
            part.select_set(True)
        export_selected(output / (filename + "-switches.glb"), instances=True)


if not args.assemble_only:
    for name in [args.only] if args.only else libraries:
        build_product(name)

if not args.only:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    for source, name in libraries.values():
        with bpy.data.libraries.load(str(source)) as (_, destination):
            destination.collections = [name]
        bpy.context.scene.collection.children.link(destination.collections[0])
    combined = authoring_file(
        "ROG keyboard and mouse assembly", "rog-peripherals.blend"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(combined), compress=True)
