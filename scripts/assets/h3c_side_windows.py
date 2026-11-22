import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

from product_workshop import finish_material


def sheet(part, name, finish, side, depth, boundary, openings=()):
    points, edges = [], []
    for loop in (boundary, *openings):
        offset = len(points)
        points.extend(Vector(p) for p in loop)
        edges.extend((offset + i, offset + (i + 1) % len(loop)) for i in range(len(loop)))
    vertices, _, triangles, *_ = delaunay_2d_cdt(points, edges, [], 0, 1e-8)

    def inside(point, loop):
        return all((b[0] - a[0]) * (point.y - a[1]) >= (b[1] - a[1]) * (point.x - a[0]) - 1e-10
                   for a, b in zip(loop, loop[1:] + loop[:1]))

    faces = []
    for tri in triangles:
        center = sum((vertices[i] for i in tri), Vector((0, 0))) / 3
        if inside(center, boundary) and not any(inside(center, cut) for cut in openings):
            faces.append(tuple(reversed(tri)) if side > 0 else tri)
    return part.surface(name, finish, [(side * depth, y, z) for z, y in vertices], faces)


def reveal(part, name, finish, side, profiles):
    rings = [[(side * x, y, z) for z, y in loop] for x, loop in profiles]
    n = len(rings[0])
    faces = [(a * n + i, a * n + (i + 1) % n, (a + 1) * n + (i + 1) % n, (a + 1) * n + i)
             for a in range(len(rings) - 1) for i in range(n)]
    return part.surface(name, finish, [p for ring in rings for p in ring],
                        faces if side < 0 else [face[::-1] for face in faces])


def build_windows(part, rectangle):
    for side, name in ((1, 'Right'), (-1, 'Left')):
        prefix = 'H3C side window · ' + name
        def window(w, h, r):
            return rectangle(-.039, .486, w, h, r, 8)

        aperture = window(.378, .144, .010)
        gasket = window(.374, .140, .0089)
        clear = window(.369, .135, .0075)
        liner = window(.355, .123, .006)
        outside = [(-.258,.013),(.242,.013),(.242,.585),(-.258,.585)]
        inside = [(-.264,.014),(.192,.014),(.192,.556),(-.264,.556)]
        sheet(part, prefix+' · aluminium surround', 'alloy', side, .2465, outside, [aperture])
        sheet(part, prefix+' · inner chamber liner', 'graphite', -side, -.225, inside, [liner])
        reveal(part, prefix+' · pressed return', 'alloy', side,
               [(.2465, aperture),(.2459, window(.3768,.1428,.0095)),(.2442,gasket)])
        reveal(part, prefix+' · rubber gasket', 'black', side,
               [(.2442,gasket),(.24565,gasket),(.2460,clear),(.2440,clear)])
        reveal(part, prefix+' · dark window reveal', 'graphite', side, [(.2440,clear),(.225,liner)])
        slots = [rectangle(.076 + i * .0105, .535, .004, .022, .0015, 5) for i in range(6)]
        sheet(part, prefix+' · smoked pane', 'smoke', side, .2441, clear, slots)
        for i, slot in enumerate(slots):
            reveal(part, prefix+f' · slot {i+1}', 'graphite', side, [(.2423,slot),(.2441,slot)])
        for z in (-.213, .135):
            for y in (.4315, .5405):
                part.rod(prefix+' · retainer bezel','black',(side*.2436,y,z),(side*.2455,y,z),.0034,.0031,24)
                part.rod(prefix+' · retainer cap','graphite',(side*.2455,y,z),(side*.2459,y,z),.0025,.0022,24)


def save_windows(part, path):
    collection = bpy.data.collections.new('H3C · left and right side windows')
    scene = bpy.data.scenes.new('H3C side windows')
    scene.collection.children.link(collection)
    for finish, objects in part.parts.items():
        for obj in objects:
            if obj.name.startswith('H3C side window ·'):
                obj.data.materials.append(finish_material(finish))
                collection.objects.link(obj)
    bpy.data.libraries.write(str(path), {scene}, fake_user=True, compress=True)
    bpy.data.scenes.remove(scene)
    bpy.data.collections.remove(collection)
