import runpy
import subprocess
from pathlib import Path

import bpy


assets = Path(__file__).resolve().parent
project = assets.parents[1]
target = project / "public" / "media" / "models" / "nikkor-z24-70-sii.glb"
lens_name = "NIKKOR Z 24-70mm f2.8 S II"

bpy.ops.wm.read_factory_settings(use_empty=True)
sculpt = runpy.run_path(str(assets / "vitrine-sculpt.py"))
optics = runpy.run_path(str(assets / "vitrine-optics.py"))
optics["build_lenses"](sculpt["Sculpture"], sculpt["finish"], {1})
lens = bpy.context.scene.objects[lens_name]
del lens["opticalVariant"]

receiver = sculpt["Sculpture"]("Z8 body-side mount receiver")
metal = sculpt["finish"]("Z8 mount receiver / satin nickel", "A6A8AA", 0.77, 0.31)
black = sculpt["finish"]("Z8 mount receiver / black casting", "242628", 0.21, 0.54)
receiver.turn(
    [(-7.0, 28), (-7.0, 34.0), (-5.0, 35.2), (-1.6, 35.2), (-1.0, 34.6), (-1.0, 28)],
    black,
    96,
)
receiver.turn(
    [(-1.0, 27.5), (-1.0, 34.5), (-0.7, 34.8), (-0.28, 34.8),
     (-0.08, 34.55), (-0.08, 27.63), (-0.24, 27.5), (-1.0, 27.5)],
    metal,
    128,
)
receiver.finalize()
target.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_animations=False,
    export_cameras=False,
    export_lights=False,
    export_yup=True,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(["node", str(assets / "pack-product-geometry.mjs"), str(target)], check=True)
