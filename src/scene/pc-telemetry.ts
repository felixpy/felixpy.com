export function telemetryFont(size: number) {
  return `500 ${size}px Arial, sans-serif`;
}

function workload(seconds: number) {
  return (
    0.62 * Math.sin(seconds / 20 - 0.7) +
    0.27 * Math.sin(seconds / 8.7 + 0.8) +
    0.11 * Math.sin(seconds / 3.6 - 0.4)
  );
}

export function pcReadings(seconds: number) {
  const thermalLoad = 0.7 * workload(seconds - 4) + 0.3 * workload(seconds - 9);
  return {
    celsius: Math.round(42.5 + 7.5 * thermalLoad),
    watts: Math.round(225 + 75 * workload(seconds)),
  };
}
