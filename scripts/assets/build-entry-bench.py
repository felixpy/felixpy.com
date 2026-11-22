import math
import runpy
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import bpy
from mathutils import Matrix, Vector


scripts = Path(__file__).resolve().parent
project = scripts.parents[1]
review = project / ".review/atelier/entry-bench"
editable = review / "northstar-teak-42.blend"
product = "NorthStar Teak · 42 inch storage bench"
solids = runpy.run_path(str(scripts / "product_solids.py"))
sculpt = runpy.run_path(str(scripts / "vitrine-sculpt.py"))


def assembly():
    root = bpy.data.objects.new(product, None)
    bpy.context.collection.objects.link(root)
    root["product"] = "northstar-teak-42"
    root["externalSizeMm"] = [1066.8, 419.1, 457.2]
    root["shelfTopMm"] = 125.9
    finish = sculpt["finish"]
    teak = finish(
        "NorthStar · oiled teak, long grain and end grain",
        "b58152",
        rough=0.46,
        coat=0.12,
    )
    metal = finish(
        "NorthStar · brushed stainless fittings", "a9abad", metal=0.86, rough=0.34
    )
    rubber = finish("NorthStar · rubber levelling pads", "2d2c2a", rough=0.8)
    plug = finish("NorthStar · end-cut teak plugs", "90603a", rough=0.50)
    boards = []
    axes = {
        "seat": Matrix.Identity(4),
        "shelf": Matrix.Rotation(math.pi / 2, 4, "Z"),
        "post": Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1))),
    }

    def timber(name, center, dims, orientation, radius, holes=()):
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
        obj.name = name
        for vert in obj.data.vertices:
            for i, dim in enumerate(dims):
                vert.co[i] *= dim * 0.001
        obj.data.materials.append(teak)
        x, d, h = center
        obj.matrix_world = (
            Matrix.Translation((x * 0.001, -d * 0.001, h * 0.001)) @ axes[orientation]
        )
        obj.parent = root
        solids["edge"](obj, radius, 3)
        if holes:
            cuts = [
                solids["pin"](
                    "Counterbore", (cx, ch - 0.7, cd), (cx, ch + 4.1, cd), 4.0, teak, 24
                )
                for cx, cd, ch in holes
            ]
            solids["subtract"](obj, cuts)
        boards.append((obj, dims))
        return obj

    def pin(name, x, d, h1, h2, radius, mat, segments=32):
        obj = solids["pin"](name, (x, h1, d), (x, h2, d), radius, mat, segments)
        obj.parent = root
        return obj

    def screw(name, center, orientation):
        steps = 24
        rings = []
        for radius, h in [
            (2.35, -0.54),
            (3.25, -0.14),
            (3.22, 0.16),
            (2.87, 0.6),
            (2.35, 0.76),
        ]:
            rings.append(
                [
                    (
                        radius * math.cos(i * math.tau / steps),
                        radius * math.sin(i * math.tau / steps),
                        h,
                    )
                    for i in range(steps)
                ]
            )
        for size, z in [(1, 0.74), (0.63, -0.24)]:
            row = []
            for i in range(steps):
                a = i * math.tau / steps
                radius = min(
                    1.94, 0.43 / max(0.001, min(abs(math.sin(a)), abs(math.cos(a))))
                )
                row.append(
                    (size * radius * math.cos(a), size * radius * math.sin(a), z)
                )
            rings.append(row)
        pts = [tuple(v * 0.001 for v in p) for row in rings for p in row]
        faces = [
            (
                j * steps + i,
                j * steps + (i + 1) % steps,
                (j + 1) * steps + (i + 1) % steps,
                (j + 1) * steps + i,
            )
            for j in range(6)
            for i in range(steps)
        ]
        faces += [tuple(range(steps - 1, -1, -1)), tuple(range(6 * steps, 7 * steps))]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(pts, [], faces)
        for face in list(mesh.polygons)[: 4 * steps]:
            face.use_smooth = True
        mesh.materials.append(metal)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        x, d, h = center
        obj.location = (x * 0.001, -d * 0.001, h * 0.001)
        obj.rotation_euler = Vector(orientation).to_track_quat("Z", "Y").to_euler()
        obj.parent = root
        return obj

    def corner_bracket(name, x, d, side):
        y = 438.4 - 27
        profile = [(0, 1.45), (13.7, 1.45)]
        for j in range(1, 7):
            angle = (90 - j * 15) * math.pi / 180
            profile.append(
                (13.7 + 2.8 * math.cos(angle), -1.35 + 2.8 * math.sin(angle))
            )
        profile.extend([(16.5, -16.5), (15.05, -16.5), (15.05, -1.35)])
        for j in range(1, 7):
            angle = j * math.pi / 12
            profile.append(
                (13.7 + 1.35 * math.cos(angle), -1.35 + 1.35 * math.sin(angle))
            )
        profile.append((0, 0))
        shape = sculpt["Sculpture"](name)
        shape.rings(
            [[(x + side * u, y + v, d + z) for u, v in profile] for z in (-6.1, 6.1)],
            metal,
            False,
        )
        bracket = shape.finalize()
        bracket.parent = root
        screw(name + " · rail fastener", (x + side * 6.0, d, y - 0.05), (0, 0, -1))
        screw(name + " · upright fastener", (x + side * 15.00, d, y - 9), (-side, 0, 0))

    length, depth, top = 1066.8, 419.1, 457.2
    seat_count = 10
    gap = 3.15
    width = (depth - (seat_count - 1) * gap) / seat_count
    slat_depths = [
        (i - (seat_count - 1) * 0.5) * (width + gap) for i in range(seat_count)
    ]
    for i, d in enumerate(slat_depths):
        timber(
            f"Seat · teak plank {i + 1:02}",
            (0, d, top - 9.4),
            (length, width, 18.8),
            "seat",
            2.2,
        )

    for side in (-1, 1):
        for front in (-1, 1):
            timber(
                f"Seat apron · {side:+} {front:+}",
                (side * 256, front * 180.6, 425.4),
                (463, 26, 26),
                "seat",
                1.2,
            )
            timber(
                f"Shoe tray · front and back rail {side:+} {front:+}",
                (side * 256, front * 180.6, 103.3),
                (468.5, 19, 17.2),
                "seat",
                1.1,
            )
        for i in range(12):
            x = side * (54.95 + i * 37.4)
            timber(
                f"Shoe tray {side:+} · removable slat {i + 1:02}",
                (x, 0, 118.9),
                (380.2, 32.5, 14),
                "shelf",
                1.8,
            )

    for leg, x in enumerate((-500.8, -20.5, 20.5, 500.8)):
        bores = [(x, d, 411.4) for d in slat_depths if abs(d) < 172]
        timber(
            f"Seat batten · bored cross rail {leg + 1}",
            (x, 0, 424.9),
            (388.4, 29.4, 27.0),
            "shelf",
            1.2,
            bores,
        )
        for j, (_, d, h) in enumerate(bores):
            screw(
                f"Batten {leg + 1} · recessed head {j + 1}",
                (x, d, h + 3.45),
                (0, 0, -1),
            )
        for front in (-1, 1):
            d = front * 180.6
            label = f"Leg {leg + 1}{'F' if front > 0 else 'R'}"
            timber(
                label + " · teak upright",
                (x, d, 210.9),
                (401, 31.2, 32.4),
                "post",
                1.55,
            )
            pin(label + " · pressed insert", x, d, 9.7, 11.1, 6.65, metal)
            pin(label + " · levelling bolt", x, d, 5.4, 10, 3.1, metal, 20)
            pad = pin(label + " · rubber foot", x, d, 0, 7.2, 11.85, rubber, 40)
            solids["edge"](pad, 0.46, 2)
            dowel = solids["pin"](
                label + " · corner plug",
                (x, 103.3, d + front * 15.75),
                (x, 103.3, d + front * 16.36),
                4.2,
                plug,
                24,
            )
            dowel.parent = root
            toward = -1 if leg in (0, 2) else 1
            corner_bracket(
                label + " · stainless angle", x + toward * (-32.1), d, toward
            )
    return root, boards, teak


def fit(atelier):
    scene = bpy.context.scene
    receiver = next(
        obj for obj in scene.objects if obj.get("product") == "northstar-teak-42"
    )
    prior = list(receiver.children_recursive)
    was_occluder = any(item.get("studioOccluder") for item in prior)
    with bpy.data.libraries.load(
        str(atelier / "entry-bench/northstar-teak-42.blend"), link=False
    ) as (library, loaded):
        loaded.objects = list(library.objects)
    source = next(
        item for item in loaded.objects if item.get("product") == "northstar-teak-42"
    )
    for item in list(source.children):
        scene.collection.objects.link(item)
        item.parent = receiver
        item["studioOccluder"] = was_occluder
    for item in reversed(prior):
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.objects.remove(source, do_unlink=True)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    review.mkdir(parents=True, exist_ok=True)
    root, boards, material = assembly()
    with TemporaryDirectory() as folder:
        runpy.run_path(str(scripts / "entry-teak.py"))["bake"](boards, material, folder)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active.region_3d
            view.view_distance = 1.55
            view.view_location = (0, 0, 0.23)
            view.view_rotation = Vector((-1, 1.65, -0.8)).to_track_quat("-Z", "Y")
    bpy.ops.wm.save_as_mainfile(filepath=str(editable), compress=True)
    merged = solids["combine"]("Slats, rails and hardware", list(root.children))
    merged.parent = root
    path = project / "public/media/models/entry-bench.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_extras=True,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    subprocess.run(
        ["node", str(scripts / "pack-product-geometry.mjs"), str(path)], check=True
    )


if __name__ == "__main__":
    build()
