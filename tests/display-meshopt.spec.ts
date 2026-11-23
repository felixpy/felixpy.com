import { expect, test } from '@playwright/test';

test('the default Meshopt decoder mounts the Mac Studio inspection model', async ({ page }) => {
  await page.goto('/robots.txt');
  const { installed, meshCount } = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const displayModel = '/src/scene/display-model.ts';
    const T = (await import(three)) as typeof import('three');
    const { loadDisplayModel } = (await import(
      displayModel
    )) as typeof import('../src/scene/display-model');
    const root = new T.Group();
    let installed = 0;
    await loadDisplayModel(root, '/media/models/mac-studio-m5-ultra.glb', new T.LoadingManager(), {
      mounted: () => installed++,
    });
    let meshCount = 0;
    root.traverse((object) => {
      const mesh = object as import('three').Mesh;
      if (mesh.isMesh && mesh.geometry.attributes.position.count > 0) meshCount++;
    });
    return { installed, meshCount };
  });

  expect(installed).toBe(1);
  expect(meshCount).toBeGreaterThan(0);
});
