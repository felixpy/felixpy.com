import itertools
import runpy
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def projected_finish(obj, work):
    mesh = obj.data
    mesh.vertices.foreach_set("co", np.load(work / "points.npy").ravel())
    mesh.update()
    points = np.zeros((len(mesh.vertices), 3), dtype="f")
    normals = np.zeros_like(points)
    mesh.vertices.foreach_get("co", points.ravel())
    mesh.vertices.foreach_get("normal", normals.ravel())
    directions = np.asarray([(0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)])
    weight = np.maximum(normals @ directions.T, 0) ** 5
    weight[:, :2] *= 2.7
    x, y, z = (points * 1000).T
    arm = (z > 248) & (
        np.abs(x + 10)
        > np.interp(
            z, [248, 265, 308, 330, 353, 375, 420], [56, 43, 39, 35, 37, 41, 41]
        )
    )
    leg = z < 248
    axis_x = np.select(
        [arm, leg],
        [
            -10
            + np.sign(x + 10)
            * np.interp(
                z, [255, 280, 300, 320, 347, 365, 376], [56, 58, 55, 49, 42, 34, 28]
            ),
            -10 + np.sign(x + 9) * np.interp(z, [113, 198, 247], [40, 33, 22]),
        ],
        default=-10.0,
    )
    axis_y = np.select(
        [arm, leg],
        [
            np.interp(z, [255, 275, 296, 320, 346, 370], [-18, -12, -1, 7, 5, 3]),
            np.interp(z, [113, 150, 205, 247], [-5, 4, -2, -3]),
        ],
        default=-4.0,
    )
    side = x - axis_x
    depth = (y - axis_y) * np.where(arm, 1.25, 1.57)
    radial = np.column_stack((-depth, depth, -side, side))
    body_weight = np.maximum(radial, 0) ** 3.7
    body_weight[:, :2] *= 4.3
    hidden_side = ((z > 248) & (~arm)) | (arm & (side * (x + 10) < 0))
    body_weight[hidden_side, 2:] = 0
    body_weight[hidden_side, 0] += 0.08 * (y[hidden_side] < axis_y[hidden_side])
    body_weight[hidden_side, 1] += 0.08 * (y[hidden_side] >= axis_y[hidden_side])
    body_weight /= np.maximum(body_weight.max(axis=1)[:, None], 1e-8)
    weight[z > 114.5] = body_weight[z > 114.5]
    original = weight.copy()
    for i, camera in enumerate(directions):
        unit = Vector(camera)
        for vertex in np.flatnonzero(weight[:, i] > 0.0001):
            pos = Vector(points[vertex])
            hit, first, _, _ = obj.ray_cast(pos + unit * 0.55, -unit, distance=0.7)
            if hit:
                gap = (first - pos).dot(unit)
                weight[vertex, i] *= np.clip((0.004 - gap) / 0.0025, 0, 1)
    hidden = weight.sum(axis=1) < 0.0001
    weight[hidden] = original[hidden]
    weight[z > 114.5] = original[z > 114.5]
    weight[:, 0] += 0.000001
    weight /= weight.sum(axis=1)[:, None]
    material = bpy.data.materials.new("Registered large casting enamel")
    material.use_nodes = True
    tree = material.node_tree
    loops = np.zeros(len(mesh.loops), dtype="i")
    mesh.loops.foreach_get("vertex_index", loops)
    main_uv = mesh.uv_layers.active.name
    slots = list(mesh.materials)
    attribute = mesh.color_attributes.new(
        name="Photographed enamel weights", type="FLOAT_COLOR", domain="POINT"
    )
    attribute.data.foreach_set("color", weight.astype("f").ravel())
    weights = tree.nodes.new("ShaderNodeVertexColor")
    weights.layer_name = attribute.name
    split = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(weights.outputs["Color"], split.inputs[0])
    terms = []
    for i in range(4):
        uv = mesh.uv_layers.new(name="Orthographic enamel " + str(i))
        values = np.load(work / f"camera-{i}.npy")[loops]
        uv.uv.foreach_set("vector", values.ravel())
        mapping = tree.nodes.new("ShaderNodeUVMap")
        mapping.uv_map = uv.name
        sample = tree.nodes.new("ShaderNodeTexImage")
        sample.image = bpy.data.images.load(str(work / f"camera-{i}.jpg"))
        tree.links.new(mapping.outputs[0], sample.inputs["Vector"])
        term = tree.nodes.new("ShaderNodeVectorMath")
        term.operation = "SCALE"
        tree.links.new(sample.outputs[0], term.inputs[0])
        tree.links.new(
            ([*split.outputs[:3], weights.outputs["Alpha"]])[i], term.inputs["Scale"]
        )
        terms.append(term.outputs[0])
    colour = terms[0]
    for other in terms[1:]:
        total = tree.nodes.new("ShaderNodeVectorMath")
        total.operation = "ADD"
        tree.links.new(colour, total.inputs[0])
        tree.links.new(other, total.inputs[1])
        colour = total.outputs[0]
    glow = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(colour, glow.inputs[0])
    tree.links.new(glow.outputs[0], tree.nodes.get("Material Output").inputs[0])
    receiver = obj.copy()
    receiver.data = mesh.copy()
    bpy.context.collection.objects.link(receiver)
    sheet = receiver.data
    bm = bmesh.new()
    bm.from_mesh(sheet)
    bmesh.ops.delete(
        bm,
        geom=[face for face in bm.faces if face.material_index >= 4],
        context="FACES",
    )
    bm.to_mesh(sheet)
    bm.free()
    sheet.materials.clear()
    sheet.materials.append(material)
    sheet.polygons.foreach_set(
        "material_index", np.zeros(len(sheet.polygons), dtype="i")
    )
    sheet.uv_layers.active = sheet.uv_layers[main_uv]
    sheet.uv_layers.active.active_render = True
    canvas = bpy.data.images.new(
        "MK85 · four-view fired enamel", 3072, 2192, alpha=False
    )
    target = tree.nodes.new("ShaderNodeTexImage")
    target.image = canvas
    tree.nodes.active = target
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    bpy.ops.object.select_all(action="DESELECT")
    receiver.select_set(True)
    bpy.context.view_layer.objects.active = receiver
    bpy.ops.object.bake(type="EMIT", margin=7, use_clear=True)
    bpy.data.objects.remove(receiver, do_unlink=True)
    bpy.data.meshes.remove(sheet)
    bpy.context.view_layer.objects.active = obj
    canvas.filepath_raw = str(work / "mk85-large-enamel.jpg")
    canvas.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    canvas.save()
    enamel = bpy.data.images.load(
        str(work / "mk85-large-enamel.jpg"), check_existing=False
    )
    enamel.pack()
    enamel.filepath = "//mk85-large-enamel.jpg"
    for i, slot in enumerate(slots):
        mesh.materials[i] = slot
        if i < 4:
            tex = next(n for n in slot.node_tree.nodes if n.type == "TEX_IMAGE")
            tex.image = enamel
            shader = slot.node_tree.nodes["Principled BSDF"]
            shader.inputs["Roughness"].default_value = [0.57, 0.40, 0.42, 0.52][i]
            shader.inputs["Metallic"].default_value = [0.26, 0.38, 0.48, 0.21][i]
    for layer in list(mesh.uv_layers):
        if layer.name != main_uv:
            mesh.uv_layers.remove(layer)
    mesh.color_attributes.remove(mesh.color_attributes["Photographed enamel weights"])
    return points


def registered_body(obj, points, work):
    mesh = obj.data
    viewpoints = np.array([[0, -1], [0, 1], [-1, 0], [1, 0]])
    materials = []
    for i, label in enumerate(("front", "back", "left", "right")):
        m = bpy.data.materials.new("MK85 · registered paint " + label)
        m.use_nodes = True
        shader = m.node_tree.nodes["Principled BSDF"]
        shader.inputs["Metallic"].default_value = 0.38
        shader.inputs["Roughness"].default_value = 0.41
        im = bpy.data.images.load(str(work / f"camera-{i}.jpg"), check_existing=False)
        im.pack()
        im.filepath = f"//casting-enamel-{label}.jpg"
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = im
        m.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
        materials.append(len(mesh.materials))
        mesh.materials.append(m)
    mesh.attributes.new("MK85 camera view", "INT", "FACE")
    for face in mesh.polygons:
        if face.material_index >= 4:
            continue
        ids = list(face.vertices)
        x, y, z = points[ids].mean(axis=0) * 1000
        if z < 114.5:
            continue
        center = -10
        if z < 247:
            center = -10 + (1 if x > -9 else -1) * np.interp(
                z, [113, 200, 247], [40, 33, 22]
            )
            cy = np.interp(z, [113, 148, 205, 247], [-5, 4, -2, -3])
            ratio = 1.35
        else:
            arm_separator = np.interp(
                z,
                [247, 260, 305, 325, 345, 361, 372, 385, 419],
                [53, 43, 39, 35, 37, 37, 40, 55, 55],
            )
            arm = abs(x + 10) > arm_separator
            if arm:
                center = -10 + np.sign(x + 10) * np.interp(
                    z, [253, 275, 295, 320, 340, 360, 372], [55, 58, 56, 49, 44, 38, 32]
                )
                cy = np.interp(
                    z, [254, 278, 294, 318, 344, 370], [-18, -12, -1, 7, 5, 3]
                )
                ratio = 1.25
            else:
                cy = np.interp(
                    z, [247, 305, 346, 366, 385, 419], [-5, -5, -5, -1, -6, -6]
                )
                ratio = 1.75
        radial = np.array([x - center, (y - cy) * ratio])
        spatial = viewpoints @ radial
        if z > 248 and abs(x + 10) > 36 and (x - center) * (x + 10) < 0:
            spatial[2:] *= 0.1
        choice = int(np.argmax(spatial))
        face.use_smooth = True
        old = face.index
        obj.data.attributes["MK85 camera view"].data[old].value = choice


def leg_lacquer(obj):
    mesh = obj.data
    pigment = next(
        n.image for n in mesh.materials[0].node_tree.nodes if n.type == "TEX_IMAGE"
    )
    mat = bpy.data.materials.new("MK85 · continuous greave and thigh lacquer")
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Metallic"].default_value = 0.42
    shader.inputs["Roughness"].default_value = 0.43
    sample = mat.node_tree.nodes.new("ShaderNodeTexImage")
    sample.image = pigment
    mat.node_tree.links.new(sample.outputs["Color"], shader.inputs["Base Color"])
    index = len(mesh.materials)
    mesh.materials.append(mat)
    for face in mesh.polygons:
        if (
            face.material_index < 4
            and 0.1145 < face.center.z < 0.270
            and abs(face.center.x + 0.01) < 0.053
        ):
            face.material_index = index


def vambrace_lacquer(obj, work):
    mesh = obj.data
    mat = bpy.data.materials.new("MK85 · wraparound vambrace enamel")
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Metallic"].default_value = 0.5
    shader.inputs["Roughness"].default_value = 0.43
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(work / "vambrace-enamel.png"))
    tex.image.pack()
    tex.image.filepath = "//vambrace-enamel.png"
    mat.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    slot = len(mesh.materials)
    mesh.materials.append(mat)

    def boundaries(sign):
        return [
            (
                Vector((-0.067 if sign < 0 else 0.049, -0.006, 0.2845)),
                Vector((-0.16 * sign, 0.12, 1)),
            ),
            (
                Vector((-0.057 if sign < 0 else 0.040, 0.007, 0.320)),
                Vector((-0.36 * sign, -0.12, 1)),
            ),
        ]

    bm = bmesh.new()
    bm.from_mesh(mesh)
    for sign in (-1, 1):
        for point, normal in boundaries(sign):
            faces = [
                face
                for face in bm.faces
                if face.material_index < 4
                and all(
                    0.271 < v.co.z < 0.336 and sign * (v.co.x + 0.010) > 0.030
                    for v in face.verts
                )
            ]
            geometry = set(faces)
            for face in faces:
                geometry.update(face.edges)
                geometry.update(face.verts)
            bmesh.ops.bisect_plane(
                bm, geom=list(geometry), dist=1e-8, plane_co=point, plane_no=normal
            )
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    uv = mesh.uv_layers.active.uv
    for face in mesh.polygons:
        center = face.center * 1000
        if (
            face.material_index >= 4
            or not 0.275 < face.center.z < 0.333
            or abs(center.x + 10) < 37
        ):
            continue
        sign = 1 if center.x > 0 else -1
        lower, upper = boundaries(sign)
        if (face.center - lower[0]).dot(lower[1]) < -1e-7 or (
            face.center - upper[0]
        ).dot(upper[1]) > 1e-7:
            continue
        vertices = np.array([mesh.vertices[k].co[:] for k in face.vertices]) * 1000
        x, y, z = vertices.T
        levels = [285, 297, 309, 320, 327]
        cx = np.interp(
            z,
            levels,
            [-67, -66, -62.2, -57.5, -55] if sign < 0 else [49, 47, 44, 39, 37],
        )
        cy = np.interp(z, levels, [-7, 0, 4.8, 7.5, 7])
        u = 0.5 + np.arctan2(y - cy, (x - cx) * sign) / (2 * np.pi)
        if np.ptp(u) > 0.5:
            u[u < 0.5] += 1
        face.material_index = slot
        lo = (
            lower[0].z * 1000
            - lower[1].x * (x - lower[0].x * 1000)
            - lower[1].y * (y - lower[0].y * 1000)
        )
        hi = (
            upper[0].z * 1000
            - upper[1].x * (x - upper[0].x * 1000)
            - upper[1].y * (y - upper[0].y * 1000)
        )
        for loop, angle, height in zip(face.loop_indices, u, (z - lo) / (hi - lo)):
            uv[loop].vector = (angle, np.clip(height, 0.001, 0.999))


def rear_plates(obj, work, points):
    mesh = obj.data
    mapped = np.load(work / "camera-1.npy")
    faces = [list(p.vertices) for p in mesh.polygons if max(p.vertices) < len(points)]
    tree = BVHTree.FromPolygons(np.column_stack((mapped, points[:, 1])).tolist(), faces)
    positions = []
    triangles = []
    texcoords = []

    def camera(x, y):
        return (
            (899 - (450 + (x - 594) * 3 / (793 / 250))) / 900,
            1 - (1310 + (y - 1511) * 3 / (1392 / 420)) / 1360,
        )

    def on_surface(x, y, relief):
        uv = camera(x, y)
        hit, _, face, _ = tree.ray_cast((*uv, 0.4), (0, 0, -1), 0.8)
        if hit is None:
            return None
        ids = faces[face][:3]
        xy = mapped[ids]
        a, b, c = xy
        matrix = np.column_stack((a - c, b - c))
        bary = np.linalg.lstsq(matrix, np.array(uv) - c, rcond=None)[0]
        p = (
            points[ids[0]] * bary[0]
            + points[ids[1]] * bary[1]
            + points[ids[2]] * (1 - bary.sum())
        )
        p[1] += relief
        texcoords.append(uv)
        positions.append(tuple(p))
        return len(positions) - 1

    def seam(path, width, height):
        path = np.asarray(path, dtype=float)
        lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        t = np.linspace(0, lengths[-1], int(lengths[-1] / 3) + 1)
        line = np.column_stack([np.interp(t, lengths, path[:, i]) for i in range(2)])
        normals = np.gradient(line, axis=0)[:, ::-1]
        normals[:, 0] *= -1
        normals /= np.maximum(1.0e-8, np.linalg.norm(normals, axis=1)[:, None])
        rows = []
        for k, (p, n) in enumerate(zip(line, normals)):
            taper = max(0.10, min(1, k / 3, (len(line) - 1 - k) / 3))
            row = []
            for shift, lift in [
                (-1, 0.00015),
                (-0.64, 0.72),
                (0, 1),
                (0.64, 0.73),
                (1, 0.00015),
            ]:
                pt = p + n * shift * width * taper
                row.append(on_surface(*pt, 0.00012 + lift * height * taper))
            rows.append(row)
        for a, b in itertools.pairwise(rows):
            if None in a or None in b:
                continue
            for j in range(4):
                triangles.extend([(a[j], a[j + 1], b[j]), (a[j + 1], b[j + 1], b[j])])

    paths = [
        ([(505, 278), (534, 293), (557, 304), (577, 309), (585, 331)], 5.3, 0.0013),
        (
            [(480, 276), (500, 298), (530, 329), (541, 349), (550, 391), (559, 412)],
            3.7,
            0.00095,
        ),
        (
            [(455, 297), (470, 313), (491, 335), (504, 365), (522, 378), (537, 382)],
            3.8,
            0.00080,
        ),
        ([(490, 389), (514, 408), (533, 429), (544, 462), (560, 483)], 3.4, 0.00091),
        ([(491, 412), (511, 426), (525, 445), (534, 465)], 3.2, 0.00075),
        ([(575, 359), (578, 391), (585, 406)], 2.7, 0.00070),
        ([(487, 802), (494, 816), (508, 823), (521, 824)], 2.7, 0.00060),
        ([(445, 937), (460, 932), (479, 935), (499, 947)], 3.1, 0.00080),
        ([(444, 991), (456, 978), (466, 976), (475, 983), (482, 1001)], 2.8, 0.00070),
    ]
    for p, w, h in paths:
        seam(p, w, h)
        seam([(1170 - x, y) for x, y in p], w, h)
    for index, tri in enumerate(triangles):
        a, b, c = (np.array(positions[j]) for j in tri)
        if np.cross(b - a, c - a)[1] < 0:
            triangles[index] = (tri[0], tri[2], tri[1])
    plates = bpy.data.meshes.new("Stamped back, scapular and greave edges")
    plates.from_pydata(positions, [], triangles)
    plates.update()
    material = bpy.data.materials.new("MK85 · formed rear armour edges")
    material.use_nodes = True
    sample = material.node_tree.nodes.new("ShaderNodeTexImage")
    sample.image = bpy.data.images.load(str(work / "camera-1.jpg"), check_existing=True)
    sample.image.pack()
    sample.image.filepath = "//mk85-large-rear.jpg"
    pbr = material.node_tree.nodes["Principled BSDF"]
    pbr.inputs["Roughness"].default_value = 0.34
    pbr.inputs["Metallic"].default_value = 0.42
    material.node_tree.links.new(sample.outputs["Color"], pbr.inputs["Base Color"])
    plates.materials.append(material)
    uv = plates.uv_layers.new(name=mesh.uv_layers.active.name)
    uv.uv.foreach_set(
        "vector",
        np.asarray(
            [texcoords[v.vertex_index] for v in plates.loops], dtype="f"
        ).ravel(),
    )
    plates.polygons.foreach_set("use_smooth", np.ones(len(triangles), bool))
    item = bpy.data.objects.new(plates.name, plates)
    bpy.context.collection.objects.link(item)
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()


def main(work):
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    if abs(obj.dimensions.z - 0.260) > 0.0005:
        raise ValueError(
            "Open the archived 260 mm casting before fitting the large edition."
        )
    work.mkdir(parents=True, exist_ok=True)
    mesh = obj.data
    mesh.calc_loop_triangles()
    original = np.empty((len(mesh.vertices), 3), dtype="f")
    mesh.vertices.foreach_get("co", original.ravel())
    triangles = np.asarray([t.vertices[:] for t in mesh.loop_triangles], dtype="i")
    np.savez(work / "input.npz", points=original, faces=triangles)
    subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--with",
            "opencv-python-headless==5.1.0.95",
            "--with",
            "scipy==1.18.1",
            "python",
            str(Path(__file__).with_name("mk85-large-registration.py")),
            str(work),
        ],
        check=True,
    )
    points = projected_finish(obj, work)
    registered_body(obj, points, work)
    runpy.run_path(str(Path(__file__).with_name("mk85-large-armour.py")))[
        "front_inserts"
    ](obj, work, points)
    rear_plates(obj, work, points)
    runpy.run_path(str(Path(__file__).with_name("mk85-large-gauntlets.py")))[
        "articulated_shells"
    ](obj, work, points)
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    def original_hand(vertex):
        x, _, z = vertex.co
        return 0.248 < z < 0.300 and (x < -0.052 or x > 0.031)

    old_hands = [
        f
        for f in bm.faces
        if f.material_index < 4 and all(original_hand(v) for v in f.verts)
    ]
    hand_geometry = set(old_hands)
    for f in old_hands:
        hand_geometry.update(f.verts)
        hand_geometry.update(f.edges)
    bmesh.ops.bisect_plane(
        bm,
        geom=list(hand_geometry),
        dist=1e-7,
        plane_co=(0, 0, 0.2855),
        plane_no=(0, 0, 1),
        clear_inner=True,
    )
    old = [
        face
        for face in bm.faces
        if face.material_index > 3
        and obj.data.materials[face.material_index].name.startswith("Mark 85 · ")
    ]
    bmesh.ops.delete(bm, geom=old, context="FACES")
    bmesh.ops.bisect_plane(
        bm,
        geom=[*bm.verts, *bm.edges, *bm.faces],
        dist=1e-7,
        plane_co=(0, 0, 0.3798),
        plane_no=(0, 0, 1),
        clear_outer=True,
    )
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    leg_lacquer(obj)
    vambrace_lacquer(obj, work)
    runpy.run_path(str(Path(__file__).with_name("mk85-large-helmet.py")))["helmet"](
        obj, work
    )
    bpy.ops.object.material_slot_remove_unused()
    bpy.context.view_layer.update()
    assert (
        max(abs(a - b) for a, b in zip(obj.dimensions, (0.250, 0.180, 0.420))) < 0.00002
    )
    obj["edition"] = "Tongshifu MK85 large"
    obj["catalogueMassKg"] = 4.0
    obj["armourDetail"] = (
        "Continuous formed helmet, recessed optical slits, raised breastplate and triangular reactor, segmented shoulder and forearm shells, articulated closed fists and traced rear armour."
    )
    obj["catalogueDimensionsMm"] = [250, 180, 420]
    obj["surfaceRegistration"] = (
        "Owner-supplied large front, left profile, right profile and numbered rear casting"
    )
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_distance = 0.76
            area.spaces.active.region_3d.view_location = (0, 0, 0.21)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(work / "mk85.blend"), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=str(work / "mk85.glb"),
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_texcoords=True,
        export_tangents=False,
        export_animations=False,
        export_yup=True,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    print(
        "ENVELOPE",
        tuple(obj.dimensions),
        "MESH",
        len(obj.data.vertices),
        len(obj.data.polygons),
    )


if __name__ == "__main__":
    main(Path(sys.argv[-1]).resolve())
