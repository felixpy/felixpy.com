import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const folder = new URL('../../public/media/materials/', import.meta.url);
function noise(seed) {
  const field = Float32Array.from({ length: 128 * 128 }, () => {
    seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
    return seed / 4294967296;
  });
  const at = (x, y) => field[(x & 127) + (y & 127) * 128];
  const mix = (a, b, t) => (1 - t) * a + t * b;
  return (x, y) => {
    const i = Math.floor(x),
      j = Math.floor(y),
      u = x - i,
      v = y - j;
    const s = u * u * (3 - 2 * u),
      t = v * v * (3 - 2 * v);
    return mix(mix(at(i, j), at(i + 1, j), s), mix(at(i, j + 1), at(i + 1, j + 1), s), t);
  };
}

function raster(name, size, pixel) {
  const data = new Uint8ClampedArray(size * size * 3);
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) data.set(pixel(x / size, y / size), (y * size + x) * 3);
  execFileSync(
    'ffmpeg',
    [
      '-v',
      'error',
      '-y',
      '-f',
      'rawvideo',
      '-pix_fmt',
      'rgb24',
      '-s',
      size + 'x' + size,
      '-i',
      'pipe:0',
      '-frames:v',
      '1',
      '-c:v',
      'libwebp',
      '-lossless',
      '1',
      fileURLToPath(new URL(name + '.webp', folder)),
    ],
    { input: data },
  );
}

function normal(name, size, height, strength) {
  const field = Float32Array.from({ length: size * size }, (_, i) =>
    height((i % size) / size, Math.floor(i / size) / size),
  );
  const at = (x, y) => field[((x + size) % size) + ((y + size) % size) * size];
  raster(name, size, (u, v) => {
    const x = Math.round(u * size),
      y = Math.round(v * size);
    const nx = (at(x - 1, y) - at(x + 1, y)) * strength,
      ny = (at(x, y + 1) - at(x, y - 1)) * strength;
    const reciprocal = 1 / Math.hypot(nx, ny, 1);
    return [128 + nx * reciprocal * 127, 128 + ny * reciprocal * 127, 128 + reciprocal * 127];
  });
}

const plaster = noise(122),
  linen = noise(922),
  stone = noise(86),
  grip = noise(691),
  brush = noise(431);
normal(
  'wall-micro-normal',
  512,
  (u, v) =>
    plaster(u * 113, v * 113) * 0.64 +
    plaster(u * 38, v * 47) * 0.3 +
    plaster(u * 6, v * 16) * 0.06,
  0.42,
);
raster('wall-micro-roughness', 256, (u, v) =>
  Array(3).fill(195 + plaster(u * 21, v * 27) * 31 + plaster(u * 72, v * 72) * 11),
);
normal(
  'linen-micro-normal',
  512,
  (u, v) =>
    (Math.cos(u * Math.PI * 256) + Math.cos(v * Math.PI * 180)) * 0.35 +
    linen(u * 75, v * 92) * 0.25,
  0.12,
);
raster('limestone-color', 512, (u, v) => {
  const beds = stone(u * 24, v * 7 + stone(u * 3, v * 7) * 2),
    pores = stone(u * 289, v * 191);
  const base = 184 + beds * 13 + pores * 6 - (pores > 0.85 ? 15 : 0);
  return [base + 8, base + 2, base - 11];
});
normal('limestone-normal', 256, (u, v) => stone(u * 107, v * 107), 0.1);
for (const [name, threads] of [
  ['cloth', 104],
  ['carbon', 72],
]) {
  const carbon = name === 'carbon';
  const height = (u, v) => {
    const x = u * threads,
      y = v * threads;
    return (Math.floor(x) + Math.floor(y)) % 4 < 2
      ? Math.sin(x * Math.PI) ** 2
      : Math.sin(y * Math.PI) ** 2;
  };
  raster(name + '-weave', 512, (u, v) => {
    const value = carbon ? 37 + height(u, v) * 2 : 47 + height(u, v) * 3;
    return [value, value + 1, value + 2];
  });
  normal(name + '-weave-normal', 512, height, carbon ? 0.025 : 0.03);
}
normal(
  'metal-brush-normal',
  256,
  (u, v) => brush(u * 4, v * 122) * 0.8 + brush(u * 17, v * 59) * 0.2,
  0.13,
);
normal(
  'camera-grip-normal',
  256,
  (u, v) => Math.min(0.64, grip(u * 64, v * 64) * 0.91 + grip(u * 128, v * 128) * 0.09),
  0.27,
);
for (const [name, seed, frequency, strength] of [
  ['plaster', 91, 91, 0.12],
  ['cork', 61, 67, 0.24],
  ['black', 14, 105, 0.14],
  ['rubber', 34, 104, 0.16],
  ['paper', 54, 117, 0.1],
]) {
  const grain = noise(seed);
  normal(name + '-grain-normal', 256, (u, v) => grain(u * frequency, v * frequency), strength);
}
