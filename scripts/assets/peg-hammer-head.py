import math
import random
from pathlib import Path

import bpy


def category_source():
    root = Path(__file__).resolve().parents[2]
    return root / ".references/07-户外装备/帐篷寝具与搭建/Snow Peak Peg Hammer PRO.C and Solid Stake 20/Blender/snow-peak-peg-hammer-pro-c-and-solid-stake-20.blend"


def save_source(parts, destination):
    stake_file = next(category_source().parents[3].glob("*/Camping field equipment/Blender/camp-field-equipment.blend"))
    with bpy.data.libraries.load(str(stake_file), link=True) as (source, loaded):
        loaded.objects = [n for n in source.objects if n.startswith("Snow Peak Solid Stake 20")]
    if len(loaded.objects) != 3:
        raise ValueError("Expected three installed Solid Stake 20 pegs")
    for source in loaded.objects:
        stake = bpy.data.objects.new(source.name, source.data)
        bpy.context.scene.collection.objects.link(stake)
        stake.matrix_basis = source.matrix_basis.copy()
        stake.location.x -= 0.298
        stake.location.y += 0.104
        stake.location.z -= 1.982
    collection = bpy.data.collections.new("Snow Peak PRO.C · service assembly")
    bpy.context.scene.collection.children.link(collection)
    for part in parts:
        for owner in list(part.users_collection):
            owner.objects.unlink(part)
        collection.objects.link(part)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    for lib in bpy.data.libraries:
        lib.filepath = bpy.path.relpath(bpy.path.abspath(lib.filepath), start=str(destination.parent))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), relative_remap=False)


def fit(scene):
    source = category_source()
    name = "Snow Peak PRO.C · service assembly"
    anchor = scene.objects["Snow_Peak_Peg_Hammer_PROC_N-001"]
    collection = anchor.instance_collection
    if collection:
        if collection.name == name and collection.library and Path(bpy.path.abspath(collection.library.filepath)).samefile(source):
            return anchor
        raise ValueError("Unrecognized equipment-wall hammer collection")
    original = list(anchor.children)
    if anchor.type != "EMPTY" or not original or any(
        o.type != "MESH" or o.children or o.library or not o.name.startswith(anchor.name) for o in original
    ):
        raise ValueError("Unrecognized equipment-wall hammer meshes")
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (available, loaded):
        if name not in available.collections:
            raise ValueError(f"Missing installed hammer collection in {source}")
        loaded.collections = [name]
    collection = loaded.collections[0]
    if len(collection.all_objects) != 6 or any(o.type != "MESH" for o in collection.all_objects):
        raise ValueError("Expected the PRO.C shaft, receiver, insert, two pins and wrist loop")
    anchor.instance_type = "COLLECTION"
    anchor.instance_collection = collection
    anchor["proCPegHammer"] = True
    for old in original:
        bpy.data.objects.remove(old, do_unlink=True)
    return anchor


def cut(part, cutter):
    modifier = part.modifiers.new("Machined aperture", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.context.view_layer.objects.active = part
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def lathe(shape, sections, material, contact_face=False):
    rows = []
    if contact_face:
        rng = random.Random(1001)
        impressions = []
        for i in range(37):
            a, r = rng.uniform(0, math.tau), 15 * math.sqrt(rng.random())
            impressions.append((r * math.cos(a), r * math.sin(a), rng.uniform(1.2, 3.1), rng.uniform(0.09, 0.38)))
        for radius in [0.32, 2.3, 4.5, 6.7, 8.9, 11.1, 13.2, 14.6, 15.3]:
            ring = []
            for i in range(64):
                a = i * math.tau / 64
                h, d = radius * math.sin(a), radius * math.cos(a)
                relief = sum(depth * math.exp(-((h-y)**2 + (d-z)**2) / width**2) for y, z, width, depth in impressions)
                ring.append((-48.13 + relief, h, d))
            rows.append(ring)
    for x, height, radius in sections:
        rows.append([
            (x, height + radius * math.sin(i * math.tau / 64), radius * math.cos(i * math.tau / 64))
            for i in range(64)
        ])
    shape.rings(rows, material)


def forged_surface(steel):
    steel = steel.copy()
    steel.name = "PRO.C · black electrodeposited forged steel"
    size = 64
    rng = random.Random(9901)
    heights = [rng.gauss(0, 0.5) for _ in range(size * size)]
    def h(x, y):
        return heights[(y % size) * size + x % size]
    pixels = []
    for y in range(size):
        for x in range(size):
            dx, dy = h(x-1, y) - h(x+1, y), h(x, y-1) - h(x, y+1)
            length = math.sqrt(dx**2 + dy**2 + 1)
            pixels.extend([0.5 + 0.5 * dx / length, 0.5 + 0.5 * dy / length, 0.5 + 0.5 / length, 1])
    image = bpy.data.images.new("PRO.C · fine forging grain", width=size, height=size)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels)
    image.pack()
    tex = steel.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    bump = steel.node_tree.nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = 0.23
    shader = steel.node_tree.nodes.get("Principled BSDF")
    steel.node_tree.links.new(tex.outputs["Color"], bump.inputs["Color"])
    steel.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return steel


def sleeve(shape, x, outer, inner, half_length, material):
    vertices = []
    faces = []
    count = 49
    for depth, radius in [
        (-half_length, outer - 0.15),
        (-half_length + 0.32, outer),
        (half_length - 0.32, outer),
        (half_length, outer - 0.15),
        (half_length, inner),
        (-half_length, inner),
    ]:
        for i in range(count):
            a = 1.18 + i / (count - 1) * (math.tau - 0.19)
            vertices.append((x + radius * math.cos(a), radius * math.sin(a), depth))
    for row in range(6):
        j = (row + 1) % 6
        for i in range(count - 1):
            faces.append((row * count + i, row * count + i + 1, j * count + i + 1, j * count + i))
    for i in [0, count - 1]:
        faces.append(tuple(row * count + i for row in range(6)))
    shape.add(vertices, faces, material)


def copper_joint(sculpture, place, steel, copper, hardware, fork, oak):
    def object_for(shape, uv=0):
        return place(shape, (0, 0, 0), uv=uv)

    steel = forged_surface(steel)
    face = sculpture("PRO.C · N-001R-1 removable copper head")
    lathe(face, [
        (-48, 0, 15.7), (-47.5, 0, 16.65), (-46.4, 0, 17.45), (-45.9, 0, 17.5),
        (-31.8, 0, 17.5), (-31.55, 0, 17.25), (-31.55, 0, 10.2),
        (-31.35, 0, 9.95), (-14.1, 0, 9.95), (-13, 0, 9.1),
    ], copper, contact_face=True)
    face = object_for(face)
    barrel = sculpture("PRO.C · forged receiver and extraction eye")
    lathe(barrel, [
        (-31.5, 0, 17), (-31, 0, 17.45), (-26, 0, 17.4), (-18, 0, 17),
        (11, 0, 15.7), (16, 0, 16.9), (20, 0.5, 16.5), (26, 2.5, 13), (29, 5, 10),
    ], steel)
    body = object_for(barrel, 68)
    rear = object_for(fork, 68)
    rear.data.materials[0] = steel
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.00565, depth=0.032,
        location=(0.038, 0, 0.009), rotation=(math.pi / 2, 0, 0))
    extraction_hole = bpy.context.object
    cut(rear, extraction_hole)
    bpy.data.objects.remove(extraction_hole, do_unlink=True)
    edge = rear.modifiers.new("Forged edge radius", "BEVEL")
    edge.width, edge.segments = 0.00052, 2
    edge.harden_normals = True
    bpy.context.view_layer.objects.active = rear
    bpy.ops.object.modifier_apply(modifier=edge.name)
    joint = body.modifiers.new("One-piece forging", "BOOLEAN")
    joint.operation = "UNION"
    joint.solver = "EXACT"
    joint.object = rear
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=joint.name)
    bpy.data.objects.remove(rear, do_unlink=True)

    socket = sculpture("Copper tenon clearance")
    lathe(socket, [(-33, 0, 10.36), (-31.2, 0, 10.36), (-30.8, 0, 10.12),
                   (-13.2, 0, 10.12), (-12.6, 0, 9.6)], steel)
    socket = object_for(socket)
    cut(body, socket)
    bpy.data.objects.remove(socket, do_unlink=True)

    cut(body, oak)
    pins = []
    for x, radius, half_length, mate, name in [
        (-22.1, 2.06, 16.85, face, "copper-head spring pin"),
        (2.3, 2.06, 15.88, oak, "shaft retaining pin"),
    ]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=(radius + 0.04) / 1000,
            depth=0.046, location=(x / 1000, 0, 0), rotation=(math.pi / 2, 0, 0))
        bore = bpy.context.object
        for part in [body, mate]:
            cut(part, bore)
        bpy.data.objects.remove(bore, do_unlink=True)
        pin = sculpture("PRO.C · " + name)
        sleeve(pin, x, radius, 1.42, half_length, hardware)
        pins.append(object_for(pin))
    return [body, face, *pins]
