import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5173');
const target = '.review/atelier/felix-notebook';
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  const url = new URL('/notebook-print', origin).href;
  await page.route(url, (route) =>
    route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Signed sheet</title>' }),
  );
  await page.goto(url);
  const image = await page.evaluate(async () => {
    await import('/node_modules/@fontsource/caveat/latin-500.css');
    await document.fonts.load('500 32px Caveat');
    const { writtenLeaf } = await import('/src/scene/notebook.ts');
    return writtenLeaf().image.toDataURL();
  });
  await mkdir(target, { recursive: true });
  await writeFile(target + '/handwritten.png', Buffer.from(image.split(',')[1], 'base64'));
} finally {
  await browser.close();
}
