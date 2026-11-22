import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pymupdf


def outlines(drawing):
    rings = []
    ring = []
    for kind, *item in drawing["items"]:
        if kind == "re":
            rect = item[0]
            rings.append([rect.tl, rect.tr, rect.br, rect.bl])
            continue
        start, end = item[0], item[-1]
        if not ring or abs(ring[-1] - start) > 0.0008:
            if ring:
                rings.append(ring)
            ring = [start]
        if kind == "c":
            a, b, c, d = item
            for step in range(1, 9):
                t = step / 8
                ring.append(
                    a * (1 - t) ** 3
                    + b * (3 * t * (1 - t) ** 2)
                    + c * (3 * t * t * (1 - t))
                    + d * t**3
                )
        elif kind == "l":
            ring.append(end)
        else:
            raise ValueError(kind)
    return [r for r in [*rings, ring] if len(r) > 2]


def stencil(paths, bounds, scale):
    if not paths:
        return []
    density = 72
    origin = np.array([bounds.x0, bounds.y0])
    mask = np.zeros(
        (
            int(bounds.height * scale * density) + 5,
            int(bounds.width * scale * density) + 5,
        ),
        np.uint8,
    )
    for item in paths:
        rings = [
            np.rint((np.asarray(r) - origin) * scale * density + 2).astype(np.int32)
            for r in outlines(item)
        ]
        if rings:
            layer = np.zeros_like(mask)
            cv2.fillPoly(layer, rings, 255)
            mask |= layer
    loops = []
    contours = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
    for contour in contours:
        if abs(cv2.contourArea(contour)) < 5:
            continue
        points = cv2.approxPolyDP(contour, 0.021 * density, True).reshape(-1, 2)
        if len(points) > 2:
            mm = (points - 2) / density - np.array(
                [bounds.width, bounds.height]
            ) * scale / 2
            loops.append(np.round(mm, 3).tolist())
    return loops


def trace(pdf):
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != "989090f73eae6648ef4a73cb6aa95a80f7e84209eb731b9760d566ca0cb57893":
        raise ValueError(
            "Use the original ASUS M702 Q23057 PRINT4 guide for these drawing paths."
        )
    manual = pymupdf.open(pdf)
    drawing = manual[0].get_drawings()
    faces = [
        o["rect"]
        for o in drawing[64:877]
        if o["type"] == "s"
        and len(o["items"]) == 8
        and abs(o["rect"].height - 10.9) < 0.12
        and o["rect"].width > 8
    ]
    assert len(faces) == 81
    printed = [
        o for o in drawing[877:1142] if o["type"] == "f" and max(o["fill"]) < 0.3
    ]
    anchors = [119.9, 137.8, 152.2, 166.6, 181.0, 195.4]
    rows = [
        sorted(
            (
                r
                for r in faces
                if min(range(6), key=lambda n: abs(r.y0 - anchors[n])) == i
            ),
            key=lambda r: r.x0,
        )
        for i in range(6)
    ]
    scale = 19.05 / (rows[1][2].x0 - rows[1][1].x0)
    root = rows[0][0]
    specs = [
        ["Esc", *[f"F{i}" for i in range(1, 13)]],
        [*"`1234567890-=", "Back", "Ins"],
        ["Tab", *"QWERTYUIOP[]\\", "Del"],
        ["Caps", *"ASDFGHJKL;'", "Enter", "PgUp"],
        ["Shift", *"ZXCVBNM,./", "Shift", "Up", "PgDn"],
        ["Ctrl", "Win", "Alt", "Space", "Alt", "Fn", "Ctrl", "Left", "Down", "Right"],
    ]
    layout = []
    for row, key_specs in zip(rows, specs, strict=True):
        keys = []
        for rect, spec in zip(row, key_specs, strict=True):
            cx = (rect.x0 + rect.x1) / 2
            cy = (rect.y0 + rect.y1) / 2
            face = [p for p in printed if rect.contains(p["rect"])]
            lip = pymupdf.Rect(rect.x0 - 0.5, rect.y1, rect.x1 + 0.5, rect.y1 + 2.12)
            skirt = [p for p in printed if lip.contains(p["rect"])]
            top = stencil(face, rect, scale)
            assert top, spec
            keys.append(
                dict(
                    key=spec,
                    units=round((rect.width * scale + 6.37) / 19.05 * 4) / 4,
                    x=round(-147.575 + (cx - (root.x0 + root.x1) / 2) * scale, 3),
                    z=round(-51 + (cy - (root.y0 + root.y1) / 2) * scale, 3),
                    width=round(rect.width * scale, 3),
                    height=round(rect.height * scale, 3),
                    top=top,
                    front=stencil(skirt, lip, scale),
                )
            )
        layout.append(keys)
    return dict(
        manual="ASUS M702 Q23057 PRINT4, page 1, US layout",
        sha256=digest,
        frontFaceHeight=round(2.12 * scale, 4),
        rows=layout,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    destination = Path(__file__).with_name("azoth-keycap-inlays.json")
    destination.write_text(
        json.dumps(trace(args.pdf), ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
