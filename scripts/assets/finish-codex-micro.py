import math
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


project = Path(__file__).resolve().parents[2]
source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
atelier = project / ".review" / "atelier"
output = project / "public" / "media" / "models" / "codex-micro.glb"
atelier.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))


def shader(material):
    return next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")


def simple_finish(name, color, roughness, metal=0.0, glow=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    surface = shader(material)
    surface.inputs["Base Color"].default_value = (*color, 1)
    surface.inputs["Roughness"].default_value = roughness
    surface.inputs["Metallic"].default_value = metal
    surface.inputs["Emission Color"].default_value = (*color, 1)
    surface.inputs["Emission Strength"].default_value = glow
    return material


def rounded_part(name, location, size, radius, finish):
    x, y, z = (value * 0.001 for value in location)
    w, d, h = (value * 0.001 for value in size)
    radius *= 0.001
    outline = []
    for corner, (cx, cy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for step in range(9):
            angle = (corner + step / 8) * math.pi / 2
            outline.append((cx * (w / 2 - radius) + radius * math.cos(angle),
                            cy * (d / 2 - radius) + radius * math.sin(angle)))
    count = len(outline)
    verts = [(a, b, level) for level in (-h / 2, h / 2) for a, b in outline]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    for i in range(count):
        nxt = (i + 1) % count
        faces.append((i, nxt, nxt + count, i + count))
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    part = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(part)
    part.location = (x, y, z)
    part.data.materials.append(finish)
    for face in data.polygons[2:]:
        face.use_smooth = True
    return part


for part in bpy.context.scene.objects:
    part.name = part.name.removesuffix(" display")

pitch = 19.05
states = [
    ("Mint", 1, 0, (0.14, 0.82, 0.53)),
    ("Amber", 2, 0, (0.98, 0.57, 0.18)),
    ("Blue", 0, 1, (0.27, 0.48, 0.95)),
    ("White", 1, 1, (0.86, 0.9, 0.96)),
    ("Lavender", 2, 1, (0.43, 0.41, 0.9)),
    ("Rose", 3, 1, (0.95, 0.35, 0.46)),
]
for name, column, row, color in states:
    light = simple_finish(name + " agent-key light guide", color, 0.46, glow=0.20)
    shader(light).inputs["Alpha"].default_value = 0.62
    light.surface_render_method = "BLENDED"
    light.use_backface_culling = True
    rounded_part(name + " diffuser", ((column - 1.5) * pitch, (1.5 - row) * pitch, 14.31),
                 (13.45, 13.45, 0.35), 2.1, light)

graphite = simple_finish("Joystick folded retainer clips", (0.034, 0.039, 0.046), 0.48, 0.52)
center = 1.5 * pitch
for side in (-1, 1):
    for clip_index, offset in enumerate((-4.6, 0, 4.6)):
        for across in (True, False):
            dx, dy = (offset, side * 8.48) if across else (side * 8.48, offset)
            size = (2.0, 0.5, 3.9) if across else (0.5, 2.0, 3.9)
            rounded_part(f"Stick clip {side} {clip_index} {across}",
                         (center + dx, center + dy, 13.28), size, 0.16, graphite)

lining = simple_finish("USB-C socket well", (0.012, 0.014, 0.017), 0.72)
slot = rounded_part("USB-C socket well", (0, 52.65, 6.7), (9.1, 3.05, 0.58), 1.5, lining)
slot.rotation_euler.x = math.pi / 2
tongue = rounded_part("USB-C connector tongue", (0, 52.95, 6.7),
                      (6.25, 0.55, 0.92), 0.23, graphite)
tongue.rotation_euler.x = math.pi / 2

clear = bpy.data.materials["Clear polycarbonate display"]
cap = shader(clear)
cap.inputs["Transmission Weight"].default_value = 0
cap.inputs["Alpha"].default_value = 0.34
cap.inputs["Roughness"].default_value = 0.24
clear.surface_render_method = "BLENDED"
clear.use_backface_culling = True

frame = bpy.data.materials["Frosted polycarbonate display"]
rim = shader(frame)
rim.inputs["Transmission Weight"].default_value = 0
rim.inputs["Alpha"].default_value = 0.9
frame.surface_render_method = "BLENDED"
frame.use_backface_culling = True

def key_dish(x, y, extension):
    dx = math.copysign(max(0.0, abs(x) - extension), x)
    radius = math.hypot(dx, y)
    if radius <= 6.6:
        height = 3.65 + 1.75 * (radius / 6.6) ** 2
        gradient = 3.5 * radius / 6.6**2
    elif radius < 7.25:
        t = (radius - 6.6) / 0.65
        a = 3.5 / 6.6 * 0.65
        b = 0.45 - 2 * a
        c = a - 0.3
        height = 5.4 + a * t + b * t**2 + c * t**3
        gradient = (a + 2 * b * t + 3 * c * t**2) / 0.65
    else:
        return 5.55, Vector((0, 0, 1))
    scale = -gradient / radius if radius else 0
    return height, Vector((dx * scale, y * scale, 1)).normalized()


def key_outline(half_width, half_depth, radius):
    points = []
    for corner, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for step in range(17):
            angle = (corner + step / 16) * math.pi / 2
            points.append((sx * (half_width - radius) + radius * math.cos(angle),
                           sy * (half_depth - radius) + radius * math.sin(angle)))
    return points


def resurface_keycap(obj, extension):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    old_top = [face for face in mesh.faces if all(v.co.z > 2.9 for v in face.verts)]
    bmesh.ops.delete(mesh, geom=old_top, context="FACES")
    rings = [(9, 3, 5.15), (8.95, 2.95, 5.4), (8.825, 2.9, 5.55)]
    for radius in (7.25, 7.1, 6.9, 6.75, 6.6, 6.05, 5.5, 4.95, 4.4, 3.85, 3.3,
                   2.75, 2.2, 1.65, 1.1, 0.55, 0.025):
        rings.append((radius, radius, key_dish(extension + radius, 0, extension)[0]))
    previous = []
    added = []
    crown = []
    for half_depth, radius, z in rings:
        row = [mesh.verts.new((x, y, z))
               for x, y in key_outline(half_depth + extension, half_depth, radius)]
        if previous:
            for i, vertex in enumerate(row):
                j = (i + 1) % len(row)
                crown.append(mesh.faces.new((previous[i], previous[j], row[j], vertex)))
        added.extend(row)
        previous = row
    crown.append(mesh.faces.new(previous))
    uv = mesh.loops.layers.uv.verify()
    for face in crown:
        for loop in face.loops:
            loop[uv].uv = (loop.vert.co.x / 4, loop.vert.co.y / 4)
    boundary = [v for v in mesh.verts if abs(v.co.z - 5.15) < 0.0001]
    bmesh.ops.remove_doubles(mesh, verts=list(set(added + boundary)), dist=0.00001)
    mesh.to_mesh(obj.data)
    mesh.free()


def conform_key_legend(obj, extension):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.normal_update()
    bmesh.ops.delete(mesh, geom=[f for f in mesh.faces if f.normal.z < 0.7], context="FACES")
    for vertex in mesh.verts:
        x, y, _ = vertex.co
        vertex.co.z = key_dish(x, y, extension)[0] + 0.045
    mesh.to_mesh(obj.data)
    mesh.free()


def smooth_key_surface(obj, extension, ink=False):
    data = obj.data
    normals = [loop.vector.copy() for loop in data.corner_normals]
    for face in data.polygons:
        if not ink and face.center.z < 2.95:
            continue
        face.use_smooth = True
        for i in face.loop_indices:
            x, y, z = data.vertices[data.loops[i].vertex_index].co
            on_deck = face.normal.z > 0.45 and z >= 5.545
            in_dish = math.hypot(max(0, abs(x) - extension), y) <= 7.26
            if ink or on_deck or in_dish:
                normals[i] = key_dish(x, y, extension)[1]
            elif z >= 5.14:
                dx = math.copysign(max(0, abs(x) - 6.0 - extension), x)
                dy = math.copysign(max(0, abs(y) - 6.0), y)
                radial = Vector((dx, dy, 0)).normalized()
                rise = 0.14 if z < 5.3 else 0.6
                normals[i] = (radial + Vector((0, 0, rise))).normalized()
    data.normals_split_custom_set(normals)


porcelain = {}
legends = {}
for part in bpy.context.scene.objects:
    if part.type != "MESH":
        continue
    name = part.name.split(".")[0].lower()
    extension = pitch / 2 if name.startswith("microphone ") else 0
    if name.endswith(" keycap") and part.data.materials[0].name == "Fine-grain porcelain PBT display":
        resurface_keycap(part, extension)
        porcelain[part] = extension
    elif name in {"fast solid", "approve solid", "reject solid", "worktree solid", "microphone solid",
                  "codex solid"} and part.data.materials[0].name == "Printed graphite ink display":
        conform_key_legend(part, extension)
        legends[part] = extension
if len(porcelain) != 6 or len(legends) != 6:
    raise ValueError("Expected six porcelain crowns with matching printed legends")
for part, extension in porcelain.items():
    smooth_key_surface(part, extension)
for part, extension in legends.items():
    smooth_key_surface(part, extension, ink=True)

scene = bpy.context.scene
scene.name = "Codex Micro"
scene.unit_settings.system = "METRIC"
scene["reference"] = "OpenAI mcp-extensions, Bits and Bolts, Apache-2.0"
scene["finish"] = "Felix Studio: switch illumination, joystick retainers, connector and polymer finishes"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(atelier / "codex-micro.blend"), compress=True)


def trim_hidden_keycap_interiors():
    points, triangles = [], []
    for obj in scene.objects:
        if obj.type != "MESH" or any(shader(mat).inputs["Alpha"].default_value < 0.99
                                      for mat in obj.data.materials):
            continue
        offset = len(points)
        points.extend(obj.matrix_world @ vert.co for vert in obj.data.vertices)
        obj.data.calc_loop_triangles()
        triangles.extend(tuple(offset + i for i in tri.vertices) for tri in obj.data.loop_triangles)
    opaque = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    directions = []
    for elevation in (-90, -75, -60, -45, -32, -22, -14, -8, -4, -2, 0, 4, 12, 30, 60, 90):
        height = math.radians(elevation)
        for step in range(32 if abs(elevation) < 90 else 1):
            angle = step * math.tau / 32
            directions.append(Vector((math.cos(height) * math.cos(angle),
                                      math.cos(height) * math.sin(angle), math.sin(height))))

    removed = 0
    for obj in scene.objects:
        if "keycap" not in obj.name.lower() or not any(
            mat.name == "Fine-grain porcelain PBT display" for mat in obj.data.materials
        ):
            continue
        model = bmesh.new()
        model.from_mesh(obj.data)
        model.normal_update()
        world = obj.matrix_world
        normal_matrix = world.to_3x3().inverted().transposed()
        hidden = []
        for face in model.faces:
            center = world @ face.calc_center_median()
            relative = center - world.translation
            normal = (normal_matrix @ face.normal).normalized()
            if not 0.0001 < relative.z < 0.00285:
                continue
            if normal.z > -0.8 and normal.x * relative.x + normal.y * relative.y > -0.0015:
                continue
            samples = [center] + [center.lerp(world @ vertex.co, 0.94) for vertex in face.verts]
            outward = [v for v in directions if v.dot(normal) > 0.005]
            if all(opaque.ray_cast(sample + normal * 0.000002, direction, 0.3)[0] is not None
                   for sample in samples for direction in outward):
                hidden.append(face)
        if hidden:
            removed += len(hidden)
            bmesh.ops.delete(model, geom=hidden, context="FACES")
            model.to_mesh(obj.data)
        model.free()
    if not removed:
        raise ValueError("Expected inaccessible cavities in the porcelain keycaps")
    print(f"Pruned {removed} occluded porcelain keycap cavity faces")


trim_hidden_keycap_interiors()
standard_cap = next(part.data for part, extension in porcelain.items() if extension == 0)
for part, extension in porcelain.items():
    if extension == 0:
        part.data = standard_cap
    smooth_key_surface(part, extension)

for texture in bpy.data.images:
    if texture.type == "IMAGE" and max(texture.size) > 128:
        texture.scale(128, 128)
        texture.pack()
with TemporaryDirectory(dir=atelier) as staging:
    candidate = Path(staging) / output.name
    bpy.ops.export_scene.gltf(
        filepath=str(candidate),
        export_format="GLB",
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
        export_copyright="OpenAI mcp-extensions, Apache-2.0. Adapted for Felix Studio.",
    )
    for packer in ("pack-product-geometry.mjs", "pack-codex-micro.mjs"):
        subprocess.run(["node", str(project / "scripts/assets" / packer), str(candidate)], check=True)
    candidate.replace(output)
