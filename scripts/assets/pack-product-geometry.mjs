import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
import { readProduct } from './static-product.mjs';

const [file, selection = '', flag, positionSource] = process.argv.slice(2);
if (flag !== undefined && (flag !== '--positions-from' || !positionSource)) {
  throw new Error('Expected --positions-from followed by an uncompressed GLB');
}
const lossless = selection === '--lossless';
const texturesOnly = selection === '--textures-only';
const deduplicateOnly = selection === '--deduplicate';
const glb = await readFile(file);
const { doc: model, data: binary } = readProduct(glb);
const precision = {
  POSITION: { bits: 18, tolerance: 0.000009 },
  NORMAL: { bits: 13, tolerance: 0.00025 },
  TEXCOORD_0: { bits: 18, tolerance: 0.0002 },
};
const requested = new Map();
const meshes =
  lossless || texturesOnly || deduplicateOnly
    ? []
    : model.meshes.filter((mesh) => mesh.name.startsWith(selection));
for (const mesh of meshes) {
  for (const primitive of mesh.primitives) {
    for (const [semantic, index] of Object.entries(primitive.attributes)) {
      const accessor = model.accessors[index];
      if (precision[semantic] && accessor.componentType === 5126) {
        requested.set(accessor.bufferView, { accessor, ...precision[semantic] });
      }
    }
  }
}

if (positionSource) {
  const { doc, data } = readProduct(await readFile(positionSource));
  if (doc.meshes.length !== 1) throw new Error('Expected a single precision-source mesh');
  const [sourceMesh] = doc.meshes;
  const mesh = model.meshes.find((m) => m.name === sourceMesh.name);
  if (mesh?.primitives.length !== sourceMesh.primitives.length) {
    throw new Error(`Missing matching mesh for ${sourceMesh.name}`);
  }
  for (const [index, primitive] of mesh.primitives.entries()) {
    const source = sourceMesh.primitives[index];
    const accessor = model.accessors[primitive.attributes.POSITION];
    const original = doc.accessors[source.attributes.POSITION];
    const view = doc.bufferViews[original.bufferView];
    const compressed = model.bufferViews[accessor.bufferView].extensions?.EXT_meshopt_compression;
    if (
      doc.materials[source.material].name !== model.materials[primitive.material].name ||
      accessor.count !== original.count ||
      accessor.type !== 'VEC3' ||
      original.type !== 'VEC3' ||
      accessor.componentType !== 5126 ||
      original.componentType !== 5126 ||
      original.sparse ||
      view.buffer !== 0 ||
      view.extensions ||
      (view.byteStride ?? 12) !== 12 ||
      compressed?.mode !== 'ATTRIBUTES' ||
      compressed.byteStride !== 12 ||
      compressed.count !== original.count
    ) {
      throw new Error(`Mismatched precision source for ${mesh.name} primitive ${index}`);
    }
    const start = data.byteOffset + (view.byteOffset ?? 0) + (original.byteOffset ?? 0);
    const sourcePositions = new Float32Array(data.buffer, start, original.count * 3);
    requested.set(accessor.bufferView, { accessor, ...precision.POSITION, sourcePositions });
  }
}

await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
function repack(view, packed, { accessor, bits, tolerance, sourcePositions }) {
  const { count, byteStride, mode, filter } = view;
  const raw = new Uint8Array(count * byteStride);
  MeshoptDecoder.decodeGltfBuffer(raw, count, byteStride, packed, mode, filter);
  const previous = new Float32Array(raw.buffer);
  if (
    sourcePositions &&
    previous.some((value, i) => Math.abs(value - sourcePositions[i]) > 0.00025)
  ) {
    throw new Error('Precision source has different positions or vertex order');
  }
  const floats = sourcePositions ?? previous;
  const filtered = MeshoptEncoder.encodeFilterExp(
    floats,
    count,
    byteStride,
    bits,
    'SharedComponent',
  );
  const smaller = MeshoptEncoder.encodeGltfBuffer(filtered, count, byteStride, mode, 0);
  if (!sourcePositions && smaller.length >= packed.length) return packed;

  const check = new Uint8Array(raw.length);
  MeshoptDecoder.decodeGltfBuffer(check, count, byteStride, smaller, mode, 'EXPONENTIAL');
  const decoded = new Float32Array(check.buffer);
  if (decoded.some((value, i) => Math.abs(value - floats[i]) > tolerance)) {
    if (sourcePositions) throw new Error('Recovered positions failed the precision round-trip');
    return packed;
  }
  if (accessor.min) {
    const dims = byteStride / 4;
    const lo = Array(dims).fill(Infinity);
    const hi = Array(dims).fill(-Infinity);
    for (let i = 0; i < decoded.length; i++) {
      const axis = i % dims;
      lo[axis] = Math.min(lo[axis], decoded[i]);
      hi[axis] = Math.max(hi[axis], decoded[i]);
    }
    accessor.min = lo;
    accessor.max = hi;
  }
  view.filter = 'EXPONENTIAL';
  return smaller;
}

const parts = [];
let offset = 0;
const exactViews = new Map();
const storedRanges = new Map();
const sharedViews = new Map();
if (lossless) {
  for (const accessor of model.accessors) {
    if (accessor.bufferView !== undefined) exactViews.set(accessor.bufferView, accessor);
  }
  model.buffers.push({
    byteLength: model.buffers[0].byteLength,
    extensions: { EXT_meshopt_compression: { fallback: true } },
  });
  for (const key of ['extensionsUsed', 'extensionsRequired']) {
    model[key] = [...new Set([...(model[key] ?? []), 'EXT_meshopt_compression'])];
  }
}
for (const [i, view] of model.bufferViews.entries()) {
  let compression = view.extensions?.EXT_meshopt_compression;
  let source = compression ?? view;
  let data = binary.subarray(source.byteOffset ?? 0, (source.byteOffset ?? 0) + source.byteLength);
  if (lossless && exactViews.has(i) && (view.target === 34962 || view.target === 34963)) {
    if (compression) throw new Error('Lossless packing requires the original uncompressed GLB');
    const { count } = exactViews.get(i);
    const byteStride = view.byteStride ?? view.byteLength / count;
    const mode = view.target === 34962 ? 'ATTRIBUTES' : 'INDICES';
    const packed = MeshoptEncoder.encodeGltfBuffer(data, count, byteStride, mode, 0);
    const check = new Uint8Array(data.length);
    MeshoptDecoder.decodeGltfBuffer(check, count, byteStride, packed, mode, 'NONE');
    if (!data.equals(check)) throw new Error(`Meshopt round-trip failed for buffer view ${i}`);
    if (packed.length < data.length) {
      compression = { buffer: 0, count, byteStride, mode };
      (view.extensions ??= {}).EXT_meshopt_compression = compression;
      view.buffer = 1;
      source = compression;
      data = packed;
    }
  } else if (compression?.mode === 'ATTRIBUTES' && requested.has(i)) {
    data = repack(compression, data, requested.get(i));
  }
  const embedded = view.buffer === 0 && !view.target && !view.byteStride && !view.extensions;
  if (embedded || (compression && !texturesOnly)) {
    const hash = createHash('sha256').update(data).digest('hex');
    const key = (embedded ? 'raw:' : 'meshopt:') + hash;
    const first = storedRanges.get(key);
    if (first) {
      source.byteOffset = first.offset;
      source.byteLength = data.length;
      if (embedded) sharedViews.set(i, first.index);
      continue;
    }
    storedRanges.set(key, { index: i, offset });
  }
  source.byteOffset = offset;
  source.byteLength = data.length;
  const padding = (4 - (data.length % 4)) % 4;
  parts.push(data, Buffer.alloc(padding));
  offset += data.length + padding;
}
for (const image of model.images ?? []) {
  if (sharedViews.has(image.bufferView)) image.bufferView = sharedViews.get(image.bufferView);
}
model.buffers[0].byteLength = offset;
const json = Buffer.from(JSON.stringify(model));
const jsonPadding = Buffer.alloc((4 - (json.length % 4)) % 4, 32);
const header = Buffer.from(glb.subarray(0, 20));
const binHeader = Buffer.alloc(8);
binHeader.writeUInt32LE(offset);
binHeader.write('BIN\0', 4);
header.writeUInt32LE(json.length + jsonPadding.length, 12);
header.writeUInt32LE(28 + json.length + jsonPadding.length + offset, 8);
const result = Buffer.concat([header, json, jsonPadding, binHeader, ...parts]);
await writeFile(file, result);
console.log(`Product geometry packed: ${glb.length} → ${result.length} bytes`);
