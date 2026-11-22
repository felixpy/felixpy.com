import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from io_scene_gltf2.io.exp import meshopt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from blender_parts import barrel, bevel, block, xyz

ROOT = HERE.parents[1]
STUDY = ROOT / ".review/atelier/portrait-frame"
HALF_WIDTH, HALF_HEIGHT = 53.7, 79.1
PITCH = math.radians(34)
HINGE = Vector((12.4, 12.4, -5.8))
AXIS = Vector((1, -1, 0)).normalized()


def finish(name, color, roughness, metal=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    mat.diffuse_color = (*color, 1)
    bsdf.inputs["Base Color"].default_value = mat.diffuse_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metal
    return mat


def attach(obj, mat):
    obj.data.materials.append(mat)
    return obj


def solid(name, coords, faces, mat, radius=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(a) for a in coords], [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return bevel(attach(obj, mat), radius, 3)


def section(name, lower, upper, mat, radius):
    count = len(lower)
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    faces.extend(
        (i, (i + 1) % count, count + (i + 1) % count, count + i) for i in range(count)
    )
    return solid(name, [*lower, *upper], faces, mat, radius)


def rails(gold):
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for side, name in enumerate(
        ("Bottom feed rail", "Right channel", "Top stop", "Left channel")
    ):
        back_lip = 0.75 if side == 0 else 3.4
        rear = -0.13 if side == 0 else -4
        profile = [
            (0, rear),
            (0, 3.2),
            (0.14, 3.63),
            (0.43, 3.88),
            (1.21, 4.04),
            (2.12, 3.96),
            (2.95, 3.61),
            (3.78, 2.97),
            (4.05, 2.54),
            (4.05, 2.10),
            (0.57, 2.10),
            (0.57, rear + 0.56),
            (back_lip, rear + 0.56),
            (back_lip, rear),
        ]

        def end(signs, other):
            return [
                (
                    signs[0] * (HALF_WIDTH - inset) + (other[0] - signs[0]) * 0.018,
                    signs[1] * (HALF_HEIGHT - inset) + (other[1] - signs[1]) * 0.018,
                    z,
                )
                for inset, z in profile
            ]

        a, b = corners[side], corners[(side + 1) % 4]
        section(name, end(a, b), end(b, a), gold, 0.055)


def plate(name, outline, front, back, mat, radius, transform=None):
    def point(x, y, z):
        return transform((x, y, z)) if transform else (x, y, z)

    return section(
        name,
        [point(x, y, front) for x, y in outline],
        [point(x, y, back) for x, y in outline],
        mat,
        radius,
    )


def opened(co, angle=PITCH):
    v = Vector(co) - HINGE
    return (
        HINGE
        + v * math.cos(angle)
        + AXIS.cross(v) * math.sin(angle)
        + AXIS * AXIS.dot(v) * (1 - math.cos(angle))
    )


def panel(name, width, height, depth, thickness, mat, radius):
    return attach(block(name, (width, height, thickness), (0, 0, depth), radius), mat)


def flock(name):
    mat = finish(name, (0.0035, 0.0032, 0.004), 0.94)
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    bsdf.inputs["Sheen Weight"].default_value = 0.18
    bsdf.inputs["Sheen Tint"].default_value = (0.2, 0.18, 0.20, 1)
    bsdf.inputs["Sheen Roughness"].default_value = 0.82
    n = 96
    seeds = np.random.default_rng(3802).normal(0, 1, (n, n))
    nap = sum(np.roll(seeds, (j, j // 3), (0, 1)) for j in range(5)) / 5
    dx = np.roll(nap, -1, 1) - np.roll(nap, 1, 1)
    dy = np.roll(nap, -1, 0) - np.roll(nap, 1, 0)
    length = np.sqrt(1 + dx**2 + dy**2)
    pixels = np.stack(
        (
            0.5 - dx / (2 * length),
            0.5 - dy / (2 * length),
            0.5 + 0.5 / length,
            np.ones_like(nap),
        ),
        axis=-1,
    )
    grain = bpy.data.images.new("Velvet nap", n, n, alpha=False)
    grain.colorspace_settings.name = "Non-Color"
    grain.pixels.foreach_set(pixels.astype("float32").ravel())
    grain.filepath_raw = str(STUDY / "velvet-nap.png")
    grain.file_format = "PNG"
    grain.save()
    grain.pack()
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = grain
    coords = tree.nodes.new("ShaderNodeUVMap")
    coords.uv_map = "Surface"
    tree.links.new(coords.outputs["UV"], texture.inputs["Vector"])
    bump = tree.nodes.new("ShaderNodeNormalMap")
    bump.uv_map = "Surface"
    bump.inputs["Strength"].default_value = 0.19
    tree.links.new(texture.outputs["Color"], bump.inputs["Color"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def control(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.009
    return obj


def driven(curve, controller, key, expression):
    driver = curve.driver
    variable = driver.variables.new()
    variable.name = "setting"
    variable.targets[0].id = controller
    variable.targets[0].data_path = f'["{key}"]'
    driver.expression = expression


def easel(velvet, core, studs):
    back = control("Removable back · slide towards lower rail")
    back["slide_mm"] = 0.0
    back.id_properties_ui("slide_mm").update(
        min=0, max=165, description="Withdrawal through open bottom channel (mm)"
    )
    driven(back.driver_add("location", 2), back, "slide_mm", "-setting / 1000")
    for obj in [
        panel("Slide-in fibreboard", 104.8, 155.3, -1.62, 2.85, core, 0.23),
        panel(
            "Velvet backing with rolled edge", 104.95, 155.45, -3.18, 0.46, velvet, 0.16
        ),
    ]:
        obj.parent = back
    pivot = control("Diagonal easel hinge")
    pivot.parent = back
    pivot.location = xyz(HINGE)
    pivot.rotation_euler = xyz(AXIS).to_track_quat("Z", "Y").to_euler()
    motion = control("Two-way easel · opening")
    motion.parent = pivot
    motion["opening_degrees"] = 34.0
    motion.id_properties_ui("opening_degrees").update(
        min=0, max=60, description="Fold flat or open the hinged easel"
    )
    driven(
        motion.driver_add("rotation_euler", 2),
        motion,
        "opening_degrees",
        "radians(setting - 34)",
    )
    bpy.context.view_layer.update()
    original = set(bpy.context.scene.objects)
    rest = math.atan(math.tan(PITCH / 2) / math.sqrt(2))
    reach = HALF_HEIGHT - (7 - 4) * math.tan(rest)
    side = HALF_WIDTH - (7 - 4) * math.tan(rest)
    shape = [
        (0, 21),
        (3.8, 21),
        (20, 4.8),
        (20, 0),
        (-26, -reach),
        (-side + 1.2, -reach),
        (-side, -reach + 1.3),
        (-side, -39),
    ]
    center = Vector(
        (sum(x for x, y in shape) / len(shape), sum(y for x, y in shape) / len(shape))
    )
    inset = [tuple(center + (Vector(pt) - center) * 0.991) for pt in shape]
    plate("Die-cut easel stiffener", inset, -5.01, -6.62, core, 0.12, opened)[
        "productEnclosed"
    ] = True
    plate("Black velvet easel facing", shape, -6.62, -7, velvet, 0.16, opened)
    plate("Black velvet easel lining", shape, -4.64, -5.02, velvet, 0.16, opened)
    wrap = [
        [opened((x, y, z)) for x, y in edge]
        for edge, z in ((shape, -6.72), (shape, -4.90), (inset, -4.90), (inset, -6.72))
    ]
    count = len(shape)
    faces = [
        (
            ring * count + i,
            ring * count + (i + 1) % count,
            ((ring + 1) % 4) * count + (i + 1) % count,
            ((ring + 1) % 4) * count + i,
        )
        for ring in range(4)
        for i in range(count)
    ]
    solid(
        "Velvet returned around easel edge",
        [p for row in wrap for p in row],
        faces,
        velvet,
        0.035,
    )

    def hinge_edge(cross, z):
        mid = HINGE + Vector((cross, cross, 0)).normalized() * abs(cross)
        return [
            tuple(mid + AXIS * t + Vector((0, 0, z - HINGE.z))) for t in (-12.5, 12.5)
        ]

    strips = [
        hinge_edge(9, -3.45),
        hinge_edge(0.5, -3.46),
        hinge_edge(-0.5, -3.63),
        [opened(p) for p in hinge_edge(-3, -4.60)],
        [opened(p) for p in hinge_edge(-10, -4.60)],
    ]
    top = [point for pair in strips for point in pair]
    bottom = [(x, y, z - 0.33) for x, y, z in top]
    outline = list(range(0, len(top), 2)) + list(reversed(range(1, len(top), 2)))
    n = len(top)
    faces = [(i, i + 1, i + 3, i + 2) for i in range(0, n - 2, 2)]
    faces += [tuple(n + j for j in reversed(face)) for face in list(faces)]
    faces += [(i, j, j + n, i + n) for i, j in zip(outline, outline[1:] + outline[:1])]
    hinge = solid("Flexible cloth hinge", top + bottom, faces, velvet, 0.045)
    hinge.parent = back
    hinge.shape_key_add(name="Open 34 degrees")
    for degrees in (0, 17, 51, 60):
        target = hinge.shape_key_add(name=f"Fold {degrees} degrees")
        for j in range(6, 10):
            q = opened(
                hinge_edge(-3 if j < 8 else -10, -4.60)[j % 2], math.radians(degrees)
            )
            target.data[j].co = xyz(q)
            target.data[j + n].co = xyz((q.x, q.y, q.z - 0.33))
        expr = {
            0: "max(0,(17-setting)/17)",
            17: "max(0,1-abs(setting-17)/17)",
            51: "max(0,min((setting-34)/17,(60-setting)/9))",
            60: "max(0,(setting-51)/9)",
        }[degrees]
        driven(target.driver_add("value"), motion, "opening_degrees", expr)
    for i, (x, y) in enumerate(((-1.1, 10.7), (10.7, -1.1)), 1):
        shaft = attach(
            barrel(
                f"Easel rivet {i} · shank",
                opened((x, y, -7)),
                opened((x, y, -4.47)),
                1.13,
            ),
            studs,
        )
        shaft["productEnclosed"] = True
        attach(
            bevel(
                barrel(
                    f"Easel rivet {i} · domed head",
                    opened((x, y, -6.98)),
                    opened((x, y, -7.34)),
                    2.62,
                    48,
                    2.49,
                ),
                0.12,
            ),
            studs,
        )
    for obj in set(bpy.context.scene.objects) - original - {hinge}:
        obj.parent = motion
        obj.matrix_parent_inverse = motion.matrix_world.inverted()


def photograph(stock):
    image = bpy.data.images.load(
        str(ROOT / "public/media/photography/desk-portrait.webp")
    )
    image.pack()
    width = 95
    height = width * image.size[1] / image.size[0]
    ink = finish("Matte photographic print", (1, 1, 1), 0.96)
    tree = ink.node_tree
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    tree.links.new(
        texture.outputs["Color"], tree.nodes.get("Principled BSDF").inputs["Base Color"]
    )
    signs = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    verts = [
        xyz((sx * w / 2, sy * h / 2, z))
        for w, h, z in ((101.6, 152.4, 0.15), (101.6, 152.4, 0.4), (width, height, 0.4))
        for sx, sy in signs
    ]
    faces = [(3, 2, 1, 0)]
    faces.extend(
        (base + i, base + (i + 1) % 4, base + 4 + (i + 1) % 4, base + 4 + i)
        for base in (0, 4)
        for i in range(4)
    )
    faces.append((8, 9, 10, 11))
    data = bpy.data.meshes.new("Single continuous photo sheet")
    data.from_pydata(verts, [], faces)
    data.update()
    uv = data.uv_layers.new(name="Surface")
    for index, v in zip(
        data.polygons[-1].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))
    ):
        uv.data[index].uv = v
    obj = bpy.data.objects.new("4 × 6 photo · original emulsion and paper border", data)
    bpy.context.collection.objects.link(obj)
    attach(obj, stock)
    attach(obj, ink)
    data.polygons[-1].material_index = 1
    return ink, texture


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    STUDY.mkdir(exist_ok=True, parents=True)
    gold = finish("Fine gold plate", (0.95, 0.73, 0.40), 0.21, 0.95)
    core = finish("Pressed wood fibre", (0.129, 0.085, 0.052), 0.89)
    stock = finish("Photographic paper base", (0.81, 0.78, 0.72), 0.88)
    studs = finish("Oxidised rivet heads", (0.13, 0.112, 0.096), 0.42, 0.74)
    velvet = flock("Graphite velvet pile")
    rails(gold)
    panel("Acid-free pressure liner", 101.8, 152.7, -0.037, 0.35, stock, 0.04)[
        "productEnclosed"
    ] = True
    ink, texture = photograph(stock)
    glass = finish("Cut cover glass", (0.97, 0.985, 0.983), 0.095)
    bsdf = glass.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Transmission Weight"].default_value = 1
    bsdf.inputs["IOR"].default_value = 1.52
    panel("Ground edge glazing", 102.4, 153.2, 1.28, 1.55, glass, 0.17)
    easel(velvet, core, studs)
    scene = bpy.context.scene
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        uv = obj.data.uv_layers.active
        if obj.data.materials[0] == velvet:
            uv = uv or obj.data.uv_layers.new(name="Surface")
            for face in obj.data.polygons:
                axis = max(range(3), key=lambda k: abs(face.normal[k]))
                for i in face.loop_indices:
                    x, y, z = obj.data.vertices[obj.data.loops[i].vertex_index].co
                    a, b = ((y, z), (x, z), (x, y))[axis]
                    uv.data[i].uv = (a / 0.009, b / 0.009)
        if uv:
            uv.name = "Surface"
    scene.unit_settings.system = "METRIC"
    scene["reference"] = (
        "https://usa.addisonross.com/products/fine-gloss-gold-plated-frame"
    )
    scene["paperFormat"] = (
        "4 × 6 in. Manufacturer gallery, including its shared silver-back detail."
    )
    scene["support"] = (
        "34 degree diagonal fold. Hidden lamination, fastener depth and metal section inferred from the external views."
    )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(STUDY / "fine-gold-4x6.blend"), compress=True
    )
    ink.node_tree.nodes.remove(texture)
    bsdf.inputs["Transmission Weight"].default_value = 0
    bsdf.inputs["Alpha"].default_value = 0.035
    for obj in list(scene.objects):
        if obj.get("productEnclosed"):
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    for obj in list(scene.objects):
        if obj.type == "MESH" and obj.parent:
            matrix = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix
    for obj in list(scene.objects):
        if obj.type == "EMPTY":
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = scene.objects["Bottom feed rail"]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    bpy.context.object.name = "Fine gold portrait frame"
    bpy.context.object.data.name = "Fine gold portrait frame"
    target = ROOT / "public/media/models/desk-portrait-frame.glb"
    old = meshopt.EXP_FILTER_BITS
    try:
        meshopt.EXP_FILTER_BITS = 21
        bpy.ops.export_scene.gltf(
            filepath=str(target),
            export_format="GLB",
            export_animations=False,
            export_meshopt_compression_enable=True,
            export_meshopt_extension="EXT_meshopt_compression",
        )
    finally:
        meshopt.EXP_FILTER_BITS = old
    subprocess.run(
        ["node", str(HERE / "pack-product-geometry.mjs"), str(target)], check=True
    )


if __name__ == "__main__":
    main()
