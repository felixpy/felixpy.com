import { expect, test } from '@playwright/test';

test('PC readout uploads preserve canvas samples and update the same texture @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const results = await page.evaluate(async () => {
    const three = '/node_modules/.vite/deps/three.js';
    const helper = '/src/scene/pc-telemetry-texture.ts';
    const T = (await import(three)) as typeof import('three');
    const { pcTelemetryTexture } = (await import(
      helper
    )) as typeof import('../src/scene/pc-telemetry-texture');
    const renderer = new T.WebGLRenderer({ antialias: false });
    const material = new T.ShaderMaterial({
      uniforms: { readout: { value: null as import('three').Texture | null } },
      vertexShader: `
        varying vec2 readoutUv;
        void main() {
          readoutUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D readout;
        varying vec2 readoutUv;
        void main() {
          vec4 color = texture2D(readout, readoutUv);
          gl_FragColor = vec4(color.rgb * color.a, color.a);
        }
      `,
      blending: T.NoBlending,
      toneMapped: false,
    });
    const geometry = new T.PlaneGeometry(2, 2);
    const quad = new T.Mesh(geometry, material);
    quad.frustumCulled = false;
    const scene = new T.Scene();
    scene.add(quad);
    const camera = new T.Camera();

    function read(texture: import('three').Texture, target: import('three').WebGLRenderTarget) {
      material.uniforms.readout.value = texture;
      renderer.setRenderTarget(target);
      renderer.render(scene, camera);
      const pixels = new Uint8Array(target.width * target.height * 4);
      renderer.readRenderTargetPixels(target, 0, 0, target.width, target.height, pixels);
      return pixels;
    }

    function compare(a: Uint8Array, b: Uint8Array) {
      let color = 0;
      let alpha = 0;
      let changed = 0;
      for (const [index, value] of a.entries()) {
        const difference = Math.abs(value - b[index]);
        if (index % 4 === 3) alpha = Math.max(alpha, difference);
        else color = Math.max(color, difference);
        if (difference > 1) changed++;
      }
      return { color, alpha, changed };
    }

    try {
      return [
        [640, 250, '48°', '49°'],
        [320, 80, '230 W', '239 W'],
      ].map(([rawWidth, rawHeight, firstText, secondText]) => {
        const width = Number(rawWidth);
        const height = Number(rawHeight);
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d')!;
        const source = new T.CanvasTexture(canvas);
        source.colorSpace = T.SRGBColorSpace;
        source.anisotropy = 8;
        const upload = pcTelemetryTexture(source, context);
        const full = new T.WebGLRenderTarget(width, height);
        const small = new T.WebGLRenderTarget(Math.floor(width / 4), Math.floor(height / 4));
        function paint(text: string) {
          context.clearRect(0, 0, width, height);
          context.fillStyle = '#ff2417';
          context.fillRect(0, 0, width / 4, height / 3);
          context.fillStyle = 'rgba(0, 96, 255, 0.5)';
          context.fillRect(0, (height * 2) / 3, width / 4, height / 3);
          context.fillStyle = '#eff3ff';
          context.font = `500 ${Math.floor(height * 0.4)}px Arial, sans-serif`;
          context.fillText(text, width / 3, height * 0.62, width * 0.64);
          for (let x = Math.floor(width * 0.55); x < width - 2; x += 2)
            context.fillRect(x, height * 0.86, 1, Math.floor(height * 0.1));
          source.needsUpdate = true;
        }
        try {
          paint(String(firstText));
          const stockFull = read(source, full);
          const stockSmall = read(source, small);
          const typed = upload(true);
          const typedFull = read(typed, full);
          const typedSmall = read(typed, small);
          paint(String(secondText));
          const nextStockFull = read(source, full);
          const nextStockSmall = read(source, small);
          const nextTyped = upload(true);
          const nextTypedFull = read(nextTyped, full);
          const nextTypedSmall = read(nextTyped, small);
          const sample = (x: number, y: number) =>
            Array.from(typedFull.subarray((y * width + x) * 4, (y * width + x) * 4 + 4));
          return {
            size: [width, height],
            reused: typed === nextTyped,
            top: sample(8, height - 8),
            bottom: sample(8, 8),
            empty: sample(width - 4, height - 4),
            parity: [
              compare(stockFull, typedFull),
              compare(stockSmall, typedSmall),
              compare(nextStockFull, nextTypedFull),
              compare(nextStockSmall, nextTypedSmall),
            ],
            firstToNext: [
              compare(typedFull, nextTypedFull).changed,
              compare(typedSmall, nextTypedSmall).changed,
            ],
            error: renderer.getContext().getError(),
          };
        } finally {
          upload(false).dispose();
          full.dispose();
          small.dispose();
        }
      });
    } finally {
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    }
  });

  for (const result of results) {
    const label = result.size.join('×');
    expect(result.error, label).toBe(0);
    expect(result.reused, label).toBe(true);
    expect(result.top[0], label).toBeGreaterThan(240);
    expect(result.top[3], label).toBe(255);
    expect(result.bottom[2], label).toBeGreaterThan(120);
    expect(result.bottom[3], label).toBeGreaterThanOrEqual(127);
    expect(result.bottom[3], label).toBeLessThanOrEqual(128);
    expect(result.empty, label).toEqual([0, 0, 0, 0]);
    expect(
      result.firstToNext.every((count) => count > 0),
      label,
    ).toBe(true);
    for (const { color, alpha } of result.parity) {
      expect(color, label).toBeLessThanOrEqual(1);
      expect(alpha, label).toBeLessThanOrEqual(1);
    }
  }
});
