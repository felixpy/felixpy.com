import { createReadStream, existsSync, mkdirSync, rmSync, statSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';
import { createServer } from 'node:http';
import { chromium } from 'playwright';
import { isImmutableAssetPath } from '../../src/app/asset-url.ts';

const distDir = resolve(process.cwd(), 'dist');
const profileDir = resolve(process.cwd(), '.review', 'audit-profile');
const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.ktx2': 'image/ktx2',
  '.wasm': 'application/wasm',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.hdr': 'application/octet-stream',
  '.bpk': 'application/octet-stream',
  '.glb': 'model/gltf-binary',
  '.gz': 'application/gzip',
  '.mp3': 'audio/mpeg',
  '.ogg': 'audio/ogg',
  '.txt': 'text/plain; charset=utf-8',
};

function cacheHeaderFor(urlPath) {
  return isImmutableAssetPath(urlPath) ? 'public, max-age=31536000, immutable' : 'public, no-cache';
}

function startStaticServer() {
  return new Promise((resolveServer) => {
    const server = createServer((req, res) => {
      const cleanPath = (req.url || '/').split('?')[0];
      let filePath = join(distDir, cleanPath === '/' ? 'index.html' : cleanPath);
      if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
        filePath = join(distDir, 'index.html');
      }
      const stat = statSync(filePath);
      const etag = `"${stat.size}-${Math.floor(stat.mtimeMs)}"`;
      const cacheControl = cacheHeaderFor(cleanPath);
      if (req.headers['if-none-match'] === etag) {
        res.writeHead(304, { ETag: etag, 'Cache-Control': cacheControl });
        res.end();
        return;
      }
      const headers = {
        'Content-Type': mimeTypes[extname(filePath).toLowerCase()] ?? 'application/octet-stream',
        'Content-Length': stat.size,
        ETag: etag,
        'Cache-Control': cacheControl,
      };
      res.writeHead(200, headers);
      createReadStream(filePath).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      resolveServer({ server, url: `http://127.0.0.1:${addr.port}/` });
    });
  });
}

function classify(urlPath) {
  if (urlPath.startsWith('/media/basis/')) return 'basis-transcoder';
  if (urlPath.startsWith('/media/lighting/')) return 'lighting';
  if (urlPath.startsWith('/media/models/')) return 'models';
  if (urlPath.startsWith('/media/materials/')) return 'materials';
  if (urlPath.startsWith('/media/photography/')) return 'photography';
  if (urlPath.startsWith('/media/panoramas/')) return 'panoramas';
  if (urlPath.startsWith('/media/')) return 'media-other';
  if (urlPath.endsWith('.woff2') || urlPath.endsWith('.woff')) return 'fonts';
  if (urlPath.endsWith('.js')) return 'js';
  if (urlPath.endsWith('.css')) return 'css';
  return 'other';
}

function summarize(items, label, marks) {
  const byCategory = {};
  let totalWireBytes = 0;
  let diskCacheHits = 0;
  let revalidated304 = 0;
  let fetched200 = 0;
  for (const r of items) {
    const c = (byCategory[r.category] ??= { count: 0, wireKB: 0, hits: 0, r304: 0 });
    c.count++;
    if (r.fromCache) {
      diskCacheHits++;
      c.hits++;
    } else if (r.status === 304) {
      revalidated304++;
      c.r304++;
      totalWireBytes += r.encodedBytes;
      c.wireKB += r.encodedBytes / 1024;
    } else {
      fetched200++;
      totalWireBytes += r.encodedBytes;
      c.wireKB += r.encodedBytes / 1024;
    }
  }
  for (const c of Object.values(byCategory)) c.wireKB = Number(c.wireKB.toFixed(1));
  return {
    label,
    totalRequests: items.length,
    fetched200,
    diskCacheHits,
    revalidated304,
    wireMB: Number((totalWireBytes / (1024 * 1024)).toFixed(2)),
    marks,
    byCategory,
  };
}

async function measureVisit(page, cdp, url, label) {
  const requests = new Map();
  let shadedWallTime = null;
  const onReq = (e) => {
    const pathname = new URL(e.request.url).pathname;
    if (!e.request.url.startsWith(url)) return;
    requests.set(e.requestId, {
      pathname,
      category: classify(pathname),
      fromCache: false,
      status: 0,
      encodedBytes: 0,
      beforeShaded: shadedWallTime === null,
    });
  };
  const onResp = (e) => {
    const item = requests.get(e.requestId);
    if (!item) return;
    item.status = e.response.status;
    item.fromCache ||= Boolean(e.response.fromDiskCache || e.response.fromServiceWorker);
  };
  const onCached = (e) => {
    const item = requests.get(e.requestId);
    if (item) item.fromCache = true;
  };
  const onFinish = (e) => {
    const item = requests.get(e.requestId);
    if (!item) return;
    item.encodedBytes = e.encodedDataLength;
  };
  cdp.on('Network.requestWillBeSent', onReq);
  cdp.on('Network.responseReceived', onResp);
  cdp.on('Network.requestServedFromCache', onCached);
  cdp.on('Network.loadingFinished', onFinish);

  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => performance.getEntriesByName('studio-input-ready').length > 0, {
    timeout: 60000,
  });
  await page.waitForFunction(() => performance.getEntriesByName('studio-room-shaded').length > 0, {
    timeout: 60000,
  });
  shadedWallTime = Date.now();
  await page.waitForFunction(
    () => performance.getEntriesByName('studio-room-rear-ready').length > 0,
    { timeout: 60000 },
  );
  await page.waitForTimeout(800);

  const marks = await page.evaluate(() => {
    const pick = (name) => performance.getEntriesByName(name)[0]?.startTime ?? null;
    return {
      inputReadyMs: pick('studio-input-ready'),
      frontPrepMs: pick('studio-room-material-prep-end'),
      shadedMs: pick('studio-room-shaded'),
      rearReadyMs: pick('studio-room-rear-ready'),
    };
  });
  const roundedMarks = Object.fromEntries(
    Object.entries(marks).map(([k, v]) => [k, v == null ? null : Math.round(v)]),
  );

  cdp.off('Network.requestWillBeSent', onReq);
  cdp.off('Network.responseReceived', onResp);
  cdp.off('Network.requestServedFromCache', onCached);
  cdp.off('Network.loadingFinished', onFinish);

  const all = [...requests.values()].filter((r) => r.status > 0 || r.fromCache);
  const firstScreen = all.filter((r) => r.beforeShaded);
  return {
    firstScreen: summarize(firstScreen, `${label}-first-screen`, roundedMarks),
    settled: summarize(all, `${label}-settled`, roundedMarks),
  };
}

rmSync(profileDir, { recursive: true, force: true });
mkdirSync(profileDir, { recursive: true });

const { server, url } = await startStaticServer();
const context = await chromium.launchPersistentContext(profileDir, {
  channel: 'chrome',
  headless: true,
  viewport: { width: 1920, height: 1080 },
  args: ['--use-angle=d3d11', '--enable-gpu', '--mute-audio'],
});
try {
  const page = context.pages()[0] ?? (await context.newPage());
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  const cold = await measureVisit(page, cdp, url, 'cold');
  const warm = await measureVisit(page, cdp, url, 'warm');
  console.log(JSON.stringify({ cold, warm }, null, 2));
} finally {
  await context.close();
  server.close();
  rmSync(profileDir, { recursive: true, force: true });
}
