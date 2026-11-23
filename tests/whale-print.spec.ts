import { expect, test, type Page } from '@playwright/test';

async function watchPrinter(page: Page, reducedMotion: boolean) {
  await page.setViewportSize({ width: 1360, height: 900 });
  await page.addInitScript((reducedMotion) => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ quality: 'low', automaticQuality: false, reducedMotion }),
    );
  }, reducedMotion);
  await page.goto('/?review', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
    null,
    { timeout: 120_000 },
  );
  await page.evaluate(() => window.__studioReview!.activate('filament-printer'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'case');
  await page.waitForFunction(() => {
    const review = window.__studioReview;
    const figure = 'DeepSeek Whale Girl on PEI';
    return review?.objectPose(figure) && review.bounds(figure).max[1] > 0.2;
  });
}

function machinePose(page: Page) {
  return page.evaluate(() => {
    const review = window.__studioReview!;
    const pose = (name: string) => review.objectPose(name)!.position;
    return {
      x: pose('Swaptek active tool')[0],
      z: pose('CoreXY crossbeam')[2],
      rail: pose('CoreXY crossbeam')[1],
      bed: pose('Z carriage')[1],
      shape: review.bounds('DeepSeek Whale Girl on PEI'),
    };
  });
}

test('the full DeepSeek figure stays on the bed while the nozzle keeps moving above its crown @webgl', async ({
  page,
}) => {
  test.setTimeout(180_000);
  await watchPrinter(page, false);
  const start = await machinePose(page);
  const height = start.shape.max[1] - start.shape.min[1];
  expect(height).toBeGreaterThan(0.13);
  expect(start.rail - start.bed - height).toBeCloseTo(0.00048, 4);
  await Promise.all([
    page.waitForFunction(
      (x) =>
        Math.abs(window.__studioReview!.objectPose('Swaptek active tool')!.position[0] - x) > 0.003,
      start.x,
    ),
    page.waitForFunction(
      (z) =>
        Math.abs(window.__studioReview!.objectPose('CoreXY crossbeam')!.position[2] - z) > 0.002,
      start.z,
    ),
  ]);
  const current = await machinePose(page);
  expect(current.bed).toEqual(start.bed);
  expect(current.shape).toEqual(start.shape);
  await page.keyboard.press('Escape');
  await watchPrinter(page, false);
  expect((await machinePose(page)).shape).toEqual(start.shape);
});

test('reduced motion shows the same whole figure and holds its machine pose @webgl', async ({
  page,
}) => {
  test.setTimeout(150_000);
  await watchPrinter(page, true);
  const start = await machinePose(page);
  await page.waitForTimeout(450);
  expect(await machinePose(page)).toEqual(start);
  expect(start.shape.max[1] - start.shape.min[1]).toBeGreaterThan(0.13);
});

test('the crown pass loops continuously across long frame gaps without cutting the completed model', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const data = await page.evaluate(async () => {
    const three = '/node_modules/.vite/deps/three.js',
      source = '/src/scene/whale-tail-print.ts';
    const T = (await import(three)) as typeof import('three');
    const { whaleTailPrint } = (await import(
      source
    )) as typeof import('../src/scene/whale-tail-print');
    const bed = new T.Group();
    const job = whaleTailPrint(bed, new T.LoadingManager());
    await job.load();
    const model = bed.getObjectByName('DeepSeek Whale Girl on PEI')!;
    const bounds = new T.Box3().setFromObject(model, true);
    let min = Infinity,
      max = 0;
    let previous = job.update(3600);
    for (let i = 0; i < 1600; i++) {
      const p = job.update(0.012);
      const step = Math.hypot(p.x - previous.x, p.z - previous.z);
      min = Math.min(min, step);
      max = Math.max(max, step);
      if (p.height < bounds.max.y + 0.0004 || !bounds.containsPoint(new T.Vector3(p.x, 0.05, p.z)))
        throw Error('Head outside its crown pass');
      previous = p;
    }
    return { min, max, height: bounds.max.y };
  });
  expect(data.height).toBeGreaterThan(0.13);
  expect(data.min).toBeGreaterThan(0.00025);
  expect(data.max).toBeLessThan(0.00085);
});
