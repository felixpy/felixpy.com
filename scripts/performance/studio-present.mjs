import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseArgs } from 'node:util';

const usage = `Usage:
  node scripts/performance/studio-present.mjs capture --pid=PID [--seconds=65] [--presentmon=EXE]
  node scripts/performance/studio-present.mjs analyze CAPTURE.csv --pid=PID
  node scripts/performance/studio-present.mjs analyze CAPTURE.csv --pid=PID --swap-chain=ADDRESS --start=2 [--seconds=60] [--target=144]

Capture requires an explicitly selected GPU process from an isolated, headed Chrome session.
Record the tested window, monitor, refresh mode, and native scene dimensions separately.
The swap-chain-free analysis lists candidates. For cadence analysis, identify the tested
window's swap chain and provide its address explicitly. Pad both ends of the chosen interval.
Input is PresentMon v1 metrics CSV with display tracking and dropped presents retained.
The result measures OS-displayed swap-chain changes. Correlate these with distinct canvas
frames before using them for Studio acceptance.`;

const cadenceLimits = new Map([
  [30, [34, 35]],
  [60, [17, 17.5]],
  [144, [7.2, 7.5]],
]);

function numberOf(value, label, minimum = 0) {
  const number = Number(value);
  if (value === undefined || !String(value).trim() || !Number.isFinite(number) || number < minimum)
    throw new Error(`Invalid ${label}: ${value ?? '(missing)'}`);
  return number;
}

function integerOf(value, label, minimum = 1) {
  const number = numberOf(value, label, minimum);
  if (!Number.isSafeInteger(number)) throw new Error(`Invalid ${label}: ${value}`);
  return number;
}

function swapChainOf(address) {
  if (!/^(?:0x)?[\da-f]+$/i.test(address)) throw new Error(`Invalid swap chain: ${address}`);
  return '0x' + BigInt('0x' + address.replace(/^0x/i, '')).toString(16);
}

function csvFields(line) {
  const fields = [];
  const pattern = /(?:"((?:[^"]|"")*)"|([^",]*))(,|$)/gy;
  for (;;) {
    const match = pattern.exec(line);
    if (!match) throw new Error('Malformed PresentMon CSV row.');
    fields.push(match[1]?.replaceAll('""', '"') ?? match[2]);
    if (match[3] === '') return fields;
  }
}

function readCapture(path, pid) {
  const [heading, ...lines] = readFileSync(path, 'utf8').trim().split(/\r?\n/);
  const keys = csvFields(heading.replace(/^\uFEFF/, '')).map((name) => name.trim());
  const columns = new Map(keys.map((key, index) => [key, index]));
  const required = [
    'Application',
    'ProcessID',
    'SwapChainAddress',
    'Dropped',
    'TimeInSeconds',
    'MsUntilDisplayed',
  ];
  if (keys.length !== columns.size || required.some((key) => !columns.has(key)))
    throw new Error(
      'PresentMon v1 CSV is required. Capture with --v1_metrics and display tracking.',
    );

  const chains = new Map();
  for (const line of lines) {
    if (!line.trim()) continue;
    const row = csvFields(line);
    if (row.length !== columns.size) throw new Error('PresentMon CSV has inconsistent columns.');
    const read = (key) => row[columns.get(key)]?.trim();
    if (integerOf(read('ProcessID'), 'CSV ProcessID', 0) !== pid) continue;
    const address = swapChainOf(read('SwapChainAddress'));
    const chain = chains.get(address) ?? {
      address,
      applications: new Set(),
      modes: new Set(),
      frames: [],
    };
    chain.applications.add(read('Application'));
    if (columns.has('PresentMode')) chain.modes.add(read('PresentMode'));
    const dropped = integerOf(read('Dropped'), 'Dropped', 0);
    if (dropped > 1) throw new Error('Dropped must be 0 or 1.');
    const submitted = numberOf(read('TimeInSeconds'), 'TimeInSeconds') * 1e6;
    const displayed = dropped
      ? null
      : Math.round(submitted + numberOf(read('MsUntilDisplayed'), 'MsUntilDisplayed') * 1000);
    chain.frames.push({ submitted, displayed });
    chains.set(address, chain);
  }
  if (!chains.size) throw new Error(`No presents found for PID ${pid}.`);
  return chains;
}

function capture(pid, seconds, executable) {
  if (process.platform !== 'win32') throw new Error('PresentMon capture requires Windows.');
  const presentMon =
    executable ??
    [process.env.ProgramW6432, process.env.ProgramFiles]
      .filter(Boolean)
      .map((directory) =>
        join(directory, 'NVIDIA Corporation', 'FrameViewSDK', 'bin', 'PresentMon_x64.exe'),
      )
      .find(existsSync);
  if (!presentMon || !existsSync(presentMon))
    throw new Error('PresentMon was not found. Pass --presentmon with your installed executable.');

  const destination = resolve(import.meta.dirname, '../..', '.review/performance');
  mkdirSync(destination, { recursive: true });
  const directory = mkdtempSync(join(destination, 'studio-present-'));
  const path = join(directory, 'display.csv');
  const options = [
    '--process_id',
    String(pid),
    '--v1_metrics',
    '--timed',
    String(seconds),
    '--terminate_after_timed',
    '--session_name',
    `FelixStudioPresent-${process.pid}-${Date.now()}`,
    '--no_track_input',
    '--no_console_stats',
    '--output_file',
    path,
  ];
  const result = spawnSync(presentMon, options, { stdio: 'inherit', windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0 || !existsSync(path))
    throw new Error('PresentMon capture did not produce a CSV.');
  console.log(path);
}

function analyze(path, pid, address, start, seconds, target) {
  const chains = readCapture(path, pid);
  if (!address) {
    console.log(
      JSON.stringify(
        [...chains.values()].map(({ address, applications, modes, frames }) => ({
          address,
          applications: [...applications],
          modes: [...modes],
          submitted: frames.length,
          displayed: frames.filter((frame) => frame.displayed !== null).length,
        })),
        null,
        2,
      ),
    );
    return;
  }

  const chain = chains.get(swapChainOf(address));
  if (!chain || chain.address === '0x0' || chain.applications.size !== 1)
    throw new Error('Choose one identifiable swap chain for the selected process.');

  const begin = start * 1e6;
  const end = begin + seconds * 1e6;
  const events = chain.frames.flatMap(({ displayed }) => (displayed === null ? [] : [displayed]));
  const distinct = [...new Set(events)].sort((a, b) => a - b);
  if (distinct.length < 2 || distinct[0] > begin || distinct.at(-1) < end)
    throw new Error(
      'Displayed events must bracket the requested interval. Inspect capture coverage and retry.',
    );

  const timestamps = distinct.filter((time) => time >= begin && time < end);
  const intervals = [];
  for (let i = 1; i < distinct.length; i++) {
    const prior = distinct[i - 1];
    const current = distinct[i];
    if (current > begin && prior < end) intervals.push((current - prior) / 1000);
  }
  intervals.sort((a, b) => a - b);
  const percentile = (fraction) => intervals[Math.ceil(intervals.length * fraction) - 1];
  const [p95Limit, p99Limit] = cadenceLimits.get(target);
  const displayedFps = timestamps.length / seconds;
  const frameIntervalMs = {
    p50: percentile(0.5),
    p95: percentile(0.95),
    p99: percentile(0.99),
    max: intervals.at(-1),
  };
  const overTwiceBudget = intervals.filter((value) => value > 2000 / target).length;
  const overTwiceBudgetFraction = overTwiceBudget / intervals.length;
  const submissions = chain.frames.filter(({ submitted }) => submitted >= begin && submitted < end);
  const result = {
    scope: 'Windows ETW displayed swap-chain changes',
    capture: resolve(path),
    pid,
    swapChain: chain.address,
    application: [...chain.applications][0],
    presentModes: [...chain.modes],
    window: { startSeconds: start, durationSeconds: seconds },
    targetFps: target,
    displayedFps,
    distinctDisplayTimestamps: timestamps.length,
    coincidentDisplayRecords:
      events.filter((time) => time >= begin && time < end).length - timestamps.length,
    submittedPresents: submissions.length,
    droppedSubmissions: submissions.filter(({ displayed }) => displayed === null).length,
    frameIntervalMs,
    intervalCount: intervals.length,
    overTwiceBudget,
    overTwiceBudgetFraction,
    sampleDurationMeetsReleaseWindow: seconds >= 60,
    swapChainCadenceMeetsThresholds:
      displayedFps >= target &&
      frameIntervalMs.p95 <= p95Limit &&
      frameIntervalMs.p99 <= p99Limit &&
      overTwiceBudgetFraction < 0.001,
    studioCanvasFramesCorrelated: false,
  };
  console.log(JSON.stringify(result, null, 2));
}

try {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      help: { type: 'boolean', short: 'h' },
      pid: { type: 'string' },
      presentmon: { type: 'string' },
      'swap-chain': { type: 'string' },
      start: { type: 'string' },
      seconds: { type: 'string' },
      target: { type: 'string' },
    },
  });
  const [mode, path, ...extras] = positionals;
  if (values.help || !mode) console.log(usage);
  else if (
    mode === 'capture' &&
    !path &&
    !values['swap-chain'] &&
    !values.start &&
    !values.target
  ) {
    capture(
      integerOf(values.pid, 'pid'),
      integerOf(values.seconds ?? '65', 'seconds'),
      values.presentmon,
    );
  } else if (mode === 'analyze' && path && !extras.length && !values.presentmon) {
    const pid = integerOf(values.pid, 'pid');
    const address = values['swap-chain'];
    const target = integerOf(values.target ?? '144', 'target');
    if (!cadenceLimits.has(target)) throw new Error('Target must be 30, 60, or 144 FPS.');
    analyze(
      path,
      pid,
      address,
      address ? numberOf(values.start, 'start') : 0,
      numberOf(values.seconds ?? '60', 'seconds', 0.001),
      target,
    );
  } else throw new Error(usage);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
