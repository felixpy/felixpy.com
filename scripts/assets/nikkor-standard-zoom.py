import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector, geometry


def control_knurl(shape, radius, start, end, rubber, shoulders, rows=4, columns=128, peak=.46):
    height = end - start
    shape.turn(
        [
            (start - 0.35, radius - 0.1),
            (start, radius + 0.10),
            (end, radius + 0.10),
            (end + 0.35, radius - 0.1),
        ],
        shoulders,
        128,
    )
    points, faces = [], []
    for j in range(rows):
        for i in range(columns):
            a = math.tau * (i + (j % 2) * 0.5) / columns
            z = start + height * (j + 0.5) / rows
            for da, dz, lift in [
                (0, -0.5, 0.10),
                (0.48, 0, 0.10),
                (0, 0.5, 0.10),
                (-0.48, 0, 0.10),
                (0, 0, peak),
            ]:
                angle = a + da * math.tau / columns
                points.append(
                    (
                        (radius + lift) * math.sin(angle),
                        z + dz * height / rows,
                        (radius + lift) * math.cos(angle),
                    )
                )
            idx = len(points) - 5
            faces.extend((idx + k, idx + (k + 1) % 4, idx + 4) for k in range(4))
    shape.add(points, faces, rubber, False)


def side_controls(shape, radius, xyz, tooling, ink, gray, enamel, grip):
    def label(text, z, a, size, material=ink, italic=False):
        reading = -1 if a > 0 else 1
        shape.label(
            text,
            size,
            lambda x, y: xyz(a + reading * y / radius(z), z - reading * x, 0.55),
            material,
            italic,
        )

    def rocker(z, a, left, right):
        reading = -1 if a > 0 else 1

        def pad(z, a, width, height, lift, material):
            tooling["panel"](shape, radius, z, a, height, width, lift, material)

        pad(z, a, 11.2, 4.35, 0.44, enamel)
        pad(z + 1.65, a, 6.2, 3.48, 0.97, grip)
        for dz in (-0.51, 0.12, 0.85):
            pad(z + 2.6 + dz, a, 0.23, 3.1, 1.13, enamel)
        for dz, text in [(2.9, left), (-2.9, right)]:
            dz *= reading
            label(text, z + dz, a + 0.129 * reading, 1.85)
            shape.pipe(
                [
                    xyz(a + 0.081 * reading, z + dz - 1.58, 0.51),
                    xyz(a + 0.081 * reading, z + dz + 1.58, 0.51),
                ],
                0.072,
                ink,
                5,
            )

    for angle in (0, -1.85):
        tooling["button"](shape, radius, 44.6, angle, 4.6, 1.48, enamel, grip)
    label("L-Fn", 44.6, -1.65, 2.18)
    label("NIKKOR", 44.6, -0.91, 3.0)
    shape.label(
        "S",
        8.05,
        lambda x, y: xyz(-1.10 + y / radius(44.6), 44.6 - 1.75 * x, 0.55),
        gray,
        True,
    )
    rocker(12.4, -1.42, "A", "M")
    rocker(12.4, -2.10, "FULL", "LIMIT")
    rocker(44.6, 2.06, "ON", "OFF")
    label("CLICK", 44.6, 1.84, 2.28)
    label("Nikon", 44.6, 1.45, 3.25, gray, True)


def radial(r, z, a):
    return r * math.sin(a), z, r * math.cos(a)


def arc_section(shape, section, start, end, material):
    steps = max(4, math.ceil((end - start) / 3))
    rows = [
        [
            radial(r, z, math.radians(start + (end - start) * j / steps))
            for r, z in section
        ]
        for j in range(steps + 1)
    ]
    shape.rings(rows, material, False)


def screw_circle(r, cx=0, cy=0, count=24):
    return [
        (
            cx + r * math.sin(i * math.tau / count),
            cy + r * math.cos(i * math.tau / count),
        )
        for i in range(count)
    ]


def mount(shape, steel, rubber, dark, gold, contact_rotation=0, contact_height=0):
    shape.turn(
        [
            (1.35, 31.6),
            (0.88, 32.0),
            (0.3, 31.94),
            (-0.09, 31.53),
            (-0.10, 30.98),
            (0.30, 30.78),
        ],
        rubber,
        128,
    )
    shape.turn([(1.42, 31.1), (0.42, 31.1), (0.05, 30.92), (0, 30.7)], steel, 128)
    holes = []
    for az in (-144, -70, 11, 88, 159):
        x, _, y = radial(28.95, 0, math.radians(az))
        holes.append((x, y, 1.16, True))
    x, _, y = radial(29.30, 0, math.radians(50))
    holes.append((x, y, 1.5, False))
    outlines = [screw_circle(30.7, count=144), screw_circle(24.50, count=144)]
    outlines += [screw_circle(r, x, y) for x, y, r, _ in holes]
    points, edges = [], []
    for outline in outlines:
        base = len(points)
        points.extend(Vector(p) for p in outline)
        edges.extend(
            (base + i, base + (i + 1) % len(outline)) for i in range(len(outline))
        )
    verts, _, tris, _, _, _ = geometry.delaunay_2d_cdt(points, edges, [], 0, 1e-6)

    def on_flange(face):
        center = sum((verts[i] for i in face), Vector((0, 0))) / len(face)
        return center.length > 24.48 and all(
            (center.x - x) ** 2 + (center.y - y) ** 2 > (r - 0.02) ** 2
            for x, y, r, _ in holes
        )

    shape.add(
        [(p.x, 0, p.y) for p in verts], [t for t in tris if on_flange(t)], steel, False
    )
    for i, (x, y, radius, has_screw) in enumerate(holes):
        rims = [
            [(xx, h, yy) for xx, yy in screw_circle(radius * s, x, y)]
            for h, s in [(0, 1), (0.22, 0.88), (1.3, 0.85)]
        ]
        shape.rings(rims, dark, False, False)
        if not has_screw:
            shape.add(rims[-1], [tuple(range(24))], rubber, False)
            continue
        top = [
            [(xx, z, yy) for xx, yy in screw_circle(r, x, y)]
            for r, z in [(0.94, 0.40), (0.98, 0.22), (0.82, 0.12)]
        ]
        shape.rings(top, steel, False)
        a = i * 0.63
        cruciform = [
            (-0.52, -0.10),
            (-0.11, -0.10),
            (-0.11, -0.52),
            (0.11, -0.52),
            (0.11, -0.10),
            (0.52, -0.10),
            (0.52, 0.10),
            (0.11, 0.10),
            (0.11, 0.52),
            (-0.11, 0.52),
            (-0.11, 0.10),
            (-0.52, 0.10),
        ]
        shape.add(
            [
                (
                    x + dx * math.cos(a) - dy * math.sin(a),
                    0.106,
                    y + dx * math.sin(a) + dy * math.cos(a),
                )
                for dx, dy in cruciform
            ],
            [tuple(range(12))],
            dark,
            False,
        )
    shape.turn(
        [
            (0.05, 24.50),
            (-0.20, 24.63),
            (-1.78, 24.63),
            (-2.05, 24.35),
            (-2.05, 23.00),
            (-1.7, 22.7),
        ],
        steel,
        128,
    )
    for a, b in [(-174, -130), (-78, -23), (7, 58), (101, 145)]:
        arc_section(
            shape,
            [
                (24.28, -1.93),
                (25.55, -1.93),
                (26.25, -2.22),
                (26.25, -3.46),
                (25.94, -3.73),
                (24.10, -3.73),
                (23.85, -3.44),
            ],
            a,
            b,
            steel,
        )
    arc_section(
        shape,
        [
            (23.8, -2.10),
            (24.25, -2.62),
            (23.75, -4.28),
            (22.7, -4.55),
            (21.62, -4.2),
            (21.5, -2.3),
        ],
        -62 + contact_rotation,
        15 + contact_rotation,
        dark,
    )
    for i in range(11):
        a = -58.3 + 6.82 * i + contact_rotation
        arc_section(
            shape,
            [
                (21.97, -4.15 - contact_height),
                (22.04, -4.40 - contact_height),
                (22.73, -4.50 - contact_height),
                (23.68, -4.20 - contact_height),
                (23.71, -3.97 - contact_height),
            ],
            a - 1.65,
            a + 1.65,
            gold,
        )


GROUPS = (
    ((15, 39, 176), (27, 99, 140)),
    ((106, 109, 139), (114, 156, 131), (149, 161, 131)),
    ((385, 402, 105), (421, 410, 105), (429, 434, 105)),
    ((454, 469, 110), (468, 474, 110)),
    ((474, 495, 106), (479, 519, 106), (534, 525, 106)),
    ((561, 550, 77), (566, 575, 77)),
    ((577, 590, 77), (599, 596, 77)),
    ((665, 675, 74), (702, 680, 74), (711, 704, 74)),
    ((738, 725, 81), (759, 739, 81)),
    ((835, 807, 102), (842, 833, 102)),
)


def optic_geometry(part, interfaces, number, clear, coatings, cell):
    scale = 142 / 820
    rims = []
    for i, (center, shoulder, radius) in enumerate(interfaces):
        r, sag = radius * scale, (shoulder - center) * scale
        vertex = (822 - center) * scale
        curvature = (r * r + sag * sag) / (2 * abs(sag))
        profile = []
        for j in range(15):
            rho = max(0.012, r * j / 14)
            curve = curvature - math.sqrt(max(0, curvature * curvature - rho * rho))
            profile.append((vertex - math.copysign(curve, sag), rho))
        part.turn(profile, coatings.get((number, i), clear), 80)
        rims.append(profile[-1])
    part.turn(rims, cell, 80)


def merge(source, destination, omit):
    base = len(destination.vertices)
    destination.vertices.extend(source.vertices)
    for material in source.materials:
        if material not in destination.materials:
            destination.materials.append(material)
    slots = [destination.materials.index(m) for m in source.materials]
    for face, idx, smooth in zip(source.faces, source.inks, source.surface):
        if source.materials[idx] != omit:
            destination.faces.append(tuple(base + i for i in face))
            destination.inks.append(slots[idx])
            destination.surface.append(smooth)


def finish_zoom(body, Sculpture, make, controls, grips, glass, hardware):
    _, _, enamel = grips
    rubber, edge = hardware
    cell = make("S II · anti-reflection baffles", "1e2325", 0.17, 0.62)
    iris = make("S II · blackened spring-steel iris", "222528", 0.25, 0.62)
    steel = make("Z24-70 machined bayonet · nickel plating", "c8caca", 0.77, 0.24)
    brass = make("Z-mount contact · gold over nickel", "e6bf68", 0.84, 0.25)
    clear = make("Z24-70 optical interfaces · native cross section", "e0e8e0", 0, 0.015)
    optical = clear.node_tree.nodes.get("Principled BSDF")
    optical.inputs["Transmission Weight"].default_value = 1
    optical.inputs["IOR"].default_value = 1.56
    components = []
    bayonet = Sculpture("Z bayonet · lugs, gasket and CPU contacts")
    mount(bayonet, steel, rubber, enamel, brass)
    components.append(bayonet)
    coats = []
    for layer in glass:
        coat = layer.copy()
        coat.name = layer.name.replace(" / ", " / 24-70 S II / ")
        coats.append(coat)
    coatings = {(0, 0): coats[0], (1, 0): coats[1], (8, 0): coats[2], (9, 1): coats[3]}
    for i, profile in enumerate(GROUPS):
        optical_group = Sculpture(
            f"Glass group {i + 1:02} · {len(profile) - 1} element"
        )
        optic_geometry(optical_group, profile, i, clear, coatings, cell)
        components.append(optical_group)
    iris_unit = Sculpture("Eleven curved aperture blades")
    controls["diaphragm"](iris_unit, 11, 47.7, 14.0, 4.0, iris, edge)
    components.append(iris_unit)
    tube = Sculpture("Seated optical cells and internal light baffles")
    scale = 142 / 820
    tube.turn(
        [
            (142, 39.9),
            (142, 38.55),
            (141.68, 38.26),
            (139.65, 38.13),
            (139.36, 36.7),
            (139.12, 36.0),
            (136.05, 31.05),
            (135.62, 30.31),
        ],
        enamel,
        128,
    )
    for z in (140.15, 140.90, 141.65):
        tube.turn([(z + 0.12, 38.35), (z, 38.05), (z - 0.17, 38.34)], rubber, 128)
    for front, rear in zip(GROUPS, GROUPS[1:]):
        z1, r1 = (822 - front[-1][1]) * scale, front[-1][2] * scale
        z2, r2 = (822 - rear[0][1]) * scale, rear[0][2] * scale
        tube.turn(
            [
                (z1, r1 + 0.27),
                (z1 - 0.32, r1 - 0.05),
                (z2 + 0.4, r2 + 0.25),
                (z2, r2 - 0.02),
            ],
            cell,
            96,
        )
        if z1 - z2 > 8:
            for j in range(1, 9):
                t = j / 10
                z, r = z1 + (z2 - z1) * t, r1 + (r2 - r1) * t
                tube.turn(
                    [(z + 0.12, r + 0.25), (z, r - 0.3), (z - 0.13, r + 0.25)], cell, 96
                )
    tube.turn(
        [
            (-1.55, 23.6),
            (-3.88, 23.6),
            (-4.1, 22.8),
            (-4.1, 19.2),
            (-3.95, 18.98),
            (-2.40, 18.7),
            (-2.18, 18.45),
            (-1.92, 17.55),
        ],
        enamel,
        128,
    )
    for z in (-2.65, -3.12, -3.59):
        tube.turn([(z + 0.09, 18.95), (z, 18.65), (z - 0.1, 18.95)], rubber, 112)
    components.append(tube)
    source_scene = bpy.data.scenes.new("NIKKOR Z 24–70 mm S II")
    source_scene.unit_settings.system = "METRIC"
    for s in [body, *components]:
        part = s.finalize(uv_scale=46 if s is body else 0, uv_materials=grips)
        bpy.context.collection.objects.unlink(part)
        source_scene.collection.objects.link(part)
    out = (
        Path(__file__).resolve().parents[2] / ".review" / "atelier" / "nikon-reference"
    )
    out.mkdir(parents=True, exist_ok=True)
    source = out / "nikkor-z24-70-sii.blend"
    bpy.data.libraries.write(str(source), {source_scene}, compress=True)
    for part in list(source_scene.collection.objects):
        data = part.data
        bpy.data.objects.remove(part, do_unlink=True)
        bpy.data.meshes.remove(data)
    bpy.data.scenes.remove(source_scene)
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
    for s in components:
        merge(s, body, clear)
    pupil = make("Z24-70 entrance pupil · relayed light", "151917", 0, 0.54)
    ring = [radial(4.04, 47.63, i * math.tau / 64) for i in range(64)]
    body.add(ring, [tuple(range(64))], pupil, False)


if __name__ == "__main__":
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Lens workshop")
    bpy.context.preferences.filepaths.save_version = 0
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_distance = 0.28
            space.region_3d.view_location = (0, 0, 0.06)
            space.region_3d.view_rotation = Vector((0.68, -0.64, -0.5)).to_track_quat(
                "Z", "Y"
            )
            space.clip_start = 0.0006
            space.shading.color_type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
