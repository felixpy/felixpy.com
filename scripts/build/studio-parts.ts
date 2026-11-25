import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import type { Plugin } from 'vite';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
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
const partLibraries: readonly PartLibrary[] = ['studio', 'workshop'];
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

let meshoptInitialized = false;
const meshoptReady = MeshoptDecoder.ready.then(() => {
  meshoptInitialized = true;
});

type GltfDoc = ReturnType<typeof readProduct>['doc'];

function isOpaqueMaterial(mat: Record<string, any> | undefined) {
  if (!mat) return true;
  if (mat.alphaMode === 'BLEND' || mat.alphaMode === 'MASK') return false;
  if (mat.extensions?.KHR_materials_transmission || mat.extensions?.KHR_materials_volume)
    return false;
  const alpha = mat.pbrMetallicRoughness?.baseColorFactor?.[3];
  return alpha === undefined || alpha >= 1;
}

function normalizeZoneProduct(source: ReturnType<typeof readProduct>) {
  const doc = source.doc as GltfDoc & Record<string, any>;
  const data: Buffer = source.data;
  const mats: Record<string, any>[] = doc.materials ?? [];
  if (!mats.length) return;

  // 1. Strip no-op KHR_materials_clearcoat (clearcoatFactor === 0 and no clearcoatTexture)
  //    so GLTFLoader builds MeshStandardMaterial natively instead of MeshPhysicalMaterial.
  let anyClearcoatLeft = false;
  for (const mat of mats) {
    const cc = mat.extensions?.KHR_materials_clearcoat;
    if (!cc) continue;
    const factor = cc.clearcoatFactor ?? 0;
    if (factor === 0 && !cc.clearcoatTexture) {
      delete mat.extensions.KHR_materials_clearcoat;
      if (Object.keys(mat.extensions).length === 0) delete mat.extensions;
    } else {
      anyClearcoatLeft = true;
    }
  }
  if (!anyClearcoatLeft) {
    for (const key of ['extensionsUsed', 'extensionsRequired'] as const) {
      if (Array.isArray(doc[key])) {
        doc[key] = doc[key].filter((ext: string) => ext !== 'KHR_materials_clearcoat');
      }
    }
  }

  // 2. Strip doubleSided on opaque materials whose referencing meshes are mathematically
  //    verified closed, consistently outward-wound manifolds with positive node scale.
  if (!meshoptInitialized || !mats.some((m) => m.doubleSided && isOpaqueMaterial(m))) return;
  const meshes: Record<string, any>[] = doc.meshes ?? [];
  const accessors: Record<string, any>[] = doc.accessors ?? [];
  const bufferViews: Record<string, any>[] = doc.bufferViews ?? [];
  const nodes: Record<string, any>[] = doc.nodes ?? [];

  const meshNegScale = new Array<boolean>(meshes.length).fill(false);
  const walkNode = (nodeIndex: number, neg: boolean) => {
    const node = nodes[nodeIndex];
    if (!node) return;
    let det = 1;
    if (node.scale) {
      det = node.scale[0] * node.scale[1] * node.scale[2];
    } else if (node.matrix) {
      const m = node.matrix;
      det =
        m[0] * (m[5] * m[10] - m[6] * m[9]) -
        m[4] * (m[1] * m[10] - m[2] * m[9]) +
        m[8] * (m[1] * m[6] - m[2] * m[5]);
    }
    const nextNeg = det < 0 ? !neg : neg;
    if (node.mesh !== undefined && nextNeg) meshNegScale[node.mesh] = true;
    for (const child of node.children ?? []) walkNode(child, nextNeg);
  };
  const sceneNodes: number[] = doc.scenes?.[doc.scene ?? 0]?.nodes ?? [];
  for (const rootIndex of sceneNodes) walkNode(rootIndex, false);

  const decodedViews = new Map<number, Uint8Array>();
  const decodeAccessor = (accIndex: number) => {
    const acc = accessors[accIndex];
    if (!acc || acc.bufferView === undefined || acc.sparse) return null;
    const bvIndex: number = acc.bufferView;
    const bv = bufferViews[bvIndex];
    if (!bv) return null;
    let raw = decodedViews.get(bvIndex);
    if (!raw) {
      const comp = bv.extensions?.EXT_meshopt_compression;
      if (comp) {
        const begin = comp.byteOffset ?? 0;
        const src = data.subarray(begin, begin + comp.byteLength);
        raw = new Uint8Array(comp.count * comp.byteStride);
        MeshoptDecoder.decodeGltfBuffer(
          raw,
          comp.count,
          comp.byteStride,
          src,
          comp.mode,
          comp.filter,
        );
      } else {
        const begin = bv.byteOffset ?? 0;
        raw = data.subarray(begin, begin + bv.byteLength);
      }
      decodedViews.set(bvIndex, raw);
    }
    const compSize =
      acc.componentType === 5126 || acc.componentType === 5125
        ? 4
        : acc.componentType === 5123 || acc.componentType === 5122
          ? 2
          : 1;
    const elemCount = acc.type === 'VEC3' ? 3 : acc.type === 'VEC2' ? 2 : 1;
    const stride: number = bv.byteStride || compSize * elemCount;
    return { acc, raw, stride, offset: (acc.byteOffset ?? 0) as number };
  };

  const isClosedOutwardManifold = (prims: Record<string, any>[]) => {
    const vertMap = new Map<string, number>();
    const coords: number[] = [];
    let nextId = 0;
    const dirEdges = new Map<number, number>();
    let signedVol = 0;
    let tris = 0;
    for (const prim of prims) {
      if (prim.mode !== undefined && prim.mode !== 4) return false;
      if (prim.indices === undefined || prim.attributes?.POSITION === undefined) return false;
      const posR = decodeAccessor(prim.attributes.POSITION);
      const idxR = decodeAccessor(prim.indices);
      if (!posR || !idxR) return false;
      const posView = new DataView(posR.raw.buffer, posR.raw.byteOffset, posR.raw.byteLength);
      const idxView = new DataView(idxR.raw.buffer, idxR.raw.byteOffset, idxR.raw.byteLength);
      const ct: number = posR.acc.componentType;
      const scale =
        ct === 5122 && posR.acc.normalized
          ? 1 / 32767
          : ct === 5123 && posR.acc.normalized
            ? 1 / 65535
            : 1;
      const welded = new Int32Array(posR.acc.count);
      for (let i = 0; i < posR.acc.count; i++) {
        const o = posR.offset + i * posR.stride;
        let x: number;
        let y: number;
        let z: number;
        let key: string;
        if (ct === 5126) {
          x = posView.getFloat32(o, true);
          y = posView.getFloat32(o + 4, true);
          z = posView.getFloat32(o + 8, true);
          key = `${Math.round(x * 1e5)},${Math.round(y * 1e5)},${Math.round(z * 1e5)}`;
        } else if (ct === 5122) {
          const ix = posView.getInt16(o, true);
          const iy = posView.getInt16(o + 2, true);
          const iz = posView.getInt16(o + 4, true);
          x = ix * scale;
          y = iy * scale;
          z = iz * scale;
          key = `${ix},${iy},${iz}`;
        } else if (ct === 5123) {
          const ix = posView.getUint16(o, true);
          const iy = posView.getUint16(o + 2, true);
          const iz = posView.getUint16(o + 4, true);
          x = ix * scale;
          y = iy * scale;
          z = iz * scale;
          key = `${ix},${iy},${iz}`;
        } else {
          return false;
        }
        let id = vertMap.get(key);
        if (id === undefined) {
          id = nextId++;
          vertMap.set(key, id);
          coords.push(x, y, z);
        }
        welded[i] = id;
      }
      const ict: number = idxR.acc.componentType;
      const icStride = ict === 5125 ? 4 : ict === 5123 ? 2 : 1;
      const triCount = Math.floor(idxR.acc.count / 3);
      for (let t = 0; t < triCount; t++) {
        const o0 = idxR.offset + t * 3 * icStride;
        const i0 =
          ict === 5125
            ? idxView.getUint32(o0, true)
            : ict === 5123
              ? idxView.getUint16(o0, true)
              : idxView.getUint8(o0);
        const i1 =
          ict === 5125
            ? idxView.getUint32(o0 + icStride, true)
            : ict === 5123
              ? idxView.getUint16(o0 + icStride, true)
              : idxView.getUint8(o0 + icStride);
        const i2 =
          ict === 5125
            ? idxView.getUint32(o0 + 2 * icStride, true)
            : ict === 5123
              ? idxView.getUint16(o0 + 2 * icStride, true)
              : idxView.getUint8(o0 + 2 * icStride);
        const a = welded[i0];
        const b = welded[i1];
        const c = welded[i2];
        if (a === b || b === c || c === a) continue;
        tris++;
        const ax = coords[a * 3];
        const ay = coords[a * 3 + 1];
        const az = coords[a * 3 + 2];
        const bx = coords[b * 3];
        const by = coords[b * 3 + 1];
        const bz = coords[b * 3 + 2];
        const cx = coords[c * 3];
        const cy = coords[c * 3 + 1];
        const cz = coords[c * 3 + 2];
        signedVol +=
          (ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)) / 6;
        for (const [u, v] of [
          [a, b],
          [b, c],
          [c, a],
        ] as const) {
          const lo = u < v ? u : v;
          const hi = u < v ? v : u;
          const k = lo * 1048576 + hi;
          const dir = u < v ? 1 : -1;
          dirEdges.set(k, (dirEdges.get(k) ?? 0) + dir);
        }
      }
    }
    if (tris < 4 || signedVol <= 0) return false;
    for (const net of dirEdges.values()) {
      if (net !== 0) return false;
    }
    return true;
  };

  const matClosed = new Array<boolean>(mats.length).fill(true);
  const matUsed = new Array<boolean>(mats.length).fill(false);
  for (let mIdx = 0; mIdx < meshes.length; mIdx++) {
    const prims: Record<string, any>[] = meshes[mIdx].primitives ?? [];
    const allOpaque =
      !meshNegScale[mIdx] &&
      prims.every((p) => isOpaqueMaterial(p.material !== undefined ? mats[p.material] : undefined));
    const wholeClosed = allOpaque && prims.length > 1 ? isClosedOutwardManifold(prims) : false;
    for (const p of prims) {
      if (p.material === undefined) continue;
      matUsed[p.material] = true;
      if (!matClosed[p.material]) continue;
      if (meshNegScale[mIdx]) {
        matClosed[p.material] = false;
        continue;
      }
      if (!wholeClosed && !isClosedOutwardManifold([p])) {
        matClosed[p.material] = false;
      }
    }
  }
  for (let mi = 0; mi < mats.length; mi++) {
    const mat = mats[mi];
    if (mat.doubleSided && isOpaqueMaterial(mat) && matUsed[mi] && matClosed[mi]) {
      delete mat.doubleSided;
    }
  }
}

function packZone(zone: ZoneBundleId) {
  const sources: ReturnType<typeof readProduct>[] = [];
  const roots: [ReturnType<typeof readProduct>, number][] = [];
  for (const [index, modelPath] of zoneBundleModels[zone].entries()) {
    const file = modelPath.replace(/^\/media\/models\//, '');
    const raw = installedProduct(file, readFileSync(join(root, file)));
    const source = readProduct(raw);
    normalizeZoneProduct(source);
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
    async buildStart() {
      await meshoptReady;
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
        const serve = () => {
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
        };
        if (meshoptInitialized) serve();
        else void meshoptReady.then(serve, next);
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
