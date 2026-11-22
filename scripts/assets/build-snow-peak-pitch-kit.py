import math
import runpy
import subprocess
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
bpy.ops.wm.read_factory_settings(use_empty=True)
grain = runpy.run_path(str(scripts / "product-grain.py"))


def cpath(shape, points, radius, material, sides=10, tolerance=0):
    path = []
    for i in range(len(points) - 1):
        a, b, c, d = [
            Vector(points[min(max(k, 0), len(points) - 1)])
            for k in (i - 1, i, i + 1, i + 2)
        ]
        span = (b - c).length
        m = (c - a).normalized() * min(span, (a - b).length)
        n = (d - b).normalized() * min(span, (d - c).length)
        for j in range(7):
            t = j / 7
            path.append(
                b * (2 * t**3 - 3 * t * t + 1)
                + m * (t**3 - 2 * t * t + t)
                + c * (-2 * t**3 + 3 * t * t)
                + n * (t**3 - t * t)
            )
    path.append(Vector(points[-1]))
    if tolerance:
        keep = {0, len(path) - 1}
        spans = [(0, len(path) - 1)]
        while spans:
            start, end = spans.pop()
            chord = path[end] - path[start]
            square = chord.length_squared
            farthest = tolerance
            split = None
            for index in range(start + 1, end):
                delta = path[index] - path[start]
                t = min(max(chord.dot(delta) / square, 0), 1) if square else 0
                distance = (delta - chord * t).length
                if distance > farthest:
                    farthest, split = distance, index
            if split is not None:
                keep.add(split)
                spans.extend(((start, split), (split, end)))
        path = [path[i] for i in sorted(keep)]
    shape.pipe(path, radius, material, sides)


def plate(shape, boundary, holes, thickness, project, material):
    points, edges, loops = [], [], []
    for ring in [boundary] + holes:
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
        if area < 0:
            ring = list(reversed(ring))
        start = len(points)
        points.extend(Vector(point) for point in ring)
        loop = [start + i for i in range(len(ring))]
        loops.append(loop)
        edges.extend(zip(loop, loop[1:] + loop[:1]))
    verts, _, triangles, _, _, ids = delaunay_2d_cdt(points, edges, loops, 0, 0.00001)
    count = len(verts)
    faces = []
    for tri, memberships in zip(triangles, ids):
        if list(memberships) == [0]:
            faces.append(tuple(tri))
            faces.append(tuple(i + count for i in reversed(tri)))
    for a, b in edges:
        faces.append((a, b, b + count, a + count))
    shape.add(
        [project(v.x, v.y, d) for d in (0, thickness) for v in verts],
        faces,
        material,
        False,
    )


def ring(x, y, r, count=24):
    return [
        (x + r * math.cos(i * math.tau / count), y + r * math.sin(i * math.tau / count))
        for i in range(count)
    ]


def guyline():
    rope = Sculpture("Snow Peak Pro 4 mm guyline and R-050-1 tensioner")
    for k in range(14):
        theta = k * math.tau / 14
        dx, dz = 12 * math.cos(theta), 9 * math.sin(theta)
        pts = []
        for j in range(97):
            a = math.tau * j / 96
            x = dx + 17 * math.copysign(abs(math.sin(a)) ** 0.72, math.sin(a))
            h = (92 + 2.8 * math.cos(theta)) * math.copysign(
                abs(math.cos(a)) ** 0.75, math.cos(a)
            )
            pts.append((x, h, dz + 0.053 * h + 1.75 * math.sin(a * 2 + theta)))
        rope.pipe(pts, 1.95, line, 8)
    pts = []
    for i in range(211):
        a = i * math.tau / 28
        pts.append((31.7 * math.cos(a), -19.5 + i * 0.18, 12.8 * math.sin(a)))
    rope.pipe(pts, 2.05, line, 8)
    cpath(
        rope,
        [(28, 0, 0), (31, -20, 3), (34, -48, 4), (39, -68, 6), (36, -87, 8)],
        2,
        line,
    )
    cpath(
        rope,
        [(36, -85, 8), (35, -95, 11), (32, -99, 12), (27, -96, 12), (26, -88, 11)],
        2,
        line,
    )
    ends = [
        (-6.4, -17),
        (-5.8, -21),
        (-3.7, -23),
        (3.7, -23),
        (5.8, -21),
        (6.4, -17),
        (5.3, -6),
        (4.2, 0),
        (5.3, 6),
        (6.4, 17),
        (5.8, 21),
        (3.7, 23),
        (-3.7, 23),
        (-5.8, 21),
        (-6.4, 17),
        (-5.3, 6),
        (-4.2, 0),
        (-5.3, -6),
    ]
    plate(
        rope,
        ends,
        [ring(0, -15, 2.8), ring(0, 15, 2.8)],
        1.8,
        lambda x, h, d: (
            30 + x + h * 0.26,
            -75 + h,
            9 + d + 3.9 * math.cos(h * math.pi / 40),
        ),
        red,
    )
    obj = rope.finalize()
    obj.location = (-0.268, -0.097, 1.963)
    mesh = obj.data
    uv = mesh.uv_layers.new(name="Braided sheath")
    path_index = 0
    for face in mesh.polygons:
        if mesh.materials[face.material_index] != line:
            continue
        if len(face.vertices) != 4:
            continue
        strand = path_index % 8
        segment = path_index // 8
        for index, coord in zip(
            face.loop_indices,
            [
                (strand / 8, segment * 0.43),
                ((strand + 1) / 8, segment * 0.43),
                ((strand + 1) / 8, (segment + 1) * 0.43),
                (strand / 8, (segment + 1) * 0.43),
            ],
        ):
            uv.data[index].uv = coord
        path_index += 1
    y, x = np.indices((96, 64))
    stitch = (x / 64 * 4 + y / 96 * 3) % 1
    accent = (abs(stitch - 0.52) < 0.15) & ((x // 8 + y // 16) % 3 != 0)
    dark = np.where(((x / 8 - y / 11) % 1) < 0.17, 0.64, 1.0)
    rgb = (
        np.where(
            accent[:, :, None],
            np.array([0.60, 0.17, 0.095]),
            np.array([0.38, 0.41, 0.39]),
        )
        * dark[:, :, None]
    )
    tex = grain["image"]("Interwoven grey and red polypropylene", rgb)
    tex.colorspace_settings.name = "sRGB"
    image_node = line.node_tree.nodes.new("ShaderNodeTexImage")
    image_node.image = tex
    line.node_tree.links.new(
        image_node.outputs[0],
        line.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    hook = Sculpture("Guyline · double-prong rack hanger")
    for x in (-279, -254):
        cpath(
            hook,
            [
                (x, 2074, 44),
                (x, 2071, 54),
                (x, 2058, 68),
                (x, 2054, 76),
                (x, 2054, 98),
                (x, 2056, 104),
                (x, 2060, 106),
            ],
            2.15,
            keeper,
        )
    hook.finalize()


review = root / ".review/atelier"
fireplace_tools = runpy.run_path(str(scripts / "snow-peak-fireplace.py"))
fireplace_tools["build"](Sculpture, finish, cpath)
source = review / "takibi-m/st-033r.blend"
source.parent.mkdir(parents=True, exist_ok=True)
bpy.context.scene.name = "Snow Peak Pack & Carry Fireplace M"
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active.region_3d
            view.view_location = (0, 0, 0.225)
            view.view_distance = 0.88
            view.view_rotation = Vector((-0.13, 1, -0.15)).to_track_quat("-Z", "Y")
bpy.ops.wm.save_as_mainfile(filepath=str(source), copy=True, compress=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
keeper = finish("Rack · coated steel", "464845", 0.61, 0.44)
red = finish("Red anodised aluminium", "a72d32", 0.78, 0.34)
line = finish("Pro guyline · grey with vermilion tracers", "fafafa", 0, 0.80)
aurora_tools = runpy.run_path(str(scripts / "snow-peak-aurora.py"))
aurora = aurora_tools["build"](Sculpture, finish)
aurora_source = review / "aurora-800"
aurora_source.mkdir(parents=True, exist_ok=True)
product_scene = bpy.context.scene
product_scene.name = "Snow Peak Aurora Bottle 800 Rainbow"
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active.region_3d
            view.view_location = (0, 0, 0.115)
            view.view_distance = 0.46
            view.view_rotation = Vector((-0.48, 1, -0.25)).to_track_quat("-Z", "Y")
bpy.ops.wm.save_as_mainfile(
    filepath=str(aurora_source / "tw-800-ra.blend"), copy=True, compress=True
)
aurora_tools["export_inside"](aurora, root / "public/media/models/aurora-bottle-interior.glb")
product_scene.name = "Snow Peak pitch kit"
aurora.location = (-0.145, -0.171, 1.075)
with bpy.data.libraries.load(str(source), link=False) as (library, loaded):
    loaded.objects = list(library.objects)
for part in loaded.objects:
    product_scene.collection.objects.link(part)
(fireplace,) = [
    part for part in loaded.objects if part.get("product") == fireplace_tools["part_id"]
]
fireplace.location = (0, -0.090, 1.424)
guyline()
bpy.ops.wm.save_as_mainfile(filepath=str(review / "snow-peak-pitch-kit.blend"))
aurora_tools["close_for_display"](aurora)
combine = runpy.run_path(str(scripts / "product_solids.py"))["combine"]
combine("ST-033R folded fireplace surfaces", list(fireplace.children))
target = root / "public/media/models/snow-peak-pitch-kit.glb"
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_extras=True,
    export_animations=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
)

