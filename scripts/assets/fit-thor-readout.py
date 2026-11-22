from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thor_display import add_readout


product = Path(__file__).resolve().parents[2] / ".references/03-电脑硬件/电源与机箱布线/ROG Thor 1600W/Blender/thor-psu.blend"
collection_name = "ROG Thor 1600W Titanium III"


def readout(parts):
    current = [part for part in parts if part.get("thorTelemetry")]
    if len(current) != 2 or {o.get("thorTelemetry"): o.data.body for o in current} != {"watts": "206", "unit": "W"}:
        raise ValueError("Unexpected editable Thor telemetry")
    return current


def fit(scene):
    root = scene.objects.get("ROG power supply in rear cradle")
    if not root:
        return readout(scene.objects)
    instance = next((o for o in root.children if o.get("thorProductMount")), None)
    if instance:
        return readout(instance.instance_collection.all_objects)
    old = next((o for o in root.children if o.name.startswith(collection_name) and o.type == "EMPTY"), None)
    if old and any(o.name.startswith("Folded side panel") for o in old.children_recursive):
        with bpy.data.libraries.load(str(product), link=True, relative=True) as (_, loaded):
            loaded.collections = [collection_name]
        collection = loaded.collections[0]
        parts = readout(collection.all_objects)
        instance = bpy.data.objects.new(collection_name + " · power supply", None)
        old.users_collection[0].objects.link(instance)
        instance.parent = root
        instance.matrix_basis = old.matrix_basis.copy()
        instance.instance_type = "COLLECTION"
        instance.instance_collection = collection
        instance["thorProductMount"] = True
        for ob in [*reversed(old.children_recursive), old]:
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.context.view_layer.update()
        return parts
    current = [o for o in root.children_recursive if o.get("thorTelemetry")]
    if current:
        return readout(current)
    masks = [
        o for o in root.children_recursive
        if o.type == "MESH" and (o.name.startswith("Thor 1600W Titanium III • pixels")
                                 or o.get("nativePart") == "thor-1600-pixels")
    ]
    if not masks or len({o.parent for o in masks}) != 1:
        raise ValueError("Expected a single mounted Thor readout")
    parent = masks[0].parent
    material = masks[0].material_slots[0].material
    collections = list(masks[0].users_collection)
    parts = add_readout(lambda obj, _: obj.data.materials.append(material))
    for part in parts:
        part.parent = parent
        for collection in collections:
            if part.name not in collection.objects:
                collection.objects.link(part)
        for collection in list(part.users_collection):
            if collection not in collections:
                collection.objects.unlink(part)
    for mask in masks:
        bpy.data.objects.remove(mask, do_unlink=True)
    bpy.context.view_layer.update()
    return parts
