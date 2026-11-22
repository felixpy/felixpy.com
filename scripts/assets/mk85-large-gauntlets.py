import itertools
import math
import runpy
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree


def articulated_shells(obj, work, points):
    library = runpy.run_path(str(Path(__file__).with_name("mk85-large-panels.py")))[
        "COAT"
    ]
    names = list(library)
    materials = []
    for name, (hex_colour, metal, roughness) in library.items():
        if name in {"red", "garnet", "gold", "bronze", "seal"}:
            hex_colour = {
                "red": "911b29",
                "garnet": "731627",
                "gold": "ae8957",
                "bronze": "85623b",
                "seal": "62232b",
            }[name]
        c = np.asarray(list(bytes.fromhex(hex_colour))) / 255
        rgb = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        m = bpy.data.materials.new("MK85 · cast " + name)
        m.use_nodes = True
        sh = m.node_tree.nodes["Principled BSDF"]
        sh.inputs["Base Color"].default_value = (*rgb, 1)
        sh.inputs["Metallic"].default_value = metal
        sh.inputs["Roughness"].default_value = roughness + 0.05
        m.diffuse_color = (*rgb, 1)
        materials.append(m)
    positions, polys, coat = [], [], []
    registered_faces = []
    frontal_faces = set()

    def vertex(p):
        positions.append(np.asarray(p, float) * 0.001)
        return len(positions) - 1

    def face(verts, name):
        if None in verts:
            return
        polys.append(tuple(verts))
        coat.append(names.index(name))

    faces = [
        list(p.vertices) for p in obj.data.polygons if max(p.vertices) < len(points)
    ]
    tree = BVHTree.FromPolygons(points.tolist(), faces)

    def cast(c, a, z):
        direction = np.array([np.cos(a), np.sin(a), 0.0])
        location = np.r_[c, z] * 0.001 + direction * 0.20
        hit, _, _, _ = tree.ray_cast(location, -direction, 0.26)
        if hit is None:
            return None
        q = np.array(hit) * 1000
        return q if np.linalg.norm(q[:2] - c) < 33 else None

    for sign in [-1, 1]:
        x = -67.25 if sign < 0 else 49.1
        wrist_y = -5.8 if sign < 0 else -9.7

        def handpos(q, x=x, sign=sign):
            return np.array((x + sign * q[0], q[1], q[2]))

        def loft(path, dims, paints, ey=(0, 1, 0), steps=18, exponent=0.78):
            path = np.array(path, float)
            rows = []
            for i, (p, (r, w)) in enumerate(zip(path, dims)):
                tangent = path[min(len(path) - 1, i + 1)] - path[max(0, i - 1)]
                tangent /= np.linalg.norm(tangent)
                ax = np.array(ey, float)
                ax -= tangent * np.dot(ax, tangent)
                ax /= np.linalg.norm(ax)
                normal = np.cross(ax, tangent)
                ring = []
                for a in np.linspace(0, math.tau, steps, endpoint=False):
                    ct, st = np.cos(a), np.sin(a)
                    d = normal * (np.sign(ct) * abs(ct) ** exponent * r) + ax * (
                        np.sign(st) * abs(st) ** exponent * w
                    )
                    ring.append(vertex(handpos(p + d)))
                rows.append(ring)
            for i, (a, b) in enumerate(itertools.pairwise(rows)):
                for j in range(steps):
                    face(
                        (a[j], b[j], b[(j + 1) % steps], a[(j + 1) % steps]),
                        paints[min(i, len(paints) - 1)],
                    )
                    registered_faces.append(len(polys) - 1)
                    frontal_faces.add(len(polys) - 1)
            face(rows[0][::-1], paints[0])
            face(rows[-1], paints[-1])

        loft(
            [
                (0, -17, 267),
                (0, -16, 269),
                (0, -15.3, 273),
                (0, -12.6, 279),
                (0, wrist_y, 284),
                (0, wrist_y + 2.2, 289),
            ],
            [(4.1, 7.5), (5.4, 9.1), (6.3, 9.2), (6.9, 8.8), (6.6, 8.6), (5.6, 7.8)],
            ["garnet", "garnet", "red", "garnet", "gunmetal"],
        )
        for digit, (dy, drop, rad) in enumerate(
            [
                (-24.0, -0.8, 2.72),
                (-18.8, -1.55, 2.83),
                (-13.4, -0.62, 2.68),
                (-8.5, 1.2, 2.32),
            ]
        ):
            path = [
                (3.3, dy + 2.5, 274.5),
                (5.0, dy + 1.2, 272.3),
                (6.2, dy, 270.5),
                (6.4, dy - 0.6, 268.4),
                (5.7, dy - 0.8, 266.9),
                (4.3, dy - 0.8, 265.1),
                (2.1, dy - 0.65, 263.6),
                (0.2, dy - 0.5, 263.3),
                (-1.9, dy - 0.1, 263.8),
                (-3.4, dy + 0.4, 265),
                (-4.05, dy + 1, 267),
            ]
            path = [
                (px, py, pz + drop + (1.2 if sign > 0 else 0)) for px, py, pz in path
            ]
            dims = [
                (rad * 0.48, rad * 0.74),
                (rad * 0.7, rad * 0.91),
                (rad * 0.91, rad * 0.93),
                (rad, rad),
                (rad * 0.85, rad * 0.93),
                (rad * 0.67, rad * 0.81),
                (rad * 0.82, rad * 0.96),
                (rad * 0.82, rad * 0.93),
                (rad * 0.64, rad * 0.82),
                (rad * 0.74, rad * 0.81),
                (rad * 0.45, rad * 0.6),
            ]
            loft(
                path,
                dims,
                [
                    "garnet",
                    "red",
                    "red",
                    "red",
                    "seal",
                    "red",
                    "garnet",
                    "seal",
                    "bronze",
                    "gold",
                ],
            )
        loft(
            [
                (-3.2, -19.9, 278.2),
                (-4.5, -22.0, 276.0),
                (-4.1, -24.9, 272.7),
                (-2.7, -26.35, 270.8),
                (-0.7, -27.7, 269.3),
                (1.2, -27.3, 268.8),
                (3.5, -26.5, 268.9),
            ],
            [
                (2.8, 3.5),
                (3.4, 3.55),
                (3.0, 3.3),
                (2.7, 3.05),
                (2.55, 2.85),
                (2.3, 2.7),
                (1.55, 1.9),
            ],
            ["garnet", "red", "red", "seal", "red", "garnet"],
            ey=(0, 0, 1),
        )
        for k in range(3):
            loft(
                [
                    (4.5, -17.9 + k * 4.5, 273),
                    (6.6, -16.9 + k * 4.35, 276.9),
                    (6.75, -15.1 + k * 4.1, 280.3),
                    (5.3, -13.6 + k * 3.9, 282.9),
                ],
                [(0.23, 0.65), (0.56, 0.92), (0.62, 0.83), (0.22, 0.38)],
                ["gunmetal", "red", "red"],
            )
        center_z = np.array(
            [285, 297, 309, 320, 331, 344, 358, 365, 375, 385, 400, 418]
        )
        centers = np.array(
            [
                [-67, -6],
                [-66, 0],
                [-62.2, 4.8],
                [-57.5, 7.5],
                [-53, 7.0],
                [-49, 4.3],
                [-48, 4],
                [-42, 3],
                [-29, 0],
                [-12, -6],
                [-12, -7],
                [-12, -4],
            ]
            if sign < 0
            else [
                [49, -9.6],
                [48.9, -1.1],
                [44, 4.1],
                [40.8, 7.4],
                [36, 7.4],
                [32.2, 5.1],
                [26.6, 3.3],
                [21, 2.9],
                [12, 2.1],
                [-10, -6],
                [-10, -7],
                [-10, -4],
            ]
        )

        def shell(
            title,
            center,
            lower,
            upper,
            span,
            pigment,
            trim,
            lift,
            sign=sign,
            center_z=center_z,
            centers=centers,
        ):
            rows = []
            angles = np.linspace(-1, 1, 35)
            levels = [0, 0.045, 0.12, 0.24, 0.42, 0.62, 0.81, 0.92, 0.982, 1]
            for ti in levels:
                row = []
                for u in angles:
                    angle = np.deg2rad(center + span * u)
                    if sign < 0:
                        angle = np.pi - angle
                    lo = lower(u)
                    hi = upper(u)
                    z = lo * (1 - ti) + hi * ti
                    c = np.array(
                        [np.interp(z, center_z, centers[:, axis]) for axis in range(2)]
                    )
                    p = cast(c, angle, z)
                    if p is None:
                        row.append(None)
                        continue
                    bevel = min(1, (1 - abs(u)) / 0.18, ti / 0.15, (1 - ti) / 0.12)
                    d = np.array([np.cos(angle), np.sin(angle), 0])
                    row.append(vertex(p + d * (0.12 + lift * max(0, bevel) ** 0.7)))
                rows.append(row)
            for i, (a, b) in enumerate(itertools.pairwise(rows)):
                for j in range(len(a) - 1):
                    ids = [a[j], a[j + 1], b[j + 1], b[j]]
                    if None in ids:
                        continue
                    pp = np.array([positions[k] for k in ids])
                    if (
                        np.max(np.linalg.norm(pp - np.roll(pp, 1, axis=0), axis=1))
                        > 0.008
                    ):
                        continue
                    name = (
                        trim
                        if i in {0, len(rows) - 2} or j in {0, len(a) - 2}
                        else pigment
                    )
                    face(ids if sign > 0 else ids[::-1], name)
                    if "Cuff" not in title:
                        registered_faces.append(len(polys) - 1)

        shell(
            "Shoulder pauldron",
            3,
            lambda u: 342 + 5.2 * abs(u) + 1.6 * u,
            lambda u: 365.2 - 10 * abs(u) ** 2,
            73,
            "gold",
            "gunmetal",
            1.28,
        )
        shell(
            "Outer bicep",
            0,
            lambda u: 317.2 + 4.8 * abs(u) ** 1.6,
            lambda u: 340 - 4.5 * abs(u) ** 2,
            58,
            "bronze",
            "gunmetal",
            0.68,
        )
        for k in range(3):
            shell(
                "Cuff articulation",
                -4,
                lambda u, k=k: 285.15 + k * 1.55 + abs(u) * 2.0,
                lambda u, k=k: 285.72 + k * 1.55 + abs(u) * 2.0,
                55,
                "gunmetal",
                "garnet",
                0.45,
            )
    for sign in (-1, 1):
        for plate_i, (floor, crest) in enumerate(
            [
                (300.0, 305.4),
                (307.2, 313.0),
                (315.0, 321.1),
                (323.1, 330.1),
                (331.4, 338.4),
            ]
        ):
            ribs = []
            for v in [0, 0.09, 0.22, 0.45, 0.73, 0.93, 1]:
                row = []
                for u in np.linspace(0, 1, 24):
                    angle = np.deg2rad(-60 + 87 * u)
                    direction = np.array([sign * np.cos(angle), np.sin(angle), 0])
                    scale = max(0.15, np.sin(np.pi * u) ** 0.60)
                    z = (
                        floor
                        + (crest - floor) * v * scale * 0.51
                        + 10.3 * (u - 0.25)
                        + 0.85 * np.sin(1.7 * np.pi * u)
                    )
                    c = np.array([-10.0, -4.8, z]) * 0.001
                    hit, _, _, _ = tree.ray_cast(c, direction, 0.075)
                    if hit is None:
                        row.append(None)
                        continue
                    pos = np.array(hit) * 1000
                    thickness = 0.12 + 0.53 * min(1, v / 0.24, (1 - v) / 0.12) * scale
                    row.append(vertex(pos + thickness * direction))
                ribs.append(row)
            for i, (a, b) in enumerate(itertools.pairwise(ribs)):
                for j in range(len(a) - 1):
                    ids = (a[j], a[j + 1], b[j + 1], b[j])
                    if None in ids:
                        continue
                    xyz = np.array([positions[k] for k in ids])
                    if (
                        np.max(np.linalg.norm(xyz - np.roll(xyz, 1, axis=0), axis=1))
                        > 0.004
                    ):
                        continue
                    face(ids if sign > 0 else ids[::-1], "garnet" if i == 0 else "red")
                    registered_faces.append(len(polys) - 1)
                    frontal_faces.add(len(polys) - 1)
    result = bpy.data.meshes.new(
        "Articulated knuckle guards, pauldron shells and vambraces"
    )
    result.from_pydata(positions, [], polys)
    result.update()
    for m in materials:
        result.materials.append(m)
    registered = [m for m in obj.data.materials if "registered paint" in m.name]
    for m in registered:
        result.materials.append(m)
    camera = np.array([np.load(work / f"camera-{i}.npy") for i in range(4)])
    face_by_indices = {
        tuple(f.vertices): obj.data.attributes["MK85 camera view"].data[f.index].value
        for f in obj.data.polygons
        if max(f.vertices) < len(points)
    }
    uv = result.uv_layers.new(name=obj.data.uv_layers.active.name)
    for fi in registered_faces:
        idx = polys[fi]
        center = np.asarray([positions[k] for k in idx]).mean(axis=0)
        _, _, nearest, _ = tree.find_nearest(center)
        if nearest is None:
            continue
        k = 0 if fi in frontal_faces else face_by_indices[tuple(faces[nearest])]
        coat[fi] = len(materials) + k
        for loop, vertex_id in zip(result.polygons[fi].loop_indices, idx):
            target, _, selected, _ = tree.find_nearest(positions[vertex_id])
            ids = np.array(faces[selected][:3])
            a, b, c = points[ids]
            w = np.linalg.lstsq(
                np.column_stack((a - c, b - c)), np.array(target) - c, rcond=None
            )[0]
            uv.uv[loop].vector = (
                camera[k, ids[0]] * w[0]
                + camera[k, ids[1]] * w[1]
                + camera[k, ids[2]] * (1 - w.sum())
            )
    result.polygons.foreach_set("material_index", np.array(coat, dtype="i"))
    result.polygons.foreach_set("use_smooth", np.ones(len(polys), bool))
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(result)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(result)
    bm.free()
    part = bpy.data.objects.new(result.name, result)
    bpy.context.collection.objects.link(part)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    part.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
