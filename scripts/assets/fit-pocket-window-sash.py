from pathlib import Path

import bpy


def fit(scene):
    name = "Pocket window sash · bronze frame and HOPPE fittings"
    root = Path(__file__).resolve().parents[2]
    source = root / ".references/01-空间与建筑/门窗与五金/Pocket window sash/Blender/pocket-window-sash.blend"
    mount = scene.objects["Mitred aluminium window and tilt-turn sash"]
    current = mount.instance_collection
    if current and current.name == name and current.library:
        if Path(bpy.path.abspath(current.library.filepath)).resolve() == source:
            return mount
    previous = list(mount.children)
    if not previous or any(obj.type != "MESH" or obj.children for obj in previous):
        raise ValueError("Unexpected sash mounting hierarchy")
    with bpy.data.libraries.load(str(source), link=True) as (available, loaded):
        if name not in available.collections:
            raise ValueError("The archived window collection was not found")
        loaded.collections = [name]
    collection = loaded.collections[0]
    if bpy.data.filepath:
        collection.library.filepath = bpy.path.relpath(str(source))
    mount.instance_type = "COLLECTION"
    mount.instance_collection = collection
    for obj in previous:
        bpy.data.objects.remove(obj, do_unlink=True)
    return mount
