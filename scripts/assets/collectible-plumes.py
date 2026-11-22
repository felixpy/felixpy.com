import math

import bmesh
import bpy
import numpy as np


def photo_edges(image, left, right):
    width, height = image.size
    flat = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(flat)
    photo = flat.reshape(height, width, 4)[::-1, :, :3]
    background = np.median(photo[45:180, 480:500], axis=(0, 1))
    mask = np.linalg.norm(photo[:, left:right] - background, axis=2) > 0.24
    rows, bounds = [], []
    for y in range(45, 185):
        occupied = np.flatnonzero(mask[y])
        if occupied.size:
            rows.append(y)
            bounds.append((occupied[0] + left - 0.35, occupied[-1] + left + 0.35))
    edges = np.array(bounds)
    smooth = np.array([1, 3, 4, 3, 1]) / 12
    return np.array(rows), [
        np.convolve(np.pad(edge, 2, mode="edge"), smooth, mode="valid")
        for edge in edges.T
    ]


def cast_plumes(figure, root):
    mesh = figure.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    old = [
        vertex
        for vertex in bm.verts
        if vertex.co.z > 0.2184
        and vertex.co.x > -0.055
        and (vertex.co.z > 0.222 or vertex.co.x < -0.0295 or vertex.co.x > -0.019)
    ]
    bmesh.ops.delete(bm, geom=old, context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    neutral = mesh.color_attributes.new(
        name="Plume finish", type="BYTE_COLOR", domain="POINT"
    )
    neutral.data.foreach_set("color", np.ones(len(mesh.vertices) * 4, dtype="f"))

    enamel = bpy.data.materials.new("Red enamel over gilt copper • crown plumes")
    enamel.use_nodes = True
    shader = enamel.node_tree.nodes["Principled BSDF"]
    shader.inputs["Metallic"].default_value = 0.52
    shader.inputs["Roughness"].default_value = 0.32
    shader.inputs["Coat Weight"].default_value = 0.3
    shader.inputs["Coat Roughness"].default_value = 0.24
    shade = enamel.node_tree.nodes.new("ShaderNodeVertexColor")
    shade.layer_name = "Plume finish"
    enamel.node_tree.links.new(shade.outputs["Color"], shader.inputs["Base Color"])
    reference = bpy.data.images.load(
        str(root / "great-sage-high-resolution.png"), check_existing=True
    )
    vertices, faces, colors = [], [], []
    gilt = (0.62, 0.32, 0.068)
    recess = (0.22, 0.074, 0.019)
    lacquer = (0.39, 0.013, 0.012)

    def socket(x, y, slope, profile):
        resolution = 42
        start = len(vertices)
        for z, rx, ry, pigment in profile:
            for i in range(resolution):
                a = i * math.tau / resolution
                vertices.append(
                    (
                        x + slope * (z - 0.2181) + rx * math.cos(a) / 1000,
                        y + ry * math.sin(a) / 1000,
                        z,
                    )
                )
                colors.append((*pigment, 1))
        for j in range(len(profile) - 1):
            for i in range(resolution):
                k = start + j * resolution + i
                n = start + j * resolution + (i + 1) % resolution
                faces.append((k, n, n + resolution, k + resolution))
        faces.append(tuple(reversed(range(start, start + resolution))))
        end = start + len(profile) * resolution
        faces.append(tuple(range(end - resolution, end)))

    for side, bounds in [(-1, (342, 401)), (1, (425, 470))]:
        rows, (left, right) = photo_edges(reference, *bounds)
        lower = 0.2181
        upper = 0.265 if side < 0 else 0.2649
        radius = np.linspace(0, math.tau, 31)[:-1]
        count = 156
        start = len(vertices)
        for j in range(count):
            t = j / (count - 1)
            row = 181 + (rows[0] - 181) * t
            a, b = np.interp(row, rows, left), np.interp(row, rows, right)
            half = (b - a) * 0.000201
            if t > 0.981:
                half *= np.interp(t, [0.981, 1], [1, 0.14])
            x = ((a + b) / 2 - 470.5) * 0.000402
            z = lower + (upper - lower) * t
            mid_y = np.interp(
                t,
                [0, 0.18, 0.35, 0.57, 0.77, 1],
                [0.00505, 0.00515, 0.0041, 0.002, -0.00065, -0.0029],
            )
            amber = np.clip((t - 0.42) / 0.29, 0, 1)
            amber = amber * amber * (3 - 2 * amber)
            pigment = (1 - amber) * np.array([0.42, 0.013, 0.011]) + amber * np.array(
                [0.88, 0.41, 0.045]
            )
            for theta in radius:
                u, depth = math.cos(theta), math.sin(theta)
                inward = -side * u
                ridge = math.exp(-(((inward - 0.38) / 0.15) ** 2))
                barb = math.sin(2 * math.pi * (t * 46 - 0.70 * abs(inward - 0.38)))
                feather = (0.45 + 0.55 * max(0, 1 - abs(inward))) * (1 - ridge)
                y = mid_y + depth * (
                    max(0.00009, min(0.00105, half * 0.40))
                    + half * 0.17 * ridge
                    + 0.000064 * feather * barb
                )
                vertices.append((x + u * half, y, z))
                edge_color = np.array([0.84, 0.48, 0.11])
                glint = 0.62 * ridge + 0.28 * max(0, abs(u) - 0.92) / 0.08
                tint = pigment * (1 - glint) + edge_color * glint
                colors.append((*np.clip(tint * (1 + 0.045 * feather * barb), 0, 1), 1))
        ring = len(radius)
        for j in range(count - 1):
            for k in range(ring):
                i = start + j * ring + k
                n = start + j * ring + (k + 1) % ring
                faces.append((i, n, n + ring, i + ring))
        faces.append(tuple(reversed(range(start, start + ring))))
        faces.append(tuple(range(start + (count - 1) * ring, start + count * ring)))
        xroot = (
            0.5 * (np.interp(181, rows, left) + np.interp(181, rows, right)) - 470.5
        ) * 0.000402
        socket(
            xroot,
            0.00495,
            0.18 * side,
            [
                (0.2132, 3.6, 2.5, recess),
                (0.2143, 4.35, 2.78, gilt),
                (0.2151, 4.15, 2.65, gilt),
                (0.21565, 3.75, 2.38, recess),
                (0.2164, 3.7, 2.45, lacquer),
                (0.21705, 3.95, 2.6, gilt),
                (0.21755, 4.52, 2.87, gilt),
                (0.21825, 4.75, 2.97, gilt),
                (0.21885, 4.41, 2.76, gilt),
                (0.21908, 3.01, 1.89, recess),
            ],
        )
    socket(
        -0.02455,
        0.00485,
        0,
        [
            (0.2152, 3.52, 2.35, lacquer),
            (0.2168, 3.28, 2.27, lacquer),
            (0.2177, 2.49, 1.9, gilt),
            (0.2183, 2.36, 1.81, gilt),
            (0.21865, 1.78, 1.4, lacquer),
            (0.2193, 1.63, 1.33, lacquer),
            (0.21985, 1.18, 1.0, gilt),
            (0.2203, 0.68, 0.56, gilt),
            (0.2206, 0.16, 0.14, gilt),
        ],
    )
    data = bpy.data.meshes.new("Paired engraved crown feathers")
    data.from_pydata(vertices, [], faces)
    data.materials.append(enamel)
    color = data.color_attributes.new(
        name="Plume finish", type="BYTE_COLOR", domain="POINT"
    )
    color.data.foreach_set("color", np.asarray(colors, dtype="f").ravel())
    data.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    data.update()
    addition = bpy.data.objects.new(data.name, data)
    bpy.context.collection.objects.link(addition)
    bpy.ops.object.select_all(action="DESELECT")
    addition.select_set(True)
    figure.select_set(True)
    bpy.context.view_layer.objects.active = figure
    bpy.ops.object.join()
