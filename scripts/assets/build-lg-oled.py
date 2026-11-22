import argparse
import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np

assets = Path(__file__).resolve().parent
root = assets.parents[1]
sys.path.insert(0, str(assets))
from product_solids import (
    block,
    combine,
    corners,
    edge,
    engraving,
    frame,
    front_plate,
    mesh,
    outline,
    pin,
    placed,
    subtract,
)

finish = runpy.run_path(str(assets / "vitrine-sculpt.py"))["finish"]


def brushed_finish():
    mat = finish("Cabinet · graphite horizontal hairline", "383a3b", 0.39, 0.39)
    rng = np.random.default_rng(486)
    size = 128
    base = rng.normal(0.43, 0.07, (size, 1)) + rng.normal(0, 0.014, (size, size))
    px = np.ones((size, size, 4), np.float32)
    px[:, :, :3] = base[:, :, None]
    im = bpy.data.images.new(
        "Rolled graphite · directional roughness", size, size, alpha=False
    )
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(px.ravel())
    im.pack()
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = im
    mat.node_tree.links.new(
        node.outputs["Color"],
        mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"],
    )
    return mat


def rings(name, levels, material, cap=True):
    vertices = [
        (x, h + y, z)
        for w, height, h, z, r in levels
        for x, y in corners(w, height, r, 8)
    ]
    n = len(vertices) // len(levels)
    faces = [
        (a + i, a + (i + 1) % n, a + n + (i + 1) % n, a + n + i)
        for a in range(0, len(vertices) - n, n)
        for i in range(n)
    ]
    if cap:
        faces += [
            tuple(reversed(range(n))),
            tuple(range(len(vertices) - n, len(vertices))),
        ]
    return mesh(name, vertices, faces, material)


def texture_coordinates(obj):
    uv = obj.data.uv_layers.new(name="Brushed grain")
    for loop in obj.data.loops:
        v = obj.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (v.x * 4 + v.y, v.z * 32)


def pocket(name, x, h, z, w, height, depth, r, thick, mat):
    outer = front_plate(name, x, h, z + depth / 2, w, height, depth, r, mat)
    inner = front_plate(
        "Recess former",
        x,
        h,
        z + depth / 2 - 1,
        w - 2 * thick,
        height - 2 * thick,
        depth + 2 - 2 * thick,
        max(0.15, r - thick),
        mat,
    )
    subtract(outer, [inner])
    return outer


def lattice(name, columns, rows, pitch_x, pitch_y, opening_x, opening_y, depth, mat):
    verts, faces, shared = [], [], {}

    def index(x, h, d):
        key = round(x, 4), round(h, 4), d
        if key not in shared:
            shared[key] = len(verts)
            verts.append(key)
        return shared[key]

    for column in range(columns):
        for row in range(rows):
            cx = (column - (columns - 1) / 2) * pitch_x
            cy = (row - (rows - 1) / 2) * pitch_y
            rings = []
            for level in (0, -depth):
                for w, height in [(pitch_x, pitch_y), (opening_x, opening_y)]:
                    rings.append(
                        [
                            index(cx + sx * w / 2, cy + sy * height / 2, level)
                            for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
                        ]
                    )
            outer, inner, back, inside = rings
            for i in range(4):
                j = (i + 1) % 4
                faces.extend(
                    [
                        (outer[i], outer[j], inner[j], inner[i]),
                        (inner[i], inner[j], inside[j], inside[i]),
                        (back[j], back[i], inside[i], inside[j]),
                    ]
                )
                if (
                    (i == 0 and row == 0)
                    or (i == 1 and column == columns - 1)
                    or (i == 2 and row == rows - 1)
                    or (i == 3 and column == 0)
                ):
                    faces.append((outer[j], outer[i], back[i], back[j]))
    return mesh(name, verts, faces, mat)


class Television:
    def __init__(self):
        self.brushed = brushed_finish()
        self.frame = finish("Panel · anodized edge", "414347", 0.73, 0.32)
        self.back = finish("Panel · anti-glare graphite backing", "303235", 0.24, 0.47)
        self.glass = finish("Panel · inactive black border", "0b0c0f", 0.12, 0.17, 0.61)
        self.black = finish("Cabinet · moulded graphite ABS", "292b2c", 0.06, 0.48)
        self.rubber = finish("Socket wells · black elastomer", "131516", 0.02, 0.67)
        self.nickel = finish("I/O · matte tin-plated shield", "969a97", 0.83, 0.31)
        self.fastener = finish("Cabinet · dark zinc fasteners", "4a4b49", 0.77, 0.32)
        self.ink = finish("Cabinet · warm grey pad print", "b5b6b1", 0.08, 0.52)
        self.gold = finish("I/O · connector contacts", "bf9760", 0.75, 0.36)

    def panel(self):
        active_width = 48 * 25.4 * 16 / math.hypot(16, 9)
        active_height = active_width * 9 / 16
        glass_edge = (1067.7, 614.7, 0.5, 2.80, 3.0)
        seal_edge = (1068.7, 615.65, 0.45, 2.65, 3.2)
        rings(
            "OLED module · perimeter and rolled metal edge",
            [
                (1068.4, 614.3, 0.8, -4.4, 4.4),
                (1070.4, 616.8, 0.5, -3.7, 4.2),
                (1071, 617.2, 1.4, 1.0, 4.2),
                (1070.4, 616.7, 1.4, 2.55, 4.1),
                seal_edge,
            ],
            self.frame,
            cap=False,
        )
        front_plate(
            "OLED module · upper rear sheet",
            0,
            1,
            -4.55,
            1068.3,
            614.5,
            0.55,
            3.7,
            self.back,
        )
        rings(
            "OLED module · edge seal",
            [seal_edge, glass_edge],
            self.rubber,
            cap=False,
        )
        rings(
            "OLED module · black glass and masking border",
            [glass_edge, (active_width, active_height, 0, 3.00, 0)],
            self.glass,
            cap=False,
        )
        active = mesh(
            "OLED module · active display surface",
            [(x * active_width / 2, y * active_height / 2, 3.00)
             for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
            [(0, 1, 2, 3)], self.glass,
        )
        active["runtimeDisplaySurface"] = True
        front_plate(
            "IR window · smoke polycarbonate",
            0,
            -306.9,
            0.1,
            44,
            6.2,
            4.9,
            2.2,
            self.glass,
        )
        front_plate(
            "Power switch · silicone dome",
            0,
            -308.8,
            -0.85,
            8.2,
            2.4,
            4.2,
            0.9,
            self.rubber,
        )

    def rear(self):
        shell = rings(
            "Rear cover · one-piece removable moulding",
            [
                (1026.4, 362.7, -120.95, -44.1, 5),
                (1032, 367, -121, -43.5, 6),
                (1048, 372.2, -120.8, -36.8, 6),
                (1061, 373.6, -120.2, -10, 5),
                (1062.2, 373.8, -120.1, -4.7, 4.8),
                (1059.5, 371.0, -120.1, -4.7, 3.7),
                (1058.4, 370.8, -120.2, -10, 3.9),
                (1045, 369.4, -120.8, -36.1, 4),
                (1030.5, 364.3, -121, -42.0, 4.7),
                (1025.2, 360.6, -120.95, -42.45, 4),
            ],
            self.brushed,
        )
        cuts = [
            front_plate("Exhaust opening", 89, -95, -45, 496, 35, 14, 0.8, self.black),
            front_plate("I/O opening", -342, -121, -45, 201, 78, 17, 2.4, self.black),
            front_plate(
                "AC hatch opening", 449, -155, -45, 95, 73, 17, 2.0, self.black
            ),
            front_plate(
                "Pedestal dock opening", 0, -272, -45, 246, 94, 16, 3, self.black
            ),
            front_plate("Side I/O notch", -516, -56, -42, 144, 219, 56, 2, self.black),
        ]
        for x in (-150, 150):
            for h in (-150, 50):
                cuts.append(
                    pin("M6 boss hole", (x, h, -49), (x, h, -40), 4.7, self.black, 28)
                )
        subtract(shell, cuts)
        subtract(
            shell,
            [
                front_plate(
                    "Identification label relief",
                    -351,
                    -45,
                    -44.2,
                    124.2,
                    46.2,
                    0.7,
                    1.5,
                    self.black,
                )
            ],
        )
        for sx in (-1, 1):
            subtract(
                shell,
                [
                    block(
                        "Bottom audio aperture",
                        sx * 343,
                        -307,
                        -24,
                        184,
                        11,
                        15,
                        1.2,
                        self.black,
                    )
                ],
            )
            vents = lattice(
                "Down-firing speaker grille", 46, 3, 4, 5, 2.9, 3.5, 1.45, self.black
            )
            placed(
                vents, frame((sx * 343, -306.2, -24), (1, 0, 0), (0, 0, 1), (0, -1, 0))
            )
        texture_coordinates(shell)
        vent = lattice(
            "Rear cabinet · punched rectangular exhaust",
            80,
            5,
            6.2,
            7,
            4.25,
            4.95,
            1.7,
            self.brushed,
        )
        texture_coordinates(vent)
        placed(vent, frame((89, -95, -44.08), (-1, 0, 0), (0, 1, 0), (0, 0, -1)))
        for sx in (-1, 1):
            for h in (-150, 50):
                boss = pin(
                    "VESA · captive M6 insert",
                    (sx * 150, h, -44),
                    (sx * 150, h, -34),
                    4.65,
                    self.nickel,
                    32,
                )
                subtract(
                    boss,
                    [
                        pin(
                            "M6 bore",
                            (sx * 150, h, -45),
                            (sx * 150, h, -33),
                            2.6,
                            self.black,
                            32,
                        )
                    ],
                )
        pocket(
            "Unoccupied factory pedestal docking recess",
            0,
            -262,
            -44,
            248,
            74,
            9,
            3.5,
            1.4,
            self.black,
        )
        for x in (-105, 105):
            for h in (-236, -285):
                self.screw(x, h, -36.8)
        door = front_plate(
            "Power entry · removable strain-relief hatch",
            449,
            -155,
            -43.05,
            94.1,
            72.1,
            1.8,
            2.1,
            self.black,
        )
        subtract(
            door,
            [
                pin(
                    "Power exit bore",
                    (421, -179, -46),
                    (421, -179, -40),
                    6.4,
                    self.rubber,
                )
            ],
        )
        pin(
            "Unwired AC cable gland",
            (421, -179, -43.8),
            (421, -179, -36.8),
            5.95,
            self.rubber,
        )
        self.screw(462, -170, -44.0)
        self.label("AC IN", 443, -148, -44.02, 4.6)
        front_plate(
            "Rear product information carrier",
            -351,
            -45,
            -43.96,
            124,
            46,
            0.17,
            1.4,
            self.rubber,
        )
        front_plate(
            "Model identification label", -374, -46, -44.06, 62, 23, 0.06, 2, self.ink
        )
        plate = engraving("LG  OLED48G6PCA", 0, 0, 0, 5.5, self.rubber)
        placed(plate, frame((-374, -45, -44.10), (-1, 0, 0), (0, 1, 0), (0, 0, -1)))
        self.label("LG ELECTRONICS", -318, -44, -44.06, 3.7)

    def screw(self, x, h, z):
        cap = pin(
            "Cabinet recessed Phillips fastener",
            (x, h, z),
            (x, h, z + 0.95),
            3.05,
            self.fastener,
            24,
        )
        for w, height in [(3.9, 0.90), (0.9, 3.9)]:
            subtract(
                cap,
                [
                    front_plate(
                        "Drive former", x, h, z, w, height, 0.66, 0.16, self.black
                    )
                ],
            )
        return cap

    def chassis(self):
        metal = finish("Panel · galvanized reinforcement", "929294", 0.74, 0.39)
        for name, x, h, w, height in [
            ("Upper chassis crossmember", 0, 48, 1003, 16),
            ("Left electronics stay", -146, -113, 19, 118),
            ("Right electronics stay", 146, -113, 19, 118),
            ("Central pedestal reinforcement", 0, -246, 251, 112),
        ]:
            rail = front_plate(name, x, h, -6.35, w, height, 2.7, 3.1, metal)
            if w > 300:
                subtract(
                    rail,
                    [
                        pin("Harness access hole", (x, h, -9), (x, h, -4), 3.4, metal)
                        for x in (-398, 398)
                    ],
                )
                for delta in (-6.4, 6.4):
                    front_plate(
                        "Folded crossmember flange",
                        0,
                        h + delta,
                        -8.5,
                        979,
                        2.6,
                        3.8,
                        0.9,
                        metal,
                    )
                for at in (-435, -276, -150, -46, 48, 150, 279, 435):
                    pin(
                        "Clinched boss",
                        (at, h, -8.8),
                        (at, h, -6.0),
                        4.2,
                        self.fastener,
                        28,
                    )
            elif w > 100:
                for offset in (-90, 90):
                    for dy in (-38, 38):
                        pin(
                            "Pressed attachment boss",
                            (offset, h + dy, -9.8),
                            (offset, h + dy, -7.5),
                            6.0,
                            metal,
                        )
                for dx in (-77, 0, 77):
                    front_plate(
                        "Pressed longitudinal stiffener",
                        dx,
                        h,
                        -8.2,
                        4.2,
                        95,
                        3.3,
                        1.8,
                        metal,
                    )
            else:
                front_plate(
                    "Raised channel rib", x, h, -8.4, 4.3, height - 8, 3.8, 1.6, metal
                )
                for dh in (-47, 47):
                    pin(
                        "Captive stay screw",
                        (x, h + dh, -10.2),
                        (x, h + dh, -7.5),
                        4.7,
                        self.fastener,
                        24,
                    )

    def label(self, value, x, h, z, size):
        obj = engraving(value, 0, 0, 0, size, self.ink)
        return placed(obj, frame((x, h, z), (-1, 0, 0), (0, 1, 0), (0, 0, -1)))

    def ports(self, side):
        origin = (-443.7, -54, -26.1) if side else (-342, -121, -29.9)
        axes = (
            ((0, 0, 1), (0, 1, 0), (-1, 0, 0))
            if side
            else ((-1, 0, 0), (0, 1, 0), (0, 0, -1))
        )
        fixture = frame(origin, *axes)
        if side:
            locations = [
                ("USB 1", "USB", 0, -84),
                ("HDMI 1", "HDMI", 0, -56),
                ("HDMI 2  eARC", "HDMI", 0, -32),
                ("HDMI 3", "HDMI", 0, -8),
            ]
            panel = front_plate(
                "Side I/O sockets · inset wall",
                0,
                0,
                -0.8,
                33,
                219,
                1.6,
                1.2,
                self.black,
            )
        else:
            locations = [
                ("AUDIO H/P", "IR", -82, 23),
                ("OPTICAL", "OPT", -82, -7),
                ("LAN", "LAN", -59, -7),
                ("ANTENNA IN", "RF", 39, -4),
                ("HDMI 4", "HDMI", 76, 23),
                ("USB 2", "USB", 76, 8),
                ("USB 3", "USB", 76, -7),
                ("IR BLASTER", "IR", 76, -24),
            ]
            panel = front_plate(
                "Rear I/O sockets · fascia", 0, 0, -0.8, 200, 77, 1.6, 1.7, self.black
            )
        sizes = {
            "USB": (13.4, 5.7),
            "HDMI": (14.2, 5.2),
            "LAN": (14, 13.1),
            "OPT": (9.5, 9.5),
            "RF": (10, 10),
            "IR": (6.3, 6.3),
        }
        cutters = []
        for _, kind, x, h in locations:
            w, ht = sizes[kind]
            if kind in ("RF", "IR"):
                cutters.append(
                    pin(
                        "Receptacle bore",
                        (x, h, -3),
                        (x, h, 3),
                        w * 0.5 + 0.1,
                        self.black,
                    )
                )
            else:
                cutters.append(
                    front_plate(
                        "Receptacle cutout",
                        x,
                        h,
                        0,
                        w + 0.3,
                        ht + 0.3,
                        5,
                        0.7,
                        self.black,
                    )
                )
        subtract(panel, cutters)
        placed(panel, fixture)
        for text, kind, x, h in locations:
            w, ht = sizes[kind]
            if kind in ("RF", "IR"):
                shell = pin(
                    text,
                    (x, h, -4),
                    (x, h, 0.52),
                    w / 2,
                    self.nickel if kind == "RF" else self.black,
                )
                subtract(
                    shell,
                    [
                        pin(
                            "Connector bore",
                            (x, h, -5),
                            (x, h, 1),
                            w * 0.34,
                            self.black,
                        )
                    ],
                )
                parts = [
                    shell,
                    pin(
                        "Dark insulator",
                        (x, h, -3.65),
                        (x, h, -3.2),
                        w * 0.35,
                        self.rubber,
                    ),
                ]
                if kind == "RF":
                    parts.append(
                        pin(
                            "Coax centre contact",
                            (x, h, -3.2),
                            (x, h, -1.0),
                            0.7,
                            self.gold,
                        )
                    )
            else:
                if kind == "HDMI":
                    p = [
                        (-7.1, 2.6),
                        (7.1, 2.6),
                        (7.1, -0.4),
                        (5.1, -2.6),
                        (-5.1, -2.6),
                        (-7.1, -0.4),
                    ]
                    shell = outline(
                        text, [(x + a, h + b) for a, b in p], -7, 7.25, self.nickel
                    )
                    subtract(
                        shell,
                        [
                            outline(
                                "HDMI mouth",
                                [(x + a * 0.93, h + b * 0.83) for a, b in p],
                                -6.5,
                                7.1,
                                self.rubber,
                            )
                        ],
                    )
                else:
                    shell = front_plate(
                        text,
                        x,
                        h,
                        -3.4,
                        w,
                        ht,
                        7.3,
                        0.65,
                        self.nickel if kind != "OPT" else self.black,
                    )
                    subtract(
                        shell,
                        [
                            front_plate(
                                "Receptacle mouth",
                                x,
                                h,
                                -2.6,
                                w - 1.05,
                                ht - 1.0,
                                6.8,
                                0.44,
                                self.rubber,
                            )
                        ],
                    )
                parts = [
                    shell,
                    front_plate(
                        "Connector shadow",
                        x,
                        h,
                        -5.8,
                        w - 1.2,
                        ht - 1.2,
                        0.4,
                        0.3,
                        self.rubber,
                    ),
                ]
                if kind in ("HDMI", "USB", "LAN"):
                    parts.append(
                        front_plate(
                            "Socket contact carrier",
                            x,
                            h - 0.4,
                            -2.9,
                            w * 0.77,
                            1.23,
                            4.3,
                            0.3,
                            self.black,
                        )
                    )
                    count = {"HDMI": 10, "USB": 4, "LAN": 8}[kind]
                    for i in range(count):
                        parts.append(
                            front_plate(
                                "Contact",
                                x + (i - (count - 1) / 2) * (w * 0.66 / count),
                                h + 0.26,
                                -2.25,
                                w * 0.26 / count,
                                0.13,
                                1.8,
                                0.04,
                                self.gold,
                            )
                        )
                if kind == "OPT":
                    parts.append(
                        front_plate(
                            "TOSLINK dust shutter",
                            x,
                            h,
                            -0.55,
                            w - 1.45,
                            ht - 1.8,
                            0.45,
                            0.5,
                            self.rubber,
                        )
                    )
            carrier_depth = 5 if side else 10
            parts.append(
                front_plate(
                    "Board-mounted contact housing",
                    x,
                    h,
                    -5.95 - carrier_depth * 0.5,
                    w - 0.3,
                    ht - 0.3,
                    carrier_depth,
                    0.4,
                    self.rubber,
                )
            )
            connector = placed(combine(text, parts), fixture)
            connector["boardConnector"] = True
            label = engraving(text, x, h + ht / 2 + 3, 0.05, 3.2, self.ink)
            placed(label, fixture)
        if side:
            front_plate(
                "Side recess · back wall",
                -487,
                -54,
                -13.5,
                87,
                219,
                1.3,
                1.4,
                self.black,
            )
            for h in (-165, 55):
                edge(
                    block(
                        "Side cable access return",
                        -487,
                        h,
                        -28.7,
                        86,
                        1.8,
                        30.6,
                        1.3,
                        self.black,
                    ),
                    0.35,
                )
        else:
            well = pocket(
                "Rear recessed connector surround",
                -342,
                -121,
                -44.1,
                203,
                80,
                15.1,
                2.6,
                1.4,
                self.black,
            )
            subtract(
                well,
                [
                    front_plate(
                        "Open port well back",
                        -342,
                        -121,
                        -29,
                        196.8,
                        73.8,
                        5,
                        0.8,
                        self.black,
                    )
                ],
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    folder = (root / ".references/04-桌面设备/显示器与桌面支架/LG OLED evo G6/Blender"
              if args.publish else args.output_dir or root / ".review/atelier/lg-g6")
    folder.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tv = Television()
    tv.panel()
    tv.rear()
    tv.ports(False)
    tv.ports(True)
    case_parts = list(bpy.context.scene.objects)
    runpy.run_path(str(assets / "vivo-tv-arm.py"))["build"](finish)
    exterior = list(bpy.context.scene.objects)
    support = [o for o in exterior if o not in case_parts]
    tv.chassis()
    runpy.run_path(str(assets / "lg-oled-boards.py"))["build"]()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    cabinet = bpy.data.collections.new("LG OLED48G6PCA · cabinet and panel")
    scene.collection.children.link(cabinet)
    mount = bpy.data.collections.new("VIVO STAND-V155D - 300x200 grommet mount")
    scene.collection.children.link(mount)
    for obj in case_parts + support:
        if obj.get("runtimeDisplaySurface"):
            continue
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        (mount if obj in support else cabinet).objects.link(obj)
    parts = set(exterior)
    for obj in scene.objects:
        obj["assembly"] = (
            "display"
            if obj in case_parts
            else "arm"
            if obj in support
            else "electronics"
        )
        if obj.type == "MESH" and len(obj.data.polygons) == 0:
            raise ValueError(f"Empty component: {obj.name}")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(folder / "lg-oled-g6.blend"), compress=True
    )
    active = next(part for part in case_parts if part.get("runtimeDisplaySurface"))
    case_parts.remove(active)
    parts.remove(active)
    parts.difference_update(obj for obj in support if obj.get("enclosedInAssembly"))
    support = [obj for obj in support if obj in parts]
    for obj in list(scene.objects):
        if obj not in parts:
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in support:
        for uv in list(obj.data.uv_layers):
            obj.data.uv_layers.remove(uv)
    combine("OLED48G6PCA · enclosure and connector bays", case_parts)
    combine("VIVO STAND-V155D · grommet assembly", support)
    target = (args.output_dir or root / "public/media/models") / "lg-oled-g6.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(assets / "pack-product-geometry.mjs"), str(target)], check=True
    )
    if args.publish:
        runpy.run_path(str(assets / "fit-vivo-tv-arm.py"))["save_standalone"]()


if __name__ == "__main__":
    main()
