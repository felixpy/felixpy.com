import math
import random
import struct
import zlib

import bpy
from mathutils import Matrix, Vector
from product_workshop import Product, finish_material, xyz


def aluminium(out):
    size = 192
    noise = random.Random(202611)
    ridges = [noise.uniform(-1, 1) for _ in range(size)]
    pixels = bytearray()
    for y in range(size):
        ridge = 15 * ridges[y] + 5 * ridges[(y + 1) % size]
        pixels.append(0)
        for x in range(size):
            ripple = 2.7 * math.sin(math.tau * (3 * x + y) / size)
            pixels.append(round(204 + ridge + ripple + noise.uniform(-3, 3)))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    path = out.parents[1] / "materials/tolomeo-axial-grain.png"
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels, 9))
        + chunk(b"IEND", b"")
    )
    mat = finish_material("satin").copy()
    mat.name = "extrusion"
    shader = mat.node_tree.nodes["Principled BSDF"]
    alloy = [((v / 255 + 0.055) / 1.055) ** 2.4 for v in (193, 196, 194)] + [1]
    shader.inputs["Base Color"].default_value = alloy
    shader.inputs["Metallic"].default_value = 0.96
    (
        shader.inputs.get("Anisotropic") or shader.inputs["Anisotropic IOR Level"]
    ).default_value = 0.16
    texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(path), check_existing=True)
    texture.image.colorspace_settings.name = "Non-Color"
    texture.image.pack()
    scale = mat.node_tree.nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = 0.40
    mat.node_tree.links.new(texture.outputs["Color"], scale.inputs[0])
    mat.node_tree.links.new(scale.outputs[0], shader.inputs["Roughness"])


def arm(lamp, a, b):
    axis = (b - a).normalized()
    across = Vector((-axis.y, axis.x, 0))
    width = Vector((0, 0, 1))
    length = (b - a).length
    rings = [
        (0, 0.0034, 0.0037),
        (0.016, 0.0042, 0.0045),
        (0.022, 0.0044, 0.0047),
        (0.023, 0.0066, 0.0081),
        (0.025, 0.0070, 0.0084),
        (length - 0.029, 0.0061, 0.0074),
        (length - 0.027, 0.0058, 0.0071),
        (length - 0.026, 0.0038, 0.0043),
        (length, 0.0031, 0.0035),
    ]
    sides = 36
    vertices = [
        a
        + axis * offset
        + across * rx * math.cos(math.tau * i / sides)
        + width * rz * math.sin(math.tau * i / sides)
        for offset, rx, rz in rings
        for i in range(sides)
    ]
    faces = [
        (
            j * sides + i,
            j * sides + (i + 1) % sides,
            (j + 1) * sides + (i + 1) % sides,
            (j + 1) * sides + i,
        )
        for j in range(len(rings) - 1)
        for i in range(sides)
    ]
    body = lamp.surface(
        "Drawn elliptical aluminium arm with turned sleeve ends",
        "extrusion",
        vertices,
        faces,
        True,
    )
    uv = body.data.uv_layers.active.data
    for face in body.data.polygons:
        row, side = divmod(face.index, sides)
        for loop, (r, a) in zip(
            face.loop_indices,
            [(row, side), (row, side + 1), (row + 1, side + 1), (row + 1, side)],
        ):
            uv[loop].uv = (rings[r][0] / 0.032, a / sides * 1.5)


def bearing(lamp, center, radius):
    x, y, _ = center
    lamp.rod(
        "Cast pivot shoulder",
        "alloy",
        (x, y, -0.0076),
        (x, y, 0.0076),
        radius,
        sides=48,
    )
    for s in [-1, 1]:
        segments = 48
        rings = [
            (1, 0.00759),
            (0.98, 0.00776),
            (0.90, 0.00815),
            (0.80, 0.00838),
            (0.71, 0.00842),
        ]
        verts = [
            (
                x + radius * r * math.cos(i * math.tau / segments),
                y + radius * r * math.sin(i * math.tau / segments),
                s * z,
            )
            for r, z in rings
            for i in range(segments)
        ]
        faces = [
            (
                j * segments + i,
                j * segments + (i + 1) % segments,
                (j + 1) * segments + (i + 1) % segments,
                (j + 1) * segments + i,
            )
            for j in range(len(rings) - 1)
            for i in range(segments)
        ]
        lamp.surface(
            "Turned shoulder with softened die-cast rim",
            "alloy",
            verts,
            faces if s > 0 else [f[::-1] for f in faces],
            True,
        )
        lamp.rod(
            "Dark pivot bushing",
            "black",
            (x, y, s * 0.00759),
            (x, y, s * 0.0085),
            radius * 0.735,
            sides=48,
        )
        lamp.rod(
            "Satin axle head",
            "steel",
            (x, y, s * 0.00842),
            (x, y, s * 0.0089),
            radius * 0.61,
            radius * 0.565,
            sides=48,
        )
        lamp.rod(
            "Hex drive recess",
            "black",
            (x, y, s * 0.00887),
            (x, y, s * 0.0090),
            radius * 0.18,
            sides=6,
        )


def cheek(lamp, a, b, width):
    direction = (b - a).normalized()
    across = Vector((-direction.y, direction.x, 0))
    outline = []
    for center, start in [(a, math.pi / 2), (b, -math.pi / 2)]:
        for i in range(13):
            angle = start + i * math.pi / 12
            outline.append(
                center
                + width * (direction * math.cos(angle) + across * math.sin(angle))
            )
    for s in [-1, 1]:
        core = (a + b) * 0.5
        profile = [
            (0.0034, 0.94),
            (0.00368, 1),
            (0.00525, 1),
            (0.00556, 0.989),
            (0.0058, 0.955),
        ]
        vertices = [
            core + (v - core) * scale + Vector((0, 0, z * s))
            for z, scale in profile
            for v in outline
        ]
        n = len(outline)
        faces = [
            tuple(reversed(range(n))),
            tuple(range((len(profile) - 1) * n, len(profile) * n)),
        ] + [
            (j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i)
            for j in range(len(profile) - 1)
            for i in range(n)
        ]
        lamp.surface(
            "Stamped yoke cheek",
            "alloy",
            vertices,
            faces if s > 0 else [f[::-1] for f in faces],
        )


def model_tolomeo(out, clamp=False):
    lamp = Product("tolomeo-clamp" if clamp else "tolomeo-table")
    aluminium(out)
    axis = -0.044
    if clamp:
        lamp.block("Upper jaw", "alloy", (axis, 0.006, 0), (0.068, 0.010, 0.047), 0.003)
        lamp.block(
            "Upper grip", "black", (axis, 0.001, 0), (0.059, 0.002, 0.041), 0.0008
        )
        lamp.block(
            "Spine of the table clamp",
            "alloy",
            (axis - 0.030, -0.030, 0),
            (0.007, 0.071, 0.047),
            0.0025,
        )
        lamp.block(
            "Lower jaw",
            "alloy",
            (axis - 0.002, -0.062, 0),
            (0.061, 0.009, 0.045),
            0.0025,
        )
        lamp.rod(
            "Threaded clamp screw",
            "alloy",
            (axis + 0.009, -0.086, 0),
            (axis + 0.009, -0.0395, 0),
            0.0035,
        )
        lamp.rod(
            "Clamping pad",
            "black",
            (axis + 0.009, -0.0425, 0),
            (axis + 0.009, -0.038, 0),
            0.014,
        )
        lamp.lathe(
            "Hand wheel",
            "black",
            (axis + 0.009, -0.081, 0),
            [
                (0, -0.007),
                (0.014, -0.007),
                (0.015, -0.005),
                (0.015, 0.002),
                (0.013, 0.003),
                (0, 0.003),
            ],
        )
        clamp_pivot = Vector(xyz((axis, 0, 0)))
        jaw_rotation = Matrix.Rotation(math.pi / 2 - 1.92, 4, "Z")
        jaw_mount = (
            Matrix.Translation(clamp_pivot)
            @ jaw_rotation
            @ Matrix.Translation(-clamp_pivot)
        )
        for parts in lamp.parts.values():
            for obj in parts:
                obj.matrix_world = jaw_mount @ obj.matrix_world
    else:
        lamp.lathe(
            "Non-slip base inset",
            "black",
            (0, 0, 0),
            [(0, 0), (0.079, 0), (0.081, 0.0018), (0.081, 0.0032), (0, 0.0032)],
            80,
        )
        lamp.lathe(
            "Polished weighted disc",
            "alloy",
            (0, 0, 0),
            [
                (0, 0.002),
                (0.0818, 0.002),
                (0.0841, 0.003),
                (0.085, 0.0054),
                (0.0848, 0.008),
                (0.0836, 0.0094),
                (0.0805, 0.0102),
                (0.008, 0.0108),
                (0, 0.0108),
            ],
            96,
        )
    lamp.lathe(
        "Tapered swivel socket",
        "alloy",
        (axis, 0, 0),
        [
            (0.012, 0.010),
            (0.013, 0.012),
            (0.011, 0.015),
            (0.009, 0.039),
            (0.0075, 0.040),
            (0, 0.040),
        ],
    )
    bottom = Vector((axis, 0.074, 0))
    elbow = Vector((0.001, 0.330, 0))
    upper = Vector((0.014, 0.345, 0))
    wrist = Vector((0.250, 0.443, 0))
    lamp.rod("Socket spindle", "alloy", (axis, 0.038, 0), bottom, 0.0042)
    arm(lamp, bottom, elbow)
    arm(lamp, upper, wrist)
    cheek(lamp, elbow, upper, 0.0055)
    cheek(lamp, wrist, Vector((0.237, 0.450, 0)), 0.0056)
    for joint, radius in [
        (bottom, 0.0068),
        (elbow, 0.0074),
        (upper, 0.0055),
        (wrist, 0.006),
    ]:
        bearing(lamp, joint, radius)
    lower_horn = Vector((bottom.x - 0.024, bottom.y + 0.031, 0.0048))
    upper_horn = Vector((elbow.x - 0.017, elbow.y + 0.045, 0.0048))
    lamp.rod("Lower balance lever", "alloy", bottom, lower_horn, 0.0027, 0.0022, 20)
    lamp.rod("Upper balance lever", "alloy", elbow, upper_horn, 0.0029, 0.0022, 20)
    lamp.rod(
        "Lower counterbalance strand",
        "steel",
        lower_horn,
        upper_horn,
        0.00052,
        sides=10,
    )
    lamp.rod(
        "Upper counterbalance strand",
        "steel",
        upper_horn,
        wrist + Vector((-0.007, 0.008, 0.0048)),
        0.00052,
        sides=10,
    )
    for point in [lower_horn, upper_horn, wrist + Vector((-0.007, 0.008, 0.0048))]:
        lamp.rod(
            "Cable anchor bushing",
            "steel",
            point - Vector((0, 0, 0.002)),
            point + Vector((0, 0, 0.002)),
            0.0028,
            sides=20,
        )
    assembled_arm = {obj for parts in lamp.parts.values() for obj in parts}
    h = (0.297, 0.405, 0)
    outer = [
        (0.022, 0.057),
        (0.024, 0.055),
        (0.025, 0.052),
        (0.047, 0.009),
        (0.050, 0.0055),
        (0.0515, 0.0038),
        (0.0518, 0.0017),
        (0.0512, 0.0002),
        (0.0495, 0),
    ]
    lamp.lathe("Drawn aluminium conical shade", "satin", h, outer[::-1], 96)
    lamp.lathe(
        "Rolled rim and reflector",
        "reflector",
        h,
        [
            (0, 0.054),
            (0.021, 0.054),
            (0.023, 0.051),
            (0.0482, 0.004),
            (0.050, 0.0025),
            (0.0495, 0),
        ],
        96,
    )
    lamp.lathe(
        "Ventilated crown",
        "satin",
        h,
        [
            (0.023, 0.055),
            (0.022, 0.057),
            (0.012, 0.058),
            (0.010, 0.057),
            (0.0095, 0.055),
        ],
        64,
    )
    lamp.lathe(
        "Light visible through crown", "opal", h, [(0.010, 0.054), (0, 0.054)], 48
    )
    lamp.rod(
        "Lamp tilt socket",
        "satin",
        (0.237, 0.449, 0),
        (0.281, 0.429, 0),
        0.013,
        0.016,
        48,
    )
    lamp.rod(
        "Hinge end cap", "satin", (0.232, 0.451, 0), (0.237, 0.449, 0), 0.009, 0.012
    )
    loop_x = h[0] - 0.0488
    bend_y = h[1] - 0.018
    bend_radius = 0.0028
    bend = [math.pi * i / 12 for i in range(13)]
    handle = [
        (h[1] + 0.006, -bend_radius, 0),
        *((bend_y - bend_radius * math.sin(a), -bend_radius * math.cos(a), a) for a in bend),
        (h[1] + 0.006, bend_radius, math.pi),
    ]
    wire = 0.00055
    sides = 12
    vertices = [
        (loop_x + wire * math.cos(t), y + wire * math.sin(t) * math.sin(a),
         z + wire * math.sin(t) * math.cos(a))
        for y, z, a in handle for t in (math.tau * j / sides for j in range(sides))
    ]
    faces = [
        (row * sides + j, row * sides + (j + 1) % sides,
         (row + 1) * sides + (j + 1) % sides, (row + 1) * sides + j)
        for row in range(len(handle) - 1) for j in range(sides)
    ]
    lamp.surface("Bent wire shade adjustment loop", "steel", vertices, faces, True)
    lamp.lathe(
        "Porcelain lampholder",
        "reflector",
        h,
        [(0.008, 0.050), (0.010, 0.045), (0.010, 0.037), (0.008, 0.034)],
    )
    lamp.lathe(
        "Frosted E14 bulb",
        "opal",
        h,
        [
            (0, 0.004),
            (0.005, 0.005),
            (0.011, 0.007),
            (0.015, 0.011),
            (0.016, 0.016),
            (0.015, 0.022),
            (0.011, 0.027),
            (0.009, 0.031),
            (0.007, 0.037),
        ],
        48,
    )
    if clamp:
        pivot = Vector(xyz(wrist))
        tilt = Matrix.Rotation(-0.18, 4, "X") @ Matrix.Rotation(
            0.502, 4, Vector((0, -1, 0))
        )
        mount = Matrix.Translation(pivot) @ tilt @ Matrix.Translation(-pivot)
        for parts in lamp.parts.values():
            for obj in parts:
                if obj not in assembled_arm:
                    obj.matrix_world = mount @ obj.matrix_world
    if clamp:
        scene = bpy.data.scenes.new("Artemide Tolomeo Micro, aluminium")
        scene.unit_settings.system = "METRIC"
        metals = {
            "alloy": ("c5c8c5", 0.25, 0.96),
            "satin": ("bec1be", 0.36, 0.84),
            "steel": ("a5a8a7", 0.25, 0.87),
        }
        for finish, pieces in lamp.parts.items():
            native = finish_material(finish).copy()
            native.name = "Tolomeo · " + finish
            shader = native.node_tree.nodes["Principled BSDF"]
            if finish in metals:
                color, rough, metal = metals[finish]
                rgba = [
                    ((int(color[i : i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4
                    for i in (0, 2, 4)
                ] + [1]
                shader.inputs["Base Color"].default_value = rgba
                shader.inputs["Metallic"].default_value = metal
                shader.inputs["Roughness"].default_value = rough
                (
                    shader.inputs.get("Anisotropic")
                    or shader.inputs["Anisotropic IOR Level"]
                ).default_value = 0
            for piece in pieces:
                copy = piece.copy()
                copy["tolomeoFinish"] = finish
                copy.data = piece.data.copy()
                copy.data.materials.clear()
                copy.data.materials.append(native)
                scene.collection.objects.link(copy)
        master = out.parents[3] / ".references/02-家具与灯具/台灯与夹灯/Artemide Tolomeo Micro/Blender/tolomeo-micro.blend"
        master.parent.mkdir(parents=True, exist_ok=True)
        bpy.data.libraries.write(
            str(master), {scene}, path_remap="RELATIVE_ALL", compress=True
        )
        bpy.data.scenes.remove(scene)
    lamp.export(out)
