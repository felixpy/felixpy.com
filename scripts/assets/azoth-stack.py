import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


def rectangle(x, z, w, d):
    return [
        (x + i * w / 2, z + j * d / 2) for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]


def circle(x, z, radius, steps=12):
    return [
        (
            x + radius * math.cos(i * math.tau / steps),
            z + radius * math.sin(i * math.tau / steps),
        )
        for i in range(steps)
    ]


def planar_region(outline, openings):
    points, paths = [], []
    for loop in [outline, *openings]:
        paths.append(list(range(len(points), len(points) + len(loop))))
        points.extend(Vector(p) for p in loop)
    verts, _, triangles, _, _, regions = delaunay_2d_cdt(points, [], paths, 1, 0.00001)
    top_faces = [
        face for face, origins in zip(triangles, regions) if list(origins) == [0]
    ]
    if not top_faces:
        raise ValueError("Empty sheet outline")
    return verts, top_faces


def sheet(obj, outline, openings, base, top, material, tilt=0.084, project=None):
    verts, top_faces = planar_region(outline, openings)
    edges = {}
    for face in top_faces:
        for a, b in zip(face, face[1:] + face[:1]):
            key = tuple(sorted((a, b)))
            if key in edges:
                del edges[key]
            else:
                edges[key] = (a, b)
    n = len(verts)
    faces = [tuple(reversed(face)) for face in top_faces]
    faces.extend(tuple(i + n for i in face) for face in top_faces)
    faces.extend((a, b, b + n, a + n) for a, b in edges.values())
    positions = [(x, h - tilt * z, z) for h in (base, top) for x, z in verts]
    obj.add(
        [project(*p) for p in positions] if project else positions,
        faces,
        material,
        False,
    )


def crop_rear(part):
    mesh = bmesh.new()
    mesh.from_mesh(part.data)
    bmesh.ops.bisect_plane(
        mesh,
        geom=[*mesh.verts, *mesh.edges, *mesh.faces],
        dist=0.0000001,
        plane_co=(0, 0.0648, 0),
        plane_no=(0, 1, 0),
        clear_outer=True,
    )
    mesh.to_mesh(part.data)
    mesh.free()


def rear_io(obj, tools, make, alloy, rubber, steel, marking):
    def loop(x, h, w, d, r):
        return [(x + u, h + v) for u, v in tools["corners"](w, d, r)]

    def panel(boundary, holes, rear, inner, mat):
        sheet(obj, boundary, holes, rear, inner, mat, 0, lambda x, z, h: (x, h, z))

    x = -114.1
    mode = 114.7
    h = 18.6
    usb = loop(x, h, 26.2, 13.2, 6.1)
    toggle = loop(mode, h, 27, 13.2, 6.1)
    plate = loop(0, h, 100.2, 13.2, 6.2)
    panel(
        loop(0, 18.85, 330.7, 19.15, 1.7), [usb, toggle, plate], -69.45, -64.79, alloy
    )
    mouth = loop(x, h, 9.15, 3.62, 1.78)
    bore = loop(x, h, 8.55, 3.03, 1.45)
    panel(usb, [mouth], -69.04, -66.8, rubber)
    panel(mouth, [bore], -69.13, -65.2, steel)
    panel(bore, [], -64.85, -64.55, rubber)
    panel(loop(x, h, 6.48, 0.76, 0.32), [], -68.17, -64.6, rubber)
    contact = make("Azoth · USB hard gold contacts", "ab8d54", 0.84, 0.33)
    for i in range(12):
        xx = x + (i - 5.5) * 0.50
        for dh in (-0.39, 0.39):
            obj.add(
                [
                    (xx + u, h + dh, z)
                    for u, z in [
                        (-0.105, -67.88),
                        (0.105, -67.88),
                        (0.105, -65.4),
                        (-0.105, -65.4),
                    ]
                ],
                [(0, 1, 2, 3)],
                contact,
                False,
            )
    track = loop(mode, h, 18.5, 6.6, 2.8)
    panel(toggle, [track], -69.07, -66.3, rubber)
    panel(track, [], -65.9, -65.5, alloy)
    panel(loop(mode - 4.2, h, 7.7, 5.7, 1.25), [], -69.8, -65.8, rubber)
    for u in (-2.4, -0.8, 0.8, 2.4):
        obj.pipe(
            [(mode - 4.2 + u, h - 1.85, -69.8), (mode - 4.2 + u, h + 1.85, -69.8)],
            0.24,
            marking,
            6,
            0.65,
        )
    panel(plate, [], -69.04, -66, alloy)
    obj.label(
        "R E P U B L I C   O F   G A M E R S",
        2.6,
        lambda u, v: (-u, h + v, -69.09),
        rubber,
    )
    for u in (-42.7, 42.7):
        obj.pipe([(u, h, -68.9), (u, h, -69.18)], 1.25, steel, 16)
        obj.pipe([(u - 0.6, h, -69.2), (u + 0.6, h, -69.2)], 0.15, rubber, 6)


def screen_art(material):
    import numpy as np

    w, h = 320, 152
    v, u = np.mgrid[0:h, 0:w]
    u = u / (w - 1)
    v = v / (h - 1)
    background = np.zeros((h, w, 4), dtype=np.float32)
    background[:, :, :3] = [0.011, 0.013, 0.031]
    for y, width, colour in [
        (0.42, 0.18, [0.026, 0.10, 0.62]),
        (0.45, 0.075, [0.065, 0.50, 0.90]),
        (0.48, 0.045, [0.60, 0.29, 0.80]),
        (0.49, 0.015, [0.92, 0.77, 0.80]),
    ]:
        line = y + 0.60 * (u - 0.5) + 0.42 * np.sin(u * 3.8 - 0.4)
        glow = np.exp(-(((v - line) / width) ** 2)) * np.sin(u * np.pi) ** 0.8
        background[:, :, :3] += glow[:, :, None] * np.array(colour)
    red = np.exp(-(((u - 0.79) / 0.21) ** 2) - ((v - 0.57) / 0.28) ** 2)
    background[:, :, :3] += red[:, :, None] * np.array([0.62, 0.012, 0.075])
    background[:, :, 3] = 1
    texture = bpy.data.images.new(
        "Azoth · original OLED colour field", w, h, alpha=False
    )
    texture.pixels.foreach_set(background.clip(0, 1).ravel())
    texture.pack()
    nodes = material.node_tree
    tex = nodes.nodes.new("ShaderNodeTexImage")
    tex.image = texture
    shader = nodes.nodes["Principled BSDF"]
    for channel in ("Base Color", "Emission Color"):
        nodes.links.new(tex.outputs["Color"], shader.inputs[channel])
    shader.inputs["Emission Strength"].default_value = 0.72


def stepped_shell(obj, outline, profile, inner, material, slope):
    rows = [[(x, h - slope * z, z) for x, z in outline(inset)] for h, inset in profile]
    for h in (profile[-1][0], profile[0][0]):
        rows.append([(x, h - slope * z, z) for x, z in inner])
    obj.rings(rows + [rows[0]], material, False, False)


def socket_ring(obj, x, z, floor, ceiling, radius, material):
    cross = [
        (0.61, 2.07),
        (-0.61, 2.07),
        (-0.61, 0.64),
        (-2.08, 0.64),
        (-2.08, -0.64),
        (-0.61, -0.64),
        (-0.61, -2.07),
        (0.61, -2.07),
        (0.61, -0.64),
        (2.08, -0.64),
        (2.08, 0.64),
        (0.61, 0.64),
    ]
    sheet(
        obj,
        circle(x, z, radius),
        [[(x + u, z + v) for u, v in cross]],
        floor,
        ceiling,
        material,
        0,
    )


def snow_plunger(stem, corners, material):
    cross = [
        (0.56, 2),
        (-0.56, 2),
        (-0.56, 0.58),
        (-2, 0.58),
        (-2, -0.58),
        (-0.56, -0.58),
        (-0.56, -2),
        (0.56, -2),
        (0.56, -0.58),
        (2, -0.58),
        (2, 0.58),
        (0.56, 0.58),
    ]
    walls = [
        [
            (s * x, z)
            for x, z in [
                (2.68, -3.17),
                (3.31, -3.17),
                (3.31, 3.17),
                (2.68, 3.17),
                (2.32, 2.89),
                (2.32, 2.56),
                (2.68, 2.56),
                (2.68, -2.56),
                (2.32, -2.56),
                (2.32, -2.89),
            ]
        ]
        for s in (-1, 1)
    ]
    deck = corners(7.12, 7.02, 0.42, 3)

    def plane(contour, holes, h):
        def ccw(loop):
            area = sum(
                x * v - u * z for (x, z), (u, v) in zip(loop, loop[1:] + loop[:1])
            )
            return loop if area > 0 else list(reversed(loop))

        points, faces = planar_region(ccw(contour), [ccw(hole) for hole in holes])
        stem.add([(x, h, z) for x, z in points], faces, material, False)

    def lift(boundary, levels, cap=True):
        rows = [
            [(x * k + dx, h, z * k + dz) for x, z in boundary]
            for h, k, dx, dz in levels
        ]
        stem.rings(rows, material, False, False)
        if cap:
            cap_points = [(x, z) for x, _, z in rows[-1]]
            plane(cap_points, [], levels[-1][0])

    crown, seat = 3.58, 1.50
    runners = [rectangle(sign * 2.77, 0, 1.06, 4.38) for sign in (-1, 1)]
    cam = rectangle(0, 2.92, 2.72, 0.64)
    pole = circle(0, 0, 0.80, 16)
    plane(deck, [cross, *walls], crown)
    plane(deck, [pole, *runners, cam], seat)
    lift(deck, [(crown, 1, 0, 0), (seat, 1, 0, 0)], False)
    lift(cross, [(crown, 1, 0, 0), (7.05, 1, 0, 0), (7.25, 0.944, 0, 0)])
    for wall in walls:
        lift(wall, [(crown, 1, 0, 0), (7.05, 1, 0, 0), (7.18, 0.987, 0, 0)])
    lift(pole, [(seat, 1, 0, 0), (-1.76, 1, 0, 0), (-1.99, 0.86, 0, 0)])
    for runner in runners:
        lift(runner, [(seat, 1, 0, 0), (-0.70, 1, 0, 0), (-0.91, 0.973, 0, 0)])
    lift(cam, [(seat, 1, 0, 0), (0.24, 1, 0, 0.11), (-0.41, 0.86, 0, -0.14)])


def snow_contacts(part, metal, silver):
    def blade(centres):
        section = [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]
        rows = []
        for x, h, z, w, thick in centres:
            rows.append([(x + u * w, h, z + v * thick) for u, v in section])
        part.rings(rows, metal, False)

    blade(
        [
            (-3.81, -8.60, 2.54, 0.38, 0.22),
            (-3.81, -8.31, 2.54, 0.56, 0.28),
            (-3.81, -3.74, 2.54, 0.56, 0.28),
            (-3.27, -3.36, 2.62, 1.64, 0.28),
            (-2.72, -2.94, 2.94, 2.70, 0.25),
            (-2.12, -2.07, 3.28, 3.72, 0.21),
            (-1.55, -1.06, 3.48, 4.68, 0.20),
            (-1.44, -0.42, 3.62, 4.78, 0.20),
            (-1.45, 0.24, 3.54, 4.82, 0.19),
            (-1.64, 0.52, 3.28, 4.04, 0.19),
        ]
    )
    blade(
        [
            (2.54, -8.60, 5.08, 0.39, 0.23),
            (2.54, -8.31, 5.08, 0.57, 0.28),
            (2.54, -3.70, 5.08, 0.57, 0.28),
            (2.25, -3.46, 4.98, 1.14, 0.29),
            (1.12, -3.16, 4.76, 3.41, 0.28),
            (0.65, -2.84, 4.67, 4.34, 0.28),
            (0.65, -0.53, 4.68, 4.34, 0.27),
            (0.59, -0.22, 4.59, 3.86, 0.24),
        ]
    )
    for z in (3.83, 4.41):
        part.form((-0.30, -0.72, z), (0.58, 0.48, 0.20), silver)


def add_stack(Sculpture, make, tools, keys, carbon, finish):
    parts = []
    slab = tools["slab"]
    deck_slope = 0.084
    black = make("Azoth · moulded guide polymer", "24272b", 0.04, 0.56)
    ink = make("Azoth · PCB silk", "c4c6b9", 0.02, 0.68)
    solder = make("Azoth · solder and socket terminals", "b4b1a6", 0.87, 0.37)
    brass = make("Azoth · switch contact brass", "ae8646", 0.83, 0.43)
    foam = make("Azoth · PORON cut edge", "262527", 0, 0.93)
    pcb_mat = make("Azoth · black FR4 soldermask", "242a29", 0.15, 0.54)
    rubber = make("Azoth · silicone base damper", "4b494a", 0, 0.85)
    milky = make("Azoth · NX Snow lower POM", "c6c9c5", 0, 0.47)
    pom = make("Azoth · snow-white POM stem", "e0ddd2", 0, 0.35)
    clear = make("Azoth · clear switch lid", "a3b4b4", 0, 0.21, 0.4)
    clear.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.25
    clear.surface_render_method = "BLENDED"
    layout = [(-160, -62), (111, -62), (111, -38), (160, -38), (160, 60), (-160, 60)]
    cutouts, sockets, flex_slots = [], [], []
    for row, key, x, z, width in keys:
        cutouts.append(rectangle(x, z, 14.05, 14.05))
        sockets.extend(
            (
                circle(x, z, 2.12),
                circle(x - 3.81, z + 2.54, 0.91),
                circle(x + 2.54, z + 5.08, 0.91),
                circle(x - 5.08, z, 0.94),
                circle(x + 5.08, z, 0.94),
            )
        )
        if width >= 38 and key != "Space":
            cutouts.extend(
                rectangle(x + sign * 11.9, z + 0.4, 6.7, 12.2) for sign in (-1, 1)
            )
        if key == "Space":
            cutouts.extend(
                rectangle(x + sign * 50, z + 0.4, 6.7, 12.2) for sign in (-1, 1)
            )
        if row in (1, 2, 3, 4) and width < 25 and x < 95 and key not in ("Q", "A"):
            flex_slots.append(rectangle(x, z + 9.4, 15, 0.65))
    carbon_plate = Sculpture("Azoth | CNC carbon switch plate")
    sheet(carbon_plate, layout, cutouts + flex_slots, 21.65, 23.15, carbon)
    for x, word in ((-46, "ROG"), (1, "AZOTH EXTREME")):
        carbon_plate.label(
            word,
            1.6,
            lambda u, v, x=x: (x + u, 23.19 - (53.5 - v) * deck_slope, 53.5 - v),
            ink,
        )
    parts.append(finish(carbon_plate))

    def add_layer(name, holes, base, top, surface):
        layer = Sculpture("Azoth | " + name)
        sheet(layer, layout, holes, base, top, surface)
        parts.append(finish(layer, True))
        return layer

    add_layer("Die-cut PORON plate foam", cutouts, 18.50, 21.65, foam)
    add_layer("PORON switch pad", sockets, 18.0, 18.50, foam)
    add_layer("Hot-swap circuit board", sockets, 16.4, 18.0, pcb_mat)
    reliefs = [
        rectangle(-41, -13, 25, 15),
        rectangle(75, 20, 10, 7),
        rectangle(70, -8, 11, 6),
    ]
    add_layer("Silicone bottom mat", reliefs, 10.8, 12.0, rubber)
    ribs = Sculpture("Azoth | Silicone mat chevrons")
    for x in range(-153, 156, 10):
        for z in range(-54, 56, 9):
            if (x > 106 and z < -32) or any(
                abs(x - a) < w and abs(z - b) < d
                for a, b, w, d in [(-41, -13, 17, 12), (75, 20, 11, 9), (70, -8, 11, 8)]
            ):
                continue
            ribs.pipe(
                [
                    (x + u, 12.13 - deck_slope * (z + v), z + v)
                    for u, v in [(-3, -2), (0, 1), (3, -2)]
                ],
                0.7,
                rubber,
                5,
            )
    parts.append(finish(ribs, True))
    gasket = Sculpture("Azoth | Lateral suspension pads and spring seats")
    for x in (-126, -60, 33, 91):
        for z in (-62, 60):
            slab(
                gasket,
                x,
                z,
                16,
                4.3,
                1.2,
                [(20.1, 0.4), (21.65, 0), (23.65, 0.3)],
                black,
                deck_slope,
            )
    parts.append(finish(gasket, True))
    base = Sculpture("NX Snow | POM base and locating posts")
    well = tools["corners"](10.8, 10.8, 0.65, 3)
    stepped_shell(
        base,
        lambda inset: tools["corners"](13.85 - 2 * inset, 13.85 - 2 * inset, 0.75, 3),
        [(-4.75, 0.6), (-4.1, 0), (-0.1, 0), (0.2, 0.22)],
        well,
        milky,
        0,
    )
    terminals = [(-3.81, 2.54), (2.54, 5.08)]
    sheet(
        base,
        well,
        [circle(0, 0, 1.03, 16), *[rectangle(u, v, 0.70, 0.42) for u, v in terminals]],
        -4.75,
        -3.8,
        milky,
        0,
    )
    base.turn([(-7.93, 0.01), (-7.93, 1.44), (-7.76, 1.77), (-4.74, 1.9)], milky, 16)
    base.turn([(-3.79, 1.03), (-7.51, 1.03), (-7.55, 0.01)], milky, 16)
    base.turn(
        [(-3.82, 1.41), (-3.05, 1.41), (-2.86, 1.28), (-2.86, 1.04), (-3.82, 1.04)],
        milky,
        16,
    )
    for sign in (-1, 1):
        base.rings(
            [
                [(x + sign * 5.08, h, z) for x, z in circle(0, 0, r, 10)]
                for r, h in [(0.81, -4.69), (0.81, -6.82), (0.61, -7.38)]
            ],
            milky,
        )
        for side in (-1, 1):
            slab(
                base,
                sign * 3.88,
                side * 1.33,
                1.13,
                1.50,
                0.22,
                [(-3.81, 0), (-0.10, 0), (0.22, 0.12)],
                milky,
            )
    top = Sculpture("NX Snow | Clear clipped upper housing")
    shell = [
        (15.1, 15.1, 0.0),
        (15.6, 15.6, 0.37),
        (15.6, 15.6, 0.97),
        (12.0, 12.1, 3.55),
        (11.55, 11.6, 4.07),
        (7.6, 7.83, 4.07),
        (7.6, 7.83, 3.74),
        (9.4, 10.1, 3.45),
        (13.45, 13.36, 0.80),
        (13.55, 13.48, 0.0),
    ]
    shell = [
        [(x, h, z) for x, z in tools["corners"](w, d, 0.62, 3)] for w, d, h in shell
    ]
    top.rings(shell + [shell[0]], clear, False, False)
    for sign in (-1, 1):
        for fore in (-1, 1):
            slab(
                top,
                sign * 6.86,
                fore * 3.82,
                1.14,
                2.17,
                0.28,
                [(-1.86, 0.18), (-1.45, 0), (0.37, 0.04)],
                clear,
            )
    stem = Sculpture("NX Snow | Walled cross stem")
    snow_plunger(stem, tools["corners"], pom)
    spring = Sculpture("NX Snow | Return spring")
    rise = [
        -3.62 + 5.01 * (0.16 * t + 0.84 * (t * t * (3 - 2 * t)))
        for t in (i / 96 for i in range(97))
    ]
    spiral = [
        (1.68 * math.cos(i * math.tau / 16), h, 1.68 * math.sin(i * math.tau / 16))
        for i, h in enumerate(rise)
    ]
    spring.pipe(spiral, 0.15, solder, 6)
    contacts = Sculpture("NX Snow | Stamped crosspoint contacts")
    snow_contacts(contacts, brass, solder)
    hot = Sculpture("Azoth | Hot-swap socket and SMT terminals")
    outline = [(x - 0.63, z + 3.81) for x, z in tools["corners"](11.52, 5.96, 0.88, 4)]
    sheet(
        hot,
        outline,
        [rectangle(u, v, 1.62, 1.15) for u, v in terminals],
        -7.91,
        -6.74,
        black,
        0,
    )
    for u, v in terminals:
        sheet(
            hot,
            rectangle(u, v, 2.5, 2.35),
            [rectangle(u, v, 1.15, 0.65)],
            -7.99,
            -7.78,
            brass,
            0,
        )
        for sign in (-1, 1):
            hot.rings(
                [
                    [(xx, h, zz) for xx, zz in rectangle(u, v + sign * shift, w, d)]
                    for h, shift, w, d in [
                        (-7.84, 0.40, 0.91, 0.17),
                        (-7.42, 0.22, 0.79, 0.14),
                        (-7.15, 0.17, 0.68, 0.11),
                        (-6.95, 0.32, 0.63, 0.12),
                    ]
                ],
                brass,
                False,
            )
        slab(
            hot,
            u + (-1.58 if u < 0 else 1.58),
            v,
            2.25,
            1.85,
            0.22,
            [(-7.51, 0.12), (-7.2, 0), (-6.72, 0)],
            solder,
        )
    for specimen, enclosed in [
        (base, False),
        (top, False),
        (stem, False),
        (spring, True),
        (contacts, True),
        (hot, True),
    ]:
        original = finish(specimen, enclosed)
        if not enclosed:
            original["productInstanced"] = True
        if specimen is stem:
            mould = bmesh.new()
            mould.from_mesh(original.data)
            bmesh.ops.remove_doubles(mould, verts=mould.verts, dist=1e-8)
            bmesh.ops.recalc_face_normals(mould, faces=mould.faces)
            mould.to_mesh(original.data)
            mould.free()
        for index, (row, key, x, z, width) in enumerate(keys):
            instance = original if index == 0 else original.copy()
            if index:
                bpy.context.collection.objects.link(instance)
            instance.name = f"{specimen.name} · {index + 1:02d} {key}"
            instance.location = (x / 1000, -z / 1000, (23.15 - deck_slope * z) / 1000)
            parts.append(instance)
    wires = Sculpture("Azoth | Stabilizer wires with separate housings")
    for _, key, x, z, width in keys:
        if width < 38:
            continue
        reach = 50 if key == "Space" else 11.9
        h = 22.45 - deck_slope * z
        wires.pipe(
            [
                (x - reach, h, z + 0.3),
                (x - reach, h, z + 5.8),
                (x - reach + 1, h, z + 6.8),
                (x + reach - 1, h, z + 6.8),
                (x + reach, h, z + 5.8),
                (x + reach, h, z + 0.3),
            ],
            0.76,
            solder,
            10,
        )
        for sign in (-1, 1):
            slab(
                wires,
                x + reach * sign,
                z + 0.4,
                6.45,
                11.8,
                0.65,
                [(18.1, 0.3), (22.4, 0), (23.45, 0.2)],
                black,
                deck_slope,
            )
    parts.append(finish(wires, True))
    return parts
