import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

here = Path(__file__).resolve().parent
root = here.parents[1]
sys.path.insert(0, str(here))
from product_workshop import Product

reference = root / ".references/02-家具与灯具/壁灯与工作照明/Astro Mondrian 600 Wall Mount 1374042"
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "Astro Mondrian 600 • 1374042"
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
fixture = Product("Astro Mondrian 600")


def material(name, hex_color, roughness, metal):
    mat = bpy.data.materials.new(name)
    linear = [((int(hex_color[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4)]
    mat.diffuse_color = (*linear, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    return mat


shell = material("Graphite powder-coated aluminium", "343332", 0.56, 0.30)
grain = bpy.data.images.new("Fine polyester powder coat • roughness", 96, 96, alpha=False)
grain.colorspace_settings.name = "Non-Color"
rng = np.random.default_rng(1374042)
roughness = np.clip(rng.normal(0.57, 0.037, (96, 96)), 0.45, 0.69)
pixels = np.ones((96, 96, 4), dtype=np.float32)
pixels[:, :, :3] = roughness[:, :, None]
grain.pixels.foreach_set(pixels.ravel())
grain.pack()
texture = shell.node_tree.nodes.new("ShaderNodeTexImage")
texture.image = grain
mapping = shell.node_tree.nodes.new("ShaderNodeMapping")
mapping.inputs["Scale"].default_value = (16, 16, 1)
uv = shell.node_tree.nodes.new("ShaderNodeTexCoord")
shell.node_tree.links.new(uv.outputs["UV"], mapping.inputs["Vector"])
shell.node_tree.links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
shell.node_tree.links.new(texture.outputs["Color"], shell.node_tree.nodes["Principled BSDF"].inputs["Roughness"])
steel = material("Blackened steel fasteners", "494947", 0.31, 0.76)
gasket = material("Recessed black seals", "181818", 0.74, 0.04)
reflector = material("Anodised aluminium optic channel", "aeaaa0", 0.28, 0.81)
opal = material("Mondrian opal diffuser", "f1e7d5", 0.44, 0.02)
shader = opal.node_tree.nodes.get("Principled BSDF")
shader.inputs["Emission Color"].default_value = (1.0, 0.64, 0.31, 1.0)
shader.inputs["Emission Strength"].default_value = 0.9


def block(name, mat, center, size, bevel):
    return fixture.block(name, mat.name, center, size, bevel)


def rod(name, mat, start, end, radius, sides=28):
    return fixture.rod(name, mat.name, start, end, radius, sides=sides)


block("Recessed wall shoe", gasket, (0, 0, 0.0015), (0.106, 0.048, 0.003), 0.0008)
block("Die-cast driver cover", shell, (0, 0, 0.0155), (0.115, 0.055, 0.028), 0.00135)
block("Projecting square-section arm", shell, (0, 0.0202, 0.0900), (0.0095, 0.0095, 0.123), 0.0007)
block("Compression ferrule", gasket, (0, 0.0202, 0.0298), (0.0118, 0.0118, 0.0023), 0.0006)
for x in (-0.039, 0.039):
    rod("Top retaining screw", steel, (x, 0.02755, 0.014), (x, 0.02775, 0.014), 0.0023)
    block("Slotted screw recess", gasket, (x, 0.02783, 0.014), (0.0032, 0.0001, 0.0006), 0.0001)

head_tilt = math.radians(21)
co, si = math.cos(head_tilt), math.sin(head_tilt)


def head(x, height, depth):
    return (x, 0.0148 + co * height - si * depth, 0.168 + si * height + co * depth)


def extrusion(name, mat, left, right, profile, bevel):
    verts = [head(x, height, depth) for x in (left, right) for height, depth in profile]
    n = len(profile)
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    obj = fixture.surface(name, mat.name, verts, faces)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    modifier = obj.modifiers.new("Extruded edge radii", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    modifier.harden_normals = True
    obj.modifiers.new("Flat profile normals", "WEIGHTED_NORMAL")
    return obj


profile = [
    (0.008, -0.0119), (0.008, 0.0119), (0.0068, 0.0130), (-0.008, 0.0130),
    (-0.008, 0.0098), (-0.0051, 0.0098), (-0.0051, -0.0098), (-0.008, -0.0098),
    (-0.008, -0.0130), (0.0068, -0.0130),
]
extrusion("Extruded aluminium glare shield", shell, -0.2988, 0.2988, profile, 0.00042)
end = [(0.0077, -0.0119), (0.0077, 0.0119), (0.0067, 0.0127), (-0.0078, 0.0127),
       (-0.0078, -0.0127), (0.0067, -0.0127)]
for sign in (-1, 1):
    limits = sorted((sign * 0.29888, sign * 0.300))
    extrusion("Press-fit graphite end cap", shell, *limits, end, 0.0003)
extrusion("Snap-in opal lens", opal, -0.2978, 0.2978, [
    (-0.0055, -0.00958), (-0.0055, 0.00958), (-0.00665, 0.00940), (-0.00665, -0.00940),
], 0.00026)
for side in (-1, 1):
    depth = side * 0.00965
    extrusion("Optic retaining rail", reflector, -0.2978, 0.2978, [
        (-0.0052, depth - 0.0002), (-0.0052, depth + 0.0002),
        (-0.0068, depth + 0.0002), (-0.0068, depth - 0.0002),
    ], 0.00008)
for x in (-0.0044, 0.0044):
    block("Tilt yoke cheek", shell, (x, 0.019, 0.151), (0.0029, 0.0112, 0.0126), 0.0014)
rod("Tilt hinge cross pin", steel, (-0.0061, 0.0189, 0.153), (0.0061, 0.0189, 0.153), 0.0035)
for x in (-0.0063, 0.0063):
    rod("Hex key pivot recess", gasket, (x, 0.0189, 0.153),
        (x * 1.01, 0.0189, 0.153), 0.00155, 6)
rod("Centre hinge tongue", shell, (0, 0.0189, 0.152), head(0, 0.0035, -0.009), 0.0046)

for finish, parts in fixture.parts.items():
    for part in parts:
        part.data.materials.append(bpy.data.materials[finish])
bpy.ops.object.select_all(action="DESELECT")
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            region = area.spaces.active.region_3d
            region.view_distance = 0.87
            region.view_location = (0, -0.090, 0.012)
            region.view_rotation = Vector((0.47, 0.85, -0.26)).to_track_quat("-Z", "Y")
            area.spaces.active.shading.type = "MATERIAL"
            area.spaces.active.shading.color_type = "MATERIAL"
            area.spaces.active.overlay.show_overlays = False
scene["product"] = "Astro Mondrian 600 Wall Mount, Matt Black 1374042"
scene["referenceDimensionsMm"] = [600, 55, 183]
scene["source"] = "https://www.astrolighting.com/products/1374042-mondrian-600-led"
authoring = reference / "Blender/astro-mondrian-600.blend"
authoring.parent.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(authoring), compress=True)
bpy.ops.export_scene.gltf(
    filepath=str(root / "public/media/models/astro-mondrian-600.glb"), export_format="GLB",
    export_apply=True, export_animations=False, export_extras=False,
)
