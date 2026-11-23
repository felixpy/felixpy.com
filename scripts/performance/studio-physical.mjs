import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  closeSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { parseArgs } from 'node:util';
import { chromium } from '@playwright/test';
import { preview } from 'vite';
import {
  adapterNames,
  browserArgs,
  installProbe,
  profiles,
  turnDesk,
  waitForShading,
} from './studio-benchmark.mjs';

const usage = `Usage:
  node scripts/performance/studio-physical.mjs --dry-run --display='\\\\.\\DISPLAY1' --witness=EXE [options]
  node scripts/performance/studio-physical.mjs --capture --display='\\\\.\\DISPLAY1' --witness=EXE [options]
  node scripts/performance/studio-physical.mjs --measure --display='\\\\.\\DISPLAY1' --witness=EXE [options]

Options: --dist=DIR --presentmon=EXE
Capture and measurement open a private foreground Chrome kiosk on the single active 4K 144 Hz
display. Keep it clear for warmup and capture. PresentMon may need additional OS permissions.
The witness records marker metadata from a 160×4 native pixel ROI. No desktop images are saved.
Use --capture for calibration with PresentMon. Use --measure to report a 60-second observed
scene cadence lower bound from DXGI without PresentMon. Neither mode certifies release cadence.`;

const root = resolve(import.meta.dirname, '../..');
const profile = profiles['4k'];
const roi = { x: 32, y: 32, width: 160, height: 4 };
const phases = { movingMs: 4000, heldMs: 2000, resumedMs: 4000 };
const displayProbe = String.raw`
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.ComponentModel;
public static class StudioDisplayProbe {
  [StructLayout(LayoutKind.Sequential)]
  public struct Luid { public uint Low; public int High; }
  [StructLayout(LayoutKind.Sequential)]
  public struct Ratio { public uint Numerator, Denominator; }
  [StructLayout(LayoutKind.Sequential)]
  public struct Source { public Luid Adapter; public uint Id, Mode, Status; }
  [StructLayout(LayoutKind.Sequential)]
  public struct Target {
    public Luid Adapter;
    public uint Id, Mode, Technology, Rotation, Scaling;
    public Ratio Refresh;
    public uint Scanline, Available, Status;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct Path { public Source Source; public Target Target; public uint Flags; }
  [StructLayout(LayoutKind.Explicit, Size = 64)]
  public struct Mode {
    [FieldOffset(0)] public uint Type;
    [FieldOffset(16)] public uint Width;
    [FieldOffset(20)] public uint Height;
    [FieldOffset(28)] public int X;
    [FieldOffset(32)] public int Y;
    [FieldOffset(32)] public Ratio SignalRefresh;
    [FieldOffset(40)] public uint SignalWidth;
    [FieldOffset(44)] public uint SignalHeight;
  }
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct SourceName {
    public uint Type, Size;
    public Luid Adapter;
    public uint Id;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string Name;
  }
  [DllImport("user32.dll")]
  private static extern int GetDisplayConfigBufferSizes(uint flags, out uint paths, out uint modes);
  [DllImport("user32.dll")]
  private static extern int QueryDisplayConfig(uint flags, ref uint pathCount, [Out] Path[] paths,
      ref uint modeCount, [Out] Mode[] modes, IntPtr topology);
  [DllImport("user32.dll")]
  private static extern int DisplayConfigGetDeviceInfo(ref SourceName name);
  private static void Check(int status, string operation) {
    if (status != 0) throw new Win32Exception(status, operation + " failed with Win32 error " + status);
  }
  public static object Read() {
    const uint activePaths = 0x2, virtualModeAware = 0x10, virtualRefreshAware = 0x40;
    const uint flags = activePaths | virtualModeAware | virtualRefreshAware;
    uint pathCount, modeCount;
    Check(GetDisplayConfigBufferSizes(flags, out pathCount, out modeCount), "GetDisplayConfigBufferSizes");
    Path[] paths = new Path[pathCount];
    Mode[] modes = new Mode[modeCount];
    Check(QueryDisplayConfig(flags, ref pathCount, paths, ref modeCount, modes, IntPtr.Zero),
      "QueryDisplayConfig");
    if (pathCount != 1) throw new InvalidOperationException("Exactly one active display path is required.");
    Path path = paths[0];
    bool virtualMode = (path.Flags & 8) != 0;
    uint sourceIndex = virtualMode ? path.Source.Mode >> 16 : path.Source.Mode;
    uint targetIndex = virtualMode ? path.Target.Mode >> 16 : path.Target.Mode;
    if (sourceIndex >= modeCount || targetIndex >= modeCount ||
        modes[sourceIndex].Type != 1 || modes[targetIndex].Type != 2)
      throw new InvalidOperationException("Active source and signal modes were not available.");
    SourceName device = new SourceName { Type = 1, Size = (uint)Marshal.SizeOf(typeof(SourceName)),
      Adapter = path.Source.Adapter, Id = path.Source.Id };
    Check(DisplayConfigGetDeviceInfo(ref device), "DisplayConfigGetDeviceInfo");
    Mode source = modes[sourceIndex];
    Mode target = modes[targetIndex];
    return new {
      name = device.Name,
      desktop = new[] { source.Width, source.Height },
      signal = new[] { target.SignalWidth, target.SignalHeight },
      origin = new[] { source.X, source.Y },
      refresh = new[] { path.Target.Refresh.Numerator, path.Target.Refresh.Denominator },
      signalRefresh = new[] { target.SignalRefresh.Numerator, target.SignalRefresh.Denominator },
      rotation = path.Target.Rotation,
      scanline = path.Target.Scanline,
      adapterLuid = path.Target.Adapter.High + "," + path.Target.Adapter.Low
    };
  }
}
'@
[StudioDisplayProbe]::Read() | ConvertTo-Json -Compress
`;

function readDisplay() {
  return JSON.parse(
    execFileSync(
      'powershell.exe',
      [
        '-NoProfile',
        '-NonInteractive',
        '-EncodedCommand',
        Buffer.from(displayProbe, 'utf16le').toString('base64'),
      ],
      { encoding: 'utf8', timeout: 15000, windowsHide: true },
    ),
  );
}

function settings(args) {
  const { values } = parseArgs({
    args,
    options: {
      help: { type: 'boolean', short: 'h' },
      'dry-run': { type: 'boolean' },
      capture: { type: 'boolean' },
      measure: { type: 'boolean' },
      display: { type: 'string' },
      dist: { type: 'string', default: join(root, 'dist') },
      presentmon: { type: 'string' },
      witness: { type: 'string' },
    },
  });
  if (!args.length || values.help) return;
  if (
    [values['dry-run'], values.capture, values.measure].filter(Boolean).length !== 1 ||
    !/^\\\\\.\\DISPLAY[1-9]\d*$/i.test(values.display ?? '')
  )
    throw new Error('Select one mode and explicitly name the display.\n' + usage);
  if (process.platform !== 'win32') throw new Error('Physical capture requires Windows.');
  let presentMon;
  if (!values.measure)
    presentMon =
      values.presentmon ??
      [process.env.ProgramW6432, process.env.ProgramFiles]
        .filter(Boolean)
        .map((directory) =>
          join(directory, 'NVIDIA Corporation/FrameViewSDK/bin/PresentMon_x64.exe'),
        )
        .find(existsSync);
  if (!values.witness)
    throw new Error('Pass --witness=EXE with a compatible DXGI witness executable.');
  const witness = resolve(values.witness);
  const dist = resolve(values.dist);
  const inputs = [witness, join(dist, 'index.html')];
  if (!values.measure) inputs.push(presentMon);
  for (const path of inputs)
    if (!path || !existsSync(path) || !statSync(path).isFile())
      throw new Error('Missing capture input: ' + (path ?? 'PresentMon. Supply --presentmon=EXE.'));
  const assets = join(dist, 'assets');
  const buildHasHold =
    existsSync(assets) &&
    readdirSync(assets).some(
      (file) =>
        /^room-frame-marker-.*\.js$/.test(file) &&
        readFileSync(join(assets, file), 'utf8').includes('studioPresentWitness'),
    );
  if ((values.capture || values.measure) && !buildHasHold)
    throw new Error('The selected production build lacks the frame marker. Rebuild the website.');
  const display = readDisplay();
  const native = [profile.width, profile.height].join(',');
  if (
    display.name.toUpperCase() !== values.display.toUpperCase() ||
    display.desktop.join(',') !== native ||
    display.signal.join(',') !== native ||
    display.origin.join(',') !== '0,0' ||
    display.rotation !== 1 ||
    display.scanline !== 1 ||
    [display.refresh, display.signalRefresh].some(([n, d]) => !d || Math.abs(n / d - 144) > 0.05)
  )
    throw new Error(
      'Expected the selected unrotated native 4K 144 Hz display: ' + JSON.stringify(display),
    );
  return {
    capture: values.capture,
    measure: values.measure,
    display,
    dist,
    buildHasHold,
    presentMon: presentMon && resolve(presentMon),
    witness,
  };
}

function presentArgs(pid, seconds, path, session) {
  return [
    '--process_id',
    String(pid),
    '--v1_metrics',
    '--qpc_time_ms',
    '--no_track_input',
    '--no_console_stats',
    '--timed',
    String(seconds),
    '--terminate_after_timed',
    '--terminate_on_proc_exit',
    '--session_name',
    session,
    '--output_file',
    path,
  ];
}

function tool(executable, args, seconds, stderrPath, stdoutPath = stderrPath) {
  const stdout = openSync(stdoutPath, 'w');
  let stderr = stdout;
  let child;
  try {
    if (stdoutPath !== stderrPath) stderr = openSync(stderrPath, 'w');
    child = spawn(executable, args, { windowsHide: true, stdio: ['ignore', stdout, stderr] });
  } finally {
    closeSync(stdout);
    if (stdout !== stderr) closeSync(stderr);
  }
  let finished = false;
  const timeout = setTimeout(() => child.kill(), (seconds + 6) * 1000);
  const result = new Promise((done) => {
    child.once('error', (error) => done({ error: error.message }));
    child.once('close', (code, signal) => done({ code, signal }));
  }).then((exit) => {
    clearTimeout(timeout);
    finished = true;
    return exit;
  });
  return {
    result,
    get finished() {
      return finished;
    },
    stop() {
      if (!finished) child.kill();
    },
  };
}

function analysis(script, args) {
  return JSON.parse(
    execFileSync(process.execPath, [join(import.meta.dirname, script), ...args], {
      encoding: 'utf8',
      timeout: 15000,
      windowsHide: true,
    }),
  );
}

function captureFailure(name, exit, log) {
  return new Error(`${name} failed (${JSON.stringify(exit)}). See ${log}.`);
}

async function canvasState(page, trackFocus = false) {
  return page.evaluate(
    ({ x, y, width, height, trackFocus }) => {
      const sample = window.studioBench;
      if (!sample?.renderer) throw new Error('The room renderer is unavailable.');
      const { renderer, resolutions, visibilityChanged, rotations } = sample;
      if (trackFocus)
        window.addEventListener(
          'blur',
          () => {
            sample.focusLost = true;
          },
          { once: true },
        );
      const gl = renderer.getContext();
      const info = gl.getExtension('WEBGL_debug_renderer_info');
      const bounds = renderer.domElement.getBoundingClientRect();
      const meter = document.querySelector('.fps-meter')?.getBoundingClientRect();
      return {
        canvas: [bounds.left, bounds.top, bounds.width, bounds.height],
        drawingBuffer: [gl.drawingBufferWidth, gl.drawingBufferHeight],
        screen: [screenX, screenY, screen.width, screen.height],
        devicePixelRatio,
        gpu: info && gl.getParameter(info.UNMASKED_RENDERER_WEBGL),
        clearRoi:
          !meter ||
          meter.right <= x ||
          meter.left >= x + width ||
          meter.bottom <= y ||
          meter.top >= y + height,
        visible:
          document.visibilityState === 'visible' &&
          document.hasFocus() &&
          !visibilityChanged &&
          !sample.focusLost,
        resolutions: Object.keys(resolutions),
        expectedSamples: Math.min(4, renderer.capabilities.maxSamples),
        quality: JSON.parse(localStorage.getItem('felix-studio-v1') ?? '{}').quality,
        motion: rotations.length ? Math.max(...rotations) - Math.min(...rotations) : 0,
      };
    },
    { ...roi, trackFocus },
  );
}

function checkCanvas(state, sampled = false) {
  const native = `${profile.width},${profile.height}`;
  const fullscreen = '0,0,' + native;
  if (
    !state.visible ||
    !state.clearRoi ||
    state.devicePixelRatio !== 1 ||
    state.canvas.join(',') !== fullscreen ||
    state.screen.join(',') !== fullscreen ||
    state.drawingBuffer.join(',') !== native ||
    state.quality !== 'high' ||
    !adapterNames[profile.adapter].test(state.gpu) ||
    (sampled &&
      (!state.motion ||
        !state.resolutions.length ||
        state.resolutions.some((size) => size !== `${native},${native},${state.expectedSamples}`)))
  )
    throw new Error(
      'Expected foreground native 4K high rendering on RTX 4090: ' + JSON.stringify(state),
    );
}

async function calibrationHold(page) {
  return page.evaluate(async ({ movingMs, heldMs, resumedMs }) => {
    const { studioPresentWitness: witness } = window;
    const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
    async function waitHeld(held) {
      const start = performance.now();
      while (witness.held !== held && performance.now() - start < 1000) await sleep(10);
      if (witness.held !== held)
        throw new Error('The final output did not acknowledge marker hold.');
      return { serial: witness.serial, time: performance.now() };
    }
    await sleep(movingMs);
    witness.hold = true;
    let held, resumed;
    try {
      held = await waitHeld(true);
      await sleep(heldMs);
      if (held.serial !== witness.serial) throw new Error('Marker advanced during its hold.');
    } finally {
      witness.hold = false;
    }
    resumed = await waitHeld(false);
    await sleep(resumedMs);
    return { held, resumed, end: { serial: witness.serial, time: performance.now() } };
  }, phases);
}

function witnessFrames(path) {
  return readFileSync(path, 'utf8')
    .trim()
    .split(/\r?\n/)
    .map((line) => JSON.parse(line))
    .filter((entry) => entry.type === 'frame' && entry.status !== 'mouse_only');
}

function witnessReport(path, display, args = []) {
  const report = analysis('studio-witness.mjs', [path, ...args]);
  if (
    report.output.toUpperCase() !== display.name.toUpperCase() ||
    report.outputPixels.join(',') !== display.signal.join(',') ||
    Object.keys(roi).some((key) => report.roi[key] !== roi[key])
  )
    throw new Error('The witness captured an unexpected output or ROI.');
  return report;
}

function holdWitness(path, report, hold) {
  const heldSerial = hold.held.serial;
  const resumedSerial = hold.resumed.serial;
  const frames = witnessFrames(path);
  const held = frames.filter((frame) => frame.status === 'valid' && frame.sequence === heldSerial);
  const first = held.length ? frames.indexOf(held[0]) : 0;
  const last = held.length ? frames.indexOf(held.at(-1)) : frames.length - 1;
  const before = frames.slice(0, first).filter(({ status }) => status === 'valid');
  const after = frames.slice(last + 1).filter(({ status }) => status === 'valid');
  const distinctBefore = new Set(before.map(({ sequence }) => sequence)).size;
  const distinctAfter = new Set(after.map(({ sequence }) => sequence)).size;
  const resumeDeadline =
    (held.length ? BigInt(held.at(-1).lastPresentQpc) : 0n) + BigInt(report.qpcFrequency) / 2n;
  const resumedSerialObserved =
    resumedSerial !== heldSerial &&
    after.some(
      ({ sequence, lastPresentQpc }) =>
        sequence === resumedSerial && BigInt(lastPresentQpc) <= resumeDeadline,
    );
  const spanMs =
    held.length > 1
      ? (Number(BigInt(held.at(-1).lastPresentQpc) - BigInt(held[0].lastPresentQpc)) /
          Number(report.qpcFrequency)) *
        1000
      : 0;
  return {
    serial: heldSerial,
    observations: held.length,
    spanMs,
    distinctBefore,
    distinctAfter,
    resumedSerial,
    resumedSerialObserved,
    observed:
      held.length > 1 &&
      last - first + 1 === held.length &&
      spanMs >= phases.heldMs / 2 &&
      distinctBefore > 1 &&
      distinctAfter > 1 &&
      resumedSerialObserved,
  };
}

async function primeDesk(page) {
  await turnDesk(page, profile, 14000, true);
  await page.waitForTimeout(1000);
  await page.evaluate(() => {
    window.studioBench.resolutions = {};
    window.studioBench.rotations = [];
  });
  checkCanvas(await canvasState(page));
}

async function measureDesk(page, browserVersion, configuration, directory, captureWitness) {
  const { display, dist } = configuration;
  const motion = turnDesk(page, profile, 73000, false);
  const motionEnded = motion.then(() => {
    throw new Error('Desk motion ended before the witness capture was verified.');
  });
  await Promise.race([
    motionEnded,
    page.waitForFunction(() => window.studioBench.recording, null, { timeout: 10000 }),
  ]);
  const { entry, path, log } = captureWitness(65);
  const exit = await Promise.race([motionEnded, entry.result]);
  if (exit.code !== 0 && exit.code !== 2) throw captureFailure('DXGI witness', exit, log);
  const state = await Promise.race([motionEnded, canvasState(page)]);
  checkCanvas(state, true);
  if (state.expectedSamples !== 4) throw new Error('Expected 4× MSAA during measurement.');
  await motion;
  if (JSON.stringify(readDisplay()) !== JSON.stringify(display))
    throw new Error('The active output mode changed across the measurement window.');

  const report = witnessReport(path, display, ['--start=2', '--seconds=60']);
  const frames = witnessFrames(path).filter(({ status }) => status === 'valid');
  const begin = BigInt(report.window.startQpc);
  const end = BigInt(report.window.endQpc);
  const windowBracketed =
    frames.some(({ lastPresentQpc }) => BigInt(lastPresentQpc) < begin) &&
    frames.some(({ lastPresentQpc }) => BigInt(lastPresentQpc) >= end);
  const observedSceneFramesPerSecondLowerBound = windowBracketed
    ? (report.observedSceneFramesPerSecondLowerBound ?? null)
    : null;
  const chunk = await page.evaluate(() => {
    for (const { name } of performance.getEntriesByType('resource')) {
      const url = new URL(name);
      if (url.origin === location.origin && /^\/assets\/StudioView-[\w-]+\.js$/.test(url.pathname))
        return url.pathname;
    }
  });
  if (!chunk) throw new Error('The loaded StudioView production chunk was not recorded.');
  const result = {
    mode: 'measure',
    route: 'desk',
    browserVersion,
    chunk,
    chunkSHA256: createHash('sha256')
      .update(readFileSync(join(dist, chunk)))
      .digest('hex'),
    display,
    state,
    windowBracketed,
    witnessExitCode: exit.code,
    observedSceneFramesPerSecondLowerBound,
    witness: report,
    etwFramesCorrelated: false,
    certified: false,
  };
  const resultPath = join(directory, 'measurement.json');
  writeFileSync(resultPath, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ path: resultPath, observedSceneFramesPerSecondLowerBound }));
  if (!Number.isFinite(observedSceneFramesPerSecondLowerBound))
    throw new Error('No observed scene-cadence bound was available. See ' + resultPath);
}

async function run(configuration, directory) {
  const { dist, display, presentMon, witness } = configuration;
  const server = await preview({
    configFile: false,
    build: { outDir: dist },
    preview: { host: '127.0.0.1', port: 0 },
  });
  const url = new URL('http://127.0.0.1:' + server.httpServer.address().port);
  url.searchParams.set('studio-present-witness', 'roi');
  const captures = [];
  const session = `FelixStudioPhysical-${process.pid}-${Date.now()}`;
  let browser, desktop;
  function captureWitness(seconds) {
    const path = join(directory, 'witness.jsonl');
    const log = join(directory, 'witness.log');
    const roiArgs = Object.entries(roi).flatMap(([name, value]) => ['--' + name, String(value)]);
    desktop = tool(
      witness,
      ['--capture', '--output', display.name, ...roiArgs, '--seconds', String(seconds)],
      seconds,
      log,
      path,
    );
    captures.push(desktop);
    return { entry: desktop, path, log };
  }
  try {
    const args = browserArgs(profile.adapter);
    if (!args.some((arg) => arg.startsWith('--use-adapter-luid=')))
      args.push('--use-adapter-luid=' + display.adapterLuid);
    browser = await chromium.launch({
      channel: 'chrome',
      headless: false,
      args: [...args, '--kiosk', '--window-position=0,0', '--force-device-scale-factor=1'],
    });
    const page = await browser.newPage({
      viewport: null,
      serviceWorkers: 'block',
      timezoneId: 'Asia/Hong_Kong',
    });
    await page.route(/^https?:\/\//, (route) => {
      const requested = new URL(route.request().url());
      if (requested.origin === url.origin) return route.continue();
      if (requested.hostname === 'api.open-meteo.com' && requested.protocol === 'https:')
        return route.fulfill({ json: { current: { weather_code: 61, is_day: 0 } } });
      return route.abort();
    });
    await page.addInitScript(installProbe, { ...profile, weather: '雨', day: false });
    await page.addInitScript(() => {
      window.studioPresentWitness = { hold: false, held: false, serial: 0 };
    });
    await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    await waitForShading(page);
    await page.waitForFunction(() => window.studioPresentWitness.serial > 1);
    checkCanvas(await canvasState(page, true));
    if (configuration.measure) {
      await primeDesk(page);
      await measureDesk(page, browser.version(), configuration, directory, captureWitness);
      return;
    }
    const browserCdp = await browser.newBrowserCDPSession();
    const { processInfo } = await browserCdp.send('SystemInfo.getProcessInfo');
    const gpu = processInfo.filter(({ type }) => type.toLowerCase() === 'gpu');
    if (gpu.length !== 1 || !Number.isSafeInteger(gpu[0].id) || gpu[0].id <= 0)
      throw new Error('The private Chrome browser did not report a unique GPU process.');
    const pid = gpu[0].id;
    const targetCdp = await page.context().newCDPSession(page);
    const { bounds, windowId } = await targetCdp.send('Browser.getWindowForTarget');
    const analyzePresent = (path) =>
      analysis('studio-present.mjs', ['analyze', path, '--qpc-ms', '--pid=' + pid]);
    const startPresent = (name, seconds) => {
      const path = join(directory, name + '.csv');
      const log = join(directory, name + '.log');
      const entry = tool(
        presentMon,
        presentArgs(pid, seconds, path, session + '-' + name),
        seconds,
        log,
      );
      captures.push(entry);
      return { entry, path, log };
    };
    const preflight = startPresent('present-preflight', 3);
    const preflightExit = await preflight.entry.result;
    if (preflightExit.code !== 0)
      throw captureFailure('PresentMon preflight', preflightExit, preflight.log);
    if (!analyzePresent(preflight.path).some(({ displayed }) => displayed > 0))
      throw new Error('PresentMon preflight returned no display-tracked frames.');
    await primeDesk(page);

    const present = startPresent('display', 19);
    await delay(500);
    if (present.entry.finished)
      throw captureFailure('PresentMon', await present.entry.result, present.log);
    const { path: witnessPath, log: witnessLog } = captureWitness(15);
    const deadline = performance.now() + 2800;
    while (!statSync(witnessPath).size && !desktop.finished && performance.now() < deadline)
      await delay(40);
    if (desktop.finished) throw captureFailure('DXGI witness', await desktop.result, witnessLog);
    if (!statSync(witnessPath).size)
      throw new Error('The DXGI witness did not start producing metadata.');
    const [, hold] = await Promise.all([
      turnDesk(page, profile, 11500, false),
      calibrationHold(page),
    ]);
    const state = await canvasState(page);
    checkCanvas(state, true);
    const [presentExit, witnessExit] = await Promise.all([present.entry.result, desktop.result]);
    if (presentExit.code !== 0) throw captureFailure('PresentMon', presentExit, present.log);
    if (witnessExit.code !== 0 && witnessExit.code !== 2)
      throw captureFailure('DXGI witness', witnessExit, witnessLog);
    if (JSON.stringify(readDisplay()) !== JSON.stringify(display))
      throw new Error('The active output mode changed across the calibration window.');
    const chains = analyzePresent(present.path);
    const report = witnessReport(witnessPath, display);
    const opticalHold = holdWitness(witnessPath, report, hold);
    const result = {
      display,
      windowId,
      bounds,
      pid,
      state,
      chains,
      hold,
      opticalHold,
      witness: report,
      etwFramesCorrelated: false,
      certified: false,
    };
    const path = join(directory, 'trial.json');
    writeFileSync(path, JSON.stringify(result, null, 2) + '\n');
    console.log(path);
    if (
      witnessExit.code === 2 ||
      !opticalHold.observed ||
      !chains.some(({ displayed }) => displayed > 0)
    )
      throw new Error(
        'Calibration did not produce complete optical hold and present evidence. See ' + path,
      );
  } finally {
    desktop?.stop();
    try {
      await browser?.close();
    } finally {
      try {
        await server.close();
      } finally {
        const closed = Promise.allSettled(captures.map(({ result }) => result));
        await Promise.race([closed, delay(350)]);
        for (const capture of captures) capture.stop();
        await closed;
      }
    }
  }
}

try {
  const configuration = settings(process.argv.slice(2));
  if (!configuration) console.log(usage);
  else if (!configuration.capture && !configuration.measure)
    console.log(
      JSON.stringify({ ...configuration, mode: 'dry-run', roi, phases, certified: false }, null, 2),
    );
  else {
    const output = join(root, '.review/performance');
    mkdirSync(output, { recursive: true });
    const directory = mkdtempSync(join(output, 'studio-physical-'));
    console.log(
      (configuration.measure ? 'Measurement files: ' : 'Calibration files: ') + directory,
    );
    await run(configuration, directory);
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
