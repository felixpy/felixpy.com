import * as T from 'three';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { packedBuffer } from './packed-buffer';
import { surfaceKey } from './surface-finish';

export function roomDetail(interior: T.Object3D, signal: AbortSignal) {
  const indices = new Map<string, T.BufferAttribute>();
  const counts = new Set<number>();
  const changed = new Map<T.BufferGeometry, T.BufferAttribute | null>();
  const checked = new WeakSet<T.BufferGeometry>();
  let reduced = false;
  let loading: Promise<void> | undefined;

  function apply() {
    if (!reduced || !indices.size || signal.aborted) return;
    interior.traverse((object) => {
      if (!(object instanceof T.Mesh) || Array.isArray(object.material)) return;
      const geometry = object.geometry as T.BufferGeometry;
      if (checked.has(geometry)) return;
      checked.add(geometry);
      if (geometry.drawRange.count !== Infinity || !counts.has(geometry.attributes.position?.count))
        return;
      const matching = indices.get(surfaceKey(geometry));
      if (!matching) return;
      changed.set(geometry, geometry.index);
      geometry.setIndex(matching);
    });
  }

  async function load() {
    const [buffer] = await Promise.all([
      fetch('/media/models/room-lod.gz', { signal }).then(packedBuffer),
      MeshoptDecoder.ready,
    ]);
    if (signal.aborted) return;
    const view = new DataView(buffer),
      decoder = new TextDecoder();
    if (view.getUint32(0) !== 0x4c4f4431) throw new Error('Invalid room detail mesh');
    for (let pos = 4; pos < buffer.byteLength;) {
      const keyLength = view.getUint8(pos),
        count = view.getUint32(pos + 1, true),
        bytes = view.getUint32(pos + 5, true);
      const key = decoder.decode(new Uint8Array(buffer, pos + 9, keyLength));
      const start = pos + 9 + keyLength;
      const vertexCount = Number(key.split('-', 1)[0]);
      const output = vertexCount > 65535 ? new Uint32Array(count) : new Uint16Array(count);
      MeshoptDecoder.decodeIndexBuffer(
        new Uint8Array(output.buffer),
        count,
        output.BYTES_PER_ELEMENT,
        new Uint8Array(buffer, start, bytes),
      );
      indices.set(key, new T.BufferAttribute(output, 1));
      counts.add(vertexCount);
      pos = start + bytes;
    }
    apply();
  }
  return {
    refresh: apply,
    select(low: boolean) {
      if (low === reduced) return;
      reduced = low;
      if (!low) {
        for (const [geometry, index] of changed) {
          geometry.setIndex(index);
          checked.delete(geometry);
        }
        changed.clear();
      } else {
        if (!loading)
          loading = load().catch(() => {
            loading = undefined;
          });
        apply();
      }
    },
  };
}
