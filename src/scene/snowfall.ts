import * as T from 'three';
import { random } from './geometry';
import type { Environment } from '../app/environment';

function aggregateAtlas() {
  const tile = 64;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = tile * 4;
  const ctx = canvas.getContext('2d')!;
  const rng = random(2419);
  ctx.lineCap = 'round';
  for (let index = 0; index < 16; index++) {
    ctx.save();
    ctx.translate(((index % 4) + 0.5) * tile, (Math.floor(index / 4) + 0.5) * tile);
    const phase = rng() * Math.PI * 2;
    const breadth = 7 + rng() * 7;
    const length = 15 + rng() * 5;
    const crystals = 24 + Math.floor(rng() * 10);
    for (let n = 0; n < crystals; n++) {
      const u = n < 9 ? n / 4 - 1 : 2 * rng() - 1;
      const x = length * u;
      const y =
        3.5 * Math.sin(u * 3 + phase) +
        (n < 9 ? 0 : (2 * rng() - 1) * breadth * Math.sqrt(1 - u * u));
      const radius = 3 + rng() * 5;
      const tilt = rng() * Math.PI;
      ctx.fillStyle = `rgba(255,255,255,${0.35 + rng() * 0.35})`;
      ctx.strokeStyle = `rgba(255,255,255,${0.45 + rng() * 0.35})`;
      ctx.lineWidth = 1.1 + radius * 0.15;
      ctx.beginPath();
      ctx.ellipse(x, y, radius * 0.59, radius * 0.38, tilt, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      for (let arm = 0; arm < 6; arm++) {
        const angle = tilt + (arm * Math.PI) / 3;
        const dx = Math.cos(angle),
          dy = Math.sin(angle);
        const reach = radius * (0.63 + rng() * 0.37);
        ctx.moveTo(x, y);
        ctx.lineTo(x + dx * reach, y + dy * reach);
        ctx.moveTo(x + dx * reach * 0.51, y + dy * reach * 0.51);
        ctx.lineTo(x + (dx * 0.76 - dy * 0.22) * reach, y + (dy * 0.76 + dx * 0.22) * reach);
      }
      ctx.stroke();
    }
    ctx.restore();
  }
  return new T.CanvasTexture(canvas);
}

export function snowfall(parent: T.Object3D) {
  const count = 2350;
  const rng = random(701);
  const positions = new Float32Array(count * 3);
  const features = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) {
    const band = i % 8;
    const depth = band < 2 ? rng() * 2.35 : band < 6 ? 1.55 + rng() * 6.3 : 6 + rng() * 12;
    const height = 4.8 + depth * 1.15;
    const span = 4.2 + depth * 1.8;
    positions.set(
      [-1.57 - depth, 1.45 + (rng() - 0.5) * height, 0.58 + (rng() - 0.5) * span],
      i * 3,
    );
    const aggregate = rng() ** 1.65;
    features.set(
      [
        0.004 + 0.034 * aggregate,
        0.4 + aggregate * 0.46 + 0.28 * rng(),
        rng() * Math.PI * 2,
        rng(),
      ],
      i * 4,
    );
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.BufferAttribute(positions, 3));
  geometry.setAttribute('flake', new T.BufferAttribute(features, 4));
  geometry.boundingSphere = new T.Sphere(new T.Vector3(-10.57, 1.45, 0.58), 25);
  const seconds = { value: 0 };
  const darkness = { value: 0 };
  const material = new T.PointsMaterial({
    color: 0xffffff,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, { seconds, darkness });
    const varyings = 'varying vec4 flakeAppearance;\nvarying vec3 flakeLight;\n';
    shader.vertexShader =
      'attribute vec4 flake;\nuniform float seconds;\nuniform float darkness;\n' +
      varyings +
      shader.vertexShader
        .replace(
          '#include <begin_vertex>',
          `
        float t = seconds;
        float depth = -1.57 - position.x;
        float height = 4.8 + depth * 1.15;
        float span = 4.2 + depth * 1.8;
        float swing = t * (1.35 + 1.6 * flake.w) + flake.z;
        float flutter = sin(swing) + 0.24 * sin(1.8 * swing + flake.z);
        float y = 1.45 + mod(position.y - 1.45 + 0.5 * height - t * flake.y
          + 0.035 * cos(swing * 2.0), height) - 0.5 * height;
        float gust = 0.26 * sin(t * 0.61 + position.x * 0.34 + y * 0.27)
                   + 0.095 * sin(t * 0.95 + position.z * 0.48);
        vec3 transformed = vec3(position.x + 0.068 * cos(swing), y,
          0.58 + mod(position.z - 0.58 + 0.5 * span + t * (0.13 + 0.09 * flake.w) +
          gust + (0.04 + flake.x * 2.8) * flutter, span) - 0.5 * span);
        float spill = exp(-0.47 * depth - 0.26 * abs(transformed.z - 0.58) - 0.19 * abs(y - 1.55));
        flakeLight = mix(vec3(0.94, 0.97, 1.0), vec3(0.22, 0.30, 0.42) +
          vec3(0.62, 0.60, 0.53) * spill, darkness);
        flakeAppearance = vec4(flake.z + 0.69 * flutter + 0.3 * sin(t * 0.64 + flake.z),
          0.64 + 0.36 * abs(cos(swing * 0.69 + flake.z)), floor(flake.w * 16.0), 1.0);
      `,
        )
        .replace(
          '#include <logdepthbuf_vertex>',
          `
        float diameter = gl_PointSize * flake.x * projectionMatrix[1][1];
        gl_PointSize = clamp(diameter + 0.5, 1.45, 54.0 * size);
        flakeAppearance.w = min(diameter / gl_PointSize, 1.0);
        #include <logdepthbuf_vertex>
      `,
        );
    shader.fragmentShader =
      varyings +
      shader.fragmentShader.replace(
        '#include <map_particle_fragment>',
        `
      vec2 p = 2.0 * gl_PointCoord - 1.0;
      float s = sin(flakeAppearance.x), c = cos(flakeAppearance.x);
      p = mat2(c,-s,s,c) * p;
      p.y /= flakeAppearance.y;
      if (max(abs(p.x), abs(p.y)) > 1.0) discard;
      vec2 tile = vec2(mod(flakeAppearance.z, 4.0), floor(flakeAppearance.z * 0.25));
      vec2 uv = (tile + p * 0.5 + 0.5) * 0.25;
      float coverage = texture2D(map, uv).a;
      diffuseColor.a *= coverage * flakeAppearance.w;
      if (diffuseColor.a < 0.012) discard;
      diffuseColor.rgb *= flakeLight;
    `,
      );
  };
  const points = new T.Points(geometry, material);
  points.name = 'Snowfall beyond the window';
  points.visible = false;
  parent.add(points);
  return (environment: Environment, delta: number, density: number) => {
    points.visible = density > 0.012;
    if (!points.visible) return;
    if (!material.map) {
      material.map = aggregateAtlas();
      material.needsUpdate = true;
    }
    darkness.value = Number(environment.night);
    material.opacity = density;
    geometry.setDrawRange(
      0,
      environment.reducedMotion ? 720 : environment.quality === 'high' ? count : 1300,
    );
    if (!environment.reducedMotion) seconds.value += Math.min(delta, 0.12);
  };
}
