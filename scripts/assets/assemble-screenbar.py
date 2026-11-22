import bpy


def fit(atelier, read_parts, replace_branches):
    lamp = next(
        obj
        for obj in bpy.context.scene.objects
        if obj.get("product") == "BenQ ScreenBar Halo 2"
    )
    installed = {
        piece["haloFinish"]: piece for piece in lamp.children if "haloFinish" in piece
    }
    source = read_parts(
        atelier / "capture-controls/screenbar-halo-2.blend",
        lambda name: name.startswith("Halo 2 • "),
    )
    if {piece["haloFinish"] for piece in source if "haloFinish" in piece} != set(
        installed
    ):
        raise ValueError("ScreenBar native finishes differ from the installed lamp")
    for piece in source:
        if "haloEngineeringApproximation" in piece or "haloMechanicalAxis" in piece:
            piece["studioOccluder"] = False
            continue
        installed_finish = installed[piece["haloFinish"]]
        piece["studioOccluder"] = bool(installed_finish.get("studioOccluder"))
        piece.data.materials[0] = installed_finish.data.materials[0]
    replace_branches(lamp, installed.values(), source)
