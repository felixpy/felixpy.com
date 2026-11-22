import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from io_scene_gltf2.io.exp import meshopt
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
sources = project / ".references/02-家具与灯具/家居控制器/Window remote and cradle/Blender"
destination = project / "public" / "media" / "models"
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
geometry = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))
part, material = sculpt["Sculpture"], sculpt["finish"]
corners, slab, disk = (geometry[key] for key in ("corners", "slab", "disk"))
symbols = ("blinds", "angle", "city", "weather", "shuffle", "time")
keys = [(12.5 * (-1 if i % 2 == 0 else 1), -24 + 26 * (i // 2)) for i in range(6)]
key_stroke = 1.35
pad_land = 0.822


def rounded(x, z, width, depth, radius):
    return [(x + a, z + b) for a, b in corners(width, depth, radius, 7)]


def circle(x, z, radius, sides=32):
    return [
        (
            x + radius * math.cos(i * math.tau / sides),
            z + radius * math.sin(i * math.tau / sides),
        )
        for i in range(sides)
    ]


def surface(obj, outline, holes, elevation, finish):
    points, boundaries = [], []
    for loop in [outline, *holes]:
        boundaries.append(list(range(len(points), len(points) + len(loop))))
        points += [Vector(p) for p in loop]
    vertices, _, faces, _, _, interiors = delaunay_2d_cdt(
        points, [], boundaries, 1, 0.00001
    )
    visible = [face for face, regions in zip(faces, interiors) if list(regions) == [0]]
    obj.add([(x, elevation(x, z), z) for x, z in vertices], visible, finish, False)


def rim(obj, profiles, finish, skip=None):
    rows = [
        [(x, y(x, z) if callable(y) else y, z) for x, z in loop] for loop, y in profiles
    ]
    width = len(rows[0])
    faces = []
    for j, row in enumerate(rows[:-1]):
        for i, point in enumerate(row):
            k = (i + 1) % width
            if skip and skip(j, point, row[k]):
                continue
            faces.append(
                (j * width + i, j * width + k, (j + 1) * width + k, (j + 1) * width + i)
            )
    obj.add([point for row in rows for point in row], faces, finish)


def shell_edge(inset):
    outline = rounded(0, 0, 61 - 2 * inset, 126 - 2 * inset, 7.2 - inset)
    edge = []
    for i, (x, z) in enumerate(outline):
        edge.append((x, z))
        if z > 59 and outline[(i + 1) % len(outline)][0] < -18 and x > 18:
            edge.extend([(13.35, z), (-13.35, z)])
    return edge


def make_case(parts):
    cream = material("Handset | mineral warm grey ABS", "d8d7cc", rough=0.54, coat=0.04)
    shell = material("Handset | graphite polycarbonate", "474a46", rough=0.48)
    seam = material("Handset | joint shadow and carbon pills", "282b28", rough=0.66)
    rubber = material("Handset | warm grey silicone", "d1d2c5", rough=0.76)
    ochre = material("Handset | ochre silicone", "dbaa6f", rough=0.76)
    printed = printed_key_faces()
    ink = material("Handset | charcoal pad print", "454a42", rough=0.64)
    light = material(
        "Handset | amber indicator lens", "ffb972", rough=0.18, coat=0.5, glow=0.55
    )
    steel = material(
        "Handset | nickel plated contacts", "b9b4a9", metal=0.89, rough=0.29
    )
    copper = material("Handset | electroless gold", "bc944c", metal=0.75, rough=0.33)
    solder = material("Handset | solder mask", "245247", rough=0.61)
    silkscreen = material("Handset | board silkscreen", "d3d7bd", rough=0.65)
    hatch = rounded(0, 56.5, 25.8, 10.4, 1.8)
    lower = part("Lower tub with open battery-tray tunnel")
    wall = [
        (shell_edge(i), y)
        for i, y in [
            (2.2, -6.8),
            (1.2, -6.4),
            (0.55, -5.7),
            (0.24, -4.85),
            (0.1, 0.80),
            (0.05, 2.7),
        ]
    ]
    rim(
        lower,
        wall,
        shell,
        lambda j, a, b: j == 3 and max(abs(a[0]), abs(b[0])) < 13.4 and a[2] > 62,
    )
    screw_holes = [circle(x, -49, 1.55) for x in (-21, 21)]
    surface(lower, wall[0][0], [hatch, *screw_holes], lambda x, z: -6.8, shell)
    for loop in [hatch, *screw_holes]:
        rim(lower, [(loop, -6.8), (loop, -4.9)], shell)
    rim(
        lower,
        [
            (wall[-1][0], 2.7),
            (shell_edge(1.25), 2.7),
            (shell_edge(1.3), 0.80),
            (shell_edge(1.3), -4.85),
            (shell_edge(1.3), -4.95),
        ],
        shell,
        lambda j, a, b: j == 2 and max(abs(a[0]), abs(b[0])) < 13.4 and a[2] > 61,
    )
    for y, outer_z in [(-4.85, 62.76), (0.80, 62.90)]:
        lower.add(
            [
                (-13.35, y, 61.70),
                (13.35, y, 61.70),
                (13.35, y, outer_z),
                (-13.35, y, outer_z),
            ],
            [(0, 1, 2, 3)],
            shell,
            False,
        )
    for x in (-13.35, 13.35):
        lower.add(
            [(x, -4.85, 61.70), (x, -4.85, 62.76), (x, 0.80, 62.90), (x, 0.80, 61.70)],
            [(0, 1, 2, 3)],
            shell,
            False,
        )
    surface(lower, shell_edge(1.3), [hatch, *screw_holes], lambda x, z: -4.95, shell)
    parts.append((lower, False))
    seal = part("Upper and lower shell registering tongue")
    rim(
        seal,
        [(shell_edge(0.32), 2.47), (shell_edge(0.29), 3.04), (shell_edge(1.30), 3.04)],
        seam,
    )
    parts.append((seal, False))
    top = part("Upper face and six radiused switch apertures")
    upper = [
        (shell_edge(i), y)
        for i, y in [
            (0.13, 3.02),
            (0, 3.45),
            (0.08, 5.35),
            (0.52, 6.37),
            (1.3, 7.0),
            (2.45, 7.38),
        ]
    ]
    rim(top, upper, cream)
    apertures = [rounded(x, z, 21.5, 20.45, 4.4) for x, z in keys]
    pilot = rounded(0, 51.8, 5.3, 1.75, 0.86)
    surface(top, upper[-1][0], [*apertures, pilot], lambda x, z: 7.38, cream)
    surface(top, shell_edge(2.45), [*apertures, pilot], lambda x, z: 6.35, cream)
    for loop in [*apertures, pilot]:
        rim(top, [(loop, 6.35), (loop, 7.38)], cream)
    rim(
        top,
        [
            (shell_edge(2.45), 6.35),
            (shell_edge(1.3), 5.5),
            (shell_edge(1.3), 3.02),
            (upper[0][0], 3.02),
        ],
        cream,
    )
    parts.append((top, False))
    gasket = part("Six graphite silicone switch lips")
    for (x, z), aperture in zip(keys, apertures):
        lip = rounded(x, z, 20.0, 19.0, 3.75)
        rim(gasket, [(aperture, 6.3), (lip, 5.98)], seam)
    parts.append((gasket, False))
    badge = part("Pad-printed function group and service markings")
    badge.label("W I N D O W", 2.2, lambda a, b: (a, 7.396, -47.1 - b), ink)
    for text, scale, z in [
        ("STUDIO   /   06", 2.3, -19),
        ("3 V     CR2032", 1.9, 21),
        ("PUSH   >   RELEASE", 1.45, 46.3),
    ]:
        badge.label(text, scale, lambda a, b, z=z: (-a, -6.82, z - b), silkscreen)
    parts.append((badge, False))
    lamp = part("Polished light pipe and shoulder")
    slab(
        lamp,
        0,
        51.8,
        5.12,
        1.60,
        0.78,
        [(6.29, 0.25), (7.4, 0.03), (7.62, 0.18)],
        light,
    )
    parts.append((lamp, False))
    pins = part("Two recessed captive crosshead screws")
    for x in (-21, 21):
        disk(pins, x, -49, [(1.27, -5.31), (1.37, -5.94), (1.05, -6.10)], steel)
        for angle in (0, math.pi / 2):
            cs, sn = math.cos(angle), math.sin(angle)
            pins.pipe(
                [(x + r * cs, -6.112, -49 + r * sn) for r in [-0.62, 0.62]],
                0.125,
                seam,
                8,
            )
    parts.append((pins, False))
    for i, (x, z) in enumerate(keys):
        cap = part("Button_" + symbols[i])
        fill = ochre if i == 5 else rubber
        rows = [
            [(u, height, v) for u, v in corners(21 - 2 * inset, 20 - 2 * inset, 4.15 - inset)]
            for height, inset in [(-3.55, 0.01), (-0.3, 0.05), (1.35, 0.24),
                                  (1.86, 0.50), (2.05, 0.86), (2.1, 1.23)]
        ]
        cap.rings(rows, fill)
        cap.surface[-2:] = [False, False]
        cap.materials.append(printed)
        cap.inks[-1] = cap.materials.index(printed)
        parts.append((cap, False, (x, 8.1, z)))
    pad = part("One-piece silicone switch mat with conical return webs")
    loops = [rounded(x, z, 20.2, 19.1, 4) for x, z in keys]
    outline = rounded(0, 2, 51.6, 75, 4)
    surface(pad, outline, loops, lambda x, z: 2.35, rubber)
    surface(pad, outline, loops, lambda x, z: 1.72, rubber)
    rim(pad, [(outline, 1.72), (outline, 2.35)], rubber)
    for (x, z), loop in zip(keys, loops):
        shoulder = rounded(x, z, 16.8, 15.8, 3.5)
        rim(pad, [(loop, 2.35), (shoulder, 6.64)], rubber)
        rim(
            pad,
            [(loop, 1.72), (rounded(x, z, 15.8, 14.8, 3.15), 6.14), (shoulder, 6.64)],
            rubber,
        )
        pill = pad_land + key_stroke
        disk(pad, x, z, [(2.8, 6.60), (2.8, pill + 0.84), (2.55, pill + 0.5)], rubber)
        disk(pad, x, z, [(2.51, pill + 0.5), (2.51, pill)], seam)
    parts.append((pad, True))
    board = part("FR4 radio PCB with switch lands and fastener bores")
    board_outline = rounded(0, 0, 53.4, 113.0, 4.5)
    bores = [circle(x, -49, 1.9) for x in (-21, 21)]
    for h in [-0.1, 0.78]:
        surface(board, board_outline, bores, lambda x, z, h=h: h, solder)
    for outline in [board_outline, *bores]:
        rim(board, [(outline, -0.1), (outline, 0.78)], solder)
    for x, z in keys:
        for side in [-1, 1]:
            for j in range(4):
                zz = z - 2.12 + 1.22 * j + 0.51 * (side > 0)
                slab(
                    board,
                    x + side * 0.65,
                    zz,
                    3.65,
                    0.34,
                    0.13,
                    [(0.79, 0), (pad_land, 0)],
                    copper,
                )
            slab(
                board,
                x + side * 2.33,
                z,
                0.37,
                5.9,
                0.14,
                [(0.79, 0), (pad_land, 0)],
                copper,
            )
    chip = part("Radio controller, crystal, passives and PCB aerial")
    slab(chip, 0, -44, 5.1, 5.1, 0.3, [(0.78, 0.1), (1.58, 0), (1.69, 0.15)], seam)
    slab(chip, 8.4, -45.4, 3.1, 2, 0.42, [(0.79, 0.12), (1.54, 0)], steel)
    for j in range(4):
        for side in (-1, 1):
            slab(
                chip,
                side * 2.55,
                -45.32 + j * 0.86,
                0.59,
                0.42,
                0.1,
                [(0.8, 0), (1.1, 0.04)],
                steel,
            )
    for j in range(5):
        x = 12.2 + j * 1.94
        slab(chip, x, -47.7, 1.0, 1.7, 0.15, [(0.8, 0.1), (1.43, 0)], ochre)
    chip.pipe(
        [
            (-23, 0.86, -52),
            (-17, 0.86, -52),
            (-17, 0.86, -54),
            (-13, 0.86, -54),
            (-13, 0.86, -52),
            (-9, 0.86, -52),
            (-9, 0.86, -54),
            (-5, 0.86, -54),
            (-5, 0.86, -50),
            (-2, 0.86, -50),
        ],
        0.20,
        copper,
    )
    chip.label("W06    A", 2, lambda a, b: (-12 + a, 0.837, -42 - b), silkscreen)
    parts.extend([(board, True), (chip, True)])
    make_power_stack(parts, shell, seam, steel, copper, ink)
    drawer = part("Sliding carrier release and external end grip")
    slab(
        drawer, 0, 62.1, 26.05, 1.52, 0.49,
        [(-4.67, 0.18), (-4.4, 0), (0.39, 0), (0.58, 0.16)], shell,
    )
    slab(
        drawer, 0, 56.5, 25.35, 9.98, 1.6,
        [(-6.61, 0.15), (-6.44, 0), (-4.15, 0.4)], shell,
    )
    for j in range(4):
        slab(drawer, -2, 54.8 + j * 1.25, 12.5, 0.52, 0.24, [(-6.88, 0.12), (-6.51, 0)], rubber)
    slab(
        drawer, 9.9, 54.5, 2.7, 7.0, 0.6,
        [(-6.92, 0.2), (-6.59, 0.02), (-5.35, 0.12)], rubber,
    )
    parts.append((drawer, False))
    clips = part("Carrier rails, screw bosses and case snap lugs")
    for sign in (-1, 1):
        slab(clips, sign * 13.85, 47, 1.15, 30, 0.3, [(-4.77, 0), (0.33, 0)], shell)
        for zz in (-38, -9, 24):
            slab(
                clips, sign * 28.5, zz, 1.4, 4.4, 0.4,
                [(0.2, 0), (3.62, 0), (4.25, 0.22)], shell,
            )
        disk(
            clips, sign * 21, -49,
            [(2.6, -4.97), (2.6, -0.15), (1.22, -0.15), (1.22, -4.97)], shell,
        )
    parts.append((clips, True))


def make_power_stack(parts, shell, gasket, steel, copper, ink):
    tray = part("Sliding carrier fork and two supporting ledges")
    frame = rounded(0, 47.2, 25.55, 31.15, 2.1)
    opening = 5.45
    radius = 10.13
    a = math.asin(opening / radius)
    fork = []
    for i, (x, z) in enumerate(frame):
        fork.append((x, z))
        if x < -opening and frame[(i + 1) % len(frame)][0] > opening and z < 33:
            fork.append((-opening, z))
            for j in range(57):
                angle = -math.pi / 2 - a - (math.tau - 2 * a) * j / 56
                fork.append((radius * math.cos(angle), 44.2 + radius * math.sin(angle)))
            fork.append((opening, z))
    for h in (-4.31, -0.42):
        surface(tray, fork, [], lambda x, z, h=h: h, shell)
    rim(tray, [(fork, -4.31), (fork, -0.42)], shell)
    for center in (0, math.pi):
        angles = [center + 1.10 * j / 12 for j in range(-12, 13)]
        ledge = [
            (r * math.cos(t), 44.2 + r * math.sin(t))
            for r, span in [(radius, angles), (7.9, reversed(angles))]
            for t in span
        ]
        for h in (-4.35, -3.99):
            surface(tray, ledge, [], lambda x, z, h=h: h, shell)
        rim(tray, [(ledge, -4.35), (ledge, -3.99)], shell)
    parts.append((tray, True))
    cell = part("CR2032 positive can and crimp")
    profile = [(9.48, -3.99), (9.86, -3.89), (10, -3.62), (10, -1.27),
               (9.86, -1.08), (9.49, -0.99), (8.68, -0.99)]
    rim(cell, [(circle(0, 44.2, r, 64), h) for r, h in profile], steel)
    surface(cell, circle(0, 44.2, 9.48, 64), [], lambda x, z: -3.99, steel)
    cell.label("+   CR2032   3V", 1.5, lambda a, b: (-a, -3.995, 46.9 - b), ink)
    parts.append((cell, True))
    cap = part("CR2032 17 mm negative terminal and insulating grommet")
    rim(cap, [(circle(0, 44.2, r, 64), h) for r, h in [(8.7, -0.99), (8.57, -0.93), (8.46, -0.95)]], gasket)
    disk(cap, 0, 44.2, [(8.48, -1.04), (8.5, -0.87), (8.39, -0.79)], steel)
    parts.append((cap, True))
    for name, x, path in [
        ("Positive", 0, [(24.2, -0.235, 3.5), (26.1, -0.235, 3.5), (27.0, -0.55, 2.7),
                         (29.4, -4.28, 2.4), (30.5, -4.56, 2.4), (37.1, -4.56, 2.4),
                         (40.3, -4.30, 2.0), (42.6, -4.09, 1.8), (43.4, -4.09, 1.8),
                         (44.2, -4.25, 1.6)]),
        ("Negative", 3.5, [(35.8, -0.235, 3.5), (37.5, -0.235, 3.5), (38.8, -0.31, 2.8),
                           (42.6, -0.63, 2.2), (43.6, -0.69, 2.0), (44.4, -0.69, 2.0),
                           (45.2, -0.56, 1.7)]),
    ]:
        stamp = part(name + " battery spring and PCB termination")
        start = path[0][0]
        slab(stamp, x, start + 0.75, 4.5, 3.4, 0.3, [(-0.135, 0), (-0.10, 0)], copper)
        for sign in (-1, 1):
            slab(stamp, x + sign * 1.78, start + 0.75, 0.65, 2.7, 0.24,
                 [(-0.15, 0), (-0.31, 0.13)], steel)
        rows = []
        for i, (z, h, w) in enumerate(path):
            before, after = path[max(0, i - 1)], path[min(len(path)-1, i + 1)]
            dz, dh = after[0] - before[0], after[1] - before[1]
            length = math.hypot(dz, dh)
            rows.append([(x + side*w/2, h + side_h*0.10*dz/length, z - side_h*0.10*dh/length)
                         for side, side_h in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
        stamp.rings(rows, steel, smooth=False)
        parts.append((stamp, True))


def draw_symbol(index, line, dot):

    if index < 2:
        for j in (-2.6, 0, 2.6):
            line([(-4.1, j + 0.7 * index), (4.1, j - 0.7 * index)])
    elif index == 2:
        line([(-4.6, 3.4), (-4.6, -1.1), (-2, -1.1), (-2, 3.4)])
        line([(-1.2, 3.4), (-1.2, -4.0), (1.8, -4.0), (1.8, 3.4)])
        line([(2.55, 3.4), (2.55, 0.0), (4.65, 0.0), (4.65, 3.4), (-4.6, 3.4)])
    elif index == 3:
        points = []
        for j in range(43):
            t = math.tau * j / 42
            points.append(
                (
                    3.5 * math.sin(t) * (1 - 0.48 * math.cos(t)),
                    3.75 * -math.cos(t) - 0.78 * max(0, math.cos(t)) ** 5,
                )
            )
        line(points)
    elif index == 4:
        points = rounded(0, 0, 7.8, 7.8, 1.35)
        line(points + [points[0]])
        for j in (-1.9, 0, 1.9):
            dot(j, j, 0.74)
    else:
        points = circle(0, 0, 2.68, 26)
        line(points + [points[0]])
        for j in range(8):
            a = math.tau * j / 8
            line([(r * math.cos(a), r * math.sin(a)) for r in [3.72, 4.79]])


def printed_key_faces():
    size = 192
    axis = (np.arange(size) + 0.5) / size - 0.5
    x, z = np.meshgrid(axis * 21 / 1.25, axis * 20 / 1.25)
    pixels = np.ones((size * 2, size * 3, 4), dtype=np.float32)
    ink = np.array([31, 37, 36]) / 255
    for index in range(len(symbols)):
        distance = np.full_like(x, np.inf)
        def line(points):
            for (ax, az), (bx, bz) in zip(points, points[1:]):
                dx, dz = bx - ax, bz - az
                along = np.clip(((x - ax) * dx + (z - az) * dz) / max(1e-10, dx * dx + dz * dz), 0, 1)
                np.minimum(distance, np.hypot(x - ax - dx * along, z - az - dz * along) - 0.42, out=distance)
        def dot(cx, cz, radius):
            np.minimum(distance, np.hypot(x - cx, z - cz) - radius, out=distance)
        draw_symbol(index, line, dot)
        pigment = np.clip(0.5 - distance * size / 17, 0, 1)[:, :, None]
        base = np.array([219, 170, 111] if index == 5 else [209, 210, 197]) / 255
        row, col = divmod(index, 3)
        pixels[row * size:(row + 1) * size, col * size:(col + 1) * size, :3] = base * (1 - pigment) + ink * pigment
    image = bpy.data.images.new("Six pad printed silicone legends", width=size*3, height=size*2, alpha=False)
    image.pixels.foreach_set(np.ascontiguousarray(pixels[::-1]).ravel())
    image.pack()
    printed = material("Handset | printed silicone", "ffffff", rough=0.76)
    tree = printed.node_tree
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    tree.links.new(texture.outputs["Color"], tree.nodes["Principled BSDF"].inputs["Base Color"])
    return printed


def make_cradle(parts):
    wood = material(
        "Cradle | oiled quarter-sawn walnut", "795941", rough=0.47, coat=0.16
    )
    tree = wood.node_tree
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(
        str(project / "public/media/materials/walnut-surface.webp")
    )
    tree.links.new(
        tex.outputs["Color"], tree.nodes.get("Principled BSDF").inputs["Base Color"]
    )
    tex.image.pack()
    liner = material("Cradle | graphite microsuede", "4b4941", rough=0.91)
    rubber = material("Cradle | nitrile feet", "333532", rough=0.81)
    start = rounded(0, 0, 65.0, 75, 5.9)
    outline = rounded(0, 0, 66.0, 76, 6.3)
    ledge = rounded(0, 0, 64.8, 74.8, 5.8)
    slope = lambda x, z: 22.4 - 0.285 * x
    slot = rounded(2.25, 0, 17.85, 64.7, 3.25)
    inset = rounded(2.4, 0, 17.0, 64.0, 2.9)
    bottom = rounded(3.9, 0, 17.0, 64.0, 2.9)
    block = part("Single routed block with inclined stopped mortise")
    rim(
        block,
        [
            (start, 1.15),
            (outline, 2.0),
            (outline, lambda x, z: slope(x, z) - 0.95),
            (ledge, slope),
        ],
        wood,
    )
    surface(block, start, [], lambda x, z: 1.15, wood)
    surface(block, ledge, [slot], slope, wood)
    rim(
        block,
        [(slot, slope), (inset, lambda x, z: slope(x, z) - 0.6), (bottom, 9.57)],
        wood,
    )
    surface(block, bottom, [], lambda x, z: 9.57, wood)
    parts.append((block, False))
    bed = part("Suede floor pad and two angled grip strips")
    slab(bed, 3.94, 0, 16.6, 63.5, 2.7, [(9.57, 0.15), (10.15, 0.03)], liner)
    for side in (-1, 1):
        for z in (-19, 19):
            z0, z1 = z - 6.2, z + 6.2
            x0 = 3.9 + side * 8.49
            x1 = 2.4 + side * 8.49
            y1 = slope(x1, z) - 1.4
            for u in (0, -side * 0.24):
                bed.add(
                    [
                        (x0 + u, 10, z0),
                        (x0 + u, 10, z1),
                        (x1 + u, y1, z1),
                        (x1 + u, y1, z0),
                    ],
                    [(0, 1, 2, 3)],
                    liner,
                    False,
                )
    parts.append((bed, False))
    feet = part("Four countersunk elastomer feet")
    for x in (-23, 23):
        for z in (-28, 28):
            disk(feet, x, z, [(3.3, 0), (3.8, 0.28), (3.8, 1.19)], rubber)
    parts.append((feet, False))


def actuate_key_mat(collection):
    mat = next(obj for obj in collection.objects if "silicone switch mat" in obj.name)
    rest = mat.shape_key_add(name="Rest")
    for (x, z), symbol in zip(keys, symbols):
        button = collection.objects["Button_" + symbol]
        shape = mat.shape_key_add(name=symbol.title() + " contact", from_mix=False)
        for vertex, point in zip(rest.data, shape.data):
            u, v, height = vertex.co * 1000
            if abs(u - x) < 8.41 and abs(-v - z) < 7.91:
                if height > 6 or math.hypot(u - x, -v - z) < 3:
                    point.co.z -= key_stroke / 1000
        control = shape.driver_add("value").driver
        motion = control.variables.new()
        motion.name = "height"
        motion.type = "TRANSFORMS"
        motion.targets[0].id = button
        motion.targets[0].transform_type = "LOC_Z"
        motion.targets[0].transform_space = "LOCAL_SPACE"
        control.expression = f"min(1,max(0,({button.location.z:.7f}-height)/{key_stroke/1000:.7f}))"


def export_product(name, title, build):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    collection = bpy.data.collections.new(title)
    bpy.context.scene.collection.children.link(collection)
    parts = []
    build(parts)
    visible = []
    for spec, enclosed, *loc in parts:
        obj = spec.finalize(12 if name == "window-cradle" else 0)
        if obj.name.startswith("Button_"):
            row, col = divmod(symbols.index(obj.name.removeprefix("Button_")), 3)
            uv = obj.data.uv_layers.new(name="Pad printing")
            for face in obj.data.polygons:
                if face.material_index == 0:
                    continue
                for index in face.loop_indices:
                    point = obj.data.vertices[obj.data.loops[index].vertex_index].co
                    uv.data[index].uv = ((col + 0.5 + point.x / 0.021) / 3, (1.5 - row + point.y / 0.020) / 2)
        if loc:
            x, h, z = loc[0]
            obj.location = (x / 1000, -z / 1000, h / 1000)
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
        if enclosed:
            obj["productEnclosed"] = True
        else:
            visible.append(obj)
    if name == "window-controller":
        actuate_key_mat(collection)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(sources / (name + ".blend")), compress=True
    )
    bpy.ops.object.select_all(action="DESELECT")
    fixed = [o for o in visible if not o.name.startswith("Button_")]
    for obj in fixed:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = fixed[0]
    bpy.ops.object.join()
    fixed[0].name = title
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("Button_"):
            obj.select_set(True)
    if name == "window-cradle":
        for im in bpy.data.images:
            if im.name.startswith("walnut-surface"):
                im.scale(384, 384)
    meshopt.EXP_FILTER_BITS = 22
    bpy.ops.export_scene.gltf(
        filepath=str(destination / (name + ".glb")),
        export_format="GLB",
        use_selection=True,
        export_image_format="JPEG" if name == "window-cradle" else "AUTO",
        export_image_quality=88,
        export_extras=False,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        [
            "node",
            str(scripts / "pack-product-geometry.mjs"),
            str(destination / (name + ".glb")),
            "--deduplicate",
        ],
        check=True,
    )


sources.mkdir(parents=True, exist_ok=True)
destination.mkdir(parents=True, exist_ok=True)
export_product("window-controller", "Studio six-key controller", make_case)
if "--handset-only" not in sys.argv:
    export_product("window-cradle", "Oiled walnut cradle", make_cradle)
