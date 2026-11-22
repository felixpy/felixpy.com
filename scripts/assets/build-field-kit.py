import runpy
import subprocess
from pathlib import Path

import bpy


scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
review = project / ".review" / "atelier"
review.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
shared = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
sculpture, finish = shared["Sculpture"], shared["finish"]
textile = runpy.run_path(str(scripts / "field-textile.py"))["textile"]
talon = runpy.run_path(str(scripts / "field-talon.py"))
harness = runpy.run_path(str(scripts / "field-harness.py"))["build_harness"]
outsole = runpy.run_path(str(scripts / "field-outsole.py"))["build_outsole"]
tread = runpy.run_path(str(scripts / "field-tread.py"))["build_tread"]
heel = runpy.run_path(str(scripts / "field-heel.py"))["build_heel"]
closure = runpy.run_path(str(scripts / "field-boa.py"))["build_closure"]
talon["build_talon"](sculpture, finish, textile, harness)
talon["build_hook"](sculpture, finish)
runpy.run_path(str(scripts / "field-jieshan.py"))["build_jieshan"](
    sculpture, finish, textile, outsole, tread, heel, closure
)
runpy.run_path(str(scripts / "land-breeze-case.py"))["packed_tent"](
    sculpture, finish, textile
)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.ops.wm.save_as_mainfile(filepath=str(review / "talon-field-kit.blend"))
target = project / "public" / "media" / "models" / "talon-field-kit.glb"
bpy.ops.export_scene.gltf(
    filepath=str(target),
    export_format="GLB",
    export_extras=True,
    export_texcoords=True,
    export_tangents=False,
    export_animations=False,
    export_cameras=False,
    export_lights=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(target)], check=True
)
subprocess.run(["node", str(scripts / "pack-field-kit.mjs"), str(target)], check=True)
print(f"FIELD_EXPORT={target} ({target.stat().st_size} bytes)")
