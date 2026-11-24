import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import type { Plugin } from 'vite';
import {
  assetUrl,
  insertContentHash,
  isHostedAssetPath,
  isImmutableAssetPath,
} from '../../src/app/asset-url';
import { meshStreams, partLibraryPath, type PartLibrary } from '../../src/scene/blender-parts';
import { workshopToolParts } from '../../src/scene/workshop-tool-parts';
import {
  zoneBundleIds,
  zoneBundleModels,
  zoneBundlePath,
  type ZoneBundleId,
} from '../../src/scene/zone-bundles';
import { installedProduct } from './installed-product.mjs';
import { assembleProducts, readProduct } from './static-product.mjs';

const publicDirectory = resolve('public');
const root = join(publicDirectory, 'media', 'models');
const basisDirectory = resolve('node_modules', 'three', 'examples', 'jsm', 'libs', 'basis');
const basisFiles = ['basis_transcoder.js', 'basis_transcoder.wasm'] as const;
const unhashedPublicPaths = new Set(['/media/credits.txt']);
const partLibraries: readonly PartLibrary[] = ['studio', 'workshop', 'pc-hero'];
const roomFamilies = new Set([
  'aio',
  'amsterdam',
  'astral',
  'atx',
  'eps',
  'gr701',
  'pocket',
  'princess',
  'ryuo',
  'strix',
  'thor',
  'window',
]);
const roomCollections = new Set([
  'bindings',
  'capture',
  'fixtures',
  'handheld',
  'kef',
  'ryuo-mf12c',
  'stationery',
]);
const pcHeroFamilies = new Set(['aio', 'astral', 'atx', 'eps', 'ryuo', 'strix']);
const pcHeroCollections = new Set(['ryuo-mf12c']);
const pcRoomLiveParts = new Set([
  'astral-impeller-shell',
  'ryuo-mf12c/medallion',
  'ryuo-mf12c/rotor-foil',
  'ryuo-mf12c/vanes',
  'strix-fan-graphite',
  'strix-fan-opal',
  'strix-fan-white',
]);
const pcHeroExplicitParts = new Set([
  'gr701-cable-bay-contact',
  'gr701-cable-bay-drive',
  'gr701-cable-bay-polymer',
  'gr701-cable-bay-print',
  'gr701-cable-bay-smoke',
  'gr701-cable-bay-steel',
  'gr701-cable-bay-wire',
  'gr701-rail',
  'thor-1600-pixels',
]);
const toolNames = new Set<string>(Object.values(workshopToolParts));

function isPcHeroPart(name: string) {
  if (pcRoomLiveParts.has(name)) return false;
  if (pcHeroExplicitParts.has(name)) return true;
  return name.includes('/')
    ? pcHeroCollections.has(name.split('/')[0])
    : pcHeroFamilies.has(name.split('-')[0]);
}

function shortHash(bytes: Buffer) {
  return createHash('sha256').update(bytes).digest('hex').slice(0, 10);
}

function deltaMesh(bytes: Buffer) {
  const streams = meshStreams(bytes);
  const output = Buffer.allocUnsafe(bytes.length);
  bytes.copy(output, 0, 0, 52);
  for (const { offset, count, fields } of streams) {
    for (let field = 0; field < fields; field++) {
      const lowBytes = offset + field * 2 * count;
      const highBytes = lowBytes + count;
      let previous = 0;
      let source = offset + field * 2;
      for (let i = 0; i < count; i++, source += fields * 2) {
        const value = bytes.readUInt16LE(source);
        const delta = ((value - previous) << 16) >> 16;
        const code = (delta << 1) ^ (delta >> 15);
        output[lowBytes + i] = code & 255;
        output[highBytes + i] = code >>> 8;
        previous = value;
      }
    }
  }
  return output;
}

function modelFiles(extension: string) {
  return readdirSync(root, { recursive: true, withFileTypes: true })
    .filter((file) => file.isFile() && file.name.endsWith(extension))
    .map((file) => relative(root, join(file.parentPath, file.name)).replaceAll('\\', '/'))
    .sort();
}

function pack(files: string[]) {
  const chunks: Buffer[] = [Buffer.from('BPK2')];
  for (const file of files) {
    const key = Buffer.from(file.slice(0, -5));
    const data = readFileSync(join(root, file));
    const header = Buffer.alloc(5);
    header.writeUInt8(key.length);
    header.writeUInt32LE(data.length, 1);
    chunks.push(header, key, deltaMesh(data));
  }
  return gzipSync(Buffer.concat(chunks), { level: 9 });
}

function packZone(zone: ZoneBundleId) {
  const sources: ReturnType<typeof readProduct>[] = [];
  const roots: [ReturnType<typeof readProduct>, number][] = [];
  for (const [index, modelPath] of zoneBundleModels[zone].entries()) {
    const file = modelPath.replace(/^\/media\/models\//, '');
    const raw = installedProduct(file, readFileSync(join(root, file)));
    const source = readProduct(raw);
    const sceneIndex = source.doc.scene ?? 0;
    const sceneNodes = source.doc.scenes?.[sceneIndex]?.nodes ?? [];
    source.doc.nodes ??= [];
    const wrapperIndex =
      source.doc.nodes.push({
        name: `zone_item_${index}`,
        extras: { zoneModelPath: modelPath },
        children: [...sceneNodes],
      }) - 1;
    sources.push(source);
    roots.push([source, wrapperIndex]);
  }
  return gzipSync(assembleProducts(sources, roots), { level: 9 });
}

function deliveries() {
  const build = new Map<string, () => Buffer>();
  const libraries: Record<PartLibrary, string[]> = { studio: [], workshop: [], 'pc-hero': [] };
  for (const file of modelFiles('.mesh')) {
    const name = file.slice(0, -5);
    if (toolNames.has(name)) libraries.workshop.push(file);
    else if (isPcHeroPart(name)) libraries['pc-hero'].push(file);
    else if (
      name.includes('/')
        ? roomCollections.has(name.split('/')[0])
        : roomFamilies.has(name.split('-')[0])
    )
      libraries.studio.push(file);
    else throw new Error('Assign Blender model to a room or workshop collection: ' + file);
  }
  if (libraries.workshop.length !== toolNames.size) throw new Error('Missing workshop tool mesh');
  if (!libraries['pc-hero'].length) throw new Error('Missing PC hero mesh');
  for (const collection of partLibraries)
    build.set(partLibraryPath(collection), () => pack(libraries[collection]));
  for (const zone of zoneBundleIds) {
    build.set(zoneBundlePath(zone) + '.gz', () => packZone(zone));
  }
  for (const file of modelFiles('.glb')) {
    build.set('/media/models/' + file + '.gz', () =>
      gzipSync(installedProduct(file, readFileSync(join(root, file))), { level: 9 }),
    );
  }
  for (const file of basisFiles) {
    build.set('/media/basis/' + file, () => readFileSync(join(basisDirectory, file)));
  }
  return build;
}

function includePublicFile(rel: string) {
  return (
    !/^media\/models\/.*\.(mesh|glb)$/.test(rel) &&
    !/^media\/photography\/field-notes(\/|$)/.test(rel)
  );
}

function scanPublicFiles() {
  const files: Array<{ rel: string; fullPath: string }> = [];
  for (const entry of readdirSync(publicDirectory, { recursive: true, withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const fullPath = join(entry.parentPath, entry.name);
    const rel = relative(publicDirectory, fullPath).replaceAll('\\', '/');
    if (!includePublicFile(rel)) continue;
    files.push({ rel, fullPath });
  }
  files.sort((a, b) => a.rel.localeCompare(b.rel));
  return files;
}

export function studioParts(assetBase = ''): {
  plugin: Plugin;
  getManifest: () => Record<string, string>;
} {
  let isBuild = false;
  let generated = new Map<string, Buffer>();
  let publicFiles: Array<{ rel: string; fullPath: string }> = [];
  let manifest: Record<string, string> = {};

  function prepareBuildAssets() {
    generated = new Map<string, Buffer>();
    manifest = {};
    for (const [url, build] of deliveries()) {
      const bytes = build();
      generated.set(url, bytes);
      manifest[url] = insertContentHash(url, shortHash(bytes));
    }
    publicFiles = scanPublicFiles();
    for (const { rel, fullPath } of publicFiles) {
      const url = '/' + rel;
      if (!isHostedAssetPath(rel) || unhashedPublicPaths.has(url)) continue;
      const hash = shortHash(readFileSync(fullPath));
      manifest[url] = insertContentHash(url, hash);
    }
  }

  const plugin: Plugin = {
    name: 'studio-blender-parts',
    enforce: 'pre',
    configResolved(config) {
      isBuild = config.command === 'build';
    },
    buildStart() {
      if (isBuild) prepareBuildAssets();
    },
    transform(code, id) {
      if (!isBuild) return null;
      const normalized = id.split('?')[0].replaceAll('\\', '/');
      if (!normalized.endsWith('/src/app/asset-url.ts')) return null;
      const pattern = /const defaultManifest(?::\s*Record<string,\s*string>)?\s*=\s*\{\s*\};/;
      if (!pattern.test(code)) {
        throw new Error('Failed to inject media manifest into src/app/asset-url.ts');
      }
      return {
        code: code.replace(
          pattern,
          `const defaultManifest: Record<string, string> = ${JSON.stringify(manifest)};`,
        ),
        map: null,
      };
    },
    configureServer(server) {
      const cache = new Map<string, Buffer>();
      let builds: ReturnType<typeof deliveries> | undefined;
      server.watcher.on('all', (_, file) => {
        if (!/\.(mesh|glb)$/.test(file)) return;
        builds = undefined;
        if (file.endsWith('.glb')) {
          cache.delete('/media/models/' + relative(root, file).replaceAll('\\', '/') + '.gz');
          for (const zone of zoneBundleIds) cache.delete(zoneBundlePath(zone) + '.gz');
        } else {
          for (const collection of partLibraries) cache.delete(partLibraryPath(collection));
        }
      });
      server.middlewares.use((request, response, next) => {
        const url = request.url?.split('?')[0] ?? '';
        if (!url.startsWith('/media/models/') && !url.startsWith('/media/basis/')) return next();
        const build = (builds ??= deliveries()).get(url);
        if (!build) return next();
        if (!cache.has(url)) cache.set(url, build());
        const contentType = url.endsWith('.js')
          ? 'application/javascript; charset=utf-8'
          : url.endsWith('.wasm')
            ? 'application/wasm'
            : 'application/octet-stream';
        response.setHeader('Content-Type', contentType);
        response.end(cache.get(url));
      });
    },
    configurePreviewServer(server) {
      server.middlewares.use((request, response, next) => {
        const pathname = (request.url ?? '/').split('?')[0];
        if (isImmutableAssetPath(pathname)) {
          response.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
        } else if (
          pathname === '/' ||
          pathname.endsWith('.html') ||
          pathname === '/media-manifest.json' ||
          pathname === '/media/credits.txt'
        ) {
          response.setHeader('Cache-Control', 'public, no-cache');
        }
        next();
      });
    },
    generateBundle(_, bundle) {
      for (const [url, bytes] of generated) {
        const outPath = (manifest[url] ?? url).slice(1);
        this.emitFile({ type: 'asset', fileName: outPath, source: bytes });
      }
      this.emitFile({
        type: 'asset',
        fileName: 'media-manifest.json',
        source: JSON.stringify(manifest, null, 2) + '\n',
      });
      // Rewrite static CSS url('/fonts/...') and url('/media/...') to content-hashed URLs.
      for (const item of Object.values(bundle)) {
        if (item.type !== 'asset' || !item.fileName.endsWith('.css')) continue;
        if (typeof item.source !== 'string') continue;
        item.source = item.source.replace(
          /url\((['"]?)(\/(?:media|fonts)\/[^'")]+)\1\)/g,
          (_match, quote: string, path: string) =>
            `url(${quote}${assetUrl(path, assetBase, manifest)}${quote})`,
        );
      }
    },
    writeBundle({ dir }) {
      if (!dir) throw new Error('The studio requires a static output directory');
      for (const { rel, fullPath } of publicFiles) {
        const url = '/' + rel;
        const targetRel = (manifest[url] ?? url).slice(1);
        const dest = join(dir, targetRel);
        mkdirSync(dirname(dest), { recursive: true });
        copyFileSync(fullPath, dest);
      }
    },
  };

  return {
    plugin,
    getManifest: () => manifest,
  };
}
