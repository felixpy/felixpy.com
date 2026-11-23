import { expect, test } from '@playwright/test';
import { Box3, Mesh, Object3D, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

function castingPart(figure: Object3D, finish: string): Mesh {
  const part = figure.children.find(
    (child) => child instanceof Mesh && child.material.name === `MK85 casting · ${finish}`,
  );
  if (!(part instanceof Mesh)) throw new Error(`Missing MK85 ${finish} surface`);
  return new Mesh(part.geometry, part.material);
}

function eyeBounds(lens: Mesh, chest: Box3) {
  const positions = lens.geometry.getAttribute('position');
  const points: Vector3[] = [];
  for (let index = 0; index < positions.count; index++) {
    if (positions.getY(index) > chest.max.y) {
      points.push(new Vector3().fromBufferAttribute(positions, index));
    }
  }
  const centre = new Box3().setFromPoints(points).getCenter(new Vector3());
  return [
    new Box3().setFromPoints(points.filter((point) => point.x < centre.x)),
    new Box3().setFromPoints(points.filter((point) => point.x > centre.x)),
  ];
}

function interiorClearances(surface: Mesh, backing: Mesh, bounds: Box3) {
  const size = bounds.getSize(new Vector3());
  const ray = new Raycaster(new Vector3(), new Vector3(0, 0, -1));
  const gaps: number[] = [];
  const columns = 26;
  const rows = 25;
  for (let column = 3; column < columns - 3; column++) {
    const x = bounds.min.x + (size.x * (column + 0.5)) / columns;
    const section: number[] = [];
    for (let row = 0; row < rows; row++) {
      const y = bounds.min.y + (size.y * (row + 0.5)) / rows;
      ray.ray.origin.set(x, y, bounds.max.z + size.length());
      const front = ray.intersectObject(surface, false)[0];
      if (!front) continue;
      const back = ray.intersectObject(backing, false)[0];
      if (!back) throw new Error('Missing optical backing behind the window');
      section.push(back.distance - front.distance);
    }
    const interior = section.slice(
      Math.floor(section.length * 0.35),
      Math.ceil(section.length * 0.65),
    );
    gaps.push(...interior);
  }
  return gaps;
}

test('the decoded MK85 eye windows and arc reactor sit in front of their steel backing', async () => {
  const inventory = await productModel('vitrine-inventory.glb');
  const figure = inventory.children.find(
    (item) => item.userData.cabinetItem === 'Tongshifu · Iron Man Mark 85',
  );
  if (!figure) throw new Error('Missing MK85 cabinet figure');
  const lens = castingPart(figure, 'lens');
  const reactor = castingPart(figure, 'crystal');
  const backing = castingPart(figure, 'steel');
  const chest = new Box3().setFromObject(reactor, true);
  const [leftEye, rightEye] = eyeBounds(lens, chest);
  for (const [name, surface, bounds] of [
    ['left eye', lens, leftEye],
    ['right eye', lens, rightEye],
    ['arc reactor', reactor, chest],
  ] as const) {
    const gaps = interiorClearances(surface, backing, bounds);
    expect(gaps.length, `sampled ${name} interior`).toBeGreaterThan(50);
    expect.soft(Math.min(...gaps), `minimum ${name} clearance in meters`).toBeGreaterThan(0);
  }
});
