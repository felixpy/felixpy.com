import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

let decoder: typeof MeshoptDecoder | undefined;

function createDecoder() {
  const workerRequested =
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('studio-meshopt') === 'worker';
  if (!workerRequested || !MeshoptDecoder.supported || typeof Worker === 'undefined')
    return MeshoptDecoder;

  let poolActive = false;
  function stopPool() {
    poolActive = false;
    MeshoptDecoder.useWorkers(0);
    performance.mark('studio-meshopt-workers-fallback');
  }

  try {
    MeshoptDecoder.useWorkers(navigator.hardwareConcurrency >= 4 ? 2 : 1);
    poolActive = true;
    performance.mark('studio-meshopt-workers-start');
  } catch {
    stopPool();
    return MeshoptDecoder;
  }

  return {
    ...MeshoptDecoder,
    async decodeGltfBufferAsync(...args: Parameters<typeof MeshoptDecoder.decodeGltfBufferAsync>) {
      const decoding = MeshoptDecoder.decodeGltfBufferAsync(...args);
      if (!poolActive) return decoding;
      let timeout: ReturnType<typeof setTimeout> | undefined;
      const deadline = new Promise<undefined>((resolve) => {
        timeout = setTimeout(() => resolve(undefined), 10_000);
      });
      try {
        const result = await Promise.race([decoding, deadline]);
        if (result) return result;
        if (poolActive) stopPool();
        return MeshoptDecoder.decodeGltfBufferAsync(...args);
      } finally {
        clearTimeout(timeout);
      }
    },
  };
}

export function displayMeshoptDecoder() {
  return (decoder ??= createDecoder());
}
