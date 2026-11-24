import * as T from 'three';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { defaultStudioLoadingManager } from './asset-loading';

export type StudioTextureOptions = {
  srgb?: boolean;
  wrap?: T.Wrapping;
  wrapS?: T.Wrapping;
  wrapT?: T.Wrapping;
  anisotropy?: number;
  repeat?: [number, number];
  flipY?: boolean;
  onLoad?: (texture: T.Texture) => void;
  onError?: (error: unknown) => void;
};

const KTX2_PREFIXES = ['/media/materials/', '/media/photography/', '/media/panoramas/'];
const KTX2_SOURCE_EXT = /\.(?:webp|png|jpe?g)$/i;

// Textures intentionally kept as WebP/PNG (depth maps, tiny < 4 KB textures, or excluded atlases).
const KTX2_EXCLUDED_PATHS = new Set([
  '/media/materials/carbon-weave.webp',
  '/media/materials/carbon-weave-normal.webp',
  '/media/materials/cloth-weave.webp',
  '/media/materials/gr701-epdm-normal.png',
  '/media/materials/solarcycle-grille.png',
  '/media/panoramas/river-ferry-reflection.png',
]);

let sharedLoader: KTX2Loader | null = null;
let initializedRenderer: T.WebGLRenderer | null = null;
let hardwareCompressedSupported = false;

function isDisabledByQuery(): boolean {
  if (typeof location === 'undefined') return false;
  return new URLSearchParams(location.search).get('studio-ktx2') === 'off';
}

function hasHardwareCompression(renderer: T.WebGLRenderer): boolean {
  const ext = renderer.extensions;
  if (!ext) return false;
  return (
    ext.has('WEBGL_compressed_texture_astc') ||
    ext.has('EXT_texture_compression_bptc') ||
    ext.has('WEBGL_compressed_texture_etc') ||
    ext.has('WEBGL_compressed_texture_s3tc') ||
    ext.has('WEBGL_compressed_texture_pvrtc') ||
    ext.has('WEBKIT_WEBGL_compressed_texture_pvrtc')
  );
}

/**
 * Resolve the `.ktx2` sibling path for a studio texture URL, or `null` if the
 * texture is intentionally served as WebP/PNG (depth maps, tiny < 4 KB maps, etc.).
 */
export function ktx2UrlFor(url: string): string | null {
  const clean = url.split('?')[0];
  if (!KTX2_SOURCE_EXT.test(clean)) return null;
  if (!KTX2_PREFIXES.some((prefix) => clean.startsWith(prefix))) return null;
  if (clean.startsWith('/media/photography/field-notes/')) return null;
  if (clean.startsWith('/media/panoramas/') && /-depth\.png$/i.test(clean)) return null;
  if (KTX2_EXCLUDED_PATHS.has(clean)) return null;
  return clean.replace(KTX2_SOURCE_EXT, '.ktx2');
}

/**
 * Initialize the shared `KTX2Loader` for a `WebGLRenderer`.
 *
 * Uses `defaultStudioLoadingManager` (which applies `assetUrl` via `setURLModifier`)
 * together with logical path `'/media/basis/'`, so `FileLoader` resolves both
 * `basis_transcoder.js` and `basis_transcoder.wasm` through the content-hashed
 * production manifest and optional R2 `VITE_ASSET_BASE_URL` origin seamlessly.
 */
export function initStudioKtx2(renderer: T.WebGLRenderer): boolean {
  if (initializedRenderer === renderer && sharedLoader) {
    return hardwareCompressedSupported;
  }

  if (sharedLoader) {
    sharedLoader.dispose();
    sharedLoader = null;
  }

  initializedRenderer = renderer;
  if (isDisabledByQuery() || !hasHardwareCompression(renderer)) {
    hardwareCompressedSupported = false;
    return false;
  }

  const loader = new KTX2Loader(defaultStudioLoadingManager);
  loader.setTranscoderPath('/media/basis/');
  const cores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency || 2 : 2;
  loader.setWorkerLimit(Math.min(4, Math.max(1, cores)));
  loader.detectSupport(renderer);

  sharedLoader = loader;
  hardwareCompressedSupported = true;
  return true;
}

export function ktx2Supported(): boolean {
  return hardwareCompressedSupported && sharedLoader !== null;
}

export function disposeStudioKtx2(): void {
  if (sharedLoader) {
    sharedLoader.dispose();
    sharedLoader = null;
  }
  initializedRenderer = null;
  hardwareCompressedSupported = false;
}

function applyOptions(
  texture: T.Texture,
  options: StudioTextureOptions | undefined,
  isCompressed: boolean,
): void {
  if (!options) return;
  const wrapS = options.wrapS ?? options.wrap;
  const wrapT = options.wrapT ?? options.wrap;
  if (wrapS !== undefined) texture.wrapS = wrapS;
  if (wrapT !== undefined) texture.wrapT = wrapT;
  if (options.anisotropy !== undefined) texture.anisotropy = options.anisotropy;
  if (options.repeat !== undefined) texture.repeat.set(options.repeat[0], options.repeat[1]);
  if (options.srgb === true) texture.colorSpace = T.SRGBColorSpace;
  else if (options.srgb === false) texture.colorSpace = T.NoColorSpace;
  if (!isCompressed && options.flipY !== undefined) texture.flipY = options.flipY;
}

function hydrateCompressed(
  target: T.Texture,
  loaded: T.CompressedTexture,
  options: StudioTextureOptions | undefined,
): void {
  (target as T.Texture & { isCompressedTexture?: boolean }).isCompressedTexture = true;
  target.source = loaded.source;
  target.mipmaps = loaded.mipmaps;
  target.format = loaded.format;
  target.type = loaded.type;
  target.minFilter = loaded.minFilter;
  target.magFilter = loaded.magFilter;
  target.generateMipmaps = false;
  target.flipY = false;
  target.premultiplyAlpha = loaded.premultiplyAlpha;
  if (options?.srgb === true) {
    target.colorSpace = T.SRGBColorSpace;
  } else if (options?.srgb === false) {
    target.colorSpace = T.NoColorSpace;
  } else if (target.colorSpace === T.NoColorSpace && loaded.colorSpace !== T.NoColorSpace) {
    target.colorSpace = loaded.colorSpace;
  }
  target.needsUpdate = true;
}

function hydrateFallback(
  target: T.Texture,
  loaded: T.Texture,
  options: StudioTextureOptions | undefined,
): void {
  delete (target as T.Texture & { isCompressedTexture?: boolean }).isCompressedTexture;
  target.source = loaded.source;
  target.mipmaps = loaded.mipmaps;
  target.format = loaded.format;
  target.type = loaded.type;
  target.minFilter = loaded.minFilter;
  target.magFilter = loaded.magFilter;
  target.generateMipmaps = loaded.generateMipmaps;
  if (options?.flipY !== undefined) {
    target.flipY = options.flipY;
  }
  if (options?.srgb === true) {
    target.colorSpace = T.SRGBColorSpace;
  } else if (options?.srgb === false) {
    target.colorSpace = T.NoColorSpace;
  }
  target.needsUpdate = true;
}

/**
 * Load a texture synchronously like `TextureLoader.load()`, preferring the
 * Basis Universal UASTC+Zstd `.ktx2` sibling when hardware compressed textures
 * are supported and transparently falling back to `url` (WebP/PNG) otherwise.
 *
 * Clones created from the returned texture before loading finishes (e.g.
 * `woodVertical`, `photoTile`, `instantAtlas`) are automatically hydrated with
 * the same shared GPU `Texture.source` once transcoding completes.
 */
export function loadStudioTexture(
  fallbackLoader: T.TextureLoader,
  url: string,
  options?: StudioTextureOptions,
): T.Texture {
  const ktx2Path = ktx2Supported() ? ktx2UrlFor(url) : null;
  if (!ktx2Path || !sharedLoader) {
    const texture = fallbackLoader.load(
      url,
      (loaded) => options?.onLoad?.(loaded),
      undefined,
      (error) => options?.onError?.(error),
    );
    applyOptions(texture, options, false);
    return texture;
  }

  const loader = sharedLoader;
  const manager = fallbackLoader.manager;
  const placeholder = new T.Texture();
  applyOptions(placeholder, options, false);

  const clones = new Set<T.Texture>();
  let settled = false;
  let disposed = false;

  const baseClone = T.Texture.prototype.clone;
  const attachCloneTracker = (instance: T.Texture) => {
    instance.clone = function trackedClone(this: T.Texture) {
      const cloned = baseClone.call(this);
      if (!settled) {
        // Avoid WebGL warnings if a clone is rendered before image data arrives.
        if (!cloned.image) cloned.version = 0;
        clones.add(cloned);
        attachCloneTracker(cloned);
      }
      return cloned;
    };
  };
  attachCloneTracker(placeholder);

  const baseDispose = placeholder.dispose.bind(placeholder);
  placeholder.dispose = () => {
    disposed = true;
    baseDispose();
  };

  const restoreCloneMethod = (instance: T.Texture) => {
    if (Object.prototype.hasOwnProperty.call(instance, 'clone')) {
      delete (instance as Partial<T.Texture>).clone;
    }
  };

  const finishAll = (apply: (tex: T.Texture) => void, loaded: T.Texture) => {
    settled = true;
    restoreCloneMethod(placeholder);
    for (const clone of clones) restoreCloneMethod(clone);
    if (disposed) {
      loaded.dispose();
      clones.clear();
      return;
    }
    apply(placeholder);
    for (const clone of clones) apply(clone);
    clones.clear();
    options?.onLoad?.(placeholder);
  };

  const fallbackToSource = () => {
    if (disposed) {
      manager.itemEnd(ktx2Path);
      return;
    }
    fallbackLoader.load(
      url,
      (fallbackTex) => {
        finishAll((tex) => hydrateFallback(tex, fallbackTex, options), fallbackTex);
        manager.itemEnd(ktx2Path);
      },
      undefined,
      (error) => {
        settled = true;
        restoreCloneMethod(placeholder);
        for (const clone of clones) restoreCloneMethod(clone);
        clones.clear();
        options?.onError?.(error);
        manager.itemEnd(ktx2Path);
      },
    );
  };

  manager.itemStart(ktx2Path);
  const resolvedUrl = manager.resolveURL(ktx2Path);
  const binaryLoader = new T.FileLoader();
  binaryLoader.setResponseType('arraybuffer');
  binaryLoader.load(
    resolvedUrl,
    (data) => {
      if (disposed) {
        manager.itemEnd(ktx2Path);
        return;
      }
      if (!(data instanceof ArrayBuffer)) {
        fallbackToSource();
        return;
      }
      loader.parse(
        data,
        (compressed) => {
          finishAll((tex) => hydrateCompressed(tex, compressed, options), compressed);
          manager.itemEnd(ktx2Path);
        },
        () => {
          fallbackToSource();
        },
      );
    },
    undefined,
    () => {
      fallbackToSource();
    },
  );

  return placeholder;
}

export function loadStudioTextureAsync(
  fallbackLoader: T.TextureLoader,
  url: string,
  options?: Omit<StudioTextureOptions, 'onLoad' | 'onError'>,
): Promise<T.Texture> {
  return new Promise((resolve, reject) => {
    loadStudioTexture(fallbackLoader, url, {
      ...options,
      onLoad: resolve,
      onError: reject,
    });
  });
}

export type MaterialTextureSlot =
  | 'map'
  | 'normalMap'
  | 'roughnessMap'
  | 'metalnessMap'
  | 'alphaMap'
  | 'aoMap'
  | 'emissiveMap'
  | 'bumpMap';

export function applyStudioTexture(
  material: T.MeshStandardMaterial | T.MeshBasicMaterial,
  slot: MaterialTextureSlot,
  fallbackLoader: T.TextureLoader,
  url: string,
  options?: StudioTextureOptions,
): T.Texture {
  const texture = loadStudioTexture(fallbackLoader, url, {
    ...options,
    onLoad: (loaded) => {
      material.needsUpdate = true;
      options?.onLoad?.(loaded);
    },
  });
  (material as unknown as Record<string, T.Texture | null>)[slot] = texture;
  return texture;
}
