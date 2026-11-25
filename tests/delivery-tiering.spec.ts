import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { expect, test } from '@playwright/test';
import * as T from 'three';
import { decodePmrem } from '../src/scene/pmrem-decode';

test('offline PMR2 cubemaps decode losslessly into 6-mip HalfFloat PMREM cube textures', () => {
  for (const name of ['desk-day', 'desk-night', 'aj-day', 'aj-night', 'camp-day', 'camp-night']) {
    const gz = readFileSync(`public/media/lighting/${name}.pmrem.gz`);
    const raw = gunzipSync(gz);
    const buffer = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength);
    const cube = decodePmrem(buffer);
    expect(cube.isCompressedCubeTexture).toBe(true);
    expect((cube as unknown as { isPMREMTexture: boolean }).isPMREMTexture).toBe(true);
    expect((cube as unknown as { isRenderTargetTexture: boolean }).isRenderTargetTexture).toBe(
      true,
    );
    expect(cube.type).toBe(T.HalfFloatType);
    expect(cube.format).toBe(T.RGBAFormat);
    expect(cube.image).toHaveLength(6);
    const face0 = cube.image[0] as unknown as {
      mipmaps: Array<{ width: number; height: number; data: Uint16Array }>;
    };
    expect(face0.mipmaps.map((m) => m.width)).toEqual([128, 64, 32, 16, 8, 4]);
    expect(face0.mipmaps[0].data.length).toBe(128 * 128 * 4);
    // Verify non-zero radiance decoded on mip 0
    let maxVal = 0;
    for (let i = 0; i < face0.mipmaps[0].data.length; i += 4) {
      maxVal = Math.max(maxVal, T.DataUtils.fromHalfFloat(face0.mipmaps[0].data[i]));
    }
    expect(maxVal).toBeGreaterThan(0.05);
    cube.dispose();
  }
});

test('fixture reflections load pre-baked PMREM cubemaps and studioReflections supports skipPreview @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const { fixtureReflections } =
      (await import('/src/scene/fixture-reflections.ts')) as typeof import('../src/scene/fixture-reflections');
    const { studioReflections } =
      (await import('/src/scene/reflections.ts')) as typeof import('../src/scene/reflections');
    const renderer = new T.WebGLRenderer();
    const scene = new T.Scene();
    const material = new T.MeshStandardMaterial({ roughness: 0.1, metalness: 1 });
    const fixture = fixtureReflections('aj');
    fixture.bind(material);
    await fixture.preload();
    const envMap = material.envMap as (T.Texture & { isPMREMTexture?: boolean }) | null;
    const fixtureIsPmrem = Boolean(envMap?.isCompressedCubeTexture && envMap?.isPMREMTexture);

    const reflections = studioReflections(renderer, scene);
    const beforePrograms = (renderer.info.programs ?? []).length;
    const selectPromise = reflections.select(true, 'high', { skipPreview: true });
    const envBeforeLoad = scene.environment;
    await selectPromise;
    const envAfterLoad = scene.environment as (T.Texture & { isPMREMTexture?: boolean }) | null;
    const afterPrograms = (renderer.info.programs ?? []).length;

    reflections.dispose();
    material.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
    return {
      fixtureIsPmrem,
      skippedPreview: envBeforeLoad === null,
      loadedPmrem: Boolean(envAfterLoad?.isCompressedCubeTexture && envAfterLoad?.isPMREMTexture),
      compiledPmremPrograms: afterPrograms - beforePrograms,
    };
  });
  expect(result.fixtureIsPmrem).toBe(true);
  expect(result.skippedPreview).toBe(true);
  expect(result.loadedPmrem).toBe(true);
  expect(result.compiledPmremPrograms).toBe(0);
});

test('5K panoramas load at 2.5K in room view and upgrade cleanly on close-up window inspection', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith('/media/panoramas/')) requests.push(pathname);
  });
  await page.goto('/robots.txt');
  const assets = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const { buildExterior } =
      (await import('/src/scene/exterior.ts')) as typeof import('../src/scene/exterior');
    const { initialEnvironment } =
      (await import('/src/app/environment.ts')) as typeof import('../src/app/environment');
    const { buildRainGlass } =
      (await import('/src/scene/rain-glass.ts')) as typeof import('../src/scene/rain-glass');
    const { panoramaMeshName } =
      (await import('/src/scene/window-depth.ts')) as typeof import('../src/scene/window-depth');
    const manager = new T.LoadingManager();
    const loaded = new Promise<void>((resolve) => {
      manager.onLoad = resolve;
    });
    const env = {
      ...initialEnvironment,
      city: '上海' as const,
      night: false,
      weather: '阴' as const,
      reducedMotion: true,
    };
    const exterior = buildExterior(
      new T.Group(),
      new T.TextureLoader(manager),
      buildRainGlass(new T.Vector3(), new T.Vector2(2, 1)),
      env,
    );
    await loaded;
    exterior.update(env, 0, false);
    const plate = exterior.world.getObjectByName(panoramaMeshName) as import('three').Mesh<
      import('three').BufferGeometry,
      import('three').ShaderMaterial
    >;
    const roomSrc = new URL(plate.material.uniforms.photoA.value.image.src).pathname;
    // Now trigger close-up window inspection upgrade to 5K
    exterior.update(env, 0, true);
    await new Promise<void>((resolve) => {
      const check = () => {
        exterior.update(env, 0, true);
        const cur = new URL(plate.material.uniforms.photoA.value.image.src).pathname;
        if (cur.endsWith('/shanghai-day.webp')) resolve();
        else setTimeout(check, 25);
      };
      check();
    });
    const closeSrc = new URL(plate.material.uniforms.photoA.value.image.src).pathname;
    return { roomSrc, closeSrc };
  });
  expect(assets).toEqual({
    roomSrc: '/media/panoramas/shanghai-day-room.webp',
    closeSrc: '/media/panoramas/shanghai-day.webp',
  });
  expect(requests).toContain('/media/panoramas/shanghai-day-room.webp');
  expect(requests).toContain('/media/panoramas/shanghai-day.webp');
});
