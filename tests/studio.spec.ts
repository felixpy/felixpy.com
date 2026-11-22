import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import {
  DoubleSide,
  Euler,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  Quaternion,
  Raycaster,
  Vector3,
} from 'three';
import { benchEye, eye, gearEye, roomFov, windowEye } from '../src/scene/camera';
import { panoramaGeometry } from '../src/scene/exterior';
import { desk, deskSetup, display, windowOpening } from '../src/scene/layout';
import { advance, newFlight } from '../src/desktop/apps/arcade/flight';
import { initialEnvironment, pressRemote } from '../src/app/environment';
import {
  ceilingLightLevel,
  homeLights,
  isHomeLightOn,
  toggleHomeLight,
} from '../src/app/home-lights';
import { editions } from '../src/content/books';

test('Home can switch the ceiling in daylight and preserve its dimmer across sunset', () => {
  expect(initialEnvironment.ceiling).toBe(1);
  const day = pressRemote({ ...initialEnvironment, ceiling: 0.35, aura: false }, 5);
  for (const { id } of homeLights) {
    const lit = toggleHomeLight(day, id);
    expect(
      homeLights.filter((light) => isHomeLightOn(lit, light.id)).map((light) => light.id),
    ).toEqual([id]);
    expect(lit.aura).toBe(false);
    expect(lit.night).toBe(false);
  }
  const lit = toggleHomeLight(day, 'ceilingLamp');
  expect(ceilingLightLevel(lit)).toBe(0.35);
  expect(ceilingLightLevel(toggleHomeLight(lit, 'ceilingLamp'))).toBe(0);
  expect(ceilingLightLevel(pressRemote(day, 5))).toBe(0.35);
  expect(ceilingLightLevel(toggleHomeLight({ ...day, ceiling: 0 }, 'ceilingLamp'))).toBe(
    initialEnvironment.ceiling,
  );
});

test('shuffle selects a different window scene and preserves the room settings', () => {
  for (let i = 0; i < 32; i++) {
    const next = pressRemote(initialEnvironment, 4);
    expect([next.city, next.weather, next.night]).not.toEqual([
      initialEnvironment.city,
      initialEnvironment.weather,
      initialEnvironment.night,
    ]);
    expect(next.season).toBe(initialEnvironment.season);
    expect(next.blinds).toBe(initialEnvironment.blinds);
  }
});

test('the day and night key synchronizes the independently switched lights', () => {
  const day = pressRemote({ ...initialEnvironment, ceiling: 0.42, lamp: false }, 5);
  const night = pressRemote({ ...day, wallLamp: true, toolBoardLamp: true }, 5);
  for (const key of [
    'lamp',
    'benchLamp',
    'toolBoardLamp',
    'wallLamp',
    'pictureLamp',
    'floorLamp',
    'screenBar',
  ] as const) {
    expect(day[key]).toBe(false);
    expect(night[key]).toBe(true);
  }
  expect(night.ceiling).toBe(0.42);
  expect(pressRemote({ ...day, ceiling: 0 }, 5).ceiling).toBeGreaterThan(0);
  for (const aura of [true, false]) {
    let state = { ...initialEnvironment, aura };
    for (const key of [5, 5, 4, 5, 4]) {
      state = pressRemote(state, key);
      expect(state.aura).toBe(aura);
    }
  }
});

test('the flight model steers, fires automatically and applies weapon and shield pickups', () => {
  const flight = newFlight();
  const before = { ...flight.pilot };
  expect(advance(flight, new Set(['ArrowLeft', 'ArrowUp']), 0.08)).toBe('playing');
  expect(flight.pilot.x).toBeLessThan(before.x);
  expect(flight.pilot.y).toBeLessThan(before.y);
  expect(flight.shots).toHaveLength(2);
  const shot = flight.shots[0];
  flight.drones.push({
    kind: 'scout',
    x: shot.x,
    y: shot.y - 2,
    origin: shot.x,
    age: 0.4,
    speed: 0,
    phase: -1,
    hp: 1,
    maxHp: 1,
    flash: 0,
    fireAt: Infinity,
  });
  advance(flight, new Set(), 0.01);
  expect(flight.score).toBe(100);
  expect(flight.pickups[0]?.kind).toBe('power');
  Object.assign(flight.pickups[0], { x: flight.pilot.x, y: flight.pilot.y });
  flight.pickups.push({ x: flight.pilot.x, y: flight.pilot.y, kind: 'shield' });
  advance(flight, new Set(), 0.01);
  expect(flight.power).toBe(2);
  expect(flight.barrier).toBe(true);
  flight.pilot.cooldown = 0;
  flight.shots = [{ x: flight.pilot.x, y: flight.pilot.y, vx: 0, vy: 10, hostile: true }];
  advance(flight, new Set(), 0.01);
  expect(flight.shots).toHaveLength(3);
  expect(flight.barrier).toBe(false);
  expect(flight.shields).toBe(3);
  flight.wave = 3;
  flight.spawned = 18;
  expect(advance(flight, new Set(), 0.01)).toBe('playing');
  expect(flight.wave).toBe(4);
  flight.pickups.push({ x: flight.pilot.x, y: flight.pilot.y, kind: 'missile' });
  advance(flight, new Set(), 0.01);
  flight.drones.push({
    kind: 'scout',
    x: flight.pilot.x + 55,
    y: flight.pilot.y - 70,
    origin: flight.pilot.x + 55,
    age: 0.5,
    speed: 30,
    phase: 0,
    hp: 1,
    maxHp: 1,
    flash: 0,
    fireAt: Infinity,
  });
  advance(flight, new Set(), 0.04);
  expect(flight.shots.find((shot) => shot.homing)?.vx).toBeGreaterThan(0);
});

test('late formations enter before taking damage and elites scale with the player loadout', () => {
  const eliteAt = (power: number, missiles: number) => {
    const flight = newFlight(() => 0.5);
    Object.assign(flight, { wave: 8, power, missiles, spawned: 2, next: 0 });
    advance(flight, new Set(), 0);
    return { flight, elite: flight.drones[0] };
  };
  const basic = eliteAt(1, 0);
  const { flight, elite } = eliteAt(4, 2);
  expect(elite.kind).toBe('elite');
  expect(elite.hp).toBeGreaterThan(basic.elite.hp * 2);
  const shoot = () => {
    flight.shots.push({ x: elite.x, y: elite.y, vx: 0, vy: 0, hostile: false });
    advance(flight, new Set(), 0);
  };
  elite.y = 10;
  shoot();
  expect(elite.hp).toBe(elite.maxHp);
  flight.shots = [];
  Object.assign(elite, { age: 0.6, y: 36 });
  advance(flight, new Set(), 0);
  shoot();
  expect(elite.hp).toBe(elite.maxHp - 1);
  for (let i = 1; i < elite.maxHp; i++) shoot();
  expect(flight.defeated).toBe(1);
  expect(flight.pickups[0]?.kind).toBe('power');
  expect(flight.nextSupplyKill).toBe(6);
});

test('the 48-inch LG OLED and its cabinet are built at scene scale', () => {
  expect(Math.hypot(display.width, display.height) / 0.0254).toBeCloseTo(48, 6);
  expect(display.width / display.height).toBeCloseTo(16 / 9, 6);
  expect(display.outerWidth).toBe(1.071);
  expect(display.outerHeight).toBe(0.62);
});

test('the panorama covers the window from the seat and across the room', () => {
  const { wall, y0, y1, z0, z1 } = windowOpening;
  const geometry = panoramaGeometry();
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const panorama = new Mesh(geometry, material);
  const ray = new Raycaster();
  try {
    const origins = [
      new Vector3(eye.x, eye.y, eye.defaultZ),
      new Vector3(eye.x - 0.29, 1.28, 1.49),
      new Vector3(0.8, eye.y, 2.92),
      new Vector3(-1.05, eye.y, 2.53),
      new Vector3(2.3, eye.y, 1.75),
    ];
    for (const origin of origins) {
      for (const y of [y0, (y0 + y1) / 2, y1])
        for (const z of [z0, (z0 + z1) / 2, z1]) {
          const to = new Vector3(wall - 0.154, y, z).sub(origin).normalize();
          ray.set(origin, to);
          expect(ray.intersectObject(panorama)).not.toHaveLength(0);
        }
    }
  } finally {
    geometry.dispose();
    material.dispose();
  }
});

test('the waterfront stays across the river as the camera moves and still occludes lights @webgl', async ({
  page,
}) => {
  await page.goto('/');
  const sample = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const shader = '/src/scene/window-depth.ts';
    const exterior = '/src/scene/exterior.ts';
    const T = (await import(three)) as typeof import('three');
    const { panoramaMaterial, panoramaOrigin, skylineDepth, waterfrontFarClip, waterfrontPoint } =
      (await import(shader)) as typeof import('../src/scene/window-depth');
    const { panoramaGeometry } = (await import(exterior)) as typeof import('../src/scene/exterior');
    const renderer = new T.WebGLRenderer();
    const target = new T.WebGLRenderTarget(33, 33);
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(50, 1, 0.028, waterfrontFarClip);
    const { material, uniforms } = panoramaMaterial();
    const photo = new T.DataTexture(new Uint8Array([230, 24, 24, 255]), 1, 1);
    const depth = new T.DataTexture(new Uint8Array([255, 255, 0, 255, 0, 0, 0, 255]), 2, 1);
    photo.needsUpdate = depth.needsUpdate = true;
    uniforms.photoA.value = photo;
    uniforms.depthA.value = depth;
    uniforms.rangeA.value.set(130, 980);
    const waterline = uniforms.waterlines.value.x;
    const calibration = uniforms.calibrationA.value.set(0.5, 0.43, 0.34, 0.76);
    const plate = new T.Mesh(panoramaGeometry(), material);
    const light = new T.Mesh(
      new T.SphereGeometry(1),
      new T.MeshBasicMaterial({ color: '#00ff00' }),
    );
    light.renderOrder = 1;
    scene.add(plate, light);
    camera.position.copy(panoramaOrigin);
    try {
      const occlusion = [0.37, 0.63].map((u) => {
        waterfrontPoint(u, 0.4, calibration, 300, waterline, light.position);
        camera.lookAt(light.position);
        renderer.setRenderTarget(target);
        renderer.render(scene, camera);
        const pixel = new Uint8Array(4);
        renderer.readRenderTargetPixels(target, 16, 16, 1, 1, pixel);
        return [...pixel];
      });
      const stripes = new Uint8Array(256 * 4);
      for (let x = 0; x < 256; x++) {
        const red = Math.abs(x - 110) <= 2,
          green = Math.abs(x - 146) <= 2;
        stripes.set([red ? 255 : 12, green ? 255 : 12, 12, 255], x * 4);
      }
      const landmarks = new T.DataTexture(stripes, 256, 1);
      landmarks.needsUpdate = true;
      uniforms.photoA.value = landmarks;
      light.visible = false;
      const alignment = [0.34, 0.56].flatMap((v) =>
        [110, 146].flatMap((x, channel) => {
          const direction = waterfrontPoint(
            (x + 0.5) / 256,
            v,
            calibration,
            skylineDepth,
            waterline,
            new T.Vector3(),
          )
            .sub(panoramaOrigin)
            .normalize();
          return [0, 1.35, -0.52].map((shift) => {
            camera.position.copy(panoramaOrigin).add(new T.Vector3(0, 0, shift));
            // Keep the same bearing as the camera translates about a desk-to-window distance.
            camera.lookAt(camera.position.clone().add(direction));
            renderer.setRenderTarget(target);
            renderer.render(scene, camera);
            const pixel = new Uint8Array(4);
            renderer.readRenderTargetPixels(target, 16, 16, 1, 1, pixel);
            return pixel[channel] > 200 && pixel[1 - channel] < 30;
          });
        }),
      );
      landmarks.dispose();

      const horizontalMarker = new Uint8Array(256 * 4);
      for (let y = 0; y < 256; y++) {
        const red = Math.round(255 * Math.max(0, 1 - Math.abs(y - 63) / 14));
        horizontalMarker.set([red, 0, 0, 255], y * 4);
      }
      const shore = new T.DataTexture(horizontalMarker, 1, 256);
      shore.needsUpdate = true;
      uniforms.photoA.value = shore;
      camera.position.copy(panoramaOrigin);
      camera.rotation.set(0, Math.PI / 2, 0, 'YXZ');
      renderer.render(scene, camera);
      const pixels = new Uint8Array(33 * 33 * 4);
      renderer.readRenderTargetPixels(target, 0, 0, 33, 33, pixels);
      const shoreline = [2, 16, 30].map((x) => {
        const samples = Array.from({ length: 33 }, (_, y) => pixels[(y * 33 + x) * 4]);
        return samples.indexOf(Math.max(...samples));
      });
      shore.dispose();
      return { occlusion, alignment, shoreline };
    } finally {
      renderer.dispose();
      renderer.forceContextLoss();
      target.dispose();
      photo.dispose();
      depth.dispose();
      plate.geometry.dispose();
      material.dispose();
      light.geometry.dispose();
      light.material.dispose();
    }
  });
  const { occlusion, alignment, shoreline } = sample;
  expect(occlusion[0][0]).toBeGreaterThan(occlusion[0][1] * 3);
  expect(occlusion[1][1]).toBeGreaterThan(occlusion[1][0] * 3);
  expect(alignment).not.toContain(false);
  expect(shoreline[1]).toBeGreaterThan(3);
  expect(shoreline).toEqual([shoreline[1], shoreline[1], shoreline[1]]);
});

async function start(page: Page) {
  await page.goto('/?review', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(window.__studioReview));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await expect(page.locator('.studio-loading')).toHaveCount(0, { timeout: 20_000 });
}

test('the Codex Micro can be picked up, rotated and put back on the desk @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await start(page);
  const room = page.locator('.studio');
  const pose = () => page.evaluate(() => window.__studioReview!.objectPose('codex-micro')!);
  const home = await pose();
  await page.waitForFunction(() =>
    Number.isFinite(window.__studioReview!.bounds('Codex Micro').min[1]),
  );
  const bounds = await page.evaluate(() => window.__studioReview!.bounds('Codex Micro'));
  expect(bounds.min[1]).toBeCloseTo(desk.top, 4);
  expect(bounds.min[2]).toBeGreaterThan(desk.back);
  expect(bounds.max[2]).toBeLessThan(desk.front);
  expect(bounds.max[0]).toBeLessThan(deskSetup.mat.x - deskSetup.mat.width / 2);
  const point = await page.evaluate(() => window.__studioReview!.project('codex-micro')!);
  await expect
    .poll(
      async () => {
        await page.mouse.move(point.x, point.y);
        return page.locator('.world-cue').textContent();
      },
      { timeout: 20_000 },
    )
    .toContain('Inspect the Codex Micro');
  await page.mouse.click(point.x, point.y);
  await expect(room).toHaveAttribute('data-mode', 'inspect');
  await expect(page.locator('.interaction-caption')).toContainText('Codex Micro');
  const before = new Quaternion().fromArray((await pose()).rotation);
  await page.mouse.move(720, 450);
  await page.mouse.down();
  await page.mouse.move(880, 510, { steps: 8 });
  await page.mouse.up();
  await expect
    .poll(async () => before.angleTo(new Quaternion().fromArray((await pose()).rotation)))
    .toBeGreaterThan(0.2);
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await expect.poll(pose).toEqual(home);
});

test('the monitor light and wireless dial switch the same lamp @webgl', async ({ page }) => {
  test.setTimeout(150_000);
  const width = 1440;
  const height = 900;
  await page.setViewportSize({ width, height });
  await page.addInitScript(() => {
    if (!localStorage.getItem('felix-studio-v1'))
      localStorage.setItem(
        'felix-studio-v1',
        JSON.stringify({ reducedMotion: true, quality: 'low' }),
      );
  });
  await start(page);
  const room = page.locator('.studio');
  const dial = await page.evaluate(() =>
    window.__studioReview!.bounds('Wireless light controller'),
  );
  expect(dial.min[1]).toBeCloseTo(desk.top, 4);
  expect(dial.min[2]).toBeGreaterThan(desk.back);
  expect(dial.max[2]).toBeLessThan(desk.front);
  expect(dial.min[0]).toBeGreaterThan(deskSetup.mat.x + deskSetup.mat.width / 2);
  const verifyPower = async (on: boolean, mode = 'room') => {
    await expect(room).toHaveAttribute('data-mode', mode);
    await expect
      .poll(
        () =>
          page.evaluate(() => {
            const lights = window.__studioReview!.lightLevels();
            return [lights.screenBar > 0, lights.lamp > 0];
          }),
        { timeout: 30_000 },
      )
      .toEqual([on, true]);
  };
  const clickObject = async (name: string) => {
    const point = await page.evaluate((id) => window.__studioReview!.project(id)!, name);
    await page.mouse.click(point.x, point.y);
  };
  const clickBar = async (along: number) => {
    const { bounds, pose } = await page.evaluate(() => ({
      bounds: window.__studioReview!.bounds('screenbar-halo-2 • lens'),
      pose: window.__studioReview!.camera(),
    }));
    const camera = new PerspectiveCamera(pose.fov, width / height);
    camera.position.fromArray(pose.position);
    camera.quaternion.fromArray(pose.rotation);
    camera.updateMatrixWorld();
    const point = new Vector3()
      .fromArray(bounds.min)
      .lerp(new Vector3().fromArray(bounds.max), 0.5);
    point.x = bounds.min[0] + (bounds.max[0] - bounds.min[0]) * along;
    point.project(camera);
    await page.mouse.click(((1 + point.x) * width) / 2, ((1 - point.y) * height) / 2);
  };
  await verifyPower(true);
  await clickBar(0.82);
  await verifyPower(false);
  await clickObject('computer');
  await expect(room).toHaveAttribute('data-mode', 'computer');
  await expect(page.locator('.screen-anchor')).toHaveAttribute('data-interactive', 'true', {
    timeout: 20_000,
  });
  await clickBar(0.82);
  await verifyPower(true, 'computer');
  await clickBar(0.18);
  await verifyPower(false, 'computer');
  await page.keyboard.press('Escape');
  await verifyPower(false);
  await start(page);
  await verifyPower(true);
  await clickObject('Touch face');
  await verifyPower(false);
  await clickBar(0.18);
  await verifyPower(true);
  await clickObject('Touch face');
  await verifyPower(false);
});

test('shelved covers keep their editions and load full prints before extraction @webgl', async ({
  page,
  baseURL,
}) => {
  const loaded = new Set<string>();
  page.on('response', (response) => {
    const { pathname } = new URL(response.url());
    if (!response.ok()) return;
    if (pathname.startsWith('/media/books/'))
      loaded.add(pathname.split('/').pop()!.replace('.webp', ''));
    if (pathname === '/media/graphics/shelf-covers.webp') loaded.add('shelf-covers');
  });
  const visible = ['sicp', 'ways', 'creativity', 'color', 'design-us', 'shelf-covers'];
  const delayed = Promise.withResolvers<void>();
  let duneRequests = 0;
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(baseURL!).origin) return route.abort();
    if (url.pathname === '/media/books/walden.webp') await delayed.promise;
    if (url.pathname === '/media/books/dune.webp' && ++duneRequests === 1) return route.abort();
    return route.continue();
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  try {
    await start(page);
    await expect.poll(() => [...loaded].sort()).toEqual([...visible].sort());
    await page.mouse.move(840, 430);
    await page.mouse.down();
    await page.mouse.move(960, 430, { steps: 10 });
    await page.mouse.up();
    await expect
      .poll(async () => (await page.evaluate(() => window.__studioReview!.project('book-4')))!.x)
      .toBeLessThan(1400);
    const cover = await page.evaluate(() => window.__studioReview!.project('book-4'));
    expect(cover).not.toBeNull();
    await page.mouse.click(cover!.x, cover!.y);
    await expect(page.locator('.interaction-caption')).toContainText(editions[4].en);
    await expect(page.locator('a[href="' + editions[4].source + '"]')).toHaveCount(0);
    await page.keyboard.press('Escape');
    await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
    await page.evaluate(() => window.__studioReview!.activate('book-8'));
    await expect.poll(() => loaded.has('sound-and-fury')).toBe(true);
    await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  } finally {
    delayed.resolve();
  }
  await expect(page.locator('.interaction-caption')).toContainText('William Faulkner');
  await expect(page.locator('a[href="' + editions[8].source + '"]')).toHaveCount(0);
  expect([...loaded].sort()).toEqual([...visible, 'sound-and-fury', 'walden'].sort());
  await page.keyboard.press('Escape');
  await page.evaluate(() => window.__studioReview!.activate('book-8'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
  expect(duneRequests).toBe(2);
  await page.keyboard.press('Escape');
  await page.evaluate(() => window.__studioReview!.activate('book-14'));
  await expect(page.locator('.interaction-caption')).toContainText(editions[14].en);
  expect([...loaded].sort()).toEqual(
    [...visible, 'sound-and-fury', 'walden', 'dune', 'type'].sort(),
  );
});

test('an editable single-book export restores its full cover independently of its neighbors @webgl', async ({
  page,
}) => {
  const covers = new Set<string>();
  page.on('request', (request) => {
    const { pathname } = new URL(request.url());
    if (pathname.startsWith('/media/books/')) covers.add(pathname);
  });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ quality: 'low', reducedMotion: true }),
    ),
  );
  await start(page);
  const before = new Set(covers);
  const book = editions.find((edition) => edition.key === 'frankenstein')!;
  const url = '/media/books/' + book.key + '.webp';
  expect(before.has(url)).toBe(false);
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.evaluate(
      (name) => window.__studioReview!.exportRoom(name, true),
      `${book.en} (${book.imprint}, ${book.year})`,
    ),
  ]);
  expect([...covers].filter((path) => !before.has(path))).toEqual([url]);
  const bytes = await readFile((await download.path())!);
  const jsonLength = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  const front = gltf.nodes.find((node: { name: string }) => node.name?.endsWith(' · front'));
  const primitive = gltf.meshes[front.mesh].primitives[0];
  const index = gltf.materials[primitive.material].pbrMetallicRoughness.baseColorTexture.index;
  const image = gltf.images[gltf.textures[index].source];
  expect(image.mimeType).toBe('image/png');
  const offset = 28 + jsonLength + (gltf.bufferViews[image.bufferView].byteOffset ?? 0);
  const dimensions = await page.evaluate(async (url) => {
    const photo = new Image();
    photo.src = url;
    await photo.decode();
    return [photo.naturalWidth, photo.naturalHeight];
  }, url);
  expect([bytes.readUInt32BE(offset + 16), bytes.readUInt32BE(offset + 20)]).toEqual(dimensions);
});

test('the room starts music on the first drag and turns without leaving the seat @webgl', async ({
  page,
}) => {
  const rearRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().endsWith('/models/h3c.mesh.gz')) rearRequests.push(request.url());
  });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => {
    window.requestIdleCallback = () => 0;
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    );
    let pointerPressed = false;
    window.addEventListener(
      'pointerdown',
      () => {
        pointerPressed = true;
      },
      { capture: true, once: true },
    );
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = async function () {
      if (!this.src.includes('/media/audio/music/')) return play.call(this);
      if (!pointerPressed) {
        document.documentElement.dataset.roomMusic = 'blocked';
        throw new DOMException('Audio requires a gesture', 'NotAllowedError');
      }
      await play.call(this);
      document.documentElement.dataset.roomMusic = 'playing';
    };
  });
  await start(page);
  expect(rearRequests).toHaveLength(0);
  await expect(page.locator('html')).toHaveAttribute('data-room-music', 'blocked');
  const initial = await page.evaluate(() => window.__studioReview!.camera());
  await page.mouse.move(220, 395);
  await page.mouse.down();
  await page.mouse.move(440, 395, { steps: 10 });
  await expect.poll(() => rearRequests.length).toBe(1);
  await page.waitForFunction(() => Boolean(window.__studioReview!.objectPose('H3C frame-alloy')));
  await expect
    .poll(async () => {
      const snapshot = await page.evaluate(() => window.__studioReview!.camera());
      const rotation = new Quaternion(...snapshot.rotation);
      return new Vector3(0, 0, -1).applyQuaternion(rotation).x;
    })
    .toBeGreaterThan(0.5);
  await expect(page.locator('html')).toHaveAttribute('data-room-music', 'playing');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await page.mouse.up();
  await page.mouse.wheel(0, -430);
  await expect
    .poll(async () => (await page.evaluate(() => window.__studioReview!.camera())).fov)
    .toBeLessThan(initial.fov);
  await page.keyboard.press('w');
  await expect
    .poll(async () => (await page.evaluate(() => window.__studioReview!.camera())).position)
    .toEqual(initial.position);
  const layout = await page.evaluate(() => {
    const pose = (id: string) => window.__studioReview!.objectPose(id)!;
    return {
      left: pose('Left speaker'),
      right: pose('Right speaker'),
      leftBox: window.__studioReview!.bounds('Left speaker'),
      rightBox: window.__studioReview!.bounds('Right speaker'),
      shelf: window.__studioReview!.bounds('Hexcal Studio'),
      display: pose('LG OLED evo G6 · OLED48G6PCA'),
      mat: pose('Desk mat'),
      keyboard: pose('keyboard'),
      chair: pose('Desk task chair'),
    };
  });
  expect(layout.left.position[2]).toBe(layout.right.position[2]);
  expect((layout.left.position[0] + layout.right.position[0]) / 2).toBeCloseTo(display.x, 6);
  expect(layout.left.rotation).toEqual(layout.display.rotation);
  expect(layout.right.rotation).toEqual(layout.display.rotation);
  expect(layout.shelf.min[0] - layout.leftBox.max[0]).toBeCloseTo(0.05, 3);
  expect(layout.rightBox.min[0] - layout.shelf.max[0]).toBeCloseTo(0.05, 3);
  for (const item of [layout.mat, layout.keyboard, layout.chair])
    expect(item.position[0]).toBe(display.x);
  await page.evaluate(() => window.__studioReview!.activate('development-phone'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
  await expect(page.getByText('iPhone 18 Pro Max', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
});

test('clicking the workbench switches seats and inspection returns to the active seat @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await start(page);
  const room = page.locator('.studio');
  const camera = () => page.evaluate(() => window.__studioReview!.camera());
  const clickObject = async (name: string) => {
    const point = await page.evaluate((id) => window.__studioReview!.project(id), name);
    expect(point).not.toBeNull();
    await page.mouse.click(point!.x, point!.y);
  };
  await page.mouse.move(550, 380);
  await page.mouse.down();
  await page.mouse.move(859, 397, { steps: 8 });
  await page.mouse.up();
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  const desk = await camera();
  await clickObject('Workbench top');
  await expect(room).toHaveAttribute('data-mode', 'bench');
  await expect
    .poll(async () => (await camera()).position)
    .toEqual([benchEye.x, benchEye.y, benchEye.z]);
  await expect(page.locator('.workbench-exit-hint')).toHaveText('Esc Return to the computer desk');
  await page.evaluate(() => {
    window.__studioReview!.activate('workbench');
    window.__studioReview!.activate('workbench-stool');
    window.__studioReview!.activate('album-01');
    window.__studioReview!.activate('album-02');
  });
  await expect(room).toHaveAttribute('data-mode', 'bench');
  const [rocket, mat, table] = await page.evaluate(() =>
    ['Standing launch vehicle scale model', 'Self-healing cutting mat', 'Workbench top'].map(
      window.__studioReview!.bounds,
    ),
  );
  expect(rocket.min[1]).toBeCloseTo(table.max[1], 5);
  expect(rocket.min[0]).toBeGreaterThan(mat.max[0]);
  expect(rocket.max[0]).toBeLessThan(table.max[0]);
  expect(rocket.min[2]).toBeGreaterThan(table.min[2]);
  expect(rocket.max[2]).toBeLessThan(table.max[2]);
  const seated = await camera();
  await page.mouse.wheel(0, -440);
  await expect.poll(async () => (await camera()).fov).toBeLessThan(seated.fov);
  const workbench = await camera();
  await page.keyboard.press('w');
  await expect.poll(camera).toEqual(workbench);
  await clickObject('switch-sampler');
  await expect(room).toHaveAttribute('data-mode', 'inspect');
  await expect(page.getByText(/Twelve-switch sampler/)).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'bench');
  await expect.poll(camera).toEqual(workbench);
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await expect.poll(camera).toEqual(desk);
  await expect(page.locator('.workbench-exit-hint')).toHaveCount(0);
});

test('the night equipment view frames the rack, controls each fixture and restores the pack inspection @webgl', async ({
  page,
}, testInfo) => {
  test.setTimeout(160_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const quality = testInfo.project.use.launchOptions?.args?.includes('--use-angle=d3d11')
    ? 'high'
    : 'low';
  await page.addInitScript(
    (quality) =>
      localStorage.setItem(
        'felix-studio-v1',
        JSON.stringify({
          quality,
          automaticQuality: false,
          reducedMotion: true,
          night: true,
          ceiling: 1,
          wallLamp: true,
          floorLamp: true,
        }),
      ),
    quality,
  );
  await start(page);
  await page.mouse.move(250, 450);
  await page.mouse.down();
  await page.mouse.move(1014, 450, { steps: 4 });
  await page.mouse.up();
  const camera = () => page.evaluate(() => window.__studioReview!.camera());
  await expect
    .poll(async () => new Quaternion(...(await camera()).rotation).angleTo(new Quaternion()))
    .toBeGreaterThan(2.5);
  const seated = await camera();
  const lens = new PerspectiveCamera(seated.fov, 1.6);
  lens.position.fromArray(seated.position);
  lens.quaternion.fromArray(seated.rotation);
  lens.updateMatrixWorld();
  const rack = new Vector3(0.71, 1.59, 3.1).project(lens);
  const x = (1 + rack.x) * 720,
    y = (1 - rack.y) * 450;
  await expect
    .poll(
      async () => {
        await page.mouse.move(x + 2, y);
        await page.mouse.move(x, y);
        return page.locator('.world-cue').innerText();
      },
      { timeout: 15_000 },
    )
    .toContain('Explore the gear wall');
  await page.mouse.click(x, y);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'gear');
  await page.waitForFunction(() => performance.getEntriesByName('studio-room-shaded').length > 0);
  const benchItems = await page.evaluate(() => {
    const review = window.__studioReview!;
    return {
      tent: review.objectPose('Snow_Peak_SD-641_·_Land_Breeze_Pro1_carry_bag')?.position,
      shoes: [review.project('jieshan-left'), review.project('jieshan-right')],
    };
  });
  expect(benchItems.shoes).toEqual([null, null]);
  expect(benchItems.tent?.[0]).toBeCloseTo(0, 5);
  expect(benchItems.tent?.[1]).toBeCloseTo(0.12773, 5);
  await expect.poll(async () => (await camera()).fov).toBeCloseTo(50);
  for (const item of ['talon-pack', 'titanium-cup', 'alpine-carbon-cork-left']) {
    const point = await page.evaluate((id) => window.__studioReview!.project(id), item);
    expect(point!.x).toBeGreaterThan(0);
    expect(point!.x).toBeLessThan(1440);
    expect(point!.y).toBeGreaterThan(0);
    expect(point!.y).toBeLessThan(900);
  }
  const normal = await camera();
  for (const [id, cue] of [
    ['titanium-cup', 'titanium cup'],
    ['camp-lantern', 'camping lantern'],
    ['aurora-bottle', 'titanium bottle'],
    ['trek-cookset', 'Trek 900 cookset'],
    ['field-coffee-master', 'coffee percolator'],
  ]) {
    const home = await page.evaluate((id) => window.__studioReview!.objectPose(id), id);
    const point = await page.evaluate((id) => window.__studioReview!.project(id), id);
    await page.mouse.move(point!.x, point!.y);
    await expect(page.locator('.world-cue')).toContainText(cue);
    await page.mouse.click(point!.x, point!.y);
    await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
    const held = () => page.evaluate((id) => window.__studioReview!.objectPose(id), id);
    await expect
      .poll(async () => (await held())?.position, { message: `Lift ${id}` })
      .not.toEqual(home?.position);
    const portCover = () =>
      page.evaluate(() => window.__studioReview!.objectPose('ES-080_·_retained_port_cover'));
    if (id === 'camp-lantern')
      await expect
        .poll(async () => (await portCover())?.rotation[2])
        .toBeCloseTo(Math.sin((87 * Math.PI) / 360), 4);
    const rotation = (await held())!.rotation;
    await page.mouse.move(710, 440);
    await page.mouse.down();
    await page.mouse.move(830, 460, { steps: 2 });
    await page.mouse.up();
    await expect.poll(async () => (await held())?.rotation).not.toEqual(rotation);
    await page.keyboard.press('Escape');
    await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'gear');
    await expect.poll(held, { message: `Restore ${id} to its mounting point` }).toEqual(home);
    if (id === 'camp-lantern')
      await expect.poll(async () => (await portCover())?.rotation).toEqual([0, 0, 0, 1]);
    await expect.poll(camera).toEqual(normal);
  }
  const projectWorld = async (world: Vector3) => {
    const pose = await camera();
    const view = new PerspectiveCamera(pose.fov, 1.6);
    view.position.fromArray(pose.position);
    view.quaternion.fromArray(pose.rotation);
    view.updateMatrixWorld();
    const p = world.clone().project(view);
    return { x: (1 + p.x) * 720, y: (1 - p.y) * 450 };
  };
  const boardTop = await projectWorld(new Vector3(0.71, 2.16, 3.1));
  const seat = await projectWorld(new Vector3(0.71, 0.47, 2.88));
  expect(boardTop.y).toBeGreaterThanOrEqual(0);
  expect(boardTop.y).toBeLessThan(140);
  expect(seat.y).toBeGreaterThan(750);
  expect(seat.y).toBeLessThan(900);
  const drag = async (dx: number, dy: number) => {
    await page.mouse.move(680, 430);
    await page.mouse.down();
    await page.mouse.move(680 + dx, 430 + dy, { steps: 3 });
    await page.mouse.up();
  };
  const levels = () => page.evaluate(() => window.__studioReview!.lightLevels());
  const toggleTwice = async (
    key: 'wallLamp' | 'floorLamp',
    label: string,
    point: { x: number; y: number },
  ) => {
    const other = key === 'wallLamp' ? 'floorLamp' : 'wallLamp';
    const before = await levels();
    expect(before[key]).toBeGreaterThan(0.5);
    await page.mouse.move(point.x, point.y);
    await expect(page.locator('.world-cue')).toContainText(label);
    await page.mouse.click(point.x, point.y);
    await expect.poll(async () => (await levels())[key]).toBeLessThan(0.01);
    expect((await levels())[other]).toBeCloseTo(before[other], 2);
    await page.mouse.click(point.x, point.y);
    await expect.poll(async () => (await levels())[key]).toBeCloseTo(before[key], 2);
  };
  await drag(0, -270);
  const optic = await page.evaluate(() =>
    window.__studioReview!.project('ERCO Parscan 48V · equipment')!,
  );
  await toggleTwice('wallLamp', 'track lights', optic);
  await drag(230, 340);
  const shade = await page.evaluate(() =>
    window.__studioReview!.bounds('Louis Poulsen AJ Floor · polished stainless steel · lining'),
  );
  await toggleTwice(
    'floorLamp',
    'floor lamp',
    await projectWorld(
      new Vector3().fromArray(shade.min).lerp(new Vector3().fromArray(shade.max), 0.5),
    ),
  );
  await drag(-230, 100);
  await page.mouse.wheel(0, -200);
  await expect.poll(async () => (await camera()).fov).toBeCloseTo(normal.fov - 6);
  const atRack = await camera();
  const pack = await page.evaluate(() => window.__studioReview!.project('talon-pack'));
  await page.mouse.click(pack!.x, pack!.y);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'gear');
  await expect.poll(camera).toEqual(atRack);
  await page.getByRole('button', { name: 'Back', exact: false }).click();
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await expect.poll(camera).toEqual(seated);
});

test('the travel board focuses the wall and its pins without opening the computer @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await start(page);
  const camera = () => page.evaluate(() => window.__studioReview!.camera());
  const before = await camera();
  const waitForWall = (id: string) =>
    expect
      .poll(
        () =>
          page.evaluate((id) => {
            const point = window.__studioReview!.project(id);
            return point
              ? Math.hypot(point.x - innerWidth / 2, point.y - innerHeight / 2)
              : Infinity;
          }, id),
        { timeout: 30_000 },
      )
      .toBeLessThan(70);
  const click = async (id: string) => {
    const point = await page.evaluate((id) => window.__studioReview!.project(id)!, id);
    await page.mouse.click(point.x, point.y);
  };
  await click('travel-map');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'map');
  await waitForWall('travel-map');
  await click('map-pin-beijing');
  await expect(page.locator('.interaction-caption')).toHaveText('Beijing');
  await click('map-pin-guizhou');
  await expect(page.locator('.interaction-caption')).toHaveText('Guizhou');
  await expect(page.locator('.screen-anchor')).toHaveAttribute('data-visible', 'false');
  await page.keyboard.press('Escape');
  await expect.poll(camera).toEqual(before);
  await page.evaluate(() => window.__studioReview!.activate('photo-board'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'board');
  await waitForWall('photo-board');
  await click('instant-flat-white');
  await expect(page.locator('.interaction-caption')).toHaveText('Flat white');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'board');
  await page.keyboard.press('Escape');
  await expect.poll(camera).toEqual(before);
});

test('the desk opens while the first forecast is pending @webgl', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    );
    const fetch = window.fetch.bind(window);
    window.fetch = (input, init) =>
      String(input).startsWith('https://api.open-meteo.com/v1/forecast?')
        ? new Promise<Response>(() => {})
        : fetch(input, init);
  });
  await page.goto('/?review=live-weather', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.keyboard-entry')).toBeEnabled({ timeout: 30000 });
  await page.keyboard.press('e');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'computer');
});

test('live weather keeps the previous sky until a city response settles @webgl', async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date('2026-11-20T15:00:00Z'));
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  let completeInitial!: () => void;
  const first = new Promise<void>((resolve) => {
    completeInitial = resolve;
  });
  let rejectNext!: () => void;
  const second = new Promise<void>((resolve) => {
    rejectNext = resolve;
  });
  await page.route('https://api.open-meteo.com/v1/forecast?**', async (route) => {
    if (new URL(route.request().url()).searchParams.get('timezone') === 'Asia/Shanghai') {
      await first;
      await route.fulfill({ json: { current: { weather_code: 0, is_day: 1 } } });
    } else {
      await second;
      await route.fulfill({ status: 503 });
    }
  });
  await page.goto('/?review=live-weather', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.studio-loading')).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('felix-studio-v1')!).night))
    .toBe(true);
  completeInitial();
  await expect(page.locator('.studio-loading')).toHaveCount(0, { timeout: 25000 });
  const weather = () =>
    page.evaluate(() => JSON.parse(localStorage.getItem('felix-studio-v1')!).weather);
  await expect.poll(weather).toBe('晴');
  await expect
    .poll(() =>
      page.evaluate(
        (ids) => {
          const lights = window.__studioReview!.lightLevels();
          return ids.every((id) => lights[id] === 0);
        },
        homeLights.map((light) => light.id),
      ),
    )
    .toBe(true);
  await page.evaluate(() => window.__studioReview!.activate('remote'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
  await page.evaluate(() => window.__studioReview!.activate('key-2'));
  await expect.poll(weather).toBe('晴');
  rejectNext();
  await expect.poll(weather).toBe('雨');
});

test('physical monitor keeps its aspect ratio and owns input while in use @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await start(page);
  const screen = page.locator('.screen-anchor[data-visible=true]');
  async function enterComputer() {
    await page.mouse.move(640, 400);
    await page.keyboard.press('e');
    await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'computer');
    await expect(screen).toHaveAttribute('data-interactive', 'true', { timeout: 20_000 });
  }
  await enterComputer();
  const bounds = (await screen.boundingBox())!;
  expect(bounds.width / bounds.height).toBeCloseTo(16 / 9, 2);
  expect(Math.max(bounds.width / 1280, bounds.height / 800)).toBeGreaterThan(0.86);
  const lock = page.getByRole('region', { name: 'Lock screen' });
  await expect(lock).toBeVisible();
  await expect(screen.locator('.aurora-canvas')).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Applications' })).toHaveCount(0);
  await expect(lock.getByRole('button', { name: 'Unlock' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(lock).toBeHidden();
  await page.getByRole('button', { name: 'About', exact: true }).click();
  const profileHeading = page.getByRole('heading', { name: /Taste Is All\s*You Need/ });
  await expect(profileHeading).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Beihang University' })).toBeInViewport();
  const panel = page.getByRole('region', { name: 'About window' });
  const beforeResize = (await panel.boundingBox())!;
  await page.mouse.move(
    beforeResize.x + beforeResize.width - 7,
    beforeResize.y + beforeResize.height - 7,
  );
  await page.mouse.down();
  await page.mouse.move(
    beforeResize.x + beforeResize.width + 29,
    beforeResize.y + beforeResize.height - 30,
    { steps: 7 },
  );
  await page.mouse.up();
  expect((await panel.boundingBox())!.width).toBeGreaterThan(beforeResize.width + 10);
  await page.getByRole('button', { name: 'Minimize About' }).click();
  await expect(profileHeading).toBeHidden();
  await page.getByRole('button', { name: 'About', exact: true }).click();
  await page.getByRole('button', { name: 'Maximize About' }).click();
  await expect(panel).toHaveClass(/is-maximized/);
  await page.getByRole('button', { name: 'System menu' }).click();
  await page.getByRole('button', { name: 'About Felix OS' }).click();
  const osAbout = screen.getByRole('dialog', { name: 'Felix OS' });
  await expect(osAbout).toBeVisible();
  await page.getByRole('button', { name: 'System menu' }).click();
  await expect(page.getByRole('button', { name: 'System Settings…' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(osAbout).toBeVisible();
  await osAbout.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(osAbout).toHaveCount(0);
  await expect(panel).toHaveClass(/is-maximized/);
  await page.getByRole('button', { name: 'System menu' }).click();
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'computer');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room', { timeout: 18_000 });
  await expect(profileHeading).toBeHidden();
  await enterComputer();
  await expect(panel).toHaveClass(/is-maximized/);
  await expect(profileHeading).toBeVisible();
  await page.getByRole('button', { name: 'Close About' }).click();
  await expect(panel).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room', { timeout: 18_000 });
  await enterComputer();
  await expect(profileHeading).toBeVisible();
});

test('deferred cookware occupies the rear wall before the next rendered frame @webgl', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const state = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const module = '/src/scene/display-model.ts';
    const T = (await import(three)) as typeof import('three');
    const { loadDisplayModel } = (await import(
      module
    )) as typeof import('../src/scene/display-model');
    const wall = new T.Group(),
      coffee = new T.Group();
    wall.rotation.y = Math.PI;
    wall.position.z = 3.17;
    wall.add(coffee);
    await loadDisplayModel(wall, '/media/models/camp-cookware.glb', new T.LoadingManager(), {
      mounted(model) {
        const pot = model.children.find((part) => part.userData.product === 'PR-880')!;
        coffee.position.copy(pot.position);
        pot.position.set(0, 0, 0);
        coffee.add(pot);
      },
    });
    const previous = new Map<import('three').Object3D, import('three').Matrix4>();
    wall.traverse((part) => {
      if ('isMesh' in part) previous.set(part, part.matrixWorld.clone());
    });
    wall.updateMatrixWorld(true);
    return {
      products: wall.children.map((product) => product.children.length),
      changed: [...previous]
        .filter(([part, before]) => !part.matrixWorld.equals(before))
        .map(([part]) => part.name),
      meshes: previous.size,
    };
  });
  expect(state.meshes).toBeGreaterThan(1);
  expect(state.products.every((count) => count > 0)).toBe(true);
  expect(state.changed).toEqual([]);
});

for (const side of ['Left', 'Right']) {
  test(`the ${side.toLowerCase()} speaker opens Music after the lock screen releases the desktop @webgl`, async ({
    page,
  }) => {
    const width = 1280,
      height = 800;
    await page.setViewportSize({ width, height });
    await page.addInitScript(() => {
      localStorage.setItem(
        'felix-studio-v1',
        JSON.stringify({ reducedMotion: true, automaticQuality: false, quality: 'low' }),
      );
    });
    await start(page);
    await page.evaluate(() => {
      const desktop = document.querySelector<HTMLElement>('.desktop')!;
      const observer = new MutationObserver(() => {
        const app = desktop.querySelector('.os-window');
        if (!app) return;
        desktop.dataset.firstWindow = app.getAttribute('aria-label') ?? '';
        desktop.dataset.lockAtFirstWindow = String(Boolean(desktop.querySelector('.lock-screen')));
        observer.disconnect();
      });
      observer.observe(desktop, { childList: true, subtree: true });
    });
    const cue = page.locator('.world-cue');
    const foreground = side === 'Left' ? 'desk-photo' : 'camera';
    await expect
      .poll(
        async () => {
          const item = await page.evaluate((id) => window.__studioReview!.project(id), foreground);
          await page.mouse.move(item!.x, item!.y);
          return cue.textContent();
        },
        { timeout: 20_000 },
      )
      .toContain(side === 'Left' ? 'Desk portrait' : 'Examine the Nikon Z 8');
    const { bounds, pose } = await page.evaluate(
      (side) => ({
        bounds: window.__studioReview!.bounds(side + ' speaker'),
        pose: window.__studioReview!.camera(),
      }),
      side,
    );
    const camera = new PerspectiveCamera(pose.fov, width / height);
    camera.position.fromArray(pose.position);
    camera.quaternion.fromArray(pose.rotation);
    camera.updateMatrixWorld();
    const center = (bounds.min[0] + bounds.max[0]) / 2;
    const top = new Vector3(
      center,
      bounds.max[1],
      (bounds.min[2] + bounds.max[2]) / 2 + 0.05,
    ).project(camera);
    await page.mouse.move(((1 + top.x) * width) / 2, ((1 - top.y) * height) / 2);
    await expect(cue).toContainText('Open Music');
    const speaker = new Vector3(center, bounds.min[1] + 0.16, bounds.max[2]).project(camera);
    const x = ((1 + speaker.x) * width) / 2,
      y = ((1 - speaker.y) * height) / 2;
    await page.mouse.move(x, y);
    await expect(cue).toContainText('Open Music');
    await page.mouse.click(x, y);
    const lock = page.getByRole('region', { name: 'Lock screen' });
    await expect(page.locator('.screen-anchor')).toHaveAttribute('data-interactive', 'true', {
      timeout: 20_000,
    });
    await expect(lock.getByRole('button', { name: 'Unlock' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(lock).toBeHidden();
    await expect(page.getByRole('region', { name: 'Music window' })).toBeVisible();
    await expect(page.locator('.desktop')).toHaveAttribute('data-first-window', 'Music window');
    await expect(page.locator('.desktop')).toHaveAttribute('data-lock-at-first-window', 'false');
  });
}

test('only the visible OLED screen opens the computer @webgl', async ({ page }) => {
  const width = 1280;
  const height = 800;
  await page.setViewportSize({ width, height });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, automaticQuality: false, quality: 'low' }),
    ),
  );
  await start(page);
  for (const zoom of [0, -420]) {
    if (zoom) await page.mouse.wheel(0, zoom);
    if (zoom)
      await expect
        .poll(() => page.evaluate(() => window.__studioReview!.camera().fov))
        .toBeLessThan(55);
    const pose = await page.evaluate(() => window.__studioReview!.camera());
    const camera = new PerspectiveCamera(pose.fov, width / height);
    camera.position.fromArray(pose.position);
    camera.quaternion.fromArray(pose.rotation);
    camera.updateMatrixWorld();
    for (const [x, y] of [
      [-0.98, 0],
      [0.98, 0],
      [0, 0.98],
      [0, -0.98],
      [-1.03, 0],
      [1.12, 0],
      [0.6, 1.05],
      [0.6, -1.14],
    ]) {
      const p = new Vector3(
        display.x + (x * display.width) / 2,
        display.y + (y * display.height) / 2,
        display.z + display.surface,
      ).project(camera);
      await page.mouse.move(((1 + p.x) * width) / 2, ((1 - p.y) * height) / 2);
      const cue = page.locator('.world-cue');
      if (Math.abs(x) < 1 && Math.abs(y) < 1) await expect(cue).toContainText('Open computer');
      else await expect(cue).not.toContainText('Open computer');
    }
  }
  await page.keyboard.press('e');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  const center = await page.evaluate(() => window.__studioReview!.project('computer'));
  await page.mouse.click(center!.x, center!.y);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'computer');
});

test('the picture light switches on its housing and the display cabinet stays lit @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({
        night: true,
        ceiling: 0.65,
        reducedMotion: true,
        automaticQuality: false,
        quality: 'low',
      }),
    ),
  );
  await start(page);
  const levels = () => page.evaluate(() => window.__studioReview!.lightLevels());
  await expect.poll(async () => (await levels()).pictureLamp).toBeGreaterThan(30);
  const original = await levels();
  await page.mouse.move(615, 660);
  await page.mouse.down();
  await page.mouse.move(615, 465, { steps: 12 });
  await page.mouse.up();
  const pose = await page.evaluate(() => window.__studioReview!.camera());
  const camera = new PerspectiveCamera(pose.fov, 1.6);
  camera.position.fromArray(pose.position);
  camera.quaternion.fromArray(pose.rotation);
  camera.updateMatrixWorld();
  const housing = new Vector3(-0.18, 2.275, -0.401).project(camera);
  const x = (1 + housing.x) * 640,
    y = (1 - housing.y) * 400;
  await page.mouse.move(x, y);
  await expect(page.locator('.world-cue')).toContainText('picture light');
  await page.mouse.click(x, y);
  await expect.poll(async () => (await levels()).pictureLamp).toBeLessThan(0.02);
  const off = await levels();
  expect(off.displayCabinet).toBe(original.displayCabinet);
  expect(off.wallLamp).toBeCloseTo(original.wallLamp, 2);
  await page.mouse.click(x, y);
  await expect.poll(async () => (await levels()).pictureLamp).toBeGreaterThan(30);
  await page.evaluate(() => window.__studioReview!.activate('remote'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
  await page.evaluate(() => window.__studioReview!.activate('key-5'));
  await expect.poll(async () => (await levels()).pictureLamp).toBeLessThan(0.02);
  expect((await levels()).displayCabinet).toBe(original.displayCabinet);
  expect(original.displayCabinet).toBeGreaterThan(0);
});

test('look limits, remote state, and drawer ownership survive transitions @webgl', async ({
  page,
}) => {
  const mediaRequests: string[] = [];
  page.on('request', (request) => {
    const name = new URL(request.url()).pathname.match(
      /\/models\/(samsung-t7|cfexpress-type-b)\.glb(?:\.gz)?$/,
    )?.[1];
    if (name) mediaRequests.push(name);
  });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await start(page);
  await page.mouse.move(640, 450);
  await page.mouse.wheel(0, -430);
  await page.waitForTimeout(200);
  const snapshot = await page.evaluate(() => window.__studioReview!.camera());
  expect(snapshot.position[2]).toBe(eye.defaultZ);
  await page.evaluate(() => window.__studioReview!.activate('remote'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
  await page.waitForTimeout(300);
  await page.evaluate(() => window.__studioReview!.activate('key-0'));
  await expect(page.getByText('Blinds raised', { exact: true })).toBeVisible();
  await page.evaluate(() => window.__studioReview!.activate('key-3'));
  await expect(page.getByText('Snow', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  const returned = await page.evaluate(() => window.__studioReview!.camera());
  expect(returned.position[2]).toBeCloseTo(snapshot.position[2], 2);
  const shut = (await page.evaluate(() => window.__studioReview!.drawer(0)))!;
  await page.evaluate(() => window.__studioReview!.activate('camera-card'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await page.evaluate(() => window.__studioReview!.activate('drawer-0'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'drawer');
  await expect
    .poll(() => page.evaluate(() => window.__studioReview!.drawer(0)))
    .toBeGreaterThan(shut + 0.25);
  const drawerEye = await page.evaluate(() => window.__studioReview!.camera());
  expect(drawerEye.position[2]).toBeLessThan(eye.defaultZ - 0.5);
  const downward = new Vector3(0, 0, -1).applyQuaternion(new Quaternion(...drawerEye.rotation));
  expect(downward.y).toBeLessThan(-0.6);
  await page.getByRole('button', { name: 'Close drawer' }).click();
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  expect(mediaRequests).toEqual([]);
  await page.evaluate(() => window.__studioReview!.activate('drawer-3'));
  await expect
    .poll(() => page.evaluate(() => window.__studioReview!.drawer(3)))
    .toBeGreaterThan(shut + 0.25);
  expect(await page.evaluate(() => window.__studioReview!.drawer(0))).toBeCloseTo(shut, 4);
  await expect
    .poll(async () => {
      const point = (await page.evaluate(() => window.__studioReview!.project('drive')))!;
      await page.mouse.move(point.x, point.y);
      return page.locator('.world-cue').textContent();
    })
    .toContain('Samsung T7');
  expect([...mediaRequests].sort()).toEqual(['cfexpress-type-b', 'samsung-t7']);
  const drive = (await page.evaluate(() => window.__studioReview!.project('drive')))!;
  await page.mouse.click(drive.x, drive.y);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'drawer');
  expect(await page.evaluate(() => window.__studioReview!.drawer(3))).toBeGreaterThan(shut + 0.25);
  await page.evaluate(() => window.__studioReview!.activate('camera-card'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'drawer');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await expect
    .poll(() => page.evaluate(() => window.__studioReview!.drawer(3)))
    .toBeCloseTo(shut, 4);
  await page.evaluate(() => window.__studioReview!.activate('drawer-3'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'drawer');
  expect([...mediaRequests].sort()).toEqual(['cfexpress-type-b', 'samsung-t7']);
});

test('a visible cabinet opens directly from the gear wall and returns the backpack to the bench @webgl', async ({
  page,
}) => {
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1500, height: 850 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ quality: 'low', reducedMotion: true }),
    ),
  );
  await start(page);
  const room = page.locator('.studio');
  const camera = () => page.evaluate(() => window.__studioReview!.camera());
  const packPose = () => page.evaluate(() => window.__studioReview!.objectPose('talon-pack'));
  const atPose = (expected: Awaited<ReturnType<typeof camera>>) =>
    expect
      .poll(async () => {
        const actual = await camera();
        return Math.max(
          new Vector3(...expected.position).distanceTo(new Vector3(...actual.position)),
          new Quaternion(...expected.rotation).angleTo(new Quaternion(...actual.rotation)),
          Math.abs(expected.fov - actual.fov),
        );
      })
      .toBeLessThan(0.00001);
  const click = async (id: string) => {
    const { x, y } = await page.evaluate((id) => window.__studioReview!.project(id)!, id);
    expect(x).toBeGreaterThan(0);
    expect(x).toBeLessThan(1500);
    expect(y).toBeGreaterThan(0);
    expect(y).toBeLessThan(850);
    await page.mouse.click(x, y);
  };
  await expect.poll(async () => (await camera()).fov).toBe(roomFov);
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  const seated = await camera();
  await page.mouse.move(170, 90);
  await page.mouse.down();
  await page.mouse.move(275, 123, { steps: 5 });
  await page.mouse.up();
  await page.mouse.wheel(0, -150);
  await expect.poll(async () => (await camera()).fov).toBeLessThan(seated.fov);
  const roaming = await camera();
  const facingFromRoom = async (id: string) => {
    const bounds = await page.evaluate((id) => {
      const review = window.__studioReview!;
      return review.bounds(review.inventory().find((item) => item.id === id)!.name);
    }, id);
    const middle = new Vector3(...bounds.min).lerp(new Vector3(...bounds.max), 0.5);
    await expect
      .poll(async () => {
        const pose = await camera();
        const position = new Vector3(...pose.position);
        const direction = new Vector3(0, 0, -1).applyQuaternion(new Quaternion(...pose.rotation));
        return Math.max(
          position.distanceTo(new Vector3(...roaming.position)),
          Math.abs(pose.fov - roaming.fov),
          direction.angleTo(middle.clone().sub(position)),
        );
      })
      .toBeLessThan(0.22);
    await page.evaluate(
      () =>
        new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        ),
    );
  };
  await page.evaluate(() => window.__studioReview!.activate('equipment-wall'));
  await expect(room).toHaveAttribute('data-mode', 'gear');
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await atPose(roaming);
  await page.evaluate(() => window.__studioReview!.activate('equipment-wall'));
  await page.waitForFunction(
    () =>
      (window.__studioReview!.objectPose('NIKKOR Z 135mm f/1.8 S Plena · cabinet mount')
        ?.position[1] ?? 0) > 0.5,
  );
  const facingWall = new Quaternion().setFromEuler(new Euler(gearEye.pitch, gearEye.yaw, 0, 'YXZ'));
  await expect
    .poll(async () => {
      const pose = await camera();
      return Math.max(
        Math.abs(pose.fov - gearEye.fov),
        new Quaternion(...pose.rotation).angleTo(facingWall),
      );
    })
    .toBeLessThan(0.00001);
  const gear = await camera();
  const home = await packPose();
  await click('NIKKOR Z 135mm f/1.8 S Plena · cabinet mount');
  await expect(room).toHaveAttribute('data-mode', 'case');
  await expect.poll(camera).not.toEqual(gear);
  const cabinet = await camera();
  const caption = page.locator('.object-caption');
  const centeredCaption = async () => {
    const box = await caption.boundingBox();
    const viewport = page.viewportSize()!;
    expect(box).not.toBeNull();
    expect(Math.abs(box!.x + box!.width / 2 - viewport.width / 2)).toBeLessThan(1);
    expect(Math.abs(box!.y + box!.height / 2 - viewport.height * 0.87)).toBeLessThan(1);
  };
  await expect(caption).toContainText('Explore the collection cabinet');
  await centeredCaption();
  await click('NIKKOR Z 135mm f/1.8 S Plena · cabinet mount');
  await expect(room).toHaveAttribute('data-mode', 'case');
  await atPose(cabinet);
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await facingFromRoom('collection-cabinet');
  const cabinetRoam = await camera();
  await page.evaluate(() => window.__studioReview!.activate('equipment-wall'));
  await atPose(gear);
  await click('talon-pack');
  await expect(room).toHaveAttribute('data-mode', 'inspect');
  await expect.poll(packPose).not.toEqual(home);
  await click('talon-pack');
  await expect(room).toHaveAttribute('data-mode', 'inspect');
  await click('NIKKOR Z 135mm f/1.8 S Plena · cabinet mount');
  await expect(room).toHaveAttribute('data-mode', 'case');
  await expect.poll(packPose).toEqual(home);
  await atPose(cabinet);
  await page.mouse.move(680, 450);
  await page.mouse.down();
  await page.mouse.move(730, 463, { steps: 3 });
  await page.mouse.up();
  await page.mouse.wheel(0, -180);
  await expect.poll(camera).not.toEqual(cabinet);
  await expect(caption).toContainText('Explore the collection cabinet');
  await centeredCaption();
  await page.setViewportSize({ width: 980, height: 640 });
  await centeredCaption();
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await facingFromRoom('collection-cabinet');
  await atPose(cabinetRoam);
  await page.evaluate(() => window.__studioReview!.activate('workbench'));
  await expect(room).toHaveAttribute('data-mode', 'bench');
  await page.evaluate(() => window.__studioReview!.activate('filament-printer'));
  await expect(room).toHaveAttribute('data-mode', 'case');
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await facingFromRoom('filament-printer');
});

test('each of the five display lenses stays on its shelf when clicked @webgl', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await start(page);
  const camera = () => page.evaluate(() => window.__studioReview!.camera());
  const room = page.locator('.studio');
  await page.mouse.move(180, 400);
  await page.mouse.down();
  await page.mouse.move(1070, 400, { steps: 18 });
  await page.mouse.up();
  await expect
    .poll(async () => new Quaternion(...(await camera()).rotation).angleTo(new Quaternion()))
    .toBeGreaterThan(2.9);
  const seated = await camera();
  await expect
    .poll(
      () =>
        page.evaluate(
          () =>
            window.__studioReview!.objectPose('NIKKOR Z 100–400mm f/4.5–5.6 VR S · cabinet mount')!
              .position[1],
        ),
      { timeout: 20_000 },
    )
    .toBeGreaterThan(0.97);
  const glass = await page.evaluate(() =>
    window.__studioReview!.project('NIKKOR Z 100–400mm f/4.5–5.6 VR S · cabinet mount')!,
  );
  await page.mouse.click(glass.x, glass.y);
  await expect(room).toHaveAttribute('data-mode', 'case', { timeout: 20_000 });
  await page.mouse.move(515, 475);
  await page.mouse.down();
  await page.mouse.move(545, 487, { steps: 3 });
  await page.mouse.up();
  await page.mouse.wheel(0, -100);
  await expect.poll(async () => (await camera()).rotation).not.toEqual(seated.rotation);
  await page.waitForFunction(() => new Promise(requestAnimationFrame));
  const display = await camera();
  for (const model of [
    '14–24mm f/2.8 S',
    '100–400mm f/4.5–5.6 VR S',
    '70–200mm f/2.8 VR S II',
    '135mm f/1.8 S Plena',
    '58mm f/0.95 S Noct',
  ]) {
    const key = 'NIKKOR Z ' + model + ' · cabinet mount';
    const home = await page.evaluate((key) => window.__studioReview!.objectPose(key), key);
    const center = await page.evaluate((key) => window.__studioReview!.project(key)!, key);
    await page.mouse.click(center.x, center.y);
    await page.keyboard.press('KeyE');
    await expect(room).toHaveAttribute('data-mode', 'case');
    expect(await camera()).toEqual(display);
    expect(await page.evaluate((key) => window.__studioReview!.objectPose(key), key)).toEqual(home);
  }
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  await expect.poll(camera).toEqual(seated);
});

test('case inspection changes the camera while the case stays anchored @webgl', async ({
  page,
}) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await start(page);
  const read = () =>
    page.evaluate(() => ({
      camera: window.__studioReview!.camera(),
      hardware: window.__studioReview!.objectPose('case'),
    }));
  const seated = await read();
  const point = await page.evaluate(() => window.__studioReview!.project('case'));
  expect(point).not.toBeNull();
  await page.mouse.click(point!.x, point!.y);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'case');
  await expect(page.getByText('Look closer at the PC case', { exact: true })).toBeVisible();
  await expect
    .poll(async () => (await read()).camera.position[2], { timeout: 12_000 })
    .toBeLessThan(seated.camera.position[2] - 0.5);
  const close = await read();
  expect(close.hardware).toEqual(seated.hardware);
  await page.mouse.move(640, 440);
  await page.mouse.down();
  await page.mouse.move(770, 407);
  await page.mouse.up();
  const ray = (camera: typeof close.camera) =>
    new Vector3(0, 0, -1).applyQuaternion(new Quaternion(...camera.rotation));
  const forward = ray(close.camera);
  const pivot = new Vector3(...close.camera.position).addScaledVector(forward, 1.03);
  await expect.poll(async () => forward.angleTo(ray((await read()).camera))).toBeGreaterThan(0.25);
  const around = await read();
  const offset = pivot.clone().sub(new Vector3(...around.camera.position));
  expect(offset.length()).toBeCloseTo(1.03, 4);
  expect(offset.angleTo(ray(around.camera))).toBeLessThan(0.001);
  expect(around.hardware).toEqual(seated.hardware);
  const dragAcross = async (from: number, to: number) => {
    await page.mouse.move(from, 430);
    await page.mouse.down();
    await page.mouse.move(to, 430);
    await page.mouse.up();
  };
  await dragAcross(1170, 105);
  await expect.poll(async () => ray((await read()).camera).x).toBeLessThan(-0.97);
  for (const wheel of [0, 1600, -2400]) {
    await page.mouse.wheel(0, wheel);
    await page.evaluate(() => new Promise(requestAnimationFrame));
    const { hardware, camera } = await read();
    expect(camera.position[0]).toBeGreaterThan(pivot.x + 0.29);
    expect(camera.position[0]).toBeLessThan(1.83);
    expect(camera.position[2]).toBeGreaterThan(-0.16);
    expect(hardware).toEqual(seated.hardware);
  }
  await dragAcross(300, 824);
  await expect.poll(async () => Math.abs(ray((await read()).camera).x)).toBeLessThan(0.01);
  expect((await read()).camera.position[2] - pivot.z).toBeGreaterThanOrEqual(0.389);
  await page.mouse.dblclick(640, 430);
  await expect.poll(read).toEqual(close);
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await expect.poll(read, { timeout: 12_000 }).toEqual(seated);
});

test('the loader advances before the room arrives and completes after it is ready', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1100, height: 780 });
  await page.addInitScript(() =>
    localStorage.setItem('felix-studio-v1', JSON.stringify({ locale: 'zh' })),
  );
  let releaseRoom!: () => void;
  const holdRoom = new Promise<void>((resolve) => {
    releaseRoom = resolve;
  });
  await page.route(/\/src\/scene\/StudioView\.tsx(?:\?|$)/, async (route) => {
    await holdRoom;
    await route.fulfill({
      contentType: 'text/javascript',
      body: 'export default function StudioView({ onReady }) { setTimeout(onReady, 0); return null; }',
    });
  });
  try {
    await page.goto('/?review=loader', { waitUntil: 'domcontentloaded' });
    const meter = page.getByRole('progressbar', { name: 'Room loading progress' });
    const read = () => meter.evaluate((node: HTMLProgressElement) => node.value);
    const waitForProgress = (minimum: number, timeout: number) =>
      page.waitForFunction(
        (threshold) =>
          (document.querySelector<HTMLProgressElement>('.phosphor-track progress')?.value ?? 0) >=
          threshold,
        minimum,
        { timeout },
      );
    await expect(meter).toBeAttached();
    await expect(page.locator('html')).toHaveAttribute('lang', 'zh-Hans');
    await expect(page.getByRole('region', { name: 'FELIX.PY' })).toHaveAttribute('lang', 'en');
    await expect(page.getByText('Taste Is All You Need', { exact: true })).toBeVisible();
    await waitForProgress(0.25, 1250);
    const indicator = await meter.evaluate((node: HTMLProgressElement) => {
      const cursor = node.parentElement!.querySelector('.phosphor-cursor')!;
      const fill = node.parentElement!.querySelector('.phosphor-fill')!;
      const width = cursor.getBoundingClientRect().width;
      const offset = new DOMMatrixReadOnly(getComputedStyle(cursor).transform).m41;
      const inset = getComputedStyle(fill).clipPath.match(/inset\(0px ([\d.]+)%/);
      return {
        position: offset / width,
        fill: inset ? 1 - Number(inset[1]) / 100 : NaN,
        percent: node.closest('.phosphor-progress')!.querySelector('.phosphor-percent')!
          .textContent,
        progress: node.value,
      };
    });
    expect(indicator.percent).toBe(`${Math.floor(indicator.progress * 100)}%`);
    expect(indicator.position).toBeCloseTo(indicator.progress);
    expect(indicator.fill).toBeCloseTo(indicator.progress);
    await expect(page.locator('.phosphor-percent')).toHaveCSS('font-family', /IBM Plex Mono/);
    expect(
      await page.evaluate(
        async () => (await document.fonts.load('500 16px "IBM Plex Mono"', '34%')).length,
      ),
    ).toBeGreaterThan(0);
    await waitForProgress(0.9, 2500);
    expect(await read()).toBeLessThan(1);
    releaseRoom();
    await expect(meter).toHaveCount(0);
    await expect(page.locator('.keyboard-entry')).toBeEnabled();
  } finally {
    releaseRoom();
  }
});

test('mobile opens the public profile directly and computes experience from July 2014', async ({
  page,
}) => {
  await page.addInitScript(() => {
    HTMLCanvasElement.prototype.getContext = new Proxy(HTMLCanvasElement.prototype.getContext, {
      apply(getContext, canvas, args) {
        if (args[0] === 'webgl2') {
          document.documentElement.dataset.studioGraphicsProbed = 'true';
          return null;
        }
        return Reflect.apply(getContext, canvas, args);
      },
    });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.clock.setFixedTime(new Date('2027-06-20T12:00:00Z'));
  await page.goto('/');
  await expect(page.locator('.mobile-home')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { name: /Taste Is All\s*You Need/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Beihang University' })).toBeVisible();
  await expect(page.getByText('12 years', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: /GitHub/ })).toHaveAttribute(
    'href',
    'https://github.com/felixpy/felixpy.com',
  );
  await expect(page.locator('.desktop, .studio-canvas, .fps-meter')).toHaveCount(0);
  await page.clock.setFixedTime(new Date('2027-07-02T12:00:00Z'));
  await page.reload();
  await expect(page.getByText('13 years', { exact: true })).toBeVisible();
  await expect(page.locator('html')).not.toHaveAttribute('data-studio-graphics-probed', 'true');
  await page.setViewportSize({ width: 1100, height: 780 });
  await expect(page.locator('.compact-studio')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-studio-graphics-probed', 'true');
});

test('the music collection shares playback state and the computer keeps portrait game controls', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1100, height: 780 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      value: function (this: HTMLCanvasElement, type: string, options?: unknown) {
        return type === 'webgl2' ? null : Reflect.apply(getContext, this, [type, options]);
      },
    });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Unlock' }).click();
  await expect(page.locator('.os-window-about')).toBeVisible();
  await expect(
    page.locator('.menu-bar').getByRole('button', { name: 'Window', exact: true }),
  ).toHaveCount(0);
  const language = page.getByRole('button', { name: 'Switch to Chinese' });
  await language.hover();
  await expect(
    page.locator('.menu-bar .tooltip-label').filter({ hasText: 'Switch to Chinese' }),
  ).toBeVisible();
  await expect(page.locator('.desktop [title]')).toHaveCount(0);
  await page.getByRole('button', { name: 'Minimize About' }).click();
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await expect(page.locator('.os-window-about')).toHaveCount(0);
  await expect(page.locator('.os-window')).toHaveCount(1);
  const quality = page.getByRole('button', { name: /^Render quality/ });
  await quality.click();
  const qualities = page.getByRole('listbox', { name: 'Render quality' });
  await expect(qualities.getByRole('option', { name: 'Automatic', selected: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(qualities).toHaveCount(0);
  await quality.press('ArrowDown');
  await page.keyboard.press('End');
  await page.keyboard.press('Enter');
  await expect(quality).toHaveAccessibleName('Render quality Low power');
  await quality.click();
  await qualities.getByRole('option', { name: 'High' }).click();
  await expect(quality).toHaveAccessibleName('Render quality High');
  const systemMenu = page.getByRole('button', { name: 'System menu' });
  await systemMenu.click();
  await page.getByRole('button', { name: 'About Felix OS' }).click();
  const osAbout = page.getByRole('dialog', { name: 'Felix OS' });
  await expect(osAbout).toHaveAccessibleDescription('26.11');
  await expect(osAbout.getByRole('button', { name: 'Close', exact: true })).toBeFocused();
  await expect(page.locator('.os-window-about')).toHaveCount(0);
  await expect(page.locator('.os-window-settings')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(osAbout).toHaveCount(0);
  await expect(systemMenu).toBeFocused();
  await expect(quality).toBeVisible();
  await systemMenu.click();
  await page.getByRole('button', { name: 'About Felix OS' }).click();
  await page.getByRole('button', { name: 'About', exact: true }).click();
  await expect(osAbout).toHaveCount(0);
  await expect(page.locator('.os-window-about')).toBeVisible();
  await systemMenu.click();
  await page.getByRole('button', { name: 'About Felix OS' }).click();
  await systemMenu.click();
  await page.getByRole('button', { name: 'System Settings…' }).click();
  await expect(osAbout).toHaveCount(0);
  await expect(quality).toBeVisible();
  await page.getByRole('button', { name: '简体中文', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-Hans');
  await page.getByRole('button', { name: '关于', exact: true }).click();
  await expect(page.locator('.os-window-settings')).toHaveCount(0);
  await expect(page.getByText('北京航空航天大学', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-Hans');
  await page.getByRole('button', { name: '解锁' }).click();
  await page.getByRole('button', { name: '音乐', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Moonlit Skyline' })).toBeVisible();
  await expect(page.locator('.spectral-artist')).toHaveText('Nihilore');
  await expect(page.getByRole('button', { name: '暂停', exact: true })).toBeVisible();
  await expect(page.getByRole('slider', { name: '音量' })).toHaveValue('0.5');
  await page.getByRole('button', { name: '播放列表', exact: true }).click();
  await expect(page.getByRole('list', { name: '曲目' }).getByRole('button')).toHaveCount(5);
  const trackMarker = page.locator('.spectral-track-row[aria-current] > span:first-child svg');
  const numberColumn = page.locator('.spectral-track-heading > span:first-child');
  await expect(trackMarker).toBeVisible();
  expect((await trackMarker.boundingBox())!.x).toBeCloseTo((await numberColumn.boundingBox())!.x);
  const repeat = page.getByRole('button', { name: '单曲循环' });
  await repeat.click();
  await expect(repeat).toHaveAttribute('aria-pressed', 'true');
  await repeat.click();
  await expect(repeat).toHaveAttribute('aria-pressed', 'false');
  const search = page.getByRole('searchbox', { name: '搜索曲目' });
  await search.fill('Murky');
  await expect(page.getByRole('button', { name: /Moonlit Skyline/ })).toHaveCount(0);
  await page.getByRole('button', { name: '定位当前曲目' }).click();
  await expect(search).toHaveValue('');
  await expect(trackMarker).toBeVisible();
  await search.fill('Murky');
  await expect(page.getByRole('button', { name: /Moonlit Skyline/ })).toHaveCount(0);
  await page.getByRole('button', { name: /The Murky Deep/ }).click();
  await expect(page.locator('.spectral-mini')).toContainText('The Murky Deep');
  await expect(page.locator('.spectral-mini')).toContainText('Nihilore');
  await page.getByRole('button', { name: '播放器', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'The Murky Deep' })).toBeVisible();
  await expect(page.getByRole('button', { name: '暂停', exact: true })).toBeVisible();
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect(page.getByRole('button', { name: '播放', exact: true })).toBeVisible();
  await page.evaluate(() => {
    Reflect.deleteProperty(document, 'hidden');
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect(page.getByRole('button', { name: '暂停', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '近地航线', exact: true }).click();
  await expect(page.locator('.os-window-music')).toHaveCount(0);
  await page.getByRole('button', { name: '开始', exact: true }).click();
  const playfield = page.getByLabel('近地航线游戏画面');
  await expect(playfield).toBeVisible();
  await expect(page.getByLabel('得分', { exact: true })).toHaveText('000000');
  const area = (await playfield.boundingBox())!;
  expect(area.width / area.height).toBeCloseTo(192 / 304, 2);
  await expect(page.locator('.flight-console')).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(page.getByText('已暂停', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '继续', exact: true }).click();
  await expect(page.getByRole('button', { name: '暂停', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '音乐', exact: true }).click();
  await expect(page.locator('.os-window-game')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'The Murky Deep' })).toBeVisible();
  await expect(page.getByRole('button', { name: '暂停', exact: true })).toBeVisible();
});

test('the waterfront continues to move in 3D while the view is still @webgl', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem('felix-studio-v1', JSON.stringify({ quality: 'low' })),
  );
  await start(page);
  const canvas = page.locator('canvas').first();
  await page.mouse.move(1020, 430);
  await page.mouse.down();
  await page.mouse.move(779, 430, { steps: 10 });
  await page.mouse.up();
  await expect
    .poll(async () => {
      const snapshot = await page.evaluate(() => window.__studioReview!.camera());
      return new Quaternion(...snapshot.rotation).angleTo(new Quaternion());
    })
    .toBeGreaterThan(0.79);
  await page.mouse.wheel(0, -100);
  await expect
    .poll(() => page.evaluate(() => window.__studioReview!.camera().fov), { timeout: 12_000 })
    .toBe(60);
  const snapshot = await page.evaluate(() => window.__studioReview!.camera());
  const camera = new PerspectiveCamera(snapshot.fov, 1280 / 800);
  camera.position.fromArray(snapshot.position);
  camera.quaternion.fromArray(snapshot.rotation);
  camera.updateMatrixWorld(true);
  const click = new Vector3(windowOpening.wall - 0.166, 1.42, 0.85).project(camera);
  await page.mouse.move((click.x + 1) * 640, (1 - click.y) * 400);
  await expect(
    page.locator('.world-cue').getByText('Look out the window', { exact: true }),
  ).toBeVisible();
  const [walk] = await Promise.all([
    page.evaluate((destinationX) => {
      const first = window.__studioReview!.camera();
      const frames = [first];
      return new Promise<typeof frames>((resolve, reject) => {
        const timeout = window.setTimeout(() => reject(new Error('Window walk timed out')), 12000);
        function sample() {
          const frame = window.__studioReview!.camera();
          frames.push(frame);
          if (Math.abs(frame.position[0] - destinationX) < 0.001) {
            clearTimeout(timeout);
            resolve(frames);
          } else {
            requestAnimationFrame(sample);
          }
        }
        requestAnimationFrame(sample);
      });
    }, windowEye.x),
    page.mouse.click((click.x + 1) * 640, (1 - click.y) * 400),
  ]);
  for (const frame of walk) {
    expect(frame.fov).toBeCloseTo(snapshot.fov, 4);
    const right = new Vector3(1, 0, 0).applyQuaternion(new Quaternion(...frame.rotation));
    expect(Math.abs(right.y)).toBeLessThan(0.0001);
    const fraction = (frame.position[0] - eye.x) / (windowEye.x - eye.x);
    expect(frame.position[2]).toBeCloseTo(
      eye.defaultZ + (windowEye.z - eye.defaultZ) * fraction,
      4,
    );
    expect(frame.position[1]).toBeCloseTo(eye.y + (windowEye.y - eye.y) * fraction, 4);
  }
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'window');
  await expect(canvas).toBeVisible();
  await expect
    .poll(
      async () => {
        const camera = await page.evaluate(() => window.__studioReview!.camera());
        return Math.abs(camera.position[2] - windowEye.z);
      },
      { timeout: 12_000 },
    )
    .toBeLessThan(0.025);
  const initial = await page.evaluate(() => window.__studioReview!.project('Passing river ferry'));
  expect(initial).not.toBeNull();
  await expect
    .poll(
      async () => {
        const now = await page.evaluate(() =>
          window.__studioReview!.project('Passing river ferry'),
        );
        return Math.abs((now?.x ?? 0) - initial!.x);
      },
      { timeout: 10_000 },
    )
    .toBeGreaterThan(7);
  const before = await page.evaluate(() => window.__studioReview!.camera());
  await page.mouse.move(410, 415);
  await page.mouse.down();
  await page.mouse.move(200, 390, { steps: 8 });
  await page.mouse.up();
  await expect
    .poll(
      async () => {
        const now = await page.evaluate(() => window.__studioReview!.camera());
        return new Quaternion(...before.rotation).angleTo(new Quaternion(...now.rotation));
      },
      { timeout: 12_000 },
    )
    .toBeGreaterThan(0.25);
  const turned = await page.evaluate(() => window.__studioReview!.camera());
  expect(Math.abs(turned.position[2] - before.position[2])).toBeLessThan(0.045);
  await page.evaluate(() => window.__studioReview!.activate('remote'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'window');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  const returned = await page.evaluate(() => window.__studioReview!.camera());
  expect(returned.fov).toBeCloseTo(snapshot.fov, 4);
  expect(
    new Vector3(...returned.position).distanceTo(new Vector3(...snapshot.position)),
  ).toBeLessThan(0.001);
});
