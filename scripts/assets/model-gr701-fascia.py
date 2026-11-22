import json
import math
import runpy
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from blender_parts import bevel, export_batch, xyz

PRODUCT = ROOT / ".references/03-电脑硬件/机箱与整机/ROG Hyperion GR701"
COLLECTION = "GR701 · front intake and load frame"
FINISHES = {
    "cast": ("Satin die-cast aluminium", (0.118, 0.126, 0.139), 0.76, 0.34),
    "wing": ("Brushed graphite aluminium", (0.227, 0.247, 0.265), 0.72, 0.45),
    "carrier": ("Dark graphite vent carrier", (0.025, 0.028, 0.034), 0.13, 0.53),
    "filter": ("Carbon black woven screen", (0.017, 0.019, 0.022), 0.13, 0.65),
    "vane": ("Satin graphite intake blade", (0.039, 0.044, 0.049), 0.28, 0.56),
    "plate": ("Stamped silver-grey grille", (0.617, 0.631, 0.658), 0.65, 0.46),
    "light": ("Diffusing polycarbonate", (0.3, 0.56, 0.67), 0.04, 0.28),
    "ink": ("Reflective gunmetal ROG transfer", (0.034, 0.037, 0.043), 0.74, 0.23),
    "frame": ("Folded anthracite chassis steel", (0.049, 0.055, 0.063), 0.48, 0.55),
}


def shell(name, vertices, faces, edge=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(p) for p in vertices], [], faces)
    edit = bmesh.new()
    edit.from_mesh(data)
    bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
    edit.to_mesh(data)
    edit.free()
    data.update()
    uv = data.uv_layers.new(name="Finish grain")
    for p in data.polygons:
        for loop in p.loop_indices:
            co = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (co.x * 4 + abs(co.y) * 3, co.z * 2.5)
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    return bevel(o, edge, 2) if edge else o


def sheet(name, outline, holes, at, thickness, edge=0):
    vertices = []
    polys = []
    for contour in [outline, *holes]:
        if (
            sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(contour, contour[1:] + contour[:1])
            )
            < 0
        ):
            contour = list(reversed(contour))
        polys.append(list(range(len(vertices), len(vertices) + len(contour))))
        vertices.extend(Vector(p) for p in contour)
    points, _, tris, original, _, includes = delaunay_2d_cdt(
        vertices, [], polys, 1, 0.000005
    )
    n = len(points)
    faces = []
    for tri, owners in zip(tris, includes):
        if list(owners) == [0]:
            faces.extend([tuple(reversed(tri)), tuple(i + n for i in tri)])
    remap = {j: i for i, ids in enumerate(original) for j in ids}
    for poly in polys:
        ring = [remap[i] for i in poly]
        for a, b in zip(ring, ring[1:] + ring[:1]):
            faces.append((a, b, b + n, a + n))
    return shell(
        name, [at(p.x, p.y, d) for d in (-thickness, 0) for p in points], faces, edge
    )


def pill(x, y, length, width, angle, n=5):
    points = []
    for side in (1, -1):
        for i in range(n + 1):
            t = math.pi * (i / n - (0.5 if side == 1 else -0.5))
            a = side * (length - width) / 2 + width / 2 * math.cos(t)
            b = width / 2 * math.sin(t)
            points.append(
                (
                    x + a * math.cos(angle) - b * math.sin(angle),
                    y + a * math.sin(angle) + b * math.cos(angle),
                )
            )
    return points


def stamped_grain(face, sign):
    uv = face.data.uv_layers.active
    for loop in face.data.loops:
        p = face.data.vertices[loop.vertex_index].co
        u, v = p.x, sign * p.z
        uv.data[loop.index].uv = (
            (0.41 * u - 0.91 * v) * 11,
            (0.91 * u + 0.41 * v) * 26,
        )


def wing_wordmark(wing):
    strokes = [
        [(26, 39), (280, 37), (178, 144), (132, 144), (218, 54), (42, 55)],
        [(285, 53), (302, 38), (407, 37), (356, 93), (307, 93), (318, 142), (265, 142), (254, 96), (272, 79), (323, 79), (346, 54)],
        [(350, 121), (430, 38), (476, 37), (395, 122), (400, 138), (350, 139)],
        [(479, 52), (493, 38), (603, 35), (501, 140), (455, 140), (539, 53)],
        [(525, 137), (626, 36), (672, 35), (584, 123), (648, 124), (633, 138)],
        [(671, 52), (688, 36), (801, 33), (778, 46), (761, 50)],
        [(652, 137), (705, 82), (751, 81), (711, 122), (870, 120), (883, 136)],
    ]
    pieces = []
    for i, contour in enumerate(strokes):
        pieces.append(sheet(
            "Port wing · reflective ROG transfer %02d" % (i + 1), contour, [],
            lambda x, y, d: wing(6.8 + (y - 33) * 0.132, -87 + (x - 26) * 0.201, 0.17 + d),
            0.045,
        ))
    return pieces


def dust_screen():
    pitch, radius = 0.90, 0.132
    horizontal, vertical = 465, 161
    xmax = (vertical - 1) * pitch / 2
    half_height = (horizontal - 1) * pitch / 2
    center_y = -13
    vertices, faces = [], []

    def strand(section_a, section_b):
        offset = len(vertices)
        vertices.extend(section_a + section_b)
        for i in range(4):
            next_i = (i + 1) % 4
            faces.append(tuple(offset + n for n in (i, next_i, next_i+4, i+4)))

    for n in range(vertical):
        x = n * pitch - xmax
        cross = [(x-radius, 239.0), (x, 239.12), (x+radius, 239.0), (x, 238.88)]
        strand([(a, center_y-half_height, b) for a, b in cross],
               [(a, center_y+half_height, b) for a, b in cross])
    for n in range(horizontal):
        y = center_y - half_height + n * pitch
        cross = [(y-radius, 239.16), (y, 239.28), (y+radius, 239.16), (y, 239.04)]
        strand([(-xmax, a, b) for a, b in cross], [(xmax, a, b) for a, b in cross])
    screen = shell("Fine woven sliding fan filter", vertices, faces)
    screen["open_cells"] = (horizontal - 1) * (vertical - 1)
    screen["weave_pitch_mm"] = pitch
    rim = sheet(
        "Fan-side dust cassette · perimeter frame",
        [(-75, -226), (75, -226), (75, 200), (-75, 200)],
        [[(-71.6, -221.4), (71.6, -221.4), (71.6, 195.4), (-71.6, 195.4)]],
        lambda x, y, d: (x, y, 240.2 + d), 2.2, 0.55,
    )
    return screen, rim


def inner_frame():
    def chamfer(x0, y0, x1, y1, r):
        return [(x0+r,y0),(x1-r,y0),(x1,y0+r),(x1,y1-r),
                (x1-r,y1),(x0+r,y1),(x0,y1-r),(x0,y0+r)]

    def horizontal(x, z, d):
        return x, 270.2 + d, z

    def frontal(x, y, d):
        return x, y, 237.0 + d

    parts = []
    roof_holes = [chamfer(-74, -261, 74, 180, 7)]
    for x in (-87, 87):
        for z in (-248, -112, 24, 160):
            roof_holes.append(pill(x, z, 19, 3.8, math.pi / 2))
    parts.append(sheet("Top radiator carrier · removable slotted deck",
                       chamfer(-118, -300, 112, 214, 5), roof_holes, horizontal, 1.6, 0.24))
    front_holes = []
    for center in (-153, -13, 127):
        front_holes.append([(68.2 * math.cos(a * math.tau / 64),
                             center + 68.2 * math.sin(a * math.tau / 64)) for a in range(64)])
        for x in (-62.25, 62.25):
            for y in (-62.25, 62.25):
                front_holes.append(pill(x, center+y, 7.2, 4.1, math.pi / 2))
    parts.append(sheet("Front fan carrier · three 140 mm intake throats",
                       chamfer(-114, -265, 109, 253, 5), front_holes, frontal, 1.5, 0.22))
    top_end = [(198,269),(210,269),(235.5,244),(235.5,236),
               (237,236),(237,244.6),(210.6,270.5),(198,270.5)]
    parts.append(sheet("Upper front header · inclined return beneath the control console",
                       top_end, [], lambda z,y,d:(112+d,y,z), 228, 0.45))
    rear_seam = [(-297,248),(-280,251),(179,251),(196,233),(213,211),
                 (232,211),(232,247),(214,270),(-297,270)]
    for side, name in ((-1,"Glass side"), (1,"Cable side")):
        x = -117 if side < 0 else 90
        if side < 0:
            flange = [(-297,255),(184,255),(197,244),(214,216),(236,201),
                      (236,249),(216,270),(-297,270)]
        else:
            flange = rear_seam
        parts.append(sheet(name + " roof rail · vertical return and corner gusset",
                           flange, [], lambda z,y,d,s=side,x=x:(x+s*d,y,z), 1.6, 0.25))
        front_side = [(190,-254),(198,-263),(237,-263),(237,244),
                      (214,267),(197,267),(187,257),(187,199),(197,188),(197,-196),(190,-207)]
        parts.append(sheet(name + " front upright · folded intake plenum wall",
                           front_side, [], lambda z,y,d,s=side:(s*(111+d),y,z), 1.6, 0.24))
        parts.append(sheet(name + " filter rail · inward facing capture lip",
                           chamfer(73,-225,111,200,2), [],
                           lambda u,y,d,s=side:(s*u,y,239.45+d), 1.2, 0.18))
    parts.append(sheet("Back panel roof seam · folded overlap",
                       chamfer(-294,254,195,270,1.5), [],
                       lambda z,y,d:(113.5+d,y,z), 1.8, 0.2))
    for part in parts:
        relieve_casting_corners(part)
    for side, title in ((-1, "Glass side"), (1, "Cable side")):
        parts.append(glass_jamb_return(side, title))
    return parts


def relieve_casting_corners(part):
    edit = bmesh.new()
    edit.from_mesh(part.data)
    for axis, cuts in ((0, (-0.109, -0.093, -0.074, 0.074, 0.093, 0.109)),
                       (1, (-0.21, -0.19, -0.178)),
                       (2, (-0.247, -0.218, -0.194, 0.194, 0.218, 0.247))):
        normal = Vector((0, 0, 0))
        normal[axis] = 1
        for cut in cuts:
            bmesh.ops.bisect_plane(edit, geom=[*edit.verts, *edit.edges, *edit.faces],
                                   plane_co=normal * cut, plane_no=normal, dist=1e-8)
    for v in edit.verts:
        x, front, height = abs(v.co.x), -v.co.y, abs(v.co.z)
        outside = min(1.0, max(0.0, (x - 0.074) / 0.035))
        at_corner = min(1.0, max(0.0, (height - 0.194) / 0.043))
        v.co.y += max(0.0, front - 0.178) * outside * at_corner * 0.94
    edit.normal_update()
    edit.to_mesh(part.data)
    edit.free()
    part.data.update()


def glass_jamb_return(side, title):
    profile = [(109.9, 204.0), (115.9, 204.0), (117.8, 202.1), (117.8, 184.4),
               (118.3, 183.9), (120.1, 183.9), (120.1, 182.8), (117.9, 182.8),
               (116.7, 184.0), (116.7, 201.7), (115.5, 202.9), (109.9, 202.9)]
    heights = (-214, -198, 196, 211)
    vertices = []
    for y in heights:
        taper = max(0.0, abs(y) - 196) / 19
        vertices.extend((side * (x - 2.1 - 3.8 * taper), y, z - (z - 189) * 0.45 * taper)
                        for x, z in profile)
    n = len(profile)
    faces = [tuple(range(n)), tuple(range(3 * n, 4 * n))]
    for j in range(len(heights)-1):
        for i in range(n):
            k = (i + 1) % n
            faces.append((j*n+i, j*n+k, (j+1)*n+k, (j+1)*n+i))
    return shell(title + " front seal · double-return jamb", vertices, faces, 0.16)


def build():
    batches = {k: [] for k in FINISHES}
    casting = runpy.run_path(str(HERE / "build-hyperion-rail.py"))["make_casting"]()
    casting.name = "Starboard carrying handle and load-bearing X leg"
    twin = casting.copy()
    twin.name = "Port carrying handle and load-bearing X leg"
    twin.data = casting.data.copy()
    twin.data.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    twin.data.flip_normals()
    bpy.context.collection.objects.link(twin)
    batches["cast"].extend((casting, twin))

    def bridge(x, y, d):
        return (x, y, 326.15 - 0.00095 * max(0, abs(y) - 46) ** 2 + d)

    spine = [
        (-7.3, -79),
        (-2.2, -52),
        (-2.2, 52),
        (-7.3, 79),
        (0, 69),
        (7.3, 79),
        (2.2, 52),
        (2.2, -52),
        (7.3, -79),
        (0, -69),
    ]
    batches["cast"].append(
        sheet("X yoke · central closing web", spine, [], bridge, 5, 0.25)
    )
    sections = [(-149, 40, 277), (-92, 22, 298), (-59, 10, 304), (-47, 8, 307),
                (47, 8, 307), (59, 10, 304), (92, 22, 298), (149, 40, 277)]
    corners = []
    for y, width, nose in sections:
        corners.extend([(-width, y, 244), (-width, y, nose - 6), (-width + 4, y, nose),
                        (width - 4, y, nose), (width, y, nose - 6), (width, y, 244)])
    perimeter = [tuple(reversed(range(6)))]
    for j in range(len(sections) - 1):
        for i in range(6):
            k = (i + 1) % 6
            perimeter.append((6*j+i, 6*j+k, 6*j+6+k, 6*j+6+i))
    perimeter.append(tuple(range(len(corners) - 6, len(corners))))
    batches["carrier"].append(shell("Deep central intake splitter beneath the cast X", corners, perimeter, 0.55))
    rings = [
        (96.0, 289.7, 193.5),
        (96.0, 271.0, 234.0),
        (63.3, 258.3, 247.2),
        (61.0, 255.2, 242.0),
        (90.0, 264.0, 222.0),
        (90.0, 282.0, 191.5),
    ]
    for sign, name in ((1, "Upper I/O bearing saddle"), (-1, "Lower grille plinth")):
        vertices = [(s * width, sign * y, z) for width, y, z in rings for s in (-1, 1)]
        count = len(rings)
        faces = [
            (i * 2, i * 2 + 1, ((i + 1) % count) * 2 + 1, ((i + 1) % count) * 2)
            for i in range(count)
        ]
        faces.extend([tuple(i * 2 + j for i in range(count)) for j in (0, 1)])
        batches["carrier"].append(shell(name, vertices, faces, 0.65))
    outline = [
        (-55.5, 119),
        (-52, 123),
        (52, 123),
        (55.5, 119),
        (55, 115),
        (3.3, 3.6),
        (0, 1),
        (-3.3, 3.6),
    ]
    bezel = [
        (-63, 125),
        (-59, 129),
        (59, 129),
        (63, 125),
        (61, 117),
        (5, -1),
        (0, -6),
        (-5, -1),
    ]
    rebate = [
        (-56.9, 119.5),
        (-53, 124.1),
        (53, 124.1),
        (56.9, 119.5),
        (56, 114.4),
        (3.6, 3.0),
        (0, 0.2),
        (-3.6, 3.0),
    ]
    crest_panel = json.loads((HERE / "gr701-upper-grille.json").read_text())
    for sign, label in ((1, "Upper"), (-1, "Lower")):

        def triangle(x, v, d):
            return (x, sign * (132 + v), 297.4 - 0.398 * v + d)

        slots = list(crest_panel["apertures"]) if sign == 1 else []
        if sign == -1:
            for row in range(10):
                v = 17 + row * 10.9
                half = 0.45 * v - 3
                for col in range(-7, 8):
                    x = (col + (0.5 if row % 2 else 0)) * 7.2
                    if abs(x) <= half - 3:
                        slots.append(pill(x, v, 10.8, 2.45, math.radians(112)))
        eye = crest_panel["crest"] if sign == 1 else []
        face = sheet(
            label + " removable diagonal-slot metal grille",
            outline,
            slots + (crest_panel["crestSeats"] if eye else []),
            triangle,
            1.35,
            0.17,
        )
        face["open_slots"] = len(slots)
        stamped_grain(face, sign)
        batches["plate"].append(face)
        batches["carrier"].append(
            sheet(
                label + " hollow grille carrier and seating flange",
                bezel,
                [rebate],
                lambda x, y, d: triangle(x, y, d - 2.0),
                6.2,
                0.6,
            )
        )
        shoulder = [(-91, 250), (-88, 265), (88, 265), (91, 250), (13, 91), (0, 75), (-13, 91)]
        batches["carrier"].append(sheet(
            label + " stamped intake plenum behind the open grille", shoulder, [],
            lambda x, y, d: (x, sign * y, 304.5 - (y - 92) * 0.395 + d), 1.6, 0.42,
        ))
        guides = []
        if sign == 1:
            guides.append([(-47.1, 132.9), (47.1, 132.9), (45.9, 129.7), (-46.0, 129.7)])
            for side in [-1,1]:
                guides.append([(side * x, y) for x, y in [
                    (59.6, 105.6), (57.9, 105.0), (15.0, 14.9), (15.1, 11.7),
                ]])
            brow = [(-57.1, 134.5), (56.9, 134.5), (53.0, 128.3), (-53.0, 128.3)]
            batches["carrier"].append(sheet(
                "Upper brow · angled lightguide pocket", brow, [guides[0]],
                lambda x, v, d: triangle(x, v, d + 1.65), 1.8, 0.18,
            ))
        else:
            for a,b in [
                ((-48, 126.4), (47, 126.4)),
                ((-58.7, 113), (-6.8, 4.9)),
                ((58.7, 113), (6.8, 4.9)),
            ]:
                guides.append(pill(
                    (a[0] + b[0]) / 2, (a[1] + b[1]) / 2,
                    math.dist(a, b), 1.65, math.atan2(b[1] - a[1], b[0] - a[0]),
                ))
        for idx, contour in enumerate(guides):
            height = 0.85 if sign == 1 and idx == 0 else -0.65
            batches["light"].append(
                sheet(
                    label + " recessed lightguide " + str(idx + 1),
                    contour,
                    [],
                    lambda x, y, d: triangle(x, y, d + height),
                    0.95,
                    0.12,
                )
            )
        for i, stroke in enumerate(eye):
            batches["light"].append(sheet(
                "ROG luminous crest insert " + str(i + 1), stroke, [],
                lambda x, y, d: triangle(x, y, d + 0.55), 1.95, 0.21,
            ))
    sides = runpy.run_path(str(HERE / "gr701-intake-wings.py"))
    sides["fit_sides"](batches, shell, wing_wordmark)
    screen, rim = dust_screen()
    batches["filter"].append(screen)
    batches["carrier"].append(rim)
    batches["frame"] = inner_frame()
    return batches


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    assembly = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(assembly)
    for key, parts in build().items():
        name, color, metal, rough = FINISHES[key]
        material = bpy.data.materials.new(name)
        material.diffuse_color = (*color, 1)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        for socket, value in [
            ("Base Color", (*color, 1)),
            ("Roughness", rough),
            ("Metallic", metal),
        ]:
            bsdf.inputs[socket].default_value = value
        if key in ("wing", "plate"):
            detail = material.node_tree.nodes.new("ShaderNodeTexImage")
            detail.image = bpy.data.images.load(str(ROOT / "public/media/materials/metal-brush-normal.webp"),check_existing=True)
            detail.image.colorspace_settings.name = "Non-Color"
            detail.image.pack()
            normal = material.node_tree.nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = 0.49 if key == "wing" else 0.43
            material.node_tree.links.new(detail.outputs["Color"], normal.inputs["Color"])
            material.node_tree.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
        if key == "plate":
            grain = material.node_tree.nodes.new("ShaderNodeTexImage")
            grain.image = bpy.data.images.load(str(ROOT / "public/media/materials/tolomeo-axial-grain.png"), check_existing=True)
            grain.image.pack()
            tint = material.node_tree.nodes.new("ShaderNodeMixRGB")
            tint.blend_type = "MULTIPLY"
            tint.inputs[0].default_value = 1
            tint.inputs[1].default_value = (*color, 1)
            material.node_tree.links.new(grain.outputs["Color"], tint.inputs[2])
            material.node_tree.links.new(tint.outputs[0], bsdf.inputs["Base Color"])
        if key == "light":
            bsdf.inputs["Emission Color"].default_value = (0.12, 0.57, 1, 1)
            bsdf.inputs["Emission Strength"].default_value = 0.85
        for o in parts:
            o.data.materials.clear()
            o.data.materials.append(material)
            o["fasciaFinish"] = key
            o["studioOccluder"] = key not in ("ink", "light")
            assembly.objects.link(o)
            scene.collection.objects.unlink(o)
        bpy.context.view_layer.update()
        filename = "gr701-fascia-" + key
        export_batch(
            filename, parts, ROOT / "public/media/models" / (filename + ".mesh")
        )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(PRODUCT / "Blender/gr701-fascia.blend"), compress=True
    )


if __name__ == "__main__":
    main()
