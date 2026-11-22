import json
import math
import struct
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import convex_hull_2d

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product, finish_material, finishes

project = Path(__file__).resolve().parents[2]
ports = json.loads((project / "src/scene/gr701-lower-ports.json").read_text())
source = project / ".references/03-电脑硬件/机箱与整机/ROG Hyperion GR701/Blender"
bpy.ops.wm.read_factory_settings(use_empty=True)
product = Product("gr701-lower-grommets")
outline = ports["outlineMm"]
height = ports["heightMm"]


def pressed_lip(center):
    profile = [
        (88.9, 0.89),
        (88.9, 0.975),
        (88.1, 1),
        (84.6, 1),
        (83.8, 0.975),
        (83.8, 0.85),
        (84.6, 0.82),
        (87.5, 0.82),
        (87.8, 0.88),
    ]
    points = [
        (x / 1000, (height + y * s) / 1000, (center + z * s) / 1000)
        for x, s in profile
        for z, y in outline
    ]
    n = len(outline)
    faces = [
        (
            i * n + j,
            i * n + (j + 1) % n,
            ((i + 1) % len(profile)) * n + (j + 1) % n,
            ((i + 1) % len(profile)) * n + j,
        )
        for i in range(len(profile))
        for j in range(n)
    ]
    product.surface("Rolled EPDM panel lip", "black", points, faces, True)


def split_leaf(center, sign):
    outer_y = sign * 14.45
    stations = [-46, -30, -14, -10, 0, 10, 14, 30, 46]
    points = []
    for x in (85, 86):
        for z in stations:
            slope = (z + 46) / 92
            outside_z = (-30.4 + slope * 80.4) if sign > 0 else (-50 + slope * 80.4)
            points.extend(
                [
                    (x / 1000, (height + outer_y) / 1000, (center + outside_z) / 1000),
                    (x / 1000, (height + sign * 0.28) / 1000, (center + z) / 1000),
                ]
            )
    n = 2 * len(stations)
    faces = []
    for i in range(0, n - 2, 2):
        faces.extend(
            [
                (i, i + 2, i + 3, i + 1),
                (i + n, i + n + 1, i + n + 3, i + n + 2),
                (i, i + n, i + n + 2, i + 2),
                (i + 1, i + 3, i + n + 3, i + n + 1),
            ]
        )
    faces.extend([(0, 1, n + 1, n), (n - 2, 2 * n - 2, 2 * n - 1, n - 1)])
    product.surface("Flexible parted rubber leaf", "black", points, faces, True)


for center in ports["centersMm"]:
    pressed_lip(center)
    for sign in (-1, 1):
        split_leaf(center, sign)


def save(fitting):
    for finish, objects in fitting.parts.items():
        for obj in objects:
            if not obj.data.shape_keys:
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                bm.to_mesh(obj.data)
                bm.free()
            obj.data.materials.append(finish_material(finish))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(source / (fitting.name + ".blend")), compress=True
    )
    fitting.export(project / "public/media/models")


def rim(fitting):
    inside, outside = ports["boardInletMm"], ports["boardInletRimMm"]
    profile = [
        (88.9, 0.55),
        (88.9, 0.94),
        (88.55, 1),
        (88.12, 1),
        (88.06, "groove"),
        (86.54, "groove"),
        (86.48, 1),
        (84.7, 1),
        (84.32, 0.985),
        (84.12, 0.958),
        (84.08, 0.925),
        (84.08, 0.15),
        (84.08, 0.115),
        (84.15, 0.093),
        (84.32, 0.07),
        (84.82, 0.025),
        (85.18, 0),
        (87.6, 0),
        (88.05, 0.26),
    ]
    groove = [
        (z * 0.982 - 0.1, 106 + (y - 106) * 0.994)
        for z, y in ports["boardInletPunchMm"]
    ]
    points = []
    for x, fraction in profile:
        contour = (
            groove
            if fraction == "groove"
            else [
                (iz + (oz - iz) * fraction, iy + (oy - iy) * fraction)
                for (iz, iy), (oz, oy) in zip(inside, outside)
            ]
        )
        points.extend((x / 1000, y / 1000, z / 1000) for z, y in contour)
    n = len(inside)
    faces = [
        (
            i * n + j,
            i * n + (j + 1) % n,
            (i + 1) % len(profile) * n + (j + 1) % n,
            (i + 1) % len(profile) * n + j,
        )
        for i in range(len(profile))
        for j in range(n)
    ]
    flange = fitting.surface(
        "Rolled perimeter and moulded bead", "graphite", points, faces, True
    )
    for polygon in flange.data.polygons:
        if polygon.index // n in (9, 10, 11):
            polygon.use_smooth = False


def fitted_outline(names, offset):
    points = []
    for name in names:
        data = (project / "public/media/models" / (name + ".mesh")).read_bytes()
        magic, count, index_count, *bounds = struct.unpack_from("<4sII10f", data)
        if magic != b"BMS1":
            raise ValueError("Expected compact production cable mesh")
        verts = [
            Vector(
                tuple(
                    offset[i] + 1000 * (bounds[i] + value * bounds[i + 5] / 65535)
                    for i, value in enumerate(
                        struct.unpack_from("<3H", data, 52 + vertex * 16)
                    )
                )
            )
            for vertex in range(count)
        ]
        faces = struct.iter_unpack(
            "<3H", memoryview(data)[52 + count * 16 : 52 + count * 16 + index_count * 2]
        )
        for face in faces:
            tri = [verts[i] for i in face]
            if not (
                min(v.x for v in tri) <= 93.4
                and max(v.x for v in tri) >= 83.75
                and min(v.y for v in tri) > 35
            ):
                continue
            for v, w in zip(tri, tri[1:] + tri[:1]):
                if 83.75 <= v.x <= 93.4:
                    points.append(Vector((v.z, v.y)))
                for x in (83.75, 93.4):
                    if (v.x < x) != (w.x < x):
                        p = v.lerp(w, (x - v.x) / (w.x - v.x))
                        points.append(Vector((p.z, p.y)))
    outline = [points[i] for i in convex_hull_2d(points)]
    radius = 0.48
    padded = [
        p
        + Vector(
            (radius * math.cos(i * math.tau / 16), radius * math.sin(i * math.tau / 16))
        )
        for p in outline
        for i in range(16)
    ]
    return [padded[i] for i in convex_hull_2d(padded)]


def seam_limits(contour, z, rest):
    lo, hi = min(v.x for v in contour), max(v.x for v in contour)
    station = min(hi - 0.0001, max(lo + 0.0001, z))
    values = [
        a.y + (b.y - a.y) * (station - a.x) / (b.x - a.x)
        for a, b in zip(contour, contour[1:] + contour[:1])
        if min(a.x, b.x) <= station < max(a.x, b.x)
    ]
    distance = abs(z - station)
    weight = max(0, 1 - distance / 3.2)
    weight *= weight * (3 - 2 * weight)
    return tuple(
        rest + (edge - rest) * weight for edge in (min(values), max(values))
    ), weight


def rib_texture():
    width = 128
    image = bpy.data.images.new(
        "Fine diagonal moulded EPDM ribs", width, 8, alpha=False
    )
    image.colorspace_settings.name = "Non-Color"
    row = []
    for i in range(width):
        theta = math.tau * (i + 0.5) / width
        slope = 0.43 * math.sin(theta) * (0.5 + 0.5 * math.cos(theta)) ** 2
        n = Vector((slope, 0, 1)).normalized()
        row.extend([0.5 * n.x + 0.5, 0.5, 0.5 * n.z + 0.5, 1])
    image.pixels.foreach_set(row * 8)
    image.filepath_raw = str(project / "public/media/materials/gr701-epdm-normal.png")
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def diaphragm(fitting, apertures):
    atx, gpu = apertures
    left, right = -20.32, 10.32
    candidate_stations = {left + (right - left) * i / 40 for i in range(1, 40)}
    for contour in apertures:
        candidate_stations.update(v.x for v in contour)
    z_stations = [left]
    for z in sorted(candidate_stations):
        if z - z_stations[-1] > 0.08 and right - z > 0.08:
            z_stations.append(z)
    z_stations.append(right)
    rib_image = rib_texture()
    for index, (key, name) in enumerate(
        [
            ("lower", "Lower deflected EPDM tongue"),
            ("centre", "Centre overlapping EPDM tongue"),
            ("upper", "Upper deflected EPDM tongue"),
        ]
    ):
        rest_points, fitted_points, uvs = [], [], []
        rows = 28
        for z in z_stations:
            span = (z - left) / (right - left)
            root_distance = right - z if index == 1 else z - left
            tongue = max(0, min(1, root_distance / 3.8))
            tongue *= tongue * (3 - 2 * tongue)
            lower, upper = 82 - z, 128 + z
            bottom, top = 54 + z - 0.25, 176 - (z + 20) * 29 / 30 + 0.25
            gpu_edges, gpu_weight = seam_limits(gpu, z, lower)
            atx_edges, atx_weight = seam_limits(atx, z, upper)
            edge_land = min(z - left, right - z)
            overlap = -0.18 + 0.32 * max(0, min(1, (edge_land - 4.0) / 2.0))
            rest_interval = [
                (bottom, lower + overlap),
                (lower - overlap, upper + overlap),
                (upper - overlap, top),
            ][index]
            lower_lip = gpu_edges[0] + overlap * (1 - gpu_weight)
            upper_lip = atx_edges[1] - overlap * (1 - atx_weight)
            loaded_interval = [
                (bottom, lower_lip),
                (
                    gpu_edges[1] - overlap * (1 - gpu_weight),
                    atx_edges[0] + overlap * (1 - atx_weight),
                ),
                (upper_lip, top),
            ][index]
            for j in range(rows + 1):
                v = j / rows
                rest_y = (1 - v) * rest_interval[0] + v * rest_interval[1]
                fitted_y = (1 - v) * loaded_interval[0] + v * loaded_interval[1]
                lower_fold = (
                    gpu_weight * math.exp(-(((rest_y - lower) / 13.5) ** 2))
                    if index != 2
                    else 0
                )
                upper_fold = (
                    atx_weight * math.exp(-(((rest_y - upper) / 14) ** 2))
                    if index != 0
                    else 0
                )
                lip = math.exp(
                    -(
                        (min(v, 1 - v) * (rest_interval[1] - rest_interval[0]) / 0.62)
                        ** 2
                    )
                )
                tip = 0.28 * (root_distance / (right - left)) ** 2
                crown = math.sin(math.pi * span) * math.sin(math.pi * v)
                x = (
                    84.72
                    + (1.12 if index == 1 else -0.15)
                    - 0.55 * crown
                    + 0.23 * lip
                    + tip
                )
                loaded_x = x + tongue * (6.45 * lower_fold + 6.80 * upper_fold)
                rest_points.append((x / 1000, rest_y / 1000, z / 1000))
                fitted_points.append((loaded_x / 1000, fitted_y / 1000, z / 1000))
                diagonal = 1 if index == 2 else -1
                uvs.append(
                    (
                        (rest_y + diagonal * z) / (math.sqrt(2) * 2.25),
                        (z - diagonal * rest_y) / (math.sqrt(2) * 2.25),
                    )
                )
        n = len(rest_points)
        front = [
            (
                i * (rows + 1) + j,
                (i + 1) * (rows + 1) + j,
                (i + 1) * (rows + 1) + j + 1,
                i * (rows + 1) + j + 1,
            )
            for i in range(len(z_stations) - 1)
            for j in range(rows)
        ]
        faces = front + [tuple(i + n for i in reversed(f)) for f in front]
        border = (
            [i * (rows + 1) for i in range(len(z_stations))]
            + [(len(z_stations) - 1) * (rows + 1) + j for j in range(1, rows + 1)]
            + [i * (rows + 1) + rows for i in range(len(z_stations) - 2, -1, -1)]
            + list(range(rows - 1, 0, -1))
        )
        faces.extend(
            (b, a, a + n, b + n) for a, b in zip(border, border[1:] + border[:1])
        )

        def shell(points):
            return points + [(x + 0.00076, y, z) for x, y, z in points]

        obj = fitting.surface(name, key, shell(rest_points), faces, True)
        for poly in obj.data.polygons[2 * len(front) :]:
            poly.use_smooth = False
        for loop in obj.data.loops:
            obj.data.uv_layers.active.uv[loop.index].vector = uvs[loop.vertex_index % n]
        obj.shape_key_add(name="Basis")
        loaded = obj.shape_key_add(name="Installed cable deflection")
        for vertex, (x, y, z) in zip(loaded.data, shell(fitted_points)):
            vertex.co = (x, -z, y)
        loaded.value = 1.0
        material = finish_material(key)
        nodes, links = material.node_tree.nodes, material.node_tree.links
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = rib_image
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(texture.outputs["Color"], normal.inputs["Color"])
        links.new(
            normal.outputs["Normal"], nodes.get("Principled BSDF").inputs["Normal"]
        )


if "--board-only" not in sys.argv:
    save(product)
bpy.ops.wm.read_factory_settings(use_empty=True)
product = Product("gr701-board-inlet")
finishes.update(black=("303438", 0.76, 0.015), graphite=("383c40", 0.72, 0.02))
for key in ("upper", "centre", "lower"):
    finishes[key] = ("34383b", 0.70, 0.012)
rim(product)
diaphragm(
    product,
    [
        fitted_outline(["atx-ivory", "atx-charcoal"], (0, 0, 0)),
        fitted_outline(
            ["astral-harness-black", "astral-harness-satin"], (4, -8, -123.6)
        ),
    ],
)
save(product)
