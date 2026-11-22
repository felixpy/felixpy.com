import * as T from 'three';
import type { Environment } from '../app/environment';
import { box, group, mesh, random, tube, type XYZ } from './geometry';
import { snowfall } from './snowfall';
import { plasterUV, type Palette } from './materials';
import { buildExterior } from './exterior';
import { windowOpening } from './layout';
import { sillBotanicals } from './sill-botanicals';
import { buildRainGlass } from './rain-glass';
import { batchMeshes } from './batching';
import { blenderMesh } from './blender-mesh';
const extrusion = 'window-extrusions';
const epdm = 'window-epdm';
const casting = 'amsterdam-casting';
const hinge = 'amsterdam-hinges';
const blindName = 'Aluminium Venetian blind slats';

export { windowOpening } from './layout';

export function editableBlindSlats(root: T.Object3D) {
  const batch = root.getObjectByName(blindName);
  if (!(batch instanceof T.InstancedMesh)) return root;
  const assembly = new T.Group().copy(batch, false);
  for (let i = 0; i < batch.count; i++) {
    const leaf = new T.Mesh(batch.geometry.clone(), batch.material);
    leaf.name = 'Blind slat ' + String(i + 1).padStart(2, '0');
    leaf.castShadow = batch.castShadow;
    leaf.receiveShadow = batch.receiveShadow;
    leaf.userData = { ...batch.userData };
    batch.getMatrixAt(i, leaf.matrix);
    leaf.matrix.decompose(leaf.position, leaf.quaternion, leaf.scale);
    assembly.add(leaf);
  }
  if (batch === root) return assembly;
  batch.parent!.add(assembly);
  batch.removeFromParent();
  return root;
}

function rainfall(parent: T.Object3D) {
  const rng = random(54);
  const count = 340;
  const values = new Float32Array(count * 6);
  const particles = Array.from({ length: count }, () => ({
    x: -1.58 - rng() * 4.8,
    y: rng() * 4 - 0.3,
    z: rng() * 8 - 3.5,
    speed: 3.2 + rng() * 3.8,
    length: 0.0028 + rng() * 0.0065,
  }));
  const geometry = new T.BufferGeometry().setAttribute(
    'position',
    new T.BufferAttribute(values, 3).setUsage(T.DynamicDrawUsage),
  );
  const object = new T.LineSegments(
    geometry,
    new T.LineBasicMaterial({
      color: '#a6c5db',
      opacity: 0.12,
      transparent: true,
      depthWrite: false,
    }),
  );
  object.frustumCulled = false;
  parent.add(object);
  return {
    object,
    update(delta: number) {
      for (let i = 0; i < count; i++) {
        const particle = particles[i];
        particle.y -= delta * particle.speed;
        particle.z += delta * 0.52;
        if (particle.y < -0.4) {
          particle.y = 3.7;
          particle.z = rng() * 8 - 3.5;
        }
        const k = i * 6;
        values[k] = values[k + 3] = particle.x;
        values[k + 1] = particle.y;
        values[k + 2] = particle.z;
        values[k + 4] = particle.y + particle.speed * particle.length;
        values[k + 5] = particle.z - particle.length * 0.58;
      }
      geometry.attributes.position.needsUpdate = true;
    },
  };
}

export function buildWindow(
  root: T.Group,
  p: Palette,
  loader: T.TextureLoader,
  initial: Environment,
) {
  const { wall: x, z0, z1, y0, y1, thickness } = windowOpening;
  const centerZ = (z0 + z1) / 2,
    width = z1 - z0;
  const unit = group(root, 'Recessed window');
  const bronze = p.bronze.clone();
  bronze.color.set('#544f43');
  bronze.roughness = 0.57;
  bronze.metalness = 0.48;
  const gasket = p.rubber.clone();
  gasket.color.set('#272e2e');
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
  const midY = (y0 + y1) / 2;
  const joinery = group(unit, 'Mitred aluminium window and tilt-turn sash', [frameX, y0, z0]);
  mesh(joinery, blenderMesh(extrusion), bronze);
  mesh(joinery, blenderMesh(epdm), gasket);
  const satin = p.steel.clone();
  satin.color.set('#b4b7b8');
  satin.roughness = 0.32;
  mesh(joinery, blenderMesh(casting), satin).name = 'HOPPE Amsterdam satin lever';
  mesh(joinery, blenderMesh(hinge), gasket);
  for (const z of [z0 + 0.009, z1 - 0.009]) {
    box(unit, [0.142, y1 - y0, 0.018], [x - 0.064, midY, z], p.woodVertical, 0.0015);
    box(unit, [0.018, y1 - y0 + 0.034, 0.039], [x + 0.003, midY, z], p.woodVertical, 0.002);
  }
  box(unit, [0.15, 0.019, width - 0.029], [x - 0.063, y1 - 0.009, centerZ], p.wood, 0.002);
  box(unit, [0.414, 0.043, width + 0.066], [x + 0.003, y0 + 0.0155, centerZ], p.limestone, 0.0032);
  box(unit, [0.018, 0.046, width + 0.034], [x + 0.009, y0 - 0.024, centerZ], p.wood, 0.002);
  const glass = new T.MeshPhysicalMaterial({
    color: '#d3dedd',
    roughness: 0.06,
    metalness: 0,
    transparent: true,
    opacity: 0.032,
    clearcoat: 1,
    depthWrite: false,
  });
  const pane = box(
    unit,
    [0.024, y1 - y0 - 0.05, width - 0.044],
    [frameX - 0.003, (y1 + y0) / 2, centerZ],
    glass,
  );
  pane.name = 'Window glass';
  pane.castShadow = false;
  const wetGlass = buildRainGlass(
    new T.Vector3(frameX - 0.017, y0 + 0.04, z1 - 0.025),
    new T.Vector2(width - 0.05, y1 - y0 - 0.08),
  );
  const blindMaterial = p.steel.clone();
  blindMaterial.color.set('#b5b5a6');
  blindMaterial.metalness = 0.24;
  blindMaterial.roughness = 0.49;
  const blindX = x - 0.026;
  const railY = y1 - 0.083;
  box(
    unit,
    [0.077, 0.038, width - 0.085],
    [blindX + 0.002, railY + 0.02, centerZ],
    p.woodDark,
    0.002,
  );
  const blade = new T.Shape();
  blade.moveTo(-0.026, 0.0001);
  blade.quadraticCurveTo(-0.001, 0.0059, 0.026, 0.0001);
  blade.lineTo(0.026, -0.0007);
  blade.quadraticCurveTo(-0.001, 0.0044, -0.026, -0.0007);
  blade.closePath();
  const bladeGeometry = new T.ExtrudeGeometry(blade, {
    depth: width - 0.091,
    curveSegments: 6,
    bevelEnabled: false,
  });
  bladeGeometry.translate(0, 0, -(width - 0.091) / 2);
  const slats = new T.InstancedMesh(bladeGeometry, blindMaterial, 33);
  slats.name = blindName;
  slats.castShadow = slats.receiveShadow = true;
  slats.instanceMatrix.setUsage(T.DynamicDrawUsage);
  unit.add(slats);
  const slatMatrix = new T.Matrix4();
  let lastPitch = -1,
    lastAngle = -1;
  function placeSlats(pitch: number, angle: number) {
    if (pitch === lastPitch && angle === lastAngle) return;
    slatMatrix.makeRotationZ(angle);
    for (let i = 0; i < slats.count; i++) {
      slatMatrix.setPosition(blindX, railY - (i + 1) * pitch, centerZ);
      slats.setMatrixAt(i, slatMatrix);
    }
    slats.instanceMatrix.needsUpdate = true;
    slats.computeBoundingSphere();
    lastPitch = pitch;
    lastAngle = angle;
  }
  const bottom = box(
    unit,
    [0.056, 0.016, width - 0.086],
    [blindX, railY - 0.19, centerZ],
    p.woodDark,
    0.002,
  );
  const ladder = [-0.62, 0.0, 0.62]
    .map((offset) =>
      [-0.026, 0.026].map((dx) =>
        tube(
          unit,
          [blindX + dx, 0, centerZ + offset],
          [blindX + dx, 1, centerZ + offset],
          0.0014,
          p.paper,
        ),
      ),
    )
    .flat();
  for (const dz of [0.02, 0.029])
    tube(
      unit,
      [blindX + 0.046, railY, z1 - 0.084 + dz],
      [blindX + 0.046, railY - 0.65, z1 - 0.084 + dz],
      0.0012,
      p.paper,
    );
  tube(
    unit,
    [blindX + 0.046, railY - 0.65, z1 - 0.06],
    [blindX + 0.046, railY - 0.67, z1 - 0.06],
    0.004,
    p.bronze,
  );
  const tintLeaves = sillBotanicals(
    unit,
    p,
    loader.manager,
    [x + 0.14, y0 + 0.037, 0.086],
    [x + 0.07, y0 + 0.037, 0.94],
  );
  batchMeshes(unit, new Set([pane, bottom, ...ladder]));
  const seasonalTint = {
    春: new T.Color('#f1fff6'),
    夏: new T.Color('#ffffff'),
    秋: new T.Color('#fff0c8'),
    冬: new T.Color('#e2e9e2'),
  };

  const sky = new T.MeshBasicMaterial({
    color: '#102641',
    side: T.BackSide,
    toneMapped: false,
    depthWrite: false,
  });
  const skyDome = mesh(root, new T.SphereGeometry(60, 32, 20), sky);
  skyDome.castShadow = false;
  skyDome.renderOrder = -10;
  const exterior = buildExterior(root, loader, wetGlass, initial);
  const rain = rainfall(exterior.world);
  const updateSnow = snowfall(exterior.world);
  let openness = 0,
    angle = 0;
  function setBlinds(lowered: boolean, tilt: Environment['angle'], blend = 1) {
    const before = openness + angle;
    openness = T.MathUtils.lerp(openness, Number(lowered), blend);
    angle = T.MathUtils.lerp(angle, lowered ? [0, 0.58, 1.46][tilt] : 0, blend);
    const pitch = T.MathUtils.lerp(0.0038, 0.0355, openness);
    placeSlats(pitch, angle);
    bottom.position.y = railY - (slats.count + 0.6) * pitch;
    for (const cord of ladder) {
      cord.scale.y = railY - bottom.position.y;
      cord.position.y = (railY + bottom.position.y) / 2;
    }
    return {
      pitch,
      angle,
      blocked: openness * (0.24 + (angle / 1.46) * 0.76),
      moving: Math.abs(before - openness - angle) > 0.0005,
    };
  }
  setBlinds(initial.blinds, initial.angle);
  let rainBlend = 0,
    snowBlend = 0;
  const nightSky = new T.Color('#132947'),
    daySky = new T.Color('#a5bfce'),
    overcast = new T.Color('#697f92');
  const skyTarget = new T.Color();
  return {
    pane,
    unit,
    setBlinds,
    remoteRest: [x + 0.079, y0 + 0.037, 0.39] satisfies XYZ,
    update(env: Environment, delta: number) {
      const immediate = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 7);
      const blinds = setBlinds(env.blinds, env.angle, immediate);
      skyTarget.copy(env.night ? nightSky : env.weather === '晴' ? daySky : overcast);
      if (env.season === '冬') skyTarget.lerp(new T.Color('#a1aaba'), 0.1);
      sky.color.lerp(skyTarget, immediate);
      const change = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 1.65);
      rainBlend = T.MathUtils.lerp(rainBlend, Number(env.weather === '雨'), change);
      snowBlend = T.MathUtils.lerp(snowBlend, Number(env.weather === '雪'), change);
      wetGlass.update(rainBlend, env.reducedMotion ? 0 : delta);
      exterior.update(env, delta);
      rain.object.visible = rainBlend > 0.012;
      rain.object.material.opacity = rainBlend * (env.night ? 0.063 : 0.088);
      if (rain.object.visible) rain.update(env.reducedMotion ? 0 : delta);
      updateSnow(env, delta, snowBlend);
      tintLeaves(seasonalTint[env.season]);
      return blinds;
    },
  };
}
