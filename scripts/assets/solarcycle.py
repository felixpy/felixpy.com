import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product, finish_material, finishes


def grille_texture(folder):
    folder.mkdir(parents=True, exist_ok=True)
    finishes["grille"] = ("dedfdf", 0.33, 0.74)
    mat = finish_material("grille")
    shader = mat.node_tree.nodes.get("Principled BSDF")
    pitch = math.tau * 20.3 / 48
    u, v = np.meshgrid((np.arange(64) + 0.5) / 64, (np.arange(128) + 0.5) / 128)
    distances = []
    for center_u, center_v in ((0.25, 0.25), (0.75, 0.75)):
        dx = ((u - center_u + 0.5) % 1 - 0.5) * pitch
        dy = ((v - center_v + 0.5) % 1 - 0.5) * 4.82
        distances.append((dx * dx + dy * dy, dx, dy))
    first = distances[0][0] < distances[1][0]
    rr, dx, dy = [np.where(first, a, b) for a, b in zip(*distances)]
    radius = np.sqrt(rr)
    bevel = np.exp(-(((radius - 0.735) / 0.11) ** 2))
    strength = -0.84 * bevel
    normal = np.stack(
        (strength * dx / radius, strength * dy / radius, np.ones_like(radius)), axis=-1
    )
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    alpha = np.clip((radius - 0.615) / 0.065, 0, 1)
    albedo = np.clip(
        0.85 + 0.040 * bevel - 0.34 * (1 - np.clip((radius - 0.615) / 0.155, 0, 1)),
        0,
        1,
    )
    for suffix, rgb, opacity in [
        ("", np.stack((albedo * 0.994, albedo, albedo * 1.006), axis=-1), alpha),
        ("-normal", 0.5 + normal * 0.5, np.ones_like(alpha)),
    ]:
        key = "solarcycle-grille" + suffix
        image = bpy.data.images.new(key, 64, 128, alpha=True)
        image.alpha_mode = "CHANNEL_PACKED"
        image.colorspace_settings.name = "Non-Color"
        image.pixels.foreach_set(np.dstack((rgb, opacity)).astype(np.float32).ravel())
        image.filepath_raw = str(folder / (key + ".png"))
        image.file_format = "PNG"
        image.save()
        if not suffix:
            image.colorspace_settings.name = "sRGB"
        image.pack()
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        if suffix:
            node = mat.node_tree.nodes.new("ShaderNodeNormalMap")
            mat.node_tree.links.new(tex.outputs["Color"], node.inputs["Color"])
            mat.node_tree.links.new(node.outputs["Normal"], shader.inputs["Normal"])
        else:
            mat.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
            mat.node_tree.links.new(tex.outputs["Alpha"], shader.inputs["Alpha"])


def model_solarcycle(out):
    out = Path(out)
    root = Path(__file__).resolve().parents[2]
    grille_texture(root / "public/media/materials")
    unit = Product("solarcycle")
    elbow = Vector((-166, 0, 253))
    head = Vector((135, 0, 263))
    along = (head - elbow).normalized()
    across = Vector((-along.z, 0, along.x))

    def turn(label, finish, center, profile, sides=72):
        unit.lathe(
            label,
            finish,
            tuple(v * 0.001 for v in center),
            [(r / 1000, y / 1000) for r, y in profile],
            sides,
        )

    def rail(label, finish, a, b, h0, h1, width, radius):
        center = (a + b) * 0.5
        obj = unit.block(
            label,
            finish,
            (center.x / 1000, (h0 + h1) / 2000, center.z / 1000),
            ((b - a).length / 1000, (h1 - h0) / 1000, width / 1000),
            radius / 1000,
        )
        obj.rotation_euler.z = -math.atan2(b.z - a.z, b.x - a.x)

    def circles(label, finish, rows, inward=False):
        size = len(rows[0])
        verts = [tuple(v / 1000 for v in p) for row in rows for p in row]
        faces = []
        for j in range(len(rows) - 1):
            for i in range(size):
                k = (i + 1) % size
                face = (
                    j * size + i,
                    (j + 1) * size + i,
                    (j + 1) * size + k,
                    j * size + k,
                )
                faces.append(face[::-1] if inward else face)
        return unit.surface(label, finish, verts, faces, True)

    origin = Vector((0, 0, 0))
    turn(
        "Elastomer underside",
        "black",
        origin,
        [(0, 0), (95.5, 0), (97.2, 0.8), (97.5, 2.0), (95.1, 3.3), (0, 3.3)],
        96,
    )
    turn(
        "White weighted base",
        "white",
        origin,
        [
            (0, 2.0),
            (97.2, 2.0),
            (99.3, 2.6),
            (100.0, 3.8),
            (100.0, 22.8),
            (99.6, 24.1),
            (98.0, 24.8),
            (30, 25.0),
            (23.5, 25.1),
            (20.6, 24.7),
            (0, 24.7),
        ],
        112,
    )
    turn(
        "Stem mounting ferrule",
        "satin",
        origin,
        [(17.0, 24.6), (21.25, 24.6), (21.6, 25.2), (20.7, 26), (19.7, 26)],
    )
    column = 20.30
    phi = -0.32

    def curved(u, y, r=column):
        angle = phi + u / column
        return (r * math.sin(angle), y, r * math.cos(angle))

    width, port_y, port_halfheight = 3.7, 99.1, 6.8
    edges = np.linspace(width, math.tau * column - width, 90)
    rows = []
    for arc in ((-width, width), edges):
        for low, high in [
            (25.3, port_y - port_halfheight),
            (port_y + port_halfheight, 170.6),
        ] + (
            [(port_y - port_halfheight, port_y + port_halfheight)]
            if len(arc) > 2
            else []
        ):
            for a, b in zip(arc, arc[1:]):
                rows.extend(
                    [curved(a, low), curved(b, low), curved(b, high), curved(a, high)]
                )
    base = unit.surface(
        "Drawn column with USB-C port opening",
        "alloy",
        [tuple(v / 1000 for v in p) for p in rows],
        [tuple(range(i, i + 4)) for i in range(0, len(rows), 4)],
        True,
    )
    base.data.normals_split_custom_set_from_vertices(
        [(x / column, -z / column, 0) for x, _, z in rows]
    )
    corners = [(i + 0.5) * math.tau / 48 for i in range(48)]

    def port_outline(w, h, r, squared=False):
        result = []
        for a in corners:
            c, s = math.cos(a), math.sin(a)
            bound = (
                1 / max(abs(c) / w, abs(s) / h)
                if squared
                else ((abs(c) / w) ** 3.2 + (abs(s) / h) ** 3.2) ** (-1 / 3.2)
            )
            result.append(curved(bound * c, port_y + bound * s, r))
        return result

    port_rows = [
        port_outline(width, port_halfheight, column, True),
        port_outline(2.75, 5.5, column + 0.08),
        port_outline(2.46, 5.19, column + 0.13),
        port_outline(2.16, 4.84, column - 0.44),
        port_outline(2.16, 4.84, column - 1.7),
    ]
    circles("USB-C stamped shell and throat", "steel", port_rows, True)
    circles(
        "Recessed USB-C insulator",
        "black",
        [port_rows[-1], port_outline(0.15, 0.24, column - 1.85)],
        True,
    )
    circles(
        "USB-C contact tongue",
        "graphite",
        [
            port_outline(0.5, 3.64, column - 1.30),
            port_outline(0.44, 3.48, column - 0.63),
        ],
        True,
    )
    turn(
        "Ambient light mixing chamber",
        "graphite",
        origin,
        [(0, 170.2), (18.8, 170.2), (18.9, 455.4), (0, 455.4)],
    )
    low, high = 170.6, 454.6
    radial = 96
    frames = []
    for h in (low, high):
        frames.extend(
            [curved(math.tau * column * i / radial, h) for i in range(radial + 1)]
        )
    mesh = unit.surface(
        "Micro-perforated aluminium ambient stem",
        "grille",
        [tuple(v / 1000 for v in p) for p in frames],
        [(i, i + 1, i + radial + 2, i + radial + 1) for i in range(radial)],
        True,
    )
    mesh.data.normals_split_custom_set_from_vertices(
        [
            (
                math.sin(phi + (i % (radial + 1)) * math.tau / radial),
                -math.cos(phi + (i % (radial + 1)) * math.tau / radial),
                0,
            )
            for i in range(len(frames))
        ]
    )
    uv = mesh.data.uv_layers.active
    repeats = (high - low) / 4.82
    for loop in mesh.data.loops:
        row, col = divmod(loop.vertex_index, radial + 1)
        uv.data[loop.index].uv = (48 * col / radial, row * repeats)
    turn(
        "Rotary docking sleeve",
        "alloy",
        origin,
        [
            (19.9, 454.4),
            (20.4, 454.65),
            (20.45, 455.2),
            (20.45, 474.3),
            (20.15, 475.0),
            (18.55, 475.2),
            (17.60, 474.3),
            (17.2, 470.8),
            (16.4, 470.5),
        ],
    )
    turn(
        "Ambient light guide socket",
        "black",
        origin,
        [
            (17.0, 470.8),
            (16.64, 472.7),
            (15.9, 473),
            (14.95, 471.6),
            (14.95, 466.0),
            (0, 465.0),
        ],
    )
    turn(
        "Translucent docking window",
        "white",
        origin,
        [(0, 466), (15.04, 466), (14.90, 467.0), (11, 468.0), (0, 468.4)],
    )
    lower = elbow.normalized()
    rail(
        "Extruded lower arm",
        "alloy",
        lower * 7,
        elbow - lower * 2.5,
        455.2,
        474.8,
        22.4,
        1.13,
    )
    turn(
        "Elbow · rotating lower knuckle",
        "alloy",
        elbow,
        [
            (0, 454.8),
            (12.0, 454.8),
            (13.3, 455.5),
            (13.5, 456.3),
            (13.5, 474.6),
            (13.0, 475.1),
            (0, 475.1),
        ],
    )
    turn(
        "Elbow · thrust washer",
        "graphite",
        elbow,
        [(0, 474.8), (12.35, 474.8), (12.65, 475.35), (12.52, 476.2), (0, 476.2)],
    )
    turn(
        "Elbow · axial collar",
        "satin",
        elbow,
        [
            (0, 476.0),
            (12.75, 476.0),
            (13.45, 476.5),
            (13.5, 483.9),
            (13.1, 484.3),
            (0, 484.3),
        ],
    )
    turn(
        "Elbow · second bearing",
        "black",
        elbow,
        [(0, 484.15), (12.5, 484.15), (12.56, 485.6), (0, 485.6)],
    )
    turn(
        "Upper barrel and pivot cover",
        "graphite",
        elbow,
        [
            (0, 485.3),
            (12.5, 485.3),
            (13.2, 485.9),
            (13.4, 487.0),
            (13.4, 521.8),
            (13.0, 522.5),
            (11.9, 523),
            (0, 523),
        ],
    )
    stop = elbow + along * 20.3
    turn(
        "Fold stop · hardened shoulder",
        "steel",
        stop,
        [
            (0, 474.4),
            (3.9, 474.4),
            (4.1, 475.2),
            (4.1, 482.9),
            (5.3, 483.5),
            (5.3, 484.3),
            (0, 484.3),
        ],
        40,
    )
    turn(
        "Fold stop · rubber bumper",
        "black",
        stop,
        [
            (0, 483.9),
            (6.8, 483.9),
            (7.6, 484.7),
            (7.65, 486.4),
            (6.8, 487.5),
            (0, 487.5),
        ],
        48,
    )
    turn(
        "Heat pipe roll coupling",
        "satin",
        elbow + along * 20.9,
        [
            (0, 492.0),
            (6.3, 492.0),
            (7.4, 493.3),
            (7.4, 503.8),
            (6.6, 504.6),
            (0, 504.6),
        ],
        48,
    )
    turn(
        "Bearing seat",
        "graphite",
        elbow + along * 20.9,
        [(0, 491.9), (4.2, 491.9), (4.9, 492.6), (3.2, 492.7), (0, 492.2)],
        40,
    )
    rail(
        "Anodised upper heat-pipe extrusion",
        "graphite",
        elbow + along * 2,
        elbow + along * 145.3,
        503.6,
        522.8,
        23.3,
        1.0,
    )
    rail(
        "Silver optical sleeve",
        "satin",
        elbow + along * 145.0,
        head - along * 2,
        503.4,
        523.0,
        23.9,
        1.18,
    )
    rail(
        "Underside control insert",
        "white",
        elbow + along * 146.5,
        head - along * 17.0,
        502.95,
        503.55,
        20.6,
        0.52,
    )
    for i, d in enumerate([57, 44, 31]):
        pt = head - along * d
        turn(
            "Control key · recessed perimeter",
            "graphite",
            pt,
            [(0, 502.7), (4.1, 502.7), (4.2, 503.05), (0, 503.12)],
            40,
        )
        turn(
            "Underside setting " + str(i + 1),
            "satin",
            pt,
            [(0, 502.25), (3.42, 502.25), (3.74, 502.65), (3.72, 502.95), (0, 503.1)],
            40,
        )
    sensor = head - along * 72.3
    turn(
        "Motion sensor bezel",
        "graphite",
        sensor,
        [(0, 502.7), (6.4, 502.7), (6.7, 503.2), (0, 503.3)],
        48,
    )
    turn(
        "Infrared Fresnel dome",
        "steel",
        sensor,
        [
            (0.1, 499.8),
            (2.1, 500.0),
            (3.9, 500.6),
            (5.4, 501.6),
            (5.85, 502.6),
            (5.8, 503.05),
            (0, 503.05),
        ],
        48,
    )
    for d, w in [(80.8, -4.3), (83.2, 3.5)]:
        pt = head - along * d + across * w
        turn(
            "Ambient sensor port",
            "black",
            pt,
            [(0, 502.77), (1.85, 502.77), (1.98, 503.1), (0, 503.15)],
            32,
        )
    for side in (-1, 1):
        for i in range(7):
            center = head - along * (77.2 + i * 4.35) + across * (side * 5.0)
            rail(
                "Touch slider scale",
                "alloy",
                center - along * 0.38,
                center + along * 0.38,
                523.03,
                523.12,
                1.05 + i * 0.16,
                0.10,
            )
    turn(
        "Optical head · upper shell",
        "satin",
        head,
        [
            (0, 503.4),
            (20.5, 503.4),
            (21.25, 504.0),
            (21.4, 505.15),
            (21.4, 521.3),
            (21.25, 522.2),
            (20.7, 522.85),
            (19.9, 523.0),
            (0, 523.0),
        ],
        104,
    )
    turn(
        "Optical head · shadow line",
        "graphite",
        head,
        [(19.2, 503.1), (21.0, 503.1), (21.0, 504.0), (19.2, 504.0)],
        104,
    )
    turn(
        "Optical head · rotating lower cup",
        "satin",
        head,
        [
            (17.5, 484.8),
            (17.8, 482.15),
            (19.6, 481.75),
            (20.45, 482.0),
            (21.15, 482.7),
            (21.4, 484.0),
            (21.4, 502.15),
            (21.1, 503.1),
            (19.65, 503.55),
        ],
        104,
    )
    turn(
        "Optical lens · retaining ring",
        "white",
        head,
        [
            (16.3, 484.45),
            (17.25, 482.43),
            (17.85, 482.10),
            (18.42, 482.2),
            (18.8, 482.8),
            (18.5, 484.4),
        ],
        96,
    )
    turn(
        "Downlight · opal microprismatic lens",
        "opal",
        head,
        [
            (0, 482.02),
            (3.0, 482.03),
            (6.0, 482.11),
            (10.0, 482.27),
            (13.5, 482.56),
            (15.8, 482.85),
            (16.65, 483.05),
            (17.3, 483.8),
            (17.40, 484.42),
        ],
        96,
    )
    unit.export(out)


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model_solarcycle(project / "public/media/models/fixtures")
    bpy.ops.wm.save_as_mainfile(
        filepath=str(project / ".review/atelier/solarcycle.blend")
    )
