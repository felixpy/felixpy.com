from pathlib import Path
import shutil
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

root = Path(__file__).resolve().parents[2] / ".review" / "atelier"
source = Path(sys.argv[1])
slug = sys.argv[2] if len(sys.argv) > 2 else "great-sage"
shutil.copyfile(source, root / f"{slug}-high-resolution.png")
scale = 690 if slug == "great-sage" else 610
im = Image.open(source).convert("RGB").resize((scale, scale), Image.Resampling.LANCZOS)
image = np.asarray(im).astype(float)
background = np.median(image[20:50, 580:640], axis=(0, 1))
distance = np.linalg.norm(image - background, axis=2)
if slug == "great-sage":
    mask = distance > 18
    mask[:, :180] = False
else:
    bg = (image[:, 153:166].mean(axis=1) + image[:, 459:472].mean(axis=1)) * 0.5
    mask = np.linalg.norm(image - bg[:, None], axis=2) > 16
    silhouette = Image.new("L", (610, 610))
    paint = ImageDraw.Draw(silhouette)
    paint.polygon(
        [
            (281, 111),
            (309, 109),
            (318, 120),
            (319, 144),
            (312, 153),
            (340, 159),
            (354, 167),
            (365, 191),
            (367, 215),
            (373, 225),
            (373, 249),
            (370, 266),
            (365, 286),
            (346, 292),
            (338, 282),
            (343, 261),
            (348, 252),
            (344, 223),
            (338, 214),
            (331, 239),
            (331, 249),
            (335, 263),
            (345, 287),
            (344, 312),
            (349, 337),
            (357, 352),
            (363, 370),
            (364, 401),
            (367, 423),
            (374, 448),
            (414, 449),
            (426, 453),
            (427, 461),
            (415, 475),
            (423, 487),
            (416, 498),
            (425, 510),
            (425, 519),
            (437, 534),
            (443, 548),
            (446, 568),
            (443, 577),
            (400, 582),
            (170, 574),
            (168, 568),
            (174, 555),
            (177, 536),
            (184, 524),
            (186, 504),
            (194, 485),
            (192, 470),
            (196, 457),
            (209, 451),
            (245, 447),
            (250, 428),
            (256, 413),
            (262, 376),
            (260, 356),
            (263, 338),
            (261, 308),
            (265, 279),
            (268, 264),
            (272, 238),
            (275, 220),
            (269, 230),
            (266, 244),
            (257, 260),
            (254, 278),
            (252, 291),
            (242, 297),
            (232, 293),
            (230, 285),
            (234, 269),
            (235, 252),
            (239, 238),
            (241, 227),
            (248, 218),
            (249, 204),
            (247, 197),
            (249, 177),
            (256, 166),
            (277, 154),
            (286, 153),
            (280, 140),
            (278, 128),
        ],
        fill=255,
    )
    mask &= np.asarray(silhouette) > 0
comp, total = nd.label(nd.binary_closing(mask, iterations=1))
sizes = np.bincount(comp.ravel())
sizes[0] = 0
mask = comp == np.argmax(sizes)
near = nd.distance_transform_edt(~mask, return_distances=False, return_indices=True)
inpainted = image[tuple(near)].astype("uint8")
rgba = np.dstack([image, np.uint8(mask) * 255]).astype("uint8")
Image.fromarray(rgba).save(root / f"{slug}-cutout.png")
Image.fromarray(inpainted).save(root / f"{slug}-projection.png")
neutral = np.where(mask[:, :, None], image, np.array([127, 127, 127])).astype("uint8")
Image.fromarray(neutral).save(root / f"{slug}-neutral.png")
model = root / "depth-v2-model"
model.mkdir(exist_ok=True)
for orig, dest in [
    ("depth-v2-config.json", "config.json"),
    ("depth-v2-processor.json", "preprocessor_config.json"),
    ("depth-v2.safetensors", "model.safetensors"),
]:
    if not (model / dest).exists():
        shutil.copyfile(root / orig, model / dest)
processor = AutoImageProcessor.from_pretrained(
    model, local_files_only=True, use_fast=False
)
network = (
    AutoModelForDepthEstimation.from_pretrained(model, local_files_only=True)
    .to("cuda")
    .eval()
)
inputs = processor(images=Image.fromarray(neutral), return_tensors="pt").to("cuda")
with torch.inference_mode():
    depths = network(**inputs).predicted_depth
    scaled = (
        torch.nn.functional.interpolate(
            depths.unsqueeze(1),
            size=(scale, scale),
            mode="bicubic",
            align_corners=False,
        )
        .squeeze()
        .cpu()
        .numpy()
    )
levels = np.percentile(scaled[mask], [1, 99])
scaled = np.clip((scaled - levels[0]) / (levels[1] - levels[0]), 0, 1).astype("f")
np.save(root / f"{slug}-depth.npy", scaled)
Image.fromarray(np.uint8(scaled * 255)).save(root / f"{slug}-depth.png")
print("GPU", torch.cuda.get_device_name(), "depth bounds", levels, flush=True)
