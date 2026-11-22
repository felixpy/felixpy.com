import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector


SECTION_SCALE = 124.5 / 829
GROUPS = (
    (
        (0, 88, 108),
        (28, 88, 112),
        (69, 90, 129),
        (110, 95, 165),
        (143, 102, 202),
        (163, 108, 184),
        (185, 115, 162),
        (197, 119, 152),
        (216, 129, 151),
        (218, 130, 149),
    ),
    (
        (0, 196, 209),
        (46, 197, 215),
        (81, 201, 230),
        (110, 206, 254),
        (117, 207, 245),
        (126, 209, 234),
        (134, 212, 234),
    ),
    ((0, 274, 283), (46, 272, 285), (81, 268, 291), (109, 263, 298)),
    ((0, 288, 321), (46, 292, 321), (81, 301, 321), (108, 311, 320)),
    (
        (0, 451, 457.5, 490),
        (35, 454, 463, 491),
        (59, 459, 472, 491),
        (76, 465, 482, 492),
    ),
    (
        (0, 564, 572.5, 608),
        (35, 567, 577, 608),
        (59, 573, 586, 609),
        (78, 581, 598, 609),
    ),
    (
        (0, 642, 651.5, 683),
        (35, 641, 655, 682),
        (59, 639, 661, 679),
        (78, 636, 667, 677),
    ),
    ((0, 692, 725), (35, 695, 724), (59, 701, 721), (81, 710, 717)),
    (
        (0, 730, 740.5, 763),
        (35, 732, 746, 765),
        (59, 736, 754.5, 767),
        (68, 738, 759, 766),
        (74, 741, 758, 760),
    ),
    (
        (0, 769, 803.5, 811),
        (35, 772, 799, 813),
        (59, 776, 791.5, 815),
        (65, 779, 788.5, 816),
        (71, 790, 791, 816),
    ),
    ((0, 840, 849), (46, 837, 846), (69, 832, 843), (89, 827, 838)),
)


def profile(samples, side):
    radii = [row[0] for row in samples]
    axis = [row[side] for row in samples]
    slopes = [
        (b - a) / (rb - ra) for a, b, ra, rb in zip(axis, axis[1:], radii, radii[1:])
    ]
    tangent = [0]
    for left, right in zip(slopes, slopes[1:]):
        tangent.append(2 * left * right / (left + right) if left * right > 0 else 0)
    tangent.append(slopes[-1])
    rings = []
    for i in range(len(samples) - 1):
        dr = radii[i + 1] - radii[i]
        n = max(2, math.ceil(dr / 11))
        for j in range(n):
            t = j / n
            u = 1 - t
            x = (
                u * u * (1 + 2 * t) * axis[i]
                + t * t * (3 - 2 * t) * axis[i + 1]
                + dr * (t * u * u * tangent[i] - t * t * u * tangent[i + 1])
            )
            rings.append(
                ((900 - x) * SECTION_SCALE, (radii[i] + dr * t) * SECTION_SCALE)
            )
    rings.append(((900 - axis[-1]) * SECTION_SCALE, radii[-1] * SECTION_SCALE))
    return rings


def disk(shape, profile, material, segments, back=False):
    z0, _ = profile[0]
    shape.turn(list(reversed(profile[1:])) if back else profile[1:], material, segments)
    z, r = profile[1]
    pts = [(0, z0, 0)] + [
        (
            r * math.sin(i * math.tau / segments),
            z,
            r * math.cos(i * math.tau / segments),
        )
        for i in range(segments)
    ]
    fan = [(0, i + 1, (i + 1) % segments + 1) for i in range(segments)]
    shape.add(pts, fan, material)


def gel_holder(part, shell, edge):
    def outer_radius(a):
        degrees = math.degrees(math.atan2(math.sin(a), math.cos(a)))
        margin = max(0, min(1, (degrees + 48) / 6, (45 - degrees) / 6))
        return 22.95 - 1.65 * margin

    def outline(a, width, height, corner):
        dx, dz = abs(math.sin(a)), abs(math.cos(a))
        return min(
            width / max(dx, 1e-6),
            height / max(dz, 1e-6),
            (width + height - corner) / (dx + dz),
        )

    angles = [math.tau * i / 112 for i in range(113)]
    floor = []
    for a in angles:
        r = outline(a, 17.48, 13.48, 4.3)
        outer = outer_radius(a)
        floor.append(
            [
                (math.sin(a) * w, z, math.cos(a) * w)
                for w, z in [
                    (outer, 1.1),
                    (outer, -3.7),
                    (outer - 0.38, -4.82),
                    (r + 0.32, -4.82),
                    (r, -4.56),
                    (r, 0.76),
                    (r + 0.3, 1.1),
                    (outer, 1.1),
                ]
            ]
        )
    part.rings(floor, shell, False, False)
    bearing = math.atan2(19.2, 10.0)
    angles = [
        (-math.pi + bearing) + (2 * math.pi - 2 * bearing) * i / 108 for i in range(109)
    ]
    rails = []
    grooves = [[] for _ in range(3)]
    for a in angles:
        r = outline(a, 17.52, 13.47, 4.3)
        well = outline(a, 19.25, 15.25, 5.0)
        outer = outer_radius(a)
        rails.append(
            [
                (math.sin(a) * w, z, math.cos(a) * w)
                for w, z in [
                    (outer, -4.65),
                    (outer, -5.32),
                    (outer - 0.33, -5.66),
                    (r + 0.17, -5.66),
                    (r, -5.60),
                    (r, -5.35),
                    (well, -5.35),
                    (well, -4.64),
                ]
            ]
        )
        for j, row in enumerate(grooves):
            rr = r + 0.34 + j * 0.5
            row.append(
                [
                    (w * math.sin(a), z, w * math.cos(a))
                    for w, z in [(rr, -5.66), (rr + 0.08, -5.72), (rr + 0.19, -5.66)]
                ]
            )
    part.rings(rails, shell, False)
    for rows in grooves:
        part.rings(rows, edge, False)


def ribbed(part, z1, z2, r, count, lift, material, dark, detailed):
    r = min(r, 44.25 - 0.11 - lift)
    rows = []
    shoulders = [
        (z1 - 0.34, -0.17, 0.04),
        (z1 + 0.24, 0.04, 0.55),
        (z1 + 0.82, 0.11, 1),
        (z2 - 0.82, 0.11, 1),
        (z2 - 0.24, 0.04, 0.55),
        (z2 + 0.34, -0.17, 0.04),
    ]
    facets = [
        (0, 0),
        (0.17, 0),
        (0.26, 0.67),
        (0.37, 1),
        (0.65, 1),
        (0.76, 0.67),
        (0.84, 0),
    ]
    if not detailed:
        shoulders = [shoulders[i] for i in (0, 2, 3, 5)]
        facets = [facets[i] for i in (1, 3, 4, 6)]
    for z, base, relief in shoulders:
        ring = []
        for i in range(count):
            for phase, tooth in facets:
                a = (i + phase) * math.tau / count
                rr = r + base + lift * tooth * relief
                ring.append((rr * math.sin(a), z, rr * math.cos(a)))
        rows.append(ring)
    part.rings(rows, material, True, False)
    for z in (z1 - 0.63, z2 + 0.63):
        part.turn(
            [(z - 0.13, r - 0.15), (z, r + 0.03), (z + 0.13, r - 0.15)], dark, 112
        )


def build(spec, Sculpture, make, controls, standard, glass, materials):
    shell, grip, enamel, rubber, ink, gray, lcd = materials
    scene = bpy.data.scenes.new("NIKKOR Z 14–24mm f2.8 S")
    scene.unit_settings.system = "METRIC"
    target = Sculpture(spec["name"])
    finish = make("Z14-24 · optical cell black anodizing", "171b1f", 0.23, 0.51)
    dark = make("Z14-24 · light-trap anodizing", "15171a", 0.14, 0.73)
    metal = make("Z14-24 · plated flange", "c1c3c5", 0.84, 0.22)
    gold = make("Z14-24 · plated CPU contacts", "dcb86c", 0.83, 0.24)
    clear = make("Z14-24 · optical glass", "edeee8", 0, 0.012)
    shader = clear.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Transmission Weight"].default_value = 1
    shader.inputs["IOR"].default_value = 1.55
    coating = []
    for name, layer in zip(("outer", "inner", "relay", "field"), glass):
        m = layer.copy()
        m.name = "NIKKOR glass / 14-24 S / " + name
        coating.append(m)
    parts = []

    def component(name, group="Barrel and controls"):
        obj = Sculpture(name)
        parts.append((obj, group))
        return obj

    collar = [
        (0, 29.3),
        (1.7, 33.1),
        (2.4, 34.1),
        (3.6, 34.96),
        (21.8, 34.96),
        (22.7, 34.8),
        (22.8, 34.9),
    ]
    contour = collar + [p for p in spec["profile"] if p[0] > collar[-1][0]]

    def radius(z):
        for (a, ra), (b, rb) in zip(contour, contour[1:]):
            if z <= b:
                return ra + (rb - ra) * max(0, (z - a) / (b - a))
        return contour[-1][1]

    def xyz(a, z, lift=0):
        r = radius(z) + lift
        return (r * math.sin(a), z, r * math.cos(a))

    def text(part, s, z, a, size, mat=ink, lift=0.27, italic=False):
        part.label(
            s, size, lambda x, y: xyz(a + x / radius(z), z + y, lift), mat, italic
        )

    def switch_legend(part, s, z, a, size):
        part.label(s, size, lambda x, y: xyz(a + y / radius(z), z - x, 0.27), ink)

    stator = component("Zoom barrel · inner mount and fixed outer shell")
    display_fit = (42.2, 24.8, 13.1)
    controls["windowed_barrel"](
        stator, contour[len(collar) - 1 :], radius, *display_fit, shell, 120
    )
    selector_angle = -1.52
    lower = component("Anodized mount collar with AF selector opening")
    controls["windowed_barrel"](lower, collar, radius, 12.0, 5.2, 12.8, enamel, 120)
    ca, sa = math.cos(selector_angle), math.sin(selector_angle)
    lower.vertices = [
        (x * ca - y * sa, x * sa + y * ca, z) for x, y, z in lower.vertices
    ]
    for name, (a, b, teeth, relief) in zip(
        ("Assignable control ring", "Zoom ring and scale", "Manual focusing ring"),
        spec["rings"],
    ):
        part = component(name, "Zoom and focus rings")
        for mesh, detailed in ((part, True), (target, False)):
            ribbed(
                mesh,
                a,
                b,
                max(radius(a), radius(b)),
                teeth,
                relief,
                grip,
                rubber,
                detailed,
            )
            if name.startswith("Zoom"):
                for j, num in enumerate(("14", "15", "16", "18", "20", "24")):
                    text(mesh, num, 54.2, -j * 0.277, 3.18)
    panel = component("OLED cover, display key and lens function key")
    bezel = make("Z14-24 · satin OLED bezel", "17181c", 0.04, 0.32, 0.10)
    controls["recessed_display"](
        panel, radius, *display_fit, 18.53, 8.11, shell, bezel, lcd
    )
    for a, rad, caption in [(-0.64, 4.9, "DISP"), (-1.50, 7.15, "L-Fn")]:

        def circle(r, offset):
            return [
                xyz(
                    a + r * math.cos(i * math.tau / 60) / radius(42),
                    42 + r * math.sin(i * math.tau / 60),
                    offset,
                )
                for i in range(60)
            ]

        panel.rings(
            [
                circle(rad, -0.10),
                circle(rad, 0.12),
                circle(rad - 0.32, 0.49),
                circle(rad - 1.02, 0.78),
                circle(rad - 1.36, 0.66),
                circle(rad - 1.78, 0.18),
            ],
            shell,
            True,
            False,
        )
        pad_radius = rad * 0.56
        face = [
            (
                math.sin(a) * (radius(42) + 0.55)
                + math.cos(a) * pad_radius * math.cos(i * math.tau / 60),
                42 + pad_radius * math.sin(i * math.tau / 60),
                math.cos(a) * (radius(42) + 0.55)
                - math.sin(a) * pad_radius * math.cos(i * math.tau / 60),
            )
            for i in range(60)
        ]
        panel.rings(
            [
                circle(rad - 1.78, 0.18),
                circle(rad * 0.63, 0.18),
                circle(rad * 0.62, 0.39),
                face,
            ],
            rubber,
            True,
            False,
        )
        panel.add(face, [tuple(range(len(face)))], rubber, False)
        switch_legend(panel, caption, 42, a + (rad + 1.7) / radius(42), 2.25)
    controls["panel"](panel, radius, 50.25, 0, 0.81, 1.99, 0.19, ink)
    label = component("Mount index, S-Line inset and focus mode switch")
    text(label, "14–24/2.8 S", 12.1, 0, 4.40, lift=0.31)
    controls["dot"](label, xyz, 0, 4.85, 1.02, ink)

    def rounded(w, h, corner, level):
        points = []
        for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            for j in range(7):
                arc = (i + j / 6) * math.pi / 2
                u = sx * (w / 2 - corner) + corner * math.cos(arc)
                v = sy * (h / 2 - corner) + corner * math.sin(arc)
                points.append(xyz(selector_angle + u / radius(12), 12 + v, level))
        return points

    socket = component("Recessed A–M selector, thumb rib and printed position guides")
    socket.rings(
        [
            rounded(5.31, 12.91, 0.04, 0.045),
            rounded(5.03, 12.61, 0.92, 0.10),
            rounded(4.83, 12.43, 0.87, -0.07),
            rounded(4.57, 12.09, 0.83, -0.72),
        ],
        enamel,
        True,
        False,
    )
    floor = rounded(4.57, 12.09, 0.83, -0.72)
    socket.add(floor, [tuple(range(len(floor)))], rubber, False)
    controls["panel"](socket, radius, 13.24, selector_angle, 4.42, 9.27, -0.22, grip)
    controls["panel"](socket, radius, 13.24, selector_angle, 4.22, 1.66, 0.65, enamel)
    controls["panel"](socket, radius, 13.24, selector_angle, 2.87, 0.48, 0.78, ink)

    def printed_line(u1, v1, u2, v2):
        u, v = u2 - u1, v2 - v1
        half = 0.13 / math.hypot(u, v)
        positions = [
            (u1 - v * half, v1 + u * half),
            (u1 + v * half, v1 - u * half),
            (u2 + v * half, v2 - u * half),
            (u2 - v * half, v2 + u * half),
        ]
        socket.add(
            [xyz(selector_angle + x / radius(12), 12 + y, 0.13) for x, y in positions],
            [(0, 1, 2, 3)],
            ink,
            False,
        )

    for sign in (-1, 1):
        printed_line(3.48, sign * 6.35, 3.48, sign * 1.10)
        printed_line(3.48, sign * 1.10, 2.81, sign * 1.10)
    switch_legend(socket, "A", 16.72, selector_angle + 5.05 / radius(12), 2.42)
    switch_legend(socket, "M", 7.38, selector_angle + 5.05 / radius(12), 2.42)
    badge_angle = selector_angle - 12.15 / radius(12)
    badge_silver = make("Z14-24 · silver S-Line nameplate", "c3c1bc", 0.35, 0.38)
    controls["panel"](
        label, radius, 12.0, badge_angle, 10.55, 12.15, 0.35, badge_silver
    )
    controls["panel"](label, radius, 12.0, badge_angle, 10.28, 11.87, 0.43, dark)

    def badge_text(word, shift, size, italic=False):
        label.label(
            word,
            size,
            lambda x, y: xyz(badge_angle + (y + shift) / radius(12), 12 - x, 0.54),
            badge_silver,
            italic,
        )

    badge_text("NIKKOR", 1.69, 2.70)
    badge_text("S", -1.94, 4.32, True)
    text(label, "NIKKOR Z 14–24mm 1:2.8 S", 109.2, 0, 2.23, gray, 0.27)
    controls["dot"](label, xyz, -0.025, 111.7, 0.53, ink)
    hood = component("Fixed shallow petal guard and accessory bayonet")
    for start, end in [(-148, -88), (-49, 11), (65, 120), (141, 164)]:
        standard["arc_section"](
            hood,
            [
                (42.10, 112.6),
                (42.87, 113.1),
                (43.20, 113.4),
                (43.20, 114.40),
                (42.10, 114.85),
            ],
            start,
            end,
            enamel,
        )
    rows = []
    for t, delta in [
        (0, -0.08),
        (0.08, 0.08),
        (0.96, 0.08),
        (1, 0),
        (1, -0.65),
        (0.96, -0.83),
        (0, -0.87),
    ]:
        ring = []
        for i in range(192):
            a = math.tau * i / 192
            d = abs(math.atan2(math.sin(2 * a), math.cos(2 * a))) / math.pi
            crown = min(1, max(0, (abs(math.cos(2 * a)) - 0.10) / 0.40))
            h = 114.50 + t * (4.05 + (5.95 if d < 0.5 else 3.75) * crown)
            ring.append(
                (math.sin(a) * (42.05 + delta), h, math.cos(a) * (42.05 + delta))
            )
        rows.append(ring)
    hood.rings(rows, enamel, True, False)
    front = component(
        "Front filter shade and concentric anti-flare grooves", "Optical cells"
    )
    front.turn(
        [
            (118.48, 41.44),
            (118.28, 40.95),
            (118.10, 40.92),
            (117.71, 39.95),
            (116.74, 37.36),
            (115.86, 33.23),
            (115.70, 32.60),
        ],
        finish,
        144,
    )
    for i in range(7):
        r = 33.55 + i * 0.99
        z = 115.81 + i * 0.33
        front.turn([(z - 0.1, r - 0.4), (z + 0.26, r), (z + 0.04, r + 0.38)], dark, 128)
    flange = component(
        "Z mount · four lugs, recessed screws and gold CPU contacts",
        "Mount and rear filter",
    )
    standard["mount"](
        flange, metal, rubber, enamel, gold, contact_rotation=21, contact_height=0.21
    )
    holder = component(
        "38 by 30 mm rear gelatin filter carrier", "Mount and rear filter"
    )
    gel_holder(holder, enamel, finish)
    tube = component(
        "Internal chambers, field stops and rear element seat", "Optical cells"
    )
    rims = []
    coatings = {(0, 0): 0, (1, 0): 1, (6, 0): 2, (10, 1): 3}
    for g, table in enumerate(GROUPS):
        surfaces = [profile(table, side) for side in range(1, len(table[0]))]
        rims.append((surfaces[0][-1], surfaces[-1][-1]))
        for e, (a, b) in enumerate(zip(surfaces, surfaces[1:])):
            part = component(f"Group {g + 1:02} · element {e + 1}", "Optical elements")
            disk(part, a, clear, 88)
            disk(part, b, clear, 88, True)
            part.turn([a[-1], b[-1]], dark, 88)
        for j, surface in enumerate(surfaces):
            if (g, j) in coatings:
                disk(target, surface, coating[coatings[g, j]], 88, j != 0)
    for (_, start), (end, _) in zip(rims, rims[1:]):
        z, r = start
        zz, rr = end
        tube.turn(
            [
                (z, r + 0.21),
                (z - 0.26, r + 0.03),
                (zz + 0.21, rr + 0.06),
                (zz, rr + 0.18),
            ],
            finish,
            96,
        )
        if z - zz > 5.8:
            for i in range(1, 6):
                t = i / 6
                h = z + (zz - z) * t
                w = r + (rr - r) * t
                tube.turn(
                    [(h - 0.12, w + 0.08), (h, w - 0.19), (h + 0.13, w + 0.08)],
                    dark,
                    80,
                )
    z, r = rims[-1][1]
    tube.turn(
        [
            (1.35, 17.35),
            (2.10, 16.20),
            (4.48, 15.55),
            (z - 0.3, r + 0.35),
            (z, r + 0.05),
        ],
        finish,
        112,
    )
    iris = component("Nine-blade electromagnetic diaphragm", "Optical cells")
    controls["diaphragm"](iris, 9, 52.26, 11.9, 3.65, dark, finish)
    ring = [standard["radial"](3.69, 52.19, i * math.tau / 64) for i in range(64)]
    pupil = make("Z14-24 entrance pupil · relayed light", "131b19", 0, 0.5)
    target.add(ring, [tuple(range(64))], pupil, False)
    groups = {}
    assembly = bpy.data.collections.new("NIKKOR Z 14-24mm f2.8 S")
    scene.collection.children.link(assembly)
    native = []
    for part, group in parts:
        if group not in groups:
            groups[group] = bpy.data.collections.new(group)
            assembly.children.link(groups[group])
        obj = part.finalize(
            uv_scale=46
            if group in ("Barrel and controls", "Zoom and focus rings")
            else 0,
            uv_materials=(shell, grip, enamel),
        )
        bpy.context.collection.objects.unlink(obj)
        groups[group].objects.link(obj)
        native.append(obj)
        if group not in ("Optical elements", "Zoom and focus rings"):
            standard["merge"](part, target, None)
    scene.world = bpy.data.worlds.new("Ultra-wide lens workshop")
    scene["flangeToFrontMm"] = 124.5
    scene["opticalElements"] = 16
    scene["opticalGroups"] = 11
    source = (
        Path(__file__).resolve().parents[2]
        / ".references/05-摄影与陈列/相机与镜头/NIKKOR Z 14-24mm f2.8 S/Blender/nikkor-z14-24-s.blend"
    )
    bpy.data.libraries.write(str(source), {scene}, compress=True)
    for obj in native:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    bpy.data.scenes.remove(scene)
    for group in groups.values():
        bpy.data.collections.remove(group)
    bpy.data.collections.remove(assembly)
    subprocess.run(
        [
            bpy.app.binary_path,
            "-b",
            str(source),
            "--python-exit-code",
            "1",
            "--python",
            __file__,
        ],
        check=True,
    )
    obj = target.finalize(uv_scale=46, uv_materials=(shell, grip, enamel))
    obj["opticalVariant"] = 0
    return obj


if __name__ == "__main__":
    bpy.context.preferences.filepaths.save_version = 0
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_distance = 0.265
            view.region_3d.view_location = (0, 0, 0.062)
            view.region_3d.view_rotation = Vector((0.77, -0.55, 0.40)).to_track_quat(
                "Z", "Y"
            )
            view.clip_start = 0.0005
            view.overlay.show_floor = False
            view.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
