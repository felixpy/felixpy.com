import { readdirSync, readFileSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { build } from 'vite';
import { decodeBlenderMesh } from '../src/scene/blender-mesh';
import { partLibraryPath, unpackParts } from '../src/scene/blender-parts';
import { packedBuffer } from '../src/scene/packed-buffer';
import { workshopToolParts } from '../src/scene/workshop-tool-parts';

test('the room and deferred workshop archives partition the Blender meshes losslessly', async ({
  request,
}) => {
  const root = 'public/media/models';
  const files = readdirSync(root, { recursive: true }).filter((path) => path.endsWith('.mesh'));
  const sources = new Map(files.map((file) => [file.slice(0, -5).replaceAll('\\', '/'), file]));
  const restored = new Set<string>();
  for (const collection of ['studio', 'workshop'] as const) {
    const url = partLibraryPath(collection);
    const response = await request.get(url);
    await expect(response).toBeOK();
    const buffer = await packedBuffer(new Response(new Uint8Array(await response.body())));
    expect(Buffer.from(buffer, 0, 4).toString()).toBe('BPK2');
    const parts = unpackParts(buffer);
    if (collection === 'workshop')
      expect([...parts.keys()].sort()).toEqual(Object.values(workshopToolParts).sort());
    for (const [name, bytes] of parts) {
      expect(restored.has(name), name).toBe(false);
      const source = readFileSync(join(root, sources.get(name)!));
      expect(Buffer.from(bytes).equals(source), name).toBe(true);
      restored.add(name);
    }
  }
  expect([...restored].sort()).toEqual([...sources.keys()].sort());
});

test('standalone botanical and printer assemblies still load their original BPK1 geometry', async () => {
  for (const file of ['sill-botanicals.mesh.gz', 'h3c.mesh.gz']) {
    const buffer = await packedBuffer(
      new Response(new Uint8Array(readFileSync(join('public/media/models', file)))),
    );
    expect(Buffer.from(buffer, 0, 4).toString(), file).toBe('BPK1');
    const parts = unpackParts(buffer);
    expect(parts.size).toBeGreaterThan(1);
    for (const bytes of parts.values()) expect(Buffer.from(bytes, 0, 4).toString()).toBe('BMS1');
  }
});

test('the studio part Worker returns the original mesh bytes', async ({ page }) => {
  await page.goto('/robots.txt?studio-parts=worker');
  const result = await page.evaluate(async () => {
    const libraryModule = '/src/scene/blender-library.ts';
    const partsModule = '/src/scene/blender-parts.ts';
    const packedBufferModule = '/src/scene/packed-buffer.ts';
    const { loadParts, meshBytes } = (await import(
      libraryModule
    )) as typeof import('../src/scene/blender-library');
    const { partLibraryPath, unpackParts } = (await import(
      partsModule
    )) as typeof import('../src/scene/blender-parts');
    const { packedBuffer } = (await import(
      packedBufferModule
    )) as typeof import('../src/scene/packed-buffer');
    await loadParts('studio');
    const mainParts = unpackParts(await fetch(partLibraryPath('studio')).then(packedBuffer));
    return {
      transferred: mainParts.size,
      mismatch: [...mainParts].find(([name, buffer]) => {
        const input = new Uint8Array(buffer);
        const output = new Uint8Array(meshBytes(name));
        return (
          input.length !== output.length || input.some((byte, index) => byte !== output[index])
        );
      })?.[0],
      usedWorker: performance.getEntriesByName('studio-parts-studio-worker-unpack').length === 1,
      fellBack: performance.getEntriesByName('studio-parts-studio-worker-fallback').length !== 0,
    };
  });
  expect(result.transferred).toBeGreaterThan(0);
  expect(result.mismatch).toBeUndefined();
  expect(result.usedWorker).toBe(true);
  expect(result.fellBack).toBe(false);
});

test('the studio library retries on the main thread when a Worker loses the transferred input', async ({
  page,
}) => {
  await page.context().route('**/blender-parts.worker.ts?*', (route) =>
    route.fulfill({
      contentType: 'text/javascript',
      body: 'postMessage("ready"); onmessage = () => postMessage({ error: "Unable to unpack" });',
    }),
  );
  await page.goto('/robots.txt?studio-parts=worker');
  const result = await page.evaluate(async () => {
    const libraryModule = '/src/scene/blender-library.ts';
    const { loadParts, meshBytes } = (await import(
      libraryModule
    )) as typeof import('../src/scene/blender-library');
    const first = loadParts('studio');
    const other = loadParts('studio');
    await Promise.all([first, other]);
    return {
      samePromise: first === other,
      fetches: performance.getEntriesByName('studio-parts-studio-fetch-start').length,
      fellBack: performance.getEntriesByName('studio-parts-studio-worker-fallback').length === 1,
      mesh: new TextDecoder().decode(new Uint8Array(meshBytes('astral-impeller-shell'), 0, 4)),
    };
  });
  expect(result).toEqual({ samePromise: true, fetches: 2, fellBack: true, mesh: 'BMS1' });
});

test('the static build serves only the model deliveries available to site visitors', async ({
  request,
}, testInfo) => {
  const output = await mkdtemp(testInfo.outputPath('static-site-'));
  try {
    await build({ logLevel: 'silent', build: { outDir: output, reportCompressedSize: false } });
    const html = readFileSync(join(output, 'index.html'), 'utf8');
    const preloaded = Array.from(html.matchAll(/href="([^"]+\.bpk)"/g), (match) => match[1]);
    expect(preloaded).toEqual([partLibraryPath('studio')]);
    const models = 'media/models';
    const sources = readdirSync(join('public', models), { recursive: true, withFileTypes: true });
    const expected = [partLibraryPath('studio'), partLibraryPath('workshop')];
    for (const file of sources) {
      if (!file.isFile() || file.name.endsWith('.mesh')) continue;
      const path = '/' + relative('public', join(file.parentPath, file.name)).replaceAll('\\', '/');
      expected.push(file.name.endsWith('.glb') ? path + '.gz' : path);
    }
    const delivered = readdirSync(join(output, models), { recursive: true, withFileTypes: true })
      .filter((file) => file.isFile())
      .map(
        (file) => '/' + relative(output, join(file.parentPath, file.name)).replaceAll('\\', '/'),
      );
    expect(delivered.sort()).toEqual(expected.sort());
    for (const url of [
      partLibraryPath('studio'),
      partLibraryPath('workshop'),
      '/media/models/strix-z890-a.glb.gz',
      '/media/models/stationery/career-album.glb.gz',
    ]) {
      const dev = await request.get(url);
      await expect(dev).toBeOK();
      expect((await dev.body()).equals(readFileSync(join(output, url))), url).toBe(true);
    }
  } finally {
    await rm(output, { recursive: true });
  }
});

test('Astral end frame has recessed bores above two staggered rows of sealed heatpipes', () => {
  const material = new MeshBasicMaterial({ side: DoubleSide });
  function casting(finish: string) {
    const file = readFileSync('public/media/models/astral-casting-' + finish + '.mesh');
    return new Mesh(decodeBlenderMesh(Uint8Array.from(file).buffer), material);
  }
  const frame = casting('graphite');
  const sleeves = casting('black');
  const seals = casting('satin');
  function edgeDepthMm(part: Mesh, x: number, y: number) {
    const ray = new Raycaster(new Vector3(x / 1000, y / 1000, 0.2), new Vector3(0, 0, -1));
    const hit = ray.intersectObject(part)[0];
    expect(hit, `End face at ${x}, ${y} mm`).toBeDefined();
    return hit.point.z * 1000;
  }
  for (const x of [2.8, 33.9, 64.4]) {
    expect(edgeDepthMm(frame, x - 4, 23.4) - edgeDepthMm(frame, x, 23.4)).toBeCloseTo(7.8, 1);
  }
  for (const [row, xs] of [
    [10.3, [-42, -16, 10, 36]],
    [-10.3, [-28, -2, 24, 50]],
  ] as const) {
    for (const x of xs) {
      const tip = edgeDepthMm(seals, x + 0.8, row);
      expect(tip).toBeGreaterThan(edgeDepthMm(sleeves, x + 2.8, row));
      expect(tip).toBeLessThan(edgeDepthMm(frame, x, 25));
    }
  }
});
