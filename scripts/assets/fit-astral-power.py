import hashlib
import json
import os
import runpy
import sys
from itertools import groupby
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


archive = Path(__file__).resolve().parents[2] / ".references"
card_folder = archive / "03-电脑硬件/显卡与支架/ROG Astral GeForce RTX 5090/Blender"
rooms = archive / "11-项目整体/工作室全景/Felix Studio/Blender"
components = card_folder / "Components"
atx_folder = archive / "03-电脑硬件/电源与机箱布线/ATX and EPS power cables/Blender"
atx_finishes = ("atx-ivory", "atx-charcoal", "atx-comb")
atx_name = "24-pin ATX braided loom and retaining comb"
card_name = "Diecast frame and thermal module"
loom_name = "Seated 12V-2x6 power and sense loom"
castings = ("astral-casting-black", "astral-casting-graphite")
rails = ("astral-rail-graphite", "astral-rail-opal")
inlet_fin = "astral-fin-inlet-satin"
cables = ("astral-harness-black", "astral-harness-satin", "astral-harness-graphite")
old_rails = [
    ((-70, 26, 20), (7, 283, 24)),
    ((-71.9, 2, 31.7), (4, 325, 6)),
    ((-73.86, 2, 32), (1.6, 318, 2.2)),
]
strut = ((-68, -55, 0), (8, 4, 48))
dummy_plug = ((-73, -54, 13), (14, 27, 13))


def bounds(points):
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return ((high + low) / 2, high - low)


def matches(observed, target):
    return all((a - Vector(b)).length < 0.008 for a, b in zip(observed, target))


def geometry_at(holder, shape):
    inv = holder.matrix_world.inverted()
    matches_at_position = [obj for obj in holder.children if obj.type == "MESH" and
                           matches(bounds([inv @ obj.matrix_world @ Vector(p) * 1000 for p in obj.bound_box]), shape)]
    part, = matches_at_position
    return part


def source_material(objects):
    materials = {slot.material for obj in objects for slot in obj.material_slots if slot.material}
    material, = materials
    return material


def mount(key, holder, material, compact=False, role="astralPart", directory=components):
    source = directory / (key + ".blend")
    with bpy.data.libraries.load(str(source)) as (_, loaded):
        loaded.collections = [key]
    container, = loaded.collections
    parts = list(container.objects)
    assert parts and all(obj.type == "MESH" and not obj.parent for obj in parts)
    destination = holder.users_collection[0]
    for obj in parts:
        destination.objects.link(obj)
        obj.data.materials.clear()
        obj.data.materials.append(material)
    bpy.data.collections.remove(container)
    if compact:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in parts:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.convert(target="MESH")
        if len(parts)>1:
            bpy.ops.object.join()
        joined = bpy.context.object
        joined.name = key
        parts = [joined]
    for obj in parts:
        obj.parent = holder
        obj[role] = key
        obj["studioOccluder"] = key != "astral-rail-opal"
    return parts


def remove(obj):
    bpy.data.objects.remove(obj, do_unlink=True)


def remove_batch_parts(holder):
    hull_mat = None
    aura_mat = None
    found = {}
    inverse = holder.matrix_world.inverted()
    for obj in holder.children:
        if not obj.name.startswith(card_name + " · fixed surfaces"):
            continue
        matrix = inverse @ obj.matrix_world
        points = [matrix @ vert.co * 1000 for vert in obj.data.vertices]
        drop = set()
        for slot, (center, extent) in enumerate([*old_rails, strut]):
            inside = [all(abs(point[i]-center[i]) < extent[i]/2 + 0.006 for i in range(3)) for point in points]
            for hit, grouped in groupby(enumerate(inside), key=lambda flag: flag[1]):
                if not hit:
                    continue
                ids = [index for index, _ in grouped]
                if len(ids) != 900 or not matches(bounds([points[i] for i in ids]), (center, extent)):
                    continue
                assert slot not in found
                found[slot] = obj
                if slot == 3:
                    offset = matrix.to_3x3().inverted() @ Vector((0, 0.018, 0))
                    for i in ids:
                        obj.data.vertices[i].co += offset
                else:
                    drop.update(ids)
                    if slot == 0:
                        hull_mat = source_material([obj])
                    elif slot == 2:
                        aura_mat = source_material([obj])
        if drop:
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            verts = [bm.verts[i] for i in drop]
            assert all(all(p.index in drop for p in face.verts) for v in verts for face in v.link_faces)
            bmesh.ops.delete(bm, geom=verts, context="VERTS")
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()
            if "studioSurface" in obj:
                del obj["studioSurface"]
    assert len(found) == 4 and hull_mat and aura_mat
    return hull_mat, aura_mat


def inlet_fins(holder):
    bank, = [obj for obj in holder.children if obj.name.startswith("Folded cooling fins in two banks")]
    assert len(bank.children) == 134
    return [next(obj for obj in bank.children if abs(obj.location.y + 0.004 + (i-66) * 0.00236) < 0.00001)
            for i in range(82, 93)]


def fit_fins(holder):
    selected = inlet_fins(holder)
    material = source_material(selected)
    with bpy.data.libraries.load(str(components / (inlet_fin + ".blend"))) as (library, loaded):
        assert len(library.objects) == 1
        loaded.objects = list(library.objects)
    source, = loaded.objects
    assert source.type == "MESH" and len(source.modifiers) == 0 and source.matrix_basis.is_identity
    mesh = source.data
    mesh.materials.clear()
    mesh.materials.append(material)
    for obj in selected:
        obj.data = mesh
        obj["astralPart"] = inlet_fin
        if "studioSurface" in obj:
            del obj["studioSurface"]
    remove(source)


def fit_card(scene, compact, revised):
    holder = scene.objects[card_name]
    if revised:
        old = [[obj for obj in holder.children if obj.get("astralPart") == key] for key in rails]
        hull_mat, aura_mat = [source_material(parts) for parts in old]
        for grouped in old:
            for obj in grouped:
                remove(obj)
    elif compact:
        hull_mat, aura_mat = remove_batch_parts(holder)
    else:
        outlines = [geometry_at(holder, shape) for shape in old_rails]
        hull_mat, aura_mat = source_material(outlines[:2]), source_material(outlines[2:])
        for obj in outlines:
            remove(obj)
        geometry_at(holder, strut).location.y += 0.018
    if not revised:
        remove(geometry_at(holder, dummy_plug))
    for key in castings:
        finish = key.rsplit("-", 1)[1]
        if compact:
            target, = [obj for obj in holder.children if (obj.get("astralPart") == key if revised else
                       obj.name == "Astral backplate, retention and thermal fittings · " + finish)]
            material = source_material([target])
            remove(target)
            mount(key, holder, material, True)
        else:
            group, = [child for child in holder.children if child.name.startswith(key)]
            old = list(group.children)
            material = source_material(old)
            for part in old:
                remove(part)
            mount(key, group, material)
    for key, material in zip(rails, [hull_mat, aura_mat]):
        mount(key, holder, material, compact)
    fit_fins(holder)


def fit_harness(scene, compact):
    loom = scene.objects[loom_name]
    old_finishes = {}
    for key in cables:
        objects = [obj for obj in loom.children_recursive if obj.type == "MESH" and
                   (obj.get("cablePart") == key or obj.name == key or obj.parent.name.startswith(key))]
        old_finishes[key] = source_material(objects)
    colors = ("424449", "62646a", "33353a")
    for key, color in zip(cables, colors):
        groups = [obj for obj in loom.children if obj.type == "EMPTY" and obj.name.startswith(key)]
        destination = groups[0] if groups else loom
        old = list(destination.children) if groups else [
            obj for obj in loom.children if obj.get("cablePart") == key or obj.name == key
        ]
        base = old_finishes[cables[0]] if key == cables[1] else old_finishes[key]
        label = "CableMod · " + key
        material = bpy.data.materials.get(label)
        if material is None:
            material = base.copy()
            material.name = label
        rgb = tuple(((int(color[i:i+2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4))
        shader = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = (*rgb, 1)
        material.diffuse_color = (*rgb, 1)
        for obj in old:
            remove(obj)
        mount(key, destination, material, compact, role="cablePart")


def fit_atx(scene, compact):
    loom = scene.objects[atx_name]
    for key in atx_finishes:
        groups = [child for child in loom.children if child.type == "EMPTY" and child.name.startswith(key)]
        destination = groups[0] if groups else loom
        current = list(destination.children) if groups else [
            child for child in loom.children if child.get("cablePart") == key
        ]
        assert len(current) == (1 if compact or key == "atx-comb" else 12), (key, len(current))
        material = source_material(current)
        for obj in current:
            remove(obj)
        mount(key, destination, material, compact, "cablePart", atx_folder / "Components")


def fit_wiring_source():
    before = set(bpy.data.objects)
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    runpy.run_path(str(root / "build-pc-internals.py"))["power_harness"]()
    generated = set(bpy.data.objects) - before
    for prefix, kind, expected in (("ATX conductor centerline", "CURVE",24), ("Individually sleeved ATX conductor", "MESH",24),
                                   ("Removable twin-row cable comb","MESH",1)):
        def leads(objects):
            return sorted((obj for obj in objects if obj.type == kind and obj.name.startswith(prefix)),
                          key=lambda obj: obj.name)
        old, new = leads(before), leads(generated)
        assert len(old) == len(new) == expected
        for target, source in zip(old, new):
            retained_materials = list(target.data.materials)
            target.data = source.data
            target.data.materials.clear()
            for material in retained_materials:
                target.data.materials.append(material)
            target.matrix_world = source.matrix_world
    for obj in generated:
        remove(obj)
    assert set(bpy.data.objects) == before


def relocate_map(scene):
    holder = scene.objects["World travel map"]
    assert min((holder.location-Vector((0.844, 0.535, z))).length for z in (1.752, 1.817)) < 0.0002
    holder.location.z = 1.817


def dependencies():
    paths = {Path(path).resolve() for path in bpy.utils.blend_paths(absolute=True, packed=False) if path}
    assert all(path.exists() for path in paths), [str(path) for path in paths if not path.exists()]
    return len(paths)


def validate(scene, features, compact):
    bpy.context.view_layer.update()
    dependencies()
    if "map" in features:
        assert abs(scene.objects["World travel map"].location.z - 1.817) < 0.00001
        assert len([obj for obj in scene.objects if "localAim" in obj and obj.type == "LIGHT"]) == 5
        assert any("core ultra 9 285k" in obj.name.lower() for obj in scene.objects)
    adapter = scene.objects.get(card_name)
    if "card" in features:
        for key in (*rails, *castings):
            parts = [obj for obj in adapter.children_recursive if obj.get("astralPart") == key and obj.type == "MESH"]
            assert len(parts) == 1 if compact else len(parts) > 1, (key, len(parts))
        assert all(any(obj.name.startswith(word) for obj in adapter.children_recursive)
                   for word in ("Fourth pass-through fan", "Axial-tech intake 3", "Folded cooling fins"))
        clipped = inlet_fins(adapter)
        assert len({part.data for part in clipped}) == 1 and all(part.get("astralPart") == inlet_fin for part in clipped)
        assert sum(part.get("astralPart") == inlet_fin for part in adapter.children_recursive) == 11
    if "loom" in features:
        loom = scene.objects[loom_name]
        for key in cables:
            parts = [obj for obj in loom.children_recursive if obj.get("cablePart") == key and obj.type == "MESH"]
            assert len(parts) == 1 if compact else len(parts) > 1, (key, len(parts))
        if not compact:
            assert sum("16 AWG" in obj.name for obj in loom.children_recursive) == 12
    if "atx" in features:
        loom = scene.objects[atx_name]
        for key in atx_finishes:
            parts = [obj for obj in loom.children_recursive if obj.get("cablePart") == key and obj.type == "MESH"]
            assert len(parts) == (1 if compact or key == "atx-comb" else 12)
        assert any("comb" in obj.name for obj in loom.children_recursive)
    if "atxCurves" in features:
        for prefix in ("ATX conductor centerline", "Individually sleeved ATX conductor"):
            assert sum(obj.name.startswith(prefix) for obj in scene.objects) == 24


def synchronize(path, features, check_only, cable_only):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    compact = path.name == "felix-studio.blend"
    keys = ([*castings, *rails, inlet_fin] if "card" in features else []) + (list(cables) if "loom" in features else [])
    digest = hashlib.sha256(b"".join((components / (key + ".blend")).read_bytes() for key in keys)).hexdigest()
    update_astral = bool(keys) and scene.get("astralPowerRevision") != digest
    atx_digest = atx_revision()
    update_atx = any(role in features for role in ("atx","atxCurves")) and scene.get("atxCableRevision") != atx_digest
    if not update_astral and not update_atx:
        validate(scene, features, compact)
        return
    if update_astral and cable_only and "card" in features:
        assert scene.get("astralPowerRevision")
        validate(scene, ("card",), compact)
    elif update_astral and "card" in features:
        fit_card(scene, compact, bool(scene.get("astralPowerRevision")))
    if update_astral and "loom" in features:
        fit_harness(scene, compact)
    if "map" in features:
        relocate_map(scene)
    if update_astral:
        scene["astralPowerRevision"] = digest
    if update_atx:
        if "atx" in features:
            fit_atx(scene, compact)
        else:
            fit_wiring_source()
        scene["atxCableRevision"] = atx_digest
    validate(scene, features, compact)
    if check_only:
        print("CHECKED", path.name, len(scene.objects), flush=True)
        return
    staged = path.with_suffix(".fitting.blend")
    if staged.exists():
        raise FileExistsError(staged)
    bpy.context.preferences.filepaths.save_version = 0
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True, compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(staged), load_ui=False, use_scripts=False)
        validate(bpy.context.scene, features, compact)
        print("VERIFIED", path.name, len(bpy.data.objects), "objects", dependencies(), "unique dependencies", flush=True)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


targets = {
    "card": (card_folder / "astral-5090.blend", ("card",)),
    "cable": (card_folder / "astral-12v2x6.blend", ("loom",)),
    "atx": (atx_folder / "atx-24pin.blend", ("atx",)),
    "atx-source": (atx_folder / "board-wiring.blend", ("atxCurves",)),
    "room": (rooms / "felix-studio.blend", ("card", "loom", "map", "atx")),
    "assembled": (rooms / "felix-studio-assembled.blend", ("card", "loom", "map", "atx")),
}
def atx_revision():
    return hashlib.sha256(b"".join((atx_folder/"Components"/(key+".blend")).read_bytes() for key in atx_finishes)).hexdigest()


def fit_atx_power(scene):
    compact = len([o for o in scene.objects[atx_name].children_recursive if o.get("cablePart") == "atx-ivory" and o.type == "MESH"]) == 1
    revision = atx_revision()
    if scene.get("atxCableRevision") != revision:
        fit_atx(scene, compact)
        scene["atxCableRevision"] = revision
    validate(scene, ("atx",), compact)
    return scene.objects[atx_name]


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    for key in [arg for arg in args if not arg.startswith("--")] or targets:
        synchronize(*targets[key], check_only="--check-only" in args, cable_only="--cable-only" in args)
