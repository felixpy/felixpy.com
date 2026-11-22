import math
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import bpy


def wood_sample(coords, seed, normal_axis):
    length, width, depth = coords
    rng = np.random.default_rng(8701 + seed)
    phase = rng.uniform(0, math.tau, 8)
    pith_u = rng.choice((-1, 1)) * rng.uniform(22, 85)
    pith_v = rng.uniform(10, 75)
    sweep = 4.4 * np.sin(length / 248 + phase[0]) + 1.45 * np.sin(
        length / 84 + phase[1]
    )
    u = width + pith_u + sweep + 0.000048 * length**2 * np.cos(phase[0])
    v = (
        depth
        + pith_v
        + 7 * np.sin(length / 312 + phase[2])
        + 0.9 * np.sin(length / 103 + phase[4])
    )
    radius = np.sqrt(u * u + v * v)
    ring = (
        radius * 0.259
        + 0.20 * np.sin(radius / 13 + phase[3])
        + 0.13 * np.sin(u / 6 + v / 29)
    )
    earlywood = np.sin(math.tau * ring)
    latewood = np.exp(-(((earlywood - 0.68) / 0.37) ** 2)) * (
        0.58 + 0.42 * np.cos(math.tau * ring)
    )
    mineral = np.sin(radius / 3.3 + 0.72 * np.sin(radius / 9.7) + phase[5])
    band = 0.092 * np.sin(radius / 10 + phase[4]) - 0.235 * np.maximum(0, mineral) ** 3
    grain = 0.042 * earlywood - 0.089 * latewood
    vessel_phase = (
        3.13 * u
        + 2.75 * v
        + 0.31 * np.sin(length / 43 + phase[5])
        + 0.59 * np.sin(u * 0.83)
    )
    vessel = np.maximum(0, np.sin(vessel_phase)) ** 12
    interrupted = 0.28 + 0.72 * np.maximum(
        0, np.sin(length * 0.106 + 0.8 * np.sin(u * 0.5) + phase[7])
    )
    pore = vessel * interrupted
    if normal_axis == 0:
        pore = (
            np.maximum(
                0, np.sin(u * 3.45 + np.sin(v * 0.87)) * np.cos(v * 2.67 + u * 0.32)
            )
            ** 5
        )
        grain *= 1.43
    streak = np.sin(
        0.76 * u
        + 0.31 * v
        + 1.68 * np.sin(radius * 0.19)
        + np.sin(length / 166 + phase[7])
    )
    broken = 0.28 + 0.72 * np.maximum(
        0, np.sin(length / 117 + phase[6] + radius * 0.14)
    )
    tone = (
        rng.uniform(0.92, 1.17)
        + grain
        + band
        - 0.15 * pore
        - 0.154 * np.maximum(0, streak) ** 5 * broken
    )
    base = np.array([175, 112, 58]) + rng.uniform(-1, 1) * np.array([7, 10, 8])
    if normal_axis == 0:
        base *= [0.86, 0.82, 0.80]
    pixels = np.uint8(np.clip(tone[..., None] * base, 0, 255))
    relief = 0.055 * earlywood - 0.12 * latewood - 0.20 * pore
    return pixels, relief


def packed_image(folder, filename, data, quality, color_space):
    path = str(Path(folder) / filename)
    spec = oiio.ImageSpec(data.shape[1], data.shape[0], 3, oiio.UINT8)
    spec.attribute("CompressionQuality", quality)
    spec.attribute("jpeg:subsampling", "4:4:4")
    writer = oiio.ImageOutput.create(path)
    if not writer.open(path, spec) or not writer.write_image(data[::-1].copy()):
        raise RuntimeError(writer.geterror())
    writer.close()
    image = bpy.data.images.load(path)
    image.colorspace_settings.name = color_space
    image.pack()
    image.filepath = f"//{filename}"
    for item in image.packed_files:
        item.filepath = image.filepath
    return image


def bake(boards, material, folder):
    scale, padding, atlas_width = 0.77, 3, 2048
    patches = []
    for seed, (board, dims) in enumerate(boards):
        dims = np.array(dims)
        for axis in range(3):
            axes = [i for i in range(3) if i != axis]
            for sign in (-1, 1):
                w, h = np.maximum(3, np.ceil(dims[axes] * scale)).astype(int)
                patches.append((int(w), int(h), seed, axis, sign, axes, dims))

    shelves, slots = [], {}
    for w, h, seed, axis, sign, axes, dims in sorted(
        patches, key=lambda p: (-p[1], -p[0])
    ):
        width, height = w + 2 * padding, h + 2 * padding
        row = next(
            (r for r in shelves if r[1] >= height and r[2] + width <= atlas_width), None
        )
        if row is None:
            row = [sum(r[1] for r in shelves), height, 0]
            shelves.append(row)
        slots[seed, axis, sign] = row[2] + padding, row[0] + padding, w, h, axes
        row[2] += width

    atlas_height = math.ceil(sum(r[1] for r in shelves) / 16) * 16
    color = np.full((atlas_height, atlas_width, 3), (167, 113, 64), dtype=np.uint8)
    normal = np.full_like(color, (128, 128, 255))
    for w, h, seed, axis, sign, axes, dims in patches:
        left, bottom, _, _, _ = slots[seed, axis, sign]
        j, i = np.mgrid[-padding : h + padding, -padding : w + padding]
        coords = [np.full_like(i, 0.5 * dims[axis] * sign, dtype=float)] * 3
        coords[axes[0]] = (i.clip(0, w - 1) / (w - 1) - 0.5) * dims[axes[0]]
        coords[axes[1]] = (j.clip(0, h - 1) / (h - 1) - 0.5) * dims[axes[1]]
        rgb, relief = wood_sample(coords, seed, axis)
        dy, dx = np.gradient(relief)
        dz = np.sqrt(1 + dx**2 + dy**2)
        normals = np.stack((-dx / dz, -dy / dz, 1 / dz), axis=-1)
        span = (
            slice(bottom - padding, bottom + h + padding),
            slice(left - padding, left + w + padding),
        )
        color[span] = rgb
        normal[span] = np.uint8((normals * 0.5 + 0.5) * 255 + 0.5)

    for seed, (board, dims) in enumerate(boards):
        mesh = board.data
        uv = (mesh.uv_layers.active or mesh.uv_layers.new()).data
        for poly in mesh.polygons:
            axis = max(range(3), key=lambda i: abs(poly.normal[i]))
            sign = 1 if poly.normal[axis] >= 0 else -1
            left, bottom, w, h, axes = slots[seed, axis, sign]
            for li in poly.loop_indices:
                point = mesh.vertices[mesh.loops[li].vertex_index].co
                s, t = (point[i] * 1000 / dims[i] + 0.5 for i in axes)
                uv[li].uv = (
                    (left + 0.5 + s * (w - 1)) / atlas_width,
                    (bottom + 0.5 + t * (h - 1)) / atlas_height,
                )

    graph = material.node_tree
    shader = graph.nodes.get("Principled BSDF")
    image = graph.nodes.new("ShaderNodeTexImage")
    image.image = packed_image(folder, "Sawn teak - colour.webp", color, 84, "sRGB")
    graph.links.new(image.outputs["Color"], shader.inputs["Base Color"])
    grain = graph.nodes.new("ShaderNodeTexImage")
    grain.image = packed_image(
        folder, "Sawn teak - vessel relief.jpg", normal, 75, "Non-Color"
    )
    bump = graph.nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = 0.72
    graph.links.new(grain.outputs["Color"], bump.inputs["Color"])
    graph.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    print(f"Cut timber atlas {atlas_width} x {atlas_height} for {len(boards)} boards")
