import { createHash } from 'node:crypto';

export function readProduct(bytes) {
  const length = bytes.readUInt32LE(12);
  return {
    doc: JSON.parse(bytes.toString('utf8', 20, 20 + length)),
    data: bytes.subarray(28 + length),
  };
}

export function assembleProducts(sources, roots) {
  const maps = new Map(sources.map((source) => [source, new Map()]));
  const base = sources[0].doc;
  const output = {
    asset: base.asset,
    extras: base.extras,
    scene: 0,
    scenes: [{ ...base.scenes[base.scene], nodes: [] }],
  };
  const data = [],
    ranges = new Map();
  let offset = 0,
    fallbackSize = 0;
  function store(bytes) {
    const hash = createHash('sha256').update(bytes).digest('hex');
    if (ranges.has(hash)) return ranges.get(hash);
    const start = offset;
    const padding = (4 - (bytes.length % 4)) % 4;
    offset += bytes.length + padding;
    data.push(bytes, Buffer.alloc(padding));
    ranges.set(hash, start);
    return start;
  }
  function map(source, type, index) {
    const id = type + ':' + index;
    if (maps.get(source).has(id)) return maps.get(source).get(id);
    const item = structuredClone(source.doc[type][index]);
    const group = (output[type] ??= []);
    const mapped = group.length;
    group.push(item);
    maps.get(source).set(id, mapped);
    const ref = (obj, prop, kind) => {
      if (obj[prop] !== undefined) obj[prop] = map(source, kind, obj[prop]);
    };
    if (type === 'nodes') {
      if (item.skin !== undefined || item.camera !== undefined)
        throw Error('Expected a rigid display product');
      ref(item, 'mesh', 'meshes');
      const instancing = item.extensions?.EXT_mesh_gpu_instancing?.attributes;
      if (instancing) {
        for (const semantic in instancing) ref(instancing, semantic, 'accessors');
      }
      if (item.children) item.children = item.children.map((index) => map(source, 'nodes', index));
    } else if (type === 'meshes') {
      for (const primitive of item.primitives) {
        for (const semantic in primitive.attributes)
          ref(primitive.attributes, semantic, 'accessors');
        ref(primitive, 'indices', 'accessors');
        ref(primitive, 'material', 'materials');
      }
    } else if (type === 'materials') {
      function relinkTextures(node) {
        for (const [name, value] of Object.entries(node)) {
          if (!value || typeof value !== 'object') continue;
          if (name.endsWith('Texture')) ref(value, 'index', 'textures');
          else relinkTextures(value);
        }
      }
      relinkTextures(item);
    } else if (type === 'textures') {
      ref(item, 'source', 'images');
      ref(item, 'sampler', 'samplers');
      for (const extension of Object.values(item.extensions ?? {}))
        ref(extension, 'source', 'images');
    } else if (type === 'accessors' || type === 'images') {
      if (item.sparse) throw Error('Expected a dense product mesh');
      ref(item, 'bufferView', 'bufferViews');
    } else if (type === 'bufferViews') {
      const compressed = item.extensions?.EXT_meshopt_compression;
      const range = compressed ?? item;
      if (range.buffer !== 0) throw Error('Expected an embedded data range');
      const begin = range.byteOffset ?? 0;
      range.byteOffset = store(source.data.subarray(begin, begin + range.byteLength));
      if (compressed) {
        item.buffer = 1;
        item.byteOffset = fallbackSize;
        fallbackSize += Math.ceil(item.byteLength / 4) * 4;
      }
    }
    return mapped;
  }
  for (const [source, root] of roots) output.scenes[0].nodes.push(map(source, 'nodes', root));
  for (const k of ['extensionsUsed', 'extensionsRequired']) {
    output[k] = [...new Set(sources.flatMap(({ doc }) => doc[k] ?? []))];
  }
  output.buffers = [{ byteLength: offset }];
  if (fallbackSize)
    output.buffers.push({
      byteLength: fallbackSize,
      extensions: { EXT_meshopt_compression: { fallback: true } },
    });
  const json = Buffer.from(JSON.stringify(output));
  const jsonSize = Math.ceil(json.length / 4) * 4;
  const head = Buffer.alloc(20);
  head.write('glTF');
  head.writeUInt32LE(2, 4);
  head.writeUInt32LE(28 + jsonSize + offset, 8);
  head.writeUInt32LE(jsonSize, 12);
  head.write('JSON', 16);
  const bin = Buffer.alloc(8);
  bin.writeUInt32LE(offset);
  bin.write('BIN', 4);
  return Buffer.concat([head, json, Buffer.alloc(jsonSize - json.length, 32), bin, ...data]);
}
