import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('T7 housing presents its printed end and a reversible USB-C mating face', async () => {
  const drive = await productModel('samsung-t7.glb');
  drive.updateMatrixWorld(true);
  const materials = new Set<string>();
  drive.traverse((part) => {
    if (!(part instanceof Mesh)) return;
    part.material.side = DoubleSide;
    materials.add(part.material.name);
  });
  expect(materials.has('PWB solder mask')).toBe(false);
  expect(materials.has('Lead-free solder meniscus')).toBe(false);
  function hit(at: number[], direction: number[]) {
    const ray = new Raycaster(new Vector3(...at).multiplyScalar(0.001), new Vector3(...direction));
    return ray.intersectObject(drive)[0];
  }
  for (const z of [-18, 0, 18]) {
    const label = hit([45, 0.24, z], [-1, 0, 0]);
    expect((label.object as Mesh).material.name).toBe('T7 · printed regulatory label');
    expect(Math.abs(label.point.x * 1000 - 42.32)).toBeLessThan(0.02);
    expect(label.uv?.x).toBeCloseTo(0.5 - z / 55.42, 2);
  }
  expect((hit([-45, 1, 0.04], [1, 0, 0]).object as Mesh).material.name).toBe(
    'Connector insert · charcoal LCP',
  );
  for (const side of [-1, 1]) {
    for (let i = 0; i < 12; i++) {
      const finger = hit([-38.75, side * 0.95, (i - 5.5) * 0.5], [0, -side, 0]);
      expect((finger.object as Mesh).material.name).toBe('Connector contact plating');
    }
    const latch = hit([-38.6, 0.03, side * 3.8], [0, 0, -side]);
    expect((latch.object as Mesh).material.name).toBe('Stamped nickel-plated steel');
  }
});
