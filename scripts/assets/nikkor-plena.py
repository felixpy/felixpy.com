import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector, geometry


FLANGE_X = 930
MILLIMETRES_PER_PIXEL = 139.5 / (FLANGE_X - 47)
SECTION = (
    (229, ((103, 118, 166), (152, 158, 177)), ("SR front meniscus",)),
    (220, ((161, 175, 216), (209, 214, 226)), ("ED meniscus",)),
    (204, ((218, 227, 254), (254, 258, 267)), ("ED meniscus",)),
    (
        181,
        ((263, 276, 315), (326, 325.5, 323), (338, 351, 370)),
        ("ED", "cemented companion"),
    ),
    (132, ((407, 410, 417), (433, 433, 434)), ("aspherical",)),
    (119, ((446, 448, 452), (457, 463.5, 486)), ("focusing element",)),
    (129, ((598, 596.5, 589), (621, 617, 602)), ("meniscus",)),
    (
        136,
        ((624, 622, 616.5), (636, 640, 655), (656, 658, 665)),
        ("cemented companion", "ED"),
    ),
    (142, ((662, 669, 688.5), (718, 713.5, 701)), ("biconvex",)),
    (139, ((720, 722, 728), (732, 735.5, 750)), ("rear relay",)),
    (136, ((794, 798, 811.5), (820, 820, 822.5)), ("relay",)),
    (129, ((844, 843.5, 841.5), (855, 860.5, 876.5)), ("rear cell",)),
    (129, ((863, 870, 891), (894, 896, 902.5)), ("rear meniscus",)),
    (126, ((924, 919, 905), (934, 934, 934)), ("large rear element",)),
)


def section_surface(radius, samples):
    center, middle, edge = samples
    bend = (16 * (middle - center) - (edge - center)) / 3
    correction = edge - center - bend
    profile = []
    for i in range(19):
        t = i / 18
        x = center + bend * t**2 + correction * t**4
        profile.append(
            ((FLANGE_X - x) * MILLIMETRES_PER_PIXEL, radius * t * MILLIMETRES_PER_PIXEL)
        )
    return profile


def axial_ribs(shape, start, end, radius, count, lift, material, split=0):
    for a, b in (
        [(start, split - 0.32), (split + 0.32, end)] if split else [(start, end)]
    ):
        rows = []
        for z, shoulder in ((a - 0.28, 0), (a + 0.40, 1), (b - 0.40, 1), (b + 0.28, 0)):
            ring = []
            for i in range(count):
                for f, depth in ((0, 0), (0.18, 0), (0.33, 1), (0.71, 1), (0.88, 0)):
                    angle = (i + f) * math.tau / count
                    r = radius + shoulder * (0.07 + lift * depth)
                    ring.append((r * math.sin(angle), z, r * math.cos(angle)))
            rows.append(ring)
        shape.rings(rows, material, True, False)


def s_emblem(part, xyz, radius, z, angle, bezel, silver):
    strokes = (
        ((32, 91), (32, 14), (203, -5), (382, 52)),
        ((382, 52), (377, 63), (353, 81), (341, 89)),
        ((341, 89), (261, 60), (131, 43), (127, 91)),
        ((127, 91), (115, 132), (268, 130), (353, 179)),
        ((353, 179), (432, 225), (392, 295), (287, 306)),
        ((287, 306), (204, 316), (95, 300), (24, 271)),
        ((24, 271), (39, 257), (52, 242), (65, 230)),
        ((65, 230), (142, 258), (263, 275), (292, 236)),
        ((292, 236), (330, 178), (135, 180), (59, 131)),
        ((59, 131), (42, 119), (32, 108), (32, 91)),
    )
    contour = []
    for a, b, c, d in strokes:
        for i in range(10):
            t = i / 10
            u, v = (
                sum(
                    k * v
                    for k, v in zip(
                        ((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t**3),
                        axis,
                    )
                )
                for axis in zip(a, b, c, d)
            )
            contour.append(Vector(((u - 210) * 0.028, (166 - v) * 0.028, 0)))
    triangles = geometry.tessellate_polygon([contour])
    for scale, height, material in ((1.075, 0.23, bezel), (1, 0.31, silver)):
        part.add(
            [
                xyz(angle + v.y * scale / radius(z), z - v.x * scale, height)
                for v in contour
            ],
            triangles,
            material,
            False,
        )


def function_button(part, radius, xyz, z, angle, collar, recess, rubber):
    def ring(button_radius, relief):
        result = []
        for i in range(56):
            a = i * math.tau / 56
            yy = z + button_radius * math.sin(a)
            result.append(xyz(angle + button_radius * math.cos(a) / radius(yy), yy, relief))
        return result

    part.rings(
        [
            ring(r, k)
            for r, k in (
                (7.72, -0.07),
                (7.48, 0.49),
                (7.05, 1.03),
                (5.65, 1.16),
                (5.08, 0.65),
            )
        ],
        collar,
        True,
        False,
    )
    part.rings([ring(5.09, 0.65), ring(4.55, 0.64)], recess, True, False)
    part.rings(
        [
            ring(4.63, 0.62),
            ring(4.52, 1.27),
            ring(4.18, 1.42),
            ring(2.72, 1.51),
            ring(0.02, 1.53),
        ],
        rubber,
        True,
        True,
    )


def build(spec, Sculpture, make, controls, standard, wide, glass, shared):
    enamel, rubber, ink, gray = shared

    def finish(base, name, metal, roughness, grain):
        material = bpy.data.materials[base].copy()
        material.name = name
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = roughness
        normal = next(n for n in material.node_tree.nodes if n.type == "NORMAL_MAP")
        normal.inputs["Strength"].default_value = grain
        return material

    shell = finish(
        "NIKKOR barrel · black powder coat",
        "Plena · satin black metal barrel",
        0.46,
        0.32,
        0.055,
    )
    focus = finish(
        "Focus ring · charcoal elastomer",
        "Plena · vulcanised focus grip",
        0.01,
        0.56,
        0.105,
    )
    flock = make("Plena · antireflection velvet", "101415", 0.01, 0.88)
    turned = make("Plena · anodized optical cell", "181b1d", 0.28, 0.46)
    steel = make("Plena · ground stainless flange", "bdbec1", 0.86, 0.21)
    contact = make("Plena · gold-over-nickel contacts", "c9ac70", 0.8, 0.24)
    signature = make("Plena · engraved gold script", "d4b647", 0.45, 0.32)
    clear = make("Plena · colourless optical substrate", "f5f8f5", 0, 0.012)
    crystal = clear.node_tree.nodes.get("Principled BSDF")
    crystal.inputs["Transmission Weight"].default_value = 1
    crystal.inputs["IOR"].default_value = 1.54
    coatings = []
    for label, base in zip(("outer", "inner", "relay", "field"), glass):
        material = base.copy()
        material.name = "NIKKOR glass / 135 Plena / " + label
        coatings.append(material)
    parts = []
    native_scene = bpy.data.scenes.new("NIKKOR Z 135mm f1.8 S Plena")
    native_scene.unit_settings.system = "METRIC"
    workshop = bpy.data.collections.new(spec["name"])
    native_scene.collection.children.link(workshop)
    local_groups = {}
    runtime = Sculpture(spec["name"])

    def part(name, assembly, visible=True):
        item = Sculpture(name)
        parts.append((item, assembly, visible))
        return item

    contour = spec["profile"]

    def radius(z):
        for (a, r), (b, s) in zip(contour, contour[1:]):
            if z <= b:
                return r + (s - r) * max(0, (z - a) / (b - a))
        return contour[-1][1]

    def xyz(a, z, lift):
        r = radius(z) + lift
        return (r * math.sin(a), z, r * math.cos(a))

    def mark(item, text, z, angle, size, material, lift=0.17, side=False):
        def project(x, y):
            return xyz(
                angle + (y if side else x) / radius(z), z + (-x if side else y), lift
            )

        item.label(text, size, project, material)

    barrel = part(
        "Black metal fixed barrel and flared shoulders", "Barrel and controls"
    )
    barrel.turn(contour, shell, 144)
    barrel.turn(
        [(1.5, 31.1), (1.7, 33.1), (2.5, 34.8), (3.25, 34.99), (3.7, 34.89)],
        enamel,
        112,
    )
    for z in (22.2, 32.6, 43.0, 69.4, 101.8, 108.25, 122.4):
        r = radius(z)
        barrel.turn(
            [
                (z - 0.19, r),
                (z - 0.08, r + 0.09),
                (z + 0.10, r + 0.07),
                (z + 0.24, radius(z + 0.24)),
            ],
            enamel,
            112,
        )

    control = part(
        "Assignable clickless control ring · diamond knurl", "Barrel and controls"
    )
    standard["control_knurl"](control, 41.30, 34.4, 41.76, focus, enamel)
    focusing = part(
        "Wide manual focusing ring · longitudinal moulded ribs", "Barrel and controls"
    )
    axial_ribs(focusing, 72.2, 100.0, 47.88, 141, 0.61, focus)
    handling = part(
        "Fixed two-band rubber handgrip ahead of focusing ring", "Barrel and controls"
    )
    axial_ribs(handling, 109.7, 121.1, 48.43, 141, 0.50, focus, 115.25)

    buttons = part(
        "Twin L-Fn buttons, silver S inset and longitudinal A/M switch",
        "Barrel and controls",
    )
    for a in (0, -math.pi / 2):
        function_button(buttons, radius, xyz, 56.4, a, shell, rubber, focus)
    side = -math.pi / 2
    mark(buttons, "L-Fn", 56.3, side + 0.232, 2.42, gray, side=True)
    mark(buttons, "NIKKOR", 56.3, side + 0.72, 3.58, ink, side=True)
    s_emblem(buttons, xyz, radius, 56.3, side + 0.49, rubber, steel)
    controls["panel"](buttons, radius, 11.5, side, 5.35, 13.6, 0.52, enamel)
    controls["panel"](buttons, radius, 13.7, side, 4.13, 6.93, 1.02, focus)
    for z in (11.8, 12.7, 13.6, 14.5, 15.4):
        controls["panel"](buttons, radius, z, side, 3.25, 0.25, 1.18, enamel)
    controls["panel"](buttons, radius, 11.81, side, 3.29, 0.42, 1.28, gray)
    mark(buttons, "A", 15.7, side + 0.13, 2.22, ink, side=True)
    mark(buttons, "M", 7.8, side + 0.13, 2.22, ink, side=True)
    mark(buttons, "NIKKOR", 14.1, 0, 3.62, ink)
    mark(buttons, "135/1.8 S", 9.78, 0, 4.75, ink)
    controls["dot"](buttons, xyz, 0, 4.72, 1.15, ink)
    controls["signature"](buttons, xyz, 56.4, 0.64, signature)

    front = part(
        "82 × 0.75 filter thread, HB-108 locking lands and front-cell seat",
        "Optical cells",
    )
    r0 = SECTION[0][0] * MILLIMETRES_PER_PIXEL
    z0 = (FLANGE_X - SECTION[0][1][0][-1]) * MILLIMETRES_PER_PIXEL
    front.turn(
        [
            (139.5, 41.88),
            (139.5, 41.12),
            (139.1, 40.58),
            (135.6, 40.58),
            (134.4, 40.0),
            (133.5, 39.55),
            (128.65, 38.7),
            (127.4, 38.44),
            (z0 + 0.16, r0),
            (z0 - 0.45, r0 + 0.14),
        ],
        turned,
        144,
    )
    for i in range(5):
        z = 138.82 - 0.75 * i
        front.turn(
            [(z + 0.28, 40.6), (z + 0.02, 40.24), (z - 0.24, 40.58)], enamel, 128
        )
    for i in range(9):
        z, r = 125.18 + i * 0.865, 37.78 + i * 0.20
        front.turn(
            [(z + 0.22, r + 0.20), (z, r - 0.10), (z - 0.25, r + 0.06)], turned, 128
        )
    for a, b in ((-171, -96), (-57, 12), (55, 132)):
        standard["arc_section"](
            front,
            [(41.84, 135.2), (42.73, 135.5), (42.8, 137.55), (41.85, 137.7)],
            a,
            b,
            enamel,
        )
    mark(front, "NIKKOR Z 135mm 1:1.8 S Plena   ø82", 123.9, 0, 2.92, gray, 0.25)
    controls["dot"](front, xyz, 0, 127.5, 0.65, ink)

    interface = part(
        "Z bayonet · flange with lugs, locating hole and CPU land", "Z mount", False
    )
    standard["mount"](
        interface, steel, rubber, enamel, contact, contact_rotation=20, contact_height=0.21
    )
    rear = part(
        "Large curved rear element · light trap and black retaining ring",
        "Optical cells",
        False,
    )
    rear.turn(
        [
            (-1.9, 23.0),
            (-2.12, 22.42),
            (-1.92, 21.84),
            (-1.18, 20.94),
            (-0.54, 20.65),
            (-0.61, 19.81),
            (-0.19, 19.75),
        ],
        turned,
        112,
    )
    for rr in (21.63, 22.03, 22.47):
        rear.turn([(-1.86, rr + 0.12), (-2.17, rr), (-1.95, rr - 0.09)], flock, 112)

    cells = part(
        "Stepped optical chambers and knife-edge flare stops", "Optical cells", False
    )
    coatings_at = {(0, 0): 0, (1, 0): 1, (4, 0): 2, (6, 0): 3}
    rims = []
    for g, (r, samples, types) in enumerate(SECTION):
        profiles = [section_surface(r, surface) for surface in samples]
        for j, kind in enumerate(types):
            element = part(
                f"G{g + 1:02} · {j + 1} · {kind}",
                "Optical elements · 16 in 14 groups",
                False,
            )
            a, b = profiles[j : j + 2]
            wide["disk"](element, a, clear, 96)
            wide["disk"](element, b, clear, 96, True)
            element.turn([a[-1], b[-1]], turned, 104)
            if g < 7:
                runtime.turn([a[-1], b[-1]], flock, 80)
        for j, face in enumerate(profiles):
            if (g, j) in coatings_at:
                wide["disk"](
                    runtime, face[::2], coatings[coatings_at[g, j]], 80, j != 0
                )
        rims.append((profiles[0][-1], profiles[-1][-1]))
    for (_, stop), (start, _) in zip(rims, rims[1:]):
        z1, r1 = stop
        z2, r2 = start
        chamber = [
            (z1, r1 + 0.05),
            (z1 - 0.21, r1 + 0.08),
            (z2 + 0.25, r2 + 0.09),
            (z2, r2 + 0.06),
        ]
        cells.turn(chamber, flock, 96)
        if z1 > 63:
            runtime.turn(chamber, flock, 80)
        if z1 - z2 > 4:
            for j in range(1, 5):
                t = j / 5
                z, r = z1 * (1 - t) + z2 * t, r1 * (1 - t) + r2 * t
                cells.turn(
                    [(z + 0.18, r + 0.10), (z, r - 0.20), (z - 0.19, r + 0.12)],
                    turned,
                    80,
                )
                if z > 63:
                    runtime.turn(
                        [(z + 0.18, r + 0.10), (z, r - 0.20), (z - 0.19, r + 0.12)],
                        turned,
                        72,
                    )
    iris = part(
        "Eleven rounded overlapping electromagnetic diaphragm leaves", "Optical cells"
    )
    controls["diaphragm"](iris, 11, 63.1, 20.43, 15.9, turned, enamel)
    inner_cap = [standard["radial"](20.4, 46.8, i * math.tau / 80) for i in range(80)]
    runtime.add(inner_cap, [tuple(range(80))], flock, False)

    cap = part(
        "LF-N1 rear cap · removable with four internal bayonet catches",
        "LF-N1 rear cover",
        False,
    )
    cap.turn(
        [
            (-13.0, 26.8),
            (-13.0, 30.1),
            (-12.8, 31.75),
            (-12.0, 32.55),
            (-10.7, 32.87),
            (-1.65, 32.87),
            (-0.56, 33.0),
            (-0.18, 32.55),
            (-0.18, 31.98),
            (-0.68, 31.59),
            (-11.0, 31.4),
            (-11.34, 29.8),
            (-11.34, 0.01),
        ],
        enamel,
        104,
    )
    cap.turn([(-13, 26.83), (-12.66, 26.2), (-12.62, 0.01)], enamel, 104)
    axial_ribs(cap, -11.03, -1.52, 32.82, 96, 0.27, enamel)
    runtime.turn(
        [
            (-13, 30.1),
            (-12.8, 31.75),
            (-12, 32.55),
            (-1.6, 32.87),
            (-0.2, 32.55),
            (-0.2, 31.95),
        ],
        enamel,
        96,
    )
    axial_ribs(runtime, -11.03, -1.52, 32.82, 96, 0.27, enamel)
    runtime.turn([(-12.72, 30.2), (-12.72, 0.01)], flock, 72)
    cap.label("NIKKOR", 5.1, lambda x, y: (-x, -12.84, y), enamel)
    for a in (-145, -53, 44, 123):
        standard["arc_section"](
            cap,
            [(31.57, -5.04), (25.32, -5.04), (25.4, -4.02), (31.57, -3.22)],
            a,
            a + 39,
            enamel,
        )

    native_scene.world = bpy.data.worlds.new("Plena optical workshop")
    native_scene.cycles.max_bounces = 36
    native_scene.cycles.transmission_bounces = 32
    native_scene["nominalLengthFromFlangeMM"] = 139.5
    native_scene["filterThreadMM"] = 82
    native_scene["opticalConstruction"] = (
        "16 elements in 14 groups, including 4 ED, 1 SR and 1 aspherical"
    )
    native_scene["referenceSection"] = (
        "Nikon Imaging global product optical layout, traced to published flange length"
    )
    native = []
    for item, grouping, visible in parts:
        if grouping not in local_groups:
            local_groups[grouping] = bpy.data.collections.new(grouping)
            workshop.children.link(local_groups[grouping])
        obj = item.finalize(
            uv_scale=46 if shell in item.materials or focus in item.materials else 0,
            uv_materials=(shell, focus),
        )
        bpy.context.collection.objects.unlink(obj)
        local_groups[grouping].objects.link(obj)
        native.append(obj)
        if visible:
            standard["merge"](item, runtime, None)
    source = (
        Path(__file__).resolve().parents[2]
        / ".review/atelier/nikon-reference/nikkor-z135-plena.blend"
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(source), {native_scene}, compress=True)
    for obj in native:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    bpy.data.scenes.remove(native_scene)
    for collect in local_groups.values():
        bpy.data.collections.remove(collect)
    bpy.data.collections.remove(workshop)
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
    body = runtime.finalize(uv_scale=46, uv_materials=(shell, focus))
    body["opticalVariant"] = 3
    return body


if __name__ == "__main__":
    bpy.context.preferences.filepaths.save_version = 0
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_distance = 0.265
            view.region_3d.view_location = (0, 0, 0.064)
            view.region_3d.view_rotation = Vector((0.48, -0.83, 0.33)).to_track_quat(
                "Z", "Y"
            )
            view.clip_start = 0.0005
            view.overlay.show_floor = False
            view.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
