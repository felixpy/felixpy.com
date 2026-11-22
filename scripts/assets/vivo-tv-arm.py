import math

from product_solids import block, edge, frame, front_plate, outline, pin, placed, subtract


def link(name, start, end, width, height, mat):
    x, h, z = start
    dx, dz = end[0] - x, end[2] - z
    length = math.hypot(dx, dz)
    obj = edge(block(name, 0, 0, 0, length, height, width, 3, mat), 1.1)
    obj.rotation_euler.z = math.atan2(-dz, dx)
    obj.location = ((x + end[0]) * 0.0005, -(z + end[2]) * 0.0005, h * 0.001)
    return obj


def cable_clips(x, z, desk, post, elbow, nylon):
    y = desk + 172
    collar = pin("G · sliding cable clip collar", (x, y, z), (x, y + 28, z), 19.7, nylon, 64)
    subtract(collar, [pin("Clearance for pole", (x, y - 1, z), (x, y + 29, z), 17.7, nylon, 64)])
    subtract(collar, [block("Split in collar", x + 19, y + 14, z, 6, 30, 2.4, 0.2, nylon)])
    loop = block("G · open cable saddle", x, y + 14, z - 24.7, 29, 22, 19, 5.2, nylon)
    subtract(loop, [block("Saddle opening", x, y + 14, z - 24.7, 24, 24, 14.4, 3.6, nylon)])
    subtract(loop, [block("Cable entry", x + 8, y + 14, z - 34, 5.5, 24, 6, 0.4, nylon)])
    edge(loop, 0.36, 2)
    dx, dz = elbow[0] - post[0], elbow[2] - post[2]
    span = math.hypot(dx, dz)
    cross_section = [
        (-14, 12), (-14, 20.8), (14, 20.8), (14, -16.5), (18, -16.5),
        (18, -19), (14.5, -19), (14.5, -37), (-13.8, -37),
        (-13.8, -18.7), (8.5, -18.7), (8.5, -21), (-11.4, -21),
        (-11.4, -34.5), (12, -34.5), (12, 18.4), (-11.6, 18.4), (-11.6, 12),
    ]
    clip = edge(outline("H · arm clip and cable channel", cross_section, -8.5, 17, nylon), 0.5, 2)
    placed(clip, frame(((post[0] + elbow[0]) / 2, post[1], (post[2] + elbow[2]) / 2),
                       (dz / span, 0, -dx / span), (0, 1, 0), (dx / span, 0, dz / span)))


def build(finish):
    steel = finish("VIVO · black powder-coated steel", "292b2b", 0.58, 0.38)
    nylon = finish("VIVO · black injection moulding", "202222", 0.04, 0.57)
    fastener = finish("VIVO · black oxide hardware", "414341", 0.78, 0.33)
    zinc = finish("VIVO · zinc washers", "83827e", 0.78, 0.36)
    mount_y = -50
    h = mount_y + 54
    x, z, desk = 158, -225, -466
    post = (x, h - 41, z)
    elbow = (3, h - 41, -245)
    neck = (0, h, -91)
    pad = edge(block("Grommet base · neoprene pad", x, desk + 1, z, 85, 2, 82, 11, nylon), 0.5)
    shoe = edge(block("Grommet base · formed steel shoe", x, desk + 6.25, z, 84, 8.5, 80, 10, steel), 1.1)
    hub = pin("Clamp hub", (x, desk + 10.5, z), (x, desk + 37, z), 23.8, steel)
    for piece in (pad, shoe, hub):
        subtract(piece, [pin("Through bolt clearance", (x, desk - 1, z), (x, desk + 38, z), 4.5, steel)])
    for name, bottom, top in (("Lower post", 37, 260), ("Upper post", 260.3, 513.5)):
        post_tube = pin(name, (x, desk + bottom, z), (x, desk + top, z), 17.5, steel, 64)
        subtract(post_tube, [pin("Post bore", (x, desk + bottom - 1, z),
                                 (x, desk + top + 1, z), 14.8, steel, 64)])
    pin("Post end cap", (x, desk + 513.5, z), (x, desk + 515.6, z), 17.55, nylon)
    for height in (desk + 31, desk + 257):
        pin(
            "Post grub screw",
            (x + 16, height, z),
            (x + 18.1, height, z),
            2.5,
            fastener,
            6,
        )
    load_plate = block("F · pressed grommet load plate", x, desk - 39.6, z, 75, 3.2, 39, 18, zinc)
    recess = block("F · stamped recess", x, desk - 41.2, z, 66, 2.2, 30, 14, zinc)
    bore = pin("F · tapped centre", (x, desk - 46, z), (x, desk - 37, z), 3.45, zinc)
    subtract(load_plate, [recess])
    subtract(load_plate, [bore])
    edge(load_plate, 0.45, 2)
    tip = desk - 43.6
    head_y = tip + 160
    spigot = pin("E · clamp post insert and bolt seat", (x, desk + 37, z), (x, head_y + 9, z), 14.6, steel)
    subtract(spigot, [pin("Through bolt clearance", (x, desk + 36, z), (x, head_y + 10, z), 4.5, steel)])
    subtract(spigot, [pin("Recessed bearing face", (x, head_y, z), (x, head_y + 10, z), 7.4, steel)])
    spigot["enclosedInAssembly"] = True
    pin("S-B · exposed M8 tip", (x, tip, z), (x, desk - 40, z), 4, fastener)
    shank = pin("S-B · M8 through bolt", (x, desk - 40, z), (x, head_y, z), 4, fastener)
    shank["enclosedInAssembly"] = True
    head = pin("S-B · recessed socket head", (x, head_y, z), (x, head_y + 8, z), 6.6, fastener)
    subtract(head, [pin("6 mm hex socket", (x, head_y + 4.2, z), (x, head_y + 9, z),
                        6 / math.sqrt(3), fastener, 6)])
    head["enclosedInAssembly"] = True
    cable_clips(x, z, desk, post, elbow, nylon)
    collar = pin(
        "Split post collar", (x, post[1] - 22, z), (x, post[1] + 22, z), 23.5, steel, 64
    )
    subtract(
        collar,
        [pin("Bore", (x, post[1] - 25, z), (x, post[1] + 25, z), 17.6, nylon, 64)],
    )
    link("Low articulating arm", post, elbow, 24, 36, steel)
    link("Raised articulating arm", (elbow[0], h, elbow[2]), neck, 24, 36, steel)
    for px, pz, lo, hi in [
        (elbow[0], elbow[2], h - 63, h + 22),
        (neck[0], neck[2], h - 23, h + 23),
    ]:
        pin("Swivel journal", (px, lo, pz), (px, hi, pz), 18, steel)
        pin("Swivel thrust washer", (px, hi, pz), (px, hi + 1.3, pz), 15, zinc)
        pin(
            "Swivel socket head", (px, hi + 1.3, pz), (px, hi + 4.1, pz), 7, fastener, 6
        )
    for side in (-1, 1):
        ear = front_plate("Tilt clevis cheek", side * 15, h, -77, 4, 41, 43, 1.4, steel)
        edge(ear, 0.7)
    pin("Horizontal tilt shaft", (-21, h, -79), (21, h, -79), 7, fastener)
    quadrant = [(0, 57), (17, 58), (31, 63), (47, 75), (78, 101), (88, 108),
                (99, 109), (107, 105), (111, 97), (111, 53), (109, 44),
                (92, 23), (85, 12), (82, 4), (82, 0)]
    right = quadrant + [(a, -b) for a, b in reversed(quadrant[:-1])]
    perimeter = right + [(-a, b) for a, b in reversed(right[1:-1])]
    plate = outline("VESA centre plate", [(a, h + b) for a, b in perimeter], -55, 3, steel)
    holes = [
        pin(
            "75 and 100 mm bores",
            (sx * u, h + sy * u, -57),
            (sx * u, h + sy * u, -50),
            2.8,
            nylon,
            20,
        )
        for u in (37.5, 50)
        for sx in (-1, 1)
        for sy in (-1, 1)
    ]
    fastenings = []
    wing_shape = [(85, 106), (92, 110), (99, 109), (105, 104), (213, -36),
                  (218, -44), (218, -52), (214, -60), (207, -66), (198, -68),
                  (189, -65), (88, 12), (87, 39), (59, 55), (55, 61),
                  (56, 69)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            row = mount_y + sy * 100
            wing = outline(
                "300 × 200 adapter wing",
                [(sx * a, row + b) for a, b in wing_shape],
                -52,
                3.0,
                steel,
            )
            bolt_locations = [(sx * 96, row + dy) for dy in ((24, 49) if sy == 1 else (57, 96))]
            fastenings.extend(bolt_locations)
            eyes = [(sx * 150, row), (sx * 200, row - 50)]
            cutouts = [pin("Punched mounting eye", (a, b, -54), (a, b, -47), 4.8, nylon)
                       for a, b in eyes]
            cutouts.extend(pin("Adapter screw hole", (a, b, -54), (a, b, -47), 3.1, nylon)
                           for a, b in bolt_locations)
            subtract(wing, cutouts)
            edge(wing, 0.7, 2)
            lip_x, lip_y = eyes[1]
            lip = pin("Pressed rim · unused adapter eye", (lip_x, lip_y, -53.2), (lip_x, lip_y, -52),
                      8.6, steel)
            subtract(lip, [pin("Open rim", (lip_x, lip_y, -54), (lip_x, lip_y, -51), 4.8, nylon)])
            edge(lip, 0.42, 2)
            a, b = eyes[0]
            for name, low, high, radius, material in [
                ("VESA standoff", -49, -43.9, 7.4, nylon),
                ("VESA fastener washer", -52.8, -52, 7.0, zinc),
            ]:
                ring = pin(name, (a, b, low), (a, b, high), radius, material)
                subtract(
                    ring,
                    [
                        pin(
                            "Clearance for M6",
                            (a, b, low - 1),
                            (a, b, high + 1),
                            3.2,
                            material,
                        )
                    ],
                )
            pin("VESA bolt shank", (a, b, -53.5), (a, b, -37), 2.92, fastener)
            cap = pin("VESA M6 cap", (a, b, -55.7), (a, b, -52.8), 5.1, fastener, 24)
            subtract(cap, [pin("Hex socket", (a, b, -56), (a, b, -54), 2.7, nylon, 6)])
    for a, b in fastenings:
        holes.append(pin("Adapter screw bore", (a, b, -56), (a, b, -50), 3.2, steel))
        cap = pin("Adapter M6 screw", (a, b, -57), (a, b, -55), 5.3, fastener, 28)
        for w, height in ((1.05, 5), (5, 1.05)):
            subtract(cap, [front_plate("Cross recess", a, b, -56.68, w, height, 2, 0.24, nylon)])
        pin("S-A · M6x8 adapter shank", (a, b, -55), (a, b, -47), 2.98, fastener, 24)
    subtract(plate, holes)
    edge(plate, 0.8)
