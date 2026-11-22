import math

import bpy


def build_snips(sculpture, dial, forged, ground, chrome, red, blue, ink):
    root = bpy.data.objects.new("KNIPEX Electronic Super Knips 78 61 125", None)
    bpy.context.collection.objects.link(root)
    root["benchInstrument"] = "cutters"
    root["article"] = "78 61 125"
    parts = []

    def keep(shape):
        obj = shape.finalize()
        obj.parent = root
        parts.append(obj)

    handle = [
        (-107, 23.0, 0.3, 0.65, 0.08),
        (-106.8, 23.0, 1.55, 2.0, 0.1),
        (-106.1, 23.1, 3.25, 3.8, 0.13),
        (-104.6, 23.1, 4.65, 5.1, 0.22),
        (-102, 23.0, 5.35, 5.9, 0.33),
        (-98, 22.9, 5.55, 6.15, 0.36),
        (-94, 22.9, 5.62, 6.21, 0.38),
        (-91, 22.9, 5.66, 6.23, 0.41),
        (-88, 22.9, 5.71, 6.25, 0.85),
        (-85, 22.9, 5.72, 6.28, 0.96),
        (-77, 22.5, 5.79, 6.34, 1.01),
        (-66, 21.5, 5.83, 6.4, 1.01),
        (-55, 19.6, 5.7, 6.42, 1.0),
        (-50, 18.6, 5.62, 6.4, 0.96),
        (-47, 17.9, 5.54, 6.35, 0.52),
        (-45, 17.5, 5.48, 6.32, 0.41),
        (-37, 15.6, 5.31, 6.3, 0.40),
        (-31, 14.3, 5.3, 6.31, 0.39),
        (-29, 13.8, 5.38, 6.32, 0.44),
        (-27, 13.3, 5.65, 6.4, 0.88),
        (-25, 12.8, 5.86, 6.46, 1.35),
        (-23, 12.3, 5.68, 6.31, 1.54),
        (-21.8, 12.0, 5.07, 5.65, 1.56),
        (-21.45, 11.95, 4.15, 4.7, 1.56),
    ]

    def section(height):
        for low, high in zip(handle, handle[1:]):
            if low[0] <= height <= high[0]:
                ratio = (height - low[0]) / (high[0] - low[0])
                return [a + (b - a) * ratio for a, b in zip(low[1:], high[1:])]
        raise ValueError(height)

    for side in [-1, 1]:
        title = "Left" if side < 0 else "Right"
        grip = sculpture(title + " · co-moulded sleeve")
        heights = sorted(
            {row[0] for row in handle} | set(range(-103, -95)) | set(range(-49, -33))
        )
        rows, colors = [], []
        for height in heights:
            x, width, thick, shoulder = section(height)
            boundary = [
                (-math.pi / 2, shoulder, 14),
                (shoulder, math.pi - shoulder, 12),
                (math.pi - shoulder, math.pi * 1.5, 14),
            ]
            row, colors = [], []
            for j, (a, b, count) in enumerate(boundary):
                for i in range(count):
                    angle = a + (b - a) * i / count
                    s, c = math.sin(angle), math.cos(angle)
                    ribs = 0
                    if -49 <= height <= -34 or -103 <= height <= -96:
                        ribs = (
                            max(0, s) ** 8
                            * math.sin((height + 107) * math.pi / 2) ** 4
                            * 0.39
                        )
                    row.append(
                        (
                            side
                            * (x + math.copysign(abs(s) ** 0.9, s) * (width + ribs)),
                            height,
                            math.copysign(abs(c) ** 0.84, c) * thick,
                        )
                    )
                    colors.append(blue if j == 1 else red)
            rows.append(row)
        grip.rings(rows, red)
        grip.materials.append(blue)
        n = len(colors)
        grip.inks[: (len(rows) - 1) * n] = [int(m == blue) for m in colors] * (
            len(rows) - 1
        )
        for face in [-1, 1]:

            def projection(u, v):
                height = -70 + u * face
                x, width, thick, _ = section(height)
                offset = -side * v - 0.92
                s = math.copysign(abs(offset / width) ** (1 / 0.9), offset)
                return (
                    side * (x + offset),
                    height,
                    face * (thick * (1 - s * s) ** 0.42 + 0.044),
                )

            caption = "78 61 125" if side < 0 else "cap. Cu Ø 1,6 mm / medium Ø 1,2 mm"
            grip.label(caption, 2.75 if side < 0 else 1.8, projection, ink)

        def outer_stamp(u, v):
            height = -68 + side * u
            x, width, thick, _ = section(height)
            position = width * (1 - abs(v / thick) ** (2 / 0.84)) ** 0.45
            return side * (x + position + 0.055), height, v

        grip.label("KNIPEX", 6.25, outer_stamp, red)
        keep(grip)
        jaw = sculpture(title + " · shear arm and ground edge")
        rows = []
        for h, x, width, back, front in [
            (-37, 15.6, 3, -1.6, 1.65),
            (-24, 12.1, 3.85, -1.75, 1.8),
            (-21, 11.7, 4.05, -1.75, 1.85),
            (-15, 7.45, 3.85, -1.75, 1.95),
            (-10, 4.4, 4.05, -1.77, 2.0),
            (-6, 1.8, 4.85, -1.8, 2.0),
            (-3, 0.45, 5.91, -1.8, 2.0),
            (-1.55, 0.14, 6.46, -1.8, 2.0),
            (0, 0, 6.75, -1.8, 2.0),
            (1.55, -0.14, 6.43, -1.8, 2.0),
            (3, -0.41, 6.04, -1.8, 2.0),
            (4.2, -1.17, 5.29, -1.76, 1.95),
            (5.4, -2.17, 4.32, -1.65, 1.91),
        ]:
            lap = side * 1.76 * min(1, max(0, (h + 20) / 12))
            chamfer = 0.43
            rows.append(
                [
                    (side * (x + dx), h, lap + d)
                    for dx, d in [
                        (-width + chamfer, front),
                        (width - chamfer, front),
                        (width, front - chamfer),
                        (width, back + chamfer),
                        (width - chamfer, back),
                        (-width + chamfer, back),
                        (-width, back + chamfer),
                        (-width, front - chamfer),
                    ]
                ]
            )
        first_edge = len(rows) + 2
        for h, gap, outer, flush, ridge, tail in [
            (6.5, -0.32, 6.48, 2.71, 3.56, -3.10),
            (7.6, -0.04, 6.37, 3.12, 4.07, -2.78),
            (9.0, 0.14, 5.77, 3.71, 4.52, -2.39),
            (11.5, 0.36, 4.78, 4.37, 4.98, -1.59),
            (15.4, 0.64, 2.92, 5.35, 5.65, 0.54),
            (17.72, 0.84, 1.59, 5.92, 6.03, 3.35),
            (18, 0.94, 1.29, 5.97, 6.0, 4.91),
        ]:
            mid = gap + min(1.16, (outer - gap) * 0.28)
            rowspec = [
                (outer - min(0.3, (outer - gap) * 0.15), ridge),
                (mid, ridge),
                (gap, flush),
                (gap + 0.016, flush - 0.08),
                (gap + min(0.16, (outer - gap) * 0.12), flush - 0.30),
                (mid + (outer - mid) * 0.18, tail),
                (outer - min(0.14, (outer - gap) * 0.1), tail + 0.11),
                (outer, ridge - 0.31),
            ]
            rows.append([(-side * x, h, d) for x, d in rowspec])
        jaw.rings(rows, forged, False)
        ground_index = len(jaw.materials)
        jaw.materials.append(ground)
        for i in range(first_edge, len(rows) - 1):
            for j in (1, 2, 3, 4):
                jaw.inks[i * 8 + j] = ground_index
        if side > 0:

            def stamp(u, v):
                h = -15 + u
                x = 7.45 - (0.61 if h > -15 else 0.708) * (h + 15)
                d = 1.95 + (h + 15) * (0.01 if h > -15 else 0.0167)
                return x - v, h, d + min(1, max(0, (h + 20) / 12)) * 1.76 + 0.025

            jaw.label("KNIPEX", 1.83, stamp, ink)
        keep(jaw)
    pivot = sculpture("Spun stainless rivet · factory and upset heads")
    spun = chrome.copy()
    spun.name = "Knipex · satin rivet head"
    spun.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.47
    for sign in [-1, 1]:
        dial(
            pivot,
            0,
            0,
            [
                (0.02, sign * 3.78),
                (3.91, sign * 3.78),
                (4.02, sign * 3.85),
                (3.92, sign * 4.0),
                (3.5, sign * 4.13),
                (3.32, sign * 4.15),
                (0.02, sign * 4.20),
            ],
            spun,
        )
    keep(pivot)
    limiter = sculpture("Opening stop · shouldered stud")
    for r, d in [(1.75, 3.68), (1.65, 3.91)]:
        dial(
            limiter,
            2.25,
            -7.3,
            [(0.02, d), (r, d), (r - 0.12, d + 0.2), (0.02, d + 0.21)],
            forged,
        )
    keep(limiter)
    spring = sculpture("Opening spring · two anchored legs and coil")
    points = [(-6.8, -14.2, -2.07), (-5.9, -14, -2.95), (-3.6, -10.8, -3.08)]
    for i in range(60):
        a = math.pi + i / 59 * math.tau * 2.25
        points.append(
            (1.65 * math.cos(a), -7.9 + 1.65 * math.sin(a), -3.14 + i / 59 * 0.78)
        )
    points.extend([(3.8, -12.6, -2.44), (5.25, -14.0, -2.23), (6.5, -14.7, -1.87)])
    spring.pipe(points, 0.38, chrome, 10)
    keep(spring)
    assembly = bpy.data.collections.new("KNIPEX 78 61 125")
    bpy.context.scene.collection.children.link(assembly)
    for obj in [root, *parts]:
        assembly.objects.link(obj)
        bpy.context.collection.objects.unlink(obj)
    return root, parts
