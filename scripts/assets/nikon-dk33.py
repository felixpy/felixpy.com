import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector


assets = Path(__file__).resolve().parent
repo = assets.parents[1]
sys.path.insert(0, str(assets))
from product_solids import combine, corners, edge, mesh, pin, subtract

finish = runpy.run_path(str(assets / "vitrine-sculpt.py"))["finish"]
source = (
    repo
    / ".references/05-摄影与陈列/相机与镜头/Nikon DK-33 eyecup/Blender/nikon-dk33.blend"
)
web = repo / "public/media/models/nikon-dk33.glb"


def outline_solid(name, outline, back, face, mat):
    n = len(outline)
    vertices = [(x, y, -d) for d in (back, face) for x, y in outline]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    faces += [(i, i + n, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    return mesh(name, vertices, faces, mat)


def rim(name, sections, mat, notch=False):
    n = 128
    vertices = []
    for radius, depth, relief in sections:
        for i in range(n):
            a = i * math.tau / n
            x, y = radius * math.sin(a), radius * math.cos(a)
            if notch and y > 0:
                factor = min(1, max(0, (4.35 - abs(x)) / 0.45))
                y += relief * factor * factor * (3 - 2 * factor)
            vertices.append((x, y, -depth))
    faces = [
        (
            j * n + i,
            j * n + (i + 1) % n,
            (j + 1) % len(sections) * n + (i + 1) % n,
            (j + 1) % len(sections) * n + i,
        )
        for j in range(len(sections))
        for i in range(n)
    ]
    obj = mesh(name, vertices, faces, mat)
    for f in obj.data.polygons:
        f.use_smooth = True
    return obj


def round_pin(name, x, y, near, far, r, mat):
    return pin(name, (x, y, -near), (x, y, -far), r, mat, 64)


def place(obj, col):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def build():
    scene = bpy.context.scene
    assembly = bpy.data.collections.new("DK-33 installed eyepiece")
    scene.collection.children.link(assembly)
    fixed = bpy.data.collections.new("Z8 ocular and fixed fittings")
    removable = bpy.data.collections.new("DK-33 removable eyecup")
    for col in (fixed, removable):
        assembly.children.link(col)
    rubber = finish("DK-33 charcoal soft elastomer", "272727", 0, 0.73)
    casing = finish("Z8 molded graphite", "252627", 0.01, 0.58)
    resin = finish("DK-33 black moulded insert", "1c1c1e", 0, 0.4)
    metal = finish("Z8 black phosphate steel", "383839", 0.46, 0.42)
    deep = finish("Ocular light trap", "0c0c0d", 0, 0.9)
    optical = finish("EVF smoke-amber ocular glass", "302b1b", 0.25, 0.105)
    sensor_mat = finish("Viewfinder proximity sensor window", "17191b", 0.18, 0.20)
    plate_outline = [
        (x * (1 - 0.12 * (y + 20) / 40), y - 1.65)
        for x, y in corners(46, 41.4, 5.8, 10)
    ]
    plate = outline_solid(
        "Weather-sealed eyepiece carrier", plate_outline, -2.9, 3.2, casing
    )
    screws = [(14.55, 14.3), (-14.55, 14.3)]
    bx, by = 15.08, -14.48
    cuts = [round_pin("Finder bore", 0, 0, -4, 5, 14.7, deep)]
    for x, y in screws:
        cuts.append(round_pin("Screw counterbore", x, y, 0, 4, 1.77, deep))
    cuts.append(round_pin("Release button well", bx, by, -4, 4, 3.43, deep))
    subtract(plate, cuts)
    place(edge(plate, 0.36, 3), fixed)
    rolled = [
        (15.48, 4.45),
        (16.83, 4.05),
        (17.55, 4.3),
        (18.03, 4.98),
        (18.24, 5.94),
        (18.21, 7.1),
        (17.99, 8.12),
        (17.52, 8.9),
        (16.81, 9.32),
        (16.24, 9.39),
        (15.78, 9.24),
        (15.42, 8.74),
        (15.16, 7.52),
        (15.03, 6.34),
        (15.17, 5.09),
    ]
    place(
        rim(
            "DK-33 rolled elastomer eye contact rim",
            [(r, d, 0) for r, d in rolled],
            rubber,
        ),
        removable,
    )
    insert = [
        (15.67, 4.6, 0),
        (15.61, 7.98, 0),
        (15.33, 8.38, 0),
        (14.25, 8.05, 0),
        (13.18, 7.56, 0),
        (12.24, 7.2, 0.33),
        (10.39, 6.52, 2.82),
        (10.21, 6.25, 2.97),
        (10.27, 3.48, 2.83),
        (10.65, 3.29, 2.67),
        (14.75, 3.29, 0),
    ]
    place(
        rim("DK-33 keyed polymer insert and sensor clearance", insert, resin, True),
        removable,
    )
    bracket = rim(
        "Eyepiece receiver and ocular aperture",
        [
            (16.25, 2.85, 0),
            (16.25, 3.47, 0),
            (15.9, 4.16, 0),
            (15.26, 4.22, 0),
            (14.9, 3.22, 0),
            (10.43, 2.7, 2.6),
            (9.89, 2.91, 2.97),
            (9.82, 0.88, 3.02),
            (14.08, 0.57, 0),
            (14.62, 1.23, 0),
            (14.62, 2.8, 0),
        ],
        metal,
        True,
    )
    place(bracket, fixed)
    recess = outline_solid(
        "Ocular recess with clear sensor seat",
        corners(25.5, 30, 5.25, 10),
        -1.7,
        1.7,
        deep,
    )
    aperture = corners(17.45, 13.36, 2.46, 10)
    subtract(recess, [outline_solid("Rounded optical mouth", aperture, -3, 3, casing)])
    place(edge(recess, 0.11, 2), fixed)
    n = len(aperture)
    nodes = [(0, 0, -1.69)]
    for scale in (0.30, 0.6, 0.84, 1, 1):
        depth = 1.69 - 0.57 * scale * scale
        if len(nodes) > 1 + 3 * n and scale == 1:
            depth = -0.38
        nodes += [(x * scale, y * scale, -depth) for x, y in aperture]
    faces = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    for j in range(4):
        faces += [
            (
                1 + j * n + i,
                1 + j * n + (i + 1) % n,
                1 + (j + 1) * n + (i + 1) % n,
                1 + (j + 1) * n + i,
            )
            for i in range(n)
        ]
    faces.append(tuple(1 + 4 * n + i for i in range(n)))
    glass = mesh(
        "Coated rectangular ocular with curved front surface", nodes, faces, optical
    )
    for f in glass.data.polygons:
        f.use_smooth = len(f.vertices) < 5
    place(glass, fixed)
    window = [(x, y + 11.11) for x, y in corners(6.25, 3.5, 0.72, 8)]
    place(
        edge(
            outline_solid("Eye proximity sensor lens", window, 1.32, 2.02, sensor_mat),
            0.16,
        ),
        fixed,
    )
    cross = [
        (-0.17, -0.97),
        (0.17, -0.97),
        (0.17, -0.17),
        (0.97, -0.17),
        (0.97, 0.17),
        (0.17, 0.17),
        (0.17, 0.97),
        (-0.17, 0.97),
        (-0.17, 0.17),
        (-0.97, 0.17),
        (-0.97, -0.17),
        (-0.17, -0.17),
    ]
    heads = []
    for x, y in screws:
        head = edge(
            round_pin("Recessed cross head", x, y, 0.65, 2.93, 1.54, metal), 0.17, 3
        )
        subtract(
            head,
            [
                outline_solid(
                    "Driver recess",
                    [(x + dx, y + dy) for dx, dy in cross],
                    2.43,
                    3.38,
                    deep,
                )
            ],
        )
        heads.append(head)
    place(combine("Two recessed black cross-head fixings", heads), fixed)
    release = rim(
        "Eyepiece release button surround",
        [
            (3.44, 1.7, 0),
            (3.44, 3.08, 0),
            (3.13, 3.65, 0),
            (2.69, 3.92, 0),
            (2.46, 3.55, 0),
            (2.47, 1.7, 0),
        ],
        resin,
    )
    release.location = (bx / 1000, 0, by / 1000)
    place(release, fixed)
    place(
        edge(
            round_pin("Eyepiece release plunger", bx, by, 1.65, 4.24, 2.37, rubber),
            0.46,
            5,
        ),
        fixed,
    )
    scene.unit_settings.system = "METRIC"
    scene["sources"] = (
        "Nikon DK-33 product photograph, Z8 rear view, Nikon Z8 Reference Guide: viewfinder eyepiece accessories"
    )
    scene["scale"] = (
        "Exterior and seating depths reconstructed from photographs; exposed rim diameter 36.48 mm"
    )
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_distance = 0.094
            view.region_3d.view_rotation = Vector((0.14, 0.94, 0.20)).to_track_quat(
                "Z", "Y"
            )
            view.clip_start = 0.0001
            view.overlay.show_floor = False
            view.shading.color_type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=str(web),
        export_format="GLB",
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
