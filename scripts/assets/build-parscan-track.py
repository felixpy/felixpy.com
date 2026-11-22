import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / ".references/02-家具与灯具/轨道与射灯/ERCO Parscan 48V S/Blender"
LAYOUT = json.loads((ROOT / "src/scene/equipment-track-layout.json").read_text())


def blender(point):
    return Vector((point[0], -point[2], point[1]))


def material(name, rgb, roughness, metal=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    return mat


def empty(name, matrix):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_size = 0.01
    obj.matrix_world = matrix
    return obj


def box(name, position, size, mat, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    edge = obj.modifiers.new("Radiused die-cast edges", "BEVEL")
    edge.width, edge.segments = bevel, 3
    bpy.ops.object.modifier_apply(modifier=edge.name)
    normals = obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    bpy.ops.object.modifier_apply(modifier=normals.name)
    obj.data.materials.append(mat)
    return obj


def lathe(name, profile, mat, parent, hollow=False):
    count = 48
    vertices = [(r * math.cos(i * math.tau / count), r * math.sin(i * math.tau / count), z)
                for r, z in profile for i in range(count)]
    faces = [(j * count + i, j * count + (i + 1) % count,
              (j + 1) * count + (i + 1) % count, (j + 1) * count + i)
             for j in range(len(profile) - 1) for i in range(count)]
    if not hollow:
        faces += [tuple(reversed(range(count))), tuple(range(len(vertices) - count, len(vertices)))]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for face in mesh.polygons:
        face.use_smooth = len(face.vertices) == 4
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    mesh.materials.append(mat)
    return obj


def rod(name, start, end, radius, mat):
    axis = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=radius, depth=axis.length,
                                        location=(start + end) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = axis.to_track_quat("Z", "Y").to_euler()
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    obj.data.materials.append(mat)
    return obj


def solid(name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj


def bridge_sections(sections, closed=False):
    count = len(sections[0])
    last = len(sections) if closed else len(sections) - 1
    faces = [
        (s * count + j, s * count + (j + 1) % count,
         (s + 1) % len(sections) * count + (j + 1) % count,
         (s + 1) % len(sections) * count + j)
        for s in range(last) for j in range(count)
    ]
    if not closed:
        faces += [tuple(range(count)), tuple(range(last * count, (last + 1) * count))]
    return [v for section in sections for v in section], faces


def die_cast_arm(name, pivot, lateral, mat):
    tangent = Vector((0, 0, 1)).cross(lateral)
    sections = []
    for i in range(23):
        angle = math.radians(-34 + 68 * i / 22)
        radius = math.cos(angle) * lateral + math.sin(angle) * tangent
        toe = -0.006 + 0.004 * (abs(i - 11) / 11) ** 3
        section = [(0.0300, 0.0315), (0.0300, toe), (0.0235, toe),
                   (0.0235, 0.026), (0.018, 0.0272), (0.003, 0.0272),
                   (0.003, 0.0315)]
        sections.append([pivot + r * radius + Vector((0, 0, z)) for r, z in section])
    vertices, faces = bridge_sections(sections)
    obj = solid(name, vertices, faces, mat)
    for s in range(22):
        for side in (0, 2, 5):
            obj.data.polygons[s * len(section) + side].use_smooth = True
    return obj


def cut_pocket(housing, sections, mat):
    vertices, faces = bridge_sections(sections)
    cutter = solid("Bearing clearance", vertices, faces, mat)
    cutter.parent = housing.parent
    mod = housing.modifiers.new("Flush bearing seat", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = housing
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bearing_recess(housing, mat):
    profile = [(0.032, -0.040)]
    profile += [(0.032 * math.cos(i * math.pi / 28), 0.026 * math.sin(i * math.pi / 28)) for i in range(29)]
    profile.append((-0.032, -0.040))
    cut_pocket(housing, [[(x, y, z) for y, z in profile] for x in (0.0187, 0.049)], mat)
    sweep = []
    for x in (0.0015, 0.005, 0.010, 0.015, 0.020, 0.025, 0.031):
        half_width = x * math.tan(math.radians(34)) + 0.0005
        clearance = 0.0266 - 0.0014 * min(1.0, x / 0.025)
        overrun = math.atan2(half_width, clearance)
        angles = [-overrun + (math.pi / 2 + 2 * overrun) * i / 40 for i in range(41)]
        sweep.append([(x, r * math.sin(a), -r * math.cos(a))
                      for r, arc in ((clearance, angles), (0.052, reversed(angles))) for a in arc])
    cut_pocket(housing, sweep, mat)


def clear_spherolit(name, optic, mat):
    radius, sectors, rings = 0.0220, 48, 10
    vertices = [(0, 0, 0.0653)]
    for band in range(1, rings + 1):
        r = radius * band / rings
        for index in range(sectors):
            a = math.tau * (index + (band % 2) * 0.5) / sectors
            height = 0.0646 + 0.0007 * (1 - (r / radius) ** 2)
            vertices.append((r * math.cos(a), r * math.sin(a), height))
    faces = [(0, i + 1, (i + 1) % sectors + 1) for i in range(sectors)]
    for row in range(rings - 1):
        for i in range(sectors):
            k, n = 1 + row * sectors + i, 1 + row * sectors + (i + 1) % sectors
            corners = (k, k + sectors, n + sectors, n)
            center = sum((Vector(vertices[j]) for j in corners), Vector()) / 4
            center.z += 0.000070
            mid = len(vertices)
            vertices.append(center)
            faces.extend((corners[j], corners[(j + 1) % 4], mid) for j in range(4))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = optic
    mesh.materials.append(mat)
    return obj


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = "METRIC"
black = material("Parscan black powder coat", (0.028, 0.030, 0.032), 0.46, 0.42)
edge = material("Minirail anodised graphite", (0.043, 0.044, 0.046), 0.39, 0.62)
recess = material("Parscan optical baffle", (0.009, 0.010, 0.011), 0.56)
reflector = material("Parscan lens retainer", (0.037, 0.040, 0.045), 0.29, 0.45)
lens = material("Parscan Spherolit lens", (0.49, 0.50, 0.52), 0.18, 0.52)
prism = material("Parscan clear moulded Spherolit optic", (0.81, 0.87, 0.90), 0.14)
prism_shader = prism.node_tree.nodes.get("Principled BSDF")
prism_shader.inputs["Alpha"].default_value = 0.18
prism_shader.inputs["Coat Weight"].default_value = 0.8
prism_shader.inputs["Coat Roughness"].default_value = 0.12
prism.surface_render_method = "BLENDED"
shader = lens.node_tree.nodes.get("Principled BSDF")
shader.inputs["Emission Color"].default_value = (1.0, 0.77, 0.49, 1)
shader.inputs["Emission Strength"].default_value = 1.65
length = LAYOUT["railLength"]
box("Minirail · mounting web", (0, 0, -0.003), (length, 0.022, 0.006), black, 0.001)
for side in [-1, 1]:
    box("Minirail · extruded side lip", (0, side * 0.0084, -0.01),
        (length, 0.0052, 0.011), edge, 0.0006)
    box("Minirail · insulated conductor", (0, side * 0.0062, -0.009),
        (length - 0.012, 0.0012, 0.003), recess, 0.0003)
    box("Minirail · end cap", (side * length * 0.5, 0, -0.008),
        (0.004, 0.022, 0.0155), black, 0.0008)

for head in LAYOUT["heads"]:
    x = head["x"]
    name = "Parscan S · " + head["station"]
    pivot = blender((x, -0.058, 0))
    axis = (blender(head["aim"]) - blender(LAYOUT["mount"]) - pivot).normalized()
    lateral = Vector((0, 0, 1)).cross(axis).normalized()
    mount = Vector((x, 0, -0.019))
    box(name + " · 48V adapter", mount, (0.079, 0.021, 0.014), black, 0.0026)
    neck = pivot + Vector((0, 0, 0.029))
    rod(name + " · yaw joint", mount, neck, 0.008, edge)
    rod(name + " · flush bracket shoulder", neck - Vector((0, 0, 0.0057)), neck, 0.0108, black)
    die_cast_arm(name + " · support bracket", pivot, lateral, black)
    rod(name + " · tilt bearing", pivot + lateral * 0.017, pivot + lateral * 0.027, 0.006, edge)
    basis = Matrix((lateral, axis.cross(lateral), axis)).transposed().to_4x4()
    basis.translation = pivot
    optic = empty(name + " · adjustable optical axis", basis)
    housing = lathe(name + " · die-cast cylinder", [(0.026, -0.015), (0.029, -0.0145),
          (0.030, -0.013), (0.030, 0.056), (0.0296, 0.057), (0.027, 0.057)], black, optic)
    bearing_recess(housing, black)
    lathe(name + " · removable lens sleeve", [(0.027, 0.0572), (0.0297, 0.0574),
          (0.030, 0.058), (0.030, 0.0698), (0.0294, 0.071), (0.027, 0.071),
          (0.0261, 0.070), (0.0254, 0.064)], black, optic, hollow=True)
    lathe(name + " · anti-glare bevel", [(0.0254, 0.063), (0.0255, 0.066),
          (0.0249, 0.0658), (0.0229, 0.0617)], recess, optic, hollow=True)
    lathe(name + " · retaining ring", [(0.0235, 0.0606), (0.0236, 0.0650),
          (0.0218, 0.0650), (0.0217, 0.0646), (0.0222, 0.0644)], reflector, optic, hollow=True)
    collimator = [(0.0225, 0.058), (0.0224, 0.0608)]
    for band in range(5):
        r = 0.0220 - band * 0.00150
        z = 0.0608 - band * 0.00032
        collimator.extend([(r, z), (r - 0.00090, z - 0.00048), (r - 0.00110, z - 0.00028)])
    collimator.extend([(0.0143, 0.0593), (0.0126, 0.0591), (0.0108, 0.0604), (0.0082, 0.0614), (0.0048, 0.0620), (0.0026, 0.0622), (0.0001, 0.0623)])
    lathe(name + " · polymer lens", collimator, lens, optic)
    clear_spherolit(name + " · Spherolit exit face", optic, prism)

ARCHIVE.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ARCHIVE / "parscan-minirail.blend"))
bpy.context.view_layer.update()
for mat in (black, edge, recess, reflector, lens, prism):
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.active_material == mat]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    objects[0].name = mat.name
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.scene.objects:
    obj.select_set(obj.type == "MESH")
bpy.ops.export_scene.gltf(filepath=str(ROOT / "public/media/models/parscan-minirail.glb"),
                          use_selection=True, export_format="GLB",
                          export_meshopt_compression_enable=True,
                          export_meshopt_extension="EXT_meshopt_compression")
