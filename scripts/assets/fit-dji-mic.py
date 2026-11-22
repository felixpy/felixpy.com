from pathlib import Path

import bpy


PRODUCT = Path(__file__).resolve().parents[2] / ".references/05-摄影与陈列/录音与存储配件/DJI Mic 2/Blender/dji-mic-2.blend"
ASSEMBLY = "DJI Mic 2 • DMT02 assembly"
INSTANCE = "DJI Mic 2 · clip transmitter"


def fit(scene):
    mount = scene.objects[INSTANCE]
    current = mount.instance_collection
    if current and current.name == ASSEMBLY and current.library:
        assert Path(bpy.path.abspath(current.library.filepath)).resolve() == PRODUCT.resolve()
        return mount
    assert mount.type == "EMPTY" and len(mount.children) == 1
    previous = mount.children[0]
    names = {c.name.split(".")[0].replace(" ", "_") for c in previous.children}
    original_parts = {
        "Continuous_milled_chassis", "Injection-moulded_smoked_window",
        "Transmitter_details", "Upper_acoustic_cap",
    }
    assert original_parts <= names or names == {"DMT02_exterior"}
    with bpy.data.libraries.load(str(PRODUCT), link=True, relative=True) as (sources, loaded):
        assert ASSEMBLY in sources.collections
        loaded.collections = [ASSEMBLY]
    collection = loaded.collections[0]
    assert len(collection.objects) == 7 and len(collection.children[0].objects) == 7
    for obj in [*reversed(previous.children_recursive), previous]:
        bpy.data.objects.remove(obj, do_unlink=True)
    mount.instance_type = "COLLECTION"
    mount.instance_collection = collection
    if names == original_parts:
        mount.location.z += (0.02183 / 2) - 0.01081
    bpy.context.view_layer.update()
    return mount
