import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5173');
const target = '.review/atelier/flight-sprite-proof';
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  const url = new URL('/sprite-proof-print', origin).href;
  await page.route(url, (route) =>
    route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Sprite proof</title>' }),
  );
  await page.goto(url);
  const sheets = await page.evaluate(async () => {
    await Promise.all([
      import('/node_modules/@fontsource/caveat/latin-500.css'),
      import('/node_modules/@fontsource/ibm-plex-sans/latin-500.css'),
      import('/src/app/studio.css'),
    ]);
    await Promise.all([
      document.fonts.load('500 32px Caveat'),
      document.fonts.load('500 32px "IBM Plex Sans"'),
      document.fonts.load('500 32px "Studio Han"', '近地航线小屏试样'),
    ]);
    const { spriteProofStock } = await import('/src/scene/flight-proof.ts');
    const { stock, setLocale } = spriteProofStock();
    return ['en', 'zh'].map((locale) => {
      setLocale(locale);
      return [locale, stock.image.toDataURL()];
    });
  });
  await mkdir(target, { recursive: true });
  for (const [locale, data] of sheets)
    await writeFile(
      target + '/proof-' + locale + '.png',
      Buffer.from(data.split(',')[1], 'base64'),
    );
} finally {
  await browser.close();
}
