import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mesh import write_mesh


def xyz(point):
    x, y, z = point
    return (x, -z, y)


finishes = {
    'alloy': ('ced0cd',.24,.90), 'steel': ('b1b6b6',.25,.88), 'satin': ('bcbec0',.35,.74),
    'graphite': ('343a3c',.46,.28), 'black': ('252726',.59,.06), 'brass': ('af9667',.31,.82),
    'reflector': ('e9e6e0',.40,.21), 'white': ('ebe8e0',.47,.12), 'opal': ('fff2dc',.28,.03),
    'marble': ('dcd9d0',.52,.02), 'violet': ('6d6680',.50,.16), 'red': ('9b5345',.51,.17),
    'glass': ('a9b8b8',.10,.04), 'smoke': ('667579',.17,.10), 'canopy': ('849ca3',.12,.08),
    'linen': ('d7cfc0',.51,.04), 'slate': ('4a647c',.50,.03), 'teal': ('446e60',.50,.04),
    'clay': ('a55f58',.50,.03), 'spool': ('7b8180',.55,.13), 'tube': ('a0a5a4',.44,.03),
    'pei': ('9c8052',.79,.46), 'petg': ('eadfc9',.39,.05), 'shell': ('242526',.69,.08),
    'optic': ('324954',.09,.12), 'back': ('3d403e',.5,.30), 'flash': ('e2dcc0',.39,.02),
}


def finish_material(key):
    material=bpy.data.materials.get(key)
    if material:
        return material
    color, roughness, metal=finishes[key]
    rgba=[((int(color[i:i+2],16)/255+.055)/1.055)**2.4 for i in (0,2,4)]+[1.]
    material=bpy.data.materials.new(key)
    material.diffuse_color=rgba
    material.use_nodes=True
    nodes=material.node_tree.nodes
    shader=nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=rgba
    shader.inputs['Roughness'].default_value=roughness
    shader.inputs['Metallic'].default_value=metal
    if key in ('satin','alloy','steel','brass'):
        anisotropy=shader.inputs.get('Anisotropic') or shader.inputs['Anisotropic IOR Level']
        anisotropy.default_value=.28
    if key in ('glass','smoke','canopy','petg','optic'):
        shader.inputs['Transmission Weight'].default_value=.48 if key=='petg' else .83
        shader.inputs['IOR'].default_value=1.47
    if key=='opal':
        shader.inputs['Emission Color'].default_value=rgba
        shader.inputs['Emission Strength'].default_value=1.6
    if key=='marble':
        image=bpy.data.images.load(str(Path(__file__).resolve().parents[2]/'public/media/materials/carrara.webp'),check_existing=True)
        image.pack()
        tex=nodes.new('ShaderNodeTexImage')
        tex.image=image
        material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
    return material


class Product:
    def __init__(self, name):
        self.name = name
        self.parts = defaultdict(list)

    def surface(self, name, material, verts, faces, smooth=False):
        data = bpy.data.meshes.new(name)
        data.from_pydata([xyz(v) for v in verts], [], faces)
        data.validate()
        data.update()
        uv = data.uv_layers.new(name="Surface")
        for face in data.polygons:
            axis = max(range(3), key=lambda i: abs(face.normal[i]))
            first, second = ((1,2),(0,2),(0,1))[axis]
            for loop_index in face.loop_indices:
                co = data.vertices[data.loops[loop_index].vertex_index].co
                uv.data[loop_index].uv = (co[first]*3.2+.5, co[second]*3.2+.5)
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        for poly in data.polygons:
            poly.use_smooth = smooth
        self.parts[material].append(obj)
        return obj

    def lathe(self, name, material, center, profile, segments=64):
        x, y, z = center
        points = [(x+r*math.cos(i*math.tau/segments), y+h, z+r*math.sin(i*math.tau/segments))
                  for r,h in profile for i in range(segments)]
        faces = [(row*segments+i, (row+1)*segments+i, (row+1)*segments+(i+1)%segments, row*segments+(i+1)%segments)
                 for row in range(len(profile)-1) for i in range(segments)]
        return self.surface(name, material, points, faces, True)

    def rod(self, name, material, start, end, radius, radius_end=None, sides=24):
        a, b = Vector(start), Vector(end)
        v = (b-a).normalized()
        u = v.cross(Vector((0, 0, 1)) if abs(v.z)<0.8 else Vector((1,0,0))).normalized()
        w = v.cross(u)
        radii = (radius, radius if radius_end is None else radius_end)
        verts = [origin + r*(u*math.cos(i*math.tau/sides) + w*math.sin(i*math.tau/sides)) 
                 for origin,r in zip((a,b),radii) for i in range(sides)]
        faces = [(i, (i+1)%sides, (i+1)%sides+sides, i+sides) for i in range(sides)]
        obj = self.surface(name, material, verts, faces+[tuple(reversed(range(sides))),tuple(range(sides,sides*2))],True)
        obj.data.polygons[-1].use_smooth = obj.data.polygons[-2].use_smooth = False
        return obj

    def block(self, name, material, center, size, radius):
        bpy.ops.mesh.primitive_cube_add(size=1, location=xyz(center))
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = (size[0], size[2], size[1])
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = obj.modifiers.new("Machined edge", "BEVEL")
        bevel.width = radius
        bevel.segments = 3
        bevel.harden_normals = True
        obj.modifiers.new("Planar normals", "WEIGHTED_NORMAL")
        self.parts[material].append(obj)
        return obj

    def export(self, directory):
        collection=bpy.data.collections.new(self.name)
        bpy.context.scene.collection.children.link(collection)
        for material, objects in self.parts.items():
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.convert(target='MESH')
            bpy.ops.object.join()
            obj = bpy.context.object
            obj.name = self.name + '-' + material
            mat = finish_material(material)
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            result = write_mesh(obj, directory / (obj.name + '.mesh'))
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            collection.objects.link(obj)
            print(obj.name, result)
