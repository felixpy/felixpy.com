import math
import runpy
from pathlib import Path

import bmesh
import bpy
import numpy as np
from io_scene_gltf2.io.exp import meshopt
from mathutils import Vector


here = Path(__file__).resolve().parent
project = here.parents[1]
atelier = project / ".review/atelier"
review = atelier / "aerospace-notebook"
models = project / "public/media/models/stationery"
finish = runpy.run_path(str(here / "vitrine-sculpt.py"))["finish"]
title = "Introduction to Aerospace · cloth notebook"
stations = (-65, -25, 25, 65)
section_pitch = 0.834


def point(p):
    x, y, t = p
    return (x * 0.001, -t * 0.001, y * 0.001)


def collection(name, parent):
    item = bpy.data.collections.new(name)
    parent.children.link(item)
    return item


def object_mesh(
    name, coords, faces, materials, dest, inks=None, hidden=None, smooth=False
):
    data = bpy.data.meshes.new(name)
    data.from_pydata([point(v) for v in coords], [], faces)
    data.update()
    unit = bpy.data.objects.new(name, data)
    dest.objects.link(unit)
    for mat in materials:
        data.materials.append(mat)
    if inks is not None:
        data.polygons.foreach_set("material_index", inks)
    if hidden is not None:
        data.attributes.new("enclosedLeafSurface", "BOOLEAN", "FACE").data.foreach_set(
            "value", hidden
        )
    if smooth:
        for face in data.polygons:
            face.use_smooth = True
    return unit


def cloth_uvs(obj):
    mesh = obj.data
    print_uv = mesh.uv_layers.new(name="Cover layout")
    weave_uv = mesh.uv_layers.new(name="Linen weave")
    for f in mesh.polygons:
        n = f.normal
        for li in f.loop_indices:
            vertex = mesh.vertices[mesh.loops[li].vertex_index].co
            x, y, t = vertex.x * 1000, vertex.z * 1000, -vertex.y * 1000
            print_uv.data[li].uv = (x / 144 + 0.5, y / 177 + 0.5)
            if abs(n.z) > 0.75:
                pos = (x, t)
            elif abs(n.x) > 0.75:
                pos = (t, y)
            else:
                pos = (x, y)
            weave_uv.data[li].uv = (pos[0] / 6.4, pos[1] / 6.4)


def weave_normal():
    count = 128
    y, x = np.indices((count, count), dtype=np.float32) / 8
    warp = np.cos(np.pi * x) ** 4
    weft = np.cos(np.pi * y) ** 4
    crossover = np.cos(np.pi * x) * np.cos(np.pi * y)
    surface = warp * (0.44 + 0.28 * crossover) + weft * (0.44 - 0.28 * crossover)
    dx = np.roll(surface, 1, axis=1) - np.roll(surface, -1, axis=1)
    dy = np.roll(surface, 1, axis=0) - np.roll(surface, -1, axis=0)
    normals = np.stack((dx * 0.69, dy * 0.69, np.ones_like(dx)), axis=-1)
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    rgba = np.ones((count, count, 4), dtype=np.float32)
    rgba[:, :, :3] = normals * 0.5 + 0.5
    image = bpy.data.images.new(
        "Woven cotton · interlaced warp and weft",
        width=count,
        height=count,
        alpha=False,
    )
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    return image


def fabric(mat, weave, artwork=None):
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    img = tree.nodes.new("ShaderNodeTexImage")
    img.image = weave
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "Linen weave"
    tree.links.new(uv.outputs[0], img.inputs["Vector"])
    normal = tree.nodes.new("ShaderNodeNormalMap")
    normal.uv_map = uv.uv_map
    normal.inputs["Strength"].default_value = 0.86
    tree.links.new(img.outputs["Color"], normal.inputs["Color"])
    tree.links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    if artwork:
        source = tree.nodes.new("ShaderNodeTexImage")
        source.image = artwork
        source.extension = "EXTEND"
        lay = tree.nodes.new("ShaderNodeUVMap")
        lay.uv_map = "Cover layout"
        tree.links.new(lay.outputs[0], source.inputs["Vector"])
        tree.links.new(source.outputs["Color"], shader.inputs["Base Color"])


def section_profile(name, profile, extent, mat, dest, enclosed=False, endcaps=False):
    n = len(profile)
    rows = [(-extent, 0), (extent, 0)]
    if endcaps:
        rows = [
            (-extent, 1.28),
            (-91.18, 0.16),
            (-90.7, 0),
            (90.7, 0),
            (91.18, 0.16),
            (extent, 1.28),
        ]
    coords = [
        (x, y, t - math.copysign(tuck * min(1, max(0, (abs(t) - 5.48) / 2.02)), t))
        for y, tuck in rows
        for x, t in profile
    ]
    last = n * (len(rows) - 1)
    faces = [tuple(range(n)), tuple(reversed(range(last, last + n)))]
    for j in range(len(rows) - 1):
        faces.extend(
            tuple(k + j * n for k in (i, (i + 1) % n, (i + 1) % n + n, i + n))
            for i in range(n)
        )
    obj = object_mesh(name, coords, faces, [mat], dest)
    outward(obj)
    obj["productEnclosed"] = enclosed
    return obj


def outward(obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces[:])
    mesh.to_mesh(obj.data)
    mesh.free()


def shell(name, profile, rows, mat, dest, thickness, front_print=None):
    points, faces, inks = [], [], []
    for y, edge_tuck, edge_inset in rows:
        for x, z in profile:
            sign = math.copysign(1, z)
            rounding = max(0, min(1, (abs(z) - 5.48) / 2.02))
            points.append(
                (
                    x - edge_inset * max(0, min(1, (x - 69) / 5)),
                    y,
                    z - edge_tuck * sign * rounding,
                )
            )
    n = len(profile)
    for j in range(len(rows) - 1):
        for k in range(n - 1):
            i = j * n + k
            faces.append((i, i + 1, i + 1 + n, i + n))
            inks.append(1 if front_print and edge_tops(rows, j) and k < 5 else 0)
    unit = object_mesh(
        name,
        points,
        faces,
        [mat, front_print] if front_print else [mat],
        dest,
        inks,
        smooth=True,
    )
    if profile[0][1] < 0:
        unit.data.flip_normals()
    cloth_uvs(unit)
    mod = unit.modifiers.new("Backed bookcloth", "SOLIDIFY")
    mod.thickness = thickness * 0.001
    mod.offset = -1
    return unit


def edge_tops(rows, j):
    return rows[j][1] < 0.25 and rows[j + 1][1] < 0.25


def case(dest, m):
    wraps = [
        (-91.10, 1.95, 0.65),
        (-91.38, 1.76, 0.50),
        (-91.50, 1.50, 0.36),
        (-91.50, 0.55, 0.24),
        (-91.40, 0.23, 0.09),
        (-91.05, 0.06, 0),
        (-90.66, 0, 0),
        (90.66, 0, 0),
        (91.05, 0.06, 0),
        (91.40, 0.23, 0.09),
        (91.50, 0.55, 0.24),
        (91.50, 1.50, 0.36),
        (91.38, 1.76, 0.50),
        (91.10, 1.95, 0.65),
    ]
    profile = [
        (-63.2, 6.52),
        (-62.63, 6.99),
        (-61.8, 7.39),
        (-60.8, 7.5),
        (72.80, 7.5),
        (73.46, 7.43),
        (73.82, 7.22),
        (74, 6.86),
        (74, 6.00),
        (73.84, 5.71),
        (73.44, 5.50),
        (72.95, 5.46),
    ]
    near = [
        (-63.07, 6.56),
        (-62.45, 6.02),
        (-61.1, 5.60),
        (72.9, 5.60),
        (73.52, 5.83),
        (73.78, 6.13),
        (73.78, 6.80),
        (73.45, 7.17),
        (72.86, 7.30),
        (-60.8, 7.30),
        (-61.75, 7.21),
        (-62.53, 6.85),
    ]
    for side, name in [(1, "Front"), (-1, "Back")]:
        section_profile(
            name + " · bevelled greyboard",
            [(x, t * side) for x, t in near],
            90.70,
            m["board"],
            dest,
            True,
        )
        shell(
            name + " · cloth wrap with turned head and tail",
            [(x, t * side) for x, t in profile],
            wraps,
            m["cloth"],
            dest,
            0.15,
            m["print"] if side > 0 else None,
        )
        for ysign in (-1, 1):
            outer = ysign * 91.13
            inner = ysign * 78.55
            coords = [
                (-62.9, outer, 5.54 * side),
                (73.41, outer, 5.54 * side),
                (60.91, inner, 5.54 * side),
                (-62.9, inner, 5.54 * side),
            ]
            obj = object_mesh(
                name + (" · head" if ysign > 0 else " · tail") + " turn-in",
                coords,
                [(0, 1, 2, 3)],
                [m["cloth"]],
                dest,
            )
            cloth_uvs(obj)
            mod = obj.modifiers.new("Folded cloth", "SOLIDIFY")
            mod.thickness = 0.00010
        coords = [
            (73.43, -91.1, 5.48 * side),
            (73.43, 91.1, 5.48 * side),
            (60.95, 78.51, 5.48 * side),
            (60.95, -78.51, 5.48 * side),
        ]
        obj = object_mesh(
            name + " · mitred fore-edge turn-in",
            coords,
            [(0, 1, 2, 3)],
            [m["cloth"]],
            dest,
        )
        cloth_uvs(obj)
    flank = [
        (-63.2, 6.52),
        (-63.8, 6.05),
        (-64.57, 5.89),
        (-65.35, 6.00),
        (-66.4, 6.57),
        (-68.2, 7.00),
        (-71.8, 7.0),
        (-73.18, 6.79),
        (-74.07, 6.21),
        (-74.80, 5.10),
        (-75.43, 3.48),
        (-75.83, 1.77),
        (-76.0, 0),
    ]
    prof = flank + [(x, -t) for x, t in reversed(flank[:-1])]
    outline = []
    for i, (x, z) in enumerate(prof):
        prev = Vector(prof[max(0, i - 1)])
        after = Vector(prof[min(len(prof) - 1, i + 1)])
        dx, dz = (after - prev).normalized()
        outline.append((x - dz * 0.38, z + dx * 0.38))
    obj = section_profile(
        "Hollow spine · continuous cloth and two flexible joints",
        prof + outline[::-1],
        91.32,
        m["cloth"],
        dest,
        endcaps=True,
    )
    cloth_uvs(obj)
    for poly in list(obj.data.polygons)[2:]:
        poly.use_smooth = True
    leaf = [
        (-73.35, 5.66),
        (-73.95, 4.8),
        (-74.65, 3.25),
        (-75.18, 0),
        (-74.65, -3.25),
        (-73.95, -4.8),
        (-73.35, -5.66),
    ]
    section_profile(
        "Spine inlay · shaped card inside hollow case",
        leaf + [(x + 0.41, z) for x, z in reversed(leaf)],
        89.9,
        m["board"],
        dest,
    )


def rounded_back(z):
    return -72.93 + 1.94 * (abs(z) / 5.05) ** 2


def folio(index, depth, paper, dest, installed=False):
    center = (index - 5.5) * section_pitch + (0.106 if index >= 4 else -0.106)
    radius = (3.5 - depth) * 0.104
    serial = index * 4 + depth
    fore = 71.86 + math.sin(serial * 1.1) * 0.095 + math.sin(index * 0.93) * 0.17
    half = 87.61 + math.sin(serial * 1.83) * 0.07 + math.sin(index * 1.24) * 0.12
    root = rounded_back(center) - math.cos(index * 1.3) * 0.055
    ys = [-half, -half + 0.65]
    if not installed:
        for y in stations:
            ys.extend([y - 0.19, y + 0.19])
    ys.extend([half - 0.65, half])
    coords, faces, hidden = [], [], []

    def curve(r):
        arc = [
            (
                root - r * math.cos(math.pi / 2 - k * math.pi / 10),
                r * math.sin(math.pi / 2 - k * math.pi / 10),
            )
            for k in range(11)
        ]
        return [(fore, r), (fore - 0.72, r)] + arc + [(fore - 0.72, -r), (fore, -r)]

    paths = [curve(radius + 0.045), curve(radius - 0.045)]
    n = len(paths[0])
    stride = n * len(ys)
    for path in paths:
        for y in ys:
            for x, z in path:
                coords.append((x, y, center + z))

    def gap(j, k):
        return (
            0 <= j < len(ys) - 1
            and 0 <= k < n - 1
            and ys[j + 1] - ys[j] < 0.4
            and k in (6, 7)
        )

    for j in range(len(ys) - 1):
        for k in range(n - 1):
            if gap(j, k):
                continue
            a = j * n + k
            b = a + 1
            c = b + n
            d = a + n
            q = (a, b, c, d)
            covered = (
                0 < j < len(ys) - 2
                and 0 < k < n - 2
                and (depth != 0 or k not in (1, n - 3))
            )
            faces.extend([q, tuple(i + stride for i in reversed(q))])
            hidden.extend([covered, covered])
            for lo, hi, dj, dk in [
                (a, b, -1, 0),
                (b, c, 0, 1),
                (c, d, 1, 0),
                (d, a, 0, -1),
            ]:
                nj, nk = j + dj, k + dk
                if nj < 0 or nj >= len(ys) - 1 or nk < 0 or nk >= n - 1 or gap(nj, nk):
                    faces.append((hi, lo, lo + stride, hi + stride))
                    hidden.append(False)
    obj = object_mesh(
        f"Folio {depth + 1} · nested folded bifolium",
        coords,
        faces,
        [paper],
        dest,
        hidden=hidden,
    )
    outward(obj)
    obj["leaves"] = 2
    obj["gathering"] = index
    obj["nestingDepth"] = depth
    return root, center


def tube(name, path, radius, mat, dest):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = radius * 0.001
    data.bevel_resolution = 1
    data.use_fill_caps = True
    spl = data.splines.new("POLY")
    spl.points.add(len(path) - 1)
    for vertex, co in zip(spl.points, path):
        vertex.co = (*point(co), 1)
    obj = bpy.data.objects.new(name, data)
    dest.objects.link(obj)
    data.materials.append(mat)
    return obj


def sewn_block(dest, m):
    for i in range(12):
        group = collection(f"Gathering {i + 1:02} · 4 folded sheets", dest)
        for depth in range(4):
            root, center = folio(i, depth, m["papers"][(i + depth) % 3], group)
        pts = []
        for k, y in enumerate(stations):
            outer = (root - 0.50, y, center)
            inner = (root + 0.64, y, center)
            pts.extend((outer, inner) if k % 2 == 0 else (inner, outer))
        seam = tube(
            "Linen sewing · section " + str(i + 1), pts, 0.12, m["linen"], group
        )
        seam["productEnclosed"] = True
        if i:
            for y in (stations[0], stations[-1]):
                link = tube(
                    "Kettle link",
                    [
                        (root - 0.50, y, center),
                        (root - 0.78, y - 0.42, center - 0.27),
                        (root - 0.54, y, center - section_pitch),
                    ],
                    0.105,
                    m["linen"],
                    group,
                )
                link["productEnclosed"] = True
    cross = (
        [(-56.92, 5.16)]
        + [(rounded_back(z) - 0.59, z) for z in np.linspace(5.05, -5.05, 13)]
        + [(-56.92, -5.16)]
    )
    section_profile(
        "Mull lining and two glued wings",
        cross + [(x - 0.085, z * 1.011) for x, z in reversed(cross)],
        83.6,
        m["linen"],
        dest,
    )
    for sign, label in [(-1, "Rear"), (1, "Front")]:
        shape = [
            (71.96, 5.40),
            (-69.72, 5.40),
            (-71.15, 5.28),
            (-71.34, 5.19),
            (-71.05, 5.105),
            (71.84, 5.105),
        ]
        path = [(x, z * sign) for x, z in shape]
        section_profile(
            label + " · pastedown and folded free endpaper",
            path + [(x, (z + 0.075 * sign)) for x, z in reversed(path)],
            88.75,
            m["end"],
            dest,
        )
    for s, label in [(-1, "Tail"), (1, "Head")]:
        y = s * 87.97
        tube(
            label + " · corded endband",
            [(rounded_back(z) - 0.44, y, z) for z in np.linspace(-5.04, 5.04, 17)],
            0.50,
            m["linen"],
            dest,
        )
        for start, zcolor in [(0, m["linen"]), (1, m["stripe"])]:
            paths = []
            for j in range(start, 26, 2):
                path = []
                for k in range(13):
                    z = -5.06 + (j + k / 12) * 0.389
                    path.append(
                        (
                            rounded_back(z) - 0.44 + 0.51 * math.cos(k * math.tau / 12),
                            y + 0.51 * math.sin(k * math.tau / 12),
                            z,
                        )
                    )
                paths.append(path)
            obj = tube(
                label + (" · undyed wraps" if start == 0 else " · navy wraps"),
                paths[0],
                0.16,
                zcolor,
                dest,
            )
            for path in paths[1:]:
                sp = obj.data.splines.new("POLY")
                sp.points.add(len(path) - 1)
                for vert, co in zip(sp.points, path):
                    vert.co = (*point(co), 1)


def bookmark(dest, mat):
    sections = [
        (-73.7, 69.6, 1.10),
        (-73.7, 83.8, 1.12),
        (-73.58, 87.8, 1.1),
        (-72.31, 88.48, 0.70),
        (-70.80, 87.85, -0.43),
        (-69.0, 86.9, -1.665),
        (-59, 70.4, -1.665),
        (-29, 24.10, -1.665),
        (0, -30.1, -1.665),
        (29.2, -87.50, -1.665),
        (30.0, -91.2, -1.85),
        (31.2, -98.0, -2.32),
        (31.7, -100.6, -2.45),
    ]
    coords = []
    faces = []
    for j, (x, y, z) in enumerate(sections):
        width = 4.8 if j > 4 else 3.4
        for side in (-1, 1):
            coords.append(
                (
                    x + side * width * 0.5,
                    y + (side * 0.82 if j == len(sections) - 1 else 0),
                    z + side * 0.03,
                )
            )
    for j in range(len(sections) - 1):
        a = j * 2
        faces.append((a, a + 1, a + 3, a + 2))
    obj = object_mesh(
        "Ochre ribbon · glued head, folded return and bias-cut tail",
        coords,
        faces,
        [mat],
        dest,
        smooth=True,
    )
    cloth_uvs(obj)
    mod = obj.modifiers.new("Ribbon gauge", "SOLIDIFY")
    mod.thickness = 0.00013
    mod.offset = 0


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    root = collection(title, bpy.context.scene.collection)
    outer = collection("Cloth case", root)
    block = collection("Sewn text block", root)
    mats = {
        key: finish(name, color, rough=rough)
        for key, name, color, rough in [
            ("cloth", "Midnight blue cotton bookcloth", "334450", 0.81),
            ("print", "Aerospace cover · studio drawing", "334450", 0.81),
            ("board", "Compressed greyboard", "998b75", 0.94),
            ("end", "Dyed slate-blue endpapers", "415664", 0.92),
            ("linen", "Unbleached cotton and sewing linen", "c5b69b", 0.94),
            ("stripe", "Navy endband thread", "33434d", 0.9),
            ("mark", "Burnt sienna satin ribbon", "955736", 0.65),
        ]
    }
    mats["papers"] = [
        finish("Warm book paper · " + str(i + 1), c, rough=0.91)
        for i, c in enumerate(("d7cdb4", "dad0b9", "d5cab1"))
    ]
    graphic = bpy.data.images.load(str(review / "cover.png"))
    graphic.name = "Introduction to Aerospace · printed artwork"
    graphic.pack()
    normal = weave_normal()
    fabric(mats["cloth"], normal)
    fabric(mats["print"], normal, graphic)
    fabric(mats["mark"], normal)
    case(outer, mats)
    sewn_block(block, mats)
    bookmark(root, mats["mark"])
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    root["design"] = (
        "Original bilingual Beihang study notebook. Section-sewn construction informed by Bookbinders Design and the Hobonichi bookbinding instructions."
    )
    root["leaves"] = 96
    root["gatherings"] = 12
    bpy.ops.wm.save_as_mainfile(
        filepath=str(atelier / "aerospace-notebook.blend"), compress=True
    )
    for obj in list(root.all_objects):
        if "nestingDepth" in obj:
            folio(
                obj["gathering"],
                obj["nestingDepth"],
                obj.data.materials[0],
                obj.users_collection[0],
                installed=True,
            )
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == "CURVE":
            obj.data.bevel_resolution = 0
    bpy.ops.object.select_all(action="DESELECT")
    visible = [obj for obj in root.all_objects if not obj.get("productEnclosed")]
    for obj in visible:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = visible[0]
    bpy.ops.object.convert(target="MESH")
    for obj in bpy.context.selected_objects:
        attr = obj.data.attributes.get("enclosedLeafSurface")
        if attr:
            skip = {i for i, v in enumerate(attr.data) if v.value}
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.delete(
                bm, geom=[f for f in bm.faces if f.index in skip], context="FACES"
            )
            bm.to_mesh(obj.data)
            bm.free()
    bpy.ops.object.join()
    bpy.context.object.name = "Aerospace cloth notebook"
    models.mkdir(exist_ok=True, parents=True)
    meshopt.EXP_FILTER_BITS = 22
    bpy.ops.export_scene.gltf(
        filepath=str(models / "aerospace-notebook.glb"),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_extras=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )


if __name__ == "__main__":
    run()
