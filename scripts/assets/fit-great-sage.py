from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / ".references/05-摄影与陈列/手办与收藏模型/Great Sage/Blender/great-sage.blend"
)
CASTING = "Great Sage · round casting"
TITLE = "Sun Wukong · The Great Victory"


def fit(scene):
    root = next(o for o in scene.objects if o.name.replace("_", " ") == TITLE)
    direct = root.type == "MESH"
    existing = (
        root
        if direct
        else next((o for o in root.children if o.data and o.data.name == CASTING), None)
    )
    if existing and existing.data.name == CASTING:
        return existing
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
        library,
        loaded,
    ):
        if CASTING not in library.meshes:
            raise ValueError("The Great Sage library has no round casting")
        loaded.meshes = [CASTING]
    (mesh,) = loaded.meshes
    if direct:
        root.data = mesh
        installed = root
    else:
        old = list(root.children)
        if not old or not all(
            child.type == "MESH" and not child.children for child in old
        ):
            raise ValueError("Unrecognized Great Sage assembly")
        installed = bpy.data.objects.new(CASTING, mesh)
        root.users_collection[0].objects.link(installed)
        installed.parent = root
        if any(child.get("studioOccluder") for child in old):
            installed["studioOccluder"] = True
        for child in old:
            bpy.data.objects.remove(child, do_unlink=True)
    scene.view_layers[0].update()
    return installed
