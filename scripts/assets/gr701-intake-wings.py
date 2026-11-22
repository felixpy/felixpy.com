import math

from mathutils import Vector


SECTIONS = (
    (-212.0, 16.0, 3.0), (-211.1, 18.6, 4.7), (-208.0, 20.7, 6.3),
    (-139.0, 45.3, 28.0), (-131.5, 48.0, 29.9),
    (-64.0, 67.1, 30.6), (-56.0, 68.4, 30.6), (54.0, 68.4, 30.6),
    (61.0, 67.4, 30.6), (126.5, 47.1, 29.9), (135.0, 44.0, 28.0),
    (201.2, 20.4, 6.2), (204.5, 18.4, 4.5), (206.0, 15.9, 3.0),
)


def skin(side, u, y, outward):
    radius = min(1.0, max(0.0, (u - 23.0) / 45.4))
    crown = 0.55 * math.sin(math.pi * radius)
    return (side * (125.3 - u + 0.603 * outward), y, 231.8 + u * 0.755 + crown + 0.798 * outward)


def wing_panel(side, title, shell):
    vertices = []
    station_size = 0
    for y, span, rear in SECTIONS:
        fold = Vector((125.3, 231.8))
        section = [
            fold + Vector((-0.227 * rear, -rear)),
            fold + Vector((-0.35, -1.6)),
            fold + Vector((-0.09, -0.45)),
            fold + Vector((-0.17, 0.14)),
            fold + Vector((-0.78, 0.76)),
        ]
        for t in (0.14, 0.30, 0.50, 0.70, 0.86, 1.0):
            x, _, z = skin(1, span * t, y, 0)
            section.append(Vector((x, z)))
        tip = section[-1]
        section.extend((tip + Vector((-0.62, -0.20)), tip + Vector((-0.82, -0.86)),
                        tip + Vector((-0.82, -3.8))))
        inner = []
        for i, point in enumerate(section):
            before = (point - section[max(0, i - 1)]).normalized()
            after = (section[min(i + 1, len(section) - 1)] - point).normalized()
            tangent = (before + after).normalized()
            normal = Vector((-tangent.y, tangent.x))
            inner.append(point + 1.35 * normal)
        circumference = [*section, *reversed(inner)]
        station_size = len(circumference)
        vertices.extend((side * p.x, y, p.y) for p in circumference)
    faces = []
    for row in range(len(SECTIONS) - 1):
        for i in range(station_size):
            j = (i + 1) % station_size
            faces.append((row * station_size + i, row * station_size + j,
                          (row + 1) * station_size + j, (row + 1) * station_size + i))
    faces.extend((tuple(range(station_size)), tuple(range(len(vertices) - station_size, len(vertices)))))
    panel = shell(title + " · roll-formed aluminium cheek", vertices, faces)
    uv = panel.data.uv_layers.active
    for face in panel.data.polygons:
        for loop in face.loop_indices:
            co = panel.data.vertices[panel.data.loops[loop].vertex_index].co
            lateral, depth = abs(co.x) * 1000, -co.y * 1000
            across = (depth - 231.8) * 1.024 if depth < 231.8 else math.hypot(125.3 - lateral, depth - 231.8)
            uv.data[loop].uv = (co.z / 0.15, across / 67.0)
    panel["foldedWallMm"] = 1.35
    return panel


def vanes(side, title, shell):
    parts = []
    for index, x in enumerate((25, 41, 57, 73, 89, 105)):
        nose = max(242.6, min(275.4 - (x - 25) * 0.26, skin(1, 125.3 - x, 0, 0)[2] - 7.5))
        depth = min(13.4, max(2.4, nose - 242.0))
        extent = min(205.0, 52 + (x - 10) * 1.76, 190 + (105 - x) * 0.9)
        end_recess = min(6.5, depth - 1.4)
        outline = [(-0.55, 0), (0.55, 0), (0.92, -0.8),
                   (1.20, -depth), (-0.60, -depth), (-0.83, -0.82)]
        vertices, faces = [], []
        for y, retreat in ((-extent, end_recess), (-extent + 8, end_recess * 0.34),
                           (-extent + 19, 0), (extent - 19, 0),
                           (extent - 8, end_recess * 0.34), (extent, end_recess)):
            vertices.extend((side * (x + u), y, nose + z - retreat * (1 + z / depth)) for u, z in outline)
        n = len(outline)
        for j in range(5):
            for i in range(n):
                k = (i + 1) % n
                faces.append((j * n + i, j * n + k, (j + 1) * n + k, (j + 1) * n + i))
        faces.extend((tuple(range(n)), tuple(range(5 * n, 6 * n))))
        part = shell(title + " straight intake blade %02d" % (index + 1), vertices, faces, 0.18)
        part["nose_x_mm"] = side * x
        parts.append(part)
    return parts


def fit_sides(batches, shell, lettering):
    for side, title in ((-1, "Port"), (1, "Starboard")):
        batches["wing"].append(wing_panel(side, title, shell))
        batches["vane"].extend(vanes(side, title, shell))
        if side == -1:
            batches["ink"].extend(lettering(lambda u, y, d: skin(side, u, y, d)))
