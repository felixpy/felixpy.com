import * as T from 'three';
import { box, canvasTexture, group, mesh, surface, tube } from './geometry';
import type { Palette } from './materials';
import { hyperionInterior } from './hyperion-chassis';
import { blenderMesh } from './blender-mesh';
import { cableChamber, fitFrontCheeks } from './gr701-cable-chamber';
import type { ProductDetail } from './product-detail';

export function workstationCase(
  parent: T.Object3D,
  p: Palette,
  aura: T.MeshStandardMaterial[],
  manager: T.LoadingManager,
  details: ProductDetail,
) {
  const assembly = group(parent, 'Computer tower', [1.035, 1.069, -0.048]);
  const unit = group(assembly, 'ROG Hyperion GR701 chassis');
  const w = 0.268;
  box(unit, [0.235, 0.014, 0.549], [0, -0.282, -0.035], p.graphite, 0.004);
  const door = group(unit, 'GR701 starboard service door');
  const { panel, powerLight, showPower } = hyperionInterior(unit, p, manager);

  const glass = new T.MeshPhysicalMaterial({
    color: '#536167',
    metalness: 0.025,
    roughness: 0.2,
    clearcoat: 0.33,
    clearcoatRoughness: 0.14,
    ior: 1.51,
    transparent: true,
    opacity: 0.115,
    depthWrite: false,
  });
  glass.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <lights_fragment_end>',
        `#include <lights_fragment_end>
       reflectedLight.directSpecular *= 0.035;
       #ifdef USE_CLEARCOAT
         clearcoatSpecularDirect *= 0.035;
       #endif`,
      )
      .replace(
        '#include <opaque_fragment>',
        `diffuseColor.a *= 0.70 + 2.10 * pow(1.0 - abs(dot(normal, normalize(vViewPosition))), 3.0);
       #include <opaque_fragment>`,
      );
  };
  const glassPanel = box(unit, [0.004, 0.524, 0.487], [-w / 2 + 0.011, 0, -0.0505], glass, 0.001);
  glassPanel.castShadow = false;
  const rightGlass = glass.clone();
  rightGlass.onBeforeCompile = glass.onBeforeCompile;
  rightGlass.opacity = 0.29;
  const glassDoor = box(
    door,
    [0.004, 0.524, 0.487],
    [w / 2 - 0.011, 0, -0.0505],
    rightGlass,
    0.001,
  );
  glassDoor.name = 'GR701 starboard tempered glass';
  glassDoor.castShadow = false;
  glassDoor.renderOrder = 2;
  cableChamber(unit, door, details);
  for (const y of [-0.263, 0.263]) {
    box(unit, [0.005, 0.006, 0.489], [-w / 2 + 0.012, y, -0.051], p.rubber, 0.001);
    box(unit, [0.0013, 0.0012, 0.484], [-w / 2 + 0.0083, y, -0.051], p.steel, 0.00035);
  }
  for (const z of [-0.295, 0.193])
    box(unit, [0.005, 0.522, 0.006], [-0.122, 0, z], p.rubber, 0.001);
  for (const y of [-0.183, 0.181]) {
    box(unit, [0.009, 0.036, 0.017], [-0.1175, y, -0.295], p.graphite, 0.0015);
    tube(unit, [-0.12, y - 0.019, -0.297], [-0.12, y + 0.019, -0.297], 0.0046, p.steel);
  }
  for (const x of [-0.112, 0.112]) {
    for (const z of [-0.295, 0.181]) {
      const hingePost = x < 0 && z < 0;
      box(
        unit,
        [hingePost ? 0.009 : 0.014, 0.547, 0.016],
        [hingePost ? -0.117 : x, 0, z],
        p.graphite,
        0.002,
      );
      box(unit, [0.045, 0.024, 0.072], [x, -0.306, z], p.rubber, 0.004);
      for (const y of [-0.282, 0.282])
        box(unit, [0.019, 0.029, 0.031], [x, y, z], p.graphite, 0.0014);
    }
  }
  const finishes = {
    cast: surface('#676b73', 0.34, 0.76),
    wing: surface('#83888d', 0.45, 0.72),
    carrier: surface('#292b30', 0.53, 0.13),
    filter: surface('#252629', 0.65, 0.13),
    vane: surface('#383b3f', 0.56, 0.28),
    plate: surface('#ced0d4', 0.46, 0.65),
    light: surface('#667179', 0.28, 0.04),
    ink: surface('#34363b', 0.23, 0.74),
    frame: surface('#41464d', 0.55, 0.48),
  };
  finishes.light.emissive.set(0xffffff);
  finishes.light.emissiveIntensity = 1.55;
  const brush = canvasTexture(256, 4, (ctx) => {
    ctx.fillStyle = '#cdcdcd';
    ctx.fillRect(0, 0, 256, 4);
    for (let i = 0; i < 256; i++) {
      const tone = Math.round(195 + Math.sin(i * 1.47) * 11 + Math.cos(i * 0.53) * 8);
      ctx.fillStyle = 'rgb(' + tone + ',' + tone + ',' + tone + ')';
      ctx.fillRect(i, 0, 1, 4);
    }
  });
  brush.wrapS = brush.wrapT = T.RepeatWrapping;
  brush.repeat.set(5, 1);
  finishes.cast.roughnessMap = brush;
  const wingGrain = new T.TextureLoader(manager).load('/media/materials/metal-brush-normal.webp');
  wingGrain.wrapS = wingGrain.wrapT = T.RepeatWrapping;
  wingGrain.anisotropy = 8;
  finishes.wing.normalMap = wingGrain;
  finishes.wing.normalScale.set(0.49, 0.49);
  finishes.plate.normalMap = wingGrain;
  finishes.plate.normalScale.set(0.43, 0.43);
  const plateGrain = new T.TextureLoader(manager).load('/media/materials/tolomeo-axial-grain.png');
  plateGrain.colorSpace = T.SRGBColorSpace;
  plateGrain.wrapS = plateGrain.wrapT = T.RepeatWrapping;
  plateGrain.anisotropy = 8;
  finishes.plate.map = plateGrain;
  finishes.ink.side = T.DoubleSide;
  fitFrontCheeks(unit, door, finishes.wing);
  for (const [finish, material] of Object.entries(finishes)) {
    if (finish === 'wing') continue;
    const part = mesh(unit, blenderMesh('gr701-fascia-' + finish), material);
    part.name = 'GR701 front assembly · ' + finish;
    if (finish === 'light' || finish === 'ink') part.castShadow = false;
  }
  const io = group(unit, 'Angled front I/O console', [0, 0.2855, 0.217]);
  io.rotation.x = 0.39;
  const ioMaterials = {
    cover: surface('#45474b', 0.51, 0.3),
    well: surface('#15171a', 0.62, 0.1),
    contact: surface('#aaaeb3', 0.28, 0.85),
    key: surface('#393a3f', 0.42, 0.21),
    print: surface('#adaeb1', 0.54, 0.2),
  };
  for (const [name, material] of Object.entries(ioMaterials)) {
    const part = mesh(io, blenderMesh('gr701-front-io-' + name), material);
    part.name = 'GR701 front I/O · ' + name;
    if (name === 'print') part.castShadow = false;
  }
  const radiatorBounce = new T.PointLight('#9376ff', 0, 0.33, 2);
  radiatorBounce.name = 'Ryuo and DIMM light on the pump and backplate';
  radiatorBounce.position.set(-0.038, 0.207, -0.151);
  const intakeBounce = new T.PointLight('#56cfff', 0, 0.36, 2);
  intakeBounce.name = 'Front intake and panel light on the braided loom';
  intakeBounce.position.set(-0.028, 0.035, 0.111);
  const cardBounce = new T.PointLight('#ef6daf', 0, 0.19, 2);
  cardBounce.name = 'Astral edge lighting on the PSU shroud';
  cardBounce.position.set(-0.087, -0.061, -0.11);
  unit.add(radiatorBounce, intakeBounce, cardBounce);
  return {
    unit: assembly,
    showPower,
    accents: { fascia: finishes.light, psu: powerLight },
    updateLightGuide(active: boolean, high: boolean) {
      panel.emissive.setScalar(1).lerp(aura[5].emissive, 0.16);
      panel.emissiveIntensity = active ? 1.45 : 0;
      radiatorBounce.color.copy(aura[1].emissive);
      intakeBounce.color.copy(aura[5].emissive);
      cardBounce.color.copy(aura[0].emissive);
      radiatorBounce.intensity = active ? 0.075 : 0;
      intakeBounce.visible = high;
      intakeBounce.intensity = active ? 0.115 : 0;
      cardBounce.visible = high;
      cardBounce.intensity = active ? 0.075 : 0;
    },
  };
}
