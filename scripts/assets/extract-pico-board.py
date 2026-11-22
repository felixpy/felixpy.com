import argparse
import json
import runpy
from pathlib import Path

import gmsh
import cv2
import numpy as np
import pymupdf


def printed_mark(datasheet):
    with pymupdf.open(datasheet) as document:
        photo = document[3].get_images()[1][0]
        encoded = np.frombuffer(document.extract_image(photo)["image"], dtype=np.uint8)
    pixels = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    h, w = pixels.shape[:2]
    sample = pixels[
        round(h * 0.72) : round(h * 0.902), round(w * 0.36) : round(w * 0.657)
    ]
    mask = (sample.min(axis=2) > 155).astype(np.uint8)
    loops, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    outer = max(range(len(loops)), key=lambda i: cv2.contourArea(loops[i]))
    x, y, width, height = cv2.boundingRect(loops[outer])
    paths = []
    for i, loop in enumerate(loops):
        if i != outer and hierarchy[0, i, 3] != outer:
            continue
        polygon = cv2.approxPolyDP(loop, 0.82, True).reshape(-1, 2)
        if len(polygon) < 3:
            continue
        paths.append(
            [
                [
                    round((u - x - width / 2) / height, 5),
                    round((v - y - height / 2) / height, 5),
                ]
                for u, v in polygon
            ]
        )
    if len(paths) < 10:
        raise ValueError("The Pico photographic panel has changed")
    return paths


def back_registration(pixels):
    height, width = pixels.shape[:2]
    if (width, height) != (800, 1600):
        raise ValueError("Unexpected Pico underside photograph dimensions")
    ink = (pixels.min(axis=2) > 224).astype(np.uint8)
    photo, board = [], []
    for row in range(20):
        for side, first, last in [
            (1, (142, 96), (148, 1546)),
            (-1, (674, 95), (681, 1543)),
        ]:
            cx, cy = [round(a + (b - a) * row / 19) for a, b in zip(first, last)]
            radius = 21
            sample = ink[cy - radius : cy + radius + 1, cx - radius : cx + radius + 1]
            _, labels, stats, centers = cv2.connectedComponentsWithStats(sample)
            hole = labels[radius, radius]
            if not hole or not 500 < stats[hole, cv2.CC_STAT_AREA] < 1250:
                raise ValueError(f"Cannot register Pico underside contact {side}/{row}")
            photo.append(centers[hole] + [cx - radius, cy - radius])
            board.append((side * 8.89, (row - 9.5) * 2.54))
    photo = np.array(photo, dtype=np.float64).reshape(-1, 1, 2)
    board = np.array(board, dtype=np.float64).reshape(-1, 1, 2)
    matrix, _ = cv2.findHomography(photo, board)
    error = np.linalg.norm(cv2.perspectiveTransform(photo, matrix) - board, axis=2)
    if error.max() > 0.12:
        raise ValueError("Pico pin rows do not match nominal pitch")
    return matrix


def reverse_marks(datasheet):
    with pymupdf.open(datasheet) as document:
        xref = document[3].get_images()[0][0]
        encoded = np.frombuffer(document.extract_image(xref)["image"], dtype=np.uint8)
    pixels = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    matrix = back_registration(pixels)
    devices = [
        ("Recognized Component and laminate maker", (344, 500, 537, 575)),
        ("CE", (317, 872, 497, 1003)),
        ("FCC", (335, 1027, 501, 1164)),
        ("Inspection box", (317, 1186, 511, 1381)),
    ]
    marks = {}
    for name, (left, top, right, bottom) in devices:
        mask = (pixels[top:bottom, left:right].min(axis=2) > 155).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        paths = []
        for contour in contours:
            if cv2.contourArea(contour) < 5:
                continue
            polygon = cv2.approxPolyDP(contour, 0.65, True)
            if len(polygon) >= 3:
                photo = polygon.astype(np.float64) + [left, top]
                local = cv2.perspectiveTransform(photo, matrix).reshape(-1, 2)
                paths.append(local.round(5).tolist())
        if not paths:
            raise ValueError(f"Missing photographic marking: {name}")
        marks[name] = paths
    return marks


def extract(source):
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.StlAngularDeflection", 0.35)
        gmsh.option.setNumber("Mesh.StlLinearDeflection", 0.008)
        gmsh.option.setNumber("Mesh.StlLinearDeflectionRelative", 0)
        gmsh.option.setNumber("Geometry.OCCBoundsUseStl", 1)
        gmsh.model.occ.importShapes(str(source))
        gmsh.model.occ.synchronize()
        solids = gmsh.model.getEntities(3)
        (board,) = [s for s in solids if "REF_BOARD" in gmsh.model.getEntityName(*s)]
        gmsh.model.occ.remove([s for s in solids if s != board], recursive=True)
        gmsh.model.occ.synchronize()
        gmsh.model.mesh.importStl()
        gmsh.model.mesh.removeDuplicateNodes()
        tags, coords, _ = gmsh.model.mesh.getNodes()
        index = {n: i for i, n in enumerate(tags)}
        vertices = [
            [round(v, 5) for v in coords[i : i + 3]] for i in range(0, len(coords), 3)
        ]
        triangles, finishes = [], []
        for _, tag in gmsh.model.getBoundary([board], oriented=True):
            face = abs(tag)
            x, y, z, xx, yy, zz = gmsh.model.getBoundingBox(2, face)
            if gmsh.model.getType(2, face) == "Plane" and yy - y < 0.025:
                finish = 0 if xx - x > 18 and zz - z > 40 else 1
            else:
                finish = (
                    1
                    if gmsh.model.getType(2, face) == "Cylinder"
                    and xx - x < 2.2
                    and zz - z < 2.2
                    else 2
                )
            _, nodes = gmsh.model.mesh.getElementsByType(2, face)
            for i in range(0, len(nodes), 3):
                a, b, c = nodes[i : i + 3]
                triangles.append([index[a], index[b], index[c]])
                finishes.append(finish)
        return {"vertices": vertices, "triangles": triangles, "finishes": finishes}
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", type=Path)
    parser.add_argument("datasheet", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = extract(args.step)
    result["printed_mark"] = {
        "raspberry": printed_mark(args.datasheet),
        "reverse": reverse_marks(args.datasheet),
    }
    result["resist"] = runpy.run_path(str(Path(__file__).with_name("pico-resist.py")))[
        "extract_resist"
    ](args.datasheet)
    args.output.write_text(json.dumps(result, separators=(",", ":")))
