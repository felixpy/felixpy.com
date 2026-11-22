import math
import runpy
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import bpy

assets = Path(__file__).resolve().parent
root = assets.parents[1]
folder = root / ".review/atelier/nb10000"
sys.path.insert(0, str(assets))
from product_solids import (
    block,
    combine,
    corners,
    edge,
    letters,
    mesh,
    outline,
    subtract,
)

finish = runpy.run_path(str(assets / "vitrine-sculpt.py"))["finish"]
front = 60.95


def weave_texture():
    size = 128
    scalar, relief = [], []
    for y in range(size):
        for x in range(size):
            u, v = (x + 0.5) / 32, (y + 0.5) / 32
            warp = (int(u) - int(v)) % 4 < 2
            cross, along = (u, v) if warp else (v, u)
            arc = math.sin(math.pi * (cross % 1)) ** 0.62
            yarn = math.cos(cross * 16 * math.pi + math.sin(along * math.pi) * 0.22)
            lift = 0.73 + 0.27 * math.cos((along - cross) * math.pi / 2)
            scalar.append(
                round(18 + (13 if warp else 59) * arc * lift + 6 * yarn * arc)
            )
            relief.append(arc * (0.7 + 0.045 * yarn) * lift)
    colors, normals = bytearray(), bytearray()
    for y in range(size):
        for x in range(size):
            col = scalar[y * size + x]
            colors.extend((col, col + 1, col + 2))
            dx = relief[y * size + (x + 1) % size] - relief[y * size + (x - 1) % size]
            dy = (
                relief[((y + 1) % size) * size + x]
                - relief[((y - 1) % size) * size + x]
            )
            mag = math.sqrt(1 + dx * dx + dy * dy)
            normals.extend(round(127.5 * (a / mag + 1)) for a in (-dx, dy, 1))

    def bitmap(name, rgb):
        def chunk(tag, data):
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data))
            )

        path = folder / (name + ".png")
        scan = b"".join(
            b"\0" + rgb[y * size * 3 : (y + 1) * size * 3] for y in range(size)
        )
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scan, 9))
            + chunk(b"IEND", b"")
        )
        image = bpy.data.images.load(str(path))
        image.pack()
        return image

    mat = finish("2 × 2 woven carbon / clear epoxy", "343538", 0.22, 0.37, 0.07)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    color, normal = nodes.new("ShaderNodeTexImage"), nodes.new("ShaderNodeTexImage")
    color.image, normal.image = (
        bitmap("carbon-albedo", colors),
        bitmap("carbon-relief", normals),
    )
    normal.image.colorspace_settings.name = "Non-Color"
    bump = nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = 0.37
    bsdf = nodes.get("Principled BSDF")
    links.new(color.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(normal.outputs["Color"], bump.inputs["Color"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def plate(name, x, h, z, w, height, depth, radius, mat):
    profile = [(x + u, h + v) for u, v in corners(w, height, radius, 8)]
    return outline(name, profile, z - depth, depth, mat)


def shell(name, x, h, z, outside, inside, depth, mat):
    ow, oh, ro = outside
    iw, ih, ri = inside
    vertices = []
    for d, w, height, r in [
        (z, ow, oh, ro),
        (z, iw, ih, ri),
        (z - depth, iw, ih, ri),
        (z - depth, ow, oh, ro),
    ]:
        vertices.extend((x + u, h + v, d) for u, v in corners(w, height, r, 8))
    n = len(vertices) // 4
    faces = []
    for j in range(4):
        for i in range(n):
            a, b = j * n, ((j + 1) % 4) * n
            k = (i + 1) % n
            faces.append((a + i, a + k, b + k, b + i))
    return mesh(name, vertices, faces, mat)


def silk(text, x, h, z, width, height, material, back=False):
    points, faces = letters(text, False)
    xmin, xmax = min(a for a, _ in points), max(a for a, _ in points)
    ymin, ymax = min(b for _, b in points), max(b for _, b in points)
    coords = [
        (
            (a - (xmin + xmax) / 2) * width / (xmax - xmin),
            (b - (ymin + ymax) / 2) * height / (ymax - ymin),
        )
        for a, b in points
    ]
    if back:
        return mesh(text, [(x - u, h + v, z) for u, v in coords], faces, material)
    return mesh(text, [(x + u, h, z - v) for u, v in coords], faces, material)


def skin(name, h, center, length, weave):
    obj = edge(block(name, 0, h, center, 56, 0.68, length, 0.62, weave), 0.11, 3)
    uv = obj.data.uv_layers.new(name="Cloth millimetres")
    for polygon in obj.data.polygons:
        for i in polygon.loop_indices:
            v = obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv = (
                (v.x * 0.985 + v.y * 0.174) / 0.0067,
                (v.y * 0.985 - v.x * 0.174) / 0.0067,
            )
    return obj


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    folder.mkdir(parents=True, exist_ok=True)
    weave = weave_texture()
    carbon = finish("Injection-moulded carbon-filled polymer", "303135", 0.08, 0.39)
    graphite = finish("Graphite bead-blast / port carrier", "27282b", 0.06, 0.49)
    black = finish("PBT, black", "151618", 0.02, 0.50)
    print_ink = finish("Laser dark marking", "18191c", 0.05, 0.55)
    yellow = finish("Injection-moulded yellow bezel", "e7b812", 0.03, 0.37)
    metal = finish("Connector shell / folded stainless", "a8a9a4", 0.86, 0.28)
    gold = finish("Gold-plated contacts", "cca655", 0.83, 0.23)
    rail = block(
        "CFRP · continuous side rails and rear crossmember",
        0,
        5.3,
        0,
        59,
        10.6,
        121.9,
        1.32,
        carbon,
    )
    subtract(
        rail,
        [block("Open front-loading cell well", 0, 5.3, 3, 55.8, 13, 124, 0.45, carbon)],
    )
    edge(rail, 0.22, 3)
    skin("Carbon fabric lid", 10.26, -4.08, 110.9, weave)
    skin("Carbon fabric back panel", 0.34, 0.08, 119.25, weave)
    edge(
        block(
            "Sealed moulded label bridge",
            0,
            10.26,
            55.72,
            55.85,
            0.68,
            8.63,
            0.40,
            carbon,
        ),
        0.06,
        2,
    )
    fascia = plate(
        "Front moulding / pierced ports and light wells",
        0,
        5.25,
        front - 0.2,
        56.4,
        10.22,
        2.2,
        0.72,
        graphite,
    )
    ports = [
        (-17.15, 5.25, (14.78, 6.95, 0.85), (13.25, 5.48, 0.40)),
        (-2.83, 5.65, (10.32, 4.32, 2.0), (8.96, 3.12, 1.46)),
    ]
    cutters = [
        plate("Connector pocket", x, h, front + 1, w + 0.12, th + 0.12, 5, r, black)
        for x, h, (w, th, r), _ in ports
    ]
    indicators = [6.35, 9.05, 11.75, 14.45]
    button_x = 22.26
    cutters.extend(
        plate("Indicator bore", x, 5.20, front + 1, 1.09, 1.09, 5, 0.52, black)
        for x in indicators
    )
    cutters.append(
        plate(
            "Mode switch recess", button_x, 5.20, front + 1, 5.82, 5.72, 5, 0.56, black
        )
    )
    subtract(fascia, cutters)
    edge(fascia, 0.09, 2)
    for i, (x, h, outside, inside) in enumerate(ports):
        port = "USB-A" if i == 0 else "USB-C"
        shell(
            port + " · yellow isolation collar",
            x,
            h,
            front - 0.09,
            outside,
            inside,
            1.9,
            yellow,
        )
        w, d, r = inside
        shell(
            port + " · stainless sleeve",
            x,
            h,
            front - 0.37,
            inside,
            (w - 0.44, d - 0.38, max(0.2, r - 0.15)),
            9.35 if i == 0 else 6.75,
            metal,
        )
        plate(
            port + " · inner end stop",
            x,
            h,
            front - (9.72 if i == 0 else 7.13),
            w - 0.39,
            d - 0.34,
            0.55,
            max(0.2, r - 0.14),
            black,
        )
        tongue = h - 0.85 if i == 0 else h
        plate(
            port + " · keyed tongue",
            x,
            tongue,
            front - 1.15,
            10.7 if i == 0 else 6.64,
            1.42 if i == 0 else 0.67,
            8 if i == 0 else 5.7,
            0.19,
            black,
        )
        pins = 4 if i == 0 else 12
        pitch = 2.2 if i == 0 else 0.48
        for j in range(pins):
            xp = x + (j - (pins - 1) / 2) * pitch
            block(
                port + " · wipe contact",
                xp,
                tongue + (0.722 if i == 0 else 0.35),
                front - 3.5,
                0.83 if i == 0 else 0.22,
                0.05,
                3.6,
                0.045,
                gold,
            )
            if i == 1:
                block(
                    port + " · opposing contact",
                    xp,
                    tongue - 0.35,
                    front - 3.5,
                    0.22,
                    0.05,
                    3.6,
                    0.045,
                    gold,
                )
    blue_lens = finish("Blue unlit lens", "26313b", 0.04, 0.27, 0.23)
    clear_lens = finish("Clear unlit lens", "38393b", 0.04, 0.27, 0.23)
    for i, x in enumerate(indicators):
        plate(
            "Light pipe " + str(i + 1),
            x,
            5.2,
            front - 0.41,
            0.94,
            0.94,
            2.7,
            0.45,
            blue_lens if i < 3 else clear_lens,
        )
    plate(
        "Recessed power switch", button_x, 5.2, front - 0.22, 5.28, 5.14, 2, 0.43, black
    )
    centerline = [
        (
            button_x + 1.52 * math.sin(t * math.pi / 180),
            5.07 + 1.52 * math.cos(t * math.pi / 180),
        )
        for t in range(39, 322, 4)
    ]
    arc = [
        (button_x + (x - button_x) * s, 5.07 + (y - 5.07) * s)
        for s, line in [(1.09, centerline), (0.88, reversed(centerline))]
        for x, y in line
    ]
    symbol = finish("Standby symbol / moulded graphite", "37383a", 0.07, 0.48)
    outline("Standby arc", arc, front - 0.191, 0.022, symbol)
    plate("Standby line", button_x, 6.07, front - 0.169, 0.31, 1.8, 0.022, 0.12, symbol)
    for text, x, z, w, h in [
        ("10000mAh 38.5Wh", -15.2, 54.2, 23, 1.28),
        ("Rated Energy: 6400mAh 5V (TYP 1A)", -15.2, 56.7, 23, 0.76),
        ("Input: USB-C  5V 2.4A / 9V 2A", 12.4, 53.65, 24.8, 0.72),
        ("Output: USB-C  5V 3A / 9V 2.22A / 12V 1.68A", 12.4, 55.25, 25.4, 0.72),
        ("USB-A  5V 3A / 9V 2A / 12V 1.5A", 12.4, 56.9, 22, 0.72),
    ]:
        silk(text, x, 10.634, z, w, h, print_ink)
    silk("NITECORE", -6.6, 5.3, -60.984, 19.6, 3.5, print_ink, True)
    silk("NB10000", 13.8, 5.3, -60.984, 11.1, 2.3, print_ink, True)
    exterior = list(bpy.context.scene.objects)
    pouch = finish("Pouch cell / folded aluminium film", "bbc0bd", 0.71, 0.38)
    pcb = finish("Black solder resist", "23292b", 0.18, 0.46)
    ceramic = finish("MLCC ceramic", "a29880", 0.12, 0.48)
    edge(
        block("38.5 Wh pouch cell", 0, 5.33, -8.1, 54.30, 8.35, 97.85, 1.2, pouch),
        0.68,
        4,
    )
    for x in [-26.65, 26.65]:
        block("Folded heat-seal side seam", x, 5.66, -8.15, 0.74, 5.15, 95, 0.15, pouch)
    block("Pouch neck seal", 0, 3.68, 41.4, 50.7, 1.34, 4.15, 0.55, pouch)
    for x in [-14.2, 12.75]:
        block("Cell foil tab", x, 3.77, 44.1, 8.5, 0.13, 5.9, 0.20, gold)
    block("Power conversion board", 0, 3.43, 49.65, 54.2, 0.88, 19.65, 0.68, pcb)
    for name, x, z, w, d in [
        ("Controller IC", 2.15, 44.25, 4.4, 4.4),
        ("Power inductor", 18.7, 45.7, 6.8, 6.4),
        ("Protection FET", -12, 43.5, 3.6, 3.3),
        ("PD logic", -5.2, 44.55, 3.7, 3.45),
    ]:
        edge(block(name, x, 4.62, z, w, 1.48, d, 0.23, black), 0.12)
    for i in range(12):
        x = -22 + (i % 6) * 4.6
        z = 41.25 + 5.7 * (i // 6)
        block("SMD passives", x, 4.12, z, 1.32, 0.46, 0.73, 0.08, ceramic)
    for x in indicators:
        block("SMD indicator emitter", x, 4.43, 57.73, 1.12, 1.1, 1.45, 0.13, ceramic)
    block("Momentary switch housing", button_x, 5.01, 56.5, 5.44, 3.3, 3.9, 0.35, black)
    for obj in bpy.context.scene.objects:
        obj["assembly"] = "NB10000 Gen II"
        obj["partGroup"] = "Exterior" if obj in exterior else "Internal layout"
    bpy.ops.wm.save_as_mainfile(
        filepath=str(folder / "nitecore-nb10000-gen2.blend"), compress=True
    )
    for obj in list(bpy.context.scene.objects):
        if obj not in exterior:
            bpy.data.objects.remove(obj, do_unlink=True)
    combine("NB10000 Gen II · carbon frame, fabric and recessed interfaces", exterior)
    path = folder / "nitecore-nb10000-gen2.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(assets / "pack-product-geometry.mjs"), str(path)], check=True
    )


if __name__ == "__main__":
    build()
