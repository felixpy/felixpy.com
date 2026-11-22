from os.path import relpath
from pathlib import Path

import bpy


root = Path(__file__).resolve().parents[2]
library = root / ".references/04-桌面设备/显示器与桌面支架/LG OLED evo G6/Blender/lg-oled-g6.blend"
mount_name = "VIVO STAND-V155D - 300x200 grommet mount"


def source_collection():
    for collection in bpy.data.collections:
        if collection.name == mount_name and collection.library:
            if Path(bpy.path.abspath(collection.library.filepath)).resolve() == library.resolve():
                return collection
    with bpy.data.libraries.load(str(library), link=True, relative=True) as (available, loaded):
        if mount_name not in available.collections:
            raise ValueError("The LG authoring file has no 300 x 200 mount")
        loaded.collections = [mount_name]
    return loaded.collections[0]


def save_standalone():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    mount = source_collection()
    scene.collection.children.link(mount)
    folder = library.parents[2] / "VIVO monitor arm/Blender"
    mount.library.filepath = "//" + Path(relpath(library, folder)).as_posix()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "vivo-monitor-arm.blend"), compress=True, relative_remap=False)


def fit(scene):
    existing = [obj for obj in scene.objects if obj.get("installedVivoGrommet")]
    if existing:
        instance, = existing
        if instance.instance_collection != source_collection():
            raise ValueError("Incorrect VIVO mount collection")
        return instance
    combined = [obj for obj in scene.objects if obj.name.startswith("VIVO_STAND-V155D_") and obj.type == "EMPTY"]
    if combined:
        anchor, = combined
        old = list(anchor.children)
        if len(old) != 4 or not all(o.name.startswith("Grommet_base_") for o in old):
            raise ValueError("Unrecognized combined VIVO assembly")
    else:
        anchor, = [obj for obj in scene.objects if obj.name.startswith("LG OLED evo G6 · OLED48G6PCA") and obj.type == "EMPTY"]
        old = [obj for obj in anchor.children if obj.get("assembly") == "arm"]
        if not old:
            raise ValueError("No existing VIVO mount under the display")
    collection = source_collection()
    instance = bpy.data.objects.new("VIVO STAND-V155D - installed support", None)
    anchor.users_collection[0].objects.link(instance)
    instance.parent = anchor
    instance.instance_type = "COLLECTION"
    instance.instance_collection = collection
    instance["installedVivoGrommet"] = True
    for obj in old:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    return instance
