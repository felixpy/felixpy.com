import math
import subprocess
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


FLANGE_X = 968
SCALE = 150 / (FLANGE_X - 8)
SECTION = (
    (191, ((30, 32, 41), (43, 58, 106)), ("front meniscus",)),
    (176, ((69, 81, 121), (93, 103, 134)), ("negative meniscus",)),
    (176, ((202, 188, 140), (219, 215, 203)), ("inverted meniscus",)),
    (188, ((247, 239, 213), (287, 274, 230)), ("positive meniscus",)),
    (195, ((291, 298, 318), (357, 351, 330)), ("biconvex",)),
    (193, ((360, 370, 401), (399, 402, 410)), ("meniscus",)),
    (179, ((403, 416, 459), (466, 467, 470)), ("meniscus",)),
    (162, ((473, 475, 481), (510, 505, 492), (525, 537, 541)), ("ED", "cemented companion")),
    (119, ((697, 689, 666), (706, 702, 693)), ("negative meniscus",)),
    (120, ((709, 714, 729), (746, 746, 746)), ("ED",)),
    (119, ((762, 763, 765), (799, 797, 785)), ("aspherical",)),
    (121, ((820, 823, 826), (842, 841, 839)), ("aspherical",)),
    (128, ((856, 859, 866), (874, 874, 876)), ("meniscus",)),
    (128, ((877, 881, 892), (911, 909, 901), (920, 929, 951)), ("cemented front", "cemented rear")),
    (127, ((974, 969, 954), (983, 983, 985)), ("aspherical rear element",)),
)


def face_profile(radius, samples, flange=FLANGE_X, scale=SCALE):
    a, mid, edge = samples
    quadratic = (16 * (mid - a) - edge + a) / 3
    quartic = edge - a - quadratic
    return [
        ((flange - a - quadratic * t**2 - quartic * t**4) * scale, radius * t * scale)
        for t in (i / 20 for i in range(21))
    ]


def optical_face(shape, surface, material, front, segments=96):
    z, _ = surface[0]
    points = [(0, z, 0)]
    faces = []
    for j, (z, radius) in enumerate(surface[1:]):
        start = len(points)
        for i in range(segments):
            theta = i * math.tau / segments
            points.append((radius * math.sin(theta), z, radius * math.cos(theta)))
        for i in range(segments):
            a, b = start + i, start + (i + 1) % segments
            face = (0, a, b) if not j else (a - segments, a, b, b - segments)
            faces.append(face if front else tuple(reversed(face)))
    shape.add(points, faces, material)


def filter_thread(shape, material, bore=40.8, start=149.47):
    rows = []
    for step in range(4 * 112 + 1):
        t = step / 112
        angle = t * math.tau
        tip = bore - .02 - 0.30 * min(1, t * 4, (4 - t) * 4)
        rows.append([
            (r * math.sin(angle), start - t * .75 + h, r * math.cos(angle))
            for h, r in ((.19, bore + .04), (.033, tip), (-.033, tip), (-.19, bore + .04))
        ])
    shape.rings(rows, material, True, False)


def web_grip(shape, radius, start, end, count, lift, material):
    rows = []
    for z, relief in ((start - .2, 0), (start + .28, 1), (end - .28, 1), (end + .2, 0)):
        row = []
        for i in range(count):
            for fraction, tooth in ((0, 0), (.32, 1), (.72, 1)):
                a = (i + fraction) * math.tau / count
                r = radius + relief * (.07 + tooth * lift)
                row.append((r * math.sin(a), z, r * math.cos(a)))
        rows.append(row)
    shape.rings(rows, material, True, False)


def information_display(shape, radius, trim, glass, center_height=49.6):
    def ring(width, height, relief, curved=False):
        corners = []
        rounded = .78
        for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            for k in range(5):
                a = (i + k / 4) * math.pi / 2
                x = sx * (width / 2 - rounded) + rounded * math.cos(a)
                z = center_height + sy * (height / 2 - rounded) + rounded * math.sin(a)
                r = radius(z)
                y = (math.sqrt(r * r - x * x) if curved else r) + relief
                corners.append((x, z, y))
        return corners

    shape.rings([
        ring(25.4, 14.0, -.08, True),
        ring(25.0, 13.6, .46),
        ring(24.35, 13.0, .72),
        ring(20.7, 10.1, .72),
        ring(20.2, 9.6, .31),
    ], trim, False, False)
    face = ring(20.22, 9.62, .32)
    shape.add(face, [tuple(range(len(face)))], glass, False)


def build(spec, Sculpture, make, fittings, standard, sculpt, coating_bases):
    mats = bpy.data.materials
    shell = mats["NIKKOR barrel · black powder coat"].copy()
    shell.name = "50 S · stippled fixed housing"
    grain = next(node for node in shell.node_tree.nodes if node.type == "NORMAL_MAP")
    grain.inputs["Strength"].default_value = .077
    rubber = mats["Focus ring · charcoal elastomer"]
    trim = mats["Lens mount collar · anodized"]
    gasket = mats["Gasket · carbon black"]
    ink = mats["Nikon white silk print"]
    glass = mats["Lens OLED · polarizing cover"]
    flock = make("Optical flock · 50 S helicoid traps", "101315", 0, .93)
    cell = make("Optical cell · 50 S matte anodized bore", "232528", .24, .47)
    blade = make("Graphite diaphragm · 50 S rounded leaves", "252728", .15, .66)
    steel = make("50 S · machined stainless bayonet", "c5c4c2", .89, .22)
    gold = make("50 S · contact pad plating", "bd9d65", .78, .22)
    crystal = make("50 S · optical substrate", "fcfcfa", 0, .009)
    bsdf = crystal.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Transmission Weight"].default_value = 1
    bsdf.inputs["IOR"].default_value = 1.55
    coatings = []
    for name, base in zip(("outer", "inner", "relay", "field"), coating_bases):
        coating = base.copy()
        coating.name = "NIKKOR glass / 50 f1.2 S / " + name
        coatings.append(coating)

    scene = bpy.data.scenes.new(spec["name"])
    scene.unit_settings.system = "METRIC"
    scene.cycles.transmission_bounces = 40
    scene.cycles.max_bounces = 44
    components = bpy.data.collections.new(spec["name"])
    scene.collection.children.link(components)
    categories = {}
    parts = []
    runtime = Sculpture(spec["name"])

    def part(name, category, visible=True):
        if category not in categories:
            categories[category] = bpy.data.collections.new(category)
            components.children.link(categories[category])
        shape = Sculpture(name)
        parts.append((shape, categories[category], visible))
        return shape

    contour = spec["profile"]

    def radius(z):
        for (a, x), (b, y) in zip(contour, contour[1:]):
            if z <= b:
                return x + max(0, (z - a) / (b - a)) * (y - x)
        return contour[-1][1]

    def point(angle, z, lift):
        return fittings["polar"](radius(z) + lift, z, angle)

    def label(shape, text, z, angle, size, axial=False, relief=.22):
        def project(x, y):
            return point(angle + (y if axial else x) / radius(z), z + (-x if axial else y), relief)
        shape.label(text, size, project, ink)

    barrel = part("Fixed barrel, flared front housing and sealing shoulders", "Barrel")
    barrel.turn(contour, shell, 144)
    barrel.turn([(1.1, 31.5), (2.25, 33.7), (3.65, 35.03), (4.4, 35.02)], trim, 112)
    for z in (22.5, 32.4, 66.3, 117.4, 125.1, 139.1):
        r = radius(z)
        seam = [(z - .23, r), (z - .13, r + .10), (z + .10, r + .10), (z + .25, radius(z + .25))]
        barrel.turn(seam, trim, 112)
    rings = "Control rings and markings"
    control = part("Rear assignable control ring", rings, False)
    sculpt["axial_ribs"](control, 24.6, 31.6, 35.19, 148, .36, rubber)
    focus = part("Wide manual focus ring", rings, False)
    sculpt["axial_ribs"](focus, 69, 114.7, 43.5, 151, .67, rubber)
    nose = part("Fixed ribbed front grip with circumferential dividing groove", rings, False)
    sculpt["axial_ribs"](nose, 128.3, 137.1, 44.38, 141, .30, rubber, 132.7)
    for r, a, b, teeth, lift in (
        (35.19, 24.6, 31.6, 148, .36),
        (43.5, 69, 114.7, 151, .67),
        (44.38, 128.3, 132.38, 141, .3),
        (44.38, 133.02, 137.1, 141, .3),
    ):
        web_grip(runtime, r, a, b, teeth, lift, rubber)
    label(barrel, "50/1.2 S", 13.2, 0, 4.85)
    fittings["dot"](barrel, point, 0, 5.2, 1.16, ink)
    fittings["dot"](barrel, point, -.26, 125.3, .48, ink)
    controls = part("OLED window, DISP button and L-Fn pad", rings)
    information_display(controls, radius, trim, glass)
    fittings["button"](controls, radius, 49.6, -.64, 3.85, 1.1, trim, rubber)
    label(controls, "DISP", 49.6, -.47, 2.48, True)
    fittings["button"](controls, radius, 49.6, -1.49, 5.00, 1.36, trim, rubber)
    label(controls, "L-Fn", 49.6, -1.26, 2.62, True)
    switch = part("Focus mode slider and S-Line nameplate", rings)
    fittings["panel"](switch, radius, 12.7, -1.52, 5.0, 13.4, .66, trim)
    fittings["panel"](switch, radius, 14.7, -1.52, 4, 6.9, 1.14, rubber)
    for z in (13.2, 14.5, 15.8):
        fittings["panel"](switch, radius, z, -1.52, 3.5, .37, 1.31, trim)
    label(switch, "A", 17.0, -1.39, 2.6, True)
    label(switch, "M", 8.6, -1.39, 2.6, True)
    fittings["panel"](switch, radius, 12.6, -1.91, 10.5, 13.4, .55, trim)
    label(switch, "NIKKOR", 12.6, -1.83, 2.75, True, .65)
    label(switch, "S", 12.6, -1.99, 4.35, True, .65)

    mount = part("Z bayonet with four lugs and eleven spring-contact pads", "Mount")
    standard["mount"](mount, steel, gasket, trim, gold)
    mount.turn([
        (-2.02, 23.1), (-2.23, 22.42), (-2.8, 21.45),
        (-2.78, 20.72), (-2.16, 20.06), (-2.10, 19.85),
    ], cell, 128)
    retaining = part("M82 filter thread, hood lock and front retaining rings", "Optical cells")
    retaining.turn([
        (148.44, 41.88), (149.73, 41.91), (150, 41.66), (150, 41.05),
        (149.74, 40.8), (146.1, 40.8), (145.7, 40.15), (145.65, 38.90),
        (145.05, 38.30), (144.94, 33.50), (144.3, 32.75), (144.25, 32.35),
    ], trim, 128)
    filter_thread(retaining, gasket)
    for r in (32.98, 33.25, 33.52):
        retaining.turn([(144.95, r + .14), (145.13, r), (144.95, r - .16)], gasket, 112)
    def face_letter(x, y):
        a = -x / 37.03
        return (math.sin(a) * (37.03 + y), 145.12, math.cos(a) * (37.03 + y))
    retaining.label("Z  50mm  1:1.2  S   ø82", 1.71, face_letter, mats["Nikon front collar engraving"])
    hood_catch = [
        (42.05, 145.32), (43.21, 145.45), (43.46, 144.75),
        (43.22, 143.60), (42.88, 143.53),
    ]
    for a in (19, 109, 199, 289):
        standard["arc_section"](retaining, hood_catch, a, a + 37, trim)

    elements = "Optical elements · 17 in 15 groups"
    chambers = part("Inter-group sleeves and knife-edge light traps", "Optical cells", False)
    bore = []
    previous = None
    for n, (rim, samples, names) in enumerate(SECTION):
        profiles = [face_profile(rim, sample) for sample in samples]
        if n == 0:
            profiles[0].extend([(144.67, 31.95), (144.37, 32.80)])
            profiles[1].extend([(134.50, 30.02), (138.4, 30.28), (138.4, 32.80)])
        for j, name in enumerate(names):
            p, q = profiles[j:j + 2]
            shape = part(f"G{n + 1:02} E{j + 1} · {name}", elements, False)
            optical_face(shape, p, crystal, True)
            optical_face(shape, q, crystal, False)
            shape.turn([q[-1], p[-1]], cell, 96)
        chambers.turn([profiles[-1][-1], profiles[0][-1]], flock, 96)
        bore.extend([profiles[0][-1], profiles[-1][-1]])
        if previous:
            z, r = previous
            zz, rr = profiles[0][-1]
            chambers.turn([(z, r), (z - .21, r + .10), (zz + .21, rr + .10), (zz, rr)], flock, 96)
            gap = z - zz
            if gap > 2.8:
                for f in (.2, .4, .6, .8):
                    t, u = z - gap * f, r + (rr - r) * f
                    chambers.turn([(t + .15, u + .06), (t, u - .23), (t - .15, u + .06)], cell, 80)
                    if f == .4 and n in (1, 2, 14):
                        runtime.turn([(t + .12, u + .06), (t, u - .23), (t - .12, u + .06)], cell, 80)
        previous = profiles[-1][-1]
        if n in (0, 2, 6, 14):
            last = n == 14
            profile = profiles[-1] if last else profiles[0]
            coat = coatings[(0, 2, 6, 14).index(n)]
            optical_face(runtime, profile[::2], coat, not last, 80)
    runtime.turn(bore, flock, 88)
    diaphragm = part("Electromagnetic stop · nine curved overlapping leaves", "Optical cells")
    aperture_z, clear_radius = 55.0, 16.5
    fittings["diaphragm"](diaphragm, 9, aperture_z, 22.7, clear_radius, blade, trim)
    pupil = make("Z50 entrance pupil · relayed light", "111818", 0, .5)
    for z, r in ((105.0, 50 / 1.2 / 2), (aperture_z - .23, clear_radius + .04)):
        window = [standard["radial"](r, z, math.tau * i / 96) for i in range(96)]
        runtime.add(window, [tuple(range(96))], pupil, False)

    scene["flangeToFrontMm"] = 150
    scene["filterThread"] = "M82 × 0.75"
    scene["opticalConstruction"] = "17 elements in 15 groups; 2 ED, 3 aspherical"
    scene["sectionSource"] = (
        "Nikon Imaging global Z 50mm f/1.2 S optical construction chart, "
        "traced to the published envelope"
    )
    scene.world = bpy.data.worlds.new("50 mm optical workshop")
    objs = []
    for shape, collection, visible in parts:
        obj = shape.finalize(uv_scale=46, uv_materials=(shell, rubber, trim))
        if collection.name == elements:
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            bmesh.ops.remove_doubles(mesh, verts=mesh.verts, dist=1e-8)
            bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
            if not all(e.is_manifold for e in mesh.edges):
                raise ValueError(f"Open optical element: {shape.name}")
            mesh.to_mesh(obj.data)
            mesh.free()
        bpy.context.collection.objects.unlink(obj)
        collection.objects.link(obj)
        objs.append(obj)
        if visible:
            standard["merge"](shape, runtime, None)
    path = Path(__file__).resolve().parents[2] / ".review/atelier/nikon-reference/nikkor-z50-f12-s.blend"
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(path), {scene}, compress=True)
    subprocess.run(
        [bpy.app.binary_path, "-b", str(path), "--python-exit-code", "1", "--python", __file__],
        check=True,
    )
    for obj in objs:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    bpy.data.scenes.remove(scene)
    for collection in [*categories.values(), components]:
        bpy.data.collections.remove(collection)
    obj = runtime.finalize(uv_scale=46, uv_materials=(shell, rubber, trim))
    obj["opticalVariant"] = 4
    return obj


if __name__ == "__main__":
    bpy.context.preferences.filepaths.save_version = 0
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            viewport = area.spaces.active
            viewport.region_3d.view_location = (0, 0, .069)
            viewport.region_3d.view_distance = .25
            viewport.region_3d.view_rotation = Vector((.62, -.78, .32)).to_track_quat("Z", "Y")
            viewport.clip_start = .0004
            viewport.overlay.show_floor = False
            viewport.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
