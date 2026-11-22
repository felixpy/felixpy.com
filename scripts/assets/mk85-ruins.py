from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial import Delaunay


def elevations(masks, levels):
    bounds = []
    for mask in masks:
        rows = []
        for z in levels:
            yy = np.clip(round(1310 - min(106, max(1.6, z)) * 3), 0, mask.shape[0] - 1)
            xx = np.flatnonzero(mask[yy])
            rows.append(((xx.min() - 450) / 3, (xx.max() - 450) / 3))
        bounds.append(ndimage.median_filter(np.array(rows), size=(5, 1)))
    return bounds


def badge(directory, image, profiles, heights, angles):
    x0, x1, z0, z1 = -37, 33, 5, 36
    dx = 0.265
    xx = np.arange(x0, x1, dx)
    zz = np.arange(z1, z0, -dx)
    gridx, gridz = np.meshgrid(xx, zz)
    source = cv2.remap(
        image,
        (450 + gridx * 3).astype("f"),
        (1310 - gridz * 3).astype("f"),
        cv2.INTER_CUBIC,
    )
    r, g, b = source.transpose(2, 0, 1)
    ink = ((r > 127) & (g > 99) & (r - b > 25) & (g - b > 10) & (r > g * 0.99)).astype(
        np.uint8
    )
    roi = (gridx > -35.7) & (gridx < 29.7) & (gridz > 6.8) & (gridz < 33)
    ink *= roi.astype("B")
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    mask = np.zeros_like(ink)
    for i in range(1, count):
        _x, _y, w, h, area = stats[i]
        if area > 22 and h >= 6 and area < w * h * 0.92:
            mask[labels == i] = 1
    contours = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]
    points = [
        cv2.approxPolyDP(c, 0.49, True).reshape(-1, 2) for c in contours if len(c) > 2
    ]
    iy, ix = np.nonzero(mask[2::4, 2::4])
    points = np.unique(
        np.vstack((*points, np.column_stack((ix * 4 + 2, iy * 4 + 2)))), axis=0
    )
    tri = Delaunay(points).simplices
    for s in (
        (0.33, 0.34, 0.33),
        (0.48, 0.48, 0.04),
        (0.04, 0.48, 0.48),
        (0.48, 0.04, 0.48),
    ):
        cent = np.rint(np.einsum("j,ijk->ik", s, points[tri])).astype(int)
        tri = tri[mask[cent[:, 1], cent[:, 0]] > 0]
    px = xx[points[:, 0]]
    pz = zz[points[:, 1]]
    front = (angles >= -np.pi / 2) & (angles <= np.pi / 2)
    depths = []
    for row in profiles:
        xs = row[front, 0]
        ys = row[front, 1]
        inds = np.argsort(xs)
        depths.append(np.interp(xx, xs[inds], ys[inds]))
    f = RegularGridInterpolator(
        (heights, xx), np.array(depths), bounds_error=False, fill_value=None
    )
    py = f(np.column_stack((pz, px)))
    xyz = np.column_stack((px, py - 0.75, pz))
    np.savez(directory / "badge.npz", xyz=xyz, tri=tri)


def build(directory, photos, masks):
    heights = np.unique(np.r_[np.arange(0, 108, 0.72), 108.0])
    angles = np.arange(-np.pi, np.pi, 2 * np.pi / 200)
    phi = angles[None, :]
    z = heights[:, None]
    c, s = np.cos(phi), np.sin(phi)
    bounds = elevations(masks, heights)
    tx = np.where(c >= 0, 1 - (1 - c) ** 2 * 0.45, (1 + c) ** 2 * 0.45)
    ty = np.where(s >= 0, (1 - s) ** 2 * 0.45, 1 - (1 + s) ** 2 * 0.45)

    def trace(a, b, weight, vec, exponent):
        lo = bounds[a][:, :1] * weight + bounds[b][:, :1] * (1 - weight)
        hi = bounds[a][:, 1:] * weight + bounds[b][:, 1:] * (1 - weight)
        return (lo + hi) / 2 + (hi - lo) / 2 * np.sign(vec) * abs(vec) ** exponent

    x = trace(0, 1, tx, s, 0.77)
    y = trace(2, 3, ty, -c, 0.77)
    for field, weight in ((x, abs(s) ** 10), (y, abs(c) ** 10)):
        smooth = ndimage.gaussian_filter1d(field, sigma=10, axis=0)
        field[:] = smooth + (field - smooth) * (0.12 + 0.86 * weight)
    rng = np.random.default_rng(85)
    circumference = 639
    arc = phi * circumference / (2 * np.pi)
    fragments = []
    for k, level in enumerate((0, 18, 37, 55, 74, 93, 111)):
        count = int(rng.integers(11, 17))
        width = circumference / count
        for i in range(count):
            sx = (
                -circumference / 2
                + (i + 0.5 * (k % 2) + rng.uniform(-0.26, 0.26)) * width
            )
            sz = level + rng.uniform(-5, 5)
            dx = (arc - sx + circumference / 2) % circumference - circumference / 2
            dz = z - sz
            xslant, zslant = rng.uniform(-0.45, 0.45), rng.uniform(-0.20, 0.20)
            run = abs(dx + dz * xslant) / (width * rng.uniform(0.83, 1.12))
            rise = abs(dz + dx * zslant) / (22 * rng.uniform(0.75, 1.19))
            distance = np.maximum(run, rise) + 0.15 * np.minimum(run, rise)
            fragments.append(
                (
                    distance,
                    rng.uniform(-2.2, 2.2) + dx * xslant * 0.23 + dz * zslant * 0.42,
                )
            )
    ds = np.stack([d for d, _ in fragments])
    facets = np.stack([np.broadcast_to(h, x.shape) for _, h in fragments])
    near = np.argpartition(ds, 1, axis=0)[:2]
    distances = np.take_along_axis(ds, near, axis=0)
    heights_by_face = np.take_along_axis(facets, near, axis=0)
    margin = abs(distances[1] - distances[0])
    relief = heights_by_face[0] - 5.4 * np.exp(-((margin / 0.105) ** 1.45))
    weight = np.maximum(np.concatenate([c, -c, -s, s], axis=0), 0.003) ** 6
    weight /= weight.sum(axis=0)
    py = np.broadcast_to(1310 - 3 * z, x.shape).astype("f")
    for cam, photo in enumerate(photos):
        px = (450 + 3 * (x if cam < 2 else y)).astype("f")
        value = cv2.cvtColor(photo, cv2.COLOR_RGB2GRAY)
        local = cv2.GaussianBlur(value, (0, 0), 2.25) - cv2.GaussianBlur(
            value, (0, 0), 25
        )
        relief += weight[cam] * cv2.remap(local, px, py, cv2.INTER_LINEAR) * 0.060
    fade = np.clip(z / 3, 0, 1) * np.clip((108 - z) / 4, 0, 1)
    plaque = np.exp(-((phi / 0.38) ** 6) - ((z - 20) / 15) ** 6)
    rough = relief * fade * (1 - 0.82 * plaque)
    x += s * rough
    y -= c * rough
    x = (x - (x.max() + x.min()) / 2) * (250 / np.ptp(x))
    y = (y - (y.max() + y.min()) / 2) * (180 / np.ptp(y))
    sides = np.stack(np.broadcast_arrays(x, y, z), axis=-1)
    rings = list(sides)
    top = []
    for f in (
        0.975,
        0.94,
        0.9,
        0.84,
        0.77,
        0.69,
        0.60,
        0.50,
        0.40,
        0.30,
        0.20,
        0.10,
        0.025,
    ):
        tx = x[-1] * f
        ty = y[-1] * f
        level = (
            0.75 * np.sin(tx * 0.064 + ty * 0.031)
            + 0.58 * np.sin(tx * 0.105 - ty * 0.087)
            + 0.37 * np.sin(tx * 0.175 + ty * 0.09)
        )
        h = 108 + min(1, (1 - f) * 13) * (4.75 + level)
        foot = np.minimum(abs(tx - 41), abs(tx + 59)) < 13
        h = np.where(foot & (abs(ty) < 22) & (f < 0.91), np.maximum(112.65, h), h)
        top.append(np.column_stack((tx, ty, h)))
    rings.extend(top)
    np.savez(directory / "ruins-shape.npz", rings=rings, side_count=len(sides))
    nga, ngz = 1664, 968
    u = np.linspace(-np.pi, np.pi, nga)[None, :]
    h = np.linspace(108, 0, ngz)[:, None]
    grid = np.stack(np.broadcast_arrays(h, u), axis=-1)
    angle_wrap = np.r_[angles, np.pi]

    def surface(field):
        return RegularGridInterpolator(
            (heights, angle_wrap), np.c_[field, field[:, :1]]
        )(grid)

    gx, gy = surface(x), surface(y)
    py = np.broadcast_to(1310 - 3 * h, gx.shape).astype("f")
    wx = (
        np.maximum(
            np.concatenate([np.cos(u), -np.cos(u), -np.sin(u), np.sin(u)], axis=0),
            0.005,
        )
        ** 5
    )
    wx /= wx.sum(axis=0)
    base = 0
    for i, img in enumerate(photos):
        px = (450 + 3 * (gx if i < 2 else gy)).astype("f")
        base = (
            base
            + cv2.remap(img, px, py, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            * wx[i][None, :, None]
        )
    color = np.uint8(np.clip(base * 0.82 + np.array((11, 8, 5)), 0, 255))
    cv2.imwrite(
        str(directory / "ruins.jpg"), color[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 96]
    )
    root = Path(__file__).resolve().parents[2]
    stone = cv2.imread(str(root / "public/media/materials/limestone-color.webp"))
    stone = cv2.resize(stone, (1024, 768)).astype(float)
    tone = np.mean(stone, axis=-1)
    val = np.clip(1 + 2.0 * (tone - np.median(tone)) / 255, 0.69, 1.34)
    top = np.uint8(np.clip(val[:, :, None] * np.array((69, 80, 87)), 0, 255))
    cv2.imwrite(str(directory / "ledge.jpg"), top, [cv2.IMWRITE_JPEG_QUALITY, 93])
    badge(directory, photos[0], sides, heights, angles)
