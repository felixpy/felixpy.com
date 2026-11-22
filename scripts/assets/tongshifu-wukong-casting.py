import math

import numpy as np
import cv2
from PIL import Image
from scipy import ndimage
from scipy.interpolate import PchipInterpolator


def casting():
    parts = []
    gold, darkgold, cobalt, orange, red = 5, 10, 8, 9, 11
    weave, trousers = 18, 19

    def append(name, vertices, faces, finish, uv=None):
        vertices = np.asarray(vertices, float)
        faces = np.asarray(faces, int)
        if uv is None:
            uv = np.zeros((len(faces), 3, 2), dtype="f")
        materials = np.broadcast_to(np.asarray(finish), (len(faces),)).copy()
        parts.append((name, vertices, faces, materials, uv))

    def rings(name, shape, finish, uv_scale=(1, 1), per_ring=None):
        levels, count = shape.shape[:2]
        faces, uvs, materials = [], [], []
        for row in range(levels - 1):
            for col in range(count):
                a = row * count + col
                b = row * count + (col + 1) % count
                u0, u1 = col / count * uv_scale[0], (col + 1) / count * uv_scale[0]
                v0, v1 = (
                    row / (levels - 1) * uv_scale[1],
                    (row + 1) / (levels - 1) * uv_scale[1],
                )
                faces.extend([(a, b, b + count), (a, b + count, a + count)])
                uvs.extend(
                    [[(u0, v0), (u1, v0), (u1, v1)], [(u0, v0), (u1, v1), (u0, v1)]]
                )
                slot = (
                    finish
                    if per_ring is None
                    else per_ring(row / (levels - 1), col / count)
                )
                materials.extend([slot, slot])
        for i in range(1, count - 1):
            end = (levels - 1) * count
            faces.extend([(0, i + 1, i), (end, end + i, end + i + 1)])
            uvs.extend([[(0, 0)] * 3] * 2)
            materials.extend([finish, finish])
        append(name, shape.reshape(-1, 3), faces, materials, np.asarray(uvs, dtype="f"))

    def loft(
        name, sections, finish, power=2, folds=0, fold_rate=6, detail=36, mat=None
    ):
        sections = np.asarray(sections, float)
        z = np.linspace(sections[0, 0], sections[-1, 0], max(12, len(sections) * 4))
        x, y, rx, ry = PchipInterpolator(sections[:, 0], sections[:, 1:], axis=0)(z).T
        a = np.linspace(0, math.tau, detail, endpoint=False)[None, :]
        t = (z - z[0]) / (z[-1] - z[0])
        ripple = (
            1
            + folds
            * np.sin(a * fold_rate + t[:, None] * 1.9)
            * np.sin(np.pi * t[:, None]) ** 0.8
        )
        sx, sy = np.sin(a), -np.cos(a)
        px = x[:, None] + rx[:, None] * np.sign(sx) * abs(sx) ** (2 / power) * ripple
        py = y[:, None] + ry[:, None] * np.sign(sy) * abs(sy) ** (2 / power) * ripple
        rings(
            name,
            np.stack(np.broadcast_arrays(px, py, z[:, None]), -1),
            finish,
            per_ring=mat,
        )

    def sweep(
        name,
        knots,
        widths,
        depths,
        finish,
        reference=(0, 1, 0),
        sides=16,
        density=5,
        finish_at=None,
    ):
        knots = np.asarray(knots, float)
        along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(knots, axis=0), axis=1))]
        along /= along[-1]
        t = np.linspace(0, 1, max(12, len(along) * density))
        path = PchipInterpolator(along, knots, axis=0)(t)
        w = PchipInterpolator(along, widths)(t)
        d = PchipInterpolator(along, depths)(t)
        tangent = np.gradient(path, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1)[:, None]
        normal = np.cross(tangent, reference)
        normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-7)
        binormal = np.cross(tangent, normal)
        a = np.linspace(0, math.tau, sides, endpoint=False)
        cross = normal[:, None] * (w[:, None] * np.cos(a))[:, :, None]
        cross += binormal[:, None] * (d[:, None] * np.sin(a))[:, :, None]
        rings(name, path[:, None] + cross, finish, per_ring=finish_at)

    def patch(
        name, grid, normal, finish, edge_finish, thickness, uv_scale, rim, middle=False
    ):
        rows, cols = grid.shape[:2]
        vs = np.concatenate(
            [grid.reshape(-1, 3), (grid - thickness * normal).reshape(-1, 3)]
        )
        front_size = rows * cols
        faces, mats, uvs = [], [], []

        def quad(a, b, c, d, material, local):
            faces.extend([(a, b, c), (a, c, d)])
            mats.extend([material, material])
            uvs.extend([[local[0], local[1], local[2]], [local[0], local[2], local[3]]])

        def cell_uv(i, j):
            return (j / (cols - 1) * uv_scale[0], i / (rows - 1) * uv_scale[1])

        for i in range(rows - 1):
            for j in range(cols - 1):
                a = i * cols + j
                b, c, d = a + 1, a + cols + 1, a + cols
                local = [
                    cell_uv(i, j),
                    cell_uv(i, j + 1),
                    cell_uv(i + 1, j + 1),
                    cell_uv(i + 1, j),
                ]
                u, v = (j + 0.5) / (cols - 1), (i + 0.5) / (rows - 1)
                border = min(u, 1 - u) < rim[0] or min(v, 1 - v) < rim[1]
                if middle and abs(u - 0.5) < 0.048:
                    border = True
                quad(a, b, c, d, edge_finish if border else finish, local)
                quad(
                    d + front_size,
                    c + front_size,
                    b + front_size,
                    a + front_size,
                    edge_finish,
                    local,
                )
        outline = [
            *range(cols),
            *range(2 * cols - 1, rows * cols, cols),
            *range(rows * cols - 2, (rows - 1) * cols - 1, -1),
            *range((rows - 2) * cols, 0, -cols),
        ]
        for a, b in zip(outline, outline[1:] + outline[:1]):
            quad(b, a, a + front_size, b + front_size, edge_finish, [(0, 0)] * 4)
        append(name, vs, faces, mats, np.asarray(uvs, dtype="f"))

    def armour_panel(
        name, angle, arc, low, high, rx0, rx1, ry0, ry1, drop, scale, middle=False
    ):
        v, u = np.mgrid[0:1:19j, -1:1:37j]
        a = angle + u * arc * (0.87 + 0.13 * v)
        if name in (
            "Flared lamellar skirt · lappet 1",
            "Flared lamellar skirt · lappet 2",
        ):
            sign = np.sign(angle)
            a -= sign * 0.19 * v**1.75 * (1 - sign * u) / 2
        front_drop = drop * np.maximum(0, 1 - u**2) ** 1.3
        z = low + (high - low) * v - (1 - v) * front_drop
        rx = rx0 * (1 - v) + rx1 * v + np.sin(v * np.pi) * 2.0
        ry = ry0 * (1 - v) + ry1 * v + np.sin(v * np.pi) * 2.2
        if middle:
            z += v * (1 - u**2) * 4.0
        n = np.stack((np.sin(a), -np.cos(a), np.zeros_like(a)), -1)
        grid = np.stack((-6 + np.sin(a) * rx, -9.5 - np.cos(a) * ry, z), -1)
        rim_depth = np.minimum(1 - abs(u), 2 * np.minimum(v, 1 - v))
        grid += n * (0.42 * np.exp(-(((rim_depth - 0.055) / 0.048) ** 2)))[..., None]
        patch(name, grid, n, weave, gold, 1.55, scale, (0.046, 0.088), middle)

    def sleeve(name, knots, widths, depths):
        sweep(
            name + " · folded silk sleeve",
            knots,
            widths,
            depths,
            orange,
            reference=(0, 0, 1),
            sides=28,
        )

    loft(
        "Fitted persimmon silk tunic",
        [
            (128.5, -5.6, -8.2, 15, 13),
            (131.5, -5.5, -8, 21.8, 17),
            (139, -5, -9, 20, 17.1),
            (153, -6, -8.5, 24, 19),
            (160, -6, -8.5, 22.5, 18),
            (166, -6.5, -10.5, 15, 12.3),
            (170.6, -6.7, -12.0, 8.2, 7.2),
        ],
        orange,
        folds=0.042,
    )

    for label, x in [("Staff side", -21), ("Cape side", 9.4)]:
        loft(
            label + " · balloon breeches gathered at knee",
            [
                (113.9, x, -7.0, 6.4, 7.0),
                (115.5, x, -7.0, 7.9, 8.3),
                (118.8, x, -7.1, 10.4, 10.1),
                (123, x, -7.3, 12.1, 11.4),
                (128.5, x + (-1 if x > 0 else 1), -7, 12.1, 12.0),
                (135, x, -6.5, 7, 7.8),
            ],
            trousers,
            folds=0.07,
            fold_rate=7,
        )
        loft(
            label + " · gilt outsole",
            [
                (99.15, x, -10.1, 7.7, 12.0),
                (99.45, x, -10.2, 8.0, 12.4),
                (100.9, x, -10.2, 8.2, 12.5),
                (101.25, x, -10.2, 8.05, 12.4),
            ],
            gold,
            2.85,
        )
        boot_profile = np.array(
            [
                (100.85, -10.2, 8.02, 12.3),
                (102.2, -10.0, 8.08, 12.25),
                (103.8, -9.7, 7.85, 11.8),
                (105.8, -8.65, 7.15, 10.3),
                (107.5, -7.45, 6.36, 8.2),
                (110.3, -6.75, 6.55, 7.35),
                (114.7, -6.70, 6.9, 7.55),
            ]
        )
        heights = np.linspace(boot_profile[0, 0], boot_profile[-1, 0], 70)
        yc, rx, ry = PchipInterpolator(boot_profile[:, 0], boot_profile[:, 1:], axis=0)(
            heights
        ).T
        angles = np.linspace(0, np.pi * 2, 112, endpoint=False)
        sign = -1 if label.startswith("Staff") else 1

        a, z = np.meshgrid(angles, heights)
        vamp_top, band_distance = boot_relief_coordinates(z, a, sign)
        offset = 0.17 * np.exp(-(((z - vamp_top) / 0.38) ** 2)) + 0.12 * np.exp(
            -((band_distance / 0.9) ** 4)
        )
        sx, sy = np.sin(a), -np.cos(a)
        power = 2.62 - 0.55 * np.clip((z - 104) / 6, 0, 1)
        grid = np.stack(
            (
                x + (rx[:, None] + offset) * np.sign(sx) * abs(sx) ** (2 / power),
                yc[:, None]
                + (ry[:, None] + offset) * np.sign(sy) * abs(sy) ** (2 / power),
                z,
            ),
            -1,
        )
        rings(label + " · leather boot and bound instep", grid, 26)
        loft(
            label + " · brass boot cuff",
            [
                (112.25, x, -6.65, 6.9, 7.4),
                (112.55, x, -6.65, 7.2, 7.8),
                (115.05, x, -6.7, 7.45, 8.05),
                (115.3, x, -6.7, 7.22, 7.92),
            ],
            gold,
        )

    v, u = np.mgrid[0:1:23j, -1:1:35j]
    apron_width = 9.7 - 3.0 * v + 1.15 * np.sin(v * np.pi)
    edge_height = 3.35 * (1 - np.sqrt(np.maximum(0, 1 - u * u)))
    height = 121.35 + 16.4 * v + (1 - v) * edge_height
    depth = (
        -34.1 + 5.6 * v + 2.45 * u * u - 1.65 * np.sin(v * np.pi) * (1 - 0.6 * u * u)
    )
    apron = np.stack((-6.8 + u * apron_width, depth, height), -1)
    outward = np.stack((u * 0.20, -np.ones_like(u), 0.24 - 0.12 * v), -1)
    outward /= np.linalg.norm(outward, axis=-1, keepdims=True)
    patch(
        "Pendant fan beneath the guardian clasp",
        apron,
        outward,
        weave,
        gold,
        1.15,
        (1, 1),
        (0.073, 0.083),
    )
    for i, a in enumerate((-0.91, 0.91, -1.91, 1.91, np.pi)):
        flank = i < 2
        armour_panel(
            "Flared lamellar skirt · lappet " + str(i + 1),
            a,
            0.40 if flank else 0.45,
            124.6 if flank else 127.8,
            139,
            32 if flank else 30,
            21.5,
            25.9 if flank else 23.5,
            18.6,
            1.7 if flank else 1.5,
            (1.7, 1.0),
        )
    armour_panel(
        "Gilt breastplate with central spine",
        0,
        1.11,
        145.5,
        160.1,
        23.7,
        25.5,
        23.9,
        21.8,
        3.1,
        (3.4, 1.5),
        True,
    )
    loft(
        "Wide cobalt silk girdle",
        [
            (135.5, -5.7, -9, 22.5, 20.1),
            (135.9, -5.7, -9, 23.3, 21),
            (139.8, -5.7, -9, 23.1, 20.9),
            (143, -5.7, -9, 23.9, 21.3),
            (145.8, -5.8, -9, 24.6, 21.9),
            (146.1, -5.8, -9, 24.2, 21.5),
        ],
        cobalt,
    )
    loft(
        "Vermilion band around the girdle",
        [
            (139.3, -5.7, -9, 23.5, 21.3),
            (139.6, -5.7, -9, 23.6, 21.4),
            (141.25, -5.7, -9, 23.85, 21.5),
            (141.5, -5.7, -9, 23.55, 21.2),
        ],
        red,
    )
    sleeve(
        "Staff arm",
        [
            (-22, -8, 158),
            (-31, -9, 157),
            (-39, -11.5, 151.6),
            (-44.5, -16, 152.2),
            (-49.5, -20.4, 155.3),
        ],
        [7, 9.2, 7.3, 6, 5.5],
        [7.6, 8.3, 7.6, 6.6, 5.7],
    )
    sleeve(
        "Arm akimbo",
        [
            (12, -8, 158.5),
            (21, -9, 157.3),
            (25.3, -12.4, 152.6),
            (23, -18.8, 148.4),
            (18.5, -24, 144.8),
        ],
        [7, 9.2, 7.3, 6.1, 5.4],
        [7.6, 8.3, 7.6, 6.6, 5.7],
    )

    def shoulder(label, sign):
        v, u = np.mgrid[0:1:24j, -1:1:43j]
        a = u * 1.56
        radius = 4.15 + 11.5 * v
        x = -6 + sign * (22.4 + radius * np.cos(a) * 1.04)
        y = -10.15 + radius * 1.10 * np.sin(a)
        z = 165.6 - 7.7 * v**1.45 + 1.25 * np.sin(v * np.pi)
        z -= np.sin(a) ** 2 * (1.7 + 4.8 * v) * (1.0 - 0.46 * np.sin(a))
        grid = np.stack((x, y, z), -1)
        n = np.stack(
            (sign * np.cos(a) * v * 0.7, np.sin(a) * v * 0.65, np.ones_like(v)), -1
        )
        n /= np.linalg.norm(n, axis=-1)[..., None]
        if sign > 0:
            grid, n = grid[:, ::-1], n[:, ::-1]
        patch(
            label + " · domed woven pauldron",
            grid,
            n,
            weave,
            gold,
            1.65,
            (2.45, 0.95),
            (0.055, 0.13),
        )

    shoulder("Staff side", -1)
    shoulder("Cape side", 1)
    for name, pts in [
        ("Staff wrist", [(-47, -18.3, 154), (-49.7, -20, 155), (-52, -21, 155.8)]),
        (
            "Akimbo wrist",
            [(20.4, -21.5, 146.6), (18.7, -24.3, 144.8), (17.1, -26.1, 143.7)],
        ),
    ]:
        sweep(
            name + " · gold edged enamel cuff",
            pts,
            [5.9, 5.85, 5.55],
            [6.05, 6.0, 5.65],
            cobalt,
            (0, 0, 1),
            28,
            finish_at=lambda t, a: gold if t < 0.12 or t > 0.80 else cobalt,
        )
    sweep(
        "Palm gripping the staff",
        [(-50.7, -20.5, 155.7), (-53.8, -21, 156), (-56.5, -21.6, 156.3)],
        [3.6, 4.8, 4.1],
        [3.7, 4.1, 3.0],
        gold,
        (0, 0, 1),
        24,
    )
    for j, z in enumerate((152.2, 154.5, 156.8, 159.05)):
        x = -45.9 - (z - 100) * 0.159
        sweep(
            "Staff grip · jointed finger " + str(j + 1),
            [
                (x + 2.7, -21.5, z + 0.45),
                (x + 1.25, -24.7, z + 0.6),
                (x - 0.75, -25.65, z + 0.35),
                (x - 2.45, -24.85, z),
                (x - 2.7, -23.35, z - 0.38),
            ],
            [1.4, 1.45, 1.28, 1.15, 0.72],
            [1.37, 1.45, 1.33, 1.16, 0.75],
            gold,
            (0, 0, 1),
        )
    sweep(
        "Opposed thumb on staff",
        [
            (-51.7, -21.3, 158.2),
            (-53.1, -23.1, 160),
            (-55.8, -24, 159.8),
            (-56.6, -24.4, 158.4),
        ],
        [2.0, 1.85, 1.48, 0.95],
        [1.85, 1.65, 1.4, 0.85],
        gold,
        (0, 0, 1),
    )
    sweep(
        "Palm resting against sash",
        [(17.7, -25.3, 144.1), (16.2, -28.4, 142.8), (14.1, -30.2, 140.5)],
        [3.6, 4.7, 3.6],
        [3.4, 4.4, 3.4],
        gold,
        (0, 0, 1),
        24,
    )
    for j, z in enumerate((138.0, 140.1, 142.25, 144.4)):
        dx = (1.8, 0.3, -0.45, 1.1)[j]
        sweep(
            "Sash hand · curled finger " + str(j + 1),
            [
                (16, -28, z + 0.5),
                (14.7, -30.3, z + 0.55),
                (12 + dx * 0.45, -31.75, z + 0.15),
                (9.0 + dx, -32.4, z - 0.28),
            ],
            [1.2, 1.35, 1.14, 0.79],
            [1.26, 1.34, 1.19, 0.71],
            gold,
            (0, 0, 1),
        )
    sweep(
        "Thumb tucked at waist",
        [
            (18, -27.2, 144.1),
            (16.7, -28.3, 146.0),
            (14.4, -30.0, 145.8),
            (13.2, -30.8, 145.3),
        ],
        [1.7, 1.6, 1.35, 0.85],
        [1.6, 1.6, 1.26, 0.75],
        gold,
        (0, 0, 1),
    )

    def ribbon(name, path, widths, finish, lift=1.1):
        path = np.asarray(path, float)
        t, u = np.mgrid[0:1:41j, -1:1:15j]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        arc /= arc[-1]
        center = PchipInterpolator(arc, path, axis=0)(t)
        tangent = np.gradient(center, axis=0)
        across = np.stack((tangent[..., 2], np.zeros_like(t), -tangent[..., 0]), -1)
        across /= np.maximum(np.linalg.norm(across, axis=-1)[..., None], 1e-8)
        width = PchipInterpolator(arc, widths)(t)
        center += across * (width * u)[..., None]
        center[..., 1] -= (
            0.6 * (1 - u**2) + lift * np.exp(-(((u - 0.23) / 0.27) ** 2))
        ) * np.sin(0.18 + t * 2.7)
        normal = np.zeros_like(center)
        normal[..., 1] = -1
        patch(name, center, normal, finish, finish, 0.72, (1, 1), (0, 0))

    for sign in (-1, 1):
        x = lambda s: -6.8 + sign * s
        ribbon(
            "Ribbon at throat " + str(sign),
            [
                (x(0.4), -26.4, 166.4),
                (x(3), -30.9, 163.4),
                (x(6.3), -32.9, 160.8),
                (x(9.6), -32.5, 160.3),
            ],
            [1.2, 2.05, 2.24, 0.55],
            red,
            0.7,
        )
        ribbon(
            "Sculpted waist bow " + str(sign),
            [
                (x(2), -33, 140.3),
                (x(5.4), -33.9, 141.1),
                (x(8.2), -34, 141.5),
                (x(9.4), -33.4, 142.1),
            ],
            [1.4, 2.7, 3.45, 0.6],
            red,
        )
        ribbon(
            "Trailing waist ribbon " + str(sign),
            [
                (x(3.4), -33, 139.9),
                (x(5.3), -34, 136.4),
                (x(7.8), -34.8, 130.9),
                (x(13.3), -34.5, 127.7),
                (x(18.6), -31.4, 126.7),
                (x(24.3), -30.2, 128.7 if sign < 0 else 126.6),
                (x(28.7 if sign < 0 else 31.2), -26.2, 130.4 if sign < 0 else 125.8),
            ],
            [1.25, 2.18, 2.42, 2.55, 2.58, 2.02, 0.48],
            red,
            1.05,
        )
    for name, z, rx, depth, dz in [
        ("Guardian buckle", 140.1, 5.7, 2.1, 5.5),
        ("Muzzle of guardian", 139.3, 3.1, 1.2, 1.7),
        ("Beard of guardian", 135.8, 2.45, 1.3, 2.55),
    ]:
        yc = -34.8 if name != "Muzzle of guardian" else -36.65
        loft(
            name,
            [
                (z - dz, -6.8, yc, 0.55, 0.52),
                (z - dz * 0.64, -6.8, yc, rx * 0.80, depth * 0.82),
                (z, -6.8, yc, rx, depth),
                (z + dz * 0.65, -6.8, yc, rx * 0.82, depth * 0.83),
                (z + dz, -6.8, yc, rx * 0.45, depth * 0.49),
            ],
            darkgold,
            2.2,
        )
    for sign in (-1, 1):
        x = lambda n: -6.8 + sign * n
        for label, path, sizes in [
            (
                "Brow",
                [
                    (x(0.8), -36.7, 140.7),
                    (x(2.2), -36.9, 141.6),
                    (x(4.1), -36.4, 142.3),
                ],
                [0.44, 0.65, 0.28],
            ),
            (
                "Horn",
                [
                    (x(3.7), -34.6, 142.5),
                    (x(4.7), -34.6, 144.1),
                    (x(5.2), -34.1, 145.6),
                ],
                [1.38, 0.95, 0.15],
            ),
            (
                "Fang",
                [
                    (x(1.85), -36.4, 138.0),
                    (x(1.75), -36.4, 136.9),
                    (x(1.5), -36.1, 136.3),
                ],
                [0.63, 0.40, 0.1],
            ),
        ]:
            sweep(
                label + " on guardian clasp " + str(sign),
                path,
                sizes,
                sizes,
                gold,
                (0, 1, 0),
                12,
            )

    def staff_at(z):
        return np.array([-45.9 - (z - 100) * 0.159, -23 + (z - 100) * 0.004, z])

    levels = [98.9, 99.15, 115.9, 116.3, 201.8, 202.2, 226.0, 226.5]
    radii = [2.25, 2.40, 2.38, 1.72, 1.72, 2.38, 2.38, 2.23]
    sweep(
        "Gold staff · shaft with two chased end sleeves",
        [staff_at(z) for z in levels],
        radii,
        radii,
        gold,
        (0, 1, 0),
        28,
    )
    for low, high in [(99.1, 116.2), (202, 226.3)]:
        for h in (low + 0.55, high - 0.65):
            sweep(
                "Ferrule rim " + str(h),
                [staff_at(h - 0.48), staff_at(h), staff_at(h + 0.48)],
                [2.4, 2.64, 2.40],
                [2.4, 2.64, 2.40],
                gold,
                (0, 1, 0),
                28,
            )
        for i in range(int((high - low - 2) / 4.1)):
            for k in range(3):
                t = np.linspace(0, 1, 18)
                a = (
                    k * np.pi * 2 / 3
                    + i * 0.66
                    + 0.7 * (1 - 0.72 * t) * np.cos(t * np.pi * 2.0)
                )
                z = (
                    low
                    + 2.9
                    + i * 4.1
                    + 1.55 * (1 - 0.72 * t) * np.sin(t * np.pi * 2.0)
                )
                path = np.array([staff_at(h) for h in z])
                path[:, 0] += 2.38 * np.sin(a)
                path[:, 1] -= 2.38 * np.cos(a)
                rad = 0.16 + 0.11 * np.sin(np.pi * t)
                sweep(
                    "Cloud scroll " + str((low, i, k)),
                    path,
                    rad,
                    rad,
                    darkgold,
                    (0, 0, 1),
                    7,
                    1,
                )

    def plume_point(sign, t):
        knots = np.array(
            [
                [-6 + sign * 4, -1, 224],
                [-6 + sign * 7.4, 2.7, 236],
                [-6 + sign * 11.3, 9.5, 246],
                [-6 + sign * 15.0, 19, 255.5],
                [-6 + sign * 18, 31, 262.1],
                [-6 + sign * 19.6, 42, 263.4],
                [-6 + sign * 20, 50.5, 260.3],
                [-6 + sign * 19.6, 54.8, 251.2],
            ]
        )
        return PchipInterpolator(np.linspace(0, 1, len(knots)), knots, axis=0)(t)

    for sign in (-1, 1):
        values = np.linspace(0, 1, 361)
        path = plume_point(sign, values)
        width = PchipInterpolator(
            [0, 0.15, 0.27, 0.42, 0.66, 0.85, 1],
            [2.0, 2.65, 3.35, 3.65, 3.20, 2.30, 0.18],
        )(values)
        depth = np.maximum(0.15, width * 0.55)
        tangent = np.gradient(path, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
        along_width = np.cross(tangent, [1, 0, 0])
        along_width /= np.linalg.norm(along_width, axis=1, keepdims=True)
        along_depth = np.cross(tangent, along_width)
        arc = np.linspace(0, 2 * np.pi, 44, endpoint=False)[None, :]
        vane = values[:, None] * 45 - 0.75 * abs(np.cos(arc))
        engraving = (0.5 + 0.5 * np.cos(2 * np.pi * vane)) ** 5
        exposed = np.clip((values - 0.19) / 0.07, 0, 1)[:, None]
        thickness = depth[:, None] * (1 - exposed * 0.22 * engraving)
        shaft = 0.20 * np.exp(-((np.cos(arc) / 0.19) ** 2))
        grid = (
            path[:, None]
            + along_width[:, None] * (width[:, None] * np.cos(arc))[..., None]
        )
        grid += along_depth[:, None] * ((thickness + shaft) * np.sin(arc))[..., None]
        rings(
            "Incised golden crown feather " + str(sign),
            grid,
            21,
            per_ring=lambda t, a: (
                10
                if t > 0.22
                and (
                    0.5
                    + 0.5
                    * np.cos(2 * np.pi * (t * 45 - 0.75 * abs(np.cos(a * 2 * np.pi))))
                )
                ** 6
                > 0.68
                else 21
            ),
        )
        pts = [
            plume_point(sign, t)
            for t in [0.005, 0.055, 0.100, 0.125, 0.148, 0.175, 0.198, 0.22]
        ]
        radii = [2.85, 3.10, 3.0, 3.3, 3.28, 3.05, 3.8, 3.6]
        sweep(
            "Gold collared cobalt plume ferrule " + str(sign),
            pts,
            radii,
            radii,
            cobalt,
            (1, 0, 0),
            28,
            6,
            lambda t, a: (
                gold
                if (0.32 < t < 0.42 or 0.69 < t < 0.79)
                else (13 if t > 0.79 else cobalt)
            ),
        )
    return parts


def save_finish(out, name, color, height, strength):
    dx = np.gradient(height, axis=1)
    dy = np.gradient(height, axis=0)
    normal = np.stack((-dx * strength, dy * strength, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    Image.fromarray(np.uint8(np.clip(color, 0, 255))).save(
        out / (name + "-paint.jpg"), quality=97, subsampling=0
    )
    Image.fromarray(np.uint8(127.5 + 127.5 * normal)).save(
        out / (name + "-detail.jpg"), quality=96
    )


def boot_relief_coordinates(z, angle, sign):
    facing = np.cos(angle)
    off_axis = np.angle(np.exp(1j * (angle - sign * 0.23)))
    vamp_top = 102.0 + 1.8 * np.maximum(0, facing) ** 2
    vamp_top += 9.20 * np.exp(
        -np.square(off_axis / (0.27 + 0.16 * np.clip((113.5 - z) / 9.5, 0, 1)))
    )
    bands = np.array([106.0, 108.9, 111.75])[:, None, None]
    margin = np.min(
        abs(
            z[None, ...]
            - bands
            - sign * 0.90 * np.sin(angle)[None, ...]
            - 0.42 * np.sin(2 * angle) * sign
        ),
        axis=0,
    )
    return vamp_top, margin


def write_boot_finish(out):
    rows, cols = np.mgrid[:384, :768]
    height = 114.7 - (114.7 - 100.85) * (rows + 0.5) / 384
    angle = (cols + 0.5) * 2 * np.pi / 768
    vamp, band = boot_relief_coordinates(height, angle, 1)
    leather = np.clip((vamp - height) / 0.13 + 0.5, 0, 1)[..., None]
    indigo = np.clip((0.83 - band) / 0.11 + 0.5, 0, 1)[..., None]
    underlay = (
        np.array([151, 61, 25])
        + (np.sin(angle * 3) + np.cos(height * 0.6))[..., None] * 1.5
    )
    wraps = underlay * (1 - indigo) + np.array([28, 37, 53]) * indigo
    color = wraps * (1 - leather) + np.array([105, 39, 27]) * leather
    bevel = 0.17 * np.exp(-(((height - vamp) / 0.20) ** 2)) + 0.18 * np.exp(
        -(((band - 0.8) / 0.20) ** 2)
    )
    save_finish(out, "boot-hide", color, bevel, 2.6)


def write_tooling(out, photos):
    source = np.asarray(Image.open(photos / "胸甲与束带.jpg").convert("RGB"))
    tile = source[224:313, 231:307].astype(float)
    tile = np.concatenate([tile, tile[:, ::-1]], axis=1)
    tile = np.concatenate([tile, tile[::-1]], axis=0)
    light = cv2.cvtColor(tile.astype("B"), cv2.COLOR_RGB2GRAY).astype(float)
    light = light - cv2.GaussianBlur(light, (0, 0), 27) + 148
    height = np.clip((light - 102) / 103, -0.60, 1.35)
    color = np.array([149, 115, 61]) + height[..., None] * [62, 58, 47]
    save_finish(out, "tooling", color, height, 2.0)

    closeup = np.array(Image.open(photos / "面部和握棒.jpg").convert("RGB"))
    v, u = (np.mgrid[:384, :256].astype("f") + 0.5) / np.array([384, 256])[
        :, None, None
    ]
    row = np.float32(119 + 190 * v)
    col = np.float32(194 + 0.165 * (row - 119) + 13.0 * np.sin(u * 2 * np.pi))
    band = cv2.remap(closeup, col, row, cv2.INTER_CUBIC)
    light = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY).astype(float)
    relief = (light - cv2.GaussianBlur(light, (0, 0), 11)) / 100
    save_finish(
        out,
        "ferrule",
        np.array([165, 131, 77]) + relief[..., None] * [87, 78, 61],
        relief,
        3.0,
    )

    hsv = cv2.cvtColor(source, cv2.COLOR_RGB2HSV)
    gold_mask = (hsv[..., 0] > 6) & (hsv[..., 0] < 43) & (hsv[..., 1] > 27)
    nearest = ndimage.distance_transform_edt(
        ~gold_mask, return_distances=False, return_indices=True
    )
    gold_img = source[tuple(nearest)].astype(float)
    grey = cv2.cvtColor(gold_img.astype("B"), cv2.COLOR_RGB2GRAY).astype(float)
    neutral = grey - cv2.GaussianBlur(grey, (0, 0), 22) * 0.55 - 60
    save_finish(
        out,
        "repousse",
        np.array([164, 131, 78]) + neutral[..., None] * [0.86, 0.81, 0.71],
        neutral / 125,
        2.4,
    )
    badge = source[326:478, 297:448].copy()
    h, sat, value = cv2.split(cv2.cvtColor(badge, cv2.COLOR_RGB2HSV))
    gold = (h > 5) & (h < 35) & (value > 28)
    y, x = np.indices(gold.shape)
    mask = gold & ((x - 76) ** 2 / 74**2 + (y - 69) ** 2 / 99**2 < 1)
    where = ndimage.distance_transform_edt(
        ~mask, return_distances=False, return_indices=True
    )
    extended = badge[tuple(where)].astype(float)
    grey = cv2.cvtColor(extended.astype("B"), cv2.COLOR_RGB2GRAY).astype(float)
    color = np.array([145, 108, 61]) + (extended - [154, 123, 76]) * 0.68
    save_finish(out, "guardian", color, grey / 255, 3.2)


def register_depth(pieces):
    def selected(name, group):
        if group == "rock":
            return name.startswith("01")
        if group == "head":
            return name[:2] in ("03", "09", "10")
        if group == "boots":
            return "·" in name and any(
                k in name
                for k in (
                    "breeches",
                    "outsole",
                    "quarter",
                    "shin wrap",
                    "boot binding",
                    "boot cuff",
                    "bound instep",
                )
            )
        if group == "cape":
            return name.startswith("05")
        excluded = (
            "01",
            "03",
            "04",
            "05",
            "09",
            "10",
            "Incised",
            "Plume",
            "Gold collared",
            "Gold staff",
            "Ferrule",
            "Cloud scroll",
            "Staff grip",
            "Opposed thumb",
            "Palm gripping",
            "Staff wrist",
        )
        return not name.startswith(excluded) and not selected(name, "boots")

    controls = {
        "rock": [
            (3, 131, 380),
            (8, 132, 379),
            (30, 137, 372),
            (60, 153, 361),
            (80, 170, 350),
            (90, 184, 344),
            (95, 188, 335),
        ],
        "head": [
            (168, 213, 331),
            (173, 205, 336),
            (177, 203, 346),
            (181, 203, 349),
            (185, 197, 350),
            (190, 207, 349),
            (195, 204, 349),
            (199, 200, 350),
            (205, 205, 338),
            (210, 229, 318),
            (214, 247, 307),
        ],
        "boots": [
            (101, 231, 313),
            (105, 237, 312),
            (110, 246, 309),
            (116, 247, 308),
            (121, 242, 310),
            (126, 237, 311),
            (131, 239, 306),
        ],
        "body": [
            (119, 227, 312),
            (125, 214, 316),
            (130, 207, 319),
            (137, 203, 322),
            (144, 204, 325),
            (150, 210, 321),
            (157, 209, 322),
            (162, 212, 320),
            (166, 218, 321),
            (168, 222, 320),
        ],
        "cape": [
            (115, 345, 368),
            (120, 340, 373),
            (125, 310, 378),
            (130, 311, 379),
            (137, 309, 388),
            (144, 310, 398),
            (150, 308, 401),
            (157, 310, 383),
            (162, 310, 370),
            (165, 277, 354),
            (168, 220, 339),
        ],
    }
    for group, data in controls.items():
        matching = [(name, v) for name, v, *_ in pieces if selected(name, group)]
        envelope = np.concatenate([v for name, v in matching])
        target = np.array(data, dtype=float)
        heights = target[:, 0]
        sides = []
        for z in heights:
            band = envelope[abs(envelope[:, 2] - z) < 0.88, 1]
            if not len(band):
                band = envelope[np.argsort(abs(envelope[:, 2] - z))[:16], 1]
            sides.append((band.min(), band.max()))
        near, far = np.array(sides).T
        near_delta = (target[:, 1] - 307.5) / 3.20909 - near
        far_delta = (target[:, 2] - 307.5) / 3.20909 - far
        for name, v in matching:
            z = v[:, 2]
            near_y, far_y = np.interp(z, heights, near), np.interp(z, heights, far)
            weight = np.clip((v[:, 1] - near_y) / np.maximum(far_y - near_y, 1), 0, 1)
            if group == "cape":
                curve = PchipInterpolator(heights, far_delta)(
                    np.clip(z, heights[0], heights[-1])
                )
                delta = (
                    curve
                    * np.clip((weight - 0.27) / 0.73, 0, 1)
                    * np.clip((168.6 - z) / 4.2, 0, 1)
                )
            else:
                delta = (
                    np.interp(z, heights, near_delta) * (1 - weight)
                    + np.interp(z, heights, far_delta) * weight
                )
            if name.startswith("Staff arm"):
                delta *= np.clip((v[:, 0] + 53) / 19, 0, 1)
            if group == "head":
                delta *= np.clip((220 - z) / 5, 0, 1) * np.clip((z - 164) / 4, 0, 1)
            if group == "rock":
                delta *= np.clip((100 - z) / 5, 0, 1)
            v[:, 1] += delta

    pauldron = next(v for name, v, *_ in pieces if name.startswith("Cape side · domed"))
    pauldron[:, 1] -= 0.65 * np.maximum(0, pauldron[:, 1] + 2)


def register_stance(pieces):
    heights = np.array(
        [100, 103, 105, 108, 110, 112, 114, 116, 118, 121, 125, 130, 135]
    )
    photo = {
        "Staff side": [
            (196, 245),
            (197, 244),
            (198, 246),
            (203, 247),
            (207, 247),
            (208, 248),
            (211, 251),
            (209, 253),
            (206, 261),
            (200, 266),
            (197, 269),
            (202, 269),
            (214, 268),
        ],
        "Cape side": [
            (290, 336),
            (289, 333),
            (290, 332),
            (287, 330),
            (286, 327),
            (284, 328),
            (282, 324),
            (277, 327),
            (272, 330),
            (267, 335),
            (267, 337),
            (267, 331),
            (266, 322),
        ],
    }
    for side, section in photo.items():
        matching = [
            v
            for name, v, *_ in pieces
            if name.startswith(side + " · ") and "pauldron" not in name
        ]
        sign = -1 if side == "Staff side" else 1
        cx = np.median([np.mean(v[:, 0]) for v in matching])
        for v in matching:
            z = v[:, 2]
            weight = np.clip((122.5 - z) / 13, 0, 1)
            angle = sign * np.deg2rad(10.5) * weight
            dx, dy = v[:, 0] - cx, v[:, 1] + 8.6
            v[:, 0] = cx + dx * np.cos(angle) - dy * np.sin(angle)
            v[:, 1] = -8.6 + dx * np.sin(angle) + dy * np.cos(angle)
            v[:, 2] += (
                sign
                * 0.12
                * dx
                * np.clip((z - 103) / 7, 0, 1)
                * np.clip((129 - z) / 8, 0, 1)
            )
        envelope = np.concatenate(matching)
        authored = []
        for height in heights:
            near = envelope[abs(envelope[:, 2] - height) < 0.70, 0]
            if not len(near):
                near = envelope[np.argsort(abs(envelope[:, 2] - height))[:12], 0]
            authored.append([near.min(), near.max()])
        old = np.array(authored)
        target = (np.array(section) - 289) / 3.16
        for v in matching:
            z = v[:, 2].clip(heights[0], heights[-1])
            center = PchipInterpolator(heights, old.mean(axis=1))(z)
            new_center = PchipInterpolator(heights, target.mean(axis=1))(z)
            scale = PchipInterpolator(
                heights,
                (target[:, 1] - target[:, 0]) / np.maximum(old[:, 1] - old[:, 0], 1),
            )(z)
            v[:, 0] = new_center + (v[:, 0] - center) * scale


def prepare(out, parts, profiles, wrap, photos):
    write_tooling(out, photos)
    write_boot_finish(out)
    pieces = []
    for name, v, f in parts:
        key = name[:2]
        points = v[f]
        normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
        mat = np.full(len(f), 4, dtype="B")
        uv = np.zeros((len(f), 3, 2), dtype="f")
        if key in profiles:
            profile, za, zb, finish = profiles[key]
            uv = wrap(points, profile, za, zb).astype("f")
            mat[:] = finish
            if key == "01":
                mat[np.abs(normals[:, 2]) > 0.91] = 6
            if key == "03":
                vertex_normal = np.zeros_like(v)
                for i in range(3):
                    np.add.at(vertex_normal, f[:, i], normals)
                vertex_normal /= np.maximum(
                    np.linalg.norm(vertex_normal, axis=1, keepdims=True), 1e-9
                )
                coord = wrap(v[:, None, :], profile, za, zb)[:, 0]
                grey = np.asarray(
                    Image.open(out / "head-paint.jpg").convert("L")
                ).astype("f")
                weight = (
                    np.asarray(Image.open(out / "head-metal-rough.png"))[:, :, 2] / 255
                )
                relief = (grey - cv2.GaussianBlur(grey, (0, 0), 7.5)) / 46
                row = (1 - coord[:, 1]) * (grey.shape[0] - 1)
                col = (coord[:, 0] % 1) * (grey.shape[1] - 1)
                displacement = ndimage.map_coordinates(
                    np.clip(relief, -1, 1) * np.clip((weight - 0.10) * 2, 0, 1),
                    [row, col],
                    order=1,
                    mode="nearest",
                )
                v = v + 0.29 * vertex_normal * displacement[:, None]
        elif key in ("09", "10"):
            sign = -1 if key == "09" else 1
            local_x = 0.48 * sign * (points[..., 0] - (-6.5 + sign * 23.4)) + 0.877 * (
                points[..., 1] + 7
            )
            uv[..., 0] = (584 + 277 + local_x * 2.85) / 1136
            uv[..., 1] = 1 - (913 + 317 - (points[..., 2] - 189.3) * 3.05) / 1861
            mat[:] = 3
        pieces.append((name, v, f, mat, uv))
    pieces.extend(casting())
    for name, v, f, m, uv in pieces:
        if name.startswith("Gilt breastplate"):
            points = v[f]
            selected = m == 18
            uv[..., 0] = np.clip(370 + (points[..., 0] + 6) * 7.28, 202, 542) / 790
            uv[..., 1] = (
                1 - np.clip(336 - (points[..., 2] - 145.0) * 9.2, 188, 343) / 954
            )
            m[selected] = 23
        if "domed woven pauldron" in name:
            selected = m == 18
            x = uv[..., 0] / 2.45
            y = uv[..., 1] / 0.95
            uv[..., 0] = (615 + 122 * x) / 790
            uv[..., 1] = 1 - (170 + 62 * y) / 954
            m[selected] = 23
        if name.startswith("Pendant fan"):
            selected = m == 18
            x, y = uv[..., 0].copy(), uv[..., 1].copy()
            uv[..., 0] = (306 + 123 * x) / 790
            uv[..., 1] = 1 - (582 - 144 * y) / 954
            m[selected] = 23
        if name.startswith("Flared lamellar"):
            selected = m == 18
            x = uv[..., 0] / 1.7
            y = uv[..., 1]
            uv[..., 0] = (313 + 116 * x) / 790
            uv[..., 1] = 1 - (536 - 75 * y) / 954
            m[selected] = 23
        if name.startswith("Staff side · leather boot and bound instep"):
            uv[..., 0] = 1 - uv[..., 0]
        if name.startswith("Gold staff"):
            points = v[f]
            h = points[..., 2]
            axis_x = -45.9 - (h - 100) * 0.159
            axis_y = -23 + (h - 100) * 0.004
            band = (h.mean(axis=1) < 116.2) | (h.mean(axis=1) > 202)
            uv[..., 0] = np.arctan2(
                points[..., 1] - axis_y, points[..., 0] - axis_x
            ) / (2 * np.pi)
            uv[..., 1] = np.clip(
                np.where(h < 160, (h - 99.1) / 17.1, (h - 202) / 24.3), 0, 1
            )
            m[band] = 22
        if name in ("Guardian buckle", "Muzzle of guardian", "Beard of guardian"):
            points = v[f]
            uv[..., 0] = np.clip((points[..., 0] + 6.8) / 11.7 + 0.5, 0.002, 0.998)
            uv[..., 1] = np.clip((points[..., 2] - 133.4) / 12.1, 0.002, 0.998)
            m[:] = 20
    verts = np.concatenate([p[1] for p in pieces])
    low, high = verts.min(axis=0), verts.max(axis=0)
    scale = np.array([145, 110, 265]) / (high - low)
    center = (low + high) / 2
    center[2] = low[2]
    pieces = [(name, (v - center) * scale, f, m, uv) for name, v, f, m, uv in pieces]
    register_depth(pieces)
    register_stance(pieces)
    result = {"names": np.array([p[0] for p in pieces])}
    for i, (name, v, f, m, uv) in enumerate(pieces):
        result[f"v{i}"] = np.float32(v * 0.001)
        result[f"f{i}"] = f.astype(np.uint32)
        result[f"uv{i}"] = uv.astype(np.float32)
        result[f"material{i}"] = m.astype(np.uint8)
    np.savez_compressed(out / "parts.npz", **result)
    print("Casting components", len(pieces), "size", np.round((high - low) * scale, 2))
