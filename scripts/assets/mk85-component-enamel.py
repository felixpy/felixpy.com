import json
import math
import runpy
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from scipy.interpolate import CubicHermiteSpline

REGISTRATION = runpy.run_path(
    str(Path(__file__).with_name("mk85-large-registration.py"))
)
SCALE = 420 / 731
TW, TH = 608, 464
PAINT = {
    "red": (163, 24, 38),
    "gold": (196, 169, 117),
    "steel": (84, 81, 83),
    "silver": (139, 139, 142),
}


def views(work):
    images = []
    masks = []
    for k, (img, mask) in enumerate(REGISTRATION["camera_views"]()):
        mask = mask.astype(bool)
        img = cv2.resize(img, (900, 1360), interpolation=cv2.INTER_AREA)
        indices = ndimage.distance_transform_edt(
            ~mask, return_indices=True, return_distances=False
        )
        image = img[tuple(indices)][..., ::-1].astype(np.float32)
        images.append(image)
        masks.append(mask)
    return images, masks


def sample(img, x, z):
    return cv2.remap(
        img,
        x.astype("f"),
        z.astype("f"),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def intervals(mask):
    rows = []
    for line in mask:
        cuts = np.flatnonzero(np.diff(np.r_[False, line, False])).reshape(-1, 2)
        rows.append([(a, b) for a, b in cuts if b - a > 3])
    return rows


def coordinates(item):
    rows = np.asarray(item["rows"])
    v = np.linspace(-0.008 / 0.984, 1 + 0.008 / 0.984, TH)[:, None]
    v = np.clip(v, 0, 1) * (rows[-1, 0] - rows[0, 0]) + rows[0, 0]
    a = ((np.linspace(0, 1, TW)[None, :] - 0.008) / 0.984 - 0.5) * (2 * np.pi)
    spline = CubicHermiteSpline(
        rows[:, 0], rows[:, 1:], np.gradient(rows[:, 1:], rows[:, 0], axis=0)
    )
    cx, cy, rx, fore, aft = spline(v[:, 0]).T[:, :, None]
    sin, cos = np.sin(a), np.cos(a)
    xx = rx * SCALE * np.sign(sin) * abs(sin) ** item["square"]
    yy = -np.where(cos > 0, fore, aft) * np.sign(cos) * abs(cos) ** item["square"]
    yaw = item["yaw"]
    x = (cx - 221) * SCALE + item["side"] * (xx * math.cos(yaw) - yy * math.sin(yaw))
    y = cy + xx * math.sin(yaw) + yy * math.cos(yaw)
    angle = np.arctan2(item["side"] * np.sin(a + yaw), np.cos(a + yaw))
    return x, y, (791 - v) * SCALE, np.broadcast_to(angle, x.shape), cx


def registered_x(x, z, rows, cx, name, side, cam):
    out = 450 + 3 * x
    base = out.copy()
    y = np.rint(1310 - z[:, 0] * 3).astype(int)
    u = 791 - z[:, 0] / SCALE
    for i, row in enumerate(y):
        strips = rows[np.clip(row, 0, len(rows) - 1)]
        if not strips:
            continue
        lx, rx = out[i].min(), out[i].max()
        if rx - lx < 0.01:
            continue
        unit = np.clip((out[i] - lx) / (rx - lx), 0.014, 0.986)
        head = name == "Helmet" and u[i] < 124
        legs = any(n in name for n in ("thigh", "greave", "knee", "sabatons"))
        arm = any(n in name for n in ("upper arm", "vambrace", "gauntlet"))
        center = "Breast" in name
        lim = None
        if cam < 2:
            if head:
                lim = (strips[0][0], strips[-1][1])
            elif (
                legs
                and u[i] > 348
                and len(strips) >= 2
                or arm
                and u[i] > 208
                and len(strips) >= 3
            ):
                lim = strips[0] if side < 0 else strips[-1]
            elif center and 215 < u[i] < 291 and len(strips) >= 3:
                lim = max(strips, key=lambda ab: ab[1] - ab[0])
            if cam == 1 and lim is None:
                shift = np.interp(
                    u[i],
                    [60, 128, 155, 220, 275, 338, 430, 585],
                    [32, 29, 26, 22, 22, 22, 21, 16],
                )
                out[i] += shift
        else:
            lim = (strips[0][0], strips[-1][1])
            if 130 < u[i] < 350:
                if center:
                    out[i] += np.interp(
                        u[i], [130, 175, 232, 300, 350], [4, -9, -6, -12, -20]
                    )
                    lim = None
                elif arm:
                    lo, hi = lim
                    if "upper arm" in name:
                        lim = (lo + 0.24 * (hi - lo), hi - 0.04 * (hi - lo))
                    elif "vambrace" in name:
                        lim = (lo + 0.13 * (hi - lo), hi - 0.14 * (hi - lo))
                    else:
                        lim = (lo, lo + 0.74 * (hi - lo))
        if lim:
            out[i] = lim[0] + (lim[1] - lim[0]) * unit
    amount = 6.0 if "thigh" in name else 2.2
    return ndimage.gaussian_filter1d(out - base, amount, axis=0) + base


def paint_layers(img):
    r, g, b = np.moveaxis(img + 3, -1, 0)
    luma = 0.26 * r + 0.61 * g + 0.13 * b
    soft = cv2.GaussianBlur(luma, (0, 0), 7)
    broad = cv2.GaussianBlur(luma, (0, 0), 26)
    variation = (
        np.clip((luma + 14) / (soft + 14), 0.40, 1.42) ** 0.76
        * np.clip((soft + 34) / (broad + 34), 0.68, 1.27) ** 0.35
    )
    chroma = np.clip((r - g - 11) / 40, 0, 1) * np.clip((r - b - 12) / 42, 0, 1)
    warm = (
        np.clip((g - b - 5) / 23, 0, 1) * np.clip((r - b - 9) / 33, 0, 1) * (1 - chroma)
    )
    dark = np.clip((80 - luma) / 68, 0, 1)
    neutral = (1 - chroma[:, :, None]) * (
        (1 - warm)[:, :, None] * np.array((122, 125, 127))
        + warm[:, :, None] * np.array(PAINT["gold"])
    )
    cast = chroma[:, :, None] * np.array(PAINT["red"]) + neutral
    casts = {}
    for key, base in PAINT.items():
        strength = {"red": 0.40, "gold": 0.38, "silver": 0.13, "steel": 0.72}[key]
        color = (1 - strength) * np.array(base) + strength * cast
        val = variation * (1 - 0.30 * dark)
        casts[key] = np.float32(np.clip(color * val[:, :, None], 3, 246))
    return casts


def body(work, photos, masks):
    items = json.loads((work / "profiles.json").read_text())
    strips = list(map(intervals, masks))
    by_camera = [paint_layers(im) for im in photos]
    atlases = {key: np.zeros((TH * 5, TW * 4, 3), np.uint8) for key in PAINT}
    for idx, item in enumerate(items):
        x, y, z, angle, cx = coordinates(item)
        w = [
            np.maximum(np.cos(angle), 0) ** 2.7,
            np.maximum(-np.cos(angle), 0) ** 2.7,
            np.maximum(-np.sin(angle), 0) ** 3,
            np.maximum(np.sin(angle), 0) ** 3,
        ]
        if "Breast" in item["name"] or "Cervical" in item["name"]:
            w[2] *= 0.18
            w[3] *= 0.18
        if item["name"].startswith("Right "):
            w[3] *= 0.28
        if item["name"].startswith("Left "):
            w[2] *= 0.28
        xmaps = []
        zmap = np.broadcast_to(1310 - 3 * z, x.shape)
        for k in range(4):
            raw = x if k < 2 else y
            xmaps.append(
                registered_x(raw, z, strips[k], cx, item["name"], item["side"], k)
            )
        for key, color in PAINT.items():
            values = sum(
                sample(by_camera[k][key], xmaps[k], zmap) * w[k][:, :, None]
                for k in range(4)
            )
            values /= np.maximum(1e-6, sum(w))[:, :, None]
            front = np.maximum(np.cos(angle), 0)
            strength = 0.70
            if item["name"] == "Helmet":
                strength = 0.44 - 0.38 * front**2
            elif "thigh" in item["name"]:
                strength = 0.29 + 0.22 * (1 - front)
            elif "Breast" in item["name"]:
                v = 791 - z / SCALE
                core = np.exp(-((angle / 0.44) ** 6) - ((v - 182.5) / 20) ** 6)
                strength = 0.84 * (1 - 0.992 * core)
            pigment = np.asarray(color)
            values = (
                pigment
                + (values - pigment) * np.broadcast_to(strength, x.shape)[:, :, None]
            )
            tile = np.uint8(np.clip(values, 0, 255))
            atlases[key][
                (idx // 4) * TH : (idx // 4 + 1) * TH,
                (idx % 4) * TW : (idx % 4 + 1) * TW,
            ] = tile
    for key, image in atlases.items():
        cv2.imwrite(
            str(work / (key + "-lacquer.jpg")),
            image[:, :, ::-1],
            [cv2.IMWRITE_JPEG_QUALITY, 94],
        )


def main(work):
    photos, masks = views(work)
    body(work, photos, masks)
    runpy.run_path(str(Path(__file__).with_name("mk85-ruins.py")))["build"](
        work, photos, masks
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
