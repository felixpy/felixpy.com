import math
import runpy
from pathlib import Path

import bpy


solids = runpy.run_path(str(Path(__file__).with_name("product_solids.py")))
variants = [
    ("Black", "282626"), ("Red", "ad3034"), ("Brown", "78543b"), ("Blue", "3e6b9b"),
    ("Clear", "bab6a9"), ("White", "e0ded2"), ("Green", "345c44"), ("RGB Silver", "989b94"),
    ("Gray", "777d7a"), ("Speed Silver", "969a96"), ("Silent Black", "333633"), ("Silent Red", "ab5055"),
]


def cross(arm, half):
    return [
        (half, arm), (-half, arm), (-half, half), (-arm, half),
        (-arm, -half), (-half, -half), (-half, -arm), (half, -arm),
        (half, -half), (arm, -half), (arm, half), (half, half),
    ]


def build(Sculpture, finish, rounded, pad, clear, cap, rubber, ink):
    collection = bpy.data.collections.new("Glanaut 12-key Cherry MX switch tester")
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(collection.name, None)
    collection.objects.link(root)
    root["benchInstrument"] = "tester"
    visible = []
    hidden = []

    def attach(obj, enclosed=False):
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.parent = root
        (hidden if enclosed else visible).append(obj)

    polymer = finish("MX · black moulded housing", "25272a", rough=0.61)
    milky = finish("MX RGB · translucent lower housing", "dadccc", rough=0.38)
    milky.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.72
    milky.diffuse_color = (0.84, 0.87, 0.79, 0.72)
    spring_wire = finish("MX · spring wire", "96989b", metal=0.84, rough=0.27)
    terminals = finish("MX · stamped copper alloy", "ab895a", metal=0.77, rough=0.35)
    contact = finish("MX · gold crosspoints", "d7b951", metal=0.84, rough=0.23)
    centers = [((1 - i // 4) * 19.05, (i % 4 - 1.5) * 19.05) for i in range(12)]
    deck = solids["block"]("Glanaut · drilled acrylic block", 0, 4.7, 0, 60, 7.6, 79, 2.9, clear)
    cutters = [solids["block"]("MX plate opening", x, 4.7, d, 14.05, 12, 14.05, 0.25, clear)
               for x, d in centers]
    solids["subtract"](deck, cutters)
    solids["edge"](deck, 0.15)
    attach(deck)
    feet = Sculpture("Glanaut · four elastomer buffers")
    for x in (-25.2, 25.2):
        for d in (-34.8, 34.8):
            feet.form((x, 0.57, d), (2.3, 0.57, 2.3), rubber)
    attach(feet.finalize())

    for (name, color), (cx, cd) in zip(variants, centers):
        pigment = finish("MX · " + name, color, rough=0.56)

        def row(profile, height):
            return [(cx + u, height, cd + v) for u, v in profile]

        def shell(width, height, radius):
            return row(rounded(width, width, radius, 3), height)

        lower = Sculpture("MX " + name + " · lower case and locator")
        base_material = milky if name == "RGB Silver" else polymer
        lower.rings([shell(w, h, r) for w, h, r in [
            (12.8, 3.45, 0.7), (13.7, 4, 0.6), (13.7, 8.49, 0.6),
            (15.5, 8.52, 0.7), (15.5, 9.08, 0.7),
            (12.5, 9.08, 0.5), (12.5, 4.3, 0.5),
        ]], base_material, False)
        lower.loft([(cx, h, cd, r, r) for h, r in [(0.4, 1.48), (0.7, 1.65), (3.45, 1.65)]], base_material, 28)
        for dx, dz in [(-2.54, -5.08), (3.81, -2.54)]:
            pad(lower, cx + dx, 2.05, cd + dz, 0.85, 0.28, 3.0, 0.08, terminals, True, 0.06)
        attach(lower.finalize())

        upper = Sculpture("MX " + name + " · removable upper cover")
        housing = clear if name == "RGB Silver" else polymer
        upper.rings([shell(w, h, r) for w, h, r in [
            (15.5, 9.09, 0.7), (15.35, 9.9, 0.7), (13.3, 10.2, 0.65), (10.7, 12.85, 0.55),
            (6.85, 12.85, 0.24), (6.85, 12.2, 0.24), (9.8, 12.18, 0.4),
            (12.55, 9.72, 0.5), (14.1, 9.69, 0.5), (14.1, 9.09, 0.5), (15.5, 9.09, 0.7),
        ]], housing, False, close=False)
        for dx in (-6.65, 6.65):
            for dz in (-4.1, 4.1):
                pad(upper, cx + dx, 8.32, cd + dz, 0.45, 2.35, 1.6, 0.15, housing, True, 0.08)
        attach(upper.finalize())

        stem = Sculpture("MX " + name + " · guided slider")
        pad(stem, cx, 10.75, cd, 6.3, 6.25, 2.0, 0.5, pigment, True, 0.18)
        stem.rings([row(cross(1.99, 0.58), h) for h in (11.65, 16.48)], pigment, False)
        attach(stem.finalize())
        action = Sculpture("MX " + name + " · return spring and contact leaves")
        points = []
        for j in range(113):
            t = j / 112
            theta = t * 7 * math.tau
            points.append((cx + 1.85 * math.cos(theta), 4.53 + t * 5.08, cd + 1.85 * math.sin(theta)))
        action.pipe(points, 0.16, spring_wire, 6)
        for dx, dz, reach, height in [(-2.54, -5.08, -1.07, 8.1), (3.81, -2.54, -0.80, 8.82)]:
            outline = [(cx + dx, 3.47, cd + dz), (cx + dx, 6.55, cd + dz),
                       (cx + reach, height, cd - 3.55), (cx + reach, height + 0.55, cd - 3.55)]
            action.pipe(outline, 0.33, terminals, 4, 0.28)
            action.pipe([(cx + reach, height, cd - 3.55), (cx + reach, height + 0.47, cd - 3.55)], 0.18, contact, 8)
        if name in ("Blue", "White", "Green"):
            action.rings([shell(w, h, 0.35) for w, h in [(6.46, 9.1), (6.46, 9.68), (4.85, 9.68),
                                                          (4.85, 9.1), (6.46, 9.1)]], cap, False, close=False)
        if name.startswith("Silent"):
            for dx in (-3.02, 3.02):
                pad(action, cx + dx, 10.85, cd, 0.58, 3.6, 2.32, 0.23, rubber, True, 0.12)
        attach(action.finalize(), name != "RGB Silver")

        key = Sculpture("Glanaut · " + name + " R4 keycap")

        def cap_row(w, depth, r, height, shift, tilt):
            return [(cx + shift + u, height + tilt * u, cd + v) for u, v in rounded(w, depth, r)]

        key.rings([cap_row(*p) for p in [
            (13.4, 14.3, 0.9, 20.64, -1, 0.055), (13.8, 14.7, 0.95, 20.4, -1, 0.055),
            (17.75, 17.75, 1.05, 12.85, 0, 0), (17.62, 17.62, 1.0, 12.65, 0, 0),
            (15.55, 15.55, 0.62, 12.65, 0, 0), (12.1, 12.95, 0.53, 19.48, -1, 0.055),
        ]], cap, False)
        socket = cross(2.05, 0.625)
        sleeve = [(2.72 * u / math.hypot(u, v), 2.72 * v / math.hypot(u, v)) for u, v in socket]
        key.rings([row(sleeve, 19.65), row(sleeve, 13.2), row(socket, 13.2), row(socket, 18.85)], cap, False)

        def mark(u, v):
            return cx - 1 + v, 20.665 + 0.055 * v, cd + u

        for j, label in enumerate(["Cherry", name]):
            key.label(label, 2.36, lambda u, v: mark(u, v - 1 - j * 2.65), ink)
        marker = [mark(u, v + 3.55) for u, v in rounded(6.4, 1.75, 0.79)]
        key.add(marker, [tuple(range(len(marker)))], pigment, False)
        attach(key.finalize())
    return root, visible, hidden, collection
