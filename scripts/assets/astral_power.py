from pathlib import Path

import bpy

from product_workshop import finish_material


project = Path(__file__).resolve().parents[2]
source = (
    project / ".references/03-电脑硬件/显卡与支架/ROG Astral GeForce RTX 5090/Blender"
)


def archive_components(product):
    directory = source / "Components"
    directory.mkdir(parents=True, exist_ok=True)
    for finish, objects in product.parts.items():
        key = product.name + "-" + finish
        group = bpy.data.collections.new(key)
        for obj in objects:
            if not obj.data.materials:
                obj.data.materials.append(finish_material(finish))
            group.objects.link(obj)
        bpy.data.libraries.write(
            str(directory / (key + ".blend")), {group}, compress=True
        )
        bpy.data.collections.remove(group)
