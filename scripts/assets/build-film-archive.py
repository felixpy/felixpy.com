import math
import runpy
import subprocess
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
review = root / ".review/atelier/film-archive"
review.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
finish = runpy.run_path(str(scripts / "vitrine-sculpt.py"))["finish"]
corners = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))["corners"]
tau = math.tau
iron = finish("Crimped black lacquered tinplate", "2e2d2b", 0.52, 0.32)
acetal = finish("Injection moulded spool", "292929", 0.04, 0.40)
velvet = finish("Black flock light trap", "181716", 0, 0.94)
base = finish("Unexposed acetate and emulsion", "583525", 0.05, 0.35)
mask = finish("Pressed slide mask", "999b98", 0.73, 0.40)
white = finish("Gepe ivory projector face", "e0dfd7", 0, 0.53)
black = finish("Gepe dark projector face", "3d4142", 0, 0.52)


def textured(name, image, rough):
    mat = finish(name, "ffffff", 0.04, rough)
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(review / image))
    node.image.pack()
    shader = mat.node_tree.nodes["Principled BSDF"]
    mat.node_tree.links.new(node.outputs["Color"], shader.inputs["Base Color"])
    return mat


wood = textured("Oiled archive tray", "filing-tray.jpg", 0.56)


def group(name, xyz):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = tuple(t / 1000 for t in xyz)
    obj.empty_display_size = 0.006
    return obj


def mesh(name, vertices, faces, mat, parent, uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata([tuple(n / 1000 for n in p) for p in vertices], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    data.materials.append(mat)
    if uv is not None:
        layer = data.uv_layers.new(name="Print registration")
        for loop in data.loops:
            layer.data[loop.index].uv = uv[loop.vertex_index]
    return obj


def loft(name, rows, mat, parent, smooth=False, close_profile=False):
    width = len(rows[0])
    faces = [
        (
            i * width + j,
            i * width + (j + 1) % width,
            ((i + 1) % len(rows)) * width + (j + 1) % width,
            ((i + 1) % len(rows)) * width + j,
        )
        for i in range(len(rows) if close_profile else len(rows) - 1)
        for j in range(width)
    ]
    obj = mesh(name, [v for row in rows for v in row], faces, mat, parent)
    if smooth:
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def lathe(name, profile, mat, parent):
    obj = loft(
        name,
        [
            [
                (r * math.cos(i * tau / 80), r * math.sin(i * tau / 80), h)
                for i in range(80)
            ]
            for r, h in profile
        ],
        mat,
        parent,
        True,
        True,
    )
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for edge in bm.edges:
        edge.smooth = edge.calc_face_angle(0.0) < math.radians(34)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def block(name, center, dims, mat, parent, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(t / 1000 for t in dims)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = tuple(t / 1000 for t in center)
    obj.parent = parent
    obj.data.materials.append(mat)
    if mat == wood:
        mapping = obj.data.uv_layers.active
        along = max(range(3), key=lambda n: dims[n])
        for face in obj.data.polygons:
            axis = max(range(3), key=lambda n: abs(face.normal[n]))
            planes = [n for n in range(3) if n != axis]
            planes.sort(key=lambda n: n != along)
            for index in face.loop_indices:
                co = obj.data.vertices[obj.data.loops[index].vertex_index].co
                mapping.data[index].uv = (
                    co[planes[0]] * 8 + 0.39 + center[1] / 160,
                    co[planes[1]] * 21 + 0.52,
                )
    edge = obj.modifiers.new("Edge radius", "BEVEL")
    edge.width = bevel / 1000
    edge.segments = 3
    edge.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=edge.name)
    obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return obj


def form_shell(parent):
    ink = textured("Portra 400 printed tinplate", "cassette-print.png", 0.42)
    exposed = finish("Unpainted DX sensing contacts", "c7c7bd", 0.83, 0.29)
    arc = tau - 0.20
    start = math.pi + 0.68
    levels = sorted({1.4, 39.6, *(37.3 - i * 5.85 for i in range(7))})
    stations = sorted({i / 96 for i in range(97)} | {0.650, 0.748, 0.846})
    count = len(stations)

    def position(u, z, radius):
        a = start + arc * u
        return (radius * math.cos(a), radius * math.sin(a), z)

    verts = [
        position(u, z, r) for r in (12.15, 11.95) for z in levels for u in stations
    ]
    uvs = [(u, (z - 1.4) / 38.2) for _ in range(2) for z in levels for u in stations]
    rows = len(levels)
    side = rows * count
    faces, finishes = [], []
    contacts = [(1, 0, 0, 1, 1, 0), (1, 0, 0, 1, 1, 1)]
    for i in range(rows - 1):
        dx = math.floor((37.3 - (levels[i] + levels[i + 1]) / 2) / 5.85)
        for j, (a, b) in enumerate(zip(stations, stations[1:])):
            u = (a + b) / 2
            conductive = (
                0 <= dx < 6 and 0.650 < u < 0.846 and contacts[int(u >= 0.748)][dx]
            )
            k = i * count + j
            quad = (k, k + 1, k + 1 + count, k + count)
            faces.extend((quad, tuple(side + v for v in reversed(quad))))
            finishes.extend((2 if conductive else 0, 1))
    for zrow in (0, rows - 1):
        for j in range(count - 1):
            k = zrow * count + j
            faces.append((k, k + side, k + side + 1, k + 1))
            finishes.append(1)
    obj = mesh(
        "Drawn can with open throat and DX contacts", verts, faces, ink, parent, uvs
    )
    obj.data.materials.append(iron)
    obj.data.materials.append(exposed)
    for poly, index in zip(obj.data.polygons, finishes):
        poly.material_index = index
        poly.use_smooth = True
    for u, lip_x in [(0, -9.19), (1, -10.26)]:
        x, y, _ = position(u, 2, 12.10)
        contour = [
            (x, y),
            (lip_x, -10.6),
            (lip_x, -11.2),
            (lip_x - 0.23, -11.18),
            (x - 0.13, y + 0.08),
        ]
        loft(
            "Folded cassette lip",
            [[(x, y, z) for x, y in contour] for z in (1.4, 39.6)],
            iron,
            parent,
        )
        block(
            "Velvet ribbon",
            (lip_x + (-0.22 if u == 0 else 0.22), -9.75, 20.5),
            (0.51, 2.95, 37.7),
            velvet,
            parent,
            0.16,
        )
    for z, sign in [(0, 1), (41, -1)]:
        lathe(
            "Dished lower cap" if sign == 1 else "Dished upper cap",
            [
                (r, z + sign * h)
                for r, h in [
                    (5.04, 1.65),
                    (5.3, 1.25),
                    (9.9, 1.16),
                    (10.8, 0.58),
                    (11.5, 0.08),
                    (12.12, 0),
                    (12.48, 0.16),
                    (12.55, 0.37),
                    (12.57, 1.65),
                    (12.53, 2.10),
                    (12.36, 2.32),
                    (12.05, 2.34),
                    (12.16, 0.62),
                    (11.7, 0.4),
                    (10.1, 1.52),
                    (5.08, 2.03),
                ]
            ],
            iron,
            parent,
        )
    lathe(
        "Hollow rewind spindle and film anchor",
        [
            (4.55, 0.45),
            (4.74, 1.05),
            (4.82, 2.10),
            (4.82, 40.0),
            (5.02, 40.2),
            (5.02, 45.85),
            (4.82, 46.05),
            (3.96, 46.05),
            (3.68, 45.7),
            (3.2, 0.7),
            (3.48, 0.45),
        ],
        acetal,
        parent,
    )
    for z in (2.55, 38.45):
        lathe(
            "Spool film guide flange",
            [
                (4.6, z),
                (10.85, z),
                (11.18, z + 0.18),
                (10.95, z + 0.45),
                (4.6, z + 0.51),
            ],
            acetal,
            parent,
        )["insideCassette"] = True
    for z in (3.4, 40.2):
        block("Rewind drive rib", (0, 0, z), (7.52, 1.30, 2.25), acetal, parent, 0.21)


pitch = 4.75
turns = 32
inner_radius = 4.9
outer_radius = inner_radius + turns * 0.15
length = math.pi * turns * (inner_radius + outer_radius)


def film_path(s):
    if s < 0:
        radius = math.sqrt(outer_radius**2 + 0.15 * s / math.pi)
        angle = math.pi + (radius - outer_radius) * tau / 0.15
        return radius * math.cos(angle), radius * math.sin(angle)
    throat = min(s, 11.25)
    bend = max(0, s - throat) / 24
    return -outer_radius - 24 * (1 - math.cos(bend)), -throat - 24 * math.sin(bend)


def cut_stock(parent, name, start, end, concealed):
    vertices, faces = [], []

    def point(s, z):
        x, y = film_path(s)
        return (x, y, z)

    def segment(s):
        if s < 33:
            return 3.13, 38.10
        fraction = min(1.0, (s - 33) / 15)
        raised = 19.6 * fraction**2 * (3 - 2 * fraction)
        corner = 1.1 * max(0, (s - (end - 1.5)) / 1.5) ** 2
        return 3.13 + raised + corner, 38.10 - corner

    stations = {start, end}
    for i in range(math.floor(start / pitch) - 1, math.ceil(end / pitch) + 1):
        stations.update(
            i * pitch + t
            for t in (0, 0.24, 0.54, 1.0, 1.44, 1.74, 1.98, 3.05, 4.05)
            if start < i * pitch + t < end
        )
    stations = sorted(stations)
    for j, (s, t) in enumerate(zip(stations, stations[1:])):
        slot = ((s + t) / 2) % pitch < 1.98
        for k in (s, t):
            v = k % pitch
            rounding = max(0, 0.43 - min(v, abs(1.98 - v))) if v <= 1.981 else 0.43
            low, high = segment(k)
            for h in (
                low,
                max(low, 5.06 + rounding),
                max(low, 7.84 - rounding),
                max(low, 33.39 + rounding),
                max(low, 36.18 - rounding),
                high,
            ):
                vertices.append(point(k, h))
        for row in range(5):
            if slot and row in (1, 3):
                continue
            idx = j * 12 + row
            faces.append((idx, idx + 6, idx + 7, idx + 1))
    strip = mesh(name, vertices, faces, base, parent)
    bm = bmesh.new()
    bm.from_mesh(strip.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00000001)
    bm.to_mesh(strip.data)
    bm.free()
    for face in strip.data.polygons:
        face.use_smooth = True
    thickness = strip.modifiers.new("Acetate base gauge", "SOLIDIFY")
    thickness.thickness = 0.00013
    thickness.offset = 0
    thickness.use_rim = True
    thickness.use_quality_normals = True
    edge = bpy.data.materials.get("Cut acetate edge") or finish(
        "Cut acetate edge", "493727", 0.04, 0.52
    )
    strip.data.materials.append(edge)
    thickness.material_offset_rim = 1
    bpy.context.view_layer.objects.active = strip
    bpy.ops.object.modifier_apply(modifier=thickness.name)
    for polygon in strip.data.polygons:
        if polygon.material_index:
            polygon.use_smooth = False
    strip["insideCassette"] = concealed
    strip["perforationPitchMM"] = pitch


def slide_frame(parent, name, w, d, r, aw, ad, h, thick, mat):
    loops = []
    for width, depth, radius, level in [
        (w - 0.25, d - 0.25, r, h),
        (w, d, r, h + 0.14 * thick),
        (w, d, r, h + thick * 0.82),
        (w - 0.26, d - 0.26, r, h + thick),
        (aw + 0.5, ad + 0.5, 0.38, h + thick),
        (aw, ad, 0.28, h + 0.16 * thick),
        (aw, ad, 0.28, h),
    ]:
        loops.append([(x, y, level) for x, y in corners(width, depth, radius, 4)])
    return loft(name, loops, mat, parent, close_profile=True)


def pierced_plate(parent, name, contours, h, gauge, mat):
    points, rings = [], []
    for contour in contours:
        offset = len(points)
        points.extend(Vector(xy) for xy in contour)
        rings.append(list(range(offset, len(points))))
    verts, _, tris, _, _, ids = delaunay_2d_cdt(points, [], rings, 0, 0.00001)
    count = len(verts)
    faces = []
    for face, regions in zip(tris, ids):
        if set(regions) == {0}:
            faces.append(tuple(reversed(face)))
            faces.append(tuple(i + count for i in face))
    index = {(round(p.x, 4), round(p.y, 4)): i for i, p in enumerate(verts)}
    for number, ring in enumerate(rings):
        ids = [index[(round(points[i].x, 4), round(points[i].y, 4))] for i in ring]
        if number:
            ids.reverse()
        for a, b in zip(ids, ids[1:] + ids[:1]):
            faces.append((a, b, b + count, a + count))
    return mesh(
        name, [(p.x, p.y, z) for z in (h, h + gauge) for p in verts], faces, mat, parent
    )


def rect(x, y, w, d, r):
    return [(a + x, b + y) for a, b in corners(w, d, r, 5)]


def slide(parent, index, artwork):
    slide_frame(parent, "Dark slide half", 50, 50, 0.92, 36.4, 24.4, 0, 0.41, black)
    slide_frame(
        parent, "Lower retaining lip", 50, 50, 0.92, 44.7, 44.7, 0.40, 0.56, black
    )
    slide_frame(
        parent, "Upper retaining lip", 50, 50, 0.92, 44.7, 44.7, 0.96, 0.59, white
    )
    slide_frame(parent, "Ivory slide half", 50, 50, 0.92, 36.4, 24.4, 1.54, 0.41, white)
    holes = [rect(0, 0, 44.3, 44.3, 2.2), rect(0, 0, 35.6, 23.6, 0.25)]
    for side in (-1, 1):
        holes.append(rect(0, side * 17.1, 13.4, 1.62, 0.72))
        for x in (-17.4, 17.4):
            holes.append(rect(x, side * 17.95, 2.45, 2.45, 1.20))
    for level in (0.76, 1.0):
        pierced_plate(parent, "Pressed aluminium mask", holes, level, 0.12, mask)
    strip = [rect(0, 0, 38, 34.97, 0.18), rect(0, 0, 35.96, 23.96, 0.16)]
    for side in (-1, 1):
        strip.extend(
            rect((k - 3.5) * pitch, side * 14.16, 1.98, 2.79, 0.36) for k in range(8)
        )
    pierced_plate(parent, "Trimmed reversal film", strip, 0.88, 0.12, base)
    for x in (-19.62, 19.62):
        for y in (-10, 10):
            block(
                "Mask fixing tongue",
                (x, y, 0.91),
                (0.96, 1.62, 0.25),
                mask,
                parent,
                0.06,
            )
    for x in (-19.2, 19.2):
        for y in (-18.2, 18.2):
            block("Moulded snap", (x, y, 0.93), (1.75, 1.72, 0.74), black, parent, 0.28)
    u, v = (index % 2) / 2, 0.5 - (index // 2) * 0.5
    mesh(
        "Mounted colour transparency",
        [(-18, -12, 0.94), (18, -12, 0.94), (18, 12, 0.94), (-18, 12, 0.94)],
        [(0, 1, 2, 3)],
        artwork,
        parent,
        [(u, v), (u + 0.5, v), (u + 0.5, v + 0.5), (u, v + 0.5)],
    )


def archive():
    cassette = group("Kodak Professional Portra 400 135-36", (52, -10, 0))
    form_shell(cassette)
    cut_stock(cassette, "Unexposed stock on rewind spool", -length, 7.0, True)
    cut_stock(cassette, "Slit and perforated film leader", 7.0, 60.40, False)
    art = textured("Original travel transparencies", "mounted-positives.jpg", 0.30)
    for i in range(4):
        mount = group("Gepe 7011 loose slide", (-45, -15, i * 1.95))
        mount.rotation_euler.z = -0.075 * i
        slide(mount, i, art)
    tray = group("Oak slide filing tray", (153, -5, 0))
    block("Recessed tray bottom", (0, 0, 2), (63, 64, 4), wood, tray, 0.62)
    for side in (-1, 1):
        block("Tray side", (side * 30, 0, 17.4), (4, 64, 34.8), wood, tray, 0.62)
        block("Tray end", (0, side * 30, 10), (56, 4, 20), wood, tray, 0.62)
    for i in range(5):
        mount = group("Gepe 7011 filed slide", (0, -19 + i * 9.5, 29))
        mount.parent = tray
        mount.rotation_euler.x = math.pi / 2
        slide(mount, (i + 2) % 4, art)
        for side in (-1, 1):
            block(
                "Slide register",
                (side * 26.6, -17.1 + i * 9.5, 13),
                (3.2, 1.9, 18),
                wood,
                tray,
                0.25,
            )


def joined_mesh(name, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    obj = bpy.context.object
    transform = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = transform
    obj.name = name
    return obj


def web_geometry():
    slides = [
        obj for obj in bpy.context.scene.objects if obj.name.startswith("Gepe 7011")
    ]
    positions = [obj.matrix_world.copy() for obj in slides]
    for mount in slides:
        for obj in list(mount.children):
            if not obj.name.startswith("Mounted colour"):
                bpy.data.objects.remove(obj, do_unlink=True)
    for obj in list(bpy.context.scene.objects):
        if obj.get("insideCassette"):
            bpy.data.objects.remove(obj, do_unlink=True)
    joined_mesh(
        "Film archive and positive images",
        [o for o in bpy.context.scene.objects if o.type == "MESH"],
    )
    holder = group("Reusable slide support", (0, 0, 0))
    slide_frame(holder, "Slide dark exterior", 50, 50, 0.92, 36.4, 24.4, 0, 0.96, black)
    slide_frame(
        holder, "Slide ivory exterior", 50, 50, 0.92, 36.4, 24.4, 0.96, 0.99, white
    )
    slide_frame(
        holder, "Exposed mask edge", 36.6, 24.6, 0.45, 35.6, 23.6, 0.73, 0.41, mask
    )
    master = joined_mesh("Gepe optical gate", list(holder.children))
    for i, transform in enumerate(positions):
        obj = master.copy() if i else master
        if i:
            bpy.context.collection.objects.link(obj)
        obj.parent = holder
        obj.matrix_world = transform
    for obj in list(bpy.context.scene.objects):
        if obj.type == "EMPTY" and obj != holder:
            bpy.data.objects.remove(obj, do_unlink=True)


archive()
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
bpy.ops.object.select_all(action="DESELECT")
focus = Vector((0.060, -0.010, 0.020))
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.clip_start = 0.0005
            space.region_3d.view_location = focus
            space.region_3d.view_distance = 0.31
            space.region_3d.view_rotation = Vector((-0.03, 0.26, -0.13)).to_track_quat(
                "-Z", "Y"
            )
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(review / "film-archive.blend"), compress=True)
web_geometry()
target = root / "public/media/models/film-archive.glb"
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_gpu_instances=True,
    export_animations=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
)
