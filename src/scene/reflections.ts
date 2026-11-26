import * as T from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import type { Environment } from '../app/environment';
import { defaultStudioLoadingManager } from './asset-loading';
import { packedBuffer } from './packed-buffer';
import { decodePmrem } from './pmrem-decode';
import radiance from './desk-radiance.json';

type Time = keyof typeof radiance;
type Probe = {
  preview?: T.WebGLCubeRenderTarget;
  full?: T.WebGLCubeRenderTarget | T.CompressedCubeTexture;
  pending?: Promise<void>;
};

function probeTexture(entry: T.WebGLCubeRenderTarget | T.CompressedCubeTexture): T.Texture {
  return entry instanceof T.WebGLCubeRenderTarget ? entry.texture : entry;
}

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
  providedGenerator?: T.PMREMGenerator,
) {
  let generator = providedGenerator;
  const loader = new HDRLoader(defaultStudioLoadingManager);
  const probes: Record<Time, Probe> = { day: {}, night: {} };
  const canPrefilter = supportsRadiance(renderer);
  let active: Time = 'night';
  let detailed = false;
  let disposed = false;
  function prefilter(source: T.Texture) {
    try {
      generator ??= new T.PMREMGenerator(renderer);
      return generator.fromEquirectangular(source);
    } finally {
      source.dispose();
    }
  }
  function loadHdrFallback(time: Time, probe: Probe): Promise<void> {
    return new Promise<void>((resolve) => {
      loader.load(
        '/media/lighting/desk-' + time + '.hdr',
        (texture) => {
          if (disposed) {
            texture.dispose();
            resolve();
            return;
          }
          probe.full = prefilter(texture);
          probe.pending = undefined;
          if (time === active && detailed) scene.environment = probeTexture(probe.full);
          resolve();
        },
        undefined,
        () => {
          probe.pending = undefined;
          resolve();
        },
      );
    });
  }
  function ensureFull(time: Time): Promise<void> {
    const probe = probes[time];
    if (probe.full) return Promise.resolve();
    if (probe.pending) return probe.pending;
    const pmremPath = '/media/lighting/desk-' + time + '.pmrem.gz';
    const url = defaultStudioLoadingManager.resolveURL(pmremPath);
    probe.pending = fetch(url)
      .then((response) => packedBuffer(response))
      .then((buffer) => {
        const cube = decodePmrem(buffer);
        if (disposed) {
          cube.dispose();
          return;
        }
        renderer.initTexture(cube);
        probe.full = cube;
        probe.pending = undefined;
        if (time === active && detailed) scene.environment = cube;
      })
      .catch(() => {
        if (disposed) return;
        return loadHdrFallback(time, probe);
      });
    return probe.pending;
  }
  return {
    preload(quality: Environment['quality']): Promise<void> {
      if (!canPrefilter || quality !== 'high') return Promise.resolve();
      return Promise.all([ensureFull('day'), ensureFull('night')]).then(() => {});
    },
    select(
      night: boolean,
      quality: Environment['quality'],
      options?: { skipPreview?: boolean } | boolean,
    ): Promise<void> {
      if (!canPrefilter) return Promise.resolve();
      const skipPreview = typeof options === 'boolean' ? options : Boolean(options?.skipPreview);
      active = night ? 'night' : 'day';
      detailed = quality === 'high';
      const time = active;
      const probe = probes[time];
      if (!detailed) {
        if (probe.full) {
          scene.environment = probeTexture(probe.full);
        } else {
          probe.preview ??= prefilter(previewTexture(time));
          scene.environment = probeTexture(probe.preview);
        }
        return Promise.resolve();
      }
      if (probe.full) {
        scene.environment = probeTexture(probe.full);
        return Promise.resolve();
      }
      if (!skipPreview && !scene.environment) {
        probe.preview ??= prefilter(previewTexture(time));
        scene.environment = probeTexture(probe.preview);
      } else if (probe.preview && !scene.environment) {
        scene.environment = probeTexture(probe.preview);
      }
      return ensureFull(time);
    },
    dispose() {
      disposed = true;
      scene.environment = null;
      for (const probe of Object.values(probes)) {
        probe.preview?.dispose();
        probe.full?.dispose();
      }
      generator?.dispose();
    },
  };
}
