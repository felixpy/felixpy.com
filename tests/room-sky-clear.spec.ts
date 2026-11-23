import { expect, test } from '@playwright/test';

test('the sky clear preserves offscreen color and depth and falls back outside its room view @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const three = '/node_modules/.vite/deps/three.js';
    const module = '/src/scene/room-sky-clear.ts';
    const T = (await import(three)) as typeof import('three');
    const { roomSkyClear, roomSkyName } = (await import(
      module
    )) as typeof import('../src/scene/room-sky-clear');
    const renderer = new T.WebGLRenderer({ alpha: false });
    renderer.toneMapping = T.ACESFilmicToneMapping;
    const size = 32;
    const depth = new T.DepthTexture(size, size);
    const beauty = new T.WebGLRenderTarget(size, size, {
      type: T.HalfFloatType,
      samples: Math.min(4, renderer.capabilities.maxSamples),
      depthTexture: depth,
    });
    const copy = new T.WebGLRenderTarget(size, size);
    const scene = new T.Scene();
    const room = new T.Group();
    scene.add(room);
    const camera = new T.PerspectiveCamera(50, 1, 0.028, 3000);
    const sky = new T.Mesh(
      new T.SphereGeometry(60, 32, 20),
      new T.MeshBasicMaterial({
        color: '#132947',
        side: T.BackSide,
        toneMapped: false,
        depthWrite: false,
      }),
    );
    sky.name = roomSkyName;
    sky.renderOrder = -10;
    sky.castShadow = false;
    room.add(sky);
    const foreground = new T.Mesh(
      new T.BoxGeometry(1.2, 1.2, 0.3),
      new T.MeshBasicMaterial({ color: '#d4b285' }),
    );
    foreground.position.set(0.3, 0, -3);
    room.add(foreground);
    const probe = new T.Mesh(
      new T.PlaneGeometry(2, 2),
      new T.ShaderMaterial({
        uniforms: {
          colorTexture: { value: beauty.texture },
          depthTexture: { value: depth },
          readDepth: { value: false },
        },
        vertexShader: `
          varying vec2 sampleUv;
          void main() {
            sampleUv = uv;
            gl_Position = vec4(position.xy, 0., 1.);
          }`,
        fragmentShader: `
          #include <packing>
          varying vec2 sampleUv;
          uniform sampler2D colorTexture, depthTexture;
          uniform bool readDepth;
          void main() {
            gl_FragColor = readDepth ? packDepthToRGBA(texture2D(depthTexture, sampleUv).r)
              : texture2D(colorTexture, sampleUv);
          }`,
        depthTest: false,
        depthWrite: false,
      }),
    );
    probe.frustumCulled = false;
    const probeCamera = new T.Camera();
    const clear = roomSkyClear(scene)!;
    function capture(optimized: boolean) {
      renderer.setRenderTarget(beauty);
      if (optimized) clear(renderer, camera);
      else renderer.render(scene, camera);
      const draws = renderer.info.render.calls;
      const pixels = [false, true].map((readDepth) => {
        probe.material.uniforms.readDepth.value = readDepth;
        renderer.setRenderTarget(copy);
        renderer.render(probe, probeCamera);
        const bytes = new Uint8Array(size * size * 4);
        renderer.readRenderTargetPixels(copy, 0, 0, size, size, bytes);
        return bytes;
      });
      return { draws, pixels };
    }
    function compare() {
      const original = capture(false);
      const candidate = capture(true);
      return {
        skipped: original.draws - candidate.draws,
        differences: original.pixels.map((pixels, i) =>
          pixels.reduce(
            (max, value, j) => Math.max(max, Math.abs(value - candidate.pixels[i][j])),
            0,
          ),
        ),
      };
    }

    try {
      const night = compare();
      sky.material.color.set('#b3c9df');
      const day = compare();
      sky.layers.set(1);
      const layer = compare();
      sky.layers.set(0);
      room.visible = false;
      const hidden = compare();
      room.visible = true;
      camera.far = 20;
      camera.updateProjectionMatrix();
      const far = compare();
      return {
        night,
        day,
        layer,
        hidden,
        far,
        restored: sky.visible && scene.background === null,
        error: renderer.getContext().getError(),
      };
    } finally {
      sky.geometry.dispose();
      sky.material.dispose();
      foreground.geometry.dispose();
      foreground.material.dispose();
      probe.geometry.dispose();
      probe.material.dispose();
      beauty.dispose();
      copy.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(result.error).toBe(0);
  expect(result.restored).toBe(true);
  for (const view of [result.night, result.day]) {
    expect(view.skipped).toBe(1);
    expect(view.differences[0]).toBeLessThanOrEqual(1);
    expect(view.differences[1]).toBe(0);
  }
  for (const view of [result.layer, result.hidden, result.far]) {
    expect(view).toEqual({ skipped: 0, differences: [0, 0] });
  }
});
