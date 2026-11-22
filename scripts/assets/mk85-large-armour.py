import itertools
import math
import runpy
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree


def front_inserts(obj, work, points):
    panel = runpy.run_path(str(Path(__file__).with_name("mk85-large-panels.py")))
    mesh = obj.data
    camera = np.load(work / "camera-0.npy")
    faces = [list(p.vertices) for p in mesh.polygons]
    tree = BVHTree.FromPolygons(
        np.column_stack((camera, -points[:, 1])).tolist(), faces
    )
    names = list(panel["COAT"])
    paints = []
    for name, (hex_colour, metal, roughness) in panel["COAT"].items():
        c = np.frombuffer(bytes.fromhex(hex_colour), dtype=np.uint8).astype(float) / 255
        linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        mat = bpy.data.materials.new("Tongshifu MK85 · " + name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes["Principled BSDF"]
        shader.inputs["Base Color"].default_value = (*linear, 1)
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Coat Weight"].default_value = (
            0.16 if name in {"red", "garnet"} else 0.05
        )
        shader.inputs["Coat Roughness"].default_value = 0.33
        if name == "lens":
            shader.inputs["Emission Color"].default_value = (*linear, 1)
            shader.inputs["Emission Strength"].default_value = 0.18
        mat.diffuse_color = (*linear, 1)
        paints.append(mat)
    photo = bpy.data.images.load(str(work / "camera-0.jpg"), check_existing=True)
    photo.pack()
    photo.filepath = "//mk85-frontal-pigment.jpg"
    shader_names = {"red", "garnet", "gold", "bronze"}
    for name, paint in zip(names, paints):
        if name not in shader_names:
            continue
        nodes = paint.node_tree.nodes
        sample = nodes.new("ShaderNodeTexImage")
        sample.image = photo
        paint.node_tree.links.new(
            sample.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"]
        )
    positions = []
    polygons = []
    material_ids = []
    uv_coords = []

    def surface(x, y):
        uv = np.array(
            [
                (450 + (x - 220) * 3 / (437 / 250)) / 900,
                1 - (1310 + (y - 791) * 3 / (731 / 420)) / 1360,
            ]
        )
        hit, _, face, _ = tree.ray_cast((*uv, 0.4), (0, 0, -1), 0.8)
        if hit is None:
            return None
        ids = faces[face][:3]
        a, b, c = camera[ids]
        w = np.linalg.lstsq(np.column_stack((a - c, b - c)), uv - c, rcond=None)[0]
        return (
            points[ids[0]] * w[0]
            + points[ids[1]] * w[1]
            + points[ids[2]] * (1 - w.sum())
        )

    def vertex(x, y, lift):
        p = surface(x, y)
        if p is None:
            return None
        p[1] -= lift / 1000
        positions.append(tuple(p))
        uv_coords.append(
            (
                (450 + (x - 220) * 3 / (437 / 250)) / 900,
                1 - (1310 + (y - 791) * 3 / (731 / 420)) / 1360,
            )
        )
        return len(positions) - 1

    def tri(ia, ib, ic, material):
        if ia is None or ib is None or ic is None:
            return
        p, q, r = np.array([positions[k] for k in (ia, ib, ic)])
        if (
            max(np.linalg.norm(p - q), np.linalg.norm(r - q), np.linalg.norm(r - p))
            > 0.008
        ):
            return
        polygons.append((ia, ib, ic) if np.cross(q - p, r - p)[1] < 0 else (ic, ib, ia))
        material_ids.append(names.index(material))

    def make(name, pigment, center, edges, height, band, inset):
        ring = np.array(edges + edges[:1], dtype=float)
        lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
        spacing = (
            1.35
            if height > 1.6 or name.startswith(("Left visor", "Right visor"))
            else 2.6
        )
        steps = np.unique(np.r_[lengths[:-1], np.arange(0, lengths[-1], spacing)])
        edge = np.column_stack(
            [np.interp(steps, lengths, ring[:, i]) for i in range(2)]
        )
        center = np.array(center, float)
        radius = np.max(np.linalg.norm(edge - center, axis=1))
        border = min(0.22, band / max(radius, 0.2))
        core = np.linspace(0.001, 1 - border, max(3, math.ceil(radius / 2.3)))
        levels = [*core, 1 - border * 0.55, 1 - border * 0.13, 1.0]
        rows = []
        for k, fraction in enumerate(levels):
            loc = center + (edge - center) * fraction
            lift = height * (1 - 0.14 * fraction * fraction)
            if (
                name.startswith("Arc reactor")
                or "visor rail" in name
                or "visor lens" in name
            ):
                lift += 0.50
            if k == len(levels) - 2:
                lift -= min(0.26, height * 0.24)
            if k == len(levels) - 1:
                lift -= min(0.48, height * 0.45)
            row = []
            for x, y in loc:
                sculpt = 0
                if name == "Hammered crown visor":
                    sculpt = (
                        0.65
                        * max(0, 1 - abs(x - 196.6) / 7.5)
                        * max(0, 1 - abs(y - 100) / 17)
                    )
                if name == "Continuous breastplate":
                    sculpt = (
                        0.64
                        * math.cos((x - 206) * math.pi / 56) ** 2
                        * max(0, 1 - abs(y - 178) / 35)
                    )
                row.append(vertex(x, y, lift + sculpt))
            rows.append(row)
        for i, (a, b) in enumerate(itertools.pairwise(rows)):
            material = (
                pigment
                if i < len(rows) - 2
                else (
                    "gunmetal"
                    if pigment not in {"lens", "seal", "reflector"}
                    else pigment
                )
            )
            for j in range(len(edge)):
                k = (j + 1) % len(edge)
                tri(a[j], b[j], a[k], material)
                tri(a[k], b[j], b[k], material)

    for p in panel["armour"]():
        if not p[0].endswith("bracer"):
            make(*p)
    for row in range(5):
        yy = 178.4 + row * 2.45
        for col in range(8):
            xx = 197.7 + col * 2.45 + (row % 2) * 1.12
            if xx < 198.6 + (yy - 178.4) * 0.4 or xx > 215.8 - (yy - 178.4) * 0.43:
                continue
            make(
                "Reactor lattice facets",
                "lens" if (row + col) % 3 else "titanium",
                (xx, yy),
                [
                    (xx - 0.56, yy - 0.71),
                    (xx + 0.57, yy - 0.71),
                    (xx + 0.79, yy),
                    (xx + 0.37, yy + 0.59),
                    (xx - 0.52, yy + 0.52),
                ],
                2.81,
                0.08,
                0.1,
            )
    plates = bpy.data.meshes.new(
        "Fitted large casting armour and recessed enamel joints"
    )
    plates.from_pydata(positions, [], polygons)
    plates.update()
    for paint in paints:
        plates.materials.append(paint)
    plates.polygons.foreach_set("use_smooth", np.ones(len(polygons), bool))
    plates.polygons.foreach_set("material_index", np.asarray(material_ids, dtype="i"))
    uv = plates.uv_layers.new(name=mesh.uv_layers.active.name)
    uv.uv.foreach_set(
        "vector",
        np.asarray(
            [uv_coords[l.vertex_index] for l in plates.loops], dtype="f"
        ).ravel(),
    )
    parts = bpy.data.objects.new(plates.name, plates)
    bpy.context.collection.objects.link(parts)
    bpy.ops.object.select_all(action="DESELECT")
    parts.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
