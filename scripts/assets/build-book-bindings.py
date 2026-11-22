import json
import math
import runpy
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
target = root / "public/media/models/bindings"
review = root / ".review/atelier"
write_mesh = runpy.run_path(str(scripts / "blender_mesh.py"))["write_mesh"]
editions = json.loads(
    subprocess.check_output(
        [
            "node",
            "--input-type=module",
            "-e",
            "import {editions} from './src/content/books.ts'; console.log(JSON.stringify(editions));",
        ],
        cwd=root,
    )
)
bpy.ops.wm.read_factory_settings(use_empty=True)


class Surface:
    def __init__(self):
        self.vertices, self.faces, self.uvs, self.smooth = [], [], [], []
        self.indices = {}

    def quad(self, points, mapping, outward, smooth=False):
        points = [Vector(p) for p in points]
        if (points[1] - points[0]).cross(points[2] - points[0]).dot(
            Vector(outward)
        ) < 0:
            points.reverse()
            mapping = list(reversed(mapping))
        face = []
        for p in points:
            v = (p.x / 150, -p.z / 32, p.y / 230)
            key = (v, smooth)
            if key not in self.indices:
                self.indices[key] = len(self.vertices)
                self.vertices.append(v)
            face.append(self.indices[key])
        self.faces.append(face)
        self.uvs.append(mapping)
        self.smooth.append(smooth)

    def object(self, name, collection):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        uv = mesh.uv_layers.new(name="Binding print")
        for poly, coords, smooth in zip(mesh.polygons, self.uvs, self.smooth):
            poly.use_smooth = smooth
            for i, point in zip(poly.loop_indices, coords):
                uv.data[i].uv = point
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj


def build(kind, collection):
    case = kind != "paper"
    jacket = kind == "jacket"
    board = 1.72 if case else 0.39
    cover = 16 - (0.19 if jacket else 0)
    square = 2.55 if case else 0.42
    x0, x1, y0, y1 = -75, 75, -115, 115
    edge = [(0.003, 0.997)] * 4
    paper, front, wrap = Surface(), Surface(), Surface()

    def relief(x):
        if case:
            return 0.56 * math.exp(-(((x + 68.6) / 1.35) ** 2))
        return 0.17 * math.exp(-(((x + 70.6) / 0.58) ** 2))

    rows = [-75, -72.0, -70.7, -69.8, -68.6, -67.2, -65, 72, 74.45, 75]
    for sign in (-1, 1):
        rect = front if sign == 1 else wrap
        skin = cover + (0.19 if jacket else 0)
        for l, r in zip(rows, rows[1:]):
            a, b = (l + 75) / 150, (r + 75) / 150
            u, v = (a, b) if sign == 1 else ((1 - a) * 0.75, (1 - b) * 0.75)
            rect.quad(
                [
                    (l, y0, sign * (skin - relief(l))),
                    (r, y0, sign * (skin - relief(r))),
                    (r, y1, sign * (skin - relief(r))),
                    (l, y1, sign * (skin - relief(l))),
                ],
                [(u, 0), (v, 0), (v, 1), (u, 1)],
                (0, 0, sign),
                True,
            )
        for y in (y0, y1):
            ny = math.copysign(1, y)
            for l, r in zip(rows, rows[1:]):
                wrap.quad(
                    [
                        (l, y, sign * (skin - relief(l))),
                        (r, y, sign * (skin - relief(r))),
                        (r, y, sign * (cover - board)),
                        (l, y, sign * (cover - board)),
                    ],
                    edge,
                    (0, ny, 0),
                )
        wrap.quad(
            [
                (x1, y0, sign * skin),
                (x1, y1, sign * skin),
                (x1, y1, sign * (cover - board)),
                (x1, y0, sign * (cover - board)),
            ],
            edge,
            (1, 0, 0),
        )
        inside = cover - board
        paper.quad(
            [
                (x0 + 1.9, y0 + 0.6, sign * inside),
                (x1 - 0.6, y0 + 0.6, sign * inside),
                (x1 - 0.6, y1 - 0.6, sign * inside),
                (x0 + 1.9, y1 - 0.6, sign * inside),
            ],
            [(0, 0.755), (1, 0.755), (1, 0.785), (0, 0.785)],
            (0, 0, -sign),
        )
        if jacket:
            fold_end = 20
            fold_skin = inside - 0.16
            wrap.quad(
                [
                    (fold_end, y0 + 0.4, sign * fold_skin),
                    (x1 - 0.35, y0 + 0.4, sign * fold_skin),
                    (x1 - 0.35, y1 - 0.4, sign * fold_skin),
                    (fold_end, y1 - 0.4, sign * fold_skin),
                ],
                edge,
                (0, 0, -sign),
            )
            for y in (y0 + 0.4, y1 - 0.4):
                wrap.quad(
                    [
                        (fold_end, y, sign * fold_skin),
                        (x1 - 0.35, y, sign * fold_skin),
                        (x1 - 0.35, y, sign * (fold_skin + 0.14)),
                        (fold_end, y, sign * (fold_skin + 0.14)),
                    ],
                    edge,
                    (0, y, 0),
                )

    crest = 2.7 if case else 0.48

    def spine(t, y):
        return (x0 - crest * (1 - (t * 2 - 1) ** 2), y, (t * 2 - 1) * 16)

    for i in range(16):
        l, r = i / 16, (i + 1) / 16
        wrap.quad(
            [spine(l, y0), spine(r, y0), spine(r, y1), spine(l, y1)],
            [
                (0.75 + l * 0.25, 0),
                (0.75 + r * 0.25, 0),
                (0.75 + r * 0.25, 1),
                (0.75 + l * 0.25, 1),
            ],
            (-1, 0, 0),
            True,
        )
        for y in (y0, y1):
            p, q = spine(l, y), spine(r, y)
            wrap.quad(
                [p, q, (q[0] + board, y, q[2]), (p[0] + board, y, p[2])],
                edge,
                (0, y, 0),
            )

    zmax = cover - board - (0.48 if jacket else 0.22)
    xp = x0 + (2.8 if case else 0.6)
    yp = y1 - square

    def leaf(t):
        z = (2 * t - 1) * zmax
        concave = (1 - (t * 2 - 1) ** 2) * (0.86 if case else 0.29)
        trim = (0.15 if case else 0.095) * math.exp(
            -(((t * 10 % 1) - 0.92) ** 2) / 0.003
        )
        return x1 - square - concave - trim, z

    cuts = [(i + pos) / 10 for i in range(10) for pos in (0, 0.7, 0.92)] + [1]
    for l, r in zip(cuts, cuts[1:]):
        a, z = leaf(l)
        b, v = leaf(r)
        paper.quad(
            [(a, -yp, z), (b, -yp, v), (b, yp, v), (a, yp, z)],
            [(l, 0.05), (r, 0.05), (r, 0.41), (l, 0.41)],
            (1, 0, 0),
            True,
        )
        for y in (-yp, yp):
            row = 0.48 if y > 0 else 0.07
            paper.quad(
                [(xp, y, z), (a, y, z), (b, y, v), (xp, y, v)],
                [(l, row), (l, row + 0.12), (r, row + 0.12), (r, row)],
                (0, y, 0),
            )
        if case:
            for sign in (-1, 1):
                y = sign * (yp + 0.4)
                lift = 0.46 * math.sin(math.pi * (l + r) / 2)
                radius = 0.78
                for k in range(6):
                    phi, psi = (k / 6) * math.pi, (k + 1) / 6 * math.pi

                    def band(c, depth):
                        return (
                            xp - 0.55 + radius * math.cos(c),
                            y + sign * (lift + radius * math.sin(c)),
                            depth,
                        )

                    paper.quad(
                        [band(phi, z), band(phi, v), band(psi, v), band(psi, z)],
                        [(l, 0.90), (r, 0.90), (r, 0.95), (l, 0.95)],
                        (
                            math.cos((phi + psi) / 2),
                            sign * math.sin((phi + psi) / 2),
                            0,
                        ),
                        True,
                    )
    for sign in (-1, 1):
        z = sign * (zmax + 0.08)
        paper.quad(
            [(xp, -yp, z), (x1 - square, -yp, z), (x1 - square, yp, z), (xp, yp, z)],
            [(0, 0.755), (1, 0.755), (1, 0.785), (0, 0.785)],
            (0, 0, sign),
        )
    return {
        name: shape.object(kind + "-" + name, collection)
        for name, shape in (("front", front), ("wrapper", wrap), ("leaves", paper))
    }


def material(name, hex_color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    shader = m.node_tree.nodes.get("Principled BSDF")
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    shader.inputs["Base Color"].default_value = tuple(c**2.2 for c in channels) + (1,)
    shader.inputs["Roughness"].default_value = 0.79
    return m


def print_layer(shader, filename, repeat=1):
    nodes = shader.node_tree.nodes
    links = shader.node_tree.links
    image = bpy.data.images.load(str(filename), check_existing=True)
    if not image.packed_file:
        image.pack()
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    if repeat != 1:
        projection = nodes.new("ShaderNodeVectorMath")
        projection.operation = "MULTIPLY"
        projection.inputs[1].default_value = (repeat, 1, 1)
        uv = nodes.new("ShaderNodeTexCoord")
        links.new(uv.outputs["UV"], projection.inputs[0])
        links.new(projection.outputs["Vector"], texture.inputs["Vector"])
    links.new(
        texture.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"]
    )


graphics = review / "binding-prints"
catalog = json.loads((graphics / "catalog.json").read_text("utf8"))
templates = bpy.data.collections.new("Binding masters")
bpy.context.scene.collection.children.link(templates)
masters = {kind: build(kind, templates) for kind in ("paper", "board", "jacket")}
bpy.context.view_layer.update()
for parts in masters.values():
    for part in parts.values():
        write_mesh(part, target / (part.name + ".mesh"))
templates.hide_render = True
templates.hide_viewport = True
library = bpy.data.collections.new("Published bindings")
bpy.context.scene.collection.children.link(library)
for i, book in enumerate(editions):
    kind = "jacket" if book.get("jacket") else book["binding"]
    support = bpy.data.objects.new(book["en"], None)
    library.objects.link(support)
    w, h, t = book["size"]
    support.location = ((i % 7) * 0.35, 0, (i // 7) * 0.34)
    support["ISBN"] = book["identifier"]
    support["printed_pages"] = book["pages"]
    support["source"] = book["source"]
    if book.get("rearReference"):
        support["rear_reference"] = book["rearReference"]
    cover = material(book["key"] + " · cover", book["cloth"])
    print_layer(cover, root / ("public/media/books/" + book["key"] + ".webp"))
    cloth = material(book["key"] + " · binding", book["cloth"])
    print_layer(cloth, graphics / (book["key"] + ".png"))
    leaves = material(book["key"] + " · paper and headbands", "#e3dbca")
    print_layer(
        leaves,
        graphics / (catalog[book["key"]]["paper"] + ".png"),
        catalog[book["key"]]["x"],
    )
    for name, part in masters[kind].items():
        if not part.data.materials:
            part.data.materials.append(leaves)
        model = bpy.data.objects.new(name, part.data)
        library.objects.link(model)
        model.parent = support
        model.scale = (w, t, h)
        model.material_slots[0].link = "OBJECT"
        model.material_slots[0].material = {
            "front": cover,
            "wrapper": cloth,
            "leaves": leaves,
        }[name]
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = "METRIC"
review.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(review / "published-bindings.blend"))
