import gzip
import json
import math
import runpy
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(__file__).resolve().parents[2]
scene = bpy.context.scene
gear = runpy.run_path(str(Path(__file__).with_name("movable-camp-gear.py")))
gear["exclude_from_static_lighting"](scene)


def view_point(x, y, z):
    return Vector((x, -z, y))


deps = bpy.context.evaluated_depsgraph_get()
verts = []
faces = []
sources = 0
for entry in deps.object_instances:
    obj = entry.object
    if not gear["static_mesh"](entry):
        continue
    matrix = entry.matrix_world
    corners = [matrix @ Vector(point) for point in obj.bound_box]
    if any(
        max(v[i] for v in corners) < lo or min(v[i] for v in corners) > hi
        for i, lo, hi in [(0, -1.5, 2.75), (1, -3.5, 0.82), (2, -0.2, 2.95)]
    ):
        continue
    data = obj.data
    if not data.polygons:
        continue
    data.calc_loop_triangles()
    first = len(verts)
    verts.extend([matrix @ vertex.co for vertex in data.vertices])
    faces.extend(
        [tuple(first + i for i in face.vertices) for face in data.loop_triangles]
    )
    sources += 1
if sources < 60 or len(faces) < 20000:
    raise RuntimeError(
        f"Incomplete occluder geometry: {sources} parts, {len(faces)} faces"
    )
bvh = BVHTree.FromPolygons(verts, faces, all_triangles=True)
triangles = len(faces)
del verts, faces
w, h, d = 64, 48, 64
cell = 0.0625
origin = (-1.375, -0.125, -0.6875)
samples = []
for i in range(48):
    y = 1 - (i + 0.5) * 2 / 48
    radius = math.sqrt(1 - y * y)
    a = i * 2.399963229728653
    direction = (radius * math.cos(a), y, radius * math.sin(a))
    samples.append((view_point(*direction), direction))
data = bytearray(w * h * d * 4)
for z in range(d):
    for y in range(h):
        for x in range(w):
            point = view_point(
                origin[0] + (x + 0.5) * cell,
                origin[1] + (y + 0.5) * cell,
                origin[2] + (z + 0.5) * cell,
            )
            total = mx = my = mz = 0.0
            for ray, (rx, ry, rz) in samples:
                _, _, _, distance = bvh.ray_cast(point, ray, 1.06)
                open_fraction = (
                    1 if distance is None else 1 - (1 - distance / 1.06) ** 1.65
                )
                total += open_fraction
                mx += rx * open_fraction
                my += ry * open_fraction
                mz += rz * open_fraction
            k = 4 * (x + w * (y + h * z))
            for axis, moment in enumerate((mx, my, mz)):
                data[k + axis] = max(
                    0, min(255, 128 + 4 * round(moment * 455 / (4 * len(samples))))
                )
            data[k + 3] = round(round(total * 63 / len(samples)) * 255 / 63)
    if z % 8 == 0:
        print(f"Completed slice {z + 1}/{d}", flush=True)
packed = gzip.compress(data, compresslevel=9, mtime=0)
destination = root / "public/media/lighting/room-visibility.gz"
destination.write_bytes(packed)
print(
    json.dumps(
        {
            "objects": len(scene.objects),
            "shadow_parts": sources,
            "triangles": triangles,
            "rays": w * h * d * len(samples),
            "bytes": len(packed),
        }
    )
)
