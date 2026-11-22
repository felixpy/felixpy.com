import math
from pathlib import Path

import bpy
import numpy as np

ITEM = (
    Path(__file__).resolve().parents[2]
    / ".references/07-户外装备/咖啡与饮具/Snow Peak titanium mugs"
)
PRODUCT = ITEM / "Blender/snow-peak-titanium-mugs.blend"
ASSEMBLY = "MG-153 · Ti-Double 450"


def printed_mark(sculpt, finish):
    source = bpy.data.images.load(str(ITEM / "参考图/SNP0123A0403-0.jpg"))
    w, h = source.size
    pixels = np.empty((h, w, 4), dtype=np.float32)
    source.pixels.foreach_get(pixels.ravel())
    patch = pixels[h - 1224 : h - 828, 501:843, :3].mean(axis=2)
    bpy.data.images.remove(source)
    background = np.median(patch, axis=1, keepdims=True) - 0.047
    coverage = np.clip((background - patch) / (background - 0.14), 0, 1)
    coverage[coverage < 0.105] = 0
    mask = np.empty((*coverage.shape, 4), dtype=np.float32)
    mask[:, :, :3] = 1
    mask[:, :, 3] = coverage
    ink = bpy.data.images.new(
        "MG-153 · Japanese face print", coverage.shape[1], coverage.shape[0], alpha=True
    )
    ink.pixels.foreach_set(mask.ravel())
    ink.update()
    ink.pack()
    mat = finish("MG-153 · charcoal print", "292727", 0.13, 0.53)
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = ink
    mat.node_tree.links.new(
        node.outputs["Alpha"], mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"]
    )
    mat.use_backface_culling = True
    art = sculpt("MG-153 · curved factory markings")
    count = 38
    rows = []
    for vertical in range(4):
        height = 21.0 + vertical * 43.6 / 3
        radius = body_radius(height) + 0.077
        for column in range(count + 1):
            angle = math.asin((column / count - 0.5) * 0.866)
            rows.append((radius * math.sin(angle), height, radius * math.cos(angle)))
    faces = [
        (
            j * (count + 1) + i,
            j * (count + 1) + i + 1,
            (j + 1) * (count + 1) + i + 1,
            (j + 1) * (count + 1) + i,
        )
        for j in range(3)
        for i in range(count)
    ]
    art.add(rows, faces, mat, False)
    obj = art.finalize()
    uv = obj.data.uv_layers.new(name="Surface scale")
    for loop in obj.data.loops:
        row, col = divmod(loop.vertex_index, count + 1)
        uv.data[loop.index].uv = (col / count, row / 3)
    return obj


def body_radius(height):
    return 47.10 + 0.68 * (height - 7) / (90 - 7)


def hinge_frame(x, depth):
    angle = math.atan2(depth, x)
    c, s = math.cos(angle), math.sin(angle)

    def project(radial, height, tangential):
        return (
            x + radial * c - tangential * s,
            height,
            depth + radial * s + tangential * c,
        )

    return project


def build(sculpt, wire, finish, titanium, polished):
    root = bpy.data.objects.new("Ti-Double 450", None)
    bpy.context.collection.objects.link(root)
    root["campProduct"] = "450"
    root["manufacturerPart"] = "MG-153"
    root.empty_display_size = 0.008
    outer = [
        (1.78, 0.02),
        (1.78, 39.0),
        (1.60, 41.1),
        (0.28, 43.25),
        (0.05, 44.05),
        (0.05, 44.72),
        (0.48, 45.48),
        (1.9, 46.27),
        (3.7, 46.76),
        (7, body_radius(7)),
        (90, body_radius(90)),
        (92.39, 48.0),
        (93.17, 47.86),
        (93.66, 47.52),
        (93.8, 47.09),
        (93.63, 46.75),
        (93.21, 46.49),
        (92.18, 46.38),
    ]
    cavity = [
        (91.75, 45.97),
        (90.8, 45.84),
        (89.70, 45.82),
        (89.05, 45.54),
        (88.72, 45.19),
        (11.9, 43.41),
        (9.55, 42.60),
        (8.20, 40.7),
        (7.73, 37.9),
        (7.73, 0.02),
    ]
    body = sculpt("MG-153 · drawn cup with joined drinking rim")
    body.turn(outer + cavity, titanium, 96)
    shell = body.finalize(24, [titanium])
    shell.parent = root
    inner = sculpt("MG-153 · air-facing walls under the welded lip")
    inner.turn(
        [
            (2.16, 0.02),
            (2.16, 40),
            (1.10, 43.9),
            (1.15, 44.65),
            (3.85, 46.31),
            (7, 46.74),
            (90, 47.40),
            (92.5, 47.5),
            (93, 47.15),
            (91.79, 46.55),
            (89.4, 46.14),
            (88.45, 45.61),
            (11.8, 43.78),
            (9.17, 42.89),
            (7.84, 40.9),
            (7.36, 37.9),
            (7.36, 0.02),
        ],
        titanium,
        64,
    )
    sealed = inner.finalize(24, [titanium])
    sealed["sealedCavity"] = True
    sealed.parent = root
    printed_mark(sculpt, finish).parent = root

    for side in (-1, 1):
        axis_d = side * 14.5
        axis_x = 47.50

        surface = hinge_frame(axis_x, axis_d)
        sleeve = sculpt(f"MG-153 · rolled hinge sleeve {side:+}")
        rings = []
        for y, r in [
            (24.4, 2.30),
            (24.55, 2.48),
            (75.0, 2.48),
            (75.15, 2.30),
            (75.15, 1.82),
            (75.0, 1.75),
            (24.55, 1.75),
            (24.4, 1.82),
        ]:
            rings.append(
                [
                    surface(
                        r * math.cos(math.tau * i / 36),
                        y,
                        r * math.sin(math.tau * i / 36),
                    )
                    for i in range(36)
                ]
            )
        rings.append(rings[0])
        sleeve.rings(rings, titanium, close=False)
        sleeve.finalize(30, [titanium]).parent = root
        for y in (33.0, 66.5):
            wing = sculpt(f"MG-153 · pressed welded feet {side:+} {int(y)}")
            for t in (-1, 1):
                sections = []
                for dh, span in [
                    (-7.0, 0.30),
                    (-6.55, 0.76),
                    (-5.6, 1),
                    (5.6, 1),
                    (6.55, 0.76),
                    (7, 0.30),
                ]:
                    coords = [
                        (-1.04, 1.77),
                        (-1.43, 2.35),
                        (-2.22, 2.87),
                        (-2.65, 3.60),
                        (-2.72, 4.14),
                        (-3.1, 4.14),
                        (-3.02, 3.38),
                        (-2.58, 2.70),
                        (-1.84, 2.12),
                        (-1.4, 1.62),
                    ]
                    sections.append(
                        [
                            surface(n, y + dh, t * (1.63 + (s - 1.63) * span))
                            for n, s in coords
                        ]
                    )
                wing.rings(sections, titanium)
            wing.finalize(30, [titanium]).parent = root
        arm = sculpt(f"MG-153 · bent titanium handle {side:+}")
        path = [
            (0, 69, 0),
            (0, 75.0, 0),
            (0.45, 77.8, -0.16),
            (2.2, 79.7, -0.45),
            (4.9, 80.4, -1.2),
            (13.9, 79.9, -4.45),
            (21.8, 80.6, -6.45),
            (26.6, 80.1, -7.5),
            (30.7, 77.5, -8.6),
            (33.25, 73.0, -9.0),
            (34.1, 66.4, -9.3),
            (32.6, 54.7, -9.4),
            (27.6, 41.3, -10.0),
            (21.5, 29.7, -10.4),
            (17.9, 24.5, -10.0),
            (14.5, 22.70, -9.1),
            (8.3, 22.4, -5.2),
            (3.6, 21.90, -1.7),
            (1.25, 22.05, -0.45),
            (0.2, 23.35, -0.1),
            (0, 25.10, 0),
            (0, 30, 0),
        ]
        folded_angle = math.radians(144)
        ca, sa = math.cos(folded_angle), math.sin(folded_angle)
        points = []
        for radial, height, depth in path:
            radial *= 1.052
            along = axis_x * ca + axis_d * side * sa + radial
            across = -axis_x * sa + axis_d * side * ca
            envelope = body_radius(height) + 1.92
            tangent = math.sqrt(max(0, envelope**2 - along**2))
            depth = min(depth, -tangent - across)
            points.append((radial, height, side * depth))
        wire(arm, points, 1.62, polished, 4)
        handle = arm.finalize(24, [polished])
        handle.parent = root
        handle.location = (axis_x / 1000, -axis_d / 1000, 0)
        handle["foldAxis"] = "Z"
        handle["foldDirection"] = -side
        travel = handle.constraints.new("LIMIT_ROTATION")
        travel.name = "Fold against the cup wall"
        travel.owner_space = "LOCAL"
        travel.use_limit_x = travel.use_limit_y = travel.use_limit_z = True
        travel.min_z, travel.max_z = sorted((0, -side * folded_angle))
        travel.use_transform_limit = True
    return root


def save_product(root):
    collection = bpy.data.collections.new(ASSEMBLY)
    for obj in (root, *root.children_recursive):
        collection.objects.link(obj)
    scene = bpy.data.scenes.new(ASSEMBLY)
    scene.collection.children.link(collection)
    scene.unit_settings.system = "METRIC"
    bpy.data.libraries.write(
        str(PRODUCT), {scene}, path_remap="RELATIVE_ALL", compress=True
    )
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(collection)


def fit(scene):
    anchor = next(obj for obj in scene.objects if obj.get("campProduct") == "450")
    if anchor.instance_collection and anchor.instance_collection.name == ASSEMBLY:
        return anchor
    original = list(anchor.children_recursive)
    if anchor.type == "MESH":
        if anchor.name != "Ti-Double 450" or original:
            raise ValueError("Unrecognised standalone mug")
    elif (
        anchor.type != "EMPTY"
        or not original
        or any(obj.type not in {"MESH", "EMPTY"} or obj.library for obj in original)
    ):
        raise ValueError("Unrecognised equipment-wall mug assembly")
    with bpy.data.libraries.load(str(PRODUCT), link=True, relative=True) as (_, linked):
        linked.collections = [ASSEMBLY]
    collection = linked.collections[0]
    if not collection or sum("hinge sleeve" in o.name for o in collection.objects) != 2:
        raise ValueError("Expected two MG-153 hinge sleeves")
    if anchor.type == "MESH":
        old = anchor
        name = old.name
        old.name = name + " · legacy surface"
        anchor = bpy.data.objects.new(name, None)
        for owner in old.users_collection:
            owner.objects.link(anchor)
        anchor.parent = old.parent
        anchor.matrix_basis = old.matrix_basis.copy()
        anchor["campProduct"] = "450"
        original = [old]
    anchor.instance_type = "COLLECTION"
    anchor.instance_collection = collection
    for obj in reversed(original):
        bpy.data.objects.remove(obj, do_unlink=True)
    return anchor
