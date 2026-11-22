import { createHash } from 'node:crypto';
import { MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';
import { assembleProducts } from './static-product.mjs';

export async function compactProductMeshes(
  { doc, data },
  { triangleRatio = () => 1, shareGeometry = false } = {},
) {
  const views = [...doc.bufferViews];
  const accessors = [...doc.accessors];
  const chunks = [data];
  let offset = data.length;
  await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready, MeshoptSimplifier.ready]);
  const streams = new Map();

  function attribute(index) {
    const accessor = accessors[index];
    const view = views[accessor.bufferView];
    const stream = view.extensions?.EXT_meshopt_compression;
    const range = stream ?? view;
    const start = range.byteOffset ?? 0;
    let raw = Uint8Array.from(data.subarray(start, start + range.byteLength));
    if (stream) {
      const decoded = new Uint8Array(stream.count * stream.byteStride);
      MeshoptDecoder.decodeGltfBuffer(
        decoded,
        stream.count,
        stream.byteStride,
        raw,
        stream.mode,
        stream.filter,
      );
      raw = decoded;
    }
    const Type = { 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array }[
      accessor.componentType
    ];
    if (!Type || accessor.byteOffset || accessor.sparse)
      throw new Error('Unexpected rigid product attribute');
    return new Type(raw.buffer);
  }

  function store(raw, count, stride, type, componentType, mode, filter = 'NONE') {
    const encoded = MeshoptEncoder.encodeGltfBuffer(raw, count, stride, mode, 0);
    const streamKey = shareGeometry
      ? [
          count,
          stride,
          type,
          componentType,
          mode,
          filter,
          createHash('sha256').update(encoded).digest('hex'),
        ].join(':')
      : undefined;
    if (streamKey && streams.has(streamKey)) return streams.get(streamKey);
    const padding = -encoded.length & 3;
    const stream = {
      buffer: 0,
      byteOffset: offset,
      byteLength: encoded.length,
      count,
      byteStride: stride,
      mode,
      filter,
    };
    chunks.push(encoded, Buffer.alloc(padding));
    offset += encoded.length + padding;
    const view = {
      buffer: 1,
      byteLength: count * stride,
      extensions: { EXT_meshopt_compression: stream },
    };
    const accessor = { bufferView: doc.bufferViews.length, type, componentType, count };
    if (mode === 'ATTRIBUTES') Object.assign(view, { byteStride: stride, target: 34962 });
    else view.target = 34963;
    if (componentType === 5120) accessor.normalized = true;
    if (type === 'VEC3' && componentType === 5126) {
      const decoded = new Uint8Array(count * stride);
      MeshoptDecoder.decodeGltfBuffer(decoded, count, stride, encoded, mode, filter);
      const positions = new Float32Array(decoded.buffer);
      accessor.min = [Infinity, Infinity, Infinity];
      accessor.max = [-Infinity, -Infinity, -Infinity];
      for (let i = 0; i < positions.length; i++) {
        const axis = i % 3;
        accessor.min[axis] = Math.min(accessor.min[axis], positions[i]);
        accessor.max[axis] = Math.max(accessor.max[axis], positions[i]);
      }
    }
    doc.bufferViews.push(view);
    const index = doc.accessors.push(accessor) - 1;
    if (streamKey) streams.set(streamKey, index);
    return index;
  }

  function reorder(values, components, stride, remap, count) {
    const ordered = new Float32Array(count * stride);
    for (let i = 0; i < remap.length; i++) {
      if (remap[i] < count)
        ordered.set(values.subarray(i * components, (i + 1) * components), remap[i] * stride);
    }
    return ordered;
  }

  for (const mesh of doc.meshes) {
    for (const primitive of mesh.primitives) {
      const attrs = primitive.attributes;
      let indices = Uint32Array.from(attribute(primitive.indices));
      const vertices = attribute(attrs.POSITION);
      const directions = attribute(attrs.NORMAL);
      const ratio = triangleRatio(mesh, doc.materials[primitive.material]);
      if (ratio < 1) {
        const target = Math.min(
          indices.length,
          3 * Math.max(16, Math.round((indices.length * ratio) / 3)),
        );
        [indices] = MeshoptSimplifier.simplifyWithAttributes(
          indices,
          vertices,
          3,
          directions,
          3,
          [0.11, 0.11, 0.11],
          null,
          target,
          0.035,
          ['Permissive'],
        );
      }
      const [remap, count] = MeshoptEncoder.reorderMesh(indices, true, true);
      const positions = reorder(vertices, 3, 3, remap, count);
      const normals = reorder(directions, 3, 4, remap, count);
      const exp = (values, stride) =>
        MeshoptEncoder.encodeFilterExp(values, count, stride, 13, 'SharedComponent');
      attrs.POSITION = store(
        exp(positions, 12),
        count,
        12,
        'VEC3',
        5126,
        'ATTRIBUTES',
        'EXPONENTIAL',
      );
      attrs.NORMAL = store(
        MeshoptEncoder.encodeFilterOct(normals, count, 4, 8),
        count,
        4,
        'VEC3',
        5120,
        'ATTRIBUTES',
        'OCTAHEDRAL',
      );
      const material = doc.materials[primitive.material];
      if (attrs.TEXCOORD_0 !== undefined && /"[^"]*Texture"\s*:/.test(JSON.stringify(material))) {
        const uvs = reorder(attribute(attrs.TEXCOORD_0), 2, 2, remap, count);
        attrs.TEXCOORD_0 = store(exp(uvs, 8), count, 8, 'VEC2', 5126, 'ATTRIBUTES', 'EXPONENTIAL');
      } else delete attrs.TEXCOORD_0;
      const compact = count < 65536 ? Uint16Array.from(indices) : indices;
      primitive.indices = store(
        new Uint8Array(compact.buffer),
        compact.length,
        compact.BYTES_PER_ELEMENT,
        'SCALAR',
        compact.BYTES_PER_ELEMENT === 2 ? 5123 : 5125,
        'TRIANGLES',
      );
    }
  }
  if (shareGeometry) {
    const meshes = new Map();
    for (const node of doc.nodes) {
      if (node.mesh === undefined) continue;
      const signature = JSON.stringify(doc.meshes[node.mesh].primitives);
      if (meshes.has(signature)) node.mesh = meshes.get(signature);
      else meshes.set(signature, node.mesh);
    }
  }
  for (const key of ['extensionsUsed', 'extensionsRequired']) {
    doc[key] = [...new Set([...(doc[key] ?? []), 'KHR_mesh_quantization'])];
  }
  const product = { doc, data: Buffer.concat(chunks) };
  const result = assembleProducts(
    [product],
    doc.scenes[doc.scene].nodes.map((i) => [product, i]),
  );
  return result;
}
