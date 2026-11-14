import * as T from 'three';
import type { Environment } from '../app/environment';
import { canvasTexture, group, mesh } from './geometry';
import { panoramaMaterial, panoramaMeshName, panoramaPoint, waterfrontPoint } from './window-depth';
import type { buildRainGlass } from './rain-glass';

export function panoramaGeometry() {
  const columns = 96,
    rows = 48;
  const positions: number[] = [],
    uvs: number[] = [],
    indices: number[] = [];
  const vertex = new T.Vector3();
  for (let row = 0; row <= rows; row++) {
    const v = row / rows;
    for (let column = 0; column <= columns; column++) {
      const u = column / columns;
      panoramaPoint(u, v, 53, vertex);
      positions.push(vertex.x, vertex.y, vertex.z);
      uvs.push(u, v);
      if (row && column) {
        const index = row * (columns + 1) + column;
        const prior = index - columns - 1;
        indices.push(prior - 1, index - 1, prior, index - 1, index, prior);
      }
    }
  }
  const geometry = new T.BufferGeometry()
    .setAttribute('position', new T.Float32BufferAttribute(positions, 3))
    .setAttribute('uv', new T.Float32BufferAttribute(uvs, 2))
    .setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

const cities = {
  上海: {
    clear: 'shanghai-clear',
    overcast: 'shanghai-day',
    night: 'shanghai-night',
    depth: 'shanghai',
    near: 130,
    far: 980,
    lightDepth: 275,
    lightRow: 0.064,
    waterline: 0.115,
    upright: 0.084,
    calibration: [0.502, 0.282, 0.49, 1.31],
  },
  纽约: {
    clear: 'new-york-day',
    overcast: 'new-york-overcast',
    night: 'new-york-night',
    depth: 'new-york',
    near: 150,
    far: 1100,
    lightDepth: 320,
    lightRow: 0.084,
    waterline: 0.145,
    upright: 0,
    calibration: [0.598, 0.322, 0.39, 1.32],
  },
} as const;

const calibrations = {
  上海: new T.Vector4(...cities.上海.calibration),
  纽约: new T.Vector4(...cities.纽约.calibration),
};

function waterfront(
  parent: T.Group,
  loader: T.TextureLoader,
  glass: ReturnType<typeof buildRainGlass>,
) {
  function loadPlate(asset: string) {
    const color = loader.load('/media/panoramas/' + asset + '.webp');
    color.colorSpace = T.SRGBColorSpace;
    color.anisotropy = 8;
    return color;
  }
  function loadCity(city: Environment['city']) {
    const { clear, overcast, night, depth: asset, near, far, waterline, upright } = cities[city];
    const depth = loader.load('/media/panoramas/' + asset + '-depth.png');
    depth.generateMipmaps = false;
    depth.minFilter = T.LinearFilter;
    const range = new T.Vector2(near, far);
    const shared = {
      night: loadPlate(night),
      depth,
      range,
      waterline,
      upright,
      calibration: calibrations[city],
    };
    return {
      clear: { ...shared, day: loadPlate(clear) },
      overcast: { ...shared, day: loadPlate(overcast) },
    };
  }
  const plates = { 上海: loadCity('上海'), 纽约: loadCity('纽约') };
  const blankDepth = new T.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
  blankDepth.needsUpdate = true;
  const { material, uniforms } = panoramaMaterial(glass);
  const plate = mesh(parent, panoramaGeometry(), material);
  plate.name = panoramaMeshName;
  plate.castShadow = plate.receiveShadow = false;
  const grading = new T.Color();
  let shown = plates.上海.clear,
    target = shown,
    blend = 1;
  return (env: Environment, delta: number, night: number) => {
    const overcast = env.weather !== '晴';
    const desired = plates[env.city][overcast ? 'overcast' : 'clear'];
    if (desired.day.image && desired.night.image && desired !== target) {
      if (desired === shown && blend < 1) {
        shown = target;
        target = desired;
        blend = 1 - blend;
      } else {
        if (blend > 0.5) shown = target;
        target = desired;
        blend = shown === target ? 1 : 0;
      }
    }
    blend = Math.min(1, blend + (env.reducedMotion ? 1 : delta * 2));
    if (blend === 1) shown = target;
    plate.visible = Boolean(shown.day.image);
    uniforms.photoA.value = shown.day;
    uniforms.photoB.value = target.day;
    uniforms.nightA.value = shown.night.image ? shown.night : shown.day;
    uniforms.nightB.value = target.night.image ? target.night : target.day;
    uniforms.depthA.value = shown.depth.image ? shown.depth : blankDepth;
    uniforms.depthB.value = target.depth.image ? target.depth : blankDepth;
    uniforms.rangeA.value.copy(shown.range);
    uniforms.rangeB.value.copy(target.range);
    uniforms.calibrationA.value.copy(shown.calibration);
    uniforms.calibrationB.value.copy(target.calibration);
    uniforms.waterlines.value.set(shown.waterline, target.waterline);
    uniforms.verticalCorrections.value.set(shown.upright, target.upright);
    uniforms.sameDepth.value = shown.depth === target.depth;
    uniforms.blend.value = shown === target ? 0 : T.MathUtils.smoothstep(blend, 0, 1);
    uniforms.night.value = night;
    const ease = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 3);
    uniforms.mist.value = T.MathUtils.lerp(uniforms.mist.value, overcast ? 0.23 : 0, ease);
    grading.set(
      env.weather === '雨'
        ? '#d4dee9'
        : env.weather === '雪'
          ? '#e1e8f0'
          : env.weather === '阴'
            ? '#e1e5ed'
            : '#ffffff',
    );
    if (env.season === '冬') grading.multiplyScalar(0.97);
    uniforms.grade.value.lerp(grading, ease);
  };
}

function distantPassage(parent: T.Group) {
  const ferry = group(parent, 'Passing river ferry');
  const image = canvasTexture(256, 96, (ctx) => {
    for (const [x, y, color] of [
      [63, 38, '#ffdcab'],
      [92, 38, '#efcf9e'],
      [119, 38, '#fff3d3'],
      [146, 38, '#f5deba'],
      [176, 33, '#f4f2e0'],
      [195, 41, '#c96e53'],
    ] as const) {
      const glow = ctx.createRadialGradient(x, y, 0, x, y, 8);
      glow.addColorStop(0, color);
      glow.addColorStop(1, color + '00');
      ctx.fillStyle = glow;
      ctx.fillRect(x - 8, y - 8, 16, 16);
      for (let i = 0; i < 7; i++) {
        ctx.globalAlpha = (1 - i / 7) * 0.15;
        ctx.fillStyle = color;
        ctx.fillRect(x - 2 + Math.sin(i * 3 + x) * 4, y + 7 + i * 2, 3 + i, 1);
      }
      ctx.globalAlpha = 1;
    }
  });
  const lights = new T.MeshBasicMaterial({
    map: image,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  });
  const glints = mesh(ferry, new T.PlaneGeometry(16, 4.8), lights);
  glints.castShadow = glints.receiveShadow = false;
  glints.renderOrder = -2;
  return (time: number, night: number, city: Environment['city'], viewer: T.Vector3) => {
    const position = (time * 0.039 + 0.36) % 1;
    const { lightDepth, lightRow, waterline, upright } = cities[city];
    waterfrontPoint(
      T.MathUtils.lerp(0.17, 0.85, position),
      lightRow,
      calibrations[city],
      lightDepth,
      waterline,
      ferry.position,
      upright,
    );
    glints.rotation.y = Math.atan2(viewer.x - ferry.position.x, viewer.z - ferry.position.z);
    lights.opacity = night * Math.min(1, position * 9, (1 - position) * 9) * 0.84;
  };
}

export function buildExterior(
  root: T.Group,
  loader: T.TextureLoader,
  glass: ReturnType<typeof buildRainGlass>,
) {
  const world = group(root, 'Outdoor volume');
  const plate = waterfront(world, loader, glass);
  const passage = distantPassage(world);
  let time = 0,
    darkness = 1;
  return {
    world,
    update(env: Environment, delta: number, viewer: T.Vector3) {
      if (!env.reducedMotion) time += delta;
      darkness = T.MathUtils.lerp(
        darkness,
        Number(env.night),
        env.reducedMotion ? 1 : 1 - Math.exp(-delta * 4),
      );
      plate(env, delta, darkness);
      passage(time, darkness, env.city, viewer);
    },
  };
}
