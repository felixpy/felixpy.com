import argparse
import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

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
    pin,
    placed,
    subtract,
)

sculpt = runpy.run_path(str(assets / "vitrine-sculpt.py"))
finish = sculpt["finish"]


def case(name, levels, material):
    vertices = []
    for height, width, depth in levels:
        vertices.extend((x, height, z) for x, z in corners(width, depth, 1.2, 4))
    n = len(vertices) // len(levels)
    faces = [tuple(range(n)), tuple(reversed(range(len(vertices) - n, len(vertices))))]
    for start in range(0, len(vertices) - n, n):
        for i in range(n):
            j = (i + 1) % n
            faces.append((start + i, start + i + n, start + j + n, start + j))
    return mesh(name, vertices, faces, material)


def rear_frame(x, h, d):
    return frame((x, h, d), (-1, 0, 0), (0, 1, 0), (0, 0, -1))


class StudioRiser:
    def __init__(self):
        self.alloy = finish("Graphite powder-coated unibody", "434545", 0.57, 0.36)
        self.deck = finish("Bead-blasted anodized cover", "414444", 0.62, 0.42)
        self.metal = finish("Turned satin aluminium", "adaeab", 0.88, 0.28)
        self.dark = finish("Socket cavity", "111414", 0.09, 0.56)
        self.soft = finish("Graphite silicone rubber", "262929", 0, 0.77)
        self.glass = finish("Tinted Qi insert", "2d3031", 0.18, 0.19, 0.68)
        self.nickel = finish("Connector nickel", "92958e", 0.82, 0.29)
        self.ink = finish("Laser-marked aluminium", "959a98", 0.36, 0.43)
        self.blue = finish("Data bridge blue", "2f7b9d", 0, 0.51)
        self.green = finish("Data bridge green", "3b8565", 0, 0.51)
        self.orange = finish("Quick-charge port orange", "b6492d", 0, 0.51)
        self.polymer = finish("Moulded black connector resin", "37393a", 0.05, 0.42)
        self.button = finish("Pearl grey light keys", "a6aaa8", 0.28, 0.43)
        self.opal = finish("Warm opal diffuser", "ede5cc", 0, 0.42, glow=0.75)
        self.cable_x = [(j - 5.5) * 62.8 for j in range(12)]
        self.usb_mount = frame(
            (-558, 89.6, 0), (0.873, -0.487, 0), (0, 0, 1), (-0.487, -0.873, 0)
        )

    def usb(self, name, x, h, d, is_c, tongue):
        w, height = (9.0, 3.3) if is_c else (13.5, 5.7)
        outer = front_plate(
            name,
            x,
            h,
            d,
            w + 1.0,
            height + 1.0,
            5.9,
            1.75 if is_c else 0.65,
            self.nickel,
        )
        aperture = front_plate(
            "Socket well tool",
            x,
            h,
            d + 0.65,
            w,
            height,
            5.8,
            1.45 if is_c else 0.38,
            self.dark,
        )
        subtract(outer, [aperture])
        insert = front_plate(
            "Connector blade",
            x,
            h - (0 if is_c else 1.25),
            d + 0.65,
            w - 2.0,
            0.8 if is_c else 1.55,
            3.4,
            0.28,
            tongue,
        )
        well = front_plate(
            "Moulded port floor", x, h, d - 2.1, w, height, 0.3, 0.35, self.dark
        )
        return combine(name, [outer, insert, well])

    def screw(self, x, h, z, radius=1.9):
        head = pin(
            "Recessed fastener", (x, h, z), (x, h, z + 0.6), radius, self.nickel, 20
        )
        slots = [
            front_plate("Drive", x, h, z + 0.7, w, hh, 0.22, 0.12, self.dark)
            for w, hh in [(2.6, 0.52), (0.52, 2.6)]
        ]
        return combine("Cross recess fastener", [head, *slots])

    def shell(self):
        chassis = case(
            "Four-way tapered alloy chassis",
            [(36, 924, 61), (113, 1200, 217.3), (140.6, 1200, 217.3), (145, 1194, 210)],
            self.alloy,
        )
        chamber = block(
            "Accessory chamber tool", 0, 133.8, 0, 1010, 65, 150, 2.5, self.dark
        )
        cable_slots = [
            block("Cable throat tool", x, 144, -93, 19, 40, 41, 2.2, self.dark)
            for x in self.cable_x
        ]
        side = front_plate(
            "USB service opening tool", 0, 0, -3.8, 22, 68, 12, 2.7, self.dark
        )
        subtract(chassis, [chamber])
        subtract(chassis, cable_slots)
        subtract(chassis, [placed(side, self.usb_mount)])
        if len(chassis.data.polygons) < 100:
            raise ValueError("The open cable chamber must retain the outer chassis")
        edge(chassis, 0.55, 3)
        cover = edge(
            block(
                "Sliding removable aluminium cover",
                0,
                145.65,
                0.7,
                1021.8,
                4.7,
                197.7,
                1.2,
                self.deck,
            ),
            0.55,
        )
        cover["servicePart"] = "Slide to the rear to clear the rail before lifting."
        end_x = 554.6
        for x, mat, label in [
            (-end_x, self.glass, "Wireless charging module"),
            (end_x, self.deck, "Fixed right end cap"),
        ]:
            cap = edge(block(label, x, 145.7, 0.7, 85.4, 4.6, 197.7, 1.1, mat), 0.5)
            if x < 0:
                intake = block(
                    "Concealed service post", x, 134, -56, 39, 18, 16, 1.6, self.dark
                )
                combine(
                    "Firmware service socket beneath Qi module",
                    [
                        intake,
                        placed(
                            self.usb("Service USB", 0, 0, 0, False, self.dark),
                            frame((x, 144, -56), (1, 0, 0), (0, 0, -1), (0, 1, 0)),
                        ),
                    ],
                )
            cap["materialFinish"] = "Smoked polymer" if x < 0 else "Anodized aluminium"
        for x in [-498, 498]:
            pieces = [
                block("Upper guide flange", x, 142.2, 0, 6, 1.4, 147, 1.0, self.metal),
                block("Chamber sidewall", x, 122.4, 0, 2.7, 39.4, 146, 1.0, self.alloy),
            ]
            combine("Cover rail " + ("left" if x < 0 else "right"), pieces)
        for x in [-452, 452]:
            clip = [
                front_plate("Keeper slot", 0, 0, 0, 45, 5.5, 0.8, 1.1, self.dark),
                front_plate("Slide", 0, 0, 0.95, 24, 3.7, 1.55, 0.75, self.metal),
            ]
            for u in [-7, -4, -1, 2, 5, 8]:
                clip.append(
                    front_plate(
                        "Thumb rib", u, 0, 1.85, 0.7, 2.6, 0.45, 0.22, self.nickel
                    )
                )
            placed(
                combine("Surface lock " + str(x), clip), rear_frame(x, 136.6, -107.925)
            )

    def internals(self):
        for j in range(9):
            x = (j - 4) * 89.8
            edge(
                block(
                    f"Thermal cushion {j + 1:02d}",
                    x,
                    103.25,
                    0,
                    87.9,
                    3.4,
                    143,
                    1.1,
                    self.soft,
                ),
                0.55,
            )
        for index, x in enumerate([-462, 462]):
            side = "Left" if index == 0 else "Right"
            block(
                side + " extension foot cradle",
                x,
                104.1,
                0,
                76,
                4.3,
                126,
                2.2,
                self.dark,
            )
            for j, dx in enumerate([-18.6, 18.6]):
                xx = x + dx
                pieces = [
                    pin(
                        "Threaded extension foot",
                        (xx, 106.1, 0),
                        (xx, 134.5, 0),
                        16.8,
                        self.metal,
                        48,
                    ),
                    pin(
                        "Anti-slip tread",
                        (xx, 134.5, 0),
                        (xx, 136.2, 0),
                        15.3,
                        self.soft,
                        48,
                    ),
                    pin(
                        "Thread insert",
                        (xx, 136.15, 0),
                        (xx, 136.55, 0),
                        4.2,
                        self.nickel,
                        32,
                    ),
                ]
                for k in range(10):
                    a = k * math.tau / 10
                    px, pz = xx + math.cos(a) * 10.8, math.sin(a) * 10.8
                    pieces.append(
                        pin(
                            "Mould mark",
                            (px, 136.15, pz),
                            (px, 136.35, pz),
                            0.95,
                            self.dark,
                            12,
                        )
                    )
                combine(f"{side} stored screw-on extension {j + 1}", pieces)
        inner = frame((-494, 122, 22), (0, 0, -1), (0, 1, 0), (1, 0, 0))
        for h, mat in [(4.1, self.blue), (-4.1, self.green)]:
            placed(self.usb("Interior USB bridge", 0, h, 0, False, mat), inner)
        for index, x in enumerate(self.cable_x):
            arms = []
            for side in [-1, 1]:
                points = [
                    (x + side * 9.2, 124.6, -107.8),
                    (x + side * 5.7, 125.5, -107.8),
                    (x + side * 1.5, 130.3, -107.8),
                    (x + side * 3.2, 130.6, -107.8),
                    (x + side * 9.2, 128.9, -107.8),
                ]
                vs = points + [(a, h, d + 28.5) for a, h, d in points]
                fs = [tuple(range(5)), tuple(reversed(range(5, 10)))] + [
                    (k, (k + 1) % 5, (k + 1) % 5 + 5, k + 5) for k in range(5)
                ]
                arms.append(mesh("Compliant cable retainer", vs, fs, self.soft))
            combine(f"Cord router {index + 1:02d}", arms)

    def ac_outlet(self, x, h, rotation):
        housing = front_plate(
            "Polarized receptacle", 0, 0, 0, 29, 30, 7.4, 3.0, self.polymer
        )
        holes = [
            front_plate(
                "Terminal slot",
                u,
                1,
                2.6,
                1.9,
                9 if u < 0 else 7.1,
                8.3,
                0.42,
                self.dark,
            )
            for u in [-6.35, 6.35]
        ]
        holes.append(
            pin("Ground aperture", (0, -7.4, -2.8), (0, -7.4, 9), 2.7, self.dark)
        )
        subtract(housing, holes)
        back = front_plate(
            "Contact recess floor", 0, 0, -1.85, 21, 22, 0.28, 2, self.dark
        )
        transform = rear_frame(x, h, -106.3) @ Matrix.Rotation(rotation, 4, "Y")
        return placed(combine("Rear AC receptacle", [housing, back]), transform)

    def panel(self):
        edge(
            block(
                "Rear power distribution enclosure",
                0,
                67,
                -69.7,
                805,
                59.7,
                73.5,
                2.5,
                self.alloy,
            ),
            1,
        )
        for x, angle in [
            (-266, math.pi / 2),
            (-224, -math.pi / 2),
            (-90, math.pi),
            (-30, math.pi),
            (30, math.pi),
            (90, math.pi),
            (224, math.pi / 2),
            (266, -math.pi / 2),
        ]:
            self.ac_outlet(x, 62 if abs(x) > 100 else 69, angle)
        for x in [-377, 377]:
            transform = rear_frame(x, 69, -105.7)
            pieces = [
                front_plate(
                    "Recessed switch surround", 0, 0, 0, 29, 46, 3.2, 2.1, self.dark
                )
            ]
            if x < 0:
                for h, label in [(10, "INT"), (-10, "EXT")]:
                    pieces.extend(
                        [
                            front_plate(
                                label + " rocker",
                                3,
                                h,
                                2.1,
                                16,
                                13,
                                3.4,
                                1.6,
                                self.polymer,
                            ),
                            engraving(label, -8, h, 2.5, 3.2, self.ink),
                        ]
                    )
            else:
                pieces.append(
                    pin(
                        "Over-current reset",
                        (0, 9, 1),
                        (0, 9, 4.3),
                        3.2,
                        self.nickel,
                        24,
                    )
                )
                pieces.append(engraving("RESET", 0, -1, 2, 4, self.ink))
                pieces.append(
                    pin(
                        "Recessed supply grommet",
                        (0, -10, 1),
                        (0, -10, 4),
                        4.8,
                        self.soft,
                    )
                )
            placed(
                combine(
                    "Isolated INT and EXT rockers"
                    if x < 0
                    else "Over-current reset and inlet",
                    pieces,
                ),
                transform,
            )
        outer = front_plate(
            "USB socket strip", 0, 0, -1.1, 22.5, 70, 4, 2.2, self.polymer
        )
        openings = []
        inserts = []
        for h, mat, is_c in [
            (22, self.dark, True),
            (9, self.orange, False),
            (-8, self.blue, False),
            (-22, self.green, False),
        ]:
            openings.append(
                front_plate(
                    "Milled aperture",
                    0,
                    h,
                    0,
                    10.3 if is_c else 15.2,
                    4.8 if is_c else 7.3,
                    9,
                    1.0,
                    self.dark,
                )
            )
            inserts.append(
                self.usb("USB-C PD" if is_c else "USB-A socket", 0, h, -2.1, is_c, mat)
            )
        subtract(outer, openings)
        placed(
            combine("Recessed four-port I/O strip", [outer, *inserts]), self.usb_mount
        )
        tag = [
            front_plate(
                "Device information label", 0, 0, 0, 126, 28, 0.16, 1.35, self.dark
            ),
            engraving("H E X C A L   S T U D I O", 0, 5.5, 0.13, 6.5, self.ink),
            engraving("MODEL   SLT-LWF-BNF-DG-UC210", 0, -5.0, 0.13, 3.7, self.ink),
        ]
        placed(
            combine("Device information label", tag),
            frame((323, 37.06, -68), (1, 0, 0), (0, 0, 1), (0, -1, 0)),
        )

    def feet_and_front(self):
        for x in [-461, 461]:
            for z in [-52, 52]:
                items = [
                    pin("Elastomer foot", (x, 0, z), (x, 2, z), 16.9, self.soft, 48),
                    pin("Turned leg", (x, 2, z), (x, 68, z), 18.0, self.metal, 64),
                    pin("Mount collar", (x, 60, z), (x, 70, z), 18.7, self.alloy, 64),
                ]
                combine(f"Primary leg {x} {z}", items)
        keys = []
        left = -505
        for label, w, gap in [
            ("POWER", 43, 0),
            ("MODE", 20, 12),
            ("SAVE", 20, 4),
            ("FAVE", 20, 4),
            ("RANGE", 20, 4),
            ("INTST", 34, 4),
            ("TEMP", 34, 5),
        ]:
            x = left + gap + w / 2
            keys.extend(
                [
                    front_plate(
                        "Key surround", x, 126, 108.8, w, 6.8, 1.4, 0.6, self.dark
                    ),
                    front_plate(
                        "Key cap", x, 126, 109.62, w - 1.2, 5.6, 0.5, 0.44, self.button
                    ),
                    engraving(label, x, 126, 109.95, 4.35, self.dark),
                ]
            )
            if label in ("INTST", "TEMP"):
                for side in [-1, 1]:
                    px = x + side * w * 0.38
                    keys.append(
                        mesh(
                            "Arrow inlay",
                            [
                                (px - 1, 126 - side, 109.96),
                                (px + 1, 126 - side, 109.96),
                                (px, 126 + side, 109.96),
                            ],
                            [(0, 1, 2)],
                            self.dark,
                        )
                    )
            if label == "POWER":
                keys.append(
                    front_plate(
                        "Power indicator",
                        x - 15,
                        126,
                        109.98,
                        2.8,
                        2.8,
                        0.055,
                        0.22,
                        self.opal,
                    )
                )
            left = x + w / 2
        combine("Seven light controls", keys)
        engraving("H E X C A L  S T U D I O", 441, 127.7, 108.73, 10.3, self.ink)
        lens = frame((0, 109.15, 106.30), (1, 0, 0), (0, 0.72, 0.69), (0, -0.69, 0.72))
        gaskets = [
            front_plate("Task light channel", 0, 0, 0, 843, 8.2, 2.4, 1.2, self.dark)
        ]
        for index in range(4):
            gaskets.append(
                front_plate(
                    "Opal diffuser",
                    (index - 1.5) * 210.3,
                    0,
                    1.35,
                    209.8,
                    6.4,
                    1.3,
                    0.72,
                    self.opal,
                )
            )
        placed(combine("Four-zone task light", gaskets), lens)
        under = frame((0, 35.6, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))
        fittings = [
            front_plate("Spine", 0, 0, 0, 913, 54, 1.1, 1.4, self.alloy),
            engraving("H E X C A L", 0, 1, 0.7, 20, self.ink),
            engraving("I N D O O R   S Y S T E M S", 0, -10, 0.7, 4.2, self.ink),
        ]
        for x in [-448, -417, 417, 448]:
            for h in [-18, 18]:
                fittings.append(self.screw(x, h, 0.5))
        placed(combine("Screwed underside spine", fittings), under)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    folder = args.output_dir or root / ".review/atelier/hexcal-study"
    folder.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    riser = StudioRiser()
    riser.shell()
    riser.internals()
    riser.panel()
    riser.feet_and_front()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(folder / "hexcal-studio.blend"), compress=True
    )
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    combine("Hexcal Studio SLT-LWF-BNF-DG-UC210", meshes)
    target = (args.output_dir or root / "public/media/models") / "hexcal-studio.glb"
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


if __name__ == "__main__":
    main()
