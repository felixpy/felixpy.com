import * as T from 'three';
import { cable, canvasTexture, group, mesh, random, surface, type XYZ } from './geometry';
import { loadDisplayModel } from './display-model';
import lunaSections from './kinto-luna-sections.json';

function blownGlass(color: string, opacity: number) {
  return new T.MeshPhysicalMaterial({
    color,
    roughness: 0.14,
    clearcoat: 1,
    clearcoatRoughness: 0.08,
    metalness: 0.04,
    envMapIntensity: 1.5,
    transparent: true,
    opacity,
    depthWrite: false,
  });
}

function floweringQuince(parent: T.Group) {
  const twig = surface('#695447', 0.88);
  const stem = cable(
    parent,
    [
      [-0.01, 0.009, 0.005],
      [0.003, 0.081, 0],
      [0.016, 0.132, -0.013],
      [0.009, 0.205, -0.025],
      [0.031, 0.243, -0.038],
      [0.029, 0.279, -0.05],
    ],
    0.0016,
    twig,
  );
  stem.name = 'Cut flowering quince';
  cable(
    parent,
    [
      [0.013, 0.134, -0.013],
      [-0.003, 0.162, -0.003],
      [-0.029, 0.183, 0.003],
      [-0.044, 0.216, -0.002],
    ],
    0.00121,
    twig,
  );
  cable(
    parent,
    [
      [0.012, 0.208, -0.026],
      [0.044, 0.218, -0.017],
      [0.061, 0.237, -0.011],
    ],
    0.00104,
    twig,
  );
  const petalGeometry = new T.SphereGeometry(1, 12, 8);
  const shadow = surface('#a96867', 0.72);
  const paper = [surface('#d69f94', 0.81), surface('#efd0ba', 0.77), surface('#d1a89b', 0.8)];
  const anther = surface('#ca9b52', 0.82);
  const rng = random(419);
  const sites: XYZ[] = [
    [0.027, 0.248, -0.04],
    [0.016, 0.217, -0.029],
    [-0.025, 0.182, 0.003],
    [-0.04, 0.209, -0.001],
    [0.054, 0.229, -0.014],
  ];
  sites.forEach((where, index) => {
    const flower = group(parent, 'Quince blossom', where);
    flower.rotation.set(-0.43 + rng() * 0.8, index * 2.22, rng() * 0.39);
    const base = mesh(flower, petalGeometry, shadow);
    base.scale.set(0.0038, 0.0033, 0.0026);
    for (let j = 0; j < 5; j++) {
      const petal = group(flower, 'Petal');
      petal.rotation.z = (j * 2 * Math.PI) / 5 + rng() * 0.13;
      const blade = mesh(petal, petalGeometry, paper[(j + index) % 3], [0, 0.006, 0.0014]);
      blade.scale.set(0.0055 + rng() * 0.001, 0.0081, 0.00145);
      blade.rotation.x = 0.22 + rng() * 0.46;
    }
    for (let j = 0; j < 8; j++) {
      const a = j * 2.4;
      const stamen = mesh(flower, petalGeometry, anther, [
        Math.cos(a) * 0.0024,
        Math.sin(a) * 0.0024,
        0.004,
      ]);
      stamen.scale.set(0.00056, 0.00059, 0.0025);
    }
  });
  for (const [x, y, z] of [
    [0.029, 0.277, -0.05],
    [-0.044, 0.215, -0.002],
    [0.059, 0.236, -0.012],
  ]) {
    const bud = mesh(parent, petalGeometry, shadow, [x, y, z]);
    bud.scale.set(0.0029, 0.0052, 0.003);
    bud.rotation.z = -0.35;
  }
}

export function lunaVase(parent: T.Object3D, position: XYZ) {
  const vessel = group(parent, 'KINTO LUNA · bronze glass and quince', position);
  vessel.userData.product = 'KINTO LUNA 20332';
  function install(key: keyof typeof lunaSections, material: T.Material) {
    const profile = lunaSections[key].map(([r, h]) => new T.Vector2(r / 1000, h / 1000));
    const geometry = new T.LatheGeometry(profile, 96);
    const part = mesh(vessel, geometry, material);
    part.name = key;
    part.userData.sillPart = key;
    part.castShadow = !material.transparent;
    return part;
  }
  const glass = blownGlass('#c7a781', 0.31);
  glass.name = 'Brown soda glass · KINTO 20332';
  glass.ior = 1.515;
  glass.roughness = 0.075;
  const water = blownGlass('#dce5df', 0.12);
  water.name = 'Water · 36 mm fill';
  water.ior = 1.333;
  water.metalness = 0;
  water.roughness = 0.055;
  for (const layer of [glass, water]) {
    layer.onBeforeCompile = (shader) => {
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <opaque_fragment>',
        `float grazing = pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), 2.25);
         diffuseColor.a = mix(opacity, 0.82, grazing);
         #include <opaque_fragment>`,
      );
    };
  }
  install('v-glass', glass).renderOrder = 2;
  install('v-water', water).renderOrder = 1;
  const brush = canvasTexture(256, 4, (ctx) => {
    const jitter = random(20332);
    for (let x = 0; x < ctx.canvas.width; x++) {
      const v = Math.round(202 + jitter() * 47);
      ctx.fillStyle = `rgb(${v} ${v} ${v})`;
      ctx.fillRect(x, 0, 1, ctx.canvas.height);
    }
  });
  brush.colorSpace = T.NoColorSpace;
  const brass = new T.MeshStandardMaterial({
    color: '#cfb985',
    metalness: 0.94,
    roughness: 0.38,
    roughnessMap: brush,
  });
  brass.name = 'Spun and hairline brushed brass';
  const plate = install('v-brass', brass);
  const { position: vertices, uv } = plate.geometry.attributes;
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(i, Math.hypot(vertices.getX(i), vertices.getZ(i)) / 0.04, 0.5);
  }
  return { unit: vessel, fallback: () => floweringQuince(vessel) };
}

export function skogDiffuser(
  parent: T.Object3D,
  position: XYZ,
  manager: T.LoadingManager,
  defer: (load: () => void) => void,
) {
  const pivotHeight = 0.112;
  const bottle = group(parent, 'Skandinavisk SKOG · forest scent', [
    position[0],
    position[1] + pivotHeight,
    position[2],
  ]);
  bottle.rotation.y = Math.PI - 0.21;
  const base = group(bottle, 'SKOG bottle base', [0, -pivotHeight, 0]);
  defer(() => loadDisplayModel(base, '/media/models/skog-20303.glb', manager));
  return bottle;
}
