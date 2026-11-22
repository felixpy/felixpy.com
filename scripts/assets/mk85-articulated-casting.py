import itertools
import json
import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / ".references/05-摄影与陈列/手办与收藏模型/Iron Man Mark 85"
LABEL = "Tongshifu · Iron Man Mark 85"
SCALE = 420 / 731
FINISHES = {
    "ruby": ("ae1b2e", 0.67, 0.245, 0.32),
    "red": ("971625", 0.69, 0.26, 0.29),
    "wine": ("701322", 0.62, 0.29, 0.22),
    "gold": ("c9ac78", 0.72, 0.32, 0.12),
    "bronze": ("a3895b", 0.70, 0.35, 0.10),
    "silver": ("9b9fa1", 0.76, 0.34, 0.08),
    "steel": ("62656b", 0.70, 0.33, 0.06),
    "titanium": ("25242b", 0.38, 0.44, 0.025),
    "satin titanium": ("73727a", 0.58, 0.36, 0.04),
    "seal": ("302d32", 0.34, 0.40, 0.05),
    "lens": ("9bbac0", 0.52, 0.29, 0.12),
    "crystal": ("d1e6ea", 0.36, 0.20, 0.28),
}


def finish(name, spec):
    color, metal, rough, coat = spec
    rgb = tuple(
        ((int(color[i : i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4)
    )
    mat = bpy.data.materials.new("MK85 casting · " + name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    for key, value in (
        ("Base Color", (*rgb, 1)),
        ("Metallic", metal),
        ("Roughness", rough),
        ("Coat Weight", coat),
        ("Coat Roughness", 0.24),
    ):
        shader.inputs[key].default_value = value
    if name == "titanium":
        shader.inputs["Specular IOR Level"].default_value = 0.24
    if name in ("lens", "crystal"):
        shader.inputs["Emission Color"].default_value = (*rgb, 1)
        shader.inputs["Emission Strength"].default_value = 0.13
    return mat


class Assembly:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.materials = []
        self.parts = {}
        self.palette = {key: index for index, key in enumerate(FINISHES)}
        self.charts = []
        self.uv = []

    def begin(self, name):
        self.parts[name] = len(self.vertices)

    def vertex(self, point):
        self.vertices.append(tuple(v / 1000 for v in point[:3]))
        self.uv.append(point[3:])
        return len(self.vertices) - 1

    def face(self, vertices, pigment):
        self.faces.append(tuple(vertices))
        self.materials.append(self.palette[pigment])

    def join(self, base, folder):
        mesh = bpy.data.meshes.new("Nested armour shells")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        images = {}
        for name, spec in FINISHES.items():
            mat = finish(name, spec)
            family = (
                {
                    "ruby": "red",
                    "red": "red",
                    "wine": "red",
                    "gold": "gold",
                    "bronze": "gold",
                    "steel": "steel",
                    "silver": "silver",
                }
            ).get(name)
            if family:
                if family not in images:
                    images[family] = bpy.data.images.load(
                        str(folder / (family + "-lacquer.jpg"))
                    )
                    images[family].pack()
                    images[family].filepath = "//" + family + "-lacquer.jpg"
                tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
                tex.image = images[family]
                mat.node_tree.links.new(
                    tex.outputs["Color"],
                    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
                )
            mesh.materials.append(mat)
        uv = mesh.uv_layers.new(name=base.data.uv_layers.active.name)
        uvdata = np.zeros((len(mesh.loops), 2), dtype="f")
        source = np.asarray(self.uv)
        for poly in mesh.polygons:
            coords = source[list(poly.vertices)].copy()
            if coords[:, 1].max() - coords[:, 1].min() > 0.5:
                coords[coords[:, 1] < 0.5, 1] += 1
            index = int(coords[0, 0])
            uvdata[poly.loop_start : poly.loop_start + poly.loop_total, 0] = (
                index % 4 + 0.008 + coords[:, 1] * 0.984
            ) / 4
            uvdata[poly.loop_start : poly.loop_start + poly.loop_total, 1] = (
                1 - (index // 4 + 0.008 + coords[:, 2] * 0.984) / 5
            )
        uv.uv.foreach_set("vector", uvdata.ravel())
        mesh.polygons.foreach_set(
            "material_index", np.asarray(self.materials, dtype="i")
        )
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), dtype=bool))
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("Articulated armour", mesh)
        bpy.context.collection.objects.link(obj)
        names = list(self.parts)
        for i, label in enumerate(names):
            first = self.parts[label]
            last = (
                self.parts[names[i + 1]] if i + 1 < len(names) else len(mesh.vertices)
            )
            if last > first:
                obj.vertex_groups.new(name=label).add(
                    list(range(first, last)), 1, "REPLACE"
                )
        bpy.ops.object.select_all(action="DESELECT")
        base.select_set(True)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = base
        bpy.ops.object.join()


def signed(x, exponent):
    return math.copysign(abs(x) ** exponent, x)


class Casting:
    def __init__(
        self, assembly, name, profile, pigment, side=1, angle=0, square=0.94, form=None
    ):
        self.a, self.name, self.side = assembly, name, side
        self.rows = np.asarray(profile, dtype=float)
        if name == "Helmet":
            self.rows[:, 3] *= 0.925
        self.slopes = np.gradient(self.rows[:, 1:], self.rows[:, 0], axis=0)
        self.yaw = math.radians(angle)
        self.square, self.form = square, form
        self.chart = len(assembly.charts)
        assembly.charts.append(
            {
                "name": name,
                "rows": self.rows.tolist(),
                "side": side,
                "yaw": self.yaw,
                "square": square,
            }
        )
        self.skin(pigment)

    def dimensions(self, v):
        v = min(max(v, self.rows[0, 0]), self.rows[-1, 0])
        i = min(
            len(self.rows) - 2,
            max(0, int(self.rows[:, 0].searchsorted(v, side="right") - 1)),
        )
        h = self.rows[i + 1, 0] - self.rows[i, 0]
        t = (v - self.rows[i, 0]) / h
        return (
            (1 + 2 * t) * (1 - t) ** 2 * self.rows[i, 1:]
            + t * (1 - t) ** 2 * h * self.slopes[i]
            + t * t * (3 - 2 * t) * self.rows[i + 1, 1:]
            - t * t * (1 - t) * h * self.slopes[i + 1]
        )

    def point(self, angle, v, lift=0):
        cx, cy, rx, front, back = self.dimensions(v)
        a = math.radians(angle)
        si, co = math.sin(a), math.cos(a)
        if self.form:
            lift += self.form(angle, v)
        xx = signed(si, self.square) * (rx * SCALE + lift)
        if self.name == "Helmet":
            phi = abs((angle + 180) % 360 - 180)
            k = min(1.0, max(0.0, (103 - phi) / 29))
            cheek_taper = min(1.0, max(0.0, (v - 104) / 17))
            xx *= 1 - (0.078 + 0.018 * cheek_taper) * (k * k * (3 - 2 * k))
            side_cap = min(1, max(0, (phi - 70) / 25))
            xx *= 1 + 0.038 * side_cap * side_cap * (3 - 2 * side_cap) * math.exp(
                -(((v - 87) / 30) ** 4)
            )
        yy = -signed(co, self.square) * ((front if co > 0 else back) + lift)
        x = xx * math.cos(self.yaw) - yy * math.sin(self.yaw)
        y = xx * math.sin(self.yaw) + yy * math.cos(self.yaw)
        return (
            (cx - 221) * SCALE + self.side * x,
            cy + y,
            (791 - v) * SCALE,
            self.chart,
            ((angle + 180) % 360) / 360,
            (v - self.rows[0, 0]) / (self.rows[-1, 0] - self.rows[0, 0]),
        )

    def xangle(self, u, v, front=True):
        cx, _, rx, _, _ = self.dimensions(v)
        frac = (u - cx) / (max(0.01, rx) * self.side)
        angle = math.degrees(
            math.asin(signed(max(-0.994, min(0.994, frac)), 1 / self.square))
        )
        return angle if front else 180 - angle

    def skin(self, color):
        self.a.begin(self.name)
        nv = np.unique(
            np.r_[np.arange(self.rows[0, 0], self.rows[-1, 0], 2.4), self.rows[:, 0]]
        )
        rings = [
            [self.a.vertex(self.point(a, v)) for a in range(-180, 180, 6)] for v in nv
        ]
        self.a.face(rings[0], color)
        for top, bot in itertools.pairwise(rings):
            for i in range(len(top)):
                j = (i + 1) % len(top)
                self.a.face((top[i], bot[i], bot[j], top[j]), color)
        self.a.face(rings[-1][::-1], color)

    def plate(
        self,
        label,
        outline,
        color,
        height=1.05,
        edge="steel",
        center=None,
        ridge=0,
        front=False,
        base=-0.17,
    ):
        self.a.begin(self.name + " / " + label)
        points = np.asarray(outline, dtype=float)
        if front:
            points = np.array([(self.xangle(x, v), v) for x, v in points])
        inner = np.asarray(center, dtype=float) if center else np.mean(points, axis=0)
        if center and front:
            inner[0] = self.xangle(*inner)
        points = np.array(
            [
                p + (q - p) * t
                for p, q in zip(points, np.roll(points, -1, axis=0))
                for t in (0.08, 0.92)
            ]
        )
        perimeter = []
        for p, q in zip(points, np.roll(points, -1, axis=0)):
            n = max(1, math.ceil(np.linalg.norm((q - p) * (0.38, 0.575)) / 1.55))
            perimeter.extend(p + (q - p) * k / n for k in range(n))
        perimeter = np.array(perimeter)
        rings = []
        for k, lift in (
            (0.001, height * 1.16 + ridge),
            (0.18, height * 1.16 + ridge * 0.95),
            (0.4, height * 1.15 + ridge * 0.80),
            (0.65, height * 1.12 + ridge * 0.5),
            (0.83, height * 1.07 + ridge * 0.25),
            (0.94, height),
            (0.977, height * 0.91),
            (1, height * 0.48),
            (1, base),
        ):
            rings.append(
                [
                    self.a.vertex(self.point(*p, lift))
                    for p in inner + (perimeter - inner) * k
                ]
            )
        for k, (r0, r1) in enumerate(itertools.pairwise(rings)):
            for i in range(len(r0)):
                j = (i + 1) % len(r0)
                self.a.face((r0[j], r0[i], r1[i], r1[j]), color if k < 7 else edge)
        self.a.face(rings[0], color)
        self.a.face(rings[-1][::-1], edge)

    def sheet(
        self, label, stations, pigment, rise, border, relief=None, vertical=False
    ):
        self.a.begin(self.name + " / " + label)
        stations = np.asarray(stations, dtype=float)
        angles = np.linspace(
            stations[0, 0],
            stations[-1, 0],
            2 + math.ceil((stations[-1, 0] - stations[0, 0]) / 1.5),
        )
        bottom, top = (
            np.interp(angles, stations[:, 0], stations[:, 2]),
            np.interp(angles, stations[:, 0], stations[:, 1]),
        )
        across = np.r_[0, 0.027, 0.065, np.linspace(0.10, 0.90, 13), 0.935, 0.973, 1]
        rows = []
        for t in across:
            ring = []
            for a, hi, lo in zip(angles, top, bottom):
                v = hi + t * (lo - hi)
                dist = min(
                    t * (lo - hi) * (0.22 if vertical else SCALE),
                    (1 - t) * (lo - hi) * (0.22 if vertical else SCALE),
                    (a - angles[0]) * 0.20,
                    (angles[-1] - a) * 0.20,
                )
                if vertical:
                    a, v = v, a
                bevel = min(1, max(0, dist / 0.29))
                lift = (
                    rise
                    + (relief(a, v, t) if relief else 0)
                    - (1 - bevel) ** 1.65 * 0.21
                )
                ring.append(self.a.vertex(self.point(a, v, lift)))
            rows.append(ring)
        for k, (row, nxt) in enumerate(itertools.pairwise(rows)):
            mat = (
                (pigment[1] if across[k] > 0.78 else pigment[0])
                if isinstance(pigment, tuple)
                else pigment
            )
            for i in range(len(row) - 1):
                self.a.face((row[i], nxt[i], nxt[i + 1], row[i + 1]), mat)
        perimeter = [
            *rows[0],
            *(row[-1] for row in rows[1:]),
            *rows[-1][-2::-1],
            *(row[0] for row in rows[-2:0:-1]),
        ]
        inner = []
        for face_id in perimeter:
            _chart, u, z = self.a.uv[face_id]
            a = u * 360 - 180
            v = self.rows[0, 0] + z * (self.rows[-1, 0] - self.rows[0, 0])
            inner.append(self.a.vertex(self.point(a, v, -0.20)))
        for i, j in zip(range(len(inner)), np.roll(np.arange(len(inner)), -1)):
            self.a.face((perimeter[i], perimeter[j], inner[j], inner[i]), border)
        self.a.face(inner[::-1], border)

    def band(self, label, v, thick, color, tilt=0):
        self.a.begin(self.name + " / " + label)
        rows = []
        for dv, h in (
            (0, -0.18),
            (0, 0.15),
            (thick * 0.25, 0.42),
            (thick * 0.74, 0.40),
            (thick, -0.18),
        ):
            rows.append(
                [
                    self.a.vertex(
                        self.point(a, v + dv - tilt * math.cos(math.radians(a)), h)
                    )
                    for a in range(-180, 180, 5)
                ]
            )
        for r0, r1 in zip(rows, rows[1:] + rows[:1]):
            for i in range(len(r0)):
                j = (i + 1) % len(r0)
                self.a.face((r0[i], r1[i], r1[j], r0[j]), color)


def pedestal(work):
    form = np.load(work / "ruins-shape.npz")
    rings = form["rings"]
    side_count = int(form["side_count"])
    rows, n = rings.shape[:2]
    shape = rings.reshape(-1, 3)
    faces = []
    material_ids = []
    texcoords = []

    def face(indices, material, uv):
        faces.append(indices)
        material_ids.append(material)
        texcoords.extend(uv)

    def planar(indices):
        points = shape[list(indices)]
        return np.column_stack((0.5 + points[:, 0] / 250, 0.5 + points[:, 1] / 180))

    for row in range(rows - 1):
        for col in range(n):
            j = (col + 1) % n
            ids = (row * n + col, row * n + j, (row + 1) * n + j, (row + 1) * n + col)
            if row < side_count - 1:
                u, v = col / n, (col + 1) / n
                bottom, top = rings[row, col, 2] / 108, rings[row + 1, col, 2] / 108
                face(ids, 0, ((u, bottom), (v, bottom), (v, top), (u, top)))
            else:
                face(ids, 1, planar(ids))
    lower = tuple(reversed(range(n)))
    upper = tuple(range((rows - 1) * n, rows * n))
    face(lower, 1, planar(lower))
    face(upper, 1, planar(upper))
    badge = np.load(work / "badge.npz")
    letters = badge["xyz"]
    start = len(shape)
    count = len(letters)
    xyz = np.vstack((shape, letters, letters + np.array([0, 0.62, 0])))
    xyz[:, 1] = (xyz[:, 1] - (xyz[:, 1].max() + xyz[:, 1].min()) / 2) * (
        180 / np.ptp(xyz[:, 1])
    )
    edges = {}
    for t in badge["tri"]:
        a, b, c = map(int, t)
        if np.cross(letters[b] - letters[a], letters[c] - letters[a])[1] > 0:
            b, c = c, b
        face((start + a, start + b, start + c), 2, ((0, 0),) * 3)
        face(
            (start + count + c, start + count + b, start + count + a), 2, ((0, 0),) * 3
        )
        for edge in ((a, b), (b, c), (c, a)):
            key = tuple(sorted(edge))
            if key in edges:
                edges.pop(key)
            else:
                edges[key] = edge
    for a, b in edges.values():
        face(
            (start + b, start + a, start + count + a, start + count + b),
            2,
            ((0, 0),) * 4,
        )
    mesh = bpy.data.meshes.new("Layered ruin casting")
    mesh.from_pydata((xyz / 1000).tolist(), [], faces)
    mesh.update()
    side = finish("Rock courses", ("75654d", 0.37, 0.57, 0.04))
    side.name = LABEL + " · Cast brass ruins"
    for mat in (
        side,
        finish("Rock ledge", ("807567", 0.37, 0.57, 0.03)),
        finish("Raised brass lettering", ("b99d6c", 0.58, 0.39, 0.08)),
    ):
        mesh.materials.append(mat)
    mesh.polygons.foreach_set("material_index", np.asarray(material_ids, dtype="i"))
    mesh.polygons.foreach_set("use_smooth", np.array(material_ids) != 2)
    layer = mesh.uv_layers.new(name="Casting finish")
    layer.uv.foreach_set("vector", np.asarray(texcoords, dtype="f").ravel())
    base = bpy.data.objects.new(LABEL, mesh)
    bpy.context.collection.objects.link(base)
    base.vertex_groups.new(name="Rock ledges and rubble").add(
        list(range(start)), 1, "REPLACE"
    )
    base.vertex_groups.new(name="Avengers brass lettering").add(
        list(range(start, len(xyz))), 1, "REPLACE"
    )
    return base


def mirrored(outline, sign):
    return [(a * sign, v) for a, v in outline]


def make_torso(a):
    def pectoral(angle, v):
        ang = abs((angle + 180) % 360 - 180)
        peak = math.exp(-(((ang - 33) / 25) ** 2) - ((v - 179) / 24) ** 2)
        scapula = math.exp(-(((ang - 147) / 23) ** 2) - ((v - 174) / 28) ** 2)
        sulcus = math.exp(-((ang / 10) ** 2) - ((v - 158) / 22) ** 2)
        return 2.1 * peak + 1.65 * scapula - 0.75 * sulcus

    trunk = Casting(
        a,
        "Breast, waist and pelvis",
        [
            (126, 205, -3, 12, 9, 12),
            (137, 205, -2, 34, 12.8, 17.8),
            (145, 206, -2, 52, 16, 20),
            (155, 206, -2, 62, 19.8, 22),
            (174, 206, -2, 61, 24.9, 24.8),
            (189, 206, -1.6, 58, 25, 24),
            (206, 206, -1, 50, 23, 23.0),
            (221, 206, -1.1, 45, 21.7, 21.6),
            (238, 206, -1, 40, 20.2, 19.4),
            (258, 206, -1.8, 37.4, 19.3, 19.9),
            (275, 206, -1.8, 40.4, 20.1, 21.5),
            (291, 206, -2.0, 45.8, 21.4, 23.5),
            (306, 206, -1.7, 44.3, 21, 23.1),
            (320, 206, -1.7, 36, 18.7, 20.4),
            (332, 206, -2.7, 14, 11.2, 14),
            (336, 206, -4, 8, 6.5, 6.8),
        ],
        "wine",
        square=0.91,
        form=pectoral,
    )
    chest = [
        (-81, 173),
        (-70, 158),
        (-57, 151),
        (-37, 146),
        (-20, 145),
        (-9, 153),
        (-6, 157),
        (6, 157),
        (9, 153),
        (20, 145),
        (37, 146),
        (57, 151),
        (70, 158),
        (81, 173),
        (74, 184),
        (56, 191),
        (43, 199),
        (36, 209),
        (25, 213),
        (19, 217),
        (-19, 217),
        (-25, 213),
        (-36, 209),
        (-43, 199),
        (-56, 191),
        (-74, 184),
    ]
    trunk.plate(
        "One-piece pectoral cuirass",
        chest,
        "ruby",
        2.35,
        "steel",
        center=(0, 182),
        ridge=0.9,
    )
    for sign in (-1, 1):

        def panel(name, path, c, h, sign=sign, **kwargs):
            trunk.plate(name + str(sign), mirrored(path, sign), c, h, **kwargs)

        panel(
            "Shoulder yoke",
            [
                (19, 141),
                (33, 136),
                (69, 139),
                (108, 151),
                (105, 174),
                (85, 167),
                (70, 155),
                (48, 147),
                (24, 148),
            ],
            "red",
            1.12,
        )
        panel(
            "Collar flange",
            [(26, 141), (36, 135), (58, 138), (64, 143), (44, 141), (29, 146)],
            "silver",
            1.76,
        )
        panel(
            "Axillary titanium rail",
            [
                (39, 210),
                (54, 194),
                (81, 184),
                (101, 183),
                (104, 189),
                (72, 193),
                (58, 201),
                (50, 215),
                (42, 219),
            ],
            "silver",
            1,
        )
        for i in range(4):
            v = 196 + 12 * i
            panel(
                "Oblique flank louvre " + str(i + 1),
                [
                    (36, v + 19),
                    (54, v + 6),
                    (90, v - 4),
                    (108, v - 7),
                    (107, v + 1),
                    (85, v + 8),
                    (60, v + 16),
                    (44, v + 26),
                ],
                "red",
                1.31,
            )
            panel(
                "Intercostal articulated link " + str(i + 1),
                [
                    (32, v + 22),
                    (36, v + 16),
                    (43, v + 14),
                    (48, v + 19),
                    (44, v + 23),
                    (39, v + 20),
                    (34, v + 26),
                ],
                "steel",
                1.01,
            )
        panel(
            "Iliac crest",
            [
                (30, 268),
                (39, 262),
                (58, 252),
                (72, 251),
                (72, 268),
                (79, 283),
                (82, 291),
                (60, 290),
                (49, 295),
                (40, 303),
                (29, 305),
                (35, 289),
                (42, 283),
            ],
            "ruby",
            1.27,
        )
        panel(
            "Ventral hip tendon",
            [
                (27, 277),
                (32, 264),
                (40, 248),
                (47, 243),
                (51, 245),
                (44, 258),
                (42, 272),
                (46, 275),
                (40, 279),
            ],
            "gold",
            1.32,
        )
    for i, (v0, v1, w) in enumerate(
        ((215, 231, 36), (229, 245, 33), (243, 260, 33), (258, 276, 34), (274, 294, 37))
    ):
        pts = [
            (-w - 4, v0 - 6),
            (-w + 3, v0 - 1),
            (-16, v0 + 3),
            (16, v0 + 3),
            (w - 3, v0 - 1),
            (w + 4, v0 - 6),
            (w, v1 - 8),
            (22, v1 - 1),
            (11, v1 + 1),
            (-11, v1 + 1),
            (-22, v1 - 1),
            (-w, v1 - 8),
        ]
        trunk.plate(
            "Floating abdominal lame " + str(i + 1),
            pts,
            "red" if i % 2 else "ruby",
            1.2 + 0.13 * (4 - i),
            "wine",
            center=(0, (v0 + v1) / 2),
        )
    trunk.plate(
        "Pelvic apron",
        [
            (-58, 293),
            (-34, 292),
            (-25, 296),
            (25, 296),
            (34, 292),
            (58, 293),
            (49, 303),
            (34, 312),
            (25, 323),
            (11, 331),
            (-11, 331),
            (-25, 323),
            (-34, 312),
            (-49, 303),
        ],
        "red",
        1.42,
        "wine",
        center=(0, 308),
        ridge=0.54,
    )
    back = [
        (180, 267),
        (162, 262),
        (151, 250),
        (143, 232),
        (141, 217),
        (127, 204),
        (112, 183),
        (114, 166),
        (125, 152),
        (142, 148),
        (165, 157),
        (180, 166),
        (195, 157),
        (218, 148),
        (235, 152),
        (246, 166),
        (248, 183),
        (233, 204),
        (219, 217),
        (217, 232),
        (209, 250),
        (198, 262),
    ]
    trunk.plate(
        "Dorsal spine and double scapular wings",
        back,
        "ruby",
        1.8,
        "steel",
        center=(180, 195),
        ridge=0.85,
    )
    trunk.plate(
        "Gold dorsal collar chevron",
        [
            (116, 148),
            (131, 142),
            (149, 146),
            (177, 155),
            (184, 156),
            (211, 147),
            (230, 142),
            (244, 148),
            (218, 151),
            (196, 162),
            (184, 178),
            (178, 181),
            (165, 168),
            (148, 157),
        ],
        "gold",
        2.05,
        "steel",
        center=(181, 158),
    )
    for sign in (-1, 1):
        for i, (s, v0, v1) in enumerate(((0, 157, 218), (8, 208, 250), (16, 231, 268))):
            pts = [
                (114 + s, v0 + 2),
                (125 + s, v0 - 2),
                (142 + s, v0 + 11),
                (157 + s, v0 + 17),
                (163 + s, v0 + 26),
                (154 + s, v0 + 27),
                (135 + s, v0 + 16),
                (126 + s, v1 - 4),
                (119 + s, v1),
            ]
            trunk.plate(
                "Dorsal overlapping vane " + str((sign, i)),
                [(180 + sign * (p - 180), v) for p, v in pts],
                "ruby" if i == 0 else "bronze" if i == 1 else "silver",
                2.45 if i == 0 else 2.15,
            )
        blade = [
            (123, 152),
            (131, 151),
            (150, 160),
            (161, 173),
            (165, 189),
            (173, 200),
            (176, 219),
            (165, 208),
            (155, 198),
            (150, 179),
            (138, 168),
            (123, 164),
        ]
        trunk.plate(
            "Shoulder blade return " + str(sign),
            [(180 + sign * (p - 180), v) for p, v in blade],
            "ruby",
            2.51,
            "wine",
        )
        blade = [
            (113, 177),
            (125, 180),
            (142, 192),
            (150, 192),
            (155, 196),
            (151, 201),
            (136, 198),
            (123, 188),
            (112, 185),
        ]
        trunk.plate(
            "Infraspinous titanium frame " + str(sign),
            [(180 + sign * (p - 180), v) for p, v in blade],
            "silver",
            2.37,
        )
        pts = [
            (99, 209),
            (127, 218),
            (146, 231),
            (157, 246),
            (155, 255),
            (143, 254),
            (138, 244),
            (120, 235),
            (101, 232),
        ]
        trunk.plate(
            "Lower dorsal gold rib " + str(sign),
            [(180 + sign * (p - 180), v) for p, v in pts],
            "gold",
            1.68,
        )
    trunk.plate(
        "Lumbar lock",
        [
            (153, 250),
            (163, 253),
            (167, 263),
            (178, 266),
            (196, 263),
            (204, 252),
            (216, 249),
            (213, 266),
            (201, 274),
            (177, 276),
            (159, 268),
        ],
        "silver",
        1.31,
    )
    trunk.plate(
        "Sacral and hip guard",
        [
            (108, 288),
            (124, 273),
            (151, 270),
            (179, 278),
            (209, 271),
            (236, 274),
            (251, 288),
            (237, 307),
            (216, 312),
            (192, 310),
            (180, 306),
            (166, 310),
            (145, 313),
            (124, 309),
        ],
        "red",
        1.26,
        "wine",
        center=(180, 294),
        ridge=0.66,
    )

    neck = Casting(
        a,
        "Cervical articulation",
        [
            (113, 201, -5.2, 11, 7, 8),
            (122, 201, -4.8, 15, 8.5, 10),
            (130, 203, -4, 16, 9.5, 11),
            (139, 205, -3, 19, 11, 12),
            (150, 206, -2, 26, 13, 14),
        ],
        "red",
    )
    for i in range(4):
        neck.band("Overlapping collar ring " + str(i + 1), 121 + i * 5, 3.1, "red", 2)
    for side in (-1, 1):
        neck.plate(
            "Neck tendon " + str(side),
            mirrored(
                [(18, 124), (29, 123), (60, 129), (70, 142), (48, 142), (33, 137)], side
            ),
            "ruby",
            1.02,
        )
    trunk.plate(
        "Clavicular notch",
        [
            (0, 156),
            (-9, 154),
            (-15, 146),
            (-15, 143),
            (-12, 143),
            (-7, 149),
            (0, 152),
            (7, 149),
            (12, 143),
            (15, 143),
            (15, 146),
            (9, 154),
        ],
        "steel",
        1.05,
    )
    source = [
        (-12.2, 174.8),
        (-10.6, 172.8),
        (-7.4, 172.5),
        (-2, 174.5),
        (2, 174.5),
        (7.4, 172.5),
        (10.6, 172.8),
        (12.2, 174.8),
        (9.8, 181.4),
        (4.6, 191),
        (1.4, 195.7),
        (-1.4, 195.7),
        (-4.6, 191),
        (-9.8, 181.4),
    ]
    for label, pigment, size, h in (
        ("Reactor gasket", "seal", 1.13, 3.43),
        ("Brushed reactor bevel", "silver", 1, 3.69),
        ("Reactor optical seat", "steel", 0.86, 3.86),
        ("Triangular arc window", "crystal", 0.76, 3.96),
    ):
        pts = [(u * size, 182 + (v - 182) * size) for u, v in source]
        trunk.plate(label, pts, pigment, h, edge="steel", center=(0, 182.5))
    for row in range(4):
        for col in range(6 - row):
            u = (col - (5 - row) / 2) * 2.19
            v = 177.5 + row * 3.2
            trunk.plate(
                "Optical prism " + str((row, col)),
                [
                    (u - 1.04, v - 0.45),
                    (u + 0.91, v - 0.5),
                    (u + 0.63, v + 0.63),
                    (u, v + 1.5),
                ],
                "lens" if (row + col) % 3 else "silver",
                4.23,
                edge="crystal",
            )


def limb(a, name, rows, side, color, **kwargs):
    centers = np.asarray(
        [
            (287, 184, 235),
            (309, 181, 239),
            (320, 180, 241),
            (330, 178, 243),
            (337, 177, 244),
            (350, 175, 245),
            (360, 173, 246),
            (375, 171, 250.5),
            (396, 168.5, 254.5),
            (412, 165.5, 258.5),
            (430, 161.5, 263.5),
            (438, 160, 265.5),
            (451, 158.5, 268.5),
            (477, 151.5, 276.5),
            (510, 145.5, 282),
            (535, 144, 284),
            (558, 143, 287.5),
            (572, 142, 289.5),
            (581, 139.5, 293),
            (595.5, 137.5, 295),
        ]
    )
    leg = name in {
        "thigh and hip bearing",
        "knee articulation",
        "calf and greave",
        "sabatons",
    }
    profile = []
    for v, offset, cy, rx, fore, aft in rows:
        cx = (
            np.interp(v, centers[:, 0], centers[:, 1 if side < 0 else 2])
            if leg
            else 206 + side * offset
        )
        profile.append((v, cx, cy, rx, fore, aft))
    return Casting(
        a,
        ("Left " if side == 1 else "Right ") + name,
        profile,
        color,
        side=side,
        **kwargs,
    )


def make_leg(a, side):
    thigh = limb(
        a,
        "thigh and hip bearing",
        [
            (287, 32, 1, 12, 12, 13),
            (300, 39, 2, 19.5, 16.5, 17),
            (319, 43, 1.4, 24.4, 18.1, 18),
            (343, 47, -0.1, 25.1, 20.2, 17.4),
            (358, 49, -1.5, 23, 20.5, 16.5),
            (385, 53, -2.8, 20, 18.7, 15.5),
            (409, 57, -4, 15.7, 15.5, 13.5),
            (425, 59, -3.7, 15.3, 13.7, 13.4),
            (438, 60, -3, 14.2, 11.3, 12),
        ],
        side,
        "bronze",
        square=0.9,
    )
    thigh.plate(
        "Inguinal red coupler",
        [
            (-135, 303),
            (-115, 294),
            (-53, 290),
            (19, 293),
            (76, 299),
            (108, 310),
            (100, 319),
            (66, 324),
            (30, 317),
            (4, 306),
            (-48, 304),
            (-87, 314),
        ],
        "red",
        1.45,
    )
    thigh.plate(
        "Quadriceps champagne cuisse",
        [
            (-17, 331),
            (8, 318),
            (33, 316),
            (57, 324),
            (71, 337),
            (76, 359),
            (68, 382),
            (48, 394),
            (23, 405),
            (4, 409),
            (-12, 404),
            (-21, 391),
            (-28, 362),
            (-28, 345),
        ],
        "gold",
        1.62,
        "steel",
        center=(20, 361),
        ridge=0.68,
    )
    thigh.plate(
        "Adductor inner leaf",
        [
            (-133, 319),
            (-115, 310),
            (-91, 310),
            (-63, 318),
            (-40, 327),
            (-34, 343),
            (-32, 368),
            (-23, 391),
            (-23, 405),
            (-34, 420),
            (-47, 432),
            (-66, 428),
            (-85, 408),
            (-101, 390),
            (-116, 349),
        ],
        "gold",
        1.20,
        "steel",
        center=(-76, 363),
        ridge=0.42,
    )
    thigh.plate(
        "Outer thigh return",
        [
            (77, 328),
            (100, 319),
            (128, 320),
            (146, 333),
            (148, 359),
            (133, 394),
            (109, 417),
            (77, 432),
            (58, 429),
            (71, 408),
            (84, 393),
            (88, 371),
        ],
        "gold",
        1.27,
        "silver",
        center=(110, 370),
        ridge=0.58,
    )
    thigh.plate(
        "Hamstring gold shell",
        [
            (134, 315),
            (156, 308),
            (180, 308),
            (207, 311),
            (224, 322),
            (233, 344),
            (224, 363),
            (211, 382),
            (196, 399),
            (181, 407),
            (164, 404),
            (152, 388),
            (141, 362),
        ],
        "gold",
        1.34,
        "steel",
        center=(183, 352),
    )
    thigh.plate(
        "Titanium inguinal branch",
        [
            (-114, 308),
            (-97, 304),
            (-78, 301),
            (-64, 302),
            (-47, 307),
            (-30, 313),
            (-19, 318),
            (-9, 325),
            (-7, 333),
            (-18, 331),
            (-33, 324),
            (-47, 321),
            (-65, 317),
            (-82, 316),
            (-102, 320),
            (-121, 328),
        ],
        "silver",
        1.61,
        "steel",
        center=(-62, 312),
        ridge=0.23,
    )
    thigh.plate(
        "Gloss red hip return",
        [
            (-157, 304),
            (-129, 298),
            (-108, 298),
            (-89, 302),
            (-80, 308),
            (-81, 318),
            (-76, 328),
            (-68, 335),
            (-66, 345),
            (-72, 355),
            (-83, 361),
            (-91, 350),
            (-97, 336),
            (-111, 327),
            (-131, 321),
            (-154, 317),
        ],
        "wine",
        1.95,
        "red",
        center=(-104, 322),
        ridge=0.37,
    )
    thigh.sheet(
        "Brushed medial quadriceps joint",
        [
            (317, -43, -39),
            (319, -41, -32),
            (322, -37, -23),
            (328, -31, -18),
            (336, -24, -10),
            (342, -23, -8),
            (354, -28, -14),
            (366, -29, -16),
            (378, -27, -15),
            (386, -23, -12),
            (394, -17, -7),
            (400, -9, 0),
            (405, -2, 8),
            (408, 0, 10),
            (411, 4, 7),
        ],
        ("steel", "silver"),
        2.46,
        "steel",
        lambda a, v, t: 0.085 * math.sin(t * math.pi),
        vertical=True,
    )
    thigh.plate(
        "Tibiofemoral track",
        [
            (-17, 412),
            (-9, 406),
            (7, 411),
            (23, 406),
            (37, 401),
            (34, 415),
            (28, 429),
            (15, 433),
            (-14, 429),
        ],
        "silver",
        1.12,
    )
    knee = limb(
        a,
        "knee articulation",
        [
            (411, 59, -4, 12.2, 12, 12.4),
            (423, 60, -4.6, 16.3, 14.3, 15),
            (438, 62, -4.8, 17.9, 14.6, 14.8),
            (453, 65, -2.9, 16.9, 13, 14.5),
            (463, 66, -1.5, 15.4, 11.2, 13),
        ],
        side,
        "steel",
    )
    for i in range(5):
        v = 418 + i * 5.2
        knee.plate(
            "Popliteal bellows " + str(i + 1),
            [
                (111, v),
                (146, v + 1.4),
                (179, v + 3),
                (213, v + 1.5),
                (245, v),
                (240, v + 3),
                (180, v + 5),
                (117, v + 3.7),
            ],
            "silver",
            0.65,
            edge="steel",
        )
    knee.plate(
        "Patella carapace",
        [
            (-76, 430),
            (-54, 422),
            (-21, 419),
            (17, 419),
            (46, 422),
            (66, 431),
            (60, 441),
            (48, 452),
            (20, 462),
            (0, 465),
            (-24, 460),
            (-45, 451),
            (-61, 442),
        ],
        "bronze",
        1.42,
        center=(0, 440),
    )
    knee.plate(
        "Patella raised shield",
        [
            (-44, 425),
            (-23, 421),
            (12, 421),
            (40, 424),
            (44, 432),
            (31, 440),
            (18, 446),
            (-3, 447),
            (-24, 445),
            (-40, 435),
        ],
        "gold",
        2.23,
        edge="bronze",
        center=(0, 432),
        ridge=0.42,
    )
    shin = limb(
        a,
        "calf and greave",
        [
            (444, 64, -2.2, 14.5, 11, 13),
            (458, 66, 0.5, 18.2, 14.4, 16),
            (477, 69, 2.2, 21.7, 13.8, 19.7),
            (496, 72, 4.8, 21.4, 13.9, 22.3),
            (512, 74, 5.8, 18.5, 13.1, 20.1),
            (533, 77, 6.3, 15.3, 11.3, 15.9),
            (553, 80, 5.8, 13.2, 9, 11.8),
            (565, 81, 4.9, 12.7, 8.7, 11.2),
            (577, 82, 3.0, 13, 9.7, 11.4),
        ],
        side,
        "red",
        square=0.9,
    )
    shin.plate(
        "Greave titanium gorget",
        [
            (-110, 449),
            (-76, 450),
            (-52, 457),
            (-16, 465),
            (0, 467),
            (26, 463),
            (58, 453),
            (79, 446),
            (91, 450),
            (70, 464),
            (45, 471),
            (7, 478),
            (-18, 475),
            (-60, 468),
            (-91, 458),
        ],
        "silver",
        1.1,
        center=(0, 465),
    )
    shin.plate(
        "Raised tibial guard",
        [
            (-61, 469),
            (-34, 472),
            (2, 481),
            (29, 476),
            (55, 468),
            (61, 480),
            (48, 495),
            (37, 510),
            (30, 528),
            (28, 552),
            (18, 559),
            (-14, 558),
            (-28, 551),
            (-30, 530),
            (-38, 508),
            (-55, 495),
            (-64, 482),
        ],
        "ruby",
        1.31,
        "red",
        center=(0, 509),
        ridge=1.03,
    )
    shin.plate(
        "Lateral calf vane",
        [
            (69, 456),
            (102, 452),
            (129, 456),
            (151, 467),
            (151, 488),
            (139, 509),
            (127, 529),
            (121, 548),
            (131, 563),
            (114, 569),
            (93, 562),
            (86, 541),
            (71, 523),
            (63, 507),
            (57, 491),
            (68, 476),
        ],
        "ruby",
        1.31,
        center=(105, 507),
    )
    shin.plate(
        "Posterior calf split",
        [
            (148, 461),
            (165, 458),
            (191, 459),
            (212, 466),
            (225, 482),
            (215, 498),
            (199, 513),
            (194, 542),
            (197, 565),
            (184, 574),
            (168, 568),
            (167, 543),
            (163, 515),
            (152, 500),
            (142, 487),
        ],
        "red",
        1.28,
        center=(182, 501),
    )
    shin.plate(
        "Achilles exposed piston",
        [
            (172, 509),
            (179, 504),
            (189, 509),
            (191, 521),
            (188, 552),
            (184, 564),
            (178, 565),
            (174, 557),
            (172, 535),
        ],
        "steel",
        1.71,
    )
    shin.plate(
        "Achilles piston highlight",
        [(178, 517), (183, 512), (186, 517), (184, 547), (181, 554), (178, 547)],
        "silver",
        1.97,
    )
    foot = limb(
        a,
        "sabatons",
        [
            (548, 81, 5.8, 11.8, 8.3, 10.5),
            (558, 82, 4.8, 14.5, 11.1, 12),
            (570, 83, 3.7, 16.5, 16.5, 14.4),
            (578, 84, 3.0, 18, 23, 16),
            (587, 86, 1.5, 22.4, 30.4, 17.8),
            (592, 86, 1, 22.3, 31.7, 17.8),
            (595.5, 86, 1, 21.6, 30.9, 17),
        ],
        side,
        "red",
        angle=7,
        square=0.83,
    )
    foot.band("Dark outsole", 592.8, 1.9, "seal")
    foot.plate(
        "Ankle saddle",
        [
            (-84, 562),
            (-45, 555),
            (-12, 554),
            (28, 556),
            (67, 559),
            (81, 566),
            (58, 579),
            (29, 581),
            (-10, 575),
            (-47, 577),
            (-73, 573),
        ],
        "ruby",
        1.11,
    )
    foot.plate(
        "Instep lames",
        [
            (-57, 574),
            (-14, 573),
            (5, 574),
            (42, 574),
            (60, 577),
            (42, 584),
            (18, 586),
            (-19, 585),
            (-54, 582),
        ],
        "red",
        1.53,
    )
    foot.plate(
        "Toe casting",
        [
            (-62, 585),
            (-30, 582),
            (12, 584),
            (52, 585),
            (70, 589),
            (60, 592),
            (17, 592.6),
            (-29, 592.4),
            (-63, 591),
        ],
        "ruby",
        1.08,
        center=(0, 588),
    )


def make_arm(a, side):
    upper = limb(
        a,
        "upper arm",
        [
            (144, 64, 0.6, 9, 10, 11.2),
            (152, 67, 0.6, 15.3, 14.3, 15.7),
            (165, 70, 0.8, 19.1, 16.2, 17.2),
            (178, 72, 1.3, 19.6, 16.9, 18),
            (190, 73, 2.5, 17.4, 15.2, 17.2),
            (207, 77, 3.3, 15.8, 14.8, 17.5),
            (219, 81, 3.2, 15.3, 14.1, 17),
            (233, 85, 4.7, 12.7, 11.7, 13.3),
            (243, 86, 5, 11.6, 10.1, 12.3),
        ],
        side,
        "bronze",
        square=0.93,
    )
    upper.plate(
        "Shoulder dome",
        [
            (8, 145),
            (35, 141),
            (77, 143),
            (107, 147),
            (134, 151),
            (151, 164),
            (145, 179),
            (124, 187),
            (97, 192),
            (78, 184),
            (63, 174),
            (44, 167),
            (17, 164),
            (-2, 159),
        ],
        "gold",
        1.76,
        "silver",
        center=(78, 161),
        ridge=0.71,
    )
    upper.plate(
        "Shoulder front scale",
        [
            (-60, 151),
            (-32, 146),
            (-12, 146),
            (12, 151),
            (34, 160),
            (41, 167),
            (18, 170),
            (0, 177),
            (-30, 184),
            (-49, 179),
            (-58, 166),
        ],
        "gold",
        1.64,
        "steel",
        center=(-12, 163),
    )
    upper.plate(
        "Shoulder rear scale",
        [
            (129, 148),
            (155, 147),
            (182, 152),
            (206, 163),
            (218, 178),
            (207, 184),
            (184, 181),
            (162, 174),
            (145, 169),
        ],
        "gold",
        1.55,
        "steel",
        center=(173, 163),
    )
    upper.plate(
        "Biceps plate",
        [
            (-79, 200),
            (-54, 194),
            (-30, 189),
            (-4, 186),
            (19, 189),
            (43, 193),
            (61, 203),
            (68, 218),
            (55, 229),
            (34, 237),
            (10, 240),
            (-16, 237),
            (-33, 230),
            (-47, 224),
            (-69, 210),
        ],
        "gold",
        1.50,
        center=(-3, 211),
        ridge=0.76,
    )
    upper.plate(
        "Triceps plate",
        [
            (72, 194),
            (96, 188),
            (121, 183),
            (153, 182),
            (179, 186),
            (195, 197),
            (204, 209),
            (193, 216),
            (171, 222),
            (140, 236),
            (117, 237),
            (105, 228),
            (96, 216),
        ],
        "gold",
        1.41,
        center=(140, 207),
        ridge=0.77,
    )
    upper.plate(
        "Inner elbow bracket",
        [
            (-145, 205),
            (-128, 200),
            (-103, 204),
            (-81, 214),
            (-64, 229),
            (-47, 237),
            (-59, 242),
            (-84, 238),
            (-107, 230),
            (-133, 224),
        ],
        "silver",
        0.73,
    )
    fore = limb(
        a,
        "vambrace",
        [
            (226, 85, 4.2, 10.2, 9.4, 11),
            (235, 88, 3.5, 13.2, 12.6, 13.3),
            (245, 92, 0.8, 17.1, 14, 16.8),
            (261, 97, -2.5, 18.8, 14.4, 16.6),
            (274, 100, -5.9, 17.2, 12.9, 15.2),
            (288, 101, -9.2, 13.9, 11.1, 12.1),
            (300, 102, -12.1, 11.3, 8.6, 9.9),
            (305, 102, -12.6, 11.5, 9.1, 10),
        ],
        side,
        "red",
    )
    fore.plate(
        "Vambrace silver bed",
        [
            (-57, 237),
            (-25, 230),
            (12, 231),
            (49, 241),
            (68, 258),
            (63, 269),
            (46, 271),
            (15, 266),
            (-22, 259),
            (-44, 248),
        ],
        "silver",
        1.17,
    )
    fore.plate(
        "Crimson dorsal gauntlet",
        [
            (-35, 238),
            (-19, 231),
            (-2, 228),
            (18, 230),
            (40, 238),
            (54, 250),
            (56, 260),
            (49, 267),
            (33, 265),
            (10, 260),
            (-15, 256),
            (-31, 251),
        ],
        "ruby",
        2.0,
        "wine",
        center=(14, 248),
        ridge=0.68,
    )
    fore.plate(
        "Vambrace outer crease",
        [
            (50, 239),
            (83, 238),
            (108, 246),
            (124, 258),
            (135, 263),
            (128, 278),
            (105, 291),
            (73, 301),
            (56, 299),
            (67, 280),
            (67, 266),
        ],
        "ruby",
        1.43,
        "red",
        center=(94, 269),
    )
    fore.plate(
        "Inner forearm flexor",
        [
            (-145, 240),
            (-119, 237),
            (-89, 249),
            (-65, 260),
            (-41, 272),
            (-31, 289),
            (-42, 297),
            (-76, 299),
            (-103, 286),
            (-131, 268),
        ],
        "ruby",
        1.11,
    )
    fore.plate(
        "Ulnar spine",
        [
            (146, 236),
            (169, 235),
            (188, 243),
            (201, 255),
            (205, 277),
            (197, 289),
            (178, 300),
            (162, 298),
            (169, 279),
            (165, 260),
        ],
        "ruby",
        1.43,
    )
    for k in range(3):
        fore.plate(
            "Distal wrist ribs " + str(k),
            [
                (74, 287 + k * 3),
                (99, 284 + k * 3),
                (126, 282 + k * 3),
                (136, 283 + k * 3),
                (126, 285 + k * 3),
                (96, 288 + k * 3),
                (75, 290 + k * 3),
            ],
            "silver",
            0.73,
        )
    hand = limb(
        a,
        "closed gauntlet",
        [
            (292, 102, -11, 9.3, 8, 8.8),
            (301, 102, -13, 12.7, 10, 11),
            (310, 103, -15.9, 15, 11.5, 12.6),
            (319, 103.5, -18, 15.4, 11.8, 12.2),
            (328, 103, -18.9, 13.2, 10.6, 10.6),
            (335, 102, -18.9, 7.4, 7, 8.7),
        ],
        side,
        "wine",
        angle=-8,
        square=0.85,
    )
    hand.plate(
        "Metacarpal guard",
        [
            (14, 306),
            (37, 295),
            (64, 292),
            (103, 296),
            (128, 305),
            (139, 318),
            (125, 325),
            (99, 329),
            (71, 324),
            (54, 319),
            (27, 317),
        ],
        "ruby",
        1.51,
        center=(79, 311),
        ridge=0.47,
    )
    for j in range(4):
        start = -10 + j * 26
        drop = abs(1 - j) * 0.95
        for k, (v0, v1) in enumerate(((316, 324.8), (324.6, 330.7), (330.1, 334))):
            hand.plate(
                "Finger phalanx " + str((j + 1, k + 1)),
                [
                    (start - 10, v0 + drop + 1.5),
                    (start - 4, v0 + drop),
                    (start + 7, v0 + drop + 0.4),
                    (start + 12, v0 + drop + 2.5),
                    (start + 10, v1 + drop),
                    (start - 3, v1 + drop + 0.9),
                    (start - 10, v1 + drop - 0.6),
                ],
                "ruby" if k == 0 else "red" if k == 1 else "bronze",
                1.47 if k == 0 else 0.91,
                edge="wine",
                ridge=0.36,
            )
    hand.plate(
        "Folded thumb",
        [
            (-125, 308),
            (-106, 305),
            (-82, 306),
            (-63, 310),
            (-48, 315),
            (-27, 318),
            (-16, 321),
            (-24, 326),
            (-39, 329),
            (-60, 328),
            (-80, 321),
            (-103, 319),
            (-121, 315),
        ],
        "ruby",
        1.76,
        center=(-74, 316),
        ridge=0.8,
    )
    for k in range(6):
        hand.plate(
            "Glove palm flex slot " + str(k),
            [
                (-129, 299 + k * 2.85),
                (-153, 297 + k * 2.85),
                (-172, 298 + k * 2.85),
                (-181, 300 + k * 2.85),
                (-170, 300.6 + k * 2.85),
                (-149, 300 + k * 2.85),
                (-132, 302 + k * 2.85),
            ],
            "steel",
            0.58,
            edge="seal",
        )


def make_helmet(a):
    def tool(angle, v):
        phi = abs((angle + 180) % 360 - 180)
        brow = math.exp(-(((phi - 27) / 21) ** 2) - ((v - 90.9) / 4.7) ** 2)
        cheek = math.exp(-(((phi - 47) / 13) ** 2) - ((v - 101.3) / 8.1) ** 2)
        bridge = math.exp(-((phi / 11) ** 2) - ((v - 97) / 8.1) ** 2)
        return 0.18 * brow + 0.41 * cheek + 0.16 * bridge

    helmet = Casting(
        a,
        "Helmet",
        [
            (60, 198, -5.4, 0.15, 0.1, 0.13),
            (61.8, 198, -5.35, 10.1, 6.7, 6.4),
            (64.1, 198, -5.2, 16.1, 10.3, 10),
            (68, 198, -5.1, 20.7, 13.4, 12.1),
            (74, 198, -5.5, 23.3, 16.3, 14.4),
            (83, 198, -5.5, 24.2, 17.4, 15.7),
            (93, 198, -5.5, 24, 17.5, 16.7),
            (101, 198, -5.8, 23, 17.8, 15.5),
            (110, 198, -6.2, 20, 16.6, 14.2),
            (118, 197.6, -6.8, 17.8, 15, 12.9),
            (123, 197.8, -6.9, 16, 13.7, 11.2),
            (128, 198.1, -6.2, 11, 10, 9.7),
        ],
        "red",
        angle=-9,
        square=0.78,
        form=tool,
    )
    helm = helmet.plate

    def cheekplane(a, v, t):
        angle = abs(a)
        broad = 0.91 * math.exp(-((angle / 24) ** 2))
        hinge = 54 - 19 * t
        cheek = 0.35 * math.tanh((angle - hinge) / 7)
        return broad + cheek * (0.55 + 0.45 * math.sin(math.pi * t)) + 0.16 * (1 - t)

    def contour(stations):
        return [(-a, hi, lo) for a, hi, lo in stations[:0:-1]] + stations

    helmet.sheet(
        "Sweep-formed brow",
        contour(
            [
                (0, 79.0, 92.6),
                (3.1, 79.0, 92.55),
                (5.1, 78.73, 92.48),
                (13.9, 74.9, 92.15),
                (28, 70.7, 91.75),
                (46, 68.15, 91.33),
                (55, 67.35, 90.70),
                (61, 67.55, 89.79),
                (66, 68.0, 89.05),
                (69, 69.1, 89.42),
            ]
        ),
        "gold",
        0.87,
        "bronze",
        lambda a, v, t: (
            0.19 * np.interp(abs(a), (0, 26, 49, 72), (1, 0.72, 0.19, 0.41))
            + 0.18 * (1 - t)
        ),
    )
    helmet.sheet(
        "Stamped maxillary and cheek face",
        contour(
            [
                (0, 92.72, 115.3),
                (8, 92.70, 115.30),
                (14, 92.62, 115.31),
                (17, 93.73, 115.32),
                (21, 94.46, 115.43),
                (25, 94.65, 116.15),
                (29, 94.73, 117.7),
                (33, 94.70, 116.95),
                (40, 94.36, 112.2),
                (46, 93.57, 109.2),
                (49, 92.68, 108.0),
                (51, 91.50, 107.2),
                (52.5, 90.97, 106.7),
                (56, 90.53, 105.23),
                (62, 89.71, 103.28),
                (67, 88.99, 101.41),
                (69, 89.44, 100.02),
                (73, 92.70, 98.12),
            ]
        ),
        "gold",
        0.91,
        "bronze",
        cheekplane,
    )
    helmet.sheet(
        "Inlaid narrow oral joint",
        contour(
            [
                (0, 115.28, 115.85),
                (18, 115.32, 115.90),
                (22, 115.44, 116.03),
                (29, 117.67, 118.31),
                (33, 116.94, 117.64),
                (38, 114.0, 114.83),
            ]
        ),
        "steel",
        0.76,
        "bronze",
        lambda a, v, t: 0.63 * np.interp(abs(a), (0, 22, 40), (1, 0.7, 0.3)),
    )
    helmet.sheet(
        "Chin folding below the mouth seam",
        contour(
            [
                (0, 115.72, 121.75),
                (11, 115.72, 121.75),
                (17, 115.76, 121.87),
                (22, 115.97, 122.82),
                (29, 118.18, 124.42),
                (33, 117.62, 123.76),
                (38, 114.74, 122.31),
                (40, 114.4, 120.3),
            ]
        ),
        "gold",
        1.02,
        "bronze",
        lambda a, v, t: (
            0.70 * np.interp(abs(a), (0, 18, 29, 40), (1, 0.90, 0.30, 0.13))
            + 0.22 * math.sin(t * math.pi)
        ),
    )
    for sign in (-1, 1):

        def panel(label, pts, color, h, sign=sign, **kwargs):
            helm(label + str(sign), mirrored(pts, sign), color, h, **kwargs)

        stations = [
            (13.3, 92.47, 92.96),
            (16.8, 92.34, 93.80),
            (22, 92.12, 94.55),
            (29, 91.91, 94.84),
            (38, 91.59, 94.64),
            (46, 91.27, 93.72),
            (50, 91.13, 92.78),
            (52.3, 91.01, 91.55),
        ]
        slot = [
            (16.0, 92.73, 93.21),
            (19.4, 92.69, 93.74),
            (25, 92.49, 94.12),
            (31, 92.26, 94.16),
            (39, 91.99, 93.90),
            (45, 91.74, 93.19),
            (49.5, 91.43, 92.53),
            (50.8, 91.34, 91.76),
        ]
        for label, lines, pigment, h in (
            ("Inset optical aperture", stations, "steel", 0.62),
            ("Optical lens", slot, "lens", 0.70),
        ):
            helmet.sheet(
                label + str(sign),
                sorted([(u * sign, hi, lo) for u, hi, lo in lines]),
                pigment,
                h,
                "steel",
            )

        def side_sheet(label, rows, metal, depth, edge="seal", sign=sign):
            helmet.sheet(
                label + str(sign),
                sorted([(u * sign, hi, lo) for u, hi, lo in rows]),
                metal,
                depth,
                edge,
            )

        side_sheet(
            "Recessed stepped temporal socket",
            [
                (69.3, 85.8, 94.7),
                (73, 86.2, 95.8),
                (78, 86.05, 95.2),
                (86, 84.85, 92.2),
                (95, 82.7, 89.0),
                (105, 80.8, 86.2),
                (114, 79.6, 84.2),
                (121, 79.2, 82.2),
                (126, 79.7, 80.5),
            ],
            "seal",
            0.51,
        )
        side_sheet(
            "Upper titanium rim over the ear",
            [
                (69.8, 86.05, 87.2),
                (74, 86.51, 88.7),
                (79, 86.22, 89.0),
                (87, 84.8, 87.33),
                (96, 82.7, 85.05),
                (105, 81.13, 82.92),
                (115, 79.79, 81.18),
                (123, 79.43, 80.27),
            ],
            "titanium",
            0.84,
        )
        side_sheet(
            "Lower diagonal titanium latch",
            [
                (70, 87.65, 94.2),
                (74, 89.18, 95.0),
                (79, 89.4, 94.1),
                (87, 87.74, 91.1),
                (96, 85.45, 88.1),
                (106, 83.2, 85.3),
                (115, 81.55, 83.24),
                (121, 80.65, 81.65),
            ],
            "titanium",
            0.88,
        )
        side_sheet(
            "Machined edge below temple latch",
            [
                (71, 94.2, 94.41),
                (75, 94.79, 95.09),
                (80, 93.72, 94.04),
                (88, 90.71, 91.03),
                (98, 87.42, 87.70),
                (106, 85.22, 85.50),
                (116, 82.89, 83.07),
            ],
            "satin titanium",
            0.94,
        )
        side_sheet(
            "Zygomatic recessed guide",
            [
                (38.7, 117.42, 118.05),
                (42, 113.85, 115.31),
                (50, 109.9, 112.0),
                (59, 106.93, 109.15),
                (68, 104.3, 105.8),
                (75, 102.36, 102.97),
                (80, 101.13, 101.40),
            ],
            "titanium",
            0.66,
        )
        side_sheet(
            "Polished cheek edge",
            [
                (39.5, 116.88, 117.08),
                (43, 113.55, 113.87),
                (51, 109.77, 110.09),
                (60, 106.72, 107.08),
                (68, 104.47, 104.79),
                (74, 102.75, 102.98),
                (78, 101.82, 101.99),
            ],
            "satin titanium",
            0.82,
            "titanium",
        )
        panel(
            "Mandibular rail",
            [
                (36, 124),
                (49, 118),
                (69, 111),
                (88, 105),
                (106, 103),
                (118, 106),
                (118, 112),
                (98, 116),
                (80, 119),
                (61, 125),
                (43, 127),
            ],
            "ruby",
            1.25,
        )
        side_sheet(
            "Pressed red auricular shell",
            [
                (78, 97.6, 99.5),
                (86, 93.9, 102.7),
                (98, 89.95, 107.3),
                (111, 86.2, 109.1),
                (121, 84.1, 109.7),
                (131, 81.75, 108.8),
                (138, 82.7, 105.7),
                (145, 86.0, 100.3),
                (149, 89.8, 97.0),
            ],
            "ruby",
            0.73,
            "wine",
        )
    helm(
        "Occipital shell",
        [
            (129, 70),
            (149, 65),
            (177, 63),
            (210, 65),
            (231, 70),
            (237, 81),
            (228, 92),
            (206, 97),
            (181, 99),
            (155, 97),
            (132, 92),
            (123, 83),
        ],
        "ruby",
        0.44,
        "wine",
        center=(179, 80),
    )
    for k in range(3):
        helm(
            "Nape laminate " + str(k + 1),
            [
                (115, 104 + k * 4),
                (135, 100 + k * 4),
                (154, 101 + k * 4),
                (180, 104 + k * 4),
                (204, 101 + k * 4),
                (224, 100 + k * 4),
                (244, 104 + k * 4),
                (237, 107 + k * 4),
                (210, 106 + k * 4),
                (179, 109 + k * 4),
                (151, 106 + k * 4),
                (123, 108 + k * 4),
            ],
            "wine" if k == 2 else "red",
            0.55,
            "steel",
        )


def build(directory):
    work = ROOT / ".review/mk85-component-rebuild/finish"
    work.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assembly = Assembly()
    make_torso(assembly)
    for side in (-1, 1):
        make_leg(assembly, side)
        make_arm(assembly, side)
    make_helmet(assembly)
    (work / "profiles.json").write_text(json.dumps(assembly.charts))
    subprocess.run(
        [
            "uv",
            "--cache-dir",
            str(ROOT / ".review/uv-assets-cache"),
            "run",
            "--no-project",
            "--with",
            "opencv-python-headless==5.1.0.95",
            "--with",
            "scipy==1.18.1",
            "python",
            str(Path(__file__).with_name("mk85-component-enamel.py")),
            str(work),
        ],
        check=True,
    )
    base = pedestal(work)
    for mat, filename in zip(base.data.materials, ("ruins.jpg", "ledge.jpg")):
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(work / filename))
        image.pack()
        image.filepath = "//" + filename
        tex.image = image
        pbr = mat.node_tree.nodes["Principled BSDF"]
        mat.node_tree.links.new(tex.outputs["Color"], pbr.inputs["Base Color"])
        pbr.inputs["Metallic"].default_value = 0.37
        pbr.inputs["Roughness"].default_value = 0.57
    assembly.join(base, work)
    base.name = LABEL
    base.data.name = LABEL
    base["edition"] = "Tongshifu MK85 large"
    base["catalogueDimensionsMm"] = [250, 180, 420]
    base["catalogueMassKg"] = 4.0
    base["armourDetail"] = (
        "Folded helmet, optical slits, overlapping chest and abdominal plates, V-shaped dorsal yoke, pauldron cups, vambraces, knuckles, cuisses, articulated knees, greaves and sabatons."
    )
    base["surfaceRegistration"] = (
        "Form and plate boundaries reconstructed from the supplied front, back and two profile product views."
    )
    bpy.context.view_layer.update()
    if (
        max(abs(x - y) for x, y in zip(base.dimensions, (0.250, 0.180, 0.420)))
        > 0.00003
    ):
        raise ValueError(str(base.dimensions))
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_distance = 0.66
            area.spaces.active.region_3d.view_location = (0, 0, 0.21)
    directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(directory / "mk85.blend"), compress=True)
    print(
        "MK85 CASTING",
        tuple(base.dimensions),
        len(base.data.vertices),
        len(assembly.parts),
    )


if __name__ == "__main__":
    build(Path(sys.argv[-1]).resolve() if "--" in sys.argv else PRODUCT / "Blender")
