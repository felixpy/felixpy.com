import type { PartWorkerResult } from './blender-parts.worker';

export function startPartWorker(mark: (phase: string) => void) {
  let worker: Worker;
  try {
    mark('worker-start');
    worker = new Worker(new URL('./blender-parts.worker.ts', import.meta.url), { type: 'module' });
  } catch {
    return;
  }

  let timeout: ReturnType<typeof setTimeout>;
  const ready = new Promise<boolean>((resolve) => {
    timeout = setTimeout(() => resolve(false), 10_000);
    worker.onmessage = () => {
      clearTimeout(timeout);
      mark('worker-ready');
      resolve(true);
    };
    const fail = (event: Event) => {
      event.preventDefault();
      clearTimeout(timeout);
      resolve(false);
    };
    worker.onerror = fail;
    worker.onmessageerror = fail;
  });

  return {
    async unpack(buffer: ArrayBuffer) {
      if (!(await ready)) throw new Error('Blender part worker did not start');
      return new Promise<PartWorkerResult>((resolve, reject) => {
        const fail = (message: string) => reject(new Error(message));
        timeout = setTimeout(() => fail('Blender part worker did not respond'), 10_000);
        worker.onmessage = ({ data }: MessageEvent<PartWorkerResult | { error: string }>) => {
          clearTimeout(timeout);
          mark('worker-receive');
          if ('error' in data) fail(data.error);
          else resolve(data);
        };
        const handleFailure = (event: Event) => {
          event.preventDefault();
          clearTimeout(timeout);
          fail('Blender part worker failed');
        };
        worker.onerror = handleFailure;
        worker.onmessageerror = handleFailure;
        mark('worker-send');
        worker.postMessage(buffer, [buffer]);
      });
    },
    dispose() {
      clearTimeout(timeout);
      worker.terminate();
    },
  };
}
