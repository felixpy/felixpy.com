import json
import math
import runpy
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

scripts = Path(__file__).resolve().parent
root = scripts.parents[1]
archive = root / ".references/05-摄影与陈列/录音与存储配件"
bpy.ops.wm.read_factory_settings(use_empty=True)
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
tools = runpy.run_path(str(scripts / "rog-peripheral-tools.py"))
slab, corners = tools["slab"], tools["corners"]
body = finish("Anthracite PC-ABS", "252628", 0.11, 0.55)
cover = finish("Textured top shell", "424347", 0.10, 0.59)
polished = finish("Polished mould detail", "171719", 0.22, 0.32)
tpe = finish("Recessed magnetic base", "373838", 0.04, 0.81)
steel = finish("Stamped card cage", "8f908e", 0.77, 0.36)
shadow = finish("Socket polymer", "161719", 0.05, 0.60)
ferrule = finish("Contact plating", "b1975d", 0.71, 0.38)
printed = finish("White slot legends", "c4c4c0", 0.11, 0.49)
lamp = finish("Amber status lens", "bb7432", 0.19, 0.36, 0.15, 0.16)
cfexpress = runpy.run_path(str(scripts / "cfexpress-interface.py"))


def well(part, name, s, h, w, thickness, r):
    side = -1 if name == "USB-C" else 1

    def project(x, y, z):
        return (x * side, y, z * side)

    ring = [(x + s, y + h) for x, y in corners(w, thickness, r)]
    throat = cfexpress["CAGE_MOUTH"]
    tip = cfexpress["SEATED_TIP"]
    stop = {"CFexpress B": tip - 1.025, "SD UHS-II": 12.5, "USB-C": 29.2}[name]
    part.rings(
        [[project(x, y, z) for x, y in ring] for z in (35.3, throat)],
        shadow,
        False,
        False,
    )
    part.rings(
        [[project(x, y, z) for x, y in ring] for z in (throat, stop)],
        steel if name != "USB-C" else shadow,
        False,
        False,
    )
    part.add(
        [project(x, y, stop) for x, y in ring], [tuple(range(len(ring)))], shadow, False
    )
    if name == "CFexpress B":
        for first, last in [(-12, -6), (-3.2, 3.2), (6, 12)]:
            slab(
                part,
                s + (first + last) / 2,
                tip + 0.52,
                last - first + 0.75,
                3.2,
                0.12,
                [(h - 0.66, 0.06), (h - 0.30, 0)],
                shadow,
            )
        for x in cfexpress["CONTACT_CENTERS"]:
            part.pipe(
                [
                    (s + x, h - 0.65, tip - 0.65),
                    (s + x, h - 0.72, tip + 0.25),
                    (s + x, h - 0.82, tip + 1.17),
                    (s + x, h - 0.75, tip + 1.91),
                ],
                0.085,
                ferrule,
                8,
                1.85,
            )
        for sign in (-1, 1):
            slab(
                part,
                s + sign * 15.32,
                (throat + stop) / 2,
                0.43,
                throat - stop - 0.6,
                0.16,
                [(h - 1.95, 0.06), (h + 1.87, 0)],
                shadow,
            )
    if name == "SD UHS-II":
        for count, depth in [(9, 15.0), (8, 20.0)]:
            for j in range(count):
                x = s + (j - (count - 1) / 2) * 2.38
                part.pipe(
                    [
                        (x, h - 1.23, depth - 1.8),
                        (x, h - 0.86, depth - 0.18),
                        (x, h - 0.65, depth + 0.68),
                        (x, h - 0.81, depth + 1.5),
                    ],
                    0.11,
                    ferrule,
                    8,
                    1.70,
                )
    if name == "USB-C":
        slab(part, -s, -33.1, 6.5, 2.3, 0.45, [(h - 0.31, 0), (h + 0.31, 0)], polished)
    return ring


def letter_contours(text, size, cx, cy):
    vertices, faces = sculpt["letters"](text, False)
    return [
        [(cx + vertices[i][0] * size, cy + vertices[i][1] * size) for i in f]
        for f in faces
    ]


def printed_panel(part, edge, openings, artwork, surface, ink, project, recess=0):
    points, loops = [], []
    for ring in [edge, *openings, *artwork]:
        area = sum(x * b - a * y for (x, y), (a, b) in zip(ring, ring[1:] + ring[:1]))
        ring = ring if area > 0 else list(reversed(ring))
        loops.append(list(range(len(points), len(points) + len(ring))))
        points.extend(Vector(p) for p in ring)
    vv, _, tris, _, _, ids = delaunay_2d_cdt(points, [], loops, 0, 0.00001)
    fields = ([], [])
    for tri, region in zip(tris, ids):
        if 0 in region and all(i == 0 or i > len(openings) for i in region):
            fields[(len(region) - 1) % 2].append(tri)
    for faces, material, depth in zip(fields, (surface, ink), (0, recess)):
        if faces:
            part.add([project(v.x, v.y, depth) for v in vv], faces, material, False)
    if recess:
        for ring in artwork:
            part.rings(
                [[project(x, y, d) for x, y in ring] for d in (0, recess)],
                ink,
                False,
                False,
            )


def face(part, side, openings, legends=()):
    edge = [(-30.9, 1.25), (30.9, 1.25), (30.9, 14.25), (-30.9, 14.25)]
    printed_panel(
        part,
        edge,
        openings,
        legends,
        body,
        printed,
        lambda x, y, depth: (x * side, y, (35.3 - depth) * side),
    )


def scalloped_top(lid, shell):
    roof = [(x, z) for x, _, z in shell]
    design = [(-12, -6.5), (0, 3.2), (12, -6.5), (0, -0.82)]
    chevrons = [
        [(x * scale, z + y * scale) for x, y in design]
        for z, scale in [(-14.0, 0.67), (-4.9, 0.84), (6.1, 1.0)]
    ]
    contours = json.loads((scripts / "prograde-reader-wordmark.json").read_text())
    artwork = [
        [((x - 183) * 0.121, 20.1 + (y - 21.5) * 0.121) for x, y in ring]
        for ring in contours
    ]
    printed_panel(
        lid,
        roof,
        chevrons,
        artwork,
        cover,
        polished,
        lambda x, z, d: (x, 17.77 - d, z),
        0.15,
    )
    for ring in chevrons:
        top = [(x, 17.77, z) for x, z in ring]
        base = [(x, 17.57, z) for x, z in ring]
        lid.rings([top, base], polished, False, False)
        lid.add(base, [(0, 1, 3), (1, 2, 3)], polished, False)


def main():
    outer = Sculpture("Moulded base, two card apertures and USB-C receptacle")
    periphery = corners(70.6, 70.6, 4.4, 12)
    for i, (x, z) in enumerate(periphery):
        u, v = periphery[(i + 1) % len(periphery)]
        if abs(z - v) < 0.0001 and abs(z) > 35.29:
            continue
        outer.add(
            [(x, 1.25, z), (u, 1.25, v), (u, 14.25, v), (x, 14.25, z)],
            [(0, 1, 2, 3)],
            body,
            False,
        )
    receivers = Sculpture(
        "CFexpress B and SD cages, spring contacts and USB receptacle"
    )
    rings = [
        well(receivers, *row)
        for row in [
            ("CFexpress B", 3.7, 10.82, 31.25, 4.63, 0.43),
            ("SD UHS-II", 2.8, 5.42, 25.8, 2.65, 0.35),
        ]
    ]
    legends = letter_contours("CFexpress B", 2.28, -21.8, 10.9)
    legends += letter_contours("SD UHS-II", 2.24, -20.9, 5.40)
    face(outer, 1, rings, legends)
    face(outer, -1, [well(receivers, "USB-C", 0, 8.6, 8.95, 3.42, 1.47)])
    outer.finalize()
    receivers.finalize()
    lid = Sculpture("Scalloped shell cap and moulded side grips")
    rows = []
    for h, inset in [(14.25, 0), (15.0, 0.22), (17.50, 1.32), (17.77, 1.79)]:
        w = 70.6 - 2 * inset
        boundary = corners(w, w, 4.4 - inset, 12)
        profile = []
        for i, (x, z) in enumerate(boundary):
            nx, nz = boundary[(i + 1) % len(boundary)]
            steps = 36 if abs(z - nz) > 22 and abs(x - nx) < 0.01 else 1
            for k in range(steps):
                xx, zz = x + (nx - x) * k / steps, z + (nz - z) * k / steps
                dent = (
                    1.8 * math.exp(-((abs(zz) / 15) ** 4)) * (h - 14.25) / 3.52
                    if abs(xx) > 28
                    else 0
                )
                profile.append((xx - math.copysign(dent, xx), h, zz))
        rows.append(profile)
    lid.rings(rows, cover, True, False)
    scalloped_top(lid, rows[-1])
    for sign in (-1, 1):
        for i in range(14):
            z = (i - 6.5) * 4.17
            for a, b in [(2.8, 5.15), (12.20, 15.15)]:
                lid.pipe(
                    [
                        (35.27 * sign, a, z - 0.36),
                        (35.29 * sign, b - 0.65, z + 0.38),
                        (35.04 * sign, b, z + 0.63),
                    ],
                    0.27,
                    shadow,
                    8,
                )
    lid.finalize()
    printwork = Sculpture("ProGrade wordmark, slot legends and indicator lenses")
    for h in (10.9, 5.40):
        printwork.pipe([(25.0, h, 35.34), (27.1, h, 35.34)], 0.22, lamp, 10)
    printwork.finalize()
    sole = Sculpture("Magnetic mounting surface and recessed rubber surround")
    slab(
        sole,
        0,
        0,
        70.8,
        70.8,
        4.6,
        [(0.35, 1.5), (0.53, 1.1), (1.23, 0.10), (1.26, 0.10)],
        body,
    )
    rings = [
        [(x, h, z) for x, z in corners(61.3 - 2 * inset, 61.3 - 2 * inset, 3.1 - inset)]
        for h, inset in [(0, 0.23), (0.10, 0.04), (0.40, 0)]
    ]
    sole.rings(rings, tpe, True, False)
    sole.add(rings[-1], [tuple(range(len(rings[-1])))], tpe, False)
    printed_panel(
        sole,
        [(x, z) for x, _, z in rings[0]],
        [],
        letter_contours("ProGrade Digital  PG05.5", 2.08, 0, 15),
        tpe,
        printed,
        lambda x, z, d: (x, d, z),
    )
    sole.finalize()
    source = archive / "CFexpress Type B card/Blender/cfexpress-type-b.blend"
    if not source.exists():
        subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--",
                bpy.app.binary_path,
                "-b",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "-P",
                str(scripts / "build-cfexpress.py"),
            ],
            check=True,
        )
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (
        existing,
        imported,
    ):
        imported.objects = [
            n for n in existing.objects if n.startswith("256 GB CFexpress")
        ]
    if len(imported.objects) != 1:
        raise ValueError("Expected one full-size CFexpress card")
    card = imported.objects[0].copy()
    bpy.context.scene.collection.objects.link(card)
    card_center = (cfexpress["SEATED_TIP"] + cfexpress["CARD_LENGTH"] / 2) / 1000
    card.location = (0.0037, -card_center, 0.01082)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.wm.save_as_mainfile(
        filepath=str(archive / "ProGrade Digital PG05.5/Blender/prograde-pg05-5.blend"),
        compress=True,
    )
    card.data = card.data.copy()
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = card
    bpy.ops.object.join()
    target = root / "public/media/models/prograde-pg05-5.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
    )


if __name__ == "__main__":
    main()
