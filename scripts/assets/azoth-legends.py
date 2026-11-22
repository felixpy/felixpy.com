import json
from pathlib import Path

layout = json.loads(
    Path(__file__).with_name("azoth-keycap-inlays.json").read_text(encoding="utf-8")
)


def mark(part, provenance, x, z, top_height, legend, pad_print, inlay):
    def top(u, v):
        return x + u, top_height(u, v) + 0.14, z + v

    def face(u, v):
        t = 0.5 + v / layout["frontFaceHeight"]
        depth = 7.65 + 1.3 * t
        shoulder = (provenance["width"] + 1) / 2 - 1.38
        skirt = (19.05 * provenance["units"] - 0.9) / 2 - 1.2
        high = top_height(shoulder, 7.65) - 0.55
        low = top_height(skirt, 8.95) - 6.15
        return x + u, high + (low - high) * t, z + depth + 0.075

    inlay(part, provenance["top"], top, legend)
    inlay(part, provenance["front"], face, pad_print)
