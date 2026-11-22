import math
import runpy
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


assets = Path(__file__).resolve().parent
project = assets.parents[1]
sys.path.insert(0, str(assets))
from blender_mesh import write_mesh

sculpt = runpy.run_path(str(assets / "vitrine-sculpt.py"))
Sculpture, finish = sculpt["Sculpture"], sculpt["finish"]
source = (
    project
    / ".references/05-摄影与陈列/相机与镜头/Nikon HB-117 lens hood/Blender/nikon-hb-117-lens-hood.blend"
)
output = project / "public/media/models/handheld"
seat = 132
window_half = 21
travel = 17.55


def polar(angle, z, r):
    a = math.radians(angle)
    return r * math.sin(a), r * math.cos(a), seat + z


def radius(z):
    return 43.90 + 0.143 * z


def reach(angle):
    a = abs((angle + 90) % 180 - 90)
    stations = [
        (0, 45),
        (14, 44.8),
        (25, 41.2),
        (36, 30.0),
        (49, 16.1),
        (56, 13.7),
        (66, 17.9),
        (83, 25.4),
        (90, 26),
    ]
    for (lo, z0), (hi, z1) in zip(stations, stations[1:]):
        if a <= hi:
            t = (a - lo) / (hi - lo)
            return z0 + (z1 - z0) * (t * t * (3 - 2 * t))
    return stations[-1][1]


def arc(shape, material, start, end, profile, count=None):
    n = count or max(3, math.ceil(abs(end - start) / 2))
    rows = [
        [polar(start + (end - start) * i / n, z, r) for z, r in profile]
        for i in range(n + 1)
    ]
    shape.rings(rows, material, close=abs(end - start) < 359)


def shell(shape, resin):
    angles = sorted(set(range(-180, 180, 2)) | {-21, 21, -20.5, 20.5, -19.5, 19.5})
    vertices, faces = [], []
    for angle in angles:
        top = reach(angle)
        s = min(1.0, max(0.0, (window_half - abs(angle)) / 1.65))
        rounded = 1.25 * (1 - math.sqrt(1 - (1 - s) ** 2))
        low = 2.0 + rounded
        high = min(22.1, top - 2.0) - rounded
        zs = (0, 0.27, low, high, top - 0.52, top - 0.18, top)
        for inner in (False, True):
            for i, z in enumerate(zs):
                outer = radius(z)
                bevel = (0.18, 0, 0, 0, 0, 0.10, 0.38)[i]
                vertices.append(
                    polar(angle, z, outer - 1.52 + bevel if inner else outer - bevel)
                )
    n = len(angles)

    def at(i, layer, row):
        return (i % n) * 14 + layer * 7 + row

    for i, a in enumerate(angles):
        j = (i + 1) % n
        cut = -window_half <= a < window_half
        for k in range(6):
            if k == 2 and cut:
                continue
            for layer in (0, 1):
                faces.append(
                    (
                        at(i, layer, k),
                        at(j, layer, k),
                        at(j, layer, k + 1),
                        at(i, layer, k + 1),
                    )
                )
        for k in (0, 2, 3, 6) if cut else (0, 6):
            faces.append((at(i, 0, k), at(j, 0, k), at(j, 1, k), at(i, 1, k)))
        if abs(a) == window_half:
            faces.append((at(i, 0, 2), at(i, 0, 3), at(i, 1, 3), at(i, 1, 2)))
    shape.add(vertices, faces, resin)


def mold_grain(materials):
    size = 192
    random = np.random.default_rng(117)
    spectrum = np.fft.rfft2(random.standard_normal((size, size)))
    freq = np.fft.fftfreq(size)[:, None] ** 2 + np.fft.rfftfreq(size)[None, :] ** 2
    heights = np.fft.irfft2(spectrum * np.exp(-14 * freq))
    heights *= 0.30 / heights.std()
    x = (np.roll(heights, 1, axis=1) - np.roll(heights, -1, axis=1)) / 2
    y = (np.roll(heights, 1, axis=0) - np.roll(heights, -1, axis=0)) / 2
    length = np.sqrt(1 + x * x + y * y)
    rgba = np.stack((x / length, y / length, 1 / length, np.ones_like(x)), axis=-1)
    image = bpy.data.images.new(
        "HB-117 fine injection texture", size, size, alpha=False, is_data=True
    )
    image.pixels.foreach_set((rgba * 0.5 + 0.5).astype(np.float32).ravel())
    image.file_format = "PNG"
    image.filepath_raw = str(project / "public/media/materials/hb117-mold-normal.png")
    image.save()
    image.pack()
    for mat in materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        sample = nodes.new("ShaderNodeTexImage")
        sample.image = image
        normal = nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value = 0.63
        links.new(sample.outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"])


def cylindrical_uv(obj):
    mesh = obj.data
    uv = mesh.uv_layers.new(name="14 mm mold grain")
    for face in mesh.polygons:
        coords = [
            mesh.vertices[mesh.loops[i].vertex_index].co for i in face.loop_indices
        ]
        angles = [math.atan2(v.x, v.z) / math.tau for v in coords]
        wraps = max(angles) - min(angles) > 0.5
        for idx, angle, pos in zip(face.loop_indices, angles, coords):
            uv.data[idx].uv = (
                20 * (angle + (1 if wraps and angle < 0 else 0)),
                -pos.y / 0.014,
            )


def build():
    resin = finish("HB-117 · textured black molded resin", "262627", 0.0, 0.66)
    lining = finish("HB-117 · matte internal light traps", "161719", 0.0, 0.87)
    slide = finish("HB-117 · sliding filter cover", "29292a", 0.0, 0.61)
    ink = finish("HB-117 · light grey identification", "dededb", 0, 0.69)
    collar = finish("HB-117 · satin bayonet hardware", "232425", 0.04, 0.44)
    mold_grain((resin, slide))
    barrel = Sculpture("Four-petal shroud with through filter aperture")
    shell(barrel, resin)
    race = Sculpture("Bayonet ring and opposed pairs of receiving ramps")
    arc(
        race,
        collar,
        -180,
        180,
        [(0.2, 42.32), (0.2, 43.32), (1.85, 43.72), (1.85, 42.44)],
        180,
    )
    for start in (-160, -70, 20, 110):
        arc(
            race,
            collar,
            start,
            start + 38,
            [(2.3, 42.74), (2.75, 41.23), (3.85, 41.14), (4.05, 42.96)],
        )
    ribs = Sculpture("Interior light-trap serrations")
    for j in range(23):
        z = 7.0 + 1.61 * j
        spans = [a for a in range(-180, 181) if abs(a) >= 23 and z + 0.95 < reach(a)]
        start = None
        for a in range(-180, 182):
            if a not in spans and start is not None:
                if a - 1 > start:
                    arc(
                        ribs,
                        lining,
                        start,
                        a - 1,
                        [
                            (z - 0.44, radius(z - 0.44) - 1.45),
                            (z - 0.06, radius(z) - 1.96),
                            (z + 0.08, radius(z) - 1.97),
                            (z + 0.4, radius(z + 0.4) - 1.45),
                        ],
                    )
                start = None
            elif a in spans and start is None:
                start = a
    shutter = Sculpture("Captive curved filter-window shutter")
    arc(
        shutter,
        slide,
        -20.65,
        20.65,
        [
            (2.35, radius(2.35) - 2.05),
            (2.60, radius(2.60) - 1.84),
            (21.62, radius(21.62) - 1.84),
            (21.79, radius(21.79) - 2.05),
            (21.75, radius(21.75) - 2.66),
            (2.35, radius(2.35) - 2.66),
        ],
    )
    lever = Sculpture("Window finger ledge and molded travel arrow")
    arc(
        lever,
        slide,
        -18.9,
        18.9,
        [
            (2.6, radius(2.6) - 1.95),
            (2.6, radius(2.6) + 0.35),
            (2.95, radius(2.95) + 0.62),
            (3.8, radius(3.8) + 0.62),
            (4.15, radius(4.15) - 1.95),
        ],
    )
    lever.add(
        [
            polar(a, z, radius(z) - 1.80)
            for a, z in ((-1.7, 5.8), (0, 7.85), (1.7, 5.8))
        ],
        [(0, 1, 2)],
        collar,
        False,
    )
    guides = Sculpture("Molded side guide channels and end stops")
    for low, high in ((0.7, 3.3), (20.9, 23.4)):
        arc(
            guides,
            collar,
            -22.3,
            22.3,
            [
                (low, radius(low) - 3.3),
                (low, radius(low) - 3.0),
                (high, radius(high) - 3.0),
                (high, radius(high) - 3.3),
            ],
        )
    for a in (-1, 1):
        arc(
            guides,
            collar,
            a * 19.2,
            a * 22.0,
            [
                (1.58, radius(1.58) - 3.28),
                (1.65, radius(1.65) - 2.97),
                (39.2, radius(39.2) - 2.97),
                (39.2, radius(39.2) - 3.28),
            ],
        )
    grip = Sculpture("Bayonet grip flutes and separate lock release")
    for center in (-90, 90):
        for i in range(-16, 17):
            a = center + i * 1.65
            arc(
                grip,
                collar,
                a - 0.38,
                a + 0.38,
                [
                    (0.8, radius(0.8) - 0.04),
                    (0.88, radius(0.88) + 0.20),
                    (6.65, radius(6.65) + 0.20),
                    (6.85, radius(6.85) - 0.04),
                ],
                2,
            )
    arc(
        grip,
        collar,
        -104,
        -91,
        [
            (1.23, radius(1.23)),
            (1.23, radius(1.23) + 0.43),
            (5.37, radius(5.37) + 0.44),
            (5.6, radius(5.6)),
        ],
    )
    for z in (2.2, 3.05, 3.90, 4.75):
        arc(
            grip,
            resin,
            -102.8,
            -92.2,
            [
                (z - 0.22, radius(z) + 0.42),
                (z, radius(z) + 0.68),
                (z + 0.19, radius(z) + 0.42),
            ],
        )
    marks = Sculpture("Identification print, lock and alignment marks")
    marks.label(
        "HB-117  ø77  MADE IN JAPAN",
        2.08,
        lambda x, y: polar(-x / 46 * 180 / math.pi, 24.4 + y, radius(24.4 + y) + 0.045),
        ink,
    )
    marks.label(
        "Nikon",
        2.72,
        lambda x, y: polar(
            179 - x / 45 * 180 / math.pi, 9.1 + y, radius(9.1 + y) + 0.05
        ),
        ink,
        True,
    )
    for azimuth in (0, 180):
        arc(
            marks,
            ink,
            azimuth - 0.65,
            azimuth + 0.65,
            [
                (0.54, radius(0.54) + 0.035),
                (0.56, radius(0.56) + 0.075),
                (1.39, radius(1.39) + 0.075),
                (1.42, radius(1.42) + 0.035),
            ],
        )
        arc(
            marks,
            ink,
            azimuth + 24.4,
            azimuth + 25.6,
            [
                (3.0, radius(3) + 0.035),
                (3.04, radius(3.04) + 0.075),
                (5.2, radius(5.2) + 0.075),
                (5.24, radius(5.24) + 0.035),
            ],
        )
    collection = bpy.data.collections.new("HB-117 service parts")
    bpy.context.scene.collection.children.link(collection)
    products = {}
    for shape, key in (
        (barrel, "shell"),
        (race, "mount"),
        (ribs, "baffle"),
        (shutter, "slide"),
        (lever, "lever"),
        (guides, "guides"),
        (grip, "release"),
        (marks, "ink"),
    ):
        obj = shape.finalize()
        if key in ("shell", "slide", "lever"):
            cylindrical_uv(obj)
        bpy.context.collection.objects.unlink(obj)
        collection.objects.link(obj)
        products[key] = obj
    moving = products["slide"]
    products["lever"].parent = moving
    moving["opening_mm"] = 0.0
    moving.id_properties_ui("opening_mm").update(
        min=0, max=travel, description="Filter-access travel toward the front petal"
    )
    for axis, factor in ((1, -0.001), (2, 0.000143)):
        driver = moving.driver_add("location", axis).driver
        driver.type = "SCRIPTED"
        variable = driver.variables.new()
        variable.name = "opening"
        variable.targets[0].id = moving
        variable.targets[0].data_path = '["opening_mm"]'
        driver.expression = f"opening * {factor}"
    bpy.context.view_layer.update()
    for key, obj in products.items():
        print(key, write_mesh(obj, output / ("hb117-" + key + ".mesh")))
    scene = bpy.context.scene
    scene.name = "Nikon HB-117"
    scene.unit_settings.system = "METRIC"
    scene["reference"] = "https://www.nikonusa.com/p/hb-117-lens-hood/4295"
    scene["guide"] = "NIKKOR Z 24-70mm f/2.8 S II Reference Guide, pp. 15–16 and 21–24"
    scene["assembly"] = "Mounted with the filter window on top, shutter closed"
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_location = (0, -0.153, 0)
            view.region_3d.view_distance = 0.18
            view.region_3d.view_rotation = Vector((0.6, -0.63, 0.55)).to_track_quat(
                "Z", "Y"
            )
            view.clip_start = 0.00025
            view.shading.color_type = "MATERIAL"
            view.overlay.show_floor = False
            view.overlay.show_axis_x = False
            view.overlay.show_axis_y = False
    bpy.context.preferences.filepaths.save_version = 0
    source.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
