import math

import bpy
from mathutils import Matrix

from blender_parts import barrel, xyz


def caliper_finish(objects):
    calibration = {
        "beam": ("530 · longitudinal satin chrome", (0.31, 0.32, 0.30), 0.59, 0.80),
        "jaws": ("530 · ground measuring faces", (0.36, 0.38, 0.36), 0.42, 0.84),
        "etch": ("530 · recessed black scale", (0.019, 0.022, 0.020), 0.79, 0.0),
    }
    materials = {}
    for category, (name, color, roughness, metal) in calibration.items():
        material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        material.diffuse_color = (*color, 1)
        material.use_nodes = True
        node = material.node_tree.nodes["Principled BSDF"]
        node.inputs["Base Color"].default_value = (*color, 1)
        node.inputs["Roughness"].default_value = roughness
        node.inputs["Metallic"].default_value = metal
        if category == "beam" and not material.node_tree.nodes.get(
            "Longitudinal grain"
        ):
            tree = material.node_tree
            coords = tree.nodes.new("ShaderNodeTexCoord")
            stretch = tree.nodes.new("ShaderNodeVectorMath")
            stretch.operation = "MULTIPLY"
            stretch.inputs[1].default_value = (35, 1.3, 120)
            noise = tree.nodes.new("ShaderNodeTexNoise")
            noise.name = "Longitudinal grain"
            noise.inputs["Scale"].default_value = 1
            noise.inputs["Detail"].default_value = 2
            bounds = tree.nodes.new("ShaderNodeMapRange")
            bounds.inputs["To Min"].default_value = roughness - 0.055
            bounds.inputs["To Max"].default_value = roughness + 0.055
            tree.links.new(coords.outputs["Generated"], stretch.inputs[0])
            tree.links.new(stretch.outputs[0], noise.inputs["Vector"])
            tree.links.new(noise.outputs["Fac"], bounds.inputs["Value"])
            tree.links.new(bounds.outputs["Result"], node.inputs["Roughness"])
        materials[category] = material
    groups = {key: [] for key in calibration}
    for obj in objects:
        if obj.get("instrument") != "Mitutoyo 530-104" or obj.type not in (
            "MESH",
            "FONT",
            "CURVE",
        ):
            continue
        category = (
            "etch"
            if obj.get("workshopBatch") == "etch"
            else "jaws"
            if "measuring jaw" in obj.name or "knife-edge" in obj.name
            else "beam"
        )
        material = materials[category]
        if obj.material_slots:
            obj.material_slots[0].material = material
        else:
            obj.data.materials.append(material)
        groups[category].append(obj)
    assert all(groups.values())
    return groups


def mount_caliper(ink, shell, hanger, pitch):
    origin = 4 * pitch
    height = 2 * pitch - 0.35
    back, face = -10.2, -13.2
    opening = 12
    zero = 17.5
    wheel_x = 53 + opening
    steel = []
    markings = []

    def point(z, y, d):
        return (d, height + y, origin + z)

    def slab(name, outline, rear, front, bevel=0.09):
        obj = shell(
            name,
            [[point(z, y, d) for z, y in outline] for d in (rear, front)],
            radius=bevel,
        )
        steel.append(obj)
        return obj

    def measurement_jaw(name, contact, direction, sections):
        rings = []
        for y, outer, inner, width in sections:
            x = -11.7
            rings.append(
                [
                    point(contact + direction * z, y, d)
                    for z, d in [
                        (inner, x - width),
                        (outer * 0.6 + inner * 0.4, x - width),
                        (outer, x - width * 0.67),
                        (outer, x + width * 0.67),
                        (outer * 0.6 + inner * 0.4, x + width),
                        (inner, x + width),
                    ]
                ]
            )
        steel.append(shell(name, rings, radius=0.038))

    slab(
        "530-104 · 229 mm main beam and step datum",
        [(0, -8), (229, -8), (229, 8), (14, 8), (14, 10.7), (0, 10.7)],
        back,
        face,
    )
    for moving in [False, True]:
        name = "Movable" if moving else "Fixed"
        contact = 13.8 + (opening if moving else 0)
        side = 1 if moving else -1
        measurement_jaw(
            name + " · lapped OD measuring jaw",
            contact,
            side,
            [
                (-7.95, 13.8, 0.52, 1.50),
                (-15, 13.8, 0.52, 1.50),
                (-19.1, 12.6, 0.52, 1.5),
                (-20.2, 12.2, 0, 1.5),
                (-37.4, 6.04, 0, 1.48),
                (-40, 5.20, 0, 1.3),
                (-45.8, 3.2, 0, 0.99),
                (-47.91, 1.05, 0, 0.78),
                (-48, 0.65, 0, 0.76),
            ],
        )
        in_contact = 5.3 + (opening if moving else 0)
        measurement_jaw(
            name + " · relieved knife-edge ID jaw",
            in_contact,
            -side,
            [
                (7.98, 5.62, 0, 1.45),
                (12, 5.62, 0, 1.45),
                (16, 5.5, 1.05, 1.33),
                (18, 5.3, 1.02, 1.18),
                (20, 5.02, 0.12, 1.12),
                (23, 4.3, 0, 0.97),
                (27.2, 1.91, 0, 0.61),
                (28.96, 0.25, 0, 0.27),
            ],
        )
    slab(
        "Moving jaw · carriage connection",
        [
            (5.3 + opening, 8),
            (5.3 + opening, 13),
            (13.8 + opening, 13),
            (19 + opening, 9),
            (19 + opening, -9),
            (13.8 + opening, -12),
            (13.8 + opening, -8),
            (5.3 + opening, -8),
        ],
        -8.5,
        -14.05,
    )
    for side, label in [(-1, "metric"), (1, "inch")]:
        slab(
            "Slider · " + label + " raised vernier land",
            [
                (12 + opening, side * 6.6),
                (67.8 + opening, side * 6.6),
                (67.8 + opening, side * 10.6),
                (66.5 + opening, side * 11.95),
                (25.4 + opening, side * 11.95),
                (19 + opening, side * 13.7),
                (12 + opening, side * 13.7),
            ],
            -8.45,
            -15.16,
            0.13,
        )
    slab(
        "Back of sliding carriage",
        [
            (12 + opening, -11.6),
            (67.5 + opening, -10.6),
            (67.5 + opening, 10.6),
            (12 + opening, 11.6),
        ],
        -7.69,
        -9.99,
    )
    slab(
        "Knife for measuring depth · square end and undercut",
        [
            (1, -1.58),
            (229 + opening, -1.58),
            (229 + opening, 0.35),
            (226 + opening, 0.35),
            (225 + opening, 1.45),
            (1, 1.45),
        ],
        -9.41,
        -10.16,
        0.035,
    )
    for z in [221.5]:
        for y in [-5.45, 5.45]:
            steel.append(
                barrel(
                    "Depth guide · countersunk screw",
                    point(z, y, face + 0.05),
                    point(z, y, face - 0.12),
                    1.45,
                    28,
                    1.31,
                )
            )
    for begin, end, r in [
        (11.94, 14.25, 1.38),
        (14.2, 14.72, 2.93),
        (18.51, 18.97, 2.89),
    ]:
        steel.append(
            barrel(
                "Clamp screw · " + str(begin),
                point(44 + opening, begin, -11.7),
                point(44 + opening, end, -11.7),
                r,
                32,
            )
        )

    def knurl(name, levels, center, radius, depth, teeth):
        loops = []
        for y, taper in levels:
            row = []
            for i in range(teeth * 2):
                a = i * math.pi / teeth
                r = radius * taper - (i % 2) * depth
                row.append(point(center + r * math.sin(a), y, -11.7 + r * math.cos(a)))
            loops.append(row)
        steel.append(shell(name, loops))

    knurl(
        "Clamp screw · straight-cut knurl",
        [(14.6, 0.94), (14.88, 1), (18.36, 1), (18.64, 0.94)],
        44 + opening,
        3.13,
        0.22,
        32,
    )
    wheel = [(0, 0.78), (0.35, 0.98), (0.53, 1), (2.32, 1), (2.5, 0.98), (2.8, 0.78)]
    loops = []
    for d, factor in wheel:
        loops.append(
            [
                point(
                    wheel_x
                    + math.cos(a * math.pi / 36) * factor * (5.55 - 0.30 * (a % 2)),
                    -11.75
                    + math.sin(a * math.pi / 36) * factor * (5.55 - 0.30 * (a % 2)),
                    -9.7 - d,
                )
                for a in range(72)
            ]
        )
    steel.append(shell("Thumb roller · finely milled rim", loops))
    rotation = Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0))).to_quaternion()

    def text(s, z, y, d, size, align="CENTER"):
        font = bpy.data.curves.new("Scale lettering", "FONT")
        font.body = s
        font.size = size / 1000
        font.resolution_u = 2
        font.align_x = align
        obj = bpy.data.objects.new("530-104 · " + s, font)
        bpy.context.collection.objects.link(obj)
        obj.location = xyz(point(z, y, d))
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = rotation
        markings.append(obj)

    vertices, faces = [], []

    def tick(z, y, y2, d, width):
        i = len(vertices)
        lo, hi = sorted((y, y2))
        vertices.extend(
            xyz(point(q, r, d))
            for q, r in [
                (z - width / 2, lo),
                (z + width / 2, lo),
                (z + width / 2, hi),
                (z - width / 2, hi),
            ]
        )
        faces.append(tuple(i + k for k in range(4)))

    for i in range(151):
        h = 3.53 if i % 10 == 0 else 2.56 if i % 5 == 0 else 1.53
        tick(zero + i, -7.91, -7.91 + h, face - 0.036, 0.16 if i % 5 == 0 else 0.095)
        if i % 10 == 0:
            text(str(i), zero + i, -3.65, face - 0.036, 2.53)
    for i in range(97):
        h = (
            3.52
            if i % 16 == 0
            else 2.71
            if i % 8 == 0
            else 2.19
            if i % 4 == 0
            else 1.70
            if i % 2 == 0
            else 1.16
        )
        z = zero + i * 25.4 / 16
        tick(z, 7.91, 7.91 - h, face - 0.036, 0.14 if i % 4 == 0 else 0.095)
        if i % 16 == 0:
            text(str(i // 16), z, 2.02, face - 0.036, 2.47)
    for side, n, spacing in [(-1, 20, 1.95), (1, 8, 25.4 * 15 / 128)]:
        for i in range(n + 1):
            z = zero + opening + i * spacing
            major = i % (2 if side < 0 else 4) == 0
            h = 2.32 if major else 1.35
            tick(z, side * 6.67, side * (6.67 + h), -15.20, 0.12)
            if major:
                text(
                    str(i if side > 0 else i // 2),
                    z,
                    -11.35 if side < 0 else 9.71,
                    -15.20,
                    1.87,
                )
    text("Mitutoyo", 8.15, -1.2, face - 0.041, 2.65)
    text("530-104", 198.6, 1.75, face - 0.036, 2.2)
    text("0–150 mm", 198.6, -2.16, face - 0.036, 2.06)
    text("1/128 in", 64.4, 7.42, -15.20, 1.9)
    text("0.05 mm", 75.2, -10.58, -15.20, 1.58)
    for y in [-5.45, 5.45]:
        tick(221.5, y - 1.03, y + 1.03, face - 0.155, 0.28)
    mesh = bpy.data.meshes.new("Main scale and vernier lines")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new("530-104 · engraved dual scale", mesh)
    bpy.context.collection.objects.link(obj)
    markings.append(obj)
    for z in [8 * pitch, 12 * pitch]:
        hanger(z, 2 * pitch, 17)
    assembly = bpy.data.collections.new("Mitutoyo 530-104")
    bpy.context.scene.collection.children.link(assembly)
    for objects in (steel, markings):
        for obj in objects:
            obj["instrument"] = "Mitutoyo 530-104"
            obj["workshopBatch"] = "steel" if objects is steel else "etch"
            assembly.objects.link(obj)
            bpy.context.collection.objects.unlink(obj)
    groups = caliper_finish(assembly.objects)
    ink.extend(markings)
    return {
        "workshop-caliper-beam": groups["beam"],
        "workshop-caliper-jaws": groups["jaws"],
    }
