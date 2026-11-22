import math
import runpy
import subprocess
from pathlib import Path

import bpy
from io_scene_gltf2.io.exp import meshopt
from mathutils import Matrix, Vector


scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
review = project / ".review/atelier/camp-rack"
editable = review / "equipment-rack.blend"
solids = runpy.run_path(str(scripts / "product_solids.py"))
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
finish = sculpt["finish"]
pitch = 25.4
datum = 1572
wall = -18
face = 52
gauge = 0.91
flange = 15.875


def block(name, x, h, d, w, height, depth, material, bevel=0.5):
    vertices = [
        (x + i * w / 2, h + j * height / 2, d + k * depth / 2)
        for i, j, k in [
            (-1, -1, -1),
            (1, -1, -1),
            (1, 1, -1),
            (-1, 1, -1),
            (-1, -1, 1),
            (1, -1, 1),
            (1, 1, 1),
            (-1, 1, 1),
        ]
    ]
    obj = solids["mesh"](
        name,
        vertices,
        [
            (3, 2, 1, 0),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ],
        material,
    )
    return solids["edge"](obj, bevel, 3) if bevel else obj


def wire(name, points, radius, material):
    curve = sculpt["Sculpture"](name)
    points = [Vector(p) for p in points]
    rounded = [points[0]]
    for a, b, c in zip(points, points[1:], points[2:]):
        u, v = a - b, c - b
        trim = min(u.length * 0.38, v.length * 0.38, radius * 2.4)
        entry, leave = b + u.normalized() * trim, b + v.normalized() * trim
        for t in (0, 0.25, 0.5, 0.75, 1):
            rounded.append((1 - t) ** 2 * entry + 2 * t * (1 - t) * b + t * t * leave)
    curve.pipe(rounded + [points[-1]], radius, material, 14)
    return curve.finalize()


def cassette(label, columns, material):
    vertices, faces, lookup = [], [], {}

    def point(x, h, d):
        key = tuple(round(n, 6) for n in (x, h, d))
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(key)
        return lookup[key]

    for column in columns:
        x = column * pitch
        for row in range(-21, 22):
            h = datum + row * pitch
            low = h - pitch / 2 if row > -21 else 1011
            high = h + pitch / 2 if row < 21 else 2138
            left = x - pitch / 2 + (0.65 if column == columns[0] else 0)
            right = x + pitch / 2 - (0.65 if column == columns[-1] else 0)
            corners = [(right, high), (left, high), (left, low), (right, low)]
            front = [point(a, b, face) for a, b in corners]
            back = [point(a, b, face - gauge) for a, b in corners]
            rings = [
                [
                    point(
                        x + radius * math.cos(math.pi / 4 + i * math.tau / 16),
                        h + radius * math.sin(math.pi / 4 + i * math.tau / 16),
                        d,
                    )
                    for i in range(16)
                ]
                for radius, d in [(3.175, face), (3.175, face - gauge)]
            ]
            for side in range(4):
                edge = (side + 1) % 4
                a, b = 4 * side, (4 * edge) % 16
                for outer, ring, reverse in [
                    (front, rings[0], False),
                    (back, rings[1], True),
                ]:
                    for i in range(a, a + 4):
                        poly = (outer[side], ring[(i + 1) % 16], ring[i])
                        faces.append(poly[::-1] if reverse else poly)
                    poly = (outer[side], outer[edge], ring[b])
                    faces.append(poly[::-1] if reverse else poly)
                if (
                    side == 0
                    and row == 21
                    or side == 1
                    and column == columns[0]
                    or side == 2
                    and row == -21
                    or side == 3
                    and column == columns[-1]
                ):
                    faces.append((front[edge], front[side], back[side], back[edge]))
            for i in range(16):
                j = (i + 1) % 16
                faces.append((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    return solids["mesh"](label, vertices, faces, material)


def screw(name, x, h, start, end, radius, mat):
    head = sculpt["Sculpture"](name)
    head.rings(
        [
            [
                (
                    x + r * math.cos(i * math.tau / 24),
                    h + r * math.sin(i * math.tau / 24),
                    d,
                )
                for i in range(24)
            ]
            for r, d in [
                (radius * 0.46, start),
                (radius * 0.46, end - 0.7),
                (radius, end),
                (radius, end + 0.65),
                (0.84 * radius, end + 1.35),
            ]
        ],
        mat,
        True,
        False,
    )
    shape = []
    for d, r in [(end + 1.35, radius * 0.42), (end + 0.03, radius * 0.35)]:
        shape.append(
            [
                (
                    x + r * math.cos(i * math.tau / 24) * (1 if i % 4 == 0 else 0.77),
                    h + r * math.sin(i * math.tau / 24) * (1 if i % 4 == 0 else 0.77),
                    d,
                )
                for i in range(24)
            ]
        )
    rim = [
        (
            x + radius * 0.84 * math.cos(i * math.tau / 24),
            h + radius * 0.84 * math.sin(i * math.tau / 24),
            end + 1.35,
        )
        for i in range(24)
    ]
    head.rings([rim, *shape], mat, False, False)
    head.add(shape[-1], [tuple(range(24))], mat, False)
    return head.finalize()


def shelf(stove, metal, rubber):
    rear, front = 52.15, 300.5
    block(
        "Tray · powder-coated work surface",
        0,
        1074.15,
        (rear + front) / 2,
        1160,
        1.7,
        front - rear,
        stove,
    )
    for d in (rear + 0.95, front - 0.95):
        block("Tray · folded lip", 0, 1064.55, d, 1160, 21.1, 1.9, stove)
        block(
            "Tray · returned hem",
            0,
            1054.85,
            d + (1 if d < 100 else -1) * 4.7,
            1157,
            1.7,
            10.6,
            stove,
        )
    for x in (-579, 579):
        block(
            "Tray · end flange",
            x,
            1064.85,
            (front + rear) / 2,
            2,
            20.3,
            front - rear - 3,
            stove,
        )
    for x in (-457.2, 457.2):
        block("Shelf bracket · upright", x, 955.5, wall + 2, 32, 95, 4, stove, 1.1)
        block("Shelf bracket · offset below panel", x, 1001, 24, 32, 4, 80, stove)
        block("Shelf bracket · folded riser", x, 1026, 62.1, 32, 50, 3.8, stove)
        block("Shelf bracket · reach", x, 1051.5, 169, 32, 5, 234, stove)
        for d in (78, 252):
            block("Tray · welded hat rail", x, 1063.65, d, 35, 19.3, 15, stove, 1)
        wire(
            "Shelf bracket · diagonal brace",
            [(x, 918, wall + 2), (x, 923, -5), (x, 1046, 253), (x, 1050, 263)],
            7.1,
            stove,
        )
        for h in (941, 985):
            screw("Shelf · cabinet fixing", x, h, wall - 27, wall + 4, 5.9, metal)
        for d in (76, 252):
            solids["pin"](
                "Shelf · rivet nut", (x, 1048.55, d), (x, 1056, d), 3.2, metal
            )
    block("Carry loop · captive reinforcement", -369, 1063.7, 127, 35, 19.2, 27, stove)
    block("Carry loop · oval mounting plate", -369, 1053.25, 127, 22, 1.6, 16, metal)
    wire(
        "Carry loop · under-shelf J",
        [
            (-369, 1054, 127),
            (-369, 1025, 127),
            (-369, 1018.65, 132),
            (-369, 1018.65, 143),
            (-369, 1021, 151),
            (-369, 1027, 154),
        ],
        2.45,
        metal,
    )
    for x in (-377, -361):
        solids["pin"](
            "Carry loop · rivet head", (x, 1052.0, 127), (x, 1054.3, 127), 2.45, metal
        )
    for h in (545, 740.7):
        for x in (615, 659):
            solids["pin"](
                "Shaft clip · compression spacer",
                (x, h, wall),
                (x, h, 1.35),
                5.4,
                rubber,
                24,
            )
            screw(
                "Shaft clip · countersunk wall fixing",
                x,
                h,
                wall - 22,
                12.45,
                3.6,
                metal,
            )
    block("Tip rest · wall plate", 631.5, 394, wall + 1.65, 85, 33, 3.3, stove, 1)
    for x, d in ((603, 103), (660, 133)):
        screw("Tip rest · wall fixing", x, 400, wall - 23, wall + 3.3, 4.2, metal)
        screw("Tip rest · lower wall fixing", x, 385, wall - 23, wall + 3.3, 3.3, metal)
        block(
            "Tip rest · formed arm",
            x,
            400.5,
            (wall + 3.1 + d + 7) / 2,
            13,
            2.3,
            d + 7 - wall - 3.1,
            stove,
        )
        for side in (-1, 1):
            block(
                "Tip rest · stiffening return",
                x + side * 5.8,
                397.7,
                (wall + 3.1 + d + 3) / 2,
                1.4,
                5.3,
                d + 3 - wall - 3.1,
                stove,
            )
        cup = sculpt["Sculpture"]("Tip rest · rubber socket")
        profile = [
            (401.65, 1.0),
            (401.65, 6.9),
            (402.2, 7.5),
            (409.3, 7.5),
            (410.2, 6.9),
            (410.2, 5.7),
            (409.6, 5.25),
            (405, 3.4),
            (405, 0.02),
        ]
        cup.rings(
            [
                [
                    (
                        x + rad * math.sin(i * math.tau / 36),
                        h,
                        d + rad * math.cos(i * math.tau / 36),
                    )
                    for i in range(36)
                ]
                for h, rad in profile
            ],
            rubber,
        )
        cup.finalize()


def hardware(wire_mat, rubber):
    def hook(name, c, r, xh, depth_end, radius=2.15, front=0, seating=None):
        x, h = c * pitch, datum + r * pitch
        sx, sh = xh
        path = [
            (x, h + 8.3, face - gauge - radius + 0.10),
            (x, h + 5.6, 44),
            (x, h + 1.8, 44),
            (x, h, 47),
            (x, h, 57.5),
            (x, h - 5.6, 60.5),
            (sx, sh + 3, 64.5),
            (sx, sh, 73),
        ]
        path.extend(seating or [(sx, sh, depth_end - 5)])
        path.extend([(sx, sh + 0.9, depth_end), (sx, sh + front, depth_end + 3.5)])
        wire(name, path, radius, wire_mat)
        wire(
            name + " · anti-roll foot",
            [
                (x, h - 5.5, 60.5),
                (x, h - 10.2, 56.4),
                (x, h - 12, face + radius * 0.95),
            ],
            radius,
            wire_mat,
        )

    hook("Cup · folding bail cradle", -16, 16, (-406.4, 1951.4), 131, 2.15, 6)
    hook(
        "Gloves · common hanging pin",
        -16,
        5,
        (-408.7, 1671.92),
        100,
        1.65,
        6,
        [(-408.7, 1671.92, 86), (-408.7, 1670.35, 91.2), (-408.7, 1670.35, 96.3)],
    )
    hook("Guyline · narrow loop pin", -11, 18, (-268, 2016.02), 118, 1.45, 8)
    x, h = -10 * pitch, datum + 18 * pitch
    wire(
        "Guyline · second locking tang",
        [
            (x, h + 8, 49.6),
            (x, h + 4, 44),
            (x, h, 47.5),
            (x, h, 58),
            (x, h - 6, 61),
            (-268, 2018.9, 65),
        ],
        1.45,
        wire_mat,
    )
    for side in (-1, 1):
        hook("TAKIBI · vent hanger", side * 2, 10, (side * 49, 1804.61), 111, 2.2, 5)
        x, h = side * 5 * pitch, datum + 4 * pitch
        solids["pin"]("TAKIBI · bumper fixing", (x, h, 47), (x, h, 55), 2.55, wire_mat)
        solids["pin"]("TAKIBI · stand-off stem", (x, h, 52), (x, h, 78), 4.1, wire_mat)
        solids["pin"](
            "TAKIBI · elastomer bumper", (x, h, 77.8), (x, h, 90.59), 7, rubber
        )
    for c, sx, sh in [(11, 277.5, 1962.34), (13, 318.5, 1963.74)]:
        hook("Hammer · split head cradle", c, 16, (sx, sh), 128, 2.55, 7)
    for x in (406.4, 482.6):
        wire(
            "Canvas organizer · recovery tang",
            [(x, 1956, 44), (x, 1959.2, 42.4), (x, 1964, 45), (x, 1964.2, 49.05)],
            2.05,
            wire_mat,
        )
    cloth = finish("Rack · bound olive canvas", "7e7863", 0, 0.94)
    thread = finish("Rack · saddle stitches", "a69b7d", 0, 0.91)
    for i, x in enumerate([410, 445, 480]):
        toe = 1790 - 2 * i
        pocket = sculpt["Sculpture"]("Stake organizer · stitched toe pocket")
        rings = [
            (toe - 1.4, 3.6, 2.4),
            (toe - 0.6, 6.6, 4.5),
            (toe + 11, 7.4, 5.3),
            (toe + 14, 7.4, 5.3),
            (toe + 14, 6.25, 4.2),
            (toe, 4.35, 3.55),
            (toe, 0.03, 0.03),
        ]
        pocket.rings(
            [
                [
                    (
                        x + rx * math.sin(j * math.tau / 24),
                        h,
                        84 + rz * math.cos(j * math.tau / 24),
                    )
                    for j in range(24)
                ]
                for h, rx, rz in rings
            ],
            cloth,
        )
        for s in (-1, 1):
            block(
                "Stake organizer · sewn welt",
                x + s * 5.5,
                toe + 7,
                80.6,
                3,
                13.5,
                4.5,
                cloth,
            )
            for h in (toe + 2, toe + 6, toe + 10):
                pocket.pipe(
                    [(x + s * 6.5, h, 81.3), (x + s * 6.5, h + 2, 81.3)],
                    0.32,
                    thread,
                    6,
                )
        pocket.finalize()


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    review.mkdir(parents=True, exist_ok=True)
    coat = finish("Rack · graphite powder enamel", "565a56", 0.41, 0.64, 0.07)
    frame = finish("Rack · iron grey folded steel", "363c38", 0.51, 0.48, 0.08)
    steel = finish("Rack · zinc nickel hardware", "838681", 0.81, 0.34)
    rubber = finish("Rack · dark elastomer", "353a37", 0, 0.77)
    timber = finish("Rack · sealed charcoal mounting board", "46433e", 0, 0.9)
    for section, columns in enumerate([range(-22, -7), range(-7, 8), range(8, 23)]):
        center = (columns[0] + columns[-1]) * pitch / 2
        cassette("Panel %d · 645 punched holes" % (section + 1), columns, coat)
        for x in (center - 189.39, center + 189.39):
            block(
                "Panel · folded side return",
                x,
                1574.5,
                face - flange / 2,
                0.95,
                1127,
                flange,
                coat,
                0.2,
            )
        for h in (1011.5, 2137.5):
            block(
                "Panel · folded end return",
                center,
                h,
                face - flange / 2,
                378,
                1,
                flange,
                coat,
                0.2,
            )
        for x in (columns[0] * pitch, columns[-1] * pitch):
            for row in (-20, 0, 21):
                h = datum + row * pitch
                solids["pin"](
                    "Board · crush sleeve",
                    (x, h, face - flange),
                    (x, h, face - gauge),
                    6.2,
                    frame,
                    18,
                )
                screw("Board · six-lobe fastener", x, h, wall - 24, face, 4.95, steel)
    block(
        "Board · recessed dark mounting back",
        0,
        1574.5,
        face - flange - 6,
        1142,
        1127,
        12,
        timber,
        1,
    )
    for x in (-548, -190.5, 190.5, 548):
        block(
            "Board · concealed wall batten",
            x,
            1574.5,
            (wall + face - flange - 12) / 2,
            71,
            1127,
            face - flange - 12 - wall,
            timber,
            0.8,
        )
    shelf(frame, steel, rubber)
    hardware(steel, rubber)
    root = bpy.data.objects.new("Field wall · three perforated cassettes", None)
    bpy.context.collection.objects.link(root)
    root["product"] = "camp-load-rack"
    root["pitchMm"] = pitch
    root["holeDiameterMm"] = 6.35
    root["panelThicknessMm"] = gauge
    root["wallDepthMm"] = wall
    for obj in list(bpy.context.scene.objects):
        if obj != root:
            obj.parent = root
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(editable), compress=True)
    panel_parts = [o for o in root.children if "punched holes" in o.name]
    hardware_parts = [o for o in root.children if o not in panel_parts]
    panel_parts.sort(key=lambda obj: obj.name)
    center = panel_parts[1]
    center.data.transform(Matrix.Translation((0, 0, -datum / 1000)))
    for i, part in enumerate(panel_parts):
        part.data = center.data
        part.location = ((i - 1) * 15 * pitch / 1000, 0, datum / 1000)
    solids["combine"](
        "Rack supports · folded returns, hardware and tray", hardware_parts
    ).parent = root
    target = project / "public/media/models/camp-rack.glb"
    original_bits = meshopt.EXP_FILTER_BITS
    try:
        meshopt.EXP_FILTER_BITS = 20
        bpy.ops.export_scene.gltf(
            filepath=str(target),
            export_format="GLB",
            export_extras=True,
            export_animations=False,
            export_meshopt_compression_enable=True,
            export_meshopt_extension="EXT_meshopt_compression",
        )
    finally:
        meshopt.EXP_FILTER_BITS = original_bits
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
    )


if __name__ == "__main__":
    build()
