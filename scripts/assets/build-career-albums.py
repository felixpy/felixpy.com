import json
import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from io_scene_gltf2.io.exp import meshopt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from blender_parts import xyz

REPO = HERE.parents[1]
STUDY = REPO / ".review/atelier/career-albums"
OUTPUT = REPO / "public/media/models/stationery"
PAGE_COUNT = 14
PITCH = 1.10


def material(name, color, roughness):
    color = color.lstrip("#")
    srgb = [int(color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    rgba = tuple(
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb
    ) + (1,)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = rgba
    return mat


def linen(mat):
    size = 160
    y, x = np.mgrid[0:size, 0:size] * (math.tau * 10 / size)
    warp = np.cos(x + 0.12 * np.sin(y * 0.4))
    weft = np.cos(y + 0.10 * np.sin(x * 0.3))
    over = np.cos(x / 2) * np.cos(y / 2)
    relief = 0.5 * (warp + weft) + 0.45 * over * (warp - weft)
    du = (np.roll(relief, -1, 1) - np.roll(relief, 1, 1)) * 0.5
    dv = (np.roll(relief, -1, 0) - np.roll(relief, 1, 0)) * 0.5
    magnitude = np.sqrt(1 + du**2 + dv**2)
    image = bpy.data.images.new("Plain-weave book linen", size, size, alpha=False)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(
        np.stack(
            (
                0.5 - du / magnitude / 2,
                0.5 - dv / magnitude / 2,
                0.5 + 0.5 / magnitude,
                np.ones_like(du),
            ),
            axis=-1,
        )
        .astype("float32")
        .ravel()
    )
    image.filepath_raw = str(STUDY / "linen-normal.png")
    image.file_format = "PNG"
    image.save()
    image.pack()
    tree = mat.node_tree
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    bump = tree.nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = 0.38
    tree.links.new(tex.outputs["Color"], bump.inputs["Color"])
    tree.links.new(
        bump.outputs["Normal"], tree.nodes.get("Principled BSDF").inputs["Normal"]
    )


def solid(name, coords, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(p) for p in coords], [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    uv = data.uv_layers.new(name="Surface")
    for poly in data.polygons:
        axis = max(range(3), key=lambda k: abs(poly.normal[k]))
        for idx in poly.loop_indices:
            x, depth, up = data.vertices[data.loops[idx].vertex_index].co
            a, b = ((-depth, up), (x, up), (x, -depth))[axis]
            uv.data[idx].uv = (a / 0.0048, b / 0.0048)
    return obj


def round_rect(left, right, half_height, radius):
    result = []
    for i, (cx, cy) in enumerate(
        (
            (right - radius, half_height - radius),
            (left + radius, half_height - radius),
            (left + radius, -half_height + radius),
            (right - radius, -half_height + radius),
        )
    ):
        for j in range(5):
            angle = (i + j / 4) * math.pi / 2
            result.append(
                (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            )
    return result


def plate(name, profile, mat, close_loop=False):
    count = len(profile[0])
    faces = [
        (
            i * count + j,
            i * count + (j + 1) % count,
            (i + 1) * count + (j + 1) % count,
            (i + 1) * count + j,
        )
        for i in range(len(profile) - 1)
        for j in range(count)
    ]
    if close_loop:
        start = (len(profile) - 1) * count
        faces.extend(
            (start + j, start + (j + 1) % count, (j + 1) % count, j)
            for j in range(count)
        )
    else:
        faces += [
            tuple(reversed(range(count))),
            tuple(range((len(profile) - 1) * count, len(profile) * count)),
        ]
    return solid(name, [pt for row in profile for pt in row], faces, mat)


def level(left, right, half_height, radius, z):
    return [(x, y, z) for x, y in round_rect(left, right, half_height, radius)]


def strip(name, path, gauge, half_height, mat):
    side = []
    for i, (x, z) in enumerate(path):
        before = Vector(path[max(0, i - 1)])
        after = Vector(path[min(len(path) - 1, i + 1)])
        dx, dz = (after - before).normalized()
        side.append(
            (
                x - dz * gauge / 2,
                z + dx * gauge / 2,
                x + dz * gauge / 2,
                z - dx * gauge / 2,
            )
        )
    outline = [(a, b) for a, b, _, _ in side] + [
        (c, d) for _, _, c, d in reversed(side)
    ]
    return plate(
        name,
        [[(x, y, z) for x, z in outline] for y in (-half_height, half_height)],
        mat,
    )


def board(side, cloth, grayboard):
    name = "Front" if side == 1 else "Rear"
    left, right, height = -62.8, 72, 89

    def contour(inset, z):
        return level(
            left + inset,
            right - inset,
            height - inset,
            max(0.32, 1.05 - inset),
            z * side,
        )

    core = plate(
        name + " · binder’s board",
        [contour(0.23, 8.26), contour(0.23, 10.76)],
        grayboard,
    )
    core["enclosed"] = True
    rows = [
        contour(0.38, 11),
        contour(0.08, 10.91),
        contour(0, 10.68),
        contour(0, 8.33),
        contour(0.12, 8.09),
        contour(0.35, 8.02),
        contour(4.9, 8.02),
        contour(4.9, 8.25),
        contour(0.25, 8.25),
        contour(0.22, 10.77),
        contour(0.38, 10.78),
    ]
    count = len(rows[0])
    faces = [
        (
            i * count + j,
            i * count + (j + 1) % count,
            (i + 1) * count + (j + 1) % count,
            (i + 1) * count + j,
        )
        for i in range(len(rows) - 1)
        for j in range(count)
    ]
    faces += [
        tuple(range(count)),
        tuple(range((len(rows) - 1) * count, len(rows) * count)),
    ]
    cover = solid(
        name + " · linen with returned edges",
        [p for row in rows for p in row],
        faces,
        cloth,
    )
    for face in cover.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    cover.data.set_sharp_from_angle(angle=math.radians(40))


def jacket(cloth, grayboard):
    for side in (-1, 1):
        board(side, cloth, grayboard)
    bottom = [
        (-62.77, -10.72),
        (-63.5, -10.57),
        (-64.15, -10.10),
        (-64.8, -9.85),
        (-65.45, -10.07),
        (-66.1, -10.43),
        (-67.6, -10.43),
        (-69.6, -10.12),
        (-71.05, -9.4),
        (-71.85, -8.1),
        (-72.08, -6),
    ]
    spine = (
        bottom
        + [(-72.19, -3), (-72.24, 0), (-72.19, 3)]
        + [(x, -z) for x, z in reversed(bottom)]
    )
    wrap = strip("Spine · continuous crimped case cloth", spine, 0.32, 88.98, cloth)
    for face in wrap.data.polygons:
        face.use_smooth = abs(face.normal.z) < 0.5
    wrap.data.set_sharp_from_angle(angle=math.radians(35))
    insert = strip(
        "Spine · curved back stiffener",
        [(-71.25, -7), (-71.5, -5), (-71.65, 0), (-71.5, 5), (-71.25, 7)],
        0.78,
        87.9,
        grayboard,
    )
    insert["enclosed"] = True


def binding(stock, core, endpaper):
    for i in range(PAGE_COUNT):
        center = (i - (PAGE_COUNT - 1) / 2) * PITCH
        right = 69.1 + 0.06 * math.sin(i * 2.47)
        height = 85.6 + 0.045 * math.sin(i * 1.14)
        fold = [
            (-67.8 - 0.17 * math.cos(t), center + 0.17 * math.sin(t))
            for t in [(j / 8 - 0.5) * math.pi for j in range(9)]
        ]
        path = (
            [(right, center - 0.115), (66, center - 0.167)]
            + fold
            + [(66, center + 0.167), (right, center + 0.115)]
        )
        strip(f"Spread {i + 1:02} · continuous matte print", path, 0.20, height, stock)
        if i < PAGE_COUNT - 1:
            thickness = (PITCH - 0.534) / 2
            mid = center + PITCH / 2
            plate(
                f"Mount {i + 1:02} · laminated fibre core",
                [
                    level(-67.65, right - 0.15, height - 0.065, 0.26, mid - thickness),
                    level(-67.65, right - 0.15, height - 0.065, 0.26, mid + thickness),
                ],
                core,
            )
    for side in (-1, 1):
        plate(
            ("Rear" if side < 0 else "Front") + " · mounted end leaf",
            [
                level(-68.08, 69.06, 85.63, 0.35, 7.42 * side),
                level(-68.08, 69.06, 85.63, 0.35, 7.92 * side),
            ],
            endpaper,
        )
        plate(
            ("Rear" if side < 0 else "Front") + " · linen case lining",
            [
                level(-63.0, 68.15, 85, 0.42, 7.93 * side),
                level(-63.0, 68.15, 85, 0.42, 8.024 * side),
            ],
            endpaper,
        )


def ribbon(mat):
    xy = [(25.5, -77), (32.1, -77), (33.65, -98.4), (30.4, -97.25), (26.8, -99.7)]

    def height(y):
        return -0.55 - max(0, -y - 85.7) * 0.085

    xy[2:2] = [(32.71, -85.7)]
    xy.append((26.01, -85.7))
    return plate(
        "Bookmark · cut woven tail",
        [[(x, y, height(y) + dz) for x, y in xy] for dz in (-0.053, 0.053)],
        mat,
    )


def cover_print(mat, paper, filename):
    obj = plate(
        "Cover · tipped-in printed panel",
        [level(-60.5, 66.5, 83.5, 0.55, 11), level(-60.5, 66.5, 83.5, 0.55, 11.19)],
        paper,
    )
    obj.data.materials.append(mat)
    layer = obj.data.uv_layers.active
    for face in obj.data.polygons:
        if face.normal.y > -0.98:
            continue
        face.material_index = 1
        for j in face.loop_indices:
            x, _, y = obj.data.vertices[obj.data.loops[j].vertex_index].co
            layer.data[j].uv = ((x + 0.0605) / 0.127, (y + 0.0835) / 0.167)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(filename))
    tex.image.pack()
    mat.node_tree.links.new(
        tex.outputs["Color"],
        mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"],
    )


def edition(code):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = json.loads((STUDY / (code + ".json")).read_text())
    cloth = material("Dyed book linen", spec["jacket"], 0.83)
    linen(cloth)
    core = material("Warm archival mount board", "#c8bda7", 0.92)
    stock = material("Matte photo stock", "#ebe4d4", 0.77)
    ends = material("Dyed endpaper", "#918a7a", 0.88)
    jacket(cloth, material("Grey book board", "#8d8579", 0.96))
    binding(stock, core, ends)
    ribbon(material("Woven marker", spec["accent"], 0.76))
    cover_print(
        material("Custom cover print", "#ffffff", 0.77), stock, STUDY / (code + ".png")
    )
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["edition"] = spec["title"]
    scene["construction"] = (
        "Cloth case, 14 folded spreads and 13 intermediate mounts. Custom format."
    )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(STUDY / ("career-" + code + ".blend")), compress=True
    )
    if code != "first":
        return
    print_finish = bpy.data.materials["Custom cover print"]
    print_finish.node_tree.nodes.remove(
        next(n for n in print_finish.node_tree.nodes if n.type == "TEX_IMAGE")
    )
    for obj in list(scene.objects):
        if obj.get("enclosed"):
            bpy.data.objects.remove(obj, do_unlink=True)
    objects = list(scene.objects)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    bpy.context.object.name = "Career journals · shared binding"
    path = OUTPUT / "career-album.glb"
    old_bits = meshopt.EXP_FILTER_BITS
    try:
        meshopt.EXP_FILTER_BITS = 21
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            export_format="GLB",
            export_animations=False,
            export_meshopt_compression_enable=True,
            export_meshopt_extension="EXT_meshopt_compression",
        )
    finally:
        meshopt.EXP_FILTER_BITS = old_bits
    subprocess.run(
        ["node", str(HERE / "pack-product-geometry.mjs"), str(path)], check=True
    )


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for code in ("first", "second"):
        edition(code)
