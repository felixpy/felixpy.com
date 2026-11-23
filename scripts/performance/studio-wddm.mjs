import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';

const intervalMs = 1000;
const startTimeoutMs = 8000;

function adapterIdentity(adapterLuid) {
  if (!/^-?\d+,\d+$/.test(adapterLuid ?? ''))
    throw new Error('WDDM telemetry requires an adapter LUID in high,low decimal form.');
  const [high, low] = adapterLuid.split(',').map(Number);
  if (high < -0x80000000 || high > 0x7fffffff || low > 0xffffffff)
    throw new Error('WDDM telemetry adapter LUID is outside its 32-bit field ranges.');
  const fields = [high, low].map((value) => '0x' + (value >>> 0).toString(16).padStart(8, '0'));
  return { decimal: `${high},${low}`, instance: 'luid_' + fields.join('_') };
}

function counterProgram(gpuPid, adapter) {
  return String.raw`
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$chromePid = ${gpuPid}
$enginePattern = '^pid_(?<pid>[0-9]+)_${adapter}_phys_(?<physical>[0-9]+)_eng_(?<engine>[0-9]+)_engtype_3d$'
$memoryPattern = '^${adapter}_phys_[0-9]+$'

function Measure-Sample($sample) {
  $engines = @{}
  $memory = $null
  $chromeReported = $false
  foreach ($counter in $sample.CounterSamples) {
    $instance = $counter.InstanceName
    if ($instance -notlike '*${adapter}*') { continue }
    if ($counter.Status -notin 0, 1) { continue }
    $value = [double]$counter.CookedValue
    if ($value -lt 0 -or [double]::IsNaN($value) -or [double]::IsInfinity($value)) { continue }
    if ($instance -match $enginePattern) {
      $key = $Matches.physical + ',' + $Matches.engine
      if (!$engines.ContainsKey($key)) {
        $engines[$key] = [pscustomobject]@{
          physicalIndex = [int]$Matches.physical
          engineIndex = [int]$Matches.engine
          chromePct = 0.0
          otherPct = 0.0
        }
      }
      $engine = $engines[$key]
      if ([uint32]$Matches.pid -eq $chromePid) {
        $chromeReported = $true
        $engine.chromePct += $value
      } else {
        $engine.otherPct += $value
      }
    } elseif ($instance -match $memoryPattern) {
      $memory = [int64]$memory + [int64]$value
    }
  }
  [pscustomobject]@{
    timeUtc = $sample.Timestamp.ToUniversalTime().ToString('o')
    dedicatedBytes = $memory
    chromeReported = $chromeReported
    engines = @($engines.Values | Sort-Object physicalIndex, engineIndex)
  }
}

$counters = '\GPU Engine(*)\Utilization Percentage', '\GPU Adapter Memory(*)\Dedicated Usage'
Get-Counter $counters -SampleInterval 1 -MaxSamples 900 -ErrorAction SilentlyContinue | ForEach-Object {
  [Console]::WriteLine((Measure-Sample $_ | ConvertTo-Json -Depth 4 -Compress))
}
`;
}

export async function startWddmTelemetry({ gpuPid, adapterLuid }) {
  if (process.platform !== 'win32') throw new Error('WDDM telemetry requires Windows.');
  if (!Number.isSafeInteger(gpuPid) || gpuPid <= 0 || gpuPid > 0xffffffff)
    throw new Error('WDDM telemetry requires the benchmark Chrome GPU process ID.');
  const adapter = adapterIdentity(adapterLuid);
  const report = { gpuPid, adapterLuid: adapter.decimal, intervalMs, samples: [] };
  const encoded = Buffer.from(counterProgram(gpuPid, adapter.instance), 'utf16le').toString(
    'base64',
  );
  const child = spawn(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
    {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  let requestedStop = false;
  let closed = false;
  let lastTime = -Infinity;
  const stop = () => {
    requestedStop = true;
    if (!closed) child.kill();
  };
  const ready = Promise.withResolvers();
  const timer = setTimeout(() => {
    report.error ??= 'WDDM counters did not report a usable sample for the selected adapter.';
    stop();
    ready.resolve();
  }, startTimeoutMs);
  const markReady = () => {
    clearTimeout(timer);
    ready.resolve();
  };
  const completed = new Promise((resolve) => {
    child.once('error', (error) => {
      report.error ??= error.message;
    });
    child.once('close', (code) => {
      closed = true;
      if (!requestedStop) report.error ??= `WDDM counter process exited (code ${code}).`;
      markReady();
      resolve();
    });
  });
  const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  lines.on('line', (line) => {
    try {
      const sample = JSON.parse(line);
      const time = Date.parse(sample.timeUtc);
      if (!Number.isFinite(time) || time <= lastTime || !Array.isArray(sample.engines))
        throw new Error('WDDM counter timestamps or engine samples are invalid.');
      lastTime = time;
      if (sample.dedicatedBytes === null) return;
      report.samples.push(sample);
      markReady();
    } catch (error) {
      report.error ??= error.message;
      stop();
      markReady();
    }
  });
  child.stderr.resume();
  await ready.promise;
  return {
    async stop() {
      if (!requestedStop) stop();
      await completed;
      if (!report.samples.some(({ chromeReported }) => chromeReported))
        report.error ??=
          'WDDM did not report the benchmark Chrome GPU PID on the selected adapter.';
      return report;
    },
  };
}
