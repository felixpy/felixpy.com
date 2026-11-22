import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { gzipSync } from 'node:zlib';
import { chromium } from '@playwright/test';
import { preview } from 'vite';
import { startCpuTelemetry } from './studio-cpu-telemetry.mjs';
import { startWddmTelemetry } from './studio-wddm.mjs';

const profiles = {
  '4k': { width: 3840, height: 2160, quality: 'high', adapter: '4090' },
  '1440p': { width: 2560, height: 1440, quality: 'high', adapter: '4090' },
  'uhd-adaptive': { width: 1920, height: 1080, quality: 'low', adapter: 'intel' },
  'uhd-native': { width: 1920, height: 1080, quality: 'low', adapter: 'intel', forceNative: true },
};
const adapterNames = {
  4090: /NVIDIA.*4090/i,
  intel: /\bIntel\b.*\bUHD Graphics 770\b/i,
  current:
    /^(?!.*(?:swiftshader|llvmpipe|softpipe|software rasterizer|microsoft basic render|\bwarp\b)).+$/i,
};
const roomRoutes = {
  desk: null,
  case: {
    target: 'ROG Hyperion GR701 chassis',
    mode: 'case',
    caption: 'Look closer at the PC case',
  },
  window: { target: 'Window glass', mode: 'window', turn: -430 },
  workbench: { target: 'Workbench top', mode: 'bench', turn: 309, pitch: 17 },
  cabinet: {
    target: 'NIKKOR Z 135mm f/1.8 S Plena · cabinet mount',
    mode: 'case',
    caption: 'Explore the collection cabinet',
    turn: -865,
  },
};
const weatherCodes = { clear: 0, overcast: 3, rain: 61, snow: 71 };
const weatherLabels = { clear: '晴', overcast: '阴', rain: '雨', snow: '雪' };
const experiments = {
  '--deferred-books': ['studio-startup', 'deferred-books'],
  '--warm-preview': ['studio-preview', 'warm'],
  '--warm-oled': ['studio-preview', 'oled'],
  '--staged-preview-textures': ['studio-preview-textures', 'staged'],
  '--input-priority-textures': ['studio-preview-textures', 'input-priority'],
  '--in-view-preview-uploads': ['studio-preview-upload-order', 'in-view'],
  '--warm-buffers': ['studio-buffers', 'warm'],
  '--worker-parts': ['studio-parts', 'worker'],
  '--worker-meshopt': ['studio-meshopt', 'worker'],
  '--priority-rear': ['studio-rear', 'priority'],
  '--vitrine-timing': ['studio-vitrine-timing', 'on'],
  '--early-rear': ['studio-rear', 'early'],
  '--native-low': ['studio-low', 'native'],
  '--sliced-build': ['studio-build', 'sliced'],
  '--photo-fasteners': ['studio-photo-fasteners', 'instanced'],
  '--preload-details': ['studio-details', 'preload'],
  '--simple-low': ['studio-low-shading', 'simple'],
  '--fused-output': ['studio-output', 'fused'],
  '--legacy-output': ['studio-output', 'legacy'],
  '--stable-effects': ['studio-effects', 'stable'],
  '--warm-waterfront': ['studio-waterfront', 'warm'],
  '--cold-waterfront': ['studio-waterfront', 'cold'],
  '--sky-clear': ['studio-sky', 'clear'],
  '--window-scissor': ['studio-window-clip', 'scissor'],
  '--warm-ferry': ['studio-ferry', 'warm'],
  '--eager-water-motion': ['studio-water-motion', 'eager'],
  '--window-only-water': ['studio-water-motion', 'window'],
  '--bitmap-images': ['studio-images', 'bitmap'],
  '--atlas-detail-on-inspect': ['studio-atlas-detail', 'on-inspect'],
  '--incremental-warmup': ['studio-warmup', 'incremental'],
  '--paced-warmup': ['studio-warmup', 'paced'],
  '--catch-up-warmup': ['studio-warmup', 'catch-up'],
  '--isolated-catch-up': ['studio-warmup', 'isolated-catch-up'],
  '--resident-warmup-maps': ['studio-warmup-maps', 'resident'],
  '--live-front-warmup': ['studio-warmup-live', 'front'],
  '--warm-workbench': ['studio-warmup', 'workbench'],
  '--adaptive-warmup': ['studio-warmup', 'adaptive'],
  '--culled-lights': ['studio-lighting', 'culled'],
  '--lean-lighting': ['studio-light-kernel', 'lean'],
  '--culled-all-lights': ['studio-lighting', 'culled-all'],
  '--matte-surfaces': ['studio-lighting', 'matte'],
  '--depth-prefill': ['studio-depth-prefill', 'coarse'],
  '--wide-depth-prefill': ['studio-depth-prefill', 'wide'],
  '--shared-reflections': ['studio-reflections', 'shared'],
  '--legacy-loader': ['studio-loader', 'legacy'],
  '--present-witness': ['studio-present-witness', 'roi'],
  '--merge-first': ['studio-batching', 'merge-first'],
  '--transform-first': ['studio-batching', 'transform-first'],
};
const usage = `Usage: node scripts/performance/studio-benchmark.mjs [profiles] [run IDs] [options]

Profiles: 4k (default), 1440p, uhd-adaptive, uhd-native
List profiles or positive run IDs with commas. Run ID defaults to 1.
Example: node scripts/performance/studio-benchmark.mjs 4k,uhd-adaptive 1,2,3
Use --current-adapter to keep the selected resolution and quality on Chrome's active hardware GPU.
Use --loader-profile to profile startup CPU work through loader removal.
Use --steady-profile to profile CPU work during the warmed desk turn.
Use --gpu-timing to sample main-color GPU work during the final steady route, including any depth prefill.
Add --gpu-panorama to alternate whole-room queries with queries around the panorama draw.
Add --gpu-downstream to also time GTAO and final output on the high-quality path.
Add --gpu-low-grade to time the low-quality framebuffer copy and room-grade draw.
Add --gpu-depth-prepass to alternate inclusive and split depth/color samples on the low-quality path.
Add --gpu-color-passes to alternate inclusive and opaque/translucent draw samples on the low-quality path.
Use --opaque-near-first to measure a front-to-back opaque draw order in the replay.
Use --draw-calls to record WebGL indexed and multi-draw calls during the final steady route.
Use --draw-inventory to attribute main-color draws to objects in up to three steady route frames.
Use --wddm-luid=<high,low> to sample the specified Windows adapter during the steady route.
Use --cpu-telemetry to sample Windows logical processors from browser launch through measurement.
Use --repeat-desk to prime the shaders and geometry with one matched desk turn before sampling.
Use --seconds=<duration> to set the measured steady desk route duration (default 12).
Use --route=<${Object.keys(roomRoutes).join('|')}> and --weather=<${Object.keys(weatherCodes).join('|')}> to replay room views.
Use --day to start in daylight. Combine with --weather=overcast for the Shanghai 5120-pixel panorama.
Use --loader-trace to capture compositor events and screenshots during loading.
Use --startup to exercise the first drag as soon as the loader disappears.
Add --startup-spans to record long renderer calls during loading and the first ten seconds of input.
Use --warmup-work to count program readiness queries and texture uploads during room preparation.
Add --in-view-preview-uploads to prioritize visible textures with an existing preview staging mode.
Add --route=workbench to turn toward the workbench on that first drag.
Combine --loader-profile and --startup to profile through the first ten seconds after the drag.
Add --full-room to wait for rear asset readiness on builds that report it.
Set --input-delay-ms=<milliseconds> to wait before the first drag.
Use --screenshot to save a full-viewport image after sampling.
Use --slow-draws to attribute individual draw calls taking longer than 50 ms.
Use --texture-uploads to record uploads of at least 10 ms without timing every draw.
Use --check-shaders to report shader compilation errors in production builds.
Use --warm to prime the origin in the same browser context before measuring a reload.
Use --dist=<directory> to serve an alternate production build.
Experiment switches: ${Object.keys(experiments).join(', ')}.
Build first with npm run build. Named adapter checks use installed Chrome on Windows and ANGLE D3D11.
On other operating systems, --current-adapter leaves the graphics backend to installed Chrome.
Local results are grouped by commit. Long Windows paths use a shorter filename with the same run ID.`;

function options(args) {
  const captured = new Set(args.filter((arg) => arg.startsWith('--')));
  const positional = args.filter((arg) => !captured.has(arg));
  const names = (positional[0] ?? '4k').split(',');
  const ids = (positional[1] ?? '1').split(',');
  const currentAdapter = captured.delete('--current-adapter');
  const captureProfile = captured.delete('--loader-profile');
  const steadyProfile = captured.delete('--steady-profile');
  const gpuTiming = captured.delete('--gpu-timing');
  const gpuPanorama = captured.delete('--gpu-panorama');
  const gpuDownstream = captured.delete('--gpu-downstream');
  const gpuLowGrade = captured.delete('--gpu-low-grade');
  const gpuDepthPrepass = captured.delete('--gpu-depth-prepass');
  const gpuColorPasses = captured.delete('--gpu-color-passes');
  const opaqueNearFirst = captured.delete('--opaque-near-first');
  const drawCalls = captured.delete('--draw-calls');
  const drawInventory = captured.delete('--draw-inventory');
  const cpuTelemetry = captured.delete('--cpu-telemetry');
  const wddmArgument = [...captured].find((arg) => arg.startsWith('--wddm-luid='));
  captured.delete(wddmArgument);
  const wddmLuid = wddmArgument?.slice('--wddm-luid='.length);
  const loaderTrace = captured.delete('--loader-trace');
  const startup = captured.delete('--startup');
  const startupSpans = captured.delete('--startup-spans');
  const warmupWork = captured.delete('--warmup-work');
  const fullRoom = captured.delete('--full-room');
  const delayArgument = [...captured].find((arg) => arg.startsWith('--input-delay-ms='));
  captured.delete(delayArgument);
  const inputDelayMs = delayArgument ? Number(delayArgument.slice('--input-delay-ms='.length)) : 0;
  const screenshot = captured.delete('--screenshot');
  const slowDraws = captured.delete('--slow-draws');
  const textureUploads = captured.delete('--texture-uploads');
  const checkShaders = captured.delete('--check-shaders');
  const warm = captured.delete('--warm');
  const repeatDesk = captured.delete('--repeat-desk');
  const day = captured.delete('--day');
  const routeArgument = [...captured].find((arg) => arg.startsWith('--route='));
  const weatherArgument = [...captured].find((arg) => arg.startsWith('--weather='));
  captured.delete(routeArgument);
  captured.delete(weatherArgument);
  const route = routeArgument ? routeArgument.slice('--route='.length) : 'desk';
  const weather = weatherArgument ? weatherArgument.slice('--weather='.length) : 'clear';
  const secondsArgument = [...captured].find((arg) => arg.startsWith('--seconds='));
  captured.delete(secondsArgument);
  const seconds = secondsArgument ? Number(secondsArgument.slice('--seconds='.length)) : 12;
  const selected = Object.keys(experiments).filter((flag) => captured.delete(flag));
  const distArgument = [...captured].find((arg) => arg.startsWith('--dist='));
  captured.delete(distArgument);
  const dist = distArgument ? distArgument.slice('--dist='.length) : 'dist';
  if (
    positional.length > 2 ||
    captured.size ||
    !dist ||
    ((fullRoom || delayArgument || startupSpans) && !startup) ||
    !Number.isSafeInteger(inputDelayMs) ||
    inputDelayMs < 0 ||
    (captureProfile && screenshot) ||
    (gpuTiming && (captureProfile || steadyProfile || startup || loaderTrace || slowDraws)) ||
    (gpuPanorama && !gpuTiming) ||
    (gpuDownstream &&
      (!gpuTiming || gpuPanorama || names.some((name) => profiles[name]?.quality !== 'high'))) ||
    (gpuLowGrade && (!gpuTiming || names.some((name) => profiles[name]?.quality !== 'low'))) ||
    (gpuDepthPrepass &&
      (!gpuTiming || gpuPanorama || names.some((name) => profiles[name]?.quality !== 'low'))) ||
    (gpuColorPasses &&
      (!gpuTiming ||
        gpuPanorama ||
        gpuDepthPrepass ||
        names.some((name) => profiles[name]?.quality !== 'low'))) ||
    (drawCalls && (captureProfile || steadyProfile || startup || loaderTrace)) ||
    (drawInventory &&
      (captureProfile ||
        steadyProfile ||
        startup ||
        loaderTrace ||
        gpuTiming ||
        drawCalls ||
        slowDraws)) ||
    (wddmArgument &&
      (process.platform !== 'win32' ||
        captureProfile ||
        startup ||
        loaderTrace ||
        !/^-?\d+,\d+$/.test(wddmLuid))) ||
    (loaderTrace && (captureProfile || startup || screenshot || slowDraws)) ||
    (steadyProfile && (captureProfile || loaderTrace || startup || slowDraws)) ||
    ((repeatDesk || secondsArgument) && (captureProfile || loaderTrace || startup)) ||
    (route !== 'desk' && (loaderTrace || (captureProfile && !startup))) ||
    (startup && route !== 'desk' && route !== 'workbench') ||
    !Object.hasOwn(roomRoutes, route) ||
    !Object.hasOwn(weatherCodes, weather) ||
    !Number.isSafeInteger(seconds) ||
    seconds < 1 ||
    names.some((name) => !Object.hasOwn(profiles, name)) ||
    ids.some((id) => !/^[1-9]\d*$/.test(id) || !Number.isSafeInteger(Number(id))) ||
    new Set(names).size !== names.length ||
    new Set(ids).size !== ids.length ||
    new Set(selected.map((flag) => experiments[flag][0])).size !== selected.length
  )
    throw new Error(usage);
  return {
    names,
    runs: ids.map(Number),
    currentAdapter,
    captureProfile,
    steadyProfile,
    gpuTiming,
    gpuPanorama,
    gpuDownstream,
    gpuLowGrade,
    gpuDepthPrepass,
    gpuColorPasses,
    opaqueNearFirst,
    drawCalls,
    drawInventory,
    cpuTelemetry,
    wddmLuid,
    loaderTrace,
    startup,
    startupSpans,
    warmupWork,
    fullRoom,
    inputDelayMs,
    screenshot,
    slowDraws,
    textureUploads,
    checkShaders,
    warm,
    repeatDesk,
    day,
    seconds,
    route,
    weather,
    selected,
    dist,
  };
}

function browserArgs(adapter) {
  const args = ['--enable-gpu', '--mute-audio'];
  if (process.platform === 'win32') args.unshift('--use-angle=d3d11');
  else if (adapter !== 'current') throw new Error('Use --current-adapter outside Windows.');
  if (adapter === 'current') return args;
  let luid = adapter === 'intel' ? process.env.INTEL_LUID : process.env.DISCRETE_LUID;
  if (adapter === 'intel' && !luid) {
    const query =
      "Get-ChildItem 'HKLM:/SOFTWARE/Microsoft/DirectX' | Get-ItemProperty | Where-Object { $_.Description -match '\\bIntel\\b.*\\bUHD Graphics 770\\b' } | Select-Object -First 1 -ExpandProperty AdapterLuid";
    const id = execFileSync('powershell.exe', ['-NoProfile', '-Command', query], {
      encoding: 'utf8',
    }).trim();
    if (!/^\d+$/.test(id))
      throw new Error('UHD 770 adapter unavailable. Set INTEL_LUID for this Windows boot.');
    const value = BigInt(id);
    luid = `${value >> 32n},${value & 0xffffffffn}`;
  }
  if (luid && !/^-?\d+,\d+$/.test(luid))
    throw new Error('An adapter LUID requires high,low decimal integers.');
  if (luid) args.push('--use-adapter-luid=' + luid);
  return args;
}

function installProbe({
  quality,
  forceNative,
  drawCalls,
  drawInventory,
  startup,
  startupSpans,
  warmupWork,
  slowDraws,
  textureUploads,
  checkShaders,
  gpuTiming,
  gpuPanorama,
  gpuDownstream,
  gpuLowGrade,
  gpuDepthPrepass,
  gpuColorPasses,
  opaqueNearFirst,
  day,
  weather,
}) {
  performance.setResourceTimingBufferSize(1000);
  localStorage.setItem(
    'felix-studio-v1',
    JSON.stringify({
      quality,
      automaticQuality: false,
      night: !day,
      weather,
      reducedMotion: false,
      rainAudio: false,
    }),
  );
  const sample = (window.studioBench = {
    roomFrames: [],
    submissions: [],
    rotations: [],
    ...(gpuTiming && { cameraYaws: [] }),
    loaderFrames: [],
    loaderProgress: [],
    resolutions: {},
    longTasks: [],
    ...(startup && { firstDrag: { frames: [] } }),
    ...(startupSpans && { startupSpans: [] }),
    ...(slowDraws && { slowDraws: [] }),
    ...(drawInventory && { drawInventory: [] }),
    ...((slowDraws || textureUploads) && { slowTextureUploads: [] }),
    recording: false,
    visible: document.visibilityState,
    visibilityChanged: false,
  });
  document.addEventListener('visibilitychange', () => {
    sample.visibilityChanged = true;
  });
  new PerformanceObserver((list) => {
    for (const task of list.getEntries()) sample.longTasks.push([task.startTime, task.duration]);
  }).observe({ type: 'longtask', buffered: true });
  const observer = new MutationObserver(() => {
    const loader = document.querySelector('.studio-loading');
    const attached = !!loader;
    const meter = loader?.querySelector('progress');
    if (meter && sample.loaderProgress.at(-1)?.value !== meter.value)
      sample.loaderProgress.push({ time: performance.now(), value: meter.value });
    if (sample.loaderStart == null && attached) {
      sample.loaderStart = performance.now();
      function record() {
        if (sample.loaderEnd != null) return;
        sample.loaderFrames.push(performance.now());
        requestAnimationFrame(record);
      }
      requestAnimationFrame(record);
    } else if (sample.loaderStart != null && !attached) {
      sample.loaderEnd = performance.now();
      observer.disconnect();
    }
  });
  observer.observe(document, { subtree: true, childList: true, attributeFilter: ['value'] });

  function attachWarmupWork(renderer) {
    const gl = renderer.getContext();
    const completion = gl.getExtension('KHR_parallel_shader_compile')?.COMPLETION_STATUS_KHR;
    const stages = {
      'studio-room-preview-start': 'preview',
      'studio-room-shader-warm-start': 'shader',
      'studio-room-shader-catch-up-start': 'catchUp',
      'studio-room-shader-warm-end': 'finalPreparation',
      'studio-room-full-draw-start': 'firstFullDraw',
      'studio-room-shaded': 'rear',
    };
    const report = (sample.warmupWork = { parallelCompile: completion !== undefined, phases: [] });
    const ids = new WeakMap();
    let nextId = 0;
    function programId(program) {
      if (!ids.has(program)) ids.set(program, ++nextId);
      return ids.get(program);
    }
    function begin(stage, start) {
      const phase = { stage, start, work: {}, programs: {} };
      report.phases.push(phase);
      return phase;
    }
    let phase = begin('beforePreview', performance.now());
    let shaded = false;
    let rear = false;
    const mark = performance.mark;
    performance.mark = function (...args) {
      const entry = mark.apply(this, args);
      if (!phase) return entry;
      const [name] = args;
      if (name === 'studio-room-shaded') shaded = true;
      if (name === 'studio-room-rear-ready') rear = true;
      const stage = stages[name];
      if (stage || (shaded && rear)) {
        phase.end = entry.startTime;
        phase = shaded && rear ? undefined : begin(stage, entry.startTime);
      }
      return entry;
    };
    function track(phase, name, duration) {
      const entry = (phase.work[name] ??= { calls: 0, total: 0, max: 0 });
      entry.calls++;
      entry.total += duration;
      entry.max = Math.max(entry.max, duration);
    }
    function measureCall(owner, method, category, after) {
      const original = owner[method];
      owner[method] = function (...args) {
        const active = phase;
        const name = active && category(args);
        if (!name) return original.apply(this, args);
        const start = performance.now();
        const result = original.apply(this, args);
        track(active, name, performance.now() - start);
        after?.(active, args, result, start);
        return result;
      };
    }
    measureCall(renderer, 'compile', () => 'compile');
    const renderBuffer = renderer.renderBufferDirect;
    renderer.renderBufferDirect = function (camera, scene, geometry, material, object, group) {
      if (phase?.stage !== 'firstFullDraw')
        return renderBuffer.call(this, camera, scene, geometry, material, object, group);

      const active = phase;
      const result = renderBuffer.call(this, camera, scene, geometry, material, object, group);
      const { currentProgram } = renderer.properties.get(material);
      const id = ids.get(currentProgram?.program);
      const entry = active.programs[id];
      if (entry && !entry.firstDraw) {
        const path = [];
        for (let node = object; node; node = node.parent) {
          if (node.name) path.unshift(node.name);
        }
        entry.firstDraw = { path, material: material.name, type: currentProgram.type };
      }
      return result;
    };
    measureCall(renderer, 'initTexture', ([texture]) => {
      const properties = renderer.properties.has(texture) && renderer.properties.get(texture);
      return properties?.__webglTexture && properties.__version === texture.version
        ? 'initResidentTexture'
        : 'initTexture';
    });
    measureCall(
      gl,
      'linkProgram',
      () => 'link',
      (active, [program], _, start) => {
        const entry = (active.programs[programId(program)] ??= {});
        entry.linkAt = start;
      },
    );
    measureCall(
      gl,
      'getProgramParameter',
      ([, parameter]) =>
        parameter === completion ? 'completion' : parameter === gl.LINK_STATUS ? 'linkStatus' : '',
      (active, [program, parameter], ready, start) => {
        if (parameter !== completion) return;
        const entry = (active.programs[programId(program)] ??= {});
        entry.polls = (entry.polls ?? 0) + 1;
        entry.firstPollAt ??= start;
        entry.lastPollAt = start;
        if (ready) entry.readyAt ??= start;
        else entry.pending = (entry.pending ?? 0) + 1;
      },
    );
    for (const name of [
      'texImage2D',
      'texSubImage2D',
      'texImage3D',
      'texSubImage3D',
      'compressedTexImage2D',
      'compressedTexSubImage2D',
      'compressedTexImage3D',
      'compressedTexSubImage3D',
    ])
      measureCall(gl, name, () => 'textureTransfer');
  }

  function attachGpuTiming(renderer) {
    const gl = renderer.getContext();
    const timer = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    if (!timer) return;
    const pending = [];
    const makeTiming = () => ({ durations: [], frameIndices: [], discarded: 0 });
    const timings = { main: (sample.mainColorGpu = makeTiming()) };
    if (gpuPanorama) timings.panorama = sample.panoramaGpu = makeTiming();
    if (gpuDownstream) timings.downstream = sample.downstreamGpu = makeTiming();
    if (gpuLowGrade) timings.grade = sample.lowGradeGpu = makeTiming();
    if (gpuDepthPrepass) {
      timings.depth = sample.depthOnlyGpu = makeTiming();
      timings.color = sample.colorAfterDepthGpu = makeTiming();
    }
    if (gpuColorPasses) {
      timings.opaque = sample.opaqueColorGpu = makeTiming();
      timings.translucent = sample.translucentColorGpu = makeTiming();
    }
    let active = false;
    let openQuery;

    function poll() {
      if (!pending.length) return true;
      if (gl.getParameter(timer.GPU_DISJOINT_EXT)) {
        for (const { query, result } of pending.splice(0)) {
          result.discarded++;
          gl.deleteQuery(query);
        }
        return true;
      }
      while (pending.length && gl.getQueryParameter(pending[0].query, gl.QUERY_RESULT_AVAILABLE)) {
        const { query, result, index } = pending.shift();
        result.durations.push(gl.getQueryParameter(query, gl.QUERY_RESULT) / 1e6);
        result.frameIndices.push(index);
        gl.deleteQuery(query);
      }
      return pending.length === 0;
    }

    sample.beginGpuTiming = () => {
      active = true;
    };
    sample.finishGpuTiming = () => {
      active = false;
      if (openQuery) end(openQuery, true);
      return poll();
    };
    const splitFrame = () => active && sample.roomFrames.length % 34 === 17;
    const panoramaFrame = () => Boolean(timings.panorama) && splitFrame();
    const splitDepthFrame = () => Boolean(timings.depth) && splitFrame();
    const colorPassFrame = () => Boolean(timings.opaque) && splitFrame();
    function end(query, discard = false) {
      if (openQuery !== query) return;
      gl.endQuery(timer.TIME_ELAPSED_EXT);
      openQuery = undefined;
      if (discard) {
        query.result.discarded++;
        gl.deleteQuery(query.query);
      } else pending.push(query);
    }
    return {
      panoramaFrame,
      splitDepthFrame,
      colorPassFrame,
      begin(stage = 'main', index = sample.roomFrames.length) {
        const result = timings[stage];
        const selected =
          stage === 'downstream' ||
          stage === 'grade' ||
          (sample.roomFrames.length % 17 === 0 &&
            (stage === 'main'
              ? !panoramaFrame() && !splitDepthFrame() && !colorPassFrame()
              : splitFrame()));
        if (!active || !result || openQuery || !selected) return null;
        poll();
        const query = gl.createQuery();
        if (!query) return null;
        gl.beginQuery(timer.TIME_ELAPSED_EXT, query);
        openQuery = { query, result, index };
        return openQuery;
      },
      end,
    };
  }

  window.__THREE_DEVTOOLS__ = new EventTarget();
  window.__THREE_DEVTOOLS__.addEventListener('observe', ({ detail: renderer }) => {
    if (!renderer.isWebGLRenderer) return;
    sample.renderer = renderer;
    if (warmupWork) attachWarmupWork(renderer);
    if (opaqueNearFirst)
      renderer.setOpaqueSort(
        (a, b) =>
          a.groupOrder - b.groupOrder ||
          a.renderOrder - b.renderOrder ||
          a.z - b.z ||
          a.material.id - b.material.id ||
          a.id - b.id,
      );
    const drag = sample.firstDrag;
    function recordStartupSpan(name, start, target) {
      const duration = performance.now() - start;
      if (duration < 16 || start >= (drag.move ?? Infinity) + 10000) return;
      sample.startupSpans.push({
        name,
        start,
        duration,
        ...(target && { target: [target.width, target.height] }),
      });
    }
    if (startupSpans) {
      for (const name of ['compile', 'initTexture']) {
        const execute = renderer[name];
        renderer[name] = function (...args) {
          const start = performance.now();
          const target = renderer.getRenderTarget();
          try {
            return execute.apply(this, args);
          } finally {
            recordStartupSpan(name, start, target);
          }
        };
      }
    }
    let yaw;
    if (drag) {
      renderer.domElement.addEventListener(
        'pointerdown',
        (event) => {
          drag.press = event.timeStamp;
          drag.pressDispatch = performance.now();
          drag.yawBefore = yaw;
        },
        { capture: true, once: true },
      );
      renderer.domElement.addEventListener(
        'pointermove',
        (event) => {
          if (drag.press == null || drag.move != null || !(event.buttons & 1)) return;
          drag.move = event.timeStamp;
          drag.moveDispatch = performance.now();
        },
        { capture: true },
      );
    }
    if (forceNative) {
      const setRatio = renderer.setPixelRatio.bind(renderer);
      renderer.setPixelRatio = () => setRatio(1);
      setRatio(1);
    }
    if (slowDraws || textureUploads) {
      const gl = renderer.getContext();
      for (const name of ['texImage2D', 'texSubImage2D', 'texImage3D', 'texSubImage3D']) {
        const upload = gl[name];
        gl[name] = function (...args) {
          const start = performance.now();
          const result = upload.apply(this, args);
          const duration = performance.now() - start;
          if (duration >= 10) {
            const image = args.find(
              (arg) => arg instanceof HTMLImageElement || arg instanceof ImageBitmap,
            );
            sample.slowTextureUploads.push({
              name,
              start,
              duration,
              ...(image && { width: image.width, height: image.height }),
              ...(image instanceof HTMLImageElement && {
                path: new URL(image.src, location.href).pathname,
              }),
              ...(image instanceof ImageBitmap && { source: 'ImageBitmap' }),
            });
          }
          return result;
        };
      }
    }
    if (slowDraws) {
      const renderBufferDirect = renderer.renderBufferDirect;
      renderer.renderBufferDirect = function (camera, scene, geometry, material, object, group) {
        const start = performance.now();
        const result = renderBufferDirect.call(
          this,
          camera,
          scene,
          geometry,
          material,
          object,
          group,
        );
        const duration = performance.now() - start;
        if (duration > 50) {
          const target = renderer.getRenderTarget();
          const gl = renderer.getContext();
          const program = renderer.properties.get(material).currentProgram;
          const ancestry = [];
          for (let node = object; node && ancestry.length < 6; node = node.parent)
            ancestry.push({ id: node.id, name: node.name, type: node.type });
          sample.slowDraws.push({
            start,
            duration,
            ancestry,
            material: {
              id: material.id,
              name: material.name,
              type: material.type,
              defines: Object.keys(material.defines ?? {}),
              uniforms: Object.keys(material.uniforms ?? {}),
            },
            geometry: {
              id: geometry.id,
              name: geometry.name,
              type: geometry.type,
              attributes: Object.keys(geometry.attributes),
              vertices: geometry.getAttribute('position')?.count,
              indices: geometry.index?.count,
            },
            target: target && [target.width, target.height, target.samples],
            drawingBuffer: [gl.drawingBufferWidth, gl.drawingBufferHeight],
            program: program && { id: program.id, name: program.name, type: program.type },
          });
        }
        return result;
      };
    }
    const gpu = gpuTiming ? attachGpuTiming(renderer) : undefined;
    let colorWork;
    if (gpu && gpuColorPasses) {
      const renderBuffer = renderer.renderBufferDirect;
      renderer.renderBufferDirect = function (...args) {
        if (colorWork) {
          const material = args[3];
          if (renderer.getRenderTarget()) colorWork.offscreen++;
          else {
            const translucent = material.transparent || material.transmission > 0;
            const stage =
              translucent || colorWork.stage === 'translucent' ? 'translucent' : 'opaque';
            if (colorWork.stage === 'translucent' && !translucent) colorWork.lateOpaque++;
            if (colorWork.stage !== stage) {
              if (colorWork.query) gpu.end(colorWork.query);
              colorWork.query = gpu.begin(stage);
              colorWork.stage = stage;
            }
            colorWork[stage]++;
          }
        }
        return renderBuffer.apply(this, args);
      };
    }
    let renderPanorama = false;
    if (gpu && gpuPanorama) {
      const renderBuffer = renderer.renderBufferDirect;
      renderer.renderBufferDirect = function (...args) {
        if (!renderPanorama || args[4].name !== 'Depth-reprojected waterfront photograph')
          return renderBuffer.apply(this, args);
        const query = gpu.begin('panorama');
        try {
          return renderBuffer.apply(this, args);
        } finally {
          if (query) gpu.end(query);
        }
      };
    }
    let drawSample = null;
    if (drawCalls) {
      const gl = renderer.getContext();
      const multi = gl.getExtension('WEBGL_multi_draw');
      sample.multiDrawAvailable = Boolean(multi);
      sample.drawCalls = [];
      const drawElements = gl.drawElements;
      gl.drawElements = function (...args) {
        if (drawSample) drawSample.indexed++;
        return drawElements.apply(this, args);
      };
      if (multi) {
        const multiDraw = multi.multiDrawElementsWEBGL;
        multi.multiDrawElementsWEBGL = function (...args) {
          if (drawSample) {
            drawSample.multi++;
            drawSample.multiSubdraws += args[6];
          }
          return multiDraw.apply(this, args);
        };
      }
    }
    let world, roomCamera;
    let inventory;
    if (drawInventory) {
      const renderBuffer = renderer.renderBufferDirect;
      renderer.renderBufferDirect = function (camera, scene, geometry, material, object, group) {
        if (!inventory || scene !== world || renderer.getRenderTarget() !== inventory.target)
          return renderBuffer.call(this, camera, scene, geometry, material, object, group);

        const before = renderer.info.render;
        const { calls: previousCalls, triangles: previousTriangles } = before;
        const result = renderBuffer.call(this, camera, scene, geometry, material, object, group);
        const { calls, triangles } = renderer.info.render;
        if (calls <= previousCalls) return result;

        const path = [];
        for (let node = object; node && node !== world; node = node.parent) {
          if (node.name) path.unshift(node.name);
        }
        inventory.draws.push({
          path,
          object: object.id,
          type: object.type,
          geometry: geometry.id,
          material: material.id,
          materialName: material.name,
          materialType: material.type,
          translucent: Boolean(material.transparent || material.transmission > 0),
          calls: calls - previousCalls,
          triangles: triangles - previousTriangles,
        });
        return result;
      };
    }
    let depthQuery, depthDrawnAt;
    let downstreamQuery, downstreamFrame;
    let gradeFrame, gradeIndex, gradeQuery, gradeTexture;
    if (gpu && gpuLowGrade) {
      const copy = renderer.copyFramebufferToTexture;
      renderer.copyFramebufferToTexture = function (texture, ...args) {
        if (!texture.isFramebufferTexture || gradeFrame !== document.timeline.currentTime)
          return copy.call(this, texture, ...args);
        gradeFrame = undefined;
        gradeTexture = texture;
        gradeQuery = gpu.begin('grade', gradeIndex);
        return copy.call(this, texture, ...args);
      };
    }
    sample.project = (name) => {
      const object = world?.getObjectByName(name);
      if (!object || !roomCamera) return null;
      const point = object.getWorldPosition(roomCamera.position.clone()).project(roomCamera);
      if (point.z < -1 || point.z > 1) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      return {
        x: rect.x + ((1 + point.x) * rect.width) / 2,
        y: rect.y + ((1 - point.y) * rect.height) / 2,
      };
    };
    const render = renderer.render;
    renderer.render = function (scene, camera) {
      if (checkShaders && !renderer.debug.checkShaderErrors)
        renderer.debug.checkShaderErrors = true;
      if (
        !world &&
        scene.isScene &&
        camera.isPerspectiveCamera &&
        scene.getObjectByName('Felix Studio')
      )
        world = scene;
      const frame = document.timeline.currentTime;
      if (gradeQuery && sample.roomFrames.at(-1) !== frame) {
        gpu.end(gradeQuery, true);
        gradeQuery = gradeTexture = undefined;
      }
      if (depthQuery && depthDrawnAt !== frame) {
        gpu.end(depthQuery, true);
        depthQuery = undefined;
      }
      if (downstreamQuery && downstreamFrame !== frame) {
        gpu.end(downstreamQuery, true);
        downstreamQuery = undefined;
      }
      const downstreamOutput =
        downstreamQuery &&
        scene.isMesh &&
        camera.isOrthographicCamera &&
        scene.material.name === 'OutputShader' &&
        !renderer.getRenderTarget();
      const gradeOutput =
        gradeQuery &&
        scene.isMesh &&
        camera.isOrthographicCamera &&
        scene.material.uniforms?.tDiffuse?.value === gradeTexture &&
        !renderer.getRenderTarget();
      const room = world === scene && camera.isPerspectiveCamera && !camera.parent?.isCubeCamera;
      if (room) roomCamera = camera;
      const primary =
        sample.recording && room && !scene.overrideMaterial && sample.roomFrames.at(-1) !== frame;
      const depthPrefill =
        sample.recording && room && scene.overrideMaterial?.name === 'Studio depth prefill';
      if (depthPrefill) sample.depthPrefillFrames = (sample.depthPrefillFrames ?? 0) + 1;
      const start = primary || startupSpans ? performance.now() : 0;
      const startupTarget = startupSpans ? renderer.getRenderTarget() : null;
      let query;
      const splitDepth = gpu?.splitDepthFrame();
      if (primary) {
        if (splitDepth) {
          if (depthDrawnAt === frame) query = gpu.begin('color');
        } else query = depthQuery ?? gpu?.begin();
      } else if (depthPrefill) query = gpu?.begin(splitDepth ? 'depth' : 'main');
      if (primary && drawCalls) drawSample = { indexed: 0, multi: 0, multiSubdraws: 0 };
      if (
        primary &&
        drawInventory &&
        sample.drawInventory.length < 3 &&
        frame - (sample.drawInventory.at(-1)?.frame ?? -Infinity) >= 1400
      )
        inventory = {
          frame,
          yaw: camera.quaternion.y,
          target: renderer.getRenderTarget(),
          draws: [],
        };
      if (gpuPanorama) renderPanorama = primary && gpu?.panoramaFrame();
      if (renderPanorama) sample.panoramaFrames = (sample.panoramaFrames ?? 0) + 1;
      if (primary && gpu?.colorPassFrame())
        colorWork = { opaque: 0, translucent: 0, offscreen: 0, lateOpaque: 0 };
      let result;
      let complete = false;
      try {
        result = render.call(this, scene, camera);
        complete = true;
        if (depthPrefill) {
          depthDrawnAt = frame;
          if (!splitDepth) depthQuery = query;
          if (gpuTiming) {
            const { calls, triangles } = renderer.info.render;
            (sample.depthPrefillWork ??= []).push([calls, triangles]);
          }
        }
      } finally {
        if (startupSpans)
          recordStartupSpan(room ? 'room-render' : 'other-render', start, startupTarget);
        renderPanorama = false;
        if (primary && drawSample) {
          sample.drawCalls.push(drawSample);
          drawSample = null;
        }
        if (primary && inventory) {
          const { frame, yaw, draws } = inventory;
          if (complete) sample.drawInventory.push({ frame, yaw, draws });
          inventory = undefined;
        }
        if (query && (!depthPrefill || depthQuery !== query)) {
          gpu.end(query, !complete);
          depthQuery = undefined;
        }
        if (downstreamOutput) {
          gpu.end(downstreamQuery, !complete);
          downstreamQuery = undefined;
        }
        if (gradeOutput) {
          gpu.end(gradeQuery, !complete);
          gradeQuery = gradeTexture = undefined;
        }
        if (primary && colorWork) {
          const { query, stage, ...work } = colorWork;
          if (query) gpu.end(query, !complete);
          if (complete) (sample.colorPassWork ??= []).push(work);
          colorWork = undefined;
        }
      }
      if (drag && room && !scene.overrideMaterial) {
        yaw = camera.quaternion.y;
        if (drag.move != null) {
          const submitted = performance.now();
          drag.nextSubmit ??= submitted;
          if (Math.abs(yaw - drag.yawBefore) > 0.00001) drag.changedSubmit ??= submitted;
          if (submitted < drag.move + 10000 && drag.frames.at(-1) !== frame)
            drag.frames.push(frame);
        }
      }
      if (primary) {
        const target = renderer.getRenderTarget();
        if (query && gpuDownstream && target) {
          downstreamQuery = gpu.begin('downstream');
          downstreamFrame = frame;
        }
        if (query && gpuLowGrade && !target) {
          gradeFrame = frame;
          gradeIndex = sample.roomFrames.length;
        }
        sample.roomFrames.push(frame);
        sample.submissions.push(performance.now() - start);
        sample.rotations.push(camera.quaternion.y);
        if (gpuTiming) {
          const { x, y, z, w } = camera.quaternion;
          sample.cameraYaws.push(Math.atan2(2 * (w * y + x * z), 1 - 2 * (x * x + y * y)));
        }
        sample.draws = renderer.info.render.calls;
        sample.tris = renderer.info.render.triangles;
        const gl = renderer.getContext();
        const dimensions = [
          gl.drawingBufferWidth,
          gl.drawingBufferHeight,
          target?.width ?? 0,
          target?.height ?? 0,
          target?.samples ?? 0,
        ].join(',');
        sample.resolutions[dimensions] = (sample.resolutions[dimensions] ?? 0) + 1;
      }
      return result;
    };
  });
}

function readSamples() {
  const { renderer, rotations, recording, project, beginGpuTiming, finishGpuTiming, ...raw } =
    window.studioBench;
  const gl = renderer.getContext();
  const info = gl.getExtension('WEBGL_debug_renderer_info');
  const { weather, night } = JSON.parse(localStorage.getItem('felix-studio-v1') ?? '{}');
  const resources = performance
    .getEntriesByType('resource')
    .filter((entry) => new URL(entry.name).origin === location.origin)
    .map(({ name, initiatorType, startTime, responseEnd, transferSize, encodedBodySize }) => ({
      path: new URL(name).pathname,
      initiatorType,
      startTime,
      responseEnd,
      transferSize,
      encodedBodySize,
    }));
  return {
    ...raw,
    timeOriginUnixMs: performance.timeOrigin,
    gpu: info && gl.getParameter(info.UNMASKED_RENDERER_WEBGL),
    shaderProgramCount: renderer.info.programs?.length ?? 0,
    ...(raw.slowDraws && {
      shaderPrograms: renderer.info.programs?.map(({ id, cacheKey }) => ({ id, cacheKey })),
    }),
    mode: document.querySelector('.studio')?.dataset.mode,
    weather,
    night,
    viewport: [innerWidth, innerHeight],
    devicePixelRatio,
    drawingBuffer: [gl.drawingBufferWidth, gl.drawingBufferHeight],
    defaultFramebufferAntialias: gl.getContextAttributes()?.antialias ?? null,
    motion: rotations.length ? Math.max(...rotations) - Math.min(...rotations) : 0,
    marks: Object.fromEntries(
      performance
        .getEntriesByType('mark')
        .filter((e) => e.name.startsWith('studio'))
        .map((e) => [e.name, e.startTime]),
    ),
    measures: Object.fromEntries(
      performance
        .getEntriesByType('measure')
        .filter((e) => e.name.startsWith('studio'))
        .map((e) => [e.name, { start: e.startTime, duration: e.duration }]),
    ),
    resources,
    chunk: resources.find(
      ({ path }) => path.startsWith('/assets/StudioView-') && path.endsWith('.js'),
    )?.path,
  };
}

const deskOrigin = ({ width, height }) => ({
  x: Math.round(width * 0.48),
  y: Math.round(height * 0.36),
});

function waitForShading(page) {
  return page.waitForFunction(
    () => performance.getEntriesByName('studio-room-shaded').length > 0,
    null,
    { timeout: 120000 },
  );
}

async function sampleStartup(page, profile, inputDelayMs, route) {
  await page.waitForFunction(
    (delay) => {
      const end = window.studioBench?.loaderEnd;
      return end > 0 && performance.now() >= end + delay;
    },
    inputDelayMs,
    { timeout: 120000 + inputDelayMs },
  );
  const { x, y } = deskOrigin(profile);
  const start = performance.now();
  await page.mouse.move(x, y);
  const positioned = performance.now();
  await page.mouse.down();
  const pressed = performance.now();
  await page.mouse.move(x + (route?.turn ?? 96), y + (route?.pitch ?? 0));
  const moved = performance.now();
  await page.mouse.up();
  const released = performance.now();
  await page.waitForFunction(
    () => performance.now() >= window.studioBench?.firstDrag?.move + 10000,
    null,
    { timeout: 20000 },
  );
  const arrival = route
    ? await page.evaluate((target) => window.studioBench.project(target), route.target)
    : undefined;
  if (
    route &&
    (!arrival ||
      arrival.x < 0 ||
      arrival.x > profile.width ||
      arrival.y < 0 ||
      arrival.y > profile.height)
  )
    throw new Error('The first drag did not bring the workbench into the viewport.');
  return {
    position: rounded(positioned - start),
    press: rounded(pressed - positioned),
    move: rounded(moved - pressed),
    release: rounded(released - moved),
    ...(arrival && { arrival }),
  };
}

async function turnDesk(page, profile, duration, reset) {
  const origin = deskOrigin(profile);
  await page.mouse.move(origin.x, origin.y);
  await page.mouse.down();
  await page.evaluate(
    ({ x, y, duration, reset }) =>
      new Promise((done) => {
        let start;
        function tick(time) {
          start ??= time;
          const elapsed = time - start;
          const sample = window.studioBench;
          const finished = elapsed >= duration;
          sample.recording = elapsed > 2000 && !finished;
          const phase = reset && finished ? 0 : elapsed / 1500;
          sample.renderer.domElement.dispatchEvent(
            new PointerEvent('pointermove', {
              pointerType: 'mouse',
              pointerId: 1,
              buttons: 1,
              bubbles: true,
              clientX: x + 180 * Math.sin(phase),
              clientY: y + 25 * Math.sin(phase),
            }),
          );
          if (finished) done();
          else requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      }),
    { ...origin, duration, reset },
  );
  await page.mouse.up();
}

async function enterRoute(page, profile, routeName) {
  const route = roomRoutes[routeName];
  if (!route) return;
  if (route.turn) {
    const origin = deskOrigin(profile);
    await page.mouse.move(origin.x, origin.y);
    await page.mouse.down();
    await page.mouse.move(origin.x + route.turn, origin.y + (route.pitch ?? 0));
    await page.mouse.up();
    await page.waitForTimeout(400);
  }
  const projected = await page.waitForFunction((target) => {
    const point = window.studioBench.project(target);
    return point && point.x > 0 && point.x < innerWidth && point.y > 0 && point.y < innerHeight
      ? point
      : null;
  }, route.target);
  const { x, y } = await projected.jsonValue();
  await page.mouse.click(x, y);
  await page.waitForFunction(
    ({ mode, caption }) =>
      document.querySelector('.studio')?.dataset.mode === mode &&
      (!caption || document.querySelector('.object-caption')?.textContent?.includes(caption)),
    route,
  );
  await page.waitForTimeout(1200);
}

async function sampleDesk(
  page,
  profile,
  { repeatDesk, seconds, screenshot, route, gpuTiming },
  beforeMeasurement,
) {
  await waitForShading(page);
  await page.waitForTimeout(5000);
  await enterRoute(page, profile, route);
  let firstTurn;
  if (repeatDesk) {
    await turnDesk(page, profile, 14000, true);
    firstTurn = await page.evaluate(() => {
      const sample = window.studioBench;
      const { roomFrames, submissions } = sample;
      sample.roomFrames = [];
      sample.submissions = [];
      sample.rotations = [];
      if (sample.cameraYaws) sample.cameraYaws.length = 0;
      sample.resolutions = {};
      if (sample.depthPrefillFrames !== undefined) sample.depthPrefillFrames = 0;
      if (sample.depthPrefillWork) sample.depthPrefillWork.length = 0;
      if (sample.drawCalls) sample.drawCalls.length = 0;
      if (sample.drawInventory) sample.drawInventory.length = 0;
      return { roomFrames, submissions };
    });
    await page.waitForTimeout(1000);
  }
  await beforeMeasurement?.();
  if (gpuTiming)
    await page.evaluate(() => {
      const begin = window.studioBench.beginGpuTiming;
      if (!begin) throw new Error('Main-color GPU timer unavailable.');
      begin();
    });
  await turnDesk(page, profile, 2000 + seconds * 1000, screenshot);
  if (gpuTiming)
    await page.waitForFunction(() => window.studioBench.finishGpuTiming(), null, {
      polling: 50,
      timeout: 15000,
    });
  if (screenshot) await page.waitForTimeout(500);
  return firstTurn;
}

function checkSamples(raw, profile, { captureProfile, loaderTrace, startup }) {
  if (
    typeof raw.gpu !== 'string' ||
    !adapterNames[profile.adapter].test(raw.gpu.trim()) ||
    raw.visible !== 'visible' ||
    raw.visibilityChanged
  )
    throw new Error(
      `Expected visible page on ${profile.adapter}, observed ${raw.gpu}, ${raw.visible}, visibility changed: ${raw.visibilityChanged}.`,
    );
  if (!raw.chunk || !raw.loaderFrames.length || !(raw.loaderEnd > raw.loaderStart))
    throw new Error('The production room chunk or loader samples are missing.');
  if (startup) {
    if (!raw.firstDrag?.changedSubmit || raw.firstDrag.frames.length < 2)
      throw new Error('The first drag produced no measurable change in submitted room frames.');
    const [width, height] = raw.drawingBuffer;
    if (
      (profile.quality === 'high' || profile.forceNative) &&
      (width !== profile.width || height !== profile.height)
    )
      throw new Error('Unexpected native drawing-buffer dimensions: ' + raw.drawingBuffer);
    return;
  }
  if (captureProfile || loaderTrace) return;
  if (!raw.motion || raw.roomFrames.length < 2)
    throw new Error(
      'The desk route produced no measurable camera movement or room frame intervals.',
    );
  for (const key of Object.keys(raw.resolutions)) {
    const [width, height, targetWidth, targetHeight] = key.split(',').map(Number);
    if (
      (profile.quality === 'high' || profile.forceNative) &&
      (width !== profile.width || height !== profile.height)
    )
      throw new Error('Unexpected native drawing-buffer dimensions: ' + key);
    if (profile.quality === 'high' && (targetWidth !== width || targetHeight !== height))
      throw new Error('High-quality target differs from the drawing buffer: ' + key);
  }
}

async function traceLoader(cdp) {
  const completed = new Promise((resolve) => cdp.once('Tracing.tracingComplete', resolve));
  await cdp.send('Tracing.start', {
    categories: 'cc,viz,benchmark,devtools.timeline,disabled-by-default-devtools.screenshot',
    transferMode: 'ReturnAsStream',
  });
  return async () => {
    await cdp.send('Tracing.end');
    const { stream, dataLossOccurred } = await completed;
    if (!stream || dataLossOccurred) throw new Error('The compositor trace is incomplete.');
    const chunks = [];
    try {
      let part;
      do {
        part = await cdp.send('IO.read', { handle: stream });
        chunks.push(Buffer.from(part.data, part.base64Encoded ? 'base64' : 'utf8'));
      } while (!part.eof);
    } finally {
      await cdp.send('IO.close', { handle: stream });
    }
    return Buffer.concat(chunks);
  };
}

const rounded = (value) => Number(value.toFixed(2));
const intervals = (times) => times.slice(1).map((end, i) => end - times[i]);
function stats(values) {
  const ordered = values.toSorted((a, b) => a - b);
  const percentile = (fraction) => rounded(ordered[Math.ceil(fraction * ordered.length) - 1]);
  return {
    samples: values.length,
    fps: rounded((1000 * values.length) / values.reduce((a, b) => a + b)),
    p50: percentile(0.5),
    p95: percentile(0.95),
    p99: percentile(0.99),
    max: percentile(1),
    over33_4: values.filter((v) => v > 33.4).length,
    over50: values.filter((v) => v > 50).length,
  };
}

function startupSummary(raw, automationCommandMs) {
  const { press, pressDispatch, move, moveDispatch, nextSubmit, changedSubmit, frames } =
    raw.firstDrag;
  const accepted = raw.marks['studio-input-accepted'];
  const longTasks = raw.longTasks.filter(
    ([start, duration]) => start < move + 10000 && start + duration > move,
  );
  const resources = raw.resources.filter(({ responseEnd }) => responseEnd <= (accepted ?? move));
  const observedPressUploads = raw.slowTextureUploads
    ?.map(({ start, duration, path, source }) => ({
      path,
      source,
      durationMs: rounded(Math.min(pressDispatch, start + duration) - Math.max(press, start)),
    }))
    .filter(({ durationMs }) => durationMs > 0);
  return {
    loaderEndToPressMs: rounded(press - raw.loaderEnd),
    loaderEndToMoveMs: rounded(move - raw.loaderEnd),
    loaderEndToChangedRoomSubmitMs: rounded(changedSubmit - raw.loaderEnd),
    pressDispatchMs: rounded(pressDispatch - press),
    ...(observedPressUploads && {
      observedPressUploads,
      observedPressUploadMs: rounded(
        observedPressUploads.reduce((total, upload) => total + upload.durationMs, 0),
      ),
    }),
    inputDispatchMs: rounded(moveDispatch - move),
    inputToNextRoomSubmitMs: rounded(nextSubmit - move),
    inputToChangedRoomSubmitMs: rounded(changedSubmit - move),
    acceptedInputToChangedRoomSubmitMs: accepted == null ? null : rounded(changedSubmit - accepted),
    afterFirstInput: stats(intervals(frames)),
    afterFirstInputLongTaskCount: longTasks.length,
    afterFirstInputLongTaskMax: Math.max(0, ...longTasks.map(([, duration]) => duration)),
    finishedResourcesBeforeInput: resources.length,
    transferBytesBeforeInput: resources.reduce((total, entry) => total + entry.transferSize, 0),
    automationCommandMs,
  };
}

async function measure({ base, directory, head, name, run, settings }) {
  const {
    captureProfile,
    steadyProfile,
    gpuTiming,
    gpuPanorama,
    gpuDownstream,
    gpuLowGrade,
    gpuDepthPrepass,
    gpuColorPasses,
    opaqueNearFirst,
    drawCalls,
    drawInventory,
    cpuTelemetry,
    wddmLuid,
    loaderTrace,
    startup,
    startupSpans,
    warmupWork,
    fullRoom,
    inputDelayMs,
    screenshot,
    slowDraws,
    textureUploads,
    checkShaders,
    selected,
    dist,
    warm,
    repeatDesk,
    day,
    seconds,
    route,
    weather,
    currentAdapter,
  } = settings;
  const profile = currentAdapter ? { ...profiles[name], adapter: 'current' } : profiles[name];
  const url = new URL(base);
  for (const flag of selected) url.searchParams.set(...experiments[flag]);
  const args = browserArgs(profile.adapter);
  const pinnedAdapter = args.find((arg) => arg.startsWith('--use-adapter-luid='));
  if (wddmLuid && pinnedAdapter && pinnedAdapter !== `--use-adapter-luid=${wddmLuid}`)
    throw new Error('WDDM telemetry must target the pinned Chrome adapter.');
  let cpuCollection = cpuTelemetry ? await startCpuTelemetry() : undefined;
  let browser, wddm;
  try {
    browser = await chromium.launch({ channel: 'chrome', headless: true, args });
    const page = await browser.newPage({
      viewport: { width: profile.width, height: profile.height },
      deviceScaleFactor: 1,
      timezoneId: 'Asia/Hong_Kong',
      serviceWorkers: 'block',
    });
    const issues = [];
    page.on('pageerror', (error) => issues.push(String(error)));
    page.on('console', (message) => {
      if (message.type() === 'error') issues.push(message.text());
    });
    page.on('console', (message) => {
      if (
        message.type() === 'error' &&
        /WebGLProgram|shader (error|compilation|link)/i.test(message.text())
      )
        issues.push(message.text());
    });
    page.on('response', (response) => {
      if (response.status() >= 400) issues.push(response.status() + ' ' + response.url());
    });
    page.on('requestfailed', (request) =>
      issues.push(request.failure()?.errorText + ' ' + request.url()),
    );
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: !warm });
    const cachedRequests = new Set();
    const revalidatedRequests = new Set();
    cdp.on('Network.requestServedFromCache', ({ requestId }) => cachedRequests.add(requestId));
    cdp.on('Network.responseReceived', ({ requestId, response }) => {
      if (response.fromDiskCache) cachedRequests.add(requestId);
    });
    cdp.on('Network.responseReceivedExtraInfo', ({ requestId, statusCode }) => {
      if (statusCode === 304) revalidatedRequests.add(requestId);
    });
    const weatherFixture = {
      current: { weather_code: weatherCodes[weather], is_day: Number(day) },
    };
    if (warm) {
      cdp.on('Fetch.requestPaused', ({ requestId, request }) => {
        const meteorology = new URL(request.url).hostname === 'api.open-meteo.com';
        const response = meteorology
          ? {
              requestId,
              responseCode: 200,
              responseHeaders: [
                { name: 'Content-Type', value: 'application/json' },
                { name: 'Access-Control-Allow-Origin', value: '*' },
              ],
              body: Buffer.from(JSON.stringify(weatherFixture)).toString('base64'),
            }
          : { requestId, responseCode: 204 };
        void cdp.send('Fetch.fulfillRequest', response).catch((error) => {
          issues.push(String(error));
        });
      });
      await cdp.send('Fetch.enable', { patterns: [{ urlPattern: 'https://*' }] });
    } else {
      await page.route(/^https:\/\//, (route) => {
        if (new URL(route.request().url()).hostname === 'api.open-meteo.com')
          return route.fulfill({ json: weatherFixture });
        return route.abort();
      });
    }
    await page.addInitScript(installProbe, {
      ...profile,
      startup,
      startupSpans,
      warmupWork,
      slowDraws,
      textureUploads,
      checkShaders,
      gpuTiming,
      gpuPanorama,
      gpuDownstream,
      gpuLowGrade,
      gpuDepthPrepass,
      gpuColorPasses,
      opaqueNearFirst,
      drawCalls,
      drawInventory,
      day,
      weather: weatherLabels[weather],
    });
    if (warm) {
      await page.goto(url.href, { waitUntil: 'domcontentloaded' });
      await waitForShading(page);
      await page.waitForLoadState('networkidle', { timeout: 120000 });
      cachedRequests.clear();
      revalidatedRequests.clear();
    }
    if (captureProfile || steadyProfile || loaderTrace) await cdp.send('Performance.enable');
    if (captureProfile || steadyProfile) {
      await cdp.send('Profiler.enable');
      await cdp.send('Profiler.setSamplingInterval', { interval: 1000 });
    }
    if (captureProfile) await cdp.send('Profiler.start');
    const stopTrace = loaderTrace ? await traceLoader(cdp) : undefined;
    if (warm) await page.reload({ waitUntil: 'domcontentloaded' });
    else await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    let cpuProfile, compositorTrace, navigationStart, automationCommandMs, firstTurn;
    if (startup)
      automationCommandMs = await sampleStartup(page, profile, inputDelayMs, roomRoutes[route]);
    if (stopTrace) {
      await page.waitForFunction(() => window.studioBench?.loaderEnd > 0, null, {
        timeout: 120000,
      });
      compositorTrace = await stopTrace();
      const { metrics } = await cdp.send('Performance.getMetrics');
      navigationStart = metrics.find((metric) => metric.name === 'NavigationStart')?.value;
      if (!navigationStart) throw new Error('The compositor trace has no navigation clock.');
    }
    if (captureProfile && !startup)
      await page.waitForFunction(() => window.studioBench?.loaderEnd > 0, null, {
        timeout: 120000,
      });
    if (!captureProfile && !loaderTrace && !startup) {
      firstTurn = await sampleDesk(page, profile, settings, async () => {
        if (wddmLuid) {
          const browserCdp = await browser.newBrowserCDPSession();
          const { processInfo } = await browserCdp.send('SystemInfo.getProcessInfo');
          const gpu = processInfo.filter(({ type }) => type.toLowerCase() === 'gpu');
          if (gpu.length !== 1 || !Number.isSafeInteger(gpu[0].id) || gpu[0].id <= 0)
            throw new Error('The private Chrome browser did not report a unique GPU process.');
          wddm = await startWddmTelemetry({ gpuPid: gpu[0].id, adapterLuid: wddmLuid });
          await browserCdp.detach();
        }
        if (steadyProfile) await cdp.send('Profiler.start');
      });
    }
    if (captureProfile || steadyProfile) {
      cpuProfile = (await cdp.send('Profiler.stop')).profile;
      const { metrics } = await cdp.send('Performance.getMetrics');
      navigationStart = metrics.find((m) => m.name === 'NavigationStart')?.value;
      if (!cpuProfile.samples.length || !navigationStart)
        throw new Error('CPU samples or navigation clock unavailable.');
    }
    if (startup) await waitForShading(page);
    if (fullRoom)
      await page.waitForFunction(
        () => performance.getEntriesByName('studio-room-rear-ready').length > 0,
        null,
        { polling: 250, timeout: 120000 },
      );
    const raw = await page.evaluate(readSamples);
    if (cpuCollection) {
      raw.cpuTelemetry = await cpuCollection.stop();
      cpuCollection = undefined;
    }
    if (wddm) {
      raw.wddm = await wddm.stop();
      wddm = undefined;
    }
    checkSamples(raw, profile, settings);
    const summary = {
      variant: name,
      run,
      head,
      time: new Date().toISOString(),
      node: process.version,
      chrome: browser.version(),
      platform: process.platform,
      os: os.release(),
      cpu: os.cpus()[0]?.model,
      gpu: raw.gpu,
      shaderProgramCount: raw.shaderProgramCount,
      viewport: raw.viewport,
      devicePixelRatio: raw.devicePixelRatio,
      drawingBuffer: raw.drawingBuffer,
      defaultFramebufferAntialias: raw.defaultFramebufferAntialias,
      chunk: raw.chunk,
      chunkSHA256: createHash('sha256')
        .update(readFileSync(join(dist, raw.chunk)))
        .digest('hex'),
      visible: raw.visible,
      visibilityChanged: raw.visibilityChanged,
      issues,
      cache: {
        policy: warm ? 'warm' : 'cold',
        hits: cachedRequests.size,
        revalidated: revalidatedRequests.size,
      },
      args,
      profile,
      route,
      weather,
      ...(startup && { requestedInputDelayMs: inputDelayMs }),
      observedWeather: raw.weather,
      night: raw.night,
      mode: raw.mode,
      experiments: Object.fromEntries(url.searchParams),
      ...(slowDraws && { slowDraws: raw.slowDraws.length }),
      ...(raw.slowTextureUploads && { slowTextureUploads: raw.slowTextureUploads.length }),
      ...(opaqueNearFirst && { opaqueSort: 'near-first' }),
      ...(drawInventory && { inventoryFrames: raw.drawInventory.length }),
      ...(warmupWork && {
        warmupWork: raw.warmupWork.phases.map(({ stage, start, end, work, programs }) => ({
          stage,
          ...(end !== undefined && { elapsedMs: rounded(end - start) }),
          programs: Object.keys(programs).length,
          readyPrograms: Object.values(programs).filter(({ readyAt }) => readyAt !== undefined)
            .length,
          ...Object.fromEntries(
            Object.entries(work).map(([name, { calls, total, max }]) => [
              name,
              { calls, totalMs: rounded(total), maxMs: rounded(max) },
            ]),
          ),
        })),
      }),
      ...(raw.cpuTelemetry && {
        cpuTelemetrySamples: raw.cpuTelemetry.samples.length,
        ...(raw.cpuTelemetry.error && { cpuTelemetryError: raw.cpuTelemetry.error }),
      }),
      ...(raw.wddm && {
        wddmSamples: raw.wddm.samples.length,
        ...(raw.wddm.error && { wddmError: raw.wddm.error }),
      }),
      ...(drawCalls && {
        multiDrawAvailable: raw.multiDrawAvailable,
        indexedDrawP50: stats(raw.drawCalls.map(({ indexed }) => indexed)).p50,
        multiDrawFrames: raw.drawCalls.filter(({ multi }) => multi > 0).length,
        multiDrawMax: Math.max(0, ...raw.drawCalls.map(({ multi }) => multi)),
        multiSubdrawsMax: Math.max(0, ...raw.drawCalls.map(({ multiSubdraws }) => multiSubdraws)),
      }),
    };
    let stem = join(
      directory,
      [
        captureProfile && 'loader-profile',
        steadyProfile && 'steady-profile',
        gpuTiming && 'gpu-timing',
        gpuPanorama && 'gpu-panorama',
        gpuDownstream && 'gpu-downstream',
        gpuLowGrade && 'gpu-low-grade',
        gpuDepthPrepass && 'gpu-depth-prepass',
        gpuColorPasses && 'gpu-color-passes',
        opaqueNearFirst && 'opaque-near-first',
        drawCalls && 'draw-calls',
        drawInventory && 'draw-inventory',
        cpuTelemetry && 'cpu-telemetry',
        wddmLuid && 'wddm',
        loaderTrace && 'loader-trace',
        startup && 'startup',
        startupSpans && 'startup-spans',
        warmupWork && 'warmup-work',
        inputDelayMs > 0 && `input-delay-${inputDelayMs}ms`,
        slowDraws && 'slow-draws',
        textureUploads && 'texture-uploads',
        checkShaders && 'check-shaders',
        warm && 'warm',
        repeatDesk && 'repeat-desk',
        seconds !== 12 && `${seconds}s`,
        route !== 'desk' && route,
        day && 'day',
        weather !== 'clear' && weather,
        currentAdapter && 'current-adapter',
        name,
        ...selected.map((flag) => flag.slice(2)),
        run,
      ]
        .filter(Boolean)
        .join('-'),
    );
    if (process.platform === 'win32' && resolve(stem + '.trace.json.gz').length >= 260) {
      const fingerprint = createHash('sha256').update(stem).digest('hex').slice(0, 12);
      stem = join(directory, `${name}-${route}-${fingerprint}-${run}`);
    }
    const frontMs = raw.marks['studio-room-material-prep-end'];
    const rearMs = raw.marks['studio-room-rear-ready'];
    const shadedMs = raw.marks['studio-room-shaded'];
    if ([frontMs, rearMs, shadedMs].every(Number.isFinite))
      summary.roomReadinessMs = {
        front: rounded(frontMs),
        rear: rounded(rearMs),
        initialShading: rounded(shadedMs),
        assetsAndInitialShading: rounded(Math.max(frontMs, rearMs, shadedMs)),
      };

    summary.loaderProgress = raw.loaderProgress;
    if (gpuTiming) {
      const { durations, discarded } = raw.mainColorGpu;
      if (durations.length < 5)
        throw new Error('Insufficient valid main-color GPU timing queries.');
      const { samples, p50, p95, p99, max } = stats(durations);
      summary.mainColorGpuMs = { samples, p50, p95, p99, max, discarded };
    }
    if (gpuPanorama) {
      const { durations, discarded } = raw.panoramaGpu;
      if (durations.length < 5) throw new Error('Insufficient valid panorama GPU timing queries.');
      const { samples, p50, p95, p99, max } = stats(durations);
      summary.panoramaGpuMs = {
        frames: raw.panoramaFrames,
        samples,
        p50,
        p95,
        p99,
        max,
        discarded,
      };
    }
    if (gpuDownstream) {
      const { durations, discarded } = raw.downstreamGpu;
      if (durations.length < 5)
        throw new Error('Insufficient valid downstream GPU timing queries.');
      const { samples, p50, p95, p99, max } = stats(durations);
      summary.downstreamGpuMs = { samples, p50, p95, p99, max, discarded };
    }
    for (const [enabled, key, rawTiming] of [
      [gpuDepthPrepass, 'depthOnlyGpuMs', raw.depthOnlyGpu],
      [gpuDepthPrepass, 'colorAfterDepthGpuMs', raw.colorAfterDepthGpu],
      [gpuColorPasses, 'opaqueColorGpuMs', raw.opaqueColorGpu],
      [gpuColorPasses, 'translucentColorGpuMs', raw.translucentColorGpu],
      [gpuLowGrade, 'lowGradeGpuMs', raw.lowGradeGpu],
    ]) {
      if (!enabled) continue;
      if (rawTiming.durations.length < 5)
        throw new Error('Insufficient valid GPU timing queries for ' + key);
      const { samples, p50, p95, p99, max } = stats(rawTiming.durations);
      summary[key] = { samples, p50, p95, p99, max, discarded: rawTiming.discarded };
    }
    if (gpuColorPasses) {
      const work = raw.colorPassWork;
      summary.colorPassWork = {
        frames: work.length,
        medianOpaqueDraws: stats(work.map(({ opaque }) => opaque)).p50,
        medianTranslucentDraws: stats(work.map(({ translucent }) => translucent)).p50,
        offscreenDraws: work.reduce((sum, { offscreen }) => sum + offscreen, 0),
        lateOpaqueDraws: work.reduce((sum, { lateOpaque }) => sum + lateOpaque, 0),
      };
    }
    if (raw.depthPrefillWork?.length) {
      summary.depthPrefillWork = {
        frames: raw.depthPrefillWork.length,
        medianDraws: stats(raw.depthPrefillWork.map(([draws]) => draws)).p50,
        medianTriangles: stats(raw.depthPrefillWork.map(([, triangles]) => triangles)).p50,
      };
    }
    if (cpuProfile) {
      summary.navigationStartMonotonicSeconds = navigationStart;
      summary.sampledIntervalMicroseconds = 1000;
      writeFileSync(stem + '.cpuprofile.gz', gzipSync(JSON.stringify(cpuProfile)));
    }
    if (captureProfile) {
      if (startup) Object.assign(summary, startupSummary(raw, automationCommandMs));
      const metadata = { ...raw, ...summary, textureUploadEvents: raw.slowTextureUploads };
      writeFileSync(stem + '.meta.json', JSON.stringify(metadata, null, 2));
    } else {
      const loaderTasks = raw.longTasks.filter(
        ([start, duration]) => start < raw.loaderEnd && start + duration > raw.loaderStart,
      );
      Object.assign(summary, {
        loader: stats(intervals([raw.loaderStart, ...raw.loaderFrames, raw.loaderEnd])),
        loaderStart: rounded(raw.loaderStart),
        loaderEnd: rounded(raw.loaderEnd),
        loaderLongTaskMax: Math.max(0, ...loaderTasks.map(([, duration]) => duration)),
        marks: raw.marks,
        measures: raw.measures,
      });
      if (startup) Object.assign(summary, startupSummary(raw, automationCommandMs));
      else if (!loaderTrace)
        Object.assign(summary, {
          resolutions: raw.resolutions,
          room: stats(intervals(raw.roomFrames)),
          primarySubmitP95: stats(raw.submissions).p95,
          draws: raw.draws,
          tris: raw.tris,
          motion: raw.motion,
          durationSeconds: seconds,
        });
      if (firstTurn) {
        summary.firstTurn = {
          room: stats(intervals(firstTurn.roomFrames)),
          primarySubmitP95: stats(firstTurn.submissions).p95,
        };
        raw.firstTurn = firstTurn;
      }
      if (compositorTrace) {
        const captures = JSON.parse(compositorTrace)
          .traceEvents.filter((event) => event.name === 'Screenshot')
          .map(({ ts, args }) => ({
            time: ts / 1000 - navigationStart * 1000,
            image: args.snapshot,
          }))
          .filter(({ time }) => time >= raw.loaderStart && time <= raw.loaderEnd)
          .sort((a, b) => a.time - b.time);
        const changed = captures.filter(
          (capture, index) => capture.image !== captures[index - 1]?.image,
        );
        summary.loaderScreenshots = stats(intervals(captures.map(({ time }) => time)));
        summary.loaderScreenshotChanges = stats(intervals(changed.map(({ time }) => time)));
        summary.navigationStartMonotonicSeconds = navigationStart;
        writeFileSync(stem + '.trace.json.gz', gzipSync(compositorTrace));
      }
      writeFileSync(stem + '.json', JSON.stringify({ summary, raw }, null, 2));
      if (screenshot) await page.screenshot({ path: stem + '.png', timeout: 60000 });
    }
    console.log(stem, JSON.stringify(summary));
    if (issues.length) throw new Error('Browser issues were recorded in the measurement output.');
    if (warm && !cachedRequests.size && !revalidatedRequests.size)
      throw new Error('The warm reload observed no HTTP cache hits or revalidations.');
  } finally {
    try {
      await Promise.all([wddm?.stop(), cpuCollection?.stop()]);
    } finally {
      await browser?.close();
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) return console.log(usage);
  const settings = options(args);
  const { names, runs, dist } = settings;
  if (!existsSync(join(dist, 'index.html')))
    throw new Error('Run npm run build from the website root first.');
  const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const directory = join('.review', 'performance', head.slice(0, 7));
  mkdirSync(directory, { recursive: true });
  const server = await preview({
    configFile: false,
    build: { outDir: dist },
    preview: { host: '127.0.0.1', port: 0 },
  });
  const base = 'http://127.0.0.1:' + server.httpServer.address().port;
  try {
    for (const run of runs)
      for (const name of names) await measure({ base, directory, head, name, run, settings });
  } finally {
    await server.close();
  }
}

export { adapterNames, browserArgs, installProbe, profiles, turnDesk, waitForShading };

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url)
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
