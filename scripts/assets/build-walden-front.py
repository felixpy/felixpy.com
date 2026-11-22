from pathlib import Path
import os

from PIL import Image, ImageDraw, ImageFont


root = Path(__file__).resolve().parents[2]
source = root / ".references/08-书籍与纸品/文学/Walden and Civil Disobedience/参考图/Original source files/walden.jpg"
original = Image.open(source).convert("RGB")
factor = 3
sheet = Image.new("RGB", (457 * factor, 700 * factor), "#17191b")
sheet.paste(original.crop((0, 0, 457, 457)).resize((457 * factor, 457 * factor), Image.Resampling.LANCZOS))
pen = ImageDraw.Draw(sheet)
pen.rectangle((0, 457 * factor, 457 * factor, 495 * factor), fill="#f8f5e9")
fonts = Path(os.environ.get("WINDIR", "")) / "Fonts"
fallback = {"arial.ttf": "LiberationSans-Regular.ttf", "seguisb.ttf": "LiberationSans-Bold.ttf", "georgiai.ttf": "LiberationSerif-Italic.ttf"}


def tracking(text, center, baseline, face, size, spacing, color):
    source_font = fonts / face
    font = ImageFont.truetype(str(source_font if source_font.is_file() else fallback[face]), round(size * factor))
    width = font.getlength(text) + (len(text) - 1) * spacing * factor
    x = center * factor - width / 2
    for letter in text:
        pen.text((x, baseline * factor), letter, font=font, fill=color, anchor="ls")
        x += font.getlength(letter) + spacing * factor


tracking("PENGUIN", 145, 481, "arial.ttf", 10.2, 4.6, "#201f1d")
tracking("CLASSICS", 309, 481, "arial.ttf", 10.2, 4.6, "#201f1d")
pen.ellipse((218 * factor, 461 * factor, 239 * factor, 491 * factor), fill="#e7732b")
mark = original.crop((214, 463, 243, 507)).convert("L").convert("RGBA")
ImageDraw.floodfill(mark, (0, 0), (255, 255, 255, 0), thresh=80)
mark = mark.resize((17 * factor, 25 * factor), Image.Resampling.LANCZOS)
sheet.paste(mark, (220 * factor, 463 * factor), mark)
tracking("HENRY DAVID THOREAU", 228.5, 582, "seguisb.ttf", 22, 2.8, "#e77d42")
tracking("Walden and Civil Disobedience", 228.5, 634, "georgiai.ttf", 24, 0.48, "#f8f4e9")
sheet.resize(original.size, Image.Resampling.LANCZOS).save(root / "public/media/books/walden.webp", quality=94, method=6)
