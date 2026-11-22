import base64
from pathlib import Path
from tempfile import TemporaryDirectory


def extract_resist(datasheet):
    import cv2
    import numpy as np
    import pymupdf

    density = 24
    width, height = 21 * density, 51 * density
    faces = []
    with pymupdf.open(datasheet) as document:
        for row in reversed(document[3].get_images()[:2]):
            raw = document.extract_image(row[0])["image"]
            photo = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            b, g, r = cv2.split(cv2.medianBlur(photo, 5).astype(np.float32))
            green = (g > r * 1.36 + 3) & (g > b * 1.14 + 3)
            closing = cv2.morphologyEx(
                g,
                cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)),
            )
            lines = np.uint8(green & (closing - g > 15) & (g < 103)) * 255
            near_resist = cv2.blur(green.astype(np.float32), (11, 11)) > 0.69
            bright = cv2.dilate(
                np.uint8((r > 105) & (g > 111)), np.ones((7, 7), np.uint8)
            )
            lines[~near_resist | (bright > 0)] = 0
            _, labels, stats, _ = cv2.connectedComponentsWithStats(lines)
            keep = np.flatnonzero(
                (stats[:, cv2.CC_STAT_AREA] >= 14)
                & (
                    np.maximum(
                        stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT]
                    )
                    >= 7
                )
            )
            lines = np.uint8(np.isin(labels, keep[keep != 0])) * 255
            source = []
            for cy in (115, 1525):
                for cx in (237, 579):
                    crop = photo[cy - 42 : cy + 43, cx - 42 : cx + 43]
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    circles = cv2.HoughCircles(
                        gray,
                        cv2.HOUGH_GRADIENT,
                        1,
                        40,
                        param1=75,
                        param2=16,
                        minRadius=28,
                        maxRadius=36,
                    )
                    if circles is None:
                        raise ValueError("Pico mounting-hole registration failed")
                    x, y, _ = min(
                        circles[0], key=lambda c: (c[0] - 42) ** 2 + (c[1] - 42) ** 2
                    )
                    source.append((cx - 42 + x, cy - 42 + y))
            target = [
                [(10.5 + x) * density, (25.5 + z) * density]
                for z in (-23.5, 23.5)
                for x in (-5.7, 5.7)
            ]
            transform = cv2.getPerspectiveTransform(
                np.float32(source), np.float32(target)
            )
            faces.append(
                cv2.warpPerspective(
                    lines, transform, (width, height), flags=cv2.INTER_LINEAR
                )
            )
    trace = np.rint(np.hstack(faces).astype(np.float32) / 42.5) / 6
    base = np.array([13, 92, 52])
    etched = np.array([4, 43, 29])
    rgb = np.uint8(base + (etched - base) * trace[:, :, None])
    ok, encoded = cv2.imencode(
        ".png", rgb[:, :, ::-1], [cv2.IMWRITE_PNG_COMPRESSION, 9]
    )
    if not ok:
        raise ValueError("Could not encode solder mask artwork")
    return base64.b64encode(encoded).decode("ascii")


def apply_resist(board, material, encoded):
    import bpy

    with TemporaryDirectory() as folder:
        path = Path(folder) / "pico-solder-resist.png"
        path.write_bytes(base64.b64decode(encoded))
        image = bpy.data.images.load(str(path))
        image.pack()
        image.filepath = "//pico-solder-resist.png"
        for packed in image.packed_files:
            packed.filepath = image.filepath
    nodes = material.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    material.node_tree.links.new(
        tex.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"]
    )
    uv = board.data.uv_layers.new(name="Registered board artwork").data
    midplane = (
        min(p.co.z for p in board.data.vertices)
        + max(p.co.z for p in board.data.vertices)
    ) / 2
    for face in board.data.polygons:
        if face.material_index != 0:
            continue
        reverse = face.center.z < midplane
        for i in face.loop_indices:
            p = board.data.vertices[board.data.loops[i].vertex_index].co
            across = p.x / 0.021 + 0.5
            uv[i].uv = ((2 - across if reverse else across) * 0.5, p.y / 0.051 + 0.5)
