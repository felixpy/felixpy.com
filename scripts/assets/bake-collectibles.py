import math
import json
import runpy
import subprocess
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[2] / ".review" / "atelier"


def point_color(mesh, name, rgb):
    attr = mesh.color_attributes.new(name=name, type="FLOAT_COLOR", domain="POINT")
    rgba = np.ones((len(rgb), 4), dtype="f")
    rgba[:, :3] = rgb
    attr.data.foreach_set("color", rgba.ravel())
    return attr.name


def linear(rgb):
    return np.where(rgb < 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def temple_paint(mesh, data, vertex_ids, tree, reference, base):
    def fade(value, low, high):
        t = np.clip((value - low) / (high - low), 0, 1)
        return t * t * (3 - 2 * t)

    x, y, z = data["points"].T * 1000
    dx = x + 25
    angle = np.arctan2((y - 3) * 2.3, np.abs(dx))
    band = fade(z, 166, 176) * (1 - fade(z, 197, 203))
    ear = np.exp(-(((z - 178) / 5.7) ** 2) - ((y - 1) / 3.2) ** 2)
    temple = (
        band
        * fade(angle, -0.59, -0.02)
        * (1 - fade(angle, 1.04, 1.46))
        * (1 - fade(np.abs(dx), 27, 33))
        * (1 - ear)
    )
    temple *= 1 - fade(data["mix"], 0.72, 0.96)
    pixels = np.empty(len(reference.pixels), dtype="f")
    reference.pixels.foreach_get(pixels)
    raw = pixels.reshape(reference.size[1], reference.size[0], 4)
    patch = raw[reference.size[1] - 248 : reference.size[1] - 229, 382:428]
    mirrored = np.concatenate((patch, patch[:, ::-1]), axis=1)
    tile = np.concatenate((mirrored, mirrored[::-1]), axis=0)
    grain = bpy.data.images.new(
        "Photographed temple curls", tile.shape[1], tile.shape[0], float_buffer=True
    )
    grain.colorspace_settings.name = "Non-Color"
    grain.pixels.foreach_set(tile.ravel())
    travel = (
        (z - 164) * 3.55
        + angle * 16
        + 4.2 * np.sin(angle * 1.7)
        + angle * (z - 180) * 0.28
    )
    coordinates = np.column_stack(
        (travel / tile.shape[1], (angle * 20 - (z - 180) * 0.26) / tile.shape[0])
    ).astype("f")
    second = mesh.uv_layers.new(name="Side hair paint")
    second.uv.foreach_set("vector", coordinates[vertex_ids].ravel())
    layer = tree.nodes.new("ShaderNodeUVMap")
    layer.uv_map = second.name
    sample = tree.nodes.new("ShaderNodeTexImage")
    sample.image = grain
    tree.links.new(layer.outputs["UV"], sample.inputs["Vector"])
    weight = tree.nodes.new("ShaderNodeVertexColor")
    weight.layer_name = point_color(
        mesh, "Temple paint blend", np.tile(temple[:, None], (1, 3))
    )
    blend = tree.nodes.new("ShaderNodeMixRGB")
    tree.links.new(weight.outputs["Color"], blend.inputs[0])
    tree.links.new(base, blend.inputs[1])
    tree.links.new(sample.outputs["Color"], blend.inputs[2])
    return blend.outputs[0]


def painted_master(slug, title, dimension):
    data = np.load(ROOT / f"{slug}-casting.npz")
    mesh = bpy.data.meshes.new(title)
    mesh.from_pydata(data["points"].tolist(), [], data["faces"].tolist())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), dtype=bool))
    mesh.update()
    obj = bpy.data.objects.new(title, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    polygon_uv = mesh.uv_layers.new(name="Photo registration")
    vertex_ids = np.empty(len(mesh.loops), dtype="i")
    mesh.loops.foreach_get("vertex_index", vertex_ids)
    polygon_uv.uv.foreach_set("vector", data["uv"][vertex_ids].ravel())
    atlas_uv = mesh.uv_layers.new(name="Baked surface")
    atlas_uv.active_render = True
    mesh.uv_layers.active = atlas_uv
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(68),
        island_margin=0.002,
        area_weight=0.25,
        correct_aspect=False,
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    source = point_color(mesh, "Reconstructed finish", linear(data["rear"]))
    confidence = point_color(
        mesh,
        "Frontal visibility",
        np.broadcast_to(data["mix"][:, None], (len(data["mix"]), 3)),
    )
    bake_material = bpy.data.materials.new("Registered reference and reverse")
    bake_material.use_nodes = True
    mesh.materials.append(bake_material)
    tree = bake_material.node_tree
    nodes = tree.nodes
    links = tree.links
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(
        str(ROOT / f"{slug}-surface.png"), check_existing=True
    )
    projection = nodes.new("ShaderNodeUVMap")
    projection.uv_map = "Photo registration"
    links.new(projection.outputs["UV"], tex.inputs["Vector"])
    back = nodes.new("ShaderNodeVertexColor")
    back.layer_name = source
    weight = nodes.new("ShaderNodeVertexColor")
    weight.layer_name = confidence
    mix = nodes.new("ShaderNodeMixRGB")
    links.new(weight.outputs["Color"], mix.inputs[0])
    links.new(back.outputs["Color"], mix.inputs[1])
    links.new(tex.outputs["Color"], mix.inputs[2])
    emission = nodes.new("ShaderNodeEmission")
    paint = mix.outputs[0]
    if slug == "great-sage":
        paint = temple_paint(mesh, data, vertex_ids, tree, tex.image, paint)
        mesh.uv_layers.active = mesh.uv_layers["Baked surface"]
        mesh.uv_layers.active.active_render = True
    links.new(paint, emission.inputs["Color"])
    links.new(emission.outputs[0], nodes.get("Material Output").inputs["Surface"])
    target = nodes.new("ShaderNodeTexImage")
    target.image = bpy.data.images.new(title + " · paint", 1536, 1536, alpha=False)
    nodes.active = target
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    bpy.ops.object.bake(type="EMIT", use_clear=True, margin=5)
    target.image.filepath_raw = str(ROOT / f"{slug}-paint.jpg")
    target.image.file_format = "JPEG"
    target.image.save()
    layout = json.loads(subprocess.check_output([
        "uv", "--cache-dir", str(ROOT.parent / "uv-assets-cache"), "run", "--no-project",
        "--with", "pillow", "--with", "numpy", "--with", "opencv-python-headless",
        "python", str(Path(__file__).with_name("collectible-front-atlas.py")),
        str(ROOT), slug,
    ], text=True))
    color_atlas = bpy.data.images.load(str(ROOT / f"{slug}-registered-paint.jpg"), check_existing=False)
    color_atlas.pack()
    atlas_uv = mesh.uv_layers["Baked surface"]
    assert len(atlas_uv.uv) == len(mesh.loops)
    coordinates = np.zeros((len(mesh.loops), 2), dtype="f")
    atlas_uv.uv.foreach_get("vector", coordinates.ravel())
    assert np.isfinite(coordinates).all() and np.max(np.abs(coordinates)) < 1.01
    coordinates *= layout["fallback"]
    front_faces = np.min(data["mix"][data["faces"]], axis=1) >= 0.96
    visible = np.repeat(front_faces, 3)
    coordinates[visible] = data["uv"][vertex_ids[visible]] * layout["source"] + layout["offset"]
    coordinates /= layout["atlas"]
    atlas_uv.uv.foreach_set("vector", coordinates.ravel())
    mesh.uv_layers.remove(mesh.uv_layers["Photo registration"])
    if slug == "great-sage":
        mesh.uv_layers.remove(mesh.uv_layers["Side hair paint"])
    for attr in list(mesh.color_attributes):
        mesh.color_attributes.remove(attr)
    mesh.materials.clear()
    slots = [
        ("Patinated base", 0.18, 0.56, 0.04),
        ("Painted surface", 0.11, 0.53, 0.035),
        ("Polished gilt", 0.26, 0.49, 0.04),
        ("Face paint", 0.02, 0.67, 0.01),
        ("Spacing and cloth", 0.08, 0.63, 0.03),
    ]
    if slug == "mk85":
        slots = [
            ("Cast brass ruins", 0.29, 0.52, 0.07),
            ("Candy red armor", 0.29, 0.40, 0.16),
            ("Gold and silver armor", 0.39, 0.40, 0.12),
            ("Articulated seals", 0.17, 0.47, 0.09),
        ]
    for name, metal, rough, coat in slots:
        mat = bpy.data.materials.new(title + " · " + name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = rough
        shader.inputs["Coat Weight"].default_value = coat
        shader.inputs["Coat Roughness"].default_value = max(0.08, rough * 0.68)
        paint = mat.node_tree.nodes.new("ShaderNodeTexImage")
        paint.image = color_atlas
        mat.node_tree.links.new(paint.outputs["Color"], shader.inputs["Base Color"])
        mesh.materials.append(mat)
    faces = data["faces"]
    h = data["points"][faces, 2].mean(axis=1) / dimension[2]
    colors = data["front"][faces].mean(axis=1)
    red, green, blue = colors.T
    mats = np.ones(len(faces), dtype="i")
    if slug == "great-sage":
        mats[(red > blue * 1.22) & (green > 0.73 * red)] = 2
        mats[
            (h > 0.565)
            & (h < 0.695)
            & (red > blue * 1.33)
            & (blue > 0.63 * green)
            & (green > 0.65 * red)
        ] = 3
        mats[(colors.max(axis=1) < 0.35) & (h > 0.24)] = 4
        mats[h < 0.238] = 0
    else:
        mats[(green > 0.66 * red)] = 2
        mats[(colors.max(axis=1) < 0.25)] = 3
        mats[h < 0.27] = 0
    mesh.polygons.foreach_set("material_index", mats)
    reducer = obj.modifiers.new("Display detail", "DECIMATE")
    reducer.ratio = 0.78
    reducer.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=reducer.name)
    mesh = obj.data
    p = np.empty(len(mesh.vertices) * 3, dtype="f")
    mesh.vertices.foreach_get("co", p)
    p = p.reshape(-1, 3)
    p -= np.array(
        [
            (p[:, 0].max() + p[:, 0].min()) / 2,
            (p[:, 1].max() + p[:, 1].min()) / 2,
            p[:, 2].min(),
        ]
    )
    p *= dimension / np.ptp(p, axis=0)
    p[:, 2] = np.where(p[:, 2] < 0.00045, 0, p[:, 2])
    mesh.vertices.foreach_set("co", p.ravel())
    mesh.update()
    runpy.run_path(str(Path(__file__).with_name("collectible-relief.py")))[
        "model_surface"
    ](obj, data, slug, ROOT)
    if slug == "great-sage":
        runpy.run_path(str(Path(__file__).with_name("sculpt-great-sage.py")))["sculpt"](obj)
    runpy.run_path(str(Path(__file__).with_name("collectible_sole.py")))["level_sole"](obj, slug)
    obj["cabinetItem"] = title
    print(f"CASTING {title}: {len(mesh.polygons)} triangles; {dimension}", flush=True)
    return obj


def write_statuette(figure, slug):
    source = ROOT / "sculptures"
    source.mkdir(exist_ok=True)
    scene = bpy.data.scenes.new(figure.name)
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.collection.objects.link(figure)
    scene.display.shading.color_type = "TEXTURE"
    window = bpy.context.window
    previous = window.scene
    window.scene = scene
    try:
        figure.select_set(True)
        bpy.context.view_layer.objects.active = figure
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.clip_start = 0.0001
                view.region_3d.view_distance = 0.48
                view.region_3d.view_location = (0, 0, 0.13)
                view.region_3d.view_rotation = (0.7053, 0.7053, 0.0462, 0.0462)
                view.shading.type = "MATERIAL"
                view.overlay.show_overlays = False
        bpy.data.libraries.write(
            str(source / (slug + ".blend")),
            {scene, window.workspace},
            fake_user=True,
            compress=True,
        )
    finally:
        window.scene = previous
        bpy.data.scenes.remove(scene)


def new_pair():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    a = painted_master(
        "great-sage", "Sun Wukong · The Great Victory", np.array([0.175, 0.057, 0.265])
    )
    b = painted_master(
        "mk85", "Tongshifu · Iron Man Mark 85", np.array([0.155, 0.110, 0.260])
    )
    bpy.data.libraries.write(
        str(ROOT / "registered-collectibles.blend"), {a, b}, fake_user=True
    )
    write_statuette(a, "great-sage")
    write_statuette(b, "mk85")
    return a, b


if __name__ == "__main__":
    new_pair()
    for slug in ["great-sage", "mk85"]:
        path = ROOT / "sculptures" / (slug + ".blend")
        bpy.ops.wm.open_mainfile(filepath=str(path))
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
