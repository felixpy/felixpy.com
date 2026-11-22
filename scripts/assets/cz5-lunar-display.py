from math import cos, pi, sin
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / ".review/atelier/cz5-display"
PRODUCT = (
    ROOT / ".references/06-工坊与工具/三维打印与模型/Launch vehicle scale model/Blender"
)
NAME = "CZ-5 Y8 · lunar mission display shell"


def paint(name, rgb, roughness, metallic=0, artwork=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if artwork:
        image = bpy.data.images.load(str(ART / artwork))
        image.pack()
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        mat.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    return mat


def model_surface(name, levels, mat, uv_limits, rotation=0.0, offset=0.0, sides=96):
    positions, faces, loops = [], [], []
    start, end = uv_limits
    for profile in levels:
        z, nominal, displacement, *rib = profile
        for i in range(sides):
            longitude = (i / sides - 0.5) * 2 * pi
            relief = 0.0
            if rib:
                depth, smooth_panel = rib
                taper = (
                    min(1.0, max(0.0, (abs(longitude) - 0.46) * 8))
                    if smooth_panel
                    else 1
                )
                relief = depth * (1 + cos(longitude * 48)) * 0.5 * taper
            angle = rotation + longitude
            radius = nominal + relief
            x = radius * sin(angle) + (offset + displacement) * sin(rotation)
            y = -radius * cos(angle) - (offset + displacement) * cos(rotation)
            positions.append((x * 0.001, y * 0.001, z * 0.001))
    for j in range(len(levels) - 1):
        low = (levels[j][0] - start) / (end - start)
        high = (levels[j + 1][0] - start) / (end - start)
        for i in range(sides):
            n = (i + 1) % sides
            faces.append(
                (j * sides + i, j * sides + n, (j + 1) * sides + n, (j + 1) * sides + i)
            )
            loops.extend(
                [
                    (i / sides, low),
                    ((i + 1) / sides, low),
                    ((i + 1) / sides, high),
                    (i / sides, high),
                ]
            )
    for ring, flipped in [(0, True), (len(levels) - 1, False)]:
        order = range(sides - 1, -1, -1) if flipped else range(sides)
        faces.append(tuple(ring * sides + i for i in order))
        loops.extend([(0, 0)] * sides)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    uv = mesh.uv_layers.new()
    uv.uv.foreach_set("vector", [v for value in loops for v in value])
    for face in list(mesh.polygons)[:-2]:
        face.use_smooth = True
    return obj


def shoulder_shoe(name, angle, mat):
    silhouette = [(26, -89), (33, -89), (33, -85), (26, -75)]
    vertices = []
    for t in [-1.35, 1.35]:
        for r, z in silhouette:
            vertices.append(
                (
                    (r * sin(angle) + t * cos(angle)) * 0.001,
                    (-r * cos(angle) + t * sin(angle)) * 0.001,
                    z * 0.001,
                )
            )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        vertices,
        [],
        [
            (0, 3, 2, 1),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ],
    )
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    bevel = obj.modifiers.new("Rounded mould edges", "BEVEL")
    bevel.width = 0.00024
    bevel.segments = 3
    obj.modifiers.new("Even enamel highlights", "WEIGHTED_NORMAL")


bpy.ops.wm.read_factory_settings(use_empty=True)
collection = bpy.data.collections.new(NAME)
bpy.context.scene.collection.children.link(collection)
body = paint(
    "Ivory lacquer · CLEP, CASC and 中国航天",
    (1, 1, 1),
    0.36,
    0.13,
    "cz5-body-paint.png",
)
pod = paint(
    "Paired carmine checks on enamel", (1, 1, 1), 0.4, 0.09, "cz5-pod-paint.png"
)
silver = paint("Soft aluminium display trim", (0.59, 0.61, 0.59), 0.42, 0.51)
copper = paint("Russet foot of the display core", (0.27, 0.086, 0.035), 0.41, 0.32)
metal = paint("Porcelain-white pressed fairings", (0.81, 0.82, 0.77), 0.41, 0.20)
u = (-92, 178)
model_surface(
    "Display core · russet heel",
    [(-92, 12.4, 0), (-90, 12.7, 0), (-75, 12.7, 0)],
    copper,
    u,
)
model_surface(
    "Smooth enamel barrel · Long March 5 roundel",
    [(-75, 12.7, 0), (-74.7, 12.9, 0), (78.8, 12.9, 0)],
    body,
    u,
)
model_surface(
    "中国航天 · painted on the core stage",
    [
        (78.8, 12.9, 0),
        (79.4, 12.9, 0, 0.20, True),
        (117.4, 12.9, 0, 0.20, True),
        (118.2, 12.9, 0),
    ],
    body,
    u,
    sides=288,
)
model_surface(
    "Blue CASC seal on smooth band", [(118.2, 12.9, 0), (128.6, 13.0, 0)], body, u
)
model_surface(
    "Ribbed collar · red rollout pinstripe",
    [
        (128.6, 13.0, 0),
        (129.1, 13, 0, 0.20, False),
        (137, 13.1, 0, 0.20, False),
        (137.7, 13.1, 0),
    ],
    body,
    u,
    sides=288,
)
model_surface(
    "Tapered crown · Chinese lunar exploration emblem",
    [
        (137.7, 13.1, 0),
        (139, 13.45, 0),
        (155, 13.45, 0),
        (157.6, 13.24, 0),
        (160.4, 12.75, 0),
        (164.5, 11.38, 0),
        (168.2, 9.5, 0),
        (171.4, 7.43, 0),
        (174.3, 5.13, 0),
        (176.6, 2.79, 0),
        (177.65, 1.23, 0),
        (178, 0.28, 0),
    ],
    body,
    u,
)
for number in range(4):
    a = pi * (0.25 + number * 0.5)
    label = f"Painted side shell {number + 1}"
    profile = [
        (-79, 8.05, 0),
        (-74, 8.13, 0),
        (37, 8.13, 0),
        (39, 8.02, -0.15),
        (41, 7.42, -0.62),
        (49, 5.43, -2.54),
        (55.2, 3.54, -4.05),
        (59.0, 1.90, -4.97),
        (60.6, 0.65, -5.25),
        (60.8, 0.25, -5.24),
    ]
    model_surface(
        f"{label} · stepped checks and inward crown",
        profile,
        pod,
        (-91, 60.8),
        a,
        20.0,
        64,
    )
    model_surface(
        f"{label} · satin shoe",
        [
            (-91, 8.35, 0),
            (-89, 8.62, 0),
            (-85, 8.64, 0),
            (-84.6, 8.17, 0),
            (-79, 8.05, 0),
        ],
        silver,
        u,
        a,
        20.0,
        64,
    )
    shoulder_shoe(f"{label} · flared heel", a, metal)
plate = bpy.data.meshes.new("Lunar mission nameplate")
plate.from_pydata(
    [
        (-0.039, -0.043, -0.1395),
        (0.039, -0.043, -0.1395),
        (0.039, -0.043, -0.1305),
        (-0.039, -0.043, -0.1305),
    ],
    [],
    [(0, 1, 2, 3)],
)
plate.uv_layers.new().uv.foreach_set("vector", [0, 0, 1, 0, 1, 1, 0, 1])
plate.materials.append(
    paint("Engraved CZ-5 Y8 nameplate", (1, 1, 1), 0.47, 0.22, "cz5-plinth-paint.png")
)
collection.objects.link(
    bpy.data.objects.new("CZ-5 Y8 · Chang'e-6 plinth plaque", plate)
)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(
    filepath=str(PRODUCT / "cz5-y8-painted-shell.blend"), compress=True
)
bpy.ops.export_scene.gltf(
    filepath=str(ROOT / "public/media/models/cz5-y8-painted-shell.glb"),
    export_format="GLB",
    export_apply=True,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
