import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mesh import write_mesh

root = Path(__file__).resolve().parents[2]
archive = root / ".references/01-空间与建筑/供暖设施/Cast iron radiator/Blender"
web = root / "public/media/models"
bpy.ops.wm.read_factory_settings(use_empty=True)
collection = bpy.data.collections.new("Carron Princess 610")
bpy.context.scene.collection.children.link(collection)


def finish(name, rgb, metal, rough):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    return mat


enamel = finish("Warm ivory stove enamel", (0.75, 0.72, 0.66), 0.13, 0.43)
brass = finish("Patinated brass", (0.38, 0.25, 0.115), 0.77, 0.34)
wood = finish("Stained hardwood wheel", (0.11, 0.038, 0.018), 0.05, 0.34)
joint = finish("Dark joint line", (0.047, 0.04, 0.035), 0.15, 0.6)
noise = enamel.node_tree.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 2100
noise.inputs["Detail"].default_value = 2
coords = enamel.node_tree.nodes.new("ShaderNodeTexCoord")
bump = enamel.node_tree.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.18
bump.inputs["Distance"].default_value = 0.00012
enamel.node_tree.links.new(coords.outputs["Object"], noise.inputs["Vector"])
enamel.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
enamel.node_tree.links.new(
    bump.outputs["Normal"], enamel.node_tree.nodes["Principled BSDF"].inputs["Normal"]
)


class Casting:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.smooth = []

    def loops(self, rings, close=False, caps=False, rounded=True):
        start = len(self.vertices)
        count = len(rings[0])
        for ring in rings:
            self.vertices.extend(
                (x / 1000, -along / 1000, h / 1000) for x, along, h in ring
            )
        for j in range(len(rings) if close else len(rings) - 1):
            a = start + j * count
            b = start + (j + 1) % len(rings) * count
            for i in range(count):
                k = (i + 1) % count
                self.faces.append((a + i, a + k, b + k, b + i))
                self.smooth.append(rounded)
        if caps:
            self.faces.extend(
                [
                    tuple(start + i for i in reversed(range(count))),
                    tuple(start + (len(rings) - 1) * count + i for i in range(count)),
                ]
            )
            self.smooth.extend([False, False])

    def turned(self, center, profile, axis="h", sides=36):
        x, along, height = center
        rings = []
        for r, pos in profile:
            ring = []
            for i in range(sides):
                theta = math.tau * i / sides
                a, b = r * math.cos(theta), r * math.sin(theta)
                if axis == "h":
                    ring.append((x + a, along + b, height + pos))
                elif axis == "along":
                    ring.append((x + a, along + pos, height + b))
                else:
                    ring.append((x + pos, along + a, height + b))
            rings.append(ring)
        self.loops(rings, caps=True, rounded=sides > 8)

    def bake(self, name, slug, mat):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        for polygon, smooth in zip(mesh.polygons, self.smooth):
            polygon.use_smooth = smooth
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if slug == "footed":
            cut = bmesh.ops.bisect_plane(
                bm,
                geom=[*bm.verts, *bm.edges, *bm.faces],
                dist=1e-7,
                plane_co=(0, 0, 0),
                plane_no=(0, 0, 1),
                clear_inner=True,
            )
            sole_edges = [
                edge for edge in cut["geom_cut"]
                if isinstance(edge, bmesh.types.BMEdge) and edge.is_boundary
            ]
            soles = bmesh.ops.holes_fill(bm, edges=sole_edges)["faces"]
            if len(soles) != 2 or any(f.calc_area() < 0.0003 for f in soles):
                raise ValueError("Each end casting needs two flat load-bearing soles")
            for face in soles:
                face.smooth = False
                for edge in face.edges:
                    edge.smooth = False
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        if mat == enamel:
            uv = mesh.uv_layers.new(name="Casting grain")
            for polygon in mesh.polygons:
                axis = max(range(3), key=lambda k: abs(polygon.normal[k]))
                u, v = ((1, 2), (0, 2), (0, 1))[axis]
                for index in polygon.loop_indices:
                    point = mesh.vertices[mesh.loops[index].vertex_index].co
                    uv.data[index].uv = (point[u] * 18, point[v] * 18)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.data.materials.append(mat)
        bpy.context.view_layer.update()
        write_mesh(obj, web / f"princess-{slug}.mesh")
        return obj


def bezier(points, t):
    return tuple(
        (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t**3 * d
        for a, b, c, d in zip(*points)
    )


def smoothstep(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def section(foot):
    outer = [(0, 610)]
    inner = [(0, 507)]

    def sweep(o, i, steps):
        start_a, start_b = outer[-1], inner[-1]
        for step in range(1, steps + 1):
            outer.append(bezier([start_a, *o], step / steps))
            inner.append(bezier([start_b, *i], step / steps))

    sweep([(31, 610), (62.5, 596), (62.5, 563)], [(13, 507), (22, 498), (22, 485)], 12)
    sweep(
        [(62.5, 523), (62.5, 506), (62.5, 472)], [(22, 467), (22, 450), (22, 426)], 10
    )
    sweep([(62.5, 380), (62.5, 235), (62.5, 176)], [(22, 365), (22, 255), (22, 208)], 7)
    sweep(
        [(62.5, 151), (62.5, 130), (62.5, 114)], [(22, 190), (22, 179), (21.6, 172)], 10
    )
    sweep(
        [(62.5, 83), (44, 56), (0, 54)], [(21, 158), (12, 150), (0, 150)],
        36 if foot else 16,
    )
    outer += [(-x, h) for x, h in reversed(outer[1:-1])]
    inner += [(-x, h) for x, h in reversed(inner[1:-1])]
    casting = Casting()
    half_profile = [
        (0, 0),
        (0.001, 0.025),
        (0.009, 0.048),
        (0.022, 0.065),
        (0.028, 0.105),
        (0.045, 0.26),
        (0.085, 0.48),
        (0.15, 0.70),
        (0.24, 0.88),
        (0.34, 0.97),
        (0.45, 1.0),
        (0.55, 1.005),
        (0.65, 0.99),
        (0.76, 0.92),
        (0.84, 0.80),
        (0.91, 0.64),
        (0.96, 0.43),
        (0.986, 0.25),
        (1, 0),
    ]
    if foot:
        denser = []
        for i, point in enumerate(half_profile):
            if i and point[0] - half_profile[i - 1][0] > 0.025:
                denser.append(tuple((a + b) * 0.5 for a, b in zip(half_profile[i - 1], point)))
            denser.append(point)
        half_profile = denser
    profile = half_profile + [(f, -w) for f, w in reversed(half_profile[1:-1])]
    rings = []
    for (xo, ho), (xi, hi) in zip(outer, inner):
        row = []
        for fraction, bulge in profile:
            x = xo + (xi - xo) * fraction
            h = ho + (hi - ho) * fraction
            half = 20.6 * abs(bulge)
            radius = min(math.hypot(x, h - 555), math.hypot(x, h - 105))
            if bulge:
                half += (37.35 - half) * smoothstep((46.0 - radius) / 20.0)
            if foot and h < 114:
                footprint = math.hypot((abs(x) - 43) / 16, half / 19)
                taper = smoothstep((1.32 - footprint) / 0.57)
                h -= 102 * taper * smoothstep((114 - h) / 27)
            row.append((x, math.copysign(half, bulge), h))
        rings.append(row)
    casting.loops(rings, close=True)
    return casting.bake(
        "End section with integral feet" if foot else "Two-column intermediate casting",
        "footed" if foot else "section",
        enamel,
    )


pitch = 75
centers = [33.5 + i * pitch for i in range(10)]
body_section = section(False)
end_section = section(True)
for i, along in enumerate(centers):
    template = end_section if i in (0, 9) else body_section
    obj = (
        template
        if i in (0, 1)
        else bpy.data.objects.new(f"Section {i + 1:02d}", template.data)
    )
    if obj is not template:
        collection.objects.link(obj)
    obj.location.y = -along / 1000

paint = Casting()
metal = Casting()
wheel = Casting()
seals = Casting()
for index, sign in [(0, -1), (9, 1)]:
    end = centers[index] + sign * 37.5

    def end_profile(form, height, radii, sides=36):
        form.turned((0, end, height), [(r, z * sign) for r, z in radii], "along", sides)

    for h in (105, 555):
        end_profile(paint, h, [(29, -1), (29, 1.6), (27.5, 2.3)])
        end_profile(paint, h, [(20.9, 2.2), (22.3, 3.1), (22.3, 8), (20.8, 9.6)], 6)
    if sign == 1:
        end_profile(
            metal, 555, [(9.5, 9.4), (10.4, 10.4), (10.4, 13.6), (9.4, 14.3)], 6
        )
        end_profile(metal, 555, [(6, 14), (5.7, 15.4), (4.4, 15.7), (4.4, 17.2)])
        end_profile(metal, 555, [(5.3, 17), (5.9, 17.4), (5.9, 19.6), (5.3, 20.1)])
        metal.turned(
            (6, end, 559.1),
            [(1.8, 13.8), (1.85, 15.5), (1.45, 15.9), (0.86, 15.9), (0.8, 14.5)],
            "along", 24,
        )
        seals.turned((6, end, 559.1), [(0.79, 14.48), (0.79, 14.55)], "along", 24)
    else:
        end_profile(
            paint, 555, [(11, 9.3), (11.4, 10.2), (11.4, 11.1), (10.5, 11.8)], 6
        )
    end_profile(metal, 105, [(8.8, 9.4), (10, 10.2), (10, 16), (8.5, 16.7), (8.5, 35)])
    end_profile(metal, 105, [(12.4, 18.2), (13.8, 19.6), (13.8, 26.5), (12, 27.7)], 6)
    stem = end + sign * 44

    def stem_profile(profile, sides=36):
        metal.turned((0, stem, 0), profile, sides=sides)

    stem_profile([(19.8, 0), (20, 1.35), (17.8, 2.4), (10.3, 5.9), (8.4, 9), (8.4, 76)])
    stem_profile([(11.6, 70), (12.6, 71.8), (12.6, 79), (11.3, 80.3)], 6)
    stem_profile(
        [
            (10, 79),
            (10, 83),
            (12.6, 86),
            (13.1, 92),
            (12.6, 96),
            (11.6, 98),
            (12.8, 102),
            (12.6, 110),
            (11, 115),
            (9.7, 117),
        ]
    )
    if sign == 1:
        stem_profile([(9.2, 114.5), (10, 120), (7.6, 129), (6.4, 136), (6.4, 140)])
        wheel.turned(
            (0, stem, 0),
            [
                (8.8, 138),
                (15.8, 139.6),
                (18, 142.6),
                (17.8, 146.5),
                (15, 149.4),
                (8.2, 150.1),
            ],
        )
        stem_profile([(7.5, 149.4), (8.2, 150), (7.4, 151.1), (3.8, 152), (3.6, 154.5)])
    else:
        stem_profile([(9.5, 116), (10.1, 119), (8.9, 121), (7.9, 131.5), (6.8, 133.2)])
for k in range(9):
    for h in (105, 555):
        seals.turned(
            (0, centers[k] + 37.5, h), [(28.7, -0.38), (29, 0.0), (28.7, 0.38)], "along"
        )
for gap in (1, 7):
    along = centers[gap] + 37.5
    metal.turned((0, along, 508), [(12, -130), (12, -128), (4.3, -125), (4.3, 57)], "x")
    plates = []
    for x, shrink in ((53.2, 1), (53.8, 0), (57.2, 0), (58, 1)):
        contour = []
        for i in range(4):
            a, b = ((22, 8), (-22, 8), (-22, -8), (22, -8))[i]
            for j in range(6):
                theta = (i + j / 5) * math.pi / 2
                r = 3 - shrink
                contour.append(
                    (x, along + a + r * math.cos(theta), 508 + b + r * math.sin(theta))
                )
        plates.append(contour)
    metal.loops(plates, caps=True)
    metal.turned(
        (0, along, 508), [(7.5, 57.9), (8.2, 58.8), (8.2, 60.5), (7, 61.5)], "x"
    )
    metal.turned(
        (0, along, 508), [(5, 61.1), (5.6, 62), (5.6, 64.1), (5, 64.8)], "x", 6
    )
for parts, name, slug, mat in [
    (paint, "Painted end bushes and blank plug", "bush", enamel),
    (metal, "Paired floor valves, bleed key and wall stays", "fittings", brass),
    (seals, "Compressed sectional gaskets", "joints", joint),
    (wheel, "Hardwood inlet wheel", "wheel", wood),
]:
    parts.bake(name, slug, mat)
collection["Product"] = "Carron Princess TBK104/105"
collection["Section pitch (mm)"] = 75
collection["Height, depth and tapping centres (mm)"] = [610, 125, 450]
collection["Source"] = (
    "https://www.carronheating.co.uk/radiators/cast-iron-radiators/princess/"
)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(
    filepath=str(archive / "cast-iron-radiator.blend"), compress=True
)
