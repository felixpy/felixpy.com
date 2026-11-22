import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from blender_parts import barrel, bevel, export_batch, pipe, xyz

PRODUCT = ROOT / ".references/03-电脑硬件/风扇与水冷/ROG Strix 140 mm ARGB"
FRAME = "Model 14 · stationary moulding"
SCREWS = "Model 14 · mounting screws"
FINISHES = {
    "nylon": ("Glass-filled nylon", (0.023, 0.024, 0.027), 0.0, 0.51),
    "satin": ("Polished die surfaces", (0.047, 0.050, 0.054), 0.09, 0.37),
    "label": (
        "Graphite motor label and PVC conductors",
        (0.016, 0.018, 0.020),
        0.05,
        0.48,
    ),
    "ink": ("Rear motor label screen print", (0.60, 0.62, 0.62), 0.15, 0.49),
    "screws": ("Black oxide on steel", (0.059, 0.060, 0.065), 0.78, 0.37),
}


def circle(r, x=0, y=0, n=96):
    return [
        (x + r * math.cos(i * math.tau / n), y + r * math.sin(i * math.tau / n))
        for i in range(n)
    ]


def quarter(points, side):
    angle = side * math.pi / 2
    c, s = round(math.cos(angle)), round(math.sin(angle))
    return [(x * c - y * s, x * s + y * c) for x, y in points]


def solid(name, outline, holes, z0, z1, edge=0.12):
    loops = [outline, *holes]
    coordinates = []
    polygons = []
    for points in loops:
        polygons.append(list(range(len(coordinates), len(coordinates) + len(points))))
        coordinates.extend(Vector((x, y)) for x, y in points)
    points, _, faces, originals, _, owners = delaunay_2d_cdt(
        coordinates, [], polygons, 1, 0.000005
    )
    verts = [(x, y, z) for z in (z0, z1) for x, y in points]
    result = []
    size = len(points)
    for tri, ids in zip(faces, owners):
        if list(ids) == [0]:
            result.extend([tuple(reversed(tri)), tuple(i + size for i in tri)])
    lookup = {old: i for i, ids in enumerate(originals) for old in ids}
    for indices in polygons:
        loop = [lookup[j] for j in indices]
        for a, b in zip(loop, loop[1:] + loop[:1]):
            result.append((a, b, b + size, a + size))
    return surface(name, verts, result, edge)


def surface(name, points, faces, edge=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(p) for p in points], [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return bevel(obj, edge)


def rolled(name, profiles, x=0, y=0, count=128):
    points = [(a, b, z) for z, r in profiles for a, b in circle(r, x, y, count)]
    faces = [
        (
            j * count + i,
            j * count + (i + 1) % count,
            k * count + (i + 1) % count,
            k * count + i,
        )
        for j in range(len(profiles))
        for k in [(j + 1) % len(profiles)]
        for i in range(count)
    ]
    obj = surface(name, points, faces)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def print_text(name, caption, x, y, z, size, tangent=0, reverse=False):
    font = bpy.data.curves.new(name, "FONT")
    font.body = caption
    font.align_x = "CENTER"
    font.align_y = "CENTER"
    font.size = size * 0.001
    font.resolution_u = 4
    obj = bpy.data.objects.new(name, font)
    bpy.context.collection.objects.link(obj)
    trans = (
        Matrix.Translation(xyz((x, y, z)))
        @ Matrix.Rotation(math.pi / 2, 4, "X")
        @ Matrix.Rotation(tangent, 4, "Z")
    )
    obj.matrix_world = trans @ Matrix.Rotation(math.pi, 4, "Y") if reverse else trans
    return obj


def build():
    groups = {key: [] for key in FINISHES}
    body, satin, rubber, ink, screws = (groups[k] for k in FINISHES)
    border = [
        (x, y) for side in range(4) for x, y in quarter([(70, -62.8), (70, 62.8)], side)
    ]
    pitch = 62.25
    bolt_holes = [
        circle(2.32, x, y, 28) for x in (-pitch, pitch) for y in (-pitch, pitch)
    ]
    marks = [
        circle(2.05, x, y, 20)
        for i in range(4)
        for x, y in quarter([(51.6, 66.8), (66.8, 51.6)], i)
    ]
    body.append(
        solid(
            "Intake flange · eight recessed die witnesses",
            border,
            [circle(66.75), *bolt_holes, *marks],
            5.60,
            7.0,
            0.18,
        )
    )
    for i in range(4):
        for j, (x, y) in enumerate(quarter([(51.6, 66.8), (66.8, 51.6)], i)):
            satin.append(
                barrel(
                    f"Mould insert witness {i + 1}.{j + 1}",
                    (x, y, 5.54),
                    (x, y, 6.76),
                    2.041,
                    20,
                )
            )
    body.append(
        solid(
            "Exhaust flange · open mounting ears",
            border,
            [circle(66.75), *bolt_holes],
            -18,
            -15.4,
            0.20,
        )
    )
    body.append(
        rolled(
            "Bellmouth, blade clearance and narrow outer waist",
            [
                (7, 66.83),
                (6.6, 66.25),
                (5.4, 65.42),
                (3.5, 64.97),
                (-13, 64.97),
                (-15.8, 65.52),
                (-17.6, 66.32),
                (-18, 66.85),
                (-17.65, 68),
                (-14.9, 68.5),
                (4.6, 68.55),
                (6.6, 68.1),
            ],
        )
    )
    for i in range(4):
        x, y = quarter([(pitch, pitch)], i)[0]
        body.append(
            rolled(
                f"Intake pilot boss {i + 1}",
                [(5.8, 2.32), (5.8, 3.7), (2.5, 3.42), (2.5, 2.32)],
                x,
                y,
                32,
            )
        )
        body.append(
            rolled(
                f"Exhaust pilot boss {i + 1}",
                [(-15.5, 2.32), (-15.5, 3.75), (-12, 3.42), (-12, 2.32)],
                x,
                y,
                32,
            )
        )
        for j, offset in enumerate((0, 4.3)):
            rib = quarter(
                [
                    (43.2 + offset, 53.8 - offset),
                    (45.2 + offset, 52.3 - offset),
                    (60.5 + offset, 64 - offset),
                    (59.2 + offset, 65.5 - offset),
                ],
                i,
            )
            body.append(
                solid(
                    f"Corner diagonal bridge rib {i + 1}.{j + 1}",
                    rib,
                    [],
                    -15.65,
                    5.72,
                    0.20,
                )
            )
        spoke = quarter(
            [
                (63.6, 14.6),
                (66.3, 15.3),
                (66.8, 21.7),
                (14.0, 21.1),
                (9.6, 21.8),
                (6.1, 18.0),
                (7.8, 14.1),
            ],
            i,
        )
        body.append(
            solid(f"Stationary motor support {i + 1}", spoke, [], -17.8, -14.6, 0.46)
        )
        if i == 1:
            for j in range(4):
                lane = 15.99 + j * 1.02
                knots = quarter(
                    [
                        (11.5, lane),
                        (21, lane),
                        (43, lane),
                        (61, lane),
                        (64.6, lane + 0.18),
                    ],
                    i,
                )
                rubber.append(
                    pipe(
                        f"Recessed PWM conductor {j + 1}",
                        [(x, y, -17.96) for x, y in knots],
                        0.46,
                    )
                )
            for j, position in enumerate((33.5, 51.0)):
                edge = quarter(
                    [
                        (position, 15.0),
                        (position + 1.48, 15.0),
                        (position + 1.48, 20.8),
                        (position, 20.8),
                    ],
                    i,
                )
                body.append(
                    solid(
                        f"Wire-retaining bridge {j + 1}", edge, [], -18.45, -17.7, 0.13
                    )
                )
        bore = 2.24
        bolt = []
        for j in range(4):
            bolt += quarter(
                [(0.43, 2.19), (-0.43, 2.19), (-0.46, 0.74), (-0.74, 0.46)], j
            )
        bolt = [(x + a, y + b) for a, b in bolt]
        screws.append(
            solid(
                f"Cross-recess flange screw {i + 1}",
                circle(3.80, x, y, 40),
                [bolt],
                7.56,
                8.63,
                0.22,
            )
        )
        screws.append(
            barrel(
                f"Pan-head socket floor and pilot {i + 1}",
                (x, y, 4.85),
                (x, y, 7.60),
                bore,
                32,
            )
        )
    body.append(
        barrel(
            "Stationary 45 mm motor can", (0, 0, -17.78), (0, 0, -4.85), 22.7, 112, 20.4
        )
    )
    rubber.append(
        barrel(
            "Circular identification label", (0, 0, -18.13), (0, 0, -17.78), 21.45, 96
        )
    )
    for idx, (caption, y, size) in enumerate(
        [
            ("REPUBLIC OF GAMERS", 7.8, 1.9),
            ("ROG STRIX MODEL 14 ARGB", 2.6, 2.48),
            ("DC 12V     PWM", -3.7, 2.17),
            ("CE     UKCA     EAC", -9.6, 2.4),
        ]
    ):
        ink.append(
            print_text(
                f"Laser-printed line {idx + 1}",
                caption,
                0,
                y,
                -18.170,
                size,
                reverse=True,
            )
        )
    legend = "REPUBLIC OF GAMERS"
    for idx, ch in enumerate(legend):
        if ch != " ":
            a = math.radians(100 + idx * 2.45)
            satin.append(
                print_text(
                    "Moulded intake legend " + str(idx + 1),
                    ch,
                    68.33 * math.cos(a),
                    68.33 * math.sin(a),
                    7.075,
                    2.05,
                    a + math.pi / 2,
                )
            )
    return groups


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    collections = {}
    for name in (FRAME, SCREWS):
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        collections[name] = collection
    for key, objects in build().items():
        name, color, metal, roughness = FINISHES[key]
        material = bpy.data.materials.new(name)
        material.diffuse_color = (*color, 1)
        material.use_nodes = True
        shader = material.node_tree.nodes["Principled BSDF"]
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = roughness
        collection = collections[SCREWS if key == "screws" else FRAME]
        for obj in objects:
            obj.data.materials.append(material)
            obj["mountGroup"] = key
            collection.objects.link(obj)
            scene.collection.objects.unlink(obj)
        bpy.context.view_layer.update()
        filename = "strix-140-" + key
        export_batch(
            filename, objects, ROOT / "public/media/models" / (filename + ".mesh")
        )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(PRODUCT / "Blender" / "strix-140-stationary-frame.blend"),
        compress=True,
    )


if __name__ == "__main__":
    main()
