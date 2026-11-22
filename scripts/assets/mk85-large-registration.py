import runpy
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

PRODUCT = (
    Path(__file__).resolve().parents[2]
    / ".references/05-摄影与陈列/手办与收藏模型/Iron Man Mark 85"
)
REFS = PRODUCT / "参考图/用户参考图"
SIZE = (900, 1360)
SCALE, CX, FLOOR = 3.0, 450, 1310


def photo(name):
    return cv2.imdecode(
        np.frombuffer((REFS / name).read_bytes(), np.uint8), cv2.IMREAD_COLOR
    )


def outlined(image, rows, gap=()):
    outline = np.int32(
        [(left, y) for y, left, right in rows]
        + [(right, y) for y, left, right in rows[::-1]]
    )
    silhouette = cv2.fillPoly(np.zeros(image.shape[:2], np.uint8), [outline], 1)
    if gap:
        cv2.fillPoly(silhouette, [np.int32(gap)], 0)
    dilation = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    prior = np.where(
        cv2.dilate(silhouette, dilation), cv2.GC_PR_BGD, cv2.GC_BGD
    ).astype(np.uint8)
    prior[silhouette == 1] = cv2.GC_PR_FGD
    eroded = cv2.erode(
        silhouette, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (33, 33))
    )
    saturation = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)[:, :, 1]
    prior[(eroded == 1) & (saturation > 39)] = cv2.GC_FGD
    cv2.grabCut(image, prior, None, None, None, 4, cv2.GC_INIT_WITH_MASK)
    mask = (prior % 2).astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    keep = cv2.drawContours(
        np.zeros_like(mask), [max(contours, key=cv2.contourArea)], -1, 1, -1
    )
    mask *= keep
    return mask


def register(
    image, mask, center, bottom, width_scale, height_scale, flip=False, density=1
):
    matrix = np.float32(
        [
            [SCALE / width_scale, 0, CX - center * SCALE / width_scale],
            [0, SCALE / height_scale, FLOOR - bottom * SCALE / height_scale],
        ]
    )
    layer = cv2.warpAffine(
        image, matrix * density, tuple(n * density for n in SIZE), flags=cv2.INTER_CUBIC
    )
    region = cv2.warpAffine(mask, matrix, SIZE, flags=cv2.INTER_NEAREST)
    if flip:
        layer, region = (
            np.ascontiguousarray(layer[:, ::-1]),
            np.ascontiguousarray(region[:, ::-1]),
        )
    return layer, region


def frontal_detail(front, mask):
    source = cv2.imdecode(
        np.frombuffer(
            (PRODUCT / "参考图/mk85-manufacturer-a.jpg").read_bytes(), np.uint8
        ),
        cv2.IMREAD_COLOR,
    )
    anchors = np.float32(
        [
            (365, 142, 202, 60),
            (315, 159, 184, 67),
            (355, 193, 194, 79),
            (409, 162, 217, 67),
            (431, 189, 228, 79),
            (301, 225, 177.5, 91.5),
            (330, 234, 187, 94.2),
            (357, 229, 196, 92),
            (396, 228, 211, 92),
            (417, 219, 216, 89),
            (432, 241, 229, 96),
            (320, 278, 184, 110),
            (369, 289, 197, 115),
            (414, 264, 216, 105),
            (324, 302, 185, 120.5),
            (372, 315, 203, 124),
            (417, 293, 214, 116),
            (316, 326, 181, 130),
            (421, 317, 223, 124),
            (288, 335, 168, 138),
            (448, 331, 231, 137),
            (219, 363, 138, 148),
            (171, 386, 124, 154),
            (135, 451, 116, 179),
            (143, 492, 118, 197),
            (198, 478, 135, 187),
            (210, 455, 141.5, 174),
            (216, 414, 144, 159),
            (236, 371, 147, 145),
            (278, 363, 167, 144),
            (311, 360, 180, 143),
            (346, 366, 191, 141),
            (360, 386, 198.3, 151),
            (392, 399, 210, 155),
            (413, 366, 219, 141),
            (468, 355, 241, 144),
            (495, 369, 253, 149),
            (525, 393, 262, 156),
            (561, 380, 274, 145),
            (599, 408, 286, 157),
            (610, 453, 293, 175),
            (597, 476, 290, 188),
            (568, 465, 279, 183),
            (547, 450, 271, 174),
            (342, 443, 194, 174),
            (352, 440, 198, 172),
            (372, 447, 205.6, 175),
            (391, 440, 213, 172),
            (402, 447, 219, 176),
            (371, 501, 207, 194),
            (225, 465, 149, 179),
            (255, 505, 161, 193),
            (278, 531, 170, 201),
            (316, 563, 184, 212),
            (362, 566, 199, 217),
            (423, 565, 226, 217),
            (456, 535, 241, 202),
            (500, 501, 255, 189),
            (519, 462, 263, 175),
            (142, 493, 122, 196),
            (126, 552, 116, 218),
            (128, 603, 120, 237),
            (167, 612, 131, 239),
            (207, 520, 144, 203),
            (571, 486, 276, 188),
            (613, 496, 291, 194),
            (621, 590, 299, 227),
            (593, 616, 288, 238),
            (108, 588, 112, 232),
            (91, 634, 104, 249),
            (88, 698, 102, 271),
            (109, 708, 106, 278),
            (144, 662, 120, 258),
            (613, 601, 300, 229),
            (650, 630, 313, 241),
            (651, 694, 316, 265),
            (633, 703, 313, 269),
            (305, 594, 183, 223),
            (375, 606, 205, 231),
            (437, 593, 228, 222),
            (305, 638, 183, 242),
            (380, 647, 206, 246),
            (443, 633, 228, 241),
            (302, 683, 182, 259),
            (380, 694, 206, 261),
            (444, 675, 231, 256),
            (310, 720, 184, 274),
            (383, 736, 206, 277),
            (446, 710, 228, 272),
            (314, 755, 181, 287),
            (368, 776, 203, 293),
            (446, 752, 232, 288),
            (84, 760, 100, 296),
            (122, 776, 112, 301),
            (86, 843, 99, 324),
            (98, 868, 105, 338),
            (121, 881, 111, 342),
            (148, 852, 123, 330),
            (608, 775, 294, 296),
            (646, 756, 311, 286),
            (666, 777, 319, 290),
            (656, 841, 318, 316),
            (632, 880, 310, 336),
            (587, 861, 293, 326),
            (242, 792, 149, 299),
            (257, 837, 155, 317),
            (280, 866, 166, 330),
            (330, 895, 186, 341),
            (399, 889, 224, 339),
            (450, 844, 240, 317),
            (490, 829, 257, 310),
            (500, 855, 263, 324),
            (515, 878, 269, 334),
        ]
    )
    destination = anchors[:, 2:]
    source_xy = anchors[:, :2] * (source.shape[1] / 700)
    from scipy.interpolate import RBFInterpolator

    warp = RBFInterpolator(destination, source_xy, smoothing=1.35)
    zoom = 3
    h, w = front.shape[:2]
    yy, xx = np.mgrid[:365:2, : w + 2 : 2].astype("f")
    input_points = np.column_stack((xx.ravel(), yy.ravel()))
    sampling = warp(input_points).reshape((*xx.shape, 2)).astype("f")
    sampling = cv2.resize(
        sampling,
        (2 * zoom * xx.shape[1], 2 * zoom * xx.shape[0]),
        interpolation=cv2.INTER_CUBIC,
    )[: 365 * zoom, : w * zoom]
    mapped = cv2.remap(
        source, sampling, None, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    large = cv2.resize(front, (w * zoom, h * zoom), interpolation=cv2.INTER_CUBIC)
    pixels = (np.arange(mapped.shape[0]) / zoom)[:, None, None]
    mix = np.clip((348 - pixels) / 12, 0, 1)
    large[: mapped.shape[0]] = np.uint8(
        np.clip(mapped * mix + large[: mapped.shape[0]] * (1 - mix), 0, 255)
    )
    return large, cv2.resize(
        mask, (w * zoom, h * zoom), interpolation=cv2.INTER_NEAREST
    )


def camera_views():
    sheet = photo("large-four-views.png")
    front = sheet[:815, :463].copy()
    side = sheet[951:1755, :463].copy()
    opposite = sheet[951:1755, 605:1037].copy()
    back = photo("large-rear-armour.png")
    front_rows = [
        (60, 195, 207),
        (68, 179, 225),
        (106, 177, 229),
        (128, 185, 221),
        (140, 146, 254),
        (156, 127, 279),
        (179, 118, 291),
        (217, 117, 299),
        (246, 104, 311),
        (305, 94, 322),
        (341, 98, 316),
        (346, 142, 279),
        (422, 144, 277),
        (460, 137, 286),
        (502, 128, 294),
        (564, 128, 299),
        (583, 121, 303),
        (597, 115, 309),
        (600, 36, 380),
        (623, 30, 391),
        (658, 28, 392),
        (693, 18, 409),
        (742, 10, 430),
        (775, 4, 438),
        (791, 34, 393),
    ]
    front_gap = [
        (171, 338),
        (207, 330),
        (238, 336),
        (254, 430),
        (276, 574),
        (279, 587),
        (152, 587),
        (169, 451),
        (182, 385),
        (183, 355),
    ]
    side_rows = [
        (38, 205, 223),
        (47, 190, 240),
        (75, 188, 249),
        (108, 192, 244),
        (130, 183, 236),
        (146, 170, 245),
        (174, 156, 260),
        (199, 158, 262),
        (235, 169, 255),
        (273, 176, 252),
        (305, 181, 257),
        (323, 179, 260),
        (348, 176, 249),
        (386, 184, 247),
        (426, 190, 244),
        (463, 177, 241),
        (492, 169, 225),
        (536, 170, 224),
        (558, 174, 243),
        (581, 174, 267),
        (588, 132, 291),
        (600, 115, 336),
        (636, 93, 341),
        (652, 82, 337),
        (678, 71, 350),
        (725, 56, 360),
        (758, 48, 359),
        (784, 42, 353),
        (794, 115, 327),
    ]
    opposite_rows = [
        (38, 211, 241),
        (55, 192, 248),
        (79, 188, 249),
        (108, 187, 239),
        (132, 181, 243),
        (154, 174, 267),
        (188, 174, 279),
        (222, 177, 270),
        (256, 179, 258),
        (293, 169, 264),
        (325, 166, 265),
        (357, 180, 259),
        (400, 187, 249),
        (431, 184, 245),
        (470, 188, 260),
        (496, 198, 270),
        (540, 192, 270),
        (573, 171, 268),
        (583, 164, 270),
        (585, 130, 316),
        (600, 109, 344),
        (627, 107, 357),
        (666, 99, 372),
        (706, 93, 375),
        (743, 82, 380),
        (777, 77, 383),
        (792, 96, 310),
    ]
    back_rows = [
        (119, 575, 595),
        (132, 551, 626),
        (166, 539, 635),
        (217, 547, 633),
        (242, 530, 651),
        (264, 477, 692),
        (302, 439, 735),
        (354, 410, 755),
        (404, 398, 768),
        (461, 388, 775),
        (516, 377, 783),
        (589, 368, 805),
        (642, 370, 813),
        (659, 385, 798),
        (661, 462, 716),
        (719, 457, 713),
        (796, 452, 716),
        (844, 438, 733),
        (901, 428, 752),
        (980, 418, 767),
        (1106, 410, 776),
        (1140, 405, 782),
        (1153, 301, 887),
        (1168, 256, 948),
        (1210, 245, 957),
        (1241, 271, 955),
        (1288, 260, 963),
        (1337, 229, 978),
        (1395, 229, 977),
        (1477, 205, 997),
        (1511, 211, 989),
    ]
    back_gap = [
        (546, 727),
        (578, 694),
        (616, 718),
        (638, 810),
        (672, 928),
        (696, 1123),
        (471, 1126),
        (483, 975),
        (505, 831),
    ]
    frontal, foreground = frontal_detail(front, outlined(front, front_rows, front_gap))
    zoom = frontal.shape[0] / front.shape[0]
    views = [
        register(
            frontal,
            foreground,
            220 * zoom,
            791 * zoom,
            437 / 250 * zoom,
            731 / 420 * zoom,
            density=2,
        ),
        register(
            back,
            outlined(back, back_rows, back_gap),
            594,
            1511,
            793 / 250,
            1392 / 420,
            True,
        ),
        register(side, outlined(side, side_rows), 197, 790, 316 / 180, 752 / 420, True),
        register(
            opposite, outlined(opposite, opposite_rows), 229, 790, 319 / 180, 752 / 420
        ),
    ]
    return views


def projected(points, axis):
    return np.column_stack((CX + points[:, axis] * SCALE, FLOOR - points[:, 2] * SCALE))


def enamel_pigments(image, mask, index):
    density = image.shape[1] // SIZE[0]
    if density != 1:
        mask = cv2.resize(mask, image.shape[1::-1], interpolation=cv2.INTER_NEAREST)
    panel = runpy.run_path(str(Path(__file__).with_name("mk85-large-panels.py")))
    coat = panel["COAT"]

    def colour(name):
        return np.array(list(bytes.fromhex(coat[name][0]))[::-1], dtype=float)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    b, g, r = image.astype(float).transpose(2, 0, 1) + 4
    valid = mask.astype(bool)
    vivid = (r / g > 1.33) & (r / b > 1.35) & (r - g > 21)
    gilded = (r / g < 1.33) & (g / b > 1.12) & (r / b > 1.22) & (g > 43)
    coordinates = np.indices(mask.shape)
    y = coordinates[0] / density
    armour = valid & (y < 969)
    seed_red = cv2.morphologyEx(
        np.uint8(armour & vivid), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    )
    seed_gold = cv2.morphologyEx(
        np.uint8(armour & gilded), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    )
    d_red = ndimage.distance_transform_edt(~seed_red.astype(bool))
    d_gold = ndimage.distance_transform_edt(~seed_gold.astype(bool))
    gold = np.clip((d_red - d_gold + 3) / 6, 0, 1)
    gold = ndimage.gaussian_filter(gold, 1.2)
    luma = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(float)
    local = ndimage.gaussian_filter(luma, 4)
    ridge = np.clip((local - luma - 10) / 50, 0, 1)
    neutral = np.clip((50 - hsv[:, :, 1].astype(float)) / 35, 0, 1)
    metal = np.clip((np.minimum(d_red, d_gold) - 3) / 10, 0, 1) * neutral
    metal *= np.clip((180 - luma) / 76, 0, 1)
    paint = colour("red") * (1 - gold[:, :, None]) + colour("gold") * gold[:, :, None]
    paint = (
        paint * (1 - metal[:, :, None] * 0.8)
        + colour("gunmetal") * metal[:, :, None] * 0.8
    )
    paint *= (1 - ridge * 0.34)[:, :, None]
    source = image.astype(np.float32)
    intensity = luma.astype(np.float32)
    macro = cv2.GaussianBlur(intensity, (0, 0), 13 * density)
    ink = np.clip((intensity + 25) / (macro + 25), 0.40, 1.15)
    tone = np.clip((macro + 45) / 165, 0.69, 1.15)
    saturation = np.max(source, axis=2) - np.min(source, axis=2)
    polished = np.clip((intensity - 105) / 97, 0, 1) * np.clip(
        (105 - saturation) / 90, 0, 1
    )
    tint = (
        paint * (1 - polished[:, :, None] * 0.30)
        + colour("titanium") * polished[:, :, None] * 0.30
    )
    paint = np.clip(tint * (tone * 0.92 * ink)[:, :, None], 0, 255)
    if index == 0:
        finish = np.clip(0.94 + 0.12 * (tone - 1) + 0.18 * (ink - 1), 0.78, 1.01)
        for name, pigment, _, outline, *_ in panel["armour"]():
            if not any(
                part in name.lower()
                for part in ("shoulder casting", "upper-arm shell", "bracer")
            ):
                continue
            vertices = np.array(outline, dtype=float)
            vertices[:, 0] = (CX + (vertices[:, 0] - 220) * SCALE * 250 / 437) * density
            vertices[:, 1] = (
                FLOOR + (vertices[:, 1] - 791) * SCALE * 420 / 731
            ) * density
            coverage = np.zeros(mask.shape, np.uint8)
            cv2.fillPoly(
                coverage, [vertices.round().astype(np.int32)], 255, cv2.LINE_AA
            )
            weight = cv2.GaussianBlur(coverage, (0, 0), 0.75 * density) * (0.68 / 255)
            paint += (colour(pigment) * finish[:, :, None] - paint) * weight[:, :, None]
    elif index in (2, 3):
        upper = np.clip((y - 176) / 35, 0, 1) * np.clip((520 - y) / 40, 0, 1)
        enamel = (
            colour("red") * (1 - gold[:, :, None]) + colour("gold") * gold[:, :, None]
        )
        paint += (enamel - paint) * (0.30 * upper[:, :, None])
    fade = np.clip((974 - y) / 12, 0, 1)[:, :, None]
    return np.uint8(np.clip(image * (1 - fade) + paint * fade, 0, 255))


def solid_projection(points, faces, axis):
    mask = np.zeros(SIZE[::-1], np.uint8)
    vertices = np.rint(projected(points, axis)).astype(np.int32)
    for f in faces:
        cv2.fillConvexPoly(mask, vertices[f], 1)
    return mask


def runs(row):
    strip = ndimage.binary_closing(row, structure=np.ones(5))
    edges = np.flatnonzero(np.diff(np.r_[0, strip, 0].astype(np.int8))).reshape(-1, 2)
    return [(lo, hi) for lo, hi in edges if hi - lo >= 4]


def maps(source, target, split):
    xs = np.arange(SIZE[0])
    output = np.zeros((SIZE[1], SIZE[0]), dtype=np.float32)
    valid = []
    for row in range(SIZE[1]):
        src, dst = runs(source[row]), runs(target[row])
        if not src or not dst:
            continue
        knots = lambda ranges: np.array(ranges).reshape(-1)
        if split and len(src) == len(dst):
            a, b = knots(src), knots(dst)
        else:
            a, b = [src[0][0], src[-1][1]], [dst[0][0], dst[-1][1]]
        output[row] = np.interp(xs, a, b) - xs
        valid.append(row)
    for row in set(range(SIZE[1])) - set(valid):
        nearest = valid[np.argmin(np.abs(np.asarray(valid) - row))]
        output[row] = output[nearest]
    return ndimage.gaussian_filter(output, (6, 3))


def fit_front_sections(points, uv):
    x, _, z = points.T
    py = 791 - z * 731 / 420
    ys = np.array([145, 160, 180, 197, 219, 237, 259, 277, 295, 316, 338, 346])
    bounds = np.array(
        [
            [124, 152, 150, 258, 258, 282],
            [119, 148, 147, 259, 260, 289],
            [117, 147, 149, 264, 264, 293],
            [114, 145, 153, 257, 270, 297],
            [111, 140, 158, 254, 273, 300],
            [106, 134, 163, 251, 279, 308],
            [101, 133, 166, 250, 285, 317],
            [100, 128, 164, 253, 290, 318],
            [97, 121, 158, 256, 294, 320],
            [96, 119, 153, 264, 291, 320],
            [100, 122, 149, 269, 293, 316],
            [105, 117, 148, 271, 301, 310],
        ]
    )
    sep = np.interp(z, [250, 267, 309, 331, 352, 372], [53, 44, 38, 36, 37, 36])
    side = np.where(x < (-10 - sep), 0, np.where(x > (-10 + sep), 2, 1))
    output = uv[:, 0].copy()
    for i in range(3):
        mask = (side == i) & (py >= 143) & (py <= 344)
        order = np.arange(142, 346, 2)
        rows = []
        lo = []
        hi = []
        for y in order:
            local = x[mask & (abs(py - y) < 2.9)]
            if len(local) > 6:
                rows.append(y)
                lo.append(np.quantile(local, 0.012))
                hi.append(np.quantile(local, 0.988))
        if len(rows) < 2:
            continue
        xmin = np.interp(py[mask], rows, ndimage.gaussian_filter1d(lo, 1.5))
        xmax = np.interp(py[mask], rows, ndimage.gaussian_filter1d(hi, 1.5))
        unit = np.clip((x[mask] - xmin) / np.maximum(1, xmax - xmin), 0.034, 0.966)
        px = (
            np.interp(py[mask], ys, bounds[:, 2 * i]) * (1 - unit)
            + np.interp(py[mask], ys, bounds[:, 2 * i + 1]) * unit
        )
        new = 450 + (px - 220) * 3 / (437 / 250)
        weight = np.minimum(
            np.clip((py[mask] - 143) / 17, 0, 1), np.clip((344 - py[mask]) / 9, 0, 1)
        )
        output[mask] += np.clip(new - uv[mask, 0], -25, 25) * weight * 0.76
    return output


def vambrace_enamel(work):
    size = 1024
    paint = np.zeros((size, size, 3), np.uint8)
    paint[:] = (46, 29, 153)

    def panel(curves, fill):
        start, *segments = curves
        start = np.asarray(start, dtype=float)
        outline = [start]
        t = np.linspace(0, 1, 36)[:, None]
        for segment in segments:
            b, c, end = np.asarray(segment, dtype=float)
            points = (
                (1 - t) ** 3 * start
                + 3 * (1 - t) ** 2 * t * b
                + 3 * (1 - t) * t**2 * c
                + t**3 * end
            )
            outline.extend(points)
            start = end
        vertices = np.asarray(outline).round().astype(np.int32)
        cv2.fillPoly(paint, [vertices], fill, cv2.LINE_AA)

    panel(
        [
            (318, 18),
            [(384, 8), (508, 90), (551, 220)],
            [(569, 338), (528, 497), (460, 627)],
            [(420, 712), (390, 771), (359, 772)],
            [(309, 760), (240, 674), (210, 614)],
            [(229, 453), (237, 252), (261, 96)],
            [(276, 47), (291, 23), (318, 18)],
        ],
        (48, 43, 60),
    )
    panel(
        [
            (317, 22),
            [(383, 14), (498, 99), (542, 228)],
            [(556, 348), (512, 492), (450, 617)],
            [(411, 695), (385, 746), (356, 750)],
            [(308, 730), (256, 663), (224, 610)],
            [(245, 467), (249, 258), (274, 104)],
            [(287, 62), (300, 33), (317, 22)],
        ],
        (106, 115, 125),
    )
    panel(
        [
            (320, 22),
            [(389, 28), (495, 108), (532, 228)],
            [(545, 349), (502, 497), (437, 612)],
            [(403, 672), (376, 713), (357, 718)],
            [(323, 706), (281, 656), (249, 598)],
            [(265, 452), (260, 244), (283, 103)],
            [(292, 62), (305, 35), (320, 22)],
        ],
        (48, 31, 165),
    )
    panel(
        [
            (55, 172),
            [(138, 240), (153, 331), (153, 448)],
            [(150, 609), (122, 713), (121, 833)],
            [(152, 874), (174, 953), (167, 1024)],
            [(158, 968), (139, 906), (110, 842)],
            [(107, 715), (136, 554), (140, 432)],
            [(139, 327), (124, 244), (55, 172)],
        ],
        (40, 26, 92),
    )
    panel(
        [
            (621, 185),
            [(656, 195), (725, 257), (766, 313)],
            [(808, 407), (823, 518), (812, 640)],
            [(796, 751), (738, 869), (691, 932)],
            [(733, 844), (779, 734), (793, 630)],
            [(807, 501), (786, 403), (754, 321)],
            [(714, 266), (669, 220), (621, 185)],
        ],
        (40, 26, 110),
    )
    t = np.linspace(0, 1, size)[:, None]
    shade = (
        0.80
        - 0.28 * np.exp(-(((t - 0.992) / 0.095) ** 2))
        - 0.23 * np.exp(-(((t - 0.004) / 0.065) ** 2))
    )
    paint = np.uint8(paint * shade[:, :, None])
    cv2.imwrite(str(work / "vambrace-enamel.png"), paint)


def main(work):
    cv2.setNumThreads(3)
    vambrace_enamel(work)
    original = np.load(work / "input.npz")
    points, faces = original["points"].astype(float) * 1000, original["faces"]
    points[:, :2] -= (points.max(axis=0)[:2] + points.min(axis=0)[:2]) / 2
    yaw = np.radians(
        np.interp(
            points[:, 2],
            [0, 52, 76, 98, 136, 153, 168, 191, 215, 230, 260],
            [8, 8, 14, 17, 13, 13, 18, 18, 12, 13, 14],
        )
    )
    x, y = points[:, :2].copy().T
    points[:, 0] = x * np.cos(yaw) - y * np.sin(yaw)
    points[:, 1] = x * np.sin(yaw) + y * np.cos(yaw)
    points[:, :2] *= [250 / np.ptp(points[:, 0]), 180 / np.ptp(points[:, 1])]
    points[:, 2] = np.interp(
        points[:, 2], [0, 72, 161, 196, 234, 260], [0, 113.2, 258, 317, 379.3, 420]
    )
    views = camera_views()
    for index, axis in [(0, 0), (2, 1)]:
        orig = solid_projection(points, faces, axis)
        fields = maps(orig, views[index][1], False)
        fields = ndimage.gaussian_filter(fields, (27, 10))
        uv = projected(points, axis)
        adjustment = ndimage.map_coordinates(
            fields, [uv[:, 1], uv[:, 0]], order=1, mode="nearest"
        )
        limit, amount = (15, 0.68) if axis == 0 else (24, 0.78)
        points[:, axis] += np.clip(adjustment / SCALE, -limit, limit) * amount
    points[:, :2] -= (points.max(axis=0)[:2] + points.min(axis=0)[:2]) / 2
    points[:, :2] *= [250 / np.ptp(points[:, 0]), 180 / np.ptp(points[:, 1])]
    x, y, z = points.T
    side = np.sign(x + 7)
    separate = np.clip((np.abs(x + 7) - 35) / 10, 0, 1)
    curl = (
        separate * np.clip((282 - z) / 26, 0, 1) ** 1.7 * np.clip((z - 243) / 10, 0, 1)
    )
    points[:, 0] += side * 8.0 * curl
    points[:, 1] += (y + 17) * 0.20 * curl
    points[:, 2] += np.where(side < 0, 4.2, 1.6) * curl
    from scipy.spatial import cKDTree

    welded, duplicate = np.unique(np.round(points, 3), axis=0, return_inverse=True)
    neighbors = cKDTree(welded)
    dist, knn = neighbors.query(welded, k=21, distance_upper_bound=5.1)
    weights = np.exp(-((dist / 2.4) ** 2))
    weights /= weights.sum(axis=1, keepdims=True)
    knn = np.minimum(knn, len(welded) - 1)
    shape = welded.copy()
    region = np.clip((shape[:, 2] - 114) / 8, 0, 1) * np.clip(
        (419.8 - shape[:, 2]) / 3, 0, 1
    )
    for _ in range(4):
        average = np.einsum("ij,ijk->ik", weights, shape[knn])
        shape += (average - shape) * (0.49 * region[:, None])
    points += shape[duplicate] - welded[duplicate]
    np.save(work / "points.npy", points.astype("f") * 0.001)
    for index, (image, region) in enumerate(views):
        axis = 0 if index < 2 else 1
        rendered = solid_projection(points, faces, axis)
        field = ndimage.gaussian_filter(maps(rendered, region, False), (17, 10))
        if axis == 0:
            correction = ndimage.gaussian_filter(
                maps(rendered, region, True) - field, (17, 15)
            )
            field += np.clip(correction, -14, 14)
        uv = projected(points, axis)
        uv[:, 0] += ndimage.map_coordinates(
            field, [uv[:, 1], uv[:, 0]], order=1, mode="nearest"
        )
        if index == 0:
            uv[:, 0] = fit_front_sections(points, uv)
        uv /= SIZE
        uv[:, 1] = 1 - uv[:, 1]
        np.save(work / f"camera-{index}.npy", uv.astype("f"))
        texture_mask = cv2.resize(
            region, image.shape[1::-1], interpolation=cv2.INTER_NEAREST
        )
        nearest = ndimage.distance_transform_edt(
            ~texture_mask.astype(bool), return_distances=False, return_indices=True
        )
        padded = enamel_pigments(image, region, index)[tuple(nearest)]
        cv2.imwrite(
            str(work / f"camera-{index}.jpg"), padded, [cv2.IMWRITE_JPEG_QUALITY, 96]
        )
        edges = cv2.Canny(region * 255, 40, 100) > 0
        contour = cv2.resize(image, SIZE)
        contour[edges] = (255, 200, 0)
        cv2.imwrite(
            str(work / f"camera-{index}-mask.jpg"), cv2.resize(contour, (400, 604))
        )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
