from pathlib import Path

import bpy


def fit(atelier, read_parts, replace_branches):
    lamp = bpy.context.scene.objects["Workbench lamp"]
    installed = {
        obj.name.rsplit(" · ", 1)[-1]: obj
        for obj in lamp.children
        if obj.type == "MESH"
    }
    source = read_parts(Path(__file__).resolve().parents[2] / ".references/02-家具与灯具/台灯与夹灯/Artemide Tolomeo Micro/Blender/tolomeo-micro.blend")
    finishes = {piece["tolomeoFinish"] for piece in source}
    if finishes != set(installed):
        raise ValueError(
            f"Tolomeo exported surfaces differ from the native finishes: {finishes} vs {set(installed)}"
        )
    for piece in source:
        finish = piece["tolomeoFinish"]
        piece["studioOccluder"] = bool(installed[finish].get("studioOccluder"))
        if finish in {"opal", "reflector", "black"}:
            piece.data.materials[0] = installed[finish].data.materials[0]
    replace_branches(lamp, installed.values(), source)
