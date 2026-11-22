import bpy
import numpy as np


def image(name, rgb):
    height, width = rgb.shape[:2]
    bitmap = bpy.data.images.new(name, width, height, alpha=False)
    bitmap.colorspace_settings.name = "Non-Color"
    pixels = np.empty((height, width, 4), dtype=np.float32)
    pixels[:, :, :3] = rgb
    pixels[:, :, 3] = 1
    bitmap.pixels.foreach_set(pixels.ravel())
    bitmap.update()
    bitmap.pack()
    return bitmap


def coat_grain(name, materials, brushed=False):
    random = np.random.default_rng(45 if brushed else 618)
    noise = random.normal(0, 0.18, (128, 128))
    height = noise
    if brushed:
        for shift in range(1, 12):
            height = height + np.roll(noise, shift, axis=1)
        height /= 3.8
    else:
        height = height + 0.35 * (np.roll(noise, 1, axis=1) + np.roll(noise, 1, axis=0))
    x = np.roll(height, 1, axis=1) - np.roll(height, -1, axis=1)
    y = np.roll(height, 1, axis=0) - np.roll(height, -1, axis=0)
    xyz = np.stack((x, y, np.ones_like(x)), axis=2)
    xyz = xyz / np.linalg.norm(xyz, axis=2, keepdims=True)
    sample = image(name, xyz * 0.5 + 0.5)
    for mat, strength in materials:
        graph = mat.node_tree
        tex = graph.nodes.new("ShaderNodeTexImage")
        tex.image = sample
        normal = graph.nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value = strength
        graph.links.new(tex.outputs["Color"], normal.inputs["Color"])
        graph.links.new(
            normal.outputs["Normal"], graph.nodes["Principled BSDF"].inputs["Normal"]
        )


def cherry(material):
    n = 256
    u, v = np.meshgrid(np.arange(n) / n, np.arange(n) / n)
    phase = (
        u * 19
        + 0.35 * np.sin(2 * np.pi * (v + u))
        + 0.14 * np.cos(2 * np.pi * (2 * v - u))
    )
    growth = 0.5 + 0.5 * np.cos(2 * np.pi * phase)
    pores = (
        abs(
            np.sin(
                2
                * np.pi
                * (u * 59 + 0.82 * np.sin(2 * np.pi * v) + 0.24 * np.sin(4 * np.pi * v))
            )
        )
        ** 21
    )
    noise = np.random.default_rng(416).normal(0, 0.012, (n, n))
    tone = 0.90 + 0.14 * growth - 0.105 * pores + noise
    color = np.array([0.66, 0.455, 0.267])[None, None, :] * tone[:, :, None]
    tile = image("Oiled cherry · long grain", color)
    tile.colorspace_settings.name = "sRGB"
    graph = material.node_tree
    tex = graph.nodes.new("ShaderNodeTexImage")
    tex.image = tile
    graph.links.new(
        tex.outputs["Color"], graph.nodes["Principled BSDF"].inputs["Base Color"]
    )
