import hashlib
import json
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


root = Path(__file__).resolve().parents[2]
model = root / ".references/03-电脑硬件/机箱与整机/ROG Hyperion GR701/Blender"
room = root / ".references/11-项目整体/工作室全景/Felix Studio/Blender"
layout = root / "src/scene/gr701-lower-ports.json"
collars = model / "gr701-lower-grommets.blend"
board_collar = model / "gr701-board-inlet.blend"
layout_data = json.loads(layout.read_text())
revision = hashlib.sha256(layout.read_bytes() + collars.read_bytes() + board_collar.read_bytes()).hexdigest()
part_tag = "lowerCableGrommet"


def bounds(points):
    return tuple(tuple(op(point[i] for point in points) for i in range(3)) for op in (min,max))


def close(first, second):
    return all(abs(a-b) < 0.012 for p, q in zip(first,second) for a,b in zip(p,q))


def in_bounds(point, extent):
    return all(lo-.012 <= value <= hi+.012 for value,lo,hi in zip(point,*extent))


def pan_and_seal(holder):
    pan_extent = ((86.6,-216,-275),(88,307,251))
    seal_extent = ((82.7,-29.5,90.5),(86,5.5,169.5))
    pan, seal, seal_ids = None, None, []
    for obj in holder.children:
        if obj.type != "MESH" or obj.get(part_tag) or obj.get("boardCableGrommet"):
            continue
        mx = holder.matrix_world.inverted() @ obj.matrix_world
        bb = bounds([mx @ Vector(p)*1000 for p in obj.bound_box])
        if close(bb, pan_extent):
            pan = obj
        if all(bb[0][i] - .012 <= seal_extent[0][i] and bb[1][i] + .012 >= seal_extent[1][i] for i in range(3)):
            if close(bb,seal_extent):
                seal = obj
                seal_ids = list(range(len(obj.data.vertices)))
            else:
                points = [mx @ vert.co * 1000 for vert in obj.data.vertices]
                hits = [i for i,point in enumerate(points) if in_bounds(point, seal_extent)]
                if len(hits) == 192 and close(bounds([points[i] for i in hits]),seal_extent):
                    seal = obj
                    seal_ids = hits
    assert pan is not None
    return pan, seal, seal_ids


def lower_ribs(holder):
    targets = (((76.5,-200,-148.5),(87.5,286,-141.5)), ((72.8,-188.5,-143),(78.8,278.5,-141)))
    found = set()
    for obj in holder.children:
        if obj.type != "MESH" or len(obj.data.vertices)%900:
            continue
        mx = holder.matrix_world.inverted() @ obj.matrix_world
        for start in range(0,len(obj.data.vertices),900):
            verts = obj.data.vertices[start:start+900]
            bb = bounds([mx @ v.co*1000 for v in verts])
            for i, target in enumerate(targets):
                if close(bb,target):
                    assert i not in found
                    found.add(i)
                    if len(verts)==len(obj.data.vertices):
                        obj.location.z -= .015
                    else:
                        shift = mx.to_3x3().inverted() @ Vector((0,0,-.015))
                        for v in verts:
                            v.co += shift
                        obj.data.update()
                    if "studioSurface" in obj:
                        del obj["studioSurface"]
    assert len(found)==2, found


def fit_shroud(bay):
    panel = ((-102.5,-31,-169),(104.5,295,-169))
    back_rail = ((98.5,-32,-175.5),(107.5,302,-168.5))
    found = set()
    for obj in bay.children:
        if obj.type != "MESH":
            continue
        matrix = bay.matrix_world.inverted() @ obj.matrix_world
        positions = [matrix @ v.co*1000 for v in obj.data.vertices]
        for key, extent, expected in (("vent",panel,4),("rail",back_rail,900)):
            selected = [(i,p) for i,p in enumerate(positions) if in_bounds(p,extent)]
            if len(selected)!=expected or not close(bounds([p for _,p in selected]),extent):
                continue
            assert key not in found
            found.add(key)
            inverse = matrix.inverted()
            for i,point in selected:
                if key=="vent":
                    point.x = -102.5 + (point.x+102.5) * 190/207
                else:
                    point.x -= 19
                obj.data.vertices[i].co = inverse @ (point*.001)
            obj.data.update()
            if "studioSurface" in obj:
                del obj["studioSurface"]
    assert found=={"vent","rail"}, found


def prism(name, outline, depth, mx):
    n = len(outline)
    vertices = [mx @ (Vector((x,-z,y))*.001) for x in depth for z,y in outline]
    faces = [tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces += [(i,n+i,n+(i+1)%n,(i+1)%n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def chamfered(z,y,width,height,corner):
    l,r = z-width/2,z+width/2
    b,t = y-height/2,y+height/2
    return [(l+corner,b),(r-corner,b),(r,b+corner),(r,t-corner),
            (r-corner,t),(l+corner,t),(l,t-corner),(l,b+corner)]


def tray_punches():
    cutouts = [chamfered(-199,106,130,89,9),layout_data["boardInletPunchMm"],chamfered(*layout_data["serviceMm"])]
    cutouts.extend([[(center+z*layout_data["punchScale"], layout_data["heightMm"]+y*layout_data["punchScale"])
                     for z,y in layout_data["outlineMm"]] for center in layout_data["centersMm"]])
    cutouts.extend(chamfered(z,224,68,15,4) for z in (-226,-115,4,128))
    return cutouts


def plate_matches(pan, chassis, cutouts):
    mx = chassis.matrix_world.inverted() @ pan.matrix_world
    points = [mx @ v.co * 1000 for v in pan.data.vertices]
    corners = [(-p.y,p.z) for p in points if abs(p.x - 88) < .005]
    return all(any(abs(a-z) < .005 and abs(b-y) < .005 for a,b in corners)
               for shape in cutouts for z,y in shape)


def rebuild_pan(pan, chassis, cutouts):
    mx = pan.matrix_world.inverted() @ chassis.matrix_world
    steel = pan.active_material
    boundary = [(-307,-275),(216,-275),(216,216),(192,251),(-286,251),(-307,228)]
    pan.data = prism("GR701 pressed motherboard tray",boundary,(86.6,88),mx)
    pan.data.materials.append(steel)
    for outline in cutouts:
        cutter_mesh = prism("Cable opening punch",outline,(80,94),mx)
        cutter = bpy.data.objects.new("Lower cable opening punch",cutter_mesh)
        pan.users_collection[0].objects.link(cutter)
        cutter.matrix_world = pan.matrix_world
        boolean = pan.modifiers.new("Cut lower cable opening","BOOLEAN")
        boolean.operation = "DIFFERENCE"
        boolean.solver = "EXACT"
        boolean.object = cutter
        bpy.context.view_layer.objects.active = pan
        bpy.ops.object.modifier_apply(modifier=boolean.name)
        bpy.data.objects.remove(cutter,do_unlink=True)
        bpy.data.meshes.remove(cutter_mesh)
    if "studioSurface" in pan:
        del pan["studioSurface"]
    pan["lowerCableOpenings"] = True


def remove_old_seal(obj, ids):
    if len(ids) == len(obj.data.vertices):
        bpy.data.objects.remove(obj,do_unlink=True)
        return
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    selected = [bm.verts[i] for i in ids]
    allowed = set(selected)
    assert all(all(p in allowed for p in face.verts) for v in selected for face in v.link_faces)
    bmesh.ops.delete(bm, geom=selected, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    if "studioSurface" in obj:
        del obj["studioSurface"]


def install(chassis, material, path, count, tag):
    with bpy.data.libraries.load(str(path)) as (source, loaded):
        loaded.objects = list(source.objects)
    assert count is None or len(loaded.objects)==count
    for part in loaded.objects:
        assert part.type == "MESH" and not part.parent
        chassis.users_collection[0].objects.link(part)
        part.parent = chassis
        if tag==part_tag:
            part.data.materials.clear()
            part.data.materials.append(material)
        part[tag] = True
        part["studioOccluder"] = True


def verify():
    scene = bpy.context.scene
    chassis = scene.objects["ROG Hyperion GR701 chassis"]
    ports = [o for o in chassis.children if o.get(part_tag)]
    assert len(ports)==6 and len({o.active_material for o in ports}) == 1
    upper = [o for o in chassis.children if o.get("boardCableGrommet")]
    assert len(upper)==4 and all(o.active_material for o in upper)
    tongues = [o for o in upper if o.data.shape_keys]
    assert len(tongues)==3 and all(o.data.shape_keys.key_blocks["Installed cable deflection"].value==1 for o in tongues)
    pan, = [o for o in chassis.children if o.get("lowerCableOpenings")]
    local = chassis.matrix_world.inverted() @ pan.matrix_world
    geometry = BVHTree.FromPolygons([local @ v.co for v in pan.data.vertices],
                                    [list(f.vertices) for f in pan.data.polygons])
    def contains(z, height):
        return geometry.ray_cast(Vector((.08,-z*.001,height*.001)),Vector((1,0,0)),.018)[0] is not None
    for z in layout_data["centersMm"]:
        y = layout_data["heightMm"]
        assert all(not contains(z + dz,y + dy) for dz,dy in ((0,0),(25,6),(-25,-6)))
        assert contains(z,y+21) and contains(z,y-21)
    for z,y in ((-199,106),(12,130),(-226,224),(-115,224),(4,224),(128,224)):
        assert not contains(z,y)
    assert plate_matches(pan, chassis, tray_punches())
    assert all(not contains(z,y) for z,y in ((-69,-233),(-35,-205),(-115,-241)))
    assert contains(-69,-189) and contains(-4,-233)
    missing = [path for path in bpy.utils.blend_paths(absolute=True,packed=False) if path and not Path(path).exists()]
    assert not missing, missing


def update(path, check_only):
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    scene = bpy.context.scene
    if scene.get("gr701LowerPorts") == revision:
        verify()
        return
    chassis = scene.objects["ROG Hyperion GR701 chassis"]
    channel = scene.objects["Formed motherboard tray and wiring channel"]
    pan, original_seal, indices = pan_and_seal(chassis)
    assert original_seal or any(o.get("boardCableGrommet") for o in chassis.children)
    old = [obj for obj in chassis.children if obj.get(part_tag) or obj.get("boardCableGrommet")]
    material = next((obj.active_material for obj in old if obj.get(part_tag)),None)
    if material is None:
        material = original_seal.active_material
    if original_seal:
        remove_old_seal(original_seal,indices)
    if not pan.get("lowerCableOpenings"):
        lower_ribs(channel)
    cutouts = tray_punches()
    if not plate_matches(pan, chassis, cutouts):
        rebuild_pan(pan,chassis,cutouts)
    if not scene.get("gr701ShroudFit"):
        fit_shroud(scene.objects["Hyperion removable PSU shroud and accessory drawer"])
        scene["gr701ShroudFit"] = True
    for part in old:
        bpy.data.objects.remove(part,do_unlink=True)
    install(chassis,material,collars,6,part_tag)
    install(chassis,material,board_collar,None,"boardCableGrommet")
    bpy.context.view_layer.update()
    scene["gr701LowerPorts"] = revision
    verify()
    if check_only:
        print("CHECKED",path.name, len(bpy.data.objects),flush=True)
        return
    bpy.context.preferences.filepaths.save_version = 0
    staged = path.with_suffix(".ports.blend")
    if staged.exists():
        raise FileExistsError(staged)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True, compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(staged),load_ui=False,use_scripts=False)
        verify()
        print("VERIFIED",path.name,len(bpy.data.objects),flush=True)
        os.replace(staged,path)
    finally:
        staged.unlink(missing_ok=True)


args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
targets = {"chassis":model/"hyperion-gr701.blend","room":room/"felix-studio.blend",
           "assembled":room/"felix-studio-assembled.blend"}
for name in [arg for arg in args if not arg.startswith("--")] or targets:
    update(targets[name],"--check-only" in args)
