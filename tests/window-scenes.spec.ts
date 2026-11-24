import { expect, test, type Page } from '@playwright/test';
import { windowCities } from '../src/content/window-scenes';

async function openEmptyPage(page: Page) {
  await page.route('**/__window-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><title>Exterior test</title>',
    }),
  );
  await page.goto('/__window-test');
}

test('photographed landmarks and quays stay in world space throughout the approach @webgl', async ({
  page,
}) => {
  await openEmptyPage(page);
  const deviations = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const T = (await import(three)) as typeof import('three');
    const shader = '/src/scene/window-depth.ts',
      exterior = '/src/scene/exterior.ts';
    const { panoramaMaterial, panoramaOrigin, bankSlope, skylineDepth, riverLevel } = (await import(
      shader
    )) as typeof import('../src/scene/window-depth');
    const { panoramaGeometry } = (await import(exterior)) as typeof import('../src/scene/exterior');
    const registry = '/src/content/window-scenes.ts';
    const { windowCities } = (await import(
      registry
    )) as typeof import('../src/content/window-scenes');
    const rain = '/src/scene/rain-glass.ts';
    const { buildRainGlass } = (await import(rain)) as typeof import('../src/scene/rain-glass');
    const glass = buildRainGlass(new T.Vector3(-1.431, 0.987, 1.365), new T.Vector2(1.56, 1.273));
    const cameraModule = '/src/scene/camera.ts';
    const { windowEye, eye, benchEye, roomFov } = (await import(
      cameraModule
    )) as typeof import('../src/scene/camera');
    const positions = Array.from({ length: 9 }, (_, step) => {
      const t = step / 8;
      return [
        T.MathUtils.lerp(eye.x, windowEye.x, t),
        T.MathUtils.lerp(eye.y, windowEye.y, t),
        T.MathUtils.lerp(eye.defaultZ, windowEye.z, t),
        0.44 * (1 - t),
      ];
    });
    for (const turn of [-0.46, 0.46]) {
      positions.push([
        windowEye.x + 0.075 * (1 - Math.cos(turn)),
        windowEye.y,
        windowEye.z + 0.075 * Math.sin(turn),
        -turn,
      ]);
    }
    positions.push([benchEye.x, benchEye.y, benchEye.z, 0]);
    const size = 513;
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(size, size);
    const camera = new T.PerspectiveCamera(roomFov, 1, 0.028, 3000);
    const { material, uniforms } = panoramaMaterial(glass);
    uniforms.physicalWater.value = true;
    const geometry = panoramaGeometry();
    const room = new T.Scene();
    room.add(new T.Mesh(geometry, material));
    const depth = new T.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
    depth.needsUpdate = true;
    uniforms.depthA.value = depth;
    uniforms.rangeA.value.set(skylineDepth, skylineDepth);
    const pixels = new Uint8Array(size * size * 4);
    const shorelineErrors: number[] = [],
      landmarkErrors: number[] = [],
      edgeClearances: number[] = [];
    renderer.setRenderTarget(target);
    try {
      for (const city of Object.values(windowCities)) {
        for (const exposure of [city.clear, city.overcast, city.night]) {
          const width = 512,
            height = 768;
          const band = new Uint8Array(width * height * 4);
          for (let col = 0; col < width; col++) {
            const u = ((col + 0.5) / width) * 8;
            const i = Math.floor(u);
            const edge = T.MathUtils.lerp(exposure.shoreline[i], exposure.shoreline[i + 1], u - i);
            const row = Math.round(edge * height - 0.5);
            for (let y = row - 2; y <= row + 2; y++) band[4 * (y * width + col)] = 255;
            for (const [channel, center] of [219, 285].entries()) {
              if (Math.abs(col - center) <= 1)
                for (let y = row + 10; y < height; y++)
                  band[4 * (y * width + col) + channel + 1] = 255;
            }
          }
          const marker = new T.DataTexture(band, width, height);
          marker.needsUpdate = true;
          uniforms.photoA.value = marker;
          uniforms.shoreA.value = Float32Array.from(exposure.shoreline);
          uniforms.flowA.value.set(0, 0, 1);
          uniforms.waterlines.value.x = exposure.shoreline[4];
          const fy = exposure.aspect * exposure.focal;
          uniforms.calibrationA.value.set(
            exposure.center,
            exposure.shoreline[4] + bankSlope * fy,
            exposure.focal,
            fy,
          );
          for (const [x, y, z, yaw] of positions) {
            camera.position.set(x, y, z);
            camera.rotation.set(0.075, Math.PI / 2 - yaw, 0, 'YXZ');
            camera.updateMatrixWorld();
            renderer.render(room, camera);
            renderer.readRenderTargetPixels(target, 0, 0, size, size, pixels);
            for (const edgeZ of [1.39, -0.22]) {
              const u = exposure.center + exposure.focal * ((z - edgeZ) / (x + 1.414));
              edgeClearances.push(Math.min(u, 1 - u));
            }
            for (const [channel, imageCol] of [219, 285].entries()) {
              const bearing = ((imageCol + 0.5) / width - exposure.center) / exposure.focal;
              const point = panoramaOrigin
                .clone()
                .add(new T.Vector3(-skylineDepth, 0.12 * skylineDepth, -bearing * skylineDepth))
                .project(camera);
              if (Math.abs(point.x) >= 0.95) continue;
              const row = Math.floor(((point.y + 1) * size) / 2);
              const stripe = [];
              for (let col = 0; col < size; col++)
                if (pixels[4 * (row * size + col) + channel + 1] > 230) stripe.push(col);
              const center = (stripe[0] + stripe[stripe.length - 1]) / 2;
              landmarkErrors.push(
                stripe.length ? Math.abs(center - (((point.x + 1) * size) / 2 - 0.5)) : size,
              );
            }
            const bank = exposure.shoreline.map((v, i) => {
              const depth =
                ((panoramaOrigin.y - riverLevel) * fy) / (uniforms.calibrationA.value.y - v);
              const bearing =
                (i / (exposure.shoreline.length - 1) - exposure.center) / exposure.focal;
              return new T.Vector3(
                panoramaOrigin.x - depth,
                riverLevel,
                panoramaOrigin.z - depth * bearing,
              ).project(camera);
            });
            for (const col of [135, 200, 260, 330, 390]) {
              const nx = (2 * (col + 0.5)) / size - 1;
              const i = bank.findIndex(
                (a, i) => i < bank.length - 1 && a.x <= nx && bank[i + 1].x >= nx,
              );
              if (i < 0) continue;
              const a = bank[i],
                b = bank[i + 1];
              const predicted =
                ((a.y + ((nx - a.x) * (b.y - a.y)) / (b.x - a.x) + 1) * size) / 2 - 0.5;
              const lit = [];
              for (let row = 0; row < size; row++)
                if (pixels[(row * size + col) * 4] > 215) lit.push(row);
              shorelineErrors.push(
                lit.length ? Math.abs((lit[0] + lit[lit.length - 1]) / 2 - predicted) : size,
              );
            }
          }
          marker.dispose();
        }
      }
    } finally {
      geometry.dispose();
      material.dispose();
      target.dispose();
      depth.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
    return { shorelineErrors, landmarkErrors, edgeClearances };
  });
  expect(deviations.shorelineErrors).toHaveLength(360);
  expect(deviations.landmarkErrors.length).toBeGreaterThan(120);
  expect(Math.max(...deviations.shorelineErrors)).toBeLessThan(1.5);
  expect(Math.max(...deviations.landmarkErrors)).toBeLessThan(1);
  expect(Math.min(...deviations.edgeClearances)).toBeGreaterThan(0.012);
});

test('the Blender export retains the photographed depths and window camera @webgl', async ({
  page,
}) => {
  await openEmptyPage(page);
  const baked = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const T = (await import(three)) as typeof import('three');
    const shader = '/src/scene/window-depth.ts',
      exterior = '/src/scene/exterior.ts';
    const { panoramaMaterial, panoramaOrigin } = (await import(
      shader
    )) as typeof import('../src/scene/window-depth');
    const { panoramaGeometry } = (await import(exterior)) as typeof import('../src/scene/exterior');
    const path = '/src/scene/review/bake-waterfront.ts';
    const { bakeWaterfront } = (await import(
      path
    )) as typeof import('../src/scene/review/bake-waterfront');
    const camera = '/src/scene/camera.ts';
    const { windowEye, roomFov } = (await import(camera)) as typeof import('../src/scene/camera');
    const renderer = new T.WebGLRenderer();
    const { material, uniforms } = panoramaMaterial();
    const texture = new T.DataTexture(new Uint8Array([255, 0, 0, 255, 0, 255, 0, 255]), 2, 1);
    texture.needsUpdate = true;
    uniforms.photoA.value = uniforms.depthA.value = texture;
    uniforms.rangeA.value.set(240, 900);
    uniforms.calibrationA.value.set(0.5, 0.21, 0.4, 1.0);
    const source = new T.Mesh(panoramaGeometry(), material);
    const result = bakeWaterfront(renderer, source, 1024);
    try {
      const positions = result.geometry.getAttribute('position');
      const point = new T.Vector3();
      const errors = [];
      for (let i = 0; i < positions.count; i++) {
        point.fromBufferAttribute(positions, i).sub(panoramaOrigin);
        const slope = point.z / point.x,
          vertical = point.y / -point.x;
        if (Math.abs(slope) >= 0.5 || Math.abs(slope) <= 0.05 || vertical < 0.05 || vertical > 0.5)
          continue;
        const measured = -point.x;
        const expected = slope < 0 ? 900 : 240;
        errors.push(Math.abs(measured - expected) / expected);
      }
      return {
        errors,
        camera: result.calibration.camera,
        expected: [windowEye.x, windowEye.y, windowEye.z],
        fov: result.calibration.fov,
        roomFov,
      };
    } finally {
      result.material.map?.dispose();
      result.material.dispose();
      result.geometry.dispose();
      source.geometry.dispose();
      material.dispose();
      texture.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(baked.errors.length).toBeGreaterThan(25);
  expect(Math.max(...baked.errors)).toBeLessThan(0.025);
  expect(baked.camera).toEqual(baked.expected);
  expect(baked.fov).toBe(baked.roomFov);
});

test('a cold inland panorama renders by bearing with no river assets @webgl', async ({ page }) => {
  await openEmptyPage(page);
  const requests: string[] = [];
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith('/media/')) requests.push(path);
  });
  const image = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;
    for (const [i, color] of ['#ed1c24', '#214fee'].entries()) {
      ctx.fillStyle = color;
      ctx.fillRect(i * 64, 0, 64, 64);
    }
    return canvas.toDataURL('image/png').split(',')[1];
  });
  await page.route('**/inland-bearing-fixture.webp', (route) =>
    route.fulfill({ contentType: 'image/png', body: Buffer.from(image, 'base64') }),
  );
  await page.route(/\/src\/content\/window-scenes\.ts(?:\?.*)?$/, async (route) => {
    const response = await route.fetch();
    const inland = { kind: 'land', asset: 'inland-bearing-fixture', yaw: 0 };
    await route.fulfill({
      response,
      body: (await response.text()) + '\nwindowCities["上海"].clear = ' + JSON.stringify(inland),
    });
  });
  const sample = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const exteriorModule = '/src/scene/exterior.ts';
    const depthModule = '/src/scene/window-depth.ts';
    const envModule = '/src/app/environment.ts';
    const glassModule = '/src/scene/rain-glass.ts';
    const T = (await import(three)) as typeof import('three');
    const { buildExterior } = (await import(
      exteriorModule
    )) as typeof import('../src/scene/exterior');
    const { panoramaOrigin, waterfrontFarClip, panoramaMeshName } = (await import(
      depthModule
    )) as typeof import('../src/scene/window-depth');
    const { initialEnvironment } = (await import(
      envModule
    )) as typeof import('../src/app/environment');
    const { buildRainGlass } = (await import(
      glassModule
    )) as typeof import('../src/scene/rain-glass');
    const manager = new T.LoadingManager();
    const loaded = new Promise<void>((resolve, reject) => {
      manager.onLoad = resolve;
      manager.onError = (asset) => reject(new Error('Missing fixture ' + asset));
    });
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(17, 17);
    try {
      const settings = {
        ...initialEnvironment,
        city: '上海' as const,
        night: false,
        weather: '晴' as const,
        reducedMotion: false,
      };
      const scene = new T.Scene();
      const root = new T.Group();
      scene.add(root);
      const camera = new T.PerspectiveCamera(36, 1, 0.028, waterfrontFarClip);
      const glass = buildRainGlass(new T.Vector3(), new T.Vector2(2, 1));
      const exterior = buildExterior(root, new T.TextureLoader(manager), glass, settings);
      await loaded;
      exterior.update(settings, 1);
      const plate = exterior.world.getObjectByName(panoramaMeshName)!;
      camera.position.copy(panoramaOrigin);
      renderer.setRenderTarget(target);
      const read = (offset: number) => {
        camera.lookAt(camera.position.clone().add(new T.Vector3(-1, 0, offset)));
        renderer.render(scene, camera);
        const pixel = new Uint8Array(4);
        renderer.readRenderTargetPixels(target, 8, 8, 1, 1, pixel);
        return [...pixel];
      };
      const east = read(0.72);
      const west = read(-0.72);
      camera.position.z += 0.75;
      exterior.update(settings, 17);
      return {
        east,
        west,
        later: read(-0.72),
        plateVisible: plate.visible,
        hasBoat: Boolean(exterior.world.getObjectByName('Passing river ferry')),
      };
    } finally {
      target.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(requests).toEqual(['/media/panoramas/inland-bearing-fixture.webp']);
  expect(sample.plateVisible).toBe(true);
  expect(sample.hasBoat).toBe(false);
  expect(sample.east[0]).toBeGreaterThan(sample.east[2] * 3);
  expect(sample.west[2]).toBeGreaterThan(sample.west[0] * 3);
  expect(sample.later).toEqual(sample.west);
});

test('both river cities load original plates and apply each exposure mask and sailing route @webgl', async ({
  page,
}) => {
  await openEmptyPage(page);
  const requests: string[] = [];
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith('/media/')) requests.push(path);
  });
  const views = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const exteriorModule = '/src/scene/exterior.ts';
    const depthModule = '/src/scene/window-depth.ts';
    const envModule = '/src/app/environment.ts';
    const glassModule = '/src/scene/rain-glass.ts';
    const T = (await import(three)) as typeof import('three');
    const { buildExterior } = (await import(
      exteriorModule
    )) as typeof import('../src/scene/exterior');
    const { initialEnvironment } = (await import(
      envModule
    )) as typeof import('../src/app/environment');
    const { buildRainGlass } = (await import(
      glassModule
    )) as typeof import('../src/scene/rain-glass');
    const { panoramaMeshName, panoramaOrigin } = (await import(
      depthModule
    )) as typeof import('../src/scene/window-depth');
    const manager = new T.LoadingManager();
    let pending: Promise<void> = Promise.resolve();
    let finish: () => void = () => {};
    const missing: string[] = [];
    manager.onStart = () => {
      pending = new Promise<void>((resolve) => {
        finish = resolve;
      });
    };
    manager.onLoad = () => finish();
    manager.onError = (url) => missing.push(url);
    const glass = buildRainGlass(new T.Vector3(), new T.Vector2(2, 1));
    const initial = {
      ...initialEnvironment,
      city: '上海' as const,
      night: false,
      weather: '晴' as const,
      reducedMotion: true,
    };
    const model = buildExterior(new T.Group(), new T.TextureLoader(manager), glass, initial);
    const plate = model.world.getObjectByName(panoramaMeshName) as import('three').Mesh<
      import('three').BufferGeometry,
      import('three').ShaderMaterial
    >;
    const result = [];
    for (const city of ['上海', '纽约'] as const) {
      for (const name of ['clear', 'overcast', 'night'] as const) {
        const environment = {
          ...initial,
          city,
          night: name === 'night',
          weather: name === 'overcast' ? ('阴' as const) : ('晴' as const),
        };
        model.update(environment, 0);
        await pending;
        model.update(environment, 0);
        const uniforms = plate.material.uniforms;
        const vessel = model.world.getObjectByName('Passing river ferry')!;
        result.push({
          city,
          name,
          visible: vessel.visible,
          shore: [...uniforms.shoreA.value],
          secondShore: [...uniforms.shoreB.value],
          asset: new URL(uniforms.photoA.value.image.src).pathname,
          position: [vessel.position.x - panoramaOrigin.x, vessel.position.z - panoramaOrigin.z],
        });
      }
    }
    if (missing.length) throw new Error('Missing media: ' + missing.join(', '));
    return result;
  });
  expect(views).toHaveLength(6);
  expect(new Set(views.map((v) => v.shore.join(','))).size).toBe(6);
  expect(requests.filter((path) => path.includes('-wings'))).toEqual([]);
  expect(requests.filter((path) => path.includes('/river-ferry.'))).toEqual([
    '/media/models/river-ferry.glb.gz',
  ]);
  expect(requests).toContain('/media/panoramas/river-slopes.webp');
  const { CatmullRomCurve3, Vector3 } = await import('three');
  const tiered = new Set(['shanghai-day', 'new-york-night']);
  for (const view of views) {
    const exposure = windowCities[view.city][view.name];
    const expectedAsset = tiered.has(exposure.asset) ? exposure.asset + '-room' : exposure.asset;
    expect(view.asset).toBe('/media/panoramas/' + expectedAsset + '.webp');
    expect(view.shore).toEqual([...Float32Array.from(exposure.shoreline)]);
    expect(view.secondShore).toEqual(view.shore);
    expect(view.visible).toBe(true);
    const route = exposure.route!;
    const curve = new CatmullRomCurve3(route.points.map(([x, z]) => new Vector3(x, 0, z)));
    const start = curve.getPointAt(route.start);
    expect(view.position[0]).toBeCloseTo(start.x, 3);
    expect(view.position[1]).toBeCloseTo(start.z, 3);
  }
  expect(views[0].position).not.toEqual(views[3].position);
});

test('river motion waits for its post-room warmup while the photographed window renders @webgl', async ({
  page,
}) => {
  await openEmptyPage(page);
  const result = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const T = (await import(three)) as typeof import('three');
    const exteriorModule = '/src/scene/exterior.ts';
    const { buildExterior } = (await import(
      exteriorModule
    )) as typeof import('../src/scene/exterior');
    const envModule = '/src/app/environment.ts';
    const { initialEnvironment } = (await import(
      envModule
    )) as typeof import('../src/app/environment');
    const rainModule = '/src/scene/rain-glass.ts';
    const { buildRainGlass } = (await import(
      rainModule
    )) as typeof import('../src/scene/rain-glass');
    const depthModule = '/src/scene/window-depth.ts';
    const { panoramaMeshName } = (await import(
      depthModule
    )) as typeof import('../src/scene/window-depth');
    const effectModule = '/src/scene/room-effect-material.ts';
    const { warmRoomEffect } = (await import(
      effectModule
    )) as typeof import('../src/scene/room-effect-material');

    const manager = new T.LoadingManager();
    const front = Promise.withResolvers<void>();
    manager.onLoad = front.resolve;
    const controller = new AbortController();
    const root = new T.Group();
    const room = new T.Scene();
    room.add(root);
    const glass = buildRainGlass(new T.Vector3(-1.43, 0.99, 1.36), new T.Vector2(1.56, 1.27));
    const environment = { ...initialEnvironment, weather: '晴' as const };
    const exterior = buildExterior(
      root,
      new T.TextureLoader(manager),
      glass,
      environment,
      undefined,
      true,
    );
    const plate = root.getObjectByName(panoramaMeshName) as import('three').Mesh<
      import('three').BufferGeometry,
      import('three').ShaderMaterial
    >;
    const original = plate.material;
    const renderer = new T.WebGLRenderer({ preserveDrawingBuffer: true });
    renderer.setSize(33, 33, false);
    const camera = new T.PerspectiveCamera(50, 1, 0.028, 3000);
    camera.position.set(-1.05, 1.35, 0.63);
    camera.rotation.y = Math.PI / 2;
    const context = renderer.getContext();
    const adapter = context.getExtension('WEBGL_debug_renderer_info');
    const shaderErrors: string[] = [];
    renderer.debug.onShaderError = (gl, _program, vertex, fragment) => {
      shaderErrors.push(
        gl.getShaderInfoLog(vertex) || gl.getShaderInfoLog(fragment) || 'Link failed',
      );
    };
    function visiblePhoto() {
      renderer.render(room, camera);
      const pixels = new Uint8Array(33 * 33 * 4);
      context.readPixels(0, 0, 33, 33, context.RGBA, context.UNSIGNED_BYTE, pixels);
      return pixels.some((value, index) => index % 4 !== 3 && value > 15);
    }

    try {
      await front.promise;
      exterior.update(environment, 1 / 60);
      const staticPhoto = visiblePhoto();
      const initialMotion =
        original.uniforms.waterSlopes.value !== null ||
        Boolean(original.defines.STUDIO_ANIMATED_WATER);
      const warming = Promise.withResolvers<void>();
      const proceed = Promise.withResolvers<void>();
      exterior.prepareWaterMotion!(async (material) => {
        warming.resolve();
        await proceed.promise;
        return warmRoomEffect(renderer, material, controller.signal);
      }, controller.signal);
      exterior.update({ ...environment, reducedMotion: true }, 1 / 60);
      const reducedMotionRequestsWaves = original.uniforms.waterSlopes.value !== null;
      exterior.update(environment, 1 / 60);
      await warming.promise;
      const stillStaticDuringWarmup = plate.material === original;
      proceed.resolve();
      const deadline = performance.now() + 12000;
      while (plate.material === original && performance.now() < deadline)
        await new Promise<void>((resolve) => setTimeout(resolve, 16));
      exterior.update(environment, 1 / 60);
      return {
        gpu: adapter && context.getParameter(adapter.UNMASKED_RENDERER_WEBGL),
        shaderErrors,
        staticPhoto,
        initialMotion,
        reducedMotionRequestsWaves,
        stillStaticDuringWarmup,
        sharedUniforms: plate.material.uniforms === original.uniforms,
        activated: Boolean(plate.material.defines.STUDIO_ANIMATED_WATER),
        clock: plate.material.uniforms.riverTime.value,
        animatedPhoto: visiblePhoto(),
      };
    } finally {
      controller.abort();
      renderer.dispose();
      renderer.forceContextLoss();
    }
  });
  expect(result.gpu).toContain('SwiftShader');
  expect(result.shaderErrors).toEqual([]);
  expect(result.staticPhoto).toBe(true);
  expect(result.initialMotion).toBe(false);
  expect(result.reducedMotionRequestsWaves).toBe(false);
  expect(result.stillStaticDuringWarmup).toBe(true);
  expect(result.sharedUniforms).toBe(true);
  expect(result.activated).toBe(true);
  expect(result.clock).toBeGreaterThan(0);
  expect(result.animatedPhoto).toBe(true);
});

test('native low reuses prepared waterfront motion only during window views', async ({ page }) => {
  await openEmptyPage(page);
  const result = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const T = (await import(three)) as typeof import('three');
    const exteriorModule = '/src/scene/exterior.ts';
    const { buildExterior } = (await import(
      exteriorModule
    )) as typeof import('../src/scene/exterior');
    const envModule = '/src/app/environment.ts';
    const { initialEnvironment } = (await import(
      envModule
    )) as typeof import('../src/app/environment');
    const rainModule = '/src/scene/rain-glass.ts';
    const { buildRainGlass } = (await import(
      rainModule
    )) as typeof import('../src/scene/rain-glass');
    const depthModule = '/src/scene/window-depth.ts';
    const { panoramaMeshName } = (await import(
      depthModule
    )) as typeof import('../src/scene/window-depth');

    const root = new T.Group();
    const glass = buildRainGlass(new T.Vector3(), new T.Vector2(1.56, 1.27));
    const environment = { ...initialEnvironment, quality: 'low' as const };
    const exterior = buildExterior(
      root,
      new T.TextureLoader(),
      glass,
      environment,
      undefined,
      true,
      true,
    );
    const plate = root.getObjectByName(panoramaMeshName) as import('three').Mesh<
      import('three').BufferGeometry,
      import('three').ShaderMaterial
    >;
    const original = plate.material;
    const warming = Promise.withResolvers<import('three').ShaderMaterial>();
    exterior.prepareWaterMotion!(async (moving) => {
      warming.resolve(moving);
      return true;
    }, new AbortController().signal);
    exterior.update(environment, 1);
    exterior.update(environment, 1, true);
    const pending = plate.material === original;
    const moving = await warming.promise;
    await new Promise<void>((resolve) => setTimeout(resolve, 0));

    exterior.update(environment, 1);
    const room = plate.material === original && original.uniforms.riverTime.value === 0;
    exterior.update(environment, 1, true);
    const close = plate.material === moving && original.uniforms.riverTime.value === 1;
    exterior.update({ ...environment, reducedMotion: true }, 1, true);
    const reduced = plate.material === original && original.uniforms.riverTime.value === 1;
    exterior.update(environment, 1);
    const exit = plate.material === original && original.uniforms.riverTime.value === 1;
    const ferry = root.getObjectByName('Passing river ferry');
    const noFerry =
      ferry?.visible === false &&
      original.uniforms.ferryTrack.value.equals(new T.Vector4(100000, 100000, 0, -1));
    exterior.update(environment, 1, true);
    const returnToWindow = plate.material === moving && original.uniforms.riverTime.value === 2;
    exterior.update({ ...environment, quality: 'high' }, 1);
    const high = plate.material === moving && original.uniforms.riverTime.value === 3;
    return {
      pending,
      room,
      close,
      reduced,
      exit,
      noFerry,
      returnToWindow,
      high,
      sharedUniforms: original.uniforms === moving.uniforms,
      staticShader: !original.defines.STUDIO_ANIMATED_WATER,
      animatedShader: Boolean(moving.defines.STUDIO_ANIMATED_WATER),
    };
  });
  expect(result).toEqual({
    pending: true,
    room: true,
    close: true,
    reduced: true,
    exit: true,
    noFerry: true,
    returnToWindow: true,
    high: true,
    sharedUniforms: true,
    staticShader: true,
    animatedShader: true,
  });
});
