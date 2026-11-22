import { packedBuffer } from './packed-buffer';
import { partLibraryPath, unpackParts, type PartLibrary } from './blender-parts';
import { startPartWorker } from './blender-parts-worker';

const loaded = new Map<string, Promise<void>>();
const parts = new Map<string, ArrayBuffer>();

async function readParts(collection: PartLibrary) {
  const prefix = 'studio-parts-' + collection + '-';
  const mark = (phase: string) => performance.mark(prefix + phase);
  const workerRequested =
    collection === 'studio' &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('studio-parts') === 'worker';
  const worker = workerRequested ? startPartWorker(mark) : undefined;
  if (workerRequested && !worker) mark('worker-fallback');

  async function download() {
    mark('fetch-start');
    const response = await fetch(partLibraryPath(collection));
    mark('fetch-headers');
    const buffer = await packedBuffer(response);
    mark('inflate-end');
    return buffer;
  }

  try {
    let buffer = await download();
    mark('unpack-start');
    let restored: Map<string, ArrayBuffer> | undefined;
    if (worker) {
      const inputLength = buffer.byteLength;
      try {
        const { parts, startTime, duration } = await worker.unpack(buffer);
        restored = parts;
        performance.measure(prefix + 'worker-unpack', {
          start: Math.max(0, startTime - performance.timeOrigin),
          duration,
        });
      } catch {
        mark('worker-fallback');
        if (inputLength && !buffer.byteLength) buffer = await download();
      }
    }
    restored ??= unpackParts(buffer);
    mark('unpack-end');
    for (const [name, bytes] of restored) parts.set(name, bytes);
    mark('installed');
  } finally {
    worker?.dispose();
  }
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
