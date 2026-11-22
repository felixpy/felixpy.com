from pathlib import Path

import bpy


PRODUCTS = {
    "NIKKOR Z 14-24mm f2.8 S": "nikkor-z14-24-s.blend",
    "NIKKOR Z 100-400mm f4.5-5.6 VR S": "nikkor-z100-400-s.blend",
    "NIKKOR Z 58mm f0.95 S Noct": "nikkor-z58-noct.blend",
}


def fit(scene):
    directory = Path(__file__).resolve().parents[2] / ".references/05-摄影与陈列/相机与镜头"
    changed = False
    for name, filename in PRODUCTS.items():
        holder = scene.objects[name.replace(" ", "_").replace(".", "")]
        source = directory / name / "Blender" / filename
        current = holder.instance_collection
        if current and current.library and Path(bpy.path.abspath(current.library.filepath)).resolve() == source:
            continue
        old = list(holder.children_recursive)
        if current or not old or any(part.library or part.type != "MESH" for part in old):
            raise ValueError(f"Unknown native assembly for {name}")
        with bpy.data.libraries.load(str(source), link=True, relative=True) as (available, linked):
            if name not in available.collections:
                raise ValueError(f"No matching product collection in {source}")
            linked.collections = [name]
        (assembly,) = linked.collections
        if not any("OLED" in part.name for part in assembly.all_objects):
            raise ValueError(f"Missing OLED assembly in {source}")
        holder.instance_type = "COLLECTION"
        holder.instance_collection = assembly
        for part in reversed(old):
            bpy.data.objects.remove(part, do_unlink=True)
        changed = True
    return changed
