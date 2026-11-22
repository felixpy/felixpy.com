import { expect, test } from '@playwright/test';

test('snow clusters resolve near the window and diminish with distance and night lighting @webgl', async ({
  page,
}) => {
  await page.route('**/__snow', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Snowfall</title>' }),
  );
  await page.goto('/__snow');
  const readings = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const snowModule = '/src/scene/snowfall.ts';
    const envModule = '/src/app/environment.ts';
    const T = (await import(three)) as typeof import('three');
    const { snowfall } = (await import(snowModule)) as typeof import('../src/scene/snowfall');
    const { initialEnvironment } = (await import(
      envModule
    )) as typeof import('../src/app/environment');
    const env = { ...initialEnvironment, night: false, reducedMotion: true };
    const scene = new T.Scene();
    const update = snowfall(scene);
    const particles = scene.children[0] as import('three').Points<
      import('three').BufferGeometry,
      import('three').PointsMaterial
    >;
    const features = particles.geometry.getAttribute('flake');
    let largest = 0;
    for (let i = 1; i < features.count; i++)
      if (features.getX(i) > features.getX(largest)) largest = i;
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(512, 512);
    renderer.setSize(512, 512);
    renderer.setRenderTarget(target);
    const camera = new T.PerspectiveCamera(36, 1, 0.02, 40);
    camera.position.set(-0.57, 1.45, 0.58);
    camera.lookAt(-2, 1.45, 0.58);
    const pixels = new Uint8Array(512 * 512 * 4);
    const read = (depth: number) => {
      const positions = particles.geometry.getAttribute('position');
      positions.setXYZ(largest, -1.57 - depth, 1.45, 0.58);
      positions.needsUpdate = true;
      particles.geometry.setDrawRange(largest, 1);
      renderer.render(scene, camera);
      renderer.readRenderTargetPixels(target, 0, 0, 512, 512, pixels);
      let area = 0,
        energy = 0,
        xSum = 0,
        ySum = 0,
        xx = 0,
        yy = 0,
        xy = 0;
      let xMin = 512,
        xMax = -1,
        yMin = 512,
        yMax = -1;
      for (let i = 0; i < pixels.length; i += 4) {
        const intensity = pixels[i] + pixels[i + 1] + pixels[i + 2];
        energy += intensity;
        if (intensity < 76) continue;
        const x = (i / 4) % 512,
          y = Math.floor(i / 2048);
        xMin = Math.min(xMin, x);
        xMax = Math.max(xMax, x);
        yMin = Math.min(yMin, y);
        yMax = Math.max(yMax, y);
        xSum += x;
        ySum += y;
        xx += x * x;
        yy += y * y;
        xy += x * y;
        area++;
      }
      const x = xSum / area,
        y = ySum / area;
      const a = xx / area - x * x,
        b = yy / area - y * y,
        c = xy / area - x * y;
      const stretch = Math.hypot(a - b, 2 * c);
      return {
        area,
        energy,
        extent: Math.max(xMax - xMin + 1, yMax - yMin + 1),
        x,
        y,
        aspect: Math.sqrt((a + b + stretch) / (a + b - stretch)),
      };
    };
    try {
      update(env, 0, 1);
      const near = read(0),
        far = read(4);
      update(env, 0.1, 1);
      const reduced = read(0);
      update({ ...env, night: true }, 0, 1);
      const night = read(0);
      update({ ...env, reducedMotion: false }, 0.1, 1);
      const later = read(0);
      update(env, 0.1, 0);
      return { near, far, reduced, night, later, clear: read(0).area };
    } finally {
      particles.geometry.dispose();
      particles.material.map?.dispose();
      particles.material.dispose();
      target.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(readings.near.extent).toBeGreaterThanOrEqual(14);
  expect(readings.near.extent).toBeGreaterThan(readings.far.extent * 2.5);
  expect(readings.near.aspect).toBeGreaterThan(1.25);
  expect(readings.far.energy).toBeGreaterThan(0);
  expect(readings.night.energy).toBeLessThan(readings.near.energy);
  expect(readings.reduced).toEqual(readings.near);
  expect(
    Math.hypot(readings.later.x - readings.near.x, readings.later.y - readings.near.y),
  ).toBeGreaterThan(3);
  expect(readings.clear).toBe(0);
});
