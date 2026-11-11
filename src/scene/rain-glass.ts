import * as T from 'three';
import { random } from './geometry';

function heightMap(width: number, height: number) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d', { alpha: false })!;
  const texture = new T.CanvasTexture(canvas);
  texture.generateMipmaps = false;
  texture.minFilter = T.LinearFilter;
  return { context, texture };
}

function bead(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  stretch: number,
  lean: number,
  opacity = 1,
) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(lean);
  ctx.scale(1, stretch);
  ctx.globalAlpha = opacity;
  const dome = ctx.createRadialGradient(0, 0, 0, 0, 0, radius);
  dome.addColorStop(0, '#dedede');
  dome.addColorStop(0.55, '#c0c0c0');
  dome.addColorStop(0.83, '#8f8f8f');
  dome.addColorStop(0.96, '#414141');
  dome.addColorStop(1, 'transparent');
  ctx.fillStyle = dome;
  ctx.fillRect(-radius, -radius, radius * 2, radius * 2);
  ctx.restore();
}

export function buildRainGlass(origin: T.Vector3, size: T.Vector2) {
  const still = heightMap(1600, 1320);
  const running = heightMap(768, 640);
  still.texture.generateMipmaps = true;
  still.texture.minFilter = T.LinearMipmapLinearFilter;
  const rng = random(240);
  for (const [count, min, max] of [
    [1100, 0.9, 2.1],
    [420, 2.1, 4.5],
    [145, 4.5, 8],
    [49, 8, 13],
  ]) {
    for (let i = 0; i < count; i++) {
      const x = rng() * still.context.canvas.width;
      const y = rng() * still.context.canvas.height;
      bead(
        still.context,
        x,
        y,
        T.MathUtils.lerp(min, max, rng()),
        0.92 + rng() * 0.38,
        (rng() - 0.5) * 0.38,
        0.65 + rng() * 0.35,
      );
    }
  }

  const { context: ctx, texture } = running;
  const { width, height } = ctx.canvas;
  const nextDrop = () => ({
    x: (0.03 + rng() * 0.94) * width,
    y: (-0.06 + rng() * 0.81) * height,
    radius: 2.3 + rng() * 3.5,
    travel: (0.2 + rng() * 0.64) * height,
    duration: 2.1 + rng() * 4,
    pause: 0.5 + rng() * 3.2,
    sway: (rng() - 0.5) * 5,
    time: 0,
  });
  const drops = Array.from({ length: 13 }, () => {
    const drop = nextDrop();
    drop.time = rng() * (drop.duration + drop.pause);
    return drop;
  });
  const amount = { value: 0 };
  let elapsed = 0;
  return {
    uniforms: {
      rainAmount: amount,
      rainBeads: { value: still.texture },
      rainRuns: { value: texture },
      glassOrigin: { value: origin },
      glassSize: { value: size },
    },
    update(blend: number, delta: number) {
      amount.value = blend;
      if (blend <= 0.012 || delta <= 0) return;
      elapsed += delta;
      if (elapsed < 1 / 24) return;
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, width, height);
      for (const drop of drops) {
        drop.time += elapsed;
        if (drop.time > drop.pause + drop.duration) Object.assign(drop, nextDrop());
        if (drop.time <= drop.pause) continue;
        const phase = (drop.time - drop.pause) / drop.duration;
        const distance = drop.travel * phase ** 1.7;
        const x = drop.x + Math.sin(phase * 6) * drop.sway;
        const y = drop.y + distance;
        const tail = Math.min(distance, 32 + drop.radius * 11);
        const fade = Math.min(1, phase * 16, (1 - phase) * 8);
        if (tail > 1) {
          const trail = ctx.createLinearGradient(0, y - tail, 0, y);
          trail.addColorStop(0, 'transparent');
          trail.addColorStop(0.75, '#353535');
          trail.addColorStop(1, '#929292');
          ctx.globalAlpha = fade;
          ctx.strokeStyle = trail;
          ctx.lineWidth = Math.max(0.8, drop.radius * 0.44);
          ctx.beginPath();
          ctx.moveTo(x - drop.sway * 0.5, y - tail);
          ctx.quadraticCurveTo(x + drop.sway * 0.55, y - tail * 0.45, x, y);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
        bead(ctx, x, y, drop.radius, 1.18 + phase * 0.42, 0, fade);
      }
      texture.needsUpdate = true;
      elapsed = 0;
    },
  };
}
