import { readdirSync, readFileSync } from 'node:fs';
import { basename, join, relative, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import type { Plugin } from 'vite';
import { meshStreams, partLibraryPath } from '../../src/scene/blender-parts';
import { installedProduct, installedProducts } from './installed-product.mjs';

const root = resolve('public/media/models');
const archives = new Map<string, { bench: boolean; version: 1 | 2 }>();
for (const collection of ['studio', 'workshop'] as const)
  for (const version of [1, 2] as const)
    archives.set(partLibraryPath(collection, version), {
      bench: collection === 'workshop',
      version,
    });

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

function pack({ bench, version }: { bench: boolean; version: 1 | 2 }) {
  const chunks: Buffer[] = [Buffer.from('BPK' + version)];
  const files = modelFiles('.mesh').filter(
    (file) => basename(file).startsWith('workshop-') === bench,
  );
  for (const file of files) {
    const key = Buffer.from(file.slice(0, -5));
    const data = readFileSync(join(root, file));
    const header = Buffer.alloc(5);
    header.writeUInt8(key.length);
    header.writeUInt32LE(data.length, 1);
    chunks.push(header, key, version === 2 ? deltaMesh(data) : data);
  }
  return gzipSync(Buffer.concat(chunks), { level: 9 });
}

export function studioParts(): Plugin {
  return {
    name: 'studio-blender-parts',
    configureServer(server) {
      const cache = new Map<string, Buffer>();
      server.watcher.on('all', (_, file) => {
        if (file.endsWith('.mesh')) cache.clear();
        if (file.endsWith('.glb')) cache.delete('/media/models/' + basename(file) + '.gz');
      });
      server.middlewares.use((request, response, next) => {
        const url = request.url?.split('?')[0] ?? '';
        const product = installedProducts.find((name) => url === '/media/models/' + name + '.gz');
        if (product) {
          if (!cache.has(url))
            cache.set(url, gzipSync(installedProduct(product, readFileSync(join(root, product)))));
          response.setHeader('Content-Type', 'application/octet-stream');
          response.end(cache.get(url));
          return;
        }
        const archive = archives.get(url);
        if (!archive) return next();
        if (!cache.has(url)) cache.set(url, pack(archive));
        response.setHeader('Content-Type', 'application/octet-stream');
        response.end(cache.get(url));
      });
    },
    generateBundle() {
      for (const [url, archive] of archives)
        this.emitFile({ type: 'asset', fileName: url.slice(1), source: pack(archive) });
      for (const file of modelFiles('.glb')) {
        this.emitFile({
          type: 'asset',
          fileName: 'media/models/' + file + '.gz',
          source: gzipSync(installedProduct(file, readFileSync(join(root, file))), { level: 9 }),
        });
      }
    },
  };
}
