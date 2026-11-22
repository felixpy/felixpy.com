import { packedBuffer } from './packed-buffer';
import { partLibraryPath, unpackParts } from './blender-parts';

const loaded = new Map<string, Promise<void>>();
const parts = new Map<string, ArrayBuffer>();

export function loadParts(collection: 'studio' | 'workshop') {
  const cached = loaded.get(collection);
  if (cached) return cached;
  const pending = fetch(partLibraryPath(collection))
    .then(packedBuffer)
    .then((buffer) => {
      for (const [name, bytes] of unpackParts(buffer)) parts.set(name, bytes);
    })
    .catch((error) => {
      loaded.delete(collection);
      throw error;
    });
  loaded.set(collection, pending);
  return pending;
}

export function meshBytes(name: string) {
  const data = parts.get(name);
  if (!data) throw new Error('Missing Blender part ' + name);
  return data;
}
