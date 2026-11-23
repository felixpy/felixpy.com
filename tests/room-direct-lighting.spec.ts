import { expect, test } from '@playwright/test';

test('culling zero-contribution lights preserves low-quality PBR pixels @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const lighting = '/src/scene/room-direct-lighting.ts';
    const T = (await import(three)) as typeof import('three');
    const { cullRoomDirectLighting } = (await import(
      lighting
    )) as typeof import('../src/scene/room-direct-lighting');
    const size = 64;
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(size, size);
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(45, 1, 0.05, 20);
    camera.position.set(0, 0.4, 3);
    const material = new T.MeshPhysicalMaterial({
      color: 0xd3c4aa,
      roughness: 0.37,
      metalness: 0.2,
      clearcoat: 0.85,
      clearcoatRoughness: 0.19,
    });
    const culled = material.clone();
    culled.onBeforeCompile = (shader) => {
      shader.fragmentShader = cullRoomDirectLighting(
        shader.fragmentShader,
        T.ShaderChunk.lights_fragment_begin,
      );
    };
    const object = new T.Mesh(new T.SphereGeometry(0.9, 32, 16), material);
    const sun = new T.DirectionalLight(0xc9dbfa, 0.4);
    sun.position.set(0.1, 1.5, -2);
    const point = new T.PointLight(0xefdcec, 2, 2, 2);
    point.position.set(-0.6, 0.2, 1.5);
    const distant = new T.PointLight(0xffddcc, 40, 0.5, 2);
    distant.position.set(0, 0, 3);
    const task = new T.SpotLight(0xffd6a1, 4, 2.1, 0.56, 0.45, 2);
    task.position.set(1, 1, 1.1);
    scene.add(object, new T.HemisphereLight(0xe3eadf, 0x8b7b6f, 0.3), sun, point, distant, task);

    function render(material: InstanceType<typeof T.MeshPhysicalMaterial>) {
      object.material = material;
      renderer.setRenderTarget(target);
      renderer.render(scene, camera);
      const pixels = new Uint8Array(size * size * 4);
      renderer.readRenderTargetPixels(target, 0, 0, size, size, pixels);
      return pixels;
    }

    function maxDifference(a: Uint8Array, b: Uint8Array) {
      return a.reduce((max, value, index) => Math.max(max, Math.abs(value - b[index])), 0);
    }

    try {
      const lit = render(material);
      const litDifference = maxDifference(lit, render(culled));
      point.intensity = task.intensity = 0;
      const dim = render(material);
      return {
        litDifference,
        dimDifference: maxDifference(dim, render(culled)),
        lampDifference: maxDifference(lit, dim),
        error: renderer.getContext().getError(),
      };
    } finally {
      material.dispose();
      culled.dispose();
      object.geometry.dispose();
      target.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(result.error).toBe(0);
  expect(result.litDifference).toBeLessThanOrEqual(1);
  expect(result.dimDifference).toBeLessThanOrEqual(1);
  expect(result.lampDifference).toBeGreaterThan(10);
});
