import argparse
import json
import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
import bmesh

assets = Path(__file__).resolve().parent
root = assets.parents[1]
sys.path.insert(0, str(assets))
from product_solids import block, combine, edge, mesh, pin, vertex

finish = runpy.run_path(str(assets / "vitrine-sculpt.py"))["finish"]
board_mid = 11.54
surface = board_mid + 0.5


def label(text, x, y, z, size, ink, angle=0, underside=False):
    data = bpy.data.curves.new(text, "FONT")
    data.body = text
    data.size = size * 0.001
    data.align_x = data.align_y = "CENTER"
    data.resolution_u = 3
    obj = bpy.data.objects.new(text, data)
    bpy.context.collection.objects.link(obj)
    obj.location = vertex(x, y, z)
    obj.rotation_euler = (math.pi if underside else 0, 0, math.radians(angle))
    data.materials.append(ink)
    deps = bpy.context.evaluated_depsgraph_get()
    new_mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    matrix = obj.matrix_world.copy()
    bpy.data.objects.remove(obj, do_unlink=True)
    obj = bpy.data.objects.new(text, new_mesh)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world = matrix
    return obj


def passive(name, x, z, w, d, height, mat, metal):
    body = block(name, x, surface + height / 2, z, w, height, d, 0.09, mat)
    tabs = []
    for sign in (-1, 1):
        dx, dz = (sign * (w * 0.405), 0) if w > d else (0, sign * (d * 0.405))
        tabs.append(
            block(
                "Solder termination",
                x + dx,
                surface + height * 0.49,
                z + dz,
                w * 0.21 if dx else w * 1.02,
                height * 0.99,
                d * 0.21 if dz else d * 1.02,
                0.04,
                metal,
            )
        )
    return combine(name, [body, *tabs])


def leadless_chip(
    name, x, z, w, d, height, count, spacing, mat, metal, four_sides=False
):
    case = edge(
        block(name, x, surface + height / 2, z, w, height, d, 0.14, mat), 0.055, 2
    )
    case["perimeterPins"] = count * (4 if four_sides else 2)
    pins = []
    for i in range(count):
        a = (i - (count - 1) / 2) * spacing
        for sign in (-1, 1):
            pads = [(x + sign * w / 2, z + a, 0.24, spacing * 0.52)]
            if four_sides:
                pads.append((x + a, z + sign * d / 2, spacing * 0.52, 0.24))
            for px, pz, width, depth in pads:
                pins.append(
                    block(
                        "Exposed package pad",
                        px,
                        surface + 0.075,
                        pz,
                        width,
                        0.15,
                        depth,
                        0.04,
                        metal,
                    )
                )
    pins.append(
        block(
            "Underside thermal land",
            x,
            surface + 0.018,
            z,
            w * 0.58,
            0.04,
            d * 0.58,
            0.12,
            metal,
        )
    )
    combine(name + " · lead frame", pins)
    return case


def usb(m):
    hood = [
        (-2.86, 0.04),
        (2.86, 0.04),
        (3.78, 0.87),
        (3.78, 2.34),
        (3.58, 2.52),
        (-3.58, 2.52),
        (-3.78, 2.34),
        (-3.78, 0.87),
    ]
    vertices, faces = [], []
    for z, dx, dy in [(-26.8, 1.05, 1.07), (-26.15, 1, 1), (-21.2, 1, 1)]:
        for inset in [0, 0.19]:
            for x, y in hood:
                vertices.append(
                    (
                        x * dx - math.copysign(inset, x),
                        surface
                        + 1.25
                        + (y - 1.25) * dy
                        - math.copysign(inset, y - 1.25),
                        z,
                    )
                )
    n = len(hood)
    for a, b in [(0, 8), (8, 24), (24, 40), (40, 32), (32, 16), (16, 0)]:
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    shield = mesh(
        "J1 · folded micro-B shield and flared mouth", vertices, faces, m["tin"]
    )
    from product_solids import subtract

    subtract(
        shield,
        [
            block("Stamped window", x, surface + 2.52, z, w, 1.0, d, 0.13, m["tin"])
            for x, z, w, d in [
                (-2.42, -24.65, 0.87, 1.65),
                (2.42, -24.65, 0.87, 1.65),
                (-2.18, -21.94, 1.54, 0.68),
                (0, -21.71, 1.46, 0.44),
                (2.18, -21.94, 1.54, 0.68),
            ]
        ],
    )
    for x in (-2.42, 2.42):
        block(
            "J1 · retaining lance",
            x,
            surface + 2.32,
            -24.57,
            0.57,
            0.16,
            1.42,
            0.10,
            m["tin"],
        )
    for x in (-2.82, 2.82):
        edge(
            block(
                "J1 · soldered shield foot",
                x,
                surface + 0.18,
                -20.95,
                1.41,
                0.36,
                1.08,
                0.14,
                m["tin"],
            ),
            0.07,
        )
    block(
        "J1 · connector rear insulator",
        0,
        surface + 1.29,
        -21.62,
        6.92,
        2.05,
        0.7,
        0.26,
        m["black"],
    )
    block(
        "J1 · contact tongue",
        0,
        surface + 1.05,
        -23.74,
        5.1,
        0.39,
        4.28,
        0.15,
        m["black"],
    )
    for i in range(5):
        x = (i - 2) * 0.65
        block(
            "J1 · contact spring",
            x,
            surface + 1.28,
            -23.82,
            0.24,
            0.095,
            3.78,
            0.07,
            m["gold"],
        )
        block(
            "J1 · solder tail",
            x,
            surface + 0.11,
            -20.88,
            0.35,
            0.22,
            1.02,
            0.06,
            m["tin"],
        )


def components(m):
    leadless_chip(
        "U1 · RP2040 QFN-56",
        0,
        0.5,
        7,
        7,
        0.9,
        14,
        0.4,
        m["black"],
        m["tin"],
        four_sides=True,
    )
    pin(
        "U1 · pin one index",
        (-2.78, surface + 0.90, -2.26),
        (-2.78, surface + 0.912, -2.26),
        0.22,
        m["mark"],
        20,
    )
    for text, z in [("RP2-B0  20/21", 1.38), ("P64M15.00 TTT", 2.26)]:
        label(text, 0, surface + 0.913, z, 0.62, m["mark"])
    leadless_chip(
        "U3 · W25Q16JVUXIQ USON-8", -3.8, -6.4, 2, 3, 0.6, 4, 0.50, m["black"], m["tin"]
    )
    leadless_chip(
        "U2 · RT6150B WDFN-10",
        2.9,
        -14.6,
        2.5,
        2.5,
        0.75,
        5,
        0.50,
        m["black"],
        m["tin"],
    )
    ceramic = block(
        "X1 · ceramic package",
        -2.3,
        surface + 0.18,
        9.05,
        3.2,
        0.36,
        2.5,
        0.16,
        m["black"],
    )
    lid = edge(
        block(
            "X1 · seam welded lid",
            -2.3,
            surface + 0.46,
            9.05,
            2.96,
            0.28,
            2.23,
            0.22,
            m["crystal"],
        ),
        0.045,
    )
    lands = [
        block(
            "X1 · wraparound land",
            -2.3 + sx * 1.24,
            surface + 0.11,
            9.05 + sz * 0.99,
            0.75,
            0.22,
            0.56,
            0.07,
            m["gold"],
        )
        for sx in (-1, 1)
        for sz in (-1, 1)
    ]
    combine("X1 · 12 MHz quartz package", [ceramic, lid, *lands])
    label("12.000", -2.3, surface + 0.614, 9.05, 0.51, m["mark"])
    passive("D1 · Schottky diode", 6, -18.9, 1.66, 3.6, 0.95, m["black"], m["tin"])
    passive("L1 · shielded inductor", 6, -14.6, 2, 2.5, 1.2, m["ferrite"], m["ferrite"])
    passive("D2 · green LED", -5.7, -20.7, 1.6, 0.8, 0.6, m["lens"], m["tin"])
    fet = block(
        "Q1 · transistor body",
        6.4,
        surface + 0.44,
        -7.2,
        1.6,
        0.68,
        0.8,
        0.09,
        m["black"],
    )
    leads = [
        block(
            "Q1 · formed terminal",
            6.4 + dx,
            surface + 0.11,
            -7.2 + dz,
            0.26,
            0.22,
            0.52,
            0.045,
            m["tin"],
        )
        for dx, dz in [(-0.50, -0.43), (0.50, -0.43), (0, 0.43)]
    ]
    combine("Q1 · DMG1012T SOT-523", [fet, *leads])
    for z in (-17.1, -12.1):
        passive(
            "Input/output ceramic capacitor",
            2.9,
            z,
            2,
            1.26,
            1.25,
            m["ceramic"],
            m["tin"],
        )
    locations = [
        ("R8", -2.7, -18.8),
        ("R3", -2.7, -17.8),
        ("R2", 3.5, -18.6),
        ("C15", -4.5, -8.85),
        ("R7", 4.35, -9.32),
        ("C3", 5.95, -9.4),
        ("R5", 6.85, -9.4),
        ("R11", -5.55, -7.36),
        ("R4", -5.55, -5.44),
        ("C11", -0.84, -4.59),
        ("C10", -0.04, -4.59),
        ("C8", 0.65, 5.43),
        ("C9", -0.11, 5.43),
        ("C12", 1.35, -4.59),
        ("C14", 2.14, -4.59),
        ("C13", 4.65, -4.59),
        ("R9", 5.56, -4.59),
        ("R6", 6.37, -4.59),
        ("C7", 4.42, -1.72),
        ("R10", 6.08, -0.15),
        ("R1", 6.08, 0.84),
        ("C6", 4.59, 1.98),
        ("C18", -4.69, -3.12),
        ("C4", -4.69, -2.1),
        ("C5", -4.58, 1.5),
        ("R15", -1.82, 6.2),
        ("R14", -1.14, 7.1),
        ("C16", -4.55, 9.4),
        ("C17", 0.04, 8.47),
    ]
    vertical = {
        "R7",
        "R11",
        "R4",
        "C11",
        "C10",
        "C12",
        "C14",
        "C13",
        "R9",
        "R6",
        "C8",
        "C9",
        "C17",
        "C16",
    }
    for ref, x, z in locations:
        w, d = (0.52, 1.02) if ref in vertical else (1.02, 0.52)
        passive(
            ref,
            x,
            z,
            w,
            d,
            0.39,
            m["ceramic" if ref.startswith("C") else "black"],
            m["tin"],
        )
    block(
        "SW1 · BOOTSEL moulded body",
        -3.5,
        surface + 0.61,
        -13.5,
        3.2,
        1.22,
        4.26,
        0.25,
        m["black"],
    )
    for sign in (-1, 1):
        block(
            "SW1 · cover strap",
            -3.5 + sign * 1.2,
            surface + 1.26,
            -13.5,
            0.65,
            0.22,
            3.98,
            0.16,
            m["tin"],
        )
    edge(
        block(
            "SW1 · oval actuator",
            -3.5,
            surface + 1.88,
            -13.5,
            2.08,
            1.24,
            2.75,
            1.0,
            m["abs"],
        ),
        0.12,
    )
    usb(m)


def printed_logo(name, x, h, z, size, contours, ink, underside=False):
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt

    points, edges = [], []
    for loop in contours:
        start = len(points)
        points.extend(Vector(p) for p in loop)
        edges.extend((start + i, start + (i + 1) % len(loop)) for i in range(len(loop)))
    vertices, _, triangles, *_ = delaunay_2d_cdt(points, edges, [], 0, 1e-8)
    segments = [(loop[i - 1], p) for loop in contours for i, p in enumerate(loop)]
    faces = []
    for triangle in triangles:
        u, v = sum((vertices[i] for i in triangle), Vector((0, 0))) / 3
        crossings = sum(
            1
            for (ax, ay), (bx, by) in segments
            if (ay > v) != (by > v) and u < (bx - ax) * (v - ay) / (by - ay) + ax
        )
        if crossings % 2:
            faces.append(tuple(triangle) if underside else tuple(reversed(triangle)))
    return mesh(
        name, [(x + u * size, h, z + v * size) for u, v in vertices], faces, ink
    )


def markings(m, contours):
    for x, z in [(-5.95, -17.9), (6.03, 19.65)]:
        pin(
            "Solder mask clearance",
            (x, surface + 0.006, z),
            (x, surface + 0.018, z),
            0.88,
            m["copper"],
            40,
        )
        pin(
            "Optical alignment fiducial",
            (x, surface + 0.017, z),
            (x, surface + 0.031, z),
            0.50,
            m["gold"],
            40,
        )
    silks = [
        ("Raspberry Pi Pico", -6.40, 12.34, 1.82, 90),
        ("© 2020", -6.40, 2.32, 1.82, 90),
        ("BOOTSEL", -6.27, -13.31, 1.52, 90),
        ("LED", -5.72, -19.49, 1.05, 0),
        ("USB", 0, -19.53, 1.1, 0),
        ("DEBUG", 0, 22.62, 1.14, 0),
        ("1", -7.97, -24.05, 0.71, 0),
    ]
    for text, x, z, s, a in silks:
        label(text, x, surface + 0.017, z, s, m["silk"], a)
    mesh(
        "DEBUG header index",
        [
            (x, surface + 0.017, z)
            for x, z in [(-2.96, 21.85), (-2.54, 22.33), (-2.12, 21.85)]
        ],
        [(0, 1, 2)],
        m["silk"],
    )
    printed_logo(
        "Pico · screen-printed raspberry",
        0,
        surface + 0.018,
        16,
        9,
        contours["raspberry"],
        m["silk"],
    )
    printed_logo(
        "U1 · laser-etched raspberry",
        0,
        surface + 0.912,
        -0.72,
        2.55,
        contours["raspberry"],
        m["mark"],
    )
    backside = board_mid - 0.515
    left = "GP0 GP1 GND GP2 GP3 GP4 GP5 GND GP6 GP7 GP8 GP9 GND GP10 GP11 GP12 GP13 GND GP14 GP15".split()
    right = "VBUS VSYS GND 3V3_EN 3V3 ADC_VREF GP28_A2 AGND GP27_A1 GP26_A0 RUN GP22 GND GP21 GP20 GP19 GP18 GND GP17 GP16".split()
    rail_labels = [
        -20.91,
        -19.74,
        -18.23,
        -16.30,
        -13.82,
        -11.40,
        -8.82,
        -6.69,
        -3.19,
        -1.00,
        1.49,
        3.98,
        6.63,
        9.02,
        11.59,
        13.98,
        16.47,
        18.56,
        20.04,
        21.13,
    ]
    for sign, row in [(-1, left), (1, right)]:
        for z, text in zip(rail_labels, row, strict=True):
            label(
                text,
                sign * (5.95 - len(text) * 0.12),
                backside,
                z,
                0.99,
                m["silk"],
                180,
                True,
            )
    for name, paths in contours["reverse"].items():
        printed_logo(
            f"Pico · underside {name}",
            0,
            backside,
            0,
            1,
            paths,
            m["silk"],
            underside=True,
        )
    for text, z, s in [
        ("94V-0 H", -6.2, 0.98),
        ("OC-136", -7.55, 1.02),
    ]:
        label(text, 0, backside, z, s, m["silk"], 180, True)
    for x, text in [(-2.54, "SWCLK"), (0, "GND"), (2.54, "SWDIO")]:
        label(text, x, backside, 21.64, 0.78, m["silk"], -90, True)
    for i, (x, z) in enumerate(
        [
            (0, -21.2),
            (-1.02, -23.94),
            (0.99, -23.94),
            (2.53, -17.6),
            (2.53, -15.16),
            (2.53, -12.72),
        ]
    ):
        block(
            f"TP{i + 1} · exposed test land",
            -x,
            backside - 0.012,
            z,
            1.36,
            0.022,
            1.45,
            0.3,
            m["gold"],
        )
        label(
            f"TP{i + 1}",
            -x + (1.82 if i >= 3 else 0),
            backside,
            z + (1.3 if i < 3 else 0.02),
            0.82,
            m["silk"],
            180,
            True,
        )


def headers(m):
    for side in (-1, 1):
        x = side * 8.89
        for i in range(20):
            z = (i - 9.5) * 2.54
            block(
                "Header · chamfered spacer cell",
                x,
                9.77,
                z,
                2.48,
                2.54,
                2.51,
                0.26,
                m["black"],
            )
            block(
                f"Header pin {i + 1 if side < 0 else 40 - i}",
                x,
                8.55,
                z,
                0.64,
                8.2,
                0.64,
                0.035,
                m["tin"],
            )
            levels = [
                (0.65, surface + 0.01),
                (0.57, surface + 0.12),
                (0.42, surface + 0.28),
                (0.33, surface + 0.39),
            ]
            pts = [
                (
                    x + r * math.cos(j * math.tau / 16),
                    h,
                    z + r * math.sin(j * math.tau / 16),
                )
                for r, h in levels
                for j in range(16)
            ]
            faces = [
                (
                    k * 16 + j,
                    (k + 1) * 16 + j,
                    (k + 1) * 16 + (j + 1) % 16,
                    k * 16 + (j + 1) % 16,
                )
                for k in range(3)
                for j in range(16)
            ]
            mesh("Wetted solder fillet", pts, faces, m["tin"])


def main():
    parser = argparse.ArgumentParser()
    folder = root / ".review/atelier/pico"
    parser.add_argument("--laminate", type=Path, default=folder / "pico-laminate.json")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    m = {
        key: finish(key + " · " + name, col, metal, rough)
        for key, name, col, metal, rough in [
            ("mask", "solder resist", "15764d", 0.09, 0.40),
            ("copper", "buried traces", "286e49", 0.15, 0.4),
            ("gold", "ENIG finish", "d6ac57", 0.69, 0.31),
            ("fr4", "exposed woven laminate", "959472", 0, 0.77),
            ("tin", "solder and plated shield", "c1c3c0", 0.85, 0.32),
            ("black", "transfer moulding", "222526", 0.04, 0.72),
            ("silk", "white PCB marking", "e6ebe1", 0.01, 0.67),
            ("mark", "etched marking", "95948a", 0.16, 0.67),
            ("crystal", "quartz lid", "aeaca3", 0.75, 0.39),
            ("ceramic", "barium titanate", "a89168", 0.22, 0.56),
            ("lens", "indicator lens", "bed594", 0.06, 0.33),
            ("ferrite", "ferrite", "45494a", 0.18, 0.77),
            ("abs", "warm white ABS", "e8e7e0", 0, 0.59),
            ("ink", "charcoal print", "434345", 0, 0.66),
            ("red", "positive rail marking", "b73838", 0, 0.65),
            ("contact", "nickel plated spring bronze", "b4a99b", 0.84, 0.37),
            ("foam", "adhesive backing", "cecdc2", 0, 0.86),
        ]
    }
    runpy.run_path(str(assets / "busboard-bb400.py"))["build"](m, label)
    base = list(bpy.context.scene.objects)
    data = json.loads(args.laminate.read_text())
    board = mesh(
        "R3a · castellated laminate and finished lands",
        [(x - 10.5, y + board_mid, z + 25.5) for x, y, z in data["vertices"]],
        data["triangles"],
        m["mask"],
    )
    board.data.materials.append(m["gold"])
    board.data.materials.append(m["fr4"])
    board.data.polygons.foreach_set("material_index", data["finishes"])
    runpy.run_path(str(assets / "pico-resist.py"))["apply_resist"](
        board, m["mask"], data["resist"]
    )
    components(m)
    markings(m, data["printed_mark"])
    headers(m)
    base_set = set(base)
    top = [obj for obj in bpy.context.scene.objects if obj not in base_set]
    for objs, name in [(base, "BB400"), (top, "Pico R3")]:
        for obj in objs:
            obj["assembly"] = name
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    folder.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(folder / "pico-bench.blend"), compress=True
    )
    for obj in [
        combine("BusBoard BB400 · sprung terminal banks", base),
        combine("Raspberry Pi Pico R3 · board and populated headers", top),
    ]:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0000002)
        bmesh.ops.dissolve_limit(
            bm,
            angle_limit=math.radians(0.30),
            verts=list(bm.verts),
            edges=list(bm.edges),
            delimit={"MATERIAL"},
        )
        bm.to_mesh(obj.data)
        bm.free()
    path = folder / "pico-bench.glb"
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
    main()
