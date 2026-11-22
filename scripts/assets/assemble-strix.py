import bpy


def fit(atelier, replace_branches):
    scene = bpy.context.scene
    parent = scene.objects["ROG Strix Z890-A Gaming WiFi S · Fubuki"]
    old = list(parent.children)
    fixed = any(part.get("studioOccluder") for part in parent.children_recursive)
    board_name = "ROG Strix Z890-A Gaming WiFi S"
    cpu_name = "LGA1851 processor package"
    components = atelier / "pc-components"
    with bpy.data.libraries.load(str(components / "strix-z890-a.blend"), link=False) as (_, loaded):
        loaded.collections = [board_name]
    board = loaded.collections[0]
    processor_file = components / "lga1851-processor.blend"
    with bpy.data.libraries.load(str(processor_file), link=False) as (_, loaded):
        loaded.collections = [cpu_name]
    cpu = loaded.collections[0]
    datum = next(obj for obj in board.all_objects if obj.name.startswith("CPU contact"))
    parts = []
    for group in [*board.children, cpu]:
        if group.name.startswith("Mechanical datums"):
            continue
        anchor = bpy.data.objects.new(group.name, None)
        anchor.empty_display_size = 0.003
        if group == cpu:
            anchor.location = datum.location.copy()
            if model := cpu.get("model"):
                anchor.name = f"Installed {model}"
                anchor["model"] = model
        scene.collection.objects.link(anchor)
        parts.append(anchor)
        for part in group.objects:
            if part.type != "MESH":
                continue
            scene.collection.objects.link(part)
            part.parent = anchor
            part["studioOccluder"] = fixed
            parts.append(part)
    replace_branches(parent, old, parts)
