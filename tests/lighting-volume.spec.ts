import { expect, test } from '@playwright/test';
import { gzipSync } from 'node:zlib';

test('room lighting accepts both compressed files and HTTP-decoded volumes', async ({ page }) => {
  const expected = [45, 200, 8, 31, 74, 16, 9, 92];
  const compressed = gzipSync(Buffer.from(expected));
  await page.route('**/test-light-file.gz', (route) => route.fulfill({ body: compressed }));
  await page.route('**/test-light-transport.gz', (route) =>
    route.fulfill({ headers: { 'content-encoding': 'gzip' }, body: compressed }),
  );
  await page.goto('/robots.txt');
  const read = await page.evaluate(async (length) => {
    const path = '/src/scene/lighting-volume.ts';
    const { lightingVolume } = (await import(
      path
    )) as typeof import('../src/scene/lighting-volume');
    const signal = new AbortController().signal;
    const results = await Promise.all([
      lightingVolume('/test-light-file.gz', length, signal),
      lightingVolume('/test-light-transport.gz', length, signal),
      lightingVolume('/test-light-file.gz', length + 1, signal),
    ]);
    return results.map((volume) => (volume ? Array.from(volume) : null));
  }, expected.length);
  expect(read).toEqual([expected, expected, null]);
});

test('prewarmed surfaces keep their lighting textures when the room reopens @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const sample = await page.evaluate(async () => {
    const threePath = '/node_modules/three/build/three.module.js';
    const geometryPath = '/src/scene/geometry.ts';
    const visibilityPath = '/src/scene/room-visibility.ts';
    const environmentPath = '/src/app/environment.ts';
    const T = (await import(threePath)) as typeof import('three');
    const { box, surface } = (await import(geometryPath)) as typeof import('../src/scene/geometry');
    const { roomVisibility } = (await import(
      visibilityPath
    )) as typeof import('../src/scene/room-visibility');
    const { initialEnvironment } = (await import(
      environmentPath
    )) as typeof import('../src/app/environment');
    const renderer = new T.WebGLRenderer();
    renderer.setSize(16, 16);
    const gl = renderer.getContext();
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(45, 1, 0.1, 10);
    camera.position.z = 2;
    const texture = new T.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    texture.needsUpdate = true;
    const material = surface(0xffffff);
    material.map = texture;
    scene.add(new T.AmbientLight(0xffffff, 2));
    const panel = box(scene, [1, 1, 0.1], [0, 0, 0], material);
    let visibility = roomVisibility([panel], initialEnvironment);
    try {
      visibility.prepareMaterials();
      await renderer.compileAsync(scene, camera);
      visibility.dispose();
      renderer.render(scene, camera);
      visibility = roomVisibility([panel], initialEnvironment);
      visibility.prepareMaterials();
      renderer.render(scene, camera);
      const pixel = new Uint8Array(4);
      gl.readPixels(8, 8, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
      return { red: pixel[0], error: gl.getError() };
    } finally {
      visibility.dispose();
      panel.geometry.dispose();
      material.dispose();
      texture.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(sample.error).toBe(0);
  expect(sample.red).toBeGreaterThan(100);
});
