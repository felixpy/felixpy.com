import math
from functools import lru_cache

import bpy
from mathutils import Vector


def finish(name, color, metal=0, rough=0.5, coat=0, glow=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    rgb = [int(color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb
    ] + [1]
    bsdf.inputs["Base Color"].default_value = linear
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = max(0.055, rough * 0.42)
    if glow:
        bsdf.inputs["Emission Color"].default_value = linear
        bsdf.inputs["Emission Strength"].default_value = glow
    return mat


@lru_cache(maxsize=80)
def letters(text, italic):
    font = bpy.data.curves.new("Die lettering", "FONT")
    font.body = text
    font.resolution_u = 2
    font.align_x = "CENTER"
    font.align_y = "CENTER"
    if italic:
        font.shear = 0.21
    obj = bpy.data.objects.new("Temporary dies", font)
    bpy.context.collection.objects.link(obj)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    data = evaluated.to_mesh()
    data.calc_loop_triangles()
    points = [(v.co.x, v.co.y) for v in data.vertices]
    faces = [tuple(t.vertices) for t in data.loop_triangles]
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(font)
    return points, faces


class Sculpture:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.inks = []
        self.surface = []
        self.materials = []

    def add(self, verts, faces, material, smooth=True):
        start = len(self.vertices)
        self.vertices.extend((x / 1000, -d / 1000, h / 1000) for x, h, d in verts)
        if material not in self.materials:
            self.materials.append(material)
        slot = self.materials.index(material)
        for face in faces:
            self.faces.append(tuple(start + i for i in face))
            self.inks.append(slot)
            self.surface.append(smooth)

    def rings(self, rows, material, smooth=True, close=True):
        n = len(rows[0])
        faces = []
        for j in range(len(rows) - 1):
            for i in range(n):
                k = (i + 1) % n
                faces.append((j * n + i, j * n + k, (j + 1) * n + k, (j + 1) * n + i))
        if close:
            faces.append(tuple(reversed(range(n))))
            faces.append(tuple((len(rows) - 1) * n + i for i in range(n)))
        self.add([p for row in rows for p in row], faces, material, smooth)

    def turn(self, profile, material, segments=56, rib=0, teeth=0):
        rows = []
        for h, r in profile:
            row = []
            for i in range(segments):
                a = math.tau * i / segments
                rr = r + rib * (0.5 + 0.5 * math.cos(teeth * a)) ** 2
                row.append((rr * math.sin(a), h, rr * math.cos(a)))
            rows.append(row)
        self.rings(rows, material, close=False)

    def loft(self, sections, material, segments=20, power=1):
        rows = []
        for x, h, d, w, depth in sections:
            row = []
            for i in range(segments):
                a = math.tau * i / segments
                s, c = math.sin(a), math.cos(a)
                row.append(
                    (
                        x + w * math.copysign(abs(s) ** power, s),
                        h,
                        d + depth * math.copysign(abs(c) ** power, c),
                    )
                )
            rows.append(row)
        self.rings(rows, material)

    def form(self, center, radii, material, angle=0):
        x, h, d = center
        w, v, depth = radii
        rows = []
        for j in range(11):
            b = -math.pi / 2 + math.pi * j / 10
            step = max(0.015, math.cos(b))
            row = []
            for i in range(20):
                a = i * math.tau / 20
                xx = w * math.sin(a) * step
                hh = v * math.sin(b)
                row.append(
                    (
                        x + xx * math.cos(angle) - hh * math.sin(angle),
                        h + hh * math.cos(angle) + xx * math.sin(angle),
                        d + depth * math.cos(a) * step,
                    )
                )
            rows.append(row)
        self.rings(rows, material)

    def pipe(self, points, radii, material, sides=8, aspect=1):
        pts = [Vector(p) for p in points]
        radius = [radii] * len(pts) if isinstance(radii, (int, float)) else radii
        rows = []
        guide = Vector((0, 0, 1))
        for i, (pt, r) in enumerate(zip(pts, radius)):
            tangent = (pts[min(len(pts) - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
            if abs(tangent.dot(guide)) > 0.95:
                guide = Vector((0, 1, 0))
            unit = tangent.cross(guide).normalized()
            depth = unit.cross(tangent).normalized()
            guide = depth
            rows.append(
                [
                    pt
                    + r
                    * (
                        math.cos(a * math.tau / sides) * unit
                        + math.sin(a * math.tau / sides) * depth * aspect
                    )
                    for a in range(sides)
                ]
            )
        self.rings(rows, material)

    def plate(self, outline, material, thickness=1.1, dome=1.3, bevel=0.11):
        n = len(outline)
        cx = sum(v[0] for v in outline) / n
        ch = sum(v[1] for v in outline) / n
        cd = sum(v[2] for v in outline) / n
        back = [(x, h, d - thickness) for x, h, d in outline]
        rim = [(x, h, d) for x, h, d in outline]
        inner = [
            (x + (cx - x) * bevel, h + (ch - h) * bevel, d + dome * 0.67)
            for x, h, d in outline
        ]
        rows = back + rim + inner + [(cx, ch, cd + dome)]
        faces = []
        for i in range(n):
            k = (i + 1) % n
            faces.extend(
                [
                    (i, k, n + k, n + i),
                    (n + i, n + k, 2 * n + k, 2 * n + i),
                    (2 * n + i, 2 * n + k, 3 * n),
                ]
            )
        faces.append(tuple(reversed(range(n))))
        self.add(rows, faces, material, False)

    def label(self, text, size, projection, material, italic=False):
        points, faces = letters(text, italic)
        self.add(
            [projection(x * size, h * size) for x, h in points], faces, material, False
        )

    def finalize(self, uv_scale=0, uv_materials=None):
        data = bpy.data.meshes.new(self.name)
        data.from_pydata(self.vertices, [], self.faces)
        data.update()
        for mat in self.materials:
            data.materials.append(mat)
        for polygon, index, smooth in zip(data.polygons, self.inks, self.surface):
            polygon.material_index = index
            polygon.use_smooth = smooth
        import bmesh

        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
        if uv_scale:
            uv = data.uv_layers.new(name="Surface scale")
            textured = (
                None
                if uv_materials is None
                else {
                    i
                    for i, material in enumerate(self.materials)
                    if material in uv_materials
                }
            )
            for poly in data.polygons:
                if textured is not None and poly.material_index not in textured:
                    continue
                normal = poly.normal
                axis = max(range(3), key=lambda i: abs(normal[i]))
                a, b = [(1, 2), (0, 2), (0, 1)][axis]
                for i in poly.loop_indices:
                    pos = data.vertices[data.loops[i].vertex_index].co
                    uv.data[i].uv = (pos[a] * uv_scale, pos[b] * uv_scale)
        obj = bpy.data.objects.new(self.name, data)
        bpy.context.collection.objects.link(obj)
        return obj
