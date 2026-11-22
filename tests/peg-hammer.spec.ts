import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('both PRO.C retaining pins and the stake-pulling eye remain open after compression', async () => {
  const equipment = await productModel('camp-field-equipment.glb');
  const tool = equipment.children.find(
    (part) => part.userData.name === 'Snow Peak Peg Hammer PRO.C N-001',
  )!;
  const pieces: Mesh[] = [];
  tool.traverse((part) => {
    if (!(part instanceof Mesh)) return;
    const material = new MeshBasicMaterial({ side: DoubleSide });
    material.name = part.material.name;
    pieces.push(new Mesh(part.geometry, material));
  });
  const ray = new Raycaster();
  ray.far = 0.06;
  function through(x: number, y: number, side: number) {
    ray.set(new Vector3(x, y, side * 0.03), new Vector3(0, 0, -side));
    return ray.intersectObjects<Mesh>(pieces).map((hit) => hit.object.material.name);
  }
  for (const side of [-1, 1]) {
    expect(through(0.038, 0.009, side)).toHaveLength(0);
    for (const x of [-0.0221, 0.0023]) {
      expect(through(x, 0, side)).toHaveLength(0);
      expect(through(x + 0.0008, 0, side)).toHaveLength(0);
      expect(through(x + 0.00172, 0, side)[0]).toBe('PRO.C · steel pins and eyelet');
      expect(through(x + 0.0033, 0, side)[0]).toBe('PRO.C · black electrodeposited forged steel');
    }
  }
});
