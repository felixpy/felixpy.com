import argparse
import runpy
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.interpolate import PchipInterpolator
from skimage.measure import marching_cubes

root = Path(__file__).resolve().parents[2]
item = root / ".references/05-摄影与陈列/手办与收藏模型/Great Sage"
ref = item / "参考图/用户参考图/铜师傅-悟空之战无不胜/03-四面实拍.png"
parser = argparse.ArgumentParser()
parser.add_argument("out", type=Path)
args = parser.parse_args()
out = args.out
out.mkdir(parents=True, exist_ok=True)
sheet = np.asarray(Image.open(ref).convert("RGB"))
regions = [
    (0, 0, 584, 905),
    (584, 0, 1136, 905),
    (0, 913, 584, 1861),
    (584, 913, 1136, 1861),
]
origins = [
    (289, 868, 3.16, 3.16),
    (272, 867, -3.16, 3.16),
    (234, 920, -3.18, 3.24),
    (296, 920, 3.18, 3.24),
]
figures = []
maps = []
views = []
for i, (x0, y0, x1, y1) in enumerate(regions):
    img = sheet[y0:y1, x0:x1].copy()
    views.append(img)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    seed = (hsv[:, :, 1].astype(float) > 32) & (
        (hsv[:, :, 0] < 110) | (hsv[:, :, 0] > 150)
    )
    seed[:7] = False
    seed[origins[i][1] + 5 :] = False
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    dense = cv2.morphologyEx(seed.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    dist = ndimage.distance_transform_edt(~dense.astype(bool))
    inner = ndimage.distance_transform_edt(dense)
    mask = np.full(seed.shape, cv2.GC_PR_BGD, np.uint8)
    mask[(dist < 3)] = cv2.GC_PR_FGD
    mask[inner > 5] = cv2.GC_FGD
    mask[dist > 12] = cv2.GC_BGD
    mask[origins[i][1] + 6 :] = cv2.GC_BGD
    cv2.setRNGSeed(265)
    cv2.grabCut(
        img, mask, None, np.zeros((1, 65)), np.zeros((1, 65)), 3, cv2.GC_INIT_WITH_MASK
    )
    silhouette = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    labels, count = ndimage.label(silhouette)
    counts = np.bincount(labels.ravel())
    silhouette &= counts[labels] > 33
    nearest = ndimage.distance_transform_edt(
        ~silhouette, return_distances=False, return_indices=True
    )
    extended = img[tuple(nearest)]
    maps.append(extended)
    figures.append(silhouette)
    Image.fromarray(np.where(silhouette[:, :, None], img, 210).astype(np.uint8)).save(
        out / f"mask-{i}.jpg"
    )

texture = np.zeros_like(sheet)
normal = np.tile([128, 128, 255], (*sheet.shape[:2], 1)).astype(np.uint8)
for i, (x0, y0, x1, y1) in enumerate(regions):
    texture[y0:y1, x0:x1] = maps[i]
    grey = cv2.cvtColor(maps[i], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    grey = ndimage.gaussian_filter(grey, 0.85) - ndimage.gaussian_filter(grey, 6)
    gx = ndimage.sobel(grey, 1) * 0.44
    gy = ndimage.sobel(grey, 0) * 0.44
    n = np.stack((-gx, gy, np.ones(gx.shape)), axis=-1)
    normal[y0:y1, x0:x1] = np.uint8(
        127.5 + 127.5 * n / np.linalg.norm(n, axis=-1)[:, :, None]
    )
Image.fromarray(texture).save(
    out / "cast-paint.jpg", quality=93, subsampling=0, optimize=True
)
Image.fromarray(normal).save(
    out / "cast-detail.jpg", quality=92, subsampling=0, optimize=True
)


def sample(view, z, restriction=None):
    origin, zero, kx, kz = origins[view]
    j = round(zero - z * kz)
    coords = np.flatnonzero(figures[view][np.clip(j, 0, figures[view].shape[0] - 1)])
    values = (coords - origin) / kx
    if restriction:
        values = values[(values >= restriction[0]) & (values <= restriction[1])]
    return np.sort(values)


def sides(z, restr=None):
    edges = []
    for i in [2, 3]:
        v = sample(i, z, restr)
        if len(v) > 4:
            edges.append((v[0], v[-1]))
    return np.mean(edges, axis=0) if edges else None


parts = []
step = 0.65
xs = np.arange(-80, 80 + step, step)
ys = np.arange(-65, 65 + step, step)
X, Y = np.meshgrid(xs, ys, indexing="ij")


def add_volume(name, zmin, zmax, distance):
    zs = np.arange(zmin - 2.6, zmax + 2.6, step)
    a = np.full((len(xs), len(ys), len(zs)), -20, np.float32)
    for k, z in enumerate(zs):
        field = distance(np.clip(z, zmin + 0.05, zmax - 0.05))
        if field is not None:
            a[:, :, k] = np.minimum(field, np.minimum(z - zmin, zmax - z))
    a = ndimage.gaussian_filter(a, 0.82 if "cape" in name else 0.54)
    v, f, _, _ = marching_cubes(
        a, 0, spacing=(step, step, step), allow_degenerate=False
    )
    parts.append((name, v + np.array([xs[0], ys[0], zs[0]]), f[:, ::-1]))


def sections(rows):
    rows = np.array(rows, dtype=float)
    return PchipInterpolator(rows[:, 0], rows[:, 1:], axis=0)


def section_field(profile, z, p=2):
    l, r, y0, y1 = profile(z)
    rx = max((r - l) * 0.5, 0.7)
    ry = max((y1 - y0) * 0.5, 0.7)
    return (
        1
        - (abs((X - (l + r) * 0.5) / rx) ** p + abs((Y - (y0 + y1) * 0.5) / ry) ** p)
        ** (1 / p)
    ) * min(rx, ry)


head = sections(
    [
        (165, -14, 0, -23, -2),
        (169, -20, 4, -30, 1),
        (175, -25, 10, -34, 6),
        (182, -28, 14, -36, 10),
        (190, -28, 15, -36, 12),
        (199, -28, 15, -34, 11),
        (205, -26, 13, -32, 8),
        (211, -19, 7, -26, 4),
        (217, -12, 1, -19, -1),
        (220, -9, -3, -16, -4),
    ]
)
chest = sections(
    [
        (120, -24, 16, -31, 8),
        (126, -28, 20, -33, 10),
        (136, -24, 17, -35, 12),
        (143, -24, 17, -36, 12),
        (152, -28, 20, -33, 14),
        (161, -27, 18, -28, 13),
        (168, -19, 9, -23, 7),
        (171, -13, 1, -19, 3),
    ]
)
hat = sections(
    [
        (213, -12, -1, -19, -2),
        (218, -13, 0, -19, 1),
        (223, -17, 3, -16, 4),
        (229, -18, 5, -13, 7),
        (235, -16, 5, -10, 7),
    ]
)


def head_slice(z):
    field = section_field(head, z)
    front = np.clip((-15 - Y) / 14, 0, 1)

    def bump(x, h, w, d):
        return np.exp(-(((X - x) / w) ** 2) - ((z - h) / d) ** 2)

    mask = 2.1 * bump(-7, 181, 9, 5) + 2.9 * bump(-7, 185.1, 2.5, 1.65)
    mask += 0.95 * bump(-7, 189.1, 2.2, 4)
    mouth_z = 180.7 + 0.6 * ((X + 7) / 4.6) ** 2
    mask -= 1.3 * np.exp(-(((X + 7) / 4.5) ** 4) - ((z - mouth_z) / 0.67) ** 2)
    for xc in [-15, 1.3]:
        orbit = np.sqrt(((X - xc) / 4.55) ** 2 + ((z - 189.5) / 3.70) ** 2)
        mask -= 2.55 * np.exp(-(orbit**2) / 1.3)
        mask += 1.25 * np.exp(-(((orbit - 0.98) / 0.23) ** 2))
        mask += 2.05 * np.exp(-(orbit**2) / 0.52)
        mask += 1.05 * bump(xc, 184.6, 4.9, 2.7)
        brow = 195.3 + (np.abs(X + 7) - 8) * 0.32
        mask += 1.25 * np.exp(-(((X - xc) / 6) ** 4) - ((z - brow) / 1.2) ** 2)
    field += mask * front
    return field


def rock_limits(z):
    front = sample(0, z)
    rear = sample(1, z)
    lateral = sides(z)
    l, r = np.mean([(front[0], front[-1]), (rear[0], rear[-1])], axis=0)
    return [z, l, r, lateral[0], lateral[1]]


rock_profile = sections([rock_limits(z) for z in [4, 10, 24, 38, 53, 66, 80, 93, 97]])


def rock_slice(z):
    l, r, y0, y1 = rock_profile(np.clip(z, 4, 97))
    mid = (l + r) / 2
    cy = (y0 + y1) / 2
    rx = (r - l) / 2
    ry = (y1 - y0) / 2
    theta = np.arctan2((Y - cy) / ry, (X - mid) / rx)
    corr = np.zeros_like(theta)
    for angle, slope, width, depth in [
        (-2.20, 0.017, 0.045, 1.65),
        (-1.78, 0.012, 0.042, 2.0),
        (-1.25, -0.012, 0.05, 1.7),
        (-0.68, -0.004, 0.045, 1.6),
        (0.09, 0.002, 0.050, 2.5),
        (0.83, -0.005, 0.052, 1.5),
        (1.24, -0.010, 0.046, 1.3),
        (2.40, 0.007, 0.05, 1.6),
        (2.82, 0.003, 0.045, 1.5),
    ]:
        phase = theta - angle - slope * (z - 48)
        gap = np.arctan2(np.sin(phase), np.cos(phase))
        corr += depth * np.exp(-0.5 * (gap / width) ** 2)
    lobe = np.clip((cy - Y) / ry, 0, 1)
    for top, width, fall in [(94, 42, 0.053), (78, 38, 0.050), (57, 34, 0.044)]:
        xrel = X - (mid + 1.5 + (94 - top) * 0.05)
        groove = z - (top - (np.abs(xrel) / width) ** 1.42 / fall * 3.2)
        corr -= 1.15 * np.exp(-((groove / 1.65) ** 2)) * lobe**2
    p = 2.74
    return (1 - (abs((X - mid) / rx) ** p + abs((Y - cy) / ry) ** p) ** (1 / p)) * min(
        rx, ry
    ) - corr


cape_outline = np.array(
    [
        (44, 340),
        (52, 336),
        (62, 339),
        (80, 350),
        (99, 352),
        (113, 349),
        (129, 352),
        (148, 346),
        (159, 341),
        (178, 340),
        (194, 336),
        (205, 338),
        (218, 344),
        (239, 344),
        (249, 338),
        (273, 339),
        (303, 341),
        (329, 342),
        (348, 338),
        (366, 339),
        (378, 345),
        (371, 368),
        (364, 388),
        (355, 403),
        (344, 414),
        (339, 431),
        (329, 452),
        (317, 466),
        (310, 484),
        (302, 496),
        (289, 502),
        (274, 505),
        (256, 503),
        (239, 497),
        (230, 496),
        (218, 505),
        (211, 505),
        (201, 499),
        (193, 498),
        (180, 482),
        (173, 468),
        (167, 463),
        (150, 464),
        (130, 465),
        (117, 457),
        (112, 445),
        (108, 430),
        (107, 410),
        (104, 395),
        (100, 389),
        (88, 387),
        (75, 377),
        (61, 362),
        (48, 352),
    ],
    np.int32,
)
cape_mask = np.zeros(figures[1].shape, np.uint8)
cv2.fillPoly(cape_mask, [cape_outline], 1)
cape_distance = ndimage.distance_transform_edt(
    cape_mask
) - ndimage.distance_transform_edt(cape_mask == 0)


def cape_slice(z):
    i = 1
    center, zero, kx, kz = origins[i]
    j = np.clip(zero - z * kz, 0, views[i].shape[0] - 1)
    indices = (center + kx * xs).clip(0, cape_mask.shape[1] - 1)
    width = ndimage.map_coordinates(
        cape_distance, [np.full_like(indices, j), indices], order=1
    )
    inset = np.maximum(0, width[:, None]) / abs(kx)
    thickness = 1.08 + 1.12 * np.tanh(inset / 3.8)
    free_edge = np.interp(
        z,
        [112, 118, 125, 132, 138, 145, 151, 157, 162, 166, 170],
        [17, 21, 23, 24, 27, 30, 30, 24, 21, 15, 8],
    )
    phase = X * 0.103 - 0.050 * (z - 143)
    ycenter = (
        free_edge
        - 6.5
        + 4.55 * np.cos(phase)
        + 2.7 * np.sin(0.13 * X + 0.18 * (z - 143))
    )
    turnout = np.exp(-(((X - (35 + 0.17 * (z - 143))) / 12.2) ** 2))
    ycenter -= turnout * np.interp(
        z, [112, 118, 126, 148, 158, 168], [0, 7, 24, 24, 18, 3]
    )
    behind_torso = 4.6 + 9.5 * np.exp(-(((X + 4) / 21) ** 4))
    behind_shoulder = (
        13.5 * np.exp(-(((X - 14.5) / 17.5) ** 4)) * np.clip((z - 144) / 10, 0, 1)
    )
    minimum = np.maximum(behind_torso, behind_shoulder)
    minimum -= 15 * np.clip((X - 26) / 10, 0, 1)
    ycenter = (ycenter + minimum + np.sqrt((ycenter - minimum) ** 2 + 1.8)) / 2
    cape = np.minimum(width[:, None] / abs(kx), thickness - np.abs(Y - ycenter))
    central_hem = 112.0 + 12.2 * np.exp(-(np.abs((X + 7.2) / 14.4) ** 3))
    cape = np.minimum(cape, z - central_hem)
    x = (X + 6.3) / 24.4
    y = (Y + 10.6) / np.where(Y < -10.6, 15.7, 24.7)
    radius = np.hypot(x, y)
    phi = np.arctan2(x, -y)
    shoulder_z = 168.1 - 7.4 * np.clip((radius - 0.41) / 0.69, 0, 1)
    shoulder_z += 1.20 * np.sin(phi) ** 2 + 0.80 * np.cos(phi * 3) * np.clip(
        radius - 0.43, 0, 1
    )
    rim = np.clip((1.10 - radius) / 0.17, 0, 1)
    neck = np.minimum.reduce(
        [
            (radius - 0.38) * 24,
            (1.10 - radius) * 24,
            0.76 + 0.59 * rim - np.abs(z - shoulder_z),
        ]
    )
    junction = np.maximum(0, 1 - np.abs(cape - neck) / 3.2)
    return np.maximum(cape, neck) + 0.80 * junction**2


add_volume("01 · Engraved mountain plinth", 0, 99.6, rock_slice)
add_volume("03 · Gilt fur, face and ears", 166.9, 216.8, head_slice)
add_volume(
    "04 · Enamel plume socket and crown",
    215.7,
    233.6,
    lambda z: np.minimum(
        section_field(hat, z),
        228.9 + 4.7 * np.clip(np.abs((X + 6) / 11), 0, 1) ** 1.3 - z,
    ),
)
add_volume("05 · Vermilion wind-blown cape", 112.0, 169.8, cape_slice)


for sign in [-1, 1]:

    def ear_slice(z, sign=sign):
        cx = -6.5 + sign * 23.4
        u = (0.48 * sign * (X - cx) + 0.877 * (Y + 7) - 0.15 * (z - 189)) / 5.0
        w = (z - 189.3) / 8.2
        outward = 0.877 * (X - cx) * sign - 0.48 * (Y + 7)
        radial = np.sqrt(u * u + w * w)
        surface = 4.7 * np.sqrt(np.clip(1 - radial**2, 0, 1))
        surface -= 2.55 * np.exp(-(((u + 0.12) / 0.47) ** 2) - ((w - 0.03) / 0.59) ** 2)
        surface += 1.1 * np.exp(
            -(((u + 0.38 + 0.17 * w) / 0.17) ** 2) - ((w + 0.12) / 0.42) ** 2
        )
        return np.minimum.reduce([(1 - radial) * 5, surface - outward, 2.65 + outward])

    add_volume(
        ("09" if sign < 0 else "10") + " · Sculpted auricle", 180.8, 197.8, ear_slice
    )

finish_recipe = runpy.run_path(
    str(Path(__file__).with_name("tongshifu-painted-surfaces.py"))
)
product_photos = item / "参考图/铜师傅官方旗舰店-战无不胜"
finish_recipe["prepare"](out, product_photos, views, origins, head, rock_profile)
finish_recipe["prepare_crown"](out, product_photos / "正面全身近摄.jpg")
craft = runpy.run_path(str(Path(__file__).with_name("tongshifu-wukong-casting.py")))
craft["prepare"](
    out,
    parts,
    {
        "01": (rock_profile, 0, 100, 0),
        "03": (head, 164, 219, 2),
        "04": (hat, 215, 234, 16),
    },
    finish_recipe["wrap"],
    product_photos,
)
