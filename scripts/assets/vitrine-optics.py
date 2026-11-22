import itertools
import math

LENSES = (
    {
        "name": "NIKKOR Z 14-24mm f2.8 S",
        "profile": [
            (0, 29.3),
            (1.7, 33.1),
            (3.6, 34.9),
            (22.8, 34.9),
            (24, 35.3),
            (31, 35.4),
            (34.5, 37.4),
            (51.5, 37.4),
            (54, 38.5),
            (58.4, 40.4),
            (60, 40.8),
            (80.3, 40.8),
            (82.1, 40.1),
            (88, 43.1),
            (90, 43.8),
            (108, 43.8),
            (109, 42.8),
            (112, 42.2),
            (115, 42.2),
        ],
        "rings": [
            (24.4, 31.4, 128, 0.22),
            (59.0, 80.0, 93, 0.6),
            (89.0, 105.0, 105, 0.5),
        ],
    },
    {
        "name": "NIKKOR Z 24-70mm f2.8 S II",
        "mark": "24-70/2.8 S II",
        "rim": "NIKKOR Z 24-70mm 1:2.8 S II  ø77",
        "h": 142,
        "profile": [
            (0, 30.1),
            (1.4, 32),
            (3.4, 35.0),
            (22.1, 35.0),
            (26, 37.0),
            (32.5, 37.4),
            (34, 37.1),
            (54.7, 37.1),
            (59.5, 40.3),
            (92.6, 40.3),
            (94.8, 39.5),
            (98.4, 40.2),
            (100, 41.1),
            (120, 41.1),
            (122, 40.5),
            (124.3, 42.0),
            (132, 42.0),
            (133.8, 40.8),
            (138.4, 40.9),
            (139.2, 40.0),
            (142, 39.9),
        ],
        "rings": [
            (27.2, 32.8, 138, 0.19),
            (59.6, 90.1, 116, 0.65),
            (100.4, 119.3, 123, 0.5),
        ],
        "focal": (56, ["24", "28", "35", "50", "70"]),
        "rim_z": 129.5,
    },
    {
        "name": "NIKKOR Z 70-200mm f2.8 VR S II",
        "profile": [
            (0, 30.2),
            (2.2, 32.5),
            (4.2, 35.0),
            (23, 35.0),
            (25.1, 35.6),
            (28.4, 39.4),
            (32.2, 40.6),
            (41.1, 40.6),
            (43.2, 39.7),
            (64.4, 39.7),
            (67.1, 41.8),
            (74.6, 42.5),
            (77.2, 42.7),
            (101, 42.7),
            (102, 43.0),
            (122, 43.0),
            (123.5, 42.4),
            (140.7, 42.4),
            (143.2, 44.0),
            (177.4, 44.0),
            (179.4, 43.3),
            (183.3, 44.7),
            (187.6, 44.7),
            (188.7, 44),
            (192.5, 44.5),
            (197.5, 44.5),
            (198.5, 43.1),
            (202.2, 43.2),
            (203.6, 42.0),
            (208, 41.9),
        ],
    },
    {
        "name": "NIKKOR Z 135mm f1.8 S Plena",
        "profile": [
            (0, 30.0),
            (2.1, 32.5),
            (4.0, 35.1),
            (22, 35.1),
            (32.6, 40.3),
            (34.2, 41.5),
            (41.6, 41.5),
            (45.5, 42.5),
            (49.7, 44.9),
            (67.6, 44.9),
            (72.2, 47.6),
            (101.4, 47.6),
            (103.1, 47.0),
            (109.4, 47.1),
            (111.1, 48.5),
            (121.3, 48.5),
            (122.5, 47.8),
            (128.4, 47.6),
            (130.6, 45.5),
            (131.4, 43.9),
            (136.1, 43.9),
            (137.5, 42.0),
            (139.5, 42),
        ],
    },
    {"name": "NIKKOR Z 58mm f0.95 S Noct"},
)


def build_lenses(Sculpture, make, selected=None):
    import runpy
    from pathlib import Path

    import bpy

    controls = runpy.run_path(str(Path(__file__).with_name("nikkor-fittings.py")))
    zoom = runpy.run_path(str(Path(__file__).with_name("nikkor-standard-zoom.py")))
    wide = runpy.run_path(str(Path(__file__).with_name("nikkor-ultrawide.py")))
    plena = runpy.run_path(str(Path(__file__).with_name("nikkor-plena.py")))
    prime = runpy.run_path(str(Path(__file__).with_name("nikkor-fast-normal.py")))
    noct = runpy.run_path(str(Path(__file__).with_name("nikkor-noct.py")))
    tele = runpy.run_path(str(Path(__file__).with_name("nikkor-telephoto.py")))

    def coating_bases():
        materials = bpy.data.materials
        return [
            materials.get("NIKKOR glass / " + layer)
            or next(
                m
                for m in materials
                if m.name.startswith("NIKKOR glass / ")
                and m.name.endswith(" / " + layer)
            )
            for layer in ("outer", "inner", "relay", "field")
        ]

    def build_super_telezoom(coatings):
        model = runpy.run_path(str(Path(__file__).with_name("nikkor-super-telezoom.py")))
        model["build"](Sculpture, make, controls, zoom, coatings)

    if selected == {5}:
        build_super_telezoom(coating_bases())
        return
    if selected == {2}:
        tele["build"](
            LENSES[2], Sculpture, make, controls, zoom, plena, prime, coating_bases()
        )
        return
    if selected == {4}:
        noct["build"](Sculpture, make, controls, zoom, prime, coating_bases())
        return
    if selected == {3}:
        mats = bpy.data.materials
        plena["build"](
            LENSES[3],
            Sculpture,
            make,
            controls,
            zoom,
            wide,
            coating_bases(),
            tuple(
                mats[name]
                for name in (
                    "Lens mount collar · anodized",
                    "Gasket · carbon black",
                    "Nikon white silk print",
                    "Nikon front collar engraving",
                )
            ),
        )
        return
    if selected == {0}:
        mats = bpy.data.materials
        wide["build"](
            LENSES[0],
            Sculpture,
            make,
            controls,
            zoom,
            coating_bases(),
            tuple(
                mats[name]
                for name in (
                    "NIKKOR barrel · black powder coat",
                    "Focus ring · charcoal elastomer",
                    "Lens mount collar · anodized",
                    "Gasket · carbon black",
                    "Nikon white silk print",
                    "Nikon front collar engraving",
                    "Lens OLED · polarizing cover",
                )
            ),
        )
        return
    grain = runpy.run_path(str(Path(__file__).with_name("product-grain.py")))
    shell = make("NIKKOR barrel · black powder coat", "222427", 0.20, 0.43)
    enamel = make("Lens mount collar · anodized", "17191d", 0.45, 0.38)
    grip = make("Focus ring · charcoal elastomer", "27282b", 0.02, 0.64)
    rubber = make("Gasket · carbon black", "131419", 0.01, 0.72)
    ink = make("Nikon white silk print", "ece9e2", 0.02, 0.52)
    gray = make("Nikon front collar engraving", "a9a9a5", 0.07, 0.52)
    lcd = make("Lens OLED · polarizing cover", "171824", 0.12, 0.17, 0.35)
    bevel = make("Diaphragm shear edges", "1a1c20", 0.16, 0.65)
    glass = []
    for label, tint in [
        ("outer", "a4a9a1"),
        ("inner", "9483a8"),
        ("relay", "789980"),
        ("field", "b2957f"),
    ]:
        m = make("NIKKOR glass / " + label, tint, 0.0, 0.034, 0.12)
        shader = m.node_tree.nodes.get("Principled BSDF")
        shader.inputs["IOR"].default_value = 1.57
        shader.inputs["Alpha"].default_value = 0.13
        m.surface_render_method = "BLENDED"
        m.use_backface_culling = False
        glass.append(m)

    grain["coat_grain"](
        "NIKKOR · elastomer and casting grain",
        [(shell, 0.24), (grip, 0.16), (enamel, 0.075)],
    )
    zoom_shell = shell.copy()
    zoom_shell.name = "S II · fine polycarbonate finish"
    next(
        node for node in zoom_shell.node_tree.nodes if node.type == "NORMAL_MAP"
    ).inputs["Strength"].default_value = 0.066

    def build_standard_zoom(spec):
        shell = zoom_shell
        shape = Sculpture(spec["name"])
        contour = spec["profile"]

        def radius(z):
            for (lo, ra), (hi, rb) in itertools.pairwise(contour):
                if z <= hi:
                    return ra + (rb - ra) * min(1, max(0, (z - lo) / (hi - lo)))
            return contour[-1][1]

        def xyz(arc, z, inset=0):
            rr = radius(z) + inset
            return (rr * math.sin(arc), z, rr * math.cos(arc))

        def mark(text, z, arc, size, material=ink, italic=False, lift=0.2):
            rr = radius(z)
            shape.label(
                text,
                size,
                lambda x, y: xyz(arc + x / rr, z + y, lift),
                material,
                italic,
            )

        shape.turn(contour, shell, 112)
        z = spec["rings"][0][0] - 1.6
        shape.turn(
            [
                (1.85, radius(1.85)),
                (3.8, radius(3.8) + 0.15),
                *[(h, r + 0.15) for h, r in contour if 3.8 < h < z - 0.4],
                (z - 0.4, radius(z) + 0.15),
                (z, radius(z)),
            ],
            enamel,
            112,
        )

        for a, b, teeth, relief in spec["rings"]:
            rr = max(radius(a), radius(b))
            if a == spec["rings"][0][0]:
                zoom["control_knurl"](shape, rr, a, b, grip, enamel)
                continue
            rows = []
            phases = [(0, 0), (0.26, 1), (0.65, 1), (0.84, 0)]
            for z, shoulder, amount in [
                (a - 0.50, -0.18, 0.08),
                (a + 0.74, 0.15, 1),
                (b - 0.74, 0.15, 1),
                (b + 0.50, -0.18, 0.08),
            ]:
                row = []
                for j in range(teeth):
                    for t, tooth in phases:
                        angle = math.tau * (j + t) / teeth
                        r = rr + shoulder + relief * amount * tooth
                        row.append((r * math.sin(angle), z, r * math.cos(angle)))
                rows.append(row)
            shape.rings(rows, grip, True, False)
            for z in (a - 0.7, b + 0.7):
                shape.turn(
                    [(z - 0.22, rr), (z, rr + 0.15), (z + 0.22, rr)], rubber, 104
                )

        mark(spec["mark"], 10.8, 0, 4.15, lift=0.36)
        mark("NIKKOR", 15.0, 0, 2.35, lift=0.36)
        controls["dot"](shape, xyz, 0, 5.1, 1.15, ink)
        mark(
            spec["rim"],
            spec["rim_z"],
            0,
            2.4,
            gray,
            lift=0.05,
        )
        if spec["focal"]:
            z, numbers = spec["focal"]
            for i, number in enumerate(numbers):
                mark(number, z, 0.03 - i * 0.28, 3.15)
            shape.plate(
                [
                    xyz(a, z + dy, 0.2)
                    for a, dy in [
                        (-0.011, -4.2),
                        (0.011, -4.2),
                        (0.011, -1.65),
                        (-0.011, -1.65),
                    ]
                ],
                ink,
                0.03,
                0.02,
            )
        zoom["side_controls"](shape, radius, xyz, controls, ink, gray, enamel, grip)
        zoom["finish_zoom"](
            shape,
            Sculpture,
            make,
            controls,
            (shell, grip, enamel),
            glass,
            (rubber, bevel),
        )
        obj = shape.finalize(uv_scale=46, uv_materials=(shell, grip, enamel))
        obj["opticalVariant"] = 1

    for index, spec in enumerate(LENSES):
        if selected is not None and index not in selected:
            continue
        if index == 2:
            tele["build"](spec, Sculpture, make, controls, zoom, plena, prime, glass)
            continue
        if index == 4:
            noct["build"](Sculpture, make, controls, zoom, prime, glass)
            continue
        if index == 3:
            plena["build"](
                spec,
                Sculpture,
                make,
                controls,
                zoom,
                wide,
                glass,
                (enamel, rubber, ink, gray),
            )
            continue
        if index == 0:
            wide["build"](
                spec,
                Sculpture,
                make,
                controls,
                zoom,
                glass,
                (shell, grip, enamel, rubber, ink, gray, lcd),
            )
            continue
        build_standard_zoom(spec)
    if selected is None or 5 in selected:
        build_super_telezoom(glass)
