import { packedBuffer } from './packed-buffer';

export async function lightingVolume(path: string, expectedBytes: number, signal: AbortSignal) {
  const response = await fetch(path, { signal });
  const data = new Uint8Array(await packedBuffer(response));
  if (!signal.aborted && data.length === expectedBytes) return data;
}
