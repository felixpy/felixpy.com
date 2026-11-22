from pathlib import Path

import bpy

NAME = "CZ-5 Y8 · lunar mission display shell"
SOURCE = (
    Path(__file__).resolve().parents[2]
    / ".references/06-工坊与工具/三维打印与模型/Launch vehicle scale model/Blender/cz5-y8-painted-shell.blend"
)


def fit(scene):
    root = scene.objects["Standing launch vehicle scale model"]
    (mount,) = [o for o in root.children if o.name == "Airframe and stage interfaces"]
    plaque = next(
        (
            o
            for o in root.children
            if o.type == "MESH"
            and abs(o.location.y + 0.043) < 1e-5
            and abs(o.location.z + 0.12) < 1e-5
            and len(o.data.polygons) <= 2
        ),
        None,
    )
    current = mount.instance_collection
    if current is not None:
        if (
            current.name != NAME
            or not current.library
            or not Path(bpy.path.abspath(current.library.filepath)).samefile(SOURCE)
            or len(current.all_objects) != 19
        ):
            raise ValueError("Unexpected display shell library")
        if plaque:
            bpy.data.objects.remove(plaque, do_unlink=True)
        return mount
    parts = list(mount.children_recursive)
    if not any("中国航天" in obj.name for obj in parts) or any(
        obj.library for obj in parts
    ):
        raise ValueError("Unrecognized launch vehicle display shell")
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
        library,
        loaded,
    ):
        if NAME not in library.collections:
            raise ValueError("Missing CZ-5 Y8 display shell")
        loaded.collections = [NAME]
    (collection,) = loaded.collections
    if (
        len(collection.all_objects) != 19
        or sum("inward crown" in obj.name for obj in collection.all_objects) != 4
    ):
        raise ValueError("Incomplete decorative display")
    mount.instance_type = "COLLECTION"
    mount.instance_collection = collection
    for child in reversed(parts):
        bpy.data.objects.remove(child, do_unlink=True)
    if plaque:
        bpy.data.objects.remove(plaque, do_unlink=True)
    return mount
