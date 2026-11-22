import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { isDeepStrictEqual, parseArgs } from 'node:util';

const usage = `Usage:
  node scripts/performance/studio-view-timing.mjs BASELINE.json CANDIDATE.json [--budget-ms=6.944444]

Compare matched native High desk replays from studio-benchmark.mjs. Each artifact must contain
recorded cameraYaws and mainColorGpu and downstreamGpu frameIndices. Only queries paired by
primary frame index enter the combined GPU metrics.

Yaw is in radians, negative toward the right. Fixed bin limits are -0.42, -0.21, 0, 0.21 and 0.42.
The lower edge of each bin is included. Each submission interval belongs to its starting frame.
An interval greater than 1.5 times the frame budget counts as a long submission interval.
The report measures browser submissions and elapsed GPU queries.`;

const yawLimits = [-0.42, -0.21, 0, 0.21, 0.42];

function requireCondition(condition, message) {
  if (!condition) throw new Error(message);
}

function queryFrames(record, frameCount, label) {
  const { durations, frameIndices, discarded } = record ?? {};
  requireCondition(
    Array.isArray(durations) &&
      Array.isArray(frameIndices) &&
      durations.length === frameIndices.length,
    `${label} must include one explicit frame index per valid duration.`,
  );
  const frames = new Map();
  let previous = -1;
  for (const [sample, index] of frameIndices.entries()) {
    const duration = durations[sample];
    requireCondition(
      Number.isSafeInteger(index) &&
        index > previous &&
        index < frameCount &&
        Number.isFinite(duration) &&
        duration >= 0,
      `Invalid or non-increasing ${label} frame index or duration at sample ${sample}.`,
    );
    frames.set(index, duration);
    previous = index;
  }
  return { frames, discarded: discarded ?? null };
}

function readRun(path) {
  const { summary, raw } = JSON.parse(readFileSync(path, 'utf8'));
  const { roomFrames, submissions, cameraYaws } = raw ?? {};
  requireCondition(
    Array.isArray(roomFrames) &&
      roomFrames.length > 1 &&
      Array.isArray(submissions) &&
      submissions.length === roomFrames.length &&
      Array.isArray(cameraYaws) &&
      cameraYaws.length === roomFrames.length,
    `${path} must include aligned roomFrames, submissions and cameraYaws.`,
  );
  const { profile } = summary ?? {};
  requireCondition(
    summary?.route === 'desk' &&
      summary.mode === 'room' &&
      profile?.quality === 'high' &&
      /^[a-f\d]{64}$/i.test(summary.chunkSHA256 ?? '') &&
      typeof summary.gpu === 'string' &&
      summary.gpu.length > 0,
    `${path} must be a High desk replay with its render adapter and StudioView SHA-256.`,
  );
  const resolutions = Object.entries(raw.resolutions ?? {});
  const [key, count] = resolutions[0] ?? [];
  const target = key?.split(',').map(Number);
  const size = [profile.width, profile.height];
  requireCondition(
    isDeepStrictEqual(raw.drawingBuffer, size) &&
      resolutions.length === 1 &&
      target?.length === 5 &&
      target.every(Number.isSafeInteger) &&
      isDeepStrictEqual(target.slice(0, 4), [...size, ...size]) &&
      target[4] >= 0 &&
      count === roomFrames.length,
    `${path} must have one matching native drawing buffer and render target for all frames.`,
  );

  const main = queryFrames(raw.mainColorGpu, roomFrames.length, 'Main-color GPU');
  const downstream = queryFrames(raw.downstreamGpu, roomFrames.length, 'Downstream GPU');
  const frames = roomFrames.map((time, index) => {
    const cpu = submissions[index];
    const yaw = cameraYaws[index];
    requireCondition(
      Number.isFinite(time) &&
        (index === 0 || time > roomFrames[index - 1]) &&
        Number.isFinite(cpu) &&
        cpu >= 0 &&
        Number.isFinite(yaw) &&
        Math.abs(yaw) <= Math.PI,
      `Invalid ${path} primary frame ${index} timestamp, CPU duration, or yaw.`,
    );
    const mainMs = main.frames.get(index);
    const downstreamMs = downstream.frames.get(index);
    return {
      yaw,
      cpu,
      nextInterval: index < roomFrames.length - 1 ? roomFrames[index + 1] - time : null,
      gpu:
        mainMs !== undefined && downstreamMs !== undefined
          ? { mainMs, downstreamMs, totalMs: mainMs + downstreamMs }
          : null,
    };
  });
  const paired = frames.filter(({ gpu }) => gpu).length;
  requireCondition(paired > 0, `${path} has no GPU queries with a matching primary frame index.`);

  const configuration = {
    chunkSHA256: summary.chunkSHA256.toLowerCase(),
    adapter: summary.gpu,
    profile,
    drawingBuffer: size,
    targetSamples: target[4],
    viewport: summary.viewport,
    devicePixelRatio: summary.devicePixelRatio,
    defaultFramebufferAntialias: summary.defaultFramebufferAntialias,
    route: summary.route,
    weather: summary.weather,
    observedWeather: summary.observedWeather,
    night: summary.night,
    cachePolicy: summary.cache?.policy,
    repeatDesk: Boolean(summary.firstTurn),
    routeSeconds: summary.durationSeconds,
    browser: summary.chrome,
    platform: summary.platform,
    browserArgs: summary.args,
    opaqueSort: summary.opaqueSort,
    wddmLuid: raw.wddm?.adapterLuid,
  };
  return {
    configuration,
    info: {
      path: resolve(path),
      run: summary.run,
      experiments: summary.experiments ?? {},
      measuredSeconds: (roomFrames.at(-1) - roomFrames[0]) / 1000,
      queryCounts: {
        main: main.frames.size,
        mainDiscarded: main.discarded,
        downstream: downstream.frames.size,
        downstreamDiscarded: downstream.discarded,
        paired,
      },
    },
    frames,
  };
}

function rounded(n) {
  return Math.round(n * 1000) / 1000;
}

function metrics(values, threshold) {
  const sorted = values.toSorted((a, b) => a - b);
  const count = sorted.length;
  const exceeded = sorted.filter((value) => value > threshold).length;
  return {
    count,
    p95Ms: count ? rounded(sorted[Math.ceil(0.95 * count) - 1]) : null,
    exceeded,
    exceededPercent: count ? rounded((100 * exceeded) / count) : null,
  };
}

function summarize(frames, budget) {
  const yaws = frames.map(({ yaw }) => yaw).toSorted((a, b) => a - b);
  const pairs = frames.flatMap(({ gpu }) => (gpu ? [gpu] : []));
  return {
    frames: frames.length,
    observedYawRange: yaws.length ? [rounded(yaws[0]), rounded(yaws.at(-1))] : null,
    cpuSubmission: metrics(
      frames.map(({ cpu }) => cpu),
      budget,
    ),
    browserInterval: metrics(
      frames.flatMap(({ nextInterval }) => (nextInterval === null ? [] : [nextInterval])),
      1.5 * budget,
    ),
    mainGpu: metrics(
      pairs.map(({ mainMs }) => mainMs),
      budget,
    ),
    downstreamGpu: metrics(
      pairs.map(({ downstreamMs }) => downstreamMs),
      budget,
    ),
    combinedGpu: metrics(
      pairs.map(({ totalMs }) => totalMs),
      budget,
    ),
  };
}

function groups(frames) {
  const bins = Array.from({ length: yawLimits.length + 1 }, () => []);
  for (const frame of frames) {
    const index = yawLimits.findIndex((limit) => frame.yaw < limit);
    (index === -1 ? bins.at(-1) : bins[index]).push(frame);
  }
  return bins;
}

function difference(a, b) {
  return a === null || b === null ? null : rounded(b - a);
}

function compareGroup(baseline, candidate, budget) {
  const before = summarize(baseline, budget);
  const after = summarize(candidate, budget);
  return {
    baseline: before,
    candidate: after,
    candidateMinusBaseline: {
      cpuP95Ms: difference(before.cpuSubmission.p95Ms, after.cpuSubmission.p95Ms),
      combinedGpuP95Ms: difference(before.combinedGpu.p95Ms, after.combinedGpu.p95Ms),
      longIntervalsPercentagePoints: difference(
        before.browserInterval.exceededPercent,
        after.browserInterval.exceededPercent,
      ),
    },
  };
}

try {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      help: { type: 'boolean', short: 'h' },
      'budget-ms': { type: 'string', default: String(1000 / 144) },
    },
  });
  if (values.help || !process.argv.slice(2).length) console.log(usage);
  else {
    requireCondition(positionals.length === 2, usage);
    const budget = Number(values['budget-ms']);
    requireCondition(Number.isFinite(budget) && budget > 0, 'Frame budget must be positive.');
    const [baseline, candidate] = positionals.map(readRun);
    const mismatches = Object.keys(baseline.configuration).filter(
      (key) => !isDeepStrictEqual(baseline.configuration[key], candidate.configuration[key]),
    );
    requireCondition(
      mismatches.length === 0,
      'The runs differ in comparable settings: ' + mismatches.join(', ') + '.',
    );
    const baselineBins = groups(baseline.frames);
    const candidateBins = groups(candidate.frames);
    console.log(
      JSON.stringify(
        {
          configuration: baseline.configuration,
          frameBudgetMs: budget,
          longSubmissionIntervalMs: 1.5 * budget,
          baseline: baseline.info,
          candidate: candidate.info,
          global: compareGroup(baseline.frames, candidate.frames, budget),
          yawBins: baselineBins.map((frames, index) => ({
            minInclusive: yawLimits[index - 1] ?? null,
            maxExclusive: yawLimits[index] ?? null,
            ...compareGroup(frames, candidateBins[index], budget),
          })),
          physicalPresentMeasured: false,
        },
        null,
        2,
      ),
    );
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
