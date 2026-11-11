import { expect, test, type Page } from '@playwright/test';
import {
  DoubleSide,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  Quaternion,
  Raycaster,
  Vector3,
} from 'three';
import { benchEye, eye, windowEye } from '../src/scene/camera';
import { panoramaGeometry } from '../src/scene/exterior';
import { display } from '../src/scene/hardware';
import { windowOpening } from '../src/scene/window';
import { advance, newFlight } from '../src/desktop/apps/arcade/flight';
import { initialEnvironment, pressRemote } from '../src/app/environment';

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

test('the OLED has a 31-inch diagonal at scene scale', () => {
  expect(Math.hypot(display.width, display.height) / 0.0254).toBeCloseTo(31, 6);
  expect(display.width / display.height).toBeCloseTo(16 / 9, 6);
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
  await page.goto('/?review');
  await page.waitForFunction(() => Boolean(window.__studioReview));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await expect(page.locator('.studio-loading')).toHaveCount(0, { timeout: 20_000 });
}

test('the room starts music on the first drag and turns without leaving the seat @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    );
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = async function () {
      if (!this.src.includes('/media/audio/music/')) return play.call(this);
      if (!navigator.userActivation.hasBeenActive) {
        document.documentElement.dataset.roomMusic = 'blocked';
        throw new DOMException('Audio requires a gesture', 'NotAllowedError');
      }
      await play.call(this);
      document.documentElement.dataset.roomMusic = 'playing';
    };
  });
  await start(page);
  await expect(page.locator('html')).toHaveAttribute('data-room-music', 'blocked');
  const initial = await page.evaluate(() => window.__studioReview!.camera());
  await page.mouse.move(220, 395);
  await page.mouse.down();
  await page.mouse.move(440, 395, { steps: 10 });
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
      mat: pose('Desk mat'),
      keyboard: pose('keyboard'),
      chair: pose('Desk task chair'),
    };
  });
  expect(layout.left.position[2]).toBe(layout.right.position[2]);
  expect((layout.left.position[0] + layout.right.position[0]) / 2).toBeCloseTo(display.x, 6);
  for (const item of [layout.mat, layout.keyboard, layout.chair])
    expect(item.position[0]).toBe(display.x);
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
  const desk = await camera();
  await clickObject('Workbench top');
  await expect(room).toHaveAttribute('data-mode', 'bench');
  await expect
    .poll(async () => (await camera()).position)
    .toEqual([benchEye.x, benchEye.y, benchEye.z]);
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
  const click = async (id: string) => {
    const point = await page.evaluate((id) => window.__studioReview!.project(id)!, id);
    await page.mouse.click(point.x, point.y);
  };
  await click('travel-map');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'map');
  await expect
    .poll(async () => (await camera()).position[1])
    .toBeGreaterThan(before.position[1] + 0.45);
  await click('map-pin-beijing');
  await expect(page.locator('.interaction-caption')).toHaveText('Beijing');
  await click('map-pin-guizhou');
  await expect(page.locator('.interaction-caption')).toHaveText('Guizhou');
  await expect(page.locator('.screen-anchor')).toHaveAttribute('data-visible', 'false');
  await page.keyboard.press('Escape');
  await expect.poll(camera).toEqual(before);
});

test('live weather keeps the previous sky until a city response settles @webgl', async ({
  page,
}) => {
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
  completeInitial();
  await expect(page.locator('.studio-loading')).toHaveCount(0, { timeout: 25000 });
  const weather = () =>
    page.evaluate(() => JSON.parse(localStorage.getItem('felix-studio-v1')!).weather);
  await expect.poll(weather).toBe('晴');
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
  await page.keyboard.press('e');
  const screen = page.locator('.screen-anchor[data-visible=true]');
  await expect(screen).toHaveAttribute('data-interactive', 'true', { timeout: 20_000 });
  const bounds = (await screen.boundingBox())!;
  expect(bounds.width / bounds.height).toBeCloseTo(16 / 9, 2);
  expect(Math.max(bounds.width / 1280, bounds.height / 800)).toBeGreaterThan(0.86);
  const lock = page.getByRole('region', { name: 'Lock screen' });
  await expect(lock).toBeVisible();
  await expect(screen.locator('.aurora-canvas')).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Applications' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Unlock' }).press('Enter');
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
  await page.keyboard.press('e');
  await expect(panel).toHaveClass(/is-maximized/);
  await expect(profileHeading).toBeVisible();
  await page.getByRole('button', { name: 'Close About' }).click();
  await expect(panel).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await page.keyboard.press('e');
  await expect(profileHeading).toBeVisible();
});

test('look limits, remote state, and drawer ownership survive transitions @webgl', async ({
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
  await page.mouse.move(640, 450);
  await page.mouse.wheel(0, -430);
  await page.waitForTimeout(200);
  const snapshot = await page.evaluate(() => window.__studioReview!.camera());
  expect(snapshot.position[2]).toBe(eye.defaultZ);
  await page.evaluate(() => window.__studioReview!.activate('remote'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
  await page.waitForTimeout(300);
  await page.evaluate(() => window.__studioReview!.activate('key-0'));
  await expect(page.getByText('Blinds lowered', { exact: true })).toBeVisible();
  await page.evaluate(() => window.__studioReview!.activate('key-3'));
  await expect(page.getByText('Snow', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  const returned = await page.evaluate(() => window.__studioReview!.camera());
  expect(returned.position[2]).toBeCloseTo(snapshot.position[2], 2);
  const shut = (await page.evaluate(() => window.__studioReview!.drawer(0)))!;
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
  await page.evaluate(() => window.__studioReview!.activate('drawer-3'));
  await expect
    .poll(() => page.evaluate(() => window.__studioReview!.drawer(3)))
    .toBeGreaterThan(shut + 0.25);
  expect(await page.evaluate(() => window.__studioReview!.drawer(0))).toBeCloseTo(shut, 4);
  await page.evaluate(() => window.__studioReview!.activate('drive'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'drawer');
  expect(await page.evaluate(() => window.__studioReview!.drawer(3))).toBeGreaterThan(shut + 0.25);
  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await expect
    .poll(() => page.evaluate(() => window.__studioReview!.drawer(3)))
    .toBeCloseTo(shut, 4);
});

test('case inspection changes the camera while the case stays anchored @webgl', async ({
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
  await page.mouse.move(770, 407, { steps: 5 });
  await page.mouse.up();
  await expect
    .poll(async () => (await read()).camera.position[0])
    .toBeLessThan(close.camera.position[0] - 0.15);
  expect((await read()).hardware).toEqual(seated.hardware);
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
    await expect(meter).toBeAttached();
    await expect(page.locator('html')).toHaveAttribute('lang', 'zh-Hans');
    await expect(page.getByRole('region', { name: 'FELIX.PY' })).toHaveAttribute('lang', 'en');
    await expect(page.getByText('Taste Is All You Need', { exact: true })).toBeVisible();
    await expect.poll(read, { timeout: 1250 }).toBeGreaterThan(0.25);
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
    await expect.poll(read, { timeout: 2500 }).toBeGreaterThanOrEqual(0.9);
    expect(await read()).toBeLessThan(1);
    releaseRoom();
    await expect.poll(read, { timeout: 3000 }).toBeGreaterThan(0.97);
    await expect(meter).toHaveCount(0);
  } finally {
    releaseRoom();
  }
});

test('mobile opens the public profile directly and computes experience from July 2014', async ({
  page,
}) => {
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
  await expect(qualities.getByRole('option', { name: 'High', selected: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(qualities).toHaveCount(0);
  await quality.press('ArrowDown');
  await page.keyboard.press('ArrowDown');
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
  await expect(page.getByRole('heading', { name: 'Galactic Rap' })).toBeVisible();
  await expect(page.getByRole('button', { name: '暂停', exact: true })).toBeVisible();
  await expect(page.getByRole('slider', { name: '音量' })).toHaveValue('0.5');
  await page.getByRole('button', { name: '播放列表', exact: true }).click();
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
  await search.fill('Space');
  await expect(page.getByRole('button', { name: /Galactic Rap/ })).toHaveCount(0);
  await page.getByRole('button', { name: '定位当前曲目' }).click();
  await expect(search).toHaveValue('');
  await expect(trackMarker).toBeVisible();
  await search.fill('Space');
  await expect(page.getByRole('button', { name: /Galactic Rap/ })).toHaveCount(0);
  await page.getByRole('button', { name: /Space Jazz/ }).click();
  await expect(page.locator('.spectral-mini')).toContainText('Space Jazz');
  await page.getByRole('button', { name: '播放器', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Space Jazz' })).toBeVisible();
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
  await expect(page.getByRole('heading', { name: 'Space Jazz' })).toBeVisible();
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
  await page.mouse.click((click.x + 1) * 640, (1 - click.y) * 400);
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
});
