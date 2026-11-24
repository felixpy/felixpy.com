import { expect, test } from '@playwright/test';
import { zoneBundleIds, zoneBundleModels, zoneBundlePath } from '../src/scene/zone-bundles';

test('all four spatial zone bundles deliver every bundled model in a single fetch and fall back on failure', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith('/media/models/')) requests.push(pathname);
  });
  await page.goto('/robots.txt');
  const result = await page.evaluate(
    async ({ ids, models }) => {
      const three = '/node_modules/three/build/three.module.js';
      const T = (await import(three)) as typeof import('three');
      const displayModule = '/src/scene/display-model.ts';
      const { loadDisplayModel, resetZoneBundleCache } = (await import(
        displayModule
      )) as typeof import('../src/scene/display-model');
      resetZoneBundleCache();
      const counts: Record<string, number> = {};
      for (const zone of ids) {
        const manager = new T.LoadingManager();
        const roots = models[zone].map(() => new T.Group());
        await Promise.all(
          models[zone].map((path, index) => loadDisplayModel(roots[index], path, manager)),
        );
        counts[zone] = roots.filter((root) => {
          let meshes = 0;
          root.traverse((node) => {
            if ((node as T.Mesh).isMesh) meshes++;
          });
          return meshes > 0;
        }).length;
      }
      return counts;
    },
    { ids: [...zoneBundleIds], models: zoneBundleModels },
  );
  for (const zone of zoneBundleIds) {
    expect(result[zone], zone).toBe(zoneBundleModels[zone].length);
    expect(requests.filter((p) => p === zoneBundlePath(zone) + '.gz')).toHaveLength(1);
  }
  expect(requests).toHaveLength(4);

  // Verify graceful fallback to standalone .glb.gz when a zone bundle fails.
  const fallbackRequests: string[] = [];
  await page.route('**/zone-north.glb.gz*', (route) => route.abort());
  page.on('request', (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith('/media/models/')) fallbackRequests.push(pathname);
  });
  const fallbackMeshes = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const T = (await import(three)) as typeof import('three');
    const displayModule = '/src/scene/display-model.ts';
    const { loadDisplayModel, resetZoneBundleCache } = (await import(
      displayModule
    )) as typeof import('../src/scene/display-model');
    resetZoneBundleCache();
    const root = new T.Group();
    await loadDisplayModel(root, '/media/models/window-cradle.glb', new T.LoadingManager());
    let meshes = 0;
    root.traverse((node) => {
      if ((node as T.Mesh).isMesh) meshes++;
    });
    return meshes;
  });
  expect(fallbackMeshes).toBeGreaterThan(0);
  expect(fallbackRequests).toContain('/media/models/window-cradle.glb.gz');
});
