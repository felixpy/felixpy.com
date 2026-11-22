import json
import math
import subprocess
from pathlib import Path

from PIL import Image


def main():
    media = Path(__file__).resolve().parents[2] / "public/media"
    keys = json.loads(subprocess.check_output([
        "node", "--input-type=module", "-e",
        "import {editions} from './src/content/books.ts';console.log(JSON.stringify(editions.map(book => book.key).sort()))",
    ], cwd=media.parents[1], encoding="utf8"))
    covers = [media / "books" / (key + ".webp") for key in keys]
    columns = math.ceil(math.sqrt(len(covers)))
    rows = math.ceil(len(covers) / columns)
    width, height = 96, 144
    atlas = Image.new("RGB", (width * columns, height * rows))
    for i, cover in enumerate(covers):
        with Image.open(cover) as source:
            tile = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            atlas.paste(tile, ((i % columns) * width, (i // columns) * height))
    atlas.save(media / "graphics/shelf-covers.webp", quality=83, method=6)


if __name__ == "__main__":
    main()
