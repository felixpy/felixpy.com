import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const directory = '.review/atelier/career-albums';
const url = new URL('/career-cover-art', process.argv[2] || 'http://127.0.0.1:5173').href;
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  await page.route(url, (route) =>
    route.fulfill({ contentType: 'text/html', body: '<!doctype html>' }),
  );
  await page.goto(url);
  const covers = await page.evaluate(async () => {
    await Promise.all(
      [500, 600, 700].map(async (weight) => {
        await import('/node_modules/@fontsource/ibm-plex-sans/latin-' + weight + '.css');
        await document.fonts.load(weight + ' 24px "IBM Plex Sans"');
      }),
    );
    const { careerEditions } = await import('/src/content/profile.ts');
    const { albumCover } = await import('/src/scene/career-albums.ts');
    return careerEditions.map((edition) => ({
      id: edition.id,
      jacket: edition.jacket,
      accent: edition.accent,
      title: edition.title,
      image: albumCover(edition).image.toDataURL(),
    }));
  });
  await mkdir(directory, { recursive: true });
  for (const { id, image, ...spec } of covers) {
    await writeFile(directory + '/' + id + '.png', Buffer.from(image.split(',')[1], 'base64'));
    await writeFile(directory + '/' + id + '.json', JSON.stringify(spec));
  }
} finally {
  await browser.close();
}
