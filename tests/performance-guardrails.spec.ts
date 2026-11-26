import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';

function collectTsFiles(dir: string): string[] {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'review') continue;
      files.push(...collectTsFiles(full));
    } else if (entry.isFile() && /\.tsx?$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

test('scene modules do not instantiate RectAreaLight and pair every onBeforeCompile with customProgramCacheKey', () => {
  const files = collectTsFiles('src/scene');
  const rectLightFiles: string[] = [];
  const missingCacheKey: string[] = [];

  for (const file of files) {
    const source = readFileSync(file, 'utf8');
    if (/\bnew\s+(?:T\.)?RectAreaLight\b/.test(source)) {
      rectLightFiles.push(file);
    }
    const compileCount = (source.match(/\.onBeforeCompile\s*=(?!=)/g) ?? []).length;
    if (compileCount > 0) {
      const cacheKeyCount = (source.match(/\.customProgramCacheKey\s*=(?!=)/g) ?? []).length;
      if (cacheKeyCount < compileCount) {
        missingCacheKey.push(
          `${file} (${compileCount} onBeforeCompile, ${cacheKeyCount} customProgramCacheKey)`,
        );
      }
    }
  }

  expect(rectLightFiles).toEqual([]);
  expect(missingCacheKey).toEqual([]);
});

test('bookshelf recessed linear light stays inside the left cabinet stile and out of the book bay', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const pose = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const { loadParts } =
      (await import('/src/scene/blender-library.ts')) as typeof import('../src/scene/blender-library');
    await loadParts('studio');
    const { bookshelf } =
      (await import('/src/scene/furniture.ts')) as typeof import('../src/scene/furniture');
    const { materials } =
      (await import('/src/scene/materials.ts')) as typeof import('../src/scene/materials');
    const manager = new T.LoadingManager();
    const loader = new T.TextureLoader(manager);
    const root = new T.Group();
    const palette = materials(loader);
    const { unit } = bookshelf(root, palette, loader, loader, true);
    const channel = unit.getObjectByName('Recessed linear light in cabinet stile');
    return channel
      ? { x: channel.position.x, z: channel.position.z, rotY: channel.rotation.y }
      : null;
  });

  expect(pose).not.toBeNull();
  // Left stile inner edge sits near x = -width/2 + 0.025 (-0.28), z = 0.153, angled into the shelf.
  expect(pose!.x).toBeCloseTo(-0.28, 3);
  expect(pose!.z).toBeCloseTo(0.153, 3);
  expect(pose!.rotY).toBeCloseTo(-Math.PI * 0.49, 3);
});

test('studioReflections.preload eliminates PMREM shader compilation on day/night city switches @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const { studioReflections } =
      (await import('/src/scene/reflections.ts')) as typeof import('../src/scene/reflections');
    const renderer = new T.WebGLRenderer();
    const scene = new T.Scene();
    const reflections = studioReflections(renderer, scene);

    const beforePrograms = (renderer.info.programs ?? []).length;
    await reflections.select(true, 'high', { skipPreview: true });
    await reflections.preload('high');
    const nightEnv = scene.environment;

    const switchStart = performance.now();
    await reflections.select(false, 'high');
    const dayEnv = scene.environment;
    await reflections.select(true, 'high');
    const switchMs = performance.now() - switchStart;
    const afterPrograms = (renderer.info.programs ?? []).length;

    reflections.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
    return {
      nightLoaded: Boolean(nightEnv),
      dayLoaded: Boolean(dayEnv),
      distinctProbes: nightEnv !== dayEnv,
      compiledPrograms: afterPrograms - beforePrograms,
      switchMs,
    };
  });

  expect(result.nightLoaded).toBe(true);
  expect(result.dayLoaded).toBe(true);
  expect(result.distinctProbes).toBe(true);
  expect(result.compiledPrograms).toBe(0);
  expect(result.switchMs).toBeLessThan(50);
});

test('exterior.preloadExposures loads all city exposures and depth maps ahead of switching @webgl', async ({
  page,
}) => {
  const requested = new Set<string>();
  page.on('request', (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith('/media/panoramas/')) requested.add(pathname);
  });
  await page.goto('/robots.txt');
  const loaded = await page.evaluate(async () => {
    const T = (await import('/node_modules/three/build/three.module.js')) as typeof import('three');
    const { buildExterior } =
      (await import('/src/scene/exterior.ts')) as typeof import('../src/scene/exterior');
    const { initialEnvironment } =
      (await import('/src/app/environment.ts')) as typeof import('../src/app/environment');
    const { buildRainGlass } =
      (await import('/src/scene/rain-glass.ts')) as typeof import('../src/scene/rain-glass');
    const { panoramaMeshName } =
      (await import('/src/scene/window-depth.ts')) as typeof import('../src/scene/window-depth');
    const renderer = new T.WebGLRenderer();
    const exterior = buildExterior(
      new T.Group(),
      new T.TextureLoader(),
      buildRainGlass(new T.Vector3(), new T.Vector2(2, 1)),
      initialEnvironment,
    );
    await exterior.preloadExposures(renderer, false);
    const nyDay = {
      ...initialEnvironment,
      city: '纽约' as const,
      night: false,
      weather: '晴' as const,
      reducedMotion: true,
    };
    exterior.update(nyDay, 0, false);
    const plate = exterior.world.getObjectByName(panoramaMeshName) as import('three').Mesh<
      import('three').BufferGeometry,
      import('three').ShaderMaterial
    >;
    const readyImmediately = Boolean(
      plate.material.uniforms.photoB.value?.image && plate.material.uniforms.depthB.value?.image,
    );
    renderer.dispose();
    renderer.forceContextLoss();
    return { readyImmediately };
  });

  expect(loaded.readyImmediately).toBe(true);
  expect(requested.has('/media/panoramas/shanghai-depth.png')).toBe(true);
  expect(requested.has('/media/panoramas/new-york-depth.png')).toBe(true);
  expect(requested.has('/media/panoramas/new-york-day.webp')).toBe(true);
});
