import * as T from 'three';
import type { Environment } from '../app/environment';
import { box, canvasTexture, group, mesh, random, tube, type XYZ } from './geometry';
import { plasterUV, type Palette } from './materials';
import { buildExterior } from './exterior';
import { windowOpening } from './furniture';
import { pottedPlant } from './props';
import { buildRainGlass } from './rain-glass';

export { windowOpening } from './furniture';

function precipitation(parent: T.Object3D, snow: boolean) {
  const rng = random(snow ? 701 : 54);
  const count = snow ? 460 : 510;
  const values = new Float32Array(count * (snow ? 3 : 6));
  const particles = Array.from({ length: count }, () => ({
    x: -1.58 - rng() * 4.8,
    y: rng() * 4 - 0.3,
    z: rng() * 8 - 3.5,
    speed: snow ? 0.16 + rng() * 0.39 : 3.2 + rng() * 3.8,
    length: 0.006 + rng() * 0.014,
  }));
  const geometry = new T.BufferGeometry().setAttribute(
    'position',
    new T.BufferAttribute(values, 3).setUsage(T.DynamicDrawUsage),
  );
  const snowMaterial = snow
    ? new T.PointsMaterial({
        color: '#eff4ff',
        map: snowCrystal(),
        size: 0.082,
        opacity: 0.79,
        transparent: true,
        depthWrite: false,
      })
    : null;
  if (snowMaterial) {
    const flakeRandom = random(417);
    geometry.setAttribute(
      'flakeScale',
      new T.Float32BufferAttribute(
        Array.from({ length: count }, () => 0.6 + flakeRandom() ** 1.8 * 1.15),
        1,
      ),
    );
    snowMaterial.onBeforeCompile = (shader) => {
      shader.vertexShader =
        'attribute float flakeScale;\n' +
        shader.vertexShader.replace('gl_PointSize = size;', 'gl_PointSize = size * flakeScale;');
    };
  }
  const material =
    snowMaterial ??
    new T.LineBasicMaterial({
      color: '#a6c5db',
      opacity: 0.12,
      transparent: true,
      depthWrite: false,
    });
  const object = snow ? new T.Points(geometry, material) : new T.LineSegments(geometry, material);
  object.frustumCulled = false;
  parent.add(object);
  return {
    object,
    update(delta: number) {
      for (const [i, particle] of particles.entries()) {
        particle.y -= delta * particle.speed;
        particle.z += delta * (snow ? Math.sin(particle.y * 5 + i) * 0.27 : 0.52);
        if (particle.y < -0.4) {
          particle.y = 3.7;
          particle.z = rng() * 8 - 3.5;
        }
        const k = i * (snow ? 3 : 6);
        values[k] = particle.x;
        values[k + 1] = particle.y;
        values[k + 2] = particle.z;
        if (!snow) {
          values[k + 3] = particle.x;
          values[k + 4] = particle.y + particle.speed * particle.length;
          values[k + 5] = particle.z - 0.011;
        }
      }
      geometry.attributes.position.needsUpdate = true;
    },
  };
}

function snowCrystal() {
  return canvasTexture(96, 96, (ctx) => {
    ctx.translate(48, 48);
    const soft = ctx.createRadialGradient(0, 0, 3, 0, 0, 39);
    soft.addColorStop(0, '#f4f6ffde');
    soft.addColorStop(0.35, '#edf2f7a0');
    soft.addColorStop(0.73, '#e2ecfb44');
    soft.addColorStop(1, '#e2ecfb00');
    ctx.fillStyle = soft;
    ctx.fillRect(-40, -40, 80, 80);
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#f7faff88';
    ctx.lineWidth = 5;
    for (let i = 0; i < 6; i++) {
      ctx.save();
      ctx.rotate((i * Math.PI) / 3);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(0, 34);
      ctx.moveTo(-9, 21);
      ctx.lineTo(0, 29);
      ctx.lineTo(9, 21);
      ctx.stroke();
      ctx.restore();
    }
  });
}

export function buildWindow(root: T.Group, p: Palette, loader: T.TextureLoader) {
  const { wall: x, z0, z1, y0, y1, thickness } = windowOpening;
  const centerZ = (z0 + z1) / 2,
    width = z1 - z0;
  const unit = group(root, 'Recessed window');
  const trim = p.woodVertical.clone();
  trim.color.set('#8e8171');
  trim.roughness = 1;
  const trimRails = p.wood.clone();
  trimRails.color.copy(trim.color);
  const frameX = x - 0.154;
  const wallX = x - thickness / 2;
  const segment = (low: number, high: number, from: number, to: number) => {
    const wall = box(
      unit,
      [thickness, high - low, to - from],
      [wallX, (high + low) / 2, (from + to) / 2],
      p.wall,
    );
    wall.geometry = wall.geometry.clone();
    plasterUV(wall.geometry, wall.position);
  };
  segment(0, 2.71, -0.58, z0);
  segment(0, 2.71, z1, 3.19);
  segment(0, y0, z0, z1);
  segment(y1, 2.71, z0, z1);
  for (const y of [y0 + 0.032, y1 - 0.032, y0 + 0.77]) {
    box(unit, [0.09, 0.064, width], [frameX, y, centerZ], trimRails, 0.003);
  }
  for (const z of [z0 + 0.027, z1 - 0.027, centerZ]) {
    box(unit, [0.088, y1 - y0 - 0.04, 0.055], [frameX, (y0 + y1) / 2, z], trim, 0.003);
  }
  for (const z of [z0 + 0.022, z1 - 0.022]) {
    box(unit, [0.019, y1 - y0 - 0.074, 0.027], [x - 0.019, (y0 + y1) / 2, z], p.woodDark, 0.002);
  }
  box(unit, [0.019, 0.026, width - 0.056], [x - 0.019, y1 - 0.029, centerZ], p.woodDark, 0.002);
  box(unit, [0.367, 0.046, width + 0.02], [x - 0.02, y0 + 0.014, centerZ], p.marble, 0.004);
  beamHandle(unit, frameX, y0 + 0.7, centerZ, p);
  const glass = new T.MeshPhysicalMaterial({
    color: '#77a1ce',
    roughness: 0.09,
    metalness: 0.16,
    transparent: true,
    opacity: 0.09,
    clearcoat: 1,
    depthWrite: false,
  });
  const pane = box(
    unit,
    [0.004, y1 - y0 - 0.05, width - 0.044],
    [frameX - 0.013, (y1 + y0) / 2, centerZ],
    glass,
  );
  pane.name = 'Window glass';
  pane.castShadow = false;
  const wetGlass = buildRainGlass(
    new T.Vector3(frameX - 0.017, y0 + 0.04, z1 - 0.025),
    new T.Vector2(width - 0.05, y1 - y0 - 0.08),
  );
  const writing = canvasTexture(704, 223, (ctx) => {
    ctx.translate(352, 110);
    ctx.rotate(-0.062);
    ctx.font = '500 124px Caveat, cursive';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#12263348';
    ctx.fillText('Hello World', 1, 2, 580);
    ctx.fillStyle = '#dce9e38a';
    ctx.fillText('Hello World', 0, 0, 580);
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = '#e3efeb45';
    ctx.strokeText('Hello World', -0.6, -1, 580);
  });
  const condensation = mesh(
    unit,
    new T.PlaneGeometry(0.52, 0.166),
    new T.MeshBasicMaterial({
      map: writing,
      transparent: true,
      opacity: 0.86,
      depthWrite: false,
      toneMapped: false,
    }),
    [frameX + 0.006, y1 - 0.367, z1 - 0.329],
  );
  condensation.name = 'Handwritten message on the upper left pane';
  condensation.rotation.y = Math.PI / 2;
  condensation.castShadow = condensation.receiveShadow = false;
  condensation.renderOrder = 4;
  const blindMaterial = p.wood.clone();
  blindMaterial.color.set('#bcad96');
  const railY = y1 - 0.083;
  box(unit, [0.077, 0.038, width - 0.085], [x - 0.056, railY + 0.02, centerZ], p.woodDark, 0.002);
  const slats = Array.from({ length: 33 }, (_, i) =>
    box(
      unit,
      [0.055, 0.0048, width - 0.091],
      [x - 0.058, railY - i * 0.0055, centerZ],
      blindMaterial,
      0.001,
    ),
  );
  const bottom = box(
    unit,
    [0.056, 0.016, width - 0.086],
    [x - 0.058, railY - 0.19, centerZ],
    p.woodDark,
    0.002,
  );
  const ladder = [-0.62, 0.0, 0.62]
    .map((offset) =>
      [-0.084, -0.032].map((dx) =>
        tube(unit, [x + dx, 0, centerZ + offset], [x + dx, 1, centerZ + offset], 0.0014, p.paper),
      ),
    )
    .flat();
  for (const dz of [0.02, 0.029])
    tube(
      unit,
      [x - 0.012, railY, z1 - 0.084 + dz],
      [x - 0.012, railY - 0.65, z1 - 0.084 + dz],
      0.0012,
      p.paper,
    );
  tube(
    unit,
    [x - 0.012, railY - 0.65, z1 - 0.06],
    [x - 0.012, railY - 0.67, z1 - 0.06],
    0.004,
    p.bronze,
  );
  const { leaves } = pottedPlant(unit, p, [x + 0.081, y0 + 0.036, 0.086]);

  const sky = new T.MeshBasicMaterial({
    color: '#102641',
    side: T.BackSide,
    toneMapped: false,
    depthWrite: false,
  });
  const skyDome = mesh(root, new T.SphereGeometry(60, 32, 20), sky);
  skyDome.castShadow = false;
  skyDome.renderOrder = -10;
  const exterior = buildExterior(root, loader, wetGlass);
  const rain = precipitation(exterior.world, false),
    snow = precipitation(exterior.world, true);
  let openness = 0,
    angle = 0;
  let rainBlend = 0,
    snowBlend = 0;
  const nightSky = new T.Color('#132947'),
    daySky = new T.Color('#a5bfce'),
    overcast = new T.Color('#697f92');
  const skyTarget = new T.Color();
  return {
    pane,
    remoteRest: [x + 0.079, y0 + 0.037, 0.39] satisfies XYZ,
    update(env: Environment, delta: number, viewer: T.Vector3) {
      const immediate = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 7);
      const before = openness + angle;
      openness += ((env.blinds ? 1 : 0) - openness) * immediate;
      angle += ((env.blinds ? [0, 0.58, 1.46][env.angle] : 0) - angle) * immediate;
      const pitch = T.MathUtils.lerp(0.0056, 0.0355, openness);
      slats.forEach((s, i) => {
        s.position.y = railY - (i + 1) * pitch;
        s.rotation.z = angle;
      });
      bottom.position.y = railY - (slats.length + 0.6) * pitch;
      for (const cord of ladder) {
        cord.scale.y = railY - bottom.position.y;
        cord.position.y = (railY + bottom.position.y) / 2;
      }
      skyTarget.copy(env.night ? nightSky : env.weather === '晴' ? daySky : overcast);
      if (env.season === '冬') skyTarget.lerp(new T.Color('#a1aaba'), 0.1);
      sky.color.lerp(skyTarget, immediate);
      const change = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 1.65);
      rainBlend = T.MathUtils.lerp(rainBlend, Number(env.weather === '雨'), change);
      snowBlend = T.MathUtils.lerp(snowBlend, Number(env.weather === '雪'), change);
      wetGlass.update(rainBlend, env.reducedMotion ? 0 : delta);
      exterior.update(env, delta, viewer);
      rain.object.visible = rainBlend > 0.012;
      snow.object.visible = snowBlend > 0.012;
      rain.object.material.opacity = rainBlend * 0.16;
      snow.object.material.opacity = snowBlend * 0.79;
      condensation.material.opacity = T.MathUtils.lerp(
        condensation.material.opacity,
        env.weather === '晴' ? 0.72 : 0.96,
        change,
      );
      if (rain.object.visible) rain.update(env.reducedMotion ? 0 : delta);
      if (snow.object.visible) snow.update(env.reducedMotion ? 0 : delta);
      const seasonal = { 春: 0.245, 夏: 0.27, 秋: 0.17, 冬: 0.23 };
      leaves.forEach((leaf, i) =>
        leaf.color.setHSL(
          seasonal[env.season] + i * 0.012,
          env.season === '冬' ? 0.25 : 0.44,
          0.18 + i * 0.035,
        ),
      );
      return {
        blocked: openness * (0.24 + (angle / 1.46) * 0.76),
        moving: Math.abs(before - openness - angle) > 0.0005,
      };
    },
  };
}

function beamHandle(parent: T.Group, x: number, y: number, z: number, p: Palette) {
  box(parent, [0.018, 0.058, 0.03], [x + 0.048, y, z], p.steel, 0.003);
  tube(parent, [x + 0.049, y, z], [x + 0.074, y, z], 0.007, p.steel);
  tube(parent, [x + 0.074, y, z], [x + 0.074, y - 0.035, z], 0.007, p.steel, 0.004);
}
