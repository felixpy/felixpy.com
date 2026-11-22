import json
import math
import random
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

assets = Path(__file__).resolve().parent
repo = assets.parents[1]
authoring = repo / ".references/05-摄影与陈列/相机与镜头/Nikon Z8/Blender"
sys.path.insert(0, str(assets))
from product_solids import (
    block,
    combine,
    corners,
    edge,
    letters,
    mesh,
    pin,
    subtract,
    vertex,
)

finish = runpy.run_path(str(assets / "vitrine-sculpt.py"))["finish"]


def contour(points, samples=5):
    result = []
    n = len(points)
    for i in range(n):
        a, b, c, d = (Vector(points[(i + j) % n]) for j in (-1, 0, 1, 2))
        for j in range(samples):
            t = j / samples
            result.append(
                b * (2 * t**3 - 3 * t * t + 1)
                + c * (3 * t * t - 2 * t**3)
                + (c - a) * (0.45 * (t**3 - 2 * t * t + t))
                + (d - b) * (0.45 * (t**3 - t * t))
            )
    return result


def profile(name, outline, levels, material, origin=(0, 0)):
    points = [
        (origin[0] + (x - origin[0]) * scale, h, origin[1] + (d - origin[1]) * scale)
        for h, scale in levels
        for x, d in outline
    ]
    n = len(outline)
    area = sum(
        outline[i][0] * outline[(i + 1) % n][1]
        - outline[i][1] * outline[(i + 1) % n][0]
        for i in range(n)
    )
    cap = (len(levels) - 1) * n
    faces = [tuple(range(n)), tuple(reversed(range(cap, cap + n)))]
    faces += [
        (j * n + i, (j + 1) * n + i, (j + 1) * n + (i + 1) % n, j * n + (i + 1) % n)
        for j in range(len(levels) - 1)
        for i in range(n)
    ]
    if area < 0:
        faces = [tuple(reversed(face)) for face in faces]
    obj = mesh(name, points, faces, material)
    for f in obj.data.polygons:
        f.use_smooth = len(f.vertices) == 4
    return obj


def bore(name, x, z, low, high, radius, mat, n=48):
    return pin(name, (x, low, z), (x, high, z), radius, mat, n)


def revolved(name, x, z, rings, mat, n=64, inward=False):
    pts = [
        (x + r * math.cos(i * math.tau / n), h, z + r * math.sin(i * math.tau / n))
        for r, h in rings
        for i in range(n)
    ]
    faces = [
        (
            row * n + i,
            (row + 1) * n + i,
            (row + 1) * n + (i + 1) % n,
            row * n + (i + 1) % n,
        )
        for row in range(len(rings) - 1)
        for i in range(n)
    ]
    if inward:
        faces = [face[::-1] for face in faces]
    obj = mesh(name, pts, faces, mat)
    for f in obj.data.polygons:
        f.use_smooth = True
    return obj


def imprint(name, x, h, z, size, mat, top=False):
    points, faces = letters(name, False)
    umin, umax = min(p[0] for p in points), max(p[0] for p in points)
    vmin, vmax = min(p[1] for p in points), max(p[1] for p in points)
    sign = -1 if top else 1
    coords = [
        (
            x + sign * (u - (umin + umax) / 2) * size,
            h,
            z + (v - (vmin + vmax) / 2) * size,
        )
        for u, v in points
    ]
    return mesh(name, coords, faces, mat)


def lower_plate(cast, rubber, metal, recess):
    outline = contour(
        json.loads((repo / "src/scene/nikon-z8-outline.json").read_text()), 4
    )
    sole = profile(
        "Magnesium lower casting · grip and mount saddle",
        outline,
        [(-51.4, 0.94), (-51.0, 0.97), (-49.6, 0.992), (-46.8, 0.995)],
        cast,
    )
    door = contour(
        [
            (-65.3, -19.5),
            (-57.4, -24.3),
            (-47.4, -24.5),
            (-42.6, -22.3),
            (-42.4, -13.6),
            (-38.9, -11.9),
            (-38.9, 0.2),
            (-42.3, 1.4),
            (-44.5, 16),
            (-46.5, 26),
            (-51.8, 32.5),
            (-58.7, 35),
            (-63.7, 33.2),
            (-66.7, 25),
            (-67.3, -7),
        ],
        4,
    )
    x, z = 16, 3
    center = (-54, 5)
    holes = [
        profile(
            "Battery door mouth", door, [(-53, 1.014), (-45, 1.014)], rubber, center
        ),
        bore("Tripod insert bore", x, z, -54, -45, 4.5, cast),
        bore("Registration bore", x, -12.7, -54, -45, 2.5, cast),
    ]
    for px, pz in [
        (-9.1, 8),
        (3.3, 8),
        (28.8, 8),
        (41.4, 8),
        (-9.1, -17),
        (41.4, -17),
        (60.7, 10.1),
    ]:
        holes.append(bore("Recessed fixing", px, pz, -54, -45.5, 1.84, recess, 28))
    subtract(sole, holes)
    pad = block(
        "Hard rubber tripod contact mat",
        16,
        -51.52,
        -4.6,
        67.5,
        0.62,
        33.4,
        1.7,
        rubber,
    )
    plateholes = [
        (x, z, 4.6),
        (x, -12.7, 2.9),
        (-9.1, 8, 2.15),
        (3.3, 8, 2.15),
        (28.8, 8, 2.15),
        (41.4, 8, 2.15),
        (-9.1, -17, 2.15),
        (41.4, -17, 2.15),
    ]
    ribs = []
    for i in range(15):
        ridge_z = -19.1 + i * 2.08
        footprint = [(16 + u, ridge_z + v) for u, v in corners(62.7, 0.67, 0.28, 2)]
        land = profile(
            "Anti-rotation land",
            footprint,
            [(-52.05, 1), (-51.65, 1)],
            rubber,
            (16, ridge_z),
        )
        ribs.append(edge(land, 0.12, 2))
    lands = combine("Fifteen moulded traction lands", ribs)
    for part in [pad, lands]:
        subtract(
            part,
            [
                bore("Tool clearance", px, pz, -53, -50, r, recess)
                for px, pz, r in plateholes
            ],
        )
    for px, pz, _ in plateholes[2:] + [(60.7, 10.1, 0)]:
        screw = bore(
            "Black cross-head fastener", px, pz, -51.63, -50.6, 1.68, recess, 32
        )
        cross = [
            (-0.25, -1.1),
            (0.25, -1.1),
            (0.25, -0.25),
            (1.1, -0.25),
            (1.1, 0.25),
            (0.25, 0.25),
            (0.25, 1.1),
            (-0.25, 1.1),
            (-0.25, 0.25),
            (-1.1, 0.25),
            (-1.1, -0.25),
            (-0.25, -0.25),
        ]
        cross = [(px + u, pz + v) for u, v in cross]
        subtract(
            screw,
            [
                profile(
                    "Tapered cross driver",
                    cross,
                    [(-52, 1), (-51.30, 0.78)],
                    metal,
                    (px, pz),
                )
            ],
        )
        edge(screw, 0.038, 1)
    revolved(
        "Nickel tripod ferrule · rolled lip and blind bore",
        x,
        z,
        [
            (4.44, -50.1),
            (4.44, -51.53),
            (4.18, -51.90),
            (3.49, -51.90),
            (3.19, -51.53),
            (3.17, -44.3),
        ],
        metal,
        inward=True,
    )
    bore("Blackened end of the tripod socket", x, z, -44.32, -44.12, 3.18, recess)
    threads = []
    steps = 5 * 48
    for j in range(steps + 1):
        t = j / 48
        a = t * math.tau
        for r, h in [(3.21, -0.43), (2.72, -0.095), (2.72, 0.095), (3.21, 0.43)]:
            threads.append(
                (x + r * math.cos(a), -51.0 + 1.27 * t + h, z + r * math.sin(a))
            )
    thread = mesh(
        "1/4-20 UNC female thread · five turns",
        threads,
        [
            (4 * j + k, 4 * (j + 1) + k, 4 * (j + 1) + k + 1, 4 * j + k + 1)
            for j in range(steps)
            for k in range(3)
        ],
        metal,
    )
    for f in thread.data.polygons:
        f.use_smooth = True
    revolved(
        "Blind alignment-pin socket",
        x,
        -12.7,
        [(2.9, -51.81), (2.39, -51.49), (2.31, -47.1), (0.03, -47.1)],
        recess,
        inward=True,
    )
    lip = profile(
        "Rebated door seat underneath perimeter clearance",
        door,
        [(-50.18, 1.028), (-48.1, 1.028)],
        recess,
        center,
    )
    subtract(
        lip,
        [
            block(
                "Battery well opening", -54.3, -49.1, 3.4, 22.8, 5.0, 42.2, 2.75, recess
            )
        ],
    )
    block(
        "Small identification window", 55.2, -51.47, -6.5, 7.0, 0.32, 20.5, 0.52, rubber
    )
    imprint("Z 8", 55.2, -51.68, -6.4, 1.98, cast)
    return door, center


def battery_door(door, center, cast, rubber, black, metal):
    cover = profile(
        "Battery door · asymmetric grip contour",
        door,
        [(-51.38, 0.953), (-51.21, 0.980), (-50.48, 0.987), (-49.55, 0.962)],
        cast,
        center,
    )
    subtract(
        cover,
        [
            block(
                "Recess for sliding release",
                -60.0,
                -51.20,
                7.6,
                6.1,
                1.25,
                10.3,
                1.45,
                black,
            )
        ],
    )
    edge(cover, 0.075, 2)
    block(
        "Latch thumb · transverse slider",
        -60.45,
        -50.95,
        7.60,
        3.96,
        0.8,
        7.28,
        0.84,
        black,
    )
    for dx in [-1.10, -0.40, 0.30, 1.00]:
        block(
            "Latch thumb traction",
            -60.45 + dx,
            -51.43,
            7.60,
            0.29,
            0.17,
            5.80,
            0.14,
            rubber,
        )
    imprint("◁", -55.8, -51.46, 7.5, 2.8, rubber)
    pin(
        "Removable battery-door hinge pin",
        (-39.25, -49.2, -13.0),
        (-39.25, -49.2, 0.9),
        0.9,
        metal,
        32,
    )
    seal = [(-54 + (x + 54) * 0.89, -49.31, 5 + (d - 5) * 0.94) for x, d in door]
    tubes = []
    for i in range(len(seal)):
        tubes.append(pin("Weather seal", seal[i - 1], seal[i], 0.32, rubber, 8))
    combine("Continuous lid weather seal", tubes)
    for z in [-10.2, -4.7]:
        pin(
            "Hinge knuckle",
            (-39.25, -49.16, z - 1.55),
            (-39.25, -49.16, z + 1.55),
            1.5,
            cast,
        )
    block("Inner sliding catch", -61.4, -48.74, 7.6, 5.0, 1.68, 6.3, 0.6, black)
    for z in [-4, 13]:
        block("Inner door spring shoe", -51.5, -48.78, z, 5.4, 1.1, 6.0, 0.83, rubber)


def battery_chamber(rubber, black, metal, orange, gold, letter):
    chamber = block(
        "Grip cavity liner", -54.3, -19.5, 3.4, 24.4, 61.0, 43.8, 3.6, black
    )
    subtract(
        chamber,
        [block("Keyed cell cavity", -54.3, -21.6, 3.4, 22.65, 61.5, 42.0, 2.8, black)],
    )
    for z in [-8.0, 14.8]:
        block("EN-EL15c guide rib", -64.9, -19.8, z, 0.9, 51.3, 1, 0.20, black)
    block(
        "Orange spring-loaded cell catch",
        -64.2,
        -47.4,
        16.0,
        3.0,
        2.3,
        4.8,
        0.65,
        orange,
    )
    battery_black = finish("EN-EL15c · charcoal cell shell", "56575a", 0.09, 0.45)
    before = set(bpy.context.scene.objects)
    x, z = -54.2, 3.5
    section = contour(
        [
            (-4.3, -19.8),
            (-8.2, -17.1),
            (-10.0, -12.3),
            (-10.1, -8.3),
            (-8.4, -4.4),
            (-7.2, -3.1),
            (-7.2, 3.1),
            (-8.4, 4.4),
            (-10.1, 8.3),
            (-10.0, 12.3),
            (-8.2, 16.9),
            (-4.3, 19.8),
            (0.85, 19.8),
            (0.85, 8),
            (0.85, -8),
            (0.85, -19.8),
        ],
        3,
    )
    section = [(x + u, z + v) for u, v in section]
    profile(
        "EN-EL15c · twin-lobed moulded battery lid",
        section,
        [
            (-47.45, 0.956),
            (-47.1, 0.99),
            (-46.65, 1),
            (7.87, 1),
            (8.22, 0.987),
            (8.45, 0.968),
        ],
        battery_black,
        (x, z),
    )
    carrier = block(
        "Keyed rail half of the battery cartridge",
        x + 5.32,
        -19.5,
        z,
        8.85,
        55.80,
        39.72,
        1.08,
        black,
    )
    for side in [-1, 1]:
        subtract(
            carrier,
            [
                block(
                    "Charger rail window",
                    x + 9.50,
                    -19.0,
                    z + side * 19.64,
                    2.19,
                    24.0,
                    2.26,
                    0.56,
                    black,
                )
            ],
        )
    cuts = []
    for dz in [3.5, 5.5, 7.5, 9.5, 11.5]:
        cuts.append(
            block(
                "Recess in electrode comb",
                x + 7.95,
                7.1,
                z + dz,
                4.17,
                4.00,
                1.32,
                0.30,
                black,
            )
        )
        block("EN-EL15c contact", x + 7.61, 5.2, z + dz, 3.67, 0.28, 0.86, 0.24, gold)
    subtract(carrier, cuts)
    edge(carrier, 0.16, 2)
    for text, d, scale in [
        ("Nikon", 0.15, 3.1),
        ("RECHARGEABLE LI-ION BATTERY PACK", -2.34, 1.61),
    ]:
        pts, triangles = letters(text, False)
        vs = [(x - 7.28, -19.5 - u * scale, z + d + v * scale) for u, v in pts]
        mesh(
            "Recessed casing print · " + text,
            vs,
            triangles,
            black,
        )
    imprint("EN-EL15c", x, -47.50, z, 2.0, letter)
    pieces = set(bpy.context.scene.objects) - before
    cell = bpy.data.objects.new("EN-EL15c · installed battery", None)
    bpy.context.collection.objects.link(cell)
    cell.location = vertex(x, -19.5, z)
    bpy.context.view_layer.update()
    for part in pieces:
        part.parent = cell
        part.matrix_parent_inverse = cell.matrix_world.inverted()
    for dz in [3.5, 5.5, 7.5, 9.5, 11.5]:
        block(
            "Contact carrier finger",
            x + 7.61,
            8.78,
            z + dz,
            2.8,
            6.1,
            0.55,
            0.15,
            metal,
        )


def release_switch(cast, rubber, black, ink):
    before = set(bpy.context.scene.objects)
    revolved(
        "Shutter switch · rotating bezel",
        0,
        0,
        [
            (0.02, -0.4),
            (8.7, -0.4),
            (8.85, 0.25),
            (8.38, 1.15),
            (7.65, 1.84),
            (4.97, 1.84),
            (4.74, 1.55),
            (4.74, 0.45),
        ],
        cast,
    )
    revolved(
        "Two-stage shutter release button",
        0,
        0,
        [
            (0.02, 0.4),
            (4.73, 0.4),
            (4.64, 1.53),
            (4.25, 2.22),
            (3.45, 2.42),
            (0.02, 2.55),
        ],
        rubber,
    )
    thumb = contour(
        [
            (2.25, 4.05),
            (4.11, 6.71),
            (4.94, 7.02),
            (5.87, 6.17),
            (5.52, 5.04),
            (3.77, 2.76),
        ],
        3,
    )
    profile(
        "Power collar thumb tab",
        thumb,
        [(1.32, 1), (1.78, 1), (2.56, 0.76)],
        black,
        (4.62, 5.3),
    )
    for text, x, z, angle in [("OFF", -4.56, -5.02, 42), ("ON", -6.96, 0.3, 79)]:
        label = imprint(text, 0, 1.90, 0, 1.44, ink, True)
        label.matrix_world = Matrix.Translation(vertex(x, 0, z)) @ Matrix.Rotation(
            math.radians(angle), 4, "Z"
        )
    index = block(
        "Stationary white power index", -5.58, 0.1, -7.91, 0.62, 0.28, 1.82, 0.18, ink
    )
    index.matrix_world = (
        Matrix.Translation(vertex(-5.58, 0, -7.91))
        @ Matrix.Rotation(-0.48, 4, "Z")
        @ Matrix.Translation(vertex(5.58, 0, 7.91))
    )
    slope = Matrix.Translation(vertex(-55, 32.1, 31)) @ Matrix.Rotation(0.385, 4, "X")
    bpy.context.view_layer.update()
    for obj in set(bpy.context.scene.objects) - before:
        obj.matrix_world = slope @ obj.matrix_world


def shoulder(cast, rubber, black, metal, ink):
    release_switch(cast, rubber, black, ink)
    cx, cz = 54.5, -4
    revolved(
        "Left shoulder switch base",
        cx,
        cz,
        [
            (0.02, 42.3),
            (12.8, 42.3),
            (13.25, 42.9),
            (13.2, 44.9),
            (12.4, 45.55),
            (0.02, 45.55),
        ],
        cast,
    )
    for i, (dx, dz, label) in enumerate(
        [(0, 7.6, "BKT"), (-7.6, 0, "WB"), (0, -7.6, "MODE"), (7.6, 0, "")]
    ):
        key = [
            (-4.0, 1.9),
            (-3.3, 3.0),
            (0, 3.54),
            (3.3, 3.0),
            (4, 1.9),
            (3.45, -0.4),
            (1.8, -2.8),
            (-1.8, -2.8),
            (-3.45, -0.4),
        ]
        angle = i * math.pi / 2
        path = contour(
            [
                (
                    cx + dx + x * math.cos(angle) - z * math.sin(angle),
                    cz + dz + x * math.sin(angle) + z * math.cos(angle),
                )
                for x, z in key
            ],
            4,
        )
        profile(
            "Raised quadrant key · " + (label or "release mode"),
            path,
            [(45.53, 1), (45.96, 1), (46.42, 0.9), (46.55, 0.81)],
            black,
            (cx + dx, cz + dz),
        )
        if label:
            imprint(label, cx + dx, 46.57, cz + dz, 2.05, ink, True)
        else:
            for k in range(2):
                loop = [
                    (cx + dx - 1.40 + k * 0.40, cz - 0.65 + k * 0.42),
                    (cx + dx - 1.40 + k * 0.40, cz + 0.65 + k * 0.42),
                    (cx + dx + 1.25 + k * 0.40, cz + 0.65 + k * 0.42),
                    (cx + dx + 1.25 + k * 0.40, cz - 0.65 + k * 0.42),
                ]
                for n in range(4):
                    x1, z1 = loop[n - 1]
                    x2, z2 = loop[n]
                    pin(
                        "Release-mode frame engraving",
                        (x1, 46.57, z1),
                        (x2, 46.57, z2),
                        0.115,
                        ink,
                        8,
                    )
    block(
        "Accessory shoe insulating base", 16, 65.20, -7, 23.6, 1.75, 22.8, 0.96, black
    )
    for x in [5.6, 26.4]:
        edge(block("Stamped shoe rail", x, 66.8, -7, 2.2, 2.8, 22, 0.37, metal), 0.13)
        edge(
            block(
                "Rail retention lip",
                x + (1 if x < 16 else -1) * 0.80,
                68.03,
                -7,
                3.72,
                0.74,
                22.2,
                0.38,
                metal,
            ),
            0.14,
        )
    edge(
        block(
            "BS-1 protective slide-in cover",
            16,
            67.75,
            -7.5,
            17.3,
            1.48,
            21.8,
            0.8,
            black,
        ),
        0.18,
    )
    for z in [-13.8, -12.95, -12.1]:
        block("BS-1 fingertip ridge", 16, 68.55, z, 14.6, 0.28, 0.32, 0.14, rubber)


def grain(materials):
    extent = 96
    rng = random.Random(803)
    noise = [rng.gauss(0, 0.10) for _ in range(extent * extent)]
    pixels = []
    for j in range(extent):
        for i in range(extent):
            dx = (
                noise[j * extent + (i + 1) % extent]
                - noise[j * extent + (i - 1) % extent]
            )
            dy = (
                noise[((j + 1) % extent) * extent + i]
                - noise[((j - 1) % extent) * extent + i]
            )
            length = math.sqrt(dx * dx + dy * dy + 1)
            pixels.extend(
                ((1 - dx / length) / 2, (1 - dy / length) / 2, (1 + 1 / length) / 2, 1)
            )
    image = bpy.data.images.new("Z8 pebbled finish", extent, extent, alpha=False)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels)
    image.pack()
    for mat, strength in materials.items():
        nodes = mat.node_tree.nodes
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        normal = nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value = strength
        mat.node_tree.links.new(tex.outputs["Color"], normal.inputs["Color"])
        mat.node_tree.links.new(
            normal.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"]
        )
    bpy.context.view_layer.update()
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not any(
            slot.material in materials for slot in obj.material_slots
        ):
            continue
        uv = obj.data.uv_layers.active or obj.data.uv_layers.new(
            name="Millimetre grain"
        )
        for face in obj.data.polygons:
            nx, ny, nz = map(abs, face.normal)
            a, b = (0, 1) if nz >= max(nx, ny) else (1, 2) if nx > ny else (0, 2)
            for i in face.loop_indices:
                co = obj.data.vertices[obj.data.loops[i].vertex_index].co
                uv.data[i].uv = (co[a] / 0.006, co[b] / 0.006)


def build():
    marks = runpy.run_path(str(assets / "nikon-body-signatures.py"))
    marks["build"]()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    authoring.mkdir(parents=True, exist_ok=True)
    cast = finish("Z8 · painted magnesium casting", "353637", 0.25, 0.55)
    black = finish("Z8 · black moulded polycarbonate", "272829", 0.06, 0.52)
    rubber = finish("Z8 · traction elastomer", "252526", 0.025, 0.79)
    recess = finish("Z8 · black phosphate and dark recess", "18191a", 0.23, 0.56)
    metal = finish("Z8 · rolled nickel-plated steel", "bbbcb9", 0.84, 0.30)
    orange = finish("Z8 · orange battery catch", "ed9329", 0.01, 0.43)
    gold = finish("Z8 · battery contact gold", "c6a467", 0.77, 0.30)
    ink = finish("Z8 · warm grey control legends", "dddcd5", 0.03, 0.50)
    door, center = lower_plate(cast, rubber, metal, recess)
    fixed = set(bpy.context.scene.objects)
    battery_door(door, center, cast, rubber, black, metal)
    lid = set(bpy.context.scene.objects) - fixed
    shoulder(cast, rubber, black, metal, ink)
    exterior = set(bpy.context.scene.objects)
    battery_chamber(rubber, black, metal, orange, gold, ink)
    grain({cast: 0.33, black: 0.15, rubber: 0.24})
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not len(obj.data.polygons):
            raise ValueError("Empty Z8 component: " + obj.name)
    hinge = bpy.data.objects.new("Z 8 · removable battery door pivot", None)
    bpy.context.collection.objects.link(hinge)
    hinge.location = vertex(-39.25, -49.16, -5.05)
    bpy.context.view_layer.update()
    for obj in lid:
        obj.parent = hinge
        obj.matrix_parent_inverse = hinge.matrix_world.inverted()
    for obj in bpy.context.scene.objects:
        obj["z8Hardware"] = "Fittings"
        obj["partGroup"] = (
            "Battery door"
            if obj in lid or obj == hinge
            else "Body exterior"
            if obj in exterior
            else "Battery chamber"
        )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(authoring / "nikon-z8-hardware.blend"), compress=True
    )
    bpy.ops.object.select_all(action="DESELECT")
    visible = {
        o
        for o in exterior
        if not o.name.startswith(
            (
                "Continuous lid",
                "Inner door",
                "Inner sliding",
                "Removable battery-door hinge",
                "Hinge knuckle",
            )
        )
    }
    with bpy.data.libraries.load(str(marks["source"])) as (library, loaded):
        loaded.objects = list(library.objects)
    for part in loaded.objects:
        bpy.context.scene.collection.objects.link(part)
        visible.add(part)
    shell = combine(
        "Nikon Z8 · bottom casting and controls", sorted(visible, key=lambda o: o.name)
    )
    shell.select_set(True)
    path = repo / "public/media/models/nikon-z8-hardware.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        use_selection=True,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(assets / "pack-product-geometry.mjs"), str(path)], check=True
    )


if __name__ == "__main__":
    build()
