import { expect, test } from '@playwright/test';

test('the Z8 keeps its card door closed on repeated inspection', async ({ page }) => {
  const chamberRequests: string[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.includes('/nikon-z8-card-bay.glb'))
      chamberRequests.push(request.url());
  });
  await page.addInitScript(() => {
    localStorage.setItem('felix-studio-v1', JSON.stringify({ reducedMotion: true }));
  });
  await page.goto('/?review');
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
  );
  const closedDoor = () =>
    page.evaluate(() => window.__studioReview!.objectPose('Z8 closed card door and overmould'));
  const restPose = await closedDoor();
  expect(restPose).toBeTruthy();
  expect(chamberRequests).toHaveLength(0);
  const studio = page.locator('.studio');
  for (let pickup = 0; pickup < 2; pickup++) {
    const point = await page.evaluate(() => window.__studioReview!.project('camera'));
    expect(point).toBeTruthy();
    await page.mouse.click(point!.x, point!.y);
    await expect(studio).toHaveAttribute('data-mode', 'inspect');
    expect(await closedDoor()).toEqual(restPose);
    await page.keyboard.press('Escape');
    await expect(studio).toHaveAttribute('data-mode', 'room');
    expect(await closedDoor()).toEqual(restPose);
  }
  expect(chamberRequests).toHaveLength(0);
});
