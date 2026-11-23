import { expect, test } from '@playwright/test';

test.use({ viewport: { width: 1100, height: 800 }, hasTouch: true });

test('room color styles change the rendered room and preserve the computer display @webgl', async ({
  page,
}) => {
  test.setTimeout(300_000);
  await page.addInitScript(() => {
    window.requestIdleCallback = () => 0;
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({
        reducedMotion: true,
        quality: 'low',
        automaticQuality: false,
        night: true,
        roomLook: 'neutral',
      }),
    );
  });
  await page.goto('/?review', { waitUntil: 'domcontentloaded' });
  const studio = page.locator('.studio');
  await expect(page.locator('.keyboard-entry')).toBeEnabled({ timeout: 40_000 });
  const enter = async () => {
    await page.keyboard.press('e');
    await expect(studio).toHaveAttribute('data-mode', 'computer');
    const settings = page.getByRole('button', { name: 'Settings', exact: true });
    await expect(settings).toBeVisible({ timeout: 40_000 });
    if (!(await page.locator('.os-window-settings').isVisible())) await settings.click();
  };
  await enter();
  for (const name of ['Desk lamp', 'Workbench lamp', 'Tool board light']) {
    await expect(page.getByRole('checkbox', { name, exact: true })).toHaveCount(0);
  }
  const aura = page.getByRole('checkbox', { name: 'Aura lighting', exact: true });
  const devices = () =>
    page.evaluate(() => {
      const { keyboard, mouse, speaker, caseLighting } = window.__studioReview!.lightLevels();
      return [keyboard, mouse, speaker, caseLighting];
    });
  await aura.uncheck();
  await expect.poll(devices).toEqual([0, 0, 0, 0]);
  await aura.check();
  await expect.poll(async () => Math.min(...(await devices()))).toBeGreaterThan(0);
  const heading = page.getByRole('heading', { name: 'Studio settings' });
  const preview = page.getByRole('img', { name: 'Studio color preview' });
  const look = page.getByRole('button', { name: /^Room color style/ });
  const quality = page.getByRole('button', { name: /^Render quality/ });
  const settle = () =>
    page.evaluate(async () => {
      for (let frame = 0; frame < 3; frame++) await new Promise(requestAnimationFrame);
    });
  for (const setting of ['High', 'Low power']) {
    await quality.click();
    await page.getByRole('option', { name: setting, exact: true }).click();
    let neutral: number[] = [];
    let ungradedText = '';
    for (const label of ['Neutral', 'Cinematic', 'Cool night']) {
      await look.click();
      await page.getByRole('option', { name: label, exact: true }).click();
      await expect(look).toHaveAccessibleName('Room color style ' + label);
      await expect(preview).toHaveCSS('filter', label === 'Neutral' ? 'none' : /room-look-/);
      const text = (await heading.screenshot()).toString('base64');
      if (label === 'Neutral') ungradedText = text;
      else expect(text).toBe(ungradedText);
      await page.keyboard.press('Escape');
      await expect(studio).toHaveAttribute('data-mode', 'room');
      await settle();
      const png = await page.screenshot({ clip: { x: 125, y: 95, width: 120, height: 70 } });
      const mean = await page.evaluate(async (encoded) => {
        const png = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
        const bitmap = await createImageBitmap(new Blob([png], { type: 'image/png' }));
        const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(bitmap, 0, 0);
        const pixels = ctx.getImageData(0, 0, bitmap.width, bitmap.height).data;
        return [0, 1, 2].map((channel) => {
          let sum = 0;
          for (let i = channel; i < pixels.length; i += 4) sum += pixels[i];
          return sum / (pixels.length / 4);
        });
      }, png.toString('base64'));
      await test.info().attach(setting + ' - ' + label, {
        body: JSON.stringify(mean),
        contentType: 'application/json',
      });
      if (label === 'Neutral') neutral = mean;
      else expect(Math.max(...mean.map((v, i) => Math.abs(v - neutral[i])))).toBeGreaterThan(1.5);
      if (setting !== 'Low power' || label !== 'Cool night') await enter();
    }
  }
});

test('settings migrate the room color style and preserve the selected look', async ({ page }) => {
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      value(this: HTMLCanvasElement, type: string, options?: unknown) {
        return type === 'webgl2' ? null : Reflect.apply(getContext, this, [type, options]);
      },
    });
    if (!localStorage.getItem('felix-studio-v1')) {
      localStorage.setItem('felix-studio-v1', JSON.stringify({ aura: false, ceiling: 0.35 }));
    }
  });
  await page.goto('/?review');
  async function openSettings() {
    await page.getByRole('button', { name: 'Settings', exact: true }).tap();
  }
  await openSettings();
  const selector = page.getByRole('button', { name: /^Room color style/ });
  await expect(selector).toHaveAccessibleName('Room color style Cinematic');
  const stored = () => page.evaluate(() => JSON.parse(localStorage.getItem('felix-studio-v1')!));
  const preview = page.getByRole('img', { name: 'Studio color preview' });
  await expect(preview).toHaveAttribute('src', '/media/graphics/room-look-night.webp');
  await expect
    .poll(() => preview.evaluate((img: HTMLImageElement) => img.naturalWidth))
    .toBeGreaterThan(0);
  for (const [value, label] of [
    ['neutral', 'Neutral'],
    ['cool-night', 'Cool night'],
    ['cinematic', 'Cinematic'],
    ['warm-film', 'Warm film'],
  ]) {
    await selector.tap();
    await page.getByRole('option', { name: label, exact: true }).tap();
    await expect.poll(stored).toMatchObject({ roomLook: value, aura: false, ceiling: 0.35 });
    await expect(preview).toHaveCSS(
      'filter',
      value === 'neutral' ? 'none' : new RegExp('room-look-' + value),
    );
  }
  await page.reload();
  await openSettings();
  await expect(selector).toHaveAccessibleName('Room color style Warm film');
  await page.evaluate(() => {
    const settings = JSON.parse(localStorage.getItem('felix-studio-v1')!);
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ ...settings, roomLook: 'expired', night: false }),
    );
  });
  await page.reload();
  await openSettings();
  await expect(selector).toHaveAccessibleName('Room color style Cinematic');
  await expect(preview).toHaveAttribute('src', '/media/graphics/room-look-day.webp');
  await expect
    .poll(() => preview.evaluate((img: HTMLImageElement) => img.naturalWidth))
    .toBeGreaterThan(0);
  await expect.poll(stored).toMatchObject({ roomLook: 'cinematic', aura: false, ceiling: 0.35 });
  await page.getByRole('button', { name: '简体中文', exact: true }).tap();
  await page.getByRole('button', { name: '房间色彩风格 电影感' }).tap();
  await expect(page.getByRole('listbox', { name: '房间色彩风格' }).getByRole('option')).toHaveText([
    '电影感',
    '原色',
    '暖调胶片',
    '冷调夜色',
  ]);
});
