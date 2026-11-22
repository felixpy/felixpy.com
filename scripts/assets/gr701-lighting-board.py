import math
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ITEM = ROOT / ".references/03-电脑硬件/机箱与整机/ROG Hyperion GR701"
GLYPHS = {
    "R": ["0,26 0,0 29,0 29,13 20,15 31,26 21,26 11,14 11,10 22,10 22,5 7,5 7,26"],
    "E": ["0,0 29,0 29,5 7,5 7,10 26,10 26,15 7,15 7,21 29,21 29,26 0,26"],
    "P": ["0,26 0,0 29,0 29,16 12,16 12,11 22,11 22,5 7,5 7,26"],
    "U": ["0,0 7,0 7,21 22,21 22,0 29,0 29,26 0,26"],
    "B": ["0,26 0,0 26,0 29,4 29,11 26,13 29,16 29,26 12,26 12,21 22,21 22,16 12,16 12,11 22,11 22,5 7,5 7,26"],
    "L": ["0,0 7,0 7,21 29,21 29,26 0,26"],
    "I": ["10,0 18,0 18,26 10,26"],
    "C": ["29,0 29,5 7,5 7,21 29,21 29,26 0,26 0,0"],
    "O": ["29,0 29,26 22,26 22,5 7,5 7,17 13,22 18,22 18,26 10,26 0,19 0,0"],
    "F": ["0,26 0,0 29,0 29,5 7,5 7,10 25,10 25,15 7,15 7,26"],
    "G": ["29,0 29,5 7,5 7,21 22,21 22,15 28,12 28,26 0,26 0,0"],
    "A": ["0,26 0,0 29,0 29,26 22,26 22,6 7,6 7,12 18,12 18,17 7,17 7,26"],
    "M": ["0,26 0,0 14,8 29,0 29,26 22,26 22,10 14,15 7,10 7,26"],
    "S": ["29,0 29,5 8,5 8,10 29,10 29,22 25,26 0,26 0,21 21,21 22,16 0,16 0,4 4,0"],
}


def polygon_mask(x, y, points):
    mask = np.zeros(np.broadcast_shapes(x.shape, y.shape), dtype=bool)
    for (a, b), (c, d) in zip(points, points[1:] + points[:1]):
        if b != d:
            mask ^= ((y > b) != (y > d)) & (x < (c - a) * (y - b) / (d - b) + a)
    return mask


def coords(path):
    return [tuple(map(float, p.split(","))) for p in path.split()]


def aperture_face():
    w, h = 448, 1472
    x = np.linspace(-11, 351, w * 2, dtype=np.float32)[None, :]
    y = np.linspace(-150, 930, h * 2, dtype=np.float32)[:, None]
    silhouettes = [
        "12,81 66,199 106,251 151,296 151,418 97,378 56,332 25,269 9,197",
        "55,4 99,74 148,139 150,270 124,232 89,155 58,76",
        "112,25 150,48 150,133 132,105",
        "198,72 252,94 296,135 337,177 342,269 324,331 300,403 279,462 248,419 219,355 199,277 200,198 227,256 256,337 272,356 289,306 298,249 298,211 275,176 239,148 198,135",
        "196,396 231,440 260,465 280,472 339,426 328,459 300,492 265,518 219,548 197,552",
        "249,533 270,528 257,581 223,631 198,652 198,617 222,581",
    ]
    cx = 15 + np.rint((x - 15) / 11.8) * 11.8
    stagger = (cx - 15) * 0.020
    cy = 15 + stagger + np.rint((y - 15 - stagger) / 12.6) * 12.6
    in_eye = np.zeros((h * 2, w * 2), dtype=bool)
    for shape in silhouettes:
        in_eye |= polygon_mask(cx, cy, coords(shape))
    radius = np.clip(1.35 + (cy + 10) * .0061, 1.3, 4.05)
    cut = in_eye & ((x - cx) ** 2 + (y - cy) ** 2 < radius ** 2)
    for letter, top in zip("REPUBLICOFGAMERS", (21,59,97,135,173,211,249,285,335,374,422,461,499,536,574,611)):
        gx, gy = x - 159, y - top
        for shape in GLYPHS[letter]:
            cut |= polygon_mask(gx, gy, coords(shape))
    for shape in (
        "140,679 153,679 192,740 184,749",
        "157,679 176,679 189,699 184,707 172,686 167,686 183,715 179,721",
        "181,679 213,679 199,704 190,692 195,692 199,696 205,685 185,685",
        "194,711 203,697 210,688 198,717 191,725 160,678 170,681",
    ):
        cut |= polygon_mask(x, y, coords(shape))
    coverage = cut.reshape(h, 2, w, 2).mean(axis=(1, 3)).astype(np.float32)
    u = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    palette = np.array([[.97,.10,.73],[.86,.13,.99],[.29,.27,1],[.03,.85,.98]], dtype=np.float32)
    t = np.minimum(u * 3, 2.9999)
    idx = t.astype(int)[...,0]
    hue = palette[idx] * (1 - (t % 1)) + palette[idx + 1] * (t % 1)
    def packed(name, rgb):
        pixels = np.ones((h, w, 4), dtype=np.float32)
        pixels[:, :, :3] = rgb[::-1]
        image = bpy.data.images.new(name, width=w, height=h, alpha=False)
        image.colorspace_settings.name = "sRGB"
        image.pixels.foreach_set(pixels.ravel())
        image.pack()
        return image
    return packed("Photomask and unlit light guide", .105 + .20 * coverage[...,None]), packed("Graded multizone light guide", hue * coverage[...,None])


def finish(name, color, metallic, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color,1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = rough
    return mat, shader


def housing(name, location, dimensions, radius, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new("Formed edge", "BEVEL")
    mod.width, mod.segments = radius, 3
    obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    obj.data.materials.append(material)


def legend(text, x, z, size, ink, turn=0):
    bpy.ops.object.text_add(location=(x,-.00767,z), rotation=(math.pi/2,0,0))
    obj = bpy.context.object
    obj.name = "Screen print " + text
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.size = size
    obj.rotation_euler.rotate_axis("Z", turn)
    obj.data.materials.append(ink)
    bpy.ops.object.convert(target="MESH")


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body,_ = finish("GR701 satin graphite carrier", (.027,.029,.034),.52,.46)
    ink,_ = finish("GR701 cool grey silkscreen", (.25,.27,.29),.17,.56)
    mask, shader = finish("GR701 illuminated photomask", (.03,.03,.035),.32,.54)
    for image, channel in zip(aperture_face(), ("Base Color","Emission Color")):
        node = mask.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        mask.node_tree.links.new(node.outputs["Color"],shader.inputs[channel])
    shader.inputs["Emission Strength"].default_value = 1.45
    housing("Folded steel carrier", (0,0,0),(.126,.015,.413),.0015,body)
    for side in (-1,1):
        housing("Rolled edge keeper", (side*.0620,-.0023,0),(.0024,.011,.408),.0007,body)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0,-.00761,0),rotation=(math.pi/2,0,0))
    face = bpy.context.object
    face.name = "Aperture mask and graduated diffuser"
    face.scale=(.121,.405,1)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    face.data.materials.append(mask)
    legend("ROG HYPERION GR701",-.039,-.087,.0027,ink,-math.pi/2)
    legend("› START",0,-.145,.0057,ink)
    legend("FOR THOSE WHO DARE",0,-.155,.0048,ink)
    legend("GAME ON",0,-.164,.0048,ink)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ITEM / "Blender/gr701-lighting-board.blend"),compress=True)
    bpy.ops.export_scene.gltf(filepath=str(ROOT / "public/media/models/gr701-lighting-board.glb"),export_apply=True)


build()
