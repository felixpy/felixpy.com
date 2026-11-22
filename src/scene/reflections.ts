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

function supportsRadiance(renderer: T.WebGLRenderer) {
  return (
    renderer.extensions.has('EXT_color_buffer_float') ||
    renderer.extensions.has('EXT_color_buffer_half_float')
  );
}

export function prelinkPreviewReflection(renderer: T.WebGLRenderer) {
  if (
    !supportsRadiance(renderer) ||
    !renderer.extensions.has('KHR_parallel_shader_compile') ||
    renderer.getContext().isContextLost() ||
    renderer.xr.isPresenting
  )
    return;

  const generator = new T.PMREMGenerator(renderer);
  const target = renderer.getRenderTarget();
  const face = renderer.getActiveCubeFace();
  const mip = renderer.getActiveMipmapLevel();
  const shadowType = renderer.shadowMap.type;
  const programs = new Set(renderer.info.programs ?? []);
  const scratch = new T.WebGLCubeRenderTarget(1, {
    type: T.HalfFloatType,
    colorSpace: T.LinearSRGBColorSpace,
    depthBuffer: false,
  });
  performance.mark('studio-pmrem-prelink-start');
  try {
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.setRenderTarget(scratch);
    generator.compileEquirectangularShader();
  } catch {
    generator.dispose();
    return;
  } finally {
    renderer.shadowMap.type = shadowType;
    renderer.setRenderTarget(target, face, mip);
    scratch.dispose();
  }

  const program = renderer.info.programs?.find(
    (candidate) => candidate.name === 'PMREMEquirectangularToCubemap' && !programs.has(candidate),
  );
  if (!program) {
    generator.dispose();
    return;
  }
  performance.mark('studio-pmrem-prelink-submitted', {
    detail: { id: program.id, name: program.name },
  });
  return generator;
}

export function studioReflections(
  renderer: T.WebGLRenderer,
  scene: T.Scene,
  generator = new T.PMREMGenerator(renderer),
) {
  const loader = new HDRLoader();
  const probes: Record<Time, Probe> = { day: {}, night: {} };
  const canPrefilter = supportsRadiance(renderer);
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
      if (!canPrefilter) return;
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
