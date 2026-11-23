import { expect, test } from '@playwright/test';
import { gzipSync } from 'node:zlib';
import { packedBuffer } from '../src/scene/packed-buffer';

function chunked(chunks: number[][]) {
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(Uint8Array.from(chunk));
        controller.close();
      },
    }),
  );
}

test('packed models accept split gzip signatures and preserve short or uncompressed assets', async () => {
  const raw = Uint8Array.of(0, 255, 25, 31, 139, 7);
  const gzip = gzipSync(raw);
  const compressed = chunked([[], [gzip[0]], [], [gzip[1]], Array.from(gzip.subarray(2))]);
  expect(new Uint8Array(await packedBuffer(compressed))).toEqual(raw);
  for (const chunks of [[], [[], []], [[31]], [[31], [], [138, 4]], [[0], [31, 139]]]) {
    expect(Array.from(new Uint8Array(await packedBuffer(chunked(chunks))))).toEqual(chunks.flat());
  }
  expect((await packedBuffer(new Response(null))).byteLength).toBe(0);
  await expect(packedBuffer(chunked([[31, 139, 8]]))).rejects.toThrow();
});

test('interrupting a streamed asset rejects the partial download', async () => {
  const source = new Error('Connection interrupted');
  let controller: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start(stream) {
      controller = stream;
      stream.enqueue(Uint8Array.of(0x1f, 0x8b));
    },
  });
  const result = packedBuffer(new Response(body));
  controller!.error(source);
  await expect(result).rejects.toBe(source);
});
