from hashlib import sha256
from pathlib import Path
import runpy

import bpy


root = Path(__file__).resolve().parents[2]
fit_print = runpy.run_path(str(root / "scripts/assets/fit-book-print.py"))["fit"]


def fit(scene):
    book, = [o for o in scene.objects if o.get("ISBN") == "9780140390445"]
    face, = [part for part in book.children if "front" in part.name.lower()]
    old_thickness = face.scale.y
    delta = 0.015 - old_thickness
    shelf_position = None
    moving = []
    if book.parent and abs(delta) > 1e-6:
        shelf_position = book.location.copy()
        shelf_position.x += delta / 2
        adjacent = {"First edition", "9780441172719", "9780441569595", "9780679732761"}
        moving = [sibling for sibling in book.parent.children if sibling.get("ISBN") in adjacent]
        if len(moving) != len(adjacent):
            raise ValueError("The four adjacent literature editions are required for this shelf")
        floor = book.location.z - face.scale.z / 2
        bookend, = [o for o in book.parent.children if o.name.startswith("Bent steel bookend") and abs(o.location.z - floor) < 0.001]
        moving.append(bookend)
    name, jacket_sha = fit_print(scene, "walden", shelf_position)
    for sibling in moving:
        sibling.location.x += delta
    front, = [n.image for n in face.material_slots[0].material.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
    source = root / "public/media/books/walden.webp"
    expected = sha256(source.read_bytes()).hexdigest()
    if not front.packed_file or sha256(front.packed_file.data).hexdigest() != expected:
        if front.library:
            raise ValueError("Update the cover print in its source library first")
        if front.packed_file:
            front.unpack(method="REMOVE")
        front.filepath = str(source)
        front.reload()
        front.pack()
        front.filepath = "//walden.webp"
    if sha256(front.packed_file.data).hexdigest() != expected:
        raise ValueError("The packed cover does not match the cabin edition")
    bpy.context.view_layer.update()
    return {name: jacket_sha, front.name: expected}
