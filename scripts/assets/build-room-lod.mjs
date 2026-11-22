import { readFile, writeFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';

await Promise.all([MeshoptEncoder.ready, MeshoptSimplifier.ready]);
const master = await readFile(process.argv[2] ?? '.review/atelier/studio-master.glb');
const jsonSize = master.readUInt32LE(12);
const model = JSON.parse(master.toString('utf8', 20, 20 + jsonSize));
const dataStart = 28 + jsonSize;
const components = { 5121: Uint8Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
const dimensions = { SCALAR: 1, VEC2: 2, VEC3: 3 };

function attribute(id) {
  const input = model.accessors[id];
  const view = model.bufferViews[input.bufferView];
  const T = components[input.componentType];
  const dim = dimensions[input.type];
  const offset = master.byteOffset + dataStart + (view.byteOffset ?? 0) + (input.byteOffset ?? 0);
  const stride = view.byteStride ? view.byteStride / T.BYTES_PER_ELEMENT : dim;
  if (stride === dim) return new T(master.buffer, offset, input.count * dim);
  const src = new T(master.buffer, offset, (input.count - 1) * stride + dim);
  return T.from(
    { length: input.count * dim },
    (_, i) => src[Math.floor(i / dim) * stride + (i % dim)],
  );
}

function mechanicalProfileLocks(nodeName, positions) {
  let keep;
  if (nodeName.startsWith('Four-way_tapered_alloy_chassis')) {
    keep = (x, y, z) =>
      y <= 0.0705 &&
      Math.abs(Math.abs(x) - 0.461) <= 0.0195 &&
      Math.abs(Math.abs(z) - 0.052) <= 0.0195;
  } else if (nodeName === 'Dyson Solarcycle Morph Desk · CD06 · alloy') {
    keep = (x, y, z) => Math.hypot(x + 0.166, z - 0.253) <= 0.014 && y >= 0.4545 && y <= 0.4755;
  } else {
    return null;
  }
  const locks = new Uint8Array(positions.length / 3);
  for (let vertex = 0; vertex < locks.length; vertex++) {
    const i = vertex * 3;
    if (keep(positions[i], positions[i + 1], positions[i + 2])) locks[vertex] = 1;
  }
  return locks;
}

const records = [Buffer.from('LOD1')];
const seen = new Set();
let before = 0,
  after = 0;
for (const node of model.nodes) {
  const key = node.extras?.studioSurface;
  if (!key || seen.has(key) || node.mesh === undefined) continue;
  seen.add(key);
  const primitives = model.meshes[node.mesh].primitives;
  if (primitives.length !== 1) continue;
  const primitive = primitives[0];
  const a = primitive.attributes;
  if (a._STUDIOINDEX === undefined || a.NORMAL === undefined || (primitive.mode ?? 4) !== 4)
    continue;
  const actual = attribute(a._STUDIOINDEX);
  const index =
    primitive.indices === undefined
      ? Uint32Array.from(actual, (_, i) => i)
      : Uint32Array.from(attribute(primitive.indices));
  if (index.length < 1800) continue;
  const positions = Float32Array.from(attribute(a.POSITION));
  const normals = Float32Array.from(attribute(a.NORMAL));
  const [out, error] = MeshoptSimplifier.simplifyWithAttributes(
    index,
    positions,
    3,
    normals,
    3,
    [0.18, 0.18, 0.18],
    mechanicalProfileLocks(node.name ?? '', positions),
    Math.floor((index.length * 0.43) / 3) * 3,
    0.003,
  );
  if (out.length > index.length * 0.8 || error > 0.00305) continue;
  const indices = Uint32Array.from(out, (i) => actual[i]);
  const encoded = MeshoptEncoder.encodeIndexBuffer(
    new Uint8Array(indices.buffer),
    indices.length,
    4,
  );
  const label = Buffer.from(key);
  const header = Buffer.alloc(9);
  header.writeUInt8(label.length, 0);
  header.writeUInt32LE(indices.length, 1);
  header.writeUInt32LE(encoded.length, 5);
  records.push(header, label, encoded);
  before += index.length / 3;
  after += indices.length / 3;
}
const file = gzipSync(Buffer.concat(records), { level: 9 });
await writeFile(process.argv[3] ?? 'public/media/models/room-lod.gz', file);
console.log({
  geometries: (records.length - 1) / 3,
  originalTriangles: before,
  lowTriangles: after,
  bytes: file.length,
});
