import { expect, test } from '@playwright/test';
import azothLayout from '../scripts/assets/azoth-keycap-inlays.json' with { type: 'json' };
import {
  Box3,
  DoubleSide,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  Raycaster,
  Triangle,
  Vector3,
} from 'three';
import { productModel } from './helpers/product-model';

function surface(root: Object3D, materialName: string) {
  const meshes: Mesh[] = [];
  root.traverse((part) => {
    if (part instanceof Mesh && part.material.name.includes(materialName)) meshes.push(part);
  });
  expect(meshes).toHaveLength(1);
  return meshes[0].geometry;
}

test('the cabinet has five distinct readable lenses and the standard zoom stays on the Z8', async () => {
  const [inventory, mounted] = await Promise.all([
    productModel('vitrine-inventory.glb'),
    productModel('nikkor-z24-70-sii.glb'),
  ]);
  expect(mounted.children.map((part) => part.userData.name).sort()).toEqual([
    'NIKKOR Z 24-70mm f2.8 S II',
    'Z8 body-side mount receiver',
  ]);
  inventory.updateMatrixWorld(true);
  const lenses = inventory.children.filter((item) =>
    item.userData.cabinetItem?.startsWith('NIKKOR'),
  );
  expect(lenses.map((lens) => lens.userData.cabinetItem).sort()).toEqual([
    'NIKKOR Z 100-400mm f4.5-5.6 VR S',
    'NIKKOR Z 135mm f1.8 S Plena',
    'NIKKOR Z 14-24mm f2.8 S',
    'NIKKOR Z 58mm f0.95 S Noct',
    'NIKKOR Z 70-200mm f2.8 VR S II',
  ]);
  const bounds = lenses.map((lens) => new Box3().setFromObject(lens, true));
  bounds.sort((a, b) => a.min.x - b.min.x);
  for (const [i, box] of bounds.entries()) {
    expect(box.min.y).toBeGreaterThanOrEqual(0.9708);
    expect(box.max.y).toBeLessThan(1.267);
    expect(box.min.z).toBeGreaterThan(0.0305);
    expect(box.max.z).toBeLessThan(0.348);
    if (i) expect(box.min.x - bounds[i - 1].max.x).toBeGreaterThan(0.025);
  }
  for (const lens of lenses) {
    const marking = lens.localToWorld(new Vector3(0, 0.012, 0.035));
    const outward = new Vector3(0, 0, 1).transformDirection(lens.matrixWorld);
    for (const eye of [new Vector3(0.098, 1.027, 1.244), new Vector3(0.066, 0.991, 0.897)]) {
      const sightline = eye.clone().sub(marking);
      expect(outward.dot(sightline.clone().normalize()), lens.name).toBeGreaterThan(0.97);
      for (const [edge, depth] of [
        [0.012, 0.35],
        [-0.012, 0.359],
      ]) {
        const x = marking.x + ((depth - marking.z) * sightline.x) / sightline.z;
        expect(Math.abs(x - edge), lens.name).toBeGreaterThan(0.028);
      }
    }
  }
});

test('Mac rear markings occupy the aluminum surface in both exported detail levels', async () => {
  for (const suffix of ['', '-room']) {
    const model = await productModel('mac-studio-m5-ultra' + suffix + '.glb');
    model.updateMatrixWorld(true);
    for (const x of [0.053, 0.0242, -0.0269, -0.0504, -0.0671]) {
      const ray = new Raycaster(new Vector3(x, 0.034, -0.11), new Vector3(0, 0, 1), 0, 0.012);
      const hits = ray.intersectObject(model);
      expect(hits, 'surfaces at a rear connector marking').toHaveLength(1);
      expect((hits[0].object as Mesh).material.name).toBe('Laser etched aluminum');
      expect(hits[0].point.z).toBeCloseTo(-0.0985, 5);
    }
  }
});

test('lettering on both packed poles remains outside the carbon shaft after web compression', async () => {
  const equipment = await productModel('camp-field-equipment.glb');
  const poles = equipment.children.filter((part) =>
    part.userData.fieldItem?.startsWith('alpine-carbon-cork-'),
  );
  expect(poles).toHaveLength(2);
  for (const pole of poles) {
    const upper = pole.children.find((part) => part.name.includes('Tundra_upper'))!;
    const print = surface(upper, 'screened');
    const shaft = new Mesh(surface(upper, 'lacquer'), new MeshBasicMaterial({ side: DoubleSide }));
    const position = print.getAttribute('position');
    const count = print.index?.count ?? position.count;
    const center = new Vector3(),
      vertex = new Vector3(),
      normal = new Vector3(),
      ray = new Raycaster();
    let minimum = Infinity;
    let maximum = -Infinity;
    for (let tri = 0; tri < count; tri += 3) {
      center.set(0, 0, 0);
      for (let corner = tri; corner < tri + 3; corner++) {
        center.add(vertex.fromBufferAttribute(position, print.index?.getX(corner) ?? corner));
      }
      center.divideScalar(3);
      normal.copy(center).setY(0).normalize();
      ray.ray.origin.copy(center).addScaledVector(normal, 0.015);
      ray.ray.direction.copy(normal).negate();
      const [hit] = ray.intersectObject(shaft);
      if (!hit) throw new Error('No shaft beneath ' + pole.name + ' lettering');
      const clearance = hit.distance - 0.015;
      minimum = Math.min(minimum, clearance);
      maximum = Math.max(maximum, clearance);
    }
    expect(count).toBeGreaterThan(0);
    expect(minimum, pole.name + ' ink clearance in meters').toBeGreaterThan(0);
    expect(maximum, pole.name + ' ink lift in meters').toBeLessThan(0.00015);
  }
});

function trianglesWithFinish(root: Object3D, material: RegExp) {
  const triangles: Triangle[] = [];
  root.updateMatrixWorld(true);
  root.traverse((part) => {
    if (!(part instanceof Mesh) || !material.test(part.material.name)) return;
    const { index, attributes } = part.geometry;
    const vertices = attributes.position;
    const vertex = (i: number) =>
      new Vector3()
        .fromBufferAttribute(vertices, index?.getX(i) ?? i)
        .applyMatrix4(part.matrixWorld);
    for (let i = 0; i < (index?.count ?? vertices.count); i += 3) {
      triangles.push(new Triangle(vertex(i), vertex(i + 1), vertex(i + 2)));
    }
  });
  return triangles;
}

function insideContour(x: number, z: number, contour: number[][]) {
  let inside = false;
  for (let i = 0, last = contour.length - 1; i < contour.length; last = i++) {
    const [ax, az] = contour[last];
    const [bx, bz] = contour[i];
    if (az > z !== bz > z && x < ax + ((z - az) * (bx - ax)) / (bz - az)) inside = !inside;
  }
  return inside;
}

test('all 81 Azoth inlays preserve the ASUS guide glyphs, counters and layout in the web mesh', async () => {
  const keyboard = await productModel('rog-azoth-extreme.glb');
  const faces = trianglesWithFinish(keyboard, /^Azoth legend \d+$/).map((face) => {
    const vertices = [face.a, face.b, face.c].map((p) => [p.x * 1000, p.z * 1000]);
    return {
      vertices,
      minX: Math.min(...vertices.map((p) => p[0])),
      maxX: Math.max(...vertices.map((p) => p[0])),
      minZ: Math.min(...vertices.map((p) => p[1])),
      maxZ: Math.max(...vertices.map((p) => p[1])),
    };
  });
  const keys = azothLayout.rows.flat();
  expect(keys).toHaveLength(81);
  const skirtInk = trianglesWithFinish(keyboard, /Azoth · silver transfer$/).map((triangle) => ({
    center: triangle.getMidpoint(new Vector3()).multiplyScalar(1000),
    normal: triangle.getNormal(new Vector3()),
  }));
  for (const key of keys.filter((key) => key.front.length > 0)) {
    const print = skirtInk.filter(
      ({ center }) =>
        Math.abs(center.x - key.x) < key.width / 2 &&
        center.z > key.z + 7.6 &&
        center.z < key.z + 9.1 &&
        center.y > 20,
    );
    expect.soft(print.length, key.key + ' front markings').toBeGreaterThan(0);
    expect
      .soft(
        print.filter(({ normal }) => normal.lengthSq() > 0).every(({ normal }) => normal.z > 0.85),
        key.key + ' front markings face outward',
      )
      .toBe(true);
  }
  for (const key of keys) {
    const ink = faces.filter(
      (f) =>
        Math.abs((f.minX + f.maxX) / 2 - key.x) < key.width / 2 &&
        Math.abs((f.minZ + f.maxZ) / 2 - key.z) < key.height / 2,
    );
    let intersection = 0;
    let union = 0;
    for (let z = -key.height / 2 + 0.07; z < key.height / 2; z += 0.17) {
      for (let x = -key.width / 2 + 0.09; x < key.width / 2; x += 0.17) {
        const reference = key.top.filter((loop) => insideContour(x, z, loop)).length % 2 === 1;
        const px = key.x + x,
          pz = key.z + z;
        const actual = ink.some(
          (f) =>
            px >= f.minX &&
            px <= f.maxX &&
            pz >= f.minZ &&
            pz <= f.maxZ &&
            insideContour(px, pz, f.vertices),
        );
        if (actual || reference) union++;
        if (actual && reference) intersection++;
      }
    }
    expect.soft(intersection / union, key.key + ' ink overlap').toBeGreaterThan(0.92);
  }
});

test('Azoth top legends clear the dished surface of each keycap after web compression', async () => {
  const keyboard = await productModel('rog-azoth-extreme.glb');
  const caps = trianglesWithFinish(keyboard, /graphite doubleshot PBT$/).map(({ a, b, c }) => ({
    heights: new Vector3(a.y, b.y, c.y),
    footprint: new Triangle(a.setY(0), b.setY(0), c.setY(0)),
  }));
  const ink = trianglesWithFinish(keyboard, /^Azoth legend \d+$/).map((triangle) =>
    triangle.getMidpoint(new Vector3()),
  );
  const weights = new Vector3();
  const projected = new Vector3();
  const pitch = 0.01905;
  const rows = [
    { labels: '1234567890', precedingUnits: 1, z: -0.027 },
    { labels: 'QWERTYUIOP', precedingUnits: 1.5, z: -0.00795 },
    { labels: 'ASDFGHJKL', precedingUnits: 1.75, z: 0.0111 },
  ];
  for (const { labels, precedingUnits, z } of rows) {
    for (let i = 0; i < labels.length; i++) {
      const x = -0.1571 + (precedingUnits + i + 0.5) * pitch;
      const onKey = (p: Vector3) => Math.abs(p.x - x) < pitch / 2 && Math.abs(p.z - z) < pitch / 2;
      const surface = caps.filter(({ footprint: t }) => [t.a, t.b, t.c].some(onKey));
      const strokes = ink.filter(onKey);
      expect(strokes.length, labels[i] + ' legend triangles').toBeGreaterThan(0);
      let min = Infinity;
      let max = -Infinity;
      for (const center of strokes) {
        projected.copy(center).setY(0);
        let top = -Infinity;
        for (const { footprint, heights } of surface) {
          if (!footprint.getBarycoord(projected, weights)) continue;
          if (Math.min(weights.x, weights.y, weights.z) < -1e-7) continue;
          top = Math.max(top, heights.dot(weights));
        }
        expect(Number.isFinite(top), labels[i] + ' cap beneath legend').toBe(true);
        min = Math.min(min, center.y - top);
        max = Math.max(max, center.y - top);
      }
      expect.soft(min, labels[i] + ' minimum legend clearance (m)').toBeGreaterThan(0);
      expect.soft(max, labels[i] + ' maximum legend clearance (m)').toBeLessThan(0.00035);
    }
  }
});
