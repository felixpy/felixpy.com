import math
import sys
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from product_workshop import Product, finish_material, finishes

finishes["black-oxide"] = ("302f30", 0.42, 0.64)


def solid(part, name, finish, rings, bevel=0):
    count = len(rings[0])
    ends = [
        tuple(range(count)),
        tuple(range((len(rings) - 1) * count, len(rings) * count)),
    ]
    sides = [
        (
            i + j * count,
            (i + 1) % count + j * count,
            (i + 1) % count + (j + 1) * count,
            i + (j + 1) * count,
        )
        for j in range(len(rings) - 1)
        for i in range(count)
    ]
    vertices = [
        tuple(axis / 1000 for axis in point) for ring in rings for point in ring
    ]
    obj = part.surface(name, finish, vertices, ends + sides)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    if bevel:
        edge = obj.modifiers.new("Tool edge radius", "BEVEL")
        edge.width, edge.segments, edge.harden_normals = bevel / 1000, 2, True
        obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return obj


def thumbscrew(part, height):
    recess = [
        (1.8, 0.42),
        (0.42, 0.42),
        (0.42, 1.8),
        (-0.42, 1.8),
        (-0.42, 0.42),
        (-1.8, 0.42),
        (-1.8, -0.42),
        (-0.42, -0.42),
        (-0.42, -1.8),
        (0.42, -1.8),
        (0.42, -0.42),
        (1.8, -0.42),
    ]
    angles = sorted(
        {math.atan2(y, z) % math.tau for z, y in recess}
        | {i * math.tau / 60 for i in range(60)}
    )

    def circle(x, radius, fluted=False):
        ring = []
        for a in angles:
            r = radius - (0.17 * (1 - math.cos(30 * a)) / 2 if fluted else 0)
            ring.append((x, height + r * math.sin(a), r * math.cos(a)))
        return ring

    def drive(x, scale):
        ring = []
        for a in angles:
            c, s = math.cos(a), math.sin(a)
            u, v = max(abs(c), 1e-9), max(abs(s), 1e-9)
            r = scale * max(min(1.8 / u, 0.42 / v), min(0.42 / u, 1.8 / v))
            ring.append((x, height + s * r, c * r))
        return ring

    solid(
        part,
        "Black knurled locking screw with recessed cross drive",
        "black-oxide",
        [
            circle(-10.8, 2.45),
            circle(-13.1, 2.45),
            circle(-13.1, 4.2),
            circle(-13.45, 4.55, True),
            circle(-16.0, 4.55, True),
            circle(-16.35, 4.15),
            drive(-16.35, 1),
            drive(-15.30, 0.73),
        ],
    )


def build():
    part = Product("gr701-holder")
    section = [
        (5.6, -12),
        (5.6, 12),
        (-5, 12),
        (-6.6, 10.4),
        (-6.6, 2.3),
        (-4.4, 2.3),
        (-4.4, 4.2),
        (-1.0, 4.2),
        (-1, -4.2),
        (-4.4, -4.2),
        (-4.4, -2.3),
        (-6.6, -2.3),
        (-6.6, -10.4),
        (-5, -12),
    ]
    solid(
        part,
        "Anodised T-slot extrusion",
        "graphite",
        [[(x, y, z) for x, z in section] for y in (-139.35, 232)],
        0.28,
    )
    for y, long_arm in [(-13, False), (-116, True)]:
        face = [
            (-10, 6),
            (-6, 9),
            (9, 9),
            (11, 6),
            (11, -6),
            (7, -10),
            (-8, -10),
            (-10, -8),
        ]
        solid(
            part,
            "Sliding carriage",
            "graphite",
            [[(x, y + dy, z) for z, dy in face] for x in (-11.1, -6.6)],
            0.48,
        )
        part.block(
            "T-slot shoe",
            "black",
            (-0.0045, y / 1000, 0),
            (0.0048, 0.013, 0.0043),
            0.00025,
        )
        thumbscrew(part, y)
        if long_arm:
            plan = [
                (-8, 10),
                (-5, 7),
                (-5, -8),
                (-25, -13),
                (-55, -19),
                (-73, -17),
                (-73, -6),
                (-53, 1),
                (-34, 4),
            ]
        else:
            plan = [
                (-5, 10),
                (-5, -9),
                (-10, -13),
                (-14, -20),
                (-25, -24),
                (-27, -21),
                (-27, -11),
                (-21, -6),
                (-17, 9),
            ]
        top = y + 11.2
        arm = solid(
            part,
            "Vertical GPU support arm" if long_arm else "Horizontal GPU support tongue",
            "graphite",
            [[(x, h, z) for x, z in plan] for h in (top - 2.8, top)],
            0.45,
        )
        if long_arm:
            ends = [(-61, -10.5), (-33, -3)]
            slot = [
                (x + 1.3 * math.cos(a), z + 1.3 * math.sin(a))
                for (x, z), start in zip(ends, (math.pi * 0.58, -math.pi * 0.42))
                for a in [start + i * math.pi / 12 for i in range(13)]
            ]
            cut = solid(
                Product("cut"),
                "Retaining stop travel",
                "black",
                [[(x, h, z) for x, z in slot] for h in (top - 4, top + 1)],
            )
            boolean = arm.modifiers.new("Stop adjustment slot", "BOOLEAN")
            boolean.operation, boolean.object = "DIFFERENCE", cut
            bpy.context.view_layer.objects.active = arm
            bpy.ops.object.modifier_move_to_index(modifier=boolean.name, index=0)
            bpy.ops.object.modifier_apply(modifier=boolean.name)
            bpy.data.objects.remove(cut, do_unlink=True)
            part.rod(
                "Vertical card retaining stop",
                "black-oxide",
                (-0.055, (top - 1) / 1000, -0.0089),
                (-0.055, (top + 3) / 1000, -0.0089),
                0.0029,
                0.0024,
            )
        else:
            pad = [
                (-16, -11),
                (-17, -19),
                (-21, -22),
                (-25.1, -20),
                (-25.1, -12),
                (-22, -10),
            ]
            solid(
                part,
                "Elastomer contact on the fan shroud perimeter",
                "black",
                [[(x, h, z) for x, z in pad] for h in (top, 0)],
                0.25,
            )
    return part


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    part = build()
    for finish, objects in part.parts.items():
        for obj in objects:
            obj.data.materials.append(finish_material(finish))
    blend = ROOT / ".review/atelier/pc-components/gr701-holder.blend"
    blend.parent.mkdir(exist_ok=True, parents=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    part.export(ROOT / "public/media/models")
