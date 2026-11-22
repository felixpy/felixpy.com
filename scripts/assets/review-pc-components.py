from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2] / ".review/atelier/pc-components"
OUT = ROOT / "renders"
OUT.mkdir(exist_ok=True)


def xyz(v):
    return Vector((v[0], -v[2], v[1]))


def separate_components(scene):
    offsets = {
        "ROG Strix Z890-A Gaming WiFi S": (-0.34, 0.04, -0.08),
        "LGA1851 processor package": (-0.41, 0.04, -0.08),
        "Ryuo IV SLC 360 pump": (-0.58, 0.16, -0.09),
        "200 mm FEP tube pair": (-0.58, 0.16, -0.09),
        "Ryuo IV 394 mm offset radiator": (0, 0.31, 0),
        "ROG MF-12C 120 mm": (0, 0.18, 0),
        "ROG Strix Fan Model 14": (0, 0, 0.18),
        "ROG Astral RTX 5090": (-0.67, -0.11, 0.02),
        "XPG D50 ROG Strix Fubuki DDR5": (-0.41, 0.31, -0.12),
        "ROG Herculx XH01": (-0.59, -0.21, 0.11),
        "12V-2x6 GPU harness": (-0.51, -0.14, 0.17),
        "24-pin ATX harness": (-0.32, 0.02, 0.14),
        "ROG Thor 1600W Titanium III": (0, -0.12, -0.56),
    }
    for part in scene.collection.all_objects:
        if not part.instance_collection:
            continue
        offset = offsets.get(part.instance_collection.name)
        if offset:
            if "Rear exhaust" in part.name:
                offset = (0, 0, -0.15)
            if part.instance_collection.name == "XPG D50 ROG Strix Fubuki DDR5":
                bank = ("A1", "A2", "B1", "B2").index(part.name.rsplit(" • ", 1)[-1])
                offset = (offset[0], offset[1], offset[2] + 0.028 * bank)
            part.location += xyz(offset)


def render(source, shots):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / (source + ".blend")))
    scene = bpy.context.scene
    if any(lib.is_missing for lib in bpy.data.libraries):
        raise RuntimeError(f"Missing library in {source}")
    if any(
        img.source == "FILE" and not img.packed_file
        for img in bpy.data.images
        if img.filepath
    ):
        raise RuntimeError(f"External image in {source}")
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 92
    scene.world = bpy.data.worlds.new("Product photography studio")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.24, 0.255, 0.285, 1)
    bg.inputs[1].default_value = 0.52
    for key, pos, look, size, energy in [
        ("Umbrella", (-0.72, 0.85, 0.53), (0, 0, 0), 0.70, 14),
        ("Long strip", (0.47, 0.50, -0.59), (0, 0, 0), 0.47, 18),
        ("Silver edge", (-0.18, -0.65, -0.40), (0, 0, 0), 0.32, 8),
        ("Fill", (0.7, -0.42, 0.6), (0, 0, 0), 0.8, 7),
    ]:
        data = bpy.data.lights.new(key, "AREA")
        obj = bpy.data.objects.new(key, data)
        scene.collection.objects.link(obj)
        obj.location = xyz(pos)
        obj.rotation_euler = (
            (xyz(look) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
        data.energy = energy
        data.shape = "DISK"
        data.size = size
    cd = bpy.data.cameras.new("Product camera")
    cam = bpy.data.objects.new("Product camera", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cd.type = "ORTHO"
    cd.clip_start = 0.001
    for name, pos, look, frame, dims in shots:
        if name == "workstation-exploded":
            separate_components(scene)
        scene.render.filepath = str(OUT / (name + ".jpg"))
        cam.location = xyz(pos)
        cam.rotation_euler = (
            (xyz(look) - cam.location).to_track_quat("-Z", "Y").to_euler()
        )
        cd.ortho_scale = frame
        scene.render.resolution_x, scene.render.resolution_y = dims
        bpy.ops.render.render(write_still=True)


sets = {
    "astral-5090": [
        ("astral-front-io", (-0.38, -0.59, -0.59), (0, 0, -0.005), 0.505, (1080, 720)),
        ("astral-rear-edge", (0.46, 0.56, -0.39), (0, 0, 0), 0.505, (1080, 720)),
        ("astral-io", (0.038, 0.012, -0.8), (0.006, 0.004, -0.14), 0.191, (920, 540)),
        (
            "astral-gold-edge",
            (0.35, 0.10, -0.12),
            (0.06, 0.019, -0.082),
            0.138,
            (920, 480),
        ),
    ],
    "ryuo-pump": [
        ("ryuo-copper", (0.13, -0.20, -0.48), (0, 0, 0.046), 0.181, (820, 680)),
        ("ryuo-screen", (-0.33, 0.24, 0.46), (0, 0, 0.067), 0.181, (820, 680)),
    ],
    "xpg-d50-fubuki": [
        ("fubuki-ddr5", (-0.16, 0.1, 0.45), (-0.02, 0, 0), 0.164, (770, 870))
    ],
    "rog-herculx-xh01": [
        ("herculx-xh01", (0.11, 0.16, 0.46), (0, 0.064, 0), 0.248, (920, 680))
    ],
    "thor-psu": [
        ("thor-1600-rear", (-0.27, 0.21, -0.49), (0, 0, 0), 0.31, (920, 740)),
        ("thor-1600-modular", (0.29, -0.36, 0.47), (0, 0, 0), 0.31, (920, 740)),
    ],
    "gr701-workstation": [
        (
            "workstation-installed",
            (-0.98, 0.25, 0.53),
            (0, 0, -0.017),
            0.765,
            (940, 900),
        ),
        ("workstation-rear", (0.31, 0.21, -1.22), (0, -0.01, -0.08), 0.742, (900, 900)),
        (
            "workstation-exploded",
            (-1.46, 0.86, 1.55),
            (-0.25, 0.07, -0.08),
            1.88,
            (1400, 1000),
        ),
    ],
}
selection = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else list(sets)
for source in selection:
    render(source, sets[source])
