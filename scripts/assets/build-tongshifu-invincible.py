import argparse
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def material(name, metallic, roughness, color, detail):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    paint = nodes.new("ShaderNodeTexImage")
    paint.image = color
    paint.extension = "REPEAT"
    engravings = nodes.new("ShaderNodeTexImage")
    engravings.image = detail
    engravings.extension = "REPEAT"
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.30
    links.new(paint.outputs["Color"], shader.inputs["Base Color"])
    links.new(engravings.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return mat


def finish(index, name, data, materials):
    verts = data["v" + str(index)]
    faces = data["f" + str(index)]
    coords = data["uv" + str(index)]
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(verts))
    mesh.vertices.foreach_set("co", verts.ravel())
    mesh.loops.add(3 * len(faces))
    mesh.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set(
        "loop_start", np.arange(0, 3 * len(faces), 3, dtype=np.int32)
    )
    mesh.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    mesh.update(calc_edges=True)
    uv = mesh.uv_layers.new(name="Registered four-view paint")
    uv.data.foreach_set("uv", coords.ravel())
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    indices = data["material" + str(index)]
    used = np.unique(indices)
    for i in used:
        mesh.materials.append(materials[i])
    mesh.polygons.foreach_set(
        "material_index", np.searchsorted(used, indices).astype(np.int32)
    )
    mesh.validate(clean_customdata=False)
    obj.vertex_groups.new(name=name).add(list(range(len(verts))), 1, "REPLACE")
    modifier = obj.modifiers.new("Silhouette-preserving cast tessellation", "DECIMATE")
    modifier.ratio = (
        0.18 if name.startswith("01 ·") else 0.62 if len(faces) > 12000 else 0.90
    )
    modifier.delimit = {"UV"}
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0

    def load(file):
        im = bpy.data.images.load(str(out / file))
        im.name = "Invincible · " + file
        if "detail" in file:
            im.colorspace_settings.name = "Non-Color"
        im.pack()
        return im

    def textured(label, metal, rough, key):
        return material(
            "Invincible · " + label,
            metal,
            rough,
            load(key + "-paint.jpg"),
            load(key + "-detail.jpg"),
        )

    def lacquer(label, srgb, metal, rough):
        m = bpy.data.materials.new("Invincible · " + label)
        m.use_nodes = True
        shader = m.node_tree.nodes.get("Principled BSDF")
        c = np.array(srgb) / 255
        c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        shader.inputs["Base Color"].default_value = (*c, 1)
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = rough
        return m

    materials = [
        textured("patinated mountain faces", 0.17, 0.68, "rock"),
        textured("hammered armour and painted cloth", 0.23, 0.54, "armour"),
        textured("hand-painted muzzle and combed gilt hair", 0.06, 0.57, "head"),
        textured("plume, chased ferrules and crown enamels", 0.32, 0.53, "cast"),
        lacquer("wind-folded cinnabar cape", (174, 24, 45), 0.045, 0.38),
        lacquer("satin gilded brass and knuckles", (183, 147, 91), 0.45, 0.38),
        lacquer("warm patina on the top and underside", (126, 108, 75), 0.18, 0.69),
        lacquer("sculpted ear enamel", (235, 174, 129), 0.03, 0.50),
        lacquer("blue enamel", (44, 77, 117), 0.05, 0.54),
        lacquer("burnt orange tunic", (187, 77, 36), 0.05, 0.49),
        lacquer("bronze engraved waist mask", (189, 145, 74), 0.45, 0.48),
        lacquer("red silk enamel of waist and throat", (191, 33, 44), 0.065, 0.45),
        lacquer("oxblood gaiter and leather boot enamel", (107, 41, 28), 0.08, 0.46),
        lacquer("flame orange crown enamel", (202, 65, 30), 0.14, 0.36),
        lacquer("engraved border", (181, 151, 101), 0.53, 0.37),
        lacquer("silk underlayer", (147, 55, 26), 0.07, 0.45),
        textured("cloisonné crown with gilt bezels", 0.28, 0.42, "crown"),
        textured("vermilion sash and gilt knuckles", 0.15, 0.46, "handwork"),
        textured("three-way chased lattice", 0.41, 0.48, "tooling"),
        lacquer("gathered dark brick breeches", (78, 28, 22), 0.055, 0.57),
        textured("cast guardian buckle", 0.43, 0.43, "guardian"),
        lacquer("antique gold of the incised plumes", (177, 124, 58), 0.46, 0.41),
        textured("scroll-chased staff end sleeves", 0.44, 0.42, "ferrule"),
        textured("repoussé breastplate and flared lappets", 0.46, 0.46, "repousse"),
        lacquer("indigo lacquer on boot bindings", (27, 44, 64), 0.035, 0.54),
        lacquer("ochre leather under the boot bindings", (154, 66, 32), 0.035, 0.49),
        textured("oxblood boot hide and indigo ankle ties", 0.057, 0.44, "boot-hide"),
    ]
    with np.load(out / "parts.npz") as data:
        parts = [
            finish(
                i,
                str(name),
                data,
                materials,
            )
            for i, name in enumerate(data["names"])
        ]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    target = parts[0]
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    target.name = "Sun Wukong · The Great Victory"
    target.data.name = "Great Sage · round casting"
    target.data.validate(verbose=True, clean_customdata=False)
    target.data.update(calc_edges=True)
    if target.data.validate(clean_customdata=False) or not target.data.uv_layers.active:
        raise ValueError("The final casting has invalid geometry or missing UVs")
    target["castingEdition"] = "Tongshifu · Invincible Wukong"
    target["referenceTitle"] = "悟空之战无不胜"
    target["dimensionsMm"] = [145, 110, 265]
    target["netMassKg"] = 1.2
    target["supportPlaneMetres"] = 0.0
    bpy.context.scene.unit_settings.system = "METRIC"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                v = area.spaces.active.region_3d
                v.view_location = (0, 0, 0.1325)
                v.view_distance = 0.45
                v.view_rotation = Vector((-0.12, 1, -0.06)).to_track_quat("-Z", "Y")


def restored_metals(out):
    def shader(label):
        t = bpy.data.materials["Invincible · " + label].node_tree
        return t, t.nodes.get("Principled BSDF")

    def change_paint(label, key, metal, rough):
        t, bsdf = shader(label)
        old = bsdf.inputs["Base Color"].links[0].from_node
        if old.image.packed_file:
            image = bpy.data.images.load(str(out / (key + "-paint.jpg")))
            original = old.image
            old.image = image
            name = original.name
            if original.users == 0:
                bpy.data.images.remove(original)
            image.name = name
            image.pack()
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        return t, bsdf

    change_paint("patinated mountain faces", "rock", 0.37, 0.56)
    _, top = shader("warm patina on the top and underside")
    color = np.asarray([93, 78, 48]) / 255
    color = ((color + 0.055) / 1.055) ** 2.4
    top.inputs["Base Color"].default_value = (*color, 1)
    top.inputs["Metallic"].default_value = 0.39
    top.inputs["Roughness"].default_value = 0.51
    tree, face = change_paint(
        "hand-painted muzzle and combed gilt hair", "head", 0.06, 0.57
    )
    painted = tree.nodes.new("ShaderNodeTexImage")
    painted.image = bpy.data.images.load(str(out / "head-metal-rough.png"))
    painted.image.name = "Invincible · gold and enamel finishes"
    painted.image.colorspace_settings.name = "Non-Color"
    painted.image.pack()
    split = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(painted.outputs["Color"], split.inputs["Color"])
    tree.links.new(split.outputs["Green"], face.inputs["Roughness"])
    tree.links.new(split.outputs["Blue"], face.inputs["Metallic"])


def save_and_export(out):
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "great-sage.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(out / "great-sage.blend"), load_ui=False)
    obj = bpy.context.scene.objects["Sun Wukong · The Great Victory"]
    assert len(obj.vertex_groups) >= 21
    assert all(i.packed_file for i in bpy.data.images if i.type == "IMAGE")
    print("CAST GEO", list(obj.dimensions), len(obj.data.polygons))
    assert (
        max(abs(s - t) for s, t in zip(obj.dimensions, (0.145, 0.110, 0.265))) < 0.00045
    )
    target = out / "great-sage.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(target),
        export_format="GLB",
        export_extras=True,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("pack-product-geometry.mjs")),
            str(target),
        ],
        check=True,
    )


def render(out):
    bpy.ops.wm.open_mainfile(filepath=str(out / "great-sage.blend"), load_ui=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 7
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 840
    scene.render.resolution_y = 1050
    scene.render.resolution_percentage = 100
    world = bpy.data.worlds.new("Neutral display booth")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs[0].default_value = (
        0.56,
        0.56,
        0.54,
        1,
    )
    world.node_tree.nodes.get("Background").inputs[1].default_value = 0.57
    scene.view_settings.view_transform = "Standard"
    for n, point, size, power in [
        ("Key", (-0.30, -0.4, 0.6), 0.5, 4.2),
        ("Fill", (0.3, -0.12, 0.3), 0.42, 1.4),
        ("Edge", (0, 0.37, 0.42), 0.40, 1.9),
    ]:
        light = bpy.data.lights.new(n, "AREA")
        light.shape = "DISK"
        light.size = size
        light.energy = power
        obj = bpy.data.objects.new(n, light)
        scene.collection.objects.link(obj)
        obj.location = point
        obj.rotation_euler = (
            (Vector((0, 0, 0.14)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
    camera = bpy.data.cameras.new("Product camera")
    c = bpy.data.objects.new("Product camera", camera)
    scene.collection.objects.link(c)
    scene.camera = c
    camera.type = "ORTHO"
    camera.ortho_scale = 0.300
    camera.clip_start = 0.01
    for name, eye in [
        ("front", (0, -0.52, 0.144)),
        ("left", (-0.52, 0, 0.144)),
        ("right", (0.52, 0, 0.144)),
        ("rear", (0, 0.52, 0.144)),
        ("oblique", (0.26, -0.48, 0.172)),
        ("waist-to-boots", (-0.007, -0.52, 0.1355)),
    ]:
        detail = name == "waist-to-boots"
        if detail:
            camera.ortho_scale = 0.083
            scene.render.resolution_x = 940
            scene.render.resolution_y = 780
            scene.cycles.samples = 19
        focus = (-0.007, 0, 0.124) if detail else (0, 0, 0.1325)
        c.location = eye
        c.rotation_euler = (
            (Vector(focus) - c.location).to_track_quat("-Z", "Y").to_euler()
        )
        scene.render.filepath = str(out / (name + ".png"))
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--finish-from", type=Path)
    opts = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    dest = opts.output.resolve()
    if opts.finish_from:
        bpy.ops.wm.open_mainfile(
            filepath=str(opts.finish_from.resolve()), load_ui=False
        )
    else:
        build(dest)
    restored_metals(dest)
    save_and_export(dest)
    if opts.render:
        render(dest)
