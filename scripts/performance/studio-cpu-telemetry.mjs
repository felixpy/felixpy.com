import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';

const intervalMs = 1000;
const readyTimeoutMs = 8000;
const counterProgram = String.raw`
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Measure-Sample($sample) {
  $processors = @{}
  $queueLength = $null
  foreach ($counter in $sample.CounterSamples) {
    if ($counter.Status -notin 0, 1) { continue }
    $value = [double]$counter.CookedValue
    if ($value -lt 0 -or [double]::IsNaN($value) -or [double]::IsInfinity($value)) { continue }
    $metric = $counter.Path.Split('\')[-1].ToLowerInvariant()
    if ($metric -eq 'processor queue length') {
      $queueLength = $value
      continue
    }
    $instance = $counter.InstanceName
    if ($instance -notmatch '^(?<group>[0-9]+),(?<index>[0-9]+)$') { continue }
    if (!$processors.ContainsKey($instance)) {
      $processors[$instance] = [pscustomobject]@{
        group = [int]$Matches.group
        index = [int]$Matches.index
        parked = $null
        utilityPct = $null
        performancePct = $null
      }
    }
    $processor = $processors[$instance]
    switch ($metric) {
      'parking status' {
        if ($value -in 0, 1) { $processor.parked = $value -eq 1 }
      }
      '% processor utility' { $processor.utilityPct = $value }
      '% processor performance' { $processor.performancePct = $value }
    }
  }
  [pscustomobject]@{
    timeUtc = $sample.Timestamp.ToUniversalTime().ToString('o')
    queueLength = $queueLength
    logicalProcessors = @($processors.Values | Sort-Object group, index)
  }
}

$counters =
  '\Processor Information(*)\Parking Status',
  '\Processor Information(*)\% Processor Utility',
  '\Processor Information(*)\% Processor Performance',
  '\System\Processor Queue Length'
Get-Counter $counters -SampleInterval 1 -MaxSamples 900 -ErrorAction SilentlyContinue | ForEach-Object {
  [Console]::WriteLine((Measure-Sample $_ | ConvertTo-Json -Depth 4 -Compress))
}
`;

export async function startCpuTelemetry() {
  const report = { intervalMs, samples: [] };
  if (process.platform !== 'win32') {
    report.error = 'Windows processor counters are unavailable on this platform.';
    return { stop: async () => report };
  }

  const encoded = Buffer.from(counterProgram, 'utf16le').toString('base64');
  const child = spawn(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
    {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  const ready = Promise.withResolvers();
  let stopping = false;
  let closed = false;
  let lastTime = -Infinity;
  const stop = () => {
    if (stopping) return;
    stopping = true;
    if (!closed) child.kill();
  };
  const timer = setTimeout(() => {
    report.error ??= 'Windows processor counters did not return a usable sample.';
    stop();
    ready.resolve();
  }, readyTimeoutMs);
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
      if (!stopping) report.error ??= `Windows CPU counter process exited (code ${code}).`;
      markReady();
      resolve();
    });
  });
  const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  lines.on('line', (line) => {
    try {
      const sample = JSON.parse(line);
      const time = Date.parse(sample.timeUtc);
      if (!Number.isFinite(time) || time <= lastTime || !Array.isArray(sample.logicalProcessors))
        throw new Error('Invalid Windows CPU counter timestamp or logical processor sample.');
      lastTime = time;
      if (!sample.logicalProcessors.length || !Number.isFinite(sample.queueLength)) return;
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
      stop();
      await completed;
      return report;
    },
  };
}
