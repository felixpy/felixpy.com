import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { chromium } from 'playwright';

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5173');
const keys = [...new Set(process.argv.slice(3))];
const target = '.review/atelier/binding-prints';
await mkdir(target, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  await page.route(origin.origin + '/edition-printing', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><title>Binding proofs</title>',
    }),
  );
  await page.goto(origin.origin + '/edition-printing');
  const editions = await page.evaluate(async (keys) => {
    const { editions: library } = await import('/src/content/books.ts');
    const editions = keys.length ? library.filter((book) => keys.includes(book.key)) : library;
    if (keys.length && editions.length !== keys.length) throw new Error('Unknown book edition');
    const { editionMaterials, pageStocks } = await import('/src/scene/book-binding.ts');
    const { LoadingManager, TextureLoader } =
      await import('/node_modules/three/build/three.module.js');
    const stock = pageStocks();
    const manager = new LoadingManager();
    const loaded = new Promise((resolve, reject) => {
      manager.onLoad = resolve;
      manager.onError = (url) => reject(new Error('Missing front print ' + url));
    });
    const loader = new TextureLoader(manager);
    const materials = editions.map((book) =>
      editionMaterials(book, loader, stock, book.rearReference ? 3 : 1),
    );
    await loaded;
    return materials.map(({ wrapper, leaves }, i) => {
      return {
        key: editions[i].key,
        isbn: editions[i].identifier,
        size: editions[i].size,
        rearReference: editions[i].rearReference,
        wrapper: wrapper.map.image.toDataURL(),
        stock: leaves.map.image.toDataURL(),
        x: leaves.map.repeat.x,
      };
    });
  }, keys);
  const catalogPath = join(target, 'catalog.json');
  const catalog = keys.length
    ? JSON.parse(
        await readFile(catalogPath, 'utf8').catch((error) => {
          if (error.code === 'ENOENT') return '{}';
          throw error;
        }),
      )
    : {};
  const papers = new Set();
  for (const { key, isbn, size, rearReference, wrapper, stock, x } of editions) {
    const paper = createHash('sha256').update(stock).digest('hex').slice(0, 16);
    const image = (uri) => Buffer.from(uri.split(',')[1], 'base64');
    if (!papers.has(paper)) {
      await writeFile(join(target, paper + '.png'), image(stock));
      papers.add(paper);
    }
    await writeFile(join(target, key + '.png'), image(wrapper));
    catalog[key] = { paper, x, isbn, size, rearReference };
  }
  await writeFile(catalogPath, JSON.stringify(catalog));
  console.log(`Saved ${editions.length} jackets and ${papers.size} paper stocks.`);
} finally {
  await browser.close();
}
