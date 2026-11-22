import argparse
import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy

assets = Path(__file__).resolve().parent
root = assets.parents[1]
common = runpy.run_path(str(assets / "vitrine-sculpt.py"))
finish = common["finish"]
sys.path.insert(0, str(assets))
from product_solids import block, combine, edge, mesh, pin, subtract, vertex


def title(name, x, h, z, size, mat, front=False):
    points, faces = common["letters"](name, False)
    pts = (
        [(x + a * size, h + b * size, z) for a, b in points]
        if front
        else [(x + a * size, h, z - b * size) for a, b in points]
    )
    return mesh(name, pts, faces, mat)


def top_normal(obj):
    import numpy as np

    size = 128
    y, x = np.mgrid[:size, :size]
    a = np.sin((x + y) * math.tau / size)
    b = np.sin((x - y) * math.tau / size)
    height = (1 - np.abs(a)) ** 5 * 0.6 + (1 - np.abs(b)) ** 6 * 0.32
    dx = np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
    dy = np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)
    normals = np.stack([-dx * 3.2, -dy * 3.2, np.ones_like(dx)], axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    pixels = np.ones((size, size, 4), np.float32)
    pixels[:, :, :3] = normals * 0.5 + 0.5
    texture = bpy.data.images.new(
        "Crosshatched injection mould", size, size, alpha=False, is_data=True
    )
    texture.pixels.foreach_set(pixels.ravel())
    texture.pack()
    tile = obj.active_material.node_tree.nodes.new("ShaderNodeTexImage")
    tile.image = texture
    tree = obj.active_material.node_tree
    normal = tree.nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.58
    tree.links.new(tile.outputs["Color"], normal.inputs["Color"])
    tree.links.new(normal.outputs[0], tree.nodes["Principled BSDF"].inputs["Normal"])
    uv = obj.data.uv_layers.new(name="Surface")
    for loop in obj.data.loops:
        co = obj.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / 0.0031, co.y / 0.0031)


def battery_cover(body):
    cover = block("Battery mount cover", 0, 30.3, -65.6, 137, 39.8, 1.42, 1.5, body)
    x0, y0 = -21.6, 16.15
    cols, rows, pitch = 20, 13, 2.18
    width, height = cols * pitch, rows * pitch
    subtract(
        cover,
        [
            block(
                "Vent insert",
                -x0 - width / 2,
                y0 + height / 2,
                -65,
                width,
                height,
                10,
                0.001,
                body,
            )
        ],
    )
    data, faces = [], []
    for j in range(rows):
        for i in range(cols):
            x = -x0 - width + (i + 0.5) * pitch
            y = y0 + (j + 0.5) * pitch
            offset = len(data)
            for rad, depth, square in [
                (pitch / 2, -66.31, True),
                (0.59, -66.31, False),
                (0.59, -64.89, False),
            ]:
                for k in range(12):
                    a = math.tau * k / 12 + math.pi / 4
                    c, s = math.cos(a), math.sin(a)
                    r = rad / max(abs(c), abs(s)) if square else rad
                    data.append((x + r * c, y + r * s, depth))
            for k in range(12):
                n = (k + 1) % 12
                faces.extend(
                    [
                        (offset + k, offset + 12 + k, offset + 12 + n, offset + n),
                        (
                            offset + 12 + k,
                            offset + 24 + k,
                            offset + 24 + n,
                            offset + 12 + n,
                        ),
                    ]
                )
    holes = mesh("Moulded perforations", data, faces, body)
    return combine("Detachable perforated battery cover", [cover, holes])


def photo_ink(name, matte):
    mat = finish(name, "ffffff", rough=0.6 if matte else 0.24, coat=0.08)
    tree = mat.node_tree
    atlas = bpy.data.images.load(
        str(root / "public/media/photography/travel-prints.webp"), check_existing=True
    )
    atlas.pack()
    sample = tree.nodes.new("ShaderNodeTexImage")
    sample.image = atlas
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / 3, 0.5, 1)
    mapping.inputs["Location"].default_value = (2 / 3, 0.5, 0)
    uv = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(uv.outputs["UV"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], sample.inputs["Vector"])
    tree.links.new(
        sample.outputs["Color"], tree.nodes["Principled BSDF"].inputs["Base Color"]
    )
    return mat


def proof_sheet():
    stock = finish("Postcard satin stock", "f6f3eb", rough=0.55)
    ink = photo_ink("Selphy postcard image", True)
    address = finish("KP-36IP · writable address side", "ffffff", rough=0.83)
    tree = address.node_tree
    sample = tree.nodes.new("ShaderNodeTexImage")
    sample.image = bpy.data.images.load(str(assets / "selphy-kp36ip-reverse.png"))
    sample.image.pack()
    tree.links.new(sample.outputs["Color"], tree.nodes["Principled BSDF"].inputs["Base Color"])
    verts, faces, inks = [], [], []

    def curl(x, y):
        return 0.65 * (x / 50) ** 2 + 0.45 * ((y + 88.5) / 177) ** 2

    cuts = [(-49.5 + i * 1.665, -49.5 + i * 1.665 + 0.87) for i in range(60)]
    regular = [-50, -48, -36, -24, -12, 0, 12, 24, 36, 48, 50]
    perforated = sorted(set(regular).union(x for cut in cuts for x in cut))
    ys = [-88.5, -74.04, -73.96, -64, -48, -32, -16, 0, 16, 32, 48, 64, 73.96, 74.04, 88.5]
    rows = []
    for y in ys:
        coordinates = perforated if abs(abs(y) - 74) < 0.1 else regular
        row = {}
        for x in coordinates:
            row[x] = len(verts)
            verts.append((x, y, curl(x, y)))
        rows.append(row)
    face_size = len(verts)
    verts.extend((x, y, z - 0.24) for x, y, z in verts[:])
    boundary = set()

    def surface(face, printed):
        faces.extend((face, tuple(k + face_size for k in reversed(face))))
        inks.extend((int(printed), 2))
        for a, b in zip(face, face[1:] + face[:1]):
            if (b, a) in boundary:
                boundary.remove((b, a))
            else:
                boundary.add((a, b))

    for lower, upper, y0, y1 in zip(rows, rows[1:], ys, ys[1:]):
        scored = y0 < -74 < y1 or y0 < 74 < y1
        intervals = perforated if scored else regular
        for x0, x1 in zip(intervals, intervals[1:]):
            if scored and any(lo <= x0 and x1 <= hi for lo, hi in cuts):
                continue
            printed = -48 <= x0 and x1 <= 48 and -64 <= y0 and y1 <= 64
            low = [v for x, v in lower.items() if x0 <= x <= x1]
            high = [v for x, v in reversed(upper.items()) if x0 <= x <= x1]
            if len(low) == len(high) == 2:
                surface(tuple(low + high), printed)
            else:
                loop = low + high if len(low) == 2 else high + low
                for b, c in zip(loop[1:], loop[2:]):
                    surface((loop[0], b, c), printed)
    for a, b in sorted(boundary):
        faces.append((b, a, a + face_size, b + face_size))
        inks.append(0)
    obj = mesh("Postcard proof with removable trim tabs", verts, faces, stock)
    obj.data.materials.append(ink)
    obj.data.materials.append(address)
    uv = obj.data.uv_layers.new(name="Paper print registration")
    for poly, slot in zip(obj.data.polygons, inks):
        poly.material_index = slot
        for i in poly.loop_indices:
            x, y, _ = verts[obj.data.loops[i].vertex_index]
            if slot == 2:
                uv.data[i].uv = (y + 88.5) / 177, (x + 50) / 100
            else:
                uv.data[i].uv = (x + 48) / 96, (y + 64) / 128
    obj.location = vertex(0, 20.7, 145)
    obj.rotation_euler.x = -math.pi / 2 + 0.024
    obj["selphyProof"] = True
    obj["paperSet"] = "Canon KP-36IP"
    return obj


def ribbon_cartridge(red, bright, dye):
    parts = []
    for side in (-1, 1):
        center = side * 23.4
        parts.append(pin("Spool", (-62, 30.8, center), (70, 30.8, center), 5.5, bright))
        parts.append(pin("Dye roll", (-53, 30.8, center), (54, 30.8, center), 6.2, dye))
        shell = []
        for x in (-60, 70):
            for r in (9.8, 8.5):
                for j in range(37):
                    a = math.radians(-134 + 268 * j / 36)
                    shell.append(
                        (x, 30.8 + r * math.cos(a), center + side * r * math.sin(a))
                    )
        fs = []
        for k in range(36):
            fs += [
                (k, k + 1, k + 75, k + 74),
                (k + 37, k + 111, k + 112, k + 38),
                (k, k + 37, k + 38, k + 1),
                (k + 74, k + 75, k + 112, k + 111),
            ]
        fs += [(0, 74, 111, 37), (36, 73, 147, 110)]
        parts.append(mesh("Formed spool cover", shell, fs, red))
        parts.append(
            pin("Takeup bearing", (70, 30.8, center), (75, 30.8, center), 5.4, red)
        )
        for k in range(14):
            a = math.tau * k / 14
            y = 30.8 + 4.8 * math.cos(a)
            z = center + 4.8 * math.sin(a)
            parts.append(pin("Toothed hub", (72, y, z), (75.4, y, z), 0.77, red, 8))
    for x in (-59, 68.8):
        parts.append(
            edge(block("Lower end bridge", x, 24, 0, 3.4, 4.5, 58, 1.5, red), 0.62)
        )
        for side in (-1, 1):
            parts.append(
                pin(
                    "Rounded cartridge end",
                    (x - 1.8, 30.8, side * 23.4),
                    (x + 1.8, 30.8, side * 23.4),
                    9.6,
                    red,
                )
            )
    parts.append(block("Ribbon sheet", 0, 35.85, 0, 105, 0.075, 46.8, 0.15, dye))
    return combine("Removable colour ink cassette", parts)


def build():
    body = finish("Pearl white PC-ABS", "e7e8e3", rough=0.47)
    top = finish("Fine pearl crosshatch", "e9e9e6", rough=0.49)
    keys = finish("Satin polar grey controls", "d9dad7", rough=0.45)
    shadow = finish("Warm grey parting line", "7c7d79", rough=0.66)
    black = finish("Paper transport interior", "252628", rough=0.72)
    grey = finish("Light grey paper guides", "b8b8b3", rough=0.66)
    rubber = finish("Rubber transport wheels", "434445", rough=0.89)
    bright = finish("Nickel axle", "8b8c89", metal=0.78, rough=0.31)
    glass = finish("LCD polarizer", "25282a", rough=0.16, coat=0.31)
    ink = finish("Control silk", "545556", rough=0.73)
    red = finish("Ribbon cartridge rose", "b34f68", rough=0.48)
    dye = finish("Dye ribbon amber panel", "ebb152", metal=0.19, rough=0.26)
    tray = finish("Graphite smoke cassette window", "686b68", rough=0.27, coat=0.26)

    shell = block("Lower housing", 0, 28, 0, 182.2, 51, 133, 10.8, body)
    subtract(
        shell, [block("Enclosed transport void", 0, 27.5, 0, 174, 43, 123, 8, black)]
    )
    subtract(
        shell,
        [
            block("Front cassette mouth", 0, 22, 65, 124, 34.2, 18, 1.1, black),
            block("SD slot", -56, 45.3, 65, 26.2, 2.8, 16, 1.1, black),
        ],
    )
    subtract(
        shell,
        [
            block("Rear pass", 0, 7.6, -64, 110, 2.4, 16, 1.2, black),
            block("Battery pocket", 0, 30.4, -64, 138, 40.4, 12, 1.6, black),
        ],
    )
    subtract(
        shell,
        [
            block("Service opening", 89, 27, 2.7, 14, 35.0, 104, 1.1, black),
            block("USB-C aperture", -89, 41, 39, 12, 3.4, 9.4, 0.9, black),
            block("Security slot", -89, 12, -20, 12, 3.1, 7, 1.4, black),
            pin("DC socket", (-96, 30, -49), (-84, 30, -49), 4.2, black),
        ],
    )
    edge(shell, 0.48)
    under = [block("Lower pan", 0, 3.8, 0, 175.6, 2.8, 127, 9, body)]
    for x in (-67, 67):
        for z in (-43, 43):
            under.append(block("Non-slip foot", x, 1.55, z, 17, 3.1, 10.4, 3.0, rubber))
            under.append(
                pin(
                    "Recessed pan fixing", (x + 9, 2.32, z), (x + 9, 2.46, z), 1.55, ink
                )
            )
    combine("Underside pan, screws and four feet", under)
    lid = block("Embossed upper shell", 0, 55.35, 0, 182.2, 4.5, 133, 10.8, top)
    subtract(
        lid, [block("Control insert pocket", 41, 57.65, 0, 78.6, 2.0, 111, 3.6, black)]
    )
    edge(lid, 0.58)
    top_normal(lid)
    pad = [
        block("Gasket", 41, 56.89, 0, 78.45, 0.43, 110.85, 3.55, shadow),
        block("Control bed", 41, 57.06, 0, 77.75, 0.42, 110.25, 3.36, keys),
        edge(
            block("Display polarizer", 41, 57.38, -7.2, 73.9, 0.28, 49.3, 0.7, glass),
            0.08,
        ),
        title("SELPHY", 65, 57.29, -45.4, 5.35, ink),
        title("CP1500", 68.5, 57.29, -41.8, 2.6, ink),
    ]
    for x, z, w, d, label in [
        (13, 29, 20.9, 11.6, "MENU"),
        (13, 43.3, 20.9, 14.6, "BACK"),
        (41, 38.2, 34, 25.5, "OK"),
        (69.1, 39.6, 18.4, 27.1, ""),
    ]:
        pad += [
            block("Button seat", x, 57.3, z, w + 0.38, 0.2, d + 0.38, 1.4, shadow),
            edge(block("Key", x, 57.45, z, w, 0.26, d, 1.22, keys), 0.1),
        ]
        if label:
            pad.append(title(label, x, 57.60, z, 2.5, ink))
    for x, z, dx, dz in [
        (41, 29, 0, -1),
        (41, 47.3, 0, 1),
        (27.3, 38, -1, 0),
        (54.7, 38, 1, 0),
    ]:
        pad.append(
            mesh(
                "Direction",
                [
                    (x + dx, 57.61, z + dz),
                    (x - dx * 0.55 + dz * 0.8, 57.61, z - dz * 0.55 - dx * 0.8),
                    (x - dx * 0.55 - dz * 0.8, 57.61, z - dz * 0.55 + dx * 0.8),
                ],
                [(0, 1, 2)],
                ink,
            )
        )
    for i in range(18):

        def arc(t):
            a = 0.47 + t * (math.tau - 0.94) / 18
            return (69.1 + 1.57 * math.sin(a), 57.61, 42.7 - 1.57 * math.cos(a))

        pad.append(pin("Power mark", arc(i), arc(i + 1), 0.17, ink, 6))
    pad.append(
        pin("Power stroke", (69.1, 57.61, 40.6), (69.1, 57.61, 42.6), 0.17, ink, 6)
    )
    combine("Fixed display, recessed keys and control graphics", pad)

    wheels = [
        pin("Feed axle", (-61, 27.8, 54), (61, 27.8, 54), 1.8, bright),
        block("Thermal head carrier", 0, 33.3, 39, 109, 5.2, 9.8, 1.1, black),
    ]
    for x in (-47, -31, -9, 9, 31, 47):
        wheels.append(
            pin("Pinch roller", (x - 3.9, 27.8, 54), (x + 3.9, 27.8, 54), 4.45, rubber)
        )
    for x in (-53, -23, 23, 53):
        wheels.append(
            pin(
                "Cassette alignment wheel",
                (x - 2.4, 12.5, 57.3),
                (x + 2.4, 12.5, 57.3),
                4,
                grey,
            )
        )
    wheels += [
        block("Paper tunnel floor", 0, 18, 0, 112, 1.8, 121, 1.1, black),
        block("Left guide", -58, 20.3, 0, 2.4, 8, 119, 0.8, black),
        block("Right guide", 58, 20.3, 0, 2.4, 8, 119, 0.8, black),
    ]
    combine("Paper transport, head carrier and guide wheels", wheels)
    ribbon_cartridge(red, bright, dye)
    door = edge(
        block("Ink access door", 89.8, 26.9, 2.7, 2.52, 34.0, 103, 1.1, body), 0.48
    )
    door["servicePart"] = "inkDoor"
    battery_cover(body)
    back = [
        block("Battery bay backing", 0, 30, -59.2, 140, 42, 2, 1.2, black),
        block("SD socket interior", -56, 44.9, 61.5, 28, 7.4, 2, 0.5, black),
        block("USB-C socket tongue", -88.6, 40.9, 39, 2, 0.58, 7.8, 0.35, black),
        pin("DC barrel", (-86, 30, -49), (-88.8, 30, -49), 3.8, black),
        pin("DC contact", (-87.9, 30, -49), (-90, 30, -49), 0.86, bright),
        block("Battery release", 54, 32.5, -61.8, 6, 12, 2.2, 0.7, grey),
    ]
    for row in range(10):
        back.append(
            block("Air louvre", 1, 15.6 + row * 3.1, -61, 41, 1.4, 2.2, 0.7, grey)
        )
    combine("Rear battery bay, release, louvres and sockets", back)
    front = [
        edge(block("Hinged access flap", 0, 6.3, 78, 123.4, 2.6, 31, 2.2, body), 0.7),
        title("Canon", 0, 44.3, 66.56, 7.4, ink, True),
    ]
    for x in (-56, 56):
        front.append(
            pin("Door hinge", (x - 3.2, 7, 64.5), (x + 3.2, 7, 64.5), 1.9, grey)
        )
    combine("Open cassette door and front markings", front)
    feed = [
        edge(
            block("Postcard cassette bottom", 0, 9.7, 131, 115, 4.0, 151, 3, grey), 0.72
        ),
        edge(block("Smoke grey base", 0, 12.1, 130, 108.4, 2.1, 147, 2.2, tray), 0.62),
        block("Unprinted paper stack", 0, 14, 124, 100, 2.1, 141, 1.1, body),
    ]
    for x in (-55.8, 55.8):
        feed.append(
            edge(
                block("Cassette retaining rail", x, 13.4, 131, 3.35, 6.1, 146, 1, grey),
                0.55,
            )
        )
    feed += [
        edge(block("Smoke cover", 0, 17.8, 144, 109, 1.7, 114, 2.5, tray), 0.55),
        edge(block("Front lip", 0, 12.5, 204, 112, 5.5, 3.6, 1.3, grey), 0.6),
    ]
    combine("Postcard supply cassette and protective lid", feed)
    screen = photo_ink("Selphy LCD thumbnail", False)
    plane = mesh(
        "LCD print preview",
        [
            (41 + x, 57.55, -7.2 + d)
            for x, d in [(-17.9, 23.86), (17.9, 23.86), (17.9, -23.86), (-17.9, -23.86)]
        ],
        [(0, 1, 2, 3)],
        screen,
    )
    uv = plane.data.uv_layers.new(name="Surface")
    for i, coord in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = coord


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    options = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    out = options.output_dir or root / ".references/05-摄影与陈列/照片打印/Canon SELPHY CP1500/Blender"
    target = (options.output_dir or root / "public/media/models") / "selphy-cp1500.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out.mkdir(parents=True, exist_ok=True)
    build()
    proof = proof_sheet()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(out / "selphy-cp1500.blend"), compress=True
    )
    for name in ("Selphy LCD thumbnail", "Selphy postcard image"):
        tree = bpy.data.materials[name].node_tree
        for link in list(tree.nodes["Principled BSDF"].inputs["Base Color"].links):
            tree.links.remove(link)
    for obj in scene.objects:
        if obj.type == "MESH" and obj != proof:
            for uv in list(obj.data.uv_layers):
                if uv.name != "Surface":
                    obj.data.uv_layers.remove(uv)
    combine(
        "Canon SELPHY CP1500 with postcard cassette",
        [obj for obj in scene.objects if obj.type == "MESH" and obj != proof],
    )
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_animations=False,
        export_extras=True,
    )
    pack = ["node", str(assets / "pack-product-geometry.mjs"), str(target)]
    subprocess.run([*pack, "--lossless"], check=True)
    subprocess.run(pack, check=True)


if __name__ == "__main__":
    main()
