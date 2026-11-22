from pathlib import Path

import bpy

SOURCE = (
    Path(__file__).resolve().parents[2]
    / ".references/05-摄影与陈列/照片打印/Canon SELPHY CP1500/Blender/selphy-cp1500.blend"
)
SHEET = "Postcard proof with removable trim tabs"


def fit(scene):
    printer = scene.objects["Canon SELPHY CP1500"]
    (proof,) = [obj for obj in printer.children_recursive if obj.get("selphyProof")]
    if proof.type == "MESH":
        sheet = proof
    else:
        sheet = next(
            (child for child in proof.children if child.get("paperSet") == "Canon KP-36IP"),
            None,
        )
    if (
        sheet
        and sheet.data.library
        and Path(bpy.path.abspath(sheet.data.library.filepath)).samefile(SOURCE)
    ):
        return sheet
    old = list(proof.children)
    if proof.type == "EMPTY" and (
        len(old) != 3 or any(obj.type != "MESH" or obj.children for obj in old)
    ):
        raise ValueError("Unexpected SELPHY postcard geometry")
    with bpy.data.libraries.load(str(SOURCE), link=True, relative=True) as (_, lib):
        lib.meshes = [SHEET]
    (mesh,) = lib.meshes
    if proof.type == "MESH":
        proof.data = mesh
        sheet = proof
    else:
        sheet = bpy.data.objects.new(SHEET, mesh)
        proof.users_collection[0].objects.link(sheet)
        sheet.parent = proof
        for part in old:
            bpy.data.objects.remove(part, do_unlink=True)
    sheet["studioOccluder"] = False
    sheet["paperSet"] = "Canon KP-36IP"
    return sheet
