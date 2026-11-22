from pathlib import Path

from PIL import Image


root = Path(__file__).resolve().parents[2]
art = root / ".references/08-书籍与纸品/计算机科学/Structure and Interpretation of Computer Programs/参考图/MIT Press paperback/MIT-cover.jpg"
cover = Image.open(art).convert("RGB")
width, height = 768, 1152
print_area = Image.new("RGB", (width, height), "#341650")
stops = [(0.066, 0), (0.108, 0.054), (0.321, 0.303), (0.813, 0.831), (0.929, 0.953), (0.975, 1)]
left = round(width * 0.015)
for (source_top, top), (source_bottom, bottom) in zip(stops, stops[1:]):
    strip = cover.resize(
        (width - left, round(height * bottom) - round(height * top)),
        Image.Resampling.LANCZOS,
        box=(0, source_top * cover.height, (1 - left / width) * cover.width / 1.143, source_bottom * cover.height),
    )
    print_area.paste(strip, (left, round(height * top)))
    print_area.paste(strip.crop((0, 0, 1, strip.height)).resize((left, strip.height)), (0, round(height * top)))
print_area.save(root / "public/media/books/sicp.webp", quality=91, method=6)
