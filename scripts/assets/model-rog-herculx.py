import math
import subprocess
import sys
from pathlib import Path

import bpy
from io_scene_gltf2.io.exp import meshopt
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from product_solids import block, combine, edge, mesh, outline, pin

TITLE = "ROG Herculx XH01"
HEIGHT = 127.35
NATIVE = ROOT / ".review/atelier/pc-components/rog-herculx-xh01.blend"
REVIEW = ROOT / ".review/atelier/d50-herculx"
PUBLIC = ROOT / "public/media/models/rog-herculx-xh01.glb"
PRINT = REVIEW / "herculx-etch"


def finish(name, srgb, rough, metal, coat=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = tuple(((v / 255 + 0.055) / 1.055) ** 2.4 for v in bytes.fromhex(srgb)) + (1,)
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Coat Weight"].default_value = coat
    shader.inputs["Coat Roughness"].default_value = 0.2
    mat.diffuse_color = rgba
    return mat


def texture(mat, stem, target):
    tree = mat.node_tree
    mapping = tree.nodes.get("Printed faces")
    if mapping is None:
        mapping = tree.nodes.new("ShaderNodeUVMap")
        mapping.name = "Printed faces"
        mapping.uv_map = "UVMap"
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.extension = "EXTEND"
    tex.image = bpy.data.images.load(str(PRINT / (stem + ".png")))
    tex.image.pack()
    tree.links.new(mapping.outputs["UV"], tex.inputs["Vector"])
    tree.links.new(
        tex.outputs["Color"], tree.nodes.get("Principled BSDF").inputs[target]
    )


def plan(name, footprint, bottom, top, material, radius=0.35):
    vs = [(x, h, z) for h in (bottom, top) for x, z in footprint]
    n = len(footprint)
    fs = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    fs.extend((i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n))
    if (
        sum(
            x * v - u * z
            for (x, z), (u, v) in zip(footprint, footprint[1:] + footprint[:1])
        )
        < 0
    ):
        fs = [f[::-1] for f in fs]
    return edge(mesh(name, vs, fs, material), radius)


def guidex(u):
    return -104 + (u - 8) * (208 / 838)


def guidey(v):
    return HEIGHT - 5.65 - (v - 9) * (208 / 838)


def profile(name, points, front, thickness, material, bevel=0.25):
    coords = [(guidex(u), guidey(v)) for u, v in points]
    return edge(outline(name, coords, front - thickness, thickness, material), bevel)


def face_artwork(obj, normal, material, coordinates):
    faces = [
        face for face in obj.data.polygons if face.normal.dot(Vector(normal)) > 0.99999
    ]
    face = max(faces, key=lambda p: p.area)
    assert face.area > 0.0001, f"Incomplete artwork surface on {obj.name}"
    obj.data.materials.append(material)
    face.material_index = len(obj.data.materials) - 1
    uvs = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")
    for i in face.loop_indices:
        v = obj.data.vertices[obj.data.loops[i].vertex_index].co
        u, t = coordinates(1000 * v.x, 1000 * v.z, -1000 * v.y)
        uvs.data[i].uv = (u / 850, 1 - t / 225)


def front_uv(x, height, z):
    return 8 + (x + 104) * 838 / 208, 9 + (HEIGHT - 5.65 - height) * 838 / 208


def build():
    zinc = finish("Herculx graphite zinc casting", "444349", 0.36, 0.68)
    body = finish("Herculx molded black polycarbonate", "25242b", 0.43, 0.15)
    shaft = finish("Herculx anodized extension", "989ba3", 0.34, 0.78)
    chrome = finish("Herculx polished fasteners", "acb1ba", 0.23, 0.86)
    rubber = finish("Herculx elastomer lands", "202022", 0.73, 0.02)
    optical = finish("Herculx optical perimeter", "3c414a", 0.23, 0.15, 0.4)
    light = finish("Herculx Aura etched lightguide", "20222a", 0.44, 0)
    light.node_tree.nodes.get("Principled BSDF").inputs[
        "Specular IOR Level"
    ].default_value = 0.065
    printed_zinc = finish(
        "Herculx printed rail and bearing carriage", "444349", 0.36, 0.67
    )
    texture(printed_zinc, "rail-and-deck", "Base Color")
    texture(light, "unlit-acrylic", "Base Color")
    texture(light, "etched-spectrum", "Emission Color")
    light.node_tree.nodes.get("Principled BSDF").inputs[
        "Emission Strength"
    ].default_value = 1.2
    red = finish("Herculx level red liquid", "ac2015", 0.17, 0.14, 0.57)

    footprint = [
        (-13, 15),
        (-9, 19),
        (83, 23),
        (98, 18),
        (104, 9),
        (104, -10),
        (94, -23),
        (63, -23),
        (-8, -13),
        (-13, -7),
    ]
    plan("Zinc alloy wedge foot", footprint, 0.75, 4.1, zinc, 0.65)
    sole = [(45 + (x - 45) * 0.982, z * 0.958) for x, z in footprint]
    plan("Non-slip captive rubber sole", sole, 0, 0.76, rubber, 0.3)
    flange_edge = 17.6
    shim_outline = []
    for (x, z), (end_x, end_z) in zip(sole, sole[1:] + sole[:1]):
        if z <= flange_edge:
            shim_outline.append((x, z))
        if (z < flange_edge) != (end_z < flange_edge):
            along = (flange_edge - z) / (end_z - z)
            shim_outline.append((x + along * (end_x - x), flange_edge))
    backing = finish("GR701 leveling shim", "202124", 0.82, 0.0)
    shim = plan("GR701 deck leveling shim", shim_outline, -0.5, 0, backing, 0.05)
    deck = [
        (9, 18),
        (86, 22),
        (99, 16),
        (102, 9),
        (102, -10),
        (94, -21),
        (58, -21),
        (33, -15),
        (27, -9),
        (18, -5),
    ]
    plan("Stepped upper die casting", deck, 3.95, 6.2, zinc, 0.52)
    post = [
        (61, 12),
        (65, 16),
        (83, 16),
        (87, 12),
        (87, -9),
        (83, -12),
        (65, -12),
        (61, -8),
    ]
    plan("Satin zinc telescoping column", post, 5.8, HEIGHT - 35, shaft, 0.45)
    channel = [(64, -10), (65, -11.5), (83, -11.5), (84, -10), (84, -9), (64, -9)]
    plan("Extension column rear keyway", channel, 6.2, HEIGHT - 41, body, 0.22)
    marks = []
    for row in range(15):
        y = HEIGHT - 58 - row * 2.55
        marks.append(block("Ratchet buttress", 75, y, -12.1, 14, 0.69, 1.1, 0.25, body))
    combine("Hidden ratchet teeth on back of extension", marks)
    button = [(87, -2), (94, -6), (98, -4), (99, 5), (96, 9), (90, 9)]
    plan("One-touch spring release at base", button, 6.15, 8.1, body, 0.45)
    sleeve = [
        (58, 14),
        (64, 19),
        (84, 19),
        (91, 11),
        (91, -12),
        (85, -17),
        (64, -17),
        (58, -10),
    ]
    plan(
        "Sliding receiver and clamp casting",
        sleeve,
        HEIGHT - 66,
        HEIGHT - 10,
        body,
        0.7,
    )
    collar = [
        (61, 12),
        (64, 16),
        (84, 16),
        (87, 13),
        (87, -10),
        (83, -13),
        (65, -13),
        (61, -9),
    ]
    plan(
        "Wiper seal at column mouth", collar, HEIGHT - 66.5, HEIGHT - 65.5, rubber, 0.22
    )

    saddle = [
        (48, 9),
        (53, 14),
        (93, 14),
        (102, 7),
        (102, -11),
        (97, -21),
        (64, -22),
        (51, -17),
    ]
    plan("Rear movable bearing carrier", saddle, HEIGHT - 17, HEIGHT - 6.15, body, 0.85)
    saddle_top = [
        (51, 9),
        (55, 12),
        (93, 12),
        (99, 6),
        (99, -8),
        (96, -17),
        (89, -19),
        (64, -20),
        (54, -16),
    ]
    cap = plan(
        "Top deck of fine adjustment mechanism",
        saddle_top,
        HEIGHT - 6.3,
        HEIGHT - 5.63,
        zinc,
        0.3,
    )
    face_artwork(
        cap,
        (0, 0, 1),
        printed_zinc,
        lambda x, y, z: (80 + (x - 54) * 16, 95 + (z + 22) * 3.54),
    )
    pad = [
        (63, -8),
        (65, -6),
        (82, -6),
        (85, -9),
        (85, -18),
        (83, -20),
        (66, -20),
        (63, -17),
    ]
    wider = [(74 + (x - 74) * 1.12, -13 + (z + 13) * 1.10) for x, z in pad]
    plan("Elevated bearing boss", wider, HEIGHT - 5.83, HEIGHT - 1.65, body, 0.75)
    plan(
        "Replaceable raised GPU contact land", pad, HEIGHT - 1.68, HEIGHT, rubber, 0.30
    )

    knob = []
    for height_off, radius, amplitude in [
        (-12, 8.3, 0),
        (-11.3, 10.1, 0.1),
        (-10.75, 11, 0.45),
        (-7.3, 11, 0.45),
        (-6.8, 10.4, 0.10),
        (-6.55, 9.4, 0),
    ]:
        loop = []
        for i in range(176):
            t = i * math.tau / 176
            r = radius - amplitude * (1 - math.cos(t * 44))
            loop.append(
                (93 + r * math.cos(t), HEIGHT + height_off, -10 + r * math.sin(t))
            )
        knob += loop
    n = 176
    fs = [tuple(range(n)), tuple(reversed(range(5 * n, 6 * n)))]
    fs += [
        (j * n + i, (j + 1) * n + i, (j + 1) * n + (i + 1) % n, j * n + (i + 1) % n)
        for j in range(5)
        for i in range(n)
    ]
    wheel = mesh("Knurled silver height adjustment wheel", knob, fs, chrome)
    for poly in list(wheel.data.polygons)[2:]:
        poly.use_smooth = True

    backing = [
        (8, 9),
        (823, 9),
        (846, 31),
        (846, 132),
        (758, 223),
        (478, 223),
        (423, 163),
        (146, 163),
        (35, 49),
        (22, 49),
    ]
    profile("Rear structural shell of the cantilever", backing, 16.7, 6.7, body, 0.6)
    rail = [
        (8, 9),
        (823, 9),
        (846, 31),
        (846, 132),
        (758, 223),
        (719, 223),
        (810, 125),
        (810, 83),
        (793, 60),
        (429, 60),
        (410, 50),
        (41, 50),
        (24, 46),
    ]
    toprail = profile(
        "Chamfered top and diagonal end rail", rail, 22.15, 7.5, zinc, 0.56
    )
    face_artwork(toprail, (0, -1, 0), printed_zinc, front_uv)
    lip = [
        (22, 21),
        (820, 21),
        (834, 36),
        (834, 129),
        (748, 215),
        (740, 215),
        (824, 126),
        (824, 41),
        (817, 30),
        (31, 30),
    ]
    profile("Crisp rear seam of upper rail", lip, 15.0, 2.2, body, 0.3)
    window = [
        (38, 46),
        (410, 46),
        (430, 57),
        (792, 57),
        (815, 80),
        (815, 124),
        (724, 215),
        (485, 215),
        (423, 154),
        (146, 154),
    ]
    pane = profile(
        "Three millimetre optical side insert", window, 21.72, 3, optical, 0.25
    )
    face_artwork(pane, (0, -1, 0), light, front_uv)
    cradle = [
        (209, 153),
        (423, 153),
        (483, 216),
        (380, 216),
        (373, 211),
        (373, 177),
        (314, 177),
        (314, 212),
        (304, 218),
        (275, 217),
        (266, 212),
    ]
    profile("Detachable magnetic level cassette", cradle, 20.8, 11.2, body, 0.57)
    level_height = guidey(194)
    x0, x1 = guidex(312), guidex(376)
    pin(
        "Red fluid spirit level cartridge",
        (x0, level_height, 17.85),
        (x1, level_height, 17.85),
        3.66,
        red,
        48,
    )
    for x in [x0 + 1.3, x1 - 1.3]:
        pin(
            "Spirit vial retaining cap",
            (x - 1.2, level_height, 17.85),
            (x + 1.2, level_height, 17.85),
            3.94,
            chrome,
            48,
        )
    for x in [x0 + 5.5, x1 - 5.5]:
        pin(
            "Level calibration hairline",
            (x - 0.15, level_height, 17.85),
            (x + 0.15, level_height, 17.85),
            3.69,
            body,
            48,
        )
    vial = block(
        "Encapsulated spirit bubble",
        (x0 + x1) / 2,
        level_height + 1.73,
        20.9,
        4.1,
        1.4,
        0.9,
        0.4,
        chrome,
    )
    edge(vial, 0.24)
    for u, v in [(58, 38), (423, 99), (757, 182), (817, 45)]:
        x, y = guidex(u), guidey(v)
        pin("Back shell countersunk fastener", (x, y, 10.03), (x, y, 9.72), 1.53, zinc)
        pin("Torx socket", (x, y, 9.72), (x, y, 9.68), 0.61, body, 6)
    connector = block(
        "3-pin addressable input on reverse",
        83,
        HEIGHT - 32,
        -16.9,
        10,
        5.3,
        3.7,
        0.7,
        body,
    )
    edge(connector, 0.33)
    for dx in [-2.54, 0, 2.54]:
        pin(
            "Recessed contact",
            (83 + dx, HEIGHT - 32, -18.7),
            (83 + dx, HEIGHT - 32, -18.78),
            0.64,
            chrome,
            12,
        )
    return shim


def assemble():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    subprocess.run(
        [
            "uv",
            "--cache-dir",
            str(ROOT / ".review/uv-assets-cache"),
            "run",
            "--no-project",
            "--with",
            "pillow",
            "--",
            "python",
            str(HERE / "herculx-etch.py"),
            str(PRINT),
        ],
        check=True,
    )
    shim = build()
    coll = bpy.data.collections.new(TITLE)
    bpy.context.scene.collection.children.link(coll)
    parts = list(bpy.context.scene.objects)
    for part in parts:
        for old in list(part.users_collection):
            old.objects.unlink(part)
        coll.objects.link(part)
    NATIVE.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(NATIVE), compress=True)
    shell = combine(TITLE, [part for part in parts if part != shim])
    shim.select_set(True)
    bpy.context.view_layer.objects.active = shell
    meshopt.EXP_FILTER_BITS = 22
    bpy.ops.export_scene.gltf(
        filepath=str(PUBLIC),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(HERE / "pack-product-geometry.mjs"), str(PUBLIC)], check=True
    )


def render():
    bpy.ops.wm.open_mainfile(filepath=str(NATIVE))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1080, 760
    scene.render.resolution_percentage = 100
    world = bpy.data.worlds.new("Product surround")
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = (
        0.49,
        0.52,
        0.57,
        1,
    )
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.28
    scene.world = world
    block(
        "Review surface",
        0,
        -1.5,
        0,
        1450,
        3,
        1450,
        0.5,
        finish("Review gray", "686e79", 0.72, 0),
    )
    for loc, watts, size in [
        ((-0.18, -0.16, 0.36), 2.8, 0.22),
        ((0.25, 0.10, 0.25), 3.1, 0.19),
        ((-0.17, 0.15, 0.15), 1.2, 0.16),
    ]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.object
        lamp.data.energy, lamp.data.shape, lamp.data.size = watts, "DISK", size
        lamp.rotation_euler = (
            (Vector((0.01, 0, 0.06)) - lamp.location)
            .to_track_quat("-Z", "Y")
            .to_euler()
        )
    bpy.ops.object.camera_add(location=(0.19, -0.36, 0.198))
    camera = bpy.context.object
    camera.rotation_euler = (
        (Vector((0.0, 0, 0.059)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    camera.data.type, camera.data.ortho_scale, camera.data.clip_start = (
        "ORTHO",
        0.258,
        0.01,
    )
    scene.camera = camera
    REVIEW.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(REVIEW / "herculx-three-quarter.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    assemble()
    if "--render" in sys.argv:
        render()
