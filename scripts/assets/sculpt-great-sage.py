from math import cos, pi, sin
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


CASTING = "Great Sage · round casting"
EDITION = "Profiled casting with registered front"


def ramp(value, low, high):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def band(value, a, b, c, d):
    return ramp(value, a, b) * (1 - ramp(value, c, d))


def give_volume(obj):
    mesh = obj.data
    points = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get("co", points.ravel())
    points *= 1000
    x, y, z = points.T
    y = y.copy()
    radial = abs(x + 24.5)
    head = band(z, 150, 163, 193, 208) * (1 - ramp(radial, 25, 34))
    neck = band(z, 101, 122, 147, 164) * (1 - ramp(radial, 20, 38))
    coronet = band(z, 194, 203, 219, 224) * (1 - ramp(radial, 17, 25))
    boots = band(z, 59, 65, 85, 94) * (1 - ramp(radial, 20, 34))
    cape = band(z, 75, 91, 136, 149) * ramp(x, -8, 26)
    base = band(z, 2, 11, 53, 62) * ramp(y, -3, 10)
    cranium = np.sqrt(np.clip(1 - ((x + 24.5) / 29.5) ** 2, 0, 1))
    chest = np.sqrt(np.clip(1 - ((x + 24.5) / 30) ** 2, 0, 1))
    dy = head * cranium * (15.6 * np.tanh((y - 4.4) / 3.6) - 1.3)
    dy += neck * chest * (8.3 * np.tanh((y - 4.8) / 5.0) - 1.1)
    dy += coronet * (6.5 * np.tanh((y - 4.5) / 3.3) - 0.6)
    dy += boots * (3.2 * np.tanh((y + 1.5) / 3.4) - 0.4)
    dy += cape * (4.3 * np.sin((x + 0.49 * z) / 13) + 2.0 * np.sin(z / 9))
    dy += base * (3.2 + 2.3 * np.sin(x / 21 + z / 14))
    deformed = y + dy
    changed = abs(dy) > 0.0001
    for sign in [-1, 1]:
        near_bound = changed & (sign * deformed > 24)
        deformed[near_bound] = sign * (
            24 + 4.5 * np.tanh((sign * deformed[near_bound] - 24) / 4.5)
        )
    points[:, 1] = deformed
    mesh.vertices.foreach_set("co", (points * 0.001).ravel())
    for name, weights in [
        ("Skull and jaw", head),
        ("Chest and mantle", neck),
        ("Coronet", coronet),
        ("Flying cloak", cape),
        ("Rear rock strata", base),
    ]:
        group = obj.vertex_groups.new(name=name)
        ids = np.flatnonzero(weights > 0.35).tolist()
        if ids:
            group.add(ids, 1.0, "REPLACE")
    mesh.update()


def axis_at(height):
    t = height - 59.0
    return Vector((-57.8 - 0.1216 * t, -9.75 + 0.021 * t, height)) * 0.001


def metal(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return mat


def swept_part(figure, label, centers, radii, material, sides, flatten=1.0):
    verts, faces = [], []
    for i, (center, radius) in enumerate(zip(centers, radii)):
        axis = (
            centers[min(i + 1, len(centers) - 1)] - centers[max(i - 1, 0)]
        ).normalized()
        lateral = axis.cross(Vector((0, 1, 0))).normalized()
        depth = axis.cross(lateral).normalized()
        for j in range(sides):
            angle = 2 * pi * j / sides
            verts.append(
                center + (lateral * cos(angle) + flatten * depth * sin(angle)) * radius
            )
            if i:
                a, b = (i - 1) * sides + j, (i - 1) * sides + (j + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    faces += [
        tuple(reversed(range(sides))),
        tuple(range(len(verts) - sides, len(verts))),
    ]
    mesh = bpy.data.meshes.new(label)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    for p in mesh.polygons:
        p.use_smooth = len(p.vertices) == 4
    obj = bpy.data.objects.new(label, mesh)
    figure.users_collection[0].objects.link(obj)
    obj.vertex_groups.new(name=label).add(list(range(len(verts))), 1, "REPLACE")
    return obj


def turn_staff(figure):
    bm = bmesh.new()
    bm.from_mesh(figure.data)

    def is_shaft(v):
        x, y, z = v.co * 1000
        cx = axis_at(z).x * 1000
        return abs(x - cx) < 5.5 and z > 61.4 and (z < 117 or z > 138)

    old = [v for v in bm.verts if is_shaft(v)]
    bmesh.ops.delete(bm, geom=old, context="VERTS")
    bm.to_mesh(figure.data)
    bm.free()
    gold = metal("Great Sage · burnished brass staff", (0.68, 0.445, 0.135), 0.66, 0.31)
    band_gold = metal("Great Sage · gilt staff collars", (0.83, 0.61, 0.25), 0.72, 0.25)
    rings = [
        (58.7, 1.9),
        (58.88, 2.12),
        (59.15, 2.23),
        (75.3, 2.23),
        (75.65, 2.08),
        (229.4, 2.08),
        (229.75, 2.23),
        (249.35, 2.23),
        (249.7, 2.12),
        (249.83, 1.9),
    ]
    parts = [
        swept_part(
            figure,
            "Round brass shaft",
            [axis_at(z) for z, r in rings],
            [r / 1000 for z, r in rings],
            gold,
            40,
        )
    ]
    for start in (59.6, 61.0, 74.6, 230.3, 247.5, 248.85):
        profile = [
            (start - 0.21, 2.18),
            (start - 0.09, 2.31),
            (start + 0.09, 2.31),
            (start + 0.21, 2.18),
        ]
        parts.append(
            swept_part(
                figure,
                "Turned staff collar",
                [axis_at(z) for z, r in profile],
                [r / 1000 for z, r in profile],
                band_gold,
                40,
            )
        )
    return parts


def comb_nape(figure):
    mesh = figure.data
    tree = BVHTree.FromPolygons(
        [v.co for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons]
    )
    mat = metal("Great Sage · patinated hair ridges", (0.42, 0.255, 0.102), 0.36, 0.47)
    parts = []
    for strand in range(-10, 11):
        k = strand / 10
        centers, radii = [], []
        for step in range(21):
            t = step / 20
            x = (
                -24.5
                + 20.0 * k * (0.31 + 0.69 * sin(t * 1.62))
                + 1.6 * sin(3.7 * t + 0.4 * k)
            )
            z = 198.1 - 0.8 * abs(k) - (35.2 - 9 * abs(k)) * t
            point, normal, _, _ = tree.ray_cast(
                Vector((x / 1000, 0.07, z / 1000)), Vector((0, -1, 0))
            )
            if point is None or normal.y < 0.10:
                continue
            r = (0.08 + (0.62 - 0.13 * abs(k)) * sin(pi * t) ** 0.67) / 1000
            centers.append(point + normal * r * 0.08)
            radii.append(r)
        if len(centers) >= 8:
            parts.append(
                swept_part(figure, "Cast nape lock", centers, radii, mat, 7, 0.53)
            )
    return parts


def sculpt(figure):
    if figure.get("castingEdition") in {EDITION, "Tongshifu · Invincible Wukong"}:
        match_cape_clearance(figure)
        return figure
    give_volume(figure)
    parts = turn_staff(figure) + comb_nape(figure)
    bpy.ops.object.select_all(action="DESELECT")
    figure.select_set(True)
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = figure
    bpy.ops.object.join()
    figure.data.name = CASTING
    figure["castingEdition"] = EDITION
    match_cape_clearance(figure)
    return figure


def match_cape_clearance(figure):
    mesh = figure.data
    points = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get("co", points.ravel())
    depth = points[:, 1]
    rear = depth.max()
    gap = 0.0285 - rear
    if abs(gap) > 0.00001:
        depth += gap * ramp(depth, 0.022, rear)
        mesh.vertices.foreach_set("co", points.ravel())
        mesh.update()


if __name__ == "__main__":
    figure = next(
        o for o in bpy.context.scene.objects if o.name.startswith("Sun Wukong")
    )
    sculpt(figure)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(bpy.data.filepath)), compress=True)
