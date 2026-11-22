import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


root = Path(__file__).resolve().parents[2]
native = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else (
    root / ".references/05-摄影与陈列/相框与展示设施/Camera display cabinet/Blender/vitrine-inventory.blend"
)
bpy.ops.wm.open_mainfile(filepath=str(native.resolve()), use_scripts=False, load_ui=False)
verts, faces = [], []
footprints = []
contact_radius = 0.018
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    mesh = obj.data
    offset = len(verts)
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    verts.extend(points)
    near_floor = [p for p in points if abs(p.z - 0.520) < contact_radius]
    if near_floor:
        footprints.append(tuple(
            (min(p[i] for p in near_floor) - contact_radius, max(p[i] for p in near_floor) + contact_radius)
            for i in (0, 1)
        ))
    mesh.calc_loop_triangles()
    faces.extend([tuple(offset + i for i in t.vertices) for t in mesh.loop_triangles])
assert len(faces) > 2000
bvh = BVHTree.FromPolygons(verts, faces, all_triangles=True)


def xyz(v):
    return Vector((v[0], -v[2], v[1]))


def emitter(layout):
    pivot = Vector((layout["x"], layout["shelf"] - 0.0231, 0.31))
    target = Vector(layout["aim"])
    direction = target - pivot
    yaw = math.atan2(-direction.x, -direction.z) + math.asin(0.00678 / math.hypot(direction.x, direction.z))
    hinge = pivot + Vector((0.00678 * math.cos(yaw), 0, -0.00678 * math.sin(yaw)))
    axis = (target - hinge).normalized()
    center = xyz(hinge + axis * 0.01327)
    normal = xyz(axis)
    right = normal.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(normal).normalized()
    return [center + (right * math.cos(k * 2.4) + up * math.sin(k * 2.4)) *
            (0.0037 * math.sqrt((k + 0.5) / 7)) for k in range(7)]


emitters = [emitter(light) for light in json.loads((root / "src/scene/cabinet-light-layout.json").read_text())]
width, height = 960, 768
hemisphere = []
for i in range(40):
    r = math.sqrt((i + 0.5) / 40)
    angle = i * math.pi * (3 - math.sqrt(5))
    hemisphere.append(Vector((r * math.cos(angle), r * math.sin(angle), math.sqrt(1 - r * r))))
pixels = np.ones((height, width, 4), dtype=np.float32)
for row in range(height):
    v = (row + 0.5) / height
    if v < 0.25:
        y, z, lights = 0.5202, 0.0195 + v * 4 * 0.351, emitters[3:]
    elif v < 0.625:
        y, z, lights = 0.520 + (v - 0.25) / 0.375 * 0.445, 0.0307, emitters[3:]
    else:
        y, z, lights = 0.965 + (v - 0.625) / 0.375 * 0.320, 0.0307, emitters[:3]
    for col in range(width):
        x = ((col + 0.5) / width - 0.5) * 1.145
        receiver = xyz((x, y, z))
        if v < 0.25 and any(x0 <= x <= x1 and y0 <= -z <= y1 for (x0, x1), (y0, y1) in footprints):
            occlusion = 0
            for ray in hemisphere:
                distance = bvh.ray_cast(receiver, ray, contact_radius)[3]
                if distance is not None:
                    occlusion += (1 - distance / contact_radius) ** 2
            pixels[row, col, 2] = 1 - occlusion / len(hemisphere)
        for channel, samples in enumerate(lights):
            if abs(x - samples[0].x) > 0.47:
                continue
            occluded = 0
            for sample in samples:
                ray = sample - receiver
                if bvh.ray_cast(receiver, ray.normalized(), ray.length)[0] is not None:
                    occluded += 1
            pixels[row, col, channel] = 1 - occluded / len(samples)
image = bpy.data.images.new("Visibility from five installed C1-mini exit pupils", width, height, alpha=False)
image.colorspace_settings.name = "Non-Color"
image.pixels.foreach_set(pixels.ravel())
image.filepath_raw = str(root / "public/media/lighting/cabinet-spot-visibility.png")
image.file_format = "PNG"
image.save()
print("Visibility samples", len(faces), [int((pixels[:, :, i] < 0.5).sum()) for i in range(3)])
