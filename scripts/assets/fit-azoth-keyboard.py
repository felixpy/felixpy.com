from pathlib import Path

import bpy


source = (
    Path(__file__).resolve().parents[2]
    / ".references/04-桌面设备/键鼠与控制台"
    / "ROG Azoth Extreme/Blender/rog-azoth-extreme.blend"
)


def fit(scene):
    parent = scene.objects["Mechanical keyboard"]
    collection_name = "ROG Azoth Extreme"
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (_, load):
        load.collections = [collection_name]
    parts = load.collections[0].objects
    mounted = {o.get("azothPart", o.name): o for o in parent.children}
    source_names = {o.name for o in parts}
    if len(mounted) == 1 and any(
        "ROG_Azoth_Extreme" in o.name for o in parent.children_recursive
    ):
        previous = list(parent.children_recursive)
        for old in reversed(previous):
            bpy.data.objects.remove(old, do_unlink=True)
        mounted = {}
        for part in parts:
            local = bpy.data.objects.new(part.name, part.data)
            parent.users_collection[0].objects.link(local)
            local.parent = parent
            local["azothPart"] = part.name
            mounted[part.name] = local
    if source_names != set(mounted):
        raise ValueError(f"Azoth assembly mismatch: {source_names ^ set(mounted)}")
    for part in parts:
        target = mounted[part.name]
        target.data = part.data
        target.matrix_basis = part.matrix_basis.copy()
        target["studioOccluder"] = False
    caps = [p for p in parent.children if p.name.startswith("Azoth | Keycap ")]
    assert len(caps) == 81 and all(k.data.library for k in caps)
    parent["keycapGuide"] = "M702 Q23057 PRINT4 (US)"
    return len(caps)
