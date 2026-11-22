import { expect, test } from '@playwright/test';

test('the first room frame lights both faces of thin cloth and keeps single-sided surfaces unchanged @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const sample = await page.evaluate(async () => {
    const three = '/node_modules/.vite/deps/three.js';
    const module = '/src/scene/room-first-frame.ts';
    const T = (await import(three)) as typeof import('three');
    const { roomFirstFrame } = (await import(
      module
    )) as typeof import('../src/scene/room-first-frame');
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(16, 16);
    const camera = new T.PerspectiveCamera(40, 1, 0.1, 5);
    camera.position.set(0, 0, 1);
    const scene = new T.Scene();
    const material = new T.MeshStandardMaterial({ color: 0xbbbbbb });
    const surface = new T.Mesh(new T.PlaneGeometry(1, 1), material);
    scene.add(surface);
    const frame = roomFirstFrame();
    const draw = (side: typeof material.side, reversed: boolean) => {
      material.side = side;
      surface.rotation.y = reversed ? Math.PI : 0;
      renderer.setRenderTarget(target);
      frame.draw(renderer, scene, camera, false, 'neutral');
      const pixel = new Uint8Array(4);
      renderer.readRenderTargetPixels(target, 8, 8, 1, 1, pixel);
      return Array.from(pixel.subarray(0, 3));
    };
    try {
      return {
        front: draw(T.FrontSide, false),
        culled: draw(T.FrontSide, true),
        doubleFront: draw(T.DoubleSide, false),
        doubleBack: draw(T.DoubleSide, true),
        singleBack: draw(T.BackSide, true),
      };
    } finally {
      frame.dispose();
      surface.geometry.dispose();
      material.dispose();
      target.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(sample.culled).toEqual([0, 0, 0]);
  expect(sample.doubleFront).toEqual(sample.front);
  expect(sample.doubleBack).toEqual(sample.front);
  expect(Math.min(...sample.singleBack)).toBeGreaterThan(0);
  expect(sample.singleBack[0]).toBeLessThan(sample.front[0] - 5);
});
