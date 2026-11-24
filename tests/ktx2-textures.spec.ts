import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';
import { expect, test } from '@playwright/test';
import { classifyTexture } from '../scripts/assets/encode-ktx2.mjs';
import { contentTypeForAsset } from '../scripts/deploy/r2-assets.mjs';
import { ktx2UrlFor } from '../src/scene/ktx2-loader';

const KTX2_MAGIC = Buffer.from([
  0xab, 0x4b, 0x54, 0x58, 0x20, 0x32, 0x30, 0xbb, 0x0d, 0x0a, 0x1a, 0x0a,
]);

const MEDIA_ROOT = resolve('public/media');
const BASIS_DIR = resolve('node_modules/three/examples/jsm/libs/basis');
const SCAN_DIRS = ['materials', 'photography', 'panoramas'];
const SOURCE_EXTS = new Set(['.webp', '.png', '.jpg', '.jpeg']);
const MIN_BYTES = 4000;

function collectExpectedKtx2() {
  const expected: Array<{ rel: string; ktx2Path: string }> = [];
  const excluded: string[] = [];
  for (const dir of SCAN_DIRS) {
    const absDir = join(MEDIA_ROOT, dir);
    for (const entry of readdirSync(absDir, { recursive: true, withFileTypes: true })) {
      if (!entry.isFile()) continue;
      const fullPath = join(entry.parentPath, entry.name);
      const ext = extname(entry.name).toLowerCase();
      if (!SOURCE_EXTS.has(ext)) continue;
      const rel = relative(MEDIA_ROOT, fullPath).replaceAll('\\', '/');
      const ktx2Path = fullPath.slice(0, -ext.length) + '.ktx2';
      const bytes = statSync(fullPath).size;
      const skip =
        rel.startsWith('photography/field-notes/') ||
        (rel.startsWith('panoramas/') && /-depth\.png$/i.test(rel)) ||
        rel === 'panoramas/river-ferry-reflection.png' ||
        bytes < MIN_BYTES;
      if (skip) excluded.push(ktx2Path);
      else expected.push({ rel, ktx2Path });
    }
  }
  return { expected, excluded };
}

test('generated KTX2 textures have valid KTX2 headers, hybrid ETC1S/UASTC+Zstd encoding, mipmaps, and mul4 dimensions', () => {
  const { expected, excluded } = collectExpectedKtx2();
  expect(expected.length).toBeGreaterThanOrEqual(45);

  for (const { rel, ktx2Path } of expected) {
    expect(existsSync(ktx2Path), `missing ${ktx2Path}`).toBe(true);
    const buf = readFileSync(ktx2Path);
    expect(buf.byteLength, ktx2Path).toBeGreaterThan(80);
    // Bytes 0..11: KTX2 12-byte identifier
    expect(buf.subarray(0, 12).equals(KTX2_MAGIC), `bad magic in ${ktx2Path}`).toBe(true);
    // Bytes 12..15: vkFormat (0 = VK_FORMAT_UNDEFINED for Basis Universal ETC1S / UASTC)
    expect(buf.readUInt32LE(12), `vkFormat in ${ktx2Path}`).toBe(0);
    // Bytes 20..23: pixelWidth, 24..27: pixelHeight (must be multiples of 4)
    const width = buf.readUInt32LE(20);
    const height = buf.readUInt32LE(24);
    expect(width % 4, `width=${width} in ${ktx2Path}`).toBe(0);
    expect(height % 4, `height=${height} in ${ktx2Path}`).toBe(0);
    // Bytes 40..43: levelCount (> 1 because --genmipmap is enabled)
    const levelCount = buf.readUInt32LE(40);
    expect(levelCount, `levelCount in ${ktx2Path}`).toBeGreaterThan(1);
    // Bytes 44..47: supercompressionScheme (1 = BasisLZ for sRGB ETC1S, 2 = Zstd for linear/normal UASTC)
    const role = classifyTexture(rel);
    const expectedSupercompression = role === 'srgb' ? 1 : 2;
    expect(buf.readUInt32LE(44), `supercompressionScheme (${role}) in ${ktx2Path}`).toBe(
      expectedSupercompression,
    );
  }

  for (const excludedPath of excluded) {
    expect(existsSync(excludedPath), `unexpected excluded KTX2: ${excludedPath}`).toBe(false);
  }
});

test('r2-assets maps KTX2, WASM, and Basis JS transcoder MIME types and ktx2UrlFor filters paths', () => {
  expect(contentTypeForAsset('media/materials/ash-color.0123456789.ktx2')).toBe('image/ktx2');
  expect(contentTypeForAsset('media/basis/basis_transcoder.0123456789.wasm')).toBe(
    'application/wasm',
  );
  expect(contentTypeForAsset('media/basis/basis_transcoder.0123456789.js')).toBe(
    'application/javascript; charset=utf-8',
  );

  expect(ktx2UrlFor('/media/materials/ash-color.webp')).toBe('/media/materials/ash-color.ktx2');
  expect(ktx2UrlFor('/media/photography/desk-portrait.webp')).toBe(
    '/media/photography/desk-portrait.ktx2',
  );
  expect(ktx2UrlFor('/media/panoramas/shanghai-day.webp')).toBe(
    '/media/panoramas/shanghai-day.ktx2',
  );
  expect(ktx2UrlFor('/media/panoramas/shanghai-depth.png')).toBeNull();
  expect(ktx2UrlFor('/media/panoramas/river-ferry-reflection.png')).toBeNull();
  expect(ktx2UrlFor('/media/photography/field-notes/arcade.webp')).toBeNull();
  expect(ktx2UrlFor('/media/materials/carbon-weave.webp')).toBeNull();
  expect(ktx2UrlFor('/media/graphics/white-dunes.webp')).toBeNull();
});

test('ktx2-loader transcodes KTX2 textures with clone hydration and falls back seamlessly to WebP', async ({
  page,
}) => {
  // Serve Basis transcoder files from node_modules for this unit test before studio-parts.ts is wired.
  await page.route('**/media/basis/basis_transcoder.js', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: readFileSync(join(BASIS_DIR, 'basis_transcoder.js')),
    }),
  );
  await page.route('**/media/basis/basis_transcoder.wasm', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/wasm',
      body: readFileSync(join(BASIS_DIR, 'basis_transcoder.wasm')),
    }),
  );

  const requests: string[] = [];
  page.on('request', (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith('/media/')) requests.push(pathname);
  });

  await page.goto('/robots.txt');

  // 1. Before initStudioKtx2 (or on unsupported GPU), loadStudioTexture falls back directly to WebP.
  const unsupportedResult = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const ktx2 =
      (await import('/src/scene/ktx2-loader.ts')) as typeof import('../src/scene/ktx2-loader');
    ktx2.disposeStudioKtx2();
    const supportedBefore = ktx2.ktx2Supported();

    const fakeNoExtRenderer = {
      extensions: { has: () => false, get: () => null },
    } as unknown as T.WebGLRenderer;
    const initResult = ktx2.initStudioKtx2(fakeNoExtRenderer);

    const loader = new T.TextureLoader();
    const tex = await ktx2.loadStudioTextureAsync(loader, '/media/materials/ash-color.webp', {
      srgb: true,
      wrap: T.RepeatWrapping,
      anisotropy: 8,
    });
    return {
      supportedBefore,
      initResult,
      supportedAfter: ktx2.ktx2Supported(),
      isCompressed: Boolean((tex as T.CompressedTexture).isCompressedTexture),
      hasImage: Boolean(tex.image),
      colorSpace: tex.colorSpace,
      wrapS: tex.wrapS,
      anisotropy: tex.anisotropy,
    };
  });

  expect(unsupportedResult.supportedBefore).toBe(false);
  expect(unsupportedResult.initResult).toBe(false);
  expect(unsupportedResult.supportedAfter).toBe(false);
  expect(unsupportedResult.isCompressed).toBe(false);
  expect(unsupportedResult.hasImage).toBe(true);
  expect(unsupportedResult.anisotropy).toBe(8);
  expect(requests).toContain('/media/materials/ash-color.webp');
  expect(requests).not.toContain('/media/materials/ash-color.ktx2');

  // 2. With hardware compression support (BC7 / S3TC), transcode KTX2 and hydrate pre-load clones.
  const ktx2Result = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const ktx2 =
      (await import('/src/scene/ktx2-loader.ts')) as typeof import('../src/scene/ktx2-loader');
    ktx2.disposeStudioKtx2();

    const fakeBc7Renderer = {
      extensions: {
        has: (name: string) =>
          name === 'EXT_texture_compression_bptc' || name === 'WEBGL_compressed_texture_s3tc',
        get: () => null,
      },
    } as unknown as T.WebGLRenderer;
    const enabled = ktx2.initStudioKtx2(fakeBc7Renderer);

    const manager = new T.LoadingManager();
    const managerDone = new Promise<void>((resolve) => {
      manager.onLoad = () => resolve();
    });
    const loader = new T.TextureLoader(manager);

    let cloneTex!: T.Texture;
    const loadedTex = await new Promise<T.Texture>((resolve, reject) => {
      const primary = ktx2.loadStudioTexture(loader, '/media/materials/ash-color.webp', {
        srgb: true,
        wrap: T.RepeatWrapping,
        anisotropy: 8,
        onLoad: resolve,
        onError: reject,
      });
      // Clone synchronously before async KTX2 transcoding finishes (mirrors woodVertical / photoTile).
      cloneTex = primary.clone();
      cloneTex.rotation = Math.PI / 2;
    });
    await managerDone;

    const normalTex = await ktx2.loadStudioTextureAsync(
      loader,
      '/media/materials/ash-normal.webp',
      {
        srgb: false,
        wrap: T.RepeatWrapping,
        anisotropy: 8,
      },
    );

    return {
      enabled,
      primaryCompressed: Boolean((loadedTex as T.CompressedTexture).isCompressedTexture),
      cloneCompressed: Boolean((cloneTex as T.CompressedTexture).isCompressedTexture),
      normalCompressed: Boolean((normalTex as T.CompressedTexture).isCompressedTexture),
      normalColorSpace: normalTex.colorSpace,
      sharedSource: loadedTex.source === cloneTex.source,
      mipCount: loadedTex.mipmaps.length,
      cloneMipCount: cloneTex.mipmaps.length,
      flipY: loadedTex.flipY,
      cloneRotation: cloneTex.rotation,
      width: (loadedTex.image as { width?: number })?.width ?? 0,
      height: (loadedTex.image as { height?: number })?.height ?? 0,
      colorSpace: loadedTex.colorSpace,
    };
  });

  expect(ktx2Result.enabled).toBe(true);
  expect(ktx2Result.primaryCompressed).toBe(true);
  expect(ktx2Result.cloneCompressed).toBe(true);
  expect(ktx2Result.normalCompressed).toBe(true);
  expect(ktx2Result.normalColorSpace).toBe('');
  expect(ktx2Result.sharedSource).toBe(true);
  expect(ktx2Result.mipCount).toBeGreaterThan(1);
  expect(ktx2Result.cloneMipCount).toBe(ktx2Result.mipCount);
  expect(ktx2Result.flipY).toBe(false);
  expect(ktx2Result.cloneRotation).toBeCloseTo(Math.PI / 2, 5);
  expect(ktx2Result.width).toBe(1024);
  expect(ktx2Result.height).toBe(1024);
  expect(ktx2Result.colorSpace).toBe('srgb');
  expect(requests).toContain('/media/materials/ash-color.ktx2');
  expect(requests).toContain('/media/materials/ash-normal.ktx2');

  // 3. When a .ktx2 fetch fails (404 / abort), transparently fall back to the .webp source and hydrate clones.
  await page.route('**/media/materials/limestone-color.ktx2', (route) => route.abort());
  const fallbackResult = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const ktx2 =
      (await import('/src/scene/ktx2-loader.ts')) as typeof import('../src/scene/ktx2-loader');
    const loader = new T.TextureLoader();

    let cloneTex!: T.Texture;
    const loadedTex = await new Promise<T.Texture>((resolve, reject) => {
      const primary = ktx2.loadStudioTexture(loader, '/media/materials/limestone-color.webp', {
        srgb: true,
        onLoad: resolve,
        onError: reject,
      });
      cloneTex = primary.clone();
    });
    return {
      isCompressed: Boolean((loadedTex as T.CompressedTexture).isCompressedTexture),
      hasImage: Boolean(loadedTex.image),
      cloneHasImage: Boolean(cloneTex.image),
      sharedSource: loadedTex.source === cloneTex.source,
      colorSpace: loadedTex.colorSpace,
    };
  });

  expect(fallbackResult.isCompressed).toBe(false);
  expect(fallbackResult.hasImage).toBe(true);
  expect(fallbackResult.cloneHasImage).toBe(true);
  expect(fallbackResult.sharedSource).toBe(true);
  expect(fallbackResult.colorSpace).toBe('srgb');
  expect(requests).toContain('/media/materials/limestone-color.webp');
});
