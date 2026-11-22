import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt


def surface_rows(shape, rows, material):
    width = len(rows[0])
    shape.add(
        [point for row in rows for point in row],
        [
            (i, i + 1, i + width + 1, i + width)
            for j in range(len(rows) - 1)
            for i in range(j * width, (j + 1) * width - 1)
        ],
        material,
    )


def stamp(shape, material, project, arm):
    outline = []
    for n in range(6):
        a = math.radians(6 + 60 * n)
        for u, v in (
            (arm, -0.20 * arm),
            (arm, 0.20 * arm),
            (math.sqrt(3) * 0.20 * arm, 0.20 * arm),
        ):
            outline.append(
                project(
                    u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a)
                )
            )
    center = len(outline)
    shape.add(
        [*outline, project(0, 0)],
        [(i, (i + 1) % center, center) for i in range(center)],
        material,
        False,
    )


def wordmark(shape, ink):
    def face(x, h):
        r = 61.46
        return r * math.sin(x / r), h, r * math.cos(x / r)

    stamp(shape, ink, lambda x, h: face(x, 91.5 + h), 6.1)
    font = bpy.data.curves.new("Coffee Master letterpress", "FONT")
    for filename in (
        "C:/Windows/Fonts/georgiab.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
    ):
        if Path(filename).is_file():
            font.font = bpy.data.fonts.load(filename, check_existing=True)
            break
    font.body = "snow peak"
    font.resolution_u = 4
    text = bpy.data.objects.new("Coffee Master type die", font)
    bpy.context.collection.objects.link(text)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = text.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    xmin = min(v.co.x for v in mesh.vertices)
    xmax = max(v.co.x for v in mesh.vertices)
    scale = 36.7 / (xmax - xmin)
    shape.add(
        [
            face((v.co.x - (xmin + xmax) * 0.5) * scale, 74 + v.co.y * scale)
            for v in mesh.vertices
        ],
        [tuple(t.vertices) for t in mesh.loop_triangles],
        ink,
        False,
    )
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(text, do_unlink=True)
    bpy.data.curves.remove(font)


def shell(shape, steel):
    count = 120

    def ring(h, r):
        return [
            (-r * math.cos(math.tau * i / count), h, r * math.sin(math.tau * i / count))
            for i in range(count)
        ]

    bands = [
        (0, 0.008),
        (0, 54.8),
        (0.4, 57.2),
        (1.5, 59.1),
        (3.6, 60.6),
        (6.4, 61.2),
        (10, 61.2),
    ]
    shape.rings([ring(h, r) for h, r in bands], steel, close=False)
    shape.rings(
        [
            ring(h, r)
            for h, r in [
                (148, 61.2),
                (151.7, 61.3),
                (153, 61.75),
                (154.1, 62.1),
                (155, 61.95),
                (155.6, 61.35),
                (155.4, 60.65),
                (154.5, 60.15),
                (152.1, 60.35),
                (148, 60.45),
            ]
        ],
        steel,
        close=False,
    )
    shape.rings(
        [
            ring(h, r)
            for h, r in [
                (10, 60.45),
                (6.5, 60.45),
                (4.1, 59.85),
                (2.3, 58.45),
                (1.05, 55.1),
                (1.05, 0.008),
            ]
        ],
        steel,
        close=False,
    )
    step = math.tau / count
    end = 5
    for r in (61.2, 60.45):
        span = [i * step for i in range(end, count - end + 1)]
        surface_rows(
            shape,
            [[(-r * math.cos(a), h, r * math.sin(a)) for a in span] for h in (10, 148)],
            steel,
        )

    extent = end * step * 61.2
    outline = (
        [(-extent + 2 * extent * i / 10, 10) for i in range(11)]
        + [(extent, 148)]
        + [(extent - 2 * extent * i / 10, 148) for i in range(1, 11)]
    )
    holes = [
        (0, 51.5),
        (-6.4, 68.2),
        (0, 68.2),
        (6.4, 68.2),
        (-6.4, 74.8),
        (0, 74.8),
        (6.4, 74.8),
    ]
    rings = [
        [
            (
                x + 1.7 * math.cos(math.tau * j / 20),
                h + 1.7 * math.sin(math.tau * j / 20),
            )
            for j in range(20)
        ]
        for x, h in holes
    ]
    points, edges = [], []
    for loop in [outline, *rings]:
        start = len(points)
        points.extend(Vector(p) for p in loop)
        edges.extend((start + i, start + (i + 1) % len(loop)) for i in range(len(loop)))
    for x in range(-14, 15, 3):
        for h in range(18, 148, 7):
            if all((x - hx) ** 2 + (h - hy) ** 2 > 3.6 for hx, hy in holes):
                points.append(Vector((x, h)))
    vertices, _, triangles, *_ = delaunay_2d_cdt(points, edges, [], 0, 0.0001)
    faces = []
    for tri in triangles:
        center = sum((vertices[i] for i in tri), Vector((0, 0))) / len(tri)
        if all((center.x - x) ** 2 + (center.y - h) ** 2 > 1.7**2 for x, h in holes):
            faces.append(tri)

    def project(x, h, r):
        return -r * math.cos(x / 61.2), h, r * math.sin(x / 61.2)

    for r in (61.2, 60.45):
        shape.add([project(x, h, r) for x, h in vertices], faces, steel)
    for loop in rings:
        shape.rings(
            [[project(x, h, r) for x, h in loop] for r in (60.45, 61.2)],
            steel,
            close=False,
        )


def folded_spout(shape, material):
    def edge(v, u):
        width = 20.6 * (0.095 + 0.905 * math.sqrt(v))
        d = u * width
        shoulder = max(0, 1 - abs(u) ** 1.04)
        return (
            -math.sqrt(61.2**2 - d * d) - (0.45 + 26.8 * v**0.88) * shoulder + 0.18,
            44.5 + 101.3 * v - 4.2 * v * shoulder,
            d,
        )

    ux = [i / 24 for i in range(-24, 25)]
    ys = [0, 0.012, 0.032, 0.071, 0.14, 0.27, 0.46, 0.68, 0.87, 0.98, 1]
    outer = [[edge(v, u) for u in ux] for v in ys]
    inner = [[(x + 0.52, h, d) for x, h, d in row] for row in outer]
    surface_rows(shape, outer, material)
    surface_rows(shape, inner[::-1], material)
    surface_rows(shape, [outer[-1], inner[-1]], material)
    for idx in (0, -1):
        surface_rows(
            shape, [[r[idx] for r in outer], [r[idx] for r in inner]], material
        )


def bracket(shape, x, h, width, height, thick, bore, mat):
    rows = []
    for face, inside in (
        (0, True),
        (0, False),
        (thick, False),
        (thick, True),
        (0, True),
    ):
        row = []
        for i in range(96):
            angle = math.tau * i / 96
            dh, d = math.cos(angle), math.sin(angle)
            r = (
                bore
                if inside
                else ((abs(dh) / (height / 2)) ** 9 + (abs(d) / (width / 2)) ** 9)
                ** (-1 / 9)
            )
            row.append((x + face, h + dh * r, d * r))
        rows.append(row)
    shape.rings(rows, mat, close=False)


def make_insert(part, fit, curve, steel, spun, wire):
    basket = part("09 pressed wedge dripper and single drain")
    count = 256

    def wedge(a, t, inside=0):
        s, c = math.sin(a), math.cos(a)
        x0 = 27.8 * math.copysign(abs(s) ** 0.32, s)
        d0 = 6.75 * math.copysign(abs(c) ** 0.32, c)
        x = x0 * (1 - t) + s * 53.25 * t
        d = d0 * (1 - t) + c * 53.25 * t
        broad = abs(c) ** 8
        ridge_count = 26
        limit = (0.96 - 0.48 * broad) + 0.08 * (1 - abs(s))
        tail = max(0, min(1, (limit - t) * 20)) * max(0, min(1, (t - 0.042) * 25))
        ribs = max(0, math.cos(a * ridge_count)) ** 4 * tail
        offset = -0.9 * ribs - inside
        notch = math.exp(-(((math.remainder(a - math.pi, math.tau)) / 0.078) ** 6))
        return x + s * offset, 80.0 + 64.7 * t - 6.8 * (t**8) * notch, d + c * offset

    steps = [0, 0.014, 0.034, 0.052] + [i / 50 for i in range(4, 50)] + [0.985, 1]
    for inside in (0, 0.45):
        basket.rings(
            [
                [wedge(math.tau * i / count, t, inside) for i in range(count)]
                for t in (reversed(steps) if inside else steps)
            ],
            steel,
            close=False,
        )
    floor = []
    for r, h in [(2.25, 79.45), (2.25, 80.0), (2.48, 80.2)]:
        floor.append(
            [
                (
                    r * math.sin(math.tau * i / count),
                    h,
                    r * math.cos(math.tau * i / count),
                )
                for i in range(count)
            ]
        )
    floor.append([wedge(math.tau * i / count, 0, 0.45) for i in range(count)])
    basket.rings(floor, steel, close=False)
    basket.rings(
        [
            [wedge(math.tau * i / count, 0) for i in range(count)],
            [
                (
                    2.25 * math.sin(math.tau * i / count),
                    79.45,
                    2.25 * math.cos(math.tau * i / count),
                )
                for i in range(count)
            ],
        ],
        steel,
        close=False,
    )

    def rim(h, r, n=168):
        return [
            (r * math.sin(a), h, r * math.cos(a))
            for a in [
                math.pi + 0.087 + (math.tau - 0.174) * i / n for i in range(n + 1)
            ]
        ]

    lip = [
        (142.2, 53.2),
        (142.15, 54.55),
        (142.5, 55.2),
        (144.85, 55.55),
        (145.55, 55.05),
        (145.65, 53.2),
        (145.1, 52.65),
        (144.45, 52.7),
    ]
    surface_rows(basket, [rim(h, r) for h, r in lip], spun)
    for sign in (-1, 1):
        x = 52.45 * sign
        basket.form((x, 142.7, 0), (1.1, 1.72, 1.72), spun)
    fit(basket, "dripper", True, pivot=(0, 80, 0))
    bridge = part("10 welded riser eye on the rim")
    curve(
        bridge,
        [
            (-8.8, 145.4, -53.0),
            (-5.5, 145.4, -53.4),
            (-4.6, 146.1, -53.6),
            (-4.2, 148.8, -53.8),
            (-2.6, 151, -53.8),
            (0, 151.8, -53.8),
            (2.6, 151, -53.8),
            (4.2, 148.8, -53.8),
            (4.6, 146.1, -53.6),
            (5.5, 145.4, -53.4),
            (8.8, 145.4, -53),
        ],
        0.92,
        wire,
        12,
    )
    fit(bridge, "riser-eye", True, pivot=(0, 145, -53.5))
    bail = part("11 folding wire dripper bail")
    points = [(-52.3, 142.7, 0), (-50.7, 142.7, 0)]
    for i in range(57):
        a = math.pi * i / 56
        points.append(
            (-50.4 * math.cos(a), 142.7 + 3.7 * math.sin(a), 48.4 * math.sin(a))
        )
    points.extend([(50.7, 142.7, 0), (52.3, 142.7, 0)])
    bail.pipe(points, 0.91, wire, 12)
    fit(bail, "folding-bail", True, pivot=(0, 142.7, 0))
    base = part("12 flanged cup support with pipe keyway")
    sections = [
        (76.35, 5.0),
        (76.35, 32.5),
        (76.6, 34.1),
        (77.65, 35.4),
        (78.05, 37),
        (78.1, 54.8),
        (77.7, 55.45),
        (74.4, 55.55),
        (74.1, 55.0),
        (74.25, 54.7),
        (77.2, 54.65),
        (77.45, 54),
        (77.38, 37),
        (77.0, 35.8),
        (75.95, 34.35),
        (75.68, 32.5),
        (75.68, 5.0),
        (76.35, 5.0),
    ]
    rows = []
    for h, r in sections:
        row = []
        for i in range(192):
            a = math.tau * i / 192
            key = (
                max(0, min(1, (r - 47.0) / 8))
                * 5.1
                * math.exp(-((math.remainder(a - math.pi, math.tau) / 0.067) ** 6))
            )
            row.append(((r - key) * math.sin(a), h, (r - key) * math.cos(a)))
        rows.append(row)
    base.rings(rows, spun, close=False)
    for j in range(3):
        a = math.tau * j / 3 + 0.31
        base.pipe(
            [(r * math.sin(a), 78.15, r * math.cos(a)) for r in (41, 42, 49, 50)],
            [0.2, 0.6, 0.6, 0.2],
            steel,
            10,
            1.8,
        )
    fit(base, "cup-stand", True, pivot=(0, 76, 0))
    funnel = part("13 steam funnel bell with intake scallops")
    bell = [
        (1.15, 51.8),
        (1.45, 52.45),
        (3.0, 52.1),
        (8.8, 51.45),
        (10.9, 50.6),
        (12.3, 49),
        (13.4, 45),
        (14.3, 36),
        (15, 21),
        (15.4, 0.008),
        (14.95, 0.008),
        (14.55, 22),
        (13.83, 36),
        (12.9, 45),
        (11.8, 48.7),
        (10.4, 50.1),
        (8.4, 50.9),
        (2, 51.6),
        (1.15, 51.8),
    ]
    rows = []
    for h, r in bell:
        row = []
        for i in range(144):
            a = i * math.tau / 144
            notch = max(0, 1 - (math.remainder(a, math.tau / 3) / 0.076) ** 2) ** 0.5
            row.append(
                (
                    r * math.sin(a),
                    h + 2.5 * notch * max(0, 1 - (h - 1.15) / 4),
                    r * math.cos(a),
                )
            )
        rows.append(row)
    funnel.rings(rows, steel, close=False)
    bell_object = fit(funnel, "steam-bell", True, pivot=(0, 1.15, 0))
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48, radius=0.00264, depth=0.009, location=(0, 0.0375, 0.014)
    )
    bore = bpy.context.object
    piercing = bell_object.modifiers.new("Steam outlet for offset riser", "BOOLEAN")
    piercing.operation = "DIFFERENCE"
    piercing.object = bore
    bpy.context.view_layer.objects.active = bell_object
    bpy.ops.object.modifier_apply(modifier=piercing.name)
    bpy.data.objects.remove(bore, do_unlink=True)
    tube = part("14 bent hollow steam riser and upper jet")
    nodes = [
        (0, 12, -37.5),
        (0, 18, -37.5),
        (0, 32, -37.5),
        (0, 40, -38.5),
        (0, 44, -40.2),
        (0, 55, -47.8),
        (0, 62, -52),
        (0, 67, -53.5),
        (0, 72, -53.8),
        (0, 145, -53.8),
        (0, 151.7, -53.2),
        (0, 156.7, -50.0),
        (0, 158.45, -45),
        (0, 158.05, -40),
        (0, 154.8, -22),
        (0, 153.8, -15),
        (0, 154.5, -10),
        (0, 157, -6.2),
        (0, 161.9, -4.7),
        (0, 167, -4.55),
        (0, 178.9, -4.55),
    ]
    pts = []
    for i in range(len(nodes) - 1):
        p0, p1, p2, p3 = (
            Vector(nodes[min(len(nodes) - 1, max(0, i + n))]) for n in (-1, 0, 1, 2)
        )
        for j in range(6):
            t = j / 6
            pts.append(
                0.5
                * (
                    2 * p1
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3
                )
            )
    pts.append(Vector(nodes[-1]))
    outer = []
    inner = []
    for i, p in enumerate(pts):
        direction = (pts[min(len(pts) - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
        axis = direction.cross(Vector((1, 0, 0))).normalized()
        for walls, r in ((outer, 2.65), (inner, 2.04)):
            walls.append(
                [
                    p + r * (Vector((1, 0, 0)) * math.cos(a) + axis * math.sin(a))
                    for a in [j * math.tau / 24 for j in range(24)]
                ]
            )
    tube.rings(outer + list(reversed(inner)) + [outer[0]], spun, close=False)
    fit(tube, "riser", pivot=(0, 13, -37.5))
    latch = part("15 lower riser support clip")
    for side in (-1, 1):
        curve(
            latch,
            [
                (side * 2.4, 74.2, -53.5),
                (side * 3.0, 73.8, -53.2),
                (side * 3.1, 72.6, -51.9),
                (side * 2.8, 72.5, -49.4),
                (side * 2.7, 73.8, -48.7),
                (side * 2.7, 75.1, -48.7),
            ],
            0.70,
            spun,
            10,
        )
    fit(latch, "riser-clip", True, pivot=(0, 73, -52))


def build(Sculpture, pose, curve, steel, spun, wire, brass, glass, ink, directory):
    collection = bpy.data.collections.new("PR-880 · installed assembly")
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new("Snow Peak PR-880 · Field Coffee Master", None)
    collection.objects.link(root)
    root.empty_display_size = 0.023
    root["product"] = "PR-880"
    root["cookware"] = root.name
    root["nominal_mm"] = [200, 130, 190]
    root["capacity_ml"] = 760

    def part(name):
        return Sculpture("PR-880 · " + name)

    def fit(s, role, hidden=False, pivot=(0, 0, 0)):
        obj = pose(s, (0, 0, 0))
        if role in (
            "body",
            "spout",
            "lid",
            "dripper",
            "riser",
            "cup-stand",
            "steam-bell",
            "sight",
        ):
            editable = bmesh.new()
            editable.from_mesh(obj.data)
            bmesh.ops.remove_doubles(editable, verts=editable.verts, dist=0.0000008)
            bmesh.ops.recalc_face_normals(editable, faces=editable.faces)
            editable.to_mesh(obj.data)
            editable.free()
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
        obj.parent = root
        obj["coffeePart"] = role
        obj["closedInterior"] = hidden
        v = Vector((pivot[0], -pivot[2], pivot[1])) / 1000
        obj.data.transform(Matrix.Translation(-v))
        obj.location = v
        return obj

    body = part("01 drawn reservoir and pierced water-level marks")
    shell(body, steel)
    wordmark(body, ink)
    fit(body, "body")
    spout = part("02 folded pouring spout")
    folded_spout(spout, steel)
    fit(spout, "spout")
    boss = part("03 welded threaded mounting plate")
    bracket(boss, 60.5, 135.4, 12.5, 29.2, 2.35, 2.15, spun)
    for h in (124.1, 146.7):
        boss.form((62.86, h, 0), (0.34, 1.15, 1.15), steel)
    fit(boss, "receiver")
    hand = part("04 removable hairpin wire handle and saddle")
    bracket(hand, 63.0, 135.4, 16.9, 21.2, 1.4, 2.4, spun)
    right = [
        (64.0, 125.7, 6.9),
        (64.3, 138, 6.9),
        (64.45, 147.2, 6.9),
        (65.5, 150.2, 6.9),
        (69.8, 151.6, 6.9),
        (98.5, 151.6, 6.9),
        (103.6, 150.6, 6.9),
        (107.1, 146.6, 6.9),
        (107.7, 141.1, 6.9),
        (107.7, 68.8, 6.9),
        (108.2, 63.0, 6.8),
        (109.4, 59.3, 5.4),
        (109.95, 57.4, 2.6),
        (109.98, 57.0, 0),
    ]
    curve(
        hand, right + [(x, h, -d) for x, h, d in reversed(right[:-1])], 1.95, wire, 18
    )
    fit(hand, "handle", pivot=(64, 135.4, 0))
    screw = part("05 straight-knurled captive thumb screw")
    screw.pipe(
        [
            (58.7, 135.4, 0),
            (59, 135.4, 0),
            (65.0, 135.4, 0),
            (65.3, 135.4, 0),
            (66.2, 135.4, 0),
            (66.6, 135.4, 0),
        ],
        [1.64, 1.75, 1.75, 4.5, 5.1, 5.1],
        brass,
        48,
    )
    threads = []
    for i in range(217):
        a = i * math.tau / 27
        x = 59.05 + i * 0.7 / 27
        crest = 1.79 + 0.34 * min(1, i / 9, (216 - i) / 9)
        threads.append(
            [
                (x + dx, 135.4 + radius * math.cos(a), radius * math.sin(a))
                for dx, radius in [
                    (-0.24, 1.73),
                    (-0.035, crest),
                    (0.035, crest),
                    (0.24, 1.73),
                ]
            ]
        )
    thread_start = len(screw.vertices)
    screw.rings(threads, brass, False)
    thread_end = len(screw.vertices)
    rows = []
    for x, r in [(66.6, 6.0), (67.0, 6.35), (71.3, 6.35), (71.8, 6.05)]:
        rows.append(
            [
                (
                    x,
                    135.4
                    + (r + (0.17 if i % 2 == 0 else -0.16))
                    * math.cos(i * math.tau / 96),
                    (r + (0.17 if i % 2 == 0 else -0.16)) * math.sin(i * math.tau / 96),
                )
                for i in range(96)
            ]
        )
    screw.rings(rows, brass, False)
    knob_screw = fit(screw, "screw", pivot=(64, 135.4, 0))
    knob_screw.vertex_groups.new(name="Thread inside the receiver").add(
        list(range(thread_start, thread_end)), 1, "REPLACE"
    )
    lid = part("06 domed lid and turned-in rim")
    profile = [
        (151.4, 59.4),
        (151.2, 60.0),
        (151.6, 60.3),
        (154.4, 60.0),
        (155.1, 62),
        (155.6, 64.1),
        (156.5, 64.85),
        (158, 65),
        (160.5, 64.4),
        (163, 62.5),
        (166, 58.9),
        (168.7, 52),
        (171, 42),
        (172.4, 31),
        (172.9, 24),
        (172.6, 21.8),
        (171.8, 20),
        (171.1, 20.2),
        (172.1, 22.1),
        (172.2, 24),
        (171.8, 31),
        (170.3, 42),
        (167.9, 52),
        (165.2, 58.8),
        (162.3, 62),
        (159.9, 64),
        (158.1, 64.25),
        (157, 64.1),
        (156.2, 62),
        (155.3, 59.55),
        (151.4, 59.4),
    ]
    lid.turn(profile, steel, 128)
    fit(lid, "lid", pivot=(0, 153, 0))
    knob = part("07 hollow pressed sight glass and positive asterisk")
    knob.turn(
        [
            (169.8, 18.4),
            (170.5, 20),
            (172.4, 20.2),
            (173.1, 23.8),
            (174, 25.1),
            (175.2, 24.9),
            (176.3, 23.6),
            (177.6, 21.9),
            (179.4, 21.35),
            (182.9, 22.2),
            (186.4, 24.25),
            (187.9, 24.55),
            (188.9, 24.05),
            (189.65, 22.1),
            (189.92, 17.9),
            (189.94, 0.008),
            (187.45, 0.008),
            (187.4, 17.8),
            (186.9, 20.7),
            (185.9, 21.0),
            (183.5, 19.8),
            (180.1, 18.3),
            (175.0, 18.25),
            (170.0, 17.8),
            (169.8, 18.4),
        ],
        glass,
        112,
    )
    stamp(knob, ink, lambda u, v: (u, 189.97, -v), 10.1)
    fit(knob, "sight", pivot=(0, 171.8, 0))
    retainer = part("08 sight-glass retaining collar")
    retainer.turn(
        [
            (169.3, 17.15),
            (169.3, 21.2),
            (169.7, 22.7),
            (170.35, 22.6),
            (170.5, 20.25),
            (171.65, 20.1),
            (171.7, 17.7),
            (169.3, 17.15),
        ],
        spun,
        80,
    )
    fit(retainer, "retainer", pivot=(0, 171.8, 0))
    make_insert(part, fit, curve, steel, spun, wire)
    bpy.context.view_layer.update()
    parts = {o.get("coffeePart"): o for o in collection.objects if o.type == "MESH"}
    for key, assembly in {
        "spout": "body",
        "receiver": "body",
        "sight": "lid",
        "retainer": "lid",
        "screw": "handle",
        "riser-eye": "dripper",
        "folding-bail": "dripper",
        "cup-stand": "dripper",
        "steam-bell": "riser",
        "riser-clip": "riser",
    }.items():
        child = parts[key]
        transform = child.matrix_world.copy()
        child.parent = parts[assembly]
        child.matrix_world = transform
    bpy.context.view_layer.update()
    native = bpy.data.scenes.new("Snow Peak Field Coffee Master")
    native.collection.children.link(collection)
    native.unit_settings.system = "METRIC"
    case = make_case(Sculpture, pose, curve, ink)
    native.collection.children.link(case)
    if directory is not None:
        directory.mkdir(exist_ok=True, parents=True)
        bpy.data.libraries.write(
            str(directory / "field-coffee-master.blend"),
            {native},
            fake_user=True,
            compress=True,
        )
    bpy.data.scenes.remove(native)
    root.location = (0.404, -0.164, 1.075)
    root.rotation_euler.z = 0.16
    return root


def make_case(Sculpture, pose, curve, ink):
    import numpy as np

    case = bpy.data.collections.new("PR-880 · supplied storage case")
    fabric = bpy.data.materials.new("Storage case · black woven polyester mesh")
    fabric.use_nodes = True
    bs = fabric.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.021, 0.024, 0.027, 1)
    bs.inputs["Roughness"].default_value = 0.84
    bs.inputs["Sheen Weight"].default_value = 0.31
    coords = np.indices((64, 64))
    wires = (0.5 + 0.5 * np.cos(coords[0] * math.pi / 4)) ** 4 + (
        0.5 + 0.5 * np.cos(coords[1] * math.pi / 4)
    ) ** 4
    pixels = np.empty((64, 64, 4), np.float32)
    pixels[:, :, :3] = np.clip(0.18 + 0.86 * wires, 0, 1)[:, :, None]
    pixels[:, :, 3] = 1
    tile = bpy.data.images.new(
        "Storage case · bias weave coverage", 64, 64, alpha=False
    )
    tile.colorspace_settings.name = "Non-Color"
    tile.pixels.foreach_set(pixels.ravel())
    tile.pack()
    tex = fabric.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = tile
    fabric.node_tree.links.new(tex.outputs["Color"], bs.inputs["Alpha"])

    def stash(s, scale=0):
        obj = s.finalize(uv_scale=scale)
        for linked in list(obj.users_collection):
            linked.objects.unlink(obj)
        case.objects.link(obj)
        obj.location.x = -0.233
        return obj

    bag = Sculpture("PR-880 accessory · sewn storage sack")
    sections = [
        (1, 54),
        (3, 57),
        (5, 61),
        (12, 67),
        (36, 70.5),
        (75, 73.5),
        (112, 74),
        (145, 75),
        (163, 72),
        (176, 65),
        (186, 56),
        (201, 40),
        (218, 20),
        (225, 9),
        (226, 4),
    ]
    rows = []
    for h, r in sections:
        row = []
        for i in range(108):
            a = i * math.tau / 108
            pleat = (max(0, min(1, (h - 150) / 47)) * 0.13 + 0.021) * r
            v = (
                r
                + pleat * math.sin(9 * a + h * 0.011)
                + 0.9 * math.sin(5 * a - 0.07 * h)
                + 0.9 * math.cos(a * 3 + h * 0.018)
            )
            spout_clearance = (
                23
                * max(0, -math.cos(a)) ** 8
                * min(1, max(0, (h - 40) / 50), max(0, (194 - h) / 26))
            )
            row.append(
                ((v + spout_clearance) * math.cos(a), h, (v + 1.5) * 0.99 * math.sin(a))
            )
        rows.append(row)
    bag.rings(rows, fabric)
    bag_mesh = stash(bag).data
    weave = bag_mesh.uv_layers.new(name="Bias-cut polyester")
    for poly in bag_mesh.polygons:
        points = [
            bag_mesh.vertices[bag_mesh.loops[i].vertex_index].co
            for i in poly.loop_indices
        ]
        angles = [math.atan2(-p.y / 0.99, p.x) / math.tau for p in points]
        crosses_seam = max(angles) - min(angles) > 0.5
        for i, a, p in zip(poly.loop_indices, angles, points):
            u = (a + (1 if crosses_seam and a < 0 else 0)) * 54
            v = p.z * 122
            weave.data[i].uv = (u + 0.06 * v, v - 0.06 * u)
    binding = Sculpture("PR-880 accessory · hem bands and woven side tag")
    for row, thickness in ((rows[2], 1.25), (rows[8], 1.1)):
        binding.pipe([*row, row[0]], thickness, ink, 10)
    label = bpy.data.materials.new("Field case · woven ecru label")
    label.diffuse_color = (0.55, 0.50, 0.42, 1)
    label.roughness = 0.92
    binding.plate(
        [(70.7, 79, 11), (80.2, 80, 9), (80.2, 105, 9), (70.7, 105, 11)],
        label,
        0.5,
        0.08,
    )
    stamp(binding, ink, lambda x, h: (75 + x, 99 + h, 11.6 - x * 0.20), 2.9)
    binding.label("snow peak", 3.3, lambda x, h: (75 + h, 88 - x, 11.4 - h * 0.20), ink)
    stash(binding)
    cord = Sculpture("PR-880 accessory · braided drawcord and barrel lock")
    curve(
        cord,
        [
            (1, 223, -1),
            (7, 229, 1),
            (15, 234, 2),
            (23, 232, 2),
            (34, 221, 2),
            (50, 190, 2),
            (61, 155, 2),
            (57, 151, 2),
            (50, 166, 2),
            (41, 198, 2),
            (25, 225, 2),
            (18, 230, 2),
            (10, 225, 2),
            (4, 221, 2),
        ],
        1.25,
        ink,
        12,
    )
    cord.pipe([(-3, 225, -3), (3, 229, 0), (9, 232, 3)], [5.1, 5.3, 4.75], ink, 22)
    stash(cord)
    return case


def openable_master(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    placeholder = bpy.context.scene
    with bpy.data.libraries.load(str(path)) as (source, target):
        target.scenes = ["Snow Peak Field Coffee Master"]
    native = target.scenes[0]
    bpy.context.window.scene = native
    bpy.data.scenes.remove(placeholder)
    assembly = next(o for o in native.objects if o.get("product") == "PR-880")
    bpy.context.view_layer.objects.active = assembly
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.clip_start = 0.001
                space.region_3d.view_distance = 0.52
                space.region_3d.view_location = (-0.087, 0, 0.102)
                space.region_3d.view_rotation = Vector(
                    (0.10, -0.60, 0.21)
                ).to_track_quat("Z", "Y")
                space.shading.light = "STUDIO"
                space.shading.color_type = "MATERIAL"
                space.shading.show_shadows = True
    bpy.context.preferences.filepaths.save_version = 0
    edit_file = path.with_suffix(".edit.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(edit_file), compress=True)
    edit_file.replace(path)
