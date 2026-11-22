from pathlib import Path

import bpy
import numpy as np


def bake():
    width, height = 1792, 1472
    rng = np.random.default_rng(5248)
    relief = np.zeros((height, width), dtype=np.float32)
    for _ in range(3300):
        cx, cy = rng.uniform(0, width), rng.uniform(0, height)
        radius = min(8.1, 0.8 + rng.gamma(1.35, 1.15))
        stretch = 0.96 + 0.065 * radius + rng.uniform(-0.09, 0.09)
        left = max(0, int(cx - radius * 1.5))
        right = min(width, int(cx + radius * 1.5 + 2))
        lower = max(0, int(cy - radius * stretch * 1.4))
        upper = min(height, int(cy + radius * stretch * 1.4 + 2))
        y, x = np.mgrid[lower:upper, left:right]
        y = (y - cy) / (stretch * radius)
        x = (x - cx) / radius + y * rng.uniform(-0.14, 0.14)
        x *= 1 + 0.15 * y
        theta = np.arctan2(y, x)
        boundary = 1 + 0.045 * np.cos(3 * theta + rng.uniform(0, 6.28))
        cap = np.maximum(0, 1 - (x * x + y * y) / boundary**2)
        h = cap**0.85 * radius * rng.uniform(0.39, 0.66)
        tile = relief[lower:upper, left:right]
        np.maximum(tile, h, out=tile)
    gy, gx = np.gradient(relief)
    result = np.ones((height, width, 4), np.float32)
    result[:, :, 0] = 0.5 - 0.5 * np.clip(gx, -1, 1)
    result[:, :, 1] = 0.5 - 0.5 * np.clip(gy, -1, 1)
    result[:, :, 2] = np.minimum(relief * 2.5, 1)
    image = bpy.data.images.new("Pinned rain • contact normals and coverage", width, height, alpha=False, is_data=True)
    image.pixels.foreach_set(result.ravel())
    image.filepath_raw = str(Path(__file__).resolve().parents[2] / "public/media/panoramas/glass-rain-beads.png")
    image.file_format = "PNG"
    image.save()


bake()
