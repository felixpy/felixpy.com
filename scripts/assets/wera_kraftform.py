import math

import bpy

from blender_parts import barrel, xyz
from product_solids import letters


PROFILE = [
    (0, 11.2),
    (0.8, 12.2),
    (2.2, 12.85),
    (5.1, 12.85),
    (6.8, 11.7),
    (9.4, 10.1),
    (14.5, 9.35),
    (19, 9.05),
    (23.5, 9.2),
    (28, 10.0),
    (33, 11.3),
    (37, 12.25),
    (44, 12.55),
    (51, 13.6),
    (57, 15.15),
    (62.8, 16.5),
    (65.5, 16.23),
    (71, 14.65),
    (79, 13.1),
    (87, 12.05),
    (92, 11.85),
    (94.8, 11.3),
    (96.5, 9.9),
    (97.5, 7.7),
]
SPECS = [
    ("350 PH", "PH 1", "05008710001", 80, 4.5, "ph"),
    ("335", "0.8 x 4", "05110004001", 100, 4.0, "slot"),
    ("367 TORX", "TX 15", "05028008001", 80, 4.0, "torx"),
]


def radius(h, a):
    for (y0, r0), (y1, r1) in zip(PROFILE, PROFILE[1:]):
        if h <= y1:
            raw = r0 + (r1 - r0) * (h - y0) / (y1 - y0)
            break
    else:
        raw = PROFILE[-1][1]
    angle = (a + math.pi / 6) % (math.pi / 3) - math.pi / 6
    hexagon = math.cos(math.pi / 6) / math.cos(angle)
    faceting = max(1 - max(0, h - 5.1) / 6, 0)
    palm = min(1, max(0, (h - 22) / 12)) * min(1, max(0, (97 - h) / 9))
    return raw * (1 - (1 - hexagon) * faceting - 0.042 * math.sin(3 * a) ** 2 * palm)


def mount_drivers(bright, dark, yellow, shell, pitch):
    batches = {
        "workshop-wera-body": [],
        "workshop-wera-grip": [],
        "workshop-wera-ph": [],
        "workshop-wera-print": [],
    }
    colors = {
        "workshop-wera-body": (
            "Kraftform · rigid black",
            (0.019, 0.022, 0.023),
            0.33,
            0,
        ),
        "workshop-wera-grip": (
            "Kraftform · soft turquoise",
            (0.026, 0.354, 0.221),
            0.70,
            0,
        ),
        "workshop-wera-ph": ("Take it easy · PH red", (0.64, 0.018, 0.020), 0.53, 0),
        "workshop-wera-print": ("Pad print · pearl", (0.77, 0.77, 0.70), 0.58, 0),
        "yellow": ("Take it easy · slotted yellow", (0.90, 0.55, 0.012), 0.49, 0),
        "bright": ("Wera · plated steel", (0.50, 0.51, 0.46), 0.32, 0.84),
        "dark": ("Wera · Black Point", (0.040, 0.043, 0.041), 0.54, 0.52),
    }
    destinations = {**batches, "yellow": yellow, "bright": bright, "dark": dark}
    materials = {}
    for key, (name, color, roughness, metal) in colors.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metal
        materials[key] = mat

    for i, (model, size, number, length, shaft, tip) in enumerate(SPECS):
        z = (-12 + 3 * i) * pitch
        y = -pitch + 5.9
        coll = bpy.data.collections.new("Wera " + model + " · " + size)
        bpy.context.scene.collection.children.link(coll)

        def part(obj, key):
            obj.data.materials.append(materials[key])
            obj["toolPartNumber"] = number
            obj["workshopBatch"] = key
            coll.objects.link(obj)
            bpy.context.collection.objects.unlink(obj)
            destinations[key].append(obj)

        def p(h, a, r):
            return (-25.4 - math.cos(a) * r, y + h, z + math.sin(a) * r)

        def smooth(obj):
            for face in obj.data.polygons:
                face.use_smooth = len(face.vertices) == 4
            return obj

        n = 36
        angles = [j * math.tau / n for j in range(n)]
        handle = [[p(h, a, radius(h, a)) for a in angles] for h, _ in PROFILE]
        part(
            smooth(
                shell("Kraftform · moulded six-flat finger stop and palm core", handle)
            ),
            "workshop-wera-body",
        )
        for sector in range(6):
            center = sector * math.tau / 6
            for low, high in [(35.4, 62.4), (65.9, 92.9)]:
                rows = []
                for fraction, width in [
                    (0, 0.065),
                    (0.04, 0.18),
                    (0.14, 0.284),
                    (0.44, 0.306),
                    (0.78, 0.302),
                    (0.93, 0.252),
                    (0.98, 0.156),
                    (1, 0.055),
                ]:
                    h = low + fraction * (high - low)
                    contour = []
                    for j in range(5):
                        a = center + width * (j / 2 - 1)
                        contour.append(p(h, a, radius(h, a) + 0.17))
                    for j in reversed(range(5)):
                        a = center + width * (j / 2 - 1)
                        contour.append(p(h, a, radius(h, a) - 0.21))
                    rows.append(contour)
                pad = shell("Kraftform · rounded grip inlay", rows)
                part(smooth(pad), "workshop-wera-grip")
        for h in (47.6, 79.4):
            bands = [
                [p(height, a, radius(height, a) + lift) for a in angles]
                for height, lift in [
                    (h - 0.88, -0.12),
                    (h - 0.88, 0.08),
                    (h + 0.88, 0.08),
                    (h + 0.88, -0.12),
                ]
            ]
            part(
                smooth(shell("Moulded bridge between soft grip zones", bands, True)),
                "workshop-wera-grip",
            )
        cap_key = {
            "slot": "yellow",
            "ph": "workshop-wera-ph",
            "torx": "workshop-wera-grip",
        }[tip]
        cap = [
            [p(h, a, r) for a in angles]
            for h, r in [(97.40, 7.65), (97.82, 6.7), (98, 5.55)]
        ]
        part(smooth(shell("Take it easy · profile end medallion", cap)), cap_key)

        def mark(s, h, scale, on_cap=False):
            points, faces = letters(s, False)
            u0 = (min(v[0] for v in points) + max(v[0] for v in points)) * 0.5
            v0 = (min(v[1] for v in points) + max(v[1] for v in points)) * 0.5
            coords = []
            for u, v in points:
                u, v = (u - u0) * scale, (v - v0) * scale
                if on_cap:
                    coords.append(xyz((-25.4 + v, y + 98.045, z + u)))
                else:
                    a = u / radius(h + v, 0)
                    coords.append(xyz(p(h + v, a, radius(h + v, a) + 0.055)))
            data = bpy.data.meshes.new("Pad printed character shapes")
            data.from_pydata(coords, [], faces)
            data.update()
            obj = bpy.data.objects.new(s, data)
            bpy.context.collection.objects.link(obj)
            part(obj, "workshop-wera-print" if not on_cap else "workshop-wera-body")

        mark("Wera", 23.6, 3.40)
        mark(model, 18.55, 2.55)
        mark(size, 14.9, 2.35)
        mark({"ph": "1", "slot": "4", "torx": "15"}[tip], 98, 5.1, True)
        tip_length = {"ph": 7.4, "slot": 12, "torx": 10}[tip]
        part(
            barrel(
                "Round plated blade",
                p(-length + tip_length, 0, 0),
                p(0.35, 0, 0),
                shaft / 2,
                n,
            ),
            "bright",
        )
        end = -length

        def laser_lines(rows, count, pitch, amplitude):
            vertices, faces = [], []
            for band in range(count):
                for edge in (0, 0.075):
                    for j, a in enumerate(angles):
                        height = (
                            y
                            + end
                            + 0.42
                            + band * pitch
                            + amplitude * math.sin(a)
                            + edge
                        )
                        for lower, upper in zip(rows, rows[1:]):
                            if height <= upper[j][1]:
                                mix = (height - lower[j][1]) / (
                                    upper[j][1] - lower[j][1]
                                )
                                x = lower[j][0] + mix * (upper[j][0] - lower[j][0])
                                depth = lower[j][2] + mix * (upper[j][2] - lower[j][2])
                                vertices.append(
                                    xyz(
                                        (
                                            x - 0.023 * math.cos(a),
                                            height,
                                            depth + 0.023 * math.sin(a),
                                        )
                                    )
                                )
                                break
                start = 2 * n * band
                for j in range(n):
                    k = (j + 1) % n
                    faces.append((start + j, start + k, start + n + k, start + n + j))
            data = bpy.data.meshes.new("Diagonal laser roughening")
            data.from_pydata(vertices, [], faces)
            obj = bpy.data.objects.new("Lasertip · etched surface furrows", data)
            bpy.context.collection.objects.link(obj)
            part(obj, "dark")

        if tip == "slot":
            sections = []
            for h, w, t in [
                (0, 1.98, 0.40),
                (0.5, 2, 0.415),
                (5.4, 2, 0.78),
                (8.5, 2, 1.5),
                (12, 2, 2),
            ]:
                sections.append(
                    [
                        p(
                            end + h,
                            a,
                            1
                            / math.sqrt(
                                (math.cos(a) / t) ** 2 + (math.sin(a) / w) ** 2
                            ),
                        )
                        for a in angles
                    ]
                )
                if h < 8:
                    sections[-1] = [
                        (
                            -25.4
                            + t * math.copysign(abs(math.cos(a)) ** 0.20, math.cos(a)),
                            y + end + h,
                            z
                            + w * math.copysign(abs(math.sin(a)) ** 0.20, math.sin(a)),
                        )
                        for a in angles
                    ]
            part(shell("335 · parallel tip ground to 0.8 mm", sections), "bright")
            laser_lines(sections, 8, 0.33, 0.28)
        elif tip == "ph":
            section = []
            for h, outer, inner in [
                (0, 0.61, 0.43),
                (0.8, 1.02, 0.45),
                (2.6, 1.65, 0.55),
                (4.4, 2.0, 0.77),
                (5.8, 2.23, 1.3),
                (7.4, 2.25, 2.25),
            ]:
                section.append(
                    [
                        p(
                            end + h,
                            a,
                            inner + (outer - inner) * max(0, math.cos(4 * a)) ** 0.63,
                        )
                        for a in angles
                    ]
                )
            part(shell("350 PH1 · four forged flutes", section), "bright")
            laser_lines(section, 6, 0.32, 0.24)
        else:
            section = []
            for h, rb, ridge in [
                (0, 1.16, 0.10),
                (0.35, 1.38, 0.20),
                (4.8, 1.38, 0.20),
                (6.4, 1.48, 0.17),
                (8.1, 1.92, 0.02),
                (10, 2, 0),
            ]:
                section.append(
                    [p(end + h, a, rb + ridge * math.cos(6 * a)) for a in angles]
                )
            part(smooth(shell("367 TX15 · six-lobe Black Point", section)), "dark")
    return batches
