import runpy
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
FRONT = runpy.run_path(str(HERE / "model-gr701-fascia.py"))
TRAY = runpy.run_path(str(HERE / "gr701-rear-tray.py"))
STORAGE = runpy.run_path(str(HERE / "gr701-storage.py"))
SOURCE = FRONT["PRODUCT"] / "Blender/gr701-cable-chamber.blend"
COLLECTION = "GR701 · cable-management chamber"
DOOR = "GR701 · glass door fittings"
FINISHES = {
    "drive": ("Anodised SSD casing", "212327", 0.54, 0.46),
    "steel": ("Pressed anthracite steel", "42464d", 0.48, 0.47),
    "polymer": ("Charcoal carrier and terminal housings", "333638", 0.08, 0.54),
    "wire": ("Satin graphite harness jackets", "37383b", 0.03, 0.49),
    "contact": ("Pale gold terminal plating", "b5a38b", 0.63, 0.37),
    "print": ("Grey print and smoke-cover foil", "797c83", 0.37, 0.42),
    "smoke": ("Smoke polycarbonate cable shield", "383c43", 0.04, 0.28),
    "trim": ("Satin perimeter and rear hinge moulding", "323439", 0.22, 0.50),
}


def cover(parts):
    position, circle = TRAY["position"], TRAY["circle"]

    def strip(name, key, contour, x, depth, openings=(), edge=0):
        part = FRONT["sheet"](
            name,
            contour,
            list(openings),
            lambda u, v, d: position(u, v, x + d),
            depth,
            edge,
        )
        parts[key].append(part)
        return part

    shield = [
        (269, 157),
        (275, 139),
        (290, 133),
        (547, 133),
        (630, 213),
        (630, 586),
        (622, 596),
        (610, 650),
        (281, 650),
        (271, 642),
    ]
    window = [
        (340, 183),
        (456, 183),
        (473, 202),
        (473, 549),
        (445, 586),
        (360, 586),
        (340, 565),
    ]
    screws = [(502, 175), (501, 555)]
    strip(
        "Removable smoke shield · stepped cable-channel window",
        "smoke",
        shield,
        113.6,
        2.1,
        [window, *[circle(u, v, 3.3, 16) for u, v in screws]],
        0.40,
    )
    for i, level in enumerate((187, 298, 424), 1):
        strip(
            "Smoke shield · diagonal window rib %d" % i,
            "smoke",
            [
                (339, level),
                (344, level),
                (475, level + 128),
                (475, level + 137),
                (469, level + 137),
                (339, level + 9),
            ],
            113.0,
            1.8,
            edge=0.23,
        )
    for i, (u, v) in enumerate(screws, 1):
        strip(
            "Captive cable-shield screw %d" % i,
            "polymer",
            circle(u, v, 6.5, 20),
            114.7,
            3.1,
            [TRAY["rectangle"](u - 2.8, v - 0.65, u + 2.8, v + 0.65, 0.2)],
            0.20,
        )
    strip(
        "Smoke shield · satin lower slash",
        "print",
        [(468, 432), (474, 427), (624, 576), (618, 593), (468, 445)],
        113.75,
        0.06,
    )
    strip(
        "Smoke shield · upper slash",
        "print",
        [(491, 162), (497, 161), (626, 292), (626, 300)],
        113.75,
        0.06,
    )
    foil = [
        [
            (35, 232),
            (57, 249),
            (82, 266),
            (116, 295),
            (146, 333),
            (116, 323),
            (90, 313),
            (70, 301),
            (54, 274),
        ],
        [
            (114, 249),
            (155, 269),
            (180, 280),
            (198, 284),
            (205, 277),
            (269, 213),
            (327, 160),
            (358, 136),
            (383, 121),
            (422, 108),
            (480, 96),
            (535, 91),
            (547, 105),
            (515, 116),
            (465, 139),
            (404, 171),
            (346, 210),
            (284, 253),
            (229, 299),
            (209, 321),
            (204, 333),
            (208, 348),
            (221, 367),
            (240, 392),
            (214, 379),
            (184, 356),
            (160, 329),
            (140, 295),
        ],
        [
            (224, 334),
            (279, 299),
            (350, 249),
            (416, 214),
            (480, 181),
            (531, 158),
            (563, 149),
            (563, 185),
            (494, 216),
            (416, 253),
            (349, 290),
            (278, 334),
            (346, 351),
            (384, 358),
            (418, 359),
            (437, 348),
            (462, 325),
            (486, 292),
            (500, 260),
            (439, 278),
            (377, 297),
            (379, 289),
            (439, 260),
            (501, 230),
            (562, 207),
            (562, 247),
            (542, 281),
            (514, 330),
            (489, 362),
            (464, 383),
            (444, 394),
            (424, 397),
            (378, 394),
            (327, 385),
            (271, 366),
            (230, 346),
        ],
    ]
    for i, path in enumerate(foil, 1):
        strip(
            "Cable-cover ROG foil %d" % i,
            "print",
            [(480 + u / 4, 340 + v / 4) for u, v in path],
            113.8,
            0.07,
        )


def door_parts():
    sheet = FRONT["sheet"]
    position = TRAY["position"]

    def flange(name, shape, depth, thickness, holes=(), radius=0.2):
        return sheet(
            name,
            shape,
            list(holes),
            lambda u, v, d: position(u, v, depth + d),
            thickness,
            radius,
        )

    outline = TRAY["rectangle"](268, 122, 803, 659, 9)
    aperture = TRAY["rectangle"](277, 131, 785, 649, 6)
    result = [
        flange("Glass-side edging · cable-access door", outline, 125.5, 2, [aperture])
    ]
    for name, y0, y1 in (("top", 145, 235), ("bottom", 519, 613)):
        result.append(
            flange(
                "Rear door grip · " + name,
                [
                    (786, y0 + 11),
                    (798, y0),
                    (806, y0 + 2),
                    (806, y1 - 6),
                    (796, y1),
                    (786, y1 - 5),
                ],
                127.3,
                6.1,
                radius=0.8,
            )
        )
        for i in range(12):
            y = y0 + 14 + i * 6.05
            result.append(
                flange(
                    "%s door grip rib %02d" % (name, i + 1),
                    [(787, y + 4), (804, y - 6), (804, y - 4), (787, y + 6)],
                    128.25,
                    1.3,
                    radius=0.28,
                )
            )
    return result


def material(key):
    label, hexcode, metal, rough = FINISHES[key]
    srgb = [int(hexcode[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    rgb = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    alpha = 0.54 if key == "smoke" else 1
    mat = bpy.data.materials.new(label)
    mat.diffuse_color = (*rgb, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    for socket, value in [
        ("Base Color", (*rgb, 1)),
        ("Metallic", metal),
        ("Roughness", rough),
        ("Alpha", alpha),
    ]:
        bsdf.inputs[socket].default_value = value
    return mat


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    chamber = bpy.data.collections.new(COLLECTION)
    door = bpy.data.collections.new(DOOR)
    for c in (chamber, door):
        scene.collection.children.link(c)
    parts = TRAY["build"](FRONT["shell"], FRONT["sheet"])
    parts["drive"] = []
    STORAGE["build"](FRONT["shell"], FRONT["sheet"], parts)
    parts["smoke"] = []
    cover(parts)
    parts["trim"] = door_parts()
    from blender_parts import export_batch

    for key, group in parts.items():
        mat = material(key)
        for ob in group:
            ob.data.materials.append(mat)
            ob["cableChamberFinish"] = key
            ob["studioOccluder"] = key not in ("print", "contact", "smoke")
            (door if key == "trim" else chamber).objects.link(ob)
            scene.collection.objects.unlink(ob)
        bpy.context.view_layer.update()
        filename = "gr701-cable-bay-" + key
        export_batch(
            filename,
            group,
            FRONT["ROOT"] / "public/media/models" / (filename + ".mesh"),
        )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(SOURCE), compress=True, check_existing=False
    )


def remove_placeholder(chassis):
    from mathutils import Vector

    targets = []
    for ob in chassis.children:
        if ob.type != "MESH":
            continue
        matrix = chassis.matrix_world.inverted() @ ob.matrix_world
        verts = [
            v.index
            for v in ob.data.vertices
            if 0.11298 < (p := matrix @ v.co).x < 0.11702
            and -0.19302 < p.y < 0.29402
            and -0.26202 < p.z < 0.26202
        ]
        if len(verts) < 300:
            continue
        selected = set(verts)
        faces = [f for f in ob.data.polygons if all(v in selected for v in f.vertices)]
        if not faces:
            continue
        indices = {v for f in faces for v in f.vertices}
        coords = [matrix @ ob.data.vertices[i].co for i in indices]
        lo = Vector(tuple(min(p[i] for p in coords) for i in range(3)))
        hi = Vector(tuple(max(p[i] for p in coords) for i in range(3)))
        if (lo - Vector((0.113, -0.193, -0.262))).length > 0.00005 or (
            hi - Vector((0.117, 0.294, 0.262))
        ).length > 0.00005:
            continue
        targets.append((ob, indices))
    if len(targets) != 1:
        raise ValueError("Expected a single flush cable-bay placeholder")
    ob, indices = targets[0]
    if len(indices) != 900:
        raise ValueError("Unexpected vertices in the solid right panel")
    if len(indices) == len(ob.data.vertices):
        bpy.data.objects.remove(ob, do_unlink=True)
        return
    old = ob.data
    ob.data = old.copy()
    edit = bmesh.new()
    edit.from_mesh(ob.data)
    edit.verts.ensure_lookup_table()
    bmesh.ops.delete(edit, geom=[edit.verts[i] for i in indices], context="VERTS")
    edit.to_mesh(ob.data)
    edit.free()
    if not old.users:
        bpy.data.meshes.remove(old)


def fit(scene):
    chassis = scene.objects["ROG Hyperion GR701 chassis"]
    mounted = {c.name: c for c in chassis.children}
    if COLLECTION not in mounted:
        remove_placeholder(chassis)
        with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (
            _,
            loaded,
        ):
            loaded.collections = [COLLECTION, DOOR]
        for col in loaded.collections:
            anchor = bpy.data.objects.new(col.name, None)
            chassis.users_collection[0].objects.link(anchor)
            anchor.parent = chassis
            anchor.instance_type = "COLLECTION"
            anchor.instance_collection = col
            anchor.empty_display_size = 0.012
            mounted[col.name] = anchor
    for name in (COLLECTION, DOOR):
        col = mounted[name].instance_collection
        assert (
            col.library
            and Path(bpy.path.abspath(col.library.filepath)).resolve() == SOURCE
        )
    return mounted[COLLECTION], mounted[DOOR]


if __name__ == "__main__":
    build()
