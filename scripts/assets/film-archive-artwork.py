from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


root = Path(__file__).resolve().parents[2]
output = root / ".review/atelier/film-archive"
output.mkdir(parents=True, exist_ok=True)


def lettering(image, text, xy, size, ink, vertical=True, bold=False):
    try:
        font = ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except OSError:
        font = ImageFont.truetype(
            "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf", size
        )
    bounds = font.getbbox(text)
    stencil = Image.new("L", (bounds[2] - bounds[0], bounds[3] - bounds[1]))
    ImageDraw.Draw(stencil).text((-bounds[0], -bounds[1]), text, font=font, fill=255)
    if vertical:
        stencil = stencil.transpose(Image.Transpose.ROTATE_270)
    image.paste(ink, xy, stencil)


label = Image.new("RGB", (1536, 800), "#1f1c18")
draw = ImageDraw.Draw(label)
draw.rectangle((182, 76, 488, 799), fill="#ffc225")
ivory = "#f4f0df"
lettering(label, "PORTRA 400", (79, 83), 55, ivory)
lettering(label, "36", (132, 615), 40, ivory)
lettering(label, "EXP", (86, 615), 36, ivory)
lettering(label, "C-41", (399, 12), 50, ivory, False)
lettering(label, "NOTES", (459, 88), 23, "#29241a")
lettering(label, "Portra 400 • 36", (195, 284), 25, "#29241a")
lettering(label, "Color Negative Film", (528, 96), 38, ivory)
lettering(label, "PORTRA 400", (665, 86), 56, ivory)
lettering(label, "KODAK PROFESSIONAL", (750, 92), 25, ivory)
patterns = (
    "11221",
    "21112",
    "12112",
    "22111",
    "11212",
    "21211",
    "12211",
    "11122",
    "21121",
    "12121",
)
code = "115334"
bars = [1, 1, 1, 1]
for a, b in zip(code[::2], code[1::2]):
    for dark, light in zip(patterns[int(a)], patterns[int(b)]):
        bars.extend((int(dark), int(light)))
bars.extend((2, 1, 1))
top = 111
draw.rectangle((1323, 58, 1451, 745), fill="#e8e4d8")
for bar, width in enumerate(bars):
    height = width * 10
    if bar % 2 == 0:
        draw.rectangle((1330, top, 1417, top + height - 1), fill="#221e1c")
    top += height
lettering(label, code, (1423, 344), 24, "#282420")
label.save(output / "cassette-print.png", optimize=True)

proofs = Image.new("RGB", (576, 384))
sources = root / "public/media/photography"
for index, filename in enumerate(
    [
        "dalian-xinghai-bay.webp",
        "field-notes/camp.webp",
        "field-notes/ferry.webp",
        "field-notes/blue-hour.webp",
    ]
):
    with Image.open(sources / filename) as photograph:
        frame = ImageOps.fit(
            photograph.convert("RGB"), (288, 192), Image.Resampling.LANCZOS
        )
    proofs.paste(frame, ((index % 2) * 288, (index // 2) * 192))
proofs.save(output / "mounted-positives.jpg", quality=86)
with Image.open(root / "public/media/materials/desk-oak-color.webp") as veneer:
    grain = ImageOps.colorize(
        ImageOps.grayscale(veneer.resize((256, 128))), "#69462f", "#c99771"
    )
    grain.save(output / "filing-tray.jpg", quality=82)
