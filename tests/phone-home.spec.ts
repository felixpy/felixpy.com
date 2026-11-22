import { expect, test, type Page } from '@playwright/test';
import { homeLights, type HomeLightId } from '../src/app/home-lights';

const storage = 'felix-studio-v1';

function nextRoomFrame(page: Page) {
  return page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

async function openPhone(page: Page) {
  await page.evaluate(() => window.__studioReview!.activate('development-phone'));
  await nextRoomFrame(page);
  const home = page.getByRole('region', { name: 'Apple Home' });
  await expect(home).toBeVisible();
  await expect(home).toHaveAttribute('data-visible', 'true');
  return home;
}

async function start(page: Page, night = false) {
  await page.setViewportSize({ width: 900, height: 600 });
  await page.route('https://api.open-meteo.com/**', (route) => route.abort());
  await page.addInitScript(
    ({ storage, lights, night }) => {
      if (localStorage.getItem(storage)) return;
      localStorage.setItem(
        storage,
        JSON.stringify({
          automaticQuality: true,
          reducedMotion: true,
          night,
          ceiling: 0.46,
          ...Object.fromEntries(lights.map((id) => [id, !night])),
        }),
      );
    },
    { storage, lights: homeLights.map((l) => l.id), night },
  );
  await page.goto('/?review', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => window.__studioReview && performance.getEntriesByName('studio-room-shaded').length > 0,
    null,
    { timeout: 120000 },
  );
}

function stored(page: Page, id: HomeLightId | 'night') {
  return page.evaluate(({ id, storage }) => JSON.parse(localStorage.getItem(storage)!)[id], {
    id,
    storage,
  });
}

test('all eight Home switches keep session changes until a daylight reload @webgl', async ({
  page,
}) => {
  test.setTimeout(180000);
  let releaseFixture!: () => void;
  const pendingFixture = new Promise<void>((resolve) => {
    releaseFixture = resolve;
  });
  await page.route('**/astro-mondrian-600.glb*', async (route) => {
    await pendingFixture;
    await route.continue();
  });
  await start(page);
  let home = await openPhone(page);
  const phoneBounds = await home.boundingBox();
  const caption = page.locator('.object-caption');
  await expect
    .poll(async () => (await caption.boundingBox())!.y - phoneBounds!.y - phoneBounds!.height)
    .toBeGreaterThan(8);
  const captionBounds = await caption.boundingBox();
  expect(captionBounds!.y + captionBounds!.height).toBeLessThanOrEqual(
    page.viewportSize()!.height - 10,
  );
  await expect(home.getByRole('switch')).toHaveCount(8);
  await expect(home.getByText('All off', { exact: true })).toBeVisible();
  for (const [index, light] of homeLights.entries()) {
    const toggle = home.getByRole('switch', { name: light.en, exact: true });
    await expect(toggle).not.toBeChecked();
    const power = () => page.evaluate((id) => window.__studioReview!.lightLevels()[id], light.id);
    await expect.poll(power).toBe(0);
    await toggle.click();
    await expect(toggle).toBeChecked();
    expect(await stored(page, light.id)).toBeUndefined();
    await nextRoomFrame(page);
    await expect.poll(power, { message: `${light.en} emits light` }).toBeGreaterThan(0);
    await expect(home.locator('[role=switch][aria-checked=true]')).toHaveCount(index + 1);
  }
  releaseFixture();
  expect(await stored(page, 'night')).toBe(false);
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-phone-home]')).toHaveCount(0);
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  home = await openPhone(page);
  await expect(home.getByText('8 on', { exact: true })).toBeVisible();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
    null,
    { timeout: 120000 },
  );
  home = await openPhone(page);
  await expect(home.getByText('All off', { exact: true })).toBeVisible();
});

test('a night reload lights every Home fixture after all eight were manually switched off @webgl', async ({
  page,
}) => {
  test.setTimeout(180000);
  await start(page, true);
  let home = await openPhone(page);
  await expect(home.getByText('8 on', { exact: true })).toBeVisible();
  for (const light of homeLights) {
    await home.getByRole('switch', { name: light.en, exact: true }).click();
    expect(await stored(page, light.id)).toBeUndefined();
  }
  await expect(home.getByText('All off', { exact: true })).toBeVisible();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
    null,
    { timeout: 120000 },
  );
  home = await openPhone(page);
  await expect(home.getByText('8 on', { exact: true })).toBeVisible();
  for (const { id } of homeLights) {
    await expect
      .poll(() => page.evaluate((id) => window.__studioReview!.lightLevels()[id], id))
      .toBeGreaterThan(0);
  }
});

test('the physical ScreenBar and remote day-night key update the held iPhone and the actual desk wash @webgl', async ({
  page,
}) => {
  test.setTimeout(180000);
  await start(page);
  const home = await openPhone(page);
  const bar = home.getByRole('switch', { name: 'Monitor light bar' });
  await bar.click();
  await nextRoomFrame(page);
  const wash = () => page.evaluate(() => window.__studioReview!.lightLevels().screenBar);
  await expect.poll(wash).toBeGreaterThan(0);
  await page.keyboard.press('Escape');
  const screenBar = await page.evaluate(() => window.__studioReview!.project('screen-bar')!);
  await page.mouse.click(screenBar.x, screenBar.y);
  await nextRoomFrame(page);
  await expect.poll(wash).toBe(0);
  await openPhone(page);
  await expect(bar).not.toBeChecked();
  await page.keyboard.press('Escape');
  for (const night of [true, false]) {
    await page.evaluate(() => window.__studioReview!.activate('remote'));
    await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
    await page.evaluate(() => window.__studioReview!.activate('key-5'));
    await expect.poll(() => stored(page, 'night')).toBe(night);
    await page.keyboard.press('Escape');
    await openPhone(page);
    await expect(home.locator('[role=switch][aria-checked=true]')).toHaveCount(night ? 8 : 0);
    await page.keyboard.press('Escape');
  }
});
