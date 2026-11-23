async function hasGzipHeader(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader();
  const signature = [0x1f, 0x8b];
  let matched = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) return false;
      for (const byte of value) {
        if (byte !== signature[matched++]) return false;
        if (matched === signature.length) return true;
      }
    }
  } finally {
    void reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export async function packedBuffer(response: Response) {
  if (!response.ok) throw new Error('Unable to load ' + response.url);
  if (!response.body) return response.arrayBuffer();
  const [signature, data] = response.body.tee();
  const compressed = await hasGzipHeader(signature);
  const stream = compressed ? data.pipeThrough(new DecompressionStream('gzip')) : data;
  return new Response(stream).arrayBuffer();
}
