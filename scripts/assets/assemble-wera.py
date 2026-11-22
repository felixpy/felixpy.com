import runpy
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


TOOLS = {
    "Wera 335 · 0.8 x 4": 23,
    "Wera 350 PH · PH 1": 23,
    "Wera 367 TORX · TX 15": 22,
}
BATCHES = {
    "bright": (
        "Ground steel, peg hooks and instrument beam",
        "Workshop · peg hooks and steel fittings",
    ),
    "dark": ("Tempered tips and ESD tweezer leaves",),
    "yellow": ("Slotted driver size code",),
    "workshop-wera-body": ("Kraftform rigid handle cores",),
    "workshop-wera-grip": ("Kraftform soft grip inlays",),
    "workshop-wera-ph": ("Phillips driver size code",),
    "workshop-wera-print": ("Wera pad printing",),
}


def fit(atelier):
    helpers = runpy.run_path(str(Path(__file__).with_name("assemble-bench-tools.py")))
    board = bpy.context.scene.objects["Oak edged workshop pegboard"]
    inverse = board.matrix_world.inverted()
    library = atelier / "workshop-fittings.blend"
    tools = {}
    grouped = defaultdict(list)
    for name, count in TOOLS.items():
        collection = helpers["load_collection"](library, name)
        objects = list(collection.objects)
        if (
            len(objects) != count
            or len({obj["toolPartNumber"] for obj in objects}) != 1
        ):
            raise ValueError(f"Incomplete tool collection {name}")
        tools[name] = objects
        for obj in objects:
            grouped[obj["workshopBatch"]].append(obj)
    plans = []
    for kind, names in BATCHES.items():
        (installed,) = [obj for obj in board.children if obj.name in names]
        footprints = []
        source = []
        for objects in tools.values():
            part = [obj for obj in objects if obj["workshopBatch"] == kind]
            if not part:
                continue
            vertices = helpers["surface_points"](part, Matrix.Identity(4))
            source.extend(vertices)
            margin = 0.0004 if kind == "dark" else 0.003
            footprints.append(
                [
                    (
                        min(p[i] for p in vertices) - margin,
                        max(p[i] for p in vertices) + margin,
                    )
                    for i in range(3)
                ]
            )
        transform = inverse @ installed.matrix_world
        points = [transform @ vertex.co for vertex in installed.data.vertices]
        if kind == "bright":
            matched = helpers["match_vertices"](source, points)
            helpers["check_fit"](source, [points[i] for i in matched], installed.name)
        else:
            matched = {
                j
                for j, point in enumerate(points)
                if any(
                    all(low <= point[i] <= high for i, (low, high) in enumerate(bounds))
                    for bounds in footprints
                )
            }
            if kind == "dark" and not matched.issubset(
                helpers["match_vertices"](source, points)
            ):
                raise ValueError("Foreign tool geometry inside a driver tip")
        faces = {
            face.index
            for face in installed.data.polygons
            if all(i in matched for i in face.vertices)
        }
        shared = kind in {"bright", "dark"}
        complete = len(faces) == len(installed.data.polygons)
        if not faces or shared == complete:
            raise ValueError(f"Unexpected neighbouring geometry in {installed.name}")
        plans.append((installed, grouped[kind], faces))
    for name, objects in tools.items():
        (core,) = [
            obj
            for obj in objects
            if obj.name.startswith("Kraftform · moulded six-flat")
        ]
        handle = helpers["surface_points"]([core], Matrix.Identity(4))
        center = Vector(
            [
                (min(p[i] for p in handle) + max(p[i] for p in handle)) / 2
                for i in range(3)
            ]
        )
        root = bpy.data.objects.new(name, None)
        board.users_collection[0].objects.link(root)
        root.parent = board
        root.matrix_basis = Matrix.Translation(center)
        root.empty_display_size = 0.008
        root["instrument"] = name
        root["toolPartNumber"] = core["toolPartNumber"]
        for obj in objects:
            transform = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_basis = root.matrix_basis.inverted() @ transform
    for installed, objects, faces in plans:
        (slot,) = installed.material_slots
        for obj in objects:
            obj["studioOccluder"] = bool(installed.get("studioOccluder"))
            obj.material_slots[0].link = "OBJECT"
            obj.material_slots[0].material = slot.material
        if len(faces) == len(installed.data.polygons):
            bpy.data.objects.remove(installed, do_unlink=True)
        else:
            editable = bmesh.new()
            try:
                editable.from_mesh(installed.data)
                retained = len(editable.faces) - len(faces)
                bmesh.ops.delete(
                    editable,
                    geom=[face for face in editable.faces if face.index in faces],
                    context="FACES",
                )
                if len(editable.faces) != retained:
                    raise ValueError(f"Unexpected face removal from {installed.name}")
                editable.to_mesh(installed.data)
                installed.data.update()
            finally:
                editable.free()
    bpy.context.view_layer.update()
