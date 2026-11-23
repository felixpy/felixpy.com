import { expect, test } from '@playwright/test';

test('the three cabinet OLED covers remain visible across their recessed openings', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const results = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const displayModel = '/src/scene/display-model.ts';
    const T = (await import(three)) as typeof import('three');
    const { loadDisplayModel } = (await import(
      displayModel
    )) as typeof import('../src/scene/display-model');
    const mount = new T.Group();
    await loadDisplayModel(mount, '/media/models/vitrine-inventory.glb', new T.LoadingManager());
    const lenses = mount.children[0].children.filter((lens) =>
      [0, 4, 5].includes(lens.userData.opticalVariant),
    );
    return lenses.map((lens) => {
      lens.removeFromParent();
      lens.position.set(0, 0, 0);
      lens.quaternion.identity();
      lens.updateMatrixWorld(true);
      const parts: import('three').Mesh[] = [];
      lens.traverse((part) => {
        if ((part as import('three').Mesh).isMesh) parts.push(part as import('three').Mesh);
      });
      const cover = parts.find((part) =>
        /polarizing cover|inactive OLED glass/.test(
          (part.material as import('three').Material).name,
        ),
      )!;
      cover.geometry.computeBoundingBox();
      const bounds = cover.geometry.boundingBox!;
      const center = bounds.getCenter(new T.Vector3());
      const size = bounds.getSize(new T.Vector3());
      const ray = new T.Raycaster();
      const blocked = [];
      for (const yaw of [-55, 0, 55]) {
        for (const pitch of [-18, 0, 18]) {
          const direction = new T.Vector3(
            Math.tan(T.MathUtils.degToRad(yaw)),
            Math.tan(T.MathUtils.degToRad(pitch)),
            1,
          ).normalize();
          for (const x of [-0.38, -0.19, 0, 0.19, 0.38]) {
            for (const y of [-0.36, 0, 0.36]) {
              const point = center.clone().add(new T.Vector3(x * size.x, y * size.y, 0));
              ray.set(point.clone().addScaledVector(direction, 0.016), direction.clone().negate());
              ray.far = 0.017;
              const first = ray.intersectObjects(parts, false)[0]?.object;
              if (first !== cover) blocked.push({ yaw, pitch, x, y, part: first?.name });
            }
          }
        }
      }
      const edgeHits = [];
      ray.ray.direction.set(0, 0, -1);
      for (const u of [-1, 0, 1]) {
        for (const v of [-1, 0, 1]) {
          const corner = u !== 0 && v !== 0;
          const margin = corner ? 0.0002 : 0.00006;
          ray.ray.origin.set(
            center.x + u * (size.x / 2 - margin),
            center.y + v * (size.y / 2 - margin),
            center.z + 0.016,
          );
          edgeHits.push(ray.intersectObjects(parts, false)[0]?.object === cover);
        }
      }
      ray.set(
        new T.Vector3(center.x + size.x * 0.9, center.y, center.z + 0.008),
        new T.Vector3(0, 0, -1),
      );
      ray.far = 0.02;
      const barrel = ray.intersectObjects(parts, false)[0]?.object;
      if (!barrel || barrel === cover) throw new Error(`Missing barrel beside ${lens.name}`);
      const shellAcrossGlass = [];
      ray.far = 0.008;
      for (const u of [-0.35, 0, 0.35]) {
        for (const v of [-0.35, 0, 0.35]) {
          ray.ray.origin.set(center.x + u * size.x, center.y + v * size.y, center.z + 0.004);
          if (ray.intersectObject(barrel, false).length) shellAcrossGlass.push([u, v]);
        }
      }
      return { name: lens.name, blocked, coverThickness: size.z, edgeHits, shellAcrossGlass };
    });
  });
  expect(results).toHaveLength(3);
  for (const result of results) {
    expect(result.blocked, result.name).toEqual([]);
    expect(result.edgeHits, result.name).not.toContain(false);
    expect(result.shellAcrossGlass, result.name).toEqual([]);
    expect(result.coverThickness, result.name).toBeLessThan(0.00001);
  }
});
