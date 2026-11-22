import math
import runpy
import subprocess
from pathlib import Path

import bpy
import bmesh
import numpy as np


scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
review = project / ".review/atelier/artek-60"
solids = runpy.run_path(str(scripts / "product_solids.py"))
finish = runpy.run_path(str(scripts / "vitrine-sculpt.py"))["finish"]


def birch_texture(material):
    size = 512
    y, x = np.mgrid[0:size, 0:size] * (math.tau / size)
    rng = np.random.default_rng(1933)
    wandering = 0.31 * np.sin(y + x) + 0.15 * np.sin(2 * y - x)
    grain = x + wandering + 0.13 * np.sin(4 * x + y)
    bands = np.exp(-np.square(np.sin(10 * grain + 0.8 * np.sin(3 * x))) / 0.12)
    fibres = np.cos(87 * x + 3 * np.sin(y) + 0.7 * np.sin(9 * x - 2 * y))
    tone = 0.98 - 0.055 * bands + 0.014 * fibres + rng.normal(0, 0.008, (size, size))
    pixels = np.ones((size, size, 4), dtype="float32")
    pixels[:, :, :3] = tone[:, :, None] * np.array([0.865, 0.745, 0.590])
    image = bpy.data.images.new("Clear birch · longitudinal fibres", size, size)
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(review / "birch-grain.jpg")
    image.file_format = "JPEG"
    image.save()
    bpy.data.images.remove(image)
    image = bpy.data.images.load(str(review / "birch-grain.jpg"))
    image.pack()
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    material.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])


def mesh(name, points, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata([tuple(q * 0.001 for q in p) for p in points], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    return obj


def rings(name, levels, mat):
    count = len(levels[0])
    faces = [tuple(reversed(range(count)))]
    for row in range(len(levels) - 1):
        for i in range(count):
            j = (i + 1) % count
            faces.append(
                (
                    row * count + i,
                    row * count + j,
                    (row + 1) * count + j,
                    (row + 1) * count + i,
                )
            )
    faces.append(tuple(range((len(levels) - 1) * count, len(levels) * count)))
    return mesh(name, [p for level in levels for p in level], faces, mat)


def turned(name, profile, mat, sections=96):
    levels = [
        [
            (
                r * math.cos(i * math.tau / sections),
                r * math.sin(i * math.tau / sections),
                h,
            )
            for i in range(sections)
        ]
        for r, h in profile
    ]
    obj = rings(name, levels, mat)
    for face in list(obj.data.polygons)[1:-1]:
        face.use_smooth = True
    return obj


def leg_path():
    path = [(196.3, 0, 0), (196.3, 2, 0), (194.4, 339, 0)]
    for i in range(1, 31):
        a = math.pi / 2 * i / 30
        path.append((134.9 + 59.5 * math.cos(a), 339 + 59.5 * math.sin(a), a))
    path.append((71, 398.5, math.pi / 2))
    return path


def bend_leg(mat, path, leg_id, face_veneer=None):
    outline = []
    for u, v, corner in [
        (10.5, 19, 0),
        (-10.5, 19, 90),
        (-10.5, -19, 180),
        (10.5, -19, 270),
    ]:
        for t in range(7):
            a = math.radians(corner + 90 * t / 6)
            outline.append((u + 2 * math.cos(a), v + 2 * math.sin(a)))
        if face_veneer and corner in (0, 180):
            marks = sorted(
                [d + delta for d in [-8, -4, 0, 4, 8] for delta in [-0.35, 0.35]],
                reverse=corner == 0,
            )
            outline.extend((m, 21 if corner == 0 else -21) for m in marks)
    section = len(outline)
    levels = [
        [(r + u * math.cos(a), v, h + u * math.sin(a)) for u, v in outline]
        for r, h, a in path
    ]
    obj = rings(f"L-leg {leg_id} · bent solid birch", levels, mat)
    for face in list(obj.data.polygons)[1:-1]:
        face.use_smooth = True
    if face_veneer:
        obj.data.materials.append(face_veneer)
        for face in list(obj.data.polygons)[1:-1]:
            row, j = divmod(face.index - 1, section)
            u, v = outline[j]
            u1, v1 = outline[(j + 1) % section]
            if (
                v == v1
                and abs(v) == 21
                and abs(abs(u - u1) - 0.7) < 0.01
                and path[row][1] >= 300
            ):
                face.material_index = 1
    uv = obj.data.uv_layers.new(name="Bent birch grain")
    lengths = [0]
    for (r, h, _), (r2, h2, _) in zip(path, path[1:]):
        lengths.append(lengths[-1] + math.hypot(r2 - r, h2 - h))
    distances = [0]
    for a, b in zip(outline, outline[1:] + outline[:1]):
        distances.append(distances[-1] + math.dist(a, b))
    for face in obj.data.polygons:
        for li in face.loop_indices:
            vi = obj.data.loops[li].vertex_index
            row, col = divmod(vi, section)
            if face.index in (0, len(obj.data.polygons) - 1):
                u, v = outline[col]
                xy = (u / 110 + 0.3, v / 180 + 0.5)
            else:
                seam = (face.index - 1) % section == section - 1 and col == 0
                xy = (
                    (distances[-1] if seam else distances[col]) / 112 + leg_id * 0.29,
                    lengths[row] / 460 + 0.21 * leg_id,
                )
            uv.data[li].uv = xy
    return obj


def veneer_insert(path, depth, mat, index, cutter=False):
    points = [(194.8, 290 + index * 3, 0), *path[2:]]
    thickness = 0.7
    levels = []
    width = 21.4 if cutter else 21
    for pos, (r, h, a) in enumerate(points):
        half = thickness * (0.04 if pos == 0 else 0.5)
        if cutter and pos == len(points) - 1:
            r -= 0.6
        levels.append(
            [
                (
                    r + (depth + offset) * math.cos(a),
                    v,
                    h + (depth + offset) * math.sin(a),
                )
                for offset, v in [
                    (-half, -width),
                    (half, -width),
                    (half, width),
                    (-half, width),
                ]
            ]
        )
    return rings(f"Glued birch slip {index + 1}", levels, mat)


def screw(r, v, zinc, number, head_only=False):
    sections = 40
    angles = [i * math.tau / sections for i in range(sections)]
    radii = [
        min(2.38, 0.47 / max(0.01, min(abs(math.sin(a)), abs(math.cos(a)))))
        for a in angles
    ]
    levels = []
    profile = [
        (radii, 387.1),
        (radii, 385.72),
        ([4.42] * sections, 385.72),
        ([4.48] * sections, 386.1),
        ([2.4] * sections, 388.5),
    ]
    if not head_only:
        profile.extend([([2.08] * sections, 428), ([0.12] * sections, 430.72)])
    for rs, z in profile:
        levels.append(
            [
                (r + rad * math.cos(a), v + rad * math.sin(a), z)
                for a, rad in zip(angles, rs)
            ]
        )
    obj = rings(f"5 × 45 cross-recess wood screw {number}", levels, zinc)
    for face in list(obj.data.polygons)[1:-1]:
        face.use_smooth = (face.index - 1) // sections >= 2
    return obj


def cylinder_cut(r, v, z1, z2, radius, mat):
    return solids["pin"]("Pilot bore", (r, z1, -v), (r, z2, -v), radius, mat, 28)


def close_seams(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    open_edges = [e for e in bm.edges if e.is_boundary]
    if open_edges:
        bmesh.ops.holes_fill(bm, edges=open_edges, sides=3)
    if any(not e.is_manifold for e in bm.edges):
        raise ValueError(f"Open birch joint on {obj.name}")
    bm.to_mesh(obj.data)
    bm.free()


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    review.mkdir(parents=True, exist_ok=True)
    birch = finish("Stool 60 · clear lacquered birch", "d8bd99", rough=0.42, coat=0.14)
    slip = finish(
        "Stool 60 · end of birch veneer splice", "cba882", rough=0.42, coat=0.14
    )
    green = finish("Stool 60 · pale green lacquer", "a5ad92", rough=0.39, coat=0.24)
    zinc = finish("Stool 60 · zinc plated screws", "97928a", rough=0.32, metal=0.85)
    birch_texture(birch)
    seat = turned(
        "349 mm edge-banded birch seat",
        [
            (172.6, 411),
            (174, 411.3),
            (174.5, 412.2),
            (174.5, 438.6),
            (174.2, 439.5),
            (173.2, 440),
        ],
        green,
    )
    seat["construction"] = "Birch core, plywood facing and solid birch edge"
    inside_seat = []
    for radius, z1, z2, name in [
        (168, 411.9, 414.4, "Lower plywood facing"),
        (168, 414.4, 436.2, "Birch core"),
        (168, 436.2, 439.1, "Upper plywood facing"),
    ]:
        inside_seat.append(turned(name, [(radius, z1), (radius, z2)], birch, 72))
    void = turned("Edge band interior", [(168, 411.9), (168, 439.1)], birch, 72)
    solids["subtract"](seat, [void])
    path = leg_path()
    holes = [(83, 0), (116, -9), (116, 9)]
    for i in range(3):
        angle = math.pi / 2 + i * math.tau / 3
        leg = bend_leg(birch, path, i + 1)
        depths = [-8, -4, 0, 4, 8]
        inserts = [
            veneer_insert(path, depth, slip, k) for k, depth in enumerate(depths)
        ]
        solids["subtract"](
            leg,
            [
                veneer_insert(path, depth, slip, k, True)
                for k, depth in enumerate(depths)
            ],
        )
        screws = [screw(r, v, zinc, 3 * i + j + 1) for j, (r, v) in enumerate(holes)]
        for obj in [leg, *inserts]:
            solids["subtract"](
                obj, [cylinder_cut(r, v, 384, 413, 2.51, birch) for r, v in holes]
            )
            solids["subtract"](obj, [turned_cut(r, v, birch) for r, v in holes])
        close_seams(leg)
        for r, v in holes:
            x, y = (
                r * math.cos(angle) - v * math.sin(angle),
                r * math.sin(angle) + v * math.cos(angle),
            )
            for obj in [seat, *inside_seat[:2]]:
                solids["subtract"](obj, [cylinder_cut(x, y, 410, 431, 2.09, birch)])
        for obj in [leg, *inserts, *screws]:
            obj.rotation_euler.z = angle
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(review / "stool-60.blend"), compress=True)
    for item in list(bpy.context.scene.objects):
        bpy.data.objects.remove(item, do_unlink=True)
    exterior = [
        turned(
            "Lacquered seat",
            [
                (172.6, 411),
                (174, 411.3),
                (174.5, 412.2),
                (174.5, 438.6),
                (174.2, 439.5),
                (173.2, 440),
            ],
            green,
        )
    ]
    visible_path = [*path[:2], (194.6, 300, 0), *path[2:]]
    for i in range(3):
        leg = bend_leg(birch, visible_path, i + 1, slip)
        solids["subtract"](leg, [turned_cut(r, v, birch) for r, v in holes])
        heads = [
            screw(r, v, zinc, 3 * i + j + 1, True) for j, (r, v) in enumerate(holes)
        ]
        for obj in [leg, *heads]:
            obj.rotation_euler.z = math.pi / 2 + i * math.tau / 3
            exterior.append(obj)
    solids["combine"]("Stool 60 · bent birch frame and lacquered seat", exterior)
    target = project / "public/media/models/artek-stool-60.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
    )


def turned_cut(r, v, mat):
    cut = turned(
        "Countersunk screw seat", [(4.58, 384), (4.58, 386.12), (2.48, 388.6)], mat, 40
    )
    cut.location = (r * 0.001, v * 0.001, 0)
    return cut


if __name__ == "__main__":
    build()
