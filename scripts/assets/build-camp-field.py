import argparse
import math
import random
import runpy
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from io_scene_gltf2.io.exp import meshopt
from mathutils import Matrix, Vector


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
arguments = argparse.ArgumentParser()
arguments.add_argument("--output-dir", type=Path)
arguments.add_argument("--hammer-source", type=Path)
options = arguments.parse_args(
    sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
)
review = options.output_dir or root / ".review/atelier"
review.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
shared = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
sculpture, finish = shared["Sculpture"], shared["finish"]
textile = runpy.run_path(str(scripts / "field-textile.py"))["textile"]


def place(shape, position, yaw=0, roll=0, eye=(0, 0, 0), uv=0):
    obj = shape.finalize(uv_scale=uv)
    orientation = Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(roll, 3, "Y")
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = orientation.to_quaternion()
    x, h, d = position
    ex, eh, ed = eye
    obj.location = (Vector((x, -d, h)) - orientation @ Vector((ex, -ed, eh))) / 1000
    return obj


def oak_pattern(name, rgb):
    size = 192
    rng = random.Random(612)
    pixels = []
    pattern = bpy.data.images.new(name, width=size, height=size)
    for y in range(size):
        for x in range(size):
            a, b = math.tau * x / size, math.tau * y / size
            growth = 0.5 + 0.5 * math.cos(
                17 * a + 0.8 * math.sin(b) + 0.32 * math.sin(a + 2 * b)
            )
            rays = (
                max(0, math.cos(54 * a + 1.9 * math.sin(b) - 0.3 * math.sin(3 * b)))
                ** 18
            )
            lum = 0.98 + 0.08 * growth - 0.08 * rays + rng.uniform(-0.017, 0.017)
            pixels.extend([min(1, max(0, c * lum / 255)) for c in rgb] + [1])
    pattern.pixels.foreach_set(pixels)
    return pattern


def grain(mat, name, rgb, kind):
    if kind == "suede":
        pattern = bpy.data.images.load(str(scripts / "field-suede.png"))
        pattern.name = name
        pattern.pack()
        pattern.filepath = f"//{name}.png"
        for packed in pattern.packed_files:
            packed.filepath = pattern.filepath
    else:
        pattern = oak_pattern(name, rgb)
        pattern.pack()
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = pattern
    bsdf = nodes.get("Principled BSDF")
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if kind == "suede":
        image = bpy.data.images.load(
            str(root / "public/media/materials/field-leather-normal.webp")
        )
        image.colorspace_settings.name = "Non-Color"
        image.pack()
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        bump = nodes.new("ShaderNodeNormalMap")
        bump.inputs["Strength"].default_value = 0.13
        links.new(tex.outputs["Color"], bump.inputs["Color"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


model_pegs = runpy.run_path(str(scripts / "camp-pegs.py"))["model_pegs"]
if options.hammer_source:
    parts = model_pegs(sculpture, finish, place, textile, grain, hammer_only=True)
    runpy.run_path(str(scripts / "peg-hammer-head.py"))["save_source"](parts, options.hammer_source)
    sys.exit(0)

runpy.run_path(str(scripts / "fireside-gloves.py"))["model_gloves"](
    sculpture, finish, place, grain
)
runpy.run_path(str(scripts / "camp-stuff-sack.py"))["model_sack"](
    sculpture, finish, place, textile
)
packed_shafts = runpy.run_path(str(scripts / "trail-cork.py"))["model_poles"](
    sculpture, finish, place, textile, shared["letters"]
)
model_pegs(sculpture, finish, place, textile, grain)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(review / "camp-field-equipment.blend"))
for shaft, visible_height in packed_shafts:
    mesh = bmesh.new()
    mesh.from_mesh(shaft.data)
    inside = shaft.data.attributes.get("insideInstalledJoint")
    occluded = [
        v
        for v in mesh.verts
        if v.co.z > visible_height + 1e-6 or (inside and inside.data[v.index].value)
    ]
    bmesh.ops.delete(mesh, geom=occluded, context="VERTS")
    mesh.to_mesh(shaft.data)
    mesh.free()
    if attribute := shaft.data.attributes.get("insideInstalledJoint"):
        shaft.data.attributes.remove(attribute)
target = (
    options.output_dir or root / "public/media/models"
) / "camp-field-equipment.glb"
meshopt.EXP_FILTER_BITS = 22
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_extras=True,
    export_animations=False,
    export_cameras=False,
    export_lights=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
)
