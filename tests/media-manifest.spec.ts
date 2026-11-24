import { existsSync, readFileSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import { build } from 'vite';
import {
  assetUrl,
  insertContentHash,
  isImmutableAssetPath,
  resolveMediaPath,
} from '../src/app/asset-url';
import { cacheControlForAsset, collectAssets } from '../scripts/deploy/r2-assets.mjs';

test('content-hash URL resolution supports local, R2 immutable origin, old versions, and rollback', () => {
  const v1Manifest = {
    '/media/models/zone-desk.glb.gz': '/media/models/zone-desk.1111111111.glb.gz',
    '/media/lighting/cabinet-spot-visibility.png':
      '/media/lighting/cabinet-spot-visibility.2222222222.png',
    '/fonts/studio-han.woff2': '/fonts/studio-han.3333333333.woff2',
  };
  const v2Manifest = {
    ...v1Manifest,
    '/media/models/zone-desk.glb.gz': '/media/models/zone-desk.aaaaaaaaaa.glb.gz',
  };

  expect(insertContentHash('/media/models/zone-desk.glb.gz', 'abcdef0123')).toBe(
    '/media/models/zone-desk.abcdef0123.glb.gz',
  );
  expect(insertContentHash('/media/lighting/desk-night.pmrem.gz', 'abcdef0123')).toBe(
    '/media/lighting/desk-night.abcdef0123.pmrem.gz',
  );
  expect(resolveMediaPath('/media/models/zone-desk.glb.gz', v1Manifest)).toBe(
    '/media/models/zone-desk.1111111111.glb.gz',
  );
  expect(resolveMediaPath('/media/models/zone-desk.glb.gz', v2Manifest)).toBe(
    '/media/models/zone-desk.aaaaaaaaaa.glb.gz',
  );

  // R2 origin resolution
  const r2Base = 'https://assets.felixpy.com/felix-studio/';
  expect(assetUrl('/media/models/zone-desk.glb.gz', r2Base, v2Manifest)).toBe(
    'https://assets.felixpy.com/felix-studio/media/models/zone-desk.aaaaaaaaaa.glb.gz',
  );
  // Unhashed human-readable license link stays stable and non-immutable
  expect(assetUrl('/media/credits.txt', r2Base, v2Manifest)).toBe(
    'https://assets.felixpy.com/felix-studio/media/credits.txt',
  );
  expect(isImmutableAssetPath('media/models/zone-desk.aaaaaaaaaa.glb.gz')).toBe(true);
  expect(isImmutableAssetPath('fonts/studio-han.3333333333.woff2')).toBe(true);
  expect(isImmutableAssetPath('media/credits.txt')).toBe(false);
  expect(cacheControlForAsset('media/models/zone-desk.aaaaaaaaaa.glb.gz')).toBe(
    'public, max-age=31536000, immutable',
  );
  expect(cacheControlForAsset('media/credits.txt')).toBe('public, no-cache');

  // Rollback: switching back to v1 manifest continues resolving v1 immutable objects
  expect(assetUrl('/media/models/zone-desk.glb.gz', r2Base, v1Manifest)).toBe(
    'https://assets.felixpy.com/felix-studio/media/models/zone-desk.1111111111.glb.gz',
  );
});

test('production build emits deterministic hashed media manifest and R2 immutable cache policy', async ({}, testInfo) => {
  const output = await mkdtemp(testInfo.outputPath('media-manifest-'));
  try {
    await build({ logLevel: 'silent', build: { outDir: output, reportCompressedSize: false } });
    const manifest = JSON.parse(
      readFileSync(join(output, 'media-manifest.json'), 'utf8'),
    ) as Record<string, string>;
    expect(Object.keys(manifest).length).toBeGreaterThan(80);
    for (const [logical, hashed] of Object.entries(manifest)) {
      expect(logical).not.toBe('/media/credits.txt');
      expect(hashed).not.toBe(logical);
      expect(isImmutableAssetPath(hashed), hashed).toBe(true);
      expect(existsSync(join(output, hashed.slice(1))), hashed).toBe(true);
    }
    // Verify credits.txt stays unhashed for stable license links
    expect(existsSync(join(output, 'media/credits.txt'))).toBe(true);
    // Verify R2 asset collector marks every hashed media/font immutable and only credits.txt no-cache
    const r2Assets = await collectAssets(output);
    const immutableCount = r2Assets.filter(
      (a) => a.cacheControl === 'public, max-age=31536000, immutable',
    ).length;
    const noCacheKeys = r2Assets
      .filter((a) => a.cacheControl !== 'public, max-age=31536000, immutable')
      .map((a) => a.key);
    expect(immutableCount).toBeGreaterThan(80);
    expect(noCacheKeys).toEqual(['media/credits.txt']);
    // Verify R2 deployment script is strictly additive (never deletes prior hashed objects)
    const r2Source = readFileSync('scripts/deploy/r2-assets.mjs', 'utf8');
    expect(r2Source).not.toContain('delete-object');
    expect(r2Source).not.toContain('delete-objects');
  } finally {
    await rm(output, { recursive: true });
  }
});
