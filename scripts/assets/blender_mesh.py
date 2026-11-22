import math
import struct
from pathlib import Path

import bpy


def write_mesh(obj, output_path):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        transform = evaluated.matrix_world
        normal_transform = transform.to_3x3().inverted_safe().transposed()
        mirrored = transform.to_3x3().determinant() < 0
        texcoords = mesh.uv_layers.active
        corners = []
        for triangle in mesh.loop_triangles:
            for loop_index in reversed(triangle.loops) if mirrored else triangle.loops:
                vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
                point = transform @ vertex.co
                normal = (
                    normal_transform @ mesh.corner_normals[loop_index].vector
                ).normalized()
                uv = texcoords.uv[loop_index].vector if texcoords else (0, 0)
                corners.append(
                    (
                        (point.x, point.z, -point.y),
                        (normal.x, normal.z, -normal.y),
                        tuple(uv),
                    )
                )
        if not corners:
            raise ValueError(f"{obj.name} has no triangles")
        values = [position + uv for position, _, uv in corners]
        minimum = tuple(map(min, zip(*values)))
        span = tuple(max(v[i] for v in values) - minimum[i] for i in range(5))
        vertices, lookup, indices = bytearray(), {}, []
        for (position, normal, uv), value in zip(corners, values):
            coord = [
                round((axis - minimum[i]) * 65535 / span[i]) if span[i] > 1e-12 else 0
                for i, axis in enumerate(value)
            ]
            packed = struct.pack(
                "<3H3h2H",
                *coord[:3],
                *(round(max(-1, min(1, v)) * 32767) for v in normal),
                *coord[3:],
            )
            if packed not in lookup:
                lookup[packed] = len(lookup)
                vertices.extend(packed)
            indices.append(lookup[packed])
        if len(lookup) > 65536 or not all(math.isfinite(v) for v in minimum + span):
            raise ValueError(f"{obj.name} exceeds the compact mesh limits")
        header = struct.pack(
            "<4sII10f", b"BMS1", len(lookup), len(indices), *minimum, *span
        )
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(header + vertices + struct.pack(f"<{len(indices)}H", *indices))
        return {
            "vertices": len(lookup),
            "triangles": len(indices) // 3,
            "bytes": path.stat().st_size,
        }
    finally:
        evaluated.to_mesh_clear()
