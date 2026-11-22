import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from blender_mesh import write_mesh
from blender_parts import xyz

ROOT = SCRIPTS.parents[1]
PROOFS = ROOT / ".review/atelier/flight-sprite-proof"
DIVISIONS = 16
WIDTH_MM = 254
HEIGHT_MM = 182
THICKNESS_MM = 0.26


def front_and_normal(u, v):
    fore = max(0, (u - 0.55) / 0.45)
    foot = max(0, (0.53 - v) / 0.53)
    su, sv = math.sin(math.pi * u), math.sin(math.pi * v)
    cu, cv = math.cos(math.pi * u), math.cos(math.pi * v)
    curl = 1.68 * fore**2 * foot**2
    bow = 0.288 * su * sv
    dx = (3.36 * fore * foot**2 / 0.45 + 0.288 * math.pi * cu * sv) / WIDTH_MM
    dy = (-3.36 * foot * fore**2 / 0.53 + 0.288 * math.pi * su * cv) / HEIGHT_MM
    front = Vector(((u - 0.5) * WIDTH_MM, (v - 0.5) * HEIGHT_MM, -0.64 + curl + bow))
    return front, Vector((-dx, -dy, 1)).normalized()


def printed_stock():
    stock = bpy.data.materials.new("Cotton proof stock · original bilingual pixel artwork")
    stock.use_nodes = True
    nodes, links = stock.node_tree.nodes, stock.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = 0.93
    mix = nodes.new("ShaderNodeMixRGB")
    switch = nodes.new("ShaderNodeValue")
    switch.label = "Artwork language · English 0 / 中文 1"
    switch.outputs[0].default_value = 0
    links.new(switch.outputs[0], mix.inputs[0])
    for i, locale in enumerate(("en", "zh"), start=1):
        path = PROOFS / f"proof-{locale}.png"
        if not path.exists():
            raise FileNotFoundError("Bake the original artwork with scripts/assets/bake-sprite-proof.mjs first")
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(path))
        node.image.pack()
        node.label = "Original studio proof · " + locale
        links.new(node.outputs["Color"], mix.inputs[i])
    links.new(mix.outputs["Color"], shader.inputs["Base Color"])
    return stock


def paper_shell():
    n = DIVISIONS + 1
    layer = n * n
    points, faces, charts = [], [], []
    for reverse in (False, True):
        for row in range(n):
            for col in range(n):
                p, normal = front_and_normal(col / DIVISIONS, row / DIVISIONS)
                if reverse:
                    p -= THICKNESS_MM * normal
                points.append(xyz(p))
        for row in range(DIVISIONS):
            for col in range(DIVISIONS):
                a = row * n + col
                quad = (a, a + 1, a + n + 1, a + n)
                for triangle in (quad[:3], (quad[0], quad[2], quad[3])):
                    faces.append(tuple(i + layer for i in reversed(triangle)) if reverse else triangle)
                    charts.append("back" if reverse else "printed")
    outline = [*range(n), *(r * n + n - 1 for r in range(1, n))]
    outline.extend((n - 1) * n + c for c in reversed(range(n - 1)))
    outline.extend(r * n for r in reversed(range(1, n - 1)))
    for a, b in zip(outline, outline[1:] + outline[:1]):
        faces.append((b, a, a + layer, b + layer))
        charts.append("edge")
    data = bpy.data.meshes.new("Trimmed proof · matched front, reverse and cut perimeter")
    data.from_pydata(points, [], faces)
    data.update()
    data.materials.append(printed_stock())
    texcoords = data.uv_layers.new(name="Signed face and unprinted stock")
    for polygon, chart in zip(data.polygons, charts):
        polygon.use_smooth = chart != "edge"
        for li in polygon.loop_indices:
            i = data.loops[li].vertex_index % layer
            u, v = (i % n) / DIVISIONS, (i // n) / DIVISIONS
            if chart == "printed":
                atlas_v = 1 - (1 - v) * 734 / 768
            else:
                atlas_v = (4 + v * 22) / 768
            texcoords.uv[li].vector = (u, atlas_v)
    obj = bpy.data.objects.new("Orbital Patrol · cotton proof paper", data)
    collection = bpy.data.collections.new("Flight sprite proofs · editable paper")
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    obj["Trim mm"] = [WIDTH_MM, HEIGHT_MM]
    obj["Stock caliper mm"] = THICKNESS_MM
    return obj


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    paper = paper_shell()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    bpy.context.view_layer.update()
    print(write_mesh(paper, ROOT / "public/media/models/stationery/flight-sprite-proof.mesh"))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(PROOFS / "flight-sprite-proof.blend"), compress=True)
