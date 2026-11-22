import math
import runpy
import subprocess
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


scripts = Path(__file__).resolve().parent
project = scripts.parent.parent
atelier = project / ".review/atelier"
editable = atelier / "aeron-c7/c7-caster.blend"
solids = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = solids["Sculpture"], solids["finish"]
radius, trail = 31.75, 20.6


def axle_surface(shape, profile, side, material, segments=72):
    rows = [
        [
            (
                side * width,
                radius + r * math.cos(math.tau * j / segments),
                trail + r * math.sin(math.tau * j / segments),
            )
            for j in range(segments)
        ]
        for width, r in profile
    ]
    shape.rings(rows, material, close=profile[0] != profile[-1])


def wheel(side, nylon, urethane):
    name = "Port" if side < 0 else "Starboard"
    core = Sculpture(name + " · injection-moulded wheel")
    axle_surface(
        core,
        [
            (23.19, 0.04),
            (23.19, 11),
            (23.20, 18),
            (23.27, 23.7),
            (23.27, 24.31),
            (23.20, 24.62),
            (22.97, 24.72),
            (21.3, 24.72),
            (21.25, 26.1),
            (10.55, 26.1),
            (10.34, 25.4),
            (10.48, 24.05),
            (11.29, 23.1),
            (13.40, 22.32),
            (16.6, 21.1),
            (17.5, 20.5),
            (18.0, 19.8),
            (18, 8.1),
            (17.5, 7.6),
            (16.4, 7.4),
            (8.9, 7.4),
            (8.62, 7.0),
            (8.62, 2.66),
            (9.25, 2.44),
            (19.65, 2.44),
            (20.2, 2.1),
            (20.3, 0.04),
        ],
        side,
        nylon,
    )
    tire = Sculpture(name + " · soft polyurethane tread")
    profile = [
        (22.88, 24.88),
        (23.23, 24.96),
        (23.63, 25.6),
        (23.94, 26.83),
        (24.00, 28.23),
        (23.83, 29.26),
        (23.43, 30.13),
        (22.80, 30.81),
        (21.60, 31.42),
        (20.25, 31.68),
        (18.65, 31.75),
        (12.24, 31.75),
        (11.05, 31.67),
        (10.29, 31.40),
        (9.85, 30.86),
        (9.70, 29.96),
        (9.70, 27.0),
        (9.92, 25.64),
        (10.32, 25.2),
        (10.52, 26.15),
        (21.29, 26.15),
        (21.36, 24.88),
    ]
    axle_surface(tire, profile + [profile[0]], side, urethane)
    return core, tire


def yoke(nylon):
    body = Sculpture("Fork · open nylon axle carrier and crown")
    rows = []
    for i in range(49):
        a = math.radians(2.5 + 175.0 * i / 48)
        ca, sa = math.cos(a), math.sin(a)
        rows.append(
            [
                (x, radius + r * sa, trail + r * ca)
                for x, r in [
                    (-8.9, 29.1),
                    (-9.04, 29.52),
                    (-9.04, 31.08),
                    (-8.99, 31.36),
                    (-8.8, 31.52),
                    (-8.46, 31.56),
                    (0, 31.63),
                    (8.46, 31.56),
                    (8.8, 31.52),
                    (8.99, 31.36),
                    (9.04, 31.08),
                    (9.04, 29.52),
                    (8.9, 29.1),
                    (8.55, 28.96),
                    (-8.55, 28.96),
                ]
            ]
        )
    body.rings(rows, nylon)
    body.loft(
        [
            (0, 28.05, 19.80, 5.0, 3.03),
            (0, 29.66, 19.15, 7.1, 6.1),
            (0, 33.50, 17.90, 7.55, 8.5),
            (0, 39, 14.6, 7.55, 9.90),
            (0, 45.8, 10.5, 7.5, 10.6),
            (0, 52.9, 6.80, 7.5, 10.4),
            (0, 56.4, 5.51, 7.56, 9.25),
        ],
        nylon,
        24,
        0.83,
    )
    body.turn(
        [
            (40.2, 4.1),
            (41.6, 7.0),
            (43.4, 7.8),
            (45.3, 8.0),
            (62.95, 8.0),
            (63.66, 7.94),
            (63.96, 7.66),
            (64.02, 7.37),
            (64.02, 5.05),
            (63.82, 4.94),
            (46.0, 4.94),
            (45.38, 4.55),
        ],
        nylon,
        48,
    )

    def die_point(d, h):
        return (math.sqrt(8.0**2 - d**2) + 0.015, h, d)

    outlines = [
        [(-3.20, 63.62), (-3.20, 59.90), (3.20, 59.90), (3.20, 63.62)],
        [
            (-2.62, 62.59),
            (-2.26, 61.96),
            (-1.47, 61.39),
            (-0.44, 61.09),
            (0.62, 61.13),
            (1.62, 61.52),
            (2.38, 62.11),
            (2.69, 62.68),
        ],
    ]
    for outline in outlines:
        body.pipe([die_point(d, h) for d, h in outline], 0.095, nylon, 6)
    return body


def hardware(steel, bushing, graphite):
    stem = Sculpture("Swivel · zinc-plated grip-ring stem")
    stem.turn(
        [
            (45.85, 0.03),
            (45.85, 4.16),
            (46.24, 4.74),
            (63.9, 4.74),
            (64.42, 4.92),
            (65.48, 4.92),
            (65.69, 5.94),
            (66.06, 6.32),
            (66.77, 6.4),
            (68.16, 6.30),
            (68.53, 5.88),
            (70.66, 5.38),
            (82.87, 5.38),
            (83.06, 5.21),
            (83.18, 4.36),
            (85.18, 4.36),
            (85.35, 5.27),
            (85.61, 5.40),
            (89.10, 5.40),
            (90.08, 5.20),
            (90.56, 4.64),
            (90.72, 3.15),
            (90.72, 0.03),
        ],
        steel,
        40,
    )
    ring = Sculpture("Swivel · split spring retaining ring")
    points = []
    for i in range(40):
        a = math.radians(12 + 336 * i / 39)
        points.append((4.97 * math.cos(a), 84.20, 4.97 * math.sin(a)))
    ring.pipe(points, 0.71, steel, 10)
    shaft = Sculpture("Axle · steel wheel pin")
    axle_surface(
        shaft,
        [
            (-19.61, 2.1),
            (-19.27, 2.45),
            (-9.2, 2.45),
            (-8.92, 2.65),
            (8.92, 2.65),
            (9.2, 2.45),
            (19.27, 2.45),
            (19.61, 2.1),
        ],
        1,
        steel,
        36,
    )
    bearing = Sculpture("Fork · transverse axle bearing")
    profile = [
        (-8.51, 2.71),
        (-8.51, 5.18),
        (-8.27, 5.52),
        (-7.84, 5.62),
        (7.84, 5.62),
        (8.27, 5.52),
        (8.51, 5.18),
        (8.51, 2.71),
    ]
    axle_surface(bearing, profile + [profile[0]], 1, bushing, 36)
    socket = Sculpture("Star base · cast blind stem socket")
    socket.turn(
        [
            (65.00, 6.53),
            (65.05, 8.53),
            (65.35, 9.07),
            (66.29, 9.39),
            (88.9, 9.39),
            (90.71, 9.14),
            (92.00, 8.34),
            (92.73, 6.65),
            (92.81, 0.04),
            (91.27, 0.04),
            (91.27, 4.03),
            (90.91, 5.52),
            (85.51, 5.65),
            (85.20, 5.89),
            (83.13, 5.89),
            (82.86, 5.60),
            (71.01, 5.60),
            (69.42, 6.00),
            (68.12, 6.58),
            (65.00, 6.53),
        ],
        graphite,
        48,
    )
    return stem, ring, shaft, bearing, socket


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    editable.parent.mkdir(parents=True, exist_ok=True)
    nylon = finish("C7 · textured black nylon", "252727", rough=0.53)
    urethane = finish("C7 · dark soft polyurethane", "232526", rough=0.32, coat=0.11)
    steel = finish("C7 · zinc plate", "a4abaa", 0.83, 0.31)
    graphite = finish("C7 · graphite base finish", "404341", 0.27, 0.50)
    bushing = finish("C7 · axle bearing black", "202324", 0.10, 0.44)
    runpy.run_path(str(scripts / "product-grain.py"))["coat_grain"](
        "C7 · mould grain", [(nylon, 0.13)]
    )
    root = bpy.data.objects.new("Herman Miller C7 · 241670", None)
    bpy.context.scene.collection.objects.link(root)
    root["nominalWheelDiameterMm"] = 63.5
    shapes = [
        *wheel(-1, nylon, urethane),
        *wheel(1, nylon, urethane),
        yoke(nylon),
        *hardware(steel, bushing, graphite),
    ]
    for shape in shapes:
        obj = shape.finalize(uv_scale=53 if nylon in shape.materials else 0)
        topology = bmesh.new()
        topology.from_mesh(obj.data)
        bmesh.ops.remove_doubles(topology, verts=list(topology.verts), dist=0.000000015)
        boundary = [edge for edge in topology.edges if edge.is_boundary]
        if boundary:
            bmesh.ops.holes_fill(topology, edges=boundary, sides=0)
        bmesh.ops.recalc_face_normals(topology, faces=list(topology.faces))
        topology.to_mesh(obj.data)
        topology.free()
        obj.parent = root
        obj["casterPart"] = shape.name
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active.region_3d
            view.view_distance = 0.18
            view.view_location = (0, -0.015, 0.044)
            view.view_rotation = Vector((-0.9, 1, -0.35)).to_track_quat("-Z", "Y")
    bpy.ops.wm.save_as_mainfile(filepath=str(editable), compress=True)
    for obj in list(root.children):
        name = obj["casterPart"]
        if name.startswith(("Axle ·", "Swivel · split")):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        topology = bmesh.new()
        topology.from_mesh(obj.data)
        hidden = []
        for face in topology.faces:
            x, y, h = face.calc_center_median() * 1000
            radial = math.hypot(y + trail, h - radius)
            if name.startswith("Swivel ·") and (h < 63.88 or h > 65.34):
                hidden.append(face)
            elif name.startswith("Star base ·") and h < 91 and math.hypot(x, y) < 6.60:
                hidden.append(face)
            elif "injection-moulded wheel" in name and (
                10.5 < abs(x) < 21.4 and radial > 25.7 or abs(x) < 20.4 and radial < 3.1
            ):
                hidden.append(face)
        bmesh.ops.delete(topology, geom=hidden, context="FACES")
        bmesh.ops.dissolve_limit(
            topology,
            angle_limit=math.radians(0.50),
            verts=list(topology.verts),
            edges=list(topology.edges),
            delimit={"UV"},
        )
        topology.to_mesh(obj.data)
        topology.free()
    combined = runpy.run_path(str(scripts / "product_solids.py"))["combine"]
    merged = combined("C7 · installed wheelset", list(root.children))
    merged.parent = root
    path = project / "public/media/models/aeron-c7.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_animations=False,
        export_extras=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(path)], check=True
    )


def fit(atelier):
    mounts = [o for o in bpy.context.scene.objects if o.get("product") == "aeron-c7"]
    if sorted(o.get("casterNumber") for o in mounts) != [1, 2, 3, 4, 5]:
        raise ValueError("Expected five installed Aeron C7 swivel sockets")
    with bpy.data.libraries.load(
        str(atelier / "aeron-c7/c7-caster.blend"), link=False
    ) as (data, loaded):
        loaded.objects = [
            n for n in data.objects if not n.startswith("Herman Miller C7")
        ]
    parts = [o for o in loaded.objects if o.get("casterPart")]
    if len(parts) != 10:
        raise ValueError("Incomplete C7 caster assembly")
    for mount in mounts:
        old = list(mount.children_recursive)
        occludes = any(o.get("studioOccluder") for o in old)
        for o in old[::-1]:
            bpy.data.objects.remove(o, do_unlink=True)
        for part in parts:
            item = part.copy()
            item.name = f"C7 {mount['casterNumber']} · {part['casterPart']}"
            mount.users_collection[0].objects.link(item)
            item.parent = mount
            item.matrix_basis = part.matrix_basis.copy()
            item["studioOccluder"] = bool(occludes)
    for part in parts:
        bpy.data.objects.remove(part, do_unlink=True)


if __name__ == "__main__":
    build()
