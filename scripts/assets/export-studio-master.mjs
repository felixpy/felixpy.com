import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const destination = path.resolve(process.argv[3] ?? '.review/atelier');
await mkdir(destination, { recursive: true });
const browser = await chromium.launch({
  channel: 'chrome',
  args: ['--enable-gpu', '--use-angle=d3d11'],
});
try {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 800 },
    acceptDownloads: true,
  });
  await page.addInitScript(() =>
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({
        quality: 'high',
        rainAudio: false,
        reducedMotion: true,
        night: false,
        weather: '晴',
        blinds: false,
      }),
    ),
  );
  await page.goto(new URL('/?review=authoring', process.argv[2] ?? 'http://127.0.0.1:5173').href);
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
    undefined,
    { timeout: 150000 },
  );
  const [file] = await Promise.all([
    page.waitForEvent('download', { timeout: 240000 }),
    page.evaluate(() => window.__studioReview.exportRoom(undefined, true)),
  ]);
  await file.saveAs(path.join(destination, 'studio-master.glb'));
} finally {
  await browser.close();
}
