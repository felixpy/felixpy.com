import { expect, test } from '@playwright/test';
import { PerspectiveCamera, Vector3 } from 'three';

test('the bookshelf can be browsed, zoomed and inspected before switching views @webgl', async ({
  page,
}, info) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ quality: 'low', reducedMotion: true }),
    ),
  );
  await page.goto('/?review', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
    null,
    { timeout: 120_000 },
  );
  const room = page.locator('.studio');
  const pose = () => page.evaluate(() => window.__studioReview!.camera());
  const bounds = await page.evaluate(() => window.__studioReview!.bounds('Oiled ash bookcase'));
  const shelfCamera = async () => {
    const frame = await pose(),
      size = page.viewportSize()!;
    const camera = new PerspectiveCamera(frame.fov, size.width / size.height, 0.01, 100);
    camera.position.fromArray(frame.position);
    camera.quaternion.fromArray(frame.rotation);
    camera.updateMatrixWorld(true);
    return camera;
  };
  await page.mouse.move(390, 350);
  await page.mouse.down();
  await page.mouse.move(570, 385, { steps: 6 });
  await page.mouse.up();
  const shelf = await page.evaluate(() => window.__studioReview!.objectPose('bookshelf')!.position);
  const stile = new Vector3(...shelf).add(new Vector3(0.305, 1.94, 0.184));
  const size = page.viewportSize()!;
  await expect
    .poll(
      async () => {
        const spot = stile.clone().project(await shelfCamera());
        await page.mouse.move(((1 + spot.x) * size.width) / 2, ((1 - spot.y) * size.height) / 2);
        return page.locator('.world-cue').textContent();
      },
      { timeout: 15000 },
    )
    .toContain('Browse the bookshelf');
  const spot = stile.project(await shelfCamera());
  await page.screenshot({ path: info.outputPath('bookshelf-entry.jpg') });
  await page.mouse.click(((1 + spot.x) * size.width) / 2, ((1 - spot.y) * size.height) / 2);
  await expect(room).toHaveAttribute('data-mode', 'bookshelf');
  await expect.poll(async () => (await pose()).fov).toBe(50);
  for (const size of [
    { width: 1280, height: 800 },
    { width: 900, height: 760 },
  ]) {
    await page.setViewportSize(size);
    await expect
      .poll(async () => {
        const camera = await shelfCamera();
        return Math.max(
          ...[bounds.min[1], bounds.max[1]].map((y) => {
            const p = new Vector3((bounds.min[0] + bounds.max[0]) / 2, y, bounds.max[2]).project(
              camera,
            );
            return Math.max(Math.abs(p.x), Math.abs(p.y));
          }),
        );
      })
      .toBeLessThan(1);
    await page.screenshot({ path: info.outputPath('bookshelf-' + size.width + '.jpg') });
  }
  const overview = await pose();
  const book = await page.evaluate(() => window.__studioReview!.project('book-4')!);
  await page.mouse.click(book.x, book.y);
  await expect(room).toHaveAttribute('data-mode', 'inspect');
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'bookshelf');
  await page.mouse.move(470, 350);
  await page.mouse.wheel(0, -900);
  await expect.poll(async () => (await pose()).fov).toBeLessThan(30);
  const pan = async (from: number, to: number) => {
    await page.mouse.move(505, from);
    await page.mouse.down();
    await page.mouse.move(505, to, { steps: 6 });
    await page.mouse.up();
  };
  await pan(240, 580);
  await expect
    .poll(async () => (await pose()).position[1])
    .toBeGreaterThan(overview.position[1] + 0.12);
  await page.screenshot({ path: info.outputPath('bookshelf-upper.jpg') });
  await pan(620, 100);
  await expect
    .poll(async () => (await pose()).position[1])
    .toBeLessThan(overview.position[1] - 0.04);
  await page.screenshot({ path: info.outputPath('bookshelf-lower.jpg') });
  await page.mouse.wheel(0, 900);
  await expect.poll(async () => (await pose()).fov).toBe(overview.fov);
  const tower = await page.evaluate(() => window.__studioReview!.project('case')!);
  await page.mouse.click(tower.x, tower.y);
  await expect(room).toHaveAttribute('data-mode', 'case');
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'room');
  const towerBounds = await page.evaluate(() => {
    const review = window.__studioReview!;
    return review.bounds(review.inventory().find((target) => target.id === 'case')!.name);
  });
  const towerCenter = new Vector3(...towerBounds.min).lerp(new Vector3(...towerBounds.max), 0.5);
  await expect
    .poll(async () => {
      const camera = await shelfCamera();
      return camera
        .getWorldDirection(new Vector3())
        .angleTo(towerCenter.clone().sub(camera.position));
    })
    .toBeLessThan(0.1);
});
