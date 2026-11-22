import bpy


def fit(atelier):
    keys = {
        "atx-ivory",
        "atx-charcoal",
        "atx-shell",
        "atx-comb",
        "eps-sleeves",
        "eps-plugs",
        "aio-braid",
        "aio-fittings",
        "aio-seals",
        "astral-harness-black",
        "astral-harness-satin",
        "astral-harness-graphite",
    }
    installed = [obj for obj in bpy.context.scene.objects if "cablePart" in obj]
    if {obj["cablePart"] for obj in installed} != keys or len(installed) != len(keys):
        raise ValueError("Expected the installed GPU, ATX, EPS and coolant assemblies")
    graph = bpy.context.evaluated_depsgraph_get()

    def bounds(meshes):
        points = []
        for obj in meshes:
            evaluated = obj.evaluated_get(graph)
            data = evaluated.to_mesh()
            try:
                points.extend(evaluated.matrix_world @ v.co for v in data.vertices)
            finally:
                evaluated.to_mesh_clear()
        return [fn(v[i] for v in points) for i in range(3) for fn in (min, max)]

    for batch in installed:
        key = batch["cablePart"]
        path = atelier / "pc-components" / "native" / (key + ".blend")
        with bpy.data.libraries.load(str(path), link=False) as (_, loaded):
            loaded.collections = [key]
        source = loaded.collections[0]
        expected = bounds([batch])
        material = batch.data.materials[0]
        pieces = list(source.objects)
        for piece in pieces:
            local = piece.matrix_basis.copy()
            batch.users_collection[0].objects.link(piece)
            piece.parent = batch.parent
            piece.matrix_local = batch.matrix_local @ local
            piece["studioOccluder"] = bool(batch.get("studioOccluder"))
            piece["cablePart"] = key
            if key == "aio-braid":
                continue
            if not piece.data.materials:
                piece.data.materials.append(material)
            for slot in piece.material_slots:
                slot.link = "OBJECT"
                slot.material = material
        bpy.context.view_layer.update()
        error = max(abs(a - b) for a, b in zip(expected, bounds(pieces)))
        if error > 0.00005:
            raise ValueError(f"{key}: installation error {error * 1000:.3f} mm")
        bpy.data.collections.remove(source)
        bpy.data.objects.remove(batch, do_unlink=True)
        print(f"{key}: {len(pieces)} installed parts, {error * 1000:.3f} mm fit error")
