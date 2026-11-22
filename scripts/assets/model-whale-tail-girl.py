import math
import runpy
import struct
import tempfile
import zlib
from itertools import pairwise
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
ITEM = ROOT / ".references/06-工坊与工具/三维打印与模型/Whale-tail girl"
SOURCE = ITEM / "参考图/four-view-character.png"
SCALE = 0.131 / 522
ORIGIN = np.array([207.0, 0.0, 600.0])
bpy.ops.wm.read_factory_settings(use_empty=True)
sheet = bpy.data.images.load(str(SOURCE))
sheet.colorspace_settings.name = "Non-Color"
width, height = sheet.size
pixels = np.empty((height, width, 4), dtype=np.float32)
sheet.pixels.foreach_get(pixels.ravel())
pixels = pixels[::-1].copy()
rgb = pixels[:, :, :3]
pixels[:, :, :3] = np.where(rgb < 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def finish(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = 0.62
    shader.inputs["Specular IOR Level"].default_value = 0.29
    return mat


navy = finish("Midnight blue PLA", (0.048, 0.073, 0.19))
blue = finish("Periwinkle PLA", (0.17, 0.32, 0.66))
white = finish("Porcelain white PLA", (0.88, 0.85, 0.82))
skin = finish("Peach PLA", (0.83, 0.59, 0.47))
gold = finish("Sand PLA", (0.48, 0.36, 0.23))
ink = finish("Ink blue PLA", (0.018, 0.022, 0.057))
support = finish("Breakaway support PLA", (0.28, 0.37, 0.44))
paint = finish("Multicolour filament inlay", (1, 1, 1))
color_node = paint.node_tree.nodes.new("ShaderNodeVertexColor")
color_node.layer_name = "Filament colors"
paint.node_tree.links.new(
    color_node.outputs["Color"],
    paint.node_tree.nodes.get("Principled BSDF").inputs["Base Color"],
)


def profile(keys, step):
    keys = np.asarray(keys, float)
    rows = []
    for i in range(len(keys) - 1):
        a, b = keys[i : i + 2]
        n = max(1, math.ceil(abs(b[0] - a[0]) / step))
        previous = keys[max(0, i - 1)]
        after = keys[min(len(keys) - 1, i + 2)]
        for j in range(n):
            t = j / n
            m = (
                (b - previous)
                * ((b[0] - a[0]) / max(1e-9, abs(b[0] - previous[0])))
                * np.sign(b[0] - a[0])
            )
            k = (
                (after - a)
                * ((b[0] - a[0]) / max(1e-9, abs(after[0] - a[0])))
                * np.sign(b[0] - a[0])
            )
            value = (
                (2 * t**3 - 3 * t * t + 1) * a
                + (t**3 - 2 * t * t + t) * m
                + (-2 * t**3 + 3 * t * t) * b
                + (t**3 - t * t) * k
            )
            rows.append(np.clip(value, np.minimum(a, b), np.maximum(a, b)))
    return np.array([*rows, keys[-1]])


def colors_at(u, v):
    u = np.clip(u, 1, width - 2)
    v = np.clip(v, 1, height - 2)
    i = u.astype(int)
    j = v.astype(int)
    fx = (u - i)[:, None]
    fy = (v - j)[:, None]
    return (pixels[j, i, :3] * (1 - fx) + pixels[j, i + 1, :3] * fx) * (1 - fy) + (
        pixels[j + 1, i, :3] * (1 - fx) + pixels[j + 1, i + 1, :3] * fx
    ) * fy


def build(label, coords, faces, material, photo=False, always_front=False):
    p = np.asarray(coords, dtype=float)
    geometry = (p - ORIGIN) * np.array([SCALE, SCALE, -SCALE])
    mesh = bpy.data.meshes.new(label)
    mesh.from_pydata(geometry.tolist(), [], faces)
    mesh.materials.append(paint if photo else material)
    mesh.update()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(label, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if photo:
        normal = np.empty((len(p), 3), dtype=np.float32)
        mesh.vertices.foreach_get("normal", normal.ravel())
        x, y, v = p.T
        front = colors_at(x, v)
        back = colors_at(565 - (x - 207), v)
        left = colors_at(868 + y, v)
        right = colors_at(1175 + y, v)
        fw = np.maximum(0, -normal[:, 1]) ** 4
        bw = np.maximum(0, normal[:, 1]) ** 4
        sw = abs(normal[:, 0]) ** 4
        if always_front:
            fw[:] = 1
            bw[:] = 0
            sw[:] = 0
        sw *= 0.78
        side = np.where((normal[:, 0] < 0)[:, None], left, right)
        base = np.asarray(material.diffuse_color[:3])
        rgb = (
            front * fw[:, None] + back * bw[:, None] + side * sw[:, None] + base * 0.012
        ) / (fw + bw + sw + 0.012)[:, None]
        for sample, weight in [(front, fw), (back, bw), (side, sw)]:
            leaked = np.min(sample, axis=1) > 0.978
            if material not in (white, skin):
                rgb[leaked] += (base - sample[leaked]) * (
                    weight[leaked] / (fw[leaked] + bw[leaked] + sw[leaked] + 0.012)
                )[:, None]
        if any(
            word in label
            for word in [
                "hair lock",
                "temple lock",
                "shoulder curl",
                "waterfall",
                "fringe",
                "cowlick",
                "side fin",
                "Swept whale",
                "horizontal fluke",
                "Mary Jane",
                "extended cuff",
            ]
        ):
            fade = (
                np.clip((v - 230) / 197, 0, 1)[:, None]
                if any(
                    word in label
                    for word in ["hair lock", "waterfall", "shoulder curl"]
                )
                else 0
            )
            field = (
                np.array([0.049, 0.073, 0.181]) * (1 - fade)
                + np.array([0.154, 0.305, 0.525]) * fade
            )
            if "Mary Jane" in label or "extended cuff" in label:
                field = np.array([0.030, 0.039, 0.090])
            if "whale" in label or "fluke" in label:
                field = np.array([0.070, 0.108, 0.264])
            chroma = np.clip((rgb[:, 2] - rgb[:, 0] - 0.025) / 0.1, 0, 1) * np.clip(
                (0.48 - rgb.max(1)) / 0.20, 0, 1
            )
            rgb = field + (rgb - field) * (0.52 * chroma[:, None])
        if label.startswith("Bell skirt"):
            cloth = np.array([0.043, 0.054, 0.114])
            reliable = (rgb[:, 2] > rgb[:, 0] * 1.18) & (rgb.max(1) < 0.37)
            rgb = np.where(reliable[:, None], rgb * 0.53 + cloth * 0.47, cloth)
        if "bodice" in label:
            rgb = np.where(
                (normal[:, 1] < -0.38)[:, None], front, np.array([0.044, 0.054, 0.115])
            )
        if "stocking" in label or "petticoat" in label or "headband" in label:
            rgb = rgb * 0.13 + np.array([0.845, 0.825, 0.862]) * 0.87
        if label.startswith(
            (
                "White apron",
                "Pleated white",
                "Tailored bodice",
                "Bell skirt",
                "Midnight waist",
                "Scalloped petticoat",
            )
        ) or any(
            word in label
            for word in (
                "sleeve piping",
                "extended cuff",
                "Mary Jane",
                "shoulder apron",
                "stocking",
                "swept upper",
            )
        ):
            rgb[:] = base
        if any(
            word in label
            for word in (
                "rear waterfall",
                "flowing hair lock",
                "shoulder curl",
                "temple lock",
                "Sculpted fringe",
                "side fin",
                "flyaway hair",
            )
        ):
            fade = np.clip((v - 228) / 181, 0, 1)[:, None]
            rgb[:] = (
                np.array([0.043, 0.065, 0.165]) * (1 - fade)
                + np.array([0.17, 0.37, 0.64]) * fade
            )
        col = mesh.color_attributes.new("Filament colors", "BYTE_COLOR", "POINT")
        rgba = np.ones((len(p), 4), dtype=np.float32)
        rgba[:, :3] = np.clip(rgb, 0, 1)
        col.data.foreach_set("color", rgba.ravel())
    return obj


def solid(
    name, rows, mat, photo=False, sides=48, density=5, flutes=0, always_front=False
):
    points = []
    faces = []
    for j, (v, left, right, fore, aft) in enumerate(profile(rows, density)):
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            pleat = 1 + flutes * math.cos(12 * angle + 0.007 * v)
            points.append(
                (
                    (left + right) / 2 + (right - left) / 2 * math.cos(angle) * pleat,
                    (fore + aft) / 2 + (aft - fore) / 2 * math.sin(angle) * pleat,
                    v,
                )
            )
            if j:
                k = (j - 1) * sides + i
                nxt = (j - 1) * sides + (i + 1) % sides
                faces.append((k, k + sides, nxt + sides, nxt))
    faces += [
        tuple(range(sides)),
        tuple(reversed(range(len(points) - sides, len(points)))),
    ]
    return build(name, points, faces, mat, photo, always_front)


def ribbon(name, controls, mat, photo=False, section="round", sides=18):
    keys = [[i, *p] for i, p in enumerate(controls)]
    samples = profile(keys, 0.14)
    pts = []
    faces = []
    for i, (_, x, y, v, w, d) in enumerate(samples):
        tangent = (
            samples[min(len(samples) - 1, i + 1), 1:4] - samples[max(0, i - 1), 1:4]
        )
        tangent /= max(np.linalg.norm(tangent), 1e-9)
        ref = (
            np.array([0.0, 1.0, 0.0])
            if abs(tangent[1]) < 0.89
            else np.array([0.0, 0.0, 1.0])
        )
        transverse = np.cross(tangent, ref)
        transverse /= max(np.linalg.norm(transverse), 1e-9)
        thickness = np.cross(tangent, transverse)
        for j in range(sides):
            t = 2 * math.pi * j / sides
            pts.append(
                np.array([x, y, v])
                + transverse * w * math.cos(t)
                + thickness * d * math.sin(t)
            )
            if i:
                k = (i - 1) * sides + j
                n = (i - 1) * sides + (j + 1) % sides
                faces.append((k, k + sides, n + sides, n))
    faces += [tuple(range(sides)), tuple(reversed(range(len(pts) - sides, len(pts))))]
    return build(name, pts, faces, mat, photo)


face = solid(
    "Face, raised brow and crown of head",
    [
        (125, 196, 220, -10, 15),
        (131, 161, 251, -30, 50),
        (149, 131, 280, -53, 78),
        (178, 116, 296, -72, 88),
        (206, 112, 301, -82, 90),
        (230, 115, 300, -85, 88),
        (254, 126, 291, -84, 84),
        (267, 132, 286, -82, 76),
        (282, 140, 275, -77, 62),
        (296, 158, 258, -67, 42),
        (303, 175, 241, -57, 33),
        (307, 195, 222, -49, 17),
    ],
    skin,
    False,
    196,
    1.2,
)


def vertex_pigment(obj, rgb):
    layer = obj.data.color_attributes.new("Filament colors", "BYTE_COLOR", "POINT")
    colors = np.ones((len(rgb), 4), dtype=np.float32)
    colors[:, :3] = np.clip(rgb, 0, 1)
    layer.data.foreach_set("color", colors.ravel())
    obj.data.materials.clear()
    obj.data.materials.append(paint)


coords = np.array([vert.co[:] for vert in face.data.vertices])
x, y, v = coords[:, 0] / SCALE + 207, coords[:, 1] / SCALE, 600 - coords[:, 2] / SCALE
front = np.clip((-y - 8) / 58, 0, 1)
cheeks = np.exp(-(((abs(x - 207) - 45) / 21) ** 2) - ((v - 272) / 13) ** 2)
nose = np.exp(-(((x - 207) / 8) ** 2) - ((v - 266) / 9) ** 2)
muzzle = np.exp(-(((x - 207) / 31) ** 2) - ((v - 285) / 12) ** 2)
coords[:, 1] -= SCALE * (cheeks * 3.8 + nose * 4.7 + muzzle * 2.8) * front
face.data.vertices.foreach_set("co", coords.astype(np.float32).ravel())
face.data.update()
skin_color = np.tile([0.985, 0.797, 0.716], (len(x), 1))
skin_color -= cheeks[:, None] * front[:, None] * np.array([0.001, 0.13, 0.12])
vertex_pigment(face, skin_color)


def crown_shell():
    base = np.array([v.co[:] for v in face.data.vertices]).reshape(-1, 196, 3)
    levels = 600 - base[:, 0, 2] / SCALE
    xs = base[:, :, 0] / SCALE + 207
    left, right = xs.min(axis=1), xs.max(axis=1)
    border = [
        (153, 291.5),
        (147.5, 286.3),
        (153.4, 287.6),
        (159.0, 287.2),
        (155.3, 284.9),
        (151.6, 280.1),
        (149.7, 275.7),
        (153.7, 276.4),
        (158.5, 276.1),
        (154.7, 273.6),
        (150.9, 268.2),
        (147.5, 260.4),
        (144.8, 252.1),
        (145, 248),
        (152, 227),
        (154, 237),
        (159, 219),
        (168, 204),
        (176, 192.5),
        (176.7, 210),
        (181, 229),
        (191, 244),
        (189.8, 234),
        (196.2, 243.4),
        (203.5, 247.3),
        (202.8, 243.5),
        (215.5, 248.1),
        (212.2, 240.7),
        (220.6, 245.2),
        (222.6, 244.6),
        (220.4, 239.7),
        (226.2, 229.5),
        (230.4, 217),
        (234.8, 194),
        (241.4, 211),
        (253.5, 227.5),
        (267.6, 244),
        (271.6, 249.4),
        (270.1, 256.3),
        (266.8, 264.4),
        (262.1, 271.4),
        (256.8, 275.7),
        (261.5, 275.6),
        (266.3, 273.9),
        (264.5, 280.1),
        (260.4, 284.9),
        (256.4, 287.1),
        (262.0, 287.3),
        (267.8, 285.5),
        (262.6, 291.3),
    ]

    def angle_at(x, row):
        a = np.interp(row, levels, left)
        b = np.interp(row, levels, right)
        return -math.acos(float(np.clip((2 * x - a - b) / (b - a), -1, 1)))

    border = [
        (
            x,
            row - max(0, min(9.0, (row - 204) * 0.27))
            if 148 <= x <= 267 and row < 255
            else row,
        )
        for x, row in border
    ]
    perimeter = [(-math.pi, 290), (-2.78, 278)]
    perimeter.extend((angle_at(x, row), row) for x, row in border)
    perimeter.extend(
        [(-0.26, 280), (0, 288), (0.58, 296), (1.57, 301), (2.55, 295), (math.pi, 290)]
    )
    from mathutils.geometry import delaunay_2d_cdt

    rim = profile([[i, a * 94, v] for i, (a, v) in enumerate(perimeter)], 0.17)[:, 1:]
    left_seam, right_seam = -math.pi * 94, math.pi * 94
    top = 125.08
    seam_levels = np.linspace(top, 290, 86)
    outline = [
        *rim,
        *((right_seam, v) for v in seam_levels[-2::-1]),
        *(
            (a, top)
            for a in np.linspace(right_seam, left_seam, 196, endpoint=False)[1:]
        ),
        *((left_seam, v) for v in seam_levels[:-1]),
    ]
    sites = [Vector(p) for p in outline]
    for j, row in enumerate(np.arange(top + 1.10, 301, 2.20)):
        for u in np.arange(left_seam + 1.15 + (j % 2) * 1.15, right_seam - 0.20, 2.30):
            sites.append(Vector((u, row)))
    uv, _, triangles, _, _, regions = delaunay_2d_cdt(
        sites, [], [list(reversed(range(len(outline))))], 0, 0.00003
    )
    used_faces = [tri for tri, region in zip(triangles, regions) if 0 in region]
    active = sorted({i for tri in used_faces for i in tri})
    remap = {source: i for i, source in enumerate(active)}
    triangles = [tuple(remap[i] for i in reversed(tri)) for tri in used_faces]
    param = np.array([uv[i][:] for i in active])
    points = []
    pigment = []
    count = len(param)
    angles = param[:, 0] / 94
    rows = param[:, 1]
    distance = np.full(count, np.inf)
    for p, q in pairwise(rim):
        edge = q - p
        t = np.clip(((param - p) @ edge) / max(edge @ edge, 1e-8), 0, 1)
        distance = np.minimum(
            distance, np.linalg.norm(param - p - t[:, None] * edge, axis=1)
        )

    def surface(angle, row):
        lo = np.clip(np.searchsorted(levels, row) - 1, 0, len(levels) - 2)
        frac = (row - levels[lo]) / (levels[lo + 1] - levels[lo])
        index = np.mod(angle, math.tau) * 196 / math.tau
        before = index.astype(int) % 196
        after = (before + 1) % 196
        f = (index - np.floor(index))[:, None]
        a = base[lo, before] * (1 - f) + base[lo, after] * f
        b = base[lo + 1, before] * (1 - f) + base[lo + 1, after] * f
        return a + (b - a) * frac[:, None]

    def scalp_row(angle, row, outside):
        position = surface(angle, row)
        radial = np.column_stack((np.cos(angle), np.sin(angle), np.zeros(count)))
        along = surface(angle + 0.001, row) - surface(angle - 0.001, row)
        down = surface(angle, row + 0.04) - surface(
            angle, np.maximum(levels[0], row - 0.04)
        )
        normal = np.cross(down, along)
        normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-12)
        normal *= np.where(np.sum(normal * radial, axis=1) < 0, -1, 1)[:, None]
        u = np.clip((row - 126) / 121, 0, 1)
        front = np.maximum(0, -np.sin(angle))
        flute = 0.5 + 0.5 * np.cos(angle * 8 + np.sin(angle * 2) * u * 3)
        thickness = 1.36 + 0.46 * flute
        lip = np.clip(distance / 5.8, 0, 1)
        lift = (0.48 + lip * (thickness - 0.48)) if outside else -0.24
        xyz = position + normal * (SCALE * np.asarray(lift).reshape(-1, 1))
        points.extend(
            np.column_stack(
                (207 + xyz[:, 0] / SCALE, xyz[:, 1] / SCALE, 600 - xyz[:, 2] / SCALE)
            )
        )
        gradient = (0.12 + 0.88 * u * u) * front
        dye = (
            np.array([0.056, 0.077, 0.195])
            + (np.array([0.114, 0.165, 0.352]) - [0.056, 0.077, 0.195])
            * gradient[:, None]
        )
        pigment.extend(dye * (1 if outside else 0.92))

    scalp_row(angles, rows, True)
    scalp_row(angles, rows, False)
    quads = triangles + [tuple(i + count for i in reversed(tri)) for tri in triangles]
    border_edges = {}
    for tri in triangles:
        for a, b in zip(tri, (*tri[1:], tri[0])):
            key = tuple(sorted((a, b)))
            if key in border_edges:
                del border_edges[key]
            else:
                border_edges[key] = (a, b)
    for a, b in border_edges.values():
        if abs(rows[a] - top) < 0.001 and abs(rows[b] - top) < 0.001:
            continue
        if (
            abs(param[a, 0] - param[b, 0]) < 0.001
            and abs(abs(param[a, 0]) - right_seam) < 0.001
        ):
            continue
        quads.append((b, a, a + count, b + count))
    crown_ring = sorted(
        np.flatnonzero((abs(rows - top) < 0.001) & (param[:, 0] < right_seam - 0.001)),
        key=lambda i: angles[i],
    )
    quads.extend((tuple(crown_ring), tuple(i + count for i in reversed(crown_ring))))
    crown = build(
        "Crown and forehead fringe · continuous fitted shell", points, quads, navy
    )
    vertex_pigment(crown, np.array(pigment))
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(crown.data)
    bm.verts.ensure_lookup_table()
    left_edge = np.flatnonzero(abs(param[:, 0] - left_seam) < 0.001)
    right_edge = np.flatnonzero(abs(param[:, 0] - right_seam) < 0.001)
    left_edge = left_edge[np.argsort(rows[left_edge])]
    right_edge = right_edge[np.argsort(rows[right_edge])]
    if not np.allclose(rows[left_edge], rows[right_edge], atol=0.0001):
        raise ValueError("The two sides of the crown seam must share their stations")
    mates = {
        bm.verts[int(b) + offset]: bm.verts[int(a) + offset]
        for a, b in zip(left_edge, right_edge, strict=True)
        for offset in (0, count)
    }
    bmesh.ops.weld_verts(bm, targetmap=mates)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(crown.data)
    bm.free()
    crown["foreheadInteriorEmbedMm"] = round(0.24 * SCALE * 1000, 3)
    crown["hemThicknessMm"] = round((0.48 + 0.24) * SCALE * 1000, 3)
    fringe = runpy.run_path(str(Path(__file__).with_name("whale_fringe.py")))
    locks = fringe["sculpt_fringe"](
        surface, levels, left, right, profile, build, vertex_pigment, navy, SCALE
    )
    fringe["finish_hair"](crown, locks)


crown_shell()
head_surface = BVHTree.FromPolygons(
    [v.co for v in face.data.vertices], [p.vertices[:] for p in face.data.polygons]
)


solid(
    "Porcelain neck",
    [(298, 193, 223, -43, 16), (305, 192, 224, -44, 14), (324, 193, 222, -36, 18)],
    skin,
)
solid(
    "Tailored bodice and pleated shirt",
    [
        (307, 183, 232, -40, 25),
        (317, 164, 252, -47, 31),
        (334, 150, 263, -50, 35),
        (356, 160, 256, -53, 37),
        (379, 171, 246, -45, 36),
        (390, 170, 247, -40, 39),
    ],
    navy,
    True,
    92,
    2.1,
)
solid(
    "Midnight waist ribbon",
    [
        (369, 168, 248, -49, 38),
        (373, 166, 249, -51, 40),
        (387, 170, 246, -49, 38),
        (390, 173, 245, -44, 36),
    ],
    navy,
    True,
    90,
    2,
)
solid(
    "Bell skirt with twelve flutes",
    [
        (380, 174, 245, -40, 36),
        (399, 149, 263, -52, 49),
        (426, 131, 282, -63, 64),
        (455, 107, 308, -76, 76),
        (476, 95, 318, -84, 84),
        (487, 90, 324, -83, 84),
        (496, 99, 315, -76, 75),
    ],
    navy,
    True,
    152,
    2,
    0.026,
)
solid(
    "Scalloped petticoat",
    [
        (481, 101, 314, -75, 73),
        (492, 97, 319, -77, 76),
        (501, 102, 311, -72, 73),
        (508, 121, 292, -65, 66),
        (513, 135, 277, -61, 65),
    ],
    white,
    True,
    144,
    2,
    0.047,
)
apron = solid(
    "White apron with whale embroidery",
    [
        (386, 180, 240, -48, -45),
        (396, 165, 253, -51, -46),
        (419, 150, 264, -65, -55),
        (445, 147, 265, -82, -67),
        (460, 158, 259, -84, -72),
        (472, 178, 240, -83, -74),
        (476, 198, 219, -81, -76),
    ],
    white,
    True,
    120,
    1.5,
    0,
    True,
)
solid(
    "Pleated white pinafore bib",
    [
        (311, 182, 232, -37, -35),
        (320, 167, 249, -49, -46),
        (336, 164, 250, -53, -50),
        (351, 166, 248, -55, -52),
        (369, 170, 245, -53, -50),
        (373, 173, 241, -51, -48),
    ],
    white,
    True,
    90,
    1.6,
    0,
    True,
)


def sculpt_hand(side, token):
    strokes = []

    def stroke(name, keys):
        mirrored = [(207 + side * x, y, v, h, w) for x, y, v, h, w in keys]
        strokes.append(ribbon(token + " " + name, mirrored, skin, sides=24))

    palm_rows = profile(
        [
            (130, -1.3, 342.8, 9.3, 9.8, 10.2),
            (138, -1.0, 343.0, 10.6, 11.6, 10.8),
            (143, -0.8, 343.5, 9.7, 11.1, 13.0),
            (149, -0.4, 344.0, 8.4, 10.3, 15.3),
            (154, 0.2, 344.3, 6.7, 9.4, 15.6),
            (159, 0.5, 344.5, 5.2, 8.2, 13.1),
            (163, 1.3, 345.0, 3.1, 6.0, 9.3),
            (165, 1.6, 345.5, 0.8, 2.4, 4.6),
            (165.4, 1.8, 345.9, 0.3, 0.7, 1.8),
        ],
        0.8,
    )
    coords, faces = [], []
    count = 48
    for i, (x, center, row, dorsal, volar, breadth) in enumerate(palm_rows):
        for j in range(count):
            angle = math.tau * j / count
            arch, across = math.cos(angle), math.sin(angle)
            rise = arch * (volar if arch > 0 else dorsal)
            if arch > 0:
                hollow = math.exp(
                    -(((x - 150) / 7.7) ** 2) - ((across + 0.05) / 0.37) ** 2
                )
                rise -= 2.6 * hollow * arch
            coords.append((207 + side * x, center + breadth * across, row + rise))
            if i:
                a = (i - 1) * count + j
                b = (i - 1) * count + (j + 1) % count
                faces.append((a, b, b + count, a + count))
    faces.extend(
        [tuple(reversed(range(count))), tuple(range(len(coords) - count, len(coords)))]
    )
    if side < 0:
        faces = [tuple(reversed(face)) for face in faces]
    strokes.append(build(token + " arched palm and wrist", coords, faces, skin))
    for name, base_y, tip_y, end, tip_v, r, roll in [
        ("index", -9.2, -10.4, 171.7, 342.9, 3.7, 0.5),
        ("middle", -2.3, -3.4, 174.6, 343.8, 3.85, 0.85),
        ("ring", 4.6, 4.7, 171.0, 345.1, 3.5, 1.15),
        ("little", 10.0, 12.1, 165.9, 346.0, 3.05, 1.55),
    ]:
        stroke(
            name + " finger",
            [
                (144.5, base_y * 0.80, 342.1 + roll, r * 0.54, r * 0.62),
                (149.2, base_y, 341.6 + roll, r * 1.18, r * 1.19),
                (
                    154.5,
                    base_y + 0.20 * (tip_y - base_y),
                    340.9 + roll,
                    r * 1.26,
                    r * 1.06,
                ),
                (
                    end - 8.1,
                    base_y + 0.66 * (tip_y - base_y),
                    tip_v - 2.5 - roll,
                    r * 1.13,
                    r * 1.05,
                ),
                (end - 4.9, tip_y, tip_v - 1.1, r * 0.94, r * 1.02),
                (end - 2.8, tip_y, tip_v - 0.35, r * 0.91, r * 0.98),
                (end - 1.35, tip_y, tip_v - 0.11, r * 0.72, r * 0.80),
                (end - 0.47, tip_y, tip_v, r * 0.43, r * 0.46),
                (end, tip_y, tip_v, 0.23, 0.22),
            ],
        )
    stroke(
        "opposed thumb",
        [
            (140.0, -8.4, 345.9, 5.7, 5.9),
            (144.1, -13.4, 348.1, 5.3, 5.0),
            (148.5, -16.2, 349.1, 4.25, 4.15),
            (152.2, -17.8, 349.9, 3.8, 3.66),
            (155.2, -18.1, 350.0, 3.32, 3.4),
            (157.3, -17.9, 349.5, 2.77, 2.95),
            (158.9, -17.6, 349.0, 1.70, 1.83),
            (159.6, -17.5, 348.8, 0.31, 0.31),
        ],
    )
    bpy.ops.object.select_all(action="DESELECT")
    for part in strokes:
        part.select_set(True)
    palm = strokes[0]
    bpy.context.view_layer.objects.active = palm
    bpy.ops.object.join()
    palm.name = token + " hand · palm, opposed thumb and curled fingers"
    palm.data.name = palm.name
    remesh = palm.modifiers.new("Sculpt knuckles and webbing", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = 0.000075
    remesh.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    relax = palm.modifiers.new("Soft fingertip finish", "SMOOTH")
    relax.factor = 0.59
    relax.iterations = 9
    bpy.ops.object.modifier_apply(modifier=relax.name)
    reduce = palm.modifiers.new("Retain sculpted curvature", "DECIMATE")
    reduce.ratio = 0.40
    bpy.ops.object.modifier_apply(modifier=reduce.name)
    verts = np.array([v.co[:] for v in palm.data.vertices]) / SCALE
    x = verts[:, 0] * side
    row = 600 - verts[:, 2]
    underside = np.clip((row - 342) / 12, 0, 1)
    tips = np.clip((x - 150) / 23, 0, 1)
    dye = np.tile([0.985, 0.797, 0.716], (len(x), 1))
    dye -= (underside * 0.8 + tips * 0.22)[:, None] * np.array([0.012, 0.165, 0.11])
    vertex_pigment(palm, dye)
    palm["digits"] = 5


cuff_facing = finish("Indigo woven cuff facing", (0.037, 0.049, 0.117))
cuff_thread = finish("Cuff embroidery · pearl lavender", (0.42, 0.39, 0.53))


def tailored_sleeve(side, token):
    cloth = [
        (48, 1, 339, 18, 21),
        (68, 0, 343, 19, 22),
        (97, -1, 345, 17, 20),
        (119, -2, 344, 16.3, 17.5),
        (123, -2, 343.8, 16.0, 17.2),
        (125, -2, 343.7, 16.2, 17.4),
        (133, -2, 343.3, 15.8, 17.1),
        (135.7, -2, 343.2, 15.5, 16.8),
        (136.7, -2, 343.2, 14.8, 16.2),
        (136.6, -2, 343.2, 14.1, 15.5),
        (134.2, -2, 343.3, 13.4, 14.7),
        (129.0, -1.4, 343, 8.4, 8.7),
    ]
    binding = [
        (134.5, -2, 343.2, 14.0, 15.3),
        (136.6, -2, 343.2, 14.4, 15.8),
        (138.0, -2, 343.2, 14.15, 15.4),
        (138.45, -2, 343.2, 13.5, 14.8),
        (138.05, -2, 343.2, 12.85, 14.1),
        (136.0, -2, 343.1, 12.2, 13.6),
        (132.1, -1.5, 343, 9.45, 10.1),
        (131.85, -1.5, 343, 9.85, 10.5),
    ]
    count = 64
    for rows, material, title, annular in [
        (cloth, navy, " extended cuff and sleeve", False),
        (binding, white, " linen cuff lining", True),
    ]:
        points, faces = [], []
        for x, center, row, h, d in rows:
            for i in range(count):
                a = i * math.tau / count
                fold = min(1, max(0, (x - 116) / 16))
                oval = 1 + fold * (
                    0.021 * math.cos(3 * a + 0.6) + 0.015 * math.sin(5 * a)
                )
                rim = x + fold * (0.64 * math.cos(a) + 0.39 * math.sin(2 * a - 0.45))
                points.append(
                    (
                        207 + side * rim,
                        center + d * math.sin(a) * oval,
                        row + h * math.cos(a) * oval,
                    )
                )
        ring_pairs = len(rows) if annular else len(rows) - 1
        for row in range(ring_pairs):
            a, b = row * count, ((row + 1) % len(rows)) * count
            for i in range(count):
                j = (i + 1) % count
                faces.append((a + i, a + j, b + j, b + i))
        if not annular:
            faces.extend(
                [
                    tuple(reversed(range(count))),
                    tuple(range(len(points) - count, len(points))),
                ]
            )
        if side < 0:
            faces = [tuple(reversed(face)) for face in faces]
        item = build(token + title, points, faces, material)
        if not annular:
            item.data.materials.append(cuff_facing)
            for poly in item.data.polygons[4 * count : 7 * count]:
                poly.material_index = 1
        else:
            item["cuffMouth"] = "Rolled binding with an open bore and inset wrist"
    points, faces = [], []
    for center_x, center_row, length, span, rotation in [
        (129.4, 342.5, 0.97, 0.45, 0.04),
        (130.25, 343.45, 0.83, 0.44, 1.30),
        (129.1, 344.2, 0.80, 0.44, -0.20),
        (128.2, 343.2, 0.94, 0.45, 1.34),
    ]:
        rings = []
        for k in range(9):
            latitude = k * math.pi / 8
            ring = []
            for j in range(1 if k in (0, 8) else 14):
                angle = j * math.tau / 14
                u = length * math.cos(angle) * math.sin(latitude)
                v = span * math.sin(angle) * math.sin(latitude)
                x = center_x + u * math.sin(rotation) + v * math.cos(rotation)
                row = center_row + u * math.cos(rotation) - v * math.sin(rotation)
                along = (x - 125) / 8
                depth = 17.4 - 0.3 * along
                height = 16.2 - 0.4 * along
                row_offset = row - (343.7 - 0.4 * along)
                fold = min(1, max(0, (x - 116) / 16))
                oval = 1
                for _ in range(3):
                    theta = math.tau - math.acos(row_offset / (height * oval))
                    oval = 1 + fold * (
                        0.021 * math.cos(3 * theta + 0.6) + 0.015 * math.sin(5 * theta)
                    )
                surface = -2 + depth * math.sin(theta) * oval
                ring.append(len(points))
                points.append(
                    (207 + side * x, surface - 0.05 - 0.38 * math.cos(latitude), row)
                )
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for j in range(14):
                n = (j + 1) % 14
                if len(a) == 1:
                    face = (a[0], b[j], b[n])
                elif len(b) == 1:
                    face = (a[j], b[0], a[n])
                else:
                    face = (a[j], b[j], b[n], a[n])
                faces.append(face if side > 0 else tuple(reversed(face)))
    build(token + " cuff flower stitching", points, faces, cuff_thread)


for side, token in [(-1, "Left"), (1, "Right")]:

    def side_x(offset, side=side):
        return 207 + side * offset

    def symmetric(points):
        return [(side_x(x), y, v, w, d) for x, y, v, w, d in points]

    foot = side_x(26)
    solid(
        token + " stocking",
        [
            (487, foot - 13, foot + 13, -13, 19),
            (502, foot - 19, foot + 19, -20, 21),
            (528, foot - 19, foot + 19, -18, 20),
            (562, foot - 16, foot + 15, -16, 16),
            (580, foot - 14, foot + 14, -15, 15),
        ],
        white,
        True,
    )
    solid(
        token + " stacked leather outsole",
        [
            (592, foot - 17, foot + 17, -34, 20),
            (595, foot - 18, foot + 18, -35, 20),
            (598, foot - 17.5, foot + 17.5, -34, 20),
            (600, foot - 16, foot + 16, -32, 19),
        ],
        ink,
        sides=72,
        density=0.85,
    )
    solid(
        token + " patent leather vamp",
        [
            (578.5, foot - 5, foot + 5, -23, -18),
            (580, foot - 11, foot + 11, -28, -13),
            (584, foot - 16, foot + 16, -34, -9),
            (590, foot - 18, foot + 18, -35, 4),
            (595, foot - 17.7, foot + 17.7, -34, 15),
        ],
        navy,
        sides=72,
        density=1,
    )
    solid(
        token + " low leather counter",
        [
            (565, foot - 9, foot + 9, 6, 17),
            (569, foot - 14, foot + 14, 3, 19),
            (576, foot - 16, foot + 16, 1, 20),
            (589, foot - 17, foot + 17, -4, 21),
            (595, foot - 17, foot + 17, -9, 20),
        ],
        navy,
        sides=64,
        density=1.3,
    )
    for sign in (-1, 1):
        ribbon(
            token + " slipper leather quarter",
            [
                (foot + sign * 12, 12, 566, 1.8, 1.8),
                (foot + sign * 15, 3, 574, 4.0, 2.0),
                (foot + sign * 16, -8, 580, 4, 2.0),
                (foot + sign * 15, -19, 585, 3.4, 1.8),
            ],
            navy,
        )
    ribbon(
        token + " buckled instep strap",
        [
            (foot - 15, -4, 579, 2.4, 1.5),
            (foot - 13, -11, 574, 2.5, 1.7),
            (foot - 7, -15.5, 571.7, 2.65, 1.45),
            (foot, -17.3, 570.8, 2.8, 1.35),
            (foot + 7, -15.7, 571.5, 2.65, 1.5),
            (foot + 13, -11.2, 574, 2.6, 1.6),
            (foot + 15, -5, 578.3, 2.2, 1.4),
        ],
        navy,
        sides=20,
    )
    lock = foot + side * 12
    ribbon(
        token + " pale brass shoe buckle",
        [
            (lock - 2.7, -12.3, 575, 0.6, 0.5),
            (lock - 2.8, -13, 572, 0.65, 0.55),
            (lock + 1, -12, 571, 0.65, 0.55),
            (lock + 2.2, -12, 574.6, 0.6, 0.55),
            (lock - 2.7, -12.3, 575.1, 0.6, 0.5),
        ],
        gold,
        sides=12,
    )
    tailored_sleeve(side, token)
    sculpt_hand(side, token)
    ribbon(
        token + " shoulder apron frill",
        symmetric(
            [
                (28, -18, 311, 3, 3),
                (39, -31, 317, 6, 5),
                (45, -41, 332, 5.5, 4),
                (44, -43, 350, 4, 3.5),
                (42, -42, 363, 3, 2),
            ]
        ),
        white,
        True,
        sides=18,
    )
    for i, (x, off) in enumerate([(88, -10), (105, 12), (119, 31)]):
        ribbon(
            token + " flowing hair lock " + str(i + 1),
            symmetric(
                [
                    (59, 23 + off, 193, 13, 12),
                    (75, 23 + off, 236, 17, 16),
                    (x - 16, 28 + off, 286, 20, 18),
                    (x - 3, 36 + off, 329, 19, 13),
                    (x + 13, 39 + off, 362, 17, 10),
                    (x + 9, 38 + off, 384, 13, 8),
                    (x - 3, 42 + off, 406, 7, 4),
                    (x + 8, 42 + off, 419 - i * 5, 0.55, 0.42),
                ]
            ),
            blue,
            True,
            sides=38,
        )
    ribbon(
        token + " temple lock",
        symmetric(
            [
                (53, -12, 166, 2.7, 2.2),
                (62, -14, 193, 4, 3),
                (70, -18, 215, 7.5, 6),
                (78, -26, 235, 12.5, 8.8),
                (82, -35, 247, 15.6, 10.6),
                (82, -38, 258, 16, 12),
                (75, -38, 278, 12, 9),
                (62, -45, 298, 1.1, 1),
            ]
        ),
        navy,
        True,
        sides=36,
    )
    ribbon(
        token + " shoulder curl",
        symmetric(
            [
                (75, -36, 267, 8, 6),
                (74, -32, 285, 10, 6),
                (67, -38, 304, 8, 6),
                (58, -43, 319, 7, 4.8),
                (67, -45, 334, 5.1, 3.4),
                (68, -48, 343, 3, 2.0),
                (62, -46, 348, 0.6, 0.6),
            ]
        ),
        blue,
        True,
        sides=28,
    )
    ribbon(
        token + " side fin",
        symmetric(
            [
                (78, -2, 220, 8, 10),
                (91, -3, 239, 13, 11),
                (113, -1, 255, 12, 8),
                (137, 0, 268, 5, 4),
                (150, -1, 271, 0.65, 0.65),
            ]
        ),
        navy,
        True,
        sides=30,
    )
    ribbon(
        token + " back ribbon",
        symmetric(
            [
                (0, 46, 395, 5, 5),
                (17, 53, 390, 13, 5),
                (40, 49, 383, 10, 4),
                (49, 45, 389, 4, 2),
            ]
        ),
        navy,
        True,
        sides=24,
    )
    ribbon(
        token + " front neck bow",
        symmetric(
            [
                (1, -49, 321, 3, 2),
                (7, -50, 318, 5, 3),
                (17, -49, 315, 5.5, 3),
                (20, -47, 318, 2.2, 1.7),
            ]
        ),
        navy,
        sides=18,
    )
    ribbon(
        token + " front neck ribbon",
        symmetric(
            [(2, -50, 321, 2.4, 2), (8, -51, 330, 4, 2.2), (14, -51, 337, 2.4, 1.7)]
        ),
        navy,
        sides=16,
    )
    for sign in (-1, 1):
        ribbon(
            token + " skirt knot",
            symmetric(
                [
                    (71, -48, 456, 1.3, 1),
                    (71 + sign * 4, -49, 454, 2.5, 1.3),
                    (71 + sign * 8, -48, 451, 2, 1),
                    (71 + sign * 7, -48, 455, 1.2, 0.8),
                ]
            ),
            gold,
            sides=12,
        )
    ribbon(
        token + " sacrificial tree",
        symmetric(
            [
                (127, 1, 599, 6, 6),
                (127, 1, 591, 5, 5),
                (126, 7, 554, 4.1, 4.1),
                (129, 10, 508, 3.7, 3.7),
                (134, 5, 459, 3.5, 3.5),
                (139, 1, 413, 3.1, 3.1),
                (140, 0, 357, 2.1, 2.1),
            ]
        ),
        support,
        sides=14,
    )
    solid(
        token + " support skirt",
        [
            (597, side_x(127) - 10, side_x(127) + 10, -10, 12),
            (600, side_x(127) - 10, side_x(127) + 10, -10, 12),
        ],
        support,
        sides=28,
    )
    ribbon(
        token + " branch to skirt",
        symmetric(
            [
                (127, 8, 539, 3.4, 3.4),
                (119, 1, 523, 2.8, 2.8),
                (104, -3, 504, 2.1, 2.1),
                (103, -3, 496, 1.5, 1.5),
            ]
        ),
        support,
        sides=12,
    )


ribbon(
    "Swept whaletail",
    [
        (215, 40, 474, 17, 20),
        (219, 61, 506, 24, 20),
        (227, 76, 540, 27, 22),
        (247, 91, 566, 24, 19),
        (274, 106, 579, 19, 15),
        (299, 119, 577, 14, 10),
        (317, 131, 565, 10, 7),
        (327, 143, 542, 7.2, 4.5),
        (329, 151, 531, 4, 3),
    ],
    blue,
    True,
    sides=54,
)
for sign in [-1, 1]:
    ribbon(
        "Paired horizontal fluke",
        [
            (329, 149, 536, 4.8, 4),
            (329 + sign * 11, 154, 530, 9, 5),
            (329 + sign * 23, 158, 522, 12, 5.4),
            (329 + sign * 36, 160, 512, 7, 3.8),
            (329 + sign * 46, 164, 496, 0.8, 1),
        ],
        navy,
        True,
        sides=30,
    )


ribbon(
    "Crown cowlick",
    [
        (205, -2, 128, 3, 5),
        (202, -3, 111, 4.8, 5),
        (193, -4, 95, 6, 5),
        (173, -5, 86, 6, 4),
        (155, -5, 88, 4.8, 3),
        (141, -6, 96, 2.5, 2),
        (130, -6, 105, 0.6, 0.5),
    ],
    navy,
    True,
    sides=24,
)


def surface_at(tree, x, v):
    hit, _, _, _ = tree.ray_cast(
        Vector(((x - 207) * SCALE, -0.08, (600 - v) * SCALE)), Vector((0, 1, 0))
    )
    if hit is None:
        raise ValueError(f"No front surface at {x}, {v}")
    return hit.y / SCALE


def enamel_portrait():
    size = 384
    x0, x1, v0, v1 = 111, 305, 123, 313
    xp, vp = np.meshgrid(np.linspace(x0, x1, size), np.linspace(v1, v0, size))
    x, v = xp.ravel(), vp.ravel()
    cheek = np.exp(-(((abs(x - 207) - 45) / 21) ** 2) - ((v - 272) / 13) ** 2)
    base = np.tile([0.985, 0.797, 0.716], (len(x), 1)) - cheek[:, None] * [
        0.001,
        0.13,
        0.12,
    ]
    source = colors_at(x, v)
    for center in (172, 244):
        local = np.sqrt(((x - center) / 23.0) ** 2 + ((v - 253) / 22.5) ** 2)
        boundary = np.clip((1.0 - local) / 0.135, 0, 1)
        broad = (x - 207) * (x - 207) > 31**2
        blue_hair = (
            (source[:, 2] > source[:, 0] * 1.25)
            & (source[:, 2] > source[:, 1] * 1.09)
            & broad
            & (abs(v - 253) > 16)
        )
        boundary[blue_hair] = 0
        skin_pixel = (source[:, 0] > source[:, 2] * 1.16) & (source[:, 0] > 0.45)
        ink = np.where(
            skin_pixel[:, None], base + (source - [1.0, 0.841, 0.752]) * 0.42, source
        )
        base += boundary[:, None] * (ink - base)
    srgb = np.where(
        base <= 0.0031308,
        12.92 * base,
        1.055 * np.maximum(base, 0) ** (1 / 2.4) - 0.055,
    )
    rgb = (np.clip(srgb, 0, 1).reshape(size, size, 3) * 255 + 0.5).astype(np.uint8)

    def chunk(name, data):
        contents = name + data
        return (
            struct.pack(">I", len(data))
            + contents
            + struct.pack(">I", zlib.crc32(contents))
        )

    encoded = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"sRGB", b"\0")
        + chunk(
            b"IDAT",
            zlib.compress(b"".join(b"\0" + row.tobytes() for row in rgb[::-1]), 9),
        )
        + chunk(b"IEND", b"")
    )
    with tempfile.TemporaryDirectory(dir=ROOT / ".review/atelier") as tmp:
        filename = Path(tmp) / "portrait-enamel.png"
        filename.write_bytes(encoded)
        image = bpy.data.images.load(str(filename))
        image.pack()
        image.filepath = "//portrait-enamel.png"
    pigment = finish("Printed portrait enamel", (0.95, 0.79, 0.72))
    pigment.node_tree.nodes.get("Principled BSDF").inputs[
        "Roughness"
    ].default_value = 0.59
    tex = pigment.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "EXTEND"
    pigment.node_tree.links.new(
        tex.outputs["Color"],
        pigment.node_tree.nodes.get("Principled BSDF").inputs["Base Color"],
    )
    uvs = face.data.uv_layers.new(name="Registered portrait surface")
    coord = np.array([v.co[:] for v in face.data.vertices])
    x, y, v = coord[:, 0] / SCALE + 207, coord[:, 1] / SCALE, 600 - coord[:, 2] / SCALE
    for cx in (172, 244):
        radius = ((x - cx) / 21) ** 2 + ((v - 254) / 20) ** 2
        coord[:, 1] -= SCALE * 1.6 * np.maximum(0, 1 - radius) ** 2 * (y < 0)
    face.data.vertices.foreach_set("co", coord.astype(np.float32).ravel())
    face.data.update()
    ids = np.array([l.vertex_index for l in face.data.loops])
    uv = np.column_stack(((x - x0) / (x1 - x0), (v1 - v) / (v1 - v0)))
    uv[y > 0] = [0.5, 0.05]
    uvs.data.foreach_set("uv", uv[ids].astype(np.float32).ravel())
    face.data.materials.clear()
    face.data.materials.append(pigment)


def raised_motif(name, outline, surface, material):
    from mathutils.geometry import tessellate_polygon

    points = [Vector((x, v, 0)) for x, v in outline]
    tris = [tuple(t) for t in tessellate_polygon([points])]
    size = len(points)
    coords = [
        (x, surface_at(surface, x, v) - rise, v)
        for rise in (-0.4, 0.84)
        for x, v, _ in points
    ]
    faces = tris + [tuple(size + i for i in reversed(t)) for t in tris]
    faces.extend(
        (i, (i + 1) % size, (i + 1) % size + size, i + size) for i in range(size)
    )
    build(name, coords, faces, material)


enamel_portrait()

for line, coords, mat in [
    (
        "Smile",
        [
            (198, 284, 0.25),
            (202, 285.4, 0.67),
            (207, 286.1, 0.78),
            (212, 285.3, 0.65),
            (216, 283.7, 0.24),
        ],
        ink,
    ),
    (
        "Nose bridge",
        [
            (206.4, 270, 0.28),
            (206.8, 272.8, 1.5),
            (207.5, 274.1, 1.15),
            (208.7, 274.2, 0.26),
        ],
        skin,
    ),
]:
    ribbon(
        line,
        [
            (x, surface_at(head_surface, x, v) - 0.50, v, r, r * 0.8)
            for x, v, r in coords
        ],
        mat,
        sides=12,
    )

for sign in (-1, 1):
    ribbon(
        "Crossed pinafore back strap",
        [
            (207 + sign * x, y, v, w, 1.4)
            for x, y, v, w in [
                (32, 26, 317, 2.8),
                (25, 36, 332, 4.2),
                (10, 41, 351, 3.9),
                (-6, 41, 370, 4.2),
                (-13, 39, 381, 4.0),
            ]
        ],
        white,
        sides=14,
    )
    ribbon(
        "Fishtail back bow streamer",
        [
            (207 + sign * x, y, v, w, d)
            for x, y, v, w, d in [
                (0, 52, 396, 2, 1.4),
                (7, 58, 411, 6, 2.7),
                (16, 69, 434, 7.3, 2.5),
                (25, 77, 454, 8, 2.1),
                (30, 82, 470, 7.7, 1.8),
                (33, 84, 474, 1.4, 0.8),
            ]
        ],
        navy,
        sides=16,
    )
    ribbon(
        "Curled flyaway hair strand",
        [
            (207 + sign * x, y, v, w, d)
            for x, y, v, w, d in [
                (86, 13, 276, 2.8, 2.1),
                (103, 20, 302, 5.8, 3.0),
                (131, 30, 331, 5.3, 3.1),
                (138, 36, 353, 4.2, 2.5),
                (129, 40, 375, 3, 2),
                (132, 41, 389, 0.45, 0.40),
            ]
        ],
        blue,
        True,
        sides=18,
    )


def front_tree(prefix):
    o = next(o for o in bpy.context.scene.objects if o.name.startswith(prefix))
    return BVHTree.FromPolygons(
        [v.co for v in o.data.vertices], [p.vertices[:] for p in o.data.polygons]
    )


bodice_surface = front_tree("Tailored bodice")
bib = next(
    o for o in bpy.context.scene.objects if o.name.startswith("Pleated white pinafore")
)
for vertex in bib.data.vertices:
    x = vertex.co.x / SCALE + 207
    v = 600 - vertex.co.z / SCALE
    face_hit = bodice_surface.ray_cast(
        Vector((vertex.co.x, -0.08, vertex.co.z)), Vector((0, 1, 0))
    )[0]
    if face_hit:
        phase = 0.42 + 0.75 * np.clip((-vertex.co.y / SCALE - 39) / 18, 0, 1)
        vertex.co.y = face_hit.y - SCALE * (phase + 0.8 * np.cos((x - 207) * 0.26) ** 2)
bib.data.update()
bib_surface = front_tree("Pleated white pinafore")
for x in (180, 187, 228, 235):
    rows = [
        (x + (207 - x) * trim, v, r)
        for v, trim, r in [
            (322, 0.18, 0.45),
            (332, 0.03, 0.8),
            (350, 0, 1.0),
            (367, 0.04, 0.55),
        ]
    ]
    ribbon(
        "Pinafore tuck seam",
        [(px, surface_at(bib_surface, px, v) - 0.6, v, r, 0.45) for px, v, r in rows],
        white,
        sides=10,
    )
for v in (342, 354, 365):
    x = 208
    d = surface_at(bib_surface, x, v)
    solid(
        "Covered blouse button",
        [
            (v - 1.75, x - 0.5, x + 0.5, d - 0.5, d + 0.2),
            (v - 1, x - 1.55, x + 1.55, d - 1.05, d + 0.4),
            (v + 1, x - 1.55, x + 1.55, d - 1.05, d + 0.4),
            (v + 1.75, x - 0.5, x + 0.5, d - 0.5, d + 0.2),
        ],
        ink,
        sides=16,
        density=1,
    )

skirt_surface = front_tree("Bell skirt")
for x, v in [
    (122, 466),
    (133, 472),
    (151, 477),
    (173, 482),
    (191, 483),
    (219, 483),
    (241, 480),
    (263, 477),
    (284, 473),
    (297, 464),
]:
    coords = [
        (x, v - 2.2),
        (x + 0.6, v - 0.5),
        (x + 2.1, v),
        (x + 0.6, v + 0.5),
        (x, v + 2.1),
        (x - 0.6, v + 0.5),
        (x - 2.1, v),
        (x - 0.6, v - 0.5),
    ]
    raised_motif("Skirt embroidered star", coords, skirt_surface, gold)

apron_surface = BVHTree.FromPolygons(
    [v.co for v in apron.data.vertices], [p.vertices[:] for p in apron.data.polygons]
)
raised_motif(
    "Whale applique · arched back, split tail and belly",
    [
        (211.5, 435),
        (211.8, 431),
        (214.2, 426.8),
        (218, 424.4),
        (223, 424),
        (227.6, 425.6),
        (231.4, 429),
        (234.3, 431.3),
        (237, 431.6),
        (239.8, 429.2),
        (238.3, 427),
        (237.4, 424),
        (238, 421.5),
        (241.1, 422.5),
        (243.1, 425.8),
        (245.6, 423.4),
        (249.7, 423),
        (248.8, 426.2),
        (245.7, 428.6),
        (244, 432.7),
        (240.5, 437.8),
        (234.4, 441.9),
        (228, 443),
        (220, 441.8),
        (215, 439.3),
    ],
    apron_surface,
    navy,
)
for sign in (-1, 1):
    hem = []
    for x, v in [
        (0, 469),
        (15, 467),
        (32, 461),
        (47, 450),
        (53, 439),
        (55, 425),
        (52, 414),
    ]:
        px = 207 + sign * x
        hem.append((px, surface_at(apron_surface, px, v) - 0.6, v, 0.85, 0.48))
    ribbon("Apron rolled stitched hem", hem, white, sides=10)
for name, points in [
    (
        "Embroidered whale belly",
        [
            (212, 435, 0.3),
            (216, 438, 1.0),
            (222, 440.3, 1.0),
            (230, 441, 1.2),
            (237, 438.7, 0.9),
            (242, 433.8, 0.25),
        ],
    ),
    (
        "Whale fountain left",
        [(227, 418, 0.4), (225.2, 415, 1.0), (222.3, 414.4, 1.15), (220.7, 415, 0.45)],
    ),
    (
        "Whale fountain right",
        [
            (228, 417.7, 0.45),
            (229.5, 414.3, 0.95),
            (232, 413.3, 1.1),
            (233.3, 413.5, 0.35),
        ],
    ),
]:
    ribbon(
        name,
        [(x, surface_at(apron_surface, x, v) - 0.6, v, r, 0.55) for x, v, r in points],
        navy,
        sides=12,
    )


def folded_bow(name, x, depth, row, scale, mat):
    for side in (-1, 1):
        verts, quads = [], []
        for ring in range(19):
            t = max(0.01, ring / 18)
            height = (2.4 + 6.2 * math.sin(t * 2.22)) * scale
            center = row - 1.6 * t * scale
            for i in range(36):
                a = i * math.tau / 36
                v = center + math.cos(a) * height
                y = depth + math.sin(a) * (0.9 + 2.6 * math.sin(math.pi * t)) * scale
                y -= scale * 1.6 * math.cos(2 * a) * math.sin(math.pi * t)
                verts.append((x + side * scale * (1 + 10 * t), y, v))
                idx = len(verts) - 1
                nex = ring * 36 + (i + 1) % 36
                if ring:
                    quads.append((idx - 36, nex - 36, nex, idx))
        quads.extend(
            [tuple(range(36)), tuple(reversed(range(len(verts) - 36, len(verts))))]
        )
        build(name + " folded silk loop", verts, quads, mat)
    solid(
        name + " gathered center knot",
        [
            (
                row - 3.5 * scale,
                x - 1.2 * scale,
                x + 1.2 * scale,
                depth - 2 * scale,
                depth + scale,
            ),
            (
                row,
                x - 2.8 * scale,
                x + 2.8 * scale,
                depth - 2.8 * scale,
                depth + 2 * scale,
            ),
            (
                row + 3.2 * scale,
                x - 1.5 * scale,
                x + 1.5 * scale,
                depth - 1.7 * scale,
                depth + scale,
            ),
        ],
        mat,
        sides=24,
        density=0.65,
    )


folded_bow("Silk collar bow", 207, -51, 322, 1.55, navy)
for px in (135, 280):
    vv = 457
    yy = surface_at(skirt_surface, px, vv)
    folded_bow("Side hem grosgrain ribbon", px, yy - 2.7, vv, 0.91, navy)
    for ss in (-1, 1):
        strand = []
        for dx, dy, sw in [(0, 1, 1.1), (3, 5, 1.8), (5, 10, 2.0), (7, 14, 1.7)]:
            xx, zz = px + dx * ss, vv + dy
            strand.append((xx, surface_at(skirt_surface, xx, zz) - 2, zz, sw, 0.65))
        ribbon("Folded ribbon at skirt vent", strand, navy, sides=12)


def lace_strip(name, line, outward, count, reach, mat):
    line = np.asarray(line, float)
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))]

    def at(u):
        v = np.clip(u, 0, 1) * arc[-1]
        return np.array([np.interp(v, arc, line[:, i]) for i in range(3)])

    for i in range(count):
        outer = []
        eye = []
        for t in np.linspace(0, 1, 12):
            p = at((i + t) / count)
            radial = np.array(outward(p))
            radial /= np.linalg.norm(radial)
            out = math.sin(math.pi * t)
            bridge = p + radial * (reach * (0.18 + 0.82 * out**0.75))
            bridge[1] -= 0.86 * out
            outer.append((*bridge, 0.95, 0.61))
            oval = p + radial * (reach * 0.62 * math.sin(math.pi * t) ** 0.85)
            eye.append((*oval, 0.59, 0.39))
        ribbon(name + " scalloped outside thread", outer, mat, sides=8)
        ribbon(name + " inset openwork", eye, mat, sides=8)


border = []
for sg in (-1, 1):
    side_rows = [
        (28, 390),
        (42, 398),
        (53, 411),
        (58, 422),
        (58, 437),
        (55, 448),
        (48, 458),
        (37, 466),
        (25, 471),
        (12, 474),
        (0, 475),
    ]
    if sg == 1:
        side_rows = side_rows[::-1][1:]
    for dx, row in side_rows:
        x = 207 + sg * dx
        inner_x = 207 + sg * dx * 0.92
        inner_row = row if row < 474 else 472.5
        y = surface_at(apron_surface, inner_x, inner_row) - 0.25
        border.append((x, y, row))
lace_strip(
    "Apron edge · embroidered eyelet lace",
    border,
    lambda p: (p[0] - 207, 0, (p[2] - 393) * 0.74),
    31,
    4.6,
    white,
)
for offset in (-1, 1):
    line = []
    for dx, v in [
        (32, 314),
        (38, 319),
        (42, 327),
        (46, 337),
        (45, 347),
        (43, 359),
        (40, 367),
    ]:
        line.append((207 + offset * dx, -35 - (v - 314) * 0.24, v))
    lace_strip(
        "Pinafore shoulder ruffle",
        line,
        lambda p, sg=offset: (sg, -0.47, 0.16),
        8,
        4.0,
        white,
    )
for sg in (-1, 1):
    for i, off in enumerate((0, 8, 16)):
        strand = [
            (77 + i * 4, 37 + off, 275, 2.9),
            (85 + i * 5, 41 + off, 302, 4.4),
            (102 + i * 7, 39 + off, 329, 4.0),
            (113 + i * 7, 37 + off, 353, 3.8),
            (118 + i * 6, 36 + off, 369, 3.4),
            (116 + i * 5, 35 + off, 387, 2.8),
            (107 + i * 5, 36 + off, 403, 1.9),
            (110 + i * 5, 42 + off, 412 - i * 2, 0.28),
        ]
        ribbon(
            "Separate curved pointed lock",
            [(207 + sg * x, y, v, w, w * 0.61) for x, y, v, w in strand],
            blue,
            sides=14,
        )


for row, radius, mat in [(477, 0.58, gold), (483, 1.15, navy), (490, 0.9, gold)]:
    ring = []
    for a in np.linspace(0, math.tau, 169):
        axis = Vector((math.cos(a), math.sin(a), 0))
        z = (600 - row) * SCALE
        origin = Vector((0, 0, z)) + axis * 0.08
        hit = skirt_surface.ray_cast(origin, -axis)[0]
        if hit:
            pos = hit + axis * (0.8 * SCALE)
            ring.append(
                (pos.x / SCALE + 207, pos.y / SCALE, row, radius, radius * 0.72)
            )
    ribbon("Continuous skirt border stitching", ring, mat, sides=9)


def back_locks():
    rows = [
        (135, 0.1, 28, 43, 19, 4),
        (153, 0, 60, 76, 34, 8),
        (177, 0, 76, 89, 35, 12),
        (208, 0, 87, 98, 26, 16),
        (239, 0, 90, 101, 24, 18),
        (264, 0, 93, 103, 26, 20),
        (282, 0.5, 96, 99, 30, 21),
        (300, 3, 101, 87, 32, 21),
        (318, 12, 112, 76, 35, 24),
        (343, 24, 127, 70, 37, 29),
        (367, 39, 135, 77, 41, 30),
        (389, 51, 132, 87, 45, 29),
        (405, 56, 122, 95, 51, 25),
        (416, 53, 108, 91, 54, 21),
        (423, 52, 90, 83, 60, 17),
        (427, 55, 67, 79, 69, 9),
    ]
    for side in (-1, 1):
        points, mesh_faces, rgb = [], [], []
        segments = 72
        for k, (row, inside, outside, y0, y1, bulge) in enumerate(profile(rows, 2)):
            for i in range(segments):
                a = math.tau * i / segments
                u = (1 - math.cos(a)) / 2
                lateral = inside + (outside - inside) * u
                y = y0 * (1 - u) + y1 * u + math.sin(a) * bulge * 1.44
                if row < 274 and math.sin(a) > 0:
                    natural = head_surface.ray_cast(
                        Vector((side * lateral * SCALE, 0.08, (600 - row) * SCALE)),
                        Vector((0, -1, 0)),
                    )[0]
                    if natural:
                        y = max(y, natural.y / SCALE + 0.75)
                if math.sin(a) > 0:
                    trail = u + 0.047 * math.sin((row - 140) / 44 + 0.35 * side)
                    crests = sum(
                        math.exp(-(((trail - peak) / spread) ** 2))
                        for peak, spread in ((0.15, 0.14), (0.49, 0.18), (0.85, 0.14))
                    )
                    rise = np.clip((row - 134) / 35, 0, 1) * np.clip(
                        (427 - row) / 32, 0, 1
                    )
                    y += float(6.4 * rise * crests * math.sin(a) ** 0.65)
                x = 207 + side * lateral
                points.append((x, y, row))
                fade = np.clip((row - 260) / 150, 0, 1)
                base = (
                    np.array([0.063, 0.084, 0.219]) * (1 - fade)
                    + np.array([0.22, 0.435, 0.72]) * fade
                )
                photo = colors_at(np.array([565 - side * lateral]), np.array([row]))[0]
                if (
                    photo[2] > 1.22 * photo[0]
                    and photo[2] > 1.07 * photo[1]
                    and photo.max() < 0.86
                ):
                    base = 0.60 * base + 0.4 * photo
                rib = math.sin((u + 0.08 * math.sin(row / 32)) * math.pi * 3) ** 2
                rgb.append(base * (0.92 + 0.09 * rib))
                if k:
                    j = k * segments + i
                    n = k * segments + (i + 1) % segments
                    mesh_faces.append(
                        (j - segments, j, n, n - segments)
                        if side > 0
                        else (n - segments, n, j, j - segments)
                    )
        mesh_faces += [
            tuple(range(segments)),
            tuple(reversed(range(len(points) - segments, len(points)))),
        ]
        item = build(
            "Split mantle of hair · curled rear fall", points, mesh_faces, blue
        )
        vertex_pigment(item, np.array(rgb))


back_locks()


def sewn_headpiece():
    import bmesh

    crown = next(
        o for o in bpy.context.scene.objects if o.name.startswith("Crown and forehead")
    )
    hair = BVHTree.FromPolygons(
        [v.co for v in crown.data.vertices],
        [p.vertices[:] for p in crown.data.polygons],
    )

    def loft(label, rings, material, dye=None):
        count = len(rings[0])
        faces = [tuple(range(count - 1, -1, -1))]
        for row in range(len(rings) - 1):
            lo = row * count
            for col in range(count):
                a, b = lo + col, lo + (col + 1) % count
                faces.append((a, b, b + count, a + count))
        faces.append(tuple(range((len(rings) - 1) * count, len(rings) * count)))
        obj = build(label, np.concatenate(rings), faces, material)
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        mesh.free()
        if dye is not None:
            vertex_pigment(obj, np.concatenate(dye))
        return obj

    def hair_radius(angle, depth):
        axis = Vector((math.sin(angle), 0, math.cos(angle)))
        center = Vector((0, depth * SCALE, (600 - 216) * SCALE))
        hit = hair.ray_cast(center + axis * 0.05, -axis)[0]
        if hit is None:
            raise ValueError("Headband must meet the crown at every station")
        return (hit - center).dot(axis) / SCALE

    def station(angle, depth, distance):
        return np.array(
            [207 + math.sin(angle) * distance, depth, 216 - math.cos(angle) * distance]
        )

    base, flounce, colors, cord = [], [], [], []
    extent = 1.55
    for angle in np.linspace(-extent, extent, 249):
        t = (angle / extent + 1) / 2
        temple = abs(math.sin(angle))
        depth = -6.3 + 29.2 * temple**1.7
        band = []
        for phi in np.linspace(0, math.tau, 16, endpoint=False):
            delta = depth + 4.05 * math.cos(phi)
            band.append(
                station(
                    angle,
                    delta,
                    hair_radius(angle, delta) + 1.75 + 2.35 * math.sin(phi),
                )
            )
        base.append(band)
        foot = depth + 2.5
        radius = hair_radius(angle, foot)
        phase = math.tau * (11.5 * t + 0.10 * math.sin(t * math.tau) + 0.12)
        lobe = (0.5 + 0.5 * math.cos(phase)) ** 0.54
        taper = 0.52 + 0.48 * min(1, min(t, 1 - t) / 0.065)
        height = (
            (6.6 + 15 * max(0, math.cos(angle)) ** 0.77) * (0.62 + 0.38 * lobe) * taper
        )
        sweep = (7.4 + 6.7 * lobe) * taper
        cross, pigment = [], []
        for side in (1, -1):
            span = np.linspace(0, 1, 10)
            for u in span if side == 1 else span[::-1]:
                radial = radius + 3.2 + (height - 2.35) * u
                forward = (
                    foot
                    + u * sweep
                    + math.sin(u * math.pi) * (3.5 * math.sin(phase) - 1.2)
                )
                forward += side * (0.60 + 0.30 * u)
                cross.append(station(angle, forward, radial))
                shade = 1 - (
                    0.26 * (1 - lobe) ** 1.25 * (1 - 0.32 * u) + 0.05 * (side == 1)
                )
                pigment.append(np.array([0.90, 0.876, 0.892]) * shade)
        flounce.append(cross)
        colors.append(pigment)
        rim = station(angle, foot + sweep, radius + 0.85 + height)
        cord.append(
            [
                rim
                + (
                    station(angle, 0.53 * math.sin(p), 0.58 * math.cos(p))
                    - [207, 0, 216]
                )
                for p in np.linspace(0, math.tau, 10, endpoint=False)
            ]
        )
    loft("Headpiece · curved cotton binding seated on the hair", base, white)
    loft("Headpiece · gathered round scallops", flounce, white, colors)
    loft("Headpiece · rolled hem following the scallops", cord, white)

    angle = 1.54
    depth = 24.2
    anchor = station(angle, depth, hair_radius(angle, depth) + 8.7)
    vertical = np.array([0, 0, 1])
    across = np.array([0.56, 0.8285, 0])
    normal = np.array([0.8285, -0.56, 0])
    fastening = []
    for u in np.linspace(-1, 1, 7):
        fastening.append(
            [
                anchor
                + across * (u * 3.0)
                + normal * (-3.3 + 6.6 * math.cos(p))
                + vertical * (5.2 * math.sin(p))
                for p in np.linspace(0, math.tau, 20, endpoint=False)
            ]
        )
    loft("Headpiece · silk tie around the binding end", fastening, blue)
    for sign in (-1, 1):
        loops, shades = [], []
        for t in np.linspace(0, 1, 22):
            ring, pigment = [], []
            for phi in np.linspace(0, math.tau, 32, endpoint=False):
                span = (1.8 + 15.3 * t) * sign
                rise = (3.8 + 8.0 * math.sin(t * 2.16)) * math.cos(phi)
                bulge = (1.1 + 2.9 * math.sin(t * math.pi)) * math.sin(phi)
                channel = math.sin(t * math.pi) * math.cos(phi * 2)
                position = (
                    anchor
                    + across * span
                    + vertical * (rise - t)
                    + normal * (bulge - channel + 2)
                )
                ring.append(position)
                pigment.append(
                    np.array([0.083, 0.239, 0.485])
                    * (0.89 + 0.13 * math.sin(phi) - 0.28 * max(0, channel))
                )
            loops.append(ring)
            shades.append(pigment)
        loft("Headpiece · cerulean temple bow loop", loops, blue, shades)
    knot = []
    for t in np.linspace(-1, 1, 9):
        knot.append(
            [
                anchor
                + vertical * (t * 5.2)
                + normal * (3.9 + 2.85 * math.cos(p))
                + across * ((2.7 + 0.55 * t * t) * math.sin(p))
                for p in np.linspace(0, math.tau, 22, endpoint=False)
            ]
        )
    loft("Headpiece · wrapped silk knot above the binding", knot, blue)


sewn_headpiece()

figure_collection = bpy.data.collections.new(
    "DeepSeek Whale Girl · printable components"
)
bpy.context.scene.collection.children.link(figure_collection)
support_collection = bpy.data.collections.new("Optional removable FDM supports")
bpy.context.scene.collection.children.link(support_collection)
for obj in list(bpy.context.scene.collection.objects):
    is_support = any(
        word in obj.name
        for word in ("sacrificial tree", "support skirt", "branch to skirt")
    )
    (support_collection if is_support else figure_collection).objects.link(obj)
    bpy.context.scene.collection.objects.unlink(obj)
support_collection.hide_render = True
support_collection.hide_viewport = True
scene = bpy.context.scene
scene.name = "DeepSeek Whale Girl · 131 mm"
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
scene.display.shading.color_type = "VERTEX"
bpy.context.preferences.filepaths.save_version = 0
triangles = []
components = []
for index, o in enumerate(figure_collection.objects):
    mesh = o.data
    mesh.calc_loop_triangles()
    vertices = np.array([v.co[:] for v in mesh.vertices]) * 1000
    tris = vertices[np.array([t.vertices[:] for t in mesh.loop_triangles])]
    triangles.append(tris)
    components.append(np.full(len(tris), index, np.uint16))
slice_source = ROOT / ".review/atelier/whale-tail-slice-source.npz"
slice_source.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(
    slice_source,
    triangles=np.concatenate(triangles),
    component=np.concatenate(components),
)
bpy.ops.object.select_all(action="DESELECT")
copies = []
for component in figure_collection.objects:
    obj = component.copy()
    obj.data = component.data.copy()
    scene.collection.objects.link(obj)
    obj.select_set(True)
    copies.append(obj)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
figure = bpy.context.view_layer.objects.active
figure.name = "DeepSeek Whale Girl · multicolour PLA"
figure.data.name = "DeepSeek Whale Girl print surfaces"
top = max(v.co.z for v in figure.data.vertices)
upper = np.array(
    [(v.co.x, -v.co.y) for v in figure.data.vertices if v.co.z >= top - 0.015]
)
ring = []
for angle in np.arange(24) * math.tau / 24:
    direction = np.array([math.cos(angle), math.sin(angle)])
    point = upper[np.argmax(upper @ direction)]
    if not ring or np.linalg.norm(point - ring[-1]) > 0.00035:
        ring.append(point)
if np.linalg.norm(ring[0] - ring[-1]) < 0.00035:
    ring.pop()
figure["crownOutline"] = np.array(ring).ravel().tolist()
figure["printHeight"] = top
figure.data["printHeight"] = top
figure.data["startX"] = float(ring[0][0])
figure.data["startY"] = -float(ring[0][1])
bpy.ops.export_scene.gltf(
    filepath=str(ROOT / "public/media/models/whale-tail-girl.glb"),
    export_format="GLB",
    use_selection=True,
    export_extras=True,
    export_vertex_color="MATERIAL",
    export_animations=False,
    export_cameras=False,
    export_lights=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
figure.data.use_fake_user = True
bpy.data.objects.remove(figure, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(
    filepath=str(ITEM / "Blender/whale-tail-girl.blend"), compress=True
)
