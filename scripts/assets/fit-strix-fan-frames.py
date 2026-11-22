import math
from pathlib import Path

import bpy
from mathutils import Matrix


SOURCE = (
    Path(__file__).resolve().parents[2]
    / ".references/03-电脑硬件/风扇与水冷/ROG Strix 140 mm ARGB/Blender/strix-140-stationary-frame.blend"
)
FRAME = "Model 14 · stationary moulding"
SCREWS = "Model 14 · mounting screws"


def fit(scene):
    targets = [
        o
        for o in scene.objects
        if o.name.startswith("ROG Strix Fan Model 14 ARGB")
        and o.type == "EMPTY"
        and any(c.name.startswith("Fan rotor") for c in o.children)
    ]
    if len(targets) not in (1, 4):
        raise ValueError("Expected the single fan library or four installed case fans")
    exhaust = (
        max(targets, key=lambda o: o.matrix_world.translation.y)
        if len(targets) == 4
        else None
    )
    materials = {}
    for fan in targets:
        if fan.get("model14FrameRevision") == 1:
            continue
        old = [o for o in fan.children if not o.name.startswith("Fan rotor")]
        if (
            len(old) not in (7, 10)
            or sum(o.name.startswith("Molded stator arm") for o in old) != 4
        ):
            raise ValueError(f"Unexpected stationary parts in {fan.name}")
        mesh_flags = {bool(o.get("studioOccluder")) for o in old if o.type == "MESH"}
        if not materials:
            with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
                library,
                data,
            ):
                data.collections = [FRAME, SCREWS]
            materials = dict(zip((FRAME, SCREWS), data.collections))
        for obj in old:
            for child in reversed(obj.children_recursive):
                bpy.data.objects.remove(child, do_unlink=True)
            bpy.data.objects.remove(obj, do_unlink=True)
        for key, collection in materials.items():
            anchor = bpy.data.objects.new(key, None)
            for owner in fan.users_collection:
                owner.objects.link(anchor)
            anchor.parent = fan
            anchor.instance_type = "COLLECTION"
            anchor.instance_collection = collection
            anchor.empty_display_size = 0.005
            anchor["studioOccluder"] = any(mesh_flags)
            if key == SCREWS and fan == exhaust:
                anchor.matrix_basis = Matrix.Translation(
                    (0, 0.011, 0)
                ) @ Matrix.Rotation(math.pi, 4, "X")
        fan["model14FrameRevision"] = 1
    for fan in targets:
        fixed = [c for c in fan.children if c.instance_collection]
        assert {c.instance_collection.name for c in fixed} == {FRAME, SCREWS}
        assert len(fan.children) == 3 and all(
            Path(bpy.path.abspath(c.instance_collection.library.filepath)).resolve()
            == SOURCE.resolve()
            for c in fixed
        )
        assert all(len(c.instance_collection.objects) >= 8 for c in fixed)
    bpy.context.view_layer.update()
    return len(targets)
