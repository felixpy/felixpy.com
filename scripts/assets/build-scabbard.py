import argparse
import math
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio
from io_scene_gltf2.io.exp import meshopt


WIDTH, DEPTH, RADIUS = 900, 400, 16


def outline(inset):
    points = []
    for quarter, (sx, sy) in enumerate(((1, -1), (1, 1), (-1, 1), (-1, -1))):
        for step in range(17):
            a = (quarter - 1 + step / 16) * math.pi / 2
            points.append(
                (
                    sx * (WIDTH / 2 - RADIUS) + (RADIUS - inset) * math.cos(a),
                    sy * (DEPTH / 2 - RADIUS) + (RADIUS - inset) * math.sin(a),
                )
            )
    return points


def layer(name, profile, material, tex_size, cap_top=True, cap_bottom=True):
    rings = [outline(inset) for inset, _ in profile]
    n = len(rings[0])
    vertices = [(x, y, z) for ring, (_, z) in zip(rings, profile) for x, y in ring]
    faces, maps, smoothing = [], [], []
    s = np.array(
        [
            0,
            *np.cumsum(
                [math.dist(rings[0][i], rings[0][(i + 1) % n]) for i in range(n)]
            ),
        ]
    )
    s *= round(s[-1] / tex_size) / s[-1]
    arc = np.array(
        [0, *np.cumsum([math.dist(a, b) for a, b in zip(profile, profile[1:])])]
    )
    arc /= arc[-1]
    for row in range(len(profile) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append(
                (row * n + i, row * n + j, (row + 1) * n + j, (row + 1) * n + i)
            )
            maps.append(
                (
                    (s[i], arc[row]),
                    (s[i + 1], arc[row]),
                    (s[i + 1], arc[row + 1]),
                    (s[i], arc[row + 1]),
                )
            )
            smoothing.append(True)
    for cap, ring in ((cap_bottom, 0), (cap_top, len(profile) - 1)):
        if not cap:
            continue
        boundary = tuple(range(ring * n, (ring + 1) * n))
        face = boundary if ring else tuple(reversed(boundary))
        faces.append(face)
        maps.append(
            [(vertices[k][0] / tex_size, vertices[k][1] / tex_size) for k in face]
        )
        smoothing.append(False)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(c * 0.001 for c in v) for v in vertices], [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Surface")
    for face, coords, smooth in zip(mesh.polygons, maps, smoothing):
        face.use_smooth = smooth
        for loop, coord in zip(face.loop_indices, coords):
            uv.data[loop].uv = coord
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    return obj


def write_bitmap(directory, name, pixels, color_space):
    path = directory / (name + (".webp" if color_space == "sRGB" else ".png"))
    spec = oiio.ImageSpec(pixels.shape[1], pixels.shape[0], 3, oiio.UINT8)
    if path.suffix == ".webp":
        spec.attribute("CompressionQuality", 93)
    out = oiio.ImageOutput.create(str(path))
    if not out.open(str(path), spec) or not out.write_image(
        np.ascontiguousarray(pixels)
    ):
        raise OSError(out.geterror())
    out.close()
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = color_space
    image.pack()
    return image


def graphic(directory, source):
    infile = oiio.ImageInput.open(str(source))
    if not infile:
        raise OSError(f"Cannot read the top view {source}")
    data = infile.read_image(oiio.UINT8)
    infile.close()
    rows, cols = np.where(data[:, :, 3] > 235)
    if not len(rows):
        raise ValueError("Expected the transparent top-view gallery photograph")
    art = data[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
    if abs(art.shape[1] / art.shape[0] - WIDTH / DEPTH) > 0.04:
        raise ValueError("The top view does not match the pad's proportions")
    rgb = art[:, :, :3].copy()
    rgb[art[:, :, 3] < 235] = (22, 22, 22)
    peak = np.max(rgb, axis=-1).astype(float)
    ink = np.clip((peak - 29) / 23, 0, 1)
    rgb = np.uint8(
        np.rint(24 + (rgb.astype(float) - 24) * (0.15 + 0.85 * ink[:, :, None]))
    )
    return write_bitmap(directory, "Edition 20 print", rgb, "sRGB")


def finish(name, color, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    surface = material.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = (*color, 1)
    surface.inputs["Roughness"].default_value = roughness
    return material


def image_socket(material, image, uv_name):
    nodes, links = material.node_tree.nodes, material.node_tree.links
    coord = nodes.new("ShaderNodeUVMap")
    coord.uv_map = uv_name
    sampler = nodes.new("ShaderNodeTexImage")
    sampler.image = image
    links.new(coord.outputs["UV"], sampler.inputs["Vector"])
    return sampler.outputs["Color"]


def normal_map(directory, material, height, strength):
    dx = np.roll(height, 1, 1) - np.roll(height, -1, 1)
    dy = np.roll(height, -1, 0) - np.roll(height, 1, 0)
    normals = np.stack((dx, dy, np.ones_like(dx)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    encoded = np.uint8(np.rint((normals * 0.5 + 0.5) * 255))
    bitmap = write_bitmap(directory, material.name, encoded, "Non-Color")
    graph = material.node_tree
    normal = graph.nodes.new("ShaderNodeNormalMap")
    normal.uv_map = "Surface"
    normal.inputs["Strength"].default_value = strength
    graph.links.new(image_socket(material, bitmap, "Surface"), normal.inputs["Color"])
    graph.links.new(
        normal.outputs["Normal"], graph.nodes["Principled BSDF"].inputs["Normal"]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("top_view", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("model", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    rubber = finish("Impressed nonslip rubber", (0.010, 0.011, 0.011), 0.92)
    fabric = finish("Coated textile face", (0.02, 0.02, 0.02), 0.84)
    edging = finish("Charcoal overlock yarn", (0.012, 0.0125, 0.013), 0.72)
    y, x = np.mgrid[:192, :192] / 192
    tau = math.tau
    chevron = np.cos(tau * (8 * x + 4 * np.abs(2 * y - 1)))
    normal_map(directory, rubber, 0.9 * np.tanh(2.5 * chevron), 0.75)
    warp = np.cos(tau * (12 * x + 0.13 * np.sin(tau * 10 * y)))
    weft = np.cos(tau * (10 * y + 0.12 * np.sin(tau * 12 * x)))
    normal_map(directory, fabric, warp * weft + 0.28 * warp, 0.28)
    strand = 8 * x + 0.64 * y + 0.22 * np.sin(tau * y)
    ridge = np.cos(tau * strand) * 0.5 + 0.5
    twist = np.cos(tau * (24 * x - 3 * y))
    normal_map(directory, edging, 2.4 * ridge**0.55 + 0.19 * twist, 0.84)
    layer(
        "01 Die-cut nonslip rubber",
        [(0.85, -1.50), (0.41, -1.44), (0.24, -1.20), (0.24, 0.88), (0.54, 1.11)],
        rubber,
        5.2,
    )
    sheet = layer("02 Printed coated cloth", [(1.55, 1.115), (1.55, 1.50)], fabric, 3.6)
    print_uv = sheet.data.uv_layers.new(name="Edition 20")
    for i, loop in enumerate(sheet.data.loops):
        x, y, _ = sheet.data.vertices[loop.vertex_index].co
        print_uv.data[i].uv = (0.5 + x * 1000 / WIDTH, 0.5 + y * 1000 / DEPTH)
    fabric.node_tree.links.new(
        image_socket(fabric, graphic(directory, args.top_view), "Edition 20"),
        fabric.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    layer(
        "03 Continuous flat-stitched binding",
        [
            (1.55, -1.47),
            (1.08, -1.49),
            (0.61, -1.43),
            (0.24, -1.20),
            (0.04, -0.96),
            (0, -0.52),
            (0, 0.72),
            (0.08, 1.00),
            (0.34, 1.27),
            (0.66, 1.40),
            (0.98, 1.475),
            (1.55, 1.50),
        ],
        edging,
        7.2,
        False,
        False,
    )
    scene = bpy.context.scene
    scene["product"] = "ROG Scabbard II XXL Edition 20"
    scene["dimensions_mm"] = [900, 400, 3]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(directory / "scabbard-ii-xxl.blend"), compress=True
    )
    previous = meshopt.EXP_FILTER_BITS
    try:
        meshopt.EXP_FILTER_BITS = 21
        bpy.ops.export_scene.gltf(
            filepath=str(args.model.resolve()),
            export_format="GLB",
            export_yup=True,
            export_animations=False,
            export_meshopt_compression_enable=True,
            export_meshopt_extension="EXT_meshopt_compression",
        )
    finally:
        meshopt.EXP_FILTER_BITS = previous
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("pack-product-geometry.mjs")),
            str(args.model.resolve()),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
