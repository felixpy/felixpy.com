import json
import math
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt


scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
atelier = root / ".review/atelier/pc-components"
atelier.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
board = bpy.data.collections.new("ROG Strix Z890-A Gaming WiFi S")
bpy.context.scene.collection.children.link(board)
mounts = bpy.data.collections.new("Mechanical datums")
board.children.link(mounts)


def coating(name, color, metal, rough):
    mat = finish(name, color, metal, rough)
    mat.diffuse_color = (
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
    )
    return mat


mask = coating("Pearl soldermask", "b8babc", 0.0, 0.49)
rear = coating("Slate soldermask", "878987", 0.16, 0.61)
edge = coating("Milled FR4 edge", "928b70", 0.03, 0.73)
white = coating("Pearl powder coat", "d7d8d2", 0.43, 0.34)
alloy = coating("Brushed aluminium", "bcc1c5", 0.79, 0.32)
steel = coating("Tin plated contacts", "b2b5b9", 0.88, 0.29)
gold = coating("Hard gold flash", "c5a04c", 0.81, 0.31)
dark = coating("Glass filled LCP", "292c2d", 0.07, 0.52)
silicon = coating("Package epoxy", "444743", 0.13, 0.61)
core = coating("Ferrite cores", "737674", 0.41, 0.57)
ink = coating("Black pad print", "454747", 0.12, 0.50)
legend = coating("White pad print", "e6e7db", 0.13, 0.50)
lcd = coating("I/O smoked inlay", "1a292e", 0.33, 0.31)
aqua = finish("ROG illuminated ink", "52d5e5", 0.28, 0.36, 0, 0.44)
blue = coating("USB 5G polymer", "294968", 0.05, 0.52)
red = coating("USB 10G polymer", "8b2e35", 0.05, 0.53)
plateholes = [
    (8, 7),
    (163, 7),
    (237, 7),
    (8, 163),
    (163, 163),
    (237, 163),
    (8, 288),
    (163, 288),
    (237, 288),
]
socket_u, socket_v = 134, 83
cooler_holes = [(socket_u + x, socket_v + y) for x in (-39, 39) for y in (-39, 39)]
slots = json.loads((root / "src/scene/dimm-slots.json").read_text())


def point(u, v, h):
    return (u, -v, h)


def circle(u, v, r, n=24):
    return [
        (u + r * math.cos(i * math.tau / n), v + r * math.sin(i * math.tau / n))
        for i in range(n)
    ]


def rectangle(x, y, w, h, r=0):
    if not r:
        return [
            (x - w / 2, y - h / 2),
            (x + w / 2, y - h / 2),
            (x + w / 2, y + h / 2),
            (x - w / 2, y + h / 2),
        ]
    out = []
    for cx, cy, start in [
        (x + w / 2 - r, y + h / 2 - r, 0),
        (x - w / 2 + r, y + h / 2 - r, 90),
        (x - w / 2 + r, y - h / 2 + r, 180),
        (x + w / 2 - r, y - h / 2 + r, 270),
    ]:
        for k in range(5):
            a = math.radians(start + 22.5 * k)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def datum(name, u, v, h):
    marker = bpy.data.objects.new(name, None)
    marker.empty_display_type = "PLAIN_AXES"
    marker.empty_display_size = 0.005
    marker.location = (u * 0.001, -h * 0.001, -v * 0.001)
    mounts.objects.link(marker)


class Part(Sculpture):
    def solid(self, outline, h, t, mat):
        self.rings(
            [[point(u, v, z) for u, v in outline] for z in (h, h + t)], mat, False
        )

    def box(self, u, v, h, w, l, t, mat, r=0):
        self.solid(rectangle(u, v, w, l, r), h, t, mat)

    def disc(self, u, v, h, r, t, mat, n=32):
        profile = circle(u, v, r, n)
        rows = [[point(a, b, z) for a, b in profile] for z in (h, h + t)]
        self.rings(rows, mat, True)
        self.surface[-2:] = [False, False]

    def path(self, path, r, mat, sides=8):
        self.pipe([point(*v) for v in path], r, mat, sides)

    def print(self, text, u, v, h, size, mat, reverse=False):
        self.label(
            text, size, lambda x, y: point(u + (-x if reverse else x), v - y, h), mat
        )

    def sheet(
        self, outline, holes, low, high, front, back=None, wall=None, project=point
    ):
        points, loops = [], []
        for ring in [outline, *holes]:
            signed = sum(
                a[0] * b[1] - a[1] * b[0] for a, b in zip(ring, ring[1:] + ring[:1])
            )
            order = ring if signed > 0 else list(reversed(ring))
            loops.append(list(range(len(points), len(points) + len(order))))
            points.extend(Vector(v) for v in order)
        verts, _, tris, _, _, ids = delaunay_2d_cdt(points, [], loops, 0, 0.00001)
        active = [tri for tri, ids in zip(tris, ids) if set(ids) == {0}]
        for z, material in [(high, front), (low, back or front)]:
            self.add(
                [project(p.x, p.y, z) for p in verts],
                active if z == low else [tuple(reversed(t)) for t in active],
                material,
                False,
            )
        for ring in [outline, *holes]:
            self.rings(
                [[project(a, b, z) for a, b in ring] for z in (low, high)],
                wall or front,
                False,
                False,
            )

    def make(self, group, pivot=None):
        obj = self.finalize()
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        group.objects.link(obj)
        if pivot:
            from mathutils import Matrix

            u, v, h = pivot
            loc = Vector((u * 0.001, -h * 0.001, -v * 0.001))
            obj.data.transform(Matrix.Translation(-loc))
            obj.location = loc
        return obj


def section(name):
    group = bpy.data.collections.new(name)
    board.children.link(group)
    return group


def face_texture(obj, material, path, reverse=False):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.pack()
    tex = material.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    material.node_tree.links.new(
        tex.outputs["Color"],
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"],
    )
    uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
    uv.name = "UVMap"
    mapping = material.node_tree.nodes.new("ShaderNodeUVMap")
    mapping.uv_map = uv.name
    material.node_tree.links.new(mapping.outputs["UV"], tex.inputs["Vector"])
    for poly in obj.data.polygons:
        if obj.data.materials[poly.material_index] != material:
            continue
        for i in poly.loop_indices:
            v = obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv = (
                1 - v.x / 0.244 if reverse else v.x / 0.244,
                1 + v.z / 0.305,
            )


def bake_substrate_occlusion(graphics):
    bpy.context.view_layer.update()
    vertices, faces = [], []
    for obj in board.all_objects:
        if obj.type != "MESH" or not obj.data.polygons:
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
        faces.extend(tuple(offset + i for i in poly.vertices) for poly in obj.data.polygons)
    geometry = BVHTree.FromPolygons(vertices, faces)
    width, height = 366, 458
    distance = 0.022
    rays = []
    for phase in range(4):
        directions = []
        for i in range(32):
            radius = math.sqrt((i + 0.5) / 32)
            angle = i * 2.39996323 + phase * math.pi / 2
            directions.append(Vector((radius * math.cos(angle), -math.sqrt(1 - radius*radius), radius * math.sin(angle))))
        rays.append(directions)
    visibility = bytearray(width * height)
    for row in range(height):
        z = -(row + 0.5) / height * 0.305
        for col in range(width):
            origin = Vector(((col + 0.5) / width * 0.244, -0.00004, z))
            blocked = 0
            for ray in rays[(col + 2*row) % 4]:
                hit = geometry.ray_cast(origin, ray, distance)[3]
                if hit is not None:
                    blocked += (1 - hit/distance)**2
            visibility[row * width + col] = round(255 * (1 - 0.92 * blocked / 32))
    subprocess.run(
        ["uv", "run", "--no-project", "--with", "pillow", "--", str(graphics),
         "--contact-map", str(width), str(height)], input=visibility, check=True,
    )
    tree = mask.node_tree
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(atelier / "artwork/face-occlusion.png"))
    texture.image.colorspace_settings.name = "Non-Color"
    texture.image.pack()
    mapping = next(node for node in tree.nodes if node.type == "UVMAP")
    tree.links.new(mapping.outputs["UV"], texture.inputs["Vector"])
    group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    output = tree.nodes.new("ShaderNodeGroup")
    output.node_tree = group
    channels = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(texture.outputs["Color"], channels.inputs["Color"])
    tree.links.new(channels.outputs["Red"], output.inputs["Occlusion"])


def printed_surface(obj, base, name, path, bounds, height, pivot=(0, 0, 0), emission=0, finish_map=None):
    material = bpy.data.materials.get(name)
    if material is None:
        material = base.copy()
        material.name = name
        image = bpy.data.images.load(
            str(atelier / "artwork" / path), check_existing=True
        )
        image.pack()
        tree = material.node_tree
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        mapping = tree.nodes.new("ShaderNodeUVMap")
        mapping.uv_map = "UVMap"
        tree.links.new(mapping.outputs["UV"], tex.inputs["Vector"])
        shader = tree.nodes["Principled BSDF"]
        tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
        if finish_map:
            treatment = tree.nodes.new("ShaderNodeTexImage")
            treatment.label = "Etching, foil and directional brushing"
            treatment.image = bpy.data.images.load(str(atelier / "artwork" / finish_map), check_existing=True)
            treatment.image.colorspace_settings.name = "Non-Color"
            treatment.image.pack()
            tree.links.new(mapping.outputs["UV"], treatment.inputs["Vector"])
            channels = tree.nodes.new("ShaderNodeSeparateColor")
            tree.links.new(treatment.outputs["Color"], channels.inputs["Color"])
            tree.links.new(channels.outputs["Green"], shader.inputs["Roughness"])
            tree.links.new(channels.outputs["Blue"], shader.inputs["Metallic"])
        if emission:
            tree.links.new(tex.outputs["Color"], shader.inputs["Emission Color"])
            shader.inputs["Emission Strength"].default_value = emission
    uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
    uv.name = "UVMap"
    obj.data.materials.append(material)
    x, y, w, h = bounds
    for poly in obj.data.polygons:
        if obj.data.materials[poly.material_index] != base:
            continue
        if any(
            abs(-obj.data.vertices[i].co.y * 1000 + pivot[2] - height) > 0.006
            for i in poly.vertices
        ):
            continue
        poly.material_index = len(obj.data.materials) - 1
        for i in poly.loop_indices:
            v = obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv = (
                (v.x * 1000 + pivot[0] - x) / w,
                1 - (-v.z * 1000 + pivot[1] - y) / h,
            )


def substrate(underside):
    group = section("PCB and plated mounting holes")
    pcb = Part("1.6 mm multilayer FR4 · Fubuki")
    pcb.sheet(
        rectangle(122, 152.5, 244, 305, 2.2),
        [circle(x, y, 1.67) for x, y in plateholes]
        + [circle(x, y, 2.15) for x, y in cooler_holes],
        -1.6,
        0,
        mask,
        rear,
        edge,
    )
    obj = pcb.make(group)
    face_texture(obj, mask, atelier / "artwork/face.png")
    face_texture(obj, rear, atelier / "artwork/rear.png", True)
    lands = Part("Ground lands and through-hole solder")
    for x, y in plateholes:
        for h in (0, -1.64):
            lands.sheet(circle(x, y, 3.65), [circle(x, y, 1.67)], h, h + 0.035, steel)
        for i in range(10):
            a = i * math.tau / 10
            lands.disc(
                x + 3 * math.cos(a), y + 3 * math.sin(a), 0.034, 0.18, 0.03, dark, 8
            )
    lands.make(group)
    joints = Part("Solder tails beneath the four DIMM slots")
    for x in [slot["centerMm"] for slot in slots]:
        for side in (-1, 1):
            for i in range(72):
                joints.disc(x + side * 2.2, 17 + i * 1.81, -1.86, 0.37, 0.22, steel, 8)
    joints.make(underside)
    return group


def socket(tray_side):
    group = section("LGA1851 retention mechanism")
    u, v = socket_u, socket_v
    backplate = Part("Socket steel backplate · rear")
    backplate.sheet(
        rectangle(u, v, 52, 72, 3), [rectangle(u, v, 21, 32, 1.7)], -4, -1.72, dark
    )
    for x, y in (
        (u - 19, v - 29),
        (u + 19, v - 29),
        (u - 19, v + 29),
        (u + 19, v + 29),
    ):
        backplate.disc(x, y, -4.7, 2.3, 0.8, steel)
        backplate.disc(x, y, -4.77, 1.05, 0.09, dark, 6)
    backplate.make(tray_side, (u, v, -1.6))
    underside = Part("CPU underside decoupling capacitors")
    for i in range(9):
        for j in range(8):
            x, y = u + (j - 3.5) * 2.12, v + (i - 4) * 2.94
            underside.box(x, y, -2.47, 1.64, 1.04, 0.85, core)
            for side in (-1, 1):
                underside.box(x + side * 0.74, y, -2.52, 0.21, 1.12, 0.93, steel)
    underside.make(tray_side, (u, v, -1.6))
    socket = Part("LGA1851 socket housing and contact banks")
    socket.box(u, v, 0.05, 47.5, 57.5, 2.0, dark, 1.4)
    socket.sheet(
        rectangle(u, v, 46.5, 56.4, 1.4),
        [rectangle(u, v, 40.4, 46.1, 0.9)],
        1.95,
        3.2,
        dark,
    )
    for row in range(45):
        for col in range(40):
            if 13 <= col <= 25 and 14 <= row <= 31:
                continue
            x, y = u + (col - 19.5) * 0.93, v + (row - 22) * 0.95
            socket.add(
                [
                    point(x - 0.28, y + 0.17, 2.1),
                    point(x + 0.03, y + 0.27, 2.1),
                    point(x + 0.32, y - 0.19, 2.67),
                    point(x + 0.04, y - 0.29, 2.58),
                ],
                [(0, 1, 2, 3)],
                gold,
                False,
            )
    for i in range(8):
        for j in range(5):
            x, y = u + (j - 2) * 2.06, v + (i - 3.5) * 1.92
            socket.box(x, y, 2.06, 1.56, 0.89, 0.51, core)
            for side in (-1, 1):
                socket.box(x + side * 0.7, y, 2.06, 0.19, 0.96, 0.56, steel)
    socket.make(group, (u, v, 0))
    cover = Part("Hinged independent loading plate")
    cover.sheet(
        rectangle(u, v, 47.8, 61, 3.1),
        [
            [
                (u + x, v + y)
                for x, y in [
                    (-15, -21),
                    (15, -21),
                    (17.25, -18.5),
                    (17.25, -6.4),
                    (15, -4.3),
                    (15, 0.3),
                    (17.25, 2),
                    (17.25, 18.4),
                    (15, 21),
                    (-15, 21),
                    (-17.25, 18.4),
                    (-17.25, 2.5),
                    (-15, 1),
                    (-15, -3.7),
                    (-17.25, -5.9),
                    (-17.25, -18.4),
                ]
            ]
        ],
        5.0,
        6.4,
        steel,
    )
    for x in (u - 20, u + 20):
        for y in (v - 28, v + 27):
            cover.disc(x, y, 6.4, 1.95, 1.0, steel)
            cover.disc(x, y, 7.4, 0.85, 0.04, dark, 6)
    for y in (v - 30, v + 29):
        for x in (u - 13, u + 12):
            cover.path([(x - 3.4, y, 5.9), (x + 3.4, y, 5.9)], 1.65, steel, 20)
    cover.path(
        [
            (u - 16, v + 28, 5),
            (u - 13, v + 31.4, 3.8),
            (u - 10, v + 31.4, 3.8),
            (u - 7, v + 28.4, 5.6),
            (u + 7, v + 28.4, 5.6),
            (u + 10, v + 31.4, 3.8),
            (u + 13, v + 31.4, 3.8),
            (u + 16, v + 28, 5),
        ],
        0.74,
        steel,
        12,
    )
    cover.print("LGA1851", u, v + 25.2, 6.43, 1.56, ink)
    cover.path(
        [
            (u - 18, v - 31, 4),
            (u - 18, v - 32, 6),
            (u + 22.8, v - 32, 6),
            (u + 24.6, v - 29, 6),
            (u + 24.9, v + 25, 4),
            (u + 27, v + 30, 3),
            (u + 29, v + 32, 4),
            (u + 30, v + 31, 5),
        ],
        1.04,
        steel,
        14,
    )
    cover.make(group, (u, v - 30, 4))
    for i, (x, y) in enumerate(cooler_holes):
        datum("LGA cooler mount " + str(i + 1), x, y, 0)
    datum("CPU contact", u, v, 7.5)
    for name, x, y, depth in [
        ("PCIe 5.0 x16", 83.4, 180, 4.3),
        ("EATX 24-pin", 233.4, 64, 10),
    ]:
        datum(name, x, y, depth)
    for slot in slots:
        datum("DDR5 " + slot["name"], slot["centerMm"], 81, 0)


def processor():
    model_script = scripts / "core-ultra-9-285k.py"
    maker = runpy.run_path(str(model_script))
    cpu = maker["build"](Part, coating, point, rectangle, sculpt["letters"])
    cpu_path = atelier / "lga1851-processor.blend"
    with tempfile.TemporaryDirectory(dir=atelier) as temp:
        source = Path(temp) / "package.blend"
        result = Path(temp) / "processor.blend"
        bpy.data.libraries.write(str(source), {cpu}, fake_user=True, compress=True)
        subprocess.run(
            [
                bpy.app.binary_path,
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python",
                str(model_script),
                "--",
                str(source),
                str(result),
            ],
            check=True,
        )
        result.replace(cpu_path)
    return cpu


def expansion():
    group = section("PCI Express, M.2 and chipset")
    nylon = coating("Ivory PCIe socket polymer", "dadbdb", 0.0, 0.54)
    socket_floor = coating("Recessed PCIe contact bed", "262829", 0.05, 0.67)
    for y, name in [
        (180, "SafeSlot PCIe 5.0 x16"),
        (283, "PCIe x16-length expansion slot"),
    ]:
        socket = Part(name)
        socket.box(82, y, 0.1, 97, 7, 3.9, nylon, 0.65)
        socket.box(83.4, y, 4.0, 88.8, 2.3, 0.32, socket_floor)
        socket.sheet(
            rectangle(83.4, y, 96, 7.1, 0.68),
            [rectangle(83.4, y, 88.8, 2.26, 0.29)],
            4.0,
            11.4,
            steel if y == 180 else nylon,
        )
        socket.box(53.7, y, 4.32, 1.65, 2.26, 7.08, nylon)
        for side in (-1, 1):
            for index in range(82):
                x = 39.7 + index * 1.065
                if 52.7 < x < 54.9:
                    continue
                socket.box(x, y + side * 0.89, 5.95, 0.42, 0.46, 4.8, steel)
                socket.box(x, y + side * 2.22, 11.40, 0.42, 1.13, 0.12, socket_floor)
        socket.solid(
            [
                (130, y - 2.8),
                (140, y - 3.5),
                (146, y - 2.9),
                (147.3, y),
                (143, y + 3.8),
                (136, y + 3.8),
                (130, y + 1.2),
            ],
            6.4,
            5.4,
            nylon,
        )
        socket.make(group, (38.6, y, 0))
    for x, y in [(28, 158), (146, 201), (34, 238), (34, 260)]:
        m2 = Part(f"M.2 edge socket and standoff {y}")
        m2.box(x, y, 0, 5.6, 22.1, 3.1, dark, 0.48)
        m2.box(x + 1.1, y, 3.1, 3.3, 21.3, 0.7, core)
        m2.disc(x + 82, y, 0, 2.65, 3.1, gold, 12)
        m2.disc(x + 82, y, 3.09, 1.16, 0.1, dark, 16)
        m2.make(group, (x, y, 0))
    primary = Part("M.2_1 removable heat spreader")
    profile = [(149, 5.7), (149, 10.3), (149.8, 11.3), (160, 11.3), (161, 11), (166.4, 9.9), (171.7, 7.5), (172.6, 6), (172.6, 3.4), (149.8, 3.4)]
    primary.rings(
        [[point(u + (4.6 if u < 20 and v < 150 else 0), v, z) for v, z in profile] for u in (17.8, 144.3)],
        alloy, False,
    )
    fin = [(37.9, 151.5), (136.8, 151.5), (131.1, 158), (32.2, 158)]
    primary.solid(fin, 11.29, 0.24, ink)
    for j in range(4):
        y = 151.72 + j * 1.52
        x = 38.1 - j * 1.34
        primary.solid([(x, y), (x + 98.3, y), (x + 97.2, y + 1.31), (x - 1.1, y + 1.31)], 11.50, 0.42, alloy)
    primary.solid([(22,151.3),(39.8,151.3),(33.1,159.2),(20.4,159.2),(20.4,155)],11.29,.18,ink)
    primary.solid([(22.2,151.6),(39.1,151.6),(33,158.8),(20.7,158.8),(20.7,155)],11.45,.11,alloy)
    primary.box(26.4, 156.2, 11.55, 11.4, 3.65, .18, ink, 1.7)
    primary.print("STRIX", 26.4, 156.7, 11.75, 1.83, legend)
    primary.box(148.1, 155.3, 5.4, 7.3, 13.5, 6.4, dark, .85)
    for row, count in enumerate((1, 2, 3, 2, 1)):
        for col in range(count):
            primary.box(147.5 + col * .85, 153.6 + row * .84, 11.8, .63, .61, .08, legend)
    primary.make(group, (18, 160, 3))

    armour = [
        ("Z890 chipset cover", 9.5,
         [(108.1,221.4),(137.3,191.5),(229.9,191.5),(229.9,216.5),(219.2,228.0),(114.4,228.0)], []),
        ("Twin SSD cooler upper plate", 7.5,
         [(21.9,240.0),(32.4,229.3),(245.8,229.3),(245.8,252.5),(21.9,252.5)],
         [(29.8,241.0),(237.4,240.6)]),
        ("Twin SSD cooler lower plate", 7.5,
         [(21.9,253.5),(245.8,253.5),(245.8,266.8),(236.6,276.1),(21.9,276.1)],
         [(29.8,265.2),(237.4,264.8)]),
    ]
    for name, height, outline, screws in armour:
        lid = Part(name)
        pivot = (*outline[0], 3)
        lid.sheet(outline, [circle(u,v,2.9) for u,v in screws], 3, height, alloy)
        obj = lid.make(group, pivot)
        printed_surface(obj, alloy, "Fubuki etched M.2 armour", "coolers.png",
                        (9.46, 178.15, 244.61, 105.04), height, pivot, finish_map="armor-finish.png")
        for u, v in screws:
            screw = Part(f"{name} · captive Phillips screw {u:.1f}")
            recess = [(1.43,.27),(.30,.30),(.27,1.43),(-.27,1.43),(-.30,.30),(-1.43,.27),
                      (-1.43,-.27),(-.30,-.30),(-.27,-1.43),(.27,-1.43),(.30,-.30),(1.43,-.27)]
            theta = .57 if u < 40 else -.72
            drive = [(u + x*math.cos(theta) - y*math.sin(theta), v + x*math.sin(theta) + y*math.cos(theta)) for x,y in recess]
            screw.disc(u,v,height-1.5,2.85,1.12,dark,36)
            screw.sheet(circle(u,v,2.58,36),[drive],height-.37,height+.04,steel,wall=core)
            screw.make(group,(u,v,3))


def regulation():
    group = section("VRM, DIMM sockets and I/O armour")
    source = runpy.run_path(str(scripts / "build-pc-internals.py"))
    from mathutils import Matrix

    datum_transform = Matrix.Translation((0.077, 0.289, 0.194)) @ Matrix.Rotation(
        -math.pi / 2, 4, "Z"
    )
    finishes = {
        "board-heatsinks": alloy,
        "board-shells": white,
        "board-components": dark,
        "board-caps": steel,
    }
    for name, parts in source["regulators"]().items():
        for obj in parts:
            if obj.name.startswith(
                (
                    "White rear I/O",
                    "Raised diagonally",
                    "Rear I/O edge",
                    "Vent louvre",
                    "Exposed side",
                    "Stamped capacitor seal",
                    "Polymer capacitor sleeve",
                )
            ):
                bpy.data.objects.remove(obj, do_unlink=True)
                continue
            obj.data.materials.append(finishes[name])
            bpy.context.view_layer.update()
            obj.matrix_world = datum_transform.inverted() @ obj.matrix_world
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            group.objects.link(obj)
    io = Part("Removable diagonal I/O and left VRM shroud")
    artwork = runpy.run_path(str(scripts / "strix-io-inlay.py"))
    def profile(points):
        return [artwork["board_point"](x, y) for x, y in points]
    io.solid(profile(artwork["fascia"]), 32.3, 1.7, white)
    io.solid(profile(artwork["inset"]), 34.0, 0.6, lcd)
    rail = [(389, 274), (493, 274), (525, 286), (533, 290),
            (533, 904), (526, 909), (344, 909), (329, 897), (389, 860)]
    io.solid(profile(rail), 26.5, 5, alloy)
    for i in range(3):
        stripe = artwork["diagonal_strip"](rail, 86 + 53 * i, 96 + 53 * i)
        io.solid(profile(stripe), 31.5, 0.12, dark)
    for offset in range(673, 916, 14):
        rib = artwork["diagonal_strip"](artwork["fluted_heel"], offset, offset + 5.0)
        if len(rib) >= 3:
            io.solid(profile(rib), 34, 0.5, alloy)
    obj = io.make(group, (0, 2, 32))
    printed_surface(
        obj, white, "I/O silver foil perimeter print", "io-fascia.png",
        artwork["board_bounds"](artwork["fascia_area"]), 34, (0, 2, 32),
    )
    printed_surface(
        obj,
        lcd,
        "I/O lenticular print",
        "inlay.png",
        artwork["board_bounds"](artwork["inset_area"]),
        34.6,
        (0, 2, 32),
        1.1,
    )
    tree = bpy.data.materials["I/O lenticular print"].node_tree
    luminous = tree.nodes.new("ShaderNodeTexImage")
    luminous.image = bpy.data.images.load(str(atelier / "artwork" / "io-emission.png"), check_existing=True)
    luminous.image.pack()
    mapping = next(node for node in tree.nodes if node.type == "UVMAP")
    tree.links.new(mapping.outputs["UV"], luminous.inputs["Vector"])
    tree.links.new(luminous.outputs["Color"], tree.nodes["Principled BSDF"].inputs["Emission Color"])
    for vertex in obj.data.vertices:
        u = vertex.co.x * 1000
        h = 32 - vertex.co.y * 1000
        slope = max(0, 59 - u) * 0.18
        vertex.co.y -= 0.001 * slope * min(1, max(0, (h - 3) / 29.3))
    obj.data.update()
    left = Part("Left-side VRM thermal rail and fins")
    left.box(45, 86, 1.9, 22, 113, 18, alloy, 1.1)
    for i in range(12):
        left.box(33 + i * 1.9, 86, 19.8, 0.68, 109, 7.4, alloy)
    left.make(group, (45, 86, 2))
    vrm = Part("Power stages, ferrite chokes and input capacitors")
    for x, y, count, dx, dy in [(88, 28, 8, 7.6, 0), (68.8, 54, 9, 0, 7.5)]:
        for i in range(count):
            u, v = x + i * dx, y + i * dy
            vrm.box(u, v, 0.1, 6.6, 6.2, 4.1, core, 0.42)
            vrm.box(
                u - (7.8 if dy else 0),
                v - (0 if dy else 7),
                0.1,
                4.6,
                5.4,
                1.4,
                silicon,
                0.2,
            )
    vrm.make(group)


def headers():
    group = section("Headers and power connectors")
    cha_fans = [90.1, 101.6, 113.0, 124.5, 136.1]
    for name, u, v, cols, rows, pitch, radius, body in [
        ("ATX 24-pin receptacle", 233.4, 64, 2, 12, 4.2, 0.44, 9.7),
        ("EPS12V A", 53.5, 4.6, 4, 2, 4.2, 0.44, 9.1),
        ("EPS12V B", 74, 4.6, 4, 2, 4.2, 0.44, 9.1),
        ("USB 3 header", 236, 135, 2, 10, 2, 0.28, 7.6),
        ("System panel", 232, 299, 8, 2, 2.54, 0.29, 4.6),
        ("Front audio", 35, 299, 5, 2, 2.54, 0.29, 4.8),
        ("USB 2 header A", 162.4, 299, 5, 2, 2.54, 0.29, 6.0),
        ("USB 2 header B", 178.5, 299, 5, 2, 2.54, 0.29, 6.0),
        ("Thunderbolt expansion", 194.1, 298.8, 7, 2, 2.0, 0.25, 4.6),
        *(("CHA_FAN" + str(i+1), x, 299, 4, 1, 2.54, 0.34, 6.0)
          for i, x in enumerate(cha_fans)),
        ("CPU OPT", 172, 3.6, 4, 1, 2.54, 0.28, 4.2),
        ("CPU FAN", 185, 3.6, 4, 1, 2.54, 0.28, 4.2),
        ("Pump tachometer", 200, 3.6, 4, 1, 2.54, 0.28, 4.2),
    ]:
        item = Part(name)
        w, l = cols * pitch + 0.9, rows * pitch + 0.9
        item.box(u, v, 0.08, w, l, 0.96, dark, 0.3)
        for c in range(cols):
            for r in range(rows):
                if name.startswith("USB 2") and c == cols - 1 and r == 1:
                    continue
                x, y = (
                    u + (c - (cols - 1) / 2) * pitch,
                    v + (r - (rows - 1) / 2) * pitch,
                )
                item.box(x, y, 1.03, radius * 1.35, radius * 1.35, body - 2, steel)
        if pitch > 4:
            holes = [
                rectangle(
                    u + (c - (cols - 1) / 2) * pitch,
                    v + (r - (rows - 1) / 2) * pitch,
                    pitch - 0.6,
                    pitch - 0.6,
                    0.5,
                )
                for c in range(cols)
                for r in range(rows)
            ]
            item.sheet(rectangle(u, v, w, l, 0.4), holes, 1.04, body, dark)
        elif name.startswith("CHA_FAN"):
            item.box(u, v-1.87, 1.04, w, 0.78, body-1.04, dark, 0.23)
            for side in (-1, 1):
                item.box(u + side*(w/2-0.38), v-0.52, 1.04, 0.76, 3.5, body-1.04, dark, 0.18)
        elif rows > 1 and name not in ("System panel", "Front audio"):
            item.sheet(
                rectangle(u, v, w, l),
                [rectangle(u, v, w - 1.2, l - 1.05)],
                1,
                body,
                dark,
            )
        item.make(group, (u, v, 0))
    for i, x in enumerate((62.1, 75.4, 48.1)):
        header = Part("Addressable 5V LED header " + str(i+1))
        header.box(x, 299.5, 0.08, 10.45, 3.17, 2.02, white, 0.22)
        for dx in (-3.81, -1.27, 3.81):
            header.box(x + dx, 299.5, 2.1, 0.55, 0.55, 4.35, steel)
        header.make(group, (x,299.5,0))
    rtc = Part("CR2032 lithium cell and spring clip")
    u, v = 211, 286
    rtc.disc(u, v, 0, 11.8, 3.3, dark)
    rtc.disc(u, v, 3.28, 9.98, 2.24, steel)
    rtc.disc(u, v, 5.50, 9.15, 0.20, alloy)
    rtc.print("CR2032", u, v - 1.6, 5.74, 2.8, ink)
    rtc.print("3V   +", u, v + 2.0, 5.74, 2.1, ink)
    rtc.box(u - 10, v, 1.8, 2.1, 6.1, 4.4, steel, 0.4)
    rtc.make(group, (u, v, 0))
    sound = Part("SupremeFX shielding and gold audio capacitors")
    sound.box(11.7, 263, 0.05, 19.7, 19, 3.7, core, 0.8)
    sound.print("SUPREMEFX", 9, 263, 3.8, 2.3, legend)
    for x in (12.5, 19):
        for y in (278, 285, 292):
            sound.disc(x, y, 0.1, 2.8, 6.3, gold, 24)
            sound.disc(x, y, 6.4, 2.25, 0.14, alloy, 24)
    sound.make(group)
    smd = Part("Surface-mount electronics and right-edge SATA")
    for u, v, w, h in [
        (91, 139, 4.5, 3.8),
        (127, 137, 4.5, 4.1),
        (153, 141, 7.4, 6.2),
        (28, 195, 5.2, 7.8),
        (76, 212, 5.6, 5.4),
        (111, 214, 8.7, 8.7),
        (171, 291, 5, 4.8),
    ]:
        smd.box(u, v, 0.13, w, h, 1.31, silicon, 0.23)
        for sign in (-1, 1):
            for c in range(9):
                smd.box(
                    u + (c - 4) * w / 10,
                    v + sign * h * 0.52,
                    0.15,
                    0.24,
                    0.81,
                    0.46,
                    steel,
                )
    smd.box(235.8, 207, 0.12, 14.7, 30.5, 11.2, dark, 0.5)
    for y in (200, 214):
        smd.box(242.9, y, 3.1, 1.1, 11.8, 5.4, silicon, 0.2)
    smd.disc(237, 22, 0.2, 5.3, 3.5, alloy)
    smd.disc(237, 22, 3.69, 4.2, 0.5, aqua)
    smd.print("START", 237, 22, 4.22, 1.55, legend)
    smd.make(group)


def board_electronics():
    group = section("Signal conditioning, audio and right-edge diagnostics")
    ceramic = coating("X7R ceramic bodies", "b59c79", 0.12, 0.59)
    can_top = coating("Gunmetal polymer capacitor crowns", "363738", 0.28, 0.55)
    for name, x, y, size, rows in [
        ("USB power delivery", 225.8, 116, 4.6, 5),
        ("Type-C retimer", 224, 128, 4, 4),
        ("Clock buffer", 166, 137, 4, 4),
        ("PCIe reference clock", 20, 191, 4.7, 4),
        ("Network and clock regulators", 45, 211, 4, 6),
        ("Expansion signal conditioners", 79, 205, 4, 5),
        ("Front-panel controller", 145, 286, 5.4, 5),
        ("Flash ROM", 184, 286, 4, 4),
        ("Storage interface controller", 230, 159, 4.6, 5),
        ("DDR5 auxiliary regulator", 212.6, 163.3, 5.4, 4),
        ("DDR5 power stage", 213.4, 172.2, 4.6, 4),
        ("SATA interface buffer A", 229.6, 181.0, 5.1, 4),
        ("SATA interface buffer B", 229.6, 186.7, 5.1, 3),
    ]:
        cluster = Part(name)
        cluster.box(x, y, 0.12, size, size, 0.86, silicon, 0.22)
        cluster.disc(x - size * 0.31, y - size * 0.31, 0.98, 0.21, 0.036, ink, 12)
        for side in (-1, 1):
            for i in range(8):
                delta = (i - 3.5) * size / 9
                cluster.box(x + delta, y + side * size / 2, 0.1, 0.19, 0.66, 0.27, steel)
                cluster.box(x + side * size / 2, y + delta, 0.1, 0.66, 0.19, 0.27, steel)
            for i in range(rows):
                for j in range(2):
                    u = x + side * (size / 2 + 1.4 + 2.1 * j)
                    v = y + (i - (rows - 1) / 2) * 1.19
                    cluster.box(u, v, 0.1, 1.48, 0.72, 0.48, steel, 0.08)
                    cluster.box(u, v, 0.12, 0.98, 0.75, 0.52, ceramic if (i+j)%3 else dark, 0.07)
        cluster.make(group, (x, y, 0))
    chokes = Part("Inductors and local rail switches below DIMM latches")
    for x, y, w, l, material in [(197.0, 165.2, 8.8, 6.3, core),
                                (227.2, 163.4, 3.6, 6.6, silicon),
                                (227.3, 170.8, 4.1, 4.8, core),
                                (208.8, 179.8, 2.6, 3.5, dark)]:
        chokes.box(x, y, 0.12, w+0.65, l-0.38, 0.63, steel, 0.21)
        chokes.box(x, y, 0.7, w, l, 2.04, material, 0.38)
    chokes.make(group)
    for name, arrays in [
        ("CPU decoupling and gate resistors", [(101.0, 68.4, 8, 1.32, 2),
                                               (101.1, 84.6, 6, 1.32, 2), (91.6, 109.0, 5, 1.14, 2)]),
        ("ATX sensing and USB line termination", [(223.9, 47.0, 12, 1.43, 3),
                                                  (224.2, 90.0, 8, 1.32, 3), (224.3, 106.7, 6, 1.26, 2)]),
        ("DIMM and PCIe rail compensation", [(158.5, 150.6, 4, 1.38, 4), (167.1, 150.2, 4, 1.38, 3),
                                             (205.0, 180.1, 5, 1.24, 3), (84.1, 201.4, 7, 1.27, 3)]),
    ]:
        array = Part(name)
        for x, y, rows, spacing, columns in arrays:
            for row in range(rows):
                for col in range(columns):
                    u, v = x + col * 1.69, y + row * spacing
                    array.box(u, v, 0.04, 1.29, 0.62, 0.24, steel)
                    array.box(u, v, 0.12, 0.77, 0.65, 0.32, ceramic if (row+col) % 4 == 0 else dark)
        array.make(group)
    for name, positions in [
        ("CPU north output bank", [(x, 41.1) for x in (103.6, 110.6, 117.7, 124.9, 131.9, 139.0, 146.0, 155.4)]),
        ("CPU west output bank", [(96.7, y) for y in (61.8, 68.9, 75.9, 83, 90, 97.1, 104.1)]
         + [(89.5, y) for y in (61.8, 68.9, 75.9, 83, 104.1)]),
        ("CPU auxiliary filtering", [(106.3, 129.6), (120.6, 129.6)]),
        ("Audio output filtering", [(18.1, 233.2), (18.4, 243.0)]),
        ("PCIe rail filtering", [(x, 211.4) for x in (42.2, 49.4, 56.6, 63.8, 70.7)] + [(42.5, 192), (49.6, 192)]),
        ("Memory and USB rail filtering", [(x, 172.5) for x in (186.8, 193.8, 200.8)] +
         [(221.1, 169.6), (225.1, 17.4), (225.1, 24.9), (233.0, 30.5), (240.2, 30.5),
          (225.0, 79.8), (225.0, 86.8), (230.3, 141.2)]),
        ("Expansion and RTC rail filtering", [(155.0, 286.2)]),
    ]:
        bank = Part(name)
        for x, y in positions:
            bank.box(x, y, 0.02, 5.1, 5.6, 0.66, dark, 0.85)
            bank.disc(x, y, 0.68, 3.08, 5.85, dark, 32)
            bank.disc(x, y, 6.52, 3.03, 0.24, core, 32)
            bank.disc(x, y, 6.76, 2.82, 0.11, can_top, 32)
            bank.box(x - 0.81, y, 6.87, 0.16, 3.55, 0.035, ink)
            bank.box(x - 1.11, y, 6.87, 0.12, 3.15, 0.035, ink)
        bank.make(group)
    leds = Part("Four POST diagnostic LEDs and test pads")
    for i, pigment in enumerate(("dcb0a0", "bea95b", "d9d9ce", "9dac81")):
        v=27.9+i*2.14
        leds.box(228.4,v,0.04,2.1,1.15,0.38,dark,0.11)
        leds.box(228.4,v,0.42,1.36,0.99,0.39,coating("Q-LED "+str(i+1),pigment,0.04,0.4),0.1)
    for j in range(2):
        for i in range(5):
            leds.disc(224.5+j*1.24,29+i*1.24,0.02,0.29,0.06,gold,12)
    leds.make(group)


def rear_io():
    group = section("Rear I/O shield and connectors")
    ports = [
        ("DP", 20, 23, 15, 6),
        ("HDMI", 38, 14, 6.7, 15),
        ("USB10", 55.8, 17.3, 13.4, 5.9),
        ("TB4", 55.8, 8.2, 9.5, 3.9),
        ("USB10", 76.2, 17.3, 13.4, 5.9),
        ("TB4", 76.2, 8.2, 9.5, 3.9),
        ("USB5", 96.5, 35, 13.4, 5.9),
        ("USB5", 96.5, 26, 13.4, 5.9),
        ("USB10", 96.5, 17.3, 13.4, 5.9),
        ("USB10", 96.5, 8.2, 13.4, 5.9),
        ("LAN", 117.5, 29, 16.2, 12.8),
        ("USB10", 117.5, 17.3, 13.4, 5.9),
        ("USB-C", 117.5, 8.2, 9.5, 3.9),
        ("WiFi", 134.5, 35, 6, 6),
        ("WiFi", 134.5, 12.2, 6, 6),
        ("Mic", 149, 34, 7.4, 7.4),
        ("Line", 149, 22.6, 7.4, 7.4),
        ("Optical", 149, 10.1, 10.7, 8.9),
        ("Clear CMOS", 16, 7.3, 4, 2.5),
        ("BIOS", 26.8, 7.3, 4, 2.5),
    ]
    plate = Part("Pre-mounted stainless rear I/O shield")

    def plane(v, h, u):
        return point(u, v, h)

    def cutout(name, x, y, w, h):
        if name in ("Mic", "Line", "WiFi"):
            return circle(x, y, w / 2)
        if name == "DP":
            return [
                (x - w / 2, y - h / 2 + 1.3),
                (x - w / 2 + 1.3, y - h / 2),
                (x + w / 2, y - h / 2),
                (x + w / 2, y + h / 2),
                (x - w / 2, y + h / 2),
            ]
        return rectangle(
            x, y, w, h, min(h, w) * (0.43 if name in ("TB4", "USB-C") else 0.09)
        )

    plate.sheet(
        rectangle(79.5, 23.5, 159, 46.2, 1.45),
        [cutout(*p) for p in ports],
        -13.7,
        -13,
        white,
        alloy,
        steel,
        plane,
    )
    plate.make(group)
    markings = Part("I/O printed legends and port symbols")
    for name, y, h in [
        ("DP", 20, 28.5),
        ("HDMI", 38, 25),
        ("10G", 55.8, 22.7),
        ("10G", 76.2, 22.7),
        ("5G", 96.5, 40),
        ("2.5G", 117.5, 38.2),
        ("BIOS", 125.5, 17.3),
        ("WI-FI 7", 135, 23.5),
        ("MIC IN", 148, 39.7),
        ("LINE OUT", 149, 28.1),
        ("S/PDIF", 149, 16.6),
        ("CMOS", 16, 11.4),
        ("FLASH", 26.8, 11.4),
        ("ROG", 20, 36.8),
    ]:
        markings.label(
            name,
            3.15 if name == "ROG" else 1.34,
            lambda x, b: plane(y + x, h + b, -13.75),
            ink,
        )
    markings.make(group)
    for name, v, h, w, t in ports:
        sock = Part(name + " jack")
        outside = cutout(name, v, h, w - 0.28, t - 0.28)
        inside = cutout(name, v, h, w - 1.22, t - 1.22)
        sock.sheet(
            outside,
            [inside],
            -13.55,
            -5.5,
            steel if name not in ("Mic", "Line") else gold,
            project=plane,
        )
        sock.rings(
            [[plane(a, b, u) for a, b in inside] for u in (-5.45, 1)], dark, False
        )
        if name in ("USB10", "USB5", "TB4", "USB-C", "HDMI", "DP"):
            tab = (
                rectangle(v, h - 0.35, w - 2.8, 1.25, 0.28)
                if name != "HDMI"
                else rectangle(v, h, 1.5, t - 3, 0.45)
            )
            sock.rings(
                [[plane(a, b, u) for a, b in tab] for u in (-12, -5.4)],
                red if name == "USB10" else blue if name == "USB5" else dark,
                False,
            )
        if name == "LAN":
            for k in range(8):
                sock.path(
                    [
                        (-9.4, v + (k - 3.5) * 1.03, h - 3),
                        (-3, v + (k - 3.5) * 1.03, h + 1),
                    ],
                    0.14,
                    gold,
                    6,
                )
        if name == "WiFi":
            sock.pipe([plane(v, h, -15), plane(v, h, -8)], 1.15, steel, 24)
        if name in ("Mic", "Line"):
            sock.pipe([plane(v, h, -7), plane(v, h, -2)], 1.6, dark, 18)
        if name in ("USB10", "USB5"):
            for k in range(4):
                sock.path(
                    [
                        (-11, v + (k - 1.5) * 2.14, h + 0.34),
                        (-7, v + (k - 1.5) * 2.14, h + 0.34),
                    ],
                    0.19,
                    steel,
                    6,
                )
        sock.make(group, (-13, v, h))


def main():
    graphics = scripts / "strix-board-graphics.py"
    print_sources = [
        graphics,
        scripts / "strix-rear-silkscreen.py",
        scripts / "strix-armor.py",
        scripts / "strix-io-inlay.py",
        *(scripts / "strix-prints").iterdir(),
    ]
    last_print_edit = max(source.stat().st_mtime_ns for source in print_sources)
    artwork = [
        atelier / "artwork" / f"{name}.{extension}"
        for name in ("face", "rear", "coolers", "inlay", "io-emission", "io-fascia", "armor-finish")
        for extension in ("png", "webp")
    ]
    if any(
        not path.exists() or path.stat().st_mtime_ns < last_print_edit
        for path in artwork
    ):
        subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--with",
                "pillow",
                "--",
                str(graphics),
            ],
            check=True,
        )
    underside = section("Tray-facing socket backplate and solder joints")
    substrate(underside)
    socket(underside)
    cpu = processor()
    expansion()
    regulation()
    headers()
    board_electronics()
    rear_io()
    bake_substrate_occlusion(graphics)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(atelier / "strix-z890-a.blend"), compress=True
    )
    export_board(board, mounts, cpu)


def export_board(board, mounts, cpu):
    for material in bpy.data.materials:
        if not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if (
                node.type == "TEX_IMAGE"
                and node.image
                and node.image.filepath
                and node.image.file_format == "PNG"
            ):
                image_path = Path(bpy.path.abspath(node.image.filepath)).with_suffix(".webp")
                color_space = node.image.colorspace_settings.name
                node.image = bpy.data.images.load(str(image_path), check_existing=True)
                node.image.colorspace_settings.name = color_space
    for obj in mounts.objects:
        obj.hide_set(True)
    installed = bpy.data.objects.new(f"Installed {cpu['model']}", None)
    installed["model"] = cpu["model"]
    installed["specCode"] = cpu["specCode"]
    installed["socket"] = cpu["socket"]
    installed.instance_type = "COLLECTION"
    visible_cpu = bpy.data.collections.new("285K installed surfaces")
    for part in cpu.objects:
        if not part.get("installedHidden"):
            visible_cpu.objects.link(part)
    installed.instance_collection = visible_cpu
    installed.location = mounts.objects["CPU contact"].location.copy()
    board.objects.link(installed)
    for collection in board.children:
        physical = [o for o in collection.objects if o.type == "MESH"]
        if not physical:
            continue
        tray_facing = collection.name == "Tray-facing socket backplate and solder joints"
        bpy.ops.object.select_all(action="DESELECT")
        for obj in physical:
            uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
            uv.name = "UVMap"
            uv.active_render = True
            if tray_facing:
                if obj.name.startswith("Solder tails beneath"):
                    obj["installedHidden"] = True
                elif obj.name.startswith("CPU underside decoupling capacitors"):
                    obj["inspectionDetail"] = True
            obj.select_set(True)
        bpy.context.view_layer.objects.active = physical[0]
        bpy.ops.object.convert(target="MESH")
        if tray_facing:
            continue
        if len(physical) > 1:
            bpy.ops.object.join()
        bpy.context.object.name = collection.name
    output = root / "public/media/models/strix-z890-a.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_image_format="WEBP",
        export_animations=False,
        export_apply=True,
        export_extras=True,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(output)], check=True
    )


if __name__ == "__main__":
    if "--processor-only" in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(atelier / "strix-z890-a.blend"))
        existing_cpu = bpy.data.collections.get("LGA1851 processor package")
        if existing_cpu:
            bpy.data.collections.remove(existing_cpu)
            bpy.data.orphans_purge(do_recursive=True)
        cpu = processor()
        export_board(
            bpy.data.collections["ROG Strix Z890-A Gaming WiFi S"],
            bpy.data.collections["Mechanical datums"],
            cpu,
        )
    else:
        main()
