from pathlib import Path

import bmesh
import bpy

PRODUCT = (
    Path(__file__).resolve().parents[2]
    / ".references/05-摄影与陈列/相机与镜头/Nikon Z8/Blender/nikon-z8-card-bay.blend"
)
ASSEMBLY = "Z8 dual media compartment"


def remove_tree(obj):
    for child in list(obj.children):
        remove_tree(child)
    bpy.data.objects.remove(obj, do_unlink=True)


def fit(scene):
    body = next(
        o
        for o in scene.objects
        if "Nikon Z8 with NIKKOR" in o.name and o.type == "EMPTY"
    )
    existing = next((o for o in body.children if o.name.startswith(ASSEMBLY)), None)
    if (
        existing
        and existing.instance_collection
        and existing.instance_collection.name == ASSEMBLY
    ):
        return existing
    shell = next(o for o in body.children if o.name.startswith("Sealed body, grip"))
    closed = next(
        (o for o in shell.children if o.name.startswith("Z8 closed card door")), None
    )
    if closed is None:
        outer = next(
            o
            for o in shell.children
            if o.type == "MESH" and len(o.data.polygons) == 2080
        )
        seam = next(
            o
            for o in shell.children
            if o.type == "MESH"
            and len(o.data.polygons) == 384
            and min(v.co.z for v in o.data.vertices) < -0.03
        )
        thumb = next(
            o
            for o in body.children
            if o.type == "MESH"
            and len(o.data.polygons) == 1224
            and abs(o.location.x + 0.063) < 0.0001
        )
        fixed = next(
            o for o in shell.children if o.type == "MESH" and "fixed surfaces" in o.name
        )
        geom = bmesh.new()
        geom.from_mesh(fixed.data)

        def old_hinge(v):
            x, y, z = fixed.matrix_local @ v.co
            return -0.074 < x < -0.069 and -0.0015 < y < 0.0049 and -0.025 < z < 0.0158

        cut = [f for f in geom.faces if all(old_hinge(v) for v in f.verts)]
        if not 12 <= len(cut) <= 350:
            geom.free()
            raise ValueError("Unexpected legacy card hinge geometry")
    with bpy.data.libraries.load(str(PRODUCT), link=True, relative=True) as (_, loaded):
        loaded.collections = [ASSEMBLY]
    parts = loaded.collections[0]
    names = [o.name for o in parts.all_objects]
    if (
        names.count("Card door pivot") != 1
        or sum(n.startswith("CFexpress · recessed terminal ") for n in names) != 21
    ):
        raise ValueError("Incomplete Nikon dual card bay")
    if closed:
        remove_tree(closed)
    else:
        bmesh.ops.delete(geom, geom=cut, context="FACES")
        geom.to_mesh(fixed.data)
        geom.free()
        for obsolete in (outer, seam, thumb):
            remove_tree(obsolete)
    if existing:
        remove_tree(existing)
    instance = bpy.data.objects.new(ASSEMBLY, None)
    scene.collection.objects.link(instance)
    instance.parent = body
    instance.instance_type = "COLLECTION"
    instance.instance_collection = parts
    instance.empty_display_size = 0.007
    return instance
