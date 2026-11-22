import * as T from 'three';
import type { Environment } from '../app/environment';
import { ceilingLightLevel } from '../app/home-lights';
import { lightingVolume } from './lighting-volume';

const width = 32,
  height = 24,
  depth = 32;
const count = width * height * depth;
const channels = 7;
const volumeBytes = count * 8;
const decode = Float32Array.from({ length: 256 }, (_, i) => (i / 255) ** 2);

function volume(data: Uint8Array<ArrayBuffer>, w: number, h: number, d: number) {
  const texture = new T.Data3DTexture(data, w, h, d);
  texture.format = T.RGBAFormat;
  texture.minFilter = texture.magFilter = T.LinearFilter;
  texture.unpackAlignment = 1;
  texture.needsUpdate = true;
  return texture;
}

function mixSources(basis: Uint8Array, weights: number[], packed: Uint8Array) {
  for (let i = 0, offset = 0; i < count; i++) {
    let r = 0,
      g = 0,
      b = 0,
      x = 0,
      y = 0,
      z = 0;
    for (let j = 0; j < channels; j++, offset += 6) {
      if (weights[j] <= 0) continue;
      const red = weights[j] * decode[basis[offset]];
      const green = weights[j] * decode[basis[offset + 1]];
      const blue = weights[j] * decode[basis[offset + 2]];
      r += red;
      g += green;
      b += blue;
      const luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue;
      x += (basis[offset + 3] - 128) * luma;
      y += (basis[offset + 4] - 128) * luma;
      z += (basis[offset + 5] - 128) * luma;
    }
    const k = i * 4,
      normal = k + count * 4;
    packed[k] = Math.min(255, Math.round(255 * Math.sqrt(r)));
    packed[k + 1] = Math.min(255, Math.round(255 * Math.sqrt(g)));
    packed[k + 2] = Math.min(255, Math.round(255 * Math.sqrt(b)));
    packed[k + 3] = 255;
    const luma = Math.max(0.00001, 0.2126 * r + 0.7152 * g + 0.0722 * b);
    packed[normal] = Math.round(128 + x / luma);
    packed[normal + 1] = Math.round(128 + y / luma);
    packed[normal + 2] = Math.round(128 + z / luma);
    packed[normal + 3] = 255;
  }
}

function unpackRadiance(raw: Uint8Array) {
  if (new DataView(raw.buffer, raw.byteOffset).getUint32(0) !== 0x52474933) return;
  const stride = channels * 6;
  const basis = new Uint8Array(count * stride);
  let offset = 4;
  for (let coefficient = 0; coefficient < stride; coefficient++) {
    for (let i = 0, previous = 0; i < count; i++, offset++) {
      previous = (raw[offset] + (i % width === 0 ? 0 : previous)) & 255;
      basis[i * stride + coefficient] = previous;
    }
  }
  return basis;
}

export function roomIrradiance(signal: AbortSignal) {
  const field = { value: volume(new Uint8Array([0, 0, 0, 255, 128, 128, 128, 255]), 1, 1, 2) };
  const strength = { value: 0 };
  let basis: Uint8Array | undefined, load: Promise<void> | undefined;
  let current: Uint8Array<ArrayBuffer> | undefined, target: Uint8Array<ArrayBuffer> | undefined;
  let weights: number[] = [];
  let previous: Environment | undefined,
    transition = 1,
    elapsed = 0;

  const select = (env: Environment) => {
    const coverage = env.blinds ? [0.24, 0.54, 1][env.angle] : 0;
    const sun = env.weather === '晴';
    const sky = env.night
      ? 0.1
      : sun
        ? 1.65
        : env.weather === '雨'
          ? 1.65
          : env.weather === '雪'
            ? 2.55
            : 2.2;
    const next = [
      sky * (1 - 0.79 * coverage),
      env.night || !sun ? 0 : 1.73 * (1 - 0.95 * coverage),
      1.3 * ceilingLightLevel(env),
      env.lamp ? 2.22 : 0,
      env.benchLamp ? 0.82 : 0,
      env.toolBoardLamp ? 0.82 : 0,
      (env.wallLamp ?? env.night) ? 1 : 0,
    ];
    if (basis && current && target && next.some((value, i) => weights[i] !== value)) {
      mixSources(basis, next, target);
      transition = env.reducedMotion ? 1 : 0;
      elapsed = 0;
      if (transition === 1) {
        current.set(target);
        field.value.needsUpdate = true;
      }
    }
    weights = next;
  };
  const ensure = () => {
    load ??= (async () => {
      const raw = await lightingVolume(
        '/media/lighting/room-irradiance.gz',
        count * channels * 6 + 4,
        signal,
      );
      const decoded = raw && unpackRadiance(raw);
      if (!decoded) {
        load = undefined;
        return;
      }
      basis = decoded;
      current = new Uint8Array(volumeBytes);
      target = new Uint8Array(volumeBytes);
      mixSources(basis, weights, current);
      target.set(current);
      field.value.dispose();
      field.value = volume(current, width, height, depth * 2);
    })().catch(() => {
      load = undefined;
    });
  };
  return {
    field,
    strength,
    get ready() {
      return load ?? Promise.resolve();
    },
    update(env: Environment, delta: number) {
      if (previous !== env) {
        previous = env;
        if (env.quality === 'high') {
          select(env);
          ensure();
        }
      }
      const gain = basis && env.quality === 'high' ? 1 : 0;
      strength.value =
        env.reducedMotion || Math.abs(strength.value - gain) < 0.001
          ? gain
          : T.MathUtils.damp(strength.value, gain, 8, delta);
      if (gain === 0 || !current || !target || transition >= 1) return;
      elapsed += delta;
      if (elapsed < 0.07) return;
      const step = Math.min(1 - transition, elapsed / 0.44);
      const fraction = step / (1 - transition);
      transition += step;
      elapsed = 0;
      if (transition >= 0.999) {
        current.set(target);
        transition = 1;
      } else
        for (let i = 0; i < volumeBytes; i++)
          current[i] += Math.round((target[i] - current[i]) * fraction);
      field.value.needsUpdate = true;
    },
    dispose() {
      field.value.dispose();
    },
  };
}
