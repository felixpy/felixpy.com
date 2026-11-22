import argparse
import gzip
import math
import runpy
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def point(x, y, z):
    return Vector((x, -z, y))


def build_room():
    gear = runpy.run_path(str(Path(__file__).with_name("movable-camp-gear.py")))
    gear["exclude_from_static_lighting"](bpy.context.scene)
    graph = bpy.context.evaluated_depsgraph_get()
    points, faces, materials, indices = [], [], [], []
    lookup, images = {}, {}

    def color(socket, depth=0):
        if depth > 4:
            return np.ones(3)
        if not socket.is_linked:
            value = socket.default_value
            return (
                np.array(value[:3]) if hasattr(value, "__len__") else np.full(3, value)
            )
        node = socket.links[0].from_node
        if node.type == "TEX_IMAGE" and node.image:
            image = node.image
            if image.name not in images:
                pixels = np.empty(len(image.pixels), dtype=np.float32)
                if len(pixels):
                    image.pixels.foreach_get(pixels)
                    rgba = pixels.reshape(image.size[1], image.size[0], -1)
                    colors = rgba[
                        :: max(1, image.size[1] // 48), :: max(1, image.size[0] // 48)
                    ]
                    images[image.name] = np.average(colors[:, :, :3], axis=(0, 1))
                else:
                    images[image.name] = np.ones(3)
            return images[image.name]
        if node.type == "MIX_RGB":
            return color(node.inputs[1], depth + 1) * color(node.inputs[2], depth + 1)
        if node.type == "MIX":
            sockets = [
                item
                for item in node.inputs
                if item.enabled and item.name in ("A", "B") and item.type == "RGBA"
            ]
            if len(sockets) == 2:
                return color(sockets[0], depth + 1) * color(sockets[1], depth + 1)
        return np.ones(3)

    def material_index(mat):
        if mat not in lookup:
            lookup[mat] = len(materials)
            base = np.full(3, 0.28)
            if mat and mat.node_tree:
                bsdf = next(
                    (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
                    None,
                )
                if bsdf:
                    metallic = bsdf.inputs["Metallic"].default_value
                    base = color(bsdf.inputs["Base Color"]) * (1 - metallic * 0.91)
            materials.append(np.clip(base, 0.012, 0.84))
        return lookup[mat]

    for entry in graph.object_instances:
        obj = entry.object
        if not gear["static_mesh"](entry):
            continue
        matrix = entry.matrix_world
        corners = [matrix @ Vector(p) for p in obj.bound_box]
        if any(
            max(p[i] for p in corners) < lo or min(p[i] for p in corners) > hi
            for i, lo, hi in [(0, -1.5, 2.75), (1, -3.5, 0.82), (2, -0.2, 2.95)]
        ):
            continue
        mesh = obj.data
        if not mesh.polygons:
            continue
        mesh.calc_loop_triangles()
        slots = [material_index(slot.material) for slot in obj.material_slots] or [
            material_index(None)
        ]
        first = len(points)
        points.extend(matrix @ v.co for v in mesh.vertices)
        faces.extend(tuple(first + j for j in t.vertices) for t in mesh.loop_triangles)
        indices.extend(slots[t.material_index] for t in mesh.loop_triangles)
    if len(faces) < 20000:
        raise ValueError("Expected the tagged studio-master room meshes")
    print(
        f"Tracing {len(faces)} triangles, {len(materials)} diffuse reflectances",
        flush=True,
    )
    return BVHTree.FromPolygons(points, faces, all_triangles=True), indices, materials


def make_lighting(bvh):
    glass = bpy.data.objects["Window glass"]
    corners = [glass.matrix_world @ Vector(p) for p in glass.bound_box]
    window_x = glass.matrix_world.translation.x - 0.007
    y0, y1 = min(p.z for p in corners) + 0.026, max(p.z for p in corners) - 0.026
    z0, z1 = min(-p.y for p in corners) + 0.026, max(-p.y for p in corners) - 0.026
    aperture = [
        point(window_x, y0 + fy * (y1 - y0), z0 + fz * (z1 - z0))
        for fy in (0.25, 0.75)
        for fz in (0.25, 0.75)
    ]
    area = (y1 - y0) * (z1 - z0) / len(aperture)
    sun = point(-3.8, 1.85, 2.19).normalized()
    ceiling = bpy.data.objects["Ceiling diffuser outlet"].matrix_world.translation
    aj = bpy.data.objects[
        "Louis Poulsen AJ Floor · polished stainless steel"
    ].matrix_world
    floor = aj @ point(0.10, 1.067, 0)
    floor_axis = (aj @ point(0.424, 0.067, 0) - floor).normalized()
    bulbs = {
        obj.parent.name: obj.matrix_world
        for obj in bpy.context.scene.objects
        if obj.name.startswith("Optical center") and obj.parent
    }
    desk = bulbs["Dyson Solarcycle Morph Desk · CD06"].translation
    bench = bulbs["Workbench lamp"].translation
    bench_axis = (bulbs["Workbench lamp"].to_3x3() @ point(0, -1, 0)).normalized()
    up = point(0, 1, 0)
    board_sources = [point(2.354, 1.5978, 0.678 + offset) for offset in (-0.172, 0.172)]
    board_axis = point(0.135, -0.3978, 0).normalized()
    rail = bpy.data.objects["ERCO Parscan 48V · Minirail"]
    heads = []
    for obj in rail.children:
        if not obj.get("gearTrackAim"):
            continue
        outer = obj.data.spot_size / 2
        inner = outer * (1 - obj.data.spot_blend)
        axis = obj.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        heads.append(
            (
                obj.matrix_world.translation,
                axis,
                obj["gearTrackCandela"] * 0.24,
                (math.cos(outer), math.cos(inner)),
            )
        )
    if len(heads) != 3:
        raise ValueError(
            "The equipment track needs three independently aimed optical exits"
        )

    def window_pass(hit, ray):
        if ray.x >= -0.01:
            return False
        t = (window_x - hit.x) / ray.x
        if t <= 0:
            return False
        end = hit + ray * t
        return (
            z0 < -end.y < z1
            and y0 < end.z < y1
            and bvh.ray_cast(hit, ray, max(0.001, t - 0.003))[0] is None
        )

    def lamp(hit, normal, source, axis, power, spread=None):
        direction = source - hit
        d = direction.length
        if d < 0.032:
            return 0.0
        direction /= d
        cosine = max(0.0, normal.dot(direction))
        cone = max(0.0, (-direction).dot(axis))
        falloff = cone**2
        if spread is not None:
            edge, inner = spread
            t = min(1.0, max(0.0, (cone - edge) / (inner - edge)))
            falloff = t * t * (3 - 2 * t)
        if (
            cosine * (falloff if spread else cone) <= 0.001
            or bvh.ray_cast(hit, direction, max(0.001, d - 0.055))[0] is not None
        ):
            return 0.0
        return power * cosine * falloff / max(0.085, d * d)

    def incoming(hit, normal):
        hit = hit + normal * 0.004
        sky = 0.0
        for opening in aperture:
            direction = opening - hit
            d = direction.length
            if d < 0.02:
                continue
            direction /= d
            cosine = max(0.0, normal.dot(direction))
            if cosine > 0 and window_pass(hit, direction):
                sky += (
                    cosine
                    * max(0.0, -direction.x)
                    * area
                    / (math.pi * max(0.08, d * d))
                )
        cosine = normal.dot(sun)
        clear = cosine if cosine > 0 and window_pass(hit, sun) else 0.0
        room_lights = lamp(hit, normal, ceiling, -up, 0.99) + lamp(
            hit, normal, floor, floor_axis, 1.20
        )
        return np.array(
            (
                min(0.95, sky),
                clear,
                room_lights,
                lamp(hit, normal, desk, -up, 0.26),
                lamp(hit, normal, bench, bench_axis, 0.31),
                sum(
                    lamp(hit, normal, source, board_axis, 0.065)
                    for source in board_sources
                ),
                sum(lamp(hit, normal, *head) for head in heads),
            )
        )

    return incoming


def bake(samples):
    bvh, indices, materials = build_room()
    incoming = make_lighting(bvh)
    w, h, d = 32, 24, 32
    ray_hits = np.empty((d, h, w, samples), dtype=np.int32)
    directions = []
    for i in range(samples):
        y = 1 - 2 * (i + 0.5) / samples
        r = math.sqrt(1 - y * y)
        a = i * 2.399963229728653
        directions.append((r * math.cos(a), y, r * math.sin(a)))
    vectors = [point(*v) for v in directions]
    directions = np.array(directions)
    luma = np.array([0.2126, 0.7152, 0.0722])
    tint = np.array(
        [
            [0.66, 0.83, 1.0],
            [1.0, 0.89, 0.71],
            [1.0, 0.80, 0.62],
            [1.0, 0.77, 0.54],
            [1.00, 0.85, 0.69],
            [1.00, 0.85, 0.69],
            [1.00, 0.74, 0.51],
        ]
    )
    first = np.zeros((d, h, w, len(tint), 6), dtype=np.float32)
    surfels = {}
    outgoing = [np.zeros((len(tint), 3))]
    surfaces = [(np.zeros(3), np.zeros(3), np.zeros(3))]
    origin = (-1.375, -0.125, -0.6875)

    def project(paths):
        rgb = paths.mean(axis=-3)
        lum = paths @ luma
        moment = np.einsum("...si,sd->...id", lum, directions) / np.maximum(
            lum.sum(axis=-2)[..., None], 1.0e-10
        )
        return np.concatenate((rgb, moment), axis=-1)

    for z in range(d):
        for y in range(h):
            for x in range(w):
                probe = point(
                    origin[0] + (x + 0.5) * 0.125,
                    origin[1] + (y + 0.5) * 0.125,
                    origin[2] + (z + 0.5) * 0.125,
                )
                ids = ray_hits[z, y, x]
                for j, v in enumerate(vectors):
                    hit, normal, index, _ = bvh.ray_cast(probe, v, 7.3)
                    if hit is None:
                        ids[j] = 0
                        continue
                    if normal.dot(v) > 0:
                        normal.negate()
                    material = indices[index]
                    key = (
                        round(hit.x * 16),
                        round(hit.y * 16),
                        round(hit.z * 16),
                        round(normal.x * 4),
                        round(normal.y * 4),
                        round(normal.z * 4),
                        material,
                    )
                    patch = surfels.get(key)
                    if patch is None:
                        patch = len(outgoing)
                        surfels[key] = patch
                        outgoing.append(
                            materials[material] * incoming(hit, normal)[:, None] * tint
                        )
                        surfaces.append(
                            (
                                (hit.x, hit.z, -hit.y),
                                (normal.x, normal.z, -normal.y),
                                materials[material],
                            )
                        )
                    ids[j] = patch
                first[z, y, x] = project(np.asarray([outgoing[i] for i in ids]))
        if z % 4 == 0:
            print(
                f"Bounce volume {z + 1}/{d}, {len(surfels)} shaded surface patches",
                flush=True,
            )
    outgoing = np.asarray(outgoing)
    surfaces = np.asarray(surfaces)
    position = surfaces[:, 0] + surfaces[:, 1] * 0.079
    indices = np.clip(
        (position - np.asarray(origin)) / 0.125 - 0.5,
        0,
        [w - 1.001, h - 1.001, d - 1.001],
    )
    low = np.floor(indices).astype(np.int32)
    t = indices - low
    reflected = np.zeros_like(outgoing)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                weight = np.prod(np.where([dx, dy, dz], t, 1 - t), axis=1)
                values = first[low[:, 2] + dz, low[:, 1] + dy, low[:, 0] + dx]
                sided = np.clip(
                    1 + 2 * np.einsum("nsc,nc->ns", values[:, :, 3:], surfaces[:, 1]),
                    0.04,
                    3,
                )
                reflected += (
                    values[:, :, :3] * sided[:, :, None] * weight[:, None, None]
                )
    outgoing += reflected * surfaces[:, 2, None, :]
    data = np.empty(first.shape, dtype=np.uint8)
    for z in range(d):
        combined = project(outgoing[ray_hits[z]])
        data[z, :, :, :, :3] = np.rint(
            np.sqrt(np.clip(combined[:, :, :, :3], 0, 1)) * 255
        )
        data[z, :, :, :, 3:] = np.rint(
            np.clip(combined[:, :, :, 3:], -1, 1) * 127 + 128
        )
    print(
        "Mean first-bounce RGB per source",
        np.round(first[:, :, :, :, :3].mean(axis=(0, 1, 2)), 4),
        flush=True,
    )
    return data


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument(
        "--out", type=Path, default=root / "public/media/lighting/room-irradiance.gz"
    )
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    raw = bake(args.samples)
    moment = raw[..., 3:].astype(np.int16)
    moment = np.rint((moment - 128) / 4) * 4 + 128
    raw[..., 3:] = np.where(
        raw[..., :3].max(axis=-1, keepdims=True) < 6, 128, np.clip(moment, 0, 255)
    )
    planes = raw.transpose(3, 4, 0, 1, 2).copy()
    planes[..., 1:] = np.diff(planes, axis=-1)
    compressed = gzip.compress(b"RGI3" + planes.tobytes(), compresslevel=9, mtime=0)
    args.out.write_bytes(compressed)
    print(
        f"{raw.shape[0] * raw.shape[1] * raw.shape[2] * args.samples} first-hit rays; {len(compressed)} bytes",
        flush=True,
    )


if __name__ == "__main__":
    main()
