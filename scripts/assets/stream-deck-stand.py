import math
from pathlib import Path

import bmesh
import bpy

PRODUCT = (
    Path(__file__).resolve().parents[2]
    / ".references/04-桌面设备/键鼠与控制台/Elgato Stream Deck Neo"
)


def arc(x, y, r, start, end, count=12):
    return [
        (x + r * math.cos(angle), y + r * math.sin(angle))
        for angle in (
            math.radians(start + (end - start) * i / count) for i in range(count + 1)
        )
    ]


def build(device, back, panel, rounded_rectangle):
    from blender_parts import barrel, bevel, block
    from product_solids import block as rounded_block, mesh, subtract

    shell = device.surfaces["shell"][0]

    def pocket(name, transform, x, s, width, height, radius, near, far):
        ring = rounded_rectangle(width, height, radius)
        n = len(ring)
        points = [transform(x + u, s + v, d) for d in [near, far] for u, v in ring]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
        tool = mesh(name, points, faces, shell)
        bm = bmesh.new()
        bm.from_mesh(tool.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(tool.data)
        bm.free()
        return tool

    recess = pocket("Folded support pocket", panel, 0, -12, 34.8, 37.8, 2.6, -18, -9.8)
    subtract(back, [recess])
    hinge_pockets = [
        pocket("Fork bearing pocket", panel, x, 11.8, 7.8, 9.8, 1.45, -18, -6.9)
        for x in [-12.35, 12.35]
    ]
    channel = pocket("Cable guide", panel, 0, 23.5, 6.4, 27.6, 3.1, -18, -7.3)
    subtract(back, [*hinge_pockets, channel])
    bevel(back, 0.23, 2)

    def horizontal(x, z, height):
        return x, height, z - 20.5

    pad = device.ply(
        "Grey non-slip silicone underside",
        "rubber",
        [(0, 81.8, 60.7, 8.4), (0.32, 82.7, 61.6, 8.8), (0.9, 83, 61.9, 9)],
        transform=horizontal,
    )
    base = device.ply(
        "Folding base with two recessed angle stops",
        "shell",
        [
            (0.8, 85.8, 64.6, 9),
            (1.35, 86.5, 65.3, 9.1),
            (3.7, 86.5, 65.3, 9.1),
            (4.65, 84.8, 63.6, 8.7),
        ],
        transform=horizontal,
    )
    subtract(
        base,
        [
            rounded_block("Angle stop tool", 0, 4.5, z, 33.7, 3.8, 5.25, 1.6, shell)
            for z in [-43.8, -29.8]
        ],
    )
    bevel(base, 0.22, 3)

    toe = (2.73, -43.8)
    pivot = panel(0, 11.8, -8.6)[1:]
    rise, run = pivot[0] - toe[0], pivot[1] - toe[1]
    length = math.hypot(rise, run)

    def frame(x, s, depth):
        return (
            x,
            toe[0] + (rise * s + run * depth) / length,
            toe[1] + (run * s - rise * depth) / length,
        )

    contour = [(-15.5, 0), (-3.3, 0), (-3.3, 1.8)]
    contour += arc(0, 1.8, 3.3, 180, 0)[1:]
    contour += [(3.3, 0), (15.5, 0)]
    contour += arc(15.5, 0.7, 0.7, -90, 0, 4)[1:]
    contour += arc(12.35, length, 3.4, 0, 180)
    contour += [(8.95, 18.4)]
    contour += arc(0, 18.4, 8.95, 0, -180)[1:]
    contour += arc(-12.35, length, 3.4, 0, 180)
    contour += arc(-15.5, 0.7, 0.7, 180, 270, 4)[:-1]
    yoke = device.loft(
        "Single forked support · open centre and split toe",
        "shell",
        [[frame(x, s, depth) for x, s in contour] for depth in [-1.25, 1.25]],
    )
    subtract(
        yoke,
        [
            pocket("Moulded fork slot", frame, x, length - 4.4, 1.8, 7.5, 0.88, -2, 2)
            for x in [-12.35, 12.35]
        ],
    )
    bevel(yoke, 0.48, 3)
    for x in [-12.35, 12.35]:
        boss = barrel(
            "Rounded upper fork bearing",
            frame(x - 3.4, length, 0),
            frame(x + 3.4, length, 0),
            2.7,
            32,
        )
        device.add(bevel(boss, 0.24, 2), "shell")

    def axle(name, x0, x1, position, radius, material):
        y, z = position
        return device.add(
            bevel(barrel(name, (x0, y, z), (x1, y, z), radius, 36), 0.16, 2), material
        )

    axle("Support transverse pivot", -15.85, 15.85, pivot, 1.2, "seam")
    for side in [-1, 1]:
        device.ply(
            "Upper hinge socket",
            "shell",
            [(0, 4.15, 8.6, 1.4), (2.65, 4.8, 8.2, 1.6), (8.0, 5, 7.5, 1.8)],
            transform=lambda x, s, t: frame(side * 6.45 + x, length + s, 1.7 - t),
        )
        axle(
            "Upper hinge knuckle",
            side * 6.45 - 2.2,
            side * 6.45 + 2.2,
            pivot,
            2.7,
            "shell",
        )

    heel = (6.7, 4.95)
    axle("Front hinge pin", -36, 36, heel, 1.9, "seam")
    for x0, x1 in [(-35.9, -20.4), (20.4, 35.9)]:
        axle("Base hinge knuckle", x0, x1, heel, 3.2, "shell")
        device.add(
            block(
                "Base hinge root", (x1 - x0, 4.6, 6.6), ((x0 + x1) / 2, 4.5, 5.75), 0.85
            ),
            "shell",
        )
    axle("Body hinge knuckle", -19.9, 19.9, heel, 3.2, "shell")
    underside_print(pad)


def underside_print(pad):
    ink = pad.data.materials[0].copy()
    ink.name = "Stream Deck Neo · factory identification on silicone"
    artwork = bpy.data.images.load(str(PRODUCT / "模型依赖/stream-deck-underside.png"))
    artwork.pack()
    nodes, links = ink.node_tree.nodes, ink.node_tree.links
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = artwork
    mix = nodes.new("ShaderNodeMixRGB")
    mix.inputs[1].default_value = ink.diffuse_color
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(texture.outputs["Color"], mix.inputs[2])
    links.new(mix.outputs[0], nodes.get("Principled BSDF").inputs["Base Color"])
    pad.data.materials.append(ink)
    uv = pad.data.uv_layers.new(name="Printed contact face")
    (bottom,) = [f for f in pad.data.polygons if f.normal.z < -0.99]
    bottom.material_index = 1
    for i in bottom.loop_indices:
        v = pad.data.vertices[pad.data.loops[i].vertex_index].co
        uv.data[i].uv = (0.5 - v.x / 0.0818, 0.5 + (v.y - 0.0205) / 0.0607)


def fit(scene):
    source = PRODUCT / "Blender/stream-deck-neo.blend"
    mount = scene.objects["Stream Deck Neo · capture and editing controls"]
    current = mount.instance_collection
    if (
        current
        and current.library
        and Path(bpy.path.abspath(current.library.filepath)).samefile(source)
    ):
        return
    old = list(mount.children_recursive)
    if current or not any(o.name.startswith("stream-deck-neo") for o in old):
        raise ValueError("Unexpected Stream Deck assembly")
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (
        available,
        loaded,
    ):
        if "stream-deck-neo" not in available.collections:
            raise ValueError("Stream Deck collection missing")
        loaded.collections = ["stream-deck-neo"]
    (collection,) = loaded.collections
    if not any(
        o.name.startswith("Single forked support") for o in collection.all_objects
    ):
        raise ValueError("Missing folding support")
    mount.instance_type = "COLLECTION"
    mount.instance_collection = collection
    for obj in reversed(old):
        bpy.data.objects.remove(obj, do_unlink=True)
