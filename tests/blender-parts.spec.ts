import { readdirSync, readFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { decodeBlenderMesh } from '../src/scene/blender-mesh';
import { partLibraryPath, unpackParts } from '../src/scene/blender-parts';
import { packedBuffer } from '../src/scene/packed-buffer';

test('both Blender part library formats restore every source mesh byte for byte', async ({
  request,
}) => {
  const root = 'public/media/models';
  const files = readdirSync(root, { recursive: true }).filter((path) => path.endsWith('.mesh'));
  for (const collection of ['studio', 'workshop'] as const) {
    const sources = new Map(
      files
        .filter((path) => basename(path).startsWith('workshop-') === (collection === 'workshop'))
        .map((path) => [path.replaceAll('\\', '/').slice(0, -5), readFileSync(join(root, path))]),
    );
    expect(sources.size).toBeGreaterThan(0);
    for (const version of [1, 2] as const) {
      const url = partLibraryPath(collection, version);
      const response = await request.get(url);
      await expect(response).toBeOK();
      const buffer = await packedBuffer(new Response(new Uint8Array(await response.body())));
      expect(Buffer.from(buffer, 0, 4).toString(), url).toBe('BPK' + version);
      const parts = unpackParts(buffer);
      expect([...parts.keys()].sort(), url).toEqual([...sources.keys()].sort());
      for (const [name, source] of sources)
        expect(Buffer.from(parts.get(name)!).equals(source), url + ' • ' + name).toBe(true);
    }
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
