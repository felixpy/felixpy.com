import runpy
import subprocess
import tempfile
from pathlib import Path

import bpy

scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
archive = (
    project / ".references/05-摄影与陈列/录音与存储配件/CFexpress Type B card/Blender"
)
archive.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
tools = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))
slab, corners = tools["slab"], tools["corners"]
finish, Sculpture = sculpt["finish"], sculpt["Sculpture"]
card = Sculpture("256 GB CFexpress Type B · ProGrade Gold 1700")
alloy = finish("Satin stamped nickel jacket", "b6b8b9", 0.62, 0.37)
shell = finish("Black glass-filled polymer", "2b2a2b", 0.06, 0.63)
insert = finish("Recessed CFexpress connector", "131315", 0.04, 0.71)
gold = finish("Gold-plated contact beams", "b89a60", 0.75, 0.39)
front = finish("Gold 1700 rolled ink and clear laminate", "ffffff", 0.12, 0.43)
reverse = finish("Laser-marked rear housing", "ffffff", 0.06, 0.63)


def contour(cx, cz, width, depth, radius, height):
    return [(cx + x, height, cz + z) for x, z in corners(width, depth, radius, 8)]


def cover(row, material):
    card.add(row, [tuple(reversed(range(len(row))))], material, False)


def texture_uvs(mesh):
    uv = mesh.uv_layers.new(name="Label register")
    for polygon in mesh.polygons:
        material = mesh.materials[polygon.material_index]
        if material not in (front, reverse):
            continue
        for i in polygon.loop_indices:
            x, y, _ = mesh.vertices[mesh.loops[i].vertex_index].co
            if material == front:
                u = 0.5 + x * 1000 / 19.3
                v = 1 - ((-y * 1000 - 2.53) / 24.2 + 0.5) * 640 / 768
            else:
                u = 0.5 - x * 1000 / 20.2
                v = (0.5 + (y * 1000 + 13.6) / 4.1) * 128 / 768
            uv.data[i].uv = (u, v)


rear = contour(0, 0, 29.34, 38.30, 0.84, -1.9)
rear_print = contour(0, 13.6, 20.2, 4.1, 0.32, -1.9)
card.rings([rear, rear_print], shell, False, False)
cover(rear_print, reverse)
outer = contour(0, 0, 29.60, 38.50, 0.92, -1.57)
upper = contour(0, 0, 29.60, 38.50, 0.92, 1.48)
upper_roll = contour(0, 0, 29.35, 38.16, 0.82, 1.70)
card.rings([rear, outer], shell, True, False)
for i, (x, h, z) in enumerate(outer):
    end = (i + 1) % len(outer)
    if z < -19.24 and outer[end][2] < -19.24:
        continue
    card.add([outer[i], outer[end], upper[end], upper[i]], [(0, 1, 2, 3)], shell)
card.rings([upper, upper_roll], shell, True, False)
jacket = contour(0, 2.57, 26.88, 31.45, 1.08, 1.70)
shoulder = contour(0, 2.57, 26.66, 31.23, 1.0, 1.90)
well = contour(0, 2.53, 19.92, 24.82, 0.98, 1.90)
stock = contour(0, 2.53, 19.30, 24.20, 0.81, 1.76)
card.rings([upper_roll, jacket], shell, False, False)
card.rings([jacket, shoulder, well, stock], alloy, False, False)
cover(stock, front)
for sign in (-1, 1):
    for za, zb in [(-17.35, -10.26), (-5.12, 15.02)]:
        slab(
            card,
            14.35 * sign,
            (za + zb) / 2,
            0.76,
            zb - za,
            0.25,
            [(1.67, 0.07), (1.77, 0.0), (1.83, 0.06)],
            alloy,
        )
    slab(card, sign * 13.1, -18.30, 1.06, 1.86, 0.20, [(-1.57, 0), (1.48, 0)], insert)
for x in (-14, 14):
    slab(card, x, -17.83, 1.18, 2.64, 0.19, [(-1.5, 0.02), (1.45, 0.02)], shell)
connector = [(-12.64, -1.03), (12.64, -1.03), (12.64, 1.08), (-12.64, 1.08)]
face = [(-13.88, -1.57), (13.88, -1.57), (13.88, 1.48), (-13.88, 1.48)]
card.rings(
    [[(x, h, -19.25) for x, h in row] for row in (face, connector)], shell, False, False
)
card.rings(
    [[(x, h, z) for x, h in connector] for z in (-19.25, -16.81)], insert, False, False
)
cover([(x, h, -16.81) for x, h in connector], insert)
for x in runpy.run_path(str(scripts / "cfexpress-interface.py"))["CONTACT_CENTERS"]:
    slab(card, x, -17.83, 0.46, 1.58, 0.05, [(-1.03, 0), (-0.90, 0.018)], gold)
card.add(
    [(6.0, 1.73, -14.55), (9.73, 1.73, -14.55), (7.86, 1.73, -17.38)],
    [(0, 1, 2)],
    insert,
    False,
)

obj = card.finalize()
texture_uvs(obj.data)
obj["product"] = "ProGrade Digital CFexpress 2.0 Type B Gold 1700, 256 GB"
obj["specimenSerial"] = (
    "Illustrative 13-character serial in the manufacturer's 33A21B family"
)
with tempfile.TemporaryDirectory(dir=project / ".review") as tmp:
    image_path = Path(tmp) / "prograde-gold-1700.png"
    subprocess.run(
        ["node", str(scripts / "rasterize-prograde-label.mjs"), str(image_path)],
        check=True,
    )
    image = bpy.data.images.load(str(image_path))
    image.name = "ProGrade Gold 256 GB · original printed artwork"
    image.pack()
    image.filepath = "//prograde-gold-1700.png"
    for mat in (front, reverse):
        tree = mat.node_tree
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tree.links.new(
            tex.outputs["Color"], tree.nodes.get("Principled BSDF").inputs["Base Color"]
        )

bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = "METRIC"
bpy.ops.wm.save_as_mainfile(
    filepath=str(archive / "cfexpress-type-b.blend"), compress=True
)
target = project / "public/media/models/cfexpress-type-b.glb"
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_animations=False,
    export_lights=False,
    export_cameras=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
print(target.name, target.stat().st_size)
