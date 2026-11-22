import math
import runpy
import sys
from pathlib import Path

import bpy
import bmesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from blender_parts import xyz, block, export_batch

OUT = ROOT / "public/media/models/capture"
SOURCE = ROOT / ".review/atelier/capture-controls"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)

FINISH = {
    "titanium": ("Warm bead-blasted aluminium", (0.275, 0.256, 0.227), 0.83, 0.33),
    "abs": ("Injection-moulded graphite", (0.028, 0.030, 0.032), 0.08, 0.47),
    "rubber": ("Grip silicone", (0.014, 0.015, 0.015), 0.01, 0.78),
    "silver": ("Turned retaining edge", (0.49, 0.51, 0.50), 0.89, 0.28),
    "frost": ("Opal bias-light diffuser", (0.80, 0.82, 0.78), 0.04, 0.42),
    "lens": ("Microprismatic exit optic", (0.77, 0.73, 0.64), 0.09, 0.26),
    "glass": ("Smoked cover glass", (0.008, 0.012, 0.014), 0.23, 0.18),
    "shell": ("Warm white ABS", (0.82, 0.82, 0.78), 0.03, 0.44),
    "seam": ("Warm grey separation line", (0.37, 0.38, 0.36), 0.08, 0.59),
    "keys": ("Glossy PBT keycap", (0.013, 0.016, 0.020), 0.1, 0.23),
}


def rectangle(w, h, r):
    points = []
    for cx, cy, begin in [
        (w / 2 - r, h / 2 - r, 0),
        (-w / 2 + r, h / 2 - r, 90),
        (-w / 2 + r, -h / 2 + r, 180),
        (w / 2 - r, -h / 2 + r, 270),
    ]:
        for i in range(10):
            a = math.radians(begin + i * 10)
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return points


class Device:
    def __init__(self, name):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.name = name
        self.surfaces = {}
        self.collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(self.collection)

    def add(self, obj, finish):
        if finish not in self.surfaces:
            label, color, metal, rough = FINISH[finish]
            if self.name == "stream-deck-neo" and finish == "rubber":
                label, color, rough = "Grey silicone desk pad", (0.52, 0.56, 0.56), 0.86
            mat = bpy.data.materials.new(label)
            mat.diffuse_color = (*color, 1)
            mat.use_nodes = True
            shader = mat.node_tree.nodes["Principled BSDF"]
            for key, value in [
                ("Base Color", (*color, 1)),
                ("Metallic", metal),
                ("Roughness", rough),
            ]:
                shader.inputs[key].default_value = value
            if finish in ["lens", "frost"]:
                shader.inputs["Emission Color"].default_value = (1, 0.82, 0.62, 1)
                shader.inputs["Emission Strength"].default_value = 0.48
            self.surfaces[finish] = (mat, [])
        mat, items = self.surfaces[finish]
        obj.data.materials.append(mat)
        items.append(obj)
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        self.collection.objects.link(obj)
        return obj

    def loft(self, title, finish, rings, smooth=False):
        n = len(rings[0])
        vertices = [xyz(v) for ring in rings for v in ring]
        faces = [tuple(reversed(range(n)))]
        for j in range(len(rings) - 1):
            for i in range(n):
                a = j * n + i
                b = j * n + (i + 1) % n
                faces.append((a, b, b + n, a + n))
        faces.append(tuple(range(len(vertices) - n, len(vertices))))
        data = bpy.data.meshes.new(title)
        data.from_pydata(vertices, [], faces)
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
        for poly in data.polygons:
            poly.use_smooth = smooth and len(poly.vertices) == 4
        obj = bpy.data.objects.new(title, data)
        bpy.context.collection.objects.link(obj)
        return self.add(obj, finish)

    def puck(self, title, finish, profile):
        rings = []
        for height, radius, tilt in profile:
            rings.append(
                [
                    (
                        radius * math.cos(i * math.tau / 96),
                        height - radius * math.sin(i * math.tau / 96) * math.sin(tilt),
                        radius * math.sin(i * math.tau / 96) * math.cos(tilt),
                    )
                    for i in range(96)
                ]
            )
        return self.loft(title, finish, rings, True)

    def ply(self, title, finish, levels, center=(0, 0), transform=None):
        def place(x, y, z):
            return (x + center[0], y + center[1], z)

        convert = transform or place
        return self.loft(
            title,
            finish,
            [
                [convert(x, y, z) for x, y in rectangle(w, h, r)]
                for z, w, h, r in levels
            ],
            True,
        )

    def finish(self):
        bpy.context.view_layer.update()
        for key, (_, items) in self.surfaces.items():
            if self.name == "stream-deck-neo":
                for part in items:
                    part["studioOccluder"] = True
            export_batch(
                self.name + "-" + key, items, OUT / (self.name + "-" + key + ".mesh")
            )
        face_art = SOURCE / "artwork" / (self.name + ".glb")
        if face_art.is_file():
            bpy.ops.import_scene.gltf(filepath=str(face_art))
            for part in list(bpy.context.selected_objects):
                for collection in list(part.users_collection):
                    collection.objects.unlink(part)
                self.collection.objects.link(part)
            bpy.ops.file.pack_all()
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = "METRIC"
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_distance = (
                    0.7 if self.name == "screenbar-halo-2" else 0.19
                )
                area.spaces.active.clip_start = 0.0003
                area.spaces.active.overlay.show_floor = False
                area.spaces.active.shading.color_type = "MATERIAL"
        bpy.ops.wm.save_as_mainfile(
            filepath=str(SOURCE / (self.name + ".blend")), compress=True
        )


def monitor_lamp():
    from screenbar_halo import build

    build(Device("screenbar-halo-2"))


def dial():
    d = Device("halo-controller")
    tilt = math.radians(10)
    d.puck(
        "Non-slip silicone annulus",
        "rubber",
        [(0, 31, 0), (0.75, 35.4, 0), (1.6, 35.6, 0)],
    )
    d.puck(
        "Fixed sloped electronics base",
        "abs",
        [
            (1.4, 34.4, 0),
            (2.1, 36.3, 0),
            (3.7, 36.8, 0),
            (12.5, 36.8, tilt),
            (13.6, 36.5, tilt),
        ],
    )
    d.puck("Rotational clearance", "rubber", [(13.6, 35.8, tilt), (14.5, 35.9, tilt)])
    d.puck(
        "Machined rotating control surround",
        "titanium",
        [
            (14.35, 36, tilt),
            (14.8, 36.8, tilt),
            (16.0, 37, tilt),
            (32.1, 37, tilt),
            (32.85, 36.6, tilt),
            (33.05, 36, tilt),
        ],
    )
    d.puck(
        "Turned highlight lip",
        "silver",
        [(32.85, 35.95, tilt), (33.06, 36, tilt), (33.13, 35.62, tilt)],
    )
    d.puck(
        "Laminated circular touch face",
        "glass",
        [(33.06, 35.53, tilt), (33.21, 35.26, tilt)],
    )
    d.add(
        block("USB-C charging recess", (8.8, 3.15, 0.55), (0, 7.0, -36.55), 0.65),
        "rubber",
    )
    d.add(
        block("USB-C central tongue", (5.75, 0.45, 0.45), (0, 7, -36.87), 0.16),
        "silver",
    )
    d.finish()


def deck():
    d = Device("stream-deck-neo")
    angle = 0.57

    def panel(x, y, z):
        return (
            x,
            39.2 + y * math.cos(angle) + z * math.sin(angle),
            -2.3 - y * math.sin(angle) + z * math.cos(angle),
        )

    back = d.ply(
        "Lower white shell with rounded shoulders",
        "shell",
        [
            (-11.7, 97, 68, 14),
            (-11.1, 101, 71, 14.4),
            (-8.8, 104.4, 75.1, 14.5),
            (-3.6, 106.2, 77, 14.7),
        ],
        transform=panel,
    )
    d.ply(
        "Continuous split line",
        "seam",
        [(-3.6, 105.9, 76.8, 14.7), (-3.1, 106, 76.8, 14.7)],
        transform=panel,
    )
    d.ply(
        "Warm white radiused front panel",
        "shell",
        [
            (-3.13, 106.2, 77, 14.7),
            (-2.8, 106.7, 77.5, 14.7),
            (0.2, 107, 78, 15.2),
            (3.9, 106, 76.8, 15.1),
            (5.85, 102, 73.5, 14.7),
            (6.4, 98, 70, 13.8),
        ],
        transform=panel,
    )
    for i in range(8):
        x = (i % 4 - 1.5) * 19.35
        y = 13.25 - (i // 4) * 19.5
        local = lambda a, b, z: panel(a + x, b + y, z)
        d.ply(
            "Key well " + str(i + 1),
            "seam",
            [(6.38, 18.55, 18.6, 4.65), (6.53, 18.55, 18.6, 4.65)],
            transform=local,
        )
        d.ply(
            "Keycap " + str(i + 1),
            "keys",
            [
                (6.6, 17.25, 17.5, 4.42),
                (8.25, 17.2, 17.4, 4.4),
                (9.65, 16.8, 17, 4.55),
                (10.25, 15.7, 15.9, 4.28),
            ],
            transform=local,
        )
    d.ply(
        "Infobar protective glass",
        "glass",
        [(6.40, 38, 7.7, 1.65), (6.66, 37.65, 7.45, 1.55)],
        transform=lambda x, y, z: panel(x, y - 22.4, z),
    )
    for x in [-29.9, 29.9]:
        d.ply(
            "Illuminated page touch bar",
            "frost",
            [(6.4, 10.2, 1.16, 0.54), (6.54, 10.2, 1.06, 0.5)],
            transform=lambda a, y, z: panel(x + a, y - 22.4, z),
        )
    runpy.run_path(str(HERE / "stream-deck-stand.py"))["build"](d, back, panel, rectangle)
    d.finish()


if "--deck-only" in sys.argv:
    OUT = SOURCE / "stream-deck-neo-parts"
    OUT.mkdir(parents=True, exist_ok=True)
    deck()
else:
    monitor_lamp()
    if "--halo-only" not in sys.argv:
        dial()
