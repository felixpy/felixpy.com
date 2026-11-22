import math
import subprocess
from pathlib import Path

import bpy
import bmesh


def spun(shape, profile, material, segments=96, emboss=None, closed_strips=None):
    vertices, rings, faces = [], [], []
    for h, r in profile:
        count = segments if r else 1
        rings.append(list(range(len(vertices), len(vertices) + count)))
        for i in range(count):
            a = math.tau * i / segments
            height, radius = emboss(h, r, a) if emboss else (h, r)
            vertices.append((radius * math.sin(a), height, radius * math.cos(a)))
    for lower, upper in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(lower) == 1:
                faces.append((lower[0], upper[j], upper[i]))
            elif len(upper) == 1:
                faces.append((lower[i], lower[j], upper[0]))
            else:
                faces.append((lower[i], lower[j], upper[j], upper[i]))
    shape.add(vertices, faces, material)
    if closed_strips is not None:
        shape.enclosed_faces = {
            i for i in range(len(faces)) if closed_strips(i // segments)
        }


def carry_handle(shape, material):
    path = []
    for side in (-1, 1):
        side_path = [(side * 29.85, 206.4), (side * 30.25, 208.4)]
        for i in range(13):
            a = math.radians(-20 + 110 * i / 12)
            side_path.append(
                (side * (30.7 + 4.87 * math.cos(a)), 223.51 + 4.87 * math.sin(a))
            )
        path.extend(side_path if side == -1 else reversed(side_path))
    rows = []
    for i, (x, h) in enumerate(path):
        prev, nex = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        dx, dh = nex[0] - prev[0], nex[1] - prev[1]
        span = math.hypot(dx, dh)
        row = []
        for j in range(20):
            a = j * math.tau / 20
            u, v = math.cos(a), math.sin(a)
            section = 1.62 * math.copysign(abs(u) ** 0.54, u)
            depth = (2.46 + 0.7 * max(0, (215 - h) / 9)) * math.copysign(
                abs(v) ** 0.54, v
            )
            row.append((x - dh / span * section, h + dx / span * section, depth))
        rows.append(row)
    shape.rings(rows, material)


def print_body(shape, ink):
    image = bpy.data.images.load(str(Path(__file__).with_name("snow-peak-aurora-print.png")))
    image.name = "TW-800-RA factory silk screen"
    image.pack()
    nodes = ink.node_tree.nodes
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.extension = "CLIP"
    shader = nodes.get("Principled BSDF")
    ink.node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    bottom, top = (1600 - 1517) / 6, (1600 - 1237) / 6
    points, uv, faces = [], [], []
    for column in range(25):
        u = column / 24
        x = (u - 0.5) * 40
        y = math.sqrt(40.13 ** 2 - x ** 2)
        for z, v in ((bottom, 0), (top, 1)):
            points.append((x, z, y))
            uv.append((u, v))
        if column:
            i = column * 2
            faces.append((i - 2, i, i + 1, i - 1))
    shape.add(points, faces, ink, True)
    obj = shape.finalize()
    layer = obj.data.uv_layers.new(name="Factory print")
    for polygon in obj.data.polygons:
        for index in polygon.loop_indices:
            layer.data[index].uv = uv[obj.data.loops[index].vertex_index]
    return obj

def thread(shape, material):
    profile = [
        (-1.0, -0.15),
        (-0.73, 0.25),
        (-0.38, 0.88),
        (-0.18, 1.01),
        (0.18, 1.01),
        (0.39, 0.88),
        (0.74, 0.24),
        (1.0, -0.15),
    ]
    rows = []
    for i in range(177):
        t = i / 176
        a = t * math.tau * 2.72
        ease = min(1, t / 0.055, (1 - t) / 0.055)
        z = 185.5 + 3.45 * a / math.tau
        rows.append(
            [
                (
                    (26.89 + dr * ease) * math.sin(a),
                    z + dh,
                    (26.89 + dr * ease) * math.cos(a),
                )
                for dh, dr in profile
            ]
        )
    shape.rings(rows, material)


def pressed_neck(h, r, angle):
    if not 183.5 <= h <= 187.5:
        return h, r
    t = angle / math.tau
    runout = max(0, (t - 0.92) / 0.08)
    lead = 3.45 * (t - 0.5 - runout * runout * (3 - 2 * runout))
    fade = max(0, min(1, t / 0.07, (0.92 - t) / 0.07))
    notch = max(0, 1 - (abs(h - 185.5) / 1.2) ** 2) ** 2
    return h + lead, r - 0.86 * notch * fade


def filter_surface(obj, interior):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    tag = mesh.faces.layers.int.get(".sealed interior")
    remove = [face for face in mesh.faces if bool(face[tag]) != interior]
    bmesh.ops.delete(mesh, geom=remove, context="FACES")
    mesh.faces.layers.int.remove(tag)
    mesh.to_mesh(obj.data)
    mesh.free()


def close_for_display(assembly):
    for obj in assembly.children_recursive:
        if ".sealed interior" in obj.data.attributes:
            filter_surface(obj, False)


def export_inside(assembly, target):
    bpy.ops.object.select_all(action="DESELECT")
    parts = []
    for obj in assembly.children_recursive:
        if ".sealed interior" not in obj.data.attributes:
            continue
        inside = bpy.data.objects.new(obj.name + " · open", obj.data.copy())
        inside["auroraFitting"] = obj["auroraFitting"]
        bpy.context.collection.objects.link(inside)
        filter_surface(inside, True)
        for color in list(inside.data.color_attributes):
            inside.data.color_attributes.remove(color)
        inside.select_set(True)
        parts.append(inside)
    bpy.ops.export_scene.gltf(
        filepath=str(target), export_format="GLB", use_selection=True, export_extras=True,
        export_animations=False, export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(["node", str(Path(__file__).with_name("pack-product-geometry.mjs")), str(target)], check=True)
    for obj in parts:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)


def finish_part(shape):
    obj = shape.finalize()
    tag = obj.data.attributes.new(".sealed interior", "INT", "FACE")
    for i in shape.enclosed_faces:
        tag.data[i].value = 1
    return obj


def vertex_colors(obj, material, color_fn):
    data = obj.data
    layer = data.color_attributes.new(
        name="Surface tint", type="BYTE_COLOR", domain="POINT"
    )
    tinted = {
        index
        for face in data.polygons
        if data.materials[face.material_index] == material
        for index in face.vertices
    }
    for v in data.vertices:
        tint = (
            color_fn(v.co.x * 1000, v.co.z * 1000, -v.co.y * 1000)
            if v.index in tinted
            else (1, 1, 1)
        )
        layer.data[v.index].color_srgb = (*tint, 1)
    nodes = material.node_tree.nodes
    color = nodes.new("ShaderNodeVertexColor")
    color.layer_name = layer.name
    material.node_tree.links.new(
        color.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"]
    )


def build(Sculpture, finish):
    titanium = finish("Aurora · satin titanium oxide", "ffffff", 0.78, 0.47)
    polymer = finish("Aurora · moulded graphite polypropylene", "282826", 0.015, 0.44)
    silicone = finish("Aurora · graphite silicone lip seal", "353633", 0, 0.68)
    ink = finish("Aurora · pale titanium print", "f2efe8", 0.13, 0.55)
    assembly = bpy.data.objects.new("Aurora 800 Rainbow · TW-800-RA", None)
    bpy.context.collection.objects.link(assembly)
    assembly["product"] = "snow-peak-tw800-ra"
    assembly["dimensionsMm"] = [80, 80, 230]
    body = Sculpture("Aurora · seamless variable-gauge titanium bottle")
    exterior = [
        (1.7, 0),
        (1.7, 26),
        (1.52, 31),
        (1.13, 33.9),
        (0.28, 35.8),
        (0, 36.9),
        (0.12, 37.7),
        (0.75, 38.7),
        (1.9, 39.5),
        (3.4, 39.93),
        (5, 40),
    ]
    exterior.extend((h, 40) for h in range(8, 160, 4))
    exterior.extend(
        [
            (161, 40),
            (163, 39.91),
            (164.5, 39.57),
            (166.6, 38.75),
            (169.7, 36.79),
            (175.4, 32.35),
            (178, 30.35),
            (179.7, 29.53),
            (181.45, 29.06),
            *(
                (185.5 + d, 28.85)
                for d in (-2, -1.2, -0.85, -0.45, 0, 0.45, 0.85, 1.2, 2)
            ),
            (189.4, 28.86),
            (201.9, 28.93),
            (202.42, 28.90),
            (202.55, 28.76),
        ]
    )
    interior = [(202.55, 28.28), (202.41, 28.13), (201.9, 28.13), (189.4, 28.06)]
    interior.extend((h, r - 0.8) for h, r in reversed(exterior) if 179.7 <= h < 189)
    interior.extend(
        [
            (175.4, 31.81),
            (169.7, 36.26),
            (166.6, 38.31),
            (164.5, 39.15),
            (163, 39.5),
            (161, 39.6),
            (5, 39.6),
            (3.45, 39.47),
            (2.42, 38.98),
            (1.65, 38.2),
            (1.12, 37.47),
            (1.0, 36.9),
            (1.17, 36.16),
            (2.05, 34.25),
            (2.49, 31.1),
            (2.7, 26),
            (2.7, 0),
        ]
    )
    spun(
        body,
        exterior + interior,
        titanium,
        emboss=pressed_neck,
        closed_strips=lambda i: i >= len(exterior),
    )
    shell = finish_part(body)
    tones = [
        (0, "157796"),
        (11, "14a8b9"),
        (54, "169dbf"),
        (73, "287fc4"),
        (90, "755ac1"),
        (106, "b749a8"),
        (119, "c96583"),
        (131, "c98e48"),
        (143, "d6b742"),
        (159, "d0c36a"),
        (174, "bfbd94"),
        (186, "bbc7b1"),
        (204, "c4cdbb"),
    ]

    def oxide(x, h, d):
        a = math.atan2(d, x)
        height = h + 1.1 * math.sin(a * 2 + 0.7) + 0.65 * math.sin(a * 3 - 0.35)
        lo, hi = next(
            (
                (left, right)
                for left, right in zip(tones, tones[1:])
                if height <= right[0]
            ),
            (tones[-2], tones[-1]),
        )
        t = max(0, min(1, (height - lo[0]) / (hi[0] - lo[0])))
        return tuple(
            ((1 - t) * int(lo[1][i : i + 2], 16) + t * int(hi[1][i : i + 2], 16)) / 255
            for i in (0, 2, 4)
        )

    vertex_colors(shell, titanium, oxide)
    inner = finish("Aurora · bare drawn titanium interior", "b9beb5", 0.78, 0.44)
    shell.data.materials.append(inner)
    for polygon in shell.data.polygons:
        if polygon.index in body.enclosed_faces:
            polygon.material_index = len(shell.data.materials) - 1
    die = Sculpture("Aurora · curved front print")
    printed = print_body(die, ink)
    closure = Sculpture("Aurora · screw cap with moulded carry aperture")
    spun(
        closure,
        [
            (205.1, 0),
            (205.1, 22.2),
            (204.98, 23.25),
            (204.51, 23.9),
            (203.7, 24.15),
            (185.05, 24.15),
            (184.4, 24.4),
            (184.14, 24.87),
            (184.14, 26.37),
            (184.38, 26.79),
            (184.94, 26.89),
            (197.48, 26.89),
            (198.1, 26.62),
            (198.28, 26.15),
            (198.4, 25.8),
            (199.25, 25.8),
            (199.55, 26.34),
            (201.62, 26.34),
            (202.1, 26.52),
            (202.6, 27.2),
            (202.7, 29.43),
            (202.77, 30.39),
            (203.13, 31.73),
            (203.69, 32.12),
            (204.48, 32.15),
            (204.86, 31.85),
            (205.0, 31.28),
            (205.48, 31.28),
            (205.73, 32.05),
            (206.0, 32.38),
            (207.70, 32.4),
            (208.15, 32.1),
            (208.42, 31.22),
            (208.0, 26),
            (207.64, 19),
            (207.6, 0),
        ],
        polymer,
        closed_strips=lambda i: i < 17,
    )
    start_thread = len(closure.faces)
    thread(closure, polymer)
    closure.enclosed_faces.update(range(start_thread, len(closure.faces)))
    carry_handle(closure, polymer)
    plug = finish_part(closure)
    seal = Sculpture("Aurora · XTW-800-02 stepped silicone gasket")
    seal.turn(
        [
            (198.8, 26.06),
            (198.75, 26.68),
            (198.84, 27.72),
            (199.08, 28.01),
            (201.34, 28.01),
            (201.60, 28.19),
            (201.65, 29.80),
            (201.86, 30.26),
            (202.58, 30.26),
            (202.69, 30.02),
            (202.66, 27.35),
            (202.24, 26.50),
            (201.53, 26.25),
            (199.46, 26.19),
            (198.8, 26.06),
        ],
        silicone,
        96,
    )
    seal.enclosed_faces = {i for i in range(len(seal.faces)) if not 5 <= i // 96 <= 9}
    packing = finish_part(seal)
    shell["auroraFitting"] = "vessel"
    plug["auroraFitting"] = "cap"
    packing["auroraFitting"] = "packing"
    shell.parent = assembly
    printed.parent = shell
    plug.parent = assembly
    packing.parent = plug
    return assembly


