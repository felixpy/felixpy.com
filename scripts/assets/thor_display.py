from mathutils import Matrix, Vector
from pathlib import Path
import os
import bpy
import bmesh

from blender_parts import xyz


def rounded(points, radius, segments=4):
    result = []
    vertices = [Vector(p) for p in points]
    for i, b in enumerate(vertices):
        a, c = vertices[i - 1], vertices[(i + 1) % len(vertices)]
        retreat = min(radius, (a - b).length * 0.3, (c - b).length * 0.3)
        start = b + (a - b).normalized() * retreat
        end = b + (c - b).normalized() * retreat
        for step in range(segments + 1):
            t = step / segments
            result.append(tuple(start * (1 - t) ** 2 + b * (2 * t * (1 - t)) + end * t * t))
    return result


def inset(points, distance):
    result = []
    poly = [Vector(p) for p in points]
    area = sum(a.x * b.y - a.y * b.x for a, b in zip(poly, poly[1:] + poly[:1]))
    for i, b in enumerate(poly):
        u = (b - poly[i - 1]).normalized()
        v = (poly[(i + 1) % len(poly)] - b).normalized()
        nu, nv = Vector((-u.y, u.x)), Vector((-v.y, v.x))
        bisector = (nu + nv).normalized()
        amount = min(distance / max(0.15, bisector.dot(nu)), 3 * distance)
        result.append(tuple(b + bisector * (amount if area > 0 else -amount)))
    return result


def label(text, origin, height, width, side, paint, finish):
    curve = bpy.data.curves.new(text, "FONT")
    curve.body = text
    curve.size = 0.01
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.resolution_u = 5
    obj = bpy.data.objects.new(text + " • pad print", curve)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    coords = [v.co for v in obj.data.vertices]
    lo = Vector((min(c.x for c in coords), min(c.y for c in coords), 0))
    hi = Vector((max(c.x for c in coords), max(c.y for c in coords), 0))
    center = (hi + lo) * 0.5
    for point in coords:
        u, v = point.x - center.x, point.y - center.y
        point.xyz = xyz((origin[0], origin[1] + v * height / (hi.y - lo.y),
                         origin[2] - side * u * width / (hi.x - lo.x)))
    paint(obj, finish)
    obj.select_set(False)


def add_readout(paint):
    candidates = [
        Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts/arial.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    font = bpy.data.fonts.get("Thor telemetry · regular")
    if not font:
        file = next((candidate for candidate in candidates if candidate.is_file()), None)
        if not file:
            raise FileNotFoundError("Install Arial Regular or its metric-compatible Liberation Sans Regular")
        font = bpy.data.fonts.load(str(file))
        font.name = "Thor telemetry · regular"
        font.pack()
    frame = Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0))).to_euler()
    px, py = 0.033 / 320, 0.0088 / 80
    digit_advance, unit_advance, gap = 130.1396484375, 58.5185546875, 4
    start = (320 - digit_advance - gap - unit_advance) / 2
    parts = []
    for role, text, left, top, width, height in (
        ("watts", "206", start + 2, 12, 125.759765625, 57),
        ("unit", "W", start + digit_advance + gap, 23, 59, 45),
    ):
        curve = bpy.data.curves.new("Thor telemetry · " + role, "FONT")
        curve.body = text
        curve.font = font
        curve.resolution_u = 12
        obj = bpy.data.objects.new("Thor OLED · " + role, curve)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.update()
        x0, x1 = min(v[0] for v in obj.bound_box), max(v[0] for v in obj.bound_box)
        y0, y1 = min(v[1] for v in obj.bound_box), max(v[1] for v in obj.bound_box)
        sx, sy = width * px / (x1 - x0), height * py / (y1 - y0)
        obj.rotation_euler = frame
        obj.scale = (sx, sy, 1)
        obj.location = (-0.07494, 0.01786 - (left - 160) * px + sx * x0,
                        -0.00187 + (40 - top) * py - sy * y1)
        obj["thorTelemetry"] = role
        obj["nativePart"] = "thor-1600-pixels"
        paint(obj, "pixels")
        parts.append(obj)
    return parts


def add_display(paint, solid):
    silver = [(52, 222), (77, 222), (79, 228), (315, 228), (620, 484),
              (52, 484), (52, 459), (56, 459), (56, 284), (52, 282)]
    upper = [(323, 228), (546, 228), (548, 234), (563, 234), (566, 228),
             (612, 228), (684, 269), (684, 483), (628, 483)]
    saddle = [(93, 308), (180, 308), (189, 300), (316, 300), (325, 308),
              (400, 308), (599, 477), (585, 477), (497, 403), (409, 403),
              (399, 410), (274, 410), (264, 403), (190, 403), (93, 320)]
    face = rounded([(109, 316), (397, 316), (477, 395), (188, 395)], 10)
    light_outline = [(114, 318), (396, 318), (474, 393), (190, 393)]
    light = rounded(light_outline, 9)
    eye = [
        [(470,318),(478,326),(489,338),(501,349),(514,357),(501,353),(489,347),(478,337)],
        [(502,326),(518,333),(531,338),(537,337),(557,317),(582,295),(605,279),(626,270),
         (638,267),(653,275),(635,284),(611,297),(584,315),(561,332),(542,351),(537,360),
         (548,375),(536,369),(526,359),(515,345)],
        [(544,357),(564,341),(591,324),(622,309),(661,292),(662,307),(630,321),(602,336),
         (579,352),(562,362),(581,369),(606,372),(622,368),(636,357),(647,341),(653,328),
         (633,334),(607,343),(628,330),(662,317),(662,355),(647,371),(632,380),(615,384),
         (597,382),(577,377),(557,368)],
    ]
    for side in (-1, 1):
        active = side < 0
        assembly = "Window side" if active else "Cable-management side"

        def point(u, v, depth):
            return (side * depth, (350 - v) * 86 / 276,
                    5 - side * (u - 367.5) * 200 / 643)

        def plate(name, loops, depth, thickness, finish, radius=0):
            obj = solid(assembly + " • " + name, loops, lambda u, v, t: point(u, v, depth + t),
                        thickness, radius)
            uv = obj.data.uv_layers.new(name="Diagonal machining")
            for entry in obj.data.loops:
                co = obj.data.vertices[entry.vertex_index].co
                uv.data[entry.index].uv = ((co.y + co.z) * 48, (co.y - co.z) * 48)
            return paint(obj, finish)

        def guide(name, outer, inner, depth, thickness):
            n = len(outer)
            vertices = [xyz(point(u, v, d)) for d in (depth, depth + thickness)
                        for contour in (outer,inner) for u,v in contour]
            quads = []
            for i in range(n):
                j = (i + 1) % n
                for a, b in [(0, n), (n, 3*n), (3*n, 2*n), (2*n, 0)]:
                    quads.append((a+i,a+j,b+j,b+i))
            data = bpy.data.meshes.new(name)
            data.from_pydata(vertices, [], quads)
            bm = bmesh.new()
            bm.from_mesh(data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(data)
            bm.free()
            obj = bpy.data.objects.new(assembly + " • " + name, data)
            bpy.context.collection.objects.link(obj)
            paint(obj, "aura")

        plate("Brushed aluminium aperture plate", [silver, saddle], 73.75, 0.66, "steel", 0.1)
        plate("Diagonally split satin aluminium cheek", [upper], 73.75, 0.7, "enamel", 0.1)
        plate("Stepped keyed display seat", [saddle, face], 73.76, 0.6, "black", 0.08)
        if active:
            plate("Detachable magnetic OLED cassette", [face], 73.95, 0.82, "black", 0.11)
            plate("Smoked display window", [light], 74.77, 0.08, "glass")
            guide("Perimeter light pipe", light, rounded(inset(light_outline, 3.8), 6), 74.86, 0.04)
        else:
            plate("Interchangeable embossed blind insert", [face], 73.9, 0.59, "black", 0.12)
            label("REPUBLIC OF GAMERS", point(308, 346, 74.52), 2.1, 28, side, paint, "enamel")
            label("T H O R", point(301, 364, 74.52), 3.9, 28, side, paint, "enamel")
        for i, path in enumerate(eye):
            name = "ROG eye inlay " + str(i + 1)
            if active:
                guide(name, path, inset(path, 2.5), 74.46, 0.07)
            else:
                plate(name, [path], 74.46, 0.07, "steel")
                crest = [(199 + (u - 560) * 0.23, 354 + (v - 325) * 0.23) for u,v in path]
                plate("Blind cover relief " + str(i + 1), [crest], 74.5, 0.15, "enamel")
        corner = [(614,214),(685,214),(687,218),(687,258),(629,230),(615,220)]
        plate("Chamfered edge diffuser", [corner], 73.86, 0.65, "aura" if active else "glass", 0.1)
        label("1600W", point(120, 426, 74.45), 3.35, 19.5, side, paint, "black")
        label("ROG THOR", point(120, 440, 74.45), 1.65, 19.5, side, paint, "black")
    add_readout(paint)
