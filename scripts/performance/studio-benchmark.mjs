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
const usage = `Usage: node scripts/performance/studio-benchmark.mjs [profiles] [run IDs] [--loader-profile]

Profiles: 4k (default), 1440p, 3060, uhd-adaptive, uhd-native
List profiles or positive run IDs with commas. Run ID defaults to 1.
Example: node scripts/performance/studio-benchmark.mjs 4k,uhd-adaptive 1,2,3
Use --loader-profile to capture startup CPU samples instead of the desk route.
Build first with npm run build. Use installed Chrome on Windows, with ANGLE D3D11.
Results go to .review/performance/<short commit>/. Matching run IDs are replaced.`;

function options(args) {
  const positional = args.filter((arg) => arg !== '--loader-profile');
  const names = (positional[0] ?? '4k').split(',');
  const ids = (positional[1] ?? '1').split(',');
  if (
    positional.length > 2 ||
    names.some((name) => !Object.hasOwn(profiles, name)) ||
    ids.some((id) => !/^[1-9]\d*$/.test(id) || !Number.isSafeInteger(Number(id))) ||
    new Set(names).size !== names.length ||
    new Set(ids).size !== ids.length
  )
    throw new Error(usage);
  return { names, runs: ids.map(Number), captureProfile: args.includes('--loader-profile') };
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

function installProbe({ quality, forceNative }) {
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
    if (forceNative) {
      const setRatio = renderer.setPixelRatio.bind(renderer);
      renderer.setPixelRatio = () => setRatio(1);
      setRatio(1);
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
      const primary =
        sample.recording &&
        world === scene &&
        camera.isPerspectiveCamera &&
        !camera.parent?.isCubeCamera &&
        !scene.overrideMaterial &&
        sample.roomFrames.at(-1) !== frame;
      const start = primary ? performance.now() : 0;
      const result = render.call(this, scene, camera);
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
  return {
    ...raw,
    gpu: info && gl.getParameter(info.UNMASKED_RENDERER_WEBGL),
    motion: rotations.length ? Math.max(...rotations) - Math.min(...rotations) : 0,
    marks: Object.fromEntries(
      performance
        .getEntriesByType('mark')
        .filter((e) => e.name.startsWith('studio'))
        .map((e) => [e.name, e.startTime]),
    ),
    chunk: performance
      .getEntriesByType('resource')
      .map((e) => new URL(e.name).pathname)
      .find((path) => path.startsWith('/assets/StudioView-') && path.endsWith('.js')),
  };
}

async function sampleDesk(page, { width, height }) {
  await page.waitForFunction(
    () => performance.getEntriesByName('studio-room-shaded').length > 0,
    null,
    { timeout: 120000 },
  );
  await page.waitForTimeout(5000);
  const origin = { x: Math.round(width * 0.48), y: Math.round(height * 0.36) };
  await page.mouse.move(origin.x, origin.y);
  await page.mouse.down();
  await page.evaluate(
    ({ x, y }) =>
      new Promise((done) => {
        let start;
        function tick(time) {
          start ??= time;
          const elapsed = time - start;
          const sample = window.studioBench;
          sample.recording = elapsed > 2000 && elapsed < 14000;
          const phase = elapsed / 1500;
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
    origin,
  );
  await page.mouse.up();
}

function checkSamples(raw, profile, captureProfile) {
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
  if (captureProfile) return;
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

async function measure({ base, directory, head, name, run, captureProfile }) {
  const profile = profiles[name];
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
    page.on('response', (response) => {
      if (response.status() >= 400) issues.push(response.status() + ' ' + response.url());
    });
    page.on('requestfailed', (request) =>
      issues.push(request.failure()?.errorText + ' ' + request.url()),
    );
    await page.route(/^https:\/\//, (route) => {
      if (new URL(route.request().url()).hostname === 'api.open-meteo.com')
        return route.fulfill({ json: { current: { weather_code: 0, is_day: 0 } } });
      return route.abort();
    });
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await page.addInitScript(installProbe, profile);
    if (captureProfile) {
      await cdp.send('Performance.enable');
      await cdp.send('Profiler.enable');
      await cdp.send('Profiler.setSamplingInterval', { interval: 1000 });
      await cdp.send('Profiler.start');
    }
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    let cpuProfile, navigationStart;
    if (captureProfile) {
      await page.waitForFunction(() => window.studioBench?.loaderEnd > 0, null, {
        timeout: 120000,
      });
      cpuProfile = (await cdp.send('Profiler.stop')).profile;
      const { metrics } = await cdp.send('Performance.getMetrics');
      navigationStart = metrics.find((m) => m.name === 'NavigationStart')?.value;
      if (!cpuProfile.samples.length || !navigationStart)
        throw new Error('Startup CPU samples or navigation clock unavailable.');
    } else await sampleDesk(page, profile);
    const raw = await page.evaluate(readSamples);
    checkSamples(raw, profile, captureProfile);
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
      chunk: raw.chunk,
      chunkSHA256: createHash('sha256')
        .update(readFileSync(join('dist', raw.chunk)))
        .digest('hex'),
      visible: raw.visible,
      visibilityChanged: raw.visibilityChanged,
      issues,
      args,
      profile,
    };
    const stem = join(directory, (captureProfile ? 'loader-profile-' : '') + name + '-' + run);
    if (captureProfile) {
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
        resolutions: raw.resolutions,
        room: stats(intervals(raw.roomFrames)),
        primarySubmitP95: stats(raw.submissions).p95,
        draws: raw.draws,
        tris: raw.tris,
        motion: raw.motion,
        loader: stats(intervals([raw.loaderStart, ...raw.loaderFrames, raw.loaderEnd])),
        loaderStart: rounded(raw.loaderStart),
        loaderEnd: rounded(raw.loaderEnd),
        loaderLongTaskMax: Math.max(0, ...loaderTasks.map(([, duration]) => duration)),
        marks: raw.marks,
      });
      writeFileSync(stem + '.json', JSON.stringify({ summary, raw }, null, 2));
    }
    console.log(stem, JSON.stringify(summary));
    if (issues.length) throw new Error('Browser issues were recorded in the measurement output.');
  } finally {
    await browser.close();
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) return console.log(usage);
  const { names, runs, captureProfile } = options(args);
  if (!existsSync('dist/index.html'))
    throw new Error('Run npm run build from the website root first.');
  const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const directory = join('.review', 'performance', head.slice(0, 7));
  mkdirSync(directory, { recursive: true });
  const server = await preview({ configFile: false, preview: { host: '127.0.0.1', port: 0 } });
  const base = 'http://127.0.0.1:' + server.httpServer.address().port;
  try {
    for (const run of runs)
      for (const name of names) await measure({ base, directory, head, name, run, captureProfile });
  } finally {
    await server.close();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
