import runpy
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
bpy.ops.wm.read_factory_settings(use_empty=True)

titanium = finish("Drawn titanium · eggshell blast", "bcb7af", 0.86, 0.41)
polished = finish("Cold-formed titanium wire", "d0cbc2", 0.94, 0.245)
ivory = finish("Ivory moulded shell", "e4dcd0", 0.02, 0.45)
gasket = finish("Dock foot elastomer", "8a847e", 0.02, 0.67)
diffuser = finish("Frosted polycarbonate", "d4d6df", 0.015, 0.29, 0.32)
rail = finish("Brushed stainless handle", "c0bcb5", 0.94, 0.25)
grain = runpy.run_path(str(scripts / "product-grain.py"))["coat_grain"]
grain("Fine titanium tooling", [(polished, 0.045), (rail, 0.05)], True)
grain("MG-153 · bead-blasted titanium", [(titanium, 0.055)])
grain("Fine mould finish", [(ivory, 0.095), (diffuser, 0.045)])


def rounded_wire(shape, knots, radius, material, samples=6):
    points = []
    for i in range(len(knots) - 1):
        a, b, c, d = [
            Vector(knots[max(0, min(j, len(knots) - 1))])
            for j in (i - 1, i, i + 1, i + 2)
        ]
        span = (c - b).length
        entry = (c - a).normalized() * min(span, (b - a).length, span * 0.85)
        leave = (d - b).normalized() * min(span, (d - c).length, span * 0.85)
        for j in range(samples):
            t = j / samples
            points.append(
                b * (2 * t**3 - 3 * t * t + 1)
                + entry * (t**3 - 2 * t * t + t)
                + c * (-2 * t**3 + 3 * t * t)
                + leave * (t**3 - t * t)
            )
    shape.pipe(points + [knots[-1]], radius, material, sides=12)


mug_tools = runpy.run_path(str(scripts / "snow-peak-mg153.py"))
lamp_tools = runpy.run_path(str(scripts / "snow-peak-home-camp.py"))
review = project / ".review/atelier"
review.mkdir(parents=True, exist_ok=True)
target = project / "public/media/models/snow-peak-lantern-mugs.glb"
mug_only = "--mug-only" in sys.argv
lamp_only = "--lantern-only" in sys.argv
if mug_only and lamp_only:
    raise ValueError("Choose one product")
models = []
if not lamp_only:
    mug = mug_tools["build"](Sculpture, rounded_wire, finish, titanium, polished)
    mug_tools["save_product"](mug)
    models.append(mug)
if not mug_only:
    lanterns = lamp_tools["build"](
        Sculpture, rounded_wire, finish, ivory, diffuser, rail, gasket
    )
    lamp_tools["save_product"](lanterns)
    models.extend(lanterns)
if not mug_only and not lamp_only:
    for model, x in zip(models, [-0.09, 0.09, 0.09]):
        model.location.x = x
    bpy.ops.wm.save_as_mainfile(filepath=str(review / "snow-peak-lantern-mugs.blend"))
    for model in models:
        model.location.x = 0
if not lamp_only:
    for part in list(mug.children):
        if part.get("sealedCavity"):
            bpy.data.objects.remove(part, do_unlink=True)
for model in models:
    lamp_tools["bake_for_web"](model)
export = (
    review / "mg153-web.glb"
    if mug_only
    else review / "es080-web.glb"
    if lamp_only
    else target
)
bpy.ops.export_scene.gltf(
    filepath=str(export),
    export_format="GLB",
    export_extras=True,
    export_animations=False,
    export_meshopt_compression_enable=True,
    export_meshopt_extension="EXT_meshopt_compression",
)
subprocess.run(
    ["node", str(scripts / "pack-product-geometry.mjs"), str(export)], check=True
)
if mug_only or lamp_only:
    subprocess.run(
        [
            "node",
            str(scripts / "replace-camp-product.mjs"),
            str(target),
            str(export),
            "450" if mug_only else "lantern",
        ],
        check=True,
    )
