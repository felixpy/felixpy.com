import { readFile, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const source = await readFile(new URL('./prograde-gold-label.svg', import.meta.url));
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  const result = await page.evaluate(async (source) => {
    const image = new Image();
    image.src = 'data:image/svg+xml;base64,' + source;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    canvas.getContext('2d').drawImage(image, 0, 0);
    return canvas.toDataURL('image/png').split(',')[1];
  }, source.toString('base64'));
  await writeFile(process.argv[2], Buffer.from(result, 'base64'));
} finally {
  await browser.close();
}
