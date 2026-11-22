import { expect, test, type Page } from '@playwright/test';
import type { InstancedMesh, Material, Scene } from 'three';

type SwitchState = {
  visible: boolean;
  parts: { id: string; count: number; material: string; roomLighting: boolean; clear: boolean }[];
};

async function pickUpKeyboard(page: Page) {
  const hint = page
    .locator('.world-cue')
    .getByText('Inspect the mechanical keyboard', { exact: true });
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
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'inspect');
}

test('a late Azoth switch delivery stays on the desk until the next inspection @webgl', async ({
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
    });
  });
  const read = () =>
    page.evaluate(() =>
      (window as Window & { readAzothSwitches: () => SwitchState | undefined }).readAzothSwitches(),
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
    const putBack = async () => {
      await page.keyboard.press('Escape');
      await expect(room).toHaveAttribute('data-mode', 'room');
    };
    expect(await read()).toEqual({ visible: false, parts: [] });
    expect(requests).toBe(0);
    await pickUpKeyboard(page);
    await expect.poll(() => requests).toBe(1);
    expect(await read()).toEqual({ visible: true, parts: [] });
    await putBack();
    expect(await read()).toEqual({ visible: false, parts: [] });
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
    await pickUpKeyboard(page);
    expect(await read()).toEqual({ ...delivered, visible: true });
    await putBack();
    expect(await read()).toEqual(delivered);
    expect(requests).toBe(1);
  } finally {
    hold.resolve();
  }
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
  await pickUpKeyboard(page);
  expect(requests).toBe(1);
});
