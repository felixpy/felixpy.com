import argparse
import hashlib
import json
import runpy
from pathlib import Path

import cv2
import numpy as np
import pymupdf


def underbody_print(pdf):
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != "e6651d6daa6aabe2baa8c88c91a3649794cb4698d85f65781693d1d0158bbb50":
        raise ValueError("Expected the ASUS P718 Q23654 first edition.")
    page = pymupdf.open(pdf)[0]
    drawing = page.get_drawings()
    shell = drawing[2]["rect"]
    midpoint = (shell.tl + shell.br) / 2
    mm_per_point = 127.5 / shell.height
    stencil = runpy.run_path(str(Path(__file__).with_name("trace-azoth-keycaps.py")))["stencil"]

    def vector_ink(first, stop, origin):
        paths = drawing[first:stop]
        bounds = pymupdf.Rect(paths[0]["rect"])
        for path in paths:
            bounds |= path["rect"]
        offset = ((bounds.tl + bounds.br) / 2 - origin) * mm_per_point
        loops = stencil(paths, bounds, mm_per_point)
        return [[[round(x + offset.x, 3), round(y + offset.y, 3)] for x, y in loop] for loop in loops]

    bounds = pymupdf.Rect(222, 571, 282, 584)
    scale = 54
    stamp = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=bounds, colorspace=pymupdf.csGRAY)
    image = np.frombuffer(stamp.samples, np.uint8).reshape(stamp.height, stamp.width)
    mask = (image < 128).astype(np.uint8)
    if np.any(mask[[0, -1], :]) or np.any(mask[:, [0, -1]]):
        raise ValueError("The marked area clips a glyph.")
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    wordmark = []
    for contour in contours:
        points = cv2.approxPolyDP(contour, 0.9, True).reshape(-1, 2)
        if len(points) < 3:
            continue
        on_page = (points + [stamp.x + 0.5, stamp.y + 0.5]) / scale
        wordmark.append(np.round((on_page - [midpoint.x, midpoint.y]) * mm_per_point, 3).tolist())
    return {
        "source": "ASUS P718 Q23654, page 1, underside diagram",
        "sha256": digest,
        "body": [wordmark, vector_ink(47, 48, midpoint), vector_ink(48, 49, midpoint), vector_ink(49, 58, midpoint)],
        "DPI": vector_ink(26, 29, (drawing[23]["rect"].tl + drawing[23]["rect"].br) / 2),
        "PAIR": vector_ink(32, 36, (drawing[29]["rect"].tl + drawing[29]["rect"].br) / 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    result = underbody_print(parser.parse_args().pdf)
    Path(__file__).with_name("harpe-base-print.json").write_text(
        json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8"
    )
