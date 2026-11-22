import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product
from astral_power import archive_components
from astral_cooling import backplate_details, heatpipe_exits, impeller, mm, rear_bezel, thermal_module

root = Path(__file__).resolve().parents[2]
out = root / 'public/media/models'
bpy.ops.wm.read_factory_settings(use_empty=True)


def section(product, name, finish, polygon, offset, bevel=0):
    a = [Vector(p) for p in polygon]
    n = len(a)
    obj = product.surface(name, finish, a+[v+Vector(offset) for v in a],
        [tuple(range(n))[::-1],tuple(range(n,2*n))]+
        [(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)])
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    if bevel:
        mod = obj.modifiers.new('Edge break','BEVEL')
        mod.width, mod.segments = bevel, 3
        mod.harden_normals = True
        obj.modifiers.new('Planar surfaces','WEIGHTED_NORMAL')
    return obj


def remove_volume(obj, cutter):
    boolean = obj.modifiers.new('Machined opening','BOOLEAN')
    boolean.operation = 'DIFFERENCE'
    boolean.object = cutter
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=boolean.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def cut_screw(part, x, y, z, radius):
    part.rod('Black captive screw collar','black',(x,y,z),(x,y+.00052,z),radius,sides=24)
    part.rod('Countersunk captive Torx head','graphite',(x,y+.00054,z),(x,y+.00073,z),radius*.72,sides=20)
    part.rod('Six point drive','black',(x,y+.00074,z),(x,y+.00082,z),radius*.32,sides=6)


def chip(part,name,finish,center,size):
    x,y,z=center
    w,h,d=[v*.5 for v in size]
    corners=[(x-w,y-h,z-d),(x+w,y-h,z-d),(x+w,y-h,z+d),(x-w,y-h,z+d)]
    return section(part,name,finish,corners,(0,2*h,0))


card = Product('astral-casting')
cutter = Product('negative')
outline=[(-.073,-.172),(-.068,-.178),(.068,-.178),(.074,-.171),
         (.074,.168),(.067,.178),(-.067,.178),(-.074,.169)]
deck=section(card,'Full diecast backplate','graphite',[(x,.0318,z) for x,z in outline],(0,.0045,0))
remove_volume(deck,cutter.rod('Pass-through opening','black',(0,.024,.116),(0,.043,.116),.0565,sides=96))
notch = [
    (-82, 39.6),
    (-73, 39.6),
    (-69.8, 41.6),
    (-55.5, 41.6),
    (-54, 43.1),
    (-54, 64.9),
    (-55.5, 66.4),
    (-69.8, 66.4),
    (-73, 68.4),
    (-82, 68.4),
]
remove_volume(
    deck,
    section(
        cutter,
        "Outer edge power inlet access",
        "black",
        [mm((x, 29, z)) for x, z in notch],
        (0, 0.011, 0),
    ),
)
die_center=-.062
def surround(hx,hz,chamfer):
    return [(a,die_center+b) for a,b in [(-hx,-hz+chamfer),(-hx+chamfer,-hz),(hx-chamfer,-hz),
      (hx,-hz+chamfer),(hx,hz-chamfer),(hx-chamfer,hz),(-hx+chamfer,hz),(-hx,hz-chamfer)]]
retainer=[(-.047,-.037),(.047,-.037),(.047,-.026),(.033,-.026),
          (.030,-.021),(.030,.021),(.033,.026),(.047,.026),(.047,.037),
          (-.047,.037),(-.047,.026),(-.034,.026),(-.030,.021),
          (-.030,-.021),(-.034,-.026),(-.047,-.026)]
remove_volume(deck,section(cutter,'Stamped H bracket access','black',
    [(x*1.05,.022,die_center+z*1.05) for x,z in retainer],(0,.026,0)))
for side in [-1,1]:
    window=[(.012,.169),(.058,.169),(.066,.162),(.066,.150),(.054,.139),
            (.049,.149),(.040,.159),(.029,.166)]
    remove_volume(deck,section(cutter,'Open corners flanking rear fan','black',
        [(side*x,.023,z) for x,z in window],(0,.024,0)))
mod=deck.modifiers.new('Machined chamfers','BEVEL')
mod.width,mod.segments,mod.harden_normals=.00072,3,True
deck.modifiers.new('Broad machined planes','WEIGHTED_NORMAL')

brace=section(card,'Steel spring bracket around the GPU land','black',
              [(x,.032,die_center+z) for x,z in retainer],(0,.0033,0))
remove_volume(brace,section(cutter,'Capacitor land opening','black',
    [(x,.026,z) for x,z in surround(.0208,.0214,.005)],(0,.017,0)))
for side in [-1,1]:
    for end in [-1,1]:
        cut_screw(card,side*.041,.0353,die_center+end*.0314,.0027)
card.block('Exposed dark PCB land','black',(0,.0289,die_center),(.071,.0012,.071),.001)
for row in range(8):
    for col in range(8):
        x=(col-3.5)*.00315
        z=die_center+(row-3.5)*.00305
        chip(card,'GPU power decoupling capacitor','brass',(x,.03019,z),(.00227,.00115,.00140))
        for s in [-1,1]:
            chip(card,'Nickel capacitor end termination','steel',(x+s*.00102,.03023,z),(.00040,.00118,.00141))
for x,z in [(-.061,-.159),(.061,-.159),(.040,.044),(-.039,.043),
            (.0678,.170),(-.0678,.170),(.064,-.012),(-.061,-.104)]:
    cut_screw(card,x,.0364,z,.00265)

ring=[(.0564,.0341),(.0575,.0355),(.0585,.0369),(.0605,.0373),(.0608,.0365),
      (.0606,.0357),(.0584,.0349),(.0564,.0341)]
rear_bezel(card,ring)
thermal_module(card)
backplate_details(card,die_center)
def tail_frame(name, outline):
    vertices = [mm((x*scale, y, z)) for z,scale in ((168,1), (177.4,.925)) for x,y in outline]
    count = len(outline)
    faces = [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    faces += [tuple(reversed(range(count))), tuple(range(count, count*2))]
    return card.surface(name, 'graphite', vertices, faces)


def edge_break(obj, radius):
    bevel = obj.modifiers.new('Broken diecast edges', 'BEVEL')
    bevel.width, bevel.segments, bevel.harden_normals = radius, 3, True
    obj.modifiers.new('Cast planar surfaces', 'WEIGHTED_NORMAL')


upper = tail_frame('Return of backplate with three recessed bores',
                   [(-73,16.4),(73,16.4),(73,31.81),(-73,31.81)])
for x in (2.8, 33.9, 64.4):
    steps = 24
    rings = [(169.6,1.53), (176.85,1.53), (177.58,2.23), (178.5,2.23)]
    bore = [mm((x+r*math.cos(math.tau*i/steps),23.4+r*math.sin(math.tau*i/steps),z))
            for z,r in rings for i in range(steps)]
    faces = [(j*steps+i,j*steps+(i+1)%steps,(j+1)*steps+(i+1)%steps,(j+1)*steps+i)
             for j in range(len(rings)-1) for i in range(steps)]
    faces += [tuple(reversed(range(steps))), tuple(range(len(bore)-steps,len(bore)))]
    remove_volume(upper, cutter.surface('Chamfered blind bore', 'black', bore, faces))
edge_break(upper, .00035)
lower = tail_frame('Intake casting with inset open end',
                   [(-73,-28.51),(73,-28.51),(73,16.24),(62,16.24),(62,-17.1),
                    (60.5,-18.6),(-60.5,-18.6),(-62,-17.1),(-62,16.24),(-73,16.24)])
edge_break(lower, .00055)

last_fin = section(card, 'Punched dark end fin', 'black',
                   [mm((x,y,162.85)) for x,y in [(-63,-17.4),(63,-17.4),(65, -15.4),
                                                  (65,15.8),(63,17.8),(-63,17.8),(-65,15.8),(-65,-15.4)]],
                   (0,0,.00052))
for x,y in heatpipe_exits():
    remove_volume(last_fin, cutter.rod('Pipe opening','black',mm((x,y,162)),mm((x,y,164.5)),.00352,sides=24))
    remove_volume(last_fin, cutter.rod('Forming relief','black',mm((x,y+3.37,162)),mm((x,y+3.37,164.5)),.00155,sides=20))
card.block(
    "FR4 under the board-mounted power inlet",
    "black",
    mm((-49.2, 22.0, 51.8)),
    mm((27.4, 1.58, 34.6)),
    0.0003,
)
inlet = section(
    card,
    "Right-angle board receptacle, mating face toward side glass",
    "black",
    [
        mm((-64.5, y, z))
        for y, z in [
            (21.21, 43.8),
            (10.9, 43.8),
            (10.5, 44.2),
            (10.5, 63.8),
            (10.9, 64.2),
            (21.21, 64.2),
        ]
    ],
    (0.0128, 0, 0),
)
for row in range(2):
    for col in range(6):
        cy, cz = 16.05 + row * 3, 46.5 + col * 3
        chamfer = 0.55 if (row + col) % 2 else 0.08
        key = [
            (-1.35, -1.35),
            (0.95, -1.35),
            (1.35, -0.95),
            (1.35, 1.35),
            (-1.35 + chamfer, 1.35),
            (-1.35, 1.35 - chamfer),
        ]
        remove_volume(
            inlet,
            section(
                cutter,
                "Polarised terminal cavity",
                "black",
                [mm((-66, cy + y, cz + z)) for y, z in key],
                (0.0127, 0, 0),
            ),
        )
        card.block(
            "Setback power terminal",
            "black",
            mm((-56.2, cy, cz)),
            mm((5.6, 0.58, 0.58)),
            0.00008,
        )
remove_volume(
    inlet,
    section(
        cutter,
        "Sideband shelf, facing the cooler",
        "black",
        [
            mm((-66, y, z))
            for y, z in [(11.45, 48.5), (13.95, 48.5), (13.95, 59.5), (11.45, 59.5)]
        ],
        (0.0115, 0, 0),
    ),
)
for z in (51, 53, 55, 57):
    card.block(
        "Shrouded sense contact",
        "black",
        mm((-56.5, 12.65, z)),
        mm((3.8, 0.35, 0.45)),
        0.00008,
    )
edge_break(inlet, 0.00016)
card.block(
    "Board receptacle latch catch",
    "black",
    mm((-62.1, 21.45, 54)),
    mm((2.1, 0.48, 4.8)),
    0.00012,
)
inlet_fin = Product("astral-fin-inlet")
inlet_outline = [
    (-65, -17),
    (-61, -20),
    (-48, -20),
    (-46, -25),
    (47, -25),
    (49, -20),
    (61, -20),
    (66, -15),
    (66, 15),
    (60, 20),
    (37, 20),
    (34, 23),
    (-25, 23),
    (-29, 18),
    (-49.4, 18),
    (-50.6, 16.8),
    (-50.6, 10.2),
    (-52, 8.8),
    (-63, 8.8),
    (-65, 6.8),
]
section(
    inlet_fin,
    "Stamped fin with board receptacle clearance",
    "satin",
    [mm((x, y, -0.22)) for x, y in inlet_outline],
    (0, 0, 0.00044),
)
archive_components(inlet_fin)
inlet_fin.export(out)
rail = Product("astral-rail")
for name, finish, x, y, w, h, start, end, radius in [
    ("Outer rail casting", "graphite", -70, 20, 7, 24, -167.5, 115.5, 2.1),
    ("Raised rail lip", "graphite", -71.9, 31.7, 4, 6, -164.5, 160.5, 1.0),
    ("Segmented Aura lens", "opal", -73.86, 32, 1.6, 2.2, -161, 157, 0.6),
]:
    for lo, hi in [(start, 39.6), (68.4, end)]:
        rail.block(
            name, finish, mm((x, y, (lo + hi) / 2)), mm((w, h, hi - lo)), radius / 1000
        )
archive_components(rail)
rail.export(out)
if "--card-power" in sys.argv:
    card.parts = {k: card.parts[k] for k in ("black", "graphite")}
    archive_components(card)
    card.export(out)
    sys.exit(0)
card.export(out)
rotor=Product('astral-impeller')
impeller(rotor)
rotor.export(out)

fin=Product('astral-fin')
cross=[(-.065,-.017),(-.061,-.020),(-.048,-.020),(-.046,-.025),
       (.047,-.025),(.049,-.020),(.061,-.020),(.066,-.015),(.066,.015),
       (.060,.020),(.037,.020),(.034,.023),(-.025,.023),(-.029,.018),
       (-.061,.018),(-.066,.013)]
section(fin,'Stamped and folded aluminium fin','satin',[(x,y,-.00022) for x,y in cross],(0,0,.00044))
fin.export(out)

pump=Product('ryuo-housing')
side=[(-.032,.022),(.029,.022),(.035,.030),(.035,.069),
      (.030,.074),(-.031,.074),(-.035,.067),(-.035,.029)]
for s in [-1,1]:
    section(pump,'White moulded side access housing','white',[(s*.043,y,z) for y,z in side],(s*.0035,0,0),.0012)
    for i in range(17):
        y=-.026+i*.00312
        chip(pump,'Edge rib on pump casing','satin',(s*.0467,y,.040),(.0006,.00068,.021))
    for y in [-.028,.027]:
        pump.rod('Recessed head fixing','steel',(s*.0465,y,.064),(s*.04685,y,.064),.0018,sides=20)
        pump.rod('Fixing recess','graphite',(s*.0469,y,.064),(s*.04698,y,.064),.00084,sides=6)
for x in [-.033,.032]:
    for y in [-.028,.028]:
        pump.rod('Pump mounting spacer','black',(x,y,.001),(x,y,.016),.0044,sides=24)
        pump.rod('Captive pressure screw','steel',(x,y,.014),(x,y,.022),.0024,sides=20)
pump.export(out)
rad=Product('ryuo-radiator')
rad.block('Brazed core behind the corrugated fins','graphite',(-.008,.0005,0),(.117,.028,.350),.0017)
for s in [-1,1]:
    rad.block('Powder coated side rail','white',(s*.0675,0,0),(.005,.032,.378),.0016)
    tank=[(-.069,-.012),(-.065,-.015),(.062,-.015),(.069,-.009),
          (.069,.012),(.065,.016),(-.064,.016),(-.069,.012)]
    section(rad,'Formed radiator end tank','white',[(x,y,s*.1745) for x,y in tank],
            (0,0,s*.0218),.0022)
    for z in [-.165,-.060,.060,.165]:
        rad.rod('Recessed rail screw','satin',(s*.0696,.002,z),(s*.07036,.002,z),.0027,sides=24)
        rad.rod('Cross recess','graphite',(s*.07037,.002,z),(s*.07049,.002,z),.00113,sides=6)
rad.export(out)
bpy.context.preferences.filepaths.save_version = 0
if __name__ == "__main__":
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'.review/atelier/case-fittings-master.blend'))
