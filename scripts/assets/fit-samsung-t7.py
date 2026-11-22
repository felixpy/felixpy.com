from pathlib import Path

import bpy

SOURCE = (
    Path(__file__).resolve().parents[2]
    / ".references/04-桌面设备/存储与充电/Samsung Portable SSD T7/Blender/samsung-t7-2tb.blend"
)


def fit(scene, *, complete=None):
    drive = scene.objects["Portable SSD"]
    parts = list(drive.children_recursive)
    mount = next((p for p in parts if p.get("t7EndAssembly")), None)
    full_name = "Samsung T7 · complete drive"
    if mount:
        assert mount.instance_collection and mount.instance_collection.library
        assembled = mount.instance_collection.name == full_name
    else:
        assembly = "Samsung Portable SSD T7 2 TB · MU-PC2T0T"
        assembled = any(p.get("assembly") == assembly for p in parts)
        if assembled:
            assert all(p.get("assembly") == assembly for p in parts)
        else:
            assert any(p.name.startswith("Samsung_T7_2_TB_") for p in parts)
            assert all(p.type in ("MESH", "EMPTY") for p in parts)
        assert not any(p.get("studioOccluder") for p in parts)
    install_full_drive = assembled if complete is None else complete
    collection = full_name if install_full_drive else "Samsung T7 · Exterior"
    if not mount or mount.instance_collection.name != collection:
        with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
            source,
            load,
        ):
            assert collection in source.collections
            load.collections = [collection]
        native = load.collections[0]
        assert native and native.library
        if not mount:
            mount = bpy.data.objects.new("T7 · installed Titan Gray drive", None)
            drive.users_collection[0].objects.link(mount)
            mount.parent = drive
            mount.instance_type = "COLLECTION"
            mount["studioOccluder"] = False
            mount["t7EndAssembly"] = True
            for part in reversed(parts):
                bpy.data.objects.remove(part, do_unlink=True)
        mount.instance_collection = native
    native = mount.instance_collection
    assert Path(bpy.path.abspath(native.library.filepath)).samefile(SOURCE)
    assert native.library.filepath.startswith("//")
    assert len(drive.children) == 1 and drive.parent.name.startswith("Drawer interior")
    assert sum(p.name.startswith("Connector contact") for p in native.all_objects) == 24
    assert any(
        p.name.startswith("Identification end · printed adhesive film")
        for p in native.all_objects
    )
    if native.name.endswith("complete drive"):
        assert sum("formed terminal" in p.name for p in native.all_objects) == 24
        assert sum("concealed Phillips" in p.name for p in native.all_objects) == 4
    return len(native.all_objects)
