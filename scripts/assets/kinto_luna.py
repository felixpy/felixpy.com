import math
import sys
import json
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import xyz


OUTSIDE = [
    (0.75, 0), (0.75, 19), (0.63, 22.4), (0.22, 23.9), (0, 24.5),
    (0, 26.0), (0.28, 27.2), (1.0, 28.5), (2.0, 30.0), (3.8, 32.1),
    (6.5, 34.6), (9.7, 36.4), (12.6, 37.2), (15.9, 37.5), (19.3, 37.35),
    (24.0, 36.8), (32, 35.6), (40, 33.9), (47, 31.9), (52, 30.35),
    (54.7, 29.92), (56.6, 29.95), (59.0, 30.5), (61.8, 32.0),
    (64.4, 34.0), (66.55, 36.15), (67.85, 37.65), (68.55, 38.2),
    (68.9, 38.14), (69.01, 37.77), (68.89, 37.17),
]
INSIDE = [
    (4.25, 0), (4.25, 15), (4.6, 22), (5.1, 25), (6.3, 28),
    (8.6, 30.1), (12.4, 32.0), (16.0, 33), (23, 32.8), (35, 31.3),
    (45, 29.3), (51, 27.8), (54.4, 27.0), (56.4, 27.0), (60.0, 28.2),
    (63.5, 30.65), (66.7, 33.9), (68.0, 35.61), (68.65, 36.73),
]
PLATE = [
    (61.83, 6.2), (61.6, 6.35), (61.58, 6.62), (61.78, 6.84), (62.4, 7.29),
    (63.25, 8.75), (64.26, 11.5), (65.67, 16.8), (67.03, 23.0), (68.25, 29.5),
    (69.15, 35), (69.61, 38.45), (69.72, 39.58), (69.84, 39.9), (70, 40),
    (69.65, 40), (69.36, 39.8), (69.1, 39.28), (68.98, 38.4), (68.9, 37.6),
    (68.65, 35.7), (67.65, 29.4), (66.41, 22.9), (65.05, 16.7), (63.66, 11.45),
    (62.68, 8.75), (61.8, 7.35), (61.17, 6.94), (60.98, 6.55), (61.03, 6.3),
    (61.28, 6.15),
]


def revolution(name, profile, closed=False):
    data = bpy.data.meshes.new(name)
    vertices, rings, faces = [], [], []
    count = 96
    for height, radius in profile:
        ring = []
        for i in range(count if radius else 1):
            angle = math.tau * i / count
            ring.append(len(vertices))
            vertices.append(xyz((radius * math.cos(angle), height, radius * math.sin(angle))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:] + ([rings[0]] if closed else [])):
        for i in range(count):
            j = (i + 1) % count
            if len(a) == 1:
                faces.append((a[0], b[i], b[j]))
            elif len(b) == 1:
                faces.append((a[i], b[0], a[j]))
            else:
                faces.append((a[i], b[i], b[j], a[j]))
    data.from_pydata(vertices, [], faces)
    data.update()
    uv = data.uv_layers.new(name="Axial brush projection")
    for poly in data.polygons:
        poly.use_smooth = True
        for loop in poly.loop_indices:
            vertex = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (0.5 + vertex.x / 0.08, 0.5 + vertex.y / 0.08)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj["sectionRings"] = [ring[0] for ring in rings]
    obj["closedSection"] = closed
    return obj


def material(name, color, roughness, metallic=0.0, transmission=0.0, ior=1.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Transmission Weight"].default_value = transmission
    shader.inputs["IOR"].default_value = ior
    return mat


def water_volume():
    level = 36.0
    wall = [(h + 0.09, max(0, r - 0.07)) for h, r in INSIDE if h < level]
    contact = 31.3 + (29.3 - 31.3) * (37.05 - 35) / 10 - 0.07
    return revolution("Water | wetted interior and capillary meniscus", wall + [
        (37.05, contact), (36.73, contact - 0.13), (36.37, contact - 0.48),
        (36.10, contact - 0.98), (level, contact - 1.8), (level, 0),
    ])


def bottom_mark():
    curve = bpy.data.curves.new("Base signature", "FONT")
    curve.body = "KINTO"
    curve.size = 0.00260
    curve.space_character = 1.04
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new("Underside | etched KINTO signature", curve)
    bpy.context.collection.objects.link(obj)
    obj.location.z = 0.000735
    obj.rotation_euler.x = math.pi
    return obj


def build_vase():
    glass = material("Brown soda glass | KINTO 20332", (0.94, 0.82, 0.65), 0.075, transmission=1, ior=1.515)
    water = material("Clear water | meniscus", (0.96, 0.99, 1.0), 0.055, transmission=1, ior=1.333)
    brass = material("Hairline brass | formed sheet", (0.67, 0.51, 0.28), 0.33, metallic=0.93)
    ink = material("Fine grey base stamp", (0.22, 0.20, 0.16), 0.61)
    wave = brass.node_tree.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"
    wave.rings_direction = "Z"
    wave.inputs["Scale"].default_value = 30
    coord = brass.node_tree.nodes.new("ShaderNodeTexCoord")
    offset = brass.node_tree.nodes.new("ShaderNodeVectorMath")
    offset.operation = "SUBTRACT"
    offset.inputs[1].default_value = (0.5, 0.5, 0)
    brass.node_tree.links.new(coord.outputs["UV"], offset.inputs[0])
    brass.node_tree.links.new(offset.outputs[0], wave.inputs["Vector"])
    mapping = brass.node_tree.nodes.new("ShaderNodeMapRange")
    mapping.inputs["To Min"].default_value = 0.29
    mapping.inputs["To Max"].default_value = 0.38
    brass.node_tree.links.new(wave.outputs["Fac"], mapping.inputs["Value"])
    brass.node_tree.links.new(mapping.outputs[0], brass.node_tree.nodes["Principled BSDF"].inputs["Roughness"])
    pieces = [
        ("v-glass", revolution("Vessel | flared rim and heavy soda-glass heel", OUTSIDE + INSIDE[::-1]), glass),
        ("v-brass", revolution("Insert | spun brass with rolled aperture", PLATE[::-1], True), brass),
        ("v-water", water_volume(), water),
        ("v-mark", bottom_mark(), ink),
    ]
    for key, obj, mat in pieces:
        obj.data.materials.append(mat)
        obj["sillPart"] = key
    return {key: [obj] for key, obj, _ in pieces}


def export_sections(pieces, path):
    sections = {}
    for key in ("v-glass", "v-brass", "v-water"):
        obj = pieces[key][0]
        rings = obj["sectionRings"]
        points = []
        for i in rings:
            point = obj.data.vertices[i].co
            points.append([round(1000 * point.x, 3), round(1000 * point.z, 3)])
        if obj["closedSection"]:
            points.append(points[0])
        sections[key] = points
    path.write_text(json.dumps(sections, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new("KINTO LUNA 20332 | 80 x 70 mm")
    bpy.context.scene.collection.children.link(collection)
    for items in build_vase().values():
        for obj in items:
            obj.users_collection[0].objects.unlink(obj)
            collection.objects.link(obj)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(sys.argv[-1]).resolve()))
