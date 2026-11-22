import json
import math
import os
import runpy
from pathlib import Path

import bpy
from mathutils import Vector


root = Path(__file__).resolve().parents[2]
archive = root / ".references"
masters = archive / "11-项目整体/工作室全景/Felix Studio/Blender"
layout = json.loads((root / "src/scene/cabinet-light-layout.json").read_text())
products = {
    "case": archive / "02-家具与灯具/柜内与陈列照明/Corporate Friends C1-mini-LC/Blender/c1-mini-lc.blend",
    "bench": archive / "02-家具与灯具/壁灯与工作照明/Astro Mondrian 600 Wall Mount 1374042/Blender/astro-mondrian-600.blend",
    "rack": archive / "07-户外装备/营地照明与供电/Snow Peak SnowMiner ES-020/Blender/snowminer-es-020.blend",
}
collection_name = "Installed luminaires | workbench, case and field wall"


def xyz(x, height, depth):
    return Vector((x, -depth, height))


def append_parts(source, collection):
    with bpy.data.libraries.load(str(source)) as (library, loaded):
        names = tuple(library.objects)
        loaded.objects = list(names)
    parts = dict(zip(names, loaded.objects))
    for obj in parts.values():
        collection.objects.link(obj)
    return parts


def empty(collection, name, parent, position):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.012
    obj.parent = parent
    obj.location = position
    collection.objects.link(obj)
    return obj


def drive(block, prop, scene, expression, variables):
    driver = block.driver_add(prop).driver
    for name, key in variables:
        var = driver.variables.new()
        var.name = name
        var.targets[0].id_type = "SCENE"
        var.targets[0].id = scene
        var.targets[0].data_path = f'["{key}"]'
    driver.expression = expression


night = ("night", "Night lighting")
work = ("bench", "Workbench light")


def optic(collection, name, style, parent, origin, direction, temperature):
    data = bpy.data.lights.new(name, style)
    data.use_temperature = True
    data.temperature = temperature
    obj = bpy.data.objects.new(name, data)
    obj.parent = parent
    obj.location = origin
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    collection.objects.link(obj)
    return data


def emissive(parts, name, expression, variables, scene, color=None):
    mat = next(slot.material for obj in parts.values() for slot in obj.material_slots
               if slot.material and slot.material.name.startswith(name))
    inputs = mat.node_tree.nodes["Principled BSDF"].inputs
    if color:
        inputs["Emission Color"].default_value = (*color, 1)
    drive(inputs["Emission Strength"], "default_value", scene, expression, variables)


def fit_bench(scene, collection):
    holder = empty(collection, "Astro Mondrian 600 · 1374042", scene.objects["Workbench"], xyz(0.313, 1.59, -0.012))
    holder.rotation_euler.z = -math.pi / 2
    parts = append_parts(products["bench"], collection)
    for obj in parts.values():
        if obj.parent is None:
            obj.parent = holder
    origin = xyz(0, 0.0078, 0.166)
    direction = xyz(0, -0.39, 0.031) - origin
    source = optic(collection, "Mondrian 600 | opal line emission", "AREA", holder, origin, direction, 2700)
    source.shape = "RECTANGLE"
    source.size = 0.5956
    source.size_y = 0.0188
    source.spread = math.radians(114)
    drive(source, "energy", scene, "1.45 * bench", [work])
    emissive(parts, "Mondrian opal diffuser", "2.4 * bench", [work], scene)


def fit_snowminer(scene, collection):
    holder = empty(collection, "Snow Peak SnowMiner ES-020", scene.objects["Camp kitchen and boot bench"],
                   xyz(-0.0762, 1.572 + 21 * 0.0254, 0.052))
    parts = append_parts(products["rack"], collection)
    for obj in parts.values():
        if obj.parent is None:
            obj.parent = holder
    pupil = parts["SnowMiner optical exit"]
    direction = parts["SnowMiner throw axis"].location - pupil.location
    source = optic(collection, "SnowMiner | expanded diffuser", "SPOT", pupil, Vector((0, 0, 0)), direction, 4700)
    source.spot_size = math.radians(162)
    source.spot_blend = 0.9
    source.shadow_soft_size = 0.018
    drive(source, "energy", scene, "0.13 * night", [night])
    for name, strength in [("SnowMiner expanded silicone diffuser", 1.05), ("SnowMiner central PMMA lens", 1.85)]:
        emissive(parts, name, f"{strength} * night", [night], scene, (1, 0.915, 0.73))


def clone(root_object, collection):
    members = (root_object, *root_object.children_recursive)
    copies = {original: original.copy() for original in members}
    for original, obj in copies.items():
        collection.objects.link(obj)
        obj.parent = copies.get(original.parent, original.parent)
        if obj.type == "LIGHT":
            obj.data = obj.data.copy()
    return copies


def fit_case(scene, collection):
    cabinet = scene.objects["Low-iron glass collection cabinet"]
    parts = append_parts(products["case"], collection)
    top = parts["C1 magnetic rail"]
    bottom = clone(top, collection)[top]
    for rail, level in [(top, 1.285), (bottom, 0.965)]:
        rail.parent = cabinet
        rail.location = xyz(0, level, 0.31)
    shoe = parts["C1 magnetic shoe"]
    originals = (shoe, *shoe.children_recursive)
    groups = [{part: part for part in originals}] + [clone(shoe, collection) for _ in layout[1:]]
    for idx, (clones, plan) in enumerate(zip(groups, layout), 1):
        obj = clones[shoe]
        obj.name = f"C1-mini-LC | {idx}"
        obj.parent = top if plan["shelf"] > 1 else bottom
        obj.location = xyz(plan["x"], -0.0073, 0)
        axis = Vector(plan["aim"]) - Vector((plan["x"], plan["shelf"] - 0.0231, 0.31))
        yaw = math.atan2(-axis.x, -axis.z) + math.asin(0.00678 / math.hypot(axis.x, axis.z))
        clones[parts["C1 pan"]].rotation_euler.z = yaw
        aligned_z = math.sin(yaw) * axis.x + math.cos(yaw) * axis.z
        clones[parts["C1 tilt"]].rotation_euler.x = math.atan2(-aligned_z, -axis.y)
        light = clones[parts["Collimator photometry"]]
        light.name = f"C1 | {idx} · {plan['beam']} degree optic"
        light["localAim"] = list(xyz(*plan["aim"]))
        light.data.spot_size = math.radians(plan["beam"] * 1.22)
        light.data.spot_blend = 0.37
        light.data.energy = 0.45 * plan["peak"] * .55
    diffuser = next(slot.material for obj in parts.values() for slot in obj.material_slots if slot.material and slot.material.name.startswith("C1-mini warm white collimator"))
    diffuser.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.65
    strips = [obj for obj in cabinet.children if obj.type == "MESH"
              and (obj.dimensions - Vector((1.075, 0.010, 0.323))).length < 0.001]
    if len(strips) != 1:
        raise ValueError("Expected the pair of legacy cabinet strips on a separate mesh")
    strips[0].hide_render = strips[0].hide_viewport = True


def fix_case_lights(scene):
    lights = [obj for obj in scene.objects if obj.type == "LIGHT" and obj.name.startswith("C1 | ")]
    assert len(lights) == len(layout)
    for obj in lights:
        number = int(obj.name.split("| ")[1].split()[0])
        obj.data.driver_remove("energy")
        obj.data.energy = 0.45 * layout[number - 1]["peak"] * 0.55
    diffusers = {slot.material for obj in scene.objects for slot in obj.material_slots
                 if slot.material and slot.material.name.startswith("C1-mini warm white collimator")}
    assert diffusers
    for material in diffusers:
        strength = material.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        strength.driver_remove("default_value")
        strength.default_value = 1.65


def daylight(scene, collection):
    origin = xyz(-3.4, 2.93, 1.86)
    sun = optic(collection, "West window | angled direct sun", "SUN", None, origin,
                xyz(0.4, 1.08, -0.33) - origin, 5250)
    sun.angle = math.radians(0.53)
    drive(sun, "energy", scene, "2.1 * (1 - night)", [night])
    sky = optic(collection, "West window | sky aperture", "AREA", None, xyz(-1.39, 1.6235, 0.585),
                Vector((1, 0, 0)), 6900)
    sky.shape = "RECTANGLE"
    sky.size = 1.536
    sky.size_y = 1.280
    drive(sky, "energy", scene, "24 - 22.8 * night", [night])
    drive(sky, "temperature", scene, "6900 + 2400 * night", [night])
    world = next(node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND")
    drive(world.inputs["Strength"], "default_value", scene, "0.26 - 0.231 * night", [night])


def install(scene):
    collection = bpy.data.collections.new(collection_name)
    scene.collection.children.link(collection)
    for key, value in [(night[1], 0.0), (work[1], 1.0)]:
        scene[key] = value
        scene.id_properties_ui(key).update(min=0.0, max=1.0)
    fit_bench(scene, collection)
    fit_snowminer(scene, collection)
    fit_case(scene, collection)
    daylight(scene, collection)


def validate(scene):
    bpy.context.view_layer.update()
    installed = bpy.data.collections[collection_name]
    cabinet = scene.objects["Low-iron glass collection cabinet"]
    sources = [obj for obj in installed.objects if obj.type == "LIGHT"]
    case = [obj for obj in sources if "localAim" in obj]
    assert len(case) == 5 and len(sources) == 9, [obj.name for obj in sources]
    for light in case:
        target = cabinet.matrix_world @ Vector(light["localAim"])
        direction = light.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        assert (target - light.matrix_world.translation).angle(direction) < 0.0009, light.name
    for value in (0.0, 1.0):
        scene["Night lighting"] = value
        scene.update_tag()
        scene.frame_set(scene.frame_current)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        snow = scene.objects["SnowMiner | expanded diffuser"].evaluated_get(deps).data.energy
        sun = scene.objects["West window | angled direct sun"].evaluated_get(deps).data.energy
        assert (snow > 0) == bool(value) and (sun > 0) != bool(value), (value, snow, sun)
    scene["Night lighting"] = 0.0
    scene.update_tag()
    scene.frame_set(scene.frame_current)
    return len(installed.objects), len(case), len(sources)


def synchronize(master):
    bpy.ops.wm.open_mainfile(filepath=str(master), load_ui=False)
    scene = bpy.context.scene
    previous = set(obj.name for obj in scene.objects)
    if collection_name not in bpy.data.collections:
        install(scene)
    fix_case_lights(scene)
    track = runpy.run_path(str(Path(__file__).with_name("equipment_track_lighting.py")))
    track["fit"](scene)
    runpy.run_path(str(Path(__file__).with_name("fit-ceiling-location.py")))["fit"](scene)
    previous -= {"Rejuvenation Crissey Sconce", "Louis Poulsen AJ Eklipta 350"}
    validate(scene)
    staged = master.with_suffix(".installing.blend")
    if staged.exists():
        raise FileExistsError(staged)
    bpy.context.preferences.filepaths.save_version = 0
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(staged), compress=True, copy=True)
        bpy.ops.wm.open_mainfile(filepath=str(staged), load_ui=False)
        scene = bpy.context.scene
        parts, heads, lights = validate(scene)
        assert previous.issubset(scene.objects.keys()), previous.difference(scene.objects.keys())
        missing = [path for path in bpy.utils.blend_paths(absolute=True, packed=False)
                   if path and not Path(path).exists() and "<UDIM>" not in path]
        print("SYNCHRONIZED", master.name, "objects", len(bpy.data.objects), "new", parts,
              "heads", heads, "sources", lights, "external", len(bpy.utils.blend_paths(absolute=True, packed=False)),
              "missing", missing, flush=True)
        assert not missing, missing
        os.replace(staged, master)
    finally:
        staged.unlink(missing_ok=True)


if __name__ == "__main__":
    for file in ("felix-studio.blend", "felix-studio-assembled.blend"):
        synchronize(masters / file)
