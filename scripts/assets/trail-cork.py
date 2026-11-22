import json
import math
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory

import bmesh
import bpy
import numpy as np
import OpenImageIO as oiio
from mathutils import Quaternion, Vector
from mathutils.geometry import delaunay_2d_cdt, tessellate_polygon


def shaft_wordmark():
    design = json.loads(
        Path(__file__)
        .with_name("black-diamond-wordmark.json")
        .read_text(encoding="utf-8")
    )
    width = design["width"]
    height = max(y for glyph in design["glyphs"] for loop in glyph for _, y in loop)
    points, faces = [], []
    for glyph in design["glyphs"]:
        vertices, edges = [], []
        for loop in glyph:
            start = len(vertices)
            vertices.extend(Vector(point) for point in loop)
            edges.extend(
                (start + i - 1 if i else start + len(loop) - 1, start + i)
                for i in range(len(loop))
            )
        result, _, triangles, *_ = delaunay_2d_cdt(vertices, edges, [], 0, 1e-5)
        base = len(points)
        points.extend(
            ((x - width / 2) / width, (y - height / 2) / width) for x, y in result
        )
        for triangle in triangles:
            u, v = sum((result[i] for i in triangle), Vector((0, 0))) / 3
            intersections = sum(
                1
                for loop in glyph
                for (x, y), (nx, ny) in zip(loop, loop[1:] + loop[:1])
                if (y > v) != (ny > v) and u < x + (nx - x) * (v - y) / (ny - y)
            )
            if intersections % 2:
                faces.append(tuple(base + i for i in triangle))
    return points, faces


def cork_surface(material):
    def image(name, pixels, color_space):
        with TemporaryDirectory() as folder:
            path = str(Path(folder) / f"{name}.jpg")
            height, width, _ = pixels.shape
            spec = oiio.ImageSpec(width, height, 3, oiio.UINT8)
            spec.attribute("CompressionQuality", 93 if color_space == "sRGB" else 91)
            spec.attribute("jpeg:subsampling", "4:4:4")
            out = oiio.ImageOutput.create(path)
            if not out.open(path, spec):
                raise RuntimeError(out.geterror())
            data = np.uint8(np.clip(pixels[::-1], 0, 1) * 255 + 0.5)
            if not out.write_image(data):
                raise RuntimeError(out.geterror())
            out.close()
            bitmap = bpy.data.images.load(path)
            bitmap.name = name
            bitmap.colorspace_settings.name = color_space
            bitmap.pack()
            bitmap.filepath = f"//{name}.jpg"
            for packed in bitmap.packed_files:
                packed.filepath = bitmap.filepath
            return bitmap

    size = 384
    rng = np.random.default_rng(112514)
    yy, xx = np.mgrid[:size, :size] * (math.tau / size)
    warm = (
        np.sin(xx * 3 + yy + 1.9 * np.sin(yy * 2))
        + 0.65 * np.sin(yy * 7 - xx * 2 + np.cos(xx * 4))
    ) * 0.017
    cell_count = 48
    cell_x = xx * cell_count / math.tau + 0.18 * np.sin(yy * 37 + np.sin(xx * 17))
    cell_y = yy * cell_count / math.tau + 0.23 * np.sin(xx * 31 + np.cos(yy * 11))
    ix, iy = np.floor(cell_x).astype(int), np.floor(cell_y).astype(int)
    centers = rng.uniform(0.05, 0.95, (cell_count, cell_count, 2))
    tones = rng.normal(0, 0.065, (cell_count, cell_count)).clip(-0.21, 0.15)
    nearest = np.full_like(xx, np.inf)
    second = nearest.copy()
    chips = np.zeros_like(xx)
    for row in (-1, 0, 1):
        for col in (-1, 0, 1):
            key = ((iy + row) % cell_count, (ix + col) % cell_count)
            seed = centers[key]
            distance = (cell_x - ix - col - seed[:, :, 0]) ** 2 + (
                cell_y - iy - row - seed[:, :, 1]
            ) ** 2
            closer = distance < nearest
            second = np.minimum(second, np.where(closer, nearest, distance))
            chips = np.where(closer, tones[key], chips)
            nearest = np.minimum(nearest, distance)
    seams = np.exp(-9 * (second - nearest))
    pore = np.zeros_like(xx)
    for i in range(1840):
        cx, cy = rng.integers(0, size, 2)
        coarse = i < 290
        rx = rng.uniform(2.7, 5.9) if coarse else min(5.2, 0.5 + rng.exponential(1.0))
        ry = rng.uniform(1.2, 3.1) if coarse else min(2.9, 0.44 + rng.exponential(0.57))
        angle = rng.uniform(0, math.pi) if coarse else rng.normal(0.0, 0.48)
        reach = math.ceil(max(rx, ry) * 1.5)
        dy, dx = np.mgrid[-reach : reach + 1, -reach : reach + 1]
        u, v = (
            dx * math.cos(angle) + dy * math.sin(angle),
            dy * math.cos(angle) - dx * math.sin(angle),
        )
        dist = (u / rx) ** 2 + (v / ry) ** 2
        depth = np.maximum(0, 1 - dist * rng.uniform(0.75, 1.27, dist.shape)) ** 0.8
        idx = ((dy + cy) % size, (dx + cx) % size)
        pore[idx] = np.maximum(pore[idx], depth * rng.uniform(0.28, 0.93))
    grain = rng.normal(0, 0.025, (size, size))
    flake = sum(
        np.roll(grain, shift, axis=(0, 1))
        for shift in [(0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (-1, 1)]
    )
    cork = np.array([0.966, 0.713, 0.39])
    rgb = (
        cork * (1 + warm + grain + chips - 0.035 * seams)[:, :, None]
        + flake[:, :, None] * [0.37, 0.81, 0.78]
        - pore[:, :, None] ** 0.77 * [0.48, 0.47, 0.31]
    )
    color = image("Natural cork · russet lenticels", rgb, "sRGB")
    height = grain * 0.22 + chips * 0.48 - seams * 0.08 - pore * 0.68
    normal = np.stack(
        (
            np.roll(height, 1, 1) - np.roll(height, -1, 1),
            np.roll(height, 1, 0) - np.roll(height, -1, 0),
            np.ones_like(pore),
        ),
        axis=-1,
    )
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    graph = material.node_tree
    albedo = graph.nodes.new("ShaderNodeTexImage")
    albedo.image = color
    relief = graph.nodes.new("ShaderNodeTexImage")
    relief.image = image(
        "Natural cork · recessed pores", normal * 0.5 + 0.5, "Non-Color"
    )
    tangent = graph.nodes.new("ShaderNodeNormalMap")
    tangent.inputs["Strength"].default_value = 0.42
    graph.links.new(
        albedo.outputs["Color"], graph.nodes["Principled BSDF"].inputs["Base Color"]
    )
    graph.links.new(relief.outputs["Color"], tangent.inputs["Color"])
    graph.links.new(
        tangent.outputs["Normal"], graph.nodes["Principled BSDF"].inputs["Normal"]
    )


def cork_uv(obj, material, hand):
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    for face in mesh.polygons:
        if mesh.materials[face.material_index] != material:
            continue
        points = [
            mesh.vertices[mesh.loops[i].vertex_index].co for i in face.loop_indices
        ]
        us = [0.5 + math.atan2(p.x, -p.y) / math.tau for p in points]
        seam = max(us) - min(us) > 0.5
        for i, u, p in zip(face.loop_indices, us, points):
            u += int(seam and u < 0.5)
            uv[i].uv = (u + 0.27 * hand, (p.z - 0.474) / 0.085 + 0.36 * hand)


def replaceable_tech_tip(part, mount, nylon, steel, carbide):
    def install(shape, exposed_height, inside=None):
        obj = mount(shape, 2, packed_height=exposed_height)
        data = obj.data
        for uv in list(data.uv_layers):
            data.uv_layers.remove(uv)
        mesh = bmesh.new()
        mesh.from_mesh(data)
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-8)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(data)
        mesh.free()
        if inside:
            enclosed = data.attributes.new("insideInstalledJoint", "BOOLEAN", "POINT")
            for vertex in data.vertices:
                x, y, z = vertex.co * 1000
                enclosed.data[vertex.index].value = inside(math.hypot(x, y), z)

    def ring(h, radius, count):
        return [
            (radius(a) * math.sin(a), h, radius(a) * math.cos(a))
            for a in [math.tau * j / count for j in range(count)]
        ]

    def threaded_rows(clearance, count):
        rows = []
        for j in range(80):
            h = 14.2 + 10.0 * j / 79
            ramp = min(1.0, (h - 14.2) / 0.65, (24.2 - h) / 0.75)

            def radius(a, h=h, ramp=ramp):
                phase = ((h - 14.2) / 1.04 - a / math.tau) % 1.0
                crest = min(1.0, max(0.0, (0.46 - abs(phase - 0.5)) / 0.31))
                return 2.11 + 0.35 * ramp * crest + clearance

            rows.append(ring(h, radius, count))
        return rows

    sleeve = part("BD112082 Flex Tech Tip with open lower socket")
    sleeve.turn(
        [
            (10.36, 4.43),
            (10.54, 4.57),
            (12.8, 4.76),
            (31, 5.37),
            (58.6, 5.90),
            (61.8, 6.05),
            (62.6, 6.57),
            (63.5, 6.96),
            (64.3, 6.96),
            (64.85, 6.24),
            (65.65, 6.21),
            (66.25, 6.98),
            (67.15, 6.98),
            (67.79, 6.30),
            (68.3, 6.31),
            (68.96, 7.00),
            (69.82, 7.0),
            (70.52, 6.7),
            (77.8, 7.08),
            (82.8, 7.38),
            (85.5, 8.68),
            (87.3, 8.71),
            (92.6, 8.25),
            (94.5, 7.51),
            (95, 7.13),
            (95, 6.97),
            (94.45, 6.94),
            (82, 6.79),
            (79.1, 6.62),
            (78.4, 6.46),
            (78.2, 0.025),
        ],
        nylon,
        72,
    )
    outer = ring(10.36, lambda a: 4.43, 72)
    socket = [
        outer,
        ring(10.36, lambda a: 3.52, 72),
        ring(10.67, lambda a: 3.23, 72),
        ring(13.58, lambda a: 3.17, 72),
        ring(14.0, lambda a: 2.69, 72),
        *threaded_rows(0.17, 72),
        ring(24.65, lambda a: 2.65, 72),
        ring(25.20, lambda a: 2.46, 72),
    ]
    sleeve.rings(socket, nylon, close=False)
    sleeve.add(socket[-1], [tuple(range(72))], nylon, False)
    sleeve.add(ring(78.2, lambda a: 0.025, 72), [tuple(range(72))], nylon, False)
    install(sleeve, 95.0, lambda radius, h: 10.6 < h < 25.4 and radius < 3.51)

    body = part("BD112119 threaded stainless Tech Tip carrier")
    rows = []
    for h, r, depth in [
        (4.12, 2.57, 0),
        (4.26, 2.69, 0),
        (5.00, 2.96, 0),
        (6.40, 3.77, 0),
        (7.30, 4.52, 0),
        (7.56, 4.78, 0.07),
        (7.85, 4.81, 0.15),
        (9.35, 4.81, 0.15),
        (9.63, 4.78, 0.07),
        (9.85, 4.56, 0),
        (10.17, 3.31, 0),
        (10.38, 3.07, 0),
        (12.92, 3.02, 0),
        (13.65, 2.71, 0),
        (13.95, 2.19, 0),
        (14.2, 2.11, 0),
    ]:
        rows.append(
            ring(
                h,
                lambda a, r=r, h=h, depth=depth: (
                    r
                    - depth * (0.5 + 0.5 * math.cos(48 * a + 0.42 * (h - 7.85))) ** 1.6
                ),
                144,
            )
        )
    body.rings(rows, steel, close=False)
    thread = threaded_rows(0, 144)
    body.rings(thread, steel, close=False)
    body.add(thread[-1], [tuple(range(144))], steel, False)
    seat = [
        ring(h, lambda a, r=r: r, 144)
        for h, r in [
            (4.12, 2.57),
            (4.12, 2.18),
            (4.34, 2.08),
            (7.84, 2.08),
            (8.08, 1.99),
        ]
    ]
    body.rings(seat, steel, close=False)
    body.add(seat[-1], [tuple(range(144))], steel, False)
    install(body, 10.38, lambda radius, h: h > 4.40 and radius < 2.12)

    contact = part("BD112119 press-fit carbide contact pin")
    contact.turn(
        [
            (0.20, 0.025),
            (0.19, 0.80),
            (0.13, 1.40),
            (0.035, 1.80),
            (0, 1.93),
            (0.065, 2.015),
            (0.17, 2.06),
            (4.25, 2.06),
            (7.78, 2.04),
            (7.98, 1.92),
            (7.98, 0.025),
        ],
        carbide,
        72,
    )
    for h in (0.20, 7.98):
        contact.add(ring(h, lambda a: 0.025, 72), [tuple(range(72))], carbide, False)
    install(contact, 4.25)


def model_poles(sculpture, finish, place, textile, letters):
    natural = finish("112514 · natural cork", "d5ad7f", rough=0.88)
    cork_surface(natural)
    tundra = finish(
        "112514 · Tundra lacquer over carbon", "49524b", metal=0.18, rough=0.43
    )
    carbon = finish("112514 · exposed prepreg", "343537", metal=0.12, rough=0.49)
    runpy.run_path(str(Path(__file__).with_name("rog-peripheral-tools.py")))["carbon"](
        carbon
    )
    tpr = finish("112514 · soft touch palm cap", "282a2d", rough=0.52)
    foam = finish("112514 · closed-cell EVA", "292b29", rough=0.93)
    nylon = finish("112514 · Flex Tip nylon", "2e2f30", rough=0.61)
    basket_mat = finish("112514 · EVA trekking basket", "363637", rough=0.78)
    black = finish(
        "FlickLock Pro · black forged aluminium", "343537", metal=0.58, rough=0.34
    )
    steel = finish("FlickLock Pro · stainless pin", "a2a2a0", metal=0.83, rough=0.27)
    hard = finish("112514 · carbide insert", "777871", metal=0.76, rough=0.43)
    tip_steel = finish(
        "BD112119 · dark stainless carrier", "595956", metal=0.86, rough=0.32
    )
    ink = finish("112514 · screened mist white", "e4e5d9", rough=0.60)
    web = textile(
        finish("Solution · charcoal webbing", "26272c", rough=0.90), "Solution warp"
    )
    green = textile(
        finish("Solution · Tundra jacquard wrist flash", "50624f", rough=0.89),
        "Solution flash",
    )
    normal = runpy.run_path(str(Path(__file__).with_name("product-grain.py")))[
        "coat_grain"
    ]
    normal(
        "112514 · moulded foam and shaft texture",
        [(foam, 0.18), (tundra, 0.07)],
    )

    brand_facets = [
        [(-0.55, 0), (0, 0.76), (0.19, 0.49), (-0.17, 0), (0.19, -0.5), (0, -0.76)],
        [(-0.06, 0), (0.25, 0.4), (0.55, 0), (0.25, -0.4)],
    ]
    wordmark = shaft_wordmark()

    def badge(shape, size, mapping, material):
        for outline in brand_facets:
            pts = [mapping(x * size, y * size) for x, y in outline]
            shape.add(pts, [tuple(range(len(pts)))], material, False)

    def printed(mesh, character, height, angle_offset, tube_radius, size):
        points, faces = (
            letters(character, False) if isinstance(character, str) else character
        )
        vertices = []
        triangles = []

        def subdivide(a, b, c):
            p, q, opposite = max(
                ((a, b, c), (b, c, a), (c, a, b)),
                key=lambda edge: abs(edge[0][1] - edge[1][1]),
            )
            if abs(p[1] - q[1]) * size > 1.15:
                middle = tuple((left + right) / 2 for left, right in zip(p, q))
                subdivide(p, middle, opposite)
                subdivide(middle, q, opposite)
                return
            start = len(vertices)
            for x, y in (a, b, c):
                h = height - x * size
                radius = tube_radius(h) if callable(tube_radius) else tube_radius
                theta = (angle_offset + y * size) / radius
                vertices.append(
                    (
                        radius * math.sin(theta),
                        h,
                        radius * math.cos(theta),
                    )
                )
            triangles.append((start, start + 1, start + 2))

        for a, b, c in faces:
            subdivide(points[a], points[b], points[c])
        mesh.add(vertices, triangles, ink, False)

    def rounded(w, h, r):
        pts = []
        for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
            for j in range(7):
                a = (i + j / 6) * math.pi / 2
                pts.append(
                    (
                        sx * (w / 2 - r) + r * math.cos(a),
                        sy * (h / 2 - r) + r * math.sin(a),
                    )
                )
        return pts

    def lever(mesh, h, r):
        a = [(-0.98 + i * (math.tau - 0.28) / 47) for i in range(48)]
        sections = [
            (-10, r * 0.91),
            (-10, r + 1.15),
            (-8.8, r + 2.1),
            (7.6, r + 2.75),
            (9.8, r + 1.75),
            (9.8, r + 0.12),
        ]
        rings = [
            [(rad * math.sin(t), h + y, rad * math.cos(t)) for t in a]
            for y, rad in sections
        ]
        n = len(a)
        faces = [
            (j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i)
            for j in range(5)
            for i in range(n - 1)
        ]
        faces.extend(
            [
                tuple(j * n for j in range(6)),
                tuple(j * n + n - 1 for j in reversed(range(6))),
            ]
        )
        mesh.add([p for row in rings for p in row], faces, black)
        outline = [
            (-14.6, 5.8),
            (-14.1, 6.15),
            (-5.0, 6.4),
            (-2.4, 6.9),
            (1.9, 11.25),
            (3.7, 11.55),
            (12.8, 11.2),
            (15.6, 10.0),
            (16.6, 7.9),
            (16.85, 3.3),
            (16.85, -7.1),
            (16.25, -9.6),
            (14.15, -10.7),
            (4, -11.0),
            (1.8, -10.65),
            (-2.7, -6.7),
            (-4.65, -6.25),
            (-13.95, -6.25),
            (-14.6, -5.85),
            (-14.65, -3.4),
            (-14.25, -2.95),
            (-5.5, -2.95),
            (-3.8, -2.35),
            (-3.3, -1.2),
            (-3.3, 1.55),
            (-4, 2.7),
            (-5.4, 3.15),
            (-14.5, 3.15),
        ]
        outline = [Vector(p) for p in reversed(outline)]
        for _ in range(2):
            outline = [
                p.lerp(q, t)
                for p, q in zip(outline, outline[1:] + outline[:1])
                for t in (0.15, 0.85)
            ]
        eye = [Vector((x + 9.25, y)) for x, y in reversed(rounded(8.4, 11.6, 2.3))]
        contours = (outline, eye)

        def depth(x, y):
            return r + 4.4 - 0.015 * (x - 0.2) ** 2 - 0.009 * y * y

        verts, faces = [], []
        for loop_index, contour in enumerate(contours):
            for inset, level in (
                (0.62, -3.8),
                (0.13, -3.48),
                (0, -2.9),
                (0, -0.84),
                (0.18, -0.39),
                (0.43, -0.11),
                (0.76, 0),
            ):
                for px, py in contour:
                    if loop_index:
                        x, y = (
                            9.25 + (px - 9.25) * (1 + inset / 4.2),
                            py * (1 + inset / 5.8),
                        )
                    else:
                        x, y = px * (1 - inset / 16.85), py * (1 - inset / 11.5)
                    verts.append((x, h + y, depth(x, y) + level))
            n = len(contour)
            base = len(verts) - 7 * n
            for row in range(6):
                start = base + row * n
                faces.extend(
                    (
                        start + i,
                        start + (i + 1) % n,
                        start + n + (i + 1) % n,
                        start + n + i,
                    )
                    for i in range(n)
                )

        for row in (0, 6):
            n, m = len(outline), len(eye)
            rings = [
                list(range(row * n, (row + 1) * n)),
                list(range(7 * n + row * m, 7 * n + (row + 1) * m)),
            ]
            indices = rings[0] + rings[1]
            points = [Vector((verts[i][0], verts[i][1] - h)) for i in indices]
            edges = [(i, (i + 1) % n) for i in range(n)] + [
                (n + i, n + (i + 1) % m) for i in range(m)
            ]
            coords, _, triangles, orig, *_ = delaunay_2d_cdt(
                points, edges, [], 0, 0.00001
            )

            def inside(x, y, loop):
                return (
                    sum(
                        1
                        for p, q in zip(loop, loop[1:] + loop[:1])
                        if (p.y > y) != (q.y > y)
                        and x < (q.x - p.x) * (y - p.y) / (q.y - p.y) + p.x
                    )
                    % 2
                )

            for tri in triangles:
                x, y = sum((coords[i] for i in tri), Vector((0, 0))) / 3
                if inside(x, y, points[:n]) and not inside(x, y, points[n:]):
                    faces.append(tuple(indices[orig[i][0]] for i in tri))
        mesh.add(verts, faces, black)
        for sign in (-1, 1):
            mesh.plate(
                [
                    (x, h + sign * y, r + 1.46 - 0.013 * x * x)
                    for x, y in [
                        (-14.8, 6.45),
                        (-4.5, 6.7),
                        (-2.1, 7.4),
                        (1.4, 10.9),
                        (-13.8, 10.9),
                        (-14.95, 10.35),
                    ]
                ],
                black,
                2.8,
                0.35,
            )
        strip = [
            (-8.9, r + 3.25),
            (-13.7, r + 3.0),
            (-15.15, r + 2.7),
            (-16.2, r + 2.1),
            (-17.1, r + 1.25),
            (-17.45, r - 0.1),
            (-17.5, r - 3.4),
            (-16.9, r - 5.8),
            (-15.65, r - 6.5),
            (-13.9, r - 6.65),
        ]
        rows = []
        for i, (x, d) in enumerate(strip):
            tx, tz = (
                Vector(strip[min(i + 1, len(strip) - 1)]) - Vector(strip[max(0, i - 1)])
            ).normalized()
            rows.append(
                [(x - tz * v, h + y, d + tx * v) for v, y in rounded(1.35, 4.85, 0.42)]
            )
        mesh.rings(rows, steel)
        mesh.pipe(
            [(-12.9, h - 7.5, r - 6.6), (-12.9, h + 7.5, r - 6.6)], 1.45, steel, 20
        )
        badge(mesh, 3.35, lambda x, y: (x, h + y, depth(x, y) + 0.095), nylon)

    wrist_pin_x, wrist_pin_h = 13.6, 596.8

    def wrist(mesh, hand):
        drop = 139
        root_center, root_half_width = -2.95, 2.13
        inner_radius, outer_radius = 1.21, 1.65
        neck_end = 0.069

        def cross(t):
            width = 3.5 + 12.1 * t * t * (3 - 2 * t) + 4.0 * math.sin(math.pi * t) ** 2
            twist = (
                0.31
                + 0.98 * math.exp(-(((t - 0.30) / 0.15) ** 2))
                - 0.23 * t
                + (0.26 if hand < 0 else -0.31) * t**3
            )
            return width * math.cos(twist), width * math.sin(twist)

        def point(t, back, w):
            span, depth = cross(t)
            x = hand * (14 + 44.5 * t - 3.7 * math.sin(math.pi * t) + w * span)
            h = 598 - drop * t + w * (8.1 if hand < 0 else 5.3) * t
            d = (
                -2.5
                + 2.8 * t
                - (2.3 + 15 * math.sin(t * math.pi)) * back
                + w * (depth - 4.2 * back * math.sin(math.pi * t))
            )
            hem = max(0, (t - 0.89) / 0.11) ** 2
            curve = (1 - w * w) * hem
            h += (1.55 if hand < 0 else 2.25) * curve + (
                0.55 if hand < 0 else -0.75
            ) * w**3 * hem
            d += (1.0 if hand < 0 else -1.45) * curve
            if t < neck_end:
                s = t / neck_end
                blend = s * s * (3 - 2 * s)
                root_x = hand * (wrist_pin_x + (2 * back - 1) * outer_radius + 1.4 * s * s)
                root_h = wrist_pin_h - drop * t
                root_d = root_center + w * root_half_width
                x = root_x + (x - root_x) * blend
                h = root_h + (h - root_h) * blend
                d = root_d + (d - root_d) * blend
            return x, h, d

        n = 45
        widths = [-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]
        neck_samples = [neck_end * i / 8 for i in range(9)]
        samples = sorted(set(neck_samples + [i / n for i in range(n + 1)]))
        def panels(rows, material):
            columns = len(rows[0])
            vertices = [vertex for row in rows for vertex in row]
            faces = [
                (i, i + 1, i + 1 + columns, i + columns)
                for r in range(len(rows) - 1)
                for i in range(r * columns, (r + 1) * columns - 1)
            ]
            mesh.add(vertices, faces, material)

        upper = [t for t in samples if t <= neck_end]
        for side in (0, 1):
            for first, last, material in [(0, 33, web), (33, 40, green), (40, n, web)]:
                rows = [
                    [point(t, side, w) for w in widths]
                    for t in samples if first / n <= t <= last / n
                ]
                panels(rows, material)
            for w in (-1, 1):
                mesh.pipe(
                    [point(t, side, w) for t in samples],
                    [0.13 + 0.32 * min(1, t / neck_end) for t in samples],
                    web,
                    5,
                )
            inner = []
            for t in upper:
                thickness = (outer_radius - inner_radius) * (1 - t / neck_end)
                row = [
                    (x - hand * (2 * side - 1) * thickness, h, d)
                    for x, h, d in (point(t, side, w) for w in (-1, 1))
                ]
                inner.append(row)
            panels(inner, web)
            for j, w in enumerate((-1, 1)):
                panels([[point(t, side, w), row[j]] for t, row in zip(upper, inner)], web)
        wraps = []
        for radius in (inner_radius, outer_radius):
            wrap = []
            for i in range(13):
                a = math.pi * i / 12
                x = hand * (wrist_pin_x - radius * math.cos(a))
                h = wrist_pin_h + radius * math.sin(a)
                wrap.append([(x, h, root_center + w * root_half_width) for w in (-1, 1)])
            panels(wrap, web)
            wraps.append(wrap)
        for j in (0, 1):
            panels([[inside[j], outside[j]] for inside, outside in zip(*wraps)], web)
        bend = []
        for j in range(9):
            angle = math.pi * j / 8
            for w in widths:
                x, h, d = point(1, 0, w)
                radius = (d - point(1, 1, w)[2]) / 2
                bend.append(
                    (
                        x,
                        h - radius * math.sin(angle),
                        d - radius * (1 - math.cos(angle)),
                    )
                )
        stride = len(widths)
        mesh.add(
            bend,
            [
                (
                    j * stride + k,
                    j * stride + k + 1,
                    (j + 1) * stride + k + 1,
                    (j + 1) * stride + k,
                )
                for j in range(8)
                for k in range(stride - 1)
            ],
            web,
        )
        for k in (0, stride - 1):
            mesh.pipe([bend[j * stride + k] for j in range(9)], 0.45, web, 5)

        left_flash = [
            [
                (-6.7, 2.6),
                (-4.4, 3.9),
                (0.0, -1.2),
                (6.0, 0.7),
                (7.4, -1.4),
                (-1.0, -4.7),
            ],
            [(-3.4, 4.0), (1.1, 6.3), (4.2, 2.7), (-0.1, 0.1)],
        ]
        right_flash = [
            [
                (-7.3, -1.7),
                (-1.2, 6.1),
                (8.0, 2.6),
                (6.5, 0.3),
                (0.0, 2.3),
                (-4.9, -3.5),
            ],
            [(-2.1, -2.7), (1.0, 1.2), (5.0, -0.5), (2.4, -4.8)],
        ]
        center_x, center_h, _ = point(0.819, 0, 0)

        def thread(x, y):
            t = 0.819 - y / drop
            for _ in range(4):
                cx, _, _ = point(t, 0, 0)
                w = (center_x + x - cx) / (hand * cross(t)[0])
                _, hh, _ = point(t, 0, w)
                t += (hh - center_h - y) / drop
            xx, hh, dd = point(t, 0, w)
            return xx, hh, dd + 0.16

        for outline in left_flash if hand < 0 else right_flash:
            vertices = [thread(x, y) for x, y in outline]
            faces = tessellate_polygon([[Vector((x, y, 0)) for x, y in outline]])
            mesh.add(vertices, faces, ink, False)

    def handle_sleeve(mesh, profile, material, sides, hand):
        def point(x, h, d):
            transition = min(1, max(0, 1 - abs(h - 474.3) / 20))
            return x, h - 0.25 * hand * x * transition, d

        angles = [i * math.tau / sides for i in range(sides)]
        rows = [
            [point(x + w * math.sin(a), h, d + depth * math.cos(a)) for a in angles]
            for x, h, d, w, depth in profile
        ]
        for h in (profile[-1][1], profile[0][1]):
            bore = 8.77 if h < 345 else 8.54
            rows.append(
                [point(bore * math.sin(a), h, bore * math.cos(a)) for a in angles]
            )
        mesh.rings(rows + rows[:1], material, close=False)

    def grip(mesh, hand):
        handle_sleeve(
            mesh,
            [
                (hand * x, y, z, w, d)
                for x, y, z, w, d in [
                    (0, 474.30, 0, 11.55, 12.5),
                    (0, 475.7, 0, 11.6, 13.2),
                    (-0.4, 478.8, 0.3, 12.8, 13.8),
                    (-2.1, 481.4, 0.8, 15.3, 14.1),
                    (-3.3, 484.4, 1.1, 16.5, 14.6),
                    (-3.4, 487.1, 1.2, 16.5, 14.7),
                    (-2.4, 490.2, 1.1, 14.9, 14.3),
                    (-0.3, 496.4, 0.8, 12.2, 13.6),
                    (1.2, 510.5, 0.5, 12.4, 14.2),
                    (2.3, 535.2, 0.2, 13.1, 15.3),
                    (1.0, 557.4, 0, 13.4, 15.8),
                    (-1.3, 576, 0.2, 13.4, 15.7),
                    (-2.9, 588.1, 0.2, 13.1, 15.0),
                    (-3.0, 590.3, 0.2, 12.8, 15.1),
                ]
            ],
            natural,
            56,
            hand,
        )
        mesh.loft(
            [
                (hand * x, y, z, w, d)
                for x, y, z, w, d in [
                    (-2.9, 588.4, 0.2, 13.3, 15.3),
                    (-3.4, 591.3, 0.4, 14.2, 16.4),
                    (-5.5, 594, 0.6, 16.4, 17.8),
                    (-9.2, 597.1, 0.8, 20.8, 18.1),
                    (-11.6, 598.8, 0.8, 23.1, 18.1),
                    (-11.9, 601.6, 0.8, 23.6, 17.9),
                    (-10.9, 604, 0.8, 22.8, 17.0),
                    (-10.2, 606, 0.6, 20.8, 15.6),
                    (-8.4, 608.7, 0.4, 15.9, 12.2),
                    (-7, 609.7, 0.25, 8.7, 7.2),
                    (-6, 610, 0, 2.8, 2.1),
                ]
            ],
            tpr,
            56,
        )
        mesh.form((hand * 3, 599.8, 18), (1.1, 1.1, 0.63), nylon)
        for depth in (-6.4, 0.5):
            mesh.loft(
                [
                    (hand * 14.9, 593.8, depth, 0.8, 0.55),
                    (hand * 14.3, 595.3, depth, 2.25, 0.96),
                    (hand * 13.2, 597.5, depth, 2.8, 1.05),
                    (hand * 11.6, 599.5, depth, 2.95, 1.09),
                    (hand * 10.2, 601.1, depth, 2.55, 0.78),
                ],
                tpr,
                18,
            )
        mesh.pipe(
            [(hand * wrist_pin_x, wrist_pin_h, -7.55), (hand * wrist_pin_x, wrist_pin_h, 1.68)],
            [1.16, 1.16],
            steel,
            16,
        )
        mesh.form((hand * wrist_pin_x, wrist_pin_h, 1.68), (1.23, 1.23, 0.25), steel)

    base_height = 405
    positions = [(603, base_height, 103), (660, base_height, 133)]
    packed_shafts = []
    for i, pos in enumerate(positions):
        hand = -1 if i == 0 else 1
        group = bpy.data.objects.new(
            "Black Diamond Alpine Carbon Cork · " + ("left" if i == 0 else "right"),
            None,
        )
        bpy.context.collection.objects.link(group)
        group.location = (pos[0] / 1000, -pos[2] / 1000, pos[1] / 1000)
        group.rotation_euler.z = (0.43, -0.98)[i]
        group["model"] = "Black Diamond Alpine Carbon Cork BD1125143010ALL1"
        group["packedLengthMm"] = 610
        group["lengthCm"] = 61.0
        group.id_properties_ui("lengthCm").update(
            min=61.0,
            max=130.0,
            default=61.0,
            description="61 cm packed, 100 to 130 cm in use",
        )
        group["fieldItem"] = "alpine-carbon-cork-" + ("left" if i == 0 else "right")

        def part(name):
            return sculpture(("L" if i == 0 else "R") + " · " + name)

        def mount(shape, moving_stages=0, packed_height=None):
            obj = place(shape, (0, 0, 0), uv=34)
            obj.parent = group
            if packed_height is not None:
                packed_shafts.append((obj, packed_height * 0.001))
            if moving_stages:
                curve = obj.driver_add("location", 2)
                driver = curve.driver
                length = driver.variables.new()
                length.name = "length_cm"
                length.targets[0].id = group
                length.targets[0].data_path = '["lengthCm"]'
                driver.expression = f"(61 - length_cm) * {moving_stages * 0.005}"
            return obj

        def shaft(shape, profile, wall, surface, sides):
            inner = [(h, r - wall) for h, r in reversed(profile)]
            shape.turn([*profile, *inner, profile[0]], surface, sides)

        upper = part("Tundra upper carbon tube and markings")
        shaft(
            upper,
            [(174, 9.0), (193, 9.0), (339, 8.7), (344, 8.65), (475, 8.48), (585, 8.42)],
            0.48,
            tundra,
            48,
        )

        def paint(x, h, r=9.02):
            a = x / r
            return r * math.sin(a), h, r * math.cos(a)

        def upper_ink_radius(h):
            return 9.0 - 0.30 * (h - 193) / (339 - 193) + 0.043

        printed(upper, wordmark, 260.5, 0, upper_ink_radius, 86.0)
        for facet in brand_facets:
            triangles = [(0, j, j + 1) for j in range(1, len(facet) - 1)]
            printed(upper, (facet, triangles), 314, 0, upper_ink_radius, 9.1)
        upper.plate(
            [
                paint(x, 190 + y, 9.11)
                for x, y in [(-5.3, -1.0), (1.4, -1), (2.2, 0), (1.3, 1), (-5.3, 1)]
            ],
            nylon,
            0.3,
            0.15,
        )
        mount(upper, packed_height=344)
        middle = part("Carbon middle tube and graduations")
        shaft(
            middle,
            [(106, 7.9), (111, 7.95), (178, 7.95), (182, 7.75), (573, 7.7)],
            0.58,
            carbon,
            44,
        )
        printed(middle, "ALPINE CARBON", 142.3, -1.5, 8.17, 5.8)
        printed(middle, "CORK", 156, 3, 8.17, 4.5)
        low = part("Carbon lower telescoping tube")
        shaft(low, [(79, 6.48), (93, 6.8), (111, 6.91), (504, 6.75)], 0.6, carbon, 42)
        for stage, clamp_height, radius in ((middle, 167, 7.82), (low, 96.5, 6.91)):
            for cm in range(100, 131):
                h = clamp_height + (cm - 61) * 5
                stop = 3.6 if cm % 5 == 0 else 0.7
                stage.pipe(
                    [paint(-2.7, h, radius), paint(stop, h, radius)], 0.17, ink, 6
                )
                if cm % 5 == 0:
                    printed(stage, str(cm), h - 3.9, 0, radius + 0.10, 3.8)
        mount(middle, 1, packed_height=178)
        mount(low, 2, packed_height=111)
        for h, r in ((106.5, 8.0), (177.0, 9.0)):
            clamp = part("Forged FlickLock Pro " + str(round(2 * r)) + " mm")
            lever(clamp, h, r)
            hardware = mount(clamp, 1 if r == 8 else 0)
            bearing = (-128, -131)[i] if r == 8 else (0, -148)[i]
            hardware.rotation_quaternion = Quaternion((0, 0, 1), math.radians(bearing))
        replaceable_tech_tip(part, mount, nylon, tip_steel, hard)
        basket = part("38 mm trekking basket")
        rows = []
        for h, r in [
            (71.8, 6.7),
            (73, 10),
            (75.2, 12),
            (76.7, 17.9),
            (77.6, 19),
            (80.2, 19),
            (81.7, 17.2),
            (82.8, 12.1),
            (83.8, 9.6),
            (84.8, 8.2),
        ]:
            rows.append(
                [
                    (
                        r * math.sin(a),
                        h - (1.2 if 75 < h < 78 and math.cos(6 * a) > 0.1 else 0),
                        r * math.cos(a),
                    )
                    for a in [math.tau * j / 72 for j in range(72)]
                ]
            )
        basket.rings(rows, basket_mat)
        mount(basket, 2)
        extension = part("EVA choke-up grip")
        handle_sleeve(
            extension,
            [
                (0, 337.4, 0, 8.9, 9.1),
                (0, 338.6, 0, 10.0, 10.5),
                (0, 341.5, 0, 10.6, 11.25),
                (0, 380, 0, 10.9, 11.5),
                (0, 455, 0.2, 11.45, 12),
                (0, 474.25, 0, 11.55, 12.5),
            ],
            foam,
            56,
            hand,
        )
        mount(extension)
        handle = part("Contoured cork grip and overhanging soft-touch cap")
        grip(handle, hand)
        cork_uv(mount(handle), natural, hand)
        strap = part("Solution wrist strap and woven flash")
        wrist(strap, hand)
        mount(strap)

    rail = sculpture("Twin shaft clips · boot bench wall")
    wood = finish("Keeper · dark oiled walnut", "624c38", rough=0.64)
    for screen_y, radius in ((335.7, 9.0), (140, 7.95)):
        y = base_height + screen_y
        rail.loft(
            [
                (637, y - 8, 7.0, 48, 5.4),
                (637, y - 6.5, 7.0, 49, 6.0),
                (637, y + 6.5, 7.0, 49, 6.0),
                (637, y + 8, 7.0, 48, 5.4),
            ],
            wood,
            28,
            0.24,
        )
        for x, _, d in positions:
            rail.pipe([(x, y, 12), (x, y, d - radius - 1)], 2.4, black, 10)
            arc = [
                (
                    x + (radius + 1.55) * math.sin(a),
                    y,
                    d + (radius + 1.55) * math.cos(a),
                )
                for a in [0.62 + (math.tau - 1.24) * j / 38 for j in range(39)]
            ]
            rail.pipe(arc, 2.15, tpr, 10)
    place(rail, (0, 0, 0), uv=30)
    return packed_shafts
