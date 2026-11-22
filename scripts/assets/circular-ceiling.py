import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from product_workshop import Product, finishes


def model_circular_ceiling(output):
    lamp = Product("circular-ceiling")
    finishes.setdefault("halo", ("ffe8c7", 0.44, 0.0))
    slices = 128
    circumference = [
        (math.cos(i * math.tau / slices), math.sin(i * math.tau / slices))
        for i in range(slices)
    ]

    def form(name, finish, section):
        vertices = []
        rings = []
        for radius, drop in section:
            start = len(vertices)
            if radius == 0:
                vertices.append((0, -drop / 1000, 0))
            else:
                vertices.extend(
                    (radius * x / 1000, -drop / 1000, radius * z / 1000)
                    for x, z in circumference
                )
            rings.append(range(start, len(vertices)))
        faces = []
        for near, far in zip(rings, rings[1:]):
            for i in range(slices):
                j = (i + 1) % slices
                if len(near) == 1:
                    faces.append((near[0], far[i], far[j]))
                elif len(far) == 1:
                    faces.append((near[i], far[0], near[j]))
                else:
                    faces.append((near[i], far[i], far[j], near[j]))
        return lamp.surface(name, finish, vertices, faces, smooth=True)

    form(
        "Recessed central opal lens",
        "opal",
        [(0, 70.7), (44, 70.8), (85, 71.1), (109.8, 71.55), (112.3, 71.6)],
    )
    form(
        "Lower reflector well",
        "reflector",
        [(112.3, 71.6), (112.38, 72.1), (112.42, 73.1),
         (112.56, 89.3), (112.60, 90.2), (112.83, 90.72)],
    )
    form(
        "Inner tier and rolled lip",
        "shell",
        [(112.83, 90.72), (113.18, 91.0), (113.58, 91.0),
         (113.88, 90.80), (114.0, 90.42), (114.0, 89.45),
         (114.0, 39.5), (114.18, 38.75), (114.68, 38.25), (115.4, 38.20)],
    )
    form(
        "Annular opal light channel",
        "halo",
        [(115.4, 38.20), (116.0, 38.08), (125.5, 37.68),
         (138.6, 37.68), (147.9, 38.04), (148.40, 38.2)],
    )
    form(
        "Upper reflector well",
        "reflector",
        [(148.40, 38.2), (148.58, 38.7), (148.60, 39.3),
         (148.68, 53.35), (148.7, 54.1), (148.85, 54.65)],
    )
    form(
        "Outer rolled steel drum",
        "shell",
        [(148.85, 54.65), (149.18, 55.0), (149.58, 55.0),
         (149.87, 54.78), (150, 54.4), (150, 53.55), (150, 3.3),
         (149.86, 2.72), (149.49, 2.27), (148.87, 2.08), (147.9, 2.08),
         (143.6, 2.08), (143.14, 1.91), (143, 1.55), (143, 0.26),
         (142.7, 0), (140, 0), (0, 0)],
    )
    lamp.export(output)
    coatings = {
        "shell": ("Powder-coated steel", (0.81, 0.81, 0.79), 0.42, 0.055, 0),
        "reflector": ("Warm white enamel", (0.89, 0.87, 0.83), 0.44, 0.025, 0),
        "opal": ("Central opal diffuser", (0.89, 0.87, 0.82), 0.52, 0.0, 1.0),
        "halo": ("Annular opal diffuser", (0.86, 0.83, 0.76), 0.47, 0.0, 0.73),
    }
    for key, (label, color, roughness, metallic, emission) in coatings.items():
        obj = bpy.data.objects[f"{lamp.name}-{key}"]
        material = obj.data.materials[0].copy()
        material.name = f"Circular ceiling · {label}"
        material.diffuse_color = (*color, 1)
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Emission Color"].default_value = (1, 0.75, 0.43, 1)
        shader.inputs["Emission Strength"].default_value = emission
        if key == "shell":
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            grain = nodes.new("ShaderNodeTexNoise")
            grain.inputs["Scale"].default_value = 3900
            grain.inputs["Detail"].default_value = 1
            grain.inputs["Roughness"].default_value = 0.55
            links.new(nodes.new("ShaderNodeTexCoord").outputs["Object"], grain.inputs["Vector"])
            bump = nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = 0.14
            bump.inputs["Distance"].default_value = 0.000055
            links.new(grain.outputs["Fac"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        obj.data.materials[0] = material


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model_circular_ceiling(root / "public/media/models/fixtures")
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(root / ".review/atelier/circular-ceiling.blend"))
