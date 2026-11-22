import gzip
import json
import math
import struct
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

root = Path(__file__).resolve().parents[2]
master = root / ".review/atelier/studio-master.glb"
source = master.read_bytes()
json_bytes = struct.unpack_from("<I", source, 12)[0]
model = json.loads(source[20:20 + json_bytes])
binary = memoryview(source)[28 + json_bytes:]
types = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
sizes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}


def read_accessor(index):
    accessor = model["accessors"][index]
    view = model["bufferViews"][accessor["bufferView"]]
    dtype = np.dtype(types[accessor["componentType"]])
    elements = sizes[accessor["type"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", dtype.itemsize * elements)
    return np.ndarray((accessor["count"], elements), dtype, binary, offset, (stride, dtype.itemsize))


def weld_normals(attributes):
    p = read_accessor(attributes["POSITION"])
    n = read_accessor(attributes["NORMAL"])
    ids = read_accessor(attributes["_STUDIOINDEX"])[:, 0]
    uv = read_accessor(attributes["TEXCOORD_0"])
    epsilon = max(1.e-9, min(2.e-6, float(np.ptp(p, axis=0).max()) * 1.e-6))
    quantized = np.rint(p / epsilon).astype(np.int64)
    order = np.lexsort(quantized.T)
    groups = np.flatnonzero(np.concatenate(([True], np.any(np.diff(quantized[order], axis=0), axis=1), [True])))
    results = {}
    for g in np.flatnonzero(np.diff(groups) > 1):
        ring = order[groups[g]:groups[g + 1]]
        if len(ring) > 512 or np.ptp(uv[ring], axis=0).max() < 0.65:
            continue
        normals = n[ring]
        if np.ptp(normals, axis=0).max() < .004:
            continue
        for local, vertex in enumerate(ring):
            neighbours = normals @ normals[local] > math.cos(math.radians(14))
            if np.count_nonzero(neighbours) < 2:
                continue
            smooth = Vector(normals[neighbours].mean(axis=0)).normalized()
            change = smooth.dot(Vector(normals[local]))
            if math.cos(math.radians(7)) <= change < math.cos(math.radians(.18)):
                results[int(ids[vertex])] = tuple(round(32767 * max(-1., min(1., v))) for v in smooth)
    return results


patches = {}
for node in model["nodes"]:
    key = node.get("extras", {}).get("studioSurface")
    if not key or key in patches or "mesh" not in node:
        continue
    changes = {}
    for primitive in model["meshes"][node["mesh"]]["primitives"]:
        attributes = primitive["attributes"]
        if {"POSITION", "NORMAL", "TEXCOORD_0", "_STUDIOINDEX"}.issubset(attributes):
            changes.update(weld_normals(attributes))
    patches[key] = changes

payload = bytearray(b"SNR1")
adjusted = {key: data for key, data in patches.items() if data}
for key, changes in sorted(adjusted.items()):
    label = key.encode("ascii")
    payload.extend(struct.pack("<BI", len(label), len(changes)))
    payload.extend(label)
    for index, normal in sorted(changes.items()):
        payload.extend(struct.pack("<I3h", index, *normal))
if not adjusted:
    raise RuntimeError("The authoring export has no continuous UV seams to finish")
destination = root / "public/media/models/surface-normals.gz"
destination.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
print(json.dumps({"blender": bpy.app.version_string, "geometries": len(patches), "adjusted": len(adjusted),
                  "vertices": sum(map(len, adjusted.values())), "bytes": destination.stat().st_size}))
