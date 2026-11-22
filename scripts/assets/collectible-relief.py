import bpy
import numpy as np
import runpy
from pathlib import Path
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree


class FrontCasting:
    def __init__(self, figure, data, reference_size):
        self.figure = figure
        self.reference_size = reference_size
        self.surface = np.asarray(data["points"])
        self.faces = np.asarray(data["faces"])
        self.projection = np.column_stack((data["uv"], -self.surface[:, 1]))
        self.projected = BVHTree.FromPolygons(
            self.projection.tolist(), self.faces.tolist(), all_triangles=True
        )
        self.positions = []
        self.triangles = []
        self.assignments = []
        self.materials = []

    def alloy(self, name, color, metal, rough):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        shader = material.node_tree.nodes["Principled BSDF"]
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = rough
        self.materials.append(material)
        return len(self.materials) - 1

    def surface_point(self, x, y):
        position = (
            x / (self.reference_size - 1),
            1 - y / (self.reference_size - 1),
            0.2,
        )
        hit, _, f, _ = self.projected.ray_cast(position, (0, 0, -1), 0.4)
        if hit is None:
            for offset in (0.001, 0.002, 0.004, 0.006):
                for dx, dy in [(offset, 0), (-offset, 0), (0, offset), (0, -offset)]:
                    hit, _, f, _ = self.projected.ray_cast(
                        (position[0] + dx, position[1] + dy, 0.2), (0, 0, -1), 0.4
                    )
                    if hit is not None:
                        break
                if hit is not None:
                    break
            if hit is None:
                raise ValueError(f"Surface registration failed at ({x}, {y})")
        vertices = self.faces[f]
        scene_point = geometry.barycentric_transform(
            hit,
            *(Vector(self.projection[i]) for i in vertices),
            *(Vector(self.surface[i]) for i in vertices),
        )
        hit, point, _, _ = self.figure.ray_cast(
            (scene_point.x, -0.20, scene_point.z), (0, 1, 0), distance=0.4
        )
        return point if hit else scene_point

    def triangle(self, a, b, c, material):
        start = len(self.positions)
        if (b - a).cross(c - a).y > 0.0000000001:
            b, c = c, b
        self.positions.extend([a, b, c])
        self.triangles.append((start, start + 1, start + 2))
        self.assignments.append(material)

    def ridge(self, path, width, advance, material):
        path = np.asarray(path, dtype=float)
        lengths = np.linalg.norm(np.diff(path, axis=0), axis=1)
        knots = np.r_[0.0, np.cumsum(lengths)]
        samples = np.linspace(0, knots[-1], max(3, round(knots[-1] * 1.5)))
        centers = np.column_stack(
            [np.interp(samples, knots, path[:, i]) for i in (0, 1)]
        )
        across = np.gradient(centers, axis=0)[:, ::-1]
        across[:, 0] *= -1
        across /= np.linalg.norm(across, axis=1)[:, None]
        rows = []
        for i, (center, normal) in enumerate(zip(centers, across)):
            taper = min(1, 0.28 + i * 0.4, 0.28 + (len(centers) - 1 - i) * 0.4)
            row = []
            for shift, depth in [
                (-1, 0.00010),
                (-0.65, advance * 0.80),
                (0, advance),
                (0.65, advance * 0.80),
                (1, 0.00010),
            ]:
                point = self.surface_point(*(center + normal * shift * width * taper))
                point.y -= depth
                row.append(point)
            rows.append(row)
        for a, b in zip(rows, rows[1:]):
            for j in range(4):
                self.triangle(a[j], b[j], a[j + 1], material)
                self.triangle(b[j], b[j + 1], a[j + 1], material)

    def scale_plate(self, corners, rim, enamel):
        outline = np.array(corners, dtype=float)
        for _ in range(2):
            following = np.roll(outline, -1, axis=0)
            outline = np.stack(
                (0.8 * outline + 0.2 * following, 0.2 * outline + 0.8 * following),
                axis=1,
            ).reshape(-1, 2)
        center = np.mean(outline, axis=0)
        rings = []
        for scale, depth in [(1, 0.00006), (0.94, 0.00015), (0.66, 0.00028)]:
            ring = []
            for xy in center + (outline - center) * scale:
                point = self.surface_point(*xy)
                point.y -= depth
                ring.append(point)
            rings.append(ring)
        peak = self.surface_point(*center)
        peak.y -= 0.00035
        for i in range(len(outline)):
            j = (i + 1) % len(outline)
            for band in range(2):
                front, back = rings[band], rings[band + 1]
                material = rim if band == 0 else enamel
                self.triangle(front[i], front[j], back[j], material)
                self.triangle(front[i], back[j], back[i], material)
            self.triangle(rings[-1][i], rings[-1][j], peak, enamel)

    def seal(self, name):
        if not self.triangles:
            return
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.positions, [], self.triangles)
        for inherited in self.figure.data.color_attributes:
            colors = mesh.color_attributes.new(
                name=inherited.name, type=inherited.data_type, domain=inherited.domain
            )
            colors.data.foreach_set("color", np.ones(len(colors.data) * 4, dtype="f"))
        for material in self.materials:
            mesh.materials.append(material)
        mesh.polygons.foreach_set("material_index", np.int32(self.assignments))
        mesh.polygons.foreach_set(
            "use_smooth", np.ones(len(self.triangles), dtype=bool)
        )
        mesh.update()
        addition = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(addition)
        bpy.ops.object.select_all(action="DESELECT")
        addition.select_set(True)
        self.figure.select_set(True)
        bpy.context.view_layer.objects.active = self.figure
        bpy.ops.object.join()
        self.figure.data.validate(clean_customdata=False)
        self.figure.data.update()


def helmet_and_reactor(casting):
    gold = casting.alloy("Mark 85 · folded champagne faceplate", (0.57, 0.40, 0.21), 0.68, 0.34)
    bevel = casting.alloy("Mark 85 · oxide inside folded edge", (0.105, 0.069, 0.047), 0.43, 0.48)
    seal = casting.alloy("Mark 85 · reactor seating gasket", (0.060, 0.059, 0.063), 0.23, 0.43)
    bezel = casting.alloy("Mark 85 · brushed reactor bezel", (0.45, 0.47, 0.46), 0.70, 0.35)
    forehead = [
        (283.7, 117.7), (284.3, 120.8), (285.4, 123.4), (286.2, 124.35),
        (287.6, 124.55), (289.6, 124.15), (291.1, 122.85), (293.8, 119.95),
        (296.3, 118.05), (298.8, 116.8), (300.7, 116.45),
    ]
    casting.ridge(forehead, 0.17, 0.00012, bevel)
    casting.ridge([(x, y + 0.22) for x, y in forehead], 0.17, 0.00022, gold)
    for upper_lid in [
        [(280.1, 132.15), (282.4, 132.7), (284.6, 133.05), (286.5, 133.05)],
        [(290.5, 132.5), (293.2, 132.05), (296.2, 131.45), (299.1, 130.65)],
    ]:
        casting.ridge(upper_lid, 0.18, 0.00014, gold)
    opening = np.array([
        (286.2, 185.2), (287.2, 183.5), (289.15, 182.4), (291.95, 182.45),
        (293.1, 183.1), (295.1, 183.0), (296.55, 182.25), (298.65, 182.15),
        (300.65, 182.95), (301.8, 184.25), (301.65, 185.45), (296.1, 196.75),
        (295.25, 197.3), (291.9, 197.2), (291.25, 196.7), (286.2, 185.2),
    ])
    centre = np.array([294, 189])
    casting.ridge(centre + (opening-centre)*1.04, 0.27, 0.00012, seal)
    casting.ridge(opening, 0.25, 0.00027, bezel)


def model_surface(figure, data, slug, root):
    if slug == "great-sage":
        runpy.run_path(str(Path(__file__).with_name("collectible-plumes.py")))[
            "cast_plumes"
        ](figure, root)
    casting = FrontCasting(figure, data, 690 if slug == "great-sage" else 610)
    if slug == "great-sage":
        gold = casting.alloy("Relief · brushed gilt", (0.69, 0.41, 0.095), 0.52, 0.29)
        edge = casting.alloy("Relief · aged bevel", (0.25, 0.12, 0.031), 0.46, 0.43)
        outline = np.load(root / "great-sage-inscription.npz")
        uvs = outline["points"]
        registration = (uvs - uvs.min(axis=0)) / np.ptp(uvs, axis=0)
        contact = []
        for x, y in registration:
            position = (
                -0.001 + 0.034 * x,
                -0.2,
                0.011 + 0.0168 * (1 - y) + 0.0013 * (x - 0.5),
            )
            hit, point, _, _ = figure.ray_cast(position, (0, 1, 0), distance=0.4)
            if not hit:
                raise ValueError(
                    f"The original gilt inscription must contact the bronze base at {position}"
                )
            contact.append(point)
        obverse = [v + Vector((0, -0.00058, 0)) for v in contact]
        for a, b, c in outline["faces"]:
            casting.triangle(obverse[a], obverse[b], obverse[c], gold)
        for a, b in outline["edges"]:
            casting.triangle(contact[a], obverse[a], obverse[b], edge)
            casting.triangle(contact[a], obverse[b], contact[b], edge)
    else:
        rubber = casting.alloy(
            "Mark 85 · recessed plate channels", (0.052, 0.019, 0.021), 0.35, 0.38
        )
        red = casting.alloy(
            "Mark 85 · candy red plate rims", (0.31, 0.012, 0.016), 0.48, 0.31
        )
        silver = casting.alloy(
            "Mark 85 · titanium faceplate lip", (0.22, 0.20, 0.15), 0.59, 0.28
        )
        knuckle = casting.alloy(
            "Mark 85 · gilt finger armour", (0.55, 0.33, 0.105), 0.49, 0.35
        )
        for plate in [
            [
                (351.7, 278.35),
                (354.35, 275.95),
                (355.85, 276.05),
                (356.9, 277.7),
                (354.3, 280.25),
                (352.15, 280.55),
            ],
            [
                (354.35, 282.05),
                (357.3, 279.85),
                (358.7, 280.25),
                (359.9, 281.95),
                (356.8, 284.9),
                (355.3, 284.25),
            ],
            [
                (357.15, 285.0),
                (359.5, 282.75),
                (361.1, 283.0),
                (361.7, 284.3),
                (359.35, 286.65),
                (357.75, 286.30),
            ],
            [
                (359.9, 286.2),
                (362.35, 283.95),
                (363.5, 284.1),
                (363.35, 285.65),
                (361.2, 287.2),
                (360.1, 287.0),
            ],
        ]:
            casting.scale_plate(plate, rubber, knuckle)
        for path in [
            [(353.3, 279.1), (354.35, 278.4), (355.25, 277.5), (355.75, 277.15)],
            [(355.8, 283.4), (357.0, 282.55), (357.9, 281.55), (358.55, 281.25)],
            [(358.65, 285.65), (359.5, 284.95), (360.25, 284.15)],
            [(360.8, 286.65), (361.5, 286.05), (362.3, 285.35)],
        ]:
            casting.ridge(path, 0.32, 0.00042, rubber)
        for i in range(5):
            dx, dy = i * 1.0, -i * 1.01
            line = [
                (357.8 + dx, 264.1 + dy),
                (359.0 + dx, 265.4 + dy),
                (359.7 + dx, 267.3 + dy),
                (360.2 + dx, 269.1 + dy),
            ]
            casting.ridge(line, 0.22, 0.00031, silver)
        helmet_and_reactor(casting)
        for line in [
            [(280.6, 136.2), (281.7, 140), (284.9, 145.5), (286.2, 147.1)],
            [(310.9, 130.1), (306.2, 137.3), (300, 143.9), (298.2, 147.2)],
            [(286.4, 148.2), (290.6, 147.5), (294.8, 148.1)],
        ]:
            casting.ridge(line, 0.32, 0.00030, silver)
        layers = [
            [
                (278.1, 209.7),
                (282, 212.7),
                (292, 212.4),
                (303.5, 211.1),
                (307.5, 208.8),
            ],
            [
                (281.7, 217.1),
                (285.4, 220.3),
                (294.3, 220.4),
                (303.8, 219),
                (307.2, 216),
            ],
            [
                (281.8, 226.2),
                (285.9, 229.9),
                (294.7, 230.1),
                (302.7, 228.9),
                (307.1, 224.4),
            ],
            [
                (282.3, 235.8),
                (286.4, 238.8),
                (294.4, 239),
                (301.5, 237.7),
                (307.4, 233.5),
            ],
            [
                (282.8, 246.6),
                (287.7, 249.4),
                (295.2, 250.2),
                (302.7, 249),
                (308, 244.5),
            ],
        ]
        for path in layers:
            casting.ridge(path, 0.50, 0.00023, rubber)
            casting.ridge([(x, y + 0.82) for x, y in path], 0.44, 0.00038, red)
    casting.seal(slug + " cast details")
    if slug == "mk85":
        runpy.run_path(str(Path(__file__).with_name("mk85-stamped-inserts.py")))["fit"](casting, root)
