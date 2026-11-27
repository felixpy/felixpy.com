import { expect, test, type Page } from '@playwright/test';
import type { InstancedMesh, Material, Mesh, Scene, Vector3 } from 'three';

type SwitchState = {
  visible: boolean;
  parts: { id: string; count: number; material: string; roomLighting: boolean; clear: boolean }[];
};

type LayerOffsets = Record<string, { dy: number; dz: number }>;

async function openExplodedKeyboard(page: Page) {
  const hint = page
    .locator('.world-cue')
    .getByText('Exploded mechanical keyboard', { exact: true });
  const key = async () => {
    const point = await page.evaluate(() => window.__studioReview!.project('keyboard'));
    return { x: point!.x + 20, y: point!.y - 8 };
  };
  await expect
    .poll(
      async () => {
        const { x, y } = await key();
        await page.mouse.move(x, y);
        return hint.isVisible();
      },
      { timeout: 20_000 },
    )
    .toBe(true);
  const { x, y } = await key();
  await page.mouse.click(x, y);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'case');
  await expect(page.locator('.interaction-caption')).toContainText(
    'ROG Azoth Extreme · Exploded View',
  );
}

test('a late Azoth switch delivery stays on the desk until the next exploded view @webgl', async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    );
    const scenes: Scene[] = [];
    const events = new EventTarget();
    events.addEventListener('observe', (event) => {
      const object = (event as CustomEvent<Scene>).detail;
      if (object.isScene) scenes.push(object);
    });
    Object.assign(window, {
      __THREE_DEVTOOLS__: events,
      readAzothSwitches(): SwitchState | undefined {
        for (const scene of scenes) {
          const group = scene.getObjectByName('Azoth switch assembly');
          if (!group) continue;
          const parts: SwitchState['parts'] = [];
          group.traverse((part) => {
            const mesh = part as InstancedMesh;
            if (!mesh.isInstancedMesh) return;
            const material = mesh.material as Material;
            parts.push({
              id: mesh.uuid,
              count: mesh.count,
              material: material.name,
              roomLighting: material.customProgramCacheKey().includes('-studio-room-visibility-'),
              clear: material.transparent,
            });
          });
          return { visible: group.visible, parts };
        }
      },
      readAzothSilverTransfer() {
        for (const scene of scenes) {
          const kb = scene.getObjectByName('Mechanical keyboard');
          if (!kb) continue;
          const parts: { layer?: string; tris: number; dy: number; studioDynamic?: boolean }[] = [];
          kb.traverse((node) => {
            const mesh = node as Mesh;
            if (!mesh.isMesh) return;
            const material = mesh.material as Material | undefined;
            if (material?.name !== 'Azoth · silver transfer') return;
            const geo = mesh.geometry;
            const tris = Math.floor((geo.index?.count ?? geo.attributes.position.count) / 3);
            const rest = mesh.userData?.azothRestPos as Vector3 | undefined;
            parts.push({
              layer: mesh.userData?.azothLayer as string | undefined,
              tris,
              dy: rest ? mesh.position.y - rest.y : 0,
              studioDynamic: mesh.userData?.studioDynamic as boolean | undefined,
            });
          });
          return parts;
        }
      },
      readAzothLayers(): LayerOffsets | undefined {
        for (const scene of scenes) {
          const kb = scene.getObjectByName('Mechanical keyboard');
          if (!kb) continue;
          const layers: LayerOffsets = {};
          kb.traverse((node) => {
            const mesh = node as Mesh;
            const layer = mesh.userData?.azothLayer as string | undefined;
            const rest = mesh.userData?.azothRestPos as Vector3 | undefined;
            if (!layer || !rest) return;
            layers[layer] = {
              dy: mesh.position.y - rest.y,
              dz: mesh.position.z - rest.z,
            };
          });
          return layers;
        }
      },
    });
  });
  const read = () =>
    page.evaluate(() =>
      (window as Window & { readAzothSwitches: () => SwitchState | undefined }).readAzothSwitches(),
    );
  const readLayers = () =>
    page.evaluate(() =>
      (window as Window & { readAzothLayers: () => LayerOffsets | undefined }).readAzothLayers(),
    );
  const readSilverTransfer = () =>
    page.evaluate(() =>
      (
        window as Window & {
          readAzothSilverTransfer: () =>
            | { layer?: string; tris: number; dy: number; studioDynamic?: boolean }[]
            | undefined;
        }
      ).readAzothSilverTransfer(),
    );
  const hold = Promise.withResolvers<void>();
  let requests = 0;
  await page.route('**/rog-azoth-extreme-switches.glb*', async (route) => {
    requests++;
    const response = await route.fetch();
    await hold.promise;
    await route.fulfill({ response });
  });
  try {
    await page.goto('/?review');
    await page.waitForFunction(
      () =>
        window.__studioReview?.objectPose('ROG_Azoth_Extreme') &&
        !document.querySelector('.studio-loading'),
    );
    const room = page.locator('.studio');
    const homePose = await page.evaluate(() => window.__studioReview!.objectPose('keyboard')!);
    const restBounds = await page.evaluate(() =>
      window.__studioReview!.bounds('Mechanical keyboard'),
    );
    const leaveView = async () => {
      await page.keyboard.press('Escape');
      await expect(room).toHaveAttribute('data-mode', 'room');
    };
    expect(await read()).toEqual({ visible: false, parts: [] });
    expect(requests).toBe(0);
    await openExplodedKeyboard(page);
    await expect.poll(() => requests).toBe(1);
    expect(await read()).toEqual({ visible: true, parts: [] });
    // Keyboard stays anchored in place on the desk mat while layers separate vertically
    expect(await page.evaluate(() => window.__studioReview!.objectPose('keyboard')!)).toEqual(
      homePose,
    );
    const partialLayers = (await readLayers())!;
    expect(partialLayers.keycaps.dy).toBeGreaterThan(0.09);
    expect(partialLayers.plate.dy).toBeGreaterThan(0.015);
    expect(partialLayers.pcb.dy).toBeGreaterThan(0.005);
    expect(partialLayers.wristpad.dz).toBeGreaterThan(0.018);
    const explodedSilver = (await readSilverTransfer())!;
    expect(explodedSilver).toHaveLength(2);
    const silverChassis = explodedSilver.find((part) => part.layer === 'chassis');
    const silverKeycaps = explodedSilver.find((part) => part.layer === 'keycaps');
    expect(silverChassis?.tris).toBeGreaterThan(0);
    expect(silverChassis?.dy).toBe(0);
    expect(silverKeycaps?.tris).toBeGreaterThan(0);
    expect(silverKeycaps?.studioDynamic).toBe(true);
    expect(silverKeycaps?.dy).toBeCloseTo(partialLayers.keycaps.dy, 5);
    await leaveView();
    expect(await read()).toEqual({ visible: false, parts: [] });
    const collapsed = (await readLayers())!;
    expect(collapsed.keycaps.dy).toBeCloseTo(0, 5);
    expect(collapsed.wristpad.dz).toBeCloseTo(0, 5);
    const collapsedSilver = (await readSilverTransfer())!;
    expect(collapsedSilver.find((part) => part.layer === 'keycaps')?.dy).toBeCloseTo(0, 5);

    const deliveredResponse = page.waitForResponse('**/rog-azoth-extreme-switches.glb*');
    hold.resolve();
    await (await deliveredResponse).finished();
    await page.waitForFunction(() => window.__studioReview?.objectPose('Installed_switches'));
    await page.evaluate(
      () =>
        new Promise<void>((done) =>
          requestAnimationFrame(() => requestAnimationFrame(() => done())),
        ),
    );
    const delivered = (await read())!;
    expect(delivered.visible).toBe(false);
    expect(
      delivered.parts
        .map(({ count, material, clear, roomLighting }) => [material, count, clear, roomLighting])
        .sort(),
    ).toEqual([
      ['Azoth · NX Snow lower POM', 81, false, true],
      ['Azoth · clear switch lid', 81, true, false],
      ['Azoth · snow-white POM stem', 81, false, true],
    ]);

    await openExplodedKeyboard(page);
    expect(await read()).toEqual({ ...delivered, visible: true });
    const fullLayers = (await readLayers())!;
    expect(fullLayers.keycaps.dy).toBeGreaterThan(fullLayers.lids.dy);
    expect(fullLayers.lids.dy).toBeGreaterThan(fullLayers.stems.dy);
    expect(fullLayers.stems.dy).toBeGreaterThan(fullLayers.bases.dy);
    expect(fullLayers.bases.dy).toBeGreaterThan(fullLayers.plate.dy);
    expect(fullLayers.plate.dy).toBeGreaterThan(fullLayers.pcb.dy);
    expect(fullLayers.pcb.dy).toBeGreaterThan(0);
    expect(fullLayers.wristpad.dz).toBeGreaterThan(0.018);
    const explodedBounds = await page.evaluate(() =>
      window.__studioReview!.bounds('Mechanical keyboard'),
    );
    expect(explodedBounds.max[1] - restBounds.max[1]).toBeGreaterThan(0.08);

    // Drag to orbit and scroll to zoom while exploded
    const camBefore = await page.evaluate(() => window.__studioReview!.camera());
    await page.mouse.move(720, 450);
    await page.mouse.down();
    await page.mouse.move(880, 390, { steps: 6 });
    await page.mouse.up();
    await expect
      .poll(async () => {
        const after = await page.evaluate(() => window.__studioReview!.camera());
        return Math.hypot(
          after.position[0] - camBefore.position[0],
          after.position[1] - camBefore.position[1],
          after.position[2] - camBefore.position[2],
        );
      })
      .toBeGreaterThan(0.05);

    await leaveView();
    expect(await read()).toEqual(delivered);
    const restoredBounds = await page.evaluate(() =>
      window.__studioReview!.bounds('Mechanical keyboard'),
    );
    expect(restoredBounds.max[1]).toBeCloseTo(restBounds.max[1], 4);
    expect(requests).toBe(1);
  } finally {
    hold.resolve();
  }
});

test('clicking the keyboard smoothly explodes all layers in place and collapses cleanly on Escape @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: false, quality: 'low' }),
    );
    const scenes: Scene[] = [];
    const events = new EventTarget();
    events.addEventListener('observe', (event) => {
      const object = (event as CustomEvent<Scene>).detail;
      if (object.isScene) scenes.push(object);
    });
    Object.assign(window, {
      __THREE_DEVTOOLS__: events,
      readAzothState() {
        for (const scene of scenes) {
          const kb = scene.getObjectByName('Mechanical keyboard');
          const sw = scene.getObjectByName('Azoth switch assembly');
          if (!kb || !sw) continue;
          const layers: LayerOffsets = {};
          kb.traverse((node) => {
            const mesh = node as Mesh;
            const layer = mesh.userData?.azothLayer as string | undefined;
            const rest = mesh.userData?.azothRestPos as Vector3 | undefined;
            if (!layer || !rest) return;
            layers[layer] = {
              dy: mesh.position.y - rest.y,
              dz: mesh.position.z - rest.z,
            };
          });
          return { switchesVisible: sw.visible, layers };
        }
      },
    });
  });
  await page.goto('/?review');
  await page.waitForFunction(
    () =>
      window.__studioReview?.objectPose('ROG_Azoth_Extreme') &&
      !document.querySelector('.studio-loading'),
  );
  const homePose = await page.evaluate(() => window.__studioReview!.objectPose('keyboard')!);
  await openExplodedKeyboard(page);

  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const s = (
            window as Window & {
              readAzothState: () => { switchesVisible: boolean; layers: LayerOffsets } | undefined;
            }
          ).readAzothState();
          return (
            s?.switchesVisible &&
            (s.layers.keycaps?.dy ?? 0) > 0.093 &&
            (s.layers.lids?.dy ?? 0) > 0.068 &&
            (s.layers.stems?.dy ?? 0) > 0.049 &&
            (s.layers.bases?.dy ?? 0) > 0.031 &&
            (s.layers.plate?.dy ?? 0) > 0.017 &&
            (s.layers.pcb?.dy ?? 0) > 0.006
          );
        }),
      { timeout: 15_000 },
    )
    .toBe(true);

  expect(await page.evaluate(() => window.__studioReview!.objectPose('keyboard')!)).toEqual(
    homePose,
  );

  await page.keyboard.press('Escape');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room', { timeout: 10_000 });
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const s = (
            window as Window & {
              readAzothState: () => { switchesVisible: boolean; layers: LayerOffsets } | undefined;
            }
          ).readAzothState();
          return (
            s !== undefined &&
            !s.switchesVisible &&
            Math.abs(s.layers.keycaps?.dy ?? 1) < 1e-4 &&
            Math.abs(s.layers.wristpad?.dz ?? 1) < 1e-4
          );
        }),
      { timeout: 10_000 },
    )
    .toBe(true);
});

test('inspection preload waits for both the installed keyboard and its switch assembly @webgl', async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    );
  });
  const holdBase = Promise.withResolvers<void>();
  const holdSwitches = Promise.withResolvers<void>();
  let requests = 0;
  await page.route('**/zone-desk.glb.gz', (route) => route.abort());
  await page.route('**/rog-azoth-extreme.glb*', async (route) => {
    await holdBase.promise;
    await route.continue();
  });
  await page.route('**/rog-azoth-extreme-switches.glb*', async (route) => {
    requests++;
    await holdSwitches.promise;
    await route.continue();
  });
  try {
    await page.goto('/?review&studio-details=preload', { waitUntil: 'domcontentloaded' });
    await expect.poll(() => requests, { timeout: 20_000 }).toBe(1);
    await expect(page.locator('.studio-loading')).toBeVisible();
    holdSwitches.resolve();
    await page.waitForFunction(() => window.__studioReview?.objectPose('Installed_switches'));
    await expect(page.locator('.studio-loading')).toBeVisible();
  } finally {
    holdBase.resolve();
    holdSwitches.resolve();
  }
  await page.waitForFunction(
    () =>
      window.__studioReview?.objectPose('Installed_switches') &&
      window.__studioReview?.objectPose('ROG_Azoth_Extreme') &&
      !document.querySelector('.studio-loading'),
  );
  await openExplodedKeyboard(page);
  expect(requests).toBe(1);
});
