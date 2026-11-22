import itertools
import math
import runpy
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, geometry

NAME = "NIKKOR Z 100-400mm f4.5-5.6 VR S"
AUTHORING = Path(__file__).resolve().parents[2] / ".references/05-摄影与陈列/相机与镜头/NIKKOR Z 100-400mm f4.5-5.6 VR S/Blender"
SCALE = 222 / (977 - 7)
PROFILE = (
    (0, 30),
    (1.5, 32),
    (3.3, 34.7),
    (4.3, 34.9),
    (21, 34.9),
    (22.6, 35.15),
    (31.4, 36.6),
    (33.5, 37.1),
    (39.4, 40.5),
    (63, 40.5),
    (65.7, 40.7),
    (68.8, 43.2),
    (71, 43.5),
    (77.8, 43.5),
    (79.2, 43.25),
    (97.5, 43.25),
    (100.5, 44.5),
    (104.8, 46.1),
    (122.2, 46.1),
    (124.1, 45.8),
    (141.1, 45.8),
    (143.1, 46.5),
    (146, 46.85),
    (151.5, 47.65),
    (196.5, 47.65),
    (198, 47.0),
    (199.2, 46.3),
    (204.9, 46.3),
    (206.2, 44.2),
    (207.8, 44.1),
    (208.6, 45.2),
    (212.4, 45.2),
    (213.2, 43.3),
    (216.5, 43.3),
    (217.2, 42.9),
    (220.8, 42.55),
    (222, 42.15),
)

SECTION = (
    (151, ((22, 25, 28), (36, 33, 30)), ("Optical glass",)),
    (150, ((40, 46, 54), (56, 56, 56)), ("Super ED",)),
    (
        111,
        ((66, 76, 88), (95, 94.5, 93), (98.7, 109.5, 121.9)),
        ("ED", "Optical glass"),
    ),
    (103, ((108, 118, 129.7), (137, 136, 134)), ("Super ED",)),
    (
        85,
        ((146, 148, 151.5), (170.5, 165, 159), (175.6, 183.5, 190.8)),
        ("Optical glass", "ED"),
    ),
    (
        70,
        ((202.6, 199.8, 196.8), (206.5, 212, 217.5), (220.4, 221.5, 222.8)),
        ("Optical glass", "Optical glass"),
    ),
    (66, ((236.8, 232.8, 228.8), (239.4, 240.4, 241.3)), ("Optical glass",)),
    (74, ((430, 432, 434.5), (441, 440, 437.8)), ("ED",)),
    (74, ((445, 449, 454.5), (458, 458, 458)), ("ED",)),
    (71, ((463, 469, 475.4), (479, 479, 479)), ("ED",)),
    (68, ((492.6, 489.8, 486.5), (497.7, 497.7, 497.7)), ("Optical glass",)),
    (61, ((563, 562, 559.8), (570, 567.5, 564.3)), ("Optical glass",)),
    (58, ((576, 577, 578.6), (579, 584.2, 590.5)), ("Optical glass",)),
    (
        58,
        ((594, 597, 600.3), (614.5, 610.5, 605.5), (619.5, 617.5, 614.5)),
        ("Optical glass", "Optical glass"),
    ),
    (56, ((625, 629, 634.4), (637, 638, 639)), ("Optical glass",)),
    (
        49,
        ((654, 655, 656.4), (662.5, 661.5, 660.5), (665.6, 669.5, 671.5)),
        ("Optical glass", "Optical glass"),
    ),
    (51, ((731, 731, 731), (739, 736.4, 734)), ("Optical glass",)),
    (50, ((752, 749, 746), (754.7, 754.7, 754.7)), ("Optical glass",)),
    (59, ((873.8, 873.8, 872.8), (876.6, 880.5, 885.2)), ("ED",)),
    (59, ((885, 889, 893.2), (907.7, 907.7, 907.7)), ("Optical glass",)),
)


def radius(z):
    for (z0, r0), (z1, r1) in itertools.pairwise(PROFILE):
        if z <= z1:
            return r0 + (r1 - r0) * max(0, (z - z0) / (z1 - z0))
    return PROFILE[-1][1]


def surface(r, samples):
    center, middle, edge = samples
    mid = 0.68**2
    quartic = ((middle - center) - (edge - center) * mid) / (mid * (mid - 1))
    quadratic = edge - center - quartic
    return [
        ((977 - center - quadratic * t * t - quartic * t**4) * SCALE, r * t * SCALE)
        for t in (i / 20 for i in range(21))
    ]


def tripod(part, shell, metal, rubber, bright, standard):
    ring = part("Rotating tripod ring and bayonet clamp", "Tripod collar")
    ring.turn(
        [
            (33.7, 36.9),
            (34.0, 37.65),
            (39.5, 41.15),
            (62.4, 41.15),
            (63.8, 41.0),
            (65.5, 40.65),
            (66.0, 40.0),
        ],
        shell,
        128,
    )
    leg = part("Curved cast removable tripod-foot neck", "Tripod collar")
    outline = [
        (36.2, -31),
        (66.0, -31),
        (65.5, -44.5),
        (65.9, -52),
        (66.7, -57.8),
        (67.9, -62.4),
        (69.5, -65.0),
        (71.7, -67.2),
        (74.0, -68.1),
        (78.0, -68.8),
        (120.9, -69.4),
        (122.5, -70.2),
        (121.0, -71.4),
        (58.3, -71.4),
        (55.4, -69.5),
        (36.9, -42),
    ]
    walls = [
        [(sx * 10.3, 65 + (z - 65) * scale, d * scale - 1.5) for z, d in outline]
        for sx, scale in ((-1, 0.985), (-0.93, 1), (0.93, 1), (1, 0.985))
    ]
    leg.rings(walls, shell, False)
    sole = part("Removable foot sole with two quarter-inch sockets", "Tripod collar")
    center = 91.8

    def sole_face(width, length, d):
        p = []
        corner = 3.6
        for j, (sx, sz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            for k in range(7):
                a = (j + k / 6) * math.pi / 2
                p.append(
                    (
                        sx * (width / 2 - corner) + corner * math.cos(a),
                        center + sz * (length / 2 - corner) + corner * math.sin(a),
                        d,
                    )
                )
        return p

    faces = [
        sole_face(w, l, d)
        for w, l, d in (
            (26.4, 63.3, -70.8),
            (29.3, 64.8, -71.4),
            (29.3, 64.8, -74.4),
            (27.1, 62.8, -75.3),
        )
    ]
    sole.rings(faces, metal, False, False)
    sockets = (82.5, 111.5)
    bores = [standard["screw_circle"](3.18, 0, center_z, 48) for center_z in sockets]
    for row in (faces[0], faces[-1]):
        loops = [[Vector((x, z)) for x, z, d in row]]
        loops.extend([Vector(p) for p in bore] for bore in bores)
        pts, edges = [], []
        for loop in loops:
            first = len(pts)
            pts.extend(loop)
            edges.extend(
                (first + i, first + (i + 1) % len(loop)) for i in range(len(loop))
            )
        vs, _, tris, _, _, _ = geometry.delaunay_2d_cdt(pts, edges, [], 0, 1e-6)
        kept = []
        for tri in tris:
            midpoint = sum((vs[i] for i in tri), Vector((0, 0))) / 3
            if all((midpoint - Vector((0, z))).length > 3.17 for z in sockets):
                kept.append(tri)
        sole.add([(p.x, p.y, row[0][2]) for p in vs], kept, metal, False)
    for center_z, bore in zip(sockets, bores):
        sole.rings(
            [[(x, z, d) for x, z in bore] for d in (-75.3, -70.8)], bright, True, False
        )
        thread = [
            [
                (
                    r * math.cos(i * math.tau / 32),
                    center_z + r * math.sin(i * math.tau / 32),
                    -75.0 + i / 32 * 1.27 + dh,
                )
                for r, dh in ((3.2, -0.32), (2.71, -0.03), (2.71, 0.03), (3.2, 0.32))
            ]
            for i in range(97)
        ]
        sole.rings(thread, bright, True, False)
    knob = part("Tripod collar-ring and removable-foot locking screws", "Tripod collar")
    for base, direction, knob_radius in (
        ((-29.5, 50.2, -26.6), (-0.86, 0, -0.51), 10.45),
        ((7.9, 53.5, -46.3), (1.0, 0, 0), 6.75),
    ):
        axis = Vector(direction).normalized()
        v = Vector((0, 1, 0))
        u = axis.cross(v)
        origin = Vector(base)
        rows = []
        for r, offset, rib in (
            (knob_radius * 0.66, -1.1, 0),
            (knob_radius * 0.68, 1.4, 0),
            (knob_radius * 0.91, 2.4, 0),
            (knob_radius, 3.1, 0.12),
            (knob_radius, 7.2, 0.12),
            (knob_radius * 0.94, 7.8, 0),
            (knob_radius * 0.82, 8.0, 0),
        ):
            rows.append(
                [
                    tuple(
                        origin
                        + axis * offset
                        + (r + (rib if i % 3 == 1 else 0))
                        * (
                            u * math.cos(i * math.tau / 120)
                            + v * math.sin(i * math.tau / 120)
                        )
                    )
                    for i in range(120)
                ]
            )
        knob.rings(rows, metal)
    latch = part("Tripod-foot release and spring return", "Tripod collar")
    latch.loft(
        [(0, 64, -49, 5.2, 3.0), (0, 66, -49, 5.3, 3.1), (0, 67, -49, 4.8, 2.8)],
        rubber,
        24,
        0.48,
    )


def build(Sculpture, make, controls, standard, bases):
    directory = Path(__file__).resolve().parent
    optic = runpy.run_path(str(directory / "nikkor-fast-normal.py"))
    sculpt = runpy.run_path(str(directory / "nikkor-plena.py"))
    mats = bpy.data.materials
    shell = mats["NIKKOR barrel · black powder coat"].copy()
    shell.name = "100-400 S · fine-grained fixed barrel"
    bump = next((n for n in shell.node_tree.nodes if n.type == "NORMAL_MAP"), None)
    if bump:
        bump.inputs["Strength"].default_value = 0.095
    metal = mats["Lens mount collar · anodized"]
    grip = mats["Focus ring · charcoal elastomer"]
    rubber = mats["Gasket · carbon black"]
    ink = mats["Nikon white silk print"]
    gray = mats["Nikon front collar engraving"]
    display = make("100-400 S · inactive OLED glass", "17151e", 0.15, 0.2, 0.32)
    bright = make("100-400 S · nickel-plated bayonet", "c5c6c6", 0.84, 0.23)
    gold = make("100-400 S · gold contact pads", "c3a369", 0.78, 0.26)
    flock = make("Optical cell · 100-400 S light trap", "171a1c", 0.12, 0.77)
    blade = make("Graphite diaphragm · 100-400 rounded leaves", "262829", 0.10, 0.58)
    substrate = make("100-400 S · optical glass", "f7fbfa", 0, 0.012)
    shader = substrate.node_tree.nodes["Principled BSDF"]
    shader.inputs["IOR"].default_value = 1.55
    shader.inputs["Transmission Weight"].default_value = 1
    coatings = []
    for layer, base in zip(("outer", "inner", "relay", "field"), bases):
        coating = base.copy()
        coating.name = "NIKKOR glass / 100-400 S / " + layer
        coatings.append(coating)
    scene = bpy.data.scenes.new(NAME)
    scene.unit_settings.system = "METRIC"
    scene.cycles.max_bounces = 60
    scene.cycles.transmission_bounces = 54
    master = bpy.data.collections.new(NAME)
    scene.collection.children.link(master)
    groups, pieces = {}, []
    runtime = Sculpture(NAME)

    def part(name, group, live=True):
        if group not in groups:
            groups[group] = bpy.data.collections.new(group)
            master.children.link(groups[group])
        shape = Sculpture(name)
        pieces.append((shape, group, live))
        return shape

    def point(a, z, lift=0):
        return controls["polar"](radius(z) + lift, z, a)

    def mark(shape, text, z, az, size, side=False, material=ink, lift=0.28):
        def project(x, y):
            return (
                point(az + y / radius(z), z - x, lift)
                if side
                else point(az + x / radius(z), z + y, lift)
            )

        shape.label(text, size, project, material)

    barrel = part("Retracted inner barrel and indexed fixed sleeves", "Fixed barrel")
    display_fit = (88.7, 25.4, 14.0)
    controls["windowed_barrel"](barrel, PROFILE, radius, *display_fit, shell, 144)
    barrel.turn(
        [(1.2, 32), (2.0, 34.0), (3.4, 35.18), (21.1, 35.18), (21.6, 34.95)], metal, 128
    )
    for z in (23.3, 67.8, 78.8, 101.7, 123.6, 143.15, 149.7, 198.4, 207.4, 216.8):
        r = radius(z)
        barrel.turn(
            [
                (z - 0.22, r),
                (z, r + 0.12),
                (z + 0.23, r + 0.10),
                (z + 0.35, radius(z + 0.35)),
            ],
            metal,
            112,
        )
    lettering = part("Printed nameplate, focal-length scale and hood index", "Markings")
    mark(lettering, "NIKKOR", 14.25, 0, 2.65, lift=0.47)
    mark(lettering, "100-400/4.5-5.6 S", 9.95, 0, 4.0, lift=0.48)
    controls["dot"](lettering, point, 0, 4.8, 1.02, ink)
    for a in (0, math.pi / 2, -math.pi / 2, math.pi):
        controls["dot"](lettering, point, a, 67.15, 0.39, ink)
    controls["dot"](lettering, point, 0, 69.48, 0.41, ink)
    mark(
        lettering,
        "NIKKOR Z 100-400mm 1:4.5-5.6 VR S  ø77",
        203.0,
        0,
        2.35,
        material=gray,
    )
    controls["dot"](lettering, point, 0, 212.9, 0.47, ink)
    for az, focal in ((0, 100), (-0.37, 135), (-0.80, 200), (-1.19, 300), (-1.43, 400)):
        mark(lettering, str(focal), 147.1, az, 2.7)
    controls["dot"](lettering, point, 0, 142.9, 0.43, ink)
    for title, lo, hi, r, n, relief in (
        ("Wide zoom grip with axial rubber flutes", 151.3, 196.5, 47.74, 130, 1.18),
        ("Manual focus ring with straight ribs", 104.9, 122.1, 46.16, 146, 0.60),
    ):
        ring = part(title, "Operating rings", False)
        sculpt["axial_ribs"](ring, lo, hi, r, n, relief, grip)
        optic["web_grip"](runtime, r, lo, hi, n, relief, grip)
    control_ring = part("Diamond-knurled assignable control ring", "Operating rings")
    standard["control_knurl"](
        control_ring, 43.53, 71.4, 77.75, grip, metal, rows=6, columns=152, peak=0.37
    )
    panel = part(
        "OLED information window, polarizer and display button",
        "Switches and indicators",
    )
    controls["recessed_display"](panel, radius, *display_fit, 20.2, 9.6, shell, metal, display)
    controls["button"](panel, radius, 88.7, -0.52, 4.12, 1.17, metal, grip)
    mark(panel, "DISP", 88.7, -0.40, 2.05, True)
    for i, a in enumerate((0, -math.pi / 2, math.pi, math.pi / 2)):
        key = part(f"L-Fn2 rubber function key {i + 1}", "Switches and indicators")
        sculpt["function_button"](key, radius, point, 133.55, a, metal, rubber, grip)
    key = part("L-Fn rubber key and S-Line badge", "Switches and indicators")
    sculpt["function_button"](
        key, radius, point, 88.7, -math.pi / 2, metal, rubber, grip
    )
    for z, title in ((88.7, "L-Fn"), (133.55, "L-Fn2")):
        mark(key, title, z, -1.385, 2.35, True)
    mark(key, "NIKKOR", 133.55, -0.985, 2.15, True)
    sculpt["s_emblem"](key, point, radius, 133.55, -1.145, metal, gray)
    switches = part(
        "A/M focus and full or three-metre limit sliders", "Switches and indicators"
    )
    for az, left, right in ((-1.23, "A", "M"), (-1.92, "FULL", "∞–3m")):
        z = 11.6
        controls["panel"](switches, radius, z, az, 4.65, 12.35, 0.72, metal)
        controls["panel"](switches, radius, z + 1.65, az, 3.72, 6.53, 1.28, grip)
        for shift in (-0.7, 0, 0.7):
            controls["panel"](
                switches, radius, z + 1.8 + shift, az, 2.95, 0.26, 1.43, rubber
            )
        for dz, txt in ((3.72, left), (-3.72, right)):
            mark(switches, txt, z + dz, az + 0.145, 2.02, True, lift=0.46)
    tripod(part, shell, metal, rubber, bright, standard)
    nose = part("M77 × 0.75 internal thread and HB-103 bayonet", "Optical cells")
    nose.turn(
        [
            (217.3, 42.9),
            (220.8, 42.55),
            (222, 42.15),
            (222, 38.60),
            (221.58, 38.32),
            (217.25, 38.32),
            (216.68, 37.7),
            (216.68, 36.1),
            (215.94, 35.3),
            (215.94, 34.4),
        ],
        metal,
        144,
    )
    optic["filter_thread"](nose, rubber, 38.35, 221.45)
    for rr in (35.1, 35.45, 35.8, 36.15):
        nose.turn([(216.55, rr + 0.13), (216.7, rr), (216.55, rr - 0.12)], flock, 112)
    for angle in (10, 100, 190, 280):
        standard["arc_section"](
            nose,
            [(42.9, 215.0), (43.72, 214.8), (43.79, 213.5), (43.15, 213.3)],
            angle,
            angle + 38,
            metal,
        )
    mount = part("Z-mount bayonet, screws, seal and eleven contact lands", "Mount")
    standard["mount"](mount, bright, rubber, metal, gold)
    rear = part("Rear shield and stepped light trap", "Optical cells")
    rear.turn(
        [
            (-2.5, 22.9),
            (-2.5, 21.8),
            (-1.3, 21.1),
            (2.6, 19.1),
            (12.3, 15.4),
            (15.8, 13.5),
        ],
        flock,
        112,
    )
    elements = "Optical elements · 25 in 20 groups"
    housings = part("Anodized spacers and blackened element seats", "Optical cells")
    shell_profile = [(215.94, 34.4)]
    for group, (rim, samples, types) in enumerate(SECTION, 1):
        faces = [surface(rim, s) for s in samples]
        for index, material in enumerate(types):
            glass = part(f"G{group:02} E{index + 1} · {material}", elements, False)
            first, last = faces[index : index + 2]
            optic["optical_face"](glass, first, substrate, True, 64)
            optic["optical_face"](glass, last, substrate, False, 64)
            glass.turn([last[-1], first[-1]], flock, 64)
        shell_profile.extend((faces[0][-1], faces[-1][-1]))
        if group in (1, 3, 8, 20):
            side = faces[-1] if group == 20 else faces[0]
            optic["optical_face"](
                runtime,
                side[::2],
                coatings[(1, 3, 8, 20).index(group)],
                group != 20,
                80,
            )
    shell_profile.append((15.8, 13.5))
    housings.turn(shell_profile, flock, 96)
    for a, b in itertools.pairwise(shell_profile):
        if a[0] - b[0] < 5:
            continue
        for k in range(1, 6):
            z = a[0] + (b[0] - a[0]) * k / 6
            r = a[1] + (b[1] - a[1]) * k / 6
            housings.turn(
                [(z + 0.15, r + 0.05), (z, r - 0.19), (z - 0.15, r + 0.05)], flock, 64
            )
    iris = part("Nine overlapping rounded diaphragm leaves", "Optical cells")
    controls["diaphragm"](iris, 9, 102.0, 14.9, 9.85, blade, metal)
    pupil = make("Z100-400 entrance pupil · relayed light", "15191b", 0, 0.48)
    window = [standard["radial"](9.90, 101.84, i * math.tau / 96) for i in range(96)]
    runtime.add(window, [tuple(range(96))], pupil, False)
    scene["source"] = (
        "https://imaging.nikon.com/imaging/lineup/lens/z-mount/z_100-400mmf45-56_vr_s/"
    )
    scene["configuration"] = (
        "Retracted 100 mm; removable tripod foot attached; rear cap supplied by cabinet"
    )
    scene["opticalConstruction"] = (
        "25 elements in 20 groups; six ED, two Super ED; nine rounded diaphragm blades"
    )
    scene["filterThread"] = "M77 × 0.75"
    scene["flangeToFrontMm"] = 222
    installed = []
    for shape, group, visible in pieces:
        obj = shape.finalize(uv_scale=46, uv_materials=(shell, grip, metal))
        if group == elements:
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            bmesh.ops.remove_doubles(mesh, verts=mesh.verts, dist=1e-8)
            bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
            if (
                not all(e.is_manifold for e in mesh.edges)
                or mesh.calc_volume(signed=True) <= 0
            ):
                raise ValueError("Open optical element: " + shape.name)
            mesh.to_mesh(obj.data)
            mesh.free()
        bpy.context.collection.objects.unlink(obj)
        groups[group].objects.link(obj)
        installed.append(obj)
        if visible:
            standard["merge"](shape, runtime, None)
    AUTHORING.mkdir(exist_ok=True, parents=True)
    bpy.data.libraries.write(
        str(AUTHORING / "nikkor-z100-400-s.blend"), {scene}, compress=True
    )
    for obj in installed:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    bpy.data.scenes.remove(scene)
    for group in [*groups.values(), master]:
        bpy.data.collections.remove(group)
    obj = runtime.finalize(uv_scale=46, uv_materials=(shell, grip, metal))
    obj["opticalVariant"] = 5
    return obj
