import math

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SECTION = 48


def sculpt_fringe(surface, levels, left, right, profile, build, pigment, navy, scale):
    locks = []

    def lock(label, stations, *, angular=False, flow=0.0, tint=1.0):
        rows = profile(stations, 1.65)
        sides = SECTION
        ring = np.arange(sides) * math.tau / sides
        lateral = (1 - np.cos(ring)) * 0.5
        arc = np.sin(ring)
        coords = []
        colors = []
        for row, start, end, depth, edge in rows:
            if angular:
                angle = start + (end - start) * lateral
            else:
                lo, hi = np.interp(row, levels, left), np.interp(row, levels, right)
                x = start + (end - start) * lateral
                angle = -np.arccos(
                    np.clip((2 * x - lo - hi) / (hi - lo), -0.9995, 0.9995)
                )
            v = np.full(sides, row)
            base = surface(angle, v)
            along = surface(angle + 0.002, v) - surface(angle - 0.002, v)
            down = surface(angle, v + 0.075) - surface(angle, v - 0.075)
            normal = np.cross(down, along)
            normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-12)
            radial = np.stack((np.cos(angle), np.sin(angle), np.zeros(sides)), axis=1)
            normal *= np.where(np.sum(normal * radial, axis=1) < 0, -1, 1)[:, None]
            t = (row - rows[0, 0]) / (rows[-1, 0] - rows[0, 0])
            curl = 0.58 * flow + 0.34 * math.sin(t * math.pi * 1.65 - 0.8)
            crest = np.maximum(0, arc) ** 1.05 * (1 + curl * (lateral - 0.5))
            divide = 0.38 + 0.14 * math.sin(3.7 * t + 0.4) - 0.22 * t
            relief_split = np.exp(-(((lateral - divide) / (0.075 + 0.04 * t)) ** 2))
            crest *= 1 - 0.24 * math.sin(t * math.pi) ** 0.72 * relief_split
            depth *= 0.58 + 0.42 * min(1, (row - rows[0, 0]) / 24)
            relief = edge + depth * crest + np.minimum(0, arc) * (edge + 0.28)
            xyz = base + scale * relief[:, None] * normal
            coords.extend(
                np.column_stack(
                    (
                        207 + xyz[:, 0] / scale,
                        xyz[:, 1] / scale,
                        600 - xyz[:, 2] / scale,
                    )
                )
            )
            gradient = np.clip((row - 131) / 145, 0, 1) ** 1.65
            dye = np.array([0.053, 0.079, 0.210]) + gradient * np.array(
                [0.053, 0.107, 0.19]
            )
            colors.extend(
                dye[None, :] * tint * (1 - 0.07 * np.maximum(0, -arc))[:, None]
            )
        faces = []
        for j in range(len(rows) - 1):
            for k in range(sides):
                a = j * sides + k
                b = j * sides + (k + 1) % sides
                faces.append((a, b, b + sides, a + sides))
        faces.extend(
            (
                tuple(reversed(range(sides))),
                tuple(range(len(coords) - sides, len(coords))),
            )
        )
        obj = build("Hair · " + label, coords, faces, navy)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
        pigment(obj, colors)
        obj["foreheadLock"] = True
        locks.append(obj)

    lock(
        "left crown sweep into cheek",
        [
            (130, 190, 195, 0.45, 0.1),
            (136, 170, 192, 2.8, 0.5),
            (150, 148, 179, 4.4, 0.65),
            (169, 133, 165, 6.4, 0.85),
            (192, 118.5, 152, 7.4, 1.2),
            (216, 114, 144, 7.6, 1.25),
            (240, 120, 143, 6.4, 1.2),
            (259, 131, 146, 5.1, 1.1),
            (273, 140, 150.9, 3.4, 1),
            (282, 146, 154.7, 2.5, 0.8),
            (287.15, 153.8, 158.7, 1.35, 0.55),
            (287.48, 158.65, 158.83, 0.13, 0.45),
        ],
        flow=0.46,
        tint=0.95,
    )
    lock(
        "right crown sweep into cheek",
        [
            (130, 219, 223, 0.4, 0.12),
            (139, 230, 250, 3, 0.65),
            (153, 245, 271, 5.2, 0.8),
            (172, 257, 285, 6.2, 1),
            (192, 266, 295, 7.1, 1.12),
            (215, 272, 299, 7.6, 1.3),
            (237, 272.5, 295, 6.1, 1.3),
            (255, 268.5, 287, 5.4, 1.25),
            (269, 261.5, 279, 4.1, 1.1),
            (275, 257.2, 272, 3.1, 1),
            (276.1, 256.1, 256.4, 0.18, 0.5),
        ],
        flow=-0.42,
        tint=0.96,
    )
    lock(
        "left swept fringe",
        [
            (129.5, 198, 201, 0.3, 0.15),
            (135, 183, 201, 2.8, 0.6),
            (147, 165, 195, 5.5, 1.1),
            (166, 150, 185.5, 6.4, 1.3),
            (187, 141.3, 178, 6.7, 1.4),
            (204, 136.2, 166.3, 7, 1.35),
            (222, 134.3, 156.4, 6.2, 1.25),
            (236, 135.6, 149.8, 4.6, 1.05),
            (246.5, 140.3, 145.8, 2.75, 0.75),
            (254.6, 144.8, 145.05, 0.18, 0.5),
        ],
        flow=0.64,
    )
    lock(
        "right swept fringe",
        [
            (129.5, 209.7, 212.8, 0.3, 0.1),
            (135.5, 212.4, 232.4, 2.9, 0.55),
            (148, 221.2, 248.3, 5.35, 1),
            (165, 228, 259.3, 6.6, 1.3),
            (184, 233, 267.3, 7.15, 1.4),
            (198, 236.4, 272, 6.9, 1.4),
            (214, 245.4, 275.8, 6.35, 1.35),
            (229, 256.4, 277, 5.4, 1.15),
            (242, 266, 275.5, 3.7, 1.0),
            (250, 270.6, 272.9, 1.6, 0.65),
            (252.7, 271.3, 271.55, 0.15, 0.45),
        ],
        flow=-0.55,
        tint=1.04,
    )
    lock(
        "forelock left feather",
        [
            (131, 199.2, 202.2, 0.3, 0.15),
            (139, 191, 204, 2.6, 0.75),
            (156, 183, 201, 4.9, 1.25),
            (178, 176.5, 198, 6, 1.4),
            (197, 176.6, 196.4, 5.7, 1.2),
            (216, 181, 196, 4.9, 1.1),
            (231, 185.7, 195.3, 3.35, 0.85),
            (238.8, 189.9, 194, 2.25, 0.65),
            (244.3, 191.4, 191.7, 0.15, 0.42),
        ],
        flow=0.42,
        tint=0.97,
    )
    lock(
        "forelock right feather",
        [
            (130.7, 206.8, 210, 0.35, 0.15),
            (140, 209.3, 221.9, 2.85, 0.75),
            (157, 216, 230, 4.1, 1.1),
            (177, 220.4, 235, 5, 1.4),
            (197, 219.5, 234.6, 5.35, 1.4),
            (213, 216.2, 231.8, 4.9, 1.1),
            (226, 212.2, 227.8, 4.65, 1),
            (235, 213, 222.6, 3.45, 0.85),
            (241, 217.3, 221.2, 2.1, 0.7),
            (245.4, 222.1, 222.4, 0.18, 0.45),
        ],
        flow=-0.48,
    )
    lock(
        "centre forelock",
        [
            (129.7, 202.8, 207.4, 0.45, 0.15),
            (134, 197.5, 215.3, 3.4, 0.75),
            (146, 190.5, 221, 5.9, 1.35),
            (164.3, 184.5, 225.1, 7.15, 1.6),
            (184, 183, 226.8, 7.65, 1.7),
            (203, 183.7, 226, 7.5, 1.65),
            (218, 187.2, 222.4, 6.7, 1.5),
            (230, 193, 216.9, 5.4, 1.4),
            (239.2, 199.3, 214.1, 3.85, 1.05),
            (244.3, 206, 214.1, 2.65, 0.85),
            (247.7, 213.8, 214.1, 0.16, 0.45),
        ],
        flow=0.58,
        tint=1.04,
    )
    for side, label in [(-1, "left"), (1, "right")]:

        def temple(row, a, b, depth, edge):
            angles = (math.pi - b, math.pi - a) if side < 0 else (a, b)
            return row, *angles, depth, edge

        lock(
            label + " temple fall from the headband",
            [
                temple(131, 0.02, 0.13, 0.38, 0.12),
                temple(147, -0.17, 0.31, 3.1, 0.7),
                temple(171, -0.29, 0.38, 5.1, 1.02),
                temple(201, -0.38, 0.46, 6.35, 1.2),
                temple(231, -0.44, 0.4, 5.9, 1.2),
                temple(252, -0.53, 0.23, 5, 1.05),
                temple(273, -0.56, -0.05, 3.9, 0.9),
                temple(287, -0.54, -0.31, 2.2, 0.75),
                temple(294, -0.48, -0.477, 0.15, 0.44),
            ],
            angular=True,
            flow=side * 0.4,
            tint=0.93,
        )
    return locks


def finish_hair(crown, locks):
    objects = [crown, *locks]
    points, faces = [], []
    for obj in objects:
        offset = len(points)
        points.extend(v.co.copy() for v in obj.data.vertices)
        faces.extend(tuple(offset + i for i in p.vertices) for p in obj.data.polygons)
    bvh = BVHTree.FromPolygons(points, faces)
    directions = []
    for i in range(24):
        a = i * 2.399963229728653
        z = math.sqrt((i + 0.5) / 24)
        r = math.sqrt(1 - z * z)
        directions.append((r * math.cos(a), r * math.sin(a), z))
    finish = crown.data.materials[0].copy()
    finish.name = "Blue pigmented hair · satin cast resin"
    bsdf = next(n for n in finish.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.38
    bsdf.inputs["Specular IOR Level"].default_value = 0.42
    for obj in objects:
        obj.data.materials[0] = finish
        if obj == crown:
            continue
        layer = obj.data.color_attributes["Filament colors"]
        colors = np.empty((len(layer.data), 4), dtype=np.float32)
        layer.data.foreach_get("color", colors.ravel())
        blocked = np.zeros(len(colors), dtype=np.float32)
        for vertex in obj.data.vertices:
            n = vertex.normal
            if n.length_squared < 0.3:
                continue
            axis = Vector((0, 0, 1)) if abs(n.z) < 0.92 else Vector((1, 0, 0))
            tangent = n.cross(axis).normalized()
            bitangent = n.cross(tangent)
            origin = vertex.co + n * 0.000028
            near = 0
            for x, y, z in directions:
                result = bvh.ray_cast(
                    origin, tangent * x + bitangent * y + n * z, 0.0025
                )
                if result[0] is not None:
                    near += (1 - result[3] / 0.0025) ** 1.4
            blocked[vertex.index] = near / len(directions)
        field = blocked.reshape(-1, SECTION)
        weights = np.array([1, 4, 6, 4, 1], dtype=float) / 16
        for _ in range(2):
            extended = np.pad(field, ((2, 2), (0, 0)), mode="edge")
            field = sum(
                weight * extended[i : i + len(field)]
                for i, weight in enumerate(weights)
            )
            field = sum(
                weight * np.roll(field, i - 2, axis=1)
                for i, weight in enumerate(weights)
            )
        colors[:, :3] *= 1 - 0.41 * field.reshape(-1, 1)
        layer.data.foreach_set("color", colors.ravel())
