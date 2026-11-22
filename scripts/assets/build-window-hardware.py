import argparse
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import barrel, bevel, block, export_batch, xyz


def solid(name, loops, closed=False, radius=0):
    vertices = [xyz(point) for loop in loops for point in loop]
    n = len(loops[0])
    faces = []
    for j in range(len(loops) if closed else len(loops) - 1):
        next_j = (j + 1) % len(loops)
        for i in range(n):
            next_i = (i + 1) % n
            faces.append(
                (j * n + i, j * n + next_i, next_j * n + next_i, next_j * n + i)
            )
    if not closed:
        faces.extend(
            [
                tuple(reversed(range(n))),
                tuple((len(loops) - 1) * n + i for i in range(n)),
            ]
        )
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return bevel(obj, radius)


def frame(name, edges, section, radius):
    y0, z0, y1, z1 = edges
    corners = [(y0, z0, 1, 1), (y1, z0, -1, 1), (y1, z1, -1, -1), (y0, z1, 1, -1)]
    return solid(
        name,
        [
            [(x, y + dy * offset, z + dz * offset) for x, offset in section]
            for y, z, dy, dz in corners
        ],
        True,
        radius,
    )


def extruded_rose(name, z, y, outline, sections):
    return solid(
        name,
        [
            [(x, y + dy * scale, z + dz * scale) for dy, dz in outline]
            for x, scale in sections
        ],
        radius=0.3,
    )


def fittings():
    metal, bush = [], []
    z, y, mount = 596, 537, 31
    outline = []
    for cy, a0 in [(19, 0), (-19, math.pi)]:
        for j in range(13):
            a = a0 + math.pi * j / 12
            outline.append((cy + math.sin(a) * 14.9, math.cos(a) * 14.9))
    bush.append(
        extruded_rose(
            "Recessed nylon rosette base",
            z,
            y,
            outline,
            [(mount - 1, 0.985), (mount + 1.2, 1)],
        )
    )
    metal.append(
        extruded_rose(
            "Full floating silver rosette cover",
            z,
            y,
            outline,
            [(mount + 0.9, 0.99), (mount + 5.2, 1), (mount + 6, 0.965)],
        )
    )
    for offset in (-21.5, 21.5):
        bush.append(
            barrel(
                "Locating lug",
                (mount - 7, y + offset, z),
                (mount, y + offset, z),
                5,
                16,
            )
        )
    metal.append(
        block("Seven millimetre square spindle", (36, 7, 7), (mount - 14, y, z), 0.24)
    )
    bush.append(
        barrel("Nylon neck bearing", (mount + 5.8, y, z), (mount + 8, y, z), 11.6, 32)
    )
    stations = [
        (7, 0, 0, 10.5, 11),
        (11, 0, 0, 10.4, 10.8),
        (25, 0.2, 0.3, 9.2, 10),
        (34, 0, 0.6, 9, 9.6),
        (40, -2, 0.8, 8.8, 9.4),
        (44.2, -6, 1, 8.6, 9.3),
        (46.5, -12, 1.1, 8.4, 9.2),
        (47.4, -20, 1.25, 8.1, 9.1),
        (48.3, -31, 1.45, 7.7, 9),
        (49.8, -53, 1.5, 7.4, 8.7),
        (51, -76, 1.3, 7, 8.3),
        (50.9, -97, 0.7, 6.5, 7.8),
        (49.4, -116, 0, 5.9, 7.3),
        (48.6, -123, -0.35, 5.6, 7),
        (48.1, -125.5, -0.4, 4.7, 6.4),
        (48, -126.7, -0.4, 2.9, 4.5),
    ]
    rings = []
    for i, (xp, yp, zp, depth, width) in enumerate(stations):
        previous = Vector(stations[max(0, i - 1)][:2])
        following = Vector(stations[min(i + 1, len(stations) - 1)][:2])
        tangent = (following - previous).normalized()
        loops = []
        for j in range(24):
            a = math.tau * j / 24
            across = math.copysign(abs(math.cos(a)) ** 0.86, math.cos(a))
            up = math.copysign(abs(math.sin(a)) ** 0.86, math.sin(a))
            loops.append(
                (
                    mount + xp - tangent.y * depth * up,
                    y + yp + tangent.x * depth * up,
                    z + zp + width * across,
                )
            )
        rings.append(loops)
    lever = solid("Amsterdam variable-section die-cast lever", rings)
    for poly in lever.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    metal.append(lever)
    for hy in (240, 872):
        for end, length in [(-27, 17.3), (-8.7, 17.4), (9.8, 17.3)]:
            bush.append(
                barrel(
                    "Three-part sash hinge barrel",
                    (34.5, hy + end, 48.6),
                    (34.5, hy + end + length, 48.6),
                    5.7,
                    24,
                )
            )
        metal.append(
            barrel(
                "Hinge pin end cap",
                (34.5, hy + 27.1, 48.6),
                (34.5, hy + 28.5, 48.6),
                5.35,
                24,
            )
        )
        bush.append(block("Hinge fixed leaf", (7, 48, 12), (29.8, hy, 41), 1))
        bush.append(block("Hinge vent leaf", (7, 22, 11), (31, hy, 55), 1))
    return metal, bush


def glazing():
    aluminum, seals = [], []
    outer = (0, 0, 1353, 1610)
    aluminum.append(
        frame(
            "Mitred 75 mm window section",
            outer,
            [
                (-40, 0),
                (25.4, 0),
                (27, 1.4),
                (27, 33),
                (23, 39),
                (11, 41),
                (11, 28),
                (-20, 28),
                (-22, 39),
                (-38, 39),
                (-40, 37),
            ],
            0.52,
        )
    )
    seals.append(
        frame(
            "Polyamide thermal separator",
            outer,
            [(-18, 27), (10, 27), (10, 33), (-18, 33)],
            0.25,
        )
    )
    stile = 627.9
    bar_width = 30
    aluminum.append(
        block("Continuous mullion", (60, 1280, bar_width), (-5, 677, stile), 1)
    )
    transom_y = 1127
    for left, right in [(35, stile - bar_width / 2), (stile + bar_width / 2, 1575)]:
        aluminum.append(
            block("Fixed upper transom", (62, 28, right - left), (-6.8, transom_y, (left + right) / 2), 0.9)
        )
    panes = [
        (34, 34, transom_y - 14, stile - 15),
        (34, stile + 15, transom_y - 14, 1576),
        (transom_y + 14, 34, 1319, stile - 15),
        (transom_y + 14, stile + 15, 1319, 1576),
    ]
    for i, edges in enumerate(panes):
        sash = i == 0
        face = 31 if sash else 24
        w = 35 if sash else 8
        shape = [
            (-28, 0),
            (face - 1, 0),
            (face, 0.9),
            (face, w - 4),
            (face - 6, w),
            (13, w + 1),
            (9, w),
            (-18, w),
            (-25, w + 1),
            (-28, w - 1),
        ]
        y0, z0, y1, z1 = edges
        clearance = 2.6 if sash else 1.4
        edges = (y0 + clearance, z0 + clearance, y1 - clearance, z1 - clearance)
        aluminum.append(
            frame("Opening vent" if sash else "Sloped glazing bead", edges, shape, 0.65)
        )
        seals.append(
            frame(
                "Sash closing gasket" if sash else "Glazing bead bedding gasket",
                edges,
                [(14, -clearance - 2.6), (21.5, -clearance - 2.6), (21.5, 2), (14, 2)],
                0.35,
            )
        )
        for x, lead in [(-15.2, -1), (9.2, 1)]:
            seals.append(
                frame(
                    "EPDM compression lip",
                    edges,
                    [
                        (x, w - 0.7),
                        (x + lead * 4.6, w - 0.7),
                        (x + lead * 4.4, w + 1.3),
                        (x + lead * 0.7, w + 4.3),
                        (x, w + 4.3),
                    ],
                    0.22,
                )
            )
    return aluminum, seals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("public/media/models"))
    parser.add_argument("--blend", type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    alloy, seals = glazing()
    silver, bush = fittings()
    bpy.context.view_layer.update()
    for name, items in [
        ("window-extrusions", alloy),
        ("window-epdm", seals),
        ("amsterdam-casting", silver),
        ("amsterdam-hinges", bush),
    ]:
        print(name, export_batch(name, items, args.out / f"{name}.mesh"))
    if args.blend:
        collection = bpy.data.collections.new("Pocket window sash · bronze frame and HOPPE fittings")
        bpy.context.scene.collection.children.link(collection)
        for items, title, rgb, roughness, metalness in [
            (alloy, "Bronze anodised aluminium", "544f43", 0.57, 0.48),
            (seals + bush, "Glazing rubber and hinge inserts", "272e2e", 0.93, 0.0),
            (silver, "Satin lever and cap", "b4b7b8", 0.32, 0.69),
        ]:
            mat = bpy.data.materials.new(title)
            mat.use_nodes = True
            shader = mat.node_tree.nodes.get("Principled BSDF")
            srgb = [int(rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            linear = [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in srgb]
            shader.inputs["Base Color"].default_value = [*linear, 1]
            shader.inputs["Roughness"].default_value = roughness
            shader.inputs["Metallic"].default_value = metalness
            mat.diffuse_color = [*linear, 1]
            for obj in items:
                for owner in list(obj.users_collection):
                    owner.objects.unlink(obj)
                collection.objects.link(obj)
                obj.data.materials.append(mat)
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))


if __name__ == "__main__":
    main()
