import json
from pathlib import Path

import bpy
from mathutils import Vector


def fit(scene):
    path = Path(__file__).resolve().parents[2] / "src/scene/ceiling-light-layout.json"
    x, y, z = json.loads(path.read_text())["mount"]
    mount = scene.objects["Recessed double-ring ceiling light · 300 mm"]
    target = Vector((x, -z, y))
    mount.location = mount.parent.matrix_world.inverted() @ target
    bpy.context.view_layer.update()
    outlet = scene.objects["Ceiling diffuser outlet"]
    assert outlet.parent == mount
    assert (outlet.matrix_world.translation - (target - Vector((0, 0, 0.093)))).length < 1e-5
    cove = next(o for o in mount.children if o.type == "LIGHT" and o.data.type == "POINT")
    assert (cove.matrix_world.translation - (target - Vector((0, 0, 0.095)))).length < 1e-5
    return tuple(round(v, 4) for v in mount.matrix_world.translation)
