import * as T from 'three';
import { packedBuffer } from './packed-buffer';

const keyCache = new WeakMap<T.BufferGeometry, string>();

export function surfaceKey(geometry: T.BufferGeometry) {
  const cached = keyCache.get(geometry);
  if (cached) return cached;
  const position = geometry.getAttribute('position'),
    normal = geometry.getAttribute('normal');
  if (!position || !normal || normal.count !== position.count) return '';
  let hash = 0x811c9dc5;
  const add = (n: number) => {
    hash = Math.imul(hash ^ n, 0x01000193);
  };
  for (let k = 0; k < 24; k++) {
    const i = Math.round((k * (position.count - 1)) / 23);
    for (const a of [position, normal]) {
      add(Math.round(a.getX(i) * 1e5));
      add(Math.round(a.getY(i) * 1e5));
      add(Math.round(a.getZ(i) * 1e5));
    }
    if (geometry.index) add(geometry.index.getX(Math.round((k * (geometry.index.count - 1)) / 23)));
  }
  const key = [position.count, geometry.index?.count ?? 0, hash >>> 0].join('-');
  keyCache.set(geometry, key);
  return key;
}

export function exportFinishGeometry(geometry: T.BufferGeometry) {
  const copy = geometry.clone(),
    position = copy.getAttribute('position');
  if (!position || !copy.getAttribute('normal')) return copy;
  copy.setAttribute(
    '_studioindex',
    new T.Float32BufferAttribute(
      Float32Array.from({ length: position.count }, (_, i) => i),
      1,
    ),
  );
  return copy;
}

export async function surfaceFinish(root: T.Object3D, signal: AbortSignal) {
  const response = await fetch('/media/models/surface-normals.gz', { signal });
  const buffer = await packedBuffer(response);
  const data = new DataView(buffer);
  if (data.getUint32(0) !== 0x534e5231) throw new Error('Invalid Blender normal adjustments');
  const patches = new Map<string, { count: number; start: number }>();
  const counts = new Set<number>();
  const utf8 = new TextDecoder();
  for (let pos = 4; pos < buffer.byteLength;) {
    const size = data.getUint8(pos),
      count = data.getUint32(pos + 1, true);
    const key = utf8.decode(new Uint8Array(buffer, pos + 5, size));
    const start = pos + 5 + size;
    patches.set(key, { count, start });
    counts.add(Number(key.split('-', 1)[0]));
    pos = start + count * 10;
  }
  const applied = new WeakSet<T.BufferGeometry>();
  return (subtree = root) => {
    if (signal.aborted) return;
    subtree.traverse((object) => {
      if (!(object instanceof T.Mesh) || applied.has(object.geometry)) return;
      const geometry = object.geometry;
      applied.add(geometry);
      if (!counts.has(geometry.getAttribute('position')?.count)) return;
      const patch = patches.get(surfaceKey(geometry));
      if (!patch) return;
      const normals = geometry.getAttribute('normal');
      for (let i = 0; i < patch.count; i++) {
        const pos = patch.start + 10 * i,
          index = data.getUint32(pos, true);
        if (index < normals.count)
          normals.setXYZ(
            index,
            data.getInt16(pos + 4, true) / 32767,
            data.getInt16(pos + 6, true) / 32767,
            data.getInt16(pos + 8, true) / 32767,
          );
      }
      normals.needsUpdate = true;
    });
  };
}
