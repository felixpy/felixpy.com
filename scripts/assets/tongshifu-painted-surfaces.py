import cv2
import numpy as np
from PIL import Image
from scipy import ndimage


def mapped(image, px, py):
    return cv2.remap(
        image,
        px.astype("f"),
        py.astype("f"),
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    ).astype(np.float32)


def clean_metal(image, base, contrast=0.40, broad_contrast=0.17):
    color = image.astype(np.float32)
    value = np.mean(color, axis=-1)
    broad = cv2.GaussianBlur(value, (0, 0), 7)
    value = (value - broad) * contrast + (broad - np.median(broad)) * broad_contrast
    return np.clip(np.asarray(base, "f") + value[..., None], 0, 255)


def detail_normal(image, strength=0.6):
    grey = image.astype("f").mean(axis=-1) / 255
    fine = cv2.GaussianBlur(grey, (0, 0), 0.6) - cv2.GaussianBlur(grey, (0, 0), 5)
    gx = cv2.Sobel(fine, -1, 1, 0) * strength
    gy = cv2.Sobel(fine, -1, 0, 1) * strength
    v = np.stack((-gx, gy, np.ones_like(gx)), axis=-1)
    return (127.5 + 127.5 * v / np.linalg.norm(v, axis=-1, keepdims=True)).astype("B")


def polygon_mask(shape, points):
    mask = np.zeros(shape[:2], "B")
    cv2.fillPoly(mask, [np.round(points).astype(np.int32)], 255)
    return cv2.GaussianBlur(mask, (0, 0), 1.3).astype("f") / 255


def register_detail(landmarks):
    src, dst = (np.asarray(points, dtype=np.float32) for points in zip(*landmarks))
    return cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)[0]


def prepare(out, folder, views, origins, head, rock):
    front = np.asarray(Image.open(folder / "正面全身近摄.jpg").convert("RGB"))
    armour = np.asarray(Image.open(folder / "胸甲与束带.jpg").convert("RGB"))
    hmatrix = register_detail(
        [
            ((242, 269), (360, 430)),
            ((295, 269), (433, 430)),
            ((265, 297), (392, 468)),
            ((267, 282), (394, 448)),
            ((190, 271), (287, 435)),
            ((348, 271), (504, 434)),
            ((271, 186), (397, 315)),
            ((265, 345), (395, 539)),
        ]
    )
    bmatrix = register_detail(
        [
            ((259, 428), (364, 399)),
            ((173, 359), (85, 190)),
            ((358, 357), (683, 197)),
            ((230, 475), (277, 549)),
            ((215, 550), (220, 813)),
            ((318, 550), (550, 815)),
        ]
    )
    target_h = 2048
    yy, xx = np.indices((target_h, 1320), "f")
    a = xx / 2.25
    b = yy / 2.25
    close = mapped(
        front,
        hmatrix[0, 0] * a + hmatrix[0, 1] * b + hmatrix[0, 2],
        hmatrix[1, 0] * a + hmatrix[1, 1] * b + hmatrix[1, 2],
    )
    detail = mapped(
        armour,
        bmatrix[0, 0] * a + bmatrix[0, 1] * b + bmatrix[0, 2],
        bmatrix[1, 0] * a + bmatrix[1, 1] * b + bmatrix[1, 2],
    )
    swap = np.clip(np.minimum((b - 343) / 10, (550 - b) / 5), 0, 1) * np.clip(
        np.minimum((a - 175) / 10, (341 - a) / 10), 0, 1
    )
    full = close * (1 - swap[..., None]) + detail * swap[..., None]
    cloth = full.copy()
    original = mapped(views[0], a, b)
    full_body = np.clip((b - 339) / 8, 0, 1) * np.clip((555 - b) / 9, 0, 1)
    cloth = cloth * full_body[..., None] + original * (1 - full_body[..., None])
    invalid = (cloth.max(axis=2) - cloth.min(axis=2) < 13) & (cloth.max(axis=2) < 131)
    invalid |= (
        (a < 102 + 0.158 * (b - 350))
        & (a > 92 + 0.158 * (b - 350))
        & (b > 345)
        & (b < 392)
    )
    body_window = (a > 76) & (a < 405) & (b > 339) & (b < 567)
    safe = body_window & ~invalid
    near = ndimage.distance_transform_edt(
        ~safe, return_distances=False, return_indices=True
    )
    cloth = cloth[tuple(near)]
    gray = cloth.mean(axis=-1)
    light = cv2.GaussianBlur(gray, (0, 0), 8)
    lifted = cloth * (0.86 + 0.10 * (128 - light) / (100 + light))[..., None] + 13
    Image.fromarray(lifted.clip(0, 255).astype("B")).save(
        out / "cloth-paint.jpg", quality=95, subsampling=0
    )
    Image.fromarray(detail_normal(cloth, 0.49)).save(
        out / "cloth-detail.jpg", quality=93, subsampling=0
    )
    z = (868 - b) / 3.16
    x = (a - 289) / 3.16
    shaft = x < -48
    side = np.zeros_like(cloth) + [173, 68, 30]

    def paint(weight, color):
        nonlocal side
        weight = np.clip(weight, 0, 1)[..., None]
        side = side * (1 - weight) + np.array(color) * weight

    def band(low, high):
        return np.clip((z - low) * 4 + 0.5, 0, 1) * np.clip((high - z) * 4 + 0.5, 0, 1)

    core = np.clip((25 - abs(x + 6)) * 0.65, 0, 1)
    paint(band(99, 125), [101, 44, 31])
    paint(band(99, 101.6) + band(116, 119), [169, 131, 70])
    paint(
        band(103, 114) * np.clip((np.cos((z + x * 0.16) * 1.5) - 0.22) * 4, 0, 1),
        [34, 54, 86],
    )
    paint(core * band(123.0, 133), [164, 126, 70])
    paint(core * band(134.0, 146), [40, 69, 111])
    paint(core * band(138.4, 140.1), [156, 34, 40])
    paint(np.clip((z - 162) * 2, 0, 1), [145, 35, 44])
    paint(
        band(148, 164) * np.clip((x + 50) * 2, 0, 1) * np.clip((-43 - x) * 2, 0, 1),
        [44, 71, 108],
    )
    paint(band(146, 165) * shaft, [167, 137, 83])
    Image.fromarray(side.clip(0, 255).astype("B")).save(
        out / "return-paint.jpg", quality=94, subsampling=0
    )
    Image.fromarray(np.full((8, 8, 3), [128, 128, 255], "B")).save(
        out / "return-detail.jpg", quality=95, subsampling=0
    )
    img = full / 255
    mx = img.max(axis=-1)
    mi = img.min(axis=-1)
    chroma = mx - mi
    is_gold = (
        (img[:, :, 0] > img[:, :, 1] * 1.01)
        & (img[:, :, 0] < img[:, :, 1] * 1.45)
        & (img[:, :, 1] > img[:, :, 2] * 1.06)
        & (chroma < 0.50)
        & (mx > 0.22)
    )
    normalized = np.clip(img * 0.86 + 0.055, 0, 1) * 255
    metal = clean_metal(full, [164, 135, 89], 0.72)
    w = cv2.GaussianBlur(is_gold.astype("f"), (0, 0), 0.9)
    normalised = normalized * (1 - w[..., None]) + metal * w[..., None]
    for xmin, xmax, ymin, ymax in [
        (141, 216, 337, 385),
        (323, 398, 336, 386),
        (203, 324, 354, 419),
    ]:
        region = (a > xmin) & (a < xmax) & (b > ymin) & (b < ymax)
        keep = (
            region
            & (full[:, :, 0] > full[:, :, 2] * 1.12)
            & (full[:, :, 1] > full[:, :, 2] * 1.05)
            & (full[:, :, 0] < full[:, :, 1] * 1.68)
            & (mx > 0.18)
        )
        nearest = ndimage.distance_transform_edt(
            ~keep, return_distances=False, return_indices=True
        )
        cleaned = full[tuple(nearest)]
        neutral = clean_metal(cleaned, [175, 144, 90], 0.83)
        normalised[region] = neutral[region]
        full[region] = cleaned[region]
    Image.fromarray(normalised.clip(0, 255).astype("B")).save(
        out / "armour-paint.jpg", quality=95, subsampling=0
    )
    Image.fromarray(detail_normal(full, 0.92)).save(
        out / "armour-detail.jpg", quality=95, subsampling=0
    )
    local_y, local_x = np.indices((576, 796), "f")
    a = local_x / 3 + 129
    b = local_y / 3 + 330
    on_silk = ~((a > 308) & (a < 361) & (b > 402) & (b < 449))
    px = bmatrix[0, 0] * a + bmatrix[0, 1] * b + bmatrix[0, 2]
    py = bmatrix[1, 0] * a + bmatrix[1, 1] * b + bmatrix[1, 2]
    local = mapped(armour, px, py)
    r, g, blue = local.transpose(2, 0, 1)
    red = (r > 1.9 * g) & (r > 1.8 * blue) & (r > 45) & on_silk
    gold = (
        (r > 1.04 * g)
        & (r < 1.64 * g)
        & (g > blue * 1.10)
        & (r > 56)
        & ~on_silk
        & (b > 411)
        & (b < 441)
        & (a < 355)
    )

    def nearest_region(mask):
        n = ndimage.distance_transform_edt(
            ~mask, return_distances=False, return_indices=True
        )
        return local[tuple(n)]

    silk = nearest_region(red)
    brass = nearest_region(gold)
    red_value = silk[:, :, 0] - cv2.GaussianBlur(silk[:, :, 0], (0, 0), 14)
    paint = np.array([157, 35, 43]) + red_value[..., None] * np.array(
        [0.57, 0.28, 0.25]
    )
    gold_paint = clean_metal(brass, [153, 124, 77], 0.66)
    paint = np.where(on_silk[..., None], paint, gold_paint)
    Image.fromarray(paint.clip(0, 255).astype("B")).save(
        out / "handwork-paint.jpg", quality=95, subsampling=0
    )
    Image.fromarray(
        detail_normal(np.where(on_silk[..., None], silk, brass), 0.68)
    ).save(out / "handwork-detail.jpg", quality=94, subsampling=0)
    for kind, prof, za, zb in [("head", head, 164, 219), ("rock", rock, 0, 100)]:
        h, w = (700, 1400) if kind == "head" else (780, 1800)
        z, theta = np.meshgrid(
            np.linspace(zb, za, h), np.linspace(-np.pi, np.pi, w), indexing="ij"
        )
        lim = prof(np.clip(z, prof.x[0], prof.x[-1]))
        p = 2 if kind == "head" else 2.48
        s, c = np.sin(theta), np.cos(theta)
        x = (lim[:, :, 0] + lim[:, :, 1]) / 2 + (
            lim[:, :, 1] - lim[:, :, 0]
        ) / 2 * np.sign(s) * abs(s) ** (2 / p)
        y = (lim[:, :, 2] + lim[:, :, 3]) / 2 - (
            lim[:, :, 3] - lim[:, :, 2]
        ) / 2 * np.sign(c) * abs(c) ** (2 / p)
        cx, cy, sx, sz = origins[0]
        fx = cx + x * sx
        fy = cy - z * sz
        if kind == "head":
            samples = mapped(close, fx * 2.25, fy * 2.25)
            face_points = [
                (213, 241),
                (230, 241),
                (248, 251),
                (266, 259),
                (280, 251),
                (303, 240),
                (322, 240),
                (327, 255),
                (323, 285),
                (328, 296),
                (316, 306),
                (311, 314),
                (294, 318),
                (285, 324),
                (267, 321),
                (256, 325),
                (242, 320),
                (227, 312),
                (217, 302),
                (208, 299),
                (212, 282),
            ]
            face = mapped(polygon_mask(views[0].shape, face_points), fx, fy).clip(0, 1)
            skin = samples.copy()
            luminance = skin.mean(axis=-1)
            skin = (skin * 0.83 + np.array([31, 27, 20], "f")).clip(0, 255)
            dark = (
                (luminance < 90)
                & (np.abs(fy - 269) < 6)
                & ((abs(fx - 242) < 7) | (abs(fx - 295) < 7))
            )
            skin[dark] = samples[dark] * 0.91 + 5
            diffuse = skin * face[..., None] + clean_metal(
                samples, [167, 125, 62], 0.85, 0.29
            ) * (1 - face[..., None])
            raw = samples
            blend = np.clip((np.deg2rad(84) - abs(theta)) / np.deg2rad(20), 0, 1)
            bx, by, bk, bz = origins[1]
            back = mapped(views[1], bx + bk * x, by - bz * z)
            sy = origins[3][0] + origins[3][2] * y
            sz = origins[3][1] - origins[3][3] * z
            margin = np.clip((sz - 266) / 19, 0, 1) * np.clip((371 - sz) / 19, 0, 1)
            nose = np.clip((254 - sy) / 13, 0, 1) * margin
            sy = sy * (1 - nose) + np.clip(535 - sy, 268, 332) * nose
            ear = np.exp(-(((sy - 278) / 21) ** 4) - ((sz - 316) / 34) ** 4)
            side = mapped(views[3], sy, sz - ear * 52)
            side_weight = np.clip((np.pi - abs(theta) - 0.53) / 0.83, 0, 1)
            hair = back * (1 - side_weight[..., None]) + side * side_weight[..., None]
            diffuse = diffuse * blend[..., None] + clean_metal(
                hair, [163, 123, 64], 0.89, 0.29
            ) * (1 - blend[..., None])
            raw = raw * blend[..., None] + hair * (1 - blend[..., None])
            normal = detail_normal(raw, 0.85)
            face_weight = face * blend
            roughness = 0.44 + face_weight * (0.52 - 0.44)
            metalness = 0.55 - face_weight * (0.55 - 0.04)
            properties = np.stack(
                (np.ones_like(roughness), roughness, metalness), axis=-1
            )
            Image.fromarray(np.uint8(np.rint(255 * properties))).save(
                out / "head-metal-rough.png", optimize=True
            )
            normal = (
                normal * (1 - face_weight[..., None])
                + [128, 128, 255] * face_weight[..., None]
            ).astype("B")
        else:
            front = mapped(views[0], fx, fy)
            bx, by, bk, bz = origins[1]
            back = mapped(views[1], bx + bk * x, by - bz * z)
            side = mapped(
                views[3],
                origins[3][0] + origins[3][2] * y,
                origins[3][1] - origins[3][3] * z,
            )
            side2 = mapped(
                views[2],
                origins[2][0] + origins[2][2] * y,
                origins[2][1] - origins[2][3] * z,
            )
            fw = np.maximum(c, 0) ** 5
            bw = np.maximum(-c, 0) ** 5
            rw = np.maximum(s, 0) ** 5
            lw = np.maximum(-s, 0) ** 5
            raw = (
                front * fw[..., None]
                + back * bw[..., None]
                + side * rw[..., None]
                + side2 * lw[..., None]
            ) / (fw + bw + rw + lw)[..., None]
            diffuse = clean_metal(raw, [94, 82, 51], 0.62, 0.39)
            stamp = (back[:, :, 0] > back[:, :, 1] * 1.55) & (bw > 0.7) & (z < 29)
            diffuse[stamp] = back[stamp] * 0.77 + 13
            burn = (
                np.clip((48 - raw.mean(axis=-1)) * 0.52, 0, 15) * (bw > 0.8) * (z < 31)
            )
            diffuse -= burn[..., None]
            normal = detail_normal(raw, 1.12)
        Image.fromarray(np.uint8(np.clip(diffuse, 0, 255))).save(
            out / (kind + "-paint.jpg"), quality=96, subsampling=0
        )
        Image.fromarray(normal).save(
            out / (kind + "-detail.jpg"), quality=95, subsampling=0
        )


def prepare_plate(out, outlines, image):
    y, x = np.indices((650, 1632), "f")
    u = x / 6 + 136
    w = y / 6 + 330
    plate = np.asarray(Image.open(image).convert("RGB")).astype("f")
    texture = np.zeros((650, 1632, 3), "f") + [160, 119, 56]
    normals = np.zeros_like(texture) + [128, 128, 255]
    refs = [
        (
            [(148, 357), (182, 343), (215, 354), (177, 380)],
            [(4, 192), (155, 153), (231, 187), (110, 259)],
        ),
        (
            [(328, 355), (355, 349), (392, 348), (369, 380)],
            [(569, 185), (659, 162), (781, 149), (707, 256)],
        ),
        (
            [(210, 397), (222, 360), (306, 362), (317, 399)],
            [(200, 329), (238, 205), (506, 210), (546, 334)],
        ),
    ]
    for outline, (source, target) in zip(outlines, refs):
        mask = np.zeros((650, 1632), "B")
        cv2.fillPoly(
            mask, [np.rint((np.array(outline) - [136, 330]) * 6).astype(np.int32)], 255
        )
        signed = cv2.distanceTransform(mask, cv2.DIST_L2, 5) - cv2.distanceTransform(
            255 - mask, cv2.DIST_L2, 5
        )
        edge = signed / (6 * 3.16)
        warped = register_detail(list(zip(source, target)))
        px = warped[0, 0] * u + warped[0, 1] * w + warped[0, 2]
        py = warped[1, 0] * u + warped[1, 1] * w + warped[1, 2]
        raw = mapped(plate, px, py)
        r, g, b = raw.transpose(2, 0, 1)
        gold = (
            (r < b * 4 + 70)
            & (r < 1.72 * g + 4)
            & (g > b * 1.12)
            & (r > 45)
            & (g > 32)
            & (edge > -0.2)
        )
        nearest = ndimage.distance_transform_edt(
            ~gold, return_distances=False, return_indices=True
        )
        mapped_gold = raw[tuple(nearest)]
        detail = clean_metal(mapped_gold, [160, 118, 55], 1.02, 0.34)
        metal = np.clip((edge + 0.14) / 0.70, 0, 1)[..., None]
        detail = metal * detail + (1 - metal) * [157, 117, 54]
        region = edge >= -0.65
        texture[region] = detail[region]
        normal = detail_normal(mapped_gold, 0.75)
        normals[region] = normal[region] * metal[region] + [128, 128, 255] * (
            1 - metal[region]
        )
    Image.fromarray(texture.clip(0, 255).astype("B")).save(
        out / "weave-paint.jpg", quality=96, subsampling=0
    )
    Image.fromarray(normals.clip(0, 255).astype("B")).save(
        out / "weave-detail.jpg", quality=95, subsampling=0
    )


def prepare_crown(out, image):
    front = np.asarray(Image.open(image).convert("RGB"))
    z, theta = np.meshgrid(
        np.linspace(234, 215, 320), np.linspace(-np.pi, np.pi, 824), indexing="ij"
    )
    y = 326 - (z - 216) * 4.85
    x = 397 + np.sin(theta) * (38 + 8 * np.sin((z - 216) * 0.10))
    sample = mapped(front, x, y)
    white = (sample.min(axis=2) > 154) & (sample.max(axis=2) - sample.min(axis=2) < 46)
    neutral = sample.astype("B")
    neutral = cv2.inpaint(neutral, np.uint8(white) * 255, 3, cv2.INPAINT_TELEA).astype(
        "f"
    )
    back = np.zeros_like(neutral) + [181, 54, 28]
    band = 220.8 + 1.65 * np.cos(theta * 6)
    back[z < band + 2.2] = [169, 134, 73]
    back[(z > band + 0.5) & (z < band + 1.6)] = [31, 62, 98]
    weight = np.clip((np.pi / 2 - np.abs(theta)) / 0.35, 0, 1)[..., None]
    diffuse = (neutral * 0.81 + 12) * weight + back * (1 - weight)
    Image.fromarray(np.uint8(np.clip(diffuse, 0, 255))).save(
        out / "crown-paint.jpg", quality=96, subsampling=0
    )
    Image.fromarray(detail_normal(diffuse, 0.73)).save(
        out / "crown-detail.jpg", quality=95, subsampling=0
    )


def body_maps(out, vertices, faces):
    photos = [
        np.asarray(Image.open(out / f))
        for f in ("cloth-paint.jpg", "return-paint.jpg", "cloth-detail.jpg")
    ]
    charts = [
        (-5, -10, 118.3, 168.1, 740),
        (-17, -8, 98.8, 120.0, 312),
        (7, -9, 98.8, 120.0, 312),
    ]
    width, total = 1600, sum(row[4] for row in charts)
    atlas = np.zeros((total, width, 3), "B")
    normal_atlas = np.zeros_like(atlas)
    uv = np.zeros((len(faces), 3, 2), "f")
    centers = vertices[faces].mean(axis=1)
    group = np.where(centers[:, 2] > 119, 0, np.where(centers[:, 0] < -5, 1, 2))
    offset = 0
    for i, (cx, cy, z0, z1, h) in enumerate(charts):
        ids = group == i
        p = vertices[faces[ids]]
        angle = np.arctan2(p[:, :, 0] - cx, -p[:, :, 1] + cy)
        uu = angle / (2 * np.pi) + 0.5
        vv = np.clip((z1 - p[:, :, 2]) / (z1 - z0), 0, 1)
        seam = np.ptp(uu, axis=1) > 0.5
        uu[seam] = np.where(uu[seam] < 0.5, uu[seam] + 1, uu[seam])
        uv[ids] = np.stack((uu, 1 - (offset + 0.5 + vv * (h - 1)) / total), axis=-1)
        radii = np.full((h, width), np.nan, "f")
        xx = np.rint((uu % 1) * (width - 1)).astype(int)
        yy = np.rint(vv * (h - 1)).astype(int)
        rr = np.hypot(p[:, :, 0] - cx, p[:, :, 1] - cy)
        np.fmax.at(radii, (yy, xx), rr)
        close = ndimage.distance_transform_edt(
            np.isnan(radii), return_distances=False, return_indices=True
        )
        radii = ndimage.gaussian_filter(radii[tuple(close)], 3.3)
        z, theta = np.meshgrid(
            np.linspace(z1, z0, h), np.linspace(-np.pi, np.pi, width), indexing="ij"
        )
        x = cx + radii * np.sin(theta)
        px = (289 + x * 3.16) * 2.25
        py = (868 - z * 3.16) * 2.25
        mask = np.clip((1.70 - abs(theta)) / 0.66, 0, 1)[..., None]
        front, back, detail = [mapped(image, px, py) for image in photos]
        sl = slice(offset, offset + h)
        atlas[sl] = np.uint8(np.clip(front * mask + back * (1 - mask), 0, 255))
        normal_atlas[sl] = np.uint8(
            np.clip(detail * mask + [128, 128, 255] * (1 - mask), 0, 255)
        )
        offset += h
    Image.fromarray(atlas).save(out / "garment-paint.jpg", quality=96, subsampling=0)
    Image.fromarray(normal_atlas).save(
        out / "garment-detail.jpg", quality=93, subsampling=0
    )
    return uv


def wrap(vertices, profile, za, zb):
    bounds = profile(np.clip(vertices[:, :, 2], profile.x[0], profile.x[-1]))
    x = (2 * vertices[:, :, 0] - bounds[:, :, 0] - bounds[:, :, 1]) / np.maximum(
        1, bounds[:, :, 1] - bounds[:, :, 0]
    )
    y = (2 * vertices[:, :, 1] - bounds[:, :, 2] - bounds[:, :, 3]) / np.maximum(
        1, bounds[:, :, 3] - bounds[:, :, 2]
    )
    a = np.arctan2(x, -y) / (2 * np.pi) + 0.5
    seam = np.ptp(a, axis=1) > 0.5
    a[seam] = np.where(a[seam] < 0.5, a[seam] + 1, a[seam])
    return np.stack([a, np.clip((vertices[:, :, 2] - za) / (zb - za), 0, 1)], axis=-1)
