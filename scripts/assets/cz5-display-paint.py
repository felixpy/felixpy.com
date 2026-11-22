from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / ".review/atelier/cz5-display"
TARGET.mkdir(parents=True, exist_ok=True)
WHITE = "#edece4"
BLUE = "#233953"
RED = "#a82937"


def label(draw, at, value, size, ink, *, cjk=False, stretch=2.14):
    face = "msyhbd.ttc" if cjk else "arialbd.ttf"
    font = ImageFont.truetype(str(Path("C:/Windows/Fonts") / face), size)
    bbox = font.getbbox(value)
    mask = Image.new("L", (bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4))
    ImageDraw.Draw(mask).text((2 - bbox[0], 2 - bbox[1]), value, fill=255, font=font)
    mask = mask.resize(
        (round(mask.width * stretch), mask.height), Image.Resampling.LANCZOS
    )
    draw.bitmap(
        (round(at[0] - mask.width / 2), round(at[1] - mask.height / 2)), mask, fill=ink
    )


def body_art():
    width, height = 1024, 1536
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    cx = width // 2

    def y(mm):
        return round((178 - mm) / 270 * height)

    def line(mm, thick, color):
        draw.rectangle((0, y(mm), width, y(mm) + thick), fill=color)

    for level in [151, 143, 137, 128, 118, 97, 79, 63, 37, 9, -67, -80]:
        line(level, 1, "#b4bab8")
    line(134, 2, "#975752")
    draw.ellipse((cx - 40, y(155) - 21, cx + 40, y(155) + 21), fill=BLUE)
    draw.ellipse((cx - 47, y(155) - 21, cx + 18, y(155) + 18), fill=WHITE)
    for dx, dy in [(-8, -6), (0, 3)]:
        draw.ellipse(
            (cx + dx - 4, y(155) + dy, cx + dx + 5, y(155) + dy + 4), fill=BLUE
        )
    label(draw, (cx, y(149)), "中国探月", 22, BLUE, cjk=True)
    label(draw, (cx, y(146)), "C L E P", 12, BLUE)
    cy = y(124)
    draw.ellipse((cx - 33, cy - 17, cx + 33, cy + 17), outline=BLUE, width=4)
    draw.polygon(
        [
            (cx - 22, cy + 10),
            (cx + 1, cy - 13),
            (cx + 22, cy + 11),
            (cx + 2, cy - 2),
            (cx - 3, cy + 6),
        ],
        fill=BLUE,
    )
    for idx, ch in enumerate("中国航天"):
        label(draw, (cx, y(114 - idx * 8.5)), ch, 44, "#182c43", cjk=True)
    cy = y(72)
    draw.ellipse((cx - 35, cy - 17, cx + 35, cy + 17), fill=RED)
    label(draw, (cx, cy - 1), "5", 35, WHITE)
    label(draw, (cx, cy + 29), "LONG MARCH", 12, "#4b5a65")
    label(draw, (cx, y(-71)), "Y8", 25, "#273642")
    for x in (width // 4, width * 3 // 4):
        for mm in (146, 137, 88, 76):
            yy = y(mm)
            draw.rounded_rectangle(
                (x - 3, yy - 5, x + 3, yy + 5), radius=2, fill="#87918e"
            )
    img.save(TARGET / "cz5-body-paint.png", optimize=True)


def pod_art():
    w, h = 512, 1024
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    for y in [162, 229, 602, 823, 900]:
        draw.line((0, y, w, y), fill="#bbc0b9", width=1)
    for x in (w // 4, w * 3 // 4):
        draw.line((x, 222, x, 914), fill="#bec0b6", width=2)
        draw.line((x + 4, 222, x + 4, 914), fill="#faf9f1", width=2)
    x = w // 2
    for lo, hi in [(227, 565), (646, 887)]:
        for row, y in enumerate(range(lo, hi - 12, 13)):
            left = x - 19 + row % 2 * 19
            draw.rectangle((left, y, left + 18, y + 12), fill=RED)
    lettering = Image.new("RGB", (88, 36), WHITE)
    label(ImageDraw.Draw(lettering), (44, 18), "CZ-5", 34, "#394345", stretch=1)
    vertical = lettering.rotate(-90, expand=True).resize(
        (40, 59), Image.Resampling.LANCZOS
    )
    img.paste(vertical, (x - 20, 577))
    draw.rectangle((0, 889, w, 921), fill="#b5b9b7")
    draw.line((0, 891, w, 891), fill="#e5e7df", width=2)
    for x in range(0, w, 24):
        draw.line((x, 927, x, 950), fill="#bbc2bb", width=1)
    img.save(TARGET / "cz5-pod-paint.png", optimize=True)


if __name__ == "__main__":
    body_art()
    pod_art()
    plaque = Image.new("RGB", (624, 72), "#31383c")
    label(
        ImageDraw.Draw(plaque),
        (312, 36),
        "CZ-5 Y8   /   CHANG’E 6",
        41,
        "#e7e3d7",
        stretch=1,
    )
    plaque.save(TARGET / "cz5-plinth-paint.png", optimize=True)
