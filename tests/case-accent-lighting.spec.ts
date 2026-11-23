import { expect, test } from '@playwright/test';

test('the Hyperion and Thor light guides share the Aura cycle while the power readout stays lit @webgl', async ({
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
    await loadParts('studio');
    const manager = new T.LoadingManager();
    const aura = Array.from({ length: 7 }, () => new T.MeshStandardMaterial());
    const pc = tower(new T.Group(), materials(new T.TextureLoader(manager)), aura, manager);
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(192, 256);
    renderer.setRenderTarget(target);
    const scene = new T.Scene();
    function check(name: string, toward: number[]) {
      const source = pc.unit.getObjectByName(name) as import('three').Mesh;
      const part = source.clone();
      scene.add(part);
      const box = new T.Box3().setFromObject(part);
      const center = box.getCenter(new T.Vector3());
      const size = box.getSize(new T.Vector3());
      const h = Math.max(size.y, (size.x * 4) / 3, (size.z * 4) / 3) * 0.54;
      const camera = new T.OrthographicCamera(-h * 0.75, h * 0.75, h, -h, 0.001, 2);
      camera.position.copy(center).add(new T.Vector3().fromArray(toward));
      camera.lookAt(center);
      function sample(enabled: boolean, seconds: number, reducedMotion = false) {
        pc.setComponentLights(enabled, undefined, seconds, { reducedMotion, quality: 'low' });
        renderer.render(scene, camera);
        const pixels = new Uint8Array(target.width * target.height * 4);
        renderer.readRenderTargetPixels(target, 0, 0, target.width, target.height, pixels);
        return pixels;
      }
      const day = sample(true, 0);
      const off = sample(false, 0);
      const cycle = sample(true, 6);
      const still = sample(true, 12, true);
      const changes = (a: Uint8Array, b: Uint8Array) =>
        a.reduce((count, value, i) => count + Number(Math.abs(value - b[i]) > 12), 0);
      const hues = new Set<number>();
      for (let i = 0; i < day.length; i += 4) {
        const [r, g, b] = day.subarray(i, i + 3);
        if (Math.max(r, g, b) - Math.min(r, g, b) < 30) continue;
        const hsl = new T.Color(r / 255, g / 255, b / 255).getHSL({ h: 0, s: 0, l: 0 });
        hues.add(Math.floor(hsl.h * 12));
      }
      scene.remove(part);
      return {
        power: changes(day, off),
        motion: changes(day, cycle),
        still: changes(day, still),
        hueBins: hues.size,
        litPixels: day.filter((value, i) => i % 4 === 0 && value > 120).length,
      };
    }
    try {
      return {
        fascia: check('GR701 front assembly · light', [0, 0, 1]),
        psu: check('Thor 1600W Titanium III • aura', [-1, 0, 0]),
        readout: check('Thor OLED power draw', [-1, 0, 0]),
      };
    } finally {
      target.dispose();
      renderer.dispose();
    }
  });
  for (const guide of [result.fascia, result.psu]) {
    expect(guide.hueBins).toBeGreaterThan(2);
    expect(guide.power).toBeGreaterThan(50);
    expect(guide.motion).toBeGreaterThan(50);
    expect(guide.still).toBe(0);
  }
  expect(result.readout.litPixels).toBeGreaterThan(100);
  expect(result.readout.power).toBe(0);
});
