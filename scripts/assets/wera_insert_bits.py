import math

import bpy
from mathutils import Matrix

from blender_parts import barrel, block, xyz


sizes = (
    ("PH", 1, 2.05, 2.15, "05072070001"),
    ("PH", 2, 2.60, 2.70, "05072072001"),
    ("PH", 3, 3.08, 3.08, "05072074001"),
    ("PZ", 1, 2.06, 2.15, "05072080001"),
    ("PZ", 2, 2.65, 2.70, "05072082001"),
    ("PZ", 3, 3.08, 3.08, "05072084001"),
    ("TX", 10, 1.370, 2.00, "05066485001"),
    ("TX", 15, 1.635, 2.00, "05066486001"),
    ("TX", 20, 1.930, 2.50, "05066487001"),
    ("TX", 25, 2.215, 2.50, "05066488001"),
)


def rings(name, levels, segments=72, cyclic=False):
    vertices, faces = [], []
    for height, radius in levels:
        for i in range(segments):
            angle = i * math.tau / segments
            r = radius(angle) if callable(radius) else radius
            vertices.append(
                (r * math.cos(angle) / 1000, r * math.sin(angle) / 1000, height / 1000)
            )
    for j in range(len(levels) if cyclic else len(levels) - 1):
        nxt = (j + 1) % len(levels)
        for i in range(segments):
            k = (i + 1) % segments
            faces.append(
                (
                    j * segments + i,
                    j * segments + k,
                    nxt * segments + k,
                    nxt * segments + i,
                )
            )
    if not cyclic:
        faces.extend(
            (
                tuple(reversed(range(segments))),
                tuple(range((len(levels) - 1) * segments, len(vertices))),
            )
        )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def section(flat, limit):
    def hexagon(angle):
        offset = (angle + math.pi / 6) % (math.pi / 3) - math.pi / 6
        return min(flat / math.cos(offset), limit)

    return hexagon


def working_end(profile, radius, neck):
    if profile == "TX":

        def star(angle):
            phase = math.cos(6 * angle)
            return radius * (0.853 + 0.147 * phase + 0.012 * (1 - phase * phase))

        return [
            (16.4, neck),
            (18.6, neck),
            (20.3, lambda a: neck * 0.72 + star(a) * 0.28),
            (21.65, lambda a: neck * 0.12 + star(a) * 0.88),
            (22.3, star),
            (24.80, star),
            (25, lambda a: star(a) * 0.93),
        ]
    pz = profile == "PZ"

    def flutes(outer, valley, wing):
        def radial(a):
            angle = abs((a + math.pi / 4) % (math.pi / 2) - math.pi / 4)
            flank = min(1, wing / max(0.001, math.sin(angle)))
            primary = max(valley, flank)
            if pz:
                rib = max(0, 1 - (math.pi / 4 - angle) / 0.21)
                primary = max(primary, valley + (0.70 - valley) * rib)
            return outer * primary

        return radial

    return [
        (15.45, neck),
        (16.8, neck),
        (18.05, flutes(neck, 0.86, 0.48)),
        (19.4, flutes(radius * 1.02, 0.63, 0.32)),
        (20.55, flutes(radius, 0.42, 0.24)),
        (22.8, flutes(radius * 0.69, 0.38, 0.24)),
        (24.65, flutes(radius * (0.39 if pz else 0.31), 0.46, 0.29)),
        (25, flutes(radius * (0.32 if pz else 0.19), 0.48, 0.36)),
    ]


def lettering(parent, caption, center, size, side=0):
    angle = math.pi + side * math.pi / 3
    nx, ny = math.cos(angle), math.sin(angle)
    curve = bpy.data.curves.new(caption, "FONT")
    curve.body = caption
    curve.size = size / 1000
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.resolution_u = 2
    obj = bpy.data.objects.new(f"{parent.name} · {caption}", curve)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_basis = Matrix(
        (
            (0, ny, nx, nx * 0.00320),
            (0, -nx, ny, ny * 0.00320),
            (1, 0, 0, center / 1000),
            (0, 0, 0, 1),
        )
    )
    return obj


def finish(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return mat


def birch_finish():
    mat = finish("Holder · clear finished birch", (0.47, 0.31, 0.15), 0, 0.60)
    tree = mat.node_tree
    shader = tree.nodes["Principled BSDF"]
    coords = tree.nodes.new("ShaderNodeTexCoord")
    stretch = tree.nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (12, 1.45, 9)
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Distortion"].default_value = 0.22
    color = tree.nodes.new("ShaderNodeValToRGB")
    color.color_ramp.elements[0].color = (0.21, 0.122, 0.055, 1)
    color.color_ramp.elements[1].color = (0.49, 0.34, 0.19, 1)
    ridge = tree.nodes.new("ShaderNodeBump")
    ridge.inputs["Distance"].default_value = 0.000035
    ridge.inputs["Strength"].default_value = 0.13
    tree.links.new(coords.outputs["Generated"], stretch.inputs[0])
    tree.links.new(stretch.outputs[0], noise.inputs["Vector"])
    tree.links.new(noise.outputs["Fac"], color.inputs[0])
    tree.links.new(color.outputs[0], shader.inputs["Base Color"])
    tree.links.new(noise.outputs["Fac"], ridge.inputs["Height"])
    tree.links.new(ridge.outputs[0], shader.inputs["Normal"])
    return mat


def build_bit_rack():
    collection = bpy.data.collections.new("Wera · 25 mm insert bits and holder")
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new("Wera · ten insert bits in bored birch holder", None)
    collection.objects.link(root)
    wood = block("Birch rack · ten blind bores", (37, 15, 157), (0, 0, 0), 2.1)
    wood.parent = root
    bpy.context.view_layer.objects.active = wood
    for modifier in list(wood.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    steel, letters, seats = [], [], []
    for index, (profile, size, radius, neck, article) in enumerate(sizes):
        pos = (0.5, 0, (index - 4.5) * 14)
        cutter = barrel(
            "Blind bore", (pos[0], -0.55, pos[2]), (pos[0], 9, pos[2]), 4.06, 36
        )
        mod = wood.modifiers.new(f"Socket {index + 1:02}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        bpy.context.view_layer.objects.active = wood
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
        seat = rings(
            f"{profile}{size} · press-fit open ferrule",
            [
                (-0.35, 3.78),
                (-0.35, 4.03),
                (7.47, 4.03),
                (7.50, 4.35),
                (7.79, 4.35),
                (7.94, 4.22),
                (7.94, 3.93),
                (7.78, 3.78),
            ],
            36,
            True,
        )
        seat.parent = root
        seat.location = xyz(pos)
        seats.append(seat)
        side = "867/1" if profile == "TX" else "855/1" if profile == "PZ" else "851/1"
        shank = [
            (0, 2.83),
            (0.33, section(3.04, 3.12)),
            (0.95, section(3.175, 3.59)),
            (7.75, section(3.175, 3.59)),
            (8.10, section(3.175, 3.39)),
            (8.45, section(3.175, 3.59)),
            (14.10 if profile != "TX" else 15.15, section(3.175, 3.59)),
        ]
        bit = rings(
            f"Wera {side} · {profile}{size}", shank + working_end(profile, radius, neck)
        )
        bit.parent = root
        bit.location = xyz((pos[0], -0.55, pos[2]))
        bit["article"] = article
        bit["length_mm"] = 25
        bit["drive_profile"] = profile
        for poly in bit.data.polygons:
            if len(poly.vertices) == 4:
                poly.use_smooth = poly.index // 72 >= len(shank) and profile == "TX"
        steel.append(bit)
        letters.extend(
            (
                lettering(bit, f"{profile}{size}", 11.75, 1.58),
                lettering(bit, "Wera", 11.75, 1.34, 1),
            )
        )
    groups = {
        "workshop-bit-steel": (
            steel,
            finish("Wera · hardened tool steel", (0.40, 0.42, 0.40), 0.83, 0.35),
        ),
        "workshop-bit-mark": (
            letters,
            finish("Wera · dark shank markings", (0.034, 0.037, 0.032), 0.2, 0.63),
        ),
        "workshop-bit-ferrules": (
            seats,
            finish(
                "Holder · blackened socket ferrules", (0.044, 0.047, 0.045), 0.73, 0.46
            ),
        ),
        "workshop-birch": ([wood], birch_finish()),
    }
    for name, (parts, mat) in groups.items():
        for obj in parts:
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            obj["workshopBatch"] = name
            collection.objects.link(obj)
            bpy.context.collection.objects.unlink(obj)
    return root, collection, {key: group[0] for key, group in groups.items()}
