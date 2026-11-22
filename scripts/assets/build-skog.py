import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
out = root / ".review/atelier/skog"
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(scripts))
from blender_parts import xyz


def material(name, rgb, roughness, image=None, ior=1.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    mat.diffuse_color = (*[c / 255 for c in rgb], 1)
    for i, c in enumerate(rgb):
        s = c / 255
        shader.inputs["Base Color"].default_value[i] = (
            s / 12.92 if s < 0.04045 else ((s + 0.055) / 1.055) ** 2.4
        )
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["IOR"].default_value = ior
    if image:
        source = bpy.data.images.load(str(out / image))
        source.pack()
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = source
        mat.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    return mat


def surface(name, rows, materials, bands, radial=False):
    n = len(rows[0])
    vertices = [xyz(point) for row in rows for point in row]
    faces = []
    for i in range(len(rows) - 1):
        for j in range(n):
            a = i * n + j
            b = i * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    uv = mesh.uv_layers.new(
        name="Cylindrical print" if radial else "Longitudinal fibres"
    )
    for mat in materials:
        mesh.materials.append(mat)
    for face in mesh.polygons:
        i, j = divmod(face.index, n)
        face.material_index = bands[i]
        face.use_smooth = True
        for loop, k, v in zip(
            face.loop_indices, [j, j + 1, j + 1, j], [i, i, i + 1, i + 1], strict=True
        ):
            height = rows[v][k % n][1]
            if not radial and bands[i] == 2:
                a = k * math.tau / n
                radius = 0.49 if v < len(rows) - 1 else 0
                uv.data[loop].uv = (
                    0.5 + radius * math.cos(a),
                    0.5 + radius * math.sin(a),
                )
                continue
            uv.data[loop].uv = (
                k / n,
                max(0, min(1, height / (576 / (2048 / (80 * math.pi)))))
                if radial
                else v / (len(rows) - 1),
            )
    welded = bmesh.new()
    welded.from_mesh(mesh)
    bmesh.ops.remove_doubles(welded, verts=list(welded.verts), dist=0.00000001)
    welded.to_mesh(mesh)
    welded.free()
    return obj


def turned(name, profile, materials, bands):
    rows = []
    for h, r in profile:
        ring = []
        for i in range(96):
            a = math.tau * (i / 96 - 0.5)
            ring.append((r * math.sin(a), h, r * math.cos(a)))
        rows.append(ring)
    return surface(name, rows, materials, bands, True)


def reed(number, start, direction, length, materials, level):
    axis = Vector(direction).normalized()
    normal = axis.cross(Vector((0, 0, 1))).normalized()
    tangent = axis.cross(normal).normalized()
    r = 1.53
    wet = (level - start[1]) / axis.y
    rows = []
    profile = [
        (0, 0),
        (0.07, r * 0.95),
        (0.20, r),
        (wet - 0.6, r),
        (wet + 0.12, r),
        (length - 0.10, r),
        (length - 0.035, r * 0.97),
        (length, r * 0.90),
        (length, 0),
    ]
    for d, radius in profile:
        ring = []
        for i in range(24):
            a = i * math.tau / 24
            point = (
                Vector(start)
                + axis * d
                + radius * (math.cos(a) * normal + math.sin(a) * tangent)
            )
            ring.append(tuple(point))
        rows.append(ring)
    obj = surface(
        f"Rattan reed {number} | cut end grain and immersed foot",
        rows,
        materials,
        [1, 1, 1, 1, 0, 0, 2, 2],
    )
    obj["lengthMm"] = length
    obj["submergedLengthMm"] = round(wet, 1)
    return obj


bpy.ops.wm.read_factory_settings(use_empty=True)
subprocess.run(["node", str(scripts / "skog-print.mjs"), str(out)], check=True)
paint = material(
    "SKOG • water dye and ivory screen print", (64, 82, 76), 0.40, "skog-vessel.png"
)
closure = material("SKOG • forest green satin glass coat", (64, 82, 76), 0.39)
inner = material("SKOG • unprinted green glass interior", (49, 70, 57), 0.20, ior=1.52)
foot = material("SKOG • polished heel and recessed base", (55, 74, 62), 0.20, ior=1.52)
oil = material(
    "SKOG • plant-based fragrance solution", (220, 203, 158), 0.09, ior=1.455
)
oil_shader = oil.node_tree.nodes.get("Principled BSDF")
oil_shader.inputs["Transmission Weight"].default_value = 0.91
dry = material(
    "Rattan • dry longitudinal fibres", (220, 188, 146), 0.64, "skog-fibre.png"
)
wet = material("Rattan • submerged fibres", (164, 133, 90), 0.39)
end = material(
    "Rattan • pale cut end grain", (197, 164, 119), 0.70, "skog-reed-end.png"
)
outside = [
    (1.9, 0),
    (1.96, 6),
    (1.82, 18),
    (1.43, 28.8),
    (0.97, 32.2),
    (0.26, 33.6),
    (0, 34.2),
    (0, 35.8),
    (0.22, 36.9),
    (0.68, 38.15),
    (1.4, 39.15),
    (2.4, 39.72),
    (3.65, 39.98),
    (6, 40),
    (68.7, 40),
    (70.3, 39.96),
    (71.1, 39.62),
    (71.55, 38.93),
    (71.90, 36.4),
    (72.6, 27.8),
    (73.33, 20.2),
    (74.2, 17.1),
    (75.75, 15.4),
    (78.2, 14.65),
    (81, 14.48),
    (91.6, 14.48),
    (92.05, 14.8),
    (92.33, 15.52),
    (92.9, 15.77),
    (93.52, 15.72),
    (94.0, 15.12),
    (94.36, 14.95),
    (94.7, 15.16),
    (95.1, 15.65),
    (95.85, 15.92),
    (96.8, 15.88),
    (97.56, 15.46),
    (97.94, 14.78),
    (98, 13.9),
    (97.91, 12.1),
    (97.57, 11.66),
]
inside = [
    (97.57, 11.66),
    (96.82, 11.43),
    (93.88, 11.37),
    (80.2, 11.45),
    (76.65, 11.95),
    (73.6, 13.5),
    (71.7, 16.5),
    (70.3, 21.4),
    (69.3, 31.4),
    (68.5, 35.8),
    (67.15, 36.9),
    (65.5, 37.3),
    (9.0, 37.30),
    (7, 36.75),
    (5.85, 35),
    (5.6, 31),
    (6.0, 21),
    (6.45, 9),
    (6.55, 0),
]
glass = turned(
    "SKOG 20303 | moulded glass, open neck and printed skin",
    outside + inside[1:],
    [paint, closure, inner, foot],
    [3 if i < 10 else 0 if 12 <= i < 15 else 1 for i in range(len(outside) - 1)]
    + [2] * (len(inside) - 1),
)
level = 49.0
oilprofile = [
    (6.64, 0),
    (6.55, 9),
    (6.10, 21),
    (5.70, 31),
    (5.97, 35),
    (7.09, 36.62),
    (9.1, 37.21),
    (level + 0.73, 37.21),
    (level + 0.50, 37.11),
    (level + 0.18, 36.83),
    (level + 0.055, 36.35),
    (level, 35.8),
    (level, 0),
]
liquid = turned(
    "Fragrance | wetted base and concave meniscus",
    oilprofile,
    [oil],
    [0] * (len(oilprofile) - 1),
)
parts = [glass, liquid]
for index, (p, axis, length) in enumerate(
    [
        ((-24, 7.1, -5), (0.265, 1, 0.038), 224),
        ((-20.2, 7.4, -7.8), (0.294, 1, 0.092), 223),
        ((-20.9, 7.6, 7.3), (0.337, 1, -0.048), 222),
    ],
    1,
):
    parts.append(reed(index, p, axis, length, [dry, wet, end], level))
assembly = bpy.data.objects.new("SKOG 20303 | 200 ml diffuser", None)
bpy.context.scene.collection.objects.link(assembly)
assembly["product"] = "Skandinavisk SKOG 20303"
assembly["diameterMm"] = 80
assembly["bottleHeightMm"] = 98
assembly["suppliedReeds"] = 8
assembly["displayedReeds"] = 3
assembly["reconstructed"] = "Inner glass, meniscus, fill and reed placement"
for obj in parts:
    obj.parent = assembly
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / "skog-20303.blend"), compress=True)
oil_shader.inputs["Transmission Weight"].default_value = 0
oil_shader.inputs["Alpha"].default_value = 0.16
dest = root / "public/media/models/skog-20303.glb"
bpy.ops.export_scene.gltf(
    filepath=str(dest),
    export_extras=True,
    export_animations=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(dest)], check=True
)
