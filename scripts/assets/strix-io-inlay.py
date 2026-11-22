import json
import math
from pathlib import Path


fascia = [
    (20, 944), (20, 25), (23, 18), (117, 18), (123, 22),
    (422, 318), (426, 325), (426, 862), (422, 873),
    (405, 889), (174, 889), (122, 940), (115, 944),
]
inset = [
    (60, 440), (63, 65), (64, 60), (68, 56), (74, 55), (97, 55),
    (105, 57), (110, 62), (372, 321), (377, 328), (377, 350),
    (380, 358), (407, 386), (409, 391), (407, 577), (406, 583),
    (376, 610), (374, 615), (373, 737), (371, 742), (366, 745),
    (360, 745), (355, 743), (64, 453), (61, 448),
]
fluted_heel = [(29, 703), (207, 883), (173, 889), (117, 943), (29, 943)]
fascia_area = (18, 16, 428, 946)
inset_area = (58, 53, 411, 748)


def board_point(x, y):
    return (-9.8 + (x - 20) * 68.8 / 406, -13 + (y - 18) * 170 / 926)


def board_bounds(area):
    x0, y0 = board_point(*area[:2])
    x1, y1 = board_point(*area[2:])
    return (x0, y0, x1 - x0, y1 - y0)


def diagonal_strip(polygon, lower, upper):
    def clip(points, limit, side):
        clipped = []
        for a, b in zip(points, points[1:] + points[:1]):
            da = (a[1] - a[0] - limit) * side
            db = (b[1] - b[0] - limit) * side
            if da >= 0:
                clipped.append(a)
            if (da < 0) != (db < 0):
                t = da / (da - db)
                clipped.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        return clipped

    return clip(clip(polygon, lower, 1), upper, -1)


def fascia_print():
    from PIL import Image, ImageDraw, ImageFont

    size = 2
    face = Image.new("RGB", (547 * size, 965 * size), "#d8d9d8")
    draw = ImageDraw.Draw(face)

    def line(points, fill, width):
        draw.line([(x * size, y * size) for x, y in points], fill=fill, width=round(width * size))

    def polygon(points, fill):
        draw.polygon([(x * size, y * size) for x, y in points], fill=fill)

    def stamp(message, start, end, height, shade, bold=False):
        for name in (("arialnb.ttf" if bold else "arialn.ttf"), "arial.ttf", "DejaVuSans.ttf"):
            try:
                font = ImageFont.truetype(name, round(height * size))
                break
            except OSError:
                continue
        else:
            font = ImageFont.load_default(size=round(height * size))
        mask = font.getmask(message)
        box = font.getbbox(message)
        stamp = Image.frombytes("L", mask.size, bytes(mask)).crop((0, 0, box[2] - box[0], box[3] - box[1]))
        dx, dy = end[0] - start[0], end[1] - start[1]
        stamp = stamp.resize((round(math.hypot(dx, dy) * size), stamp.height), Image.Resampling.LANCZOS)
        stamp = stamp.rotate(-math.degrees(math.atan2(dy, dx)), Image.Resampling.BICUBIC, expand=True)
        center = ((start[0] + end[0]) * size / 2, (start[1] + end[1]) * size / 2)
        face.paste(shade, (round(center[0] - stamp.width / 2), round(center[1] - stamp.height / 2)), stamp)

    line([(25, 33), (25, 942), (114, 942), (172, 885), (400, 885), (421, 865)], "#eeefec", 2.8)
    line([(30, 482), (406, 850), (406, 603)], "#bfc2c2", 1.6)
    line([(31, 477), (405, 843)], "#f4f4ef", 1.6)
    stamp("REPUBLIC OF GAMERS   ·   FOR THOSE WHO DARE   ·   JOIN THE", (43, 462), (43, 52), 14.3, "#f1f1eb", True)
    stamp("REPUBLIC", (49, 38), (117, 38), 14, "#f1f1eb", True)
    stamp("·   REPUBLIC OF GAMERS   ·   FOR THOSE WHO DARE", (127, 60), (391, 324), 14.5, "#f0f1ed", True)
    stamp("REPUBLIC OF GAMERS", (388, 628), (379, 778), 14, "#f0f1ed", True)
    stamp("FOR THOSE WHO DARE   ·   JOIN THE REPUBLIC   ·", (341, 753), (81, 493), 14, "#f2f2ed", True)
    polygon([(38, 553), (140, 655), (140, 692), (38, 589)], "#74787a")
    stamp("ROG", (49, 586), (73, 610), 14.6, "#eeefee", True)
    stamp("#", (112, 650), (124, 662), 14.5, "#eeefee", True)
    for i in range(16):
        x = 111 + i * 16.5
        y = 553 + i * 16.5
        line([(x, y), (x, y + 24)], "#c0c2c1", 1.7)
    polygon([(157, 693), (165, 703), (180, 705), (194, 710), (185, 710), (172, 706), (163, 706)], "#62676a")
    polygon([(164, 708), (173, 709), (189, 713), (177, 717), (170, 716)], "#62676a")
    stamp("R:REPUBLIC, O:OF, G:GAMERS", (192, 729), (336, 865), 15.5, "#585c60", True)
    for y in range(652, 871, 13):
        left = max(36, y - 645 + 36 - 32)
        right = min(261, y - 645 + 36)
        if right - left > 3:
            fill = "#696d71" if y < 763 else "#94989a"
            line([(left, y), (right, y)], fill, 3.2)
    return face.crop(tuple(v * size for v in fascia_area)).resize((448, 1024), Image.Resampling.LANCZOS)


def render(output):
    from PIL import Image, ImageDraw

    source = Path(__file__).with_name("strix-prints") / "io-apertures.json"
    mask = Image.new("L", (1094, 1930))
    draw = ImageDraw.Draw(mask)
    for hole, polygon in json.loads(source.read_text()):
        draw.polygon(polygon, fill=0 if hole else 255)
    mask = mask.crop(tuple(v * 2 for v in inset_area)).resize((448, 880), Image.Resampling.LANCZOS)
    color = Image.new("RGB", mask.size)
    physical = Image.new("RGB", mask.size, "#101a21")
    emission = Image.new("RGB", mask.size)
    ramp = [(18, 228, 225), (33, 206, 240), (55, 139, 246), (32, 83, 233)]
    rows = []
    for y in range(mask.height):
        for x in range(mask.width):
            t = min(3.0, max(0.0, 3.9 * (0.54 * x / mask.width + 0.68 * y / mask.height) - 0.7))
            i = min(2, int(t))
            rows.append(tuple(round(a + (b - a) * (t - i)) for a, b in zip(ramp[i], ramp[i + 1])))
    color.putdata(rows)
    emission.paste(color, mask=mask)
    physical.paste("#4f6269", (0, 0, *mask.size), mask)
    physical.save(output / "inlay.png", optimize=True)
    emission.save(output / "io-emission.png", optimize=True)
    fascia_print().save(output / "io-fascia.png", optimize=True)
