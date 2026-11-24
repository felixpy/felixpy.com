export type PartLibrary = 'studio' | 'workshop' | 'pc-hero';

const partLibraryFiles: Record<PartLibrary, string> = {
  studio: 'room-parts.bpk',
  workshop: 'workshop-tools.bpk',
  'pc-hero': 'pc-hero.bpk',
};

export function partLibraryPath(collection: PartLibrary) {
  return '/media/models/' + partLibraryFiles[collection];
}

export function meshStreams(bytes: Uint8Array) {
  const header = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length < 52 || header.getUint32(0) !== 0x424d5331)
    throw new Error('Invalid packed Blender mesh');
  const vertices = header.getUint32(4, true);
  const indices = header.getUint32(8, true);
  const indexOffset = 52 + vertices * 16;
  if (indexOffset + indices * 2 !== bytes.length) throw new Error('Incomplete packed Blender mesh');
  return [
    { offset: 52, count: vertices, fields: 8 },
    { offset: indexOffset, count: indices, fields: 1 },
  ];
}

function restoreMesh(bytes: Uint8Array) {
  const streams = meshStreams(bytes);
  const buffer = new ArrayBuffer(bytes.length);
  new Uint8Array(buffer, 0, 52).set(bytes.subarray(0, 52));
  const output = new DataView(buffer);
  for (const { offset, count, fields } of streams) {
    for (let field = 0; field < fields; field++) {
      const lowBytes = offset + field * 2 * count;
      const highBytes = lowBytes + count;
      let value = 0;
      let target = offset + field * 2;
      for (let i = 0; i < count; i++, target += fields * 2) {
        const code = bytes[lowBytes + i] | (bytes[highBytes + i] << 8);
        value = (value + ((code >>> 1) ^ -(code & 1))) & 0xffff;
        output.setUint16(target, value, true);
      }
    }
  }
  return buffer;
}

export function unpackParts(buffer: ArrayBuffer) {
  const view = new DataView(buffer);
  const version = buffer.byteLength >= 4 ? view.getUint32(0) : 0;
  if (version !== 0x42504b31 && version !== 0x42504b32)
    throw new Error('Invalid Blender mesh library');
  const parts = new Map<string, ArrayBuffer>();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  for (let offset = 4; offset < buffer.byteLength;) {
    if (buffer.byteLength - offset < 5) throw new Error('Incomplete Blender part header');
    const length = view.getUint8(offset);
    const size = view.getUint32(offset + 1, true);
    const start = offset + 5 + length;
    const end = start + size;
    if (!length || !size || end > buffer.byteLength) throw new Error('Incomplete Blender part');
    const name = decoder.decode(new Uint8Array(buffer, offset + 5, length));
    if (parts.has(name)) throw new Error('Duplicate Blender part ' + name);
    const bytes =
      version === 0x42504b32
        ? restoreMesh(new Uint8Array(buffer, start, size))
        : buffer.slice(start, end);
    parts.set(name, bytes);
    offset = end;
  }
  return parts;
}
