import itertools
import math
import struct
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / ".review/atelier/kinto-clk-151"
TARGET = ROOT / "public/media/models/kinto-clk-151.glb"
COLUMNS = 128
OUTER = [
    (0, 2.5),
    (14, 2.5),
    (23.8, 2.5),
    (24.7, 2.2),
    (25, 1.7),
    (25.2, 0.55),
    (25.5, 0.14),
    (26, 0),
    (27.7, 0),
    (28.2, 0.13),
    (28.8, 0.39),
    (29.4, 0.84),
    (34.7, 6.6),
    (35.8, 8.0),
    (36.3, 9.1),
    (38.9, 16.5),
    (39.15, 17.7),
    (39.32, 18.0),
    (39.42, 18.35),
    (39.44, 19.2),
    (39.52, 20.3),
    (39.62, 22),
    (39.8, 26.7),
    (40, 31.6),
    (40.23, 36.5),
    (40.48, 41.4),
    (40.88, 49.3),
    (41.25, 55.8),
    (41.53, 62.0),
    (41.70, 65.1),
    (41.83, 68.2),
    (41.96, 71.3),
    (42.08, 74.4),
    (42.22, 76.4),
    (42.44, 78.1),
    (42.50, 78.85),
    (42.36, 79.39),
    (41.86, 79.82),
    (41.1, 80),
    (40.30, 80),
]
INSIDE = [
    (0, 6.6),
    (16, 6.8),
    (23, 8),
    (29, 10.2),
    (33.2, 14.5),
    (35, 22),
    (36.65, 34.5),
    (37.9, 64),
    (39, 79.5),
    (40.3, 80),
]
HANDLE = (
    ((41.83, 68.2), (45.4, 68.9), (49.8, 69.3), (53.3, 69.2)),
    ((53.3, 69.2), (57.9, 69.1), (60.6, 67.1), (61.90, 63.8)),
    ((61.90, 63.8), (63.65, 59.55), (64.4, 55.3), (64.36, 52.7)),
    ((64.36, 52.7), (64.38, 49.3), (63.02, 47.55), (60.4, 46.05)),
    ((60.4, 46.05), (55.95, 43.42), (50.30, 41.0), (46.25, 38.36)),
    ((46.25, 38.36), (42.95, 36.16), (41.75, 32.95), (40.0, 31.6)),
)
UPPER = OUTER.index((41.53, 62.0))
LOWER = OUTER.index((39.62, 22))


def periodic_noise(rng, size, divisions):
    grid = rng.normal(size=(divisions, divisions))
    y, x = np.mgrid[:size, :size] * divisions / size
    i, j = x.astype(int), y.astype(int)
    fx, fy = x - i, y - j
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    return (1 - fy) * (
        (1 - fx) * grid[j, i] + fx * grid[j, (i + 1) % divisions]
    ) + fy * (
        (1 - fx) * grid[(j + 1) % divisions, i]
        + fx * grid[(j + 1) % divisions, (i + 1) % divisions]
    )


def bitmap(name, rgb, linear=False):
    data = np.uint8(np.clip(rgb, 0, 255))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    h, w = data.shape[:2]
    path = REVIEW / (name + ".png")
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", w, h, 8, 2, 0, 0, 0))
        + chunk(
            b"IDAT", zlib.compress(b"".join(b"\0" + row.tobytes() for row in data), 9)
        )
        + chunk(b"IEND", b"")
    )
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = "Non-Color" if linear else "sRGB"
    image.pack()
    return image


def textures():
    rng = np.random.default_rng(29513)
    size = 192
    y, x = np.mgrid[:size, :size]
    noise = rng.normal(size=(size, size))
    cloud = periodic_noise(rng, size, 5) + 0.53 * periodic_noise(rng, size, 18)
    glaze = cloud * 2.6 + noise * 1.62
    for _ in range(180):
        cx, cy = rng.uniform(0, size, 2)
        dx = (x - cx + size / 2) % size - size / 2
        dy = (y - cy + size / 2) % size - size / 2
        radius = rng.uniform(0.27, 1.04)
        glaze -= np.exp(-(dx * dx + dy * dy) / (radius * radius)) * rng.uniform(14, 64)
    clay = periodic_noise(rng, size, 21) * 3.8 + noise * 5.0
    clay += np.where(
        rng.random((size, size)) < 0.048, -rng.uniform(8, 29, (size, size)), 0
    )
    first = np.full((size, size), np.inf)
    second = first.copy()
    tone = np.zeros_like(first)
    for _ in range(180):
        xx, yy = rng.uniform(0, size, 2)
        dx = (x - xx + size / 2) % size - size / 2
        dy = (y - yy + size / 2) % size - size / 2
        dist = dx * dx + dy * dy
        closest = dist < first
        second = np.where(closest, first, np.minimum(second, dist))
        tone = np.where(closest, rng.uniform(-16, 15), tone)
        first = np.minimum(first, dist)
    edge = np.exp(-np.maximum(0, np.sqrt(second) - np.sqrt(first)) * 1.64)
    cork = (
        tone
        + cloud * 8.4
        + noise * 6.4
        - edge * 12
        - np.where(rng.random((size, size)) < 0.045, 22, 0)
    )

    def color(name, base, value):
        return bitmap(
            name, np.array(base) + value[:, :, None] * np.array((1, 0.95, 0.86))
        )

    def normal(name, value):
        nx = (np.roll(value, 1, axis=1) - np.roll(value, -1, axis=1)) * 0.5
        ny = (np.roll(value, -1, axis=0) - np.roll(value, 1, axis=0)) * 0.5
        v = np.stack((nx, ny, np.ones_like(nx)), axis=2)
        return bitmap(
            name, 127.5 + 127.5 * v / np.linalg.norm(v, axis=2, keepdims=True), True
        )

    return (
        (
            color("Ivory glaze", (221, 217, 204), glaze),
            normal("Glaze stipple", (0.009 * glaze)[::2, ::2]),
        ),
        (
            color("Exposed Hasami clay", (172, 145, 119), clay),
            normal("Clay mineral grain", (0.015 * clay)[::2, ::2]),
        ),
        (
            color("Natural cork aggregate", (164, 126, 89), cork),
            normal("Cork pores", (0.032 * cork)[::2, ::2]),
        ),
    )


def material(name, color, roughness, images=None):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    if images:
        for image, socket in zip(images, ("Base Color", "Normal")):
            t = m.node_tree.nodes.new("ShaderNodeTexImage")
            t.image = image
            n = t.outputs["Color"]
            if socket == "Normal":
                normal = m.node_tree.nodes.new("ShaderNodeNormalMap")
                normal.inputs["Strength"].default_value = 0.70
                m.node_tree.links.new(n, normal.inputs["Color"])
                n = normal.outputs["Normal"]
            m.node_tree.links.new(n, bsdf.inputs[socket])
    return m, bsdf


class Surface:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.materials = []
        self.uv = []
        self.meridian = {}

    def vertex(self, x, y, z):
        self.vertices.append((x, y, z))
        return len(self.vertices) - 1

    def face(self, indices, material=0, mode="body"):
        self.faces.append(indices)
        self.materials.append(material)
        self.uv.append(mode)

    def object(self, name, materials, tile):
        data = bpy.data.meshes.new(name)
        data.from_pydata(
            [tuple(c * 0.001 for c in p) for p in self.vertices], [], self.faces
        )
        data.update()
        for m in materials:
            data.materials.append(m)
        uv = data.uv_layers.new(name="Physical texture scale")
        for polygon, material, mode in zip(data.polygons, self.materials, self.uv):
            polygon.material_index = material
            polygon.use_smooth = True
            coordinates = []
            for i in polygon.loop_indices:
                vertex = data.loops[i].vertex_index
                x, y, z = self.vertices[vertex]
                if mode == "plane":
                    u, v = x / tile, y / tile
                elif mode == "handle":
                    u, v = (x + 0.42 * y) / tile, (z + 0.87 * y) / tile
                else:
                    u, v = (
                        math.atan2(y, x) / math.tau % 1,
                        self.meridian.get(vertex, z) / tile,
                    )
                coordinates.append((i, u, v))
            seam = (
                mode == "body"
                and max(p[1] for p in coordinates) - min(p[1] for p in coordinates)
                > 0.5
            )
            for i, u, v in coordinates:
                uv.data[i].uv = (
                    (u + int(seam and u < 0.5)) * (8 if mode == "body" else 1),
                    v,
                )
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        return obj


def ring(surface, r, z, segments, angle_offset=0):
    if r == 0:
        return [surface.vertex(0, 0, z)] * segments
    return [
        surface.vertex(r * math.cos(a), r * math.sin(a), z)
        for a in (angle_offset + i * math.tau / segments for i in range(segments))
    ]


def connect(surface, a, b, material=0, mode="body", skip=()):
    for i in range(len(a)):
        if i in skip:
            continue
        j = (i + 1) % len(a)
        indices = tuple(dict.fromkeys((a[i], a[j], b[j], b[i])))
        surface.face(indices, material, mode)


def throw_variation(a):
    return (
        0.52 * math.sin(3 * a + 0.57)
        + 0.29 * math.cos(5 * a - 0.81)
        + 0.19 * math.sin(8 * a + 0.37)
    )


def vessel(glaze, clay, pooled):
    surface = Surface()
    profile = [*OUTER, *reversed(INSIDE[:-1])]
    circles = []
    for row, (r, z) in enumerate(profile):
        if r == 0:
            circles.append([surface.vertex(0, 0, z)] * COLUMNS)
            continue
        c = []
        for col in range(COLUMNS):
            a = math.tau * col / COLUMNS
            amp = (
                (0.145 * (1 - min(1, abs(z - 48) / 45)) + 0.08)
                * min(1, z / 9)
                * min(1, max(0, (79.7 - z) / 2.1))
            )
            rr = r + (amp * throw_variation(a) if row < len(OUTER) else 0)
            zz = z
            if 16.4 <= z <= 19.2:
                zz += 0.25 * math.sin(3 * a + 0.66) + 0.14 * math.cos(7 * a)
            c.append(surface.vertex(rr * math.cos(a), rr * math.sin(a), zz))
        circles.append(c)
    excluded = [*range(4), *range(COLUMNS - 4, COLUMNS)]
    distance = 0
    for j, ring_row in enumerate(circles):
        if j:
            distance += math.dist(profile[j], profile[j - 1])
        surface.meridian.update((v, distance) for v in ring_row)
    for j, (a, b) in enumerate(itertools.pairwise(circles)):
        z = profile[j][1]
        cut = UPPER <= j < UPPER + 4 or LOWER <= j < LOWER + 4
        connect(
            surface,
            a,
            b,
            2 if j < len(OUTER) and z == 18.0 else int(j < len(OUTER) and z < 18.0),
            "plane" if j < 6 or j > len(profile) - 5 else "body",
            excluded if cut else (),
        )
    boundary = [
        *((i, 0) for i in range(-4, 5)),
        *((4, j) for j in range(1, 5)),
        *((i, 4) for i in range(3, -5, -1)),
        *((-4, j) for j in range(3, 0, -1)),
    ]
    directions = [math.atan2((j - 2) / 2, i / 4) for i, j in boundary]

    def root(row, lower):
        roots = []
        for (i, j), theta in zip(boundary, directions):
            k = row + (4 - j if lower else j)
            idx = circles[k][i % COLUMNS]
            z0 = profile[row + 2][1]
            z = z0 + (0.5 * (profile[row + 4][1] - profile[row][1])) * math.sin(
                theta
            ) * (-1 if lower else 1)
            ia = 4 * math.tau / COLUMNS * math.cos(theta)
            r = profile[row + 2][0] + (z - z0) * (0.043 if lower else 0.046)
            surface.vertices[idx] = (r * math.cos(ia), r * math.sin(ia), z)
            roots.append(idx)
        return roots

    top = root(UPPER, False)
    bottom = root(LOWER, True)
    first_handle_vertex = len(surface.vertices)
    prev = top
    for n, ctrl in enumerate(HANDLE):
        control = np.array(ctrl)
        for i in range(1, 11):
            if n == len(HANDLE) - 1 and i == 10:
                continue
            t = i / 10
            q = 1 - t
            x, z = (
                q**3 * control[0]
                + 3 * q * q * t * control[1]
                + 3 * q * t * t * control[2]
                + t**3 * control[3]
            )
            tx, tz = 3 * (
                q * q * (control[1] - control[0])
                + 2 * q * t * (control[2] - control[1])
                + t * t * (control[3] - control[2])
            )
            length = math.hypot(tx, tz)
            nx, nz = -tz / length, tx / length
            d = n + t
            fade1 = math.exp(-d * 5.0)
            fade2 = math.exp(-(len(HANDLE) - d) * 4.9)
            w = 5.45 + 2.65 * (fade1 + fade2)
            h = 3.14 + 2.45 * fade1 + 3.40 * fade2

            def signed(v):
                return math.copysign(abs(v) ** 0.70, v)

            c = [
                surface.vertex(
                    x + nx * h * signed(math.sin(a)),
                    w * signed(math.cos(a)),
                    z + nz * h * signed(math.sin(a)),
                )
                for a in directions
            ]
            connect(surface, prev, c, mode="handle")
            prev = c
    connect(surface, prev, bottom, mode="handle")
    obj = surface.object(
        "CLK-151 · glazed vessel and pulled strap", (glaze, clay, pooled), 32
    )
    for group, ids in (
        (
            "Handle and attachment roots",
            [*range(first_handle_vertex, len(surface.vertices)), *top, *bottom],
        ),
        (
            "Foot and glaze break",
            [v.index for v in obj.data.vertices if v.co.z < 0.0195],
        ),
    ):
        obj.vertex_groups.new(name=group).add(ids, 1, "REPLACE")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.delete(
        bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS"
    )
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if not all(e.is_manifold for e in bm.edges):
        raise ValueError("Cup wall and strap must form one closed ceramic shell")
    obj["ceramicVolumeCm3"] = round(bm.calc_volume() * 1e6, 3)
    bm.to_mesh(obj.data)
    bm.free()
    obj.location.z = 0.001
    return obj


def turned(name, profile, material, count, scale):
    surface = Surface()
    rings = [ring(surface, r, h, count) for r, h in profile]
    for j, (a, b) in enumerate(itertools.pairwise(rings)):
        connect(
            surface,
            a,
            b,
            mode="plane"
            if abs(profile[j + 1][0] - profile[j][0])
            > abs(profile[j + 1][1] - profile[j][1])
            else "body",
        )
    return surface.object(name, [material], scale)


def inside_radius(z):
    for (r0, z0), (r1, z1) in itertools.pairwise(INSIDE):
        if z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return INSIDE[-1][0]


def capacity(points):
    return round(
        sum(
            (z1 - z0) * math.pi * (r0 * r0 + r0 * r1 + r1 * r1) / 3
            for (r0, z0), (r1, z1) in itertools.pairwise(points)
        )
        / 1000,
        2,
    )


def liquid_surface():
    z = 61.8
    radius = inside_radius(z)
    return [
        (0, z),
        (radius - 10, z),
        (radius - 4.0, z + 0.006),
        (radius - 2.0, z + 0.049),
        (radius - 1.15, z + 0.127),
        (radius - 0.63, z + 0.245),
        (radius - 0.32, z + 0.46),
        (radius - 0.13, z + 0.75),
        (inside_radius(z + 1.05) + 0.015, z + 1.05),
    ]


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    glaze_map, clay_map, cork_map = textures()
    glaze, g = material(
        "CLK-151 · warm white reactive glaze", (0.78, 0.74, 0.66), 0.33, glaze_map
    )
    g.inputs["IOR"].default_value = 1.51
    g.inputs["Coat Weight"].default_value = 0.25
    g.inputs["Coat Roughness"].default_value = 0.23
    clay, _ = material(
        "CLK-151 · unglazed Hasami clay", (0.48, 0.31, 0.20), 0.78, clay_map
    )
    cork, _ = material(
        "Coaster · compressed natural cork", (0.39, 0.23, 0.12), 0.89, cork_map
    )
    pooled, _ = material("CLK-151 · fired glaze break", (0.48, 0.35, 0.21), 0.36)
    ceramic = vessel(glaze, clay, pooled)
    ceramic["nominalCapacityMl"] = 300
    ceramic["modelRimCapacityMl"] = capacity(INSIDE)
    coaster = turned(
        "Cork coaster · eased edge",
        [
            (0, -2),
            (50.9, -2),
            (51.48, -1.90),
            (51.83, -1.66),
            (52, -1.22),
            (52, 0.23),
            (51.87, 0.60),
            (51.55, 0.87),
            (51.0, 1),
            (0, 1),
        ],
        cork,
        96,
        25,
    )
    top = liquid_surface()
    tea, g = material("Tea · brewed amber", (0.115, 0.045, 0.018), 0.085)
    g.inputs["IOR"].default_value = 1.333
    g.inputs["Transmission Weight"].default_value = 1
    absorb = tea.node_tree.nodes.new("ShaderNodeVolumeAbsorption")
    absorb.inputs["Color"].default_value = (0.80, 0.37, 0.11, 1)
    absorb.inputs["Density"].default_value = 61
    tea.node_tree.links.new(
        absorb.outputs[0], tea.node_tree.nodes["Material Output"].inputs["Volume"]
    )
    depth = [(r - 0.12 if r else 0, z + 0.09) for r, z in INSIDE if z < 61.8]
    liquid = turned("Tea · enclosed infusion", [*depth, *reversed(top)], tea, 128, 25)
    liquid.location.z = 0.001
    liquid["volumeMl"] = capacity(
        [*[(r, z) for r, z in INSIDE if z < 61.8], (inside_radius(61.8), 61.8)]
    )
    sc = bpy.context.scene
    sc.name = "KINTO CLK-151 · white · 300 mL"
    parts = bpy.data.collections.new(sc.name)
    sc.collection.children.link(parts)
    for obj in (ceramic, coaster, liquid):
        for current in list(obj.users_collection):
            current.objects.unlink(obj)
        parts.objects.link(obj)
    sc.unit_settings.system = "METRIC"
    sc["reference"] = "https://kinto-europe.com/products/29513"
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            view = area.spaces.active
            view.region_3d.view_location = (0.009, 0, 0.038)
            view.region_3d.view_distance = 0.20
            view.region_3d.view_rotation = Vector((0.14, -0.93, 0.34)).to_track_quat(
                "Z", "Y"
            )
            view.overlay.show_floor = False
            view.clip_start = 0.0003
            view.shading.color_type = "MATERIAL"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(
        filepath=str(REVIEW / "kinto-clk-151.blend"), compress=True
    )
    web_tea, g = material(
        "Tea · amber surface and capillary meniscus", (0.068, 0.026, 0.010), 0.087
    )
    g.inputs["IOR"].default_value = 1.333
    wet = turned("Tea meniscus", list(reversed(top)), web_tea, 96, 25)
    wet.location.z = 0.001
    wet["teaSurface"] = True
    tone = wet.data.color_attributes.new(
        name="Brew depth", type="BYTE_COLOR", domain="POINT"
    )
    for vertex in wet.data.vertices:
        radius = math.hypot(vertex.co.x, vertex.co.y) * 1000
        edge = math.exp((radius - top[-1][0]) / 2.40)
        tone.data[vertex.index].color = (
            0.033 + 0.108 * edge,
            0.009 + 0.034 * edge,
            0.003 + 0.006 * edge,
            1,
        )
    hue = web_tea.node_tree.nodes.new("ShaderNodeVertexColor")
    hue.layer_name = tone.name
    web_tea.node_tree.links.new(hue.outputs["Color"], g.inputs["Base Color"])
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (ceramic, coaster, wet):
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(TARGET),
        use_selection=True,
        export_extras=True,
        export_animations=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )
    print(
        f"{TARGET.name}: {TARGET.stat().st_size} bytes, cavity {capacity(INSIDE)} mL, tea {liquid['volumeMl']} mL"
    )


if __name__ == "__main__":
    build()
