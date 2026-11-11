"""Prepare registered inverse-depth textures for the two window photographs."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation


def depth_texture(photo, processor, model, device):
    width = min(photo.width, 768)
    height = round(photo.height * width / photo.width)
    inputs = processor(images=photo, return_tensors="pt").to(device)
    with torch.inference_mode():
        estimate = model(**inputs).predicted_depth.unsqueeze(1)
        depth = torch.nn.functional.interpolate(
            estimate, size=(height, width), mode="bicubic", align_corners=False
        )[0, 0].cpu().numpy()

    far, near = np.percentile(depth, (3, 98))
    relative = np.clip((depth - far) / max(near - far, 1e-6), 0, 1)
    sharp = Image.fromarray(np.uint8(np.round(relative * 255)))
    soft = sharp.filter(ImageFilter.GaussianBlur(radius=3.5))
    return Image.merge("RGB", (soft, sharp, Image.new("L", (width, height))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to the local Depth Anything V2 Small checkpoint")
    parser.add_argument("photos", type=Path, nargs="+")
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = AutoImageProcessor.from_pretrained(args.model, local_files_only=True)
    model = AutoModelForDepthEstimation.from_pretrained(args.model, local_files_only=True).to(device).eval()
    for photo_path in args.photos:
        with Image.open(photo_path) as source:
            texture = depth_texture(source.convert("RGB"), processor, model, device)
        city = photo_path.stem.removesuffix("-day").removesuffix("-night")
        destination = photo_path.with_name(f"{city}-depth.png")
        texture.save(destination, optimize=True)
        print(f"{destination}  {texture.width}x{texture.height}")


if __name__ == "__main__":
    main()
