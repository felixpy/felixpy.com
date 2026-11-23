import * as T from 'three';
import { fixtureReflections } from './fixture-reflections';
import { blenderMesh } from './blender-mesh';
import { group, luminous, mesh, surface, type XYZ } from './geometry';
import ceilingLayout from './ceiling-light-layout.json';
import type { Palette } from './materials';

function assemble(
  parent: T.Object3D,
  model: string,
  title: string,
  position: XYZ,
  finishes: Record<string, T.Material>,
) {
  const unit = group(parent, title, position);
  for (const [finish, material] of Object.entries(finishes)) {
    const asset = 'fixtures/' + model + '-' + finish;
    const part = mesh(unit, blenderMesh(asset), material);
    part.name = title + ' · ' + finish;
    part.castShadow = finish !== 'glass' && finish !== 'opal';
  }
  return unit;
}

export function deskFixture(
  parent: T.Object3D,
  p: Palette,
  position: XYZ,
  loader: T.TextureLoader,
) {
  const map = loader.load('/media/materials/solarcycle-grille.png');
  const normal = loader.load('/media/materials/solarcycle-grille-normal.png');
  map.colorSpace = T.SRGBColorSpace;
  for (const texture of [map, normal]) {
    texture.wrapS = texture.wrapT = T.RepeatWrapping;
    texture.anisotropy = 4;
  }
  const emitter = luminous('#ffebcc', 1.2);
  const unit = assemble(parent, 'solarcycle', 'Dyson Solarcycle Morph Desk · CD06', position, {
    alloy: surface('#b6b8b5', 0.29, 0.87),
    satin: surface('#c8c9c6', 0.31, 0.77),
    white: surface('#e7e4da', 0.45, 0.12),
    graphite: surface('#555a5b', 0.39, 0.58),
    black: p.rubber,
    steel: surface('#b4b9b7', 0.24, 0.9),
    grille: new T.MeshStandardMaterial({
      map,
      normalMap: normal,
      metalness: 0.74,
      roughness: 0.33,
      transparent: true,
      alphaTest: 0.02,
      depthWrite: false,
    }),
    opal: emitter,
  });
  unit.rotation.y = 0.54;
  const bulb = group(unit, 'Optical center', [0.135, 0.482, 0.263]);
  return { unit, emitter, bulb };
}

export function workbenchFixture(
  parent: T.Object3D,
  p: Palette,
  position: XYZ,
  loader: T.TextureLoader,
) {
  const emitter = luminous('#fff0d9', 1.2);
  const grain = loader.load('/media/materials/tolomeo-axial-grain.png');
  grain.wrapS = grain.wrapT = T.RepeatWrapping;
  grain.anisotropy = 4;
  const finishes = {
    alloy: surface('#c5c8c5', 0.25, 0.96),
    extrusion: new T.MeshStandardMaterial({
      color: '#c1c4c2',
      roughnessMap: grain,
      metalness: 0.96,
      roughness: 0.4,
    }),
    satin: surface('#bec1be', 0.36, 0.84),
    steel: surface('#a5a8a7', 0.25, 0.87),
    black: p.rubber,
    reflector: surface('#ebe7de', 0.38, 0.24),
    opal: emitter,
  };
  const unit = assemble(
    parent,
    'tolomeo-clamp',
    'Artemide Tolomeo Micro · table clamp',
    position,
    finishes,
  );
  const bulb = group(unit, 'Optical center', [0.297, 0.403, 0]);
  const pivot = new T.Vector3(0.25, 0.443, 0);
  bulb.rotation.set(-0.18, 0, 0.502, 'XYZ');
  bulb.position.sub(pivot).applyQuaternion(bulb.quaternion).add(pivot);
  return { unit, emitter, bulb };
}

export function ceilingFixture(parent: T.Object3D) {
  const shell = surface('#f2f1ed', 0.47, 0.08);
  shell.emissive.set('#f4e4d1');
  shell.emissiveIntensity = 0;
  const opal = surface('#efede6', 0.56);
  opal.emissive.set('#ffe0ac');
  const halo = surface('#eeece4', 0.54);
  halo.emissive.set('#ffd49b');
  const reflector = surface('#eeeae4', 0.47);
  reflector.emissive.set('#ffd9a4');
  const [x, y, z] = ceilingLayout.mount;
  const unit = assemble(
    parent,
    'circular-ceiling',
    'Recessed double-ring ceiling light · 300 mm',
    [x, y, z],
    { shell, reflector, opal, halo },
  );
  const outlet = group(unit, 'Ceiling diffuser outlet', [0, -0.093, 0]);
  const cove = new T.PointLight('#ffe3b9', 0, 2.4, 2);
  cove.position.set(0, -0.095, 0);
  return { opal, halo, shell, reflector, outlet, cove };
}

export function cabinetFloorLight(parent: T.Object3D, p: Palette) {
  const polish = surface('#dce0e1', 0.097, 1);
  const opal = luminous('#fff0d7', 0);
  const lining = surface('#f1eee8', 0.4, 0.05);
  lining.emissive.set('#ffd6a5');
  lining.emissiveIntensity = 0;
  const unit = assemble(
    parent,
    'aj-floor',
    'Louis Poulsen AJ Floor · polished stainless steel',
    [-1.055, 0.0005, 2.32],
    {
      polish,
      black: p.rubber,
      steel: surface('#bdc3c3', 0.27, 0.92),
      lining,
      porcelain: surface('#eeebe4', 0.52),
      opal,
    },
  );
  unit.rotation.y = -0.83;
  const light = new T.SpotLight('#ffe2ba', 0, 3.4, 0.91, 0.68, 2);
  light.position.set(0.1, 1.067, 0);
  light.target.position.set(0.424, 0.067, 0);
  unit.add(light, light.target);
  const reflections = fixtureReflections('aj');
  reflections.bind(polish);
  return { unit, light, opal, lining, select: reflections.select };
}
