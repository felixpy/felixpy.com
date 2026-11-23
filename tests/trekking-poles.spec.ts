import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('both Solution wristbands wrap around their grip axle after export', async () => {
  const equipment = await productModel('camp-field-equipment.glb');
  const poles = equipment.children.filter((part) =>
    part.userData.fieldItem?.startsWith('alpine-carbon-cork-'),
  );
  expect(poles).toHaveLength(2);
  const ray = new Raycaster();
  const section = new MeshBasicMaterial({ side: DoubleSide });
  for (const pole of poles) {
    const hand = pole.userData.fieldItem.endsWith('left') ? -1 : 1;
    const strap = pole.children.find((part) => part.name.includes('Solution'))!;
    const surfaces: Mesh[] = [];
    strap.traverse((part) => {
      if (part instanceof Mesh) surfaces.push(new Mesh(part.geometry, section));
    });
    for (const depth of [-0.0045, -0.0015]) {
      const axle = new Vector3(hand * 0.0136, 0.5968, depth);
      for (const degrees of [10, 45, 90, 135, 170]) {
        const angle = (degrees * Math.PI) / 180;
        ray.set(axle, new Vector3(hand * Math.cos(angle), Math.sin(angle), 0));
        ray.far = 0.0023;
        const hits = ray.intersectObjects(surfaces);
        const sample = pole.name + ' / ' + depth + ' m / ' + degrees + '°';
        expect(hits.length, sample).toBeGreaterThanOrEqual(2);
        const inner = hits[0].distance;
        const thickness = hits[hits.length - 1].distance - inner;
        expect(inner, sample).toBeGreaterThan(0.00116);
        expect(inner, sample).toBeLessThan(0.0013);
        expect(thickness, sample).toBeGreaterThan(0.0003);
        expect(thickness, sample).toBeLessThan(0.00062);
      }
    }
  }
});
