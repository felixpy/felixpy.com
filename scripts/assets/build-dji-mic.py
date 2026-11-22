import math
import runpy
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
corners = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))["corners"]
finish, Sculpture = sculpt["finish"], sculpt["Sculpture"]
case = finish("Black moulded polycarbonate", "36373a", 0.13, 0.36, 0.1)
clip = finish("Bead-blasted clip alloy", "363739", 0.67, 0.34)
dark = finish("Recess and socket insulator", "141517", 0.1, 0.54)
edge = finish("Graphite elastomer", "26282a", 0, 0.61)
silver = finish("Contact nickel", "adb0ae", 0.79, 0.32)
solder = finish("Unpopulated pads and solder", "91928c", 0.59, 0.38)
gold = finish("Charge pad plating", "ceb66e", 0.71, 0.33)
white = finish("Logo in warm white", "e8ebe8", 0.11, 0.43)
orange = finish("Record accent", "e88b35", 0.14, 0.38)
led = finish("Link status lens", "80b98c", 0.08, 0.26, 0.18, 0.33)
board = finish("Graphite solder mask", "343536", 0.24, 0.44)
component = finish("IC epoxy casing", "28292a", 0.16, 0.5)
resin = finish("Smoked transparent cover", "555a5b", 0.05, 0.17, 0.72)
resin.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.20
resin.surface_render_method = "BLENDED"
assembly = Sculpture("Transmitter details")


def face(x, y, z):
    return (x, y, z)


def side(x, y, z):
    return (z, y, x)


def top(x, y, z):
    return (x, z, y)


def panel(o, x, y, width, height, radius, sections, mat, transform=face):
    rows = [
        [
            transform(x + u, y + v, z)
            for u, v in corners(
                width - 2 * inset,
                height - 2 * inset,
                max(0.03, radius - inset),
                8 if radius > 0.25 else 1,
            )
        ]
        for z, inset in sections
    ]
    o.rings(rows, mat)
    o.surface[-2:] = (False, False)


def roundface(o, x, y, sections, mat, transform=face):
    rows = [
        [
            transform(
                x + r * math.cos(a * math.tau / 48),
                y + r * math.sin(a * math.tau / 48),
                z,
            )
            for a in range(48)
        ]
        for r, z in sections
    ]
    o.rings(rows, mat)
    o.surface[-2:] = (False, False)


def outline(points, projection, mat):
    xy = [Vector((x, y, 0)) for x, y in points]
    assembly.add(
        [projection(x, y) for x, y in points], tessellate_polygon([xy]), mat, False
    )


def logo(projection):
    pieces = [
        [
            (0.03, 0.22),
            (0.04, 0.32),
            (0.11, 0.60),
            (0.14, 0.65),
            (0.19, 0.68),
            (0.43, 0.68),
            (0.40, 0.57),
            (0.25, 0.57),
            (0.23, 0.54),
            (0.20, 0.42),
            (0.20, 0.39),
            (0.23, 0.38),
            (0.42, 0.38),
            (0.46, 0.40),
            (0.57, 0.85),
            (0.73, 0.85),
            (0.61, 0.38),
            (0.57, 0.30),
            (0.52, 0.26),
            (0.46, 0.24),
            (0.11, 0.24),
        ],
        [
            (0.73, 0.67),
            (0.87, 0.67),
            (0.78, 0.32),
            (0.75, 0.23),
            (0.69, 0.15),
            (0.61, 0.10),
            (0.54, 0.09),
            (0.36, 0.09),
            (0.39, 0.20),
            (0.50, 0.20),
            (0.55, 0.22),
            (0.59, 0.26),
            (0.62, 0.32),
        ],
        [(0.91, 0.67), (1.07, 0.67), (0.99, 0.27), (0.83, 0.27)],
    ]
    for polygon in pieces:
        outline(polygon, lambda x, y: projection(x - 0.54, y - 0.46), white)


housing = Sculpture("Continuous milled chassis")
panel(
    housing,
    0,
    0,
    30.96,
    45.98,
    5.6,
    [
        (-4.85, 2.0),
        (-4.60, 0.95),
        (-4.00, 0.32),
        (-3.25, 0),
        (6.8, 0),
        (7.55, 0.26),
        (8.0, 1.05),
    ],
    case,
    lambda x, y, z: (x, min(y, 18.26), z),
)
body = housing.finalize()
cap = Sculpture("Upper acoustic cap")


def caprow(x, y, z):
    return (x, z, y + 2.23)


panel(
    cap,
    0,
    0,
    30.90,
    15.55,
    4.7,
    [
        (16.90, 0.05),
        (17.18, 0),
        (19.1, 0.10),
        (20.75, 0.55),
        (22.05, 1.42),
        (22.85, 2.72),
        (23.03, 3.55),
    ],
    case,
    caprow,
)
head = cap.finalize()


def subtract(part, cutter):
    mesh = cutter.finalize()
    bm = bmesh.new()
    bm.from_mesh(part.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0000002)
    bm.to_mesh(part.data)
    bm.free()
    modifier = part.modifiers.new("Aperture", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = mesh
    bpy.context.view_layer.objects.active = part
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(mesh, do_unlink=True)


inside = Sculpture("Removable front tray cavity")
panel(inside, 0, -1.5, 28.65, 39.8, 4.55, [(-3.6, 0.15), (-3.25, 0), (12, 0)], dark)
subtract(body, inside)

bores = Sculpture("Two rows of intake apertures and TRS opening")
for column in range(-4, 5):
    x = column * 2.75
    for direction in (-1, 1):
        inner = 0.62
        if abs(column - 2) == 1:
            inner = 1.55
        elif column == 2:
            inner = 3.52
        boundary = 6.65
        center = 1.95 + direction * (boundary + inner) / 2
        panel(
            bores,
            x,
            center,
            1.42,
            boundary - inner,
            0.63,
            [(16.5, 0), (25, 0)],
            dark,
            top,
        )
for x in (-13.4, 13.4):
    panel(bores, x, 2.22, 1.12, 8.15, 0.50, [(16.5, 0), (25, 0)], dark, top)
jack_x, jack_depth = 5.5, 1.72
roundface(bores, jack_x, jack_depth, [(2.33, 15.8), (2.33, 25)], dark, top)
subtract(head, bores)
head_interior = Sculpture("Crown wall thickness")
panel(
    head_interior,
    0,
    0,
    28.0,
    12.8,
    3.45,
    [(15.8, 0), (18.4, 0), (19.94, 0.42), (21.60, 2.68)],
    case,
    caprow,
)
subtract(head, head_interior)

cloth = finish("Woven acoustic mesh", "414247", 0.28, 0.63)
weave = bpy.data.images.new("Acoustic screen • over-under weave", width=64, height=64)
pixels = []
for row in range(64):
    for col in range(64):
        u, v = (col + 0.5) / 32, (row + 0.5) / 32
        warp, weft = abs(math.cos(math.pi * u)) ** 5, abs(math.cos(math.pi * v)) ** 5
        over = math.cos(math.pi * u) * math.cos(math.pi * v)
        shade = 0.025 + 0.18 * max(
            warp * (0.88 + 0.12 * over), weft * (0.76 - 0.18 * over)
        )
        pixels.extend([shade, shade, shade * 1.04, 1])
weave.pixels.foreach_set(pixels)
weave.pack()
tex = cloth.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = weave
cloth.node_tree.links.new(
    tex.outputs["Color"], cloth.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
)
screen = Sculpture("Stainless acoustic screen inside crown")
panel(
    screen,
    0,
    0,
    29.80,
    14.58,
    4.26,
    [(17.1, 0.15), (18.5, 0), (20, 0.48), (21.22, 1.30), (22.12, 2.42), (22.34, 3.08)],
    cloth,
    caprow,
)
mesh_screen = screen.finalize()
jack_bore = Sculpture("TRS through acoustic screen")
roundface(jack_bore, jack_x, jack_depth, [(2.29, 15.8), (2.29, 24.2)], dark, top)
subtract(mesh_screen, jack_bore)
mesh_interior = Sculpture("Acoustic liner inner face")
panel(
    mesh_interior,
    0,
    0,
    29.45,
    14.20,
    4.0,
    [(16.3, 0), (18.4, 0), (19.9, 0.48), (21.02, 1.3), (21.95, 2.40), (22.20, 3.08)],
    cloth,
    caprow,
)
subtract(mesh_screen, mesh_interior)
uv = mesh_screen.data.uv_layers.new(name="0.28 mm woven screen pitch")
for loop in mesh_screen.data.loops:
    point = mesh_screen.data.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (point.x / 0.00056, point.y / 0.00056)


def bore_surface(o, x, y, profile, material, transform):
    rows = [
        [
            transform(
                x + radius * math.cos(i * math.tau / 48),
                y + radius * math.sin(i * math.tau / 48),
                height,
            )
            for i in range(48)
        ]
        for radius, height in profile
    ]
    o.rings(rows, material, close=False)


bore_surface(
    assembly,
    jack_x,
    jack_depth,
    [(2.32, 21.8), (2.30, 22.96), (2.10, 23.02), (1.78, 22.72), (1.76, 16.18)],
    dark,
    top,
)
for height, phase in ((19.3, 0.50), (17.4, 3.8)):
    arc = [
        top(
            jack_x + 1.7 * math.cos(phase + i * 0.06),
            jack_depth + 1.7 * math.sin(phase + i * 0.06),
            height,
        )
        for i in range(16)
    ]
    assembly.pipe(arc, 0.115, silver, 6)
roundface(assembly, jack_x, jack_depth, [(1.8, 16.04), (1.8, 16.14)], dark, top)

socket = Sculpture("USB recess cutter")
panel(socket, 4.43, 2.45, 3.36, 8.91, 1.56, [(-16.8, 0), (-10.7, 0)], dark, side)
subtract(body, socket)
frame = [
    [side(4.43 + u, 2.45 + v, depth) for u, v in corners(w, h, r, 8)]
    for w, h, r, depth in [
        (3.32, 8.85, 1.54, -15.11),
        (3.30, 8.79, 1.51, -15.29),
        (2.74, 8.27, 1.22, -15.25),
        (2.70, 8.21, 1.2, -10.85),
    ]
]
assembly.rings(
    frame, finish("Socket shell • dark nickel", "69686a", 0.74, 0.43), close=False
)
panel(assembly, 4.43, 2.45, 2.73, 8.23, 1.2, [(-10.93, 0), (-10.77, 0)], dark, side)
panel(
    assembly,
    4.43,
    2.45,
    0.62,
    6.25,
    0.24,
    [(-14.56, 0.12), (-14.25, 0), (-10.90, 0)],
    component,
    side,
)
for direction in (-1, 1):
    for n in range(12):
        center = 2.45 + (n - 5.5) * 0.50
        surface = 4.43 + direction * 0.315
        assembly.add(
            [
                side(surface, center + v, depth)
                for v, depth in [
                    (-0.09, -14.15),
                    (0.09, -14.15),
                    (0.09, -11.35),
                    (-0.09, -11.35),
                ]
            ],
            [(0, 1, 2, 3)],
            gold,
            False,
        )

assembly.finalize()
assembly = Sculpture("Populated PCB and exposed shield • smoked window")
panel(assembly, 0, -1.6, 28.72, 41.22, 4.68, [(7.58, 0.02), (8.35, 0)], dark)
panel(assembly, -0.10, -1.72, 26.95, 39.03, 3.87, [(8.33, 0), (8.44, 0.10)], board)
for x, y, w, h in [
    (-4.4, 11.5, 4, 4.3),
    (5.55, 11.95, 6.5, 3.8),
    (-3.8, 5.35, 4.8, 3.6),
    (4.05, 2.2, 8.85, 9.65),
    (-8.6, -2.05, 2.25, 2.53),
    (5.46, -18.8, 6.3, 2.15),
]:
    panel(assembly, x, y, w, h, 0.20, [(8.45, 0), (8.61, 0.06)], component)
for x, y, cols, rows, dx, dy in [
    (-9.4, 7.5, 3, 12, 0.52, 0.69),
    (-8.95, 14.6, 19, 2, 0.75, 0.47),
    (-2.0, 8.1, 7, 10, 0.55, 0.72),
    (2.65, 14, 10, 2, 0.69, 0.52),
    (2.6, 9.62, 10, 2, 0.70, 0.45),
    (-9.55, -0.3, 3, 10, 0.62, 0.75),
    (9.4, 8.7, 2, 11, 0.48, 0.62),
    (-5.0, -3.8, 7, 3, 0.68, 0.72),
]:
    for i in range(cols):
        for j in range(rows):
            if (i + 2 * j) % 17 == 6:
                continue
            u, v = x + i * dx, y + j * dy
            assembly.add(
                [
                    (u - 0.16, v - 0.18, 8.52),
                    (u + 0.16, v - 0.18, 8.52),
                    (u + 0.16, v + 0.18, 8.52),
                    (u - 0.16, v + 0.18, 8.52),
                ],
                [(0, 1, 2, 3)],
                solder,
                False,
            )
panel(assembly, 0, -10.70, 19.9, 10.3, 1.06, [(8.45, 0), (8.58, 0.18)], component)
for i in range(52):
    intercept = -20 + i * 0.65
    lo = max(-9.16, intercept - 4.55)
    hi = min(9.16, intercept + 4.55)
    if hi - lo > 0.25:
        assembly.pipe(
            [
                (lo, -10.7 + (lo - intercept), 8.62),
                (hi, -10.7 + (hi - intercept), 8.62),
            ],
            0.066,
            board,
            5,
        )
for x, y in [(-12.2, 9.8), (11.85, -7.0), (-8.0, -20.1)]:
    roundface(assembly, x, y, [(1.23, 8.45), (1.14, 8.56), (0.71, 8.59)], edge)

window = Sculpture("Injection-moulded smoked window")
panel(
    window,
    0,
    -2.12,
    30.82,
    41.52,
    5.38,
    [(7.76, 0.12), (9.06, 0.16), (9.86, 0.54), (10.42, 1.45), (10.66, 2.48)],
    resin,
)
window.finalize()
assembly.label("MIC", 1.40, lambda x, y: (x - 6.95, y - 18.34, 8.60), solder)
assembly.label("TX", 1.40, lambda x, y: (x - 4.50, y - 18.34, 8.60), orange)
assembly.finalize()
assembly = Sculpture("Side keys and clip hardware")
logo(lambda x, y: (x * 13.7, y * 10.0 - 0.13, 10.685))

for sign in [-1, 1]:
    panel(
        assembly,
        2.8,
        13.45,
        4.14,
        1.52,
        0.64,
        [(sign * 15.46, 0), (sign * 15.57, 0.08)],
        led if sign == 1 else solder,
        side,
    )


def button(height, left, record=False):
    sign = -1 if left else 1
    for mat, r0, r1, d0, d1 in [
        (dark, 2.90, 2.84, 15.34, 15.65),
        (orange if record else case, 2.68, 2.44, 15.65, 15.97),
        (case, 2.12, 2.10, 15.98, 16.05),
    ]:
        roundface(assembly, 2.42, height, [(r0, d0 * sign), (r1, d1 * sign)], mat, side)


button(-6.60, True, True)
button(7.9, False)
button(-0.78, False)
for y in [7.9, -0.78]:
    if y == -0.78:
        points = [
            side(
                2.42 + 1.03 * math.sin(a * 0.11), y + 1.03 * math.cos(a * 0.11), 16.065
            )
            for a in range(6, 52)
        ]
        assembly.pipe(points, 0.10, silver, 6)
        assembly.pipe(
            [side(2.42, y + 0.25, 16.065), side(2.42, y + 1.60, 16.065)],
            0.11,
            silver,
            6,
        )
    else:
        for delta in [-0.46, 0.46]:
            points = [
                side(
                    2.42 + 0.48 * math.sin(a * math.tau / 19),
                    y + delta + 0.73 * math.cos(a * math.tau / 19),
                    16.065,
                )
                for a in range(20)
            ]
            assembly.pipe(points, 0.09, silver, 5)

contact_x, contact_d = 5.3, 1.78
carrier_bore = Sculpture("Dock carrier seat")
panel(
    carrier_bore,
    contact_x,
    contact_d,
    6.80,
    5.35,
    0.7,
    [(-24.0, 0), (-20.9, 0)],
    dark,
    top,
)
subtract(body, carrier_bore)
for polygon in body.data.polygons:
    if polygon.normal.z < -0.998:
        polygon.use_smooth = False
panel(
    assembly,
    contact_x,
    contact_d,
    6.75,
    5.30,
    0.67,
    [(-22.69, 0.07), (-22.54, 0), (-21.10, 0)],
    dark,
    top,
)
for x in (-1.77, 1.77):
    for d in (-1.22, 1.22):
        roundface(
            assembly,
            contact_x + x,
            contact_d + d,
            [(0.82, -22.68), (0.78, -22.75)],
            gold,
            top,
        )
for x in [-7.3, 7.3]:
    assembly.pipe([(x, 8.6, -4.55), (x, 11.2, -7.90), (x, 13.7, -8.33)], 1.11, clip, 20)
assembly.pipe([(-8.5, 11.55, -7.45), (8.50, 11.55, -7.45)], 1.24, edge, 32)
for sign in [-1, 1]:
    roundface(
        assembly, -7.45, 11.55, [(0.79, sign * 8.49), (0.71, sign * 8.6)], silver, side
    )
for y in [-10.0, -2.5]:
    panel(assembly, 0, y, 8.03, 1.12, 0.43, [(-7.35, 0.12), (-5.12, 0)], edge)


def clipface(x, y, z):
    return (x, y, z - 0.065 * y)


panel(
    assembly,
    0,
    1.10,
    18.73,
    34.5,
    2.8,
    [(-9.56, 0.43), (-9.36, 0.03), (-8.93, 0), (-8.36, 0.42)],
    clip,
    clipface,
)
logo(lambda x, y: clipface(y * 7.28, 1.2 + x * 9.4, -9.575))
etch = finish("Laser marked anodized clip", "89898b", 0.45, 0.58)


def engrave(text, size, along, across):
    assembly.label(
        text, size, lambda u, v: clipface(across + v, 1.25 + along + u, -9.582), etch
    )


engrave("202-JKM065", 1.03, -9.4, 6.76)
engrave("CCAK23LP1430T0", 1.06, 7.0, 6.76)
engrave("UK", 2.31, -10.65, 3.88)
engrave("CA", 2.31, -10.65, 2.0)
engrave("R-C-osm-DMT02", 0.87, -10.55, 0.33)
engrave("CE", 3.89, -12.5, -4.25)
engrave("R31495", 1.06, 11.6, 1.56)
engrave("RoHS", 1.11, 11.6, 0.15)
engrave("CMIIT ID: 2023DP11851", 0.87, -2.96, -3.00)
engrave("ANATEL: 15818-23-12261", 0.87, -2.96, -4.26)
engrave("FCC ID: 2ANDR-DMT02", 0.87, -2.96, -5.52)
engrave("IC: 23060-DMT02", 0.87, 8.38, -3.00)
engrave("Battery: 1.39Wh", 0.87, 8.38, -4.26)
engrave("Input: 5V / 0.4A", 0.87, 8.38, -5.52)
assembly.finalize()

external = list(bpy.context.scene.objects)
product_collection = bpy.data.collections.new("DJI Mic 2 • DMT02 assembly")
bpy.context.scene.collection.children.link(product_collection)
for obj in external:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    product_collection.objects.link(obj)
service = bpy.data.collections.new("Sealed service components • native only")
product_collection.children.link(service)


def store_part(sculpture):
    part = sculpture.finalize()
    for owner in list(part.users_collection):
        owner.objects.unlink(part)
    service.objects.link(part)
    return part


foil = finish("White battery wrap", "e5e1db", 0.08, 0.48)
copper = finish("Flexible circuit coverlay", "a26232", 0.25, 0.45)
red = finish("Power lead red", "913f35", 0, 0.6)
blue = finish("Sensor lead blue", "386484", 0, 0.56)
cell = Sculpture("HPT 542125 • lithium pouch and protective wrap")
panel(
    cell,
    0,
    -4.15,
    20.9,
    25.0,
    1.1,
    [(-3.38, 0.42), (-3.1, 0.05), (-2.78, 0), (1.65, 0), (2.08, 0.38)],
    foil,
)
panel(cell, 0, 8.82, 18.0, 1.6, 0.38, [(-2.9, 0), (1.70, 0)], copper)
for label, y, size in (
    ("BSX102-360-3.87-TX", 0.8, 1.4),
    ("360 mAh   3.87 V", -1.70, 1.22),
    ("1.393 Wh", -4.25, 1.2),
    ("Li-ion", -7.55, 1.32),
):
    cell.label(label, size, lambda x, v: (x, v + y, 2.1), component)
store_part(cell)
capsule = Sculpture("6 mm omnidirectional microphone • capsule and soldered pair")
roundface(
    capsule,
    -5.15,
    1.52,
    [(2.8, 16.32), (3.0, 16.57), (3, 19.85), (2.85, 20.04)],
    silver,
    top,
)
roundface(capsule, -5.15, 1.52, [(1.65, 20.02), (1.65, 20.07)], dark, top)
for sign, mat in ((-1, blue), (1, red)):
    capsule.pipe(
        [
            (-5.15 + sign * 1.1, 16.35, 1.52),
            (-5.55 + sign * 1.0, 14.1, 2.3),
            (-7.1 + sign * 0.33, 12.8, 5.65),
            (-8.2 + sign * 0.25, 13.20, 7.52),
        ],
        0.225,
        mat,
        8,
    )
store_part(capsule)
motor = Sculpture("Haptic coin motor • metal can and flex")
roundface(
    motor, 1.0, 13.10, [(3.28, 0.42), (3.45, 0.58), (3.45, 2.69), (3.21, 2.84)], silver
)
panel(motor, 1.0, 9.63, 2.46, 2.35, 0.30, [(1.01, 0), (1.28, 0)], copper)
for sign, mat in ((-1, red), (1, blue)):
    motor.pipe(
        [
            (1.0 + sign * 0.55, 9.75, 1.11),
            (1.44 + sign * 0.4, 8.2, 2.45),
            (2.56 + sign * 0.30, 7.72, 5.92),
            (3.23 + sign * 0.27, 8.03, 7.48),
        ],
        0.20,
        mat,
        8,
    )
store_part(motor)
input_jack = Sculpture("3.5 mm TRS • insulated jack body and PCB feet")
panel(
    input_jack,
    jack_x,
    jack_depth,
    6.4,
    5.65,
    0.54,
    [(6.8, 0.15), (7.04, 0), (16.06, 0)],
    component,
    top,
)
for x, y in ((2.05, 8.2), (8.94, 12.0), (2.05, 15.0)):
    panel(input_jack, x, y, 0.87, 1.44, 0.12, [(5.0, 0), (7.64, 0)], silver)
store_part(input_jack)
flex = Sculpture("Case-dock FPC and battery harness")
flex.pipe(
    [
        (contact_x, -21.1, contact_d),
        (contact_x, -19.82, 2.02),
        (4.29, -18.75, 3.62),
        (2.1, -18.02, 6.80),
        (1.7, -17.86, 7.56),
    ],
    0.94,
    copper,
    8,
    0.13,
)
for n, mat in enumerate((red, copper, dark)):
    flex.pipe(
        [
            (-5.6 + n * 0.48, 8.82, -0.14),
            (-8.2 + n * 0.37, 9.88, 0.78),
            (-10.98 + n * 0.38, 9.4, 3.48),
            (-11.29 + n * 0.38, 7.72, 6.58),
        ],
        0.23,
        mat,
        8,
    )
panel(flex, -10.9, 7.65, 3.13, 1.72, 0.20, [(6.55, 0), (7.45, 0)], foil)
store_part(flex)

reverse = Sculpture("Shield fences and devices • internal PCB face")
for x, y, w, h in ((2.15, 0.92, 12.25, 9.6), (-1.15, -10.68, 19.40, 11.47)):
    outline_points = [(x + u, y + v, 7.03) for u, v in corners(w, h, 0.68, 4)]
    reverse.pipe(outline_points + [outline_points[0]], 0.22, silver, 8)
    panel(
        reverse, x + 1.5, y - 0.38, 7.3, 6.5, 0.29, [(6.55, 0.07), (7.55, 0)], component
    )
for x, y in ((5.3, 4.1), (4.9, -3.5), (-7.15, -7.05), (-6.66, -12.23)):
    panel(reverse, x, y, 2.21, 1.65, 0.12, [(6.92, 0.12), (7.54, 0)], component)
store_part(reverse)

antenna = Sculpture("Stamped antenna and board contact spring")
panel(antenna, 13.55, -12.91, 1.28, 8.25, 0.43, [(-2.61, 0), (-2.43, 0)], gold)
antenna.pipe(
    [
        (13.55, -9.18, -2.52),
        (13.52, -8.64, 1.47),
        (13.02, -8.58, 3.16),
        (12.53, -8.18, 2.87),
        (12.09, -7.05, 6.92),
    ],
    0.28,
    gold,
    8,
    0.55,
)
store_part(antenna)

for axis, span in ((0, 0.03096), (1, 0.02183), (2, 0.04606)):
    coords = [v.co[axis] for o in external for v in o.data.vertices]
    center = (min(coords) + max(coords)) * 0.5
    factor = span / (max(coords) - min(coords))
    for obj in bpy.context.scene.objects:
        for v in obj.data.vertices:
            v.co[axis] = (v.co[axis] - center) * factor
        obj.data.update()

product = (
    project
    / ".references"
    / "05-摄影与陈列"
    / "录音与存储配件"
    / "DJI Mic 2"
    / "Blender"
)
product.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="DESELECT")
for part in external:
    part.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(product / "dji-mic-2.blend"), compress=True)
target = project / "public" / "media" / "models" / "dji-mic-2.glb"
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
body.name = "DMT02 exterior"
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    use_selection=True,
    export_animations=False,
    export_lights=False,
    export_cameras=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
print(target.name, target.stat().st_size)
