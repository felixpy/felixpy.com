from math import cos, pi, sin
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def make_ferry():
    vertices, faces, materials, slots = [], [], [], []

    def material(name, color, metallic=0.0):
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*color, 1)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = 0.43
        materials.append(mat)
        return len(materials) - 1

    hull = material("Marine blue enamel", (0.037, 0.105, 0.17))
    bottom = material("Copper antifouling", (0.24, 0.069, 0.04))
    cream = material("Painted aluminum", (0.75, 0.78, 0.74), 0.12)
    deck = material("Deck nonskid", (0.19, 0.223, 0.21))
    rubber = material("Rubber fender", (0.035, 0.041, 0.042))
    glass = material("Cabin glazing", (0.038, 0.092, 0.11), 0.15)
    saloon = [
        material("Saloon panorama glass", (0.13, 0.19, 0.20), 0.16),
        material("Saloon with amber lamps", (0.19, 0.21, 0.20), 0.13),
        material("Quiet saloon", (0.065, 0.12, 0.13), 0.18),
    ]
    stainless = material("Stainless pipe", (0.48, 0.51, 0.5), 0.6)
    red = material("Port red", (0.64, 0.046, 0.028))
    green = material("Starboard green", (0.015, 0.49, 0.17))

    def face(points, index):
        first = len(vertices)
        vertices.extend(points)
        faces.append(tuple(range(first, first + len(points))))
        slots.append(index)

    def loft(lower, upper, wall, roof):
        face(lower[::-1], wall)
        face(upper, roof)
        for i in range(len(lower)):
            j = (i + 1) % len(lower)
            face([lower[i], lower[j], upper[j], upper[i]], wall)

    def cabin(x0, x1, y, z0, z1, rake, wall, roof):
        def loop(a, b, half, z):
            cut = min((b-a)*.13, half*.36, .94)
            return [(a+cut*.5,-half,z),(b-cut,-half,z),(b,-half+cut,z),(b,half-cut,z),
                    (b-cut,half,z),(a+cut*.5,half,z),(a,half-cut*.5,z),(a,-half+cut*.5,z)]
        loft(loop(x0, x1, y, z0), loop(x0+0.08, x1-rake, y-0.04, z1), wall, roof)

    def pipe(start, end, radius, index, sides=6):
        p, q = Vector(start), Vector(end)
        axis = (q-p).normalized()
        u = axis.orthogonal().normalized() * radius
        v = axis.cross(u)
        ring = [u*cos(2*pi*i/sides) + v*sin(2*pi*i/sides) for i in range(sides)]
        loft([p+r for r in ring], [q+r for r in ring], index, index)

    stations = [(-16.2, 2.12, 1.0), (-15, 3.1, .56), (-11.5, 3.55, .12), (-5, 3.78, 0), (7, 3.72, 0), (11.8, 3.15, .18), (14.9, 1.65, .64), (16.9, .085, 1.15)]
    rings = []
    for x, width, rise in stations:
        rings.append([(x,-width,1.43+rise*.46),(x,-width*.96,.05+rise*.45),(x,-width*.56,-1.14+rise),(x,width*.56,-1.14+rise),(x,width*.96,.05+rise*.45),(x,width,1.43+rise*.46)])
    face(rings[0][::-1], hull)
    for a,b in zip(rings,rings[1:]):
        for j,mat in enumerate([hull,bottom,bottom,bottom,hull,deck]):
            k=(j+1)%6
            face([a[j],b[j],b[k],a[k]],mat)
        for j in [0,5]:
            p,q=a[j],b[j]
            pipe((p[0],p[1],p[2]-.31),(q[0],q[1],q[2]-.31),.11,rubber)
    face(rings[-1],hull)
    cabin(-12.8,12,3.07,1.43,2.08,.15,cream,cream)
    cabin(-12.74,11.8,3.04,2.08,3.87,.58,rubber,cream)
    cabin(-13.02,11.91,3.31,3.87,4.09,.10,cream,deck)
    cabin(4,10.38,2.66,4.09,4.65,.11,cream,cream)
    cabin(4.04,10.23,2.63,4.65,6.02,.64,glass,cream)
    cabin(3.86,9.86,2.87,6.02,6.2,.05,cream,cream)
    for side in (-1,1):
        partitions = [-12.1,-10.38,-8.5,-6.31,-4.27,-2.48,-.63,1.26,3.12,5.05,7.17,9.03,10.62]
        shades = [2,0,1,1,0,2,2,0,1,0,2,0]
        for i,(x,right) in enumerate(zip(partitions,partitions[1:])):
            a,b=x+.15,right-.15
            glass_face=[(a,side*3.049,2.26),(b,side*3.049,2.26),(b-.13,side*3.015,3.65),(a-.13,side*3.015,3.65)]
            face(glass_face if side<0 else glass_face[::-1],saloon[shades[i]])
            pipe((x,side*3.063,2.08),(x-.13,side*3.033,3.85),.055,cream)
        for x in [4.5,6.4,8.35]:
            pipe((x,side*2.635,4.65),(x-.11,side*2.641,6.03),.095,cream)
        for z in [4.53,5.03]:
            pipe((-12.45,side*3.12,z),(3.5,side*3.12,z),.05,stainless)
        for x in range(-12,4,2):
            pipe((x,side*3.12,4.09),(x,side*3.12,5.03),.047,stainless)
        for x in [-10,-6.7,-3.4,.2]:
            y=side*1.87
            seat=[(x,y-.61,4.11),(x+.47,y-.61,4.11),(x+.47,y+.61,4.11),(x,y+.61,4.11)]
            loft(seat,[(a,b,4.54) for a,b,_ in seat],deck,cream)
        for x,width in [(-11.5,3.55),(-6.5,3.73),(-1.5,3.75),(3.5,3.73),(8.5,3.55)]:
            pipe((x-.05,side*(width+.12),.53),(x+.13,side*(width+.08),1.31),.14,rubber)
            pipe((x+.13,side*(width+.08),1.31),(x+.25,side*(width-.07),1.47),.025,cream)
        pipe((8.8,side*2.86,5.95),(8.8,side*2.86,6.26),.13,red if side>0 else green)
    pipe((5.9,0,6.2),(5.9,0,7.85),.08,stainless)
    pipe((5.2,0,7.15),(6.65,0,7.15),.06,cream)
    cabin(-8.0,-6.2,.65,4.09,5.22,.23,hull,rubber)
    mesh=bpy.data.meshes.new("Raked steel hull, saloon, flying bridge and rails")
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    obj=bpy.data.objects.new("Thirty-three metre river excursion launch",mesh)
    bpy.context.collection.objects.link(obj)
    for m in materials: mesh.materials.append(m)
    for polygon,index in zip(mesh.polygons,slots): polygon.material_index=index
    width, height = 256, 72
    atlas=bpy.data.images.new("Excursion launch reflected elevations",width,height*2,alpha=True)
    samples=[0.]*(width*height*8)
    hull_tree=BVHTree.FromPolygons(vertices,faces)
    lamps={saloon[0]:(.17,.105,.051),saloon[1]:(.34,.185,.069),saloon[2]:(.025,.031,.032),
           glass:(.031,.038,.042),red:(.84,.025,.016),green:(.009,.66,.12)}
    for row in range(height):
        z=-1.5+(row+.5)*10/height
        for col in range(width):
            x=-17.5+(col+.5)*35/width
            _,normal,index,_=hull_tree.ray_cast((x,-9,z),(0,1,0),18)
            if index is None: continue
            material_id=slots[index]
            paint=materials[material_id].diffuse_color
            sky=.48+.23*max(0.,normal.z)-.12*normal.y
            daylight=tuple(paint[i]*sky for i in range(3))
            dusk=lamps.get(material_id,tuple(c*.093 for c in daylight))
            for frame,radiance in enumerate((dusk,daylight)):
                offset=4*((frame*height+row)*width+col)
                samples[offset:offset+4]=[*radiance,1.]
    atlas.pixels.foreach_set(samples)
    atlas.filepath_raw=str(Path(__file__).resolve().parents[2]/'public/media/panoramas/river-ferry-reflection.png')
    atlas.file_format='PNG'
    atlas.save()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    output=Path(__file__).resolve().parents[2]/'public/media/models/river-ferry.glb'
    output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_yup=True)


make_ferry()
