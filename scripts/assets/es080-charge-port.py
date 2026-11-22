import math

import bpy
from mathutils import Matrix, Vector


def build(body, shell, sculpt, group, solids, ivory, silicone, black, steel):
    radius = 35.59
    height = 78.15
    stem_x = 11.0
    anchor = Vector(
        (stem_x / 1000, math.sqrt(radius**2 - stem_x**2) / 1000, height / 1000)
    )
    joint = group("ES-080 · retained port cover", parent=body)
    joint.location = anchor
    joint["es080Joint"] = "port-cover"
    joint["opening"] = 0.0
    joint.id_properties_ui("opening").update(min=0.0, max=1.0)
    joint["releaseMm"] = 4.2
    joint["swingDegrees"] = 87.0
    for path, axis, formula in [
        ("location", 1, f"{anchor.y} + .0042 * min(1, self['opening'] * 4)"),
        ("rotation_euler", 1, "-1.51843645 * max(0, (self['opening'] - .25) / .75)"),
    ]:
        driver = joint.driver_add(path, axis).driver
        driver.use_self = True
        driver.expression = formula
    socket = group("ES-080 · socket behind silicone seal", parent=body)
    socket["es080Inside"] = True
    underside = group("ES-080 · hidden face of the cover", parent=joint)
    underside["es080Inside"] = True

    def rounded_section(w, h, corner, radial):
        half = w / 2
        xs = sorted(
            set(
                [round((half - corner) * i / 6, 8) for i in range(-6, 7)]
                + [
                    round(
                        side * (half - corner + corner * math.sin(i * math.pi / 16)), 8
                    )
                    for i in range(1, 9)
                    for side in (-1, 1)
                ]
            )
        )
        top, bottom = [], []
        for u in xs:
            edge = max(0, abs(u) - half + corner)
            dh = h / 2 - corner + math.sqrt(max(0, corner**2 - edge**2))
            x = (radius + radial) * math.sin(u / radius)
            depth = -(radius + radial) * math.cos(u / radius)
            top.append((x, height + dh, depth))
            bottom.append((x, height - dh, depth))
        return top + bottom[::-1]

    def mould(name, sections, material, owner, hollow=False):
        form = sculpt("ES-080 · " + name)
        rows = [rounded_section(*settings) for settings in sections]
        n = len(rows[0])
        faces = []
        for j in range(len(rows) if hollow else len(rows) - 1):
            a, b = j * n, ((j + 1) % len(rows)) * n
            faces.extend(
                (a + i, a + (i + 1) % n, b + (i + 1) % n, b + i) for i in range(n)
            )
        if not hollow:
            for start in (0, (len(rows) - 1) * n):
                faces.extend(
                    (start + i, start + i + 1, start + n - 2 - i, start + n - 1 - i)
                    for i in range(n // 2 - 1)
                )
        form.add([p for row in rows for p in row], faces, material)
        obj = form.finalize()
        obj.data.set_sharp_from_angle(angle=math.radians(45))
        obj.parent = owner
        if owner in (joint, underside):
            obj.data.transform(Matrix.Translation(-anchor))
        return obj

    cutter = solids["front_plate"](
        "Rear mould opening", 0, height, -34.0, 25.8, 13.7, 16, 3.6, ivory
    )
    solids["subtract"](shell, [cutter])
    mould(
        "recessed charging aperture and raised rim",
        [
            (31.6, 16.5, 4.6, -0.90),
            (31.6, 16.5, 4.6, 0.24),
            (31.2, 16.1, 4.45, 0.65),
            (30.5, 15.4, 4.25, 0.83),
            (28.55, 13.6, 3.7, 0.83),
            (28.15, 13.15, 3.5, 0.43),
            (26.15, 12.30, 3.15, -1.3),
            (23.20, 10.90, 2.7, -4.9),
            (24.1, 11.6, 2.95, -5.25),
            (26.65, 13.0, 3.25, -2.2),
        ],
        ivory,
        body,
        hollow=True,
    )
    mould(
        "silicone port flap",
        [
            (27.25, 12.25, 3.1, -0.10),
            (27.90, 12.83, 3.4, 0.22),
            (28.0, 12.9, 3.4, 1.02),
            (27.7, 12.55, 3.32, 1.28),
            (27.12, 12.0, 3.15, 1.39),
        ],
        silicone,
        joint,
    )
    mould(
        "double compression bead under flap",
        [
            (24.0, 10.50, 2.75, 0.06),
            (24.20, 10.75, 2.85, -0.37),
            (24.55, 11.0, 3.0, -0.58),
            (24.40, 10.85, 2.9, -0.83),
            (23.70, 10.20, 2.6, -1.07),
            (24.12, 10.68, 2.8, -1.34),
            (24.27, 10.78, 2.9, -1.53),
            (23.70, 10.22, 2.67, -1.86),
            (22.65, 9.20, 2.40, -1.86),
            (22.70, 9.25, 2.42, 0.06),
        ],
        silicone,
        underside,
        hollow=True,
    )
    stem = solids["pin"](
        "ES-080 · silicone retaining neck",
        (stem_x, height, -33.96),
        (stem_x, height, -26.2),
        1.22,
        silicone,
    )
    stem.parent = underside
    stem.location -= anchor

    def at_socket(name, x, depth, width, h, thickness, corner, material):
        obj = solids["front_plate"](
            "ES-080 · " + name, x, height, depth, width, h, thickness, corner, material
        )
        obj.parent = socket
        return obj

    bed = at_socket("carbon socket insert", 0, -29.8, 25.6, 13.3, 1.8, 3.1, black)
    opening = solids["front_plate"](
        "Insert aperture", -2.4, height, -29.8, 9.1, 3.48, 4, 1.48, black
    )
    solids["subtract"](bed, [opening])
    mouth = at_socket(
        "USB-C rolled metal shell", -2.4, -29.97, 9.02, 3.4, 3.9, 1.55, steel
    )
    opening = solids["front_plate"](
        "Receptacle aperture", -2.4, height, -29.97, 8.48, 2.9, 5.2, 1.28, steel
    )
    solids["subtract"](mouth, [opening])
    at_socket("USB-C tongue", -2.4, -29.46, 6.72, 0.68, 3.15, 0.31, black)
    at_socket("connector back wall", -2.4, -27.92, 8.55, 2.96, 0.45, 1.25, black)
