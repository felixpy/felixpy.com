import math
from functools import lru_cache
from mathutils import Vector
import bpy


@lru_cache(maxsize=2)
def woven_normal(open_weave):
    size = 256
    count = 24 if open_weave else 33
    heights = []
    for y in range(size):
        for x in range(size):
            u = x / size * math.tau
            v = y / size * math.tau
            first = math.sin(count * u + 0.42 * math.sin(count * v))
            second = math.sin(count * v + 0.21 * math.sin(count * u))
            height = 0.62 * first + 0.38 * second
            if open_weave:
                height -= max(0, first) * max(0, second)
            heights.append(height)
    pixels = []
    for y in range(size):
        for x in range(size):
            dx = heights[y * size + (x + 1) % size] - heights[y * size + (x - 1) % size]
            dy = heights[(y + 1) % size * size + x] - heights[(y - 1) % size * size + x]
            n = Vector((-dx * 0.27, -dy * 0.27, 1)).normalized()
            pixels.extend((n.x * 0.5 + 0.5, n.y * 0.5 + 0.5, n.z * 0.5 + 0.5, 1))
    name = (
        "Fine technical stretch-knit normal"
        if open_weave
        else "Technical textile warp normal"
    )
    image = bpy.data.images.new(name, width=size, height=size, is_data=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def textile(material, name, open_mesh=False, normal_strength=0, yarn_contrast=0.16):
    shader = material.node_tree.nodes.get("Principled BSDF")
    tint = shader.inputs["Base Color"].default_value[:3]
    encoded = [
        12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in tint
    ]
    name = f"{name} · {material.name}"
    image = bpy.data.images.get(name)
    if not image:
        size = 128
        image = bpy.data.images.new(name, width=size, height=size)
        pixels = []
        count = 21 if open_mesh else 24
        for y in range(size):
            for x in range(size):
                u = x / size
                v = y / size
                twist = math.sin(
                    (u * count + 0.13 * math.sin(v * count * math.tau)) * math.tau
                )
                weft = math.cos(
                    (v * count + 0.10 * math.cos(u * count * math.tau)) * math.tau
                )
                holes = max(0, twist) * max(0, weft)
                seam = (
                    0
                    if open_mesh
                    else 0.065
                    * (
                        max(0, math.cos(u * math.tau * 2)) ** 26
                        + max(0, math.cos(v * math.tau * 2)) ** 26
                    )
                )
                val = (
                    (0.95 - yarn_contrast * holes + 0.025 * (twist + weft))
                    if open_mesh
                    else (0.95 + 0.035 * twist + 0.021 * weft - seam * 0.7)
                )
                pixels.extend([min(1, v * val) for v in encoded] + [1])
        image.pixels.foreach_set(pixels)
        image.pack()
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    if normal_strength:
        source = nodes.new("ShaderNodeTexImage")
        source.image = woven_normal(open_mesh)
        normal = nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value = normal_strength
        material.node_tree.links.new(source.outputs["Color"], normal.inputs["Color"])
        material.node_tree.links.new(
            normal.outputs["Normal"], nodes.get("Principled BSDF").inputs["Normal"]
        )
    return material
