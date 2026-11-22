import math

import bpy
from blender_parts import barrel, bevel, block, xyz


def front_optics(device):
    def extrusion(name, finish, profile, left, right, smooth=False):
        return device.loft(
            name,
            finish,
            [[(x, y, z) for y, z in profile] for x in (left, right)],
            smooth,
        )

    def jacket(radius):
        return [
            (16.1 + radius * math.sin(a), 54.4 + radius * math.cos(a))
            for a in (math.radians(-36 + step * 247 / 48) for step in range(49))
        ]

    outer, inner = jacket(13.5), jacket(12.55)
    front_lip = (5.15, 64.3)
    rear_lip = (8.1, 43.3)
    jacket_section = (
        outer + [rear_lip, (8.3, 44.3)] + inner[::-1] + [(5.5, 63.3), front_lip]
    )
    shell = extrusion(
        "Slotted aluminium extrusion with forward cutoff lip",
        "titanium",
        jacket_section,
        -248.4,
        248.4,
    )
    for face in list(shell.data.polygons)[1:49]:
        face.use_smooth = True
    for sign in (-1, 1):
        for name, finish, a, b in [
            ("Elastomer cap seal", "rubber", 248.4, 248.65),
            ("Moulded end cap", "abs", 248.65, 250),
        ]:
            cap = extrusion(
                name, finish, outer + [rear_lip, front_lip], a * sign, b * sign
            )
            bevel(cap, 0.17, 2)
            for face in list(cap.data.polygons)[1:49]:
                face.use_smooth = True
    reflector = [(10.9 + 0.62 * i + 0.042 * i * i, 63.6 - 2.45 * i) for i in range(9)]
    extrusion(
        "Eight-facet aluminium reflector",
        "silver",
        reflector + [(y + 0.45, z) for y, z in reflector[::-1]],
        -244,
        244,
    )
    lens = [
        (6.65 + i * 0.317 + 0.20 * math.sin(i * math.pi / 12), 62.7 - i * 1.44)
        for i in range(13)
    ]
    extrusion(
        "Recessed precision exit optic",
        "lens",
        lens + [(y + 0.65, z) for y, z in lens[::-1]],
        -244,
        244,
    )
    for lip, y, z in [
        ("Front glare baffle", 5.9, 63.6),
        ("Rear optic retainer", 9.05, 44.1),
    ]:
        device.add(block(lip, (489, 1.1, 1.0), (0, y, z), 0.2), "abs")
    for sign in (-1, 1):
        device.add(
            block(
                "Optic end mask", (4.3, 1.05, 17.8), (sign * 246.15, 8.44, 54.1), 0.4
            ),
            "abs",
        )


def spring_clamp(device):
    def slice_xz(name, finish, sections):
        def face(z, lo, hi, width):
            w = width * 0.5
            return [
                (-w + 0.75, lo, z),
                (w - 0.75, lo, z),
                (w, lo + 0.75, z),
                (w, hi - 0.75, z),
                (w - 0.75, hi, z),
                (-w + 0.75, hi, z),
                (-w, hi - 0.75, z),
                (-w, lo + 0.75, z),
            ]

        return device.loft(name, finish, [face(*row) for row in sections])

    slice_xz(
        "Spring clamp upper casting",
        "abs",
        [
            (51, 15.3, 27.6, 35),
            (43, 12, 25.3, 37),
            (23, 7.1, 20.1, 41),
            (4, 2.3, 15.8, 47.4),
            (-12, 2.1, 15.5, 47.4),
            (-56, 2.1, 15.5, 47.4),
            (-63, 1.9, 15.6, 45.5),
        ],
    )
    slice_xz(
        "Upper shell thin metallic reveal",
        "titanium",
        [
            (50.5, 26.45, 28.15, 34.4),
            (43, 24.25, 25.95, 36.3),
            (23, 19.05, 20.75, 40.2),
            (4, 14.75, 16.45, 46.7),
            (-12, 14.45, 16.15, 46.7),
            (-60.8, 14.45, 16.15, 46.7),
        ],
    )
    device.add(
        block("3.8 mm front bezel keeper", (47.4, 6.1, 2.4), (0, -0.75, 4.55), 0.6),
        "abs",
    )
    device.add(
        block("Front glass silicone contact", (45.9, 3.2, 0.72), (0, -2.05, 3.13), 0.3),
        "rubber",
    )
    device.add(
        block("Top saddle grip insert", (44.1, 2.05, 12.2), (0, 1.7, -2.35), 0.48),
        "rubber",
    )
    for z, bottom in [(1, 0), (-1.1, -0.36), (-3.2, -1.04), (-5.3, -1.58)]:
        device.add(
            block(
                "Compliant transverse saddle ridge",
                (43.7, 1.17 - bottom, 0.9),
                (0, (1.17 + bottom) / 2, z),
                0.27,
            ),
            "rubber",
        )
    pivot_y, pivot_z = -6, -53
    for x in (-19.5, 19.5):
        device.add(
            block("Rear clevis cheek", (7.1, 8.8, 15), (x, -2.5, -57.5), 1.6), "abs"
        )
        device.add(
            barrel(
                "Pivot sleeve",
                (x - 3.6, pivot_y, pivot_z),
                (x + 3.6, pivot_y, pivot_z),
                5.9,
                40,
            ),
            "abs",
        )
    device.add(
        barrel(
            "Steel hinge spindle",
            (-23.22, pivot_y, pivot_z),
            (23.22, pivot_y, pivot_z),
            2.35,
            36,
        ),
        "silver",
    )

    fixed_parts = set(device.collection.objects)

    def jaw_plate(title, finish, lo, hi, half, thickness):
        def ring(t):
            y = pivot_y - 28.6 * t
            z = pivot_z + 40.4 * t
            return [
                (-half, y + dy, z + dz)
                for dy, dz in ((-thickness, -thickness), (thickness, thickness))
            ] + [
                (half, y + dy, z + dz)
                for dy, dz in ((thickness, thickness), (-thickness, -thickness))
            ]

        jaw = device.loft(title, finish, [ring(lo), ring(hi)])
        bevel(jaw, 1.5, 3)

    jaw_plate("Pivoted counterweight jacket", "abs", -0.035, 1.06, 34, 3.9)
    jaw_plate("Metal counterweight outer cover", "titanium", 0.13, 1.045, 33.1, 4.18)
    device.add(
        block(
            "Floating rear saddle with broad silicone pad",
            (57, 18.3, 6.5),
            (0, -33.2, -9.39),
            2.0,
        ),
        "rubber",
    )
    for sign in (-1, 1):
        for y in (-38, -34, -30):
            device.add(
                block(
                    "Stepped contact island",
                    (10.7, 3.1, 2.05),
                    (sign * 20.4, y, -5.83),
                    0.66,
                ),
                "rubber",
            )
    moving_parts = set(device.collection.objects) - fixed_parts
    hinge = bpy.data.objects.new("Halo 2 • spring jaw rotation axis", None)
    hinge["haloMechanicalAxis"] = "Rotates about local X"
    hinge.location = xyz((0, pivot_y, pivot_z))
    hinge.empty_display_size = 0.009
    device.collection.objects.link(hinge)
    bpy.context.view_layer.update()
    for part in moving_parts:
        part.parent = hinge
        part.matrix_parent_inverse = hinge.matrix_world.inverted()
    device.add(
        barrel(
            "Recessed presence sensor collar", (0, 11.4, 34), (0, 9.9, 34.5), 4.55, 36
        ),
        "rubber",
    )
    device.add(
        barrel(
            "Ultrasonic sensor mesh face", (0, 10.1, 34.45), (0, 9.72, 34.57), 3.37, 36
        ),
        "silver",
    )


def rear_optic(device):
    def rear(x, y, z):
        return x, y + 18.3, -62.7 + z

    device.ply(
        "PC/ABS surround and rear LED carrier",
        "abs",
        [
            (2.5, 83, 45, 5),
            (1.2, 88.3, 49.4, 6.3),
            (-3.7, 89.4, 49.8, 6.5),
            (-5.0, 87.8, 48.7, 6.6),
        ],
        transform=rear,
    )

    def dome(x, y, z):
        return x, y + 18.3, -67.35 + z + 2.55 * (x / 44) ** 2 + 1.7 * (y / 24) ** 2

    rings = []
    for scale, depth in [
        (1, 0.8),
        (0.995, 0.12),
        (0.94, -1.9),
        (0.8, -4.3),
        (0.61, -6.4),
        (0.34, -8.0),
        (0.07, -8.55),
    ]:
        ring = []
        for step in range(96):
            theta = step * math.tau / 96
            dx, dy = math.cos(theta), math.sin(theta)
            rx = math.copysign(abs(dx) ** 0.315, dx) * 43.25 * scale
            ry = math.copysign(abs(dy) ** 0.315, dy) * 23.7 * scale
            ring.append(dome(rx, ry, depth))
        rings.append(ring)
    device.loft(
        "Three-curvature opal diffuser • top, bottom and lateral spread",
        "frost",
        rings,
        True,
    )


def diode_boards(device):
    material = bpy.data.materials.new("White solder mask on aluminium-core board")
    material.diffuse_color = (0.82, 0.82, 0.76, 1)
    phosphor = bpy.data.materials.new("Dual-colour LED package")
    phosphor.diffuse_color = (0.94, 0.8, 0.52, 1)

    def install(part, finish):
        part.name = "Halo 2 • " + part.name
        part["haloEngineeringApproximation"] = "Emitter layout beneath the closed optic"
        part.data.materials.append(finish)
        for collection in list(part.users_collection):
            collection.objects.unlink(part)
        device.collection.objects.link(part)

    install(
        block("Front emitter board", (476, 3.5, 0.8), (0, 13.4, 43.5), 0.15), material
    )
    for i in range(48):
        install(
            block(
                "Dual-colour front emitter",
                (2.7, 1.55, 0.6),
                ((i - 23.5) * 9.85, 13.4, 44.18),
            ),
            phosphor,
        )
    install(
        block("Rear emitter board", (62, 28, 0.75), (0, 18.3, -68.1), 1.05), material
    )
    for x in (-23, -8, 8, 23):
        for y in (10.5, 25.5):
            install(
                block("Dual-colour bias emitter", (3.2, 2.6, 0.55), (x, y, -68.74)),
                phosphor,
            )


def build(device):
    front_optics(device)
    spring_clamp(device)
    rear_optic(device)
    for finish, (_, pieces) in device.surfaces.items():
        for piece in pieces:
            piece["haloFinish"] = finish
            piece.name = "Halo 2 • " + piece.name
    diode_boards(device)
    device.finish()
