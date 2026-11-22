import math
import runpy
import subprocess
import sys
from pathlib import Path
import bmesh
import bpy
from mathutils import Matrix, Vector


root = Path(__file__).resolve().parents[2]
review = root / ".review/atelier"
publish = "--publish" in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
shared = runpy.run_path(str(Path(__file__).with_name("vitrine-sculpt.py")))
Sculpture, finish = shared["Sculpture"], shared["finish"]
alloy = finish("Snow Peak · satin brushed stainless", "dbdbda", 0.81, 0.29)
turned = finish("Spun polished steel lip", "dedfdd", 0.88, 0.24)
titanium = finish("Snow Peak · bead-blasted titanium", "aaa9a0", 0.72, 0.48)
blue = finish("Snow Peak · blue anodised titanium", "51748a", 0.62, 0.39)
wire = finish("Folded stainless spring wire", "a4aaac", 0.84, 0.26)
ink = finish("Screenprinted charcoal", "23272b", 0.06, 0.56)
wood = finish("Natural beech lid knob", "b5804e", 0.01, 0.43)
brass = finish("Knurled brass thumb screw", "ab9667", 0.77, 0.27)
grain = runpy.run_path(str(Path(__file__).with_name("product-grain.py")))
grain["coat_grain"](
    "Cookware · drawn grain", [(alloy, 0.065), (turned, 0.035), (wire, 0.028)], True
)
grain["coat_grain"]("Cookware · satin microtexture", [(titanium, 0.085), (blue, 0.070)])
grain["cherry"](wood)


def pose(shape, position, pitch=0, yaw=0, roll=0, eye=None):
    obj = shape.finalize(
        uv_scale=35,
        uv_materials=(wood, alloy, turned, titanium, blue, wire),
    )
    obj["cookware"] = shape.name
    rot = (
        Matrix.Rotation(yaw, 3, "Z")
        @ Matrix.Rotation(pitch, 3, "X")
        @ Matrix.Rotation(-roll, 3, "Y")
    )
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = rot.to_quaternion()
    x, y, d = position
    obj.location = Vector((x, -d, y)) / 1000
    if eye:
        ex, ey, ed = eye
        obj.location -= (rot @ Vector((ex, -ed, ey))) / 1000
    return obj


def interpolate(stations, y):
    for (a, wa), (b, wb) in zip(stations, stations[1:]):
        if y <= b:
            t = min(1, max(0, (y - a) / (b - a)))
            return wa * (1 - t) + wb * t
    return stations[-1][1]


def curved_path(shape, control, radius, material, sides=10, section=None):
    points = []
    for i in range(len(control) - 1):
        p0, p1, p2, p3 = [
            Vector(control[min(len(control) - 1, max(0, j))])
            for j in (i - 1, i, i + 1, i + 2)
        ]
        steps = min(20, max(5, math.ceil((p2 - p1).length))) if section else 5
        for j in range(steps):
            t = j / steps
            points.append(
                (
                    2 * p1
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t
                )
                * 0.5
            )
    points.append(Vector(control[-1]))
    if section:
        section(shape, points, radius, material, sides)
    else:
        shape.pipe(points, radius, material, sides)


def utensil(name, material, fork):
    piece = Sculpture(name)
    if fork:
        stations = [
            (5, 4.20),
            (25, 4.5),
            (65, 4.3),
            (87, 4.5),
            (96, 5.2),
            (103, 6.8),
            (110, 10.4),
            (118, 15.5),
            (125, 18.5),
            (132, 20.0),
            (139, 20.2),
            (145, 19.5),
            (150, 17.9),
        ]
    else:
        stations = [
            (5, 5.5),
            (16, 5.4),
            (30, 5.3),
            (66, 5.15),
            (84, 4.3),
            (95, 4.6),
            (106, 6.1),
            (116, 10.9),
            (122, 14.4),
            (130, 17.8),
            (138, 18.9),
            (146, 18.2),
            (150, 17.2),
        ]
    half = stations[0][1]
    rows = []
    for w, h, offset in [
        (2.1, 3.0, -0.55),
        (half, 6.15, -0.55),
        (half, 6.15, 0.34),
        (2.1, 3.0, 0.34),
        (2.1, 3.0, -0.55),
    ]:
        rows.append(
            [
                (
                    w * math.cos(i * math.tau / 40),
                    -4 + h * math.sin(i * math.tau / 40),
                    offset,
                )
                for i in range(40)
            ]
        )
    piece.rings(rows, material, True, False)
    n = 40
    handle_rows, tip_rows = 22, 7
    last = handle_rows + tip_rows
    coords = []
    for bottom in (False, True):
        for j in range(last + 1):
            for k in range(n + 1):
                u = 2 * k / n - 1
                notch = max(
                    math.exp(-(((u - pos) / 0.089) ** 4)) for pos in (-0.49, 0, 0.49)
                )
                end = (
                    163.6
                    - 7.0 * abs(u) ** 2
                    + (1.4 if fork else 0)
                    - (10.3 * notch if fork else 11 * abs(u) ** 4)
                )
                if not fork:
                    end = 164.2
                s = (
                    7.05 + (150 - 7.05) * j / handle_rows
                    if j <= handle_rows
                    else 150 + (end - 150) * (j - handle_rows) / tip_rows
                )
                w = interpolate(stations, min(s, 150))
                x = u * w
                if j > handle_rows:
                    progress = (j - handle_rows) / tip_rows
                    x *= (
                        1 - 0.21 * progress
                        if fork
                        else max(0.015, math.sqrt(1 - progress**2))
                    )
                bend = math.sin(math.pi * max(0, min(1, (s - 100) / 68)))
                arc = -9.9 * bend * (1 - u * u) + 2.7 * max(0, (s - 144) / 23)
                handle_ridge = 0.7 * (1 - u * u) * max(0, min(1, (105 - s) / 10))
                thick = 0.88 if fork else 1.05
                coords.append(
                    (x, -s, arc + handle_ridge - (thick * 0.58 if bottom else -0.34))
                )
    stride = (last + 1) * (n + 1)
    faces = []
    for j in range(last):
        for k in range(n):
            a = j * (n + 1) + k
            quad = (a, a + 1, a + n + 2, a + n + 1)
            faces.extend((quad, tuple(stride + i for i in reversed(quad))))
    boundary = [
        *range(n + 1),
        *(j * (n + 1) + n for j in range(1, last + 1)),
        *(last * (n + 1) + k for k in range(n - 1, -1, -1)),
        *(j * (n + 1) for j in range(last - 1, 0, -1)),
    ]
    for i, a in enumerate(boundary):
        b = boundary[(i + 1) % len(boundary)]
        faces.append((b, a, a + stride, b + stride))
    piece.add(coords, faces, material, True)
    if fork:
        piece.label(
            "snow peak",
            3.9,
            lambda x, y: (y, -27 + x, 1.18),
            titanium if material == blue else turned,
        )
        for a in range(3):
            v = math.pi * a / 3
            piece.pipe(
                [
                    (-1.65 * math.cos(v), -15 - 1.65 * math.sin(v), 1.20),
                    (1.65 * math.cos(v), -15 + 1.65 * math.sin(v), 1.20),
                ],
                0.24,
                turned,
                6,
            )
    return piece


def hook(shape, x, y, reach):
    controls = [
        (x - 12.7, y + 15, 42),
        (x - 12.7, y, 50),
        (x - 12.6, y - 7, 56),
        (x - 2, y - 11, 59),
        (x, y - 14, 66),
        (x, y - 15, reach - 5),
        (x, y - 13.3, reach + 2),
        (x, y - 7.1, reach + 5),
    ]
    curved_path(shape, controls, 1.20, wire)
    return x, y - 14.5, reach - 3


rack = Sculpture("Stainless utensil and Trek cookset hooks")
for column, name, mat, fork, pitch, yaw, roll in [
    (-6, "Snow Peak SCT-004 · titanium", titanium, True, -0.16, -0.28, 0.06),
    (-2, "Snow Peak SCT-002 · titanium spoon", titanium, False, -0.09, 0.18, -0.07),
    (2, "Snow Peak SCT-004BL · blue titanium", blue, True, -0.19, 0.29, 0.04),
]:
    support = hook(rack, column * 25.4, 1572 + 5 * 25.4, 91)
    pose(utensil(name, mat, fork), support, pitch, yaw, roll, (0, -1.6, 0))


for i in range(3):
    bowl = Sculpture("Snow Peak Trek STW-003T · " + str(i + 1))
    profile = [
        (0, 0.01),
        (0, 39.6),
        (0.6, 42.6),
        (2.2, 43.2),
        (3.6, 47),
        (6, 50.4),
        (12, 54.4),
        (28, 60.9),
        (46, 66.0),
        (60.4, 69.3),
        (62, 69.5),
        (62.7, 70),
        (63.45, 69.7),
        (63.6, 68.9),
        (62.9, 68.4),
        (61.9, 68.5),
        (60.3, 68.6),
        (46, 65.3),
        (27.9, 60.2),
        (11.9, 53.6),
        (6.3, 49.2),
        (3.7, 44),
        (2.9, 40.5),
        (2.85, 0.01),
    ]
    bowl.turn(profile, titanium, 80)
    pose(bowl, (213, 1075 + i * 5.4, 168), yaw=i * 0.53)


pan_model = runpy.run_path(str(Path(__file__).with_name("camp-vessels.py")))
pan_model["cookset"](Sculpture, pose, curved_path, titanium, wire, turned)
glass = finish("Clear pressed glass · percolator sight", "ebf2eb", 0.0, 0.065, 0.35)
glass_bsdf = glass.node_tree.nodes.get("Principled BSDF")
glass_bsdf.inputs["Transmission Weight"].default_value = 1.0
glass_bsdf.inputs["IOR"].default_value = 1.51
glass.surface_render_method = "DITHERED"

archive = bpy.data.collections.new("Reference models · kept off the display wall")
bpy.context.scene.collection.children.link(archive)
reference_kettle = pan_model["coffee_kettle"](
    Sculpture, curved_path, alloy, turned, wire, brass, wood, ink
)
pose(reference_kettle, (-55, 1075, 163), yaw=-0.22)
pose(rack, (0, 0, 0))
for part in list(bpy.context.scene.objects):
    for collection in list(part.users_collection):
        collection.objects.unlink(part)
    archive.objects.link(part)
archive.hide_viewport = True
archive.hide_render = True

coffee = runpy.run_path(str(Path(__file__).with_name("snow-peak-field-coffee.py")))
coffee["build"](
    Sculpture,
    pose,
    curved_path,
    alloy,
    turned,
    wire,
    brass,
    glass,
    ink,
    None if publish else review / "cookware-reference",
)
trek = runpy.run_path(str(Path(__file__).with_name("snow-peak-trek-900.py")))
native_trek = root / ".references/07-户外装备/炊具与餐具/Snow Peak Trek bowls and pans/Blender/trek-900-scs-008t.blend"
trek["build"](Sculpture, curved_path, titanium, wire, turned, native_trek if publish else None)

packed_spork = pose(
    utensil("Snow Peak SCT-004 · packed titanium spork", titanium, True),
    (23, 1075, 252),
    pitch=-1.645,
    yaw=1.47,
)
bpy.context.view_layer.update()
lowest = min((packed_spork.matrix_world @ v.co).z for v in packed_spork.data.vertices)
packed_spork.location.z += 1.075 - lowest

bpy.context.scene.unit_settings.system = "METRIC"
if not publish:
    bpy.ops.wm.save_as_mainfile(filepath=str(review / "camp-cookware.blend"))
glass_bsdf.inputs["Transmission Weight"].default_value = 0
glass_bsdf.inputs["Alpha"].default_value = 0.14
for part in bpy.context.scene.objects:
    if part.get("closedInterior"):
        part.hide_set(True)
    if part.get("coffeePart") == "screw":
        thread = part.vertex_groups["Thread inside the receiver"]
        hidden_vertices = {
            v.index
            for v in part.data.vertices
            if any(g.group == thread.index for g in v.groups)
        }
        export_screw = bmesh.new()
        export_screw.from_mesh(part.data)
        bmesh.ops.delete(
            export_screw,
            geom=[v for v in export_screw.verts if v.index in hidden_vertices],
            context="VERTS",
        )
        export_screw.to_mesh(part.data)
        export_screw.free()
    if part.get("coffeePart") == "riser":
        visible_jet = bmesh.new()
        visible_jet.from_mesh(part.data)
        bmesh.ops.delete(
            visible_jet,
            geom=[v for v in visible_jet.verts if v.co.z < 0.135],
            context="VERTS",
        )
        visible_jet.to_mesh(part.data)
        visible_jet.free()
target = root / "public/media/models/camp-cookware.glb"
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_extras=True,
    export_animations=False,
    use_visible=True,
    export_cameras=False,
    export_lights=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(Path(__file__).with_name("pack-product-geometry.mjs")), str(target)],
    check=True,
)
if not publish:
    coffee["openable_master"](review / "cookware-reference/field-coffee-master.blend")
