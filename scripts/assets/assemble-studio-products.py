import argparse
import runpy
import sys
from pathlib import Path

import bpy

atelier = Path(__file__).resolve().parents[2] / ".review/atelier"
scene = bpy.context.scene


def read_parts(path, include=lambda name: True):
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (library, loaded):
        loaded.objects = [name for name in library.objects if include(name)]
    for part in loaded.objects:
        scene.collection.objects.link(part)
    return loaded.objects


def bounds(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE"}:
            continue
        evaluated = obj.evaluated_get(graph)
        if evaluated.type == "MESH":
            points.extend(
                evaluated.matrix_world @ v.co for v in evaluated.data.vertices
            )
        else:
            mesh = evaluated.to_mesh()
            try:
                points.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
            finally:
                evaluated.to_mesh_clear()
    return [f(point[i] for point in points) for i in range(3) for f in (min, max)]


def replace_branches(parent, branches, parts):
    branches = list(branches)
    removed = [
        obj for branch in branches for obj in [*branch.children_recursive, branch]
    ]
    before = bounds(removed)
    members = set(parts)
    for part in parts:
        if part.parent not in members:
            part.parent = parent
    bpy.context.view_layer.update()
    after = bounds(parts)
    if max(abs(a - b) for a, b in zip(before, after)) > 0.0006:
        raise ValueError(
            f"Source geometry does not fit {parent.name}: {before} vs {after}"
        )
    for obj in removed:
        bpy.data.objects.remove(obj, do_unlink=True)


def gltf_branch(parent, model):
    (branch,) = [
        obj
        for obj in parent.children
        if any(part.name.startswith(model) for part in obj.children)
    ]
    return branch


def fit_pencil(scene):
    mount = scene.objects["Mitsubishi 9850 HB"]
    source = (
        atelier.parents[1]
        / ".references/08-书籍与纸品/文具与工作记录/Mitsubishi 9850 pencil"
        / "Blender/mitsubishi-9850.blend"
    )
    name = "Mitsubishi 9850 HB · complete pencil"
    current = mount.instance_collection
    if (
        current and current.name == name and current.library
        and Path(bpy.path.abspath(current.library.filepath)).samefile(source)
    ):
        return
    parts = list(mount.children_recursive)
    if (
        current or not any("foil" in part.name for part in parts)
        or any(part.library or part.type not in {"MESH", "EMPTY"} for part in parts)
    ):
        raise ValueError("Unrecognized pencil assembly")
    with bpy.data.libraries.load(str(source), link=True, relative=True) as (library, loaded):
        if name not in library.collections:
            raise ValueError(f"Missing pencil collection in {source}")
        loaded.collections = [name]
    (collection,) = loaded.collections
    if len(collection.all_objects) != 7:
        raise ValueError("Expected both cedar slats, lead, enamel, foil, ferrule and eraser")
    before = bounds(parts)
    points = [
        mount.matrix_world @ part.matrix_local @ vertex.co
        for part in collection.all_objects for vertex in part.data.vertices
    ]
    after = [f(p[i] for p in points) for i in range(3) for f in (min, max)]
    if any(abs(a - b) > 0.00002 for a, b in zip(before, after)):
        raise ValueError(f"Pencil changed position: {before} vs {after}")
    mount.instance_type = "COLLECTION"
    mount.instance_collection = collection
    for part in reversed(parts):
        bpy.data.objects.remove(part, do_unlink=True)


def fit_pc_product(filename, collection, mounts):
    with bpy.data.libraries.load(str(atelier / "pc-components" / filename)) as (
        _,
        loaded,
    ):
        loaded.collections = [collection]
    originals = list(loaded.collections[0].all_objects)
    for i, mount in enumerate(mounts):
        fixed = any(part.get("studioOccluder") for part in mount.children_recursive)
        copies = {obj: obj.copy() if i < len(mounts) - 1 else obj for obj in originals}
        for obj, part in copies.items():
            scene.collection.objects.link(part)
            part.parent = copies.get(obj.parent)
            part["studioOccluder"] = fixed
        replace_branches(mount, mount.children, list(copies.values()))


def fit_workbench_and_cookware():
    runpy.run_path(str(Path(__file__).with_name("assemble-tolomeo.py")))["fit"](
        atelier, read_parts, replace_branches
    )
    runpy.run_path(str(Path(__file__).with_name("assemble-bench-tools.py")))["fit"](
        atelier
    )
    runpy.run_path(str(Path(__file__).with_name("assemble-wera.py")))["fit"](atelier)
    runpy.run_path(str(Path(__file__).with_name("fit-cz5-display.py")))["fit"](scene)

    (installed,) = [obj for obj in scene.objects if obj.get("product") == "PR-880"]
    opaque_roles = set()
    for obj in installed.children_recursive:
        if "coffeePart" in obj:
            surfaces = (
                [obj]
                if obj.type == "MESH"
                else [
                    child
                    for child in obj.children
                    if child.type == "MESH" and "coffeePart" not in child
                ]
            )
            if surfaces and all(surface.get("studioOccluder") for surface in surfaces):
                opaque_roles.add(obj["coffeePart"])
    path = atelier / "cookware-reference/field-coffee-master.blend"
    with bpy.data.libraries.load(str(path), link=False) as (library, loaded):
        loaded.objects = list(library.objects)
    (root,) = [obj for obj in loaded.objects if obj.get("product") == "PR-880"]
    parts = list(root.children_recursive)
    for obj in parts:
        scene.collection.objects.link(obj)
        obj["studioOccluder"] = obj.get("coffeePart") in opaque_roles
    replace_branches(installed, installed.children, parts)


def fit_cabinet_lens(filename, name):
    parent = scene.objects[name.replace(" ", "_").replace(".", "")]
    with bpy.data.libraries.load(str(atelier / "nikon-reference" / filename)) as (
        _,
        loaded,
    ):
        loaded.collections = [name]
    parts = list(loaded.collections[0].all_objects)
    fixed = any(obj.get("studioOccluder") for obj in parent.children_recursive)
    for obj in parts:
        scene.collection.objects.link(obj)
        obj["studioOccluder"] = fixed and not any(
            "Optical elements" in c.name for c in obj.users_collection
        )
    replace_branches(parent, parent.children, parts)


def fit_speakers():
    source = atelier / "kef-acoustics/kef-ls50.blend"
    assemblies = [obj for obj in scene.objects if "kefRole" in obj]
    if {obj["kefRole"] for obj in assemblies} != {"primary", "secondary"} or len(
        assemblies
    ) != 2:
        raise ValueError("Expected both KEF amplifier assemblies")
    for rear in assemblies:
        with bpy.data.libraries.load(str(source), link=False) as (library, loaded):
            loaded.objects = list(library.objects)
        cabinet = rear.parent
        installed = {
            obj: (obj["kefSurface"],) for obj in cabinet.children if "kefSurface" in obj
        }
        for obj in rear.children:
            if "kefSurface" in obj:
                installed[obj] = (obj["kefSurface"],)
            else:
                finish = obj.data.materials[0]["kefFinish"]
                installed[obj] = ("rear-" + finish, rear["kefRole"] + "-" + finish)
        if sum(map(len, installed.values())) != 16:
            raise ValueError(f"Incomplete {rear['kefRole']} KEF assembly")
        for original, keys in installed.items():
            pieces = [obj for obj in loaded.objects if obj.get("kefSurface") in keys]
            if not pieces:
                raise ValueError(f"Missing KEF source for {keys}")
            for obj in pieces:
                scene.collection.objects.link(obj)
                obj.hide_set(False)
                obj.hide_render = False
                obj["studioOccluder"] = bool(original.get("studioOccluder"))
                obj.data.materials[0] = original.data.materials[0]
            replace_branches(original.parent, [original], pieces)


def fit_cabinet_rollers():
    cabinet = scene.objects["Narrow storage cabinet"]
    doors = sorted(
        (
            obj
            for obj in cabinet.children
            if obj.name.startswith("Flush sliding cabinet door")
        ),
        key=lambda obj: obj.name,
    )
    if len(doors) != 2:
        raise ValueError("Expected two sliding leaves")
    groups = {
        "pocket-carriers": "Cowdroy TT40000 carriers",
        "pocket-fasteners": "Cowdroy pins and fixings",
    }
    path = atelier / "cabinet-running-gear/cowdroy-easy-roller.blend"
    for leaf in doors:
        wheels = [
            obj for obj in leaf.children if obj.name.startswith("TT40000 sheave axle")
        ]
        if len(wheels) != 2:
            raise ValueError(f"{leaf.name} needs two axle-centred sheaves")
        for wheel in wheels:
            wheel.rotation_mode = "XYZ"
            driver = wheel.driver_add("rotation_euler", 1).driver
            variable = driver.variables.new()
            variable.name = "travel"
            variable.targets[0].id = leaf
            variable.targets[0].data_path = "location[0]"
            driver.expression = f"(travel - ({leaf.location.x:.9f})) / 0.0068"
        parent = next(
            obj
            for obj in leaf.children
            if obj.name.startswith("Panel and routed finger pull")
        )
        parts = read_parts(
            path,
            lambda name: name.startswith(
                (
                    "TT40000 moulded",
                    "Captive steel axle",
                    "Countersunk fixing screw",
                    "Rolled shank and wood point",
                )
            ),
        )
        for role, label in groups.items():
            installed = next(
                obj for obj in parent.children if obj.name.startswith(label)
            )
            native = [obj for obj in parts if obj.get("cabinetPart") == role]
            for part in native:
                part["studioOccluder"] = False
            replace_branches(parent, [installed], native)


def fit_field_equipment(path, expected):
    installed = {
        obj["fieldItem"]: obj
        for obj in scene.objects
        if obj.get("fieldItem") in expected
    }
    with bpy.data.libraries.load(str(path.resolve()), link=False) as (library, loaded):
        loaded.objects = list(library.objects)
    sources = {
        obj["fieldItem"]: obj
        for obj in loaded.objects
        if obj.get("fieldItem") in expected
    }
    if expected.keys() != installed.keys() or expected.keys() != sources.keys():
        raise ValueError(f"Missing hiking equipment from {path.name}")
    for identifier, root in sources.items():
        old = installed[identifier]
        parts = list(root.children_recursive)
        if len(root.children) != expected[identifier] or (
            identifier.startswith("alpine-carbon-cork-") and root.get("lengthCm") != 61
        ):
            raise ValueError(f"Incomplete or extended field equipment: {identifier}")
        for obj in [root, *parts]:
            scene.collection.objects.link(obj)
        root.parent = old.parent
        root.matrix_world = old.matrix_world.copy()
        for part in parts:
            part["studioOccluder"] = False
        bpy.context.view_layer.update()
        before = bounds(obj for obj in old.children_recursive if obj.type == "MESH")
        after = bounds(obj for obj in parts if obj.type == "MESH")
        if max(abs(a - b) for a, b in zip(before, after)) > 0.0006:
            raise ValueError(f"Field equipment moved during assembly: {identifier}")
        for obj in [*old.children_recursive, old]:
            bpy.data.objects.remove(obj, do_unlink=True)


def fit_mounted_zoom(path):
    (parent,) = (
        obj
        for obj in scene.objects["Z mount flange"].children_recursive
        if obj.type == "EMPTY" and obj.name.split(".")[0] == "NIKKOR_Z_24-70mm_f28_S_II"
    )
    parts = read_parts(path)
    fixed = any(child.get("studioOccluder") for child in parent.children_recursive)
    for part in parts:
        part["studioOccluder"] = fixed and not part.name.startswith("Glass group ")
    replace_branches(parent, parent.children, parts)


def fit_bindings(path):
    installed = {obj["ISBN"]: obj for obj in scene.objects if "ISBN" in obj}
    with bpy.data.libraries.load(str(path), link=False) as (_, loaded):
        loaded.collections = ["Published bindings"]
    bindings = {
        obj["ISBN"]: obj for obj in loaded.collections[0].objects if "ISBN" in obj
    }
    if not bindings or bindings.keys() != installed.keys():
        raise ValueError(
            "The printed editions in the room and the binding master differ"
        )
    for identifier, book in bindings.items():
        seat = installed[identifier]
        parts = [part for part in book.children if part.name.split(".")[0] != "front"]
        installed_surfaces = {
            obj.name.split(" · ")[-1].split(".")[0]: obj for obj in seat.children
        }
        for part in parts:
            scene.collection.objects.link(part)
            surface = part.name.split(".")[0]
            model = installed_surfaces[surface]
            part["studioOccluder"] = bool(model.get("studioOccluder"))
            shader = part.material_slots[0].material.node_tree.nodes["Principled BSDF"]
            finish = model.material_slots[0].material.node_tree.nodes["Principled BSDF"]
            shader.inputs["Roughness"].default_value = finish.inputs[
                "Roughness"
            ].default_value
        for key in ("printed_pages", "source", "rear_reference"):
            if key in book:
                seat[key] = book[key]
        replace_branches(
            seat, [installed_surfaces["wrapper"], installed_surfaces["leaves"]], parts
        )


def remove_workbench_albums(room):
    removed = 0
    for title in ("STREAMING VIDEO", "SHORT-FORM VIDEO"):
        album = room.objects.get(title + " · cloth-bound album")
        if album:
            for child in list(album.children_recursive):
                bpy.data.objects.remove(child, do_unlink=True)
            bpy.data.objects.remove(album, do_unlink=True)
            removed += 1
    return removed


def fit_window_remote():
    remote = scene.objects["Window remote"]
    source = atelier.parents[1] / ".references/02-家具与灯具/家居控制器/Window remote and cradle/Blender/window-controller.blend"
    current = remote.instance_collection
    if current is None:
        previous = list(remote.children_recursive)
        if not previous or any(part.library for part in previous):
            raise ValueError("Unrecognised window remote assembly")
        with bpy.data.libraries.load(str(source), link=True, relative=True) as (_, linked):
            linked.collections = ["Studio six-key controller"]
        (controller,) = linked.collections
        if not controller or sum(part.name.startswith("Button_") for part in controller.all_objects) != 6:
            raise ValueError("Window remote requires six independent keys")
        remote.instance_type = "COLLECTION"
        remote.instance_collection = controller
        for part in reversed(previous):
            bpy.data.objects.remove(part, do_unlink=True)
    elif not current.library or Path(bpy.path.abspath(current.library.filepath)).resolve() != source:
        raise ValueError("Unexpected linked window remote")


def fit_desk_and_sill_objects():
    remove_workbench_albums(scene)
    fit_window_remote()
    sources = {
        "Desk portrait": "portrait-frame/fine-gold-4x6.blend",
        "Desk mat": "scabbard-study/scabbard-ii-xxl.blend",
        "Walnut window remote cradle": "window-cradle.blend",
        "Skandinavisk SKOG · forest scent": "skog/skog-20303.blend",
        "FELIX · working notebook": "felix-notebook/felix-working-notebook.blend",
        "Flight sprite proofs": "flight-sprite-proof/flight-sprite-proof.blend",
        "Introduction to Aerospace": "aerospace-notebook.blend",
    }
    for name, source in sources.items():
        parent = scene.objects[name]
        fixed = any(obj.get("studioOccluder") for obj in parent.children_recursive)
        native = read_parts(atelier / source)
        for obj in native:
            if obj.type == "MESH":
                obj["studioOccluder"] = fixed and not obj.get("productEnclosed", False)
        replace_branches(parent, parent.children, native)


def fit_aurora_bottle():
    runpy.run_path(str(Path(__file__).with_name("fit-aurora-bottle.py")))["fit"](scene)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--field-source", type=Path, default=atelier / "camp-field-equipment.blend"
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.destination.resolve() == Path(bpy.data.filepath).resolve():
        raise ValueError("Write the editable assembly to a separate file")
    fit_field_equipment(
        args.field_source,
        {"alpine-carbon-cork-left": 12, "alpine-carbon-cork-right": 12},
    )
    runpy.run_path(str(Path(__file__).with_name("peg-hammer-head.py")))["fit"](scene)
    fit_field_equipment(
        atelier / "talon-field-kit.blend",
        {
            "Osprey Talon 26 · Phantom Grey and Dark Charcoal": 16,
        },
    )
    runpy.run_path(str(Path(__file__).with_name("build-entry-bench.py")))["fit"](
        atelier
    )
    display = scene.objects["LG OLED evo G6 · OLED48G6PCA"]
    tv_parts = read_parts(
        Path(".references/04-桌面设备/显示器与桌面支架/LG OLED evo G6/Blender/lg-oled-g6.blend"),
        lambda name: name != "OLED module · active display surface",
    )
    for part in tv_parts:
        part["studioOccluder"] = part["assembly"] != "electronics"
    replace_branches(display, [gltf_branch(display, "OLED48G6PCA")], tv_parts)
    riser = scene.objects["Hexcal Studio"]
    riser_parts = read_parts(atelier / "hexcal-study/hexcal-studio.blend")
    for part in riser_parts:
        part["studioOccluder"] = True
    replace_branches(riser, [gltf_branch(riser, "Hexcal_Studio_SLT")], riser_parts)
    printer = scene.objects["Canon SELPHY CP1500"]
    postcard = runpy.run_path(str(Path(__file__).with_name("fit-selphy-proof.py")))
    print_parts = read_parts(postcard["SOURCE"])
    for part in print_parts:
        part["studioOccluder"] = not bool(part.get("selphyProof"))
    replace_branches(printer, printer.children, print_parts)
    postcard["fit"](scene)
    fit_mounted_zoom(atelier / "nikon-reference/nikkor-z24-70-sii.blend")
    runpy.run_path(str(Path(__file__).with_name("assemble-nikon-z8.py")))["fit"](
        atelier, read_parts, replace_branches
    )
    runpy.run_path(str(Path(__file__).with_name("assemble-screenbar.py")))["fit"](
        atelier, read_parts, replace_branches
    )
    fit_cabinet_lens("nikkor-z135-plena.blend", "NIKKOR Z 135mm f1.8 S Plena")
    runpy.run_path(str(Path(__file__).with_name("nikkor-noct.py")))["fit_cabinet"]()
    runpy.run_path(str(Path(__file__).with_name("fit-nikkor-displays.py")))["fit"](scene)
    fit_cabinet_lens("nikkor-z70-200-sii.blend", "NIKKOR Z 70-200mm f2.8 VR S II")
    fit_speakers()
    fit_pc_product(
        "rog-herculx-xh01.blend",
        "ROG Herculx XH01",
        [scene.objects["ROG Herculx XH01"]],
    )
    sockets = [obj for obj in scene.objects if obj.get("memorySocket")]
    if {obj["memorySocket"] for obj in sockets} != {"A1", "A2", "B1", "B2"} or len(
        sockets
    ) != 4:
        raise ValueError("Expected four populated DDR5 sockets")
    fit_pc_product("xpg-d50-fubuki.blend", "XPG D50 ROG Strix Fubuki DDR5", sockets)
    runpy.run_path(str(Path(__file__).with_name("assemble-strix.py")))["fit"](
        atelier, replace_branches
    )
    power = scene.objects["ROG power supply in rear cradle"]
    power_parts = read_parts(atelier / "pc-components/thor-psu.blend")
    for part in power_parts:
        part["studioOccluder"] = part.get("nativePart") in (
            "thor-1600-enamel",
            "thor-1600-shell",
        )
    replace_branches(power, power.children, power_parts)
    runpy.run_path(str(Path(__file__).with_name("snow-peak-home-camp.py")))["fit"](
        atelier
    )
    runpy.run_path(str(Path(__file__).with_name("snow-peak-mg153.py")))["fit"](scene)
    fit_workbench_and_cookware()
    stool = scene.objects["Artek Stool 60"]
    stool_parts = read_parts(atelier / "artek-60/stool-60.blend")
    for part in stool_parts:
        part["studioOccluder"] = part.name.startswith(("349 mm", "L-leg"))
    replace_branches(stool, stool.children, stool_parts)
    peripherals = atelier.parents[1] / ".references/04-桌面设备/键鼠与控制台"
    for parent_name, product, filename in [
        ("Mechanical keyboard", "ROG Azoth Extreme", "rog-azoth-extreme.blend"),
        ("Wireless mouse", "ROG Harpe Ace Extreme", "rog-harpe-extreme.blend"),
    ]:
        parent = scene.objects[parent_name]
        parts = read_parts(peripherals / product / "Blender" / filename)
        for part in parts:
            part["studioOccluder"] = False
        replace_branches(parent, parent.children, parts)
    fit_cabinet_rollers()
    runpy.run_path(str(Path(__file__).with_name("build-aeron-c7.py")))["fit"](atelier)
    runpy.run_path(str(Path(__file__).with_name("assemble-astral.py")))["fit"](atelier)
    runpy.run_path(str(Path(__file__).with_name("model-gr701-front-io.py")))["fit"](scene)
    runpy.run_path(str(Path(__file__).with_name("gr701-top-filter.py")))["fit"](scene)
    runpy.run_path(str(Path(__file__).with_name("gr701-cable-chamber.py")))["fit"](scene)
    runpy.run_path(str(Path(__file__).with_name("assemble-pc-cables.py")))["fit"](
        atelier
    )
    runpy.run_path(str(Path(__file__).with_name("assemble-ryuo-fans.py")))["fit"](
        atelier
    )
    runpy.run_path(str(Path(__file__).with_name("assemble-ams.py")))["fit"](atelier)
    archive = scene.objects["Photographic film and mounted transparencies"]
    archive_parts = read_parts(atelier / "film-archive/film-archive.blend")
    fixed = any(obj.get("studioOccluder") for obj in archive.children_recursive)
    for part in archive_parts:
        part["studioOccluder"] = fixed and not part.get("insideCassette", False)
    replace_branches(archive, archive.children, archive_parts)
    runpy.run_path(str(Path(__file__).with_name("fit-samsung-t7.py")))["fit"](scene, complete=True)
    fit_pencil(scene)
    cup = scene.objects["Glazed stoneware cup"]
    cup_parts = read_parts(atelier / "kinto-clk-151/kinto-clk-151.blend")
    cup_model = [
        obj
        for obj in cup.children
        if any(part.get("teaSurface") for part in obj.children_recursive)
    ]
    if len(cup_model) != 1:
        raise ValueError("Expected the ceramic mug, coaster and tea surface")
    for part in cup_parts:
        part["studioOccluder"] = "volumeMl" not in part
    replace_branches(cup, cup_model, cup_parts)
    vase = next(
        obj for obj in scene.objects if obj.get("product") == "KINTO LUNA 20332"
    )
    vessel_parts = read_parts(atelier / "kinto-luna/kinto-luna-20332.blend")
    surfaces = [obj for obj in vase.children if "sillPart" in obj]
    if {obj["sillPart"] for obj in surfaces} != {
        obj["sillPart"] for obj in vessel_parts
    }:
        raise ValueError("Vase and sill fittings differ")
    for part in vessel_parts:
        part["studioOccluder"] = part["sillPart"] == "v-brass"
    replace_branches(vase, surfaces, vessel_parts)
    rack = next(obj for obj in scene.objects if obj.get("product") == "camp-load-rack")
    rack_parts = read_parts(
        atelier / "camp-rack/equipment-rack.blend",
        lambda name: name != "Field wall · three perforated cassettes",
    )
    for part in rack_parts:
        part["studioOccluder"] = True
    replace_branches(rack, rack.children, rack_parts)
    fit_desk_and_sill_objects()
    runpy.run_path(str(Path(__file__).with_name("fit-dji-mic.py")))["fit"](scene)
    runpy.run_path(str(Path(__file__).with_name("assemble-mac-studio.py")))["fit"](
        atelier, read_parts, replace_branches
    )
    fit_aurora_bottle()
    runpy.run_path(str(Path(__file__).with_name("snow-peak-fireplace.py")))["fit"](
        atelier
    )
    fit_bindings(atelier / "published-bindings.blend")
    runpy.run_path(str(Path(__file__).with_name("fit-pocket-window-sash.py")))["fit"](scene)
    runpy.run_path(str(Path(__file__).with_name("movable-camp-gear.py")))["exclude_from_static_lighting"](scene)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.destination.resolve()), compress=True)


if __name__ == "__main__":
    main()
