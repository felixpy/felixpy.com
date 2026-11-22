import math
import runpy
from pathlib import Path

import bpy
from mathutils import Vector


root = Path(__file__).resolve().parents[2]
item = root / ".references/02-家具与灯具/柜内与陈列照明/Corporate Friends C1-mini-LC/Blender"
item.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
finish = runpy.run_path(str(Path(__file__).with_name("vitrine-sculpt.py")))["finish"]
black = finish("Black anodised aluminium", "353431", 0.78, 0.31)
edge = finish("Machined anodised edges", "45433e", 0.72, 0.29)
inside = finish("Blackened optical baffle", "181714", 0.18, 0.77)
steel = finish("Stainless hinge pin", "918e87", 0.94, 0.28)
rail_contact = finish("Nickel-plated contact rail", "aaa69b", 0.89, 0.36)
reflector = finish("Faceted aluminium reflector", "d0c9b7", 0.91, 0.15)
lens = finish("C1-mini warm white collimator", "fff0d2", 0.13, 0.18, 0.35, 1.8)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"


def empty(name, pos=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.empty_display_size = 0.002
    obj.parent = parent
    obj.location = Vector(pos) * 0.001
    return obj


def cube(name, center, dims, mat, parent, radius=0.25):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = Vector(dims) * 0.001
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.location = Vector(center) * 0.001
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("Milled edge radius", "BEVEL")
    bevel.width = radius * 0.001
    bevel.segments = 3
    obj.modifiers.new("Planar normals", "WEIGHTED_NORMAL")
    return obj


def turn(name, profile, mat, parent, pos=(0, 0, 0), segments=48):
    verts = []
    for radius, z in profile:
        if radius == 0:
            verts.append([(0, 0, z * 0.001)])
        else:
            verts.append([(radius * math.cos(i * math.tau / segments) * 0.001,
                           radius * math.sin(i * math.tau / segments) * 0.001,
                           z * 0.001) for i in range(segments)])
    faces = []
    start = 0
    for first, second in zip(verts, verts[1:]):
        stop = start + len(first)
        for i in range(segments):
            j = (i + 1) % segments
            ids = [start + i % len(first), start + j % len(first), stop + j % len(second), stop + i % len(second)]
            faces.append(tuple(dict.fromkeys(ids)))
        start = stop
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([v for ring in verts for v in ring], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = Vector(pos) * 0.001
    for poly in mesh.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.8 and segments > 12
    mesh.materials.append(mat)
    return obj


rail = empty("C1 magnetic rail")
cube("Track extrusion back", (0, 0, -0.7), (1050, 10.2, 1.4), black, rail)
for sign in (-1, 1):
    cube("Track side return", (0, sign * 4.48, -4.25), (1050, 1.24, 6.1), black, rail, 0.16)
    cube("Captured rail contact", (0, sign * 2.85, -4.15), (1048, 0.84, 0.72), rail_contact, rail, 0.14)
    cube("Flush end cap", (sign * 524.1, 0, -4.1), (1.8, 9.8, 6.1), inside, rail)

fixture = empty("C1 magnetic shoe")
fixture.location.z = -0.0073
cube("Magnetic track foot", (0, 0, 1.9), (16.9, 6.9, 4), inside, fixture, 0.35)
cube("Adapter housing", (0, 0, -3.0), (18.0, 12.95, 6), black, fixture, 0.56)
swivel = empty("C1 pan", (0, 0, -6.0), fixture)
turn("Turntable bearing", [(0,-1.1),(5.45,-1.1),(5.75,-0.8),(5.75,-0.3),(5.45,0),(0,0)], edge, swivel)
cube("Hinge cheek", (-2.95, 0, -7.85), (6.9, 17.85, 14.2), black, swivel, 0.7)
tilt = empty("C1 tilt", (0, 0, -9.8), swivel)
pivot = turn("Pivot shoulder screw", [(0,-3.72),(2.41,-3.72),(2.75,-3.57),(2.75,-3.1),(2.41,-2.98),(0,-2.98)], steel, tilt, (-2.91,0,0))
pivot.rotation_euler.y = math.pi / 2
socket = turn("Hex recess", [(0,-3.74),(1.24,-3.74),(1.26,-3.72)], inside, tilt, (-2.91,0,0), 6)
socket.rotation_euler.y = math.pi / 2
stem = turn("Cantilever trunnion", [(0,0),(2.05,0),(2.05,8.0),(1.85,8.4),(0,8.4)], edge, tilt)
stem.rotation_euler.y = math.pi / 2
head = empty("C1 head", (6.78, 0, 0), tilt)
turn("Head barrel", [(0,-12.55),(6.66,-12.55),(6.98,-12.26),(6.98,4.95),(6.72,5.44),(0,5.44)], black, head)
turn("Optic retaining ring", [(4.95,-12.94),(6.78,-12.94),(6.94,-12.76),(6.94,-12.43),(5.02,-12.43),(4.95,-12.94)], edge, head)
turn("Anti-glare tube A300016", [(5.98,-19.8),(6.78,-19.8),(6.99,-19.53),(6.99,-12.9),(6.81,-12.73),(5.98,-12.73),(5.98,-19.8)], black, head)
turn("Recessed flocked throat", [(4.78,-12.91),(5.95,-19.8),(6.00,-19.8),(6.00,-12.85),(4.78,-12.91)], inside, head)
turn("Recessed specular reflector", [(2.72,-12.73),(4.97,-12.99),(4.97,-12.84),(2.72,-12.73)], reflector, head, segments=32)
turn("Plano convex optic", [(0,-13.27),(1.5,-13.22),(2.72,-13.06),(3.5,-12.80),(0,-12.76)], lens, head)
pupil = empty("C1 exit pupil", (0, 0, -13.27), head)
light = bpy.data.lights.new("C1-mini-LC · 3000 K / 45°", "SPOT")
light.energy = 0.20
light.use_temperature = True
light.temperature = 3000
light.spot_size = math.radians(54)
light.spot_blend = 0.37
light.shadow_soft_size = 0.0035
source = bpy.data.objects.new("Collimator photometry", light)
scene.collection.objects.link(source)
source.parent = pupil

tilt.rotation_euler.x = math.radians(34)
fixture.location.x = 0.20
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_rotation = Vector((0.92, 1.2, 0.60)).to_track_quat("-Z", "Y")
            view.region_3d.view_distance = 0.095
            view.region_3d.view_location = (0.20, 0, -0.019)
            view.clip_start = 0.0005
            view.shading.type = "MATERIAL"
            view.overlay.show_overlays = False
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(item / "c1-mini-lc.blend"), compress=True)
tilt.rotation_euler.x = 0
fixture.location.x = 0
bpy.ops.export_scene.gltf(filepath=str(root / "public/media/models/c1-mini-lc.glb"), export_format="GLB",
                          export_animations=False, export_lights=False, export_apply=True, export_yup=True, export_normals=True,
                          export_meshopt_compression_enable=True, export_meshopt_extension="EXT_meshopt_compression")
