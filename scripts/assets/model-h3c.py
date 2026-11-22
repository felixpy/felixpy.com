import math
import runpy
import sys
import gzip
import struct
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product, finishes
from h3c_enclosure import build_enclosure
from h3c_ams3h import editable_source
from h3c_side_windows import save_windows

root = Path(__file__).resolve().parents[2]
out = root / '.review/atelier/h3c-components'
bpy.ops.wm.read_factory_settings(use_empty=True)
frame = Product('frame')


finishes['canopy'] = ('373e42', .13, .08)
finishes['smoke'] = ('252b2d', .16, .10)
finishes['web'] = ('767b7b', .48, .09)
finishes['spool'] = ('565d5e', .51, .13)
build_enclosure(frame)
out.mkdir(parents=True, exist_ok=True)
editable_source(frame, out)
window_source = root / '.references/06-工坊与工具/三维打印与模型/Bambu Lab H3C/Blender/h3c-side-windows.blend'
window_source.parent.mkdir(parents=True, exist_ok=True)
save_windows(frame, window_source)
frame.export(out)

bed=Product('bed')
bed.block('Magnetic heated bed','graphite',(0,-.0107,0),(.350,.018,.338),.003)
bed.block('Magnetic interface','black',(0,-.0014,0),(.328,.0006,.318),.00022)
bed.block('Spring steel build plate','pei',(0,-.00055,0),(.330,.0011,.320),.00045)
bed.block('Removable plate tab','pei',(0,-.00055,.164),(.056,.0011,.008),.00045)
for x in [-.181,.181]:
    bed.block('Bed carriage','black',(x,-.016,0),(.025,.026,.375),.002)
bed.export(out)

gantry=Product('gantry')
for off in [-.009,.009]:
    gantry.rod('X axis linear guide','steel',(-.194,.044,off),(.194,.044,off),.0044,sides=24)
gantry.block('Carbon crossbeam','graphite',(0,.048,-.002),(.393,.018,.015),.0018)
for s in [-1,1]:
    gantry.block('Y carriage','black',(s*.193,.046,0),(.022,.029,.048),.0025)
gantry.export(out)
head=Product('head')
head.block('Tool coupler','graphite',(0,.046,0),(.043,.049,.040),.006)
head.block('Front fan housing','black',(0,.042,.017),(.039,.035,.010),.004)
head.rod('Radial blower intake','graphite',(0,.043,.023),(0,.043,.024),.012,sides=32)
for n in range(9):
    angle = n * math.tau/9
    head.rod('Blower protective grille','black',(.003*math.cos(angle),.043+.003*math.sin(angle),.0247),
             (.0116*math.cos(angle+.23),.043+.0116*math.sin(angle+.23),.0247),.00074,sides=8)
head.rod('Blower hub','graphite',(0,.043,.024),(0,.043,.0255),.0036,sides=24)
for x in [-.0185,.0185]:
    head.rod('Coupler retaining guide','steel',(x,.032,.006),(x,.060,.006),.0021,sides=18)
head.rod('Guide tube entry collar','graphite',(0,.069,0),(0,.074,0),.0056,sides=20)
head.rod('Feed collet','satin',(0,.0738,0),(0,.075,0),.004,sides=20)
head.rod('Ceramic heater','graphite',(0,.028,0),(0,.008,0),.008,.004)
head.rod('Hardened steel nozzle','steel',(0,.009,0),(0,0,0),.004,.00035)
head.export(out)

bundle=bytearray(b'BPK1')
paths = [out / f'{product.name}-{finish}.mesh' for product in [frame,bed,gantry,head] for finish in product.parts]
for path in sorted(paths):
    key=path.stem.encode('utf-8')
    binary=path.read_bytes()
    bundle.extend(struct.pack('<BI',len(key),len(binary))+key+binary)
(root / 'public/media/models/h3c.mesh.gz').write_bytes(gzip.compress(bundle, compresslevel=9, mtime=0))
material = bpy.data.materials['web']
tree = material.node_tree
y,x = np.mgrid[:384,:384] - 191.5
r = np.hypot(x,y)
theta = np.arctan2(y,x)/math.tau
pixels = np.ones((384,384,4),dtype=np.float32)
pixels[:,:,:3] = [.80,.81,.76]
for band in [92,111,130,149,168]:
    count = int(band/3)
    arc = np.abs((theta*count - (band%2)*.5 + .5)%1 - .5) * math.tau * band/count
    dx,dy = np.maximum(np.abs(r-band)-4.2,0),np.maximum(arc-3.3,0)
    pixels[:,:,3] *= np.clip(np.hypot(dx,dy)-1.45,0,1)
weave=bpy.data.images.new('Reusable spool flange cutouts',width=384,height=384,alpha=True)
weave.pixels.foreach_set(pixels.ravel())
weave.pack()
texture=tree.nodes.new('ShaderNodeTexImage')
texture.image=weave
shader=tree.nodes['Principled BSDF']
tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
for finish in ['linen','slate','teal','clay']:
    tree=bpy.data.materials[finish].node_tree
    uv=tree.nodes.new('ShaderNodeTexCoord')
    split=tree.nodes.new('ShaderNodeSeparateXYZ')
    tree.links.new(uv.outputs['UV'],split.inputs[0])
    step=tree.nodes.new('ShaderNodeMath')
    step.operation='MULTIPLY'
    step.inputs[1].default_value=35*math.tau
    tree.links.new(split.outputs[0],step.inputs[0])
    helix=tree.nodes.new('ShaderNodeMath')
    helix.operation='COSINE'
    tree.links.new(step.outputs[0],helix.inputs[0])
    bump=tree.nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value=.00022
    tree.links.new(helix.outputs[0],bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'],tree.nodes['Principled BSDF'].inputs['Normal'])
runpy.run_path(str(Path(__file__).with_name("fit-whale-print.py")))["fit"](bpy.context.scene)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'.review/atelier/h3c-master.blend'))
