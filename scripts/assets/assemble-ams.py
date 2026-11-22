import runpy
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils.geometry import area_tri


def fit(atelier):
    printer = bpy.context.scene.objects["Bambu Lab H3C with AMS 3H"]
    assembly_name = "Bambu Lab AMS 3H · serviceable assembly"
    installed_root = bpy.context.scene.objects.get(assembly_name)
    if installed_root:
        if installed_root.parent != printer or not installed_root.children:
            raise ValueError(f"Expected {assembly_name} on the H3C")
        return installed_root
    shared = runpy.run_path(str(Path(__file__).with_name("assemble-bench-tools.py")))
    collection = shared["load_collection"](
        atelier / "h3c-components" / "ams-3h-editable.blend",
        "AMS 3H · canopy and carrier",
    )
    graph = bpy.context.evaluated_depsgraph_get()
    batches = {obj.name: obj for obj in printer.children}
    parts = defaultdict(list)
    for obj in collection.objects:
        (slot,) = obj.material_slots
        finish = slot.material.name.split(".")[0]
        parts[finish].append(obj)
    feeders = [obj for obj in collection.objects if obj.name.startswith("AMS 3H · first-stage feeder")]
    if len(feeders) != 5:
        raise ValueError("Expected five installed AMS 3H feeder stations")

    world_to_printer = printer.matrix_world.inverted()
    replacements = []
    for finish, objects in parts.items():
        installed = batches["H3C frame-" + finish]
        frame = world_to_printer @ installed.matrix_world
        points = []
        area = 0.0
        for obj in objects:
            evaluated = obj.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            try:
                vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
                points.extend(vertices)
                mesh.calc_loop_triangles()
                area += sum(
                    area_tri(*(vertices[i] for i in tri.vertices))
                    for tri in mesh.loop_triangles
                )
            finally:
                evaluated.to_mesh_clear()
        mounted = [frame @ v.co for v in installed.data.vertices]
        indices = shared["match_vertices"](points, mounted)
        shared["check_fit"](points, [mounted[i] for i in indices], installed.name)
        faces = [
            poly
            for poly in installed.data.polygons
            if all(i in indices for i in poly.vertices)
        ]
        installed_area = sum(
            area_tri(*(mounted[i] for i in poly.vertices)) for poly in faces
        )
        if abs(installed_area - area) > max(1e-7, area * 0.0005):
            raise ValueError(
                f"AMS surface area mismatch on {installed.name}: {installed_area} vs {area}"
            )
        replacements.append((installed, objects, {f.index for f in faces}))

    root = bpy.data.objects.new(assembly_name, None)
    collection.objects.link(root)
    root.parent = printer
    for installed, objects, indices in replacements:
        (slot,) = installed.material_slots
        for obj in objects:
            obj.parent = root
            obj.material_slots[0].link = "OBJECT"
            obj.material_slots[0].material = slot.material
            obj["studioOccluder"] = bool(installed.get("studioOccluder"))
        if len(indices) == len(installed.data.polygons):
            bpy.data.objects.remove(installed, do_unlink=True)
        else:
            mesh = bmesh.new()
            try:
                mesh.from_mesh(installed.data)
                discarded = [f for f in mesh.faces if f.index in indices]
                bmesh.ops.delete(mesh, geom=discarded, context="FACES")
                mesh.to_mesh(installed.data)
                installed.data.update()
            finally:
                mesh.free()
    bpy.context.view_layer.update()
    return root
