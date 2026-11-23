export async function sampleRafControl(page, milliseconds = 3000) {
  const responseGraceMs = 3000;
  const maxTimerMs = 2 ** 31 - 1;
  if (
    !Number.isFinite(milliseconds) ||
    milliseconds <= 0 ||
    milliseconds > maxTimerMs - responseGraceMs
  )
    throw new Error('A positive, timer-safe rAF control duration is required.');

  let deadline;
  const unresponsive = new Promise((_, reject) => {
    deadline = setTimeout(
      () => reject(new Error('The independent rAF control page did not respond.')),
      milliseconds + responseGraceMs,
    );
  });

  let result;
  try {
    result = await Promise.race([
      page.evaluate(
        (duration) =>
          new Promise((resolve, reject) => {
            if (location.href !== 'about:blank' || !document.body) {
              reject(new Error('Use an independent about:blank page for the rAF control.'));
              return;
            }
            const marker = document.createElement('div');
            marker.style.cssText =
              'position:fixed;left:8px;top:8px;width:4px;height:4px;background:#000;will-change:transform;contain:strict';
            document.body.append(marker);

            const visible = document.visibilityState;
            const intervals = [];
            let visibilityChanged = false;
            let first;
            let last;
            let frame;
            let finished = false;
            const recordVisibility = () => {
              visibilityChanged = true;
            };
            document.addEventListener('visibilitychange', recordVisibility);
            const timeout = setTimeout(() => finish(false), duration + 1500);

            function finish(completed) {
              if (finished) return;
              finished = true;
              clearTimeout(timeout);
              cancelAnimationFrame(frame);
              document.removeEventListener('visibilitychange', recordVisibility);
              marker.remove();
              resolve({
                timeOriginUnixMs: performance.timeOrigin,
                visible,
                visibilityEnd: document.visibilityState,
                visibilityChanged,
                completed,
                intervals,
              });
            }

            function tick(time) {
              if (finished) return;
              if (last === undefined || time > last) {
                first ??= time;
                if (last !== undefined)
                  intervals.push({ startMs: last, endMs: time, durationMs: time - last });
                last = time;
                marker.style.transform = `translate3d(${intervals.length % 2}px, 0, 0)`;
              }
              if (last - first >= duration) finish(true);
              else frame = requestAnimationFrame(tick);
            }

            frame = requestAnimationFrame(tick);
          }),
        milliseconds,
      ),
      unresponsive,
    ]);
  } finally {
    clearTimeout(deadline);
  }

  const durations = result.intervals.map(({ durationMs }) => durationMs).toSorted((a, b) => a - b);
  const samples = durations.length;
  const percentile = (fraction) => (samples ? durations[Math.ceil(fraction * samples) - 1] : null);
  const elapsedMs = samples ? result.intervals.at(-1).endMs - result.intervals[0].startMs : 0;
  return {
    ...result,
    summary: {
      samples,
      elapsedMs,
      fps: samples ? (samples * 1000) / elapsedMs : null,
      p50Ms: percentile(0.5),
      p95Ms: percentile(0.95),
      p99Ms: percentile(0.99),
      maxMs: durations.at(-1) ?? null,
    },
  };
}
