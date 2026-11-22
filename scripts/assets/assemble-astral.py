import bpy


CARD = "ROG Astral GeForce RTX 5090 · PCIe 5.0 slot"
HOUSING = "Diecast frame and thermal module"
DETAIL = "ROG Astral · close inspection"
FAN_MOUNTS = ("Axial-tech intake 1", "Axial-tech intake 2", "Axial-tech intake 3", "Fourth pass-through fan")


def parts(path):
    with bpy.data.libraries.load(str(path), link=False) as (data, imported):
        names = [name for name in data.objects if "impeller •" not in name]
        imported.objects = names.copy()
    return dict(zip(names, imported.objects))


def glow(material):
    if material and material.node_tree:
        shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader:
            strength = shader.inputs["Emission Strength"].default_value
            return strength > 0 and max(shader.inputs["Emission Color"].default_value[:3]) > 0
    return False


def remove_tree(node):
    for child in list(node.children):
        remove_tree(child)
    bpy.data.objects.remove(node, do_unlink=True)


def fit(atelier):
    scene = bpy.context.scene
    pc = atelier / "pc-components"
    card = scene.objects[CARD]
    housing = next(child for child in card.children if child.name == HOUSING)
    detail = scene.objects[DETAIL]
    mounts = [next(child for child in housing.children if child.name == name) for name in FAN_MOUNTS]
    mounted = {slot.material for obj in housing.children_recursive for slot in obj.material_slots if glow(slot.material)}
    if len(mounted) != 1:
        raise ValueError(f"Expected one installed Astral Aura material, found {len(mounted)}")
    aura = mounted.pop()
    source = parts(pc / "astral-5090.blend")
    standard = parts(pc / "astral-axial-fan.blend")["Fan rotor"]
    counter = parts(pc / "astral-axial-counter-fan.blend")["Fan rotor"]
    destination = housing.users_collection[0]

    def attach(original, parent, occludes):
        item = original.copy()
        destination.objects.link(item)
        item.parent = parent
        item.matrix_basis = original.matrix_basis.copy()
        name = original.name.split(".")[0]
        item["astralPart"] = name
        if item.type == "MESH":
            solid = True
            for slot in item.material_slots:
                material = slot.material
                if glow(material):
                    slot.link = "OBJECT"
                    slot.material = aura
                    solid = False
                elif material and material.node_tree:
                    shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
                    if shader:
                        alpha = shader.inputs["Alpha"]
                        solid &= not alpha.is_linked and alpha.default_value >= 1
            item["studioOccluder"] = occludes and solid
        for child in original.children:
            attach(child, item, occludes)
        return item

    source_housing = source[HOUSING]
    source_mounts = [source[name] for name in FAN_MOUNTS]
    for child in list(housing.children):
        if child not in mounts:
            remove_tree(child)
    for child in source_housing.children:
        if child not in source_mounts:
            attach(child, housing, True)
    for index, (mount, native) in enumerate(zip(mounts, source_mounts)):
        rotor = next(child for child in mount.children if child.name.startswith("Fan rotor"))
        mount.matrix_basis = native.matrix_basis.copy()
        for child in list(mount.children):
            if child != rotor:
                remove_tree(child)
        for child in native.children:
            attach(child, mount, False)
        for child in list(rotor.children):
            remove_tree(child)
        for child in (counter if index == 1 else standard).children:
            attach(child, rotor, True)
    for child in list(detail.children):
        remove_tree(child)
    for child in source[DETAIL].children:
        attach(child, detail, False)
    bpy.context.view_layer.update()
    pipes = [obj for obj in housing.children_recursive if obj.get("astralPart", "").startswith("Seated round heatpipe")]
    if len(pipes) != 8:
        raise ValueError(f"Expected eight independently editable heatpipes, found {len(pipes)}")
