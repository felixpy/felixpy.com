from pathlib import Path

import bpy

SOURCE = (
    Path(__file__).resolve().parents[2]
    / ".references/06-工坊与工具/电子测量与实验/Fluke 115 multimeter/Blender/fluke-115-multimeter.blend"
)


def fit(scene, *, complete=None):
    bench = scene.objects["Fluke 115 on tilt stand"]
    (holder,) = [
        child for child in bench.children if child.get("benchInstrument") == "meter"
    ]
    old = list(holder.children_recursive)
    if (
        holder.type not in {"EMPTY", "MESH"}
        or (holder.type == "EMPTY" and not old)
        or any(child.type != "MESH" for child in old)
    ):
        raise ValueError("Unexpected Fluke 115 assembly")
    if complete is None:
        complete = holder.get(
            "flukeIncludesService", any(child.name.startswith("115 ·") for child in old)
        )
    expected = 16 if complete else 9
    if (
        holder.get("flukeIncludesService") == complete
        and len(old) == expected
        and all(
            child.data.library
            and Path(bpy.path.abspath(child.data.library.filepath)).samefile(SOURCE)
            for child in old
        )
    ):
        return expected
    fixed = holder.get("studioOccluder") or any(
        child.get("studioOccluder") for child in old
    )
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (_, library):
        library.collections = ["Fluke 115"]
    (collection,) = library.collections
    (root,) = [
        child for child in collection.objects if child.get("benchInstrument") == "meter"
    ]
    shells = list(root.children)
    service = [child for child in root.children_recursive if child.get("servicePart")]
    assert len(shells) == 9 and len(service) == 7
    assert collection.library.filepath.startswith("//")
    assert Path(bpy.path.abspath(collection.library.filepath)).samefile(SOURCE)
    for child in reversed(old):
        bpy.data.objects.remove(child, do_unlink=True)
    if holder.type == "MESH":
        packed = holder
        name = packed.name
        holder = bpy.data.objects.new("Installed Fluke 115", None)
        for owner in packed.users_collection:
            owner.objects.link(holder)
        holder.parent = bench
        holder.matrix_parent_inverse = packed.matrix_parent_inverse.copy()
        holder.location = packed.location
        holder.rotation_mode = packed.rotation_mode
        holder.rotation_quaternion = packed.rotation_quaternion
        holder.rotation_axis_angle = packed.rotation_axis_angle
        holder.rotation_euler = packed.rotation_euler
        holder.scale = packed.scale
        holder.delta_location = packed.delta_location
        holder.delta_rotation_quaternion = packed.delta_rotation_quaternion
        holder.delta_rotation_euler = packed.delta_rotation_euler
        holder.delta_scale = packed.delta_scale
        for key in packed.keys():
            holder[key] = packed[key]
        bpy.data.objects.remove(packed, do_unlink=True)
        holder.name = name
    installed = {root: holder}
    for source in shells + (service if complete else []):
        item = bpy.data.objects.new(source.name, source.data)
        holder.users_collection[0].objects.link(item)
        item.parent = installed[source.parent]
        item.matrix_basis = source.matrix_basis.copy()
        item["studioOccluder"] = bool(fixed and not source.get("servicePart"))
        if source.get("servicePart"):
            item["servicePart"] = True
        installed[source] = item
    holder["flukeIncludesService"] = bool(complete)
    return expected
