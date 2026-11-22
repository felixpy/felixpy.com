import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';
import { chromium } from '@playwright/test';
import { preview } from 'vite';

const profiles = {
  '4k': { width: 3840, height: 2160, quality: 'high', adapter: '4090' },
  '1440p': { width: 2560, height: 1440, quality: 'high', adapter: '4090' },
  3060: { width: 2560, height: 1440, quality: 'high', adapter: '3060' },
  'uhd-adaptive': { width: 1920, height: 1080, quality: 'low', adapter: 'intel' },
  'uhd-native': { width: 1920, height: 1080, quality: 'low', adapter: 'intel', forceNative: true },
};
const adapterNames = {
  4090: /NVIDIA.*4090/i,
  3060: /NVIDIA.*RTX 3060\s*\(/i,
  intel: /Intel.*770/i,
};
const roomRoutes = {
  desk: null,
  case: {
    target: 'ROG Hyperion GR701 chassis',
    mode: 'case',
    caption: 'Look closer at the PC case',
  },
  window: { target: 'Window glass', mode: 'window', turn: -430 },
  cabinet: {
    target: 'NIKKOR Z 135mm f/1.8 S Plena · cabinet mount',
    mode: 'case',
    caption: 'Explore the collection cabinet',
    turn: -865,
  },
};
const weatherCodes = { clear: 0, rain: 61, snow: 71 };
const experiments = {
  '--deferred-books': ['studio-startup', 'deferred-books'],
  '--warm-preview': ['studio-preview', 'warm'],
  '--warm-oled': ['studio-preview', 'oled'],
  '--staged-preview-textures': ['studio-preview-textures', 'staged'],
  '--warm-buffers': ['studio-buffers', 'warm'],
  '--worker-parts': ['studio-parts', 'worker'],
  '--worker-meshopt': ['studio-meshopt', 'worker'],
  '--priority-rear': ['studio-rear', 'priority'],
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
  '--window-scissor': ['studio-window-clip', 'scissor'],
  '--eager-water-motion': ['studio-water-motion', 'eager'],
  '--bitmap-images': ['studio-images', 'bitmap'],
  '--incremental-warmup': ['studio-warmup', 'incremental'],
  '--paced-warmup': ['studio-warmup', 'paced'],
  '--catch-up-warmup': ['studio-warmup', 'catch-up'],
  '--adaptive-warmup': ['studio-warmup', 'adaptive'],
  '--culled-lights': ['studio-lighting', 'culled'],
  '--lean-lighting': ['studio-light-kernel', 'lean'],
  '--culled-all-lights': ['studio-lighting', 'culled-all'],
  '--matte-surfaces': ['studio-lighting', 'matte'],
  '--shared-reflections': ['studio-reflections', 'shared'],
  '--legacy-loader': ['studio-loader', 'legacy'],
  '--merge-first': ['studio-batching', 'merge-first'],
  '--transform-first': ['studio-batching', 'transform-first'],
};
const usage = `Usage: node scripts/performance/studio-benchmark.mjs [profiles] [run IDs] [options]

Profiles: 4k (default), 1440p, 3060, uhd-adaptive, uhd-native
List profiles or positive run IDs with commas. Run ID defaults to 1.
Example: node scripts/performance/studio-benchmark.mjs 4k,uhd-adaptive 1,2,3
Use --loader-profile to profile startup CPU work through loader removal.
Use --steady-profile to profile CPU work during the warmed desk turn.
Use --gpu-timing to sample main-color GPU work during the final steady route.
Use --repeat-desk to prime the shaders and geometry with one matched desk turn before sampling.
Use --seconds=<duration> to set the measured steady desk route duration (default 12).
Use --route=<${Object.keys(roomRoutes).join('|')}> and --weather=<${Object.keys(weatherCodes).join('|')}> to replay room views.
Use --loader-trace to capture compositor events and screenshots during loading.
Use --startup to exercise the first desk drag as soon as the loader disappears.
Combine --loader-profile and --startup to profile through the first ten seconds after the drag.
Add --full-room to wait for rear asset readiness on builds that report it.
Set --input-delay-ms=<milliseconds> to wait before the first drag.
Use --screenshot to save a full-viewport image after sampling.
Use --slow-draws to attribute individual draw calls taking longer than 50 ms.
Use --warm to prime the origin in the same browser context before measuring a reload.
Use --dist=<directory> to serve an alternate production build.
Experiment switches: ${Object.keys(experiments).join(', ')}.
Build first with npm run build. Use installed Chrome on Windows, with ANGLE D3D11.
Results go to .review/performance/<short commit>/. Matching run IDs are replaced.`;

function options(args) {
  const captured = new Set(args.filter((arg) => arg.startsWith('--')));
  const positional = args.filter((arg) => !captured.has(arg));
  const names = (positional[0] ?? '4k').split(',');
  const ids = (positional[1] ?? '1').split(',');
  const captureProfile = captured.delete('--loader-profile');
  const steadyProfile = captured.delete('--steady-profile');
  const gpuTiming = captured.delete('--gpu-timing');
  const loaderTrace = captured.delete('--loader-trace');
  const startup = captured.delete('--startup');
  const fullRoom = captured.delete('--full-room');
  const delayArgument = [...captured].find((arg) => arg.startsWith('--input-delay-ms='));
  captured.delete(delayArgument);
  const inputDelayMs = delayArgument ? Number(delayArgument.slice('--input-delay-ms='.length)) : 0;
  const screenshot = captured.delete('--screenshot');
  const slowDraws = captured.delete('--slow-draws');
  const warm = captured.delete('--warm');
  const repeatDesk = captured.delete('--repeat-desk');
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
    ((fullRoom || delayArgument) && !startup) ||
    !Number.isSafeInteger(inputDelayMs) ||
    inputDelayMs < 0 ||
    (captureProfile && screenshot) ||
    (gpuTiming && (captureProfile || steadyProfile || startup || loaderTrace || slowDraws)) ||
    (loaderTrace && (captureProfile || startup || screenshot || slowDraws)) ||
    (steadyProfile && (captureProfile || loaderTrace || startup || slowDraws)) ||
    ((repeatDesk || secondsArgument) && (captureProfile || loaderTrace || startup)) ||
    (route !== 'desk' && (captureProfile || loaderTrace || startup)) ||
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
    captureProfile,
    steadyProfile,
    gpuTiming,
    loaderTrace,
    startup,
    fullRoom,
    inputDelayMs,
    screenshot,
    slowDraws,
    warm,
    repeatDesk,
    seconds,
    route,
    weather,
    selected,
    dist,
  };
}

function browserArgs(adapter) {
  let luid = adapter === 'intel' ? process.env.INTEL_LUID : process.env.DISCRETE_LUID;
  if (adapter === 'intel' && !luid) {
    const query =
      "Get-ChildItem 'HKLM:/SOFTWARE/Microsoft/DirectX' | Get-ItemProperty | Where-Object { $_.Description -match 'Intel.*770' } | Select-Object -First 1 -ExpandProperty AdapterLuid";
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
  const args = ['--use-angle=d3d11', '--enable-gpu', '--mute-audio'];
  if (luid) args.push('--use-adapter-luid=' + luid);
  return args;
}

function installProbe({ quality, forceNative, startup, slowDraws, gpuTiming }) {
  performance.setResourceTimingBufferSize(1000);
  localStorage.setItem(
    'felix-studio-v1',
    JSON.stringify({
      quality,
      automaticQuality: false,
      weather: '晴',
      reducedMotion: false,
      rainAudio: false,
    }),
  );
  const sample = (window.studioBench = {
    roomFrames: [],
    submissions: [],
    rotations: [],
    loaderFrames: [],
    loaderProgress: [],
    resolutions: {},
    longTasks: [],
    ...(startup && { firstDrag: { frames: [] } }),
    ...(slowDraws && { slowDraws: [], slowTextureUploads: [] }),
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

  function attachGpuTiming(renderer) {
    const gl = renderer.getContext();
    const timer = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    if (!timer) return;
    const pending = [];
    const timings = (sample.mainColorGpu = { durations: [], discarded: 0 });
    let active = false;
    let inQuery = false;

    function poll() {
      if (!pending.length) return true;
      if (gl.getParameter(timer.GPU_DISJOINT_EXT)) {
        timings.discarded += pending.length;
        for (const query of pending.splice(0)) gl.deleteQuery(query);
        return true;
      }
      while (pending.length && gl.getQueryParameter(pending[0], gl.QUERY_RESULT_AVAILABLE)) {
        const query = pending.shift();
        timings.durations.push(gl.getQueryParameter(query, gl.QUERY_RESULT) / 1e6);
        gl.deleteQuery(query);
      }
      return pending.length === 0;
    }

    sample.beginGpuTiming = () => {
      active = true;
    };
    sample.finishGpuTiming = () => {
      active = false;
      return poll();
    };
    return {
      begin() {
        if (!active || inQuery || sample.roomFrames.length % 17) return null;
        poll();
        const query = gl.createQuery();
        if (!query) return null;
        gl.beginQuery(timer.TIME_ELAPSED_EXT, query);
        inQuery = true;
        return query;
      },
      end(query) {
        gl.endQuery(timer.TIME_ELAPSED_EXT);
        inQuery = false;
        pending.push(query);
      },
    };
  }

  window.__THREE_DEVTOOLS__ = new EventTarget();
  window.__THREE_DEVTOOLS__.addEventListener('observe', ({ detail: renderer }) => {
    if (!renderer.isWebGLRenderer) return;
    sample.renderer = renderer;
    const drag = sample.firstDrag;
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
    if (slowDraws) {
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
    let world, roomCamera;
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
      if (
        !world &&
        scene.isScene &&
        camera.isPerspectiveCamera &&
        scene.getObjectByName('Felix Studio')
      )
        world = scene;
      const frame = document.timeline.currentTime;
      const room = world === scene && camera.isPerspectiveCamera && !camera.parent?.isCubeCamera;
      if (room) roomCamera = camera;
      const primary =
        sample.recording && room && !scene.overrideMaterial && sample.roomFrames.at(-1) !== frame;
      const start = primary ? performance.now() : 0;
      const query = primary ? gpu?.begin() : null;
      let result;
      try {
        result = render.call(this, scene, camera);
      } finally {
        if (query) gpu.end(query);
      }
      if (drag && room) {
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
        sample.roomFrames.push(frame);
        sample.submissions.push(performance.now() - start);
        sample.rotations.push(camera.quaternion.y);
        sample.draws = renderer.info.render.calls;
        sample.tris = renderer.info.render.triangles;
        const target = renderer.getRenderTarget();
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

async function sampleStartup(page, profile, inputDelayMs) {
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
  await page.mouse.move(x + 96, y);
  const moved = performance.now();
  await page.mouse.up();
  const released = performance.now();
  await page.waitForFunction(
    () => performance.now() >= window.studioBench?.firstDrag?.move + 10000,
    null,
    { timeout: 20000 },
  );
  return {
    position: rounded(positioned - start),
    press: rounded(pressed - positioned),
    move: rounded(moved - pressed),
    release: rounded(released - moved),
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
    await page.mouse.move(origin.x + route.turn, origin.y);
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
  startProfile,
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
      sample.resolutions = {};
      return { roomFrames, submissions };
    });
    await page.waitForTimeout(1000);
  }
  await startProfile?.();
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
    !adapterNames[profile.adapter].test(raw.gpu) ||
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
      throw new Error(
        'The first desk drag produced no measurable change in submitted room frames.',
      );
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
    loaderTrace,
    startup,
    fullRoom,
    inputDelayMs,
    screenshot,
    slowDraws,
    selected,
    dist,
    warm,
    repeatDesk,
    seconds,
    route,
    weather,
  } = settings;
  const profile = profiles[name];
  const url = new URL(base);
  for (const flag of selected) url.searchParams.set(...experiments[flag]);
  const args = browserArgs(profile.adapter);
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args });
  try {
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
    const weatherFixture = { current: { weather_code: weatherCodes[weather], is_day: 0 } };
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
    await page.addInitScript(installProbe, { ...profile, startup, slowDraws, gpuTiming });
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
    if (startup) automationCommandMs = await sampleStartup(page, profile, inputDelayMs);
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
      const startProfile = steadyProfile ? () => cdp.send('Profiler.start') : undefined;
      firstTurn = await sampleDesk(page, profile, settings, startProfile);
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
    checkSamples(raw, profile, settings);
    const summary = {
      variant: name,
      run,
      head,
      time: new Date().toISOString(),
      node: process.version,
      chrome: browser.version(),
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
      ...(slowDraws && {
        slowDraws: raw.slowDraws.length,
        slowTextureUploads: raw.slowTextureUploads.length,
      }),
    };
    const stem = join(
      directory,
      [
        captureProfile && 'loader-profile',
        steadyProfile && 'steady-profile',
        gpuTiming && 'gpu-timing',
        loaderTrace && 'loader-trace',
        startup && 'startup',
        inputDelayMs > 0 && `input-delay-${inputDelayMs}ms`,
        slowDraws && 'slow-draws',
        warm && 'warm',
        repeatDesk && 'repeat-desk',
        seconds !== 12 && `${seconds}s`,
        route !== 'desk' && route,
        weather !== 'clear' && weather,
        name,
        ...selected.map((flag) => flag.slice(2)),
        run,
      ]
        .filter(Boolean)
        .join('-'),
    );
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
    if (cpuProfile) {
      summary.navigationStartMonotonicSeconds = navigationStart;
      summary.sampledIntervalMicroseconds = 1000;
      writeFileSync(stem + '.cpuprofile.gz', gzipSync(JSON.stringify(cpuProfile)));
    }
    if (captureProfile) {
      if (startup) Object.assign(summary, startupSummary(raw, automationCommandMs));
      writeFileSync(stem + '.meta.json', JSON.stringify({ ...raw, ...summary }, null, 2));
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
    await browser.close();
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

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
