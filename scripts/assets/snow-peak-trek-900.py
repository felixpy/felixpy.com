import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def pressed_pot_wire(shape, points, radius, material, sides):
    rows = []
    for i, p in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]).normalized()
        radial = Vector((p.x, 0, p.z)).normalized()
        face = (radial - tangent * radial.dot(tangent)).normalized()
        width = tangent.cross(face).normalized()
        if abs(p.z) > 42:
            t = min(1.0, max(0.0, (p.y - 52.0) / 3.0), max(0.0, (75.0 - p.y) / 3.5))
            press = t * t * (3 - 2 * t)
        else:
            press = 0
        half_width = radius + (2.43 - radius) * press
        half_thickness = radius + (0.88 - radius) * press
        exponent = 1 - 0.43 * press
        ring = []
        for j in range(sides):
            c = math.cos(math.tau * j / sides)
            s = math.sin(math.tau * j / sides)
            ring.append(p + width * half_width * math.copysign(abs(c) ** exponent, c)
                          + face * half_thickness * math.copysign(abs(s) ** exponent, s))
        rows.append(ring)
    shape.rings(rows, material)


def build(Sculpture, curve, titanium, wire, polished, source=None):
    collection = bpy.data.collections.new("Snow Peak SCS-008T · Titanium Trek 900")
    bpy.context.scene.collection.children.link(collection)

    def mount(name, assembly):
        obj = bpy.data.objects.new(name, None)
        collection.objects.link(obj)
        obj.empty_display_size = 0.015
        obj["trekAssembly"] = assembly
        return obj

    pot = mount("Snow Peak SCS-008T · Trek 900 pot", "pot")
    pan = mount("Snow Peak SCS-008T · Trek 900 pan lid", "pan")
    pan.parent = pot
    pan.location.z = 0.135
    pan.rotation_euler.x = math.pi

    def part(shape, parent, joint=None):
        obj = shape.finalize(uv_scale=35)
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.parent = parent
        obj["trekPart"] = shape.name
        if joint:
            x, h, d = joint
            pivot = Vector((x, -d, h)) / 1000
            obj.data.transform(Matrix.Translation(-pivot))
            obj.location = pivot
        return obj

    shell = Sculpture("SCS-008T 01 · deep-drawn pot and rolled lip")
    profile = [
        (0, .01), (0, 52.7), (.35, 54.5), (1.05, 56), (2.2, 57.25),
        (4.0, 58.02), (6.3, 58.4), (10, 58.45), (102.7, 58.52),
        (104.1, 58.8), (104.7, 59.55), (105.35, 59.94), (106, 60),
        (106.65, 59.7), (107, 59.15), (106.98, 58.65),
        (106.62, 58.15), (105.8, 58.00), (104.6, 58.08),
        (102.7, 58.06), (10, 58.0), (6.4, 57.96), (4.15, 57.6),
        (2.55, 56.83), (1.55, 55.56), (.87, 53.75), (.65, 51), (.65, .01),
    ]
    shell.turn(profile, titanium, 128)
    part(shell, pot)

    bracket = Sculpture("SCS-008T 02 · spot-welded butterfly hinge plate")
    axis_x, span, bore = 60.68, 10.7, 1.92

    def wrap(d, h, relief=0):
        a = d / 58.48
        return ((58.48 + relief) * math.cos(a), h, (58.48 + relief) * math.sin(a))

    def skin(bounds):
        rows = []
        for d, bottom, top in bounds:
            rows.append([wrap(d, bottom, .08), wrap(d, bottom, .72), wrap(d, top, .72), wrap(d, top, .08)])
        bracket.rings(rows, titanium, True)

    skin([(-10.7,23.8,82.6),(-8.5,24.6,82.2),(-6.4,26.4,79.6),(-4.0,27.1,78.8),
          (4.0,27.1,78.8),(6.4,26.4,79.6),(8.5,24.6,82.2),(10.7,23.8,82.6)])
    for sign in (-1,1):
        skin(sorted([(sign*d,b,t) for d,b,t in [(11,23.8,82.6),(13.8,23.9,82.5),(16.5,24.15,82.25),(17.35,25.0,81.3)]]))
        rings = []
        for i in range(37):
            a = math.radians(-72 + 317 * i / 36) * sign
            rings.append([
                (axis_x+r*math.cos(a), h, sign*span+r*math.sin(a))
                for r,h in [(bore,23.8),(bore+.52,23.8),(bore+.52,82.6),(bore,82.6)]
            ])
        bracket.rings(rings,titanium)

    for d,h in [(side*15.14,hh) for side in (-1,1) for hh in (30.3,52.0,76.0)] + [(0,39.0),(0,69.3)]:
        rows = []
        for radius,depth in [(1.20,.70),(.96,.84),(.71,.89),(.45,.80),(.16,.77)]:
            rows.append([wrap(d+radius*math.cos(i*math.tau/20),h+radius*math.sin(i*math.tau/20),depth) for i in range(20)])
        bracket.rings(rows,titanium,True,False)
    part(bracket, pot)

    for sign, side in [(-1,"near"),(1,"far")]:
        arm = Sculpture("SCS-008T 03 · folding " + side + " pot handle")
        points = [(axis_x,30,span),(axis_x,23.2,span),(axis_x+.5,21.5,span),
                  (axis_x,20.5,span+2.8),(59.4,19.9,18.3),(55,17.8,28.8),
                  (48.2,15.5,39.6),(40.2,15,48.1),(35.4,17.4,51.5),
                  (34.0,27.2,52.5),(35.0,43,52.15),(38.1,62,50.6),
                  (42.6,78.4,47.2),(47.4,85.4,42.1),(52.0,87.0,36.5),
                  (57.5,85.9,26.8),(60.1,85.15,17.3),(axis_x,85.3,span+2.6),
                  (axis_x+.1,84.3,span),(axis_x,82.5,span),(axis_x,75.8,span)]
        curve(arm, [(x,h,sign*d) for x,h,d in points], 1.56, wire, 20, pressed_pot_wire)
        obj = part(arm,pot,(axis_x,0,sign*span))
        obj["hingeAxis"] = "Z"

    marks = Sculpture("SCS-008T 04 · inward-reading litre and ounce dies")
    for centre,levels,high in [(0,[(29,"0.3"),(57,"0.6"),(95,"1.0")],95),
                               (22,[(28.5,"10"),(56,"20"),(83.5,"30"),(97,"35oz")],97)]:
        for inside in (True,False):
            radius = 57.93 if inside else 58.59
            def project(u,h):
                a = (centre-u)/58.48+0.015
                return (radius*math.sin(a),h,radius*math.cos(a))
            for height,txt in levels:
                marks.label(txt,4.0,lambda x,y,h=height:project(x,h+2.55+y),titanium)
                curve(marks,[project(x,height) for x in (-4,-2,0,2,4)],.20,titanium,8)
            curve(marks,[project(-4,levels[0][0]),project(-4,high)],.16,titanium,8)
    part(marks,pot)

    lid = Sculpture("SCS-008T 05 · drawn frying pan and nesting shoulder")
    lid.turn([(0,.01),(0,50),(.45,52.8),(1.65,54.6),(3.0,55.6),(5,56.2),
              (24,58.6),(25.3,58.95),(26.4,59.7),(27.7,61.15),(28.8,61.55),
              (34.7,62.1),(36.2,62.35),(36.8,63.35),(37.2,63.85),(38,64),
              (38.6,63.75),(39,63.05),(38.9,62.55),(38.3,62.1),(37.3,61.95),
              (35.5,61.7),(29.0,61.08),(28,60.8),(26.7,59.37),(25.8,58.6),
              (24,58.15),(5.1,55.76),(3.25,55.1),(1.98,54.05),(.95,52.18),(.56,50),(.56,.01)],titanium,128)
    part(lid,pan)
    ears = Sculpture("SCS-008T 06 · pan handle clevis and curled eyes")
    plate = [(56.85,7,-13),(58.17,23,-13),(58.18,23,13),(56.85,7,13)]
    ears.rings([plate,[(x+.67,h,d) for x,h,d in plate]],titanium,True)
    for sign in (-1,1):
        slot = []
        for r in (2.05,2.70):
            for d in ([sign*9.8,sign*14.9] if r==2.05 else [sign*14.9,sign*9.8]):
                slot.append([(59.9+r*math.cos(a*math.tau/32),18+r*math.sin(a*math.tau/32),d) for a in range(32)])
        ears.rings(slot+[slot[0]],titanium,True,False)
        ears.form((57.5,11.0,sign*8.4),(1.13,1.28,1.28),polished)
    part(ears,pan)
    bail=Sculpture("SCS-008T 07 · single bent pan bail")
    half=[(59.9,18,10.15),(59.9,18,14.55),(60.9,17,16.1),(60.75,13.6,16.1),
          (58.6,4.0,15.2),(56.0,-.45,15.0),(52,-1.85,14.9),
          (12,-1.9,13.6),(-10,-1.90,12.0),(-15.2,-1.80,10.3),(-17.3,-1.76,6.2)]
    control=half+[(-17.5,-1.76,0)]+[(x,h,-d) for x,h,d in reversed(half)]
    curve(bail,control,1.56,wire,16)
    ob=part(bail,pan,(59.9,18,0))
    ob["hingeAxis"]="Y"
    if source:
        native = bpy.data.scenes.new("Snow Peak Trek 900 · packed position")
        native.unit_settings.system = "METRIC"
        native.collection.children.link(collection)
        path = Path(source)
        path.parent.mkdir(exist_ok=True,parents=True)
        bpy.data.libraries.write(str(path), {native}, fake_user=True, compress=True)
        bpy.data.scenes.remove(native)
    pot.location=(.100,-.155,1.075)
    pot.rotation_euler.z=-.45
    return pot
