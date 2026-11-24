import { assetUrl } from '../app/asset-url';
import { packedBuffer } from './packed-buffer';
import { partLibraryPath, unpackParts, type PartLibrary } from './blender-parts';

const loaded = new Map<string, Promise<void>>();
const installed = new Set<PartLibrary>();
const parts = new Map<string, ArrayBuffer>();

async function readParts(collection: PartLibrary) {
  const prefix = 'studio-parts-' + collection + '-';
  const mark = (phase: string) => performance.mark(prefix + phase);
  mark('fetch-start');
  const response = await fetch(assetUrl(partLibraryPath(collection)));
  mark('fetch-headers');
  const buffer = await packedBuffer(response);
  mark('inflate-end');

  mark('unpack-start');
  const restored = unpackParts(buffer);
  mark('unpack-end');
  for (const [name, bytes] of restored) parts.set(name, bytes);
  installed.add(collection);
  mark('installed');
}

export function hasParts(collection: PartLibrary) {
  return installed.has(collection);
}

export function loadParts(collection: PartLibrary) {
  const cached = loaded.get(collection);
  if (cached) return cached;
  const pending = readParts(collection).catch((error) => {
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
