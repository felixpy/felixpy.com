import math

import bpy
from blender_parts import barrel, block, xyz


def subtract(solid, cutter):
    cut = solid.modifiers.new(cutter.name, "BOOLEAN")
    cut.operation = "DIFFERENCE"
    cut.object = cutter
    bpy.context.view_layer.objects.active = solid
    bpy.ops.object.modifier_apply(modifier=cut.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def fasten(board, head, x, bottom, shell):
    subtract(
        board,
        barrel("Timber pilot hole", (x, bottom + 15, 0), (x, bottom + 27, 0), 1.00),
    )
    shank = barrel("Plain shank", (x, bottom + 3.12, 0), (x, bottom + 23.2, 0), 1.12)
    tip = barrel(
        "Tapered wood screw point",
        (x, bottom + 23.2, 0),
        (x, bottom + 25.96, 0),
        1.12,
        24,
        0.04,
    )
    thread = []
    pitch = 1.12
    for step in range(217):
        a = math.tau * step / 18
        y = 11.5 + pitch * step / 18
        taper = min(1, (25.96 - y) / 2.76)
        thread.append(
            [
                (x + r * taper * math.cos(a), bottom + y + dy, r * taper * math.sin(a))
                for r, dy in ((1.07, -0.32), (1.44, 0), (1.07, 0.32))
            ]
        )
    crest = shell("Rolled thread", thread)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (shank, tip, crest):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = shank
    bpy.ops.object.join()
    shank.name = "Rolled shank and wood point"
    matrix = shank.matrix_world.copy()
    shank.parent = head
    shank.matrix_world = matrix
    shank["insideCabinetDoor"] = True


def running_gear(board, shell):
    bottom = -1140
    axle_y = bottom + 5.8
    subtract(
        board, block("Continuous 5 mm head guide groove", (301, 11, 5), (0, 1136.5, 0))
    )
    carriers, tyres, fasteners = [], [], []
    for x in (-94, 94):
        subtract(
            board, block("51 mm sheave pocket", (51.25, 18, 10.25), (x, bottom + 7, 0))
        )
        carrier = block(
            "TT40000 moulded carrier", (50.8, 21.75, 9.9), (x, bottom + 5, 0)
        )
        subtract(
            carrier,
            block("Lengthwise track clearance", (53, 9, 5.8), (x, bottom - 3.7, 0)),
        )
        subtract(carrier, block("Axle cavity", (18.3, 19.6, 6.8), (x, axle_y - 2.3, 0)))
        subtract(
            carrier, barrel("Axle drilling", (x, axle_y, -7), (x, axle_y, 7), 1.57)
        )
        for offset in (-20, 20):
            sx = x + offset
            subtract(
                carrier,
                barrel(
                    "Fixing screw pilot",
                    (sx, bottom - 8, 0),
                    (sx, bottom + 18, 0),
                    1.46,
                ),
            )
            subtract(
                carrier,
                barrel(
                    "Screw recess",
                    (sx, bottom + 0.64, 0),
                    (sx, bottom + 3.44, 0),
                    2.86,
                    24,
                    1.36,
                ),
            )
            screw = barrel(
                "Countersunk fixing screw",
                (sx, bottom + 0.97, 0),
                (sx, bottom + 3.22, 0),
                2.45,
                28,
                1.18,
            )
            for width, depth in ((2.7, 0.47), (0.47, 2.7)):
                subtract(
                    screw,
                    block("Cross recess", (width, 0.92, depth), (sx, bottom + 1.06, 0)),
                )
            fasten(board, screw, sx, bottom, shell)
            fasteners.append(screw)
        carriers.append(carrier)
        profile = [
            (-3.04, 1.56),
            (-3.04, 7.85),
            (-2.73, 8.25),
            (-1.94, 8.23),
            (-1.41, 7.46),
            (-0.82, 6.98),
            (0, 6.8),
            (0.82, 6.98),
            (1.41, 7.46),
            (1.94, 8.23),
            (2.73, 8.25),
            (3.04, 7.85),
            (3.04, 1.56),
        ]
        angles = [i * math.tau / 48 for i in range(48)]
        tyre = shell(
            "TT40000 concave acetal tyre",
            [
                [(radius * math.cos(a), radius * math.sin(a), z) for a in angles]
                for z, radius in profile
            ],
            True,
        )
        tyre.location = xyz((x, axle_y, 0))
        for face in tyre.data.polygons:
            face.use_smooth = abs(face.normal.y) < 0.98
        tyres.append(tyre)
        fasteners.append(
            barrel("Captive steel axle", (x, axle_y, -4.96), (x, axle_y, 4.96), 1.52)
        )

    def extrusion(name, outline):
        return shell(
            name, [[(x, y, z) for z, y in outline] for x in (-284, 284)], radius=0.14
        )

    tracks = [
        extrusion(
            "TT41621 crowned floor rail",
            [
                (-8.3, 0),
                (4.7, 0),
                (4.7, 1.20),
                (2.4, 1.72),
                (1.25, 2.44),
                (1.00, 5.84),
                (1.32, 6.28),
                (1.35, 6.81),
                (1.12, 7.40),
                (0.68, 7.85),
                (0, 8),
                (-0.68, 7.85),
                (-1.12, 7.40),
                (-1.35, 6.81),
                (-1.32, 6.28),
                (-1.0, 5.84),
                (-1.18, 3.08),
                (-1.98, 2.05),
                (-3.45, 1.50),
                (-8.3, 1.27),
            ],
        ),
        extrusion(
            "TT41921 overhead T guide",
            [
                (-8.3, 0),
                (4.7, 0),
                (4.7, -1.30),
                (1.46, -1.30),
                (1.46, -9.59),
                (1.29, -10.28),
                (0.84, -10.82),
                (0, -11),
                (-0.84, -10.82),
                (-1.29, -10.28),
                (-1.46, -9.59),
                (-1.46, -1.30),
                (-8.3, -1.30),
            ],
        ),
    ]
    return {
        "pocket-carriers": carriers,
        "pocket-tyres": tyres,
        "pocket-fasteners": fasteners,
        "pocket-floor-track": tracks[:1],
        "pocket-head-track": tracks[1:],
    }
