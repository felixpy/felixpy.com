import argparse
import math
import sys
from pathlib import Path

import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import barrel, bevel, block, export_batch, pipe, xyz
from cabinet_rollers import running_gear
from mitutoyo_vernier import mount_caliper
from wera_insert_bits import build_bit_rack
from wera_kraftform import mount_drivers


def shell(name, loops, ring=False, radius=0):
    n = len(loops[0])
    faces = []
    for i in range(len(loops) if ring else len(loops) - 1):
        j = (i + 1) % len(loops)
        for k in range(n):
            l = (k + 1) % n
            faces.append((i * n + k, i * n + l, j * n + l, j * n + k))
    if not ring:
        faces.extend(
            [tuple(range(n)), tuple((len(loops) - 1) * n + k for k in range(n))]
        )
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(v) for loop in loops for v in loop], [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return bevel(obj, radius)


def capsule(cx, cy, depth, radius, straight):
    points = []
    for y, angle in [(straight, 0), (-straight, math.pi)]:
        for i in range(17):
            a = angle + i * math.pi / 16
            points.append(
                (cx + math.cos(a) * radius, cy + y + math.sin(a) * radius, depth)
            )
    return points


def door():
    board = block("Lacquered 16 mm sliding leaf", (292, 2280, 16), (0, 0, 0))
    opening = shell(
        "Routed flush pull pocket", [capsule(-122, -48, z, 13.4, 29) for z in (-10, 13)]
    )
    mod = board.modifiers.new("Routed through opening", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = opening
    bpy.context.view_layer.objects.active = board
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(opening, do_unlink=True)
    gear = running_gear(board, shell)
    bevel(board, 0.65)
    layers = [
        (15.3, 8.3),
        (15.1, 8.9),
        (14.3, 9.1),
        (11.5, 9.1),
        (10.3, 8.5),
        (10, 7.7),
        (10, -2.8),
        (9.4, -4),
        (8, -4.9),
    ]
    pull = shell(
        "Drawn satin-bronze recessed pull",
        [capsule(-122, -48, z, r, 29) for r, z in layers],
        True,
        0.13,
    )
    back = shell(
        "Back of the finger pocket",
        [capsule(-122, -48, z, 10.4, 29) for z in (-5.9, -5)],
        radius=0.45,
    )
    return {
        "pocket-front": [board],
        "pocket-lip": [pull],
        "pocket-back": [back],
        **gear,
    }


def profile(name, outline, back, front, cy, cz, r=0.15):
    return shell(
        name,
        [[(d, cy + y, cz + z) for z, y in outline] for d in (back, front)],
        radius=r,
    )


def tools():
    bright, dark, green, amber, ink = [], [], [], [], []
    pitch = 25.4

    def hanger(z, y, length=22):
        bright.append(
            pipe(
                "Formed steel peg with upturned end",
                [
                    (9, y + 8, z),
                    (7.8, y + 4, z),
                    (5.2, y, z),
                    (-1, y, z),
                    (-2.1, y - 4, z),
                    (-3, y - 10, z),
                    (-length + 3, y - 10, z),
                    (-length, y - 8, z),
                    (-length - 1, y - 3, z),
                ],
                1.65,
            )
        )

    caliper = mount_caliper(ink, shell, hanger, pitch)
    drivers = mount_drivers(bright, dark, amber, shell, pitch)
    for z in [-12 * pitch, -9 * pitch, -6 * pitch]:
        y = -1 * pitch
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.009,
            minor_radius=0.0019,
            major_segments=20,
            minor_segments=6,
            location=xyz((-25.4, y + 4, z)),
        )
        ring = bpy.context.object
        ring.name = "Steel tool supporting loop"
        bright.append(ring)
        for side in (-1, 1):
            bright.append(
                pipe(
                    "Braced hanger with returned anchor",
                    [
                        (8, y + 33, z),
                        (8, y + 27, z),
                        (4, y + 25.4, z),
                        (-1, y + 25.4, z),
                        (-4, y + 22, z),
                        (-5, y + 6, z),
                        (-18, y + 4, z + side * 6),
                        (-21, y + 4, z + side * 7.5),
                    ],
                    1.65,
                )
            )
    bit_z = 11 * pitch
    bit_y = -4 * pitch
    bit_holder, _, bits = build_bit_rack()
    bit_holder.location = xyz((-20, bit_y, bit_z))
    wood = bits.pop("workshop-birch")
    for z in (8 * pitch, 14 * pitch):
        hanger(z, bit_y, 41)
        bright.append(
            pipe(
                "Shelf knee",
                [
                    (0, bit_y - 25.4, z),
                    (-2, bit_y - 27, z),
                    (-34, bit_y - 11, z),
                    (-35, bit_y - 8, z),
                ],
                1.65,
            )
        )
    for j, z in enumerate([15 * pitch, 17 * pitch]):
        y = 2 * pitch
        hanger(z, y, 14)
        for sign in (-1, 1):
            outline = [
                (sign * 2, 1),
                (sign * 4.5, -3),
                (sign * 5, -20),
                (sign * 3.5, -69),
                (sign * 1.4, -102),
                ((4 if j else 0.7) * sign, -115),
                (sign * 0.6, -114),
                (sign * 0.4, -101),
                (sign * 1.7, -69),
                (sign * 3.1, -23),
                (sign * 2, 0),
            ]
            dark.append(
                profile(
                    "Spring tempered ESD tweezer leaf",
                    outline,
                    -9.2,
                    -14,
                    y - 10,
                    z,
                    0.22,
                )
            )
            bright.append(
                profile(
                    "Ground tweezer tip",
                    [
                        (sign * 1.37, -101),
                        ((4 if j else 0.7) * sign, -115),
                        (sign * 0.5, -115),
                        (sign * 0.4, -100),
                    ],
                    -9.2,
                    -14,
                    y - 10,
                    z,
                    0.12,
                )
            )
        bright.append(
            barrel("Tweezer spring bow", (-14, y - 9.5, z), (-9.2, y - 9.5, z), 3.4, 16)
        )
    spool_z, spool_y = -19 * pitch, 5 * pitch - 15
    hanger(spool_z, 5 * pitch, 39)

    def circle(depth, radius):
        return [
            (
                depth,
                spool_y + radius * math.cos(math.tau * i / 40),
                spool_z + radius * math.sin(math.tau * i / 40),
            )
            for i in range(40)
        ]

    for rim in [-8, -35]:
        dark.append(
            shell(
                "Hollow solder reel flange",
                [
                    circle(rim, 32.3),
                    circle(rim - 1.8, 32.3),
                    circle(rim - 1.8, 8.5),
                    circle(rim, 8.5),
                ],
                True,
                0.36,
            )
        )
    bright.append(
        shell(
            "Wound solder pack",
            [circle(-9.6, 25.1), circle(-35, 25.1), circle(-35, 9), circle(-9.6, 9)],
            True,
            0.2,
        )
    )
    for i in range(13):
        x = -10.2 - i * 1.9
        bright.append(
            shell(
                "Wound solder highlights",
                [circle(x + 0.6, 25.1), circle(x, 25.9), circle(x - 0.6, 25.1)],
                False,
            )
        )
    bin_y, bin_z = 5 * pitch, 10 * pitch
    wood.append(
        block("Peg shelf for fasteners", (77, 9, 238), (-38.5, bin_y, bin_z), 1.1)
    )
    for col in (6, 14):
        z = col * pitch
        bright.append(
            pipe(
                "Triangular peg shelf bracket",
                [
                    (8, bin_y + 9, z),
                    (7, bin_y + 5, z),
                    (0, bin_y, z),
                    (-3, bin_y - 5, z),
                    (-69, bin_y - 5, z),
                    (-68, bin_y - 9, z),
                    (-3, bin_y - 50, z),
                    (3, bin_y - 50.8, z),
                    (8, bin_y - 50.8, z),
                ],
                2,
            )
        )
    for i in range(3):
        center = bin_z + (i - 1) * 76
        back, front = -4, -71
        dark.append(
            block(
                "Parts cup base",
                (67, 2, 69),
                ((back + front) / 2, bin_y + 5.5, center),
                0.7,
            )
        )
        green.append(
            block("Parts cup back", (2, 41, 69), (back, bin_y + 25.6, center), 0.68)
        )
        green.append(
            block("Parts cup front", (2, 16, 69), (front, bin_y + 13, center), 0.65)
        )
        for side in (-1, 1):
            z = center + side * 34
            shape = [
                (back, bin_y + 5),
                (back, bin_y + 46),
                (back - 17, bin_y + 46),
                (front + 16, bin_y + 21),
                (front, bin_y + 21),
                (front, bin_y + 5),
            ]
            green.append(
                shell(
                    "Sloping open bin cheek",
                    [[(x, y, z + t) for x, y in shape] for t in (-0.8, 0.8)],
                    radius=0.6,
                )
            )
        for j in range(5):
            z = center - 22 + j * 10.3
            x = -23 - math.sin(j * 1.9 + i) * 9
            bright.append(
                barrel(
                    "Loose M4 socket fastener",
                    (x, bin_y + 9, z),
                    (x - 12, bin_y + 9.1, z + 7),
                    2,
                    10,
                )
            )
            dark.append(
                barrel(
                    "Fastener head",
                    (x, bin_y + 9, z),
                    (x + 3.8, bin_y + 9, z - 2.2),
                    3.4,
                    12,
                )
            )
    for z, y in [
        (-22 * pitch, -9 * pitch),
        (-22 * pitch, 9 * pitch),
        (0, 9 * pitch),
        (0, -9 * pitch),
        (22 * pitch, -9 * pitch),
        (22 * pitch, 9 * pitch),
    ]:
        bright.append(
            barrel(
                "Countersunk mounting washer", (-0.1, y, z), (-1.1, y, z), 4.8, 24, 3.8
            )
        )
        dark.append(block("Countersunk slot", (0.19, 0.7, 4.4), (-1.18, y, z)))
    return {
        **drivers,
        **bits,
        **caliper,
        "workshop-steel": bright,
        "workshop-black": dark,
        "workshop-birch": wood,
        "workshop-grips": green,
        "workshop-collars": amber,
        "workshop-etch": ink,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("public/media/models"))
    parser.add_argument("--blend", type=Path)
    parser.add_argument("--doors-only", action="store_true")
    parser.add_argument("--bit-library", type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    entries = door() if args.doors_only else {**door(), **tools()}
    bpy.context.view_layer.update()
    for name, items in entries.items():
        if name == "pocket-tyres":
            wheel = items[0]
            position = wheel.location.copy()
            wheel.location = (0, 0, 0)
            bpy.context.view_layer.update()
            export_batch(name, [wheel], args.out / f"{name}.mesh")
            wheel.location = position
        else:
            export_batch(name, items, args.out / f"{name}.mesh")
    if args.blend:
        entries["pocket-floor-track"][0].location.z = -1.149
        entries["pocket-head-track"][0].location.z = 1.146
        finishes = {
            "pocket-front": (0.78, 0.76, 0.68, 0.0, 0.63),
            "pocket-lip": (0.40, 0.29, 0.18, 0.73, 0.37),
            "pocket-back": (0.071, 0.062, 0.052, 0.33, 0.56),
            "pocket-carriers": (0.56, 0.56, 0.49, 0.0, 0.58),
            "pocket-tyres": (0.79, 0.78, 0.68, 0.0, 0.32),
            "pocket-fasteners": (0.40, 0.43, 0.45, 0.88, 0.31),
            "pocket-floor-track": (0.60, 0.62, 0.64, 0.90, 0.33),
            "pocket-head-track": (0.60, 0.62, 0.64, 0.90, 0.33),
        }
        for key, values in finishes.items():
            mat = bpy.data.materials.new(key.removeprefix("pocket-").title())
            mat.use_nodes = True
            shader = mat.node_tree.nodes["Principled BSDF"]
            shader.inputs["Base Color"].default_value = (*values[:3], 1)
            shader.inputs["Metallic"].default_value = values[3]
            shader.inputs["Roughness"].default_value = values[4]
            mat.diffuse_color = (*values[:3], 1)
            for part in entries[key]:
                part["cabinetPart"] = key
                part.data.materials.append(mat)
                for hidden in part.children:
                    hidden.data.materials.append(mat)
        bpy.context.preferences.filepaths.save_version = 0
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
    if args.bit_library:
        from mathutils import Vector

        bpy.ops.wm.read_factory_settings(use_empty=True)
        build_bit_rack()
        scene = bpy.context.scene
        scene.name = "Wera · 25 mm driver bits"
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.length_unit = "MILLIMETERS"
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    space = area.spaces.active
                    space.clip_start = 0.0001
                    space.region_3d.view_distance = 0.215
                    space.region_3d.view_location = (0, 0, 0.008)
                    space.region_3d.view_rotation = Vector((-0.9, 0.32, 0.44)).to_track_quat("Z", "Y")
                    space.shading.color_type = "MATERIAL"
                    space.overlay.show_overlays = False
        bpy.context.preferences.filepaths.save_version = 0
        args.bit_library.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.bit_library.resolve()), compress=True)


if __name__ == "__main__":
    main()
