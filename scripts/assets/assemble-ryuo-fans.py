from collections import defaultdict

import bpy


def bounds(objects):
    coords = [
        tuple(obj.matrix_local @ vertex.co)
        for obj in objects
        for vertex in obj.data.vertices
    ]
    return [select(axis) for axis in zip(*coords) for select in (min, max)]


def fit(atelier):
    with bpy.data.libraries.load(str(atelier / "ryuo-mf12c.blend"), link=False) as (
        library,
        loaded,
    ):
        loaded.objects = [name for name in library.objects if name != "Fan rotor"]
    parts = defaultdict(list)
    for obj in loaded.objects:
        if "fanPart" in obj:
            parts[obj["fanPart"]].append(obj)
    fans = [obj for obj in bpy.context.scene.objects if "mf12cStation" in obj]
    if {fan["mf12cStation"] for fan in fans} != {0, 1, 2} or len(fans) != 3:
        raise ValueError(
            f"Expected all three installed MF-12C stations; found {len(fans)}"
        )
    moving = {"vanes", "medallion", "rotor-foil"}
    for fan in fans:
        installed = {
            obj["mf12cPart"]: obj
            for obj in fan.children_recursive
            if "mf12cPart" in obj
        }
        variant = "stripes" if fan["mf12cStation"] == 1 else "eye"
        if set(installed) != moving | {
            "chassis",
            "pads",
            "grey",
            "screws",
            "contacts",
            variant,
        }:
            raise ValueError(
                f"Missing fitted geometry on {fan.name}: {list(installed)}"
            )
        if (
            len({installed[key].parent for key in moving}) != 1
            or installed["vanes"].parent.parent != fan
        ):
            raise ValueError(f"Missing spindle axis in {fan.name}")
        for key, original in installed.items():
            meshes = []
            material = original.data.materials[0]
            for source in parts[key]:
                item = source.copy()
                bpy.context.scene.collection.objects.link(item)
                item.parent = original.parent
                item.matrix_local = original.matrix_local
                item["studioOccluder"] = bool(original.get("studioOccluder"))
                item.material_slots[0].link = "OBJECT"
                item.material_slots[0].material = material
                meshes.append(item)
            bpy.context.view_layer.update()
            error = max(abs(a - b) for a, b in zip(bounds([original]), bounds(meshes)))
            if error > 0.000015:
                raise ValueError(
                    f"{fan.name} / {key}: installation error {error * 1000:.3f} mm"
                )
            bpy.data.objects.remove(original, do_unlink=True)
        print(
            f"{fan.name} • {variant} side lighting • {sum(len(parts[k]) for k in installed)} editable mesh objects"
        )
    for obj in loaded.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
