import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

WIDTH, HEIGHT, SCALE = 850, 225, 2
FAMILY = {
    "R": ("1111", "1001", "1110", "1010", "1001"),
    "O": ("1111", "1001", "1001", "1001", "1111"),
    "G": ("1111", "1000", "1011", "1001", "1111"),
    "A": ("0110", "1001", "1111", "1001", "1001"),
    "B": ("1110", "1001", "1110", "1001", "1110"),
    "C": ("1111", "1000", "1000", "1000", "1111"),
    "E": ("1111", "1000", "1110", "1000", "1111"),
    "F": ("1111", "1000", "1110", "1000", "1000"),
    "I": ("11", "11", "11", "11", "11"),
    "L": ("1000", "1000", "1000", "1000", "1111"),
    "M": ("10001", "11011", "10101", "10001", "10001"),
    "P": ("1110", "1001", "1110", "1000", "1000"),
    "S": ("1111", "1000", "1111", "0001", "1111"),
    "U": ("1001", "1001", "1001", "1001", "1111"),
}


def crest(polygon, x, y, width, value):
    paths = [
        [
            (106, 181),
            ((131, 207), (162, 232), (208, 263)),
            ((166, 249), (139, 242), (126, 222)),
        ],
        [
            (176, 194),
            ((202, 207), (233, 226), (257, 226)),
            ((288, 200), (346, 139), (409, 98)),
            ((470, 72), (541, 66), (596, 67)),
            ((477, 104), (371, 167), (270, 250)),
            ((246, 272), (261, 288), (299, 321)),
            ((249, 294), (213, 249), (176, 194)),
        ],
        [
            (273, 271),
            ((356, 217), (461, 148), (566, 121)),
            ((587, 115), (609, 111), (625, 110)),
            ((621, 123), (617, 132), (608, 137)),
            ((512, 177), (428, 216), (332, 268)),
            ((383, 285), (432, 297), (463, 284)),
            ((489, 270), (516, 234), (524, 210)),
            ((487, 224), (457, 232), (426, 237)),
            ((479, 209), (546, 179), (604, 156)),
            ((580, 212), (553, 268), (512, 304)),
            ((484, 337), (368, 314), (273, 271)),
        ],
    ]
    for path in paths:
        curve = [path[0]]
        for c1, c2, end in path[1:]:
            a = curve[-1]
            for j in range(1, 9):
                t = j / 8
                curve.append(
                    tuple(
                        (1 - t) ** 3 * a[k]
                        + 3 * t * (1 - t) ** 2 * c1[k]
                        + 3 * t * t * (1 - t) * c2[k]
                        + t**3 * end[k]
                        for k in (0, 1)
                    )
                )
        polygon(
            [
                (x + (u - 106) / 519 * width, y + (v - 67) / 519 * width)
                for u, v in curve
            ],
            value,
        )


def artwork():
    mask = Image.new("L", (WIDTH * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(mask)

    def polygon(points, value):
        draw.polygon([(round(x * SCALE), round(y * SCALE)) for x, y in points], value)

    def microtype(x, y, pitch, value):
        for letter in "ROG":
            for row, bits in enumerate(FAMILY[letter]):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        u, v = x + column * pitch, y + row * pitch
                        polygon(
                            [
                                (u, v),
                                (u + pitch, v),
                                (u + pitch, v + pitch),
                                (u, v + pitch),
                            ],
                            value,
                        )
            x += 5.7 * pitch

    for row in range(13):
        y = 30 + row * 14.8
        x = 13 + (row % 3) * 8
        while x < WIDTH:
            weight = (1 + math.cos(x / 52 - row * 0.28)) / 2
            pitch = 0.68 + 0.76 * weight
            microtype(x, y, pitch, round(29 + 89 * weight))
            x += pitch * 18.6 + 2.8

    strokes = [
        [(0, 0), (241, 0), (143, 98), (96, 98), (170, 20), (12, 20)],
        [
            (250, 0),
            (359, 0),
            (305, 54),
            (268, 54),
            (275, 99),
            (225, 99),
            (218, 57),
            (233, 38),
            (280, 38),
            (293, 21),
            (232, 21),
        ],
        [(377, 0), (421, 0), (355, 78), (405, 78), (386, 99), (316, 99), (304, 81)],
        [(435, 0), (542, 0), (447, 99), (399, 99), (473, 20), (416, 20)],
        [(554, 0), (606, 0), (528, 79), (591, 79), (571, 99), (458, 99)],
        [(630, 0), (732, 0), (702, 21), (607, 21)],
        [(635, 43), (676, 43), (640, 78), (785, 78), (806, 99), (586, 99)],
    ]
    for points in strokes:
        polygon([(125 + x * 0.393, 86 + y * 0.400) for x, y in points], 246)

    crest(polygon, 525, 86, 175, 255)
    for path in [
        [(37, 44), (146, 151)],
        [(218, 152), (424, 152), (485, 214), (726, 214), (815, 124)],
        [(51, 45), (408, 45), (424, 57), (792, 57)],
    ]:
        draw.line([(int(x * SCALE), int(y * SCALE)) for x, y in path], 143, 2 * SCALE)
    ink = Image.new("RGB", mask.size, (68, 67, 73))
    draw = ImageDraw.Draw(ink)
    color = (31, 31, 35)
    crest(polygon, 490, 27, 25, color)
    x = 522
    for char in "REPUBLIC OF GAMERS":
        if char == " ":
            x += 11
            continue
        bitmap = FAMILY[char]
        for row, bits in enumerate(bitmap):
            for col, bit in enumerate(bits):
                if bit == "1":
                    u, v = x + col * 3.55 + (4 - row) * 0.84, 27 + row * 2.45
                    polygon(
                        [
                            (u, v),
                            (u + 3.67, v),
                            (u + 2.86, v + 2.56),
                            (u - 0.80, v + 2.56),
                        ],
                        color,
                    )
        x += 3.55 * (len(bitmap[0]) + 1)
    for points in strokes:
        polygon([(80 + x * 0.6, 141 + y * 0.52) for x, y in points], (171, 173, 178))
    return mask, ink


def save(directory):
    directory.mkdir(parents=True, exist_ok=True)
    mask, ink = artwork()
    colors = [
        (4, 233, 250),
        (16, 209, 254),
        (103, 88, 252),
        (202, 33, 243),
        (254, 37, 219),
    ]
    strip = Image.new("RGB", (mask.width, 1))
    for x in range(strip.width):
        t = x * (len(colors) - 1) / (strip.width - 1)
        a = min(int(t), len(colors) - 2)
        mix = t - a
        strip.putpixel(
            (x, 0),
            tuple(round(c + (d - c) * mix) for c, d in zip(colors[a], colors[a + 1])),
        )
    size = mask.size
    emission = Image.composite(strip.resize(size), Image.new("RGB", size), mask)
    base = Image.composite(
        Image.new("RGB", size, (61, 64, 73)), Image.new("RGB", size, (18, 19, 28)), mask
    )
    for name, image in [
        ("etched-spectrum", emission),
        ("unlit-acrylic", base),
        ("rail-and-deck", ink),
    ]:
        image.save(directory / (name + ".png"), optimize=True)


if __name__ == "__main__":
    save(Path(sys.argv[1]))
