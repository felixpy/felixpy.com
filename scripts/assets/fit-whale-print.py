from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / ".references/06-工坊与工具/三维打印与模型/Whale-tail girl"
MESH = "DeepSeek Whale Girl print surfaces"
TITLE = "DeepSeek Whale Girl · on PEI"


def guide_position(guide, dx, dy):
    if abs(dx) + abs(dy) < 1e-8:
        return
    if guide.data.users > 1:
        guide.data = guide.data.copy()
    for v in guide.data.vertices:
        lo, hi = 0.0, 1.0
        for step in range(16):
            t = (lo + hi) / 2
            z = (1 - t) ** 3 * 0.585 + 3 * (1 - t) * t * 0.49 + t**3 * 0.42
            if z > v.co.z:
                lo = t
            else:
                hi = t
        weight = t * t * (3 - 2 * t)
        v.co.x += dx * weight
        v.co.y += dy * weight
    guide.data.update()


def screen_image(parent):
    screen = next(
        o
        for o in parent.children
        if o.type == "MESH"
        and abs(o.location.x + 0.151) < 0.0001
        and abs(o.location.z - 0.574) < 0.0001
    )
    if screen.get("jobPanel") == "Crown finishing pass":
        return
    image = bpy.data.images.load(str(FOLDER / "对比与验证/print-status.png"))
    image.pack()
    mat = screen.data.materials[0].copy()
    next(n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE").image = image
    screen.data.materials[0] = mat
    screen["jobPanel"] = "Crown finishing pass"


def fit(scene):
    with bpy.data.libraries.load(
        str(FOLDER / "Blender/whale-tail-girl.blend"), link=True, relative=True
    ) as (source, loaded):
        if MESH not in source.meshes:
            raise ValueError("Missing complete DeepSeek Whale Girl")
        loaded.meshes = [MESH]
    figure = loaded.meshes[0]
    height, x, y = figure["printHeight"] + 0.00048, figure["startX"], figure["startY"]
    assert abs(max(v.co.z for v in figure.vertices) + 0.00048 - height) < 1e-7
    current = scene.objects.get(TITLE) or scene.objects.get("Whale-tail girl · on PEI")
    installed = current or bpy.data.objects.new(TITLE, figure)
    installed.name = TITLE
    old = installed.data
    installed.data = figure
    if old != figure and not old.users:
        bpy.data.meshes.remove(old)
    machine = scene.objects.get("Bambu Lab H3C with AMS 3H")
    if machine:
        bed = scene.objects["Z carriage"]
        if not current:
            source = scene.objects["H3C lantern-petg"]
            source.users_collection[0].objects.link(installed)
            bpy.data.objects.remove(source, do_unlink=True)
        installed.parent = bed
        rail, nozzle = (
            scene.objects["CoreXY crossbeam"],
            scene.objects["Swaptek active tool"],
        )
        guide_position(
            scene.objects["Active tool filament guide"],
            x - nozzle.location.x,
            y - rail.location.y,
        )
        rail.location.y, nozzle.location.x = y, x
        bed.location.z = rail.location.z - height
        screen_image(machine)
    else:
        if not current:
            scene.collection.objects.link(installed)
            old_lantern = bpy.data.collections.get("lantern")
            if old_lantern:
                for o in list(old_lantern.objects):
                    bpy.data.objects.remove(o, do_unlink=True)
                bpy.data.collections.remove(old_lantern)
        deck = 0.345 - height
        dz = deck - installed.location.z
        gantry = bpy.data.collections["gantry"]
        beam = next(o for o in gantry.objects if o.name.startswith("gantry-steel"))
        head = bpy.data.collections["head"]
        nozzle = next(o for o in head.objects if o.name.startswith("head-graphite"))
        dx, dy, lift = (
            x - nozzle.location.x,
            y - beam.location.y,
            0.345 - beam.location.z,
        )
        for part in bpy.data.collections["bed"].objects:
            part.location.z += dz
        for part in gantry.objects:
            part.location.z += lift
            part.location.y += dy
        for part in head.objects:
            part.location.z += lift
            part.location.x += dx
            part.location.y += dy
        installed.location.z = deck
    scene.view_layers[0].update()
    return installed
