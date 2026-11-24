"""Generate 2.5K room-distance WebP tiers for >2560px window panoramas."""

from pathlib import Path
from PIL import Image

MAX_ROOM_WIDTH = 2560
PANORAMA_DIR = Path(__file__).resolve().parents[2] / "public" / "media" / "panoramas"


def main() -> None:
    for src in sorted(PANORAMA_DIR.glob("*.webp")):
        if src.stem.endswith("-room") or src.stem == "river-slopes":
            continue
        with Image.open(src) as img:
            w, h = img.size
            if w <= MAX_ROOM_WIDTH:
                continue
            scale = MAX_ROOM_WIDTH / w
            nw = MAX_ROOM_WIDTH
            nh = max(1, int(round(h * scale)))
            resized = img.convert("RGB").resize((nw, nh), Image.Resampling.LANCZOS)
            out = src.with_name(f"{src.stem}-room.webp")
            resized.save(out, "WEBP", quality=86, method=6)
            print(
                f"{src.name} ({w}x{h}, {src.stat().st_size / 1024:.1f} KB) -> "
                f"{out.name} ({nw}x{nh}, {out.stat().st_size / 1024:.1f} KB)"
            )


if __name__ == "__main__":
    main()
