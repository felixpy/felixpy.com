import { expect, test } from '@playwright/test';

test('the Fluke 115 lifts from the workbench, rotates and returns to both feet @webgl', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ reducedMotion: true, quality: 'low' }),
    ),
  );
  await page.goto('/?review');
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
  );
  const room = page.locator('.studio');
  const click = async (name: string) => {
    const point = await page.evaluate((id) => window.__studioReview!.project(id), name);
    expect(point).not.toBeNull();
    await page.mouse.click(point!.x, point!.y);
  };
  await page.mouse.move(550, 380);
  await page.mouse.down();
  await page.mouse.move(859, 397, { steps: 8 });
  await page.mouse.up();
  await click('Workbench top');
  await expect(room).toHaveAttribute('data-mode', 'bench');
  const bounds = () =>
    page.evaluate(() => window.__studioReview!.bounds('Fluke 115 on tilt stand'));
  await expect.poll(async () => Number.isFinite((await bounds()).min[0])).toBe(true);
  const original = await bounds();
  await click('multimeter');
  await expect(room).toHaveAttribute('data-mode', 'inspect');
  await expect(page.getByText('Examine the Fluke 115 multimeter', { exact: true })).toBeVisible();
  const pose = () => page.evaluate(() => window.__studioReview!.objectPose('multimeter'));
  const lifted = await pose();
  await page.mouse.move(460, 400);
  await page.mouse.down();
  await page.mouse.move(800, 400, { steps: 10 });
  await page.mouse.up();
  await expect.poll(async () => (await pose())!.rotation).not.toEqual(lifted!.rotation);
  await page.keyboard.press('Escape');
  await expect(room).toHaveAttribute('data-mode', 'bench');
  await expect.poll(bounds).toEqual(original);
});
