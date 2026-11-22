from pathlib import Path
import subprocess
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / ".review/atelier/pc-components"
ART = STUDIO / "artwork"
RGB = "D50 opal RGB"


def rasterize():
    ART.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name("xpg-d50-print.svg").read_text(encoding="utf-8")
    (ART / "xpg-side.svg").write_text(source, encoding="utf-8")
    logo = source[source.index('<g fill="#171921"'):source.rindex("</svg>")]
    logo = logo.replace('translate(891 242)', 'translate(0 0)')
    for name, background, mark in [
        ("xpg-guide-coat", "#8e9298", "#252a30"),
        ("xpg-guide-light", "url(#spectrum)", "#000000"),
    ]:
        stops = [
            (0, "#9613e6"), (0.12, "#4c13ed"), (.25, "#065eec"),
            (.41, "#00acd7"), (.52, "#00d7b8"), (.64, "#1ed55c"),
            (.74, "#a5e409"), (.84, "#efd302"), (.95, "#fb8d0b"), (1, "#fb5912"),
        ]
        gradient = "".join(f'<stop offset="{x}" stop-color="{color}"/>' for x, color in stops)
        (ART / (name + ".svg")).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="96" viewBox="0 0 1024 96">'
            f'<defs><linearGradient id="spectrum">{gradient}</linearGradient></defs>'
            f'<rect width="1024" height="96" fill="{background}"/>'
            f'<g transform="translate(460 12) scale(.67 1.2)">{logo.replace("#171921", mark)}</g></svg>',
            encoding="utf-8",
        )
    script = """
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
(async () => {
  const local = [chromium.executablePath(), process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => p && fs.existsSync(p));
  const browser = await chromium.launch({ executablePath: local, headless: true });
  try {
    for (const [file,width,height] of [['xpg-side',1440,448],['xpg-guide-coat',1024,96],['xpg-guide-light',1024,96]]) {
      const page = await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
      const name = path.join(process.argv[1], file);
      await page.goto(pathToFileURL(name + '.svg').href);
      await page.screenshot({path:name + '.png'});
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(e => {console.error(e); process.exitCode=1});
"""
    subprocess.run(["node", "-e", script, str(ART)], cwd=ROOT, check=True)


def point(u, height, thickness):
    return (-height * .001, -thickness * .001, u * .001)


def part(name, vertices, faces, material, uvs=None, bevel=0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([point(*v) for v in vertices], [], faces)
    mesh.materials.append(material)
    mesh.update()
    if uvs:
        layer = mesh.uv_layers.new()
        for polygon, coords in zip(mesh.polygons, uvs):
            for loop, value in zip(polygon.loop_indices, coords):
                layer.data[loop].uv = value
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    product.objects.link(obj)
    if bevel:
        mod = obj.modifiers.new("Tool radius", "BEVEL")
        mod.width = bevel * .001
        mod.segments = 3
        mod.harden_normals = True
        mod = obj.modifiers.new("Plane normals", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
    return obj


def sets(name, sections, material, bevel=0):
    verts, faces = [], []
    for outer, inner in sections:
        base, n = len(verts), len(outer)
        verts.extend(outer + inner)
        faces.extend([tuple(base + i for i in reversed(range(n))),
                      tuple(base + n + i for i in range(n))])
        for i in range(n):
            j = (i + 1) % n
            faces.append((base + i, base + j, base + j + n, base + i + n))
    return part(name, verts, faces, material, bevel=bevel)


def shell(profile, near, far):
    return ([(u, h, near) for u, h in profile], [(u, h, far) for u, h in profile])


def finish(name, color, metal, rough):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return mat


def ink(mat, file, socket):
    image = bpy.data.images.load(str(ART / (file + ".png")), check_existing=True)
    image.pack()
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "EXTEND"
    mat.node_tree.links.new(tex.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs[socket])
    return tex


def crop(poly, evaluate):
    result = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ha, hb = evaluate(*a), evaluate(*b)
        if ha >= 0:
            result.append(a)
        if ha * hb < 0:
            t = ha / (ha - hb)
            result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return result


def cover(side):
    shape = [(0, 2), (5, 0), (180, 0), (185, 7), (600, 99), (608, 99), (782, 8),
             (787, 0), (1075, 0), (1080, 4), (1080, 331), (1075, 336), (5, 336), (0, 331)]
    def crease(x, y):
        return y - .199 * x - 4
    slices = [
        crop(shape, lambda x, y: -crease(x, y)),
        crop(crop(shape, crease), lambda x, y: 8 - crease(x, y)),
        crop(shape, lambda x, y: crease(x, y) - 8),
    ]
    def world(x, y, depth):
        return ((x / 1080 - .5) * 131.35 * side, 39.4 - y * (34.25 / 336), depth * side)
    def relief(x, y):
        return 3.65 + .35 * max(0, min(1, crease(x, y) / 8))
    verts, faces, uvs, index = [], [], [], {}
    def vertex(x, y, t):
        k = (round(x, 4), round(y, 4), round(t, 5))
        if k not in index:
            index[k] = len(verts)
            verts.append(world(x, y, t))
        return index[k]
    def face(points):
        faces.append([vertex(*p) for p in points])
        uvs.append([(x / 1080, 1 - y / 336) for x, y, _ in points])
    for patch in slices:
        face([(x, y, relief(x, y)) for x, y in patch])
        face([(x, y, 1.74) for x, y in reversed(patch)])
        for a, b in zip(patch, patch[1:] + patch[:1]):
            if any(abs(crease(*a) - k) < .001 and abs(crease(*b) - k) < .001 for k in (0, 8)):
                continue
            face([(*a, relief(*a)), (*b, relief(*b)), (*b, 1.74), (*a, 1.74)])
    name = "Window-side" if side == 1 else "Socket-side"
    item = part(name + " ceramic white stamped heat spreader", verts, faces, paint, uvs, .15)
    item.data.materials.append(enamel)
    for p in item.data.polygons:
        if max(abs(item.data.vertices[v].co.y) for v in p.vertices) <= .00175 or abs(p.normal.y) < .65:
            p.material_index = 1


def light_bar():
    rings = [(-65.51, 38.9), (-65.2, 39.6), (-64.6, 39.98),
             (64.6, 39.98), (65.2, 39.6), (65.51, 38.9)]
    verts, faces, uvs = [], [], []
    for u, roof in rings:
        for t, h in [(-2.39, roof), (2.39, roof), (2.86, roof - .23),
                     (2.90, 28.0), (2.49, 27.1), (-2.49, 27.1), (-2.90, 28), (-2.86, roof - .23)]:
            verts.append((u, h, t))
    for i in range(len(rings) - 1):
        for j in range(8):
            n = (j + 1) % 8
            f = [8*i + j, 8*i + n, 8*i + 8 + n, 8*i + 8 + j]
            faces.append(f)
            uvs.append([((verts[k][0] / 131.02) + .5,
                         .5 - verts[k][2] / 4.78 if j == 0 else .015) for k in f])
    for i in (0, len(rings)-1):
        f = [8*i + j for j in range(8)]
        faces.append(f)
        uvs.append([((verts[k][0] / 131.02) + .5, .015) for k in f])
    part("Continuous opaline light guide and pad printed XPG crown", verts, faces, opal, uvs)


def connector():
    profile = [(-66.675, 1.7), (-66.25, 1.22), (-40, .52), (-9, .16),
               (2.87, .02), (2.87, 3.42), (3.12, 3.78), (4.25, 3.78), (4.52, 3.42),
               (4.52, .06), (34, .45), (66.05, 1.26), (66.675, 1.91)]
    flank = [(66.675, 6.5), (65.25, 6.9), (65.25, 8.5), (66.675, 8.81),
             (66.675, 12.05), (66.02, 12.26), (66.02, 25.5), (65.55, 25.75),
             (65.55, 32.2), (64.9, 33.1)]
    outline = profile + flank + [(-u, h) for u, h in reversed(flank)]
    sets("Black solder-mask FR4 and keyed insertion edge", [shell(outline, -.631, .631)], pcb, .065)
    fingers, faces = [], []
    for side in (-1, 1):
        for i in range(144):
            u = -60.90 + i * .85 if i < 75 else 5.40 + (i - 75) * .85
            if 2.55 < u < 4.86:
                raise ValueError(f"Gold contact intersects DDR5 key at {u}")
            low = .18 + .995 * (abs(u - 1.2) / 63.25) ** 1.7
            high = 4.18 + .24 * (i % 5 != 0)
            profile = [(u-.29, low+.18), (u-.15, low), (u+.15, low), (u+.29, low+.18),
                       (u+.29, high-.13), (u+.16, high), (u-.16, high), (u-.29, high-.13)]
            base = len(fingers)
            fingers.extend((x, h, side * .635) for x, h in profile)
            order = range(len(profile)) if side > 0 else reversed(range(len(profile)))
            faces.append(tuple(base + j for j in order))
    part("288 selectively plated connector fingers", fingers, faces, gold)
    die_packs = []
    for side in (-1, 1):
        for u in (-52, -37, -22, -7, 8, 23, 38, 53):
            profile = [(u-5.2, 6.8), (u+5.2, 6.8), (u+5.2, 22.6), (u-5.2, 22.6)]
            die_packs.append(shell(profile, .68 * side, 1.71 * side))
    sets("Under-spreader thermal interface pads", die_packs, pad)


def render_product():
    output = STUDIO / "renders"
    output.mkdir(exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.view_settings.view_transform = "Khronos PBR Neutral"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.world = bpy.data.worlds.new("Neutral product studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.18, .20, .24, 1)
    scene.render.resolution_x, scene.render.resolution_y = 1180, 568
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for i, (u, h, t, watts, size) in enumerate([(-140, 160, 175, 1.8, .14), (30, 100, -150, 2.4, .18), (165, 90, 100, 1.4, .13)]):
        source = bpy.data.lights.new(f"Softbox {i+1}", "AREA")
        source.energy, source.shape, source.size = watts * .27, "DISK", size
        light = bpy.data.objects.new(source.name, source)
        scene.collection.objects.link(light)
        light.location = point(u, h, t)
        light.rotation_euler = (Vector(point(0, 20, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("Inspection camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = .151
    camera_data.clip_start = .005
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    emitter = opal.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    for title, eye in [("side", (43, 72, 188)), ("reverse", (-55, 108, -175)),
                       ("crown", (23, 140, 88)), ("unlit", (43, 72, 188))]:
        if title == "unlit":
            emitter.default_value = 0
            diffuser_tint.default_value = (1, 1, 1, 1)
        camera.location = point(*eye)
        direction = (Vector(point(0, 20, 0)) - camera.location).normalized()
        long_axis = Vector((0, 0, 1 if eye[2] > 0 else -1))
        right = (long_axis - direction * long_axis.dot(direction)).normalized()
        from mathutils import Matrix
        camera.rotation_euler = Matrix([right, right.cross(direction), -direction]).transposed().to_euler()
        scene.render.filepath = str(output / f"xpg-d50-{title}.png")
        bpy.ops.render.render(write_still=True)


rasterize()
bpy.ops.wm.read_factory_settings(use_empty=True)
product = bpy.data.collections.new("XPG D50 ROG Strix Fubuki DDR5")
bpy.context.scene.collection.children.link(product)
pcb = finish("D50 carbon black solder mask", (.018, .022, .023), .13, .51)
gold = finish("D50 hard gold edge plating", (.76, .49, .135), .83, .30)
pad = finish("D50 thermal interface", (.08, .091, .096), .05, .86)
enamel = finish("D50 pearl enamel rolled edge", (.84, .86, .88), .28, .33)
paint = finish("D50 Fubuki ceramic pad print", (.89, .90, .92), .15, .41)
ink(paint, "xpg-side", "Base Color")
opal = finish(RGB, (.84, .86, .89), .025, .36)
guide_print = ink(opal, "xpg-guide-coat", "Base Color")
scattering = opal.node_tree.nodes.new("ShaderNodeMix")
scattering.name = "Pumped diffuser scattering"
scattering.data_type, scattering.blend_type = "RGBA", "MULTIPLY"
next(i for i in scattering.inputs if i.identifier == "Factor_Float").default_value = 1
diffuser_tint = next(i for i in scattering.inputs if i.identifier == "B_Color")
diffuser_tint.default_value = (.12, .12, .12, 1)
opal.node_tree.links.new(guide_print.outputs[0], next(i for i in scattering.inputs if i.identifier == "A_Color"))
opal.node_tree.links.new(next(o for o in scattering.outputs if o.identifier == "Result_Color"),
                         opal.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
ink(opal, "xpg-guide-light", "Emission Color")
opal.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.1
connector()
cover(1)
cover(-1)
light_bar()
for obj in product.objects:
    obj.select_set(True)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(STUDIO / "xpg-d50-fubuki.blend"), compress=True)
output = ROOT / "public/media/models/xpg-d50-fubuki.glb"
bpy.ops.export_scene.gltf(
    filepath=str(output),
    export_format="GLB", export_apply=True, use_selection=True, export_extras=False,
    export_yup=True, export_materials="EXPORT", export_cameras=False, export_lights=False,
)
subprocess.run(["node", str(Path(__file__).with_name("pack-product-geometry.mjs")), str(output), "--lossless"], check=True)
if "--review" in sys.argv:
    render_product()
