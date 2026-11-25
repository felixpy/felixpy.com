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

test('uniform-bound light loops, PHYSICAL simplification, and dotNL early-out preserve PBR pixels @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const visibilityPath = '/src/scene/room-visibility.ts';
    const envPath = '/src/app/environment.ts';
    const T = (await import(three)) as typeof import('three');
    const { buildRoomLightEvaluation, roomVisibility } = (await import(
      visibilityPath
    )) as typeof import('../src/scene/room-visibility');
    const { initialEnvironment } = (await import(
      envPath
    )) as typeof import('../src/app/environment');

    const evalSource = buildRoomLightEvaluation();
    const hasUniformPointLoop = evalSource.includes('for ( int i = 0; i < uPointCount; i ++ )');
    const hasUniformSpotLoop = evalSource.includes(
      'for ( int i = NUM_SPOT_LIGHT_SHADOWS; i < uSpotCount; i ++ )',
    );
    const hasShadowUnrollOnly = evalSource.includes(
      'for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ )',
    );
    const hasClearcoatDotNL = evalSource.includes(
      'dot( geometryClearcoatNormal, directLight.direction ) > 0.0',
    );

    const size = 64;
    const renderer = new T.WebGLRenderer();
    renderer.shadowMap.enabled = true;
    const target = new T.WebGLRenderTarget(size, size);
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(45, 1, 0.05, 20);
    camera.position.set(0, 1.2, 2.4);
    camera.lookAt(0, 1.0, 0);

    // Default MeshPhysicalMaterial should simplify cleanly with defines.PHYSICAL removed (restoring 4% Fresnel specular)
    const defaultPhys = new T.MeshPhysicalMaterial({
      color: 0x303030,
      roughness: 0.18,
      metalness: 0,
    });
    // Non-default specularColor MeshPhysicalMaterial should NOT be simplified
    const customSpecPhys = new T.MeshPhysicalMaterial({
      color: 0x303030,
      roughness: 0.18,
      metalness: 0,
      specularColor: new T.Color('#66ccff'),
      specularIntensity: 0.8,
    });
    const refStandard = new T.MeshStandardMaterial({
      color: 0x303030,
      roughness: 0.18,
      metalness: 0,
    });

    const sphereA = new T.Mesh(new T.SphereGeometry(0.45, 24, 16), defaultPhys);
    sphereA.position.set(0, 1.1, 0);
    const sphereB = new T.Mesh(new T.SphereGeometry(0.2, 16, 12), customSpecPhys);
    sphereB.position.set(3, 1.1, 0);
    scene.add(sphereA, sphereB);

    // 1 shadowed spot + 2 non-shadowed spots + 2 point lights + 1 directional light
    const shadowSpot = new T.SpotLight(0xffe0b8, 6, 4.5, 0.7, 0.5, 2);
    shadowSpot.position.set(0.6, 2.1, 1.2);
    shadowSpot.target.position.set(0, 1.1, 0);
    shadowSpot.castShadow = true;
    const unshadowedSpot1 = new T.SpotLight(0xc8dcff, 5, 4.5, 0.7, 0.5, 2);
    unshadowedSpot1.position.set(-0.7, 2.0, 1.3);
    unshadowedSpot1.target.position.set(0, 1.1, 0);
    const unshadowedSpot2 = new T.SpotLight(0xffd0aa, 3, 4.5, 0.7, 0.5, 2);
    unshadowedSpot2.position.set(0.2, 1.9, 1.6);
    unshadowedSpot2.target.position.set(0, 1.1, 0);
    const point1 = new T.PointLight(0xffffff, 2.5, 3.5, 2);
    point1.position.set(0.1, 1.5, 1.4);
    const point2 = new T.PointLight(0xffeecc, 1.5, 3.5, 2);
    point2.position.set(-0.4, 1.3, 1.2);
    scene.add(
      shadowSpot,
      shadowSpot.target,
      unshadowedSpot1,
      unshadowedSpot1.target,
      unshadowedSpot2,
      unshadowedSpot2.target,
      point1,
      point2,
    );

    const visibility = roomVisibility([sphereA, sphereB], {
      ...initialEnvironment,
      quality: 'low',
    });
    visibility.prepareMaterials();

    const simplifiedHasPhysicalDefine = Boolean(
      defaultPhys.defines && 'PHYSICAL' in defaultPhys.defines,
    );
    const simplifiedIsPhysical = (defaultPhys as { isMeshPhysicalMaterial?: boolean })
      .isMeshPhysicalMaterial;
    const customSpecStillPhysical = (customSpecPhys as { isMeshPhysicalMaterial?: boolean })
      .isMeshPhysicalMaterial;

    function renderPixels() {
      renderer.setRenderTarget(target);
      renderer.render(scene, camera);
      const pixels = new Uint8Array(size * size * 4);
      renderer.readRenderTargetPixels(target, 0, 0, size, size, pixels);
      return pixels;
    }

    try {
      const physPixels = renderPixels();
      let maxSpec = 0;
      for (let i = 0; i < physPixels.length; i += 4) {
        maxSpec = Math.max(maxSpec, physPixels[i], physPixels[i + 1], physPixels[i + 2]);
      }
      // Compare with reference standard material wrapped by roomVisibility
      sphereA.material = refStandard;
      visibility.prepareMaterials(sphereA);
      const stdPixels = renderPixels();
      const maxDiff = physPixels.reduce(
        (max, value, index) => Math.max(max, Math.abs(value - stdPixels[index])),
        0,
      );
      return {
        hasUniformPointLoop,
        hasUniformSpotLoop,
        hasShadowUnrollOnly,
        hasClearcoatDotNL,
        simplifiedHasPhysicalDefine,
        simplifiedIsPhysical,
        customSpecStillPhysical,
        maxSpec,
        maxDiff,
        error: renderer.getContext().getError(),
      };
    } finally {
      visibility.dispose();
      defaultPhys.dispose();
      customSpecPhys.dispose();
      refStandard.dispose();
      sphereA.geometry.dispose();
      sphereB.geometry.dispose();
      target.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(result.error).toBe(0);
  expect(result.hasUniformPointLoop).toBe(true);
  expect(result.hasUniformSpotLoop).toBe(true);
  expect(result.hasShadowUnrollOnly).toBe(true);
  expect(result.hasClearcoatDotNL).toBe(true);
  expect(result.simplifiedHasPhysicalDefine).toBe(false);
  expect(result.simplifiedIsPhysical).toBe(false);
  expect(result.customSpecStillPhysical).toBe(true);
  expect(result.maxSpec).toBeGreaterThan(80);
  expect(result.maxDiff).toBeLessThanOrEqual(2);
});
