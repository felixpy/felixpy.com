import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

test('the blind starts lowered, can be raised and lowered, and exports 33 tilted slats @webgl', async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({ quality: 'low', reducedMotion: true }),
    ),
  );
  await page.goto('/?review');
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'room');
  await page.waitForFunction(() => Boolean(window.__studioReview));
  await expect(page.locator('.studio-loading')).toHaveCount(0, { timeout: 45_000 });
  await page.evaluate(() => window.__studioReview!.activate('remote'));
  await expect(page.locator('.studio')).toHaveAttribute('data-mode', 'remote');
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        const frame = window.requestAnimationFrame.bind(window);
        window.requestAnimationFrame = () => 0;
        frame(() => resolve());
      }),
  );
  await page.evaluate(() => window.__studioReview!.activate('key-0'));
  await expect(page.getByText('Blinds raised', { exact: true })).toBeVisible();
  await page.evaluate(() => window.__studioReview!.activate('key-0'));
  await expect(page.getByText('Blinds lowered', { exact: true })).toBeVisible();
  await page.evaluate(() => window.__studioReview!.activate('key-1'));
  await expect(page.getByText('Slats angled', { exact: true })).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.evaluate(() => window.__studioReview!.exportRoom('Aluminium Venetian blind slats', true)),
  ]);
  const bytes = await readFile((await download.path())!);
  const scene = JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12))) as {
    nodes: { name?: string; mesh?: number; matrix: number[] }[];
  };
  const slats = scene.nodes.filter((node) => node.name?.startsWith('Blind slat '));
  expect(slats).toHaveLength(33);
  expect(new Set(slats.map((node) => node.mesh)).size).toBe(33);
  for (const [index, slat] of slats.entries()) {
    expect(slat.matrix[13]).toBeCloseTo(2.217 - (index + 1) * 0.0355, 5);
    expect(slat.matrix[0]).toBeCloseTo(Math.cos(0.58), 5);
    expect(slat.matrix[1]).toBeCloseTo(Math.sin(0.58), 5);
  }
});
