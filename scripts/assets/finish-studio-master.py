import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector

root=Path(__file__).resolve().parents[2]
review=root/'.review/atelier'
master_only='--master-only' in sys.argv
if master_only:
    review=Path(sys.argv[sys.argv.index('--master-only')+1]).resolve()
waterfront=runpy.run_path(str(Path(__file__).with_name('studio-waterfront.py')))
if '--update-window' in sys.argv:
    arguments=sys.argv[sys.argv.index('--update-window')+1:]
    if not 1 <= len(arguments) <= 3:
        raise ValueError('Expected --update-window <waterfront.glb> [source.blend] [output.blend]')
    master=Path(arguments[1]) if len(arguments)>1 else review/'felix-studio.blend'
    destination=Path(arguments[2]) if len(arguments)>2 else master
    waterfront['update_window'](master,arguments[0],destination)
    raise SystemExit(0)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(review/'studio-master.glb'))
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.length_unit='METERS'
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.render.resolution_x=1600
scene.render.resolution_y=1000
scene.render.resolution_percentage=100


def view_point(x,y,z):
    return Vector((x,-z,y))


def camera(name,eye,target,lens):
    data=bpy.data.cameras.new(name)
    data.lens=lens
    cam=bpy.data.objects.new(name,data)
    scene.collection.objects.link(cam)
    cam.location=view_point(*eye)
    cam.rotation_euler=(view_point(*target)-cam.location).to_track_quat('-Z','Y').to_euler()
    return cam


scene.camera=camera('Desk | seated',(-.135,1.36,1.49),(-.135,1.216,-.246),24)
camera('Workshop | side',(.97,1.31,.81),(2.20,1.16,.64),28)
camera('Cabinet | rear',(-.135,1.36,1.49),(-.135,1.22,3.12),24)
waterfront['configure_window'](scene,waterfront['find_plate'](scene.objects))
world=bpy.data.worlds.new('Daylight studio')
world.use_nodes=True
sky=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
environment=root/'public/media/lighting/desk-day.hdr'
if environment.exists():
    sky.image=bpy.data.images.load(str(environment))
    sky.image.pack()
    world.node_tree.links.new(sky.outputs['Color'],world.node_tree.nodes['Background'].inputs['Color'])
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
scene.world=world
for object in scene.objects:
    if object.type=='MESH' and object.get('studioOccluder') is not None:
        object['studioOccluder']=bool(object['studioOccluder'])
runpy.run_path(str(Path(__file__).with_name('movable-camp-gear.py')))['exclude_from_static_lighting'](scene)
scene.render.image_settings.file_format='PNG'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(review/'felix-studio.blend'),compress=True)
if master_only:
    raise SystemExit(0)

runpy.run_path(str(Path(__file__).with_name('bake-room-visibility.py')))
