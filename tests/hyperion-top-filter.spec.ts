import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { decodeBlenderMesh } from '../src/scene/blender-mesh';

test('the removable GR701 top has 108 open vents above a separate filter and a rear release', async () => {
  const holes: [number, number, number][] = JSON.parse(
    await readFile(new URL('./fixtures/gr701-roof-apertures.json', import.meta.url), 'utf8'),
  );
  const parts = await Promise.all(
    ['plate', 'frame', 'weave', 'hardware'].map(async (name) => {
      const bytes = await readFile('public/media/models/gr701-top-filter-' + name + '.mesh');
      const piece = new Mesh(
        decodeBlenderMesh(Uint8Array.from(bytes).buffer),
        new MeshBasicMaterial({ side: DoubleSide }),
      );
      piece.name = name;
      return piece;
    }),
  );
  const ray = new Raycaster(new Vector3(), new Vector3(0, -1, 0));
  function top(x: number, z: number) {
    ray.ray.origin.set(x / 1000, 0.035, z / 1000);
    return ray.intersectObjects(parts)[0];
  }
  expect(holes).toHaveLength(108);
  for (const [x, z, span] of holes) {
    const center = top(
      x + span / 2,
      z + ((span - 2.65) * Math.tan((28 * Math.PI) / 180)) / 2 - 2.8,
    );
    expect(center.object.name).toBe('weave');
    expect(center.point.y).toBeCloseTo(0.0061, 5);
  }
  expect(top(73.5, 0).object.name).toBe('plate');
  expect(top(79, 0).object.name).toBe('frame');
  ray.ray.direction.set(0, 0, 1);
  ray.ray.origin.set(0, 0.003, -0.27);
  const well = ray.intersectObjects(parts)[0];
  expect(well.point.z).toBeGreaterThan(-0.231);
  ray.ray.origin.set(0.06, 0.003, -0.27);
  expect(ray.intersectObjects(parts)[0].point.z).toBeLessThan(-0.235);
  ray.ray.origin.set(0, -0.004, -0.27);
  expect(ray.intersectObjects(parts)[0].object.name).toBe('hardware');
});
