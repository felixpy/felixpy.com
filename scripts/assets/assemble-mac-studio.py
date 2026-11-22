import bpy


def fit(atelier, read_parts, replace_branches):
    scene = bpy.context.scene
    detail = scene.objects["Mac Studio inspection detail"]
    room = scene.objects["Mac Studio at desk distance"]
    parent = detail.parent
    if parent is None or room.parent != parent or not detail.children:
        raise ValueError(
            "Expected both Mac detail levels under the installed workstation"
        )

    branches = [room, detail]
    fixed = any(part.get("studioOccluder") for part in parent.children_recursive)
    source = read_parts(atelier / "mac-studio-m5-ultra.blend")
    internals = (
        "Left centrifugal blower",
        "Right centrifugal blower",
        "Logic board, SSD sockets",
        "Round power supply, insulator",
    )
    shell = [
        part
        for part in source
        if part.name.startswith("Machined enclosure and perforated rear grille")
    ]
    if len(shell) != 1 or any(
        not any(part.name.startswith(name) for part in source) for name in internals
    ):
        raise ValueError(
            "Missing Mac enclosure or internal components in the editable source"
        )
    for part in source:
        if part.name.startswith("Screen filtered intake and exhaust"):
            raise ValueError(
                "A display-only vent surface was included in the native Mac"
            )
        part["studioOccluder"] = fixed and not part.name.startswith(internals)
    replace_branches(parent, branches, source)
