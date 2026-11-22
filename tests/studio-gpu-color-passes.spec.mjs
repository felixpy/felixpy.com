import { expect, test } from '@playwright/test';
import { runInNewContext } from 'node:vm';
import { installProbe } from '../scripts/performance/studio-benchmark.mjs';

function measureColorPasses(quality, drawScene, { samples = 4, disjoint = false } = {}) {
  const document = {
    visibilityState: 'visible',
    addEventListener() {},
    timeline: { currentTime: 0 },
  };
  const window = {};
  class Observer {
    observe() {}
  }
  const install = runInNewContext(`(${installProbe.toString()})`, {
    window,
    document,
    EventTarget,
    performance,
    localStorage: { setItem() {} },
    MutationObserver: Observer,
    PerformanceObserver: Observer,
  });
  install({ quality, gpuTiming: true, gpuColorPasses: true });

  const beauty =
    quality === 'high'
      ? {
          isWebGLRenderTarget: true,
          width: 3840,
          height: 2160,
          samples,
          textures: [{}],
          depthBuffer: true,
          depthTexture: {},
          resolveDepthBuffer: true,
        }
      : null;
  let target = beauty;
  let gpuClock = 0;
  let open;
  let invalidate = false;
  const gl = {
    drawingBufferWidth: beauty?.width ?? 1920,
    drawingBufferHeight: beauty?.height ?? 1080,
    COLOR_BUFFER_BIT: 0x4000,
    DEPTH_BUFFER_BIT: 0x0100,
    NEAREST: 0x2600,
    QUERY_RESULT_AVAILABLE: 0x8867,
    getExtension: () => ({ TIME_ELAPSED_EXT: 0x88bf, GPU_DISJOINT_EXT: 0x8fbb }),
    getParameter: () => invalidate,
    createQuery: () => ({}),
    beginQuery(_kind, query) {
      if (open) throw new Error('Overlapping timer queries');
      open = query;
      query.start = gpuClock;
    },
    endQuery() {
      open.elapsed = gpuClock - open.start;
      open = undefined;
    },
    getQueryParameter(query, kind) {
      return kind === this.QUERY_RESULT_AVAILABLE ? true : query.elapsed * 1e6;
    },
    deleteQuery() {},
    blitFramebuffer() {
      gpuClock += 0.5;
    },
  };
  const camera = { isPerspectiveCamera: true, quaternion: { x: 0, y: 0, z: 0, w: 1 } };
  const scene = { isScene: true, getObjectByName: (name) => name === 'Felix Studio' };
  const renderer = {
    isWebGLRenderer: true,
    getContext: () => gl,
    getRenderTarget: () => target,
    getActiveMipmapLevel: () => 0,
    info: { render: { calls: 0, triangles: 0 } },
    renderBufferDirect(_camera, _scene, _geometry, material) {
      gpuClock += material.transparent ? 1 : 2;
    },
    render() {
      gpuClock += 0.25;
      drawScene({
        opaque: () => renderer.renderBufferDirect(camera, scene, {}, {}),
        translucent: () => renderer.renderBufferDirect(camera, scene, {}, { transparent: true }),
        offscreen: () => {
          target = {};
          renderer.renderBufferDirect(camera, scene, {}, {});
          target = beauty;
        },
        resolve: (mask = gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT) =>
          gl.blitFramebuffer(0, 0, 3840, 2160, 0, 0, 3840, 2160, mask, gl.NEAREST),
      });
    },
  };
  window.__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent('observe', { detail: renderer }));
  const sample = window.studioBench;
  sample.recording = true;
  sample.beginGpuTiming();
  for (let i = 0; i <= 17; i++) {
    document.timeline.currentTime += 7;
    renderer.render(scene, camera);
  }
  invalidate = disjoint;
  expect(sample.finishGpuTiming()).toBe(true);
  return sample;
}

test('native high split times actual beauty stages and color/depth resolve separately', () => {
  const sample = measureColorPasses('high', ({ opaque, translucent, offscreen, resolve }) => {
    offscreen();
    opaque();
    translucent();
    resolve();
  });
  expect(sample.mainColorGpu.durations).toEqual([5.75]);
  expect(sample.opaqueColorGpu.durations).toEqual([2]);
  expect(sample.translucentColorGpu.durations).toEqual([1]);
  expect(sample.beautyResolveGpu.durations).toEqual([0.5]);
  expect(sample.beautyResolveGpu.frameIndices).toEqual([17]);
  expect(sample.colorPassWork[0]).toMatchObject({
    offscreen: 1,
    offscreenDuringColor: 0,
    resolves: 1,
    reasons: [],
  });
});

test('high split discards ambiguous blits, off-target draws and disjoint samples', () => {
  const invalid = measureColorPasses('high', ({ opaque, translucent, offscreen, resolve }) => {
    opaque();
    translucent();
    offscreen();
    opaque();
    resolve();
    resolve();
    opaque();
  });
  expect(invalid.colorPassWork[0].reasons).toEqual([
    'multipleResolves',
    'offscreenDuringColor',
    'lateOpaque',
    'drawsAfterResolve',
  ]);
  expect(invalid.opaqueColorGpu).toMatchObject({ durations: [], discarded: 1 });
  expect(invalid.translucentColorGpu).toMatchObject({ durations: [], discarded: 1 });
  expect(invalid.beautyResolveGpu).toMatchObject({ durations: [], discarded: 1 });

  const missing = measureColorPasses('high', ({ opaque, translucent, resolve }) => {
    opaque();
    translucent();
    resolve(0x4000);
  });
  expect(missing.colorPassWork[0].reasons).toContain('missingResolve');
  expect(missing.colorPassWork[0].reasons).toContain('unexpectedBlits');
  expect(missing.beautyResolveGpu.durations).toEqual([]);

  const draw = ({ opaque, resolve }) => {
    opaque();
    resolve();
  };
  const unsupported = measureColorPasses('high', draw, { samples: 2 });
  expect(unsupported.colorPassWork[0].reasons).toEqual(['unsupportedTarget']);
  expect(unsupported.beautyResolveGpu.durations).toEqual([]);
  const disjoint = measureColorPasses('high', draw, { disjoint: true });
  expect(disjoint.colorPassWork[0].reasons).toEqual([]);
  expect(disjoint.beautyResolveGpu).toMatchObject({ durations: [], discarded: 1 });
});

test('low split keeps its default-framebuffer timings and counters', () => {
  const sample = measureColorPasses('low', ({ opaque, translucent, offscreen }) => {
    offscreen();
    opaque();
    translucent();
  });
  expect(sample.mainColorGpu.durations).toEqual([5.25]);
  expect(sample.opaqueColorGpu.durations).toEqual([2]);
  expect(sample.translucentColorGpu.durations).toEqual([1]);
  expect(sample.colorPassWork).toEqual([
    { opaque: 1, translucent: 1, offscreen: 1, lateOpaque: 0 },
  ]);
  expect(sample.beautyResolveGpu).toBeUndefined();
});
