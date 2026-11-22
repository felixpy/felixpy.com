import json
import runpy
from pathlib import Path

import bpy
from mathutils import Vector


def fit_component(name, product, file, collection, count):
    source = (
        Path(__file__).resolve().parents[2]
        / ".references/05-摄影与陈列/相机与镜头"
        / product
        / "Blender"
        / file
    )
    old = bpy.context.scene.objects[name]
    if old.instance_collection and old.instance_collection.name == collection:
        return old
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (_, loaded):
        loaded.collections = [collection]
    (parts,) = loaded.collections
    if len(parts.all_objects) != count:
        raise ValueError(f"Incomplete {collection} assembly")
    replacement = bpy.data.objects.new(name + " replacement", None)
    for owner in old.users_collection:
        owner.objects.link(replacement)
    replacement.parent = old.parent
    replacement.matrix_parent_inverse = old.matrix_parent_inverse.copy()
    replacement.matrix_basis = old.matrix_basis.copy()
    replacement.instance_type = "COLLECTION"
    replacement.instance_collection = parts
    replacement.empty_display_size = 0.013
    name = old.name
    for part in reversed(old.children_recursive):
        bpy.data.objects.remove(part, do_unlink=True)
    bpy.data.objects.remove(old, do_unlink=True)
    replacement.name = name
    return replacement


def fit_hood():
    return fit_component(
        "HB-117 bayonet petal hood",
        "Nikon HB-117 lens hood",
        "nikon-hb-117-lens-hood.blend",
        "HB-117 service parts",
        8,
    )


def fit_eyepiece():
    return fit_component(
        "Recessed EVF and rubber eyecup",
        "Nikon DK-33 eyecup",
        "nikon-dk33.blend",
        "DK-33 installed eyepiece",
        10,
    )


def fit_finder_crown(scene):
    root = Path(__file__).resolve().parents[2]
    profiles = json.loads((root / "src/scene/nikon-z8-finder.json").read_text())
    crown = next(o.data for o in scene.objects["Sloped finder crown"].children if o.type == "MESH")
    rear = [v for v in crown.vertices if v.co.y > 0]
    roof = [v for v in rear if abs(v.co.z * 1000 - profiles[-1]["height"]) < 0.01]
    if not roof:
        raise ValueError("Missing Z 8 finder crown roof")
    if max(v.co.y for v in roof) > 0.025:
        return
    for v in rear:
        profile = min(profiles, key=lambda p: abs(p["height"] - v.co.z * 1000))
        if abs(profile["height"] - v.co.z * 1000) > 0.01:
            raise ValueError("Unexpected Z 8 finder crown cross-section")
        scale = profile["scale"]
        blend = min(1, v.co.y / (0.025 * scale))
        blend *= blend * (3 - 2 * blend)
        factor = 1 + blend * (profile.get("rearScale", scale) / scale - 1)
        v.co.x *= factor
        v.co.y *= factor
    if crown.has_custom_normals:
        crown.normals_split_custom_set([(0, 0, 0)] * len(crown.loops))
    crown.update()


def fit_model_marks(scene):
    marks = runpy.run_path(str(Path(__file__).with_name("nikon-body-signatures.py")))
    item = next(
        o
        for o in scene.objects
        if "Nikon Z8 with NIKKOR" in o.name and o.type == "EMPTY"
    )
    for center in ((0.054, -0.01905, 0.0303), (-0.0601, 0.0188, 0.043)):
        for o in list(item.children):
            if (
                o.type == "MESH"
                and len(o.data.vertices) == 4
                and (o.location - Vector(center)).length < 0.00001
            ):
                bpy.data.objects.remove(o, do_unlink=True)
    existing = next((o for o in item.children if o.get("nikonModelMarks")), None)
    if existing:
        return existing
    with bpy.data.libraries.load(str(marks["source"]), link=True, relative=True) as (
        _,
        loaded,
    ):
        loaded.collections = [marks["collection"]]
    axis = bpy.data.objects.new("Z 8 front and shoulder signatures", None)
    scene.collection.objects.link(axis)
    axis.parent = item
    axis.instance_type = "COLLECTION"
    axis.instance_collection = loaded.collections[0]
    axis.empty_display_size = 0.005
    axis["nikonModelMarks"] = True
    return axis


def fit(atelier, read_parts, replace_branches):
    parent = bpy.context.scene.objects["Z8 serviceable body fittings"]
    authoring = (
        Path(__file__).resolve().parents[2]
        / ".references/05-摄影与陈列/相机与镜头/Nikon Z8/Blender"
    )
    parts = read_parts(authoring / "nikon-z8-hardware.blend")
    if {part.get("partGroup") for part in parts} != {
        "Battery chamber",
        "Battery door",
        "Body exterior",
    }:
        raise ValueError("Z 8 body fittings are incomplete")
    for part in parts:
        part["studioOccluder"] = False
    replace_branches(parent, parent.children, parts)
    fit_hood()
    fit_eyepiece()
    fit_finder_crown(bpy.context.scene)
    fit_model_marks(bpy.context.scene)
    runpy.run_path(str(Path(__file__).with_name("fit-nikon-z8-card-bay.py")))["fit"](
        bpy.context.scene
    )
