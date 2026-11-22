import { expect, test } from '@playwright/test';
import { Material, Mesh, Raycaster, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('each sampler switch sits in an open acrylic bore with a continuous rim', async () => {
  const scene = await productModel('bench-instruments.glb');
  scene.updateMatrixWorld(true);
  const tester = scene.children.find((part) => part.userData.benchInstrument === 'tester')!;
  const meshes: Mesh[] = [];
  tester.traverse((part) => {
    if (part instanceof Mesh) meshes.push(part);
  });
  const byMaterial = (name: string) =>
    meshes.find((mesh) => (mesh.material as Material).name === name)!;
  const acrylic = byMaterial('Sampler · optical acrylic');
  const ray = new Raycaster();
  for (let row = 0; row < 3; row++) {
    for (let column = 0; column < 4; column++) {
      const x = (1 - row) * 0.01905;
      const z = (column - 1.5) * 0.01905;
      ray.set(new Vector3(x, 0.0084, z), new Vector3(0, -1, 0));
      expect(ray.intersectObject(acrylic, false)).toHaveLength(0);
      for (const [dx, dz] of [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ]) {
        ray.set(new Vector3(x, 0.006, z), new Vector3(dx, 0, dz));
        expect(ray.intersectObject(acrylic, false)[0]?.distance).toBeCloseTo(0.007025, 4);
      }
      ray.set(new Vector3(x + 0.0085, 0.025, z), new Vector3(0, -1, 0));
      expect(ray.intersectObject(acrylic, false)[0]?.point.y).toBeCloseTo(0.0085, 4);
    }
  }
  const spring = byMaterial('MX · spring wire');
  spring.geometry.computeBoundingBox();
  const bounds = spring.geometry.boundingBox!;
  expect(bounds.getCenter(new Vector3()).z).toBeCloseTo(1.5 * 0.01905, 4);
  expect(bounds.getSize(new Vector3()).x).toBeLessThan(0.0045);
});
