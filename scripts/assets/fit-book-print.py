import argparse
import json
import math
import sys
from hashlib import sha256
from pathlib import Path

import bpy
from mathutils import Vector


proofs = Path(__file__).resolve().parents[2] / ".review/atelier/binding-prints"


def fit(scene, key, shelf_position=None):
    edition = json.loads((proofs / "catalog.json").read_text(encoding="utf-8"))[key]
    reference = edition["rearReference"]
    book, = [obj for obj in scene.objects if obj.get("ISBN") == edition["isbn"]]
    wrapper, = [child for child in book.children if "wrapper" in child.name.lower()]
    width, height, thickness = edition["size"]
    size = Vector((width, thickness, height))
    delta = size - wrapper.scale
    if delta.length > 1e-6:
        if any(part.library for part in book.children):
            raise ValueError(f"Resize the linked book in its source file: {key}")
        if book.parent:
            basis = book.matrix_basis.to_3x3()
            if shelf_position is not None:
                book.location = shelf_position
            elif (basis @ Vector((1, 0, 0)) - Vector((0, 1, 0))).length < 1e-5 and abs(delta.y) < 1e-6:
                book.location += basis @ (delta * 0.5)
            else:
                raise ValueError(f"Pass the updated Blender-local shelf position for {key}")
        for part in book.children:
            part.scale = size
        bpy.context.view_layer.update()
    nodes = wrapper.material_slots[0].material.node_tree.nodes
    image, = [node.image for node in nodes if node.type == "TEX_IMAGE" and node.image]
    jacket = proofs / f"{key}.png"
    expected = sha256(jacket.read_bytes()).hexdigest()
    if not image.packed_file or sha256(image.packed_file.data).hexdigest() != expected:
        if image.library:
            raise ValueError(f"Update linked jacket at {image.library.filepath}")
        if image.packed_file:
            image.unpack(method="REMOVE")
        image.filepath = str(jacket)
        image.reload()
        image.pack()
        image.filepath = f"//{key}-binding.png"
    if book.get("rear_reference") != reference:
        if book.library:
            raise ValueError(f"Update linked book at {book.library.filepath}")
        book["rear_reference"] = reference
    if tuple(image.size) != (1152, 1536) or sha256(image.packed_file.data).hexdigest() != expected:
        raise ValueError(f"Packed proof does not match {key}")
    return image.name, expected


def image_hashes():
    return {im.name: sha256(im.packed_file.data).hexdigest() for im in bpy.data.images if im.packed_file}


def fit_displayed_sicp(scene):
    book, = [obj for obj in scene.objects if obj.get("ISBN") == "9780262510875"]
    face, = [obj for obj in book.children if "front" in obj.name.lower()]
    location = book.location.copy()
    if book.parent:
        location.z += (0.03048 - face.scale.y) * math.sin(0.14) / 2
    wrapper, wrapper_hash = fit(scene, "sicp", location)
    front, = [node.image for node in face.material_slots[0].material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
    source = Path(__file__).resolve().parents[2] / "public/media/books/sicp.webp"
    expected = sha256(source.read_bytes()).hexdigest()
    if not front.packed_file or sha256(front.packed_file.data).hexdigest() != expected:
        if front.library:
            raise ValueError("Update the linked SICP front in its source library")
        if front.packed_file:
            front.unpack(method="REMOVE")
        front.filepath = str(source)
        front.reload()
        front.pack()
        front.filepath = "//sicp.webp"
    if sha256(front.packed_file.data).hexdigest() != expected:
        raise ValueError("The packed SICP front does not match the photographed printing")
    return {wrapper: wrapper_hash, front.name: expected}


def fit_editions(scene, keys):
    changed = {}
    for key in keys:
        if key == "sicp":
            changed.update(fit_displayed_sicp(scene))
        else:
            name, digest = fit(scene, key)
            changed[name] = digest
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", action="append", required=True)
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.context.preferences.filepaths.save_version = 0
    for file in args.files:
        path = str(file.resolve())
        bpy.ops.wm.open_mainfile(filepath=path)
        previous = image_hashes()
        changed = fit_editions(bpy.context.scene, args.edition)
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        bpy.ops.wm.open_mainfile(filepath=path)
        assert image_hashes() == {**previous, **changed}
        assert fit_editions(bpy.context.scene, args.edition) == changed
        print("Verified packed book jackets:", file, changed, flush=True)
