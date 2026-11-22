import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2] / ".review" / "atelier"
sys.path.insert(0, str(root / "tripo-local-libs"))
sys.path.insert(0, str(root / "local-triposr/TripoSR-main"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HOME"] = str(root / "model-cache")
import numpy as np
import torch
from PIL import Image
from skimage.measure import marching_cubes
import huggingface_hub
from huggingface_hub import hf_hub_download
from omegaconf import OmegaConf
from types import ModuleType

mc = ModuleType("torchmcubes")


def cpu_marching(values, level):
    vertices, faces, _, _ = marching_cubes(
        values.detach().float().cpu().numpy(), level=level
    )
    return torch.from_numpy(vertices[:, ::-1].copy()), torch.from_numpy(
        faces[:, ::-1].astype("i").copy()
    )


mc.marching_cubes = cpu_marching
sys.modules["torchmcubes"] = mc
sys.modules["rembg"] = ModuleType("rembg")


def local_dino(*args, **kwargs):
    if kwargs.get("filename") == "config.json":
        return str(root / "dino-vitb16-config.json")
    return hf_hub_download(*args, **kwargs)


huggingface_hub.hf_hub_download = local_dino
from tsr.system import TSR
from tsr.utils import resize_foreground

torch.set_num_threads(3)
print("Reading TripoSR", flush=True)
cfg = OmegaConf.load(root / "triposr-config.yaml")
OmegaConf.resolve(cfg)
model = TSR(cfg)
weight = torch.load(root / "triposr-model.ckpt", weights_only=True, map_location="cpu")
model.load_state_dict(weight)
del weight
model.to("cuda").eval()
model.renderer.set_chunk_size(49152)
for name in sys.argv[1:] or ["great-sage", "mk85"]:
    print("Reconstructing", name, torch.cuda.get_device_name(), flush=True)
    img = Image.open(root / f"{name}-cutout.png").convert("RGBA")
    img = resize_foreground(img, 0.85)
    source = np.asarray(img).astype("f") / 255
    conditioned = Image.fromarray(
        np.uint8(
            255 * (source[:, :, :3] * source[:, :, 3:] + 0.5 * (1 - source[:, :, 3:]))
        )
    )
    with torch.inference_mode():
        code = model([conditioned], device="cuda")
        model.extract_mesh(code, True, resolution=288, threshold=24)[0].export(
            root / f"{name}-tripo.ply"
        )
    print("Wrote", root / f"{name}-tripo.ply", flush=True)
