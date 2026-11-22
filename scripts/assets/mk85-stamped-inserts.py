import bpy
import numpy as np
from mathutils import Vector, geometry


def register(anchors):
    controls = np.array([a[:2] for a in anchors], dtype=float) / 100
    targets = np.array([a[2:] for a in anchors], dtype=float)

    def kernel(q):
        squared = np.sum((q[:, None] - controls[None, :]) ** 2, axis=2)
        return squared * np.log(squared + 1e-12)

    affine = np.column_stack((np.ones(len(controls)), controls))
    system = np.block(
        [
            [kernel(controls) + np.eye(len(controls)) * 0.0001, affine],
            [affine.T, np.zeros((3, 3))],
        ]
    )
    fit = np.linalg.solve(system, np.vstack((targets, np.zeros((3, 2)))))

    def measured(points):
        points = np.array(points) / 100
        return np.column_stack((kernel(points), np.ones(len(points)), points)) @ fit

    return measured


def stamp(casting, root, name, outline, anchors, crop, pitch, lift, roughness, metal):
    border = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        segments = max(1, int(np.ceil(np.linalg.norm(np.subtract(b, a)) / pitch)))
        border.extend(np.linspace(a, b, segments, endpoint=False).tolist())
    border_count = len(border)
    path = [Vector(v) for v in border]
    outer = list(range(border_count))
    candidates = list(path)
    outline_array = np.array(outline)
    for y in np.arange(
        outline_array[:, 1].min() + pitch * 0.36, outline_array[:, 1].max(), pitch
    ):
        for x in np.arange(
            outline_array[:, 0].min() + pitch * 0.36, outline_array[:, 0].max(), pitch
        ):
            candidates.append(Vector((x, y)))
    coords, _, faces, _, _, _ = geometry.delaunay_2d_cdt(
        candidates, [], [outer], 1, 0.00001
    )
    if not faces:
        raise ValueError("Empty stamped part")
    used = sorted({i for f in faces for i in f})
    remap = {v: i for i, v in enumerate(used)}
    faces = [tuple(remap[v] for v in f) for f in faces]
    coords = [coords[i] for i in used]
    ends = list(zip(path, path[1:] + path[:1]))

    def edge_distance(v):
        return min(
            (
                v
                - (
                    a
                    + (b - a)
                    * max(0, min(1, (v - a).dot(b - a) / (b - a).length_squared))
                )
            ).length
            for a, b in ends
        )

    projected = register(anchors)(coords)
    points = []
    for q, xy in zip(coords, projected):
        point = casting.surface_point(*xy)
        edge = min(1, edge_distance(q) / 2.8)
        point.y -= lift[0] + (lift[1] - lift[0]) * edge
        points.append(point)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], [tuple(reversed(f)) for f in faces])
    mesh.update()
    material = bpy.data.materials.new("Mark 85 · " + name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    paint = material.node_tree.nodes.new("ShaderNodeTexImage")
    filename = (
        "mk85-"
        + ("faceplate" if name.startswith("Pressed") else "arc-window")
        + "-finish.jpg"
    )
    paint.image = bpy.data.images.load(str(root / filename))
    paint.image.pack()
    paint.image.filepath = "//" + filename
    material.node_tree.links.new(paint.outputs["Color"], shader.inputs["Base Color"])
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name=casting.figure.data.uv_layers.active.name)
    for face in mesh.polygons:
        face.use_smooth = True
        if face.normal.y > 0:
            face.flip()
        for loop_id in face.loop_indices:
            x, y = coords[mesh.loops[loop_id].vertex_index]
            uv.data[loop_id].uv = (
                (x - crop[0]) / (crop[2] - crop[0]),
                1 - (y - crop[1]) / (crop[3] - crop[1]),
            )
    piece = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(piece)
    bpy.ops.object.select_all(action="DESELECT")
    piece.select_set(True)
    casting.figure.select_set(True)
    bpy.context.view_layer.objects.active = casting.figure
    bpy.ops.object.join()


def fit(casting, root):
    face = [
        (237, 130, 283.0, 117.1),
        (241, 126, 284.7, 117.1),
        (245, 132, 285.2, 120.1),
        (254, 145, 286.3, 123.9),
        (257, 148, 287.45, 124.25),
        (269, 148, 289.9, 123.8),
        (274, 145, 291.2, 122.65),
        (294, 128, 296.1, 117.9),
        (301, 124, 298.65, 116.75),
        (308, 124, 300.1, 116.65),
        (310.8, 128, 301.0, 118.6),
        (311.1, 160, 301.35, 126.3),
        (312.3, 170, 302.0, 129.7),
        (318, 185, 305.4, 134.65),
        (314, 189, 304.6, 137.0),
        (300, 201, 300.6, 141.6),
        (294, 210, 298.5, 144.7),
        (290, 222, 297.1, 147.45),
        (286, 225.5, 295.9, 148.85),
        (280, 221, 294.3, 147.3),
        (254, 220.5, 286.8, 147.1),
        (251, 226, 285.7, 148.65),
        (241, 203, 281.65, 141.2),
        (234, 191, 280.3, 136.75),
        (231.5, 178, 279.8, 133.4),
        (231, 170, 279.85, 131.4),
    ]
    eyes = [
        (232, 171.5, 279.95, 132.15),
        (247.5, 174.5, 285.1, 132.95),
        (250.2, 176, 286.8, 132.95),
        (247.5, 179.3, 285.55, 133.95),
        (234, 177, 280.4, 133.8),
        (276, 175.8, 291.05, 132.45),
        (305.1, 171, 300.2, 130.55),
        (302.2, 175, 299.5, 132.0),
        (296, 179, 297.15, 132.85),
        (278.1, 179.4, 291.9, 133.65),
    ]
    stamp(
        casting,
        root,
        "Pressed gold visor",
        [v[:2] for v in face],
        face + eyes,
        (226, 118, 330, 244),
        2.8,
        (0.00016, 0.00032),
        0.48,
        0.33,
    )
    window = [
        (257, 347, 286.65, 185.65),
        (261, 343.2, 287.25, 184.1),
        (268, 340.8, 289.2, 182.85),
        (276, 343.5, 291.5, 183.35),
        (285, 343.3, 294.2, 183.50),
        (295, 340.7, 297.3, 182.62),
        (303.3, 344.0, 300.1, 183.5),
        (306.5, 348, 301.35, 184.9),
        (301, 361, 299.75, 189.5),
        (292, 382.4, 295.7, 196.65),
        (288, 385.6, 295.12, 196.85),
        (275.2, 385.7, 292.15, 196.7),
        (271.7, 382.5, 291.55, 196.1),
    ]
    stamp(
        casting,
        root,
        "Arc window reflector cells",
        [v[:2] for v in window],
        window,
        (248, 329, 314, 394),
        2.2,
        (0.00015, 0.00022),
        0.52,
        0.21,
    )
