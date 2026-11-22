from pathlib import Path

import numpy as np
from PIL import Image


def river_spectrum(resolution=384, meters=38.0):
    random = np.random.default_rng(1629)
    frequency = 2 * np.pi * np.fft.fftfreq(resolution, d=meters / resolution)
    kx, ky = np.meshgrid(frequency, frequency)
    magnitude = np.maximum(np.hypot(kx, ky), 1e-8)
    direction = ((0.84 * kx + 0.54 * ky) / magnitude) ** 2
    energy = np.exp(-1 / (magnitude * 3.1) ** 2) * (0.12 + 0.88 * direction)
    energy *= np.exp(-(magnitude * 0.09) ** 2) / magnitude**4
    energy[0, 0] = 0
    spectrum = np.fft.fft2(random.normal(size=(resolution, resolution))) * np.sqrt(energy)
    height = np.fft.ifft2(spectrum).real
    dx = np.fft.ifft2(1j * kx * spectrum).real
    dy = np.fft.ifft2(1j * ky * spectrum).real
    channels = [np.clip(0.5 + field / (6.2 * field.std()), 0, 1) for field in (dx, dy, height)]
    return Image.fromarray(np.round(np.stack(channels, axis=-1) * 255).astype('uint8'))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    river_spectrum().save(root / 'public/media/panoramas/river-slopes.webp', lossless=True, method=6)
