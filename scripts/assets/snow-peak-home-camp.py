import math
import runpy
from pathlib import Path

import bpy


source = Path(__file__).resolve().parents[2] / ".references/07-户外装备/营地照明与供电/Snow Peak HOME and CAMP Lantern ES-080/Blender/snow-peak-home-and-camp-lantern-es-080.blend"
assemblies = {"lantern": "ES-080-IV · removable lamp", "lantern-dock": "ES-080-IV · tabletop stand"}


def build(sculpture, rounded_wire, finish, ivory, diffuser, rail, rubber):
    solids = runpy.run_path(str(Path(__file__).with_name("product_solids.py")))
    pin, pocket = solids["pin"], solids["subtract"]
    gold = finish("Gold-plated charging contacts", "d5ac63", .85, .24)
    seal = finish("Ivory silicone · port gasket and button", "d7cfc0", .02, .61)
    insulator = finish("ES-080 socket insulator", "252829", .05, .49)
    legend = finish("Ivory mould stamp relief", "c8bfaf", .02, .47)

    def group(name, key=None, parent=None):
        obj = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(obj)
        obj.empty_display_size = .012
        obj.parent = parent
        if key:
            obj["campProduct"] = key
        return obj

    def spun(name, profile, material, owner, count=96, center=(0, 0), annular=False):
        shape = sculpture("ES-080 · " + name)
        rows = [[(center[0] + radius * math.sin(math.tau * i / count), h,
                  center[1] + radius * math.cos(math.tau * i / count)) for i in range(count)]
                for h, radius in profile]
        if annular:
            faces = []
            for j in range(len(rows)):
                here, after = j*count, (j+1)%len(rows)*count
                for i in range(count):
                    nxt = (i+1)%count
                    faces.append((here+i, here+nxt, after+nxt, after+i))
            shape.add([point for row in rows for point in row], faces, material)
        else:
            shape.rings(rows, material)
        obj = shape.finalize(24, [ivory, diffuser, rail])
        obj.data.set_sharp_from_angle(angle=math.radians(37))
        obj.parent = owner
        return obj

    def mark(name, h, size, offset, ink, owner, stamp_text=False):
        shape = sculpture("ES-080 · " + name)
        rim = []
        width = size * .17
        for i in range(6):
            angle = i * math.pi / 3
            vx, vz = math.cos(angle), math.sin(angle)
            rim.extend([(offset + size * vx - across * vz, size * vz + across * vx)
                        for across in (-width, width)])
            rim.append((offset + 2 * width * math.cos(angle + math.pi/6),
                        2 * width * math.sin(angle + math.pi/6)))
        shape.rings([[(x, y, z) for x,z in rim] for y in (h - .06, h + .04)], ink, False)
        if stamp_text:
            shape.label("snow peak", 7.4, lambda x, y: (x + 3.5, h, -y), ink)
        obj = shape.finalize()
        obj.parent = owner

    body = group("HOME and CAMP Lantern · ES-080-IV", "lantern")
    dock = group("HOME and CAMP charging stand · ES-080", "lantern-dock")
    dock["manufacturerDiameterMm"] = 130
    body["manufacturerDiameterMm"] = 124
    body["manufacturerHeightMm"] = 250
    dock["assembledHeightMm"] = 270
    spun("non-slip dock ring", [(0, 54), (0, 57), (.35, 58), (1.6, 58),
                                (1.7, 53), (.35, 53)], rubber, dock)
    spun("charging stand shell", [(1.4, 56), (1.45, 62.5), (1.8, 64.2), (2.6, 65),
                                  (8.7, 65), (10.2, 64.4), (12, 62.5), (16.2, 47.5),
                                  (19.95, 35.05), (20.0, 31.0)], ivory, dock)
    guide = spun("keyed circular docking guide", [(19.93, 31.15), (20.2, 31.25),
                 (22.85, 30.5), (23.15, 30.05)], ivory, dock)
    pocket(guide, [pin("Keyway cutter", (0, 19, 31), (0, 24, 31), 3.3, ivory, 32)])
    for side in (-1, 1):
        x = side * 21.8
        spun(f"charging stand terminal {side:+}", [(23.15, 2.7), (23.28, 2.75),
             (23.47, 2.45), (23.5, 1.9)], gold, dock, 32, (x, 0))
    mark("charger mould stamp", 23.17, 5.1, 0, legend, dock)

    shell = spun("battery housing and docking recess", [(23.65, 28), (23.65, 30.9),
                 (23.4, 31.35), (20.5, 31.95), (20, 32.5), (20, 34.2),
                 (20.35, 35.1), (21.35, 35.55), (86, 35.6), (90, 35.1),
                 (91, 34.2)], ivory, body)
    runpy.run_path(str(Path(__file__).with_name("es080-charge-port.py")))["build"](
        body, shell, sculpture, group, solids, ivory, seal, insulator, rail
    )
    tab = pin("ES-080 · raised alignment key", (0, 20.35, 31.5), (0, 23.6, 31.5),
              2.85, ivory, 36)
    tab.parent = body
    for side in (-1, 1):
        x = side * 21.8
        spun(f"lamp terminal seat {side:+}", [(23.62, 3.25), (23.52, 3.1),
             (23.52, 2.45)], seal, body, 32, (x, 0))
        spun(f"lamp terminal {side:+}", [(23.51, 2.43), (23.47, 2.15)],
             gold, body, 32, (x, 0))

    for name, radius, thickness, surface in [("switch seat", 8.45, .45, seal),
                                            ("dimming switch", 7.85, 1.18, ivory)]:
        push = pin("ES-080 · " + name, (0, 69.3, 35.25), (0, 69.3, 35.3 + thickness),
                   radius, surface, 60)
        push.parent = body
    for i in range(3):
        light = pin(f"ES-080 · battery gauge light pipe {i+1}", (0, 54.5-i*5.5, 35.5),
                    (0, 54.5-i*5.5, 35.74), 1.05, legend, 24)
        light.parent = body

    globe = spun("opal globe and top neck", [(87.5, 38.8), (88.5, 40.8), (90, 42.4),
         (100.5, 42.5), (103.5, 43.15), (108, 46), (113, 47.7), (117.3, 48.05),
         (118, 47.90), (118.55, 48.15), (196.15, 48.15), (201.35, 47.6),
         (205.05, 45.4), (207.75, 40.8), (209.55, 36.8), (211.25, 35.7),
         (219.15, 35.7), (219.75, 35.2), (219.75, 33.5), (219.05, 33.25),
         (210.20, 33.25), (208.1, 35.45), (205.6, 40.3), (202.6, 44.4),
         (198.8, 46.45), (118.4, 46.65), (113.3, 46.2), (107.8, 44.4),
         (104.1, 41.7), (101.1, 40.95), (91.4, 40.95), (89.6, 39.4),
         (89.0, 38.7), (89.0, 35.4), (87.5, 35.4)], diffuser, body, annular=True)
    spun("recessed globe crown", [(208.78, 32.45), (208.95, 33.28),
         (210.42, 33.38), (211.08, 32.78), (211.22, 31.96)], diffuser, body)
    cutters = [pin("Pivot journal bore", (side*38.0,98,0), (side*44.5,98,0),
                   2.86, diffuser, 48) for side in (-1,1)]
    pocket(globe, cutters)

    bail = group("ES-080 · reversible wire handle pivot", parent=body)
    bail.location.z = .098
    half = [(37.6,0,0),(42.8,0,0),(44.2,.07,0),(46.1,.65,0),(50.9,4.4,0),(52.6,9.5,0),
            (52.8,16,0),(52.8,151.4,0),(52.4,157.5,0),(50.1,161.8,0),
            (46.2,164.3,0),(40.9,164.9,0),(10.3,164.9,0),(6.5,165.5,0),
            (4.0,167.2,0),(2.0,169.15,0),(0,170.15,0)]
    arm = sculpture("ES-080 · bent stainless wire bail")
    rounded_wire(arm, half + [(-x,h,z) for x,h,z in reversed(half[:-1])], 1.85, rail)
    arm.finalize(24, [rail]).parent = bail
    for side in (-1, 1):
        axle = spun(f"pressed pivot bushing {side:+}", [(-4.1,2.55),(-3.85,2.78),
                    (-.35,2.78),(-.24,3.27),(.14,3.34),(.52,3.06),(.55,2.15),
                    (.24,2.04),(-3.88,2.04),(-4.10,2.19)], seal, body, 48, annular=True)
        axle.location=(side*.04242,0,.098)
        axle.rotation_euler.y=side*math.pi/2
        axle.parent = body
    bail["es080Joint"] = "pivot"
    bail["axisHeightMm"] = 98.
    shade = group("ES-080 · sliding shade", parent=bail)
    shade.location.z = .106
    shade["es080Joint"] = "shade"
    shade["tableSeatMm"] = 106.
    shade["clearanceMm"] = 143.
    shade["hangSeatMm"] = 61.8
    canopy = spun("ivory shade and cap", [(17.9, 35.15), (17.5, 35.98),
                  (7.05, 35.98), (6.5, 36.25), (.6, 46),
                  (-.28, 59.7), (-.12, 61.2), (.47, 62), (2.65, 62),
                  (3.7, 61.25), (5.1, 58.5), (11.25, 38.3), (11.8, 37.9),
                  (21.55, 37.7), (23.25, 36.4), (23.75, 34.8)], ivory, None)
    cuts = []
    for side in (-1, 1):
        cuts.append(pin("Wire clearance", (side*52.8,-2,0), (side*52.8,12,0),
                        3.15, ivory, 40))
    pocket(canopy, cuts)
    canopy.parent = shade
    for side in (-1, 1):
        guide = spun(f"shade guide sleeve {side:+}", [(1.6,2.85),(1.8,3.08),
                     (5.6,3.08),(5.92,2.88),(5.92,2.22),(5.64,2.12),
                     (1.85,2.12),(1.60,2.24)], seal, shade, 32, (side*52.8,0), True)
        mount = sculpture(f"ES-080 · split guide seam {side:+}")
        for d in (-2.9, 2.9):
            mount.pipe([(side*52.8, 6.83, d), (side*58.4, 5.16, d),
                        (side*61.2, 3.84, d), (side*61.86, 2.74, d),
                        (side*61.86, .64, d)], .12, legend, 8)
        mount.finalize().parent = shade
    mark("shade stamp", 23.77, 3.25, -17.7, legend, shade, True)
    return body, dock


def bake_for_web(root):
    solids = runpy.run_path(str(Path(__file__).with_name("product_solids.py")))
    bpy.context.view_layer.update()
    for owner in [root, *[part for part in root.children_recursive if part.type == "EMPTY"]]:
        meshes = [part for part in owner.children if part.type == "MESH"]
        if meshes:
            solids["combine"](owner.name + " surfaces", meshes)


def save_product(models):
    scene = bpy.data.scenes.new("Snow Peak HOME & CAMP")
    scene.unit_settings.system = "METRIC"
    for root in models:
        collection = bpy.data.collections.new(assemblies[root["campProduct"]])
        scene.collection.children.link(collection)
        for obj in (root, *root.children_recursive):
            collection.objects.link(obj)
    bpy.data.libraries.write(str(source), {scene}, path_remap="RELATIVE_ALL", compress=True)
    collections = list(scene.collection.children)
    bpy.data.scenes.remove(scene)
    for collection in collections:
        bpy.data.collections.remove(collection)


def install(scene, key):
    root = next(obj for obj in scene.objects if obj.get("campProduct") == key)
    name = assemblies[key]
    if root.instance_collection and root.instance_collection.name == name:
        return root
    children = list(root.children_recursive)
    if root.type != "EMPTY" or not children or any(obj.library for obj in children):
        raise ValueError("Unrecognised HOME & CAMP lamp mount")
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (_, loaded):
        loaded.collections = [name]
    collection = loaded.collections[0]
    if not collection or not any(obj.get("campProduct") == key for obj in collection.objects):
        raise ValueError("Missing editable HOME & CAMP assembly")
    root.instance_type = "COLLECTION"
    root.instance_collection = collection
    for child in reversed(children):
        bpy.data.objects.remove(child, do_unlink=True)
    return root


def fit_lamp(scene):
    return install(scene, "lantern")


def fit(atelier):
    fit_lamp(bpy.context.scene)
    install(bpy.context.scene, "lantern-dock")
