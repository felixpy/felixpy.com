import math
import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
review = project / ".review" / "atelier"
(review / "nikon-reference").mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
shared = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = shared["Sculpture"], shared["finish"]
shelf_lenses = [
    ("--ultrawide", 0, "NIKKOR Z 14-24", -0.411, 0.178),
    ("--super-telezoom", 5, "NIKKOR Z 100-400", -0.25, 0.166),
    ("--telephoto", 2, "NIKKOR Z 70-200", -0.092, 0.218),
    ("--plena", 3, "NIKKOR Z 135", 0.141, 0.17),
    ("--standard-prime", 4, "NIKKOR Z 58mm", 0.365, 0.18),
]
selection = {index for flag, index, *_ in shelf_lenses if flag in sys.argv}
layout_only = not selection and "--layout-only" in sys.argv
if selection or layout_only:
    retained = tuple(name for _, index, name, *_ in shelf_lenses if index not in selection)
    with bpy.data.libraries.load(str(review / "vitrine-inventory.blend")) as (
        source,
        result,
    ):
        result.objects = [
            name
            for name in source.objects
            if name.startswith(retained)
        ]
    if len(result.objects) != len(retained):
        raise ValueError("Missing lens bodies in the saved cabinet inventory")
    for item in result.objects:
        bpy.context.collection.objects.link(item)
if not layout_only:
    runpy.run_path(str(scripts / "vitrine-optics.py"))["build_lenses"](
        Sculpture, finish, selection or {index for _, index, *_ in shelf_lenses}
    )
castings = [
    ("Sun Wukong · The Great Victory", "Great Sage", "great-sage", "Great Sage · round casting"),
    ("Tongshifu · Iron Man Mark 85", "Iron Man Mark 85", "mk85", "Tongshifu · Iron Man Mark 85"),
]
for label, product, filename, casting in castings:
    source = project / ".references/05-摄影与陈列/手办与收藏模型" / product / "Blender" / (filename + ".blend")
    with bpy.data.libraries.load(str(source)) as (available, loaded):
        if label not in available.objects:
            raise ValueError(f"Missing prepared casting {casting} in {source}")
        loaded.objects = [label]
    item = loaded.objects[0]
    if item.data.name != casting:
        raise ValueError(f"Unexpected mesh for {label}: {item.data.name}")
    bpy.context.collection.objects.link(item)


def local(x, h, d):
    return Vector((x, -d, h))


figure_clearance = []


def place_figure(label, x, z, angle, display_height):
    obj = bpy.data.objects[label]
    native_height = max(v.co.z for v in obj.data.vertices) - min(v.co.z for v in obj.data.vertices)
    obj.scale = (display_height / native_height,) * 3
    obj.location = local(x, 0.520, z)
    obj.rotation_euler.z = angle
    obj["cabinetItem"] = label
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    heights = [v.z for v in points]
    gap = min(heights) - 0.520
    if abs(gap) > 0.00012 or max(heights) > 0.951:
        raise ValueError(
            f"Unexpected cabinet fit: {label}, elevation {min(heights)} to {max(heights)}"
        )
    support = [v.co * obj.scale.z for v in obj.data.vertices if abs(v.co.z * obj.scale.z) < 0.00005]
    span = [max(v[i] for v in support) - min(v[i] for v in support) for i in (0, 1)]
    if span[0] < 0.100 or span[1] < 0.030:
        raise ValueError(f"Insufficient level footprint on {label}: {span}")
    clearance = {
        "rear": min(-v.y for v in points) - 0.0305,
        "front": 0.348 - max(-v.y for v in points),
        "side": 0.558 - max(abs(v.x) for v in points),
        "overhead": 0.965 - max(heights),
    }
    if min(clearance.values()) < 0.012:
        raise ValueError(f"Insufficient clearance around {label}: {clearance}")
    figure_clearance.append(
        {
            "figure": label,
            "supportSurfaceMM": 520,
            "lowestMM": round(min(heights) * 1000, 3),
            "highestMM": round(max(heights) * 1000, 3),
            "contactGapMM": round(gap * 1000, 3),
            "contactFootprintMM": [round(s * 1000, 1) for s in span],
            "clearanceMM": {
                side: round(value * 1000, 2) for side, value in clearance.items()
            },
        }
    )


place_figure("Sun Wukong · The Great Victory", -0.248, 0.171, -0.06, 0.265)
place_figure("Tongshifu · Iron Man Mark 85", 0.068, 0.172, 0.08, 0.260)
cap_source = review / "nikon-reference/nikkor-z135-plena.blend"
with bpy.data.libraries.load(str(cap_source)) as (library, loaded):
    (cap_name,) = [name for name in library.objects if name.startswith("LF-N1 rear cap")]
    loaded.objects = [cap_name]
(cap_master,) = loaded.objects
contacts = []
shelf = 0.971
eye_x, eye_depth = 0.098, 1.244
for _, _, prefix, x, depth in shelf_lenses:
    obj = next(o for o in bpy.context.scene.objects if o.name.startswith(prefix))
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0, 0, math.atan2(eye_x - x, eye_depth - depth))
    obj.location = local(x, shelf + 0.013, depth)
    obj["cabinetItem"] = obj.name
    support = obj
    if obj.get("opticalVariant") != 3:
        support = cap_master.copy()
        support.name = "LF-N1 rear display cap · " + prefix.removeprefix("NIKKOR Z ")
        support.data = cap_master.data
        bpy.context.collection.objects.link(support)
        support.location = obj.location
        support.rotation_euler = obj.rotation_euler
    bpy.context.view_layer.update()
    floor = min((support.matrix_world @ v.co).z for v in support.data.vertices)
    lowest = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    if abs(floor - shelf) > 0.00008 or lowest < shelf - 0.00008:
        raise ValueError(f"{obj.name}: rear cover or lens intersects shelf: {floor}, {lowest}")
    contacts.append(
        {
            "lens": obj.name,
            "rearCapBottomMM": round(floor * 1000, 3),
            "glassTopMM": 971,
            "rearCapToGlassGapMM": round((floor - shelf) * 1000, 3),
        }
    )
(review / "cabinet-supports.json").write_text(
    json.dumps(contacts, indent=2), encoding="utf-8"
)
(review / "cabinet-statues.json").write_text(
    json.dumps(figure_clearance, indent=2), encoding="utf-8"
)
bpy.context.scene.world = bpy.data.worlds.new("Cabinet studio")
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1
source_file = review / "vitrine-inventory.blend"
working_source = review / "vitrine-lens-edit.blend" if selection or layout_only else source_file
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(working_source))
target = (
    review / "vitrine-next.glb"
    if "--review-only" in sys.argv
    else project / "public" / "media" / "models" / "vitrine-inventory.glb"
)
target.parent.mkdir(parents=True, exist_ok=True)
export_options = dict(
    export_format="GLB",
    export_extras=True,
    export_texcoords=True,
    export_tangents=False,
    export_animations=False,
    export_cameras=False,
    export_lights=False,
    export_yup=True,
)
with tempfile.TemporaryDirectory(dir=review) as temporary:
    cabinet = Path(temporary) / "cabinet.glb"
    display = Path(temporary) / "display.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(cabinet),
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
        **export_options,
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(cabinet), "NIKKOR"],
        check=True,
    )
    subprocess.run(
        ["node", str(scripts / "install-cabinet-castings.mjs"), str(cabinet), str(display)],
        check=True,
    )
    if selection or layout_only:
        working_source.replace(source_file)
    if "--review-only" not in sys.argv:
        category = project / ".references/05-摄影与陈列"
        inventory = category / "相框与展示设施/Camera display cabinet/Blender/vitrine-inventory.blend"
        for name, edition, filename, casting in castings:
            item = bpy.context.scene.objects[name]
            library = category / "手办与收藏模型" / edition / "Blender" / (filename + ".blend")
            with bpy.data.libraries.load(str(library), link=True) as (available, parts):
                if casting not in available.meshes:
                    raise ValueError(f"{library} has no matching casting for {name}")
                parts.meshes = [casting]
            mesh = parts.meshes[0]
            if len(mesh.polygons) != len(item.data.polygons):
                raise ValueError(f"Publish the matching editable casting for {name} first")
            item.data = mesh
            mesh.library.filepath = bpy.path.relpath(str(library), start=str(inventory.parent))
        appended_sources = {
            "nikkor-z135-plena.blend": category / "相机与镜头/NIKKOR Z 135mm f1.8 S Plena/Blender/nikkor-z135-plena.blend",
            "registered-collectibles.blend": category / "手办与收藏模型/Display figurines/Blender/registered-collectibles.blend",
        }
        for blocks in (bpy.data.materials, bpy.data.images, bpy.data.meshes):
            for block in blocks:
                provenance = block.library_weak_reference
                if provenance and not block.library:
                    source = appended_sources.get(Path(bpy.path.abspath(provenance.filepath)).name)
                    if source:
                        provenance.filepath = bpy.path.relpath(str(source), start=str(inventory.parent))
        bpy.ops.wm.save_as_mainfile(filepath=str(inventory), compress=True, relative_remap=False)
    if "--review-only" not in sys.argv and not selection and not layout_only:
        subprocess.run(
            [
                bpy.app.binary_path,
                "-b",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python",
                str(scripts / "export-mounted-nikkor.py"),
            ],
            check=True,
        )
    display.replace(target)
print(f"VITRINE_EXPORT={target} ({target.stat().st_size} bytes)")
