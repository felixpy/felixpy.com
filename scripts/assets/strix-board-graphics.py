import math
import random
import runpy
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


output = Path(__file__).resolve().parents[2] / ".review/atelier/pc-components/artwork"
output.mkdir(parents=True, exist_ok=True)
scale = 6
armor_graphics = runpy.run_path(str(Path(__file__).with_name("strix-armor.py")))


def font(size, bold=False):
    for path in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, max(4, round(size * scale)))
        except OSError:
            pass
    return ImageFont.load_default()


def traces(draw, locations, dark):
    for x, y, count, direction, length in locations:
        for i in range(count):
            u, v = x + i * 0.49, y - i * 0.18
            run = 3.6 + i % 6 * 0.46
            end = (u + 6.7 * direction, v + run + length)
            draw.line(
                [
                    (round(a * scale), round(b * scale))
                    for a, b in [
                        (u, v),
                        (u, v + run),
                        (u + 6.7 * direction, v + run + 6.7),
                        end,
                    ]
                ],
                fill=dark,
                width=1,
            )
            u, v = end[0] * scale, end[1] * scale
            draw.ellipse((u - 1.1, v - 1.1, u + 1.1, v + 1.1), fill=dark)


def silkscreen(draw, text, x, y, size, color, bold=False):
    draw.text(
        (round(x * scale), round(y * scale)), text, fill=color, font=font(size, bold)
    )


def front_frost_print(draw):
    rng = random.Random(89026)
    fields = [(96, 91, 41, 94), (153, 125, 33, 50), (240, 112, 27, 100),
              (160, 181, 78, 29), (21, 207, 23, 61), (103, 290, 91, 23)]
    for y in range(2, 305, 4):
        for x in range(2, 244, 4):
            u = x + rng.uniform(-1.3, 1.3)
            v = y + rng.uniform(-1.3, 1.3)
            strength = max(1 - ((u-cx)/rx)**2 - ((v-cy)/ry)**2 for cx,cy,rx,ry in fields)
            if rng.random() > 0.88 * strength:
                continue
            radius = rng.uniform(0.65, 2.18)
            angle = rng.uniform(0, math.tau)
            vertices = []
            for i in range(3):
                orientation = angle + i * math.tau / 3 + rng.uniform(-0.19, 0.19)
                size = radius * rng.uniform(0.8, 1.25)
                vertices.append(((u + size*math.cos(orientation))*scale, (v + size*math.sin(orientation))*scale))
            pigment = rng.choice(("#cacccd", "#d7d8d8", "#dedfdd"))
            if rng.random() < 0.55:
                draw.line(vertices + vertices[:1], pigment, width=1)
            else:
                draw.polygon(vertices, fill=pigment)


def soldermask(back):
    rng = random.Random(2014 if back else 8920)
    image = Image.new(
        "RGB", (244 * scale, 305 * scale), "#707376" if back else "#b8babc"
    )
    draw = ImageDraw.Draw(image)
    networks = [
        (11, 16, 39, 1, 40),
        (49, 43, 26, 1, 20),
        (94, 25, 33, 1, 22),
        (138, 29, 22, -1, 30),
        (150, 85, 26, 1, 19),
        (183, 155, 31, 1, 15),
        (12, 182, 38, 1, 22),
        (147, 192, 38, -1, 28),
        (124, 254, 44, -1, 23),
        (80, 130, 28, 1, 20),
        (23, 228, 32, 1, 18),
        (199, 221, 36, -1, 47),
    ]
    if not back:
        networks.extend([(99, 42, 20, -1, 17), (149, 71, 24, 1, 23),
                         (169, 110, 22, -1, 26), (214, 98, 14, 1, 16),
                         (197, 168, 18, -1, 18), (82, 192, 25, -1, 15)])
    traces(draw, networks, "#747977" if back else "#a7abad")
    for _ in range(2250 if back else 1150):
        x, y = (rng.uniform(2, d - 2) * scale for d in (244, 305))
        r = rng.uniform(0.11, 0.33) * scale
        draw.ellipse(
            (x - r, y - r, x + r, y + r), fill="#bcc0bb" if back else "#9ca29e"
        )
        if r > 1.25:
            draw.ellipse((x - 0.52, y - 0.52, x + 0.52, y + 0.52), fill="#717671")
    if back:
        reverse = Path(__file__).with_name("strix-rear-silkscreen.py")
        runpy.run_path(str(reverse))["reverse_print"](image)
    else:
        front_frost_print(draw)
        for x, y, w, h, count in [
            (8, 60, 48, 95, 180),
            (86, 121, 80, 24, 125),
            (156, 80, 25, 65, 105),
            (223, 30, 12, 120, 53),
            (17, 170, 212, 29, 184),
            (8, 211, 226, 80, 215),
            (4, 291, 234, 10, 100),
        ]:
            for i in range(count):
                u, v = rng.uniform(x, x + w) * scale, rng.uniform(y, y + h) * scale
                a, b = rng.uniform(0.45, 1.35) * scale, 0.53 * scale
                if i % 2:
                    a, b = b, a
                draw.rectangle((u - 1, v - 1, u + a + 1, v + b + 1), fill="#969992")
                draw.rectangle(
                    (u, v, u + a, v + b),
                    fill=rng.choice(["#545951", "#77756b", "#98a198"]),
                )
        for label, x, y, s in [
            ("CPU_OPT", 165, 8, 1.25),
            ("CPU_FAN", 180, 8, 1.25),
            ("AIO_PUMP", 195, 8, 1.25),
            ("ATX_PWR", 223, 71, 1.25),
            ("Q-LED", 223, 23.5, 1.35),
            ("U32G2X2", 223, 145, 1.45),
            ("ADD_GEN2", 49, 293, 1.55),
            ("M.2_1", 65, 149, 1.25),
            ("PCIEX16(G5)", 81, 174, 1.27),
            ("SUPREMEFX", 6, 266, 1.48),
            ("F_PANEL", 210, 299, 1.35),
        ]:
            silkscreen(draw, label, x, y, s, "#373f3c", True)
    for x in [187, 196.7, 206.4, 216.1]:
        if back:
            x = 244 - x
        for row in range(138):
            for side in (-1, 1):
                u, v = (x + side * 2.05) * scale, (16 + row * 0.936) * scale
                draw.ellipse(
                    (u - 1.2, v - 1.1, u + 1.2, v + 1.1),
                    fill="#c4c8bc" if back else "#8c9386",
                )
    if not back:
        armor_graphics["front_silkscreen"](image)
    image.save(output / ("rear.png" if back else "face.png"), optimize=True)


if sys.argv[1:2] == ["--contact-map"]:
    size = tuple(map(int, sys.argv[2:4]))
    contact = Image.frombytes("L", size, sys.stdin.buffer.read()).filter(ImageFilter.GaussianBlur(0.6))
    contact.convert("RGB").save(output / "face-occlusion.png", optimize=True)
    maps = ["face-occlusion"]
else:
    soldermask(False)
    soldermask(True)
    armor_graphics["engrave_heatsinks"](output)
    runpy.run_path(str(Path(__file__).with_name("strix-io-inlay.py")))["render"](output)
    maps = ["face", "rear", "coolers", "inlay", "io-emission", "io-fascia", "armor-finish"]
for name in maps:
    with Image.open(output / f"{name}.png") as image:
        image.save(output / f"{name}.webp", lossless=True, method=6)
