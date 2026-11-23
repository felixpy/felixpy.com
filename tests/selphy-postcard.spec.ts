import { expect, test } from '@playwright/test';
import { Material, Mesh, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('the KP-36IP has a registered address face and two perforated tear-off tabs', async () => {
  const printer = await productModel('selphy-cp1500.glb');
  const proof = printer.children.find((part) => part.userData.selphyProof)!;
  expect(proof.userData.paperSet).toBe('Canon KP-36IP');
  proof.removeFromParent();
  proof.position.set(0, 0, 0);
  proof.quaternion.identity();
  proof.updateMatrixWorld(true);
  const ray = new Raycaster();
  const sample = (x: number, y: number, fromBack: boolean) => {
    const sign = fromBack ? 1 : -1;
    ray.set(new Vector3(x / 1000, y / 1000, -0.01 * sign), new Vector3(0, 0, sign));
    return ray.intersectObject(proof, true)[0];
  };
  const front = sample(4, 5, false);
  const back = sample(4, 5, true);
  expect(((front.object as Mesh).material as Material).name).toBe('Selphy postcard image');
  expect(((back.object as Mesh).material as Material).name).toContain('writable address side');
  expect(back.uv!.x).toBeCloseTo((5 + 88.5) / 177, 4);
  expect(back.uv!.y).toBeCloseTo((50 - 4) / 100, 4);
  expect(front.point.z - back.point.z).toBeCloseTo(0.00024, 5);
  for (const crease of [-74, 74]) {
    for (let index = 0; index < 60; index++) {
      const cut = -49.5 + index * 1.665;
      expect(sample(cut + 0.435, crease, false)).toBeUndefined();
      expect(sample(cut + 0.435, crease, true)).toBeUndefined();
      expect(sample(cut + 1.1, crease, false)).toBeDefined();
    }
  }
});
