import { expect, test } from '@playwright/test';

test('contact shadows shade the room and preserve a uniform distant sky @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const samples = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const module = '/src/scene/room-occlusion.ts';
    const T = (await import(three)) as typeof import('three');
    const { roomOcclusion } = (await import(
      module
    )) as typeof import('../src/scene/room-occlusion');
    const size = 64;
    const renderer = new T.WebGLRenderer();
    const camera = new T.PerspectiveCamera(50, 1, 0.028, 3000);
    const scene = new T.Scene();
    const white = new T.MeshBasicMaterial({ color: 0xffffff });
    const panel = new T.Mesh(new T.PlaneGeometry(4, 4), white);
    const step = new T.Mesh(new T.BoxGeometry(0.24, 0.24, 0.066), white);
    step.position.z = 0.033;
    panel.add(step);
    scene.add(panel);
    const depth = new T.DepthTexture(size, size);
    const beauty = new T.WebGLRenderTarget(size, size, { depthTexture: depth });
    const composite = new T.WebGLRenderTarget(size, size);
    const pass = roomOcclusion(scene, camera, depth);
    pass.setSize(size, size);
    try {
      return [0.25, -650].map((x) => {
        camera.position.set(x, 1.2, 1);
        panel.position.set(x, 1.2, 0.4);
        renderer.setRenderTarget(beauty);
        renderer.render(scene, camera);
        pass.render(renderer, composite, beauty, 0, false);
        const pixels = new Uint8Array(4 * size * size);
        renderer.readRenderTargetPixels(composite, 0, 0, size, size, pixels);
        return Math.min(...pixels.filter((_, i) => i % 4 === 0));
      });
    } finally {
      pass.dispose();
      pass.gtaoMaterial.dispose();
      pass.blendMaterial.dispose();
      beauty.dispose();
      composite.dispose();
      panel.geometry.dispose();
      step.geometry.dispose();
      white.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(samples[0]).toBeLessThan(255);
  expect(samples[1]).toBe(255);
});
