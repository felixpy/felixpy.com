import gzip
import struct
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[2]
source = np.load(ROOT / ".review/atelier/whale-tail-slice-source.npz")
triangles, groups = source["triangles"], source["component"]
heights = triangles[:, :, 2]
floor, ceiling = heights.min(axis=1), heights.max(axis=1)
pitch = 0.24


def cross_section(z):
    active = (floor <= z) & (ceiling > z)
    tri, group = triangles[active], groups[active]
    a = tri
    b = np.roll(tri, -1, axis=1)
    crossing = (a[:, :, 2] > z) != (b[:, :, 2] > z)
    a, b = a[crossing], b[crossing]
    fraction = ((z - a[:, 2]) / (b[:, 2] - a[:, 2]))[:, None]
    lines = np.round(
        (a[:, :2] + (b[:, :2] - a[:, :2]) * fraction).reshape((-1, 2, 2)), 4
    )
    solids = []
    for component in np.unique(group):
        edges = shapely.linestrings(lines[group == component])
        solids.extend(shapely.get_parts(shapely.polygonize(edges)))
    return shapely.union_all(solids)


def xy(coords):
    return np.round(np.asarray(coords) * [100, -100]).astype("<i2").tobytes()


def encode(z, index):
    section = (
        cross_section(z)
        .buffer(-0.16, quad_segs=2)
        .simplify(0.048, preserve_topology=True)
    )
    rings = []
    hatches = []
    for piece in shapely.get_parts(section):
        if piece.geom_type != "Polygon" or piece.area < 0.016:
            continue
        for hole, ring in [
            (False, piece.exterior),
            *((True, r) for r in piece.interiors),
        ]:
            pts = ring.coords[:-1]
            rings.append(
                struct.pack("<H", len(pts) | (0x8000 if hole else 0)) + xy(pts)
            )
        core = piece.buffer(-0.33, quad_segs=2)
        if core.is_empty:
            continue
        x0, y0, x1, y1 = core.bounds
        crosswise = index % 2
        interval = 0.4 if (index < 3 or index > int(ceiling.max() / pitch) - 4) else 3.0
        start, stop = (x0, x1) if crosswise else (y0, y1)
        for k in np.arange(np.ceil(start / interval) * interval, stop, interval):
            line = LineString(
                [(k, y0 - 1), (k, y1 + 1)] if crosswise else [(x0 - 1, k), (x1 + 1, k)]
            )
            for seg in shapely.get_parts(core.intersection(line)):
                if seg.geom_type == "LineString" and seg.length > 0.20:
                    hatches.append(xy([seg.coords[0], seg.coords[-1]]))
    return (
        struct.pack("<H", len(rings))
        + b"".join(rings)
        + struct.pack("<H", len(hatches))
        + b"".join(hatches)
    )


layers = [
    encode((i + 0.5) * pitch, i) for i in range(int(np.ceil(ceiling.max() / pitch)))
]
offsets = np.cumsum([0, *map(len, layers)], dtype="<u4")
raw = (
    struct.pack("<4sHH", b"WP02", len(layers), round(pitch * 1000))
    + offsets.tobytes()
    + b"".join(layers)
)
output = (
    ROOT
    / ".references/06-工坊与工具/三维打印与模型/Whale-tail girl/Blender/whale-tail-paths.gz"
)
output.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
print(f"{len(layers)} layers at {pitch} mm, {output.stat().st_size} compressed bytes")
