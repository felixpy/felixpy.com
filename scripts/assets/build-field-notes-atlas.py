"""Pack the 17 corkboard field-notes instant photos into one 5x4 WebP atlas."""

from pathlib import Path
from PIL import Image

# Exact order matching instantPhotos in src/scene/archive.ts
KEYS = [
    "tideline",
    "blue-hour",
    "gelato",
    "pastry",
    "shutters",
    "ridge",
    "noodles",
    "ferry",
    "camp",
    "estuary",
    "river-steps",
    "tart",
    "arcade",
    "tea",
    "tram",
    "waterfront",
    "flat-white",
]
COLS = 5
ROWS = 4


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "public" / "media" / "photography"
    src_dir = root / "field-notes"
    first = Image.open(src_dir / f"{KEYS[0]}.webp")
    tw, th = first.size
    atlas = Image.new("RGB", (tw * COLS, th * ROWS), (24, 24, 24))
    src_total = 0
    for idx, key in enumerate(KEYS):
        p = src_dir / f"{key}.webp"
        src_total += p.stat().st_size
        with Image.open(p) as im:
            tile = im.convert("RGB")
            if tile.size != (tw, th):
                tile = tile.resize((tw, th), Image.Resampling.LANCZOS)
            col = idx % COLS
            row = idx // COLS
            atlas.paste(tile, (col * tw, row * th))
    out = root / "field-notes-atlas.webp"
    atlas.save(out, "WEBP", quality=84, method=6)
    print(
        f"Packed {len(KEYS)} tiles ({tw}x{th}) -> {out.name} "
        f"({atlas.size[0]}x{atlas.size[1]}, {out.stat().st_size / 1024:.1f} KB vs {src_total / 1024:.1f} KB)"
    )


if __name__ == "__main__":
    main()
