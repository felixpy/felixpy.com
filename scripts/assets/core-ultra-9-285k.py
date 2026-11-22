import math
import sys

import bpy
import numpy as np
from mathutils import Vector


def marked_nickel(material, letters):
    width, height = 624, 960
    w, h = 25.6, 40
    mask = np.zeros((height, width), dtype=np.float32)

    def triangle(vertices):
        p = np.array(
            [((x / w + 0.5) * width, (0.5 - y / h) * height) for x, y in vertices]
        )
        x0, y0 = np.maximum(0, np.floor(p.min(axis=0))).astype(int)
        x1, y1 = np.minimum((width, height), np.ceil(p.max(axis=0))).astype(int)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.ogrid[y0:y1, x0:x1]
        edges = [
            (b[0] - a[0]) * (yy + 0.5 - a[1]) - (b[1] - a[1]) * (xx + 0.5 - a[0])
            for a, b in zip(p, np.roll(p, -1, axis=0))
        ]
        inside = (np.minimum.reduce(edges) >= 0) | (np.maximum.reduce(edges) <= 0)
        mask[y0:y1, x0:x1][inside] = 1

    def line(a, b, thickness):
        v = np.array(b) - a
        n = np.array((-v[1], v[0])) * (thickness * 0.5 / np.linalg.norm(v))
        corners = (a + n, b + n, b - n, a - n)
        triangle(corners[:3])
        triangle((corners[0], corners[2], corners[3]))

    def outline(vertices, thickness):
        p = np.array(vertices)
        for a, b in zip(p, np.roll(p, -1, axis=0)):
            line(a, b, thickness)

    for v, text, size in [
        (-8.1, "INTEL CORE ULTRA 9", 1.95),
        (-5.15, "285K", 1.95),
        (-2.2, "SRQD5", 1.95),
        (0.75, "L434G459", 1.95),
    ]:
        vertices, face_indices = letters(text, False)
        left = min(x for x, _ in vertices)
        for face in face_indices:
            triangle(
                [
                    (-9.24 + (vertices[i][0] - left) * size, v - vertices[i][1] * size)
                    for i in face
                ]
            )

    outline([(-9.15, -13), (-7.83, -13), (-7.83, -11.55), (-9.15, -11.55)], 0.115)
    outline([(-7.76, -11.48), (-7.17, -11.48), (-7.17, -10.85), (-7.76, -10.85)], 0.11)
    outline([(-9.12, 14.7), (-9.12, 17.16), (-6.55, 17.16)], 0.14)
    outline([(-8.76, 15.56), (-8.76, 16.8), (-7.43, 16.8)], 0.11)
    outline(
        [
            (
                1.92 + 0.86 * math.cos(i * math.tau / 32),
                0.8 + 0.86 * math.sin(i * math.tau / 32),
            )
            for i in range(32)
        ],
        0.105,
    )
    matrix = (
        "10101010101010101010101010101010",
        "11010100100110111001110111011011",
        "11011000011101101010101011111110",
        "11011011000000111011001100111001",
        "10001110000010101111000011001010",
        "11111000010001111110100100101001",
        "10010110010100001101111100010100",
        "11111111111111111111111111111111",
    )
    for row, bits in enumerate(matrix):
        for col, bit in enumerate(bits):
            if bit == "1":
                x, y = -9.24 + col * 0.22, 3.0 + row * 0.24
                triangle([(x, y), (x + 0.22, y), (x, y + 0.24)])
                triangle([(x + 0.22, y), (x + 0.22, y + 0.24), (x, y + 0.24)])
    image = bpy.data.images.new(
        "285K • nickel finish and etched lot markings", width, height, alpha=False
    )
    rng = np.random.default_rng(285)
    variation = rng.normal(0, 0.003, (height, width)) + rng.normal(
        0, 0.0018, (height, 1)
    )
    rgba = np.ones((height, width, 4), dtype=np.float32)
    for index, (base, laser) in enumerate(
        zip((0.725, 0.727, 0.715), (0.32, 0.328, 0.319))
    ):
        rgba[:, :, index] = base + mask * (laser - base) + variation
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    tex = material.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    material.node_tree.links.new(
        tex.outputs["Color"],
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    return w, h


def build(Part, coating, point, rectangle, letters):
    cpu = bpy.data.collections.new("LGA1851 processor package")
    cpu.use_fake_user = True
    cpu["model"] = "Intel Core Ultra 9 285K"
    cpu["specCode"] = "SRQD5"
    cpu["socket"] = "FCLGA1851"
    laminate = coating("285K • teal package solder mask", "205c58", 0.24, 0.44)
    etched = coating("285K • laser-marked nickel", "c1c2be", 0.85, 0.36)
    nickel = coating("285K • nickel-plated copper", "c1c2be", 0.85, 0.35)
    seal = coating("285K • lid adhesive", "31302e", 0, 0.71)
    plating = coating("285K • hard gold contact plating", "e7c46c", 0.83, 0.34)
    ceramic = coating("285K • ceramic bypass capacitors", "726655", 0.08, 0.57)
    terminal = coating("285K • tin terminations", "a8a9a4", 0.79, 0.37)
    body = Part("285K • keyed organic package substrate")
    edge = []
    for y, sign in [(-22.5, 1), (22.5, -1)]:
        notch = [
            (
                14.7 + 0.76 * math.cos(i * math.pi / 12),
                y + sign * 0.76 * math.sin(i * math.pi / 12),
            )
            for i in range(13)
        ]
        edge.extend(
            [(-18.75, y), *reversed(notch), (18.75, y)]
            if sign == 1
            else [(18.75, y), *notch, (-18.75, y)]
        )
    body.solid(edge, -4.4, 1.09, laminate)
    for x in (-18, 18):
        for y in (-21.76, 21.76):
            body.disc(x, y, -3.31, 0.245, 0.012, plating, 16)
        for y in (-13.2, -12, 17.9, 18.9):
            body.box(x, y, -3.31, 0.74, 0.4, 0.045, terminal)
    body.make(cpu)

    lid = Part("Intel Core Ultra 9 285K • stepped integrated heat spreader")
    flange_half = [
        (0, -21.15),
        (13.75, -21.15),
        (15.35, -19.75),
        (15.65, -19.05),
        (15.65, -9.55),
        (16.00, -8.75),
        (17.33, -7.9),
        (17.84, -7.02),
        (17.84, 6.58),
        (17.26, 7.6),
        (16.03, 8.36),
        (15.65, 9.13),
        (15.65, 18.95),
        (15.28, 19.82),
        (13.85, 21.1),
        (0, 21.1),
    ]
    flange = flange_half + [(-x, y) for x, y in reversed(flange_half[1:-1])]

    def flange_ring(scale, z):
        return [point(x * scale, y * scale, z) for x, y in flange]

    lid.rings([flange_ring(0.983, -3.31), flange_ring(0.983, -3.08)], seal, False)
    lid.rings(
        [
            flange_ring(0.987, -3.08),
            flange_ring(1, -2.99),
            flange_ring(1, -2.64),
            flange_ring(0.995, -2.55),
        ],
        nickel,
        False,
    )
    profiles = [
        (27.7, 40.15, 2.95, -2.55),
        (27.3, 39.95, 2.8, -2.35),
        (26.65, 39.64, 2.7, -0.98),
        (26.2, 39.27, 2.63, -0.43),
        (25.68, 38.71, 2.56, -0.12),
        (24.96, 38.06, 2.45, 0),
    ]
    ridges = [
        [point(x, y, z) for x, y in rectangle(0, 0, w, h, r)] for w, h, r, z in profiles
    ]
    lid.rings(ridges, nickel, True, False)
    lid.add(ridges[-1], [tuple(reversed(range(len(ridges[-1]))))], etched, False)
    cover = lid.make(cpu)
    cover["specCode"] = "SRQD5"
    w, h = marked_nickel(etched, letters)
    uv = cover.data.uv_layers.new(name="UVMap")
    for polygon in cover.data.polygons:
        for i in polygon.loop_indices:
            v = cover.data.vertices[cover.data.loops[i].vertex_index].co
            uv.data[i].uv = (0.5 + v.x * 1000 / w, 0.5 + v.z * 1000 / h)

    contacts = Part("285K • underside LGA contact lands")
    omitted = {
        *((x, y) for y, span in enumerate((3, 1)) for x in range(span)),
        *((43 - x, y) for y, span in enumerate((3, 1)) for x in range(span)),
        *((x, 51 - y) for y, span in enumerate((7, 6, 5, 4)) for x in range(span)),
        (43, 51),
    }
    count = 0
    for r in range(52):
        for c in range(44):
            if (15 <= c < 29 and 11 <= r < 40) or (c, r) in omitted:
                continue
            x, y = (c - 21.5) * 0.834 + (r % 2 - 0.5) * 0.135, (r - 25.5) * 0.844
            oval = [
                point(
                    x + 0.295 * math.cos(i * math.tau / 12),
                    y + 0.346 * math.sin(i * math.tau / 12),
                    -4.412,
                )
                for i in range(12)
            ]
            contacts.add(oval, [tuple(range(len(oval)))], plating, False)
            count += 1
    assert count == 1851
    lands = contacts.make(cpu)
    lands["installedHidden"] = True
    lands["landCount"] = count

    passives = Part("285K • underside decoupling network")

    def mlcc(back_x, v, width, length, horizontal=False):
        height = width * 0.54
        body_w, body_l = width, length * 0.64
        contact_w, contact_l = width * 1.015, length * 0.18
        if horizontal:
            body_w, body_l = body_l, body_w
            contact_w, contact_l = contact_l, contact_w
        passives.box(-back_x, v, -4.4 - height, body_w, body_l, height, ceramic)
        for direction in (-1, 1):
            offset = direction * length * 0.41
            passives.box(
                -back_x + (offset if horizontal else 0),
                v + (0 if horizontal else offset),
                -4.408 - height,
                contact_w,
                contact_l,
                height + 0.008,
                terminal,
            )

    for v in (-11.35, -8.25, -6.1, -3.95, -0.85):
        for x in (-5.05, -4.49, -3.93, -3.37, -2.81, -0.4, 0.16, 0.72, 1.28, 1.84):
            mlcc(x, v, 0.29, 0.72)
    for v in (-9.35, -7.12, -5.0, -1.94):
        for x in (-5.05, -2.81, -0.40, 1.84):
            mlcc(x, v, 0.26, 0.65)
    for v in (-10.32, -3.0):
        for x in (-4.85, -3.55, 0.22, 1.54):
            mlcc(x, v, 0.35, 1.03, True)
    for x, v in [
        (-1.99, -11.12),
        (-0.91, -11.12),
        (2.84, -9.55),
        (-1.99, -7.8),
        (2.83, -4.83),
        (-1.99, -3.42),
        (-0.91, -3.42),
        (2.84, -3.23),
        (3.75, -3.23),
        (-1.99, -1.7),
        (2.83, -1.67),
        (3.75, -1.67),
        (4.62, -1.67),
        (-3.88, 0.98),
        (0.08, 1.83),
        (-2.05, 3.06),
        (-0.91, 3.14),
        (3.78, 2.86),
        (-0.89, 4.78),
        (1.8, 4.59),
        (3.78, 4.33),
        (4.70, 6.04),
        (-0.9, 6.37),
        (2.8, 7.62),
        (3.76, 8.1),
        (-0.29, 9.23),
        (0.66, 9.23),
        (1.55, 9.23),
    ]:
        mlcc(x, v, 0.60, 1.3)
    for x, v in [(-4.63, 3.35), (-4.66, 5.5), (-4.65, 7.65), (0.27, 8.15)]:
        mlcc(x, v, 0.49, 1.13, True)
    for v, start in [(9.56, 2.34), (10.55, 3.08)]:
        for i in range(4):
            mlcc(start + i * 0.52, v, 0.28, 0.72)
    passives.make(cpu)["installedHidden"] = True
    return cpu


def save_inspection_scene(source, destination):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Intel Core Ultra 9 285K"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    with bpy.data.libraries.load(source, link=False) as (_, contents):
        contents.collections = ["LGA1851 processor package"]
    scene.collection.children.link(contents.collections[0])
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.clip_start = 0.00015
            space.clip_end = 20
            space.overlay.show_overlays = False
            space.shading.type = "MATERIAL"
            space.shading.studio_light = "studio.exr"
            space.shading.studiolight_rotate_z = 0.55
            space.region_3d.view_perspective = "ORTHO"
            space.region_3d.view_distance = 0.078
            space.region_3d.view_location = (0, 0.002, 0)
            space.region_3d.view_rotation = Vector(
                (0.036, -0.155, 0.039)
            ).to_track_quat("Z", "Y")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=destination, compress=True)


if __name__ == "__main__":
    save_inspection_scene(*sys.argv[sys.argv.index("--") + 1 :])
