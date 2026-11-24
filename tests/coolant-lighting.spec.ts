import { expect, test } from '@playwright/test';

test('both coolant sleeves carry Aura from pump to radiator and respect reduced motion @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const scenePath = '/src/scene/';
    const threePath = '/node_modules/three/build/three.module.js';
    const [T, { tower }, { materials }, { loadParts }] = await Promise.all([
      import(threePath) as Promise<typeof import('three')>,
      import(scenePath + 'hardware.ts') as Promise<typeof import('../src/scene/hardware')>,
      import(scenePath + 'materials.ts') as Promise<typeof import('../src/scene/materials')>,
      import(scenePath + 'blender-library.ts') as Promise<
        typeof import('../src/scene/blender-library')
      >,
    ]);
    await Promise.all([loadParts('studio'), loadParts('pc-hero')]);
    const manager = new T.LoadingManager();
    const aura = Array.from({ length: 7 }, () => new T.MeshStandardMaterial());
    const pc = tower(new T.Group(), materials(new T.TextureLoader(manager)), aura, manager);
    const panels: import('three').Mesh<
      import('three').BufferGeometry,
      import('three').MeshStandardMaterial
    >[] = [];
    pc.unit.traverse((part) => {
      if (part.userData.mf12cStation === undefined) return;
      const panel = part.children.find((child) =>
        ['stripes', 'eye'].includes(child.userData.mf12cPart),
      );
      if (!panel) throw new Error('Missing MF-12C side light guide');
      panels[part.userData.mf12cStation] = panel as (typeof panels)[number];
    });
    const fanMasks = panels.map((panel) => {
      const position = panel.geometry.getAttribute('position');
      const sides = [new Set<string>(), new Set<string>()];
      for (let vertex = 0; vertex < position.count; vertex++) {
        const side = Math.sign(position.getX(vertex));
        sides[Number(side > 0)].add(
          [
            Math.round(side * position.getY(vertex) * 100_000),
            Math.round(position.getZ(vertex) * 100_000),
          ].join('/'),
        );
      }
      const surface = new T.Mesh(panel.geometry, panel.material);
      const ray = new T.Raycaster();
      const caps = [-1, 1].map((side) => {
        const testPixel = (x: number, y: number) => {
          ray.set(
            new T.Vector3(side * 0.061, ((436 - x) * side) / 12000, 0.0128 + (y - 110) / 12000),
            new T.Vector3(-side, 0, 0),
          );
          return ray.intersectObject(surface).length > 0;
        };
        return [testPixel(800, 112), testPixel(825, 55), testPixel(825, 173)];
      });
      return {
        pattern: panel.userData.mf12cPart,
        caps,
        dualSided: sides[0].size > 40 && [...sides[0]].every((point) => sides[1].has(point)),
      };
    });
    const guide = pc.unit.children.find(
      (part): part is import('three').Mesh =>
        part.userData.cablePart === 'aio-braid' && 'isMesh' in part,
    );
    if (!guide) throw new Error('Missing optical sleeves in the installed cooler');
    const positions = guide.geometry.getAttribute('position');
    const uv = guide.geometry.getAttribute('uv');
    const rings = new Map<number, Set<number>>();
    for (let i = 0; i < uv.count; i++) {
      const travel = Math.round(uv.getY(i) * 10000);
      const ring = rings.get(travel) ?? new Set<number>();
      ring.add(Math.round(uv.getX(i) * 32) % 32);
      rings.set(travel, ring);
    }
    const ends = [
      new T.Vector3(0.0325, 0.17, -0.174),
      new T.Vector3(0.0325, 0.17, -0.154),
      new T.Vector3(0.062, 0.225, -0.198),
      new T.Vector3(0.062, 0.225, -0.178),
    ];
    const point = new T.Vector3();
    const distances = ends.map((end) => {
      let closest = Infinity;
      for (let i = 0; i < positions.count; i++) {
        closest = Math.min(closest, point.fromBufferAttribute(positions, i).distanceTo(end));
      }
      return closest;
    });
    const scene = new T.Scene();
    scene.add(guide.clone());
    const center = new T.Box3().setFromObject(scene).getCenter(new T.Vector3());
    const camera = new T.OrthographicCamera(-0.07, 0.07, 0.07, -0.07, 0.001, 1);
    camera.position.copy(center).add(new T.Vector3(-0.16, 0.04, 0.09));
    camera.lookAt(center);
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(160, 160);
    renderer.setRenderTarget(target);
    function sample(enabled: boolean, time: number, reducedMotion = false) {
      pc.setComponentLights(enabled, undefined, time, { reducedMotion, quality: 'low' });
      renderer.render(scene, camera);
      const pixels = new Uint8Array(target.width * target.height * 4);
      renderer.readRenderTargetPixels(target, 0, 0, target.width, target.height, pixels);
      return pixels;
    }
    function differences(a: Uint8Array, b: Uint8Array) {
      return a.reduce((count, value, i) => count + Number(Math.abs(value - b[i]) > 8), 0);
    }
    try {
      const unlit = sample(false, 0);
      const fansOff = panels.every((panel) => panel.material.emissiveIntensity === 0);
      const lit = sample(true, 0);
      const fansOn = panels.every((panel) => panel.material.emissiveIntensity > 0);
      const flowing = sample(true, 6);
      const still = sample(true, 6, true);
      const coverage = [];
      const shell = scene.children[0] as import('three').Mesh;
      const diffuser = shell.material;
      const silhouette = new T.MeshBasicMaterial({ color: 0xffffff });
      for (const direction of [new T.Vector3(-1, 0.3, 0.45), new T.Vector3(1, -0.3, -0.45)]) {
        camera.position.copy(center).addScaledVector(direction, 0.2);
        camera.lookAt(center);
        shell.material = silhouette;
        const mask = sample(true, 0);
        shell.material = diffuser;
        const glow = sample(true, 0);
        let area = 0;
        let luminous = 0;
        for (let i = 0; i < mask.length; i += 4) {
          if (mask[i] < 240) continue;
          area++;
          if (Math.max(glow[i], glow[i + 1], glow[i + 2]) > 32) luminous++;
        }
        coverage.push(area > 150 ? luminous / area : 0);
      }
      silhouette.dispose();
      camera.position.copy(center).add(new T.Vector3(-0.16, 0.04, 0.09));
      camera.lookAt(center);
      const fittings = pc.unit.children.filter((part) =>
        ['aio-fittings', 'aio-seals'].includes(part.userData.cablePart),
      ) as import('three').Mesh<
        import('three').BufferGeometry,
        import('three').MeshStandardMaterial
      >[];
      return {
        fanMasks,
        fansOff,
        fansOn,
        distances,
        fullRings: [...rings.values()].every((ring) => ring.size === 32),
        coverage,
        fittingEmission: fittings.map(
          ({ material }) => material.emissive.getHex() * material.emissiveIntensity,
        ),
        powered: differences(unlit, lit),
        animated: differences(lit, flowing),
        stillPowered: differences(unlit, still),
        stillChanges: differences(still, sample(true, 12, true)),
        offChanges: differences(unlit, sample(false, 14)),
      };
    } finally {
      target.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  for (const distance of result.distances) expect(distance).toBeLessThan(0.009);
  expect(result.fanMasks.map((panel) => panel.pattern)).toEqual(['eye', 'stripes', 'eye']);
  expect(result.fanMasks.every((panel) => panel.dualSided)).toBe(true);
  for (const panel of result.fanMasks) {
    expect(panel.caps).toEqual([
      [true, false, false],
      [true, false, false],
    ]);
  }
  expect(result.fansOff && result.fansOn).toBe(true);
  expect(result.fullRings).toBe(true);
  for (const fraction of result.coverage) expect(fraction).toBeGreaterThan(0.99);
  expect(result.fittingEmission).toEqual([0, 0]);
  expect(result.powered).toBeGreaterThan(100);
  expect(result.animated).toBeGreaterThan(100);
  expect(result.stillPowered).toBeGreaterThan(100);
  expect(result.stillChanges).toBe(0);
  expect(result.offChanges).toBe(0);
});
