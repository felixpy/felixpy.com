import { cpSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import type { Plugin } from 'vite';
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
const toolNames = new Set<string>(Object.values(workshopToolParts));

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
  const libraries: Record<PartLibrary, string[]> = { studio: [], workshop: [] };
  for (const file of modelFiles('.mesh')) {
    const name = file.slice(0, -5);
    if (toolNames.has(name)) libraries.workshop.push(file);
    else if (
      name.includes('/')
        ? roomCollections.has(name.split('/')[0])
        : roomFamilies.has(name.split('-')[0])
    )
      libraries.studio.push(file);
    else throw new Error('Assign Blender model to a room or workshop collection: ' + file);
  }
  if (libraries.workshop.length !== toolNames.size) throw new Error('Missing workshop tool mesh');
  for (const collection of ['studio', 'workshop'] as const)
    build.set(partLibraryPath(collection), () => pack(libraries[collection]));
  for (const zone of zoneBundleIds) {
    build.set(zoneBundlePath(zone) + '.gz', () => packZone(zone));
  }
  for (const file of modelFiles('.glb')) {
    build.set('/media/models/' + file + '.gz', () =>
      gzipSync(installedProduct(file, readFileSync(join(root, file))), { level: 9 }),
    );
  }
  return build;
}

export function studioParts(): Plugin {
  return {
    name: 'studio-blender-parts',
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
          cache.delete(partLibraryPath('studio'));
          cache.delete(partLibraryPath('workshop'));
        }
      });
      server.middlewares.use((request, response, next) => {
        const url = request.url?.split('?')[0] ?? '';
        if (!url.startsWith('/media/models/')) return next();
        const build = (builds ??= deliveries()).get(url);
        if (!build) return next();
        if (!cache.has(url)) cache.set(url, build());
        response.setHeader('Content-Type', 'application/octet-stream');
        response.end(cache.get(url));
      });
    },
    generateBundle() {
      for (const [url, build] of deliveries())
        this.emitFile({ type: 'asset', fileName: url.slice(1), source: build() });
    },
    writeBundle({ dir }) {
      if (!dir) throw new Error('The studio requires a static output directory');
      cpSync(publicDirectory, dir, {
        recursive: true,
        filter: (file) => {
          const rel = relative(publicDirectory, file).replaceAll('\\', '/');
          return (
            !/^media\/models\/.*\.(mesh|glb)$/.test(rel) &&
            !/^media\/photography\/field-notes(\/|$)/.test(rel)
          );
        },
      });
    },
  };
}
