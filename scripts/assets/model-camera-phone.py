import math
import runpy
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import noise, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from product_workshop import Product

root = Path(__file__).resolve().parents[2]
out = root/'public/media/models/handheld'
bpy.ops.wm.read_factory_settings(use_empty=True)


def phone():
    p=Product('iphone18')
    def shell(name,material,cx,cy,width,height,r,z0,z1):
        profiles=[(z0,.0006),(z0+.00023,.0002),(z0+.00062,0),(z1-.00062,0),(z1-.00023,.0002),(z1,.0006)]
        profiles=sorted(profiles) if z1-z0>.0013 else [(z0,.00022),(z0+.00012,0),(z1-.00012,0),(z1,.00022)]
        verts=[]
        for z,edge in profiles:
            for k in range(4):
                a0=k*math.pi/2
                ox=(width/2-r)*(1 if k in (0,3) else -1)
                oy=(height/2-r)*(1 if k in (0,1) else -1)
                for i in range(13):
                    a=a0+i*math.pi/24
                    verts.append((cx+ox+(r-edge)*math.cos(a),cy+oy+(r-edge)*math.sin(a),z))
        n=52
        faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profiles)-1) for i in range(n)]
        faces.extend([tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))])
        o=p.surface(name,material,verts,faces,True)
        o.data.polygons[-1].use_smooth=o.data.polygons[-2].use_smooth=False
    shell('Anodised unibody','alloy',0,0,.078,.1634,.012,-.0043,.00415)
    shell('Ceramic Shield front','glass',0,0,.0772,.1624,.0117,.0039,.00445)
    shell('Rear glass inset','back',0,-.022,.0742,.111,.0107,-.00475,-.00416)
    shell('Raised camera plateau','alloy',0,.0553,.0744,.0446,.0106,-.0083,-.0040)
    for x,y in [(.024,.067),(.0078,.0553),(.024,.0435)]:
        for z0,z1,r,m in [(-.008,-.0105,.00865,'alloy'),(-.0105,-.0111,.00778,'glass'),(-.0111,-.0113,.0051,'optic')]:
            p.rod('Camera barrel',m,(x,y,z0),(x,y,z1),r,sides=48)
    for y,r,m in [(.067,.00315,'flash'),(.048,.00265,'glass'),(.057,.00082,'glass')]:
        p.rod('Rear sensor',m,(-.0248,y,-.0083),(-.0248,y,-.00865),r)
    for x,y,l in [(-.039,.043,.007),(-.039,.024,.012),(-.039,.008,.012),(.039,.017,.018),(.039,-.041,.014)]:
        p.block('Side control','alloy',(x,y,0),(.0012,l,.0032),.0005)
    for x in [-.019,-.016,-.013,-.010,.010,.013,.016,.019]:
        p.rod('Speaker perforation','glass',(x,-.0817,0),(x,-.08182,0),.00068,sides=12)
    p.block('USB-C','glass',(0,-.08176,0),(.0089,.0004,.0027),.00018)
    p.export(out)


def marble():
    size=512
    image=bpy.data.images.new('Honed Carrara',width=size,height=size,alpha=False)
    pixels=[]
    for y in range(size):
        for x in range(size):
            p=Vector((x/size*4,y/size*4,.65))
            cloud=noise.noise_vector(p*1.3)[0]*.17+noise.noise_vector(p*4.7)[1]*.035
            phase=p.x*.56+p.y*.91+noise.noise_vector(p*.52)[0]*.84+cloud
            vein=min(1,abs(math.sin(phase*math.pi))/.092)
            grain=noise.noise_vector(p*27)[0]*.012
            value=.84-(1-vein)**1.6*.29+cloud*.19+grain
            pixels.extend([value,value-.011,value-.021,1])
    image.pixels.foreach_set(pixels)
    image.filepath_raw=str(root/'.review/atelier/carrara.png')
    image.file_format='PNG'
    image.save()


phone()
hood_script = Path(__file__).with_name("hb117.py")
subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(hood_script)], check=True)
with bpy.data.libraries.load(str(runpy.run_path(str(hood_script))["source"])) as (library, loaded):
    loaded.collections = ["HB-117 service parts"]
bpy.context.scene.collection.children.link(loaded.collections[0])
marble()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'.review/atelier/handheld-masters.blend'))
