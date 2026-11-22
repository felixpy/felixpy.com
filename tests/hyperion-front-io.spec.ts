import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { decodeBlenderMesh } from '../src/scene/blender-mesh';

test('the GR701 front plate has six recessed USB sockets, jack and distinct left and right switches', async () => {
  const surfaces = await Promise.all(
    ['cover', 'well', 'contact', 'key'].map(async (name) => {
      const bytes = await readFile('public/media/models/gr701-front-io-' + name + '.mesh');
      const piece = new Mesh(
        decodeBlenderMesh(Uint8Array.from(bytes).buffer),
        new MeshBasicMaterial({ side: DoubleSide }),
      );
      piece.name = name;
      return piece;
    }),
  );
  const ray = new Raycaster(new Vector3(), new Vector3(0, -1, 0));
  function probe(x: number, z: number) {
    ray.ray.origin.set(x / 1000, 0.03, z / 1000);
    const hit = ray.intersectObjects(surfaces)[0];
    return { surface: hit.object.name, height: hit.point.y * 1000 };
  }
  for (const x of [-43.4, -20.5, 20.5, 43.4]) {
    expect(probe(x, -3.35).height).toBeLessThan(3.0);
    expect(probe(x, -1.69).height).toBeGreaterThan(7.0);
    expect(probe(x + 6.7, -3.35).surface).toBe('contact');
  }
  for (const x of [-20.5, 20.5]) {
    expect(probe(x, 12.8).surface).toBe('well');
    expect(probe(x, 12.8).height).toBeGreaterThan(7.0);
    expect(probe(x, 13.8).height).toBeLessThan(3.0);
    expect(probe(x, 14.69).surface).toBe('contact');
  }
  expect(probe(0, -3.35).height).toBeLessThan(3.0);
  expect(probe(2.5, -3.35).surface).toBe('contact');
  expect(probe(-43.4, 12.8).height).toBeGreaterThan(probe(43.4, 12.8).height + 0.5);
  for (const x of [-51.1, -43.4, -35.7]) {
    expect(probe(x, 21.5).surface).toBe('well');
  }
  expect(probe(0, -20).surface).toBe('key');
  expect(probe(13, -24).surface).toBe('key');
  expect(probe(13, -17.5).surface).toBe('cover');
});
