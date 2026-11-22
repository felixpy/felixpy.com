from pathlib import Path
import sys
import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import xyz, barrel, block, bevel, export_batch
from thor_display import add_display

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "public/media/models"
LIBRARY = ROOT / ".review/atelier/pc-components"


def material(name, color, metal, rough):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def solid(name, contours, place, thickness, radius=0):
    points = []
    loops = []
    for index, contour in enumerate(contours):
        area = sum(
            p[0] * q[1] - p[1] * q[0]
            for p, q in zip(contour, contour[1:] + contour[:1])
        )
        contour = contour if (area > 0) == (index == 0) else list(reversed(contour))
        loops.append([Vector((a, b, 0)) for a, b in contour])
        points.extend(contour)
    first = tessellate_polygon(loops)
    n = len(points)
    faces = [tuple(reversed(face)) for face in first] + [
        tuple(n + i for i in face) for face in first
    ]
    cursor = 0
    for loop in loops:
        for i in range(len(loop)):
            a, b = cursor + i, cursor + (i + 1) % len(loop)
            faces.append((a, b, b + n, a + n))
        cursor += len(loop)
    verts = [xyz(place(a, b, t)) for t in [0, thickness] for a, b in points]
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return bevel(obj, radius)


def keypad(x, y, w, h, r=0.4):
    return [
        (x - w / 2 + r, y - h / 2),
        (x + w / 2 - r, y - h / 2),
        (x + w / 2, y - h / 2 + r),
        (x + w / 2, y + h / 2 - r),
        (x + w / 2 - r, y + h / 2),
        (x - w / 2 + r, y + h / 2),
        (x - w / 2, y + h / 2 - r),
        (x - w / 2, y - h / 2 + r),
    ]


def socket(cx, cy, type_, grow=0):
    w = (16.2 if type_ == "DP" else 14.2) / 2 + grow
    h = (5.0 if type_ == "DP" else 4.5) / 2 + grow
    return [
        (cx + x, cy + y)
        for x, y in (
            [(-w, -h), (w - 2.2, -h), (w, -h + 2.2), (w, h), (-w, h)]
            if type_ == "DP"
            else [
                (-w + 2, -h),
                (w - 2, -h),
                (w, -h + 1.8),
                (w, h),
                (-w, h),
                (-w, -h + 1.8),
            ]
        )
    ]


def thor(paint):
    def panel(name, loops, coord, t=1, metal="enamel"):
        return paint(solid(name, loops, coord, t), metal)

    rear = lambda x, y, t: (x, y, -95 + t)
    vents = []
    for row in range(21):
        for col in range(34):
            x = -69 + col * 4.16 + (row % 2) * 2.08
            y = -37.8 + row * 3.64
            if (
                x > 69
                or (y > 24 and abs(x) > 53)
                or (-32 < y < 24 and x < -18)
                or (-10 < y < 10 and -18 < x < -4)
            ):
                continue
            vents.append(
                [
                    (
                        x + 1.66 * math.cos((k + 0.5) * math.tau / 6),
                        y + 1.66 * math.sin((k + 0.5) * math.tau / 6),
                    )
                    for k in range(6)
                ]
            )
    inlet = keypad(-40, 1, 34, 24, 1.5)
    sw = keypad(-40, -23.4, 21, 14, 0.7)
    turbo = keypad(-10, 1, 11.5, 12, 0.4)
    panel(
        "Rear folded steel panel • punched cooling field",
        [keypad(0, 0, 149.5, 85.8, 1), inlet, sw, turbo, *vents],
        rear,
    )
    paint(
        block("Black internal suppression baffle", (146, 81, 1.1), (0, 0, -84), 0.35),
        "black",
    )
    panel(
        "IEC 60320 C20 entry bezel",
        [keypad(-40, 1, 36.2, 26.6, 1.6), keypad(-40, 1, 26.3, 18.7, 1.6)],
        lambda x, y, t: (x, y, -96 + t),
        7.5,
        "black",
    )
    for x, y in [(-40, 4.1), (-47.3, -2.6), (-32.7, -2.6)]:
        paint(block("IEC flat contact", (4.1, 0.95, 6.2), (x, y, -89.9), 0.22), "shell")
    for pos, size, title in [
        ((-40, -23.4, -95.5), (19.8, 12.1, 3.8), "Curved mains rocker"),
        ((-10, 1, -95.4), (9.8, 10.8, 2.6), "Turbo button"),
    ]:
        paint(block(title, size, pos, 0.7), "black")
    for x, y in [(-69, 37.0), (69, -33), (-69, -37), (69, 29), (-12, -30), (8, 20)]:
        paint(
            barrel("Rear retention screw", (x, y, -95.25), (x, y, -95.55), 2.05, 16),
            "black",
        )
    for side in [-1, 1]:
        paint(
            block("Folded side panel", (1.15, 85.8, 198.5), (side * 73.12, 0, 5), 0.34),
            "enamel",
        )
    paint(
        block("Upper chassis skin", (147.8, 1.05, 198), (0, 42.28, 5), 0.44),
        "enamel",
    )
    grille = [keypad(0, 5, 149, 199, 1)]
    for stripe in range(-32, 33):
        intercept = stripe * 7.4
        lo = max(-69, (-87 - intercept) / 0.87)
        hi = min(69, (97 - intercept) / 0.87)
        if hi - lo < 4:
            continue
        grille.append(
            [
                (lo + 0.45, 0.87 * lo + intercept),
                (hi, 0.87 * hi + intercept),
                (hi - 0.45, 0.87 * hi + intercept + 2.8),
                (lo, 0.87 * lo + intercept + 2.8),
            ]
        )
    panel(
        "Brushed diagonal fan grille", grille, lambda x, z, t: (x, -42.9 + t, z), 1.05
    )
    fan_throat = [
        (65.7 * math.cos(math.tau * i / 72), 65.7 * math.sin(math.tau * i / 72))
        for i in range(72)
    ]
    mounts = [
        [(x + 2.1 * math.cos(math.tau * i / 16), z + 2.1 * math.sin(math.tau * i / 16))
         for i in range(16)]
        for x in (-58.5, 58.5) for z in (-58.5, 58.5)
    ]
    panel("135 mm intake frame • motor tunnel and mount ears",
          [keypad(0, 0, 135, 135, 7), fan_throat, *mounts],
          lambda x, z, t: (x, -41.7 + t, z), 24.6, "black")
    paint(
        barrel("F1214025BU • recessed motor hub", (0, -39.1, 0), (0, -18.1, 0), 19, 52),
        "black",
    )
    for arm in range(4):
        angle = arm * math.pi / 2
        shape = [(13, -10), (28, -18), (61, -27), (67, -25),
                 (65, -21), (32, -13), (16, -5)]
        points = [(x*math.cos(angle) - z*math.sin(angle),
                   x*math.sin(angle) + z*math.cos(angle)) for x, z in shape]
        panel("Injection-moulded motor stay", [points], lambda x, z, t: (x, -20 + t, z), 2.4, "black")
    for blade in range(9):
        verts, faces = [], []
        stations = [(17.0,-16,48,9),(24,-19,45,11),(34,-20,40,12),
                    (45,-18,34,11),(56,-13,29,9),(63,-6,24,7),(65.1,-2,17,5)]
        for i, (radius, sweep, chord, pitch) in enumerate(stations):
            for j in range(5):
                v = j / 4
                a = blade * math.tau / 9 + math.radians(sweep + chord * v)
                y = -38 + pitch * v - 1.3 * math.sin(math.pi * v)
                verts.append(xyz((radius * math.cos(a), y, radius * math.sin(a))))
                if i and j:
                    k = i * 5 + j
                    faces.append((k-6, k-1, k, k-5))
        data = bpy.data.meshes.new("Cambered fan blade")
        data.from_pydata(verts, [], faces)
        obj = bpy.data.objects.new("Swept intake blade " + str(blade + 1), data)
        bpy.context.collection.objects.link(obj)
        for poly in data.polygons:
            poly.use_smooth = True
        skin = obj.modifiers.new("Moulded airfoil wall", "SOLIDIFY")
        skin.thickness = 0.00082
        paint(obj, "black")
    holes = []
    groups = [
        (-45, 16, 9, 2),
        (-27, 23, 5, 2),
        (-45, -9.5, 3, 2),
        (-45, -27.5, 3, 2),
        (-25, -9.5, 3, 2),
        (-25, -27.5, 3, 2),
        (-4, -9.5, 3, 2),
        (-4, -27.5, 3, 2),
    ]
    for x in [15, 35, 55]:
        for y in [-7, -27.5]:
            groups.append((x, y, 4, 2))
    for x in [34, 55]:
        groups.append((x, 23, 6, 2))
    groups.extend([(-8, 19, 2, 1), (20, 19, 2, 1)])
    for x, y, c, r in groups:
        pitch = 3.0 if c == 6 else 3.9
        w, h = r * pitch + 2, c * pitch + 2
        extra = 1.8 if c == 6 else 0
        edge = x - extra / 2
        holes.append(keypad(edge, y, w + extra + 1, h + 1, 0.7))
        slots = []
        for i in range(c):
            for j in range(r):
                p, q = x + (j - (r - 1) / 2) * pitch, y + (i - (c - 1) / 2) * pitch
                slots.append(
                    keypad(
                        p, q, pitch - 0.72, pitch - 0.72, 0.42 if (i + j) % 2 else 0.12
                    )
                )
                paint(
                    block("Plated modular contact", (0.67, 0.67, 2.8), (p, q, 103.4)),
                    "gold",
                )
        if c == 6:
            for index in range(4):
                px, py = x - w/2 - 0.55, y + (index - 1.5) * 2.0
                slots.append(keypad(px, py, 1.25, 1.5, .18))
                paint(block("12V-2×6 sideband sense pin", (.35, .47, 2.0), (px, py, 103.3)), "gold")
        panel(
            "Keyed modular socket " + str(c * r),
            [keypad(edge, y, w + extra, h, 0.45), *slots],
            lambda x, y, t: (x, y, 104.8 + t),
            2.4,
            "violet" if (x, y, c, r) == (20, 19, 2, 1) else "black",
        )
    panel(
        "Modular front connection bank",
        [keypad(0, 0, 149, 85, 1.5), *holes],
        lambda x, y, t: (x, y, 103 + t),
        1,
    )
    paint(
        block("PCB behind recessed socket walls", (146, 81, 1.2), (0, 0, 99.5)), "black"
    )
    add_display(paint, solid)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    LIBRARY.mkdir(parents=True, exist_ok=True)
    finishes = {
        key: material(name, c, m, r)
        for key, (name, c, m, r) in {
            "steel": (
                "Stamped passivated stainless steel",
                (0.37, 0.40, 0.42),
                0.84,
                0.32,
            ),
            "shell": ("Nickel-plated interface shell", (0.62, 0.64, 0.63), 0.88, 0.27),
            "black": ("Connector insulator", (0.009, 0.013, 0.016), 0.04, 0.56),
            "pcb": (
                "Multilayer graphite solder mask",
                (0.027, 0.031, 0.027),
                0.08,
                0.58,
            ),
            "gold": ("Hard gold over nickel", (0.64, 0.406, 0.094), 0.77, 0.32),
            "copper": ("Lapped copper contact plate", (0.49, 0.235, 0.094), 0.84, 0.34),
            "enamel": (
                "Textured anthracite powder coating",
                (0.039, 0.044, 0.048),
                0.48,
                0.43,
            ),
            "glass": ("Smoked OLED optical cover", (0.012, 0.015, 0.018), 0.12, 0.19),
            "aura": ("Ice-blue Aura light guide", (0.023, 0.39, 0.57), 0.12, 0.28),
            "pixels": ("White OLED wattage", (0.87, 0.92, 0.94), 0, 0.32),
            "violet": ("GPU-FIRST IVS header", (0.55, 0.012, 0.35), 0.04, 0.42),
        }.items()
    }
    for key, intensity in [("aura", 0.7), ("pixels", 1.3)]:
        node = finishes[key].node_tree.nodes.get("Principled BSDF")
        node.inputs["Emission Color"].default_value = finishes[key].diffuse_color
        node.inputs["Emission Strength"].default_value = intensity

    def paint(obj, key):
        obj.data.materials.append(finishes[key])
        return obj

    def save(prefix, collection, scope):
        bpy.context.view_layer.update()
        for key, mat in finishes.items():
            matches = [
                o
                for o in scope
                if o.type == "MESH"
                and len(o.data.materials)
                and o.data.materials[0] == mat
            ]
            if matches:
                export_batch(
                    prefix + "-" + key, matches, MODELS / (prefix + "-" + key + ".mesh")
                )
                for obj in matches:
                    obj["nativePart"] = prefix + "-" + key
        col = bpy.data.collections.new(collection)
        bpy.context.scene.collection.children.link(col)
        for obj in scope:
            for old in list(obj.users_collection):
                old.objects.unlink(obj)
            col.objects.link(obj)
        return col

    if "--only-thor" in sys.argv:
        thor(paint)
        save("thor-1600", "ROG Thor 1600W Titanium III", list(bpy.context.scene.objects))
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(LIBRARY / "thor-psu.blend"), compress=True)
        return

    cut = [
        (-39, 27),
        (-38, 30),
        (-34, 30),
        (-34, 32),
        (-26, 32),
        (-26, 30),
        (58, 30),
        (58, 31),
        (68, 31),
        (71, 28),
        (78, 28),
        (78, 19),
        (71, 19),
        (68, 16),
        (68, 13),
        (71, 10),
        (78, 10),
        (78, 1),
        (71, 1),
        (68, -4),
        (60, -4),
        (58, -2.3),
        (57, -5.7),
        (-32, -5.7),
        (-36, -1),
        (-39, -1),
    ]
    ports = [(x, 22, "DP") for x in [-20.8, 0.8, 22.4]] + [
        (44, 22, "HDMI"),
        (44, 2.8, "HDMI"),
    ]
    vents = [
        keypad(x, 4.2, 4.4, 14.7, 0.7) for x in [-25, -18, -11, -4, 3, 10, 17, 24, 56.4]
    ]
    front = -179.3
    back_shield = keypad(-3.7, 0, 138.0, 64, 2.8)
    slit = []
    for x in [-63, -53, -43]:
        slit.append([(x, -0.5), (x + 4.3, -0.5), (x - 2.9, 20), (x - 7.2, 20)])
    paint(
        solid(
            "Black rear rail with diagonal exhausts",
            [back_shield, keypad(11.6, 14.5, 94.1, 33, 1.2), *slit],
            lambda x, y, t: (x, y, front + 3.05 + t),
            1.6,
            0.25,
        ),
        "enamel",
    )
    paint(
        solid(
            "Double-slot I/O retention bracket",
            [cut] + [socket(x, y, k, 0.5) for x, y, k in ports] + vents,
            lambda x, y, t: (x, y, front + t),
            0.95,
            0.15,
        ),
        "steel",
    )
    for index, (cx, cy, kind) in enumerate(ports):
        paint(
            solid(
                f"{kind} {index + 1} • folded shield",
                [socket(cx, cy, kind, 0.23), socket(cx, cy, kind, -0.25)],
                lambda x, y, t: (x, y, front - 0.16 + t),
                6.6,
                0.055,
            ),
            "shell",
        )
        paint(
            solid(
                f"{kind} {index + 1} • recessed socket floor",
                [socket(cx, cy, kind, -0.25)],
                lambda x, y, t: (x, y, front + 5.8 + t),
                1,
            ),
            "black",
        )
        paint(
            block(
                kind + " polymer tongue",
                (12.6, 0.68, 3.3),
                (cx, cy + 0.1, front + 3.6),
                0.1,
            ),
            "black",
        )
        for i in range(10):
            paint(
                block(
                    kind + " spring contact",
                    (0.25, 0.1, 2.1),
                    (cx + (i - 4.5) * 1.08, cy + 0.46, front + 3.5),
                ),
                "gold",
            )
    for x, y in [
        (-34, 15),
        (-34, 2.5),
        (-20, 13),
        (1.4, 13),
        (23, 13),
        (43.8, 13),
        (43.8, -0.3),
        (28, 3),
    ]:
        paint(
            barrel(
                "Stamped screw seat", (x, y, front - 0.2), (x, y, front + 0.1), 2.3, 20
            ),
            "shell",
        )
        paint(
            barrel(
                "Countersunk Torx clearance",
                (x, y, front - 0.25),
                (x, y, front - 0.19),
                1.1,
                6,
            ),
            "black",
        )
    io = save(
        "astral-io", "Astral rear display interfaces", list(bpy.context.scene.objects)
    )
    prev = set(bpy.context.scene.objects)
    yz = 22
    first = -125.6
    footprint = [
        (59, first - 1),
        (66, first - 1),
        (68.4, first + 0.1),
        (68.4, first + 11.8),
        (62.3, first + 11.8),
        (62.3, first + 13.25),
        (68.4, first + 13.25),
        (68.4, first + 84),
        (66.3, first + 85.2),
        (62.9, first + 85.2),
        (62.9, first + 87),
        (66.4, first + 87),
        (67.1, first + 90),
        (62.6, first + 93),
        (58, first + 93),
    ]
    paint(
        solid(
            "PCIe 5.0 ×16 keyed FR-4 card edge",
            [footprint],
            lambda x, z, t: (x, yz - 0.79 + t, z),
            1.58,
        ),
        "pcb",
    )
    for side in [-1, 1]:
        for i in range(82):
            z = first + i + (0.6 if i < 11 else 2.7)
            stop = 67.55 if i in [10, 80] else 68.12
            paint(
                solid(
                    f"PCIe side {side:+d} contact {i + 1:02}",
                    [
                        [
                            (62, z),
                            (stop - 0.22, z),
                            (stop, z + 0.12),
                            (stop, z + 0.56),
                            (stop - 0.16, z + 0.67),
                            (62, z + 0.67),
                        ]
                    ],
                    lambda x, z, t: (x, yz + side * (0.795 + t), z),
                    0.032,
                ),
                "gold",
            )
    save(
        "astral-pcie",
        "PCIe 5.0 card-edge assembly",
        set(bpy.context.scene.objects) - prev,
    )
    prev = set(bpy.context.scene.objects)

    def ring(z, rad):
        return [
            (rad * math.cos(a * math.tau / 112), z + rad * math.sin(a * math.tau / 112))
            for a in range(112)
        ]

    cut0 = ring(-116, 55.35)
    cut1 = ring(0, 55.35)
    last = ring(116, 56.4)
    top = [
        (-59, -169),
        (-55, -173.4),
        (53, -173.4),
        (60, -166),
        (60, 164),
        (53, 173),
        (-50, 173),
        (-59, 168),
    ]
    paint(
        solid(
            "Brushed aluminium triple aperture shroud",
            [top, cut0, cut1, last],
            lambda x, z, t: (x, -34.05 - t, z),
            0.95,
            0.2,
        ),
        "steel",
    )
    for z in [-116, 0]:
        paint(
            solid(
                "Spun rounded intake lip",
                [ring(z, 56.9), ring(z, 55.28)],
                lambda x, z, t: (x, -35.0 - t, z),
                0.55,
                0.14,
            ),
            "shell",
        )
    for x in [-51, 50]:
        for z in [-62, 53]:
            groove = [(x, z - 5.6), (x + 3, z - 3.4), (x + 3, z + 3.8), (x, z + 5.2)]
            paint(
                solid(
                    "Milled bridge index",
                    [groove],
                    lambda a, b, t: (a, -35.04 - t, b),
                    0.11,
                ),
                "enamel",
            )
    save(
        "astral-intake",
        "Machined front fan shroud",
        set(bpy.context.scene.objects) - prev,
    )
    prev = set(bpy.context.scene.objects)
    paint(
        solid(
            "Cold plate • polished CPU contact face",
            [keypad(0, 0, 53, 53, 4.4)],
            lambda u, v, t: (u, v, t),
            2.8,
            0.35,
        ),
        "copper",
    )
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            wing = [
                (sx * x, sy * y)
                for x, y in [
                    (20, 18),
                    (28, 21),
                    (41, 35),
                    (43, 38),
                    (42.6, 41),
                    (40.5, 43),
                    (37.1, 43),
                    (21, 29),
                ]
            ]
            hole = [
                (sx * (39 + 2.2 * a), sy * (39 + 2.2 * b))
                for a, b in [
                    (1, 0),
                    (0.7, 0.7),
                    (0, 1),
                    (-0.7, 0.7),
                    (-1, 0),
                    (-0.7, -0.7),
                    (0, -1),
                    (0.7, -0.7),
                ]
            ]
            paint(
                solid(
                    "LGA1851 78 mm retention arm",
                    [wing, hole],
                    lambda u, v, t: (u, v, 3.2 + t),
                    1.6,
                    0.23,
                ),
                "steel",
            )
            paint(
                barrel(
                    "Shouldered socket mounting post",
                    (sx * 39, sy * 39, -3.8),
                    (sx * 39, sy * 39, 3.2),
                    1.85,
                    20,
                ),
                "steel",
            )
            paint(
                barrel(
                    "Captive knurled thumb nut",
                    (sx * 39, sy * 39, 4.8),
                    (sx * 39, sy * 39, 9.8),
                    3.8,
                    28,
                ),
                "shell",
            )
    save(
        "ryuo-mount",
        "LGA1851 cold plate and retention",
        set(bpy.context.scene.objects) - prev,
    )
    prev = set(bpy.context.scene.objects)
    thor(paint)
    save(
        "thor-1600",
        "ROG Thor 1600W Titanium III",
        set(bpy.context.scene.objects) - prev,
    )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(LIBRARY / "machined-interfaces.blend"), compress=True
    )


build()
