import { expect, test } from '@playwright/test';

test('the Meshopt pool and its fallback mount the same inspection geometry', async ({ page }) => {
  async function load(query = '') {
    await page.goto('/robots.txt' + query);
    return page.evaluate(async () => {
      const three = '/node_modules/three/build/three.module.js';
      const displayModel = '/src/scene/display-model.ts';
      const T = (await import(three)) as typeof import('three');
      const { loadDisplayModel } = (await import(
        displayModel
      )) as typeof import('../src/scene/display-model');
      const root = new T.Group();
      let installed = 0;
      await loadDisplayModel(
        root,
        '/media/models/mac-studio-m5-ultra.glb',
        new T.LoadingManager(),
        {
          mounted: () => installed++,
        },
      );
      const parts: { name: string; vertices: number; indices: number; translation: number[] }[] =
        [];
      root.traverse((object) => {
        const mesh = object as import('three').Mesh;
        if (!mesh.isMesh) return;
        parts.push({
          name: mesh.name,
          vertices: mesh.geometry.attributes.position.count,
          indices: mesh.geometry.index?.count ?? 0,
          translation: mesh.getWorldPosition(new T.Vector3()).toArray(),
        });
      });
      return {
        installed,
        parts,
        started: performance.getEntriesByName('studio-meshopt-workers-start').length,
        fellBack: performance.getEntriesByName('studio-meshopt-workers-fallback').length,
      };
    });
  }

  const main = await load();
  expect(main.installed).toBe(1);
  expect(main.parts.length).toBeGreaterThan(0);
  expect(main.started).toBe(0);
  const worker = await load('?studio-meshopt=worker');
  expect(worker).toEqual({ ...main, started: 1 });
  expect(page.workers().some((worker) => worker.url().startsWith('blob:'))).toBe(true);

  await page.addInitScript(() => {
    window.Worker = new Proxy(window.Worker, {
      construct() {
        throw new DOMException('Worker creation is blocked', 'SecurityError');
      },
    });
  });
  expect(await load('?studio-meshopt=worker')).toEqual({ ...main, fellBack: 1 });
});
