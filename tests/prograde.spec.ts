import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('PG05.5 slot and underside legends replace a single shell surface', async () => {
  const reader = await productModel('prograde-pg05-5.glb');
  reader.updateMatrixWorld(true);
  const ink: Mesh[] = [];
  reader.traverse((part) => {
    if (!(part instanceof Mesh)) return;
    (part.material as MeshBasicMaterial).side = DoubleSide;
    if (part.material.name === 'White slot legends') ink.push(part);
  });
  let frontSamples = 0;
  let bottomSamples = 0;
  for (const mesh of ink) {
    const { index, attributes } = mesh.geometry;
    const position = attributes.position;
    const center = new Vector3();
    const vertex = new Vector3();
    for (let i = 0; i < (index?.count ?? position.count); i += 21) {
      center.set(0, 0, 0);
      for (let j = i; j < i + 3; j++) {
        center.add(vertex.fromBufferAttribute(position, index?.getX(j) ?? j));
      }
      mesh.localToWorld(center.divideScalar(3));
      const front = center.z > 0.035;
      const direction = new Vector3(0, front ? 0 : 1, front ? -1 : 0);
      const origin = center.clone().addScaledVector(direction, -0.0004);
      const ray = new Raycaster(origin, direction, 0, 0.00048);
      const hits = ray.intersectObject(reader);
      expect(hits.map((hit) => (hit.object as Mesh).material.name)).toEqual(['White slot legends']);
      if (front) frontSamples++;
      else bottomSamples++;
    }
  }
  expect(frontSamples).toBeGreaterThan(30);
  expect(bottomSamples).toBeGreaterThan(30);
});

test('Type B reader and card share 21 aligned contacts and a clear insertion channel', async () => {
  const [reader, card] = await Promise.all([
    productModel('prograde-pg05-5.glb'),
    productModel('cfexpress-type-b.glb'),
  ]);
  for (const model of [reader, card]) {
    model.updateMatrixWorld(true);
    model.traverse((part) => {
      if (part instanceof Mesh) (part.material as MeshBasicMaterial).side = DoubleSide;
    });
  }
  const banks = [
    -12, -11, -10, -9, -8, -7, -6, -3.2, -2.2, -1.2, 0.2, 1.2, 2.2, 3.2, 6, 7, 8, 9, 10, 11, 12,
  ];
  const seen = (model: typeof card, origin: number[], direction: Vector3, far: number) =>
    new Raycaster(new Vector3(...origin).multiplyScalar(0.001), direction, 0, far / 1000)
      .intersectObject(model)
      .map((hit) => (hit.object as Mesh).material.name);
  for (const x of banks) {
    expect(seen(card, [x, 0, -17.83], new Vector3(0, -1, 0), 1.2)).toContain(
      'Gold-plated contact beams',
    );
    expect(seen(reader, [x + 3.7, 10.82, 3.945], new Vector3(0, -1, 0), 1.2)).toContain(
      'Contact plating',
    );
  }
  for (const x of [-5, 4.7]) {
    expect(seen(card, [x, 0, -17.83], new Vector3(0, -1, 0), 1.2)).not.toContain(
      'Gold-plated contact beams',
    );
    expect(seen(reader, [x + 3.7, 10.82, 3.945], new Vector3(0, -1, 0), 1.2)).not.toContain(
      'Contact plating',
    );
  }
  const socket = reader.clone();
  socket.traverse((part) => {
    if (part instanceof Mesh) {
      part.layers.set(['Stamped card cage', 'Socket polymer'].includes(part.material.name) ? 0 : 1);
    }
  });
  expect(seen(socket, [3.7, 11.65, 35.4], new Vector3(0, 0, -1), 32.625)).toEqual([]);
  expect(seen(socket, [3.7, 11.65, 35.4], new Vector3(0, 0, -1), 34)).toContain('Socket polymer');
});
