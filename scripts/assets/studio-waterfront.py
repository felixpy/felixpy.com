import hashlib
import math
import os
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


def coordinates(value):
    x, height, depth = value
    return Vector((x, -depth, height))


def configure_window(scene, plate):
    metadata = plate["waterfrontCamera"]
    rain_overlay = scene.objects.get("Outside glazing surface")
    if rain_overlay is not None:
        rain_overlay.hide_render = True
        rain_overlay.hide_set(True)
    plate.visible_shadow = False
    plate.visible_diffuse = False
    plate["studioOccluder"] = False
    name = "Window | waterfront"
    cam = scene.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scene.collection.objects.link(cam)
    cam.location = coordinates(metadata["camera"])
    cam.rotation_euler = (
        coordinates(metadata["direction"]).to_track_quat("-Z", "Y").to_euler()
    )
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 24
    cam.data.lens = (
        cam.data.sensor_height * 0.5 / math.tan(math.radians(metadata["fov"]) * 0.5)
    )
    for obj in scene.objects:
        if obj.type == "CAMERA":
            obj.data.clip_start = min(obj.data.clip_start, 0.028)
            obj.data.clip_end = max(obj.data.clip_end, metadata["far"])
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.clip_end = max(
                    area.spaces.active.clip_end, metadata["far"]
                )


def find_plate(objects):
    return next(
        obj for obj in objects if obj.type == "MESH" and obj.get("waterfrontCamera")
    )


def embed_daylight(scene, path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    environment = next(
        node for node in scene.world.node_tree.nodes if node.type == "TEX_ENVIRONMENT"
    )
    existing = environment.image
    if (
        existing
        and existing.packed_file
        and hashlib.sha256(existing.packed_file.data).hexdigest() == digest
    ):
        return digest
    daylight = bpy.data.images.load(str(path), check_existing=False)
    daylight.pack()
    if existing:
        existing.user_remap(daylight)
    environment.image = daylight
    return digest


def validate_saved_window(scene, digest):
    plate = find_plate(scene.objects)
    images = [
        node.image
        for material in plate.data.materials
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE"
    ]
    if (
        not plate.data.uv_layers
        or not images
        or not all(image.packed_file for image in images)
    ):
        raise ValueError(
            "The saved waterfront is missing its UV map or embedded exposure"
        )
    if (
        "Window | waterfront" not in scene.objects
        or min(obj.data.clip_end for obj in scene.objects if obj.type == "CAMERA")
        < plate["waterfrontCamera"]["far"]
    ):
        raise ValueError("The saved window camera cannot frame the complete river")
    environment = next(
        node.image
        for node in scene.world.node_tree.nodes
        if node.type == "TEX_ENVIRONMENT"
    )
    if (
        not environment.packed_file
        or hashlib.sha256(environment.packed_file.data).hexdigest() != digest
    ):
        raise ValueError("The saved master has an incorrect daylight environment")


def replace_window(scene, plate_path):
    existing = scene.objects.get("Depth-reprojected waterfront photograph")
    if existing is None:
        raise RuntimeError("The master has no waterfront shell to update")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(plate_path).resolve(strict=True)))
    imported = set(bpy.data.objects) - before
    fresh = find_plate(imported)
    if not fresh.data.uv_layers or not fresh.data.materials:
        raise ValueError(
            "The waterfront requires an embedded calibrated texture and UV coordinates"
        )
    existing.data = fresh.data
    existing["waterfrontCamera"] = fresh["waterfrontCamera"].to_dict()
    configure_window(scene, existing)
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    return existing


def update_window(master, plate_path, destination):
    bpy.ops.wm.open_mainfile(filepath=str(Path(master).resolve(strict=True)))
    scene = bpy.context.scene
    replace_window(scene, plate_path)
    digest = embed_daylight(
        scene,
        Path(__file__).resolve().parents[2] / "public/media/lighting/desk-day.hdr",
    )
    count = len(scene.objects)
    bpy.context.preferences.filepaths.save_version = 0
    destination = Path(destination).resolve()
    descriptor, staging = tempfile.mkstemp(
        dir=destination.parent, prefix=".studio-waterfront-", suffix=".blend"
    )
    os.close(descriptor)
    staging = Path(staging)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(staging), compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(staging))
        validate_saved_window(bpy.context.scene, digest)
        if len(bpy.context.scene.objects) != count:
            raise ValueError("The room object count changed while saving")
        os.replace(staging, destination)
    finally:
        staging.unlink(missing_ok=True)
