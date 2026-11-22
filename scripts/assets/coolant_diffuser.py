import bpy


def opal_finish():
    mat = bpy.data.materials.new("Ryuo opal diffusing sleeve")
    mat.use_nodes = True
    mat.diffuse_color = (0.62, 0.63, 0.65, 1)
    tree = mat.node_tree
    surface = tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = mat.diffuse_color
    surface.inputs["Roughness"].default_value = 0.43
    surface.inputs["Coat Weight"].default_value = 0.12
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "Sleeve travel"
    axes = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(uv.outputs["UV"], axes.inputs[0])
    phase = tree.nodes.new("ShaderNodeValue")
    phase.label = "Aura cycle (24 seconds)"
    driver = phase.outputs[0].driver_add("default_value").driver
    for name, path in [("fps", "render.fps"), ("base", "render.fps_base")]:
        variable = driver.variables.new()
        variable.name = name
        variable.type = "CONTEXT_PROP"
        variable.targets[0].context_property = "ACTIVE_SCENE"
        variable.targets[0].data_path = path
    driver.expression = "((frame - 1) * base / (fps * 24)) % 1"
    along = tree.nodes.new("ShaderNodeMath")
    along.operation = "MULTIPLY_ADD"
    along.inputs[1].default_value = -0.72
    along.inputs[2].default_value = 0.78
    tree.links.new(axes.outputs["Y"], along.inputs[0])
    travel = tree.nodes.new("ShaderNodeMath")
    travel.operation = "ADD"
    tree.links.new(along.outputs[0], travel.inputs[0])
    tree.links.new(phase.outputs[0], travel.inputs[1])
    colour = tree.nodes.new("ShaderNodeCombineColor")
    colour.mode = "HSV"
    colour.inputs[1].default_value = 0.78
    colour.inputs[2].default_value = 1.0
    hue = tree.nodes.new("ShaderNodeMath")
    hue.operation = "FRACT"
    tree.links.new(travel.outputs[0], hue.inputs[0])
    tree.links.new(hue.outputs[0], colour.inputs[0])
    tree.links.new(colour.outputs[0], surface.inputs["Emission Color"])
    intensity = tree.nodes.new("ShaderNodeValue")
    intensity.name = intensity.label = "Aura sleeve intensity"
    intensity.outputs[0].default_value = 0.95
    tree.links.new(intensity.outputs[0], surface.inputs["Emission Strength"])
    for node, x, y in [
        (uv, -1100, 160), (axes, -900, 160), (along, -700, 300), (phase, -700, 80),
        (travel, -500, 300), (hue, -300, 300), (colour, -100, 300),
        (intensity, -90, -40), (surface, 160, 260), (tree.nodes.get("Material Output"), 520, 260),
    ]:
        node.location = (x, y)
    return mat
