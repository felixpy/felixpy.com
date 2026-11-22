import runpy
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix
from mathutils.kdtree import KDTree


def load_collection(path, name):
    with bpy.data.libraries.load(str(path), link=False) as (_, loaded):
        loaded.collections = [name]
    collection = loaded.collections[0]
    if collection is None:
        raise ValueError(f"Missing authoring collection {name} in {path}")
    bpy.context.scene.collection.children.link(collection)
    bpy.context.view_layer.update()
    return collection


def surface_points(objects, relative_to):
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            matrix = relative_to @ evaluated.matrix_world
            points.extend(matrix @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    return points


def match_vertices(source, target, tolerance=0.000035):
    tree = KDTree(len(source))
    for i, point in enumerate(source):
        tree.insert(point, i)
    tree.balance()
    return {i for i, p in enumerate(target) if tree.find(p)[2] < tolerance}


def check_fit(source, target, name, tolerance=0.000035, envelope=0.00004):
    if not source or not target:
        raise ValueError(f"Missing geometry for {name}")
    for axis in range(3):
        for limit in (min, max):
            if (
                abs(limit(p[axis] for p in source) - limit(p[axis] for p in target))
                > envelope
            ):
                raise ValueError(f"Installed {name} envelope differs from its source")
    if len(match_vertices(target, source, tolerance)) != len(source):
        raise ValueError(f"Source {name} has points outside its installed surfaces")
    if len(match_vertices(source, target, tolerance)) != len(target):
        raise ValueError(f"Installed {name} has points outside the source surfaces")


def fit_instrument(atelier, target, identifier, name, count, envelope=0.00004):
    mounted = bpy.context.scene.objects[target]
    (old,) = [
        obj for obj in mounted.children if obj.get("benchInstrument") == identifier
    ]
    collection = load_collection(atelier / "bench-instruments.blend", name)
    (root,) = [
        obj for obj in collection.objects if obj.get("benchInstrument") == identifier
    ]
    if len(root.children) != count:
        raise ValueError(f"Expected {count} editable components in {name}")
    root.parent = mounted
    root.matrix_world = old.matrix_world.copy()
    bpy.context.view_layer.update()
    visible = [o for o in old.children_recursive if o.type == "MESH"]
    if old.type == "MESH":
        visible.append(old)
    check_fit(
        surface_points(root.children, Matrix.Identity(4)),
        surface_points(visible, Matrix.Identity(4)),
        name,
        0.00035,
        envelope,
    )
    fixed = any(part.get("studioOccluder") for part in visible)
    for part in root.children:
        part["studioOccluder"] = fixed
    for obj in [*old.children_recursive, old]:
        bpy.data.objects.remove(obj, do_unlink=True)


def fit(atelier):
    scene = bpy.context.scene
    fit_instrument(
        atelier, "KNIPEX Electronic Super Knips", "cutters", "KNIPEX 78 61 125", 7
    )
    fluke = runpy.run_path(str(Path(__file__).with_name("fit-fluke-115.py")))
    fluke["fit"](scene, complete=True)
    fit_switch_tester(scene)
    fit_caliper(atelier, scene)


def fit_switch_tester(scene):
    source = Path(__file__).resolve().parents[2] / (
        ".references/06-工坊与工具/电子测量与实验/Mechanical switch tester/Blender/mechanical-switch-tester.blend"
    )
    (holder,) = [
        part for part in scene.objects["Twelve-switch sampler"].children
        if part.get("benchInstrument") == "tester"
    ]
    current = holder.instance_collection
    if current and current.library and Path(bpy.path.abspath(current.library.filepath)).resolve() == source:
        return False
    old = list(holder.children)
    if current or holder.type != "EMPTY" or not old or any(
        part.type != "MESH" or part.children or part.library for part in old
    ):
        raise ValueError("Unrecognised installed switch tester")
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (_, linked):
        linked.collections = ["Glanaut 12-key Cherry MX switch tester"]
    (collection,) = linked.collections
    if not collection or len([part for part in collection.all_objects if "return spring" in part.name]) != 12:
        raise ValueError("Incomplete native MX mechanism library")
    holder.instance_type = "COLLECTION"
    holder.instance_collection = collection
    for part in old:
        bpy.data.objects.remove(part, do_unlink=True)
    return True


def fit_caliper(atelier, scene):
    board = scene.objects["Oak edged workshop pegboard"]
    if any(obj.get("instrument") == "Mitutoyo 530-104" for obj in board.children):
        return
    collection = load_collection(
        atelier / "workshop-fittings.blend", "Mitutoyo 530-104"
    )
    root = bpy.data.objects.new("Mitutoyo 530-104 · vernier caliper", None)
    scene.collection.objects.link(root)
    root.parent = board
    root.matrix_basis = Matrix.Translation((-0.0117, -0.1016, 0.05045))
    root["instrument"] = "Mitutoyo 530-104"
    for obj in collection.objects:
        original = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_basis = root.matrix_basis.inverted() @ original
    bpy.context.view_layer.update()
    legacy = any(
        obj.name == "Ground steel, peg hooks and instrument beam"
        for obj in board.children
    )
    metal_groups = (
        [("steel", "Ground steel, peg hooks and instrument beam")]
        if legacy
        else [
            ("beam", "Mitutoyo 530-104 · satin scale and carriage"),
            ("jaws", "Mitutoyo 530-104 · ground measuring jaws"),
        ]
    )
    for category, name in [("etch", "Engraved vernier graduations"), *metal_groups]:
        (installed,) = [obj for obj in board.children if obj.name == name]
        if category in ("beam", "jaws"):
            source = [
                obj
                for obj in collection.objects
                if obj.get("workshopBatch") == "steel"
                and (
                    ("measuring jaw" in obj.name or "knife-edge" in obj.name)
                    == (category == "jaws")
                )
            ]
        else:
            source = [
                obj
                for obj in collection.objects
                if obj.get("workshopBatch") == category
            ]
        world_to_board = board.matrix_world.inverted()
        points = surface_points(source, world_to_board)
        frame = world_to_board @ installed.matrix_world
        vertices = [frame @ v.co for v in installed.data.vertices]
        indices = match_vertices(points, vertices)
        check_fit(points, [vertices[i] for i in indices], name)
        for obj in source:
            obj["studioOccluder"] = bool(installed.get("studioOccluder"))
        if category != "steel":
            if len(indices) != len(vertices):
                raise ValueError(f"Unexpected neighbouring geometry in {name}")
            bpy.data.objects.remove(installed, do_unlink=True)
        else:
            bm = bmesh.new()
            try:
                bm.from_mesh(installed.data)
                faces = [
                    f for f in bm.faces if all(v.index in indices for v in f.verts)
                ]
                remaining = len(bm.faces) - len(faces)
                if not faces or not remaining:
                    raise ValueError(
                        "Unable to separate caliper from the pegboard steel"
                    )
                bmesh.ops.delete(bm, geom=faces, context="FACES")
                if len(bm.faces) != remaining:
                    raise ValueError(
                        "Unexpected removal from the mounted pegboard hardware"
                    )
                bm.to_mesh(installed.data)
                installed.data.update()
                installed.name = "Workshop · peg hooks and steel fittings"
            finally:
                bm.free()
