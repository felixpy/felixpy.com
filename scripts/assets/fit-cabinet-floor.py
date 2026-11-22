from pathlib import Path

import bpy
from mathutils import Vector


STAND_HEIGHT = 0.520


def fit(scene):
    cabinet = scene.objects["Low-iron glass collection cabinet"]
    archive = next(item for item in cabinet.children if item.name.startswith("Photographic film and mounted"))
    if abs(archive.location.z - STAND_HEIGHT) < 1e-5:
        return False
    original_height = 0.616
    if abs(archive.location.z - original_height) > 1e-5:
        raise ValueError("Unrecognized collection cabinet plinth")
    drop = original_height - STAND_HEIGHT
    to_cabinet = cabinet.matrix_world.inverted()
    for part in cabinet.children:
        if part.type != "MESH":
            continue
        transform = to_cabinet @ part.matrix_world
        axis = transform.to_3x3().inverted() @ Vector((0, 0, drop))
        changes = []
        for vertex in part.data.vertices:
            position = transform @ vertex.co
            if 0.545 < position.z < 0.64:
                changes.append((vertex.index, 1.0))
            elif 0.89 < position.z < 0.945 and abs(abs(position.x) - 0.523) < 0.009:
                changes.append((vertex.index, 0.5))
        if changes:
            if part.data.users > 1 or part.data.library:
                part.data = part.data.copy()
            for index, weight in changes:
                part.data.vertices[index].co -= axis * weight
            part.data.update()
    archive.location.z = STAND_HEIGHT
    subjects = [o for o in cabinet.children_recursive if o.type == "EMPTY" and
                o.name.replace("_", " ").startswith(("Sun Wukong ·", "Tongshifu · Iron Man Mark 85"))]
    if len(subjects) != 2:
        raise ValueError("Expected two display figure roots")
    for subject in subjects:
        if abs(subject.location.z - original_height) > 1e-5:
            raise ValueError(f"Unexpected base elevation for {subject.name}")
        subject.location.z = STAND_HEIGHT
    scene.view_layers[0].update()
    return True


if __name__ == "__main__":
    import sys
    for filename in sys.argv[sys.argv.index("--") + 1:]:
        path = Path(filename).resolve()
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
        if fit(bpy.context.scene):
            bpy.context.preferences.filepaths.save_version = 0
            bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
