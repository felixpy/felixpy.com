import math
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


def inlay(part, loops, position, material):
    if not loops:
        return
    points, paths = [], []
    for loop in loops:
        signed_area = sum(
            a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1])
        )
        if signed_area < 0:
            loop = list(reversed(loop))
        paths.append(list(range(len(points), len(points) + len(loop))))
        points.extend(Vector(point) for point in loop)
    verts, _, faces, _, _, regions = delaunay_2d_cdt(points, [], paths, 0, 0.00001)
    part.add(
        [position(p.x, p.y) for p in verts],
        [tuple(reversed(f)) for f, region in zip(faces, regions) if len(region) % 2],
        material,
        False,
    )


def corners(w, depth, r, steps=5):
    result = []
    for j in range(4):
        sx, sz = [(1, 1), (-1, 1), (-1, -1), (1, -1)][j]
        for k in range(steps + 1):
            a = (j + k / steps) * math.pi / 2
            result.append(
                (
                    sx * (w / 2 - r) + r * math.cos(a),
                    sz * (depth / 2 - r) + r * math.sin(a),
                )
            )
    return result


def slab(obj, x, z, w, d, r, profile, mat, tilt=0):
    rows = []
    for h, inset in profile:
        rows.append(
            [
                (x + u, h - tilt * (z + v), z + v)
                for u, v in corners(w - 2 * inset, d - 2 * inset, max(0.08, r - inset))
            ]
        )
    obj.rings(rows, mat, close=False)
    for row in [rows[0], rows[-1]]:
        obj.add(row, [tuple(range(len(row)))], mat, False)


def disk(obj, x, z, profile, mat, slope=0):
    obj.rings(
        [
            [
                (
                    x + r * math.cos(a * math.tau / 48),
                    h - slope * (z + r * math.sin(a * math.tau / 48)),
                    z + r * math.sin(a * math.tau / 48),
                )
                for a in range(48)
            ]
            for r, h in profile
        ],
        mat,
    )


def patch(obj, rows, mat):
    n = len(rows[0])
    obj.add(
        [p for row in rows for p in row],
        [
            (i + j * n, i + (j + 1) * n, i + (j + 1) * n + 1, i + j * n + 1)
            for i in range(n - 1)
            for j in range(len(rows) - 1)
        ],
        mat,
    )


def eye(obj, project, material, striped=False, engraving_width=0):
    panels = [
        [(0, 0.18), (0.053, 0.33), (0.103, 0.42), (0.149, 0.46), (0.092, 0.32)],
        [
            (0.10, 0.29),
            (0.181, 0.413),
            (0.276, 0.462),
            (0.43, 0.342),
            (0.68, 0.164),
            (0.933, 0.014),
            (0.984, 0),
            (0.849, 0.119),
            (0.58, 0.289),
            (0.318, 0.503),
            (0.282, 0.553),
            (0.315, 0.628),
            (0.235, 0.568),
            (0.161, 0.452),
        ],
        [
            (0.311, 0.508),
            (0.49, 0.359),
            (0.693, 0.236),
            (0.935, 0.114),
            (0.884, 0.247),
            (0.662, 0.356),
            (0.452, 0.487),
            (0.586, 0.529),
            (0.678, 0.514),
            (0.799, 0.371),
            (0.872, 0.291),
            (0.798, 0.454),
            (0.704, 0.582),
            (0.63, 0.625),
            (0.55, 0.615),
            (0.409, 0.56),
        ],
    ]
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon

    def clip(polygon, t, above):
        result = []
        for p, q in zip(polygon, polygon[1:] + polygon[:1]):
            a, b = p[0] - p[1] * 0.85 - t, q[0] - q[1] * 0.85 - t
            if (a >= 0) == above:
                result.append(p)
            if a * b < 0:
                f = a / (a - b)
                result.append((p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f))
        return result

    for panel in panels:
        if engraving_width:
            for p, q in zip(panel, panel[1:] + panel[:1]):
                dx, dy = q[0] - p[0], q[1] - p[1]
                f = engraving_width / (2 * math.hypot(dx, dy))
                ox, oy = -dy * f, dx * f
                obj.add(
                    [
                        project(x - 0.5, y - 0.31)
                        for x, y in [
                            (p[0] + ox, p[1] + oy),
                            (q[0] + ox, q[1] + oy),
                            (q[0] - ox, q[1] - oy),
                            (p[0] - ox, p[1] - oy),
                        ]
                    ],
                    [(0, 1, 2, 3)],
                    material,
                    False,
                )
        elif striped:
            points = [Vector((a, b, 0)) for a, b in panel]
            for indices in tessellate_polygon([points]):
                triangle = [panel[i] for i in indices]
                for band in range(-58, 105):
                    polygon = clip(
                        clip(triangle, band / 98, True), (band + 0.51) / 98, False
                    )
                    for i in range(1, len(polygon) - 1):
                        a, b, c = polygon[0], polygon[i], polygon[i + 1]
                        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (
                            c[0] - a[0]
                        )
                        if abs(area) > 1e-9:
                            obj.add(
                                [project(x - 0.5, y - 0.31) for x, y in (a, b, c)],
                                [(0, 1, 2)],
                                material,
                                False,
                            )
        else:
            points = [Vector((a, b, 0)) for a, b in panel]
            obj.add(
                [project(a - 0.5, b - 0.31) for a, b in panel],
                tessellate_polygon([points]),
                material,
                False,
            )


def carbon(mat):
    size = 256
    image = bpy.data.images.new(
        "Prepreg · diagonal 2 × 2 twill", width=size, height=size
    )
    pixels = []
    for y in range(size):
        for x in range(size):
            u = (x + y) * 8 / size
            v = (y - x) * 8 / size
            over = (math.floor(u) + math.floor(v)) % 4 < 2
            c = u if over else v
            fill = math.sin((c % 1) * math.pi) ** 0.55
            value = (
                (0.124 if over else 0.104)
                + fill * (0.094 if over else 0.056)
                + 0.014 * math.cos(c * math.tau * 9)
            )
            pixels.extend((value * 0.985, value, value * 1.04, 1))
    image.pixels.foreach_set(pixels)
    image.pack()
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    shader = mat.node_tree.nodes.get("Principled BSDF")
    mat.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    return mat
