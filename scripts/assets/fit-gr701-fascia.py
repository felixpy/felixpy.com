from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / ".references/03-电脑硬件/机箱与整机/ROG Hyperion GR701/Blender/gr701-fascia.blend"
)
COLLECTION = "GR701 · front intake and load frame"


def fit_fan_filter(scene, chassis):
    legacy = scene.objects.get("Front intake bracket and sliding filter")
    if legacy:
        assert legacy.parent == chassis and legacy.type == "EMPTY"
        assert all(child.type == "MESH" for child in legacy.children)
        for child in list(legacy.children):
            bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(legacy, do_unlink=True)
    front = [
        obj for obj in scene.objects if obj.type == "EMPTY"
        and obj.name.startswith("ROG Strix Fan Model 14 ARGB")
        and abs(obj.location.y + 0.225) < 0.0005
    ]
    if not front:
        return
    assert len(front) == 3
    title = "Unlit smoke-grey front intake impeller"
    finish = bpy.data.materials.get(title)
    if not finish:
        finish = bpy.data.materials.new(title)
        finish.diffuse_color = (0.063, 0.070, 0.080, 1)
        finish.use_nodes = True
        shader = finish.node_tree.nodes["Principled BSDF"]
        shader.inputs["Base Color"].default_value = finish.diffuse_color
        shader.inputs["Metallic"].default_value = 0.03
        shader.inputs["Roughness"].default_value = 0.54
    for housing in front:
        rotor = next(o for o in housing.children if o.name.startswith("Fan rotor"))
        blades = [o for o in rotor.children if o.type == "MESH" and o.dimensions.x > 0.1]
        assert len(blades) == 1
        slot = blades[0].material_slots[0]
        slot.link = "OBJECT"
        slot.material = finish


def fit(room):
    chassis = room.objects["ROG Hyperion GR701 chassis"]
    fit_fan_filter(room, chassis)
    existing = next((c for c in chassis.children if c.name == COLLECTION), None)
    if existing:
        linked = existing.instance_collection
        assert existing.instance_type == "COLLECTION" and linked.name == COLLECTION
        assert (
            Path(bpy.path.abspath(linked.library.filepath)).resolve()
            == SOURCE.resolve()
        )
        assert sum(o.get("open_slots", 0) for o in linked.objects) > 60
        assert len([o for o in linked.objects if "nose_x_mm" in o]) == 12
        assert sum(o.get("open_cells", 0) for o in linked.objects) == 74240
        assert sum(o.get("fasciaFinish") == "frame" for o in linked.objects) == 12
        assert sum("double-return jamb" in o.name for o in linked.objects) == 2
        return len(linked.objects)
    by_surface = {
        o.get("studioSurface"): o for o in chassis.children if o.get("studioSurface")
    }
    if "7364-26256-1825869964" in by_surface:
        dismantle = [
            by_surface[k]
            for k in ("7364-26256-1825869964", "408-0-515828573", "4-6-1538837401")
        ]
    else:
        dismantle = [
            room.objects[n]
            for n in (
                "GR701 load-bearing frame casting",
                "GR701 load-bearing frame casting.001",
                "ExtrudeGeometry.005",
                "ExtrudeGeometry.010",
                "ExtrudeGeometry.011",
                "PlaneGeometry.011",
            )
        ]
    dismantle.extend(
        room.objects[n] for n in ("Upper vented ROG crest", "Lower intake filter")
    )
    assert all(o.parent == chassis for o in dismantle)
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
        available,
        loaded,
    ):
        assert COLLECTION in available.collections
        loaded.collections = [COLLECTION]
    collection = loaded.collections[0]
    anchor = bpy.data.objects.new(COLLECTION, None)
    chassis.users_collection[0].objects.link(anchor)
    anchor.parent = chassis
    anchor.instance_type = "COLLECTION"
    anchor.instance_collection = collection
    anchor.empty_display_size = 0.01
    anchor["studioOccluder"] = True
    for o in dismantle:
        for part in list(o.children_recursive):
            bpy.data.objects.remove(part, do_unlink=True)
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return fit(room)
