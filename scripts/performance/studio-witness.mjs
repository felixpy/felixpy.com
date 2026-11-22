import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { parseArgs } from 'node:util';

const usage = `Usage:
  node scripts/performance/studio-witness.mjs CAPTURE.jsonl [--start=SECONDS] [--seconds=SECONDS]

Analyze a completed studio-dxgi-roi-v1 witness file. The window starts at capture time zero
by default and ends at the capture deadline unless a duration is provided. Reports observed
marker changes and acquisition gaps without ETW correlation or release certification.
Serial gaps describe the distance between readable markers. Acquisition gaps come from
DXGI AccumulatedFrames on records inside the selected window. The observed scene FPS
lower bound subtracts one from the number of distinct readable serials to allow for a
frame already on screen at window start. Serial reversals or inconsistent accumulation
make this bound unavailable.`;

const serialSpace = 0x1000000;
const ticksPerSecond = 1_000_000n;
const maxExamples = 12;
const unreadStatuses = new Set([
  'ambiguous_pixels',
  'wrong_sync',
  'wrong_checksum',
  'protected_content',
  'readback_timeout',
]);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function integer(row, name, minimum = 0, maximum = Number.MAX_SAFE_INTEGER) {
  const value = row[name];
  assert(Number.isSafeInteger(value) && value >= minimum && value <= maximum, `Invalid ${name}.`);
  return value;
}

function qpc(row, name) {
  assert(typeof row[name] === 'string' && /^\d+$/.test(row[name]), `Invalid ${name} QPC ticks.`);
  return BigInt(row[name]);
}

function checksum(serial) {
  let crc = 0;
  for (const byte of [0xd7, serial >>> 16, (serial >>> 8) & 0xff, serial & 0xff]) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) crc = ((crc << 1) ^ (crc & 0x80 ? 0x07 : 0)) & 0xff;
  }
  return crc;
}

function serialDistance(previous, current) {
  return (current - previous + serialSpace) % serialSpace;
}

function parseCapture(path) {
  const records = readFileSync(path, 'utf8')
    .replace(/^\uFEFF/, '')
    .split(/\r?\n/)
    .flatMap((line, index) => {
      if (!line.trim()) return [];
      try {
        const record = JSON.parse(line);
        assert(
          record && typeof record === 'object' && !Array.isArray(record),
          'Expected an object.',
        );
        return [record];
      } catch (error) {
        throw new Error(`Malformed witness JSON at line ${index + 1}: ${error.message}`);
      }
    });
  const header = records[0];
  const summary = records.at(-1);
  assert(
    header?.type === 'capture' && header.schema === 'studio-dxgi-roi-v1',
    'Expected a studio-dxgi-roi-v1 capture header.',
  );
  assert(summary?.type === 'summary', 'The witness capture has no completion summary.');
  assert(
    header.certified === false && summary.certified === false,
    'Unexpected witness certification state.',
  );
  assert(
    typeof header.output === 'string' && header.output.length > 0,
    'Missing DXGI output name.',
  );

  const outputWidth = integer(header, 'outputWidth', 1);
  const outputHeight = integer(header, 'outputHeight', 1);
  const width = integer(header, 'width', 40, 320);
  const height = integer(header, 'height', 1, 64);
  assert(
    width % 40 === 0 &&
      integer(header, 'x') + width <= outputWidth &&
      integer(header, 'y') + height <= outputHeight,
    'The marker ROI is outside the witness output or has an invalid width.',
  );
  integer(header, 'outputLeft', -0x80000000, 0x7fffffff);
  integer(header, 'outputTop', -0x80000000, 0x7fffffff);
  integer(header, 'adapterLuidHigh', -0x80000000, 0x7fffffff);
  integer(header, 'adapterLuidLow', 0, 0xffffffff);
  integer(header, 'refreshNumerator', 0, 0xffffffff);
  integer(header, 'refreshDenominator', 0, 0xffffffff);

  const frequency = qpc(header, 'qpcFrequency');
  const start = qpc(header, 'startQpc');
  const deadline = qpc(header, 'deadlineQpc');
  const duration = deadline - start;
  assert(
    frequency > 0n &&
      duration >= frequency &&
      duration <= frequency * 120n &&
      duration % frequency === 0n,
    'Invalid witness QPC frequency or capture deadline.',
  );
  assert(qpc(summary, 'endQpc') >= deadline, 'The witness ended before its capture deadline.');

  const totals = {
    desktopFrames: 0,
    mouseOnly: 0,
    validMarkers: 0,
    knownMissedDesktopUpdates: 0,
    inconsistentAccumulation: 0,
  };
  let priorAcquisition = start - 1n;
  let priorPresent = 0n;
  const frames = records.slice(1, -1).map((row, index) => {
    const label = `frame record ${index + 1}`;
    assert(row.type === 'frame', `Unexpected witness type in ${label}.`);
    const acquired = qpc(row, 'acquiredQpc');
    const presented = qpc(row, 'lastPresentQpc');
    const lastMouse = qpc(row, 'lastMouseUpdateQpc');
    const accumulated = integer(row, 'accumulatedFrames', 0, 0xffffffff);
    assert(
      acquired > priorAcquisition && acquired < deadline,
      `Non-increasing or out-of-range acquisition QPC in ${label}.`,
    );
    assert(
      presented <= acquired && lastMouse <= acquired,
      `A display or mouse timestamp follows its acquisition in ${label}.`,
    );
    priorAcquisition = acquired;

    if (presented === 0n) {
      assert(row.status === 'mouse_only', `Missing desktop timestamp in ${label}.`);
      totals.mouseOnly++;
      if (accumulated) totals.inconsistentAccumulation++;
    } else {
      assert(presented > priorPresent, `Non-increasing desktop presentation QPC in ${label}.`);
      assert(
        row.status === 'valid' || unreadStatuses.has(row.status),
        `Unexpected marker status in ${label}.`,
      );
      priorPresent = presented;
      totals.desktopFrames++;
      if (accumulated > 1) totals.knownMissedDesktopUpdates += accumulated - 1;
      if (accumulated === 0) totals.inconsistentAccumulation++;
    }

    if (row.status === 'valid' || row.status === 'wrong_checksum') {
      const actual = integer(row, 'checksum', 0, 255);
      const expected = checksum(integer(row, 'sequence', 0, serialSpace - 1));
      assert(
        integer(row, 'expectedChecksum', 0, 255) === expected &&
          (actual === expected) === (row.status === 'valid'),
        `Marker CRC is inconsistent in ${label}.`,
      );
      if (row.status === 'valid') totals.validMarkers++;
    }
    return { acquired, presented, accumulated, status: row.status, serial: row.sequence };
  });
  for (const [name, value] of Object.entries(totals)) {
    assert(
      integer(summary, name) === value,
      `The witness summary does not match its ${name} records.`,
    );
  }
  return { header, frequency, start, deadline, frames };
}

function seconds(value, name) {
  assert(/^\d+(\.\d{1,6})?$/.test(value), `Invalid ${name}. Use up to six decimal places.`);
  const [whole, fraction = ''] = value.split('.');
  return BigInt(whole) * ticksPerSecond + BigInt(fraction.padEnd(6, '0'));
}

function analyze(path, capture, startOffset, length) {
  const { header, frequency, start, deadline, frames } = capture;
  const fromMicroseconds = (value) => (value * frequency + ticksPerSecond - 1n) / ticksPerSecond;
  const begin = start + fromMicroseconds(startOffset);
  const end = length === undefined ? deadline : start + fromMicroseconds(startOffset + length);
  assert(
    begin < end && end <= deadline,
    'The requested window is outside the completed capture interval.',
  );

  const samples = {
    desktopUpdates: 0,
    mouseOnly: 0,
    validMarkers: 0,
    invalidMarkers: 0,
    observedSerialChanges: 0,
    repeatedSerials: 0,
    unlinkedMarkers: 0,
    serialGapEvents: 0,
    skippedSerialsBetweenReadings: 0,
    serialResetsOrReversals: 0,
    missedAcquisitionEvents: 0,
    knownMissedDesktopUpdates: 0,
    inconsistentAccumulation: 0,
  };
  const examples = [];
  const observed = new Set();
  let previousObservedSerial;
  let observationsMonotonic = true;
  const sparse = (kind, time, detail) => {
    if (examples.length < maxExamples) examples.push({ kind, qpc: String(time), ...detail });
  };
  let previous;
  for (const frame of frames) {
    const time = frame.presented || frame.acquired;
    if (time >= end) continue;
    const inWindow = time >= begin;
    if (frame.presented === 0n) {
      if (inWindow) {
        samples.mouseOnly++;
        if (frame.accumulated !== 0) {
          samples.inconsistentAccumulation++;
          sparse('mouse_only_with_accumulation', time, { accumulatedFrames: frame.accumulated });
        }
      }
      continue;
    }
    const valid = frame.status === 'valid';
    if (inWindow) {
      samples.desktopUpdates++;
      if (frame.accumulated > 1) {
        samples.missedAcquisitionEvents++;
        samples.knownMissedDesktopUpdates += frame.accumulated - 1;
        sparse('desktop_updates_missed_by_witness', time, { accumulatedFrames: frame.accumulated });
      } else if (frame.accumulated === 0) {
        samples.inconsistentAccumulation++;
        sparse('desktop_update_without_accumulation', time, {});
      }
      if (!valid) {
        samples.invalidMarkers++;
        sparse('unreadable_marker', time, { status: frame.status });
      } else {
        samples.validMarkers++;
        observed.add(frame.serial);
        if (
          previousObservedSerial !== undefined &&
          serialDistance(previousObservedSerial, frame.serial) >= serialSpace / 2
        )
          observationsMonotonic = false;
        if (previous === undefined) samples.unlinkedMarkers++;
        else if (previous.serial === frame.serial) samples.repeatedSerials++;
        else {
          samples.observedSerialChanges++;
          const step = serialDistance(previous.serial, frame.serial);
          const sequence = {
            previousSerial: previous.serial,
            previousQpc: String(previous.qpc),
            serial: frame.serial,
          };
          if (step >= serialSpace / 2) {
            samples.serialResetsOrReversals++;
            sparse('serial_reset_or_reversal', time, sequence);
          } else if (step > 1) {
            samples.serialGapEvents++;
            samples.skippedSerialsBetweenReadings += step - 1;
            sparse('serial_gap_between_readings', time, { ...sequence, skipped: step - 1 });
          }
        }
      }
    }
    if (valid) previousObservedSerial = frame.serial;
    previous = valid ? { serial: frame.serial, qpc: time } : undefined;
  }

  const windowSeconds = Number(end - begin) / Number(frequency);
  const hasConsistentObservations =
    observationsMonotonic && !samples.inconsistentAccumulation && windowSeconds > 0;
  return {
    scope: 'Offline DXGI desktop ROI witness',
    capture: resolve(path),
    output: header.output,
    outputPixels: [header.outputWidth, header.outputHeight],
    roi: { x: header.x, y: header.y, width: header.width, height: header.height },
    qpcFrequency: String(frequency),
    window: {
      startQpc: String(begin),
      endQpc: String(end),
      seconds: windowSeconds,
    },
    ...samples,
    distinctSerialValues: observed.size,
    observedSceneFramesPerSecondLowerBound: hasConsistentObservations
      ? Math.max(0, observed.size - 1) / windowSeconds
      : null,
    examples,
    etwFramesCorrelated: false,
    certified: false,
  };
}

try {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      help: { type: 'boolean', short: 'h' },
      start: { type: 'string' },
      seconds: { type: 'string' },
    },
  });
  if (values.help || positionals.length === 0) console.log(usage);
  else {
    assert(positionals.length === 1, usage);
    const [path] = positionals;
    const start = seconds(values.start ?? '0', 'start');
    const length = values.seconds === undefined ? undefined : seconds(values.seconds, 'seconds');
    assert(length === undefined || length > 0n, 'The requested duration must be positive.');
    console.log(JSON.stringify(analyze(path, parseCapture(path), start, length), null, 2));
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
