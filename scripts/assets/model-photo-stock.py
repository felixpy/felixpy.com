import math
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mesh import write_mesh


def stock(name, width, height, thickness, image, index, regions, curl):
    def rect(cx, cy, w, h):
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    front = [(key, rect(*area)) for key, area in (("image", image), ("index", index)) if area]
    reverse = [(key, rect(*area)) for key, area in regions]
    bounds = rect(0, 0, width, height)
    xs = {-width / 2 + i * width / 8 for i in range(9)}
    ys = {-height / 2 + i * height / 12 for i in range(13)}
    for _, (x0, y0, x1, y1) in front + reverse:
        xs.update((x0, x1))
        ys.update((y0, y1))
    xs = sorted({round(v, 6) for v in xs})
    ys = sorted({round(v, 6) for v in ys})
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    sections = {}

    def point(x, y, front_side):
        u, v = x / width + 0.5, y / height + 0.5
        lift = curl * (max(0, (u - 0.38) / 0.62) * max(0, (0.76 - v) / 0.76)) ** 2
        lift += curl * 0.09 * math.sin(math.pi * u) ** 2 * math.sin(math.pi * v) ** 2
        return (x * 0.001, -(lift + (0.5 if front_side else -0.5) * thickness) * 0.001, y * 0.001)

    def face(key, xy, side, uvrect):
        vertices, faces, uvs, lookup = sections.setdefault(key, ([], [], [], {}))
        corners = []
        for (x, y), f in zip(xy, side):
            co = point(x, y, f)
            if co not in lookup:
                lookup[co] = len(vertices)
                vertices.append(co)
            corners.append(lookup[co])
            u = (x - uvrect[0]) / (uvrect[2] - uvrect[0])
            v = (y - uvrect[1]) / (uvrect[3] - uvrect[1])
            uvs.append((u if f else 1 - u, v))
        faces.append(corners)

    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
            quad = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            for side, patches, default in ((True, front, "face"), (False, reverse, "back")):
                key, area = next(((k, r) for k, r in patches if r[0] < x < r[2] and r[1] < y < r[3]), (default, bounds))
                face(key, quad if side else quad[::-1], [side] * 4, area)
    border = ([(x, ys[0]) for x in xs] + [(xs[-1], y) for y in ys[1:]]
              + [(x, ys[-1]) for x in xs[-2::-1]] + [(xs[0], y) for y in ys[-2:0:-1]])
    for a, b in zip(border, border[1:] + border[:1]):
        face("edge", [a, a, b, b], [True, False, False, True], bounds)

    for key, (verts, faces, uvs, _) in sections.items():
        data = bpy.data.meshes.new(f"{name}-{key}")
        data.from_pydata(verts, [], faces)
        data.update()
        uv = data.uv_layers.new(name="Photographic image registration")
        for loop, coord in zip(uv.uv, uvs):
            loop.vector = coord
        for poly in data.polygons:
            poly.use_smooth = key != "edge"
        part = bpy.data.objects.new(data.name, data)
        collection.objects.link(part)
        part["surfaceRole"] = key
        finish = bpy.data.materials.new(data.name)
        finish.use_nodes = True
        bsdf = finish.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = {
            "pod": (0.06, 0.056, 0.051, 1), "stripe": (0.014, 0.013, 0.012, 1),
            "image": (0.24, 0.26, 0.24, 1),
        }.get(key, (0.9, 0.89, 0.85, 1))
        bsdf.inputs["Roughness"].default_value = 0.62 if key == "image" else 0.85
        bsdf.inputs["Specular IOR Level"].default_value = 0.11 if key == "image" else 0.16
        data.materials.append(finish)
        bpy.context.view_layer.update()
        write_mesh(part, ROOT / "public/media/models/stationery" / f"{data.name}.mesh")
    return collection


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    stock("lab-print", 101.6, 152.4, 0.25908, (0, 2, 96.6, 128.8), (-11.684, -72.0852, 68.072, 6.858), [], 1.1)
    stock("instant-film", 54, 86, 0.58, (0, 5.4, 46, 62), None, [("pod", (0, 5.2, 47.5, 62.4)), ("stripe", (0, -36, 45, 3))], 0.16)
    path = ROOT / ".references/05-摄影与陈列/相框与展示设施/Travel photo board/Blender/photographic-stock.blend"
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
