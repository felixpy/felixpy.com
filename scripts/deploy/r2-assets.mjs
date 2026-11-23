import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, readdir, unlink } from 'node:fs/promises';
import { extname, join, relative, resolve, sep } from 'node:path';
import { promisify } from 'node:util';
import { isHostedAssetPath } from '../../src/app/asset-url.ts';

const bucket = 'assets';
const contentTypes = {
  '.avif': 'image/avif',
  '.glb': 'model/gltf-binary',
  '.gz': 'application/gzip',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.json': 'application/json',
  '.mp3': 'audio/mpeg',
  '.mp4': 'video/mp4',
  '.ogg': 'audio/ogg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.wasm': 'application/wasm',
  '.webm': 'video/webm',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

const exec = promisify(execFile);
const parallelism = 8;

function hash(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

async function inBatches(items, action) {
  const results = [];
  for (let start = 0; start < items.length; start += parallelism) {
    results.push(...(await Promise.all(items.slice(start, start + parallelism).map(action))));
  }
  return results;
}

async function collectAssets(root) {
  const files = await readdir(root, { recursive: true, withFileTypes: true });
  const assets = [];
  for (const entry of files) {
    if (!entry.isFile()) continue;
    const path = join(entry.parentPath, entry.name);
    const key = relative(root, path).split(sep).join('/');
    if (!isHostedAssetPath(key)) continue;
    assets.push({
      path,
      key,
      contentType: contentTypes[extname(key).toLowerCase()] ?? 'application/octet-stream',
      cacheControl: key.startsWith('assets/')
        ? 'public, max-age=31536000, immutable'
        : 'public, max-age=0, must-revalidate',
    });
  }
  return assets;
}

async function uploadAsset(asset, base, endpoint) {
  const bytes = await readFile(asset.path);
  const sha256 = hash(bytes);
  const aws = [
    's3api',
    '--endpoint-url',
    endpoint,
    '--region',
    'auto',
    '--output',
    'json',
    '--no-cli-pager',
  ];
  const key = decodeURIComponent(base.pathname.slice(1)) + asset.key;
  const object = ['--bucket', bucket, '--key', key];
  const current = await exec('aws', [...aws, 'head-object', ...object]).then(
    ({ stdout }) => JSON.parse(stdout),
    (error) => {
      if (/\((?:404|NotFound|NoSuchKey)\)/.test(error.stderr ?? '')) return null;
      throw error;
    },
  );
  const unchanged =
    current?.Metadata?.sha256 === sha256 &&
    current.ContentType === asset.contentType &&
    current.CacheControl === asset.cacheControl &&
    current.ContentLength === bytes.byteLength &&
    !current.ContentEncoding;

  if (!unchanged) {
    await exec('aws', [
      ...aws,
      'put-object',
      ...object,
      '--body',
      asset.path,
      '--content-type',
      asset.contentType,
      '--cache-control',
      asset.cacheControl,
      '--metadata',
      `sha256=${sha256}`,
    ]);
  }

  return { ...asset, sha256, size: bytes.byteLength, changed: !unchanged };
}

async function requestAsset(asset, base, origin, method, range) {
  const key = asset.key.split('/').map(encodeURIComponent).join('/');
  const headers = { origin, 'accept-encoding': 'identity' };
  if (range) headers.range = range;
  const response = await fetch(new URL(key, base), {
    method,
    headers,
    redirect: 'error',
    signal: AbortSignal.timeout(30_000),
  });
  const cors = response.headers.get('access-control-allow-origin');
  const mime = response.headers.get('content-type')?.split(';')[0];
  if (
    response.status !== (range ? 206 : 200) ||
    (cors !== '*' && cors !== origin) ||
    mime !== asset.contentType.split(';')[0]
  ) {
    await response.body?.cancel();
    throw new Error(
      `Unexpected CDN response for ${asset.key}: ${response.status}, MIME ${mime}, CORS ${cors}`,
    );
  }
  return response;
}

async function verifyAsset(asset, base, origin) {
  const response = await requestAsset(asset, base, origin, asset.changed ? 'GET' : 'HEAD');
  if (asset.changed && hash(Buffer.from(await response.arrayBuffer())) !== asset.sha256) {
    throw new Error(`CDN content does not match the build: ${asset.key}`);
  }
}

async function verifyAudioRange(audio, base, origin) {
  const response = await requestAsset(audio, base, origin, 'GET', 'bytes=0-1023');
  const end = Math.min(audio.size - 1, 1023);
  const bytes = await response.arrayBuffer();
  if (
    response.headers.get('content-range') !== `bytes 0-${end}/${audio.size}` ||
    bytes.byteLength !== end + 1
  ) {
    throw new Error(`Invalid audio range response: ${audio.key}`);
  }
}

async function main() {
  const [directory, option] = process.argv.slice(2);
  if (!directory || (option && option !== '--check')) {
    throw new Error('Usage: node scripts/deploy/r2-assets.mjs STATIC_DIRECTORY [--check]');
  }

  const root = resolve(directory);
  const base = new URL(process.env.VITE_ASSET_BASE_URL);
  if (base.href !== 'https://assets.felixpy.com/felix-studio/') {
    throw new Error('The release asset URL must use the felix-studio prefix');
  }
  for (const page of ['index.html', 'about.html']) {
    const html = await readFile(join(root, page), 'utf8');
    if (!html.includes(base.href)) throw new Error(`${page} was not built with the R2 asset URL`);
  }

  const assets = await collectAssets(root);
  const audioIndex = assets.findIndex((asset) => asset.contentType === 'audio/mpeg');
  if (audioIndex === -1 || !assets.some((asset) => asset.contentType === 'font/woff2')) {
    throw new Error('The build output is missing the expected media or fonts');
  }

  if (option === '--check') {
    console.log(`Assets selected for R2: ${assets.length}`);
    return;
  }

  const account = process.env.R2_ACCOUNT_ID;
  const origin = process.env.SITE_ORIGIN;
  if (
    !/^[a-f0-9]{32}$/.test(account ?? '') ||
    !origin ||
    !process.env.AWS_ACCESS_KEY_ID ||
    !process.env.AWS_SECRET_ACCESS_KEY
  ) {
    throw new Error('R2 account, site origin, or upload credentials are missing');
  }

  const endpoint = `https://${account}.r2.cloudflarestorage.com`;
  const uploaded = await inBatches(assets, (asset) => uploadAsset(asset, base, endpoint));
  console.log(
    `R2 upload complete. Updated ${uploaded.filter(({ changed }) => changed).length} of ${assets.length} assets.`,
  );
  await inBatches(uploaded, (asset) => verifyAsset(asset, base, origin));
  await verifyAudioRange(uploaded[audioIndex], base, origin);
  await inBatches(assets, ({ path }) => unlink(path));
  console.log(`Verified and removed ${assets.length} R2 assets from the Vercel output.`);
}

await main();
