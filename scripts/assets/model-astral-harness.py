import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_parts import barrel, block, pipe, sample_bezier
from astral_power import archive_components, project, source
from product_workshop import Product, xyz


def path_frames():
    handles = [
        ((-85, 26, 54), (-85, 30.5, 54), (-85, 34, 54)),
        ((-85, 36.5, 54), (-85, 39.5, 54), (-85, 50.8, 54)),
        ((-76.7, 59.7, 52.9), (-65, 59.5, 51), (-49.8, 59.2, 48.5)),
        ((-30, 48.4, 42.7), (-12, 45.6, 42), (-3, 44.2, 41.65)),
        ((11, 43.2, 42.2), (20, 44.0, 45.2), (28.1, 44.7, 47.9)),
        ((40, 44.5, 55.5), (46.5, 48.3, 68.2), (51.7, 51.3, 78.4)),
        ((51.8, 55, 82.2), (55.1, 64.1, 91), (58.4, 73.2, 99.8)),
        ((64.4, 89.8, 109.5), (74.1, 94.5, 115), (77, 96.1, 116.6)),
        ((81.5, 97, 116.6), (87, 97, 116.6), (97.5, 97, 116.6)),
        ((100.2, 82.8, 115.6), (100.5, 65.5, 114.3), (100.8, 48.2, 113)),
        ((100.5, 20, 113), (100.5, 5, 113), (100.5, -34, 113)),
        ((101.5, -123, 105), (101.5, -155, 99), (101.5, -171, 96)),
        ((102, -181, 88), (99, -191, 85.5), (95.4, -203, 82.5)),
        ((85.5, -200, 90.5), (73, -200, 92), (60.5, -200, 93.5)),
        ((38, -200, 94), (38, -200, 80), (38, -200, 70)),
        ((38, -200, 49), (38, -200, 39), (38, -200, 34)),
    ]
    guide = pipe(
        "Installed cable centreline through the tray to Thor socket 2",
        [center for _, center, _ in handles],
        0,
    )
    for node, (left, _, right) in zip(guide.data.splines[0].bezier_points, handles):
        node.handle_left_type = node.handle_right_type = "FREE"
        node.handle_left = Vector(xyz(left)) * 0.001
        node.handle_right = Vector(xyz(right)) * 0.001
    points = [Vector((v.x, v.z, -v.y)) * 1000 for v in sample_bezier(guide, 0.06)]
    guide.hide_render = True
    guide.hide_set(True)
    lengths = [0]
    tangents = []
    axes = []
    for i, p in enumerate(points):
        if i:
            lengths.append(lengths[-1] + (p - points[i - 1]).length)
        before = (p - points[max(i - 1, 0)]).normalized()
        after = (points[min(i + 1, len(points) - 1)] - p).normalized()
        tangent = (before + after).normalized()
        axes.append(
            tangents[-1].rotation_difference(tangent) @ axes[-1]
            if i
            else Vector((0, 0, 1))
        )
        tangents.append(tangent)
    start = 0
    for anchor, wanted in [
        ((-12, 45.6, 42), (0, 0, 1)),
        ((20, 44, 45.2), (0, 0, 1)),
        ((87, 97, 116.6), (0, 0, 1)),
        ((101.5, -155, 99), (0, 0, 1)),
        ((38, -200, 80), (0, 1, 0)),
        ((38, -200, 39), (0, 1, 0)),
    ]:
        end = min(range(len(points)), key=lambda i: (points[i] - Vector(anchor)).length)
        desired = Vector(wanted)
        angle = math.atan2(
            axes[end].cross(desired).dot(tangents[end]), axes[end].dot(desired)
        )
        for i in range(start + 1, len(points)):
            t = min(1, (lengths[i] - lengths[start]) / (lengths[end] - lengths[start]))
            axes[i] = Quaternion(tangents[i], angle * t * t * (3 - 2 * t)) @ axes[i]
        start = end
    return [
        (p, side.cross(t).normalized(), t, side, length)
        for p, t, side, length in zip(points, tangents, axes, lengths)
    ]


def wire(part, frames, name, finish, offset, span, radius):
    sides = 14 if radius > 1 else 10
    verts = []
    faces = []
    for i, (center, outward, tangent, across, length) in enumerate(frames):
        for j in range(sides):
            angle = math.tau * j / sides
            p = (
                center
                + outward * (offset + radius * math.cos(angle))
                + across * (span + radius * math.sin(angle))
            )
            verts.append(tuple(p / 1000))
        if i:
            k = (i - 1) * sides
            for j in range(sides):
                a, b = k + j, k + (j + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    obj = part.surface(name, finish, verts, faces, True)
    uv = obj.data.uv_layers.active
    for face in obj.data.polygons:
        wrap = face.index % sides == sides - 1
        for k in face.loop_indices:
            row, col = divmod(obj.data.loops[k].vertex_index, sides)
            uv.uv[k].vector = (
                1.0 if wrap and col == 0 else col / sides,
                frames[row][4] / (math.tau * radius),
            )


def comb(part, frame, conductors):
    center, outward, tangent, across, _ = frame
    piece = block("Low-profile closed cable comb", (7.7, 3.5, 20.3), (0, 0, 0), 0.76)
    bpy.context.view_layer.objects.active = piece
    for mod in list(piece.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for dx, dz, radius in conductors:
        punch = barrel(
            "Individual throat", (dx, -3, dz), (dx, 3, dz), radius + 0.12, 16
        )
        mod = piece.modifiers.new("Wire passage", "BOOLEAN")
        mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", punch
        bpy.context.view_layer.objects.active = piece
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(punch, do_unlink=True)
    orientation = (
        Matrix([xyz(outward), xyz(-across), xyz(-tangent)]).transposed().to_4x4()
    )
    orientation.translation = Vector(xyz(center)) * 0.001
    piece.matrix_world = orientation
    part.parts["graphite"].append(piece)


def build(save=True, destination=None):
    frames = path_frames()
    part = Product("astral-harness")
    conductors = []
    for row in range(2):
        for col in range(6):
            offset, span, radius = (row - 0.5) * 3.04, (col - 2.5) * 3.12, 1.35
            wire(
                part,
                frames,
                "16 AWG braided power conductor",
                "satin" if col in (1, 4) else "black",
                offset,
                span,
                radius,
            )
            conductors.append((offset, span, radius))
    total_length = frames[-1][4]
    tray_length = (
        min(frames, key=lambda f: (f[0] - Vector((87, 97, 116.6))).length)[4] - 3
    )
    print(
        f"Cable sleeve centreline {total_length:.1f} mm, glass compartment {tray_length:.1f} mm"
    )
    for distance in (93, 207, tray_length + 96, total_length - 175, total_length - 49):
        comb(part, min(frames, key=lambda f: abs(f[4] - distance)), conductors)

    def moulding(name, size, center, bevel):
        part.parts["graphite"].append(block(name, size, center, bevel))

    outline = [
        (-65.08, 13.6),
        (-82.9, 13.6),
        (-89.5, 19.3),
        (-89.5, 30.5),
        (-80.5, 30.5),
        (-80.5, 24.9),
        (-76.8, 21.1),
        (-65.08, 21.1),
    ]
    n = len(outline)
    body = part.surface(
        "Overmoulded ninety degree GPU plug",
        "graphite",
        [(x / 1000, y / 1000, z) for z in (0.04345, 0.06455) for x, y in outline],
        [tuple(range(n)), tuple(reversed(range(n, n * 2)))]
        + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)],
    )
    bevel = body.modifiers.new("Radiused overmould", "BEVEL")
    bevel.width, bevel.segments, bevel.harden_normals = 0.00085, 4, True
    body.modifiers.new("Moulded planar faces", "WEIGHTED_NORMAL")
    for row in range(2):
        for col in range(6):
            moulding(
                "Polarised power plug terminal",
                (6.7, 2.30, 2.30),
                (-61.8, 16.05 + row * 3, 46.5 + col * 3),
                0.18,
            )
    moulding("Recessed sideband tongue", (5.9, 1.8, 10.1), (-62.3, 12.65, 54), 0.24)
    moulding(
        "Latch spring and release tab", (11.4, 0.88, 4.0), (-69.3, 22.05, 54), 0.25
    )
    moulding("Locking hook shoulder", (1.55, 1.15, 4.0), (-63.7, 21.71, 54), 0.24)
    for y in (23.4, 25.4, 27.4):
        moulding("Crowned grip rib", (0.8, 0.86, 17), (-89.38, y, 54), 0.30)
    moulding("PSU straight 16-pin plug", (9.3, 20.3, 15.4), (38, -200, 31.5), 0.64)
    moulding("PSU latch arm", (0.78, 4.1, 10), (42.9, -200, 27.8), 0.25)
    moulding("PSU-side keyed nose", (6.8, 17.9, 4.8), (38, -200, 23.0), 0.32)
    if save:
        from product_workshop import finishes

        finishes.update(
            black=("424449", 0.72, 0.04),
            satin=("62646a", 0.74, 0.04),
            graphite=("33353a", 0.44, 0.12),
        )
        archive_components(part)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(
            filepath=str(source / "astral-power.blend"), compress=True
        )
    part.export(destination or project / "public/media/models")


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if "--fit-preview" in sys.argv:
        build(save=False, destination=project / ".review/gpu-route/candidate")
    else:
        build()
