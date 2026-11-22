import json
import math
import os
import random
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

assets = Path(__file__).resolve().parent
project = assets.parents[1]
atelier = project / ".review/atelier/samsung-t7"
sys.path.insert(0, str(assets))
from product_solids import block, combine, corners, edge, letters, mesh, pin, subtract

finish = runpy.run_path(str(assets / "vitrine-sculpt.py"))["finish"]


def extrusion(name, stations, material, closed=True, offset=0):
    vertices = []
    for x, width, height, radius in stations:
        vertices.extend(
            (x, v, offset + u) for u, v in corners(width, height, radius, 12)
        )
    count = len(vertices) // len(stations)
    faces = []
    for i in range(len(stations) if closed else len(stations) - 1):
        start, end = i * count, (i + 1) % len(stations) * count
        for j in range(count):
            k = (j + 1) % count
            faces.append((start + j, end + j, end + k, start + k))
    if not closed:
        faces.extend(
            (
                tuple(range(count)),
                tuple(reversed(range(len(vertices) - count, len(vertices)))),
            )
        )
    obj = mesh(name, vertices, faces, material)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


def plug(name, x0, x1, width, height, radius, material, offset=0):
    return extrusion(
        name,
        [(x0, width, height, radius), (x1, width, height, radius)],
        material,
        False,
        offset,
    )


def anodized_finish():
    mat = finish("Titan Gray · bead-blasted anodized aluminium", "57565c", 0.76, 0.42)
    side = 64
    rng = random.Random(7302)
    noise = [rng.gauss(0, 0.11) for _ in range(side * side)]
    pixels = []
    for y in range(side):
        for x in range(side):
            dx = noise[y * side + (x + 1) % side] - noise[y * side + (x - 1) % side]
            dy = noise[((y + 1) % side) * side + x] - noise[((y - 1) % side) * side + x]
            length = math.sqrt(dx * dx + dy * dy + 1)
            pixels.extend(
                ((1 - dx / length) / 2, (1 - dy / length) / 2, (1 + 1 / length) / 2, 1)
            )
    image = bpy.data.images.new(
        "T7 · aluminium bead-blast microfinish", side, side, alpha=False
    )
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels)
    image.pack()
    nodes = mat.node_tree.nodes
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.22
    mat.node_tree.links.new(texture.outputs["Color"], normal.inputs["Color"])
    mat.node_tree.links.new(
        normal.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"]
    )
    return mat


def markings(label, x, h, z, width, height, material, underside=False):
    points, faces = letters(label, False)
    xmin, xmax = min(u for u, _ in points), max(u for u, _ in points)
    ymin, ymax = min(v for _, v in points), max(v for _, v in points)
    direction = 1 if underside else -1
    coords = [
        (
            x + (u - (xmax + xmin) / 2) * width / (xmax - xmin),
            h,
            z + direction * (v - (ymax + ymin) / 2) * height / (ymax - ymin),
        )
        for u, v in points
    ]
    return mesh(label, coords, faces, material)


def face_mark(material):
    art = json.loads((assets / "t7-wordmark.json").read_text())
    vertices, faces = [], []
    for outline in art["outlines"]:
        poly = [Vector((u, v)) for u, v in outline]
        tris = tessellate_polygon([poly])
        start = len(vertices)
        vertices.extend(
            (
                (u - art["width"] / 2) * 30.55 / art["width"],
                4.028,
                (art["height"] / 2 - v) * 30.55 / art["width"],
            )
            for u, v in outline
        )
        for a, b, c in tris:
            if (poly[b] - poly[a]).cross(poly[c] - poly[a]) < 0:
                b, c = c, b
            faces.append((start + a, start + b, start + c))
    mesh("Centre silk · seven manufacturer glyphs", vertices, faces, material)


def identification_film(cap):
    width, height = 55.42, 6.52
    closure = plug(
        "Identification end · printed adhesive film",
        42.21,
        42.32,
        width,
        height,
        3.17,
        cap,
    )
    material = finish("T7 · printed regulatory label", "626166", 0.13, 0.46)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "t7-identification.png"
        subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--with",
                "pillow",
                "--with",
                "zxing-cpp",
                "--",
                "python",
                str(assets / "paint-t7-identification.py"),
                str(path),
            ],
            check=True,
        )
        image = bpy.data.images.load(str(path))
        image.pack()
        image.filepath = "//t7-identification.png"
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    material.node_tree.links.new(
        texture.outputs["Color"],
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    closure.data.materials.append(material)
    uv = closure.data.uv_layers.new(name="UVMap")
    for face in closure.data.polygons:
        if face.normal.x < 0.999:
            continue
        face.material_index = 1
        for i in face.loop_indices:
            v = closure.data.vertices[closure.data.loops[i].vertex_index].co
            uv.data[i].uv = (0.5 + v.y * 1000 / width, 0.5 + v.z * 1000 / height)


def enclosure(alloy, cap, nickel, polymer, contacts, ink):
    body = extrusion(
        "One-piece hollow rolled aluminium extrusion",
        [
            (-42.5, 56.83, 7.83, 3.83),
            (-42.38, 57, 8, 3.92),
            (42.38, 57, 8, 3.92),
            (42.5, 56.83, 7.83, 3.83),
            (42.5, 55.53, 6.63, 3.23),
            (-42.5, 55.53, 6.63, 3.23),
        ],
        alloy,
    )
    uv = body.data.uv_layers.new(name="UVMap")
    for face in body.data.polygons:
        for loop in face.loop_indices:
            v = body.data.vertices[body.data.loops[loop].vertex_index].co
            uv.data[loop].uv = (v.x / 0.0028, (v.y + v.z) / 0.0028)
    identification_film(cap)
    fascia = plug(
        "I/O end moulding · connector and LED perforations",
        -42.32,
        -41.05,
        55.42,
        6.52,
        3.17,
        cap,
    )
    subtract(
        fascia,
        [
            plug("Socket bore", -43, -40, 9.25, 3.56, 1.65, polymer),
            plug("Indicator bore", -43, -40, 0.87, 0.87, 0.42, polymer, -11.7),
        ],
    )
    edge(fascia, 0.042, 2)
    extrusion(
        "Drawn stainless reversible connector shell",
        [
            (-42.22, 9.04, 3.28, 1.45),
            (-42.08, 9.14, 3.47, 1.65),
            (-35.5, 9.14, 3.47, 1.65),
            (-35.5, 8.34, 2.54, 1.22),
            (-42.03, 8.34, 2.54, 1.22),
            (-42.22, 8.62, 2.82, 1.35),
        ],
        nickel,
    )
    plug("USB-C insulated rear stop", -35.54, -34.6, 8.43, 2.78, 1.32, polymer)
    edge(
        plug(
            "USB-C reversible contact blade", -41.08, -35.38, 6.43, 0.64, 0.28, polymer
        ),
        0.055,
        2,
    )
    for side in (-1, 1):
        edge(
            block(
                "Tongue mid-plate · exposed latch shoulder",
                -38.6,
                0,
                side * 3.205,
                2.18,
                0.26,
                0.22,
                0.09,
                nickel,
            ),
            0.055,
            3,
        )
    for i in range(12):
        for side in (-1, 1):
            nose = -40.48 if i in (0, 3, 8, 11) else -40.05
            heel = -35.50
            block(
                "Connector contact",
                (nose + heel) / 2,
                0.328 * side,
                (i - 5.5) * 0.5,
                heel - nose,
                0.035,
                0.21,
                0.08,
                contacts,
            )
    lens = finish(
        "Unpowered LED · smoked blue PMMA light guide", "444754", 0.02, 0.25, 0.18
    )
    plug("Flush activity light guide", -42.26, -38.4, 0.80, 0.80, 0.38, lens, -11.7)
    face_mark(ink)
    markings("Samsung Portable SSD", 16.4, -4.028, -20.83, 25.5, 2.05, ink, True)
    markings("T7", 33.35, -4.028, -20.77, 3.9, 2.40, ink, True)
    label = finish("Archival tape · warm ivory", "bdb9a6", 0, 0.81)
    block("Owner's archive strip", -22.5, -4.030, 13.2, 25, 0.055, 4.7, 0.2, label)
    markings(
        "ARCHIVE  /  SSD 01  /  2 TB", -22.5, -4.086, 13.2, 22.2, 1.32, polymer, True
    )


def board_artwork(copper, tin, mask):
    traces = []
    for x, z, length, spacing, lanes, slope in [
        (-35.2, -3.7, 12.8, 0.44, 9, -1),
        (-13.1, -6.7, 8.0, 0.28, 17, 1),
        (9.6, -9.2, 6.8, 0.30, 26, 1),
        (-6.9, 12.9, 12.2, 0.27, 15, -1),
    ]:
        for i in range(lanes):
            d = z + i * spacing
            bend = (1.45 + 0.08 * i) * slope
            line = [
                (x, d),
                (x + 1.78, d),
                (x + 1.78 + abs(bend), d + bend),
                (x + length, d + bend),
            ]
            points = [
                (u, -1.19, v + offset) for u, v in line for offset in (-0.055, 0.055)
            ]
            traces.append(
                mesh(
                    "Etched track",
                    points,
                    [(j, j + 1, j + 3, j + 2) for j in (0, 2, 4)],
                    mask,
                )
            )
    combine("Solder resist over signal fan-out · representative routing", traces)
    pads = []
    for x, z, nx, nz in [
        (-36, -14, 3, 6),
        (11, 12, 5, 5),
        (29, 7, 3, 7),
        (-12, 1.6, 5, 3),
    ]:
        for i in range(nx):
            for j in range(nz):
                cx, cz = x + i * 0.70, z + j * 0.81
                pads.append(
                    pin(
                        "Unpopulated land",
                        (cx, -1.20, cz),
                        (cx, -1.17, cz),
                        0.17,
                        copper,
                        12,
                    )
                )
    combine("Exposed test lands", pads)
    for x, z in [(-31, 10.1), (6, -18), (24, 14.5)]:
        edge(block("Power regulator", x, -0.75, z, 2.85, 0.90, 2.85, 0.12, tin), 0.065)


def end_retention(polymer, steel):
    for side, name, depth in ((-1, "I/O", 40.99), (1, "Label", 42.20)):
        start, end = sorted((side * (depth - 1.10), side * depth))
        cap = plug(
            f"{name} end · retaining crossmember", start, end, 54.9, 6.1, 2.9, polymer
        )
        reliefs = []
        if side < 0:
            reliefs.extend(
                [
                    plug(
                        "Socket clearance",
                        start - 0.1,
                        end + 0.1,
                        9.4,
                        3.65,
                        1.7,
                        polymer,
                    ),
                    plug(
                        "Lens clearance",
                        start - 0.1,
                        end + 0.1,
                        1.07,
                        1.07,
                        0.5,
                        polymer,
                        -11.7,
                    ),
                ]
            )
        for lateral in (-21.7, 21.7):

            def axis(d, outward=side, front=depth, centre=lateral):
                return outward * (front - d), 0, centre

            reliefs.append(
                pin("Fastener clearance", axis(-0.1), axis(1.2), 0.89, polymer)
            )
            reliefs.append(pin("Counterbore", axis(-0.1), axis(0.79), 1.65, polymer))
            boss = pin(
                f"{name} end · carrier mounting boss",
                axis(1.10),
                axis(4.38),
                1.63,
                polymer,
            )
            subtract(boss, [pin("Pilot bore", axis(0.99), axis(4.48), 0.69, polymer)])
            edge(
                block(
                    f"{name} end · moulded rail foot",
                    side * (depth - 2.66),
                    -1.63,
                    lateral * 1.061,
                    3.11,
                    1.75,
                    4.05,
                    0.45,
                    polymer,
                ),
                0.12,
            )
            head = pin(
                f"{name} end · concealed Phillips screw",
                axis(0.09),
                axis(0.77),
                1.50,
                steel,
                28,
            )
            for height, width in ((0.39, 1.73), (1.73, 0.39)):
                subtract(
                    head,
                    [
                        block(
                            "Cross recess",
                            side * (depth - 0.12),
                            0,
                            lateral,
                            0.59,
                            height,
                            width,
                            0.09,
                            steel,
                        )
                    ],
                )
            pin(f"{name} end · screw shank", axis(0.74), axis(4.04), 0.71, steel, 16)
        subtract(cap, reliefs)


def board_receptacle(pcb, polymer, metal, tin):
    guides = []
    for x in (-37.55, -35.33):
        for side in (-1, 1):
            z = side * 5.04
            guides.append(
                block(
                    "Shield stake clearance",
                    x,
                    -1.60,
                    z,
                    0.76,
                    1.12,
                    0.39,
                    0.10,
                    polymer,
                )
            )
            block(
                "Folded shield shoe",
                x,
                -0.89,
                side * 4.76,
                0.68,
                0.21,
                0.70,
                0.05,
                metal,
            )
            block("Shield anchoring stake", x, -1.55, z, 0.61, 1.46, 0.23, 0.06, metal)
            bead = block(
                "Shield stake · solder fillet", x, -2.03, z, 1.00, 0.17, 0.60, 0.18, tin
            )
            edge(bead, 0.055, 2)
    subtract(pcb, guides)
    for side in (-1, 1):
        for i in range(12):
            z = (i - 5.5) * 0.5
            heel = -32.94 if side > 0 else -33.98
            path = [
                (-35.55, side * 0.328),
                (-34.59, side * 0.328),
                (heel, -1.08),
                (heel + 0.51, -1.08),
            ]
            vs = [
                (x, h + dy, z + dz)
                for x, h in path
                for dy, dz in (
                    (-0.049, -0.095),
                    (0.049, -0.095),
                    (0.049, 0.095),
                    (-0.049, 0.095),
                )
            ]
            faces = [(3, 2, 1, 0), (12, 13, 14, 15)]
            faces.extend(
                (n + j, n + (j + 1) % 4, n + 4 + (j + 1) % 4, n + 4 + j)
                for n in (0, 4, 8)
                for j in range(4)
            )
            tail = mesh(
                f"USB-C {('A' if side > 0 else 'B')}{i + 1:02d} · formed terminal",
                vs,
                faces,
                metal,
            )
            tail["contactPitchMm"] = 0.5
            block(
                "USB-C signal land and solder toe",
                heel + 0.24,
                -1.159,
                z,
                0.79,
                0.082,
                0.27,
                0.055,
                tin,
            )


def carrier(polymer, contacts, steel):
    mask = finish("PWB solder mask", "343d36", 0.12, 0.48)
    ceramic = finish("MLCC ceramic", "ac9675", 0.08, 0.53)
    foil = finish("Encapsulated thermal spreader", "a5a6a0", 0.69, 0.41)
    pad = finish("Thermal interface elastomer", "738a8d", 0, 0.73)
    track = finish("Copper under green-black solder resist", "414c42", 0.18, 0.45)
    laser = finish("Epoxy laser marking", "999c97", 0.05, 0.55)
    pcb = block(
        "Portable SSD multilayer PCB", 0, -1.60, 0, 77.2, 0.80, 47.0, 1.65, mask
    )
    subtract(
        pcb,
        [
            block(
                "Mid-mount USB-C socket cutout",
                -38.9,
                -1.60,
                0,
                9.1,
                2.8,
                9.3,
                0.28,
                mask,
            )
        ],
    )
    mounts = [(x, z) for x in (-34, 34) for z in (-19.8, 19.8)]
    subtract(
        pcb,
        [
            pin("Carrier fixing bore", (x, -2.3, z), (x, -0.9, z), 1.08, mask)
            for x, z in mounts
        ],
    )
    for x, z in mounts:
        washer = pin(
            "Plated mounting annulus", (x, -1.21, z), (x, -1.175, z), 2.06, contacts
        )
        subtract(
            washer, [pin("Plating bore", (x, -1.4, z), (x, -1.0, z), 1.08, contacts)]
        )
        pin("Carrier threaded boss", (x, -3.27, z), (x, -2.02, z), 1.8, polymer)
        pin("Fastener shank", (x, -3.0, z), (x, -0.80, z), 0.95, steel)
        head = pin(
            "Recessed cross-head fastener", (x, -1.20, z), (x, -0.42, z), 1.66, steel
        )
        cut = block("Cross tip", x, -0.44, z, 1.77, 0.48, 0.41, 0.10, steel)
        subtract(head, [cut])
        subtract(head, [block("Cross tip", x, -0.44, z, 0.40, 0.48, 1.75, 0.10, steel)])
    for side in (-1, 1):
        edge(
            block(
                "Injection-moulded carrier slide",
                0,
                -2.49,
                side * 24.4,
                79.4,
                1.50,
                1.6,
                0.53,
                polymer,
            ),
            0.18,
        )
    board_artwork(contacts, polymer, track)
    for name, brand, kind, x, z, w, d, height in [
        ("ASMedia ASM2362 USB bridge", "asmedia", "ASM2362", -18, -4.2, 9.9, 9.9, 1.10),
        (
            "Samsung Pablo NVMe controller",
            "SAMSUNG",
            "S4LR033",
            2,
            -4.3,
            15.6,
            15.6,
            1.24,
        ),
        (
            "Samsung V-NAND · storage package A",
            "SAMSUNG",
            "V-NAND",
            24,
            -3.65,
            16.1,
            18.4,
            1.16,
        ),
        (
            "Samsung V-NAND · storage package B",
            "SAMSUNG",
            "V-NAND",
            -14.6,
            13.7,
            17.2,
            13.8,
            1.16,
        ),
    ]:
        edge(block(name, x, -1.2 + height / 2, z, w, height, d, 0.25, polymer), 0.11)
        markings(brand, x, -1.185 + height, z - 0.61, w * 0.48, 0.87, laser)
        markings(kind, x, -1.185 + height, z + 0.78, w * 0.42, 0.59, laser)
        pin(
            "Pin-one laser dot",
            (x - w * 0.39, -1.2 + height, z - d * 0.39),
            (x - w * 0.39, -1.184 + height, z - d * 0.39),
            0.21,
            laser,
            12,
        )
        block(
            name + " · thermal pad",
            x,
            -1.2 + height + 0.32,
            z,
            w - 0.65,
            0.64,
            d - 0.65,
            0.3,
            pad,
        )
    for x, z, nx, nz in [
        (-26, -15, 8, 3),
        (-28, 7, 4, 7),
        (-7, -18, 9, 2),
        (4, 11, 4, 4),
        (18, 11, 8, 2),
    ]:
        for j in range(nz):
            for i in range(nx):
                cx, cz = x + i * 1.45, z + j * 1.24
                block(
                    "SMD decoupling capacitor",
                    cx,
                    -0.99,
                    cz,
                    0.89,
                    0.42,
                    0.50,
                    0.05,
                    ceramic,
                )
                for sign in (-1, 1):
                    block(
                        "MLCC termination",
                        cx + sign * 0.37,
                        -1.00,
                        cz,
                        0.19,
                        0.43,
                        0.52,
                        0.03,
                        steel,
                    )
    block("LED package", -38.7, -1.0, -11.7, 2, 0.42, 1.1, 0.1, ceramic)
    solder = finish("Lead-free solder meniscus", "a6a5a1", 0.87, 0.29)
    board_receptacle(pcb, polymer, steel, solder)
    end_retention(polymer, steel)
    block("Thermal envelope · foil lid", 0, 2.72, 0, 74.5, 0.24, 45.3, 1.35, foil)
    block("Thermal envelope · lower sheet", 0, -2.75, 0, 72.5, 0.27, 44.0, 1.3, foil)
    block(
        "Phase change buffer below upper foil",
        1.35,
        1.72,
        0,
        69.8,
        1.78,
        43.0,
        1.4,
        pad,
    )


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    atelier.mkdir(parents=True, exist_ok=True)
    cap = finish("End closure · satin pewter polymer", "75757b", 0.27, 0.40)
    steel = finish("Stamped nickel-plated steel", "98989a", 0.87, 0.30)
    black = finish("Connector insert · charcoal LCP", "1a1b20", 0.01, 0.51)
    gold = finish("Connector contact plating", "c9a15b", 0.77, 0.31)
    ink = finish("Light grey factory screen ink", "c7c6c7", 0.13, 0.44)
    enclosure(anodized_finish(), cap, steel, black, gold, ink)
    exterior = list(bpy.context.scene.objects)
    carrier(black, gold, steel)
    scene = bpy.context.scene
    complete = bpy.data.collections.new("Samsung T7 · complete drive")
    scene.collection.children.link(complete)
    groups = {}
    for group_name in ("Exterior", "Internal layout"):
        group = bpy.data.collections.new(f"Samsung T7 · {group_name}")
        complete.children.link(group)
        groups[group_name] = group
    for part in list(scene.objects):
        part["assembly"] = "Samsung Portable SSD T7 2 TB · MU-PC2T0T"
        part["partGroup"] = "Exterior" if part in exterior else "Internal layout"
        part["studioOccluder"] = False
        owners = list(part.users_collection)
        groups[part["partGroup"]].objects.link(part)
        for owner in owners:
            owner.objects.unlink(part)
    bpy.context.preferences.filepaths.save_version = 0
    native = (
        project
        / ".references/04-桌面设备/存储与充电/Samsung Portable SSD T7/Blender/samsung-t7-2tb.blend"
    )
    native.parent.mkdir(parents=True, exist_ok=True)
    assembly_path = atelier / native.name
    share_native = not assembly_path.exists() or (
        native.exists() and assembly_path.samefile(native)
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(native), compress=True)
    if share_native and (
        not assembly_path.exists() or not assembly_path.samefile(native)
    ):
        temporary_link = assembly_path.with_suffix(".link")
        temporary_link.hardlink_to(native)
        os.replace(temporary_link, assembly_path)
    bpy.ops.object.select_all(action="DESELECT")
    shell = combine("Samsung T7 2 TB · Titan Gray", exterior)
    shell.select_set(True)
    path = project / "public/media/models/samsung-t7.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        use_selection=True,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(assets / "pack-product-geometry.mjs"), str(path)], check=True
    )


if __name__ == "__main__":
    build()
