import argparse
import math
import runpy
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from io_scene_gltf2.io.exp import meshopt
from mathutils import Matrix

TAU = math.tau
APOTHEM = 3.42
TIP = -90.0
TAPER = 0.19
CORE = 1.0
SECTORS = 96
letters = runpy.run_path(str(Path(__file__).with_name("vitrine-sculpt.py")))["letters"]


def material(name, rgb, roughness, metal=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    return mat


def part(name, vertices, faces, finish, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(
        [(x / 1000, y / 1000, z / 1000) for x, y, z in vertices], [], faces
    )
    data.update()
    data.materials.append(finish)
    for face in data.polygons:
        face.use_smooth = smooth
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def hex_radius(angle):
    offset = (angle + TAU / 12) % (TAU / 6) - TAU / 12
    return min(3.91, APOTHEM / math.cos(offset))


def radial(angle, x, radius):
    return x, radius * math.sin(angle), radius * math.cos(angle)


def turned(name, profile, finish, smooth=True, first=0, count=SECTORS, enclosed_rows=()):
    angles = [TAU * (first + i) / SECTORS for i in range(count + (count < SECTORS))]
    rows = [[radial(a, *section(a)) for a in angles] for section in profile]
    width = len(angles)
    faces = []
    for j in range(len(rows)):
        k = (j + 1) % len(rows)
        for i in range(count):
            n = (i + 1) % width
            faces.append((j * width + i, k * width + i, k * width + n, j * width + n))
    if count < SECTORS:
        faces.extend(
            [
                tuple(j * width for j in reversed(range(len(rows)))),
                tuple(j * width + count for j in range(len(rows))),
            ]
        )
    obj = part(name, [v for row in rows for v in row], faces, finish, smooth)
    if enclosed_rows:
        enclosed = obj.data.attributes.new("Enclosed by assembly", "BOOLEAN", "FACE")
        enclosed.data.foreach_set(
            "value", [i // count in enclosed_rows for i in range(len(faces))]
        )
    return obj


def ring(x, radius):
    return lambda a: (x, radius)


def pencil_body():
    lacquer = material("Deep oxblood lacquer", (0.114, 0.017, 0.025), 0.31)
    wood = material("Sharpened cedar", (0.59, 0.35, 0.17), 0.72)
    core = material("HB graphite and clay", (0.052, 0.049, 0.046), 0.32, 0.23)
    turned(
        "HB lead · continuous core",
        [
            ring(TIP, 0.075),
            ring(TIP + (CORE - 0.075) / TAPER, CORE),
            ring(80.5, CORE),
            ring(80.5, 0.001),
            ring(TIP, 0.001),
        ],
        core,
    )
    wood_start = TIP + (CORE - 0.075) / TAPER
    for half in range(2):
        obj = turned(
            ["Cedar slat · left channel", "Cedar slat · right channel"][half],
            [
                ring(wood_start, CORE),
                lambda a: (TIP + (hex_radius(a) - 0.11) / TAPER, hex_radius(a) - 0.035),
                lambda a: (71.8, hex_radius(a) - 0.035),
                ring(72.1, 3.36),
                ring(80.5, 3.36),
                ring(80.5, CORE),
            ],
            wood,
            False,
            first=half * SECTORS // 2,
            count=SECTORS // 2,
            enclosed_rows=(1, 5, 6),
        )
        uv = obj.data.uv_layers.new(name="Long grain")
        for loop in obj.data.loops:
            x, y, z = (v * 1000 for v in obj.data.vertices[loop.vertex_index].co)
            uv.data[loop.index].uv = ((x - TIP) / 23.0, (y + 0.21 * z) / 8.0 + 0.5)
    tint = bpy.data.images.new("Split cedar fibres", width=192, height=128, alpha=False)
    pixels = []
    for y in range(128):
        for x in range(192):
            phase = y + 1.4 * math.sin(x * 0.021) + x * 0.019
            grain = 0.11 * math.sin(phase * 1.73) + 0.045 * math.sin(phase * 0.41)
            pixels.extend((0.82 + grain, 0.64 + grain, 0.44 + grain, 1))
    tint.pixels.foreach_set(pixels)
    tint.pack()
    img = wood.node_tree.nodes.new("ShaderNodeTexImage")
    img.image = tint
    wood.node_tree.links.new(
        img.outputs["Color"],
        wood.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    turned(
        "Enamel · six facets and cut scallops",
        [
            lambda a: (TIP + (hex_radius(a) - 0.11) / TAPER, hex_radius(a) - 0.035),
            lambda a: (TIP + (hex_radius(a) - 0.075) / TAPER, hex_radius(a)),
            lambda a: (71.84, hex_radius(a)),
            lambda a: (71.84, hex_radius(a) - 0.035),
        ],
        lacquer,
        False,
        enclosed_rows=(3,),
    )


def ferrule_and_eraser():
    nickel = material("Rolled nickel silver", (0.76, 0.70, 0.62), 0.24, 0.96)
    eraser = material("Warm white eraser", (0.80, 0.77, 0.69), 0.79)
    profile = []
    for x, radius in [
        (71.6, 3.64),
        (71.68, 3.85),
        (71.95, 3.9),
        (72.3, 3.77),
        (73.8, 3.77),
        (74.45, 3.77),
        (75.12, 3.77),
        (75.43, 3.88),
        (75.69, 3.87),
        (75.92, 3.73),
        (76.2, 3.73),
        (76.48, 3.89),
        (76.74, 3.86),
        (77.0, 3.75),
        (79.6, 3.75),
        (79.86, 3.88),
        (80.12, 3.88),
        (80.42, 3.73),
        (80.76, 3.73),
        (81.04, 3.88),
        (81.3, 3.88),
        (81.62, 3.76),
        (82.25, 3.76),
        (82.9, 3.76),
        (83.5, 3.76),
        (84.4, 3.82),
        (84.55, 3.7),
    ]:

        def section(a, x=x, radius=radius):
            offset = (a + TAU / 12) % (TAU / 6) - TAU / 12
            row = max(0.0, 1 - min(abs(x - 74.45), abs(x - 82.9)) / 0.67)
            return x, radius - row * 0.28 * max(0.0, 1 - abs(offset) / 0.24)

        profile.append(section)
    turned(
        "Ferrule · folded rims and two rows of clinches",
        profile + [ring(84.55, 3.54), ring(71.6, 3.54)],
        nickel,
    )
    turned(
        "Eraser plug · recessed into ferrule",
        [
            ring(80.52, 3.53),
            ring(84.55, 3.53),
            ring(89.56, 3.52),
            ring(89.83, 3.46),
            ring(89.96, 3.28),
            ring(90.0, 3.03),
            ring(90.0, 0.001),
            ring(80.52, 0.001),
        ],
        eraser,
    )


def foil():
    vertices, faces = [], []

    def transfer(facet, points, indices):
        a = facet * TAU / 6
        base = len(vertices)
        for x, v in points:
            vertices.append(
                (
                    x,
                    (APOTHEM + 0.012) * math.sin(a) + v * math.cos(a),
                    (APOTHEM + 0.012) * math.cos(a) - v * math.sin(a),
                )
            )
        faces.extend(tuple(base + i for i in face) for face in indices)

    def mark(facet, text, x, v, width, height, italic=False):
        points, indices = letters(text, italic)
        xs, ys = zip(*points)
        left, bottom = min(xs), min(ys)
        dx, dy = max(xs) - left, max(ys) - bottom
        transfer(
            facet,
            [
                (x + (px - left) / dx * width, v + (py - bottom) / dy * height)
                for px, py in points
            ],
            indices,
        )

    mark(0, "MITSUBISHI", -21.8, 0.10, 15.2, 0.81)
    mark(0, "PENCIL CO., LTD.", -24.0, -0.91, 19.0, 0.78)
    mark(0, '"MITSU-BISHI"', -1.1, -0.94, 30, 1.95)
    for i in range(3):
        angle = i * TAU / 3
        diamond = [
            (
                32.3 + x * math.cos(angle) - v * math.sin(angle),
                -0.20 + x * math.sin(angle) + v * math.cos(angle),
            )
            for x, v in [(0, 0), (0.43, 0.74), (0, 1.48), (-0.43, 0.74)]
        ]
        transfer(0, diamond, [(0, 1, 2, 3)])
    mark(0, "9 8 5 0", 36.4, -0.9, 8.5, 1.92)
    mark(2, "SMOOTH WRITING PENCIL FOR", -40, -0.66, 43, 1.32)
    mark(2, "Office Use", 5, -0.94, 23.5, 1.88, True)
    for face in (0, 2, 4):
        mark(face, "* H B *", 51, -0.78, 12.3, 1.6)
    left = [
        "0001101",
        "0011001",
        "0010011",
        "0111101",
        "0100011",
        "0110001",
        "0101111",
        "0111011",
        "0110111",
        "0001011",
    ]
    value = "4902778981061"
    encoded = "101"
    for number, mode in zip(value[1:7], "LGLLGG"):
        bits = left[int(number)]
        encoded += (
            bits if mode == "L" else bits[::-1].translate(str.maketrans("01", "10"))
        )
    encoded += (
        "01010"
        + "".join(left[int(c)].translate(str.maketrans("01", "10")) for c in value[7:])
        + "101"
    )
    module = 0.29
    for i, bit in enumerate("0" * 11 + encoded + "0" * 7):
        if bit == "0":
            x = -65.5 + i * module
            transfer(
                4,
                [(x, -1.37), (x + module, -1.37), (x + module, 1.37), (x, 1.37)],
                [(0, 1, 2, 3)],
            )
    mark(4, "4 902778 981061", -29.2, -0.92, 22.1, 1.84)
    return part(
        "Hot-stamped foil · three printed facets",
        vertices,
        faces,
        material("Brushed silver stamping", (0.76, 0.74, 0.69), 0.34, 0.63),
    )


def seat_on_facet():
    points = [v.co for obj in bpy.context.scene.objects for v in obj.data.vertices]
    first = min((v for v in points if -0.073 < v.x < -0.071), key=lambda v: v.z)
    slope = min((v.z - first.z) / (v.x - first.x) for v in points if v.x > 0.065)
    rotation = Matrix.Rotation(math.atan(slope), 4, "Y")
    floor = min((rotation @ v).z for v in points)
    transform = Matrix.Translation((0, 0, -floor)) @ rotation
    for obj in bpy.context.scene.objects:
        obj.data.transform(transform)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("model", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pencil_body()
    ferrule_and_eraser()
    foil()
    seat_on_facet()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["product"] = "Mitsubishi Pencil 9850 HB"
    scene["sharpenedLengthMm"] = 180
    pencil = bpy.data.collections.new("Mitsubishi 9850 HB · complete pencil")
    scene.collection.children.link(pencil)
    for part in list(scene.collection.objects):
        pencil.objects.link(part)
        scene.collection.objects.unlink(part)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str((args.directory / "mitsubishi-9850.blend").resolve()),
        compress=True,
    )
    for obj in scene.objects:
        data = obj.data
        enclosed = data.attributes.get("Enclosed by assembly")
        if enclosed is None:
            continue
        indices = [i for i, face in enumerate(enclosed.data) if face.value]
        data.attributes.remove(enclosed)
        editable = bmesh.new()
        editable.from_mesh(data)
        editable.faces.ensure_lookup_table()
        bmesh.ops.delete(editable, geom=[editable.faces[i] for i in indices], context="FACES")
        editable.to_mesh(data)
        editable.free()
    original_bits = meshopt.EXP_FILTER_BITS
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
        meshopt.EXP_FILTER_BITS = original_bits
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
