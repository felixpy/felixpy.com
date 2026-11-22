import * as T from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import type { Environment } from '../app/environment';
import radiance from './desk-radiance.json';

type Time = keyof typeof radiance;
type Probe = {
  preview?: T.WebGLCubeRenderTarget;
  full?: T.WebGLCubeRenderTarget;
  loading?: boolean;
};

function previewTexture(time: Time) {
  const rgbe = Uint8Array.from(atob(radiance[time]), (byte) => byte.charCodeAt(0));
  const pixels = new Uint16Array(rgbe.length);
  for (let i = 0; i < rgbe.length; i += 4) {
    const scale = 2 ** (rgbe[i + 3] - 136);
    for (let channel = 0; channel < 3; channel++) {
      pixels[i + channel] = T.DataUtils.toHalfFloat(rgbe[i + channel] * scale);
    }
    pixels[i + 3] = T.DataUtils.toHalfFloat(1);
  }
  const texture = new T.DataTexture(pixels, 16, 8, T.RGBAFormat, T.HalfFloatType);
  texture.colorSpace = T.LinearSRGBColorSpace;
  texture.mapping = T.EquirectangularReflectionMapping;
  texture.minFilter = texture.magFilter = T.LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

export function studioReflections(renderer: T.WebGLRenderer, scene: T.Scene) {
  const generator = new T.PMREMGenerator(renderer);
  const loader = new HDRLoader();
  const probes: Record<Time, Probe> = { day: {}, night: {} };
  const supportsRadiance =
    renderer.extensions.has('EXT_color_buffer_float') ||
    renderer.extensions.has('EXT_color_buffer_half_float');
  let active: Time = 'night';
  let detailed = false;
  let disposed = false;
  function prefilter(source: T.Texture) {
    try {
      return generator.fromEquirectangular(source);
    } finally {
      source.dispose();
    }
  }
  return {
    select(night: boolean, quality: Environment['quality']) {
      if (!supportsRadiance) return;
      active = night ? 'night' : 'day';
      detailed = quality === 'high';
      const time = active;
      const probe = probes[time];
      probe.preview ??= prefilter(previewTexture(time));
      scene.environment = ((detailed && probe.full) || probe.preview).texture;
      if (!detailed || probe.full || probe.loading) return;
      probe.loading = true;
      loader.load(
        '/media/lighting/desk-' + time + '.hdr',
        (texture) => {
          if (disposed) {
            texture.dispose();
            return;
          }
          probe.full = prefilter(texture);
          probe.loading = false;
          if (time === active && detailed) scene.environment = probe.full.texture;
        },
        undefined,
        () => {
          probe.loading = false;
        },
      );
    },
    dispose() {
      disposed = true;
      scene.environment = null;
      for (const probe of Object.values(probes)) {
        probe.preview?.dispose();
        probe.full?.dispose();
      }
      generator.dispose();
    },
  };
}
