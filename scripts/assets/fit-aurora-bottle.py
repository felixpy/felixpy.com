from pathlib import Path

import bpy


def fit(scene):
    folder = Path(__file__).resolve().parents[2] / ".references/07-户外装备/咖啡与饮具"
    source = folder / "Snow Peak Aurora Bottle 800 Rainbow/Blender/tw-800-ra.blend"
    mount, = [obj for obj in scene.objects if obj.get("product") == "snow-peak-tw800-ra"]
    roles = {
        "Aurora · seamless variable-gauge titanium bottle": "vessel",
        "Aurora · screw cap with moulded carry aperture": "cap",
        "Aurora · XTW-800-02 stepped silicone gasket": "packing",
        "Aurora · curved front print": None,
    }
    parts = {obj.name.replace("_", " "): obj for obj in mount.children_recursive}
    if parts.keys() != roles.keys() or any(obj.type != "MESH" for obj in parts.values()):
        raise ValueError("Unexpected Aurora bottle assembly")
    if all(obj.data.library and Path(bpy.path.abspath(obj.data.library.filepath)).resolve() == source
           and obj.data.name == name for name, obj in parts.items()):
        return mount
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (available, linked):
        if not roles.keys() <= set(available.meshes):
            raise ValueError("Missing an archived Aurora bottle mesh")
        linked.meshes = list(roles)
    for mesh in linked.meshes:
        obj = parts[mesh.name]
        obj.data = mesh
        if roles[mesh.name]:
            obj["auroraFitting"] = roles[mesh.name]
    return mount
