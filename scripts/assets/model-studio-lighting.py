import runpy
import sys
from pathlib import Path

import bpy

scripts = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts))
from solarcycle import model_solarcycle
from tolomeo import model_tolomeo

root = scripts.parents[1]
out = root / "public/media/models/fixtures"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"

model_solarcycle(out)
model_tolomeo(out, clamp=True)
runpy.run_path(str(scripts / "circular-ceiling.py"))["model_circular_ceiling"](out)
runpy.run_path(str(scripts / "aj-floor.py"))["model_aj_floor"](out)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(root / ".review/atelier/fixture-masters.blend"))
