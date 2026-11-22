import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5175');
const dir = '.review/atelier/aerospace-notebook';
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  const url = new URL('/aerospace-cover-print', origin).href;
  await page.route(url, (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><title>Aerospace cover</title>',
    }),
  );
  await page.goto(url);
  const image = await page.evaluate(async () => {
    await import('/node_modules/@fontsource/ibm-plex-sans/latin-500.css');
    const han = await new FontFace('Studio Han', 'url(/fonts/studio-han.woff2)', {
      weight: '100 900',
    }).load();
    document.fonts.add(han);
    const { aerospaceTitle } = await import('/src/scene/school.ts');
    await document.fonts.load('500 32px "IBM Plex Sans"', aerospaceTitle.en);
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = 1440;
    const ctx = canvas.getContext('2d');
    ctx.scale(2, 2);
    ctx.fillStyle = '#334450';
    ctx.fillRect(0, 0, 600, 720);
    ctx.fillStyle = '#d9c8a4';
    ctx.font = '600 57px "Studio Han", sans-serif';
    ctx.fillText(aerospaceTitle.zh, 56, 117);
    ctx.font = '500 32px "IBM Plex Sans", sans-serif';
    ctx.fillText(aerospaceTitle.en, 58, 167);
    ctx.save();
    ctx.translate(0, 93);
    ctx.strokeStyle = '#9eab9c72';
    ctx.lineWidth = 1;
    for (let x = 58; x < 550; x += 30) {
      ctx.beginPath();
      ctx.moveTo(x, 178);
      ctx.lineTo(x, 448);
      ctx.stroke();
    }
    for (let y = 178; y < 450; y += 30) {
      ctx.beginPath();
      ctx.moveTo(58, y);
      ctx.lineTo(550, y);
      ctx.stroke();
    }
    ctx.strokeStyle = '#c9b792';
    ctx.lineWidth = 3.4;
    ctx.beginPath();
    ctx.moveTo(300, 183);
    ctx.bezierCurveTo(311, 196, 317, 246, 318, 270);
    ctx.lineTo(506, 387);
    ctx.lineTo(507, 407);
    ctx.lineTo(322, 354);
    ctx.lineTo(316, 416);
    ctx.lineTo(350, 439);
    ctx.lineTo(350, 452);
    ctx.lineTo(300, 442);
    ctx.lineTo(250, 452);
    ctx.lineTo(250, 439);
    ctx.lineTo(284, 416);
    ctx.lineTo(278, 354);
    ctx.lineTo(93, 407);
    ctx.lineTo(94, 387);
    ctx.lineTo(282, 270);
    ctx.bezierCurveTo(283, 246, 289, 196, 300, 183);
    ctx.stroke();
    ctx.restore();
    return canvas.toDataURL();
  });
  await mkdir(dir, { recursive: true });
  await writeFile(dir + '/cover.png', Buffer.from(image.split(',')[1], 'base64'));
} finally {
  await browser.close();
}
