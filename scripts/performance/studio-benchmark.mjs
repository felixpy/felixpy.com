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
const experiments = {
  '--deferred-books': ['studio-startup', 'deferred-books'],
  '--warm-preview': ['studio-preview', 'warm'],
  '--warm-buffers': ['studio-buffers', 'warm'],
  '--worker-parts': ['studio-parts', 'worker'],
  '--worker-meshopt': ['studio-meshopt', 'worker'],
  '--priority-rear': ['studio-rear', 'priority'],
  '--native-low': ['studio-low', 'native'],
  '--sliced-build': ['studio-build', 'sliced'],
  '--photo-fasteners': ['studio-photo-fasteners', 'instanced'],
  '--preload-details': ['studio-details', 'preload'],
  '--simple-low': ['studio-low-shading', 'simple'],
  '--fused-output': ['studio-output', 'fused'],
  '--legacy-output': ['studio-output', 'legacy'],
  '--stable-effects': ['studio-effects', 'stable'],
  '--incremental-warmup': ['studio-warmup', 'incremental'],
  '--culled-lights': ['studio-lighting', 'culled'],
  '--legacy-loader': ['studio-loader', 'legacy'],
  '--merge-first': ['studio-batching', 'merge-first'],
  '--transform-first': ['studio-batching', 'transform-first'],
};
const usage = `Usage: node scripts/performance/studio-benchmark.mjs [profiles] [run IDs] [options]

Profiles: 4k (default), 1440p, 3060, uhd-adaptive, uhd-native
List profiles or positive run IDs with commas. Run ID defaults to 1.
Example: node scripts/performance/studio-benchmark.mjs 4k,uhd-adaptive 1,2,3
Use --loader-profile to profile startup CPU work through loader removal.
Use --loader-trace to capture compositor events and screenshots during loading.
Use --startup to exercise the first desk drag as soon as the loader disappears.
Combine both to extend CPU profiling through the first ten seconds after the drag.
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
  const loaderTrace = captured.delete('--loader-trace');
  const startup = captured.delete('--startup');
  const screenshot = captured.delete('--screenshot');
  const slowDraws = captured.delete('--slow-draws');
  const warm = captured.delete('--warm');
  const selected = Object.keys(experiments).filter((flag) => captured.delete(flag));
  const distArgument = [...captured].find((arg) => arg.startsWith('--dist='));
  captured.delete(distArgument);
  const dist = distArgument ? distArgument.slice('--dist='.length) : 'dist';
  if (
    positional.length > 2 ||
    captured.size ||
    !dist ||
    (captureProfile && screenshot) ||
    (loaderTrace && (captureProfile || startup || screenshot || slowDraws)) ||
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
    loaderTrace,
    startup,
    screenshot,
    slowDraws,
    warm,
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

function installProbe({ quality, forceNative, startup, slowDraws }) {
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
    resolutions: {},
    longTasks: [],
    ...(startup && { firstDrag: { frames: [] } }),
    ...(slowDraws && { slowDraws: [] }),
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
    const attached = !!document.querySelector('.studio-loading');
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
  observer.observe(document, { subtree: true, childList: true });
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
    let world;
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
      const primary =
        sample.recording && room && !scene.overrideMaterial && sample.roomFrames.at(-1) !== frame;
      const start = primary ? performance.now() : 0;
      const result = render.call(this, scene, camera);
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
  const { renderer, rotations, recording, ...raw } = window.studioBench;
  const gl = renderer.getContext();
  const info = gl.getExtension('WEBGL_debug_renderer_info');
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

async function sampleStartup(page, profile) {
  await page.waitForFunction(() => window.studioBench?.loaderEnd > 0, null, {
    timeout: 120000,
  });
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

async function sampleDesk(page, profile, screenshot) {
  await waitForShading(page);
  await page.waitForTimeout(5000);
  const origin = deskOrigin(profile);
  await page.mouse.move(origin.x, origin.y);
  await page.mouse.down();
  await page.evaluate(
    ({ x, y, screenshot }) =>
      new Promise((done) => {
        let start;
        function tick(time) {
          start ??= time;
          const elapsed = time - start;
          const sample = window.studioBench;
          sample.recording = elapsed > 2000 && elapsed < 14000;
          const phase = screenshot && elapsed >= 14000 ? 0 : elapsed / 1500;
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
          if (elapsed >= 14000) done();
          else requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      }),
    { ...origin, screenshot },
  );
  await page.mouse.up();
  if (screenshot) await page.waitForTimeout(500);
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
  return {
    loaderEndToPressMs: rounded(press - raw.loaderEnd),
    loaderEndToMoveMs: rounded(move - raw.loaderEnd),
    loaderEndToChangedRoomSubmitMs: rounded(changedSubmit - raw.loaderEnd),
    pressDispatchMs: rounded(pressDispatch - press),
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
  const { captureProfile, loaderTrace, startup, screenshot, slowDraws, selected, dist, warm } =
    settings;
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
    const weather = { current: { weather_code: 0, is_day: 0 } };
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
              body: Buffer.from(JSON.stringify(weather)).toString('base64'),
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
          return route.fulfill({ json: weather });
        return route.abort();
      });
    }
    await page.addInitScript(installProbe, { ...profile, startup, slowDraws });
    if (warm) {
      await page.goto(url.href, { waitUntil: 'domcontentloaded' });
      await waitForShading(page);
      await page.waitForLoadState('networkidle', { timeout: 120000 });
      cachedRequests.clear();
      revalidatedRequests.clear();
    }
    if (captureProfile || loaderTrace) await cdp.send('Performance.enable');
    if (captureProfile) {
      await cdp.send('Profiler.enable');
      await cdp.send('Profiler.setSamplingInterval', { interval: 1000 });
      await cdp.send('Profiler.start');
    }
    const stopTrace = loaderTrace ? await traceLoader(cdp) : undefined;
    if (warm) await page.reload({ waitUntil: 'domcontentloaded' });
    else await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    let cpuProfile, compositorTrace, navigationStart, automationCommandMs;
    if (startup) automationCommandMs = await sampleStartup(page, profile);
    if (stopTrace) {
      await page.waitForFunction(() => window.studioBench?.loaderEnd > 0, null, {
        timeout: 120000,
      });
      compositorTrace = await stopTrace();
      const { metrics } = await cdp.send('Performance.getMetrics');
      navigationStart = metrics.find((metric) => metric.name === 'NavigationStart')?.value;
      if (!navigationStart) throw new Error('The compositor trace has no navigation clock.');
    }
    if (captureProfile) {
      if (!startup)
        await page.waitForFunction(() => window.studioBench?.loaderEnd > 0, null, {
          timeout: 120000,
        });
      cpuProfile = (await cdp.send('Profiler.stop')).profile;
      const { metrics } = await cdp.send('Performance.getMetrics');
      navigationStart = metrics.find((m) => m.name === 'NavigationStart')?.value;
      if (!cpuProfile.samples.length || !navigationStart)
        throw new Error('Startup CPU samples or navigation clock unavailable.');
    }
    if (startup) await waitForShading(page);
    else if (!captureProfile && !loaderTrace) await sampleDesk(page, profile, screenshot);
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
      experiments: Object.fromEntries(url.searchParams),
      ...(slowDraws && { slowDraws: raw.slowDraws.length }),
    };
    const stem = join(
      directory,
      [
        captureProfile && 'loader-profile',
        loaderTrace && 'loader-trace',
        startup && 'startup',
        slowDraws && 'slow-draws',
        warm && 'warm',
        name,
        ...selected.map((flag) => flag.slice(2)),
        run,
      ]
        .filter(Boolean)
        .join('-'),
    );
    if (captureProfile) {
      if (startup) Object.assign(summary, startupSummary(raw, automationCommandMs));
      writeFileSync(stem + '.cpuprofile.gz', gzipSync(JSON.stringify(cpuProfile)));
      writeFileSync(
        stem + '.meta.json',
        JSON.stringify(
          {
            ...raw,
            ...summary,
            navigationStartMonotonicSeconds: navigationStart,
            sampledIntervalMicroseconds: 1000,
          },
          null,
          2,
        ),
      );
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
        });
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
