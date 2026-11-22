import sys
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage


def remap_channels(image, xy):
    return np.column_stack(
        [
            ndimage.map_coordinates(
                image[..., c], [xy[:, 1], xy[:, 0]], order=1, mode="nearest"
            )
            for c in range(image.shape[2])
        ]
    )


def studio_plate(reference, slug):
    l, a, b = cv2.split(cv2.cvtColor(reference, cv2.COLOR_RGB2LAB))
    reduced = cv2.GaussianBlur(l.astype("f"), (0, 0), 9)
    local = l - reduced
    l = np.uint8(np.clip(-4 + 0.91 * reduced + 1.15 * local, 0, 241))
    saturation = 1.12 if slug == "great-sage" else 1.06
    a = np.uint8(np.clip(128 + (a.astype(float) - 128) * saturation, 0, 255))
    b = np.uint8(np.clip(128 + (b.astype(float) - 128) * saturation, 0, 255))
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)


def inscription(root, image):
    factor = image.shape[0] / 690
    x, y = 410, 593
    w, h = 75, 38
    patch = cv2.resize(
        image[
            round(y * factor) : round((y + h) * factor),
            round(x * factor) : round((x + w) * factor),
        ],
        (w * 2, h * 2),
        interpolation=cv2.INTER_CUBIC,
    )
    r, g, b = patch.astype(float).transpose(2, 0, 1)
    mask = (r > 145) & (g > 119) & (r > 1.07 * g) & (g > 1.17 * b) & (r + g + b > 361)
    centers = np.column_stack(np.where(mask))
    points = []
    registry = {}
    triangles = []
    edges = []

    def point(ix, iy):
        key = (ix, iy)
        if key not in registry:
            registry[key] = len(points)
            points.append((x + ix / 2, y + iy / 2))
        return registry[key]

    for iy, ix in centers:
        a = point(ix, iy)
        b = point(ix + 1, iy)
        c = point(ix + 1, iy + 1)
        d = point(ix, iy + 1)
        triangles.extend([(a, c, b), (a, d, c)])
        for nx, ny, edge in [
            (ix, iy - 1, (a, b)),
            (ix + 1, iy, (b, c)),
            (ix, iy + 1, (c, d)),
            (ix - 1, iy, (d, a)),
        ]:
            if nx < 0 or ny < 0 or nx >= w * 2 or ny >= h * 2 or not mask[ny, nx]:
                edges.append(edge)
    np.savez_compressed(
        root / "great-sage-inscription.npz", points=points, faces=triangles, edges=edges
    )
    erase = np.zeros(image.shape[:2], dtype="uint8")
    expanded = cv2.dilate(mask.astype("uint8"), np.ones((7, 7), np.uint8))
    dest = erase[
        round(y * factor) : round((y + h) * factor),
        round(x * factor) : round((x + w) * factor),
    ]
    dest[:] = (
        cv2.resize(expanded, dest.shape[::-1], interpolation=cv2.INTER_NEAREST) * 255
    )
    return cv2.inpaint(image, erase, 4, cv2.INPAINT_TELEA)


def luminance_plate(rgb, mask):
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    canonical = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8)).apply(grey)
    return cv2.GaussianBlur(
        np.uint8(np.where(mask, 42 + 0.68 * canonical, 218)), (3, 3), 0.6
    )


def register(root, slug):
    mesh = trimesh.load(root / f"{slug}-tripo.ply", process=False)
    trimesh.smoothing.filter_taubin(
        mesh, lamb=0.43, nu=0.45, iterations=32 if slug == "mk85" else 10
    )
    points = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    colors = np.asarray(mesh.visual.vertex_colors[:, :3]).copy()
    img = np.asarray(Image.open(root / f"{slug}-cutout.png").convert("RGBA"))
    source = img[:, :, :3].copy()
    mask = img[:, :, 3] > 127
    height, width = mask.shape
    sy, sx = np.where(mask)
    minx, maxx, miny, maxy = sx.min(), sx.max(), sy.min(), sy.max()
    project = np.column_stack(
        (
            np.interp(
                points[:, 1], [points[:, 1].min(), points[:, 1].max()], [minx, maxx]
            ),
            np.interp(
                -points[:, 2], [-points[:, 2].max(), -points[:, 2].min()], [miny, maxy]
            ),
        )
    )
    pixels = np.int32(np.round(project * 2))
    render = np.full((height * 2, width * 2, 3), 127, np.uint8)
    coverage = np.zeros((height * 2, width * 2), np.uint8)
    zbuffer = np.full((height * 2, width * 2), -2, np.float32)
    depth = points[:, 0]
    face_depth = depth[faces].mean(axis=1)
    tint = colors[faces].mean(axis=1).astype("i")
    for f in np.argsort(face_depth):
        polygon = pixels[faces[f]]
        cv2.fillConvexPoly(render, polygon, tint[f].tolist())
        cv2.fillConvexPoly(coverage, polygon, 255)
        cv2.fillConvexPoly(zbuffer, polygon, float(face_depth[f]))
    render = cv2.resize(render, (width, height), interpolation=cv2.INTER_AREA)
    coverage = cv2.resize(coverage, (width, height), interpolation=cv2.INTER_AREA) > 100
    zbuffer = cv2.resize(zbuffer, (width, height), interpolation=cv2.INTER_NEAREST)
    solver = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    solver.setFinestScale(0)
    solver.setPatchSize(20)
    solver.setPatchStride(5)
    scalar = luminance_plate(render, coverage)
    original = luminance_plate(source, mask)
    field = solver.calc(scalar, original, None)
    field = np.clip(field, -21, 21)
    field = ndimage.gaussian_filter(field, (1.85, 1.85, 0))
    base_y = 502 if slug == "great-sage" else 453
    preserve_letters = np.clip((np.arange(height) - base_y) / 19, 0, 1).reshape(
        -1, 1, 1
    )
    uniform = ndimage.gaussian_filter(field, (9, 19, 0))
    field = field * (1 - preserve_letters) + uniform * preserve_letters
    mapped = project + remap_channels(field, project)
    row, col = np.mgrid[:height, :width]
    front_warp = cv2.remap(
        source,
        (col + field[:, :, 0]).astype("f"),
        (row + field[:, :, 1]).astype("f"),
        interpolation=cv2.INTER_LINEAR,
    )
    Image.fromarray(render).save(root / f"{slug}-registration-source.png")
    Image.fromarray(front_warp).save(root / f"{slug}-registration-target.png")
    source = studio_plate(source, slug)
    nearest = ndimage.distance_transform_edt(
        ~mask, return_distances=False, return_indices=True
    )
    padded = source[tuple(nearest)]
    large_path = root / f"{slug}-high-resolution.png"
    if large_path.exists():
        large = np.asarray(Image.open(large_path).convert("RGB"))
        if slug == "great-sage":
            large = inscription(root, large)
        large_mask = (
            cv2.resize(
                mask.astype("uint8"),
                large.shape[:2][::-1],
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )
        near = ndimage.distance_transform_edt(
            ~large_mask, return_distances=False, return_indices=True
        )
        final_image = studio_plate(large, slug)[tuple(near)]
    else:
        final_image = padded
    Image.fromarray(final_image).save(root / f"{slug}-surface.png", optimize=True)
    source_front = remap_channels(padded.astype("f") / 255, mapped)
    pixel_front = ndimage.map_coordinates(
        zbuffer, [project[:, 1], project[:, 0]], order=0, mode="nearest"
    )
    visible = np.clip(1 - (pixel_front - depth - 0.013) / 0.061, 0, 1)
    orient = np.asarray(mesh.vertex_normals[:, 0])
    mix = visible * np.clip((orient + 0.43) / 0.55, 0, 1)
    mix = mix * mix * (3 - 2 * mix)
    points = points.copy()
    broad_field = ndimage.gaussian_filter(field, (4, 4, 0))
    shift = remap_channels(broad_field, project)
    points[:, 1] += shift[:, 0] * np.ptp(points[:, 1]) / (maxx - minx) * 0.88
    points[:, 2] -= shift[:, 1] * np.ptp(points[:, 2]) / (maxy - miny) * 0.88
    relief = np.load(root / f"{slug}-depth.npy")
    bumps = relief - ndimage.gaussian_filter(relief, 3)
    detail = ndimage.map_coordinates(
        bumps, [mapped[:, 1], mapped[:, 0]], order=1, mode="nearest"
    )
    points[:, 0] += np.clip(detail, -0.17, 0.17) * 0.023 * mix
    norm = np.column_stack((points[:, 1], -points[:, 0], points[:, 2]))
    norm -= np.array(
        [
            (norm[:, 0].max() + norm[:, 0].min()) / 2,
            (norm[:, 1].max() + norm[:, 1].min()) / 2,
            norm[:, 2].min(),
        ]
    )
    if slug == "great-sage":
        norm *= np.array([0.175, 0.057, 0.265]) / np.ptp(norm, axis=0)
        x, y, z = norm.T
        edge = np.minimum.reduce(
            [
                (x + 0.007) / 0.009,
                (0.051 - x) / 0.009,
                (z - 0.005) / 0.008,
                (0.043 - z) / 0.009,
            ]
        )
        face_weight = np.clip(edge, 0, 1) * np.clip((-0.001 - y) / 0.012, 0, 1)
        plane = -0.024 + 0.095 * x + 0.10 * (z - 0.02)
        norm[:, 1] += face_weight * (plane - norm[:, 1])
    else:
        norm *= np.array([0.155, 0.110, 0.260]) / np.ptp(norm, axis=0)
    broad = colors.astype("f") / 255
    hsv = cv2.cvtColor(broad.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    hsv[:, 1] = np.clip(hsv[:, 1] * 1.22, 0, 1)
    broad = cv2.cvtColor(hsv.reshape(-1, 1, 3), cv2.COLOR_HSV2RGB).reshape(-1, 3)
    mapuv = np.column_stack(
        (mapped[:, 0] / (width - 1), 1 - mapped[:, 1] / (height - 1))
    )
    front_rgb = source_front * mix[:, None] + broad * (1 - mix[:, None])
    np.savez_compressed(
        root / f"{slug}-casting.npz",
        points=norm.astype("f"),
        faces=faces.astype("i"),
        uv=mapuv.astype("f"),
        rear=broad.astype("f"),
        mix=mix.astype("f"),
        front=front_rgb.astype("f"),
    )
    print(slug, len(points), "dimensional envelope", np.ptp(norm, axis=0), flush=True)


if __name__ == "__main__":
    root = Path(sys.argv[1])
    for slug in sys.argv[2:]:
        register(root, slug)
