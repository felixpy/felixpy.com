import math

import bpy
import numpy as np


def distance_polygon(x, y, vertices):
    inside = np.zeros(np.broadcast_shapes(x.shape, y.shape), dtype=bool)
    nearest = np.full(inside.shape, 1e6, dtype="f")
    for i, (ax, ay) in enumerate(vertices):
        bx, by = vertices[(i + 1) % len(vertices)]
        dx, dy = bx - ax, by - ay
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        nearest = np.minimum(nearest, (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2)
        if abs(dy) > 1e-8:
            inside ^= ((ay > y) != (by > y)) & (x < (y - ay) * dx / dy + ax)
    return np.where(inside, np.sqrt(nearest), -np.sqrt(nearest))


def field(angle, z, pixel=False):
    x = angle * 15
    a = np.abs(x)
    t = z - 379
    shade = np.zeros(np.broadcast_shapes(angle.shape, z.shape), dtype="f") + 0.99
    relief = np.zeros_like(shade)
    paint = (
        np.broadcast_to(np.float32([145, 27, 39]), (*shade.shape, 3)).copy()
        if pixel
        else None
    )

    def region(d, colour, thickness, bevel=0.55, dark_seam=0.27):
        nonlocal relief, paint
        blend = np.clip(0.5 + d / 0.15, 0, 1)
        lip = np.clip((d + 0.04) / bevel, 0, 1)
        relief += thickness * lip
        incision = np.clip(1 - np.abs(d + 0.12) / max(dark_seam, 0.01), 0, 1)
        relief -= incision * 0.12
        if paint is not None:
            paint = (
                paint * (1 - blend[:, :, None])
                + np.array(colour, dtype="f") * blend[:, :, None]
            )
            paint *= (1 - incision * 0.34)[:, :, None]

    def poly(xx, vertices, colour, thickness, bevel=0.55, dark_seam=0.27):
        region(distance_polygon(xx, t, vertices), colour, thickness, bevel, dark_seam)

    poly(
        a,
        [
            (12.0, 38.3),
            (16.4, 37.0),
            (22.7, 33.6),
            (27.5, 31),
            (27.6, 27.8),
            (24, 25.2),
            (21.0, 26.0),
            (19.7, 32.5),
            (15.4, 35),
        ],
        (121, 24, 36),
        0.18,
    )
    poly(
        a,
        [
            (20, 31.3),
            (25, 28.5),
            (25.8, 20.3),
            (23.1, 17.5),
            (20, 17.1),
            (16.3, 19.5),
            (17, 25.2),
        ],
        (66, 52, 59),
        0.22,
    )
    poly(
        a,
        [
            (21.0, 28.7),
            (23, 28.1),
            (24.8, 26.3),
            (24.9, 21.7),
            (22.8, 20.6),
            (20, 21.7),
            (19.6, 25.2),
        ],
        (132, 29, 42),
        0.46,
    )
    poly(
        a,
        [
            (29.2, 27),
            (33.5, 23.1),
            (38, 22.6),
            (44, 23.8),
            (47.3, 24.1),
            (47.3, 17.1),
            (40.2, 16.2),
            (34.9, 16.9),
            (29.8, 20.4),
        ],
        (130, 25, 38),
        0.16,
    )
    poly(
        a,
        [
            (15.5, 18.8),
            (19.0, 19.2),
            (22.8, 17.4),
            (26, 17.4),
            (29.4, 19.4),
            (28.3, 12.4),
            (24.2, 8.6),
            (18, 5.7),
            (11.5, 1.75),
            (10.7, 3.5),
            (15.8, 9.8),
            (17, 13),
        ],
        (122, 27, 40),
        0.58,
    )
    poly(
        a,
        [
            (16.7, 15.4),
            (18.7, 15.8),
            (18.4, 12.3),
            (15.3, 8.1),
            (10.2, 4.1),
            (10.9, 6.5),
            (14.6, 11.5),
        ],
        (103, 98, 92),
        0.28,
        0.2,
        0.17,
    )
    visor = [
        (-17.0, 33.4),
        (-16.4, 35.4),
        (-12.8, 36.1),
        (-8, 34.6),
        (-3.3, 30.7),
        (-1.3, 29.7),
        (1.5, 29.7),
        (3.7, 30.8),
        (9.3, 35),
        (12.3, 36.2),
        (16.0, 35.8),
        (16.6, 34.4),
        (15.2, 26.0),
        (16.7, 23.1),
        (17, 20.2),
        (14.0, 17),
        (9.5, 13.4),
        (6.3, 9.6),
        (4.8, 7.8),
        (2.3, 8.4),
        (-2.9, 8.4),
        (-5.5, 7.8),
        (-7.1, 9.5),
        (-11.6, 14.1),
        (-15.3, 17.4),
        (-17, 20.5),
        (-16.7, 23.1),
        (-15.1, 26.1),
    ]
    poly(x, visor, (188, 154, 96), 0.70, 0.65)
    nose = np.clip(1 - a / 8.0, 0, 1) * np.clip(1 - np.abs(t - 18) / 9, 0, 1)
    relief += 0.94 * nose
    shade += 0.070 * nose
    lower_cheek = np.clip((t - 8.2) / 3, 0, 1) * np.clip((22.3 - t) / 3.0, 0, 1)
    track = np.interp(t, [8.2, 12.3, 16.5, 21.9], [4.8, 6.9, 10.9, 14.5])
    fold = a - track
    relief += 0.66 * lower_cheek * np.clip(1 - np.abs(fold + 1.4) / 2.9, 0, 1)
    shade -= 0.12 * lower_cheek * np.exp(-abs(fold) / 0.78)
    shade += 0.055 * lower_cheek * np.exp(-abs(fold + 1.7) / 1.4)
    browline = 22.85 + 0.013 * (a - 3) ** 2
    forehead = np.clip((a - 1) / 3, 0, 1) * np.clip((15 - a) / 3, 0, 1)
    relief += 0.70 * forehead * np.exp(-np.abs(t - browline) / 1.7)
    shade -= 0.07 * forehead * np.exp(-np.abs(t - browline + 0.32) / 0.62)
    poly(
        a,
        [
            (5.5, 8.05),
            (6.4, 7.1),
            (6.3, 5.3),
            (4.8, 3.85),
            (2.8, 5.1),
            (-0.1, 5.35),
            (-0.1, 8.2),
            (3.2, 8.1),
        ],
        (174, 137, 83),
        0.64,
        0.36,
    )
    brow = [
        (2.15, 22.2),
        (5.8, 22.5),
        (10.7, 23.35),
        (14.25, 24.1),
        (14.2, 22.6),
        (12.5, 21.45),
        (7.0, 20.9),
        (3.7, 21.0),
    ]
    poly(a, brow, (36, 43, 47), -0.68, 0.34, 0.12)
    slit = [
        (3.45, 21.95),
        (7.4, 22.2),
        (13.2, 23.32),
        (12.4, 22.25),
        (7.0, 21.57),
        (4.4, 21.60),
    ]
    poly(a, slit, (163, 204, 211), 0.20, 0.19, 0.07)
    lower = np.clip((21 - t) / 6, 0, 1) * np.clip((t - 10) / 5, 0, 1)
    shade -= 0.055 * lower * np.exp(-((a - 9.3) ** 2) / 3)
    if pixel:
        return np.uint8(np.clip(paint * shade[:, :, None], 0, 255))
    return relief


def helmet(obj, work):
    profile = np.array(
        [
            (379, -11, -5.7, 6.5, 10, 10),
            (380.0, -11.2, -6.8, 8.65, 12.4, 12),
            (382.8, -11.1, -7.2, 10.8, 15, 13.4),
            (386.7, -11.2, -6.9, 12.4, 16.2, 15.2),
            (392.0, -11.3, -6.15, 13.5, 18.75, 15.65),
            (397.7, -11.3, -6.2, 14.35, 19.05, 16.1),
            (403.8, -11.4, -6.45, 14.25, 18.15, 15.95),
            (409, -11.35, -6.2, 13.9, 17.5, 15.65),
            (412.5, -11.3, -5.9, 13.0, 15.8, 14.9),
            (415.5, -11.5, -5.4, 11.65, 14.4, 13.1),
            (418, -11.6, -5.1, 8.5, 11.0, 10),
            (419.3, -11.7, -5.2, 4.8, 6.7, 6),
            (420, -11.7, -5.3, 0.08, 0.12, 0.12),
        ]
    )

    def shape(a, z):
        vals = []
        for k in range(1, 6):
            knots = profile[:, 0]
            values = profile[:, k]
            slope = np.gradient(values, knots)
            t = np.searchsorted(knots, z, side="right") - 1
            t = np.clip(t, 0, len(knots) - 2)
            span = knots[t + 1] - knots[t]
            u = np.clip((z - knots[t]) / span, 0, 1)
            vals.append(
                (2 * u**3 - 3 * u**2 + 1) * values[t]
                + (u**3 - 2 * u * u + u) * span * slope[t]
                + (-2 * u**3 + 3 * u * u) * values[t + 1]
                + (u**3 - u * u) * span * slope[t + 1]
            )
        cx, cy, rx, fore, aft = vals
        sa, ca = np.sin(a), np.cos(a)
        d = field(a, z)
        xx = np.sign(sa) * abs(sa) ** 0.91 * (rx + d)
        yy = -np.sign(ca) * abs(ca) ** 0.89 * (np.where(ca > 0, fore, aft) + d)
        yaw = -0.23
        return (
            np.stack(
                (
                    cx + xx * np.cos(yaw) - yy * np.sin(yaw),
                    cy + xx * np.sin(yaw) + yy * np.cos(yaw),
                    np.broadcast_to(z, xx.shape),
                ),
                axis=-1,
            )
            / 1000
        )

    segments, rings = 236, 160
    a = np.linspace(-math.pi, math.pi, segments, endpoint=False)[None, :]
    z = np.linspace(379, 420, rings)[:, None]
    pos = shape(a, z).reshape(-1, 3)
    faces = []
    uvs = []
    for j in range(rings - 1):
        for i in range(segments):
            k = (i + 1) % segments
            faces.append(
                (
                    j * segments + i,
                    j * segments + k,
                    (j + 1) * segments + k,
                    (j + 1) * segments + i,
                )
            )
            uvs.extend(
                (
                    (i / segments, j / (rings - 1)),
                    ((i + 1) / segments, j / (rings - 1)),
                    ((i + 1) / segments, (j + 1) / (rings - 1)),
                    (i / segments, (j + 1) / (rings - 1)),
                )
            )
    faces.append(tuple(range(segments - 1, -1, -1)))
    uvs.extend([(0, 0.002)] * segments)
    faces.append(tuple((rings - 1) * segments + i for i in range(segments)))
    uvs.extend([(0, 0.999)] * segments)
    data = bpy.data.meshes.new(
        "Continuous formed helmet shell, faceplate and recessed optical slits"
    )
    data.from_pydata(pos.tolist(), [], faces)
    data.update()
    uv = data.uv_layers.new(name=obj.data.uv_layers.active.name)
    uv.uv.foreach_set("vector", np.asarray(uvs, dtype="f").ravel())
    data.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    tex_w, tex_h = 1536, 768
    aa = np.linspace(-math.pi, math.pi, tex_w)[None, :]
    zz = np.linspace(379, 420, tex_h)[:, None]
    rgb = field(aa, zz, True).astype("f") / 255
    canvas = bpy.data.images.new(
        "MK85 large · painted helmet register", width=tex_w, height=tex_h
    )
    canvas.pixels.foreach_set(
        np.concatenate((rgb, np.ones((tex_h, tex_w, 1), dtype="f")), axis=2).ravel()
    )
    canvas.filepath_raw = str(work / "helmet-enamel.png")
    canvas.file_format = "PNG"
    canvas.save()
    picture = bpy.data.images.load(str(work / "helmet-enamel.png"))
    picture.pack()
    picture.filepath = "//helmet-enamel.png"
    mat = bpy.data.materials.new("MK85 · lacquered helmet and brass faceplate")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = 0.43
    bsdf.inputs["Roughness"].default_value = 0.37
    n = mat.node_tree.nodes.new("ShaderNodeTexImage")
    n.image = picture
    mat.node_tree.links.new(n.outputs["Color"], bsdf.inputs["Base Color"])
    data.materials.append(mat)
    item = bpy.data.objects.new(data.name, data)
    bpy.context.collection.objects.link(item)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    item.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
