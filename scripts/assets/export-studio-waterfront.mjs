import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { createServer } from 'vite';

const output = path.resolve(process.argv[3] ?? '.review/atelier/studio-waterfront.glb');
await mkdir(path.dirname(output), { recursive: true });
const server = process.argv[2]
  ? undefined
  : await createServer({ server: { host: '127.0.0.1', port: 0 }, logLevel: 'error' });
await server?.listen();
const url = new URL('/?review=authoring', process.argv[2] ?? server.resolvedUrls.local[0]);
let browser;
try {
  browser = await chromium.launch({
    channel: 'chrome',
    args: ['--enable-gpu', '--use-angle=d3d11'],
  });
  const page = await browser.newPage({
    acceptDownloads: true,
    viewport: { width: 1200, height: 800 },
  });
  await page.addInitScript(() => {
    localStorage.setItem(
      'felix-studio-v1',
      JSON.stringify({
        quality: 'high',
        reducedMotion: true,
        night: false,
        weather: '晴',
        rainAudio: false,
      }),
    );
  });
  await page.goto(url.href);
  await page.waitForFunction(
    () => window.__studioReview && !document.querySelector('.studio-loading'),
    undefined,
    { timeout: 150000 },
  );
  const [file] = await Promise.all([
    page.waitForEvent('download', { timeout: 120000 }),
    page.evaluate(() =>
      window.__studioReview.exportRoom('Depth-reprojected waterfront photograph', true),
    ),
  ]);
  await file.saveAs(output);
} finally {
  await browser?.close();
  await server?.close();
}
