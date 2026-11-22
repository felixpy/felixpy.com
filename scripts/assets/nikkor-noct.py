import math
import subprocess
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import interpolate_bezier


project = Path(__file__).resolve().parents[2]
source = (
    project
    / ".references/05-摄影与陈列/相机与镜头/NIKKOR Z 58mm f0.95 S Noct/Blender/nikkor-z58-noct.blend"
)
name = "NIKKOR Z 58mm f0.95 S Noct"
profile = [
    (0, 30),
    (1.4, 33.0),
    (3.0, 34.9),
    (17.9, 34.9),
    (18.9, 35.8),
    (22.5, 35.8),
    (23.1, 35.2),
    (29.8, 35.2),
    (31.1, 35.8),
    (33.7, 35.8),
    (36.6, 37.4),
    (40.9, 41.3),
    (44.5, 45.9),
    (46.6, 46.6),
    (56.4, 46.6),
    (57.3, 46.1),
    (58.0, 46.4),
    (75.5, 46.4),
    (77.4, 47.1),
    (79.2, 47.6),
    (85.2, 49.4),
    (88.0, 50.4),
    (145.9, 50.4),
    (147.4, 50.97),
    (151.9, 51),
    (152.7, 50.8),
    (153, 50.4),
]
section = [
    (
        184,
        [(101, 108, 125), (143, 142, 140), (159, 175, 211)],
        ["aspherical", "cemented companion"],
    ),
    (
        185,
        [(263, 250, 220), (277, 278, 279), (329, 318, 287)],
        ["negative meniscus", "ED"],
    ),
    (197, [(333, 341, 366), (394, 388, 374)], ["biconvex"]),
    (184, [(397, 408, 442), (450, 450, 449)], ["ED"]),
    (
        172,
        [(453, 456, 462), (497, 490, 469), (513, 530, 553)],
        ["ED", "cemented companion"],
    ),
    (
        140,
        [(593, 588, 575), (605, 617, 652), (670, 668, 663)],
        ["negative meniscus", "ED"],
    ),
    (143, [(672, 680, 697), (725, 720, 706)], ["biconvex"]),
    (
        132,
        [(727, 730, 735), (768, 762, 744), (778, 784, 798)],
        ["aspherical", "cemented companion"],
    ),
    (
        111,
        [(795, 798, 811), (829, 826, 821), (840, 846, 865)],
        ["positive meniscus", "cemented companion"],
    ),
    (
        110,
        [(845, 850, 867), (896, 894, 888), (913, 918, 935)],
        ["positive meniscus", "aspherical"],
    ),
]


def fit_cabinet():
    scene = bpy.context.scene
    root = (
        scene.objects.get("NIKKOR_Z_58mm_f095_S_Noct")
        or scene.objects["NIKKOR_Z_50mm_f12_S"]
    )
    if root.instance_collection and root.instance_collection.name == name:
        return root
    holder = root.parent
    if not holder or "inspection" not in holder.name:
        raise ValueError("Noct must replace a cabinet inspection lens")
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (_, loaded):
        loaded.collections = [name]
    (installed,) = loaded.collections
    if (
        sum(
            1
            for p in installed.all_objects
            if p.name.startswith("G") and p.name[1:3].isdigit()
        )
        != 17
    ):
        raise ValueError("Incomplete Noct optical group")
    for child in reversed(root.children_recursive):
        bpy.data.objects.remove(child, do_unlink=True)
    root.name = "NIKKOR_Z_58mm_f095_S_Noct"
    root.instance_type = "COLLECTION"
    root.instance_collection = installed
    root["cabinetItem"] = name
    holder.name = "NIKKOR Z 58mm f/0.95 S Noct · inspection"
    for child in holder.children:
        if child.name.startswith("LF-N1"):
            child.name = "LF-N1 rear display cap · 58mm Noct"
    return root


def signature(shape, point, radius, gold):
    strokes = [
        [
            (81, 175),
            (91, 149),
            (104, 125),
            (114, 106),
            (120, 127),
            (125, 154),
            (132, 170),
            (145, 132),
            (158, 87),
            (176, 86),
        ],
        [
            (176, 139),
            (174, 123),
            (164, 131),
            (158, 141),
            (146, 167),
            (153, 180),
            (169, 163),
            (176, 153),
            (178, 144),
            (176, 139),
            (183, 145),
            (188, 143),
            (193, 140),
        ],
        [
            (207, 142),
            (206, 129),
            (200, 129),
            (194, 138),
            (179, 153),
            (182, 174),
            (198, 168),
            (211, 163),
            (221, 145),
            (228, 139),
        ],
        [
            (239, 109),
            (234, 124),
            (222, 149),
            (220, 161),
            (215, 182),
            (240, 166),
            (248, 151),
        ],
        [(213, 126), (224, 131), (233, 124), (248, 122)],
    ]
    for stroke in strokes:
        points = []
        for i in range(0, len(stroke) - 1, 3):
            points.extend(
                interpolate_bezier(
                    *[Vector((x, y, 0)) for x, y in stroke[i : i + 4]], 9
                )[:-1]
            )
        points.append(Vector((*stroke[-1], 0)))
        shape.pipe(
            [
                point(
                    0.62 + (x - 167) * 0.087 / radius(67), 67 + (143 - y) * 0.087, 0.17
                )
                for x, y, _ in points
            ],
            0.16,
            gold,
            8,
        )


def collar_foot(shape, mat, dark, metal, standard):
    shape.turn(
        [
            (44.5, 45.83),
            (45.4, 46.94),
            (46.2, 47.12),
            (56.5, 47.12),
            (57.22, 46.70),
            (57.36, 46.12),
        ],
        mat,
        136,
    )
    outline = [
        (31, -37.4),
        (43, -44.9),
        (49, -46.6),
        (53, -51.4),
        (57, -52.6),
        (80.2, -52.6),
        (83, -53.5),
        (84, -55.5),
        (83.9, -58.0),
        (82.2, -59.1),
        (54.5, -59.1),
        (52.2, -58.4),
        (40, -46.5),
        (33, -41.5),
    ]
    center = (55, -49)
    rows = [
        [
            (x, center[0] + (h - center[0]) * s, center[1] + (r - center[1]) * s)
            for h, r in outline
        ]
        for x, s in [(-11.0, 0.96), (-10.45, 1), (10.45, 1), (11, 0.96)]
    ]
    shape.rings(rows, mat, False)
    for x in [-7, 7]:
        shape.pipe([(x, 56.3, -59.2), (x, 80, -59.2)], 0.33, dark, 10)
    ring = []
    for i in range(65):
        a = math.tau * i / 64
        ring.append((3.04 * math.cos(a), 68 + 3.04 * math.sin(a), -59.19))
    shape.add(ring[:-1], [tuple(range(64))], dark, False)
    shape.pipe(ring, 0.29, metal, 7)
    a = -2.16

    def radial(r, u, v):
        return (
            math.sin(a) * r + math.cos(a) * u,
            50.8 + v,
            math.cos(a) * r - math.sin(a) * u,
        )

    rows = []
    for r, w, tooth in [
        (45.2, 6.5, 0),
        (49.5, 6.5, 0),
        (50.3, 9.9, 0),
        (51.2, 10.2, 0.34),
        (57.4, 10.2, 0.34),
        (58.4, 9.9, 0),
        (58.7, 8.9, 0),
    ]:
        row = []
        for i in range(120):
            t = math.tau * i / 120
            sz = w + (0 if i % 3 == 0 else tooth)
            row.append(radial(r, sz * math.cos(t), sz * math.sin(t)))
        rows.append(row)
    shape.rings(rows, dark, True)


def build(Sculpture, make, fittings, standard, prime, coating_bases):
    mats = bpy.data.materials
    shell = mats["NIKKOR barrel · black powder coat"]
    trim = mats["Lens mount collar · anodized"]
    rubber = mats["Focus ring · charcoal elastomer"]
    seal = mats["Gasket · carbon black"]
    ink = mats["Nikon white silk print"]
    oled = mats["Lens OLED · polarizing cover"]
    gold = make("Noct · gold scale and signature", "c8a656", 0.40, 0.39)
    steel = make("Noct Z bayonet · machined stainless", "cac9c6", 0.88, 0.22)
    flock = make("Optical flock · Noct bore", "141519", 0, 0.9)
    cell = make("Optical cell · Noct anodised spacers", "28282a", 0.20, 0.45)
    blade = make("Graphite diaphragm · Noct rounded leaves", "25252a", 0.14, 0.67)
    crystal = make("Noct · optical substrate", "fcfcfa", 0, 0.012)
    crystal.node_tree.nodes.get("Principled BSDF").inputs[
        "Transmission Weight"
    ].default_value = 1
    coats = []
    for label, base in zip(("outer", "inner", "relay", "field"), coating_bases):
        c = base.copy()
        c.name = "NIKKOR glass / 58 f0.95 Noct / " + label
        coats.append(c)
    scene = bpy.data.scenes.new(name)
    native = bpy.data.collections.new(name)
    scene.collection.children.link(native)
    assemblies = {}
    parts = []
    runtime = Sculpture(name)

    def part(label, role, visible=True):
        if role not in assemblies:
            assemblies[role] = bpy.data.collections.new(role)
            native.children.link(assemblies[role])
        shape = Sculpture(label)
        parts.append((shape, assemblies[role], visible))
        return shape

    def radius(z):
        for (a, x), (b, y) in zip(profile, profile[1:]):
            if z <= b:
                return x + max(0, min(1, (z - a) / (b - a))) * (y - x)
        return profile[-1][1]

    def point(angle, z, lift=0):
        return fittings["polar"](radius(z) + lift, z, angle)

    def label(shape, text, z, az, size, mat, relief=0.24):
        shape.label(
            text, size, lambda x, y: point(az + x / radius(z), z + y, relief), mat
        )

    body = part("Fixed Noct barrel and rib shoulders", "Barrel")
    display_fit = (67.36, 25.4, 14.0)
    fittings["windowed_barrel"](body, profile, radius, *display_fit, shell, 144)
    for z in (3.35, 18.43, 22.62, 30.46, 44.45, 57.52, 76.65, 85.79, 146.37):
        body.turn(
            [
                (z - 0.25, radius(z - 0.25)),
                (z - 0.09, radius(z - 0.09) + 0.15),
                (z + 0.12, radius(z + 0.12) + 0.15),
                (z + 0.23, radius(z + 0.23)),
            ],
            trim,
            128,
        )
    label(body, "58/0.95 S", 10.7, 0, 4.35, ink)
    fittings["dot"](body, point, 0, 3.82, 0.96, ink)
    controls = part(
        "Long-throw manual focus drum and assignable rear ring", "Manual focus"
    )
    prime["web_grip"](controls, 50.40, 87.90, 145.85, 192, 0.53, rubber)
    prime["web_grip"](controls, 35.24, 23.30, 29.75, 144, 0.39, rubber)
    display = part("OLED, DISP and L-Fn controls", "Controls and marks")
    fittings["recessed_display"](display, radius, *display_fit, 20.2, 9.6, shell, trim, oled)
    for a, size, caption in [(-0.66, 2.95, "DISP"), (-1.38, 4.45, "L-Fn")]:
        fittings["button"](display, radius, 67.35, a, size, 1.0, trim, rubber)
        label(display, caption, 71.3, a, 1.76, ink)
    for z in (57.6, 77.0):
        fittings["panel"](display, radius, z, 0, 0.92, 1.53, 0.36, ink)
    fittings["panel"](body, radius, 9.8, -1.51, 10.2, 11.7, 0.61, trim)
    label(body, "NIKKOR", 11.8, -1.51, 2.24, ink, 0.82)
    label(body, "S", 7.6, -1.51, 3.07, ink, 0.82)
    scale = part(
        "Engraved dual-unit distance scale and Noct signature", "Controls and marks"
    )
    for z, values, mat in [
        (
            81.18,
            [
                (0, "∞"),
                (0.35, "5"),
                (0.67, "3"),
                (0.92, "2"),
                (1.18, "1.5"),
                (1.55, "1"),
                (2.04, "0.8"),
                (2.52, "0.7"),
                (3.02, "0.6"),
                (-2.42, "0.5"),
                (-0.36, "m"),
            ],
            ink,
        ),
        (
            84.56,
            [
                (0.37, "20"),
                (0.64, "10"),
                (0.97, "7"),
                (1.28, "5"),
                (1.74, "4"),
                (2.05, "3"),
                (2.74, "2.5"),
                (-1.79, "2"),
                (-0.40, "ft"),
            ],
            gold,
        ),
    ]:
        for a, v in values:
            label(scale, v, z, a, 2.5, mat)
    signature(scale, point, radius, gold)
    foot = part(
        "Captive rotating tripod collar, lock and integral foot", "Tripod collar"
    )
    collar_foot(foot, shell, trim, steel, standard)
    mount = part("Z bayonet with eleven contacts and four locking lugs", "Mount")
    standard["mount"](mount, steel, seal, trim, gold)
    rim = part("Front threaded filter ring and engraved name rim", "Barrel")
    rim.turn(
        [
            (151.50, 50.80),
            (152.73, 50.77),
            (153, 50.36),
            (153, 42.47),
            (152.7, 41.0),
            (151.9, 40.83),
            (147.47, 40.83),
            (146.87, 40.08),
            (146.55, 37.83),
            (145.67, 37.36),
            (145.34, 34.49),
            (144.24, 33.65),
        ],
        trim,
        144,
    )
    prime["filter_thread"](rim, seal, 40.8, 152.38)

    def rim_mark(text, angle, material, size):
        def pt(x, y):
            a = angle - x / 38.18
            return (math.sin(a) * (38.18 + y), 146.95, math.cos(a) * (38.18 + y))

        rim.label(text, size, pt, material)

    rim_mark("NIKKOR  Z  58mm  1:0.95  S", 0, ink, 1.92)
    rim_mark("Noct", 0.82, gold, 2.0)
    rim_mark("ø82", 3.03, ink, 1.90)
    optics = "Optical elements · 17 in 10 groups"
    chambers = part("Intergroup spacers and rear baffles", "Optical cells", False)
    bore = []
    for gi, (r, samples, tags) in enumerate(section):
        surfaces = [prime["face_profile"](r, s, 920, 153 / (920 - 54)) for s in samples]
        for ei, tag in enumerate(tags):
            p, q = surfaces[ei : ei + 2]
            element = part(f"G{gi + 1:02} E{ei + 1} · {tag}", optics, False)
            prime["optical_face"](element, p, crystal, True)
            prime["optical_face"](element, q, crystal, False)
            element.turn([q[-1], p[-1]], cell, 96)
        bore.extend((surfaces[0][-1], surfaces[-1][-1]))
        if gi in (0, 2, 5, 9):
            surf = surfaces[-1] if gi == 9 else surfaces[0]
            prime["optical_face"](
                runtime, surf[::2], coats[(0, 2, 5, 9).index(gi)], gi != 9, 88
            )
    chambers.turn(bore, flock, 112)
    runtime.turn(bore, flock, 96)
    diaphragm = part("Eleven curved electromagnetic diaphragm leaves", "Optical cells")
    fittings["diaphragm"](diaphragm, 11, 64.12, 30.93, 24.60, blade, trim)
    pupil = make("Z58 entrance pupil · Noct at infinity", "121716", 0, 0.5)
    for z, r in ((114.05, 58 / 0.95 / 2), (63.8, 24.65)):
        loop = [standard["radial"](r, z, math.tau * i / 112) for i in range(112)]
        runtime.add(loop, [tuple(range(112))], pupil, False)
    scene.unit_settings.system = "METRIC"
    scene["flangeToFrontMm"] = 153
    scene["maximumBarrelDiameterMm"] = 102
    scene["opticalConstruction"] = (
        "17 elements in 10 groups: four ED and three aspherical"
    )
    scene["reference"] = (
        "https://imaging.nikon.com/imaging/lineup/lens/z-mount/z_58mmf095s/index.html"
    )
    scene["presentation"] = (
        "Manual focus at infinity, 82 mm filter seat, 11 diaphragm blades"
    )
    scene["opticalLimits"] = (
        "Glass profiles trace the public section. Coating indices and concealed spacing are approximations."
    )
    objs = []
    for model, col, visible in parts:
        obj = model.finalize(uv_scale=46, uv_materials=(shell, trim, rubber))
        if col.name == optics:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-8)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            if not all(edge.is_manifold for edge in bm.edges):
                raise ValueError(f"Open surface in {model.name}")
            bm.to_mesh(obj.data)
            bm.free()
        bpy.context.collection.objects.unlink(obj)
        col.objects.link(obj)
        objs.append(obj)
        if visible:
            standard["merge"](model, runtime, None)
    scene.world = bpy.data.worlds.new("58 mm Noct optical inspection")
    source.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(source), {scene}, compress=True)
    subprocess.run(
        [
            bpy.app.binary_path,
            "-b",
            str(source),
            "--python-exit-code",
            "1",
            "-P",
            __file__,
        ],
        check=True,
    )
    for obj in objs:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    bpy.data.scenes.remove(scene)
    for col in [*assemblies.values(), native]:
        bpy.data.collections.remove(col)
    obj = runtime.finalize(uv_scale=46, uv_materials=(shell, trim, rubber))
    obj["opticalVariant"] = 4
    return obj


if __name__ == "__main__":
    scene = bpy.context.scene
    if scene.name != name or not bpy.data.collections.get(name):
        raise ValueError("Expected the assembled Noct optical workshop")
    scene.cycles.transmission_bounces = 40
    scene.cycles.max_bounces = 44
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_location = (0, 0, 0.074)
            view.region_3d.view_distance = 0.245
            view.region_3d.view_rotation = Vector((0.45, -0.89, 0.30)).to_track_quat(
                "Z", "Y"
            )
            view.clip_start = 0.00025
            view.overlay.show_floor = False
            view.shading.color_type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
