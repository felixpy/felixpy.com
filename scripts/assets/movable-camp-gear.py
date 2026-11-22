def exclude_from_static_lighting(scene):
    for root in scene.objects:
        if not (
            root.get("product") in ("PR-880", "snow-peak-tw800-ra")
            or root.get("trekAssembly") in ("pot", "lid")
            or root.get("trek900ShelfMount")
        ):
            continue
        root["studioMovable"] = True
        for part in (root, *root.children_recursive):
            if part.type == "MESH":
                part["studioOccluder"] = False


def static_mesh(entry):
    part = entry.object
    return (
        part.type == "MESH"
        and part.get("studioOccluder")
        and not (
            entry.is_instance and entry.parent and entry.parent.get("studioMovable")
        )
    )
