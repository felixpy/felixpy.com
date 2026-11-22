import { unpackParts } from './blender-parts';

export type PartWorkerResult = {
  parts: Map<string, ArrayBuffer>;
  startTime: number;
  duration: number;
};

addEventListener('message', ({ data }: MessageEvent<ArrayBuffer>) => {
  try {
    const start = performance.now();
    const parts = unpackParts(data);
    const result: PartWorkerResult = {
      parts,
      startTime: performance.timeOrigin + start,
      duration: performance.now() - start,
    };
    postMessage(result, { transfer: [...parts.values()] });
  } catch (error) {
    postMessage({ error: error instanceof Error ? error.message : String(error) });
  }
});

postMessage('ready');
