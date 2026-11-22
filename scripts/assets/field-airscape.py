import math

import bpy


def spacer_mesh(material):
    size = 192
    heights = []
    tint = []
    for y in range(size):
        v = y / size * 24
        for x in range(size):
            u = x / size * 24 - 0.5 * (int(v) % 2)
            xx = (u + 0.5) % 1 - 0.5
            yy = v % 1 - 0.5
            hole = min(1, ((xx / 0.49) ** 2 + (yy / 0.48) ** 2) ** 0.55)
            twist = math.cos(math.tau * (2 * u + 1.5 * v))
            yarn = hole**1.55 * (0.77 + 0.23 * twist)
            heights.append(yarn)
            tone = 0.150 + 0.147 * yarn
            tint.extend((tone * 0.96, tone * 0.985, tone, 1))
    normals = []
    for y in range(size):
        for x in range(size):
            dx = heights[y * size + (x + 1) % size] - heights[y * size + (x - 1) % size]
            dy = (
                heights[((y + 1) % size) * size + x]
                - heights[((y - 1) % size) * size + x]
            )
            inv = 1 / math.sqrt(1 + 1.65**2 * (dx * dx + dy * dy))
            normals.extend(
                (0.5 - 0.825 * dx * inv, 0.5 - 0.825 * dy * inv, 0.5 + 0.5 * inv, 1)
            )
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes["Principled BSDF"]
    for name, pixels, raw in [
        ("knitted face", tint, False),
        ("rib relief", normals, True),
    ]:
        image = bpy.data.images.new(
            "AirScape · " + name, width=size, height=size, is_data=raw
        )
        image.pixels.foreach_set(pixels)
        image.pack()
        tile = nodes.new("ShaderNodeTexImage")
        tile.image = image
        if raw:
            normal = nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = 0.67
            links.new(tile.outputs["Color"], normal.inputs["Color"])
            links.new(normal.outputs["Normal"], shader.inputs["Normal"])
        else:
            links.new(tile.outputs["Color"], shader.inputs["Base Color"])
    return material


def backpanel(part, sheet, rear, web, nylon, mesh, foam, frame, binding, markings):
    shell = part("Talon 26 · moulded AirScape framesheet and index rails")
    pads = part("Talon 26 · die-cut EVA ventilating cushions")
    facing = part("Talon 26 · contoured spacer mesh and wraparound lumbar")
    yoke = part("Talon 26 · sliding torso yoke and lapped sleeve")

    def pt(u, h, depth=0):
        width = 63 + 35 * max(0, math.sin(math.pi * (h - 28) / 440)) ** 0.62
        return rear(u * width, h, 5.8 + 6 * (1 - u * u) + depth)

    def inset(rows, amount):
        return [[(x, h, d + amount) for x, h, d in row] for row in rows]

    def solid(obj, front, back, mat):
        w, h = len(front[0]), len(front)
        n = w * h
        quads = [
            (j * w + i, (j + 1) * w + i, (j + 1) * w + i + 1, j * w + i + 1)
            for j in range(h - 1)
            for i in range(w - 1)
        ]
        rim = (
            list(range(w))
            + [j * w + w - 1 for j in range(1, h)]
            + list(range(n - 2, n - w - 1, -1))
            + [j * w for j in range(h - 2, 0, -1)]
        )
        sides = [(a, b, b + n, a + n) for a, b in zip(rim, rim[1:] + rim[:1])]
        faces = quads + [tuple(k + n for k in reversed(face)) for face in quads] + sides
        obj.add(
            [p for layer in (front, back) for row in layer for p in row], faces, mat
        )

    def seam(obj, path, radius, mat):
        for i in range(0, len(path) - 1, 2):
            obj.pipe(path[i : i + 2], radius, mat, 5)

    grid = [[pt(i / 16, 30 + j * 429 / 36) for i in range(-16, 17)] for j in range(37)]
    solid(shell, grid, inset(grid, 2.5), frame)
    mesh_liner = [
        [pt(i / 12 * 0.825, 128 + j * 234 / 23, 0.21) for i in range(-12, 13)]
        for j in range(24)
    ]
    sheet(facing, mesh_liner, web)
    for s in (-1, 1):
        rail = [
            [
                pt(
                    s * (0.815 + i * 0.040),
                    37 + j * 419 / 36,
                    2.8 + 4.5 * math.sin(i * math.pi / 5),
                )
                for i in range(6)
            ]
            for j in range(37)
        ]
        top = rail if s == 1 else [row[::-1] for row in rail]
        solid(shell, top, inset(top, 7.55), frame)
        for h in range(283, 429, 25):
            shell.pipe(
                [pt(s * u, h, 7.1) for u in (0.862, 0.892, 0.925)], 0.46, markings, 6
            )
        shell.label(
            "AIRSCAPE",
            4.2,
            lambda x, y, s=s: pt(s * (0.885 + y / 85), 213 + s * x, 7.6),
            markings,
        )

    for center, height in [
        (151, 19),
        (178, 18),
        (206, 19),
        (234, 18),
        (262, 18),
        (290, 19),
        (318, 17),
        (346, 17),
    ]:

        def shoulder_face(u, v, bed=False):
            side = abs(u)
            h = (
                center
                - 7.5 * math.exp(-((u / 0.43) ** 2))
                + v * height * (0.40 + 0.10 * side)
                + 1.7 * math.sin(math.pi * u)
            )
            raised = (1 - v * v) ** 0.72 * (0.83 + 0.17 * math.cos(math.pi * u / 2))
            return pt(u * 0.832, h, -0.38 if bed else 1.2 + 6.4 * raised)

        grid = [
            [shoulder_face((i - 12) / 12, (j - 3) / 3) for i in range(25)]
            for j in range(7)
        ]
        foam_face = inset(grid, 0.55)
        bed = [
            [shoulder_face((i - 12) / 12, (j - 3) / 3, True) for i in range(25)]
            for j in range(7)
        ]
        solid(facing, grid, foam_face, mesh)
        solid(pads, foam_face, bed, foam)

    def lumbar(u, v, bed=False):
        shape = 0.84 - 0.30 * v + 0.07 * math.sin(v * math.pi)
        height = 31 + v * 109 + 5 * u * u * (1 - v) - 8 * u * u * v
        crown = 15.5 * (max(0, 1 - u * u) ** 0.70) * (math.sin(v * math.pi) ** 0.64)
        return pt(u * shape, height, -0.38 if bed else 2.4 + crown)

    grid = [[lumbar((i - 14) / 14, j / 16) for i in range(29)] for j in range(17)]
    foam_face = inset(grid, 0.55)
    bed = [[lumbar((i - 14) / 14, j / 16, True) for i in range(29)] for j in range(17)]
    solid(facing, grid, foam_face, mesh)
    solid(pads, foam_face, bed, foam)
    facing.pipe(grid[0], 1.35, binding, 7)
    for s in (-1, 1):
        inner = [lumbar(s, j / 16) for j in range(17)]
        outside = [
            pt(
                s * (0.93 - 0.07 * j / 16),
                40 + j * 127 / 16,
                1.9 + 1.1 * math.sin(j / 16 * math.pi),
            )
            for j in range(17)
        ]
        rows = [[a, b] if s == 1 else [b, a] for a, b in zip(inner, outside)]
        sheet(facing, rows, web)
        facing.pipe(inner, 0.85, binding, 6)

    def yokept(u, v, offset=0):
        h = 357 + v * 70 + 10 * u * u - 5 * (1 - u * u) * math.sin(math.pi * v)
        span = 68 + v * 4 - 7 * math.sin(v * math.pi)
        return rear(
            u * span, h, 15.5 + 5.8 * (1 - u * u) + 2.8 * math.sin(v * math.pi) + offset
        )

    for a, b in ((0, 0.74), (0.68, 1)):
        grid = [
            [
                yokept((i - 13) / 13, a + (b - a) * j / 9, 0 if a == 0 else 1.65)
                for i in range(27)
            ]
            for j in range(10)
        ]
        solid(yoke, grid, inset(grid, 2.1), nylon)
        yoke.pipe(grid[0], 0.8, binding, 7)
        seam(
            yoke,
            [
                yokept((i - 25) / 25, a + 0.035, 0.75 if a == 0 else 2.35)
                for i in range(51)
            ],
            0.3,
            binding,
        )
