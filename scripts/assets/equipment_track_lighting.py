import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[2]
source = (
    root
    / ".references/02-家具与灯具/轨道与射灯/ERCO Parscan 48V S/Blender/parscan-minirail.blend"
)
name = "ERCO Parscan 48V · Minirail"


def coordinate(x, height, depth):
    return Vector((x, -depth, height))


def source_specs():
    layout = json.loads(
        (root / "src/scene/equipment-track-layout.json").read_text(encoding="utf-8")
    )
    mount = coordinate(*layout["mount"])
    heads = []
    for head in layout["heads"]:
        pivot = coordinate(head["x"], -0.058, 0)
        target = coordinate(*head["aim"]) - mount
        axis = (target - pivot).normalized()
        heads.append((head, pivot + axis * 0.071, axis))
    return mount, heads


def retire(scene):
    for title in ("Rejuvenation Crissey Sconce", "Louis Poulsen AJ Eklipta 350"):
        old = scene.objects.get(title)
        if not old:
            continue
        coll = old.instance_collection
        libs = {o.library for o in coll.all_objects if o.library} if coll else set()
        for obj in reversed([old, *old.children_recursive]):
            bpy.data.objects.remove(obj, do_unlink=True)
        if coll and not coll.users and not coll.library:
            bpy.data.collections.remove(coll)
        for lib in libs:
            if not any(
                obj.library == lib and (obj.users_collection or obj.users_scene)
                for obj in bpy.data.objects
            ):
                bpy.data.libraries.remove(lib)


def power_driver(owner, path, scene, scale):
    driver = owner.driver_add(path).driver
    if not driver.variables:
        for label, key in (
            ("state", "Equipment track override"),
            ("night", "Night lighting"),
        ):
            variable = driver.variables.new()
            variable.name = label
            variable.targets[0].id_type = "SCENE"
            variable.targets[0].id = scene
            variable.targets[0].data_path = f'["{key}"]'
    driver.expression = f"{scale} * (night if state < 0 else state)"


def power_lenses(holder, scene):
    parts = holder.instance_collection
    for obj in list(parts.objects):
        if not obj.library or obj.type != "MESH" or not obj.material_slots:
            continue
        source_mat = obj.material_slots[0].material
        if source_mat.name != "Parscan Spherolit lens":
            continue
        finish = (
            bpy.data.materials.get("Parscan Spherolit · switched lens")
            or source_mat.copy()
        )
        finish.name = "Parscan Spherolit · switched lens"
        strength = finish.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        power_driver(strength, "default_value", scene, 1.65)
        lens = obj.copy()
        parts.objects.link(lens)
        lens.material_slots[0].link = "OBJECT"
        lens.material_slots[0].material = finish
        lens["gearTrackLens"] = True
        parts.objects.unlink(obj)
    assert len([o for o in parts.objects if o.get("gearTrackLens")]) == 3


def fit(scene):
    retire(scene)
    mount, heads = source_specs()
    owner = scene.objects["Camp kitchen and boot bench"]
    holder = scene.objects.get(name)
    if not holder:
        parts = bpy.data.collections.new("Parscan S · linked track hardware")
        holder = bpy.data.objects.new(name, None)
        owner.users_collection[0].objects.link(holder)
        holder.instance_type = "COLLECTION"
        holder.instance_collection = parts
    parts = holder.instance_collection
    installed = {obj.data.name if obj.get("gearTrackLens") else obj.name for obj in parts.objects}
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (existing, items):
        items.objects = [title for title in existing.objects if title not in installed]
    for obj in items.objects:
        if obj.type in ("MESH", "EMPTY"):
            parts.objects.link(obj)
    holder.parent = owner
    holder.location = mount
    holder.empty_display_size = 0.025
    prop = "Equipment track override"
    if prop not in scene:
        scene[prop] = -1
    scene.id_properties_ui(prop).update(
        min=-1, max=1, description="Automatic at night (-1), off (0), or on (1)"
    )
    power_lenses(holder, scene)
    for head, position, axis in heads:
        role = head["station"]
        lamp = next((o for o in holder.children if o.get("gearTrackAim") == role), None)
        if not lamp:
            data = bpy.data.lights.new("Parscan S · " + role, "SPOT")
            lamp = bpy.data.objects.new(data.name, data)
            holder.users_collection[0].objects.link(lamp)
            lamp.parent = holder
            lamp["gearTrackAim"] = role
        data = lamp.data
        data.use_temperature = True
        data.temperature = 3000
        data.shadow_soft_size = 0.024
        data.spot_size = math.radians(head["beamDegrees"])
        data.spot_blend = 0.64
        lamp["gearTrackCandela"] = head["candela"]
        power_driver(data, "energy", scene, head["candela"] * 0.24)
        lamp.location = position
        lamp.rotation_euler = axis.to_track_quat("-Z", "Y").to_euler()
    return holder
