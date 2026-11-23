import * as T from 'three';
import { canvasTexture, group, mesh, surface, type XYZ } from './geometry';
import type { Locale } from '../app/locale';
import type { Palette } from './materials';
import { installMotherboard } from './motherboard';
import { fittedCable, pcPowerHarness } from './case-interior-parts';
import { ryuoIV } from './ryuo-iv';
import { deferredDisplayModel, loadDisplayModel } from './display-model';
import { galleryDisplay } from './gallery-display';
import { astralGraphics } from './astral-graphics';
import { workstationCase } from './workstation-case';
import { pcReadings } from './pc-telemetry';
import { productDetail } from './product-detail';
import { nearfieldSpeaker } from './nearfield-speaker';
import { blenderMesh } from './blender-mesh';
import { caseReflections } from './case-reflections';
import { caseComponentLights } from './case-component-lights';
import { oledWallpaper } from './oled-wallpaper';
import { oledClock } from './oled-clock';
import { markStandardRoomDepth } from './room-depth-prefill';

import { display, deskSetup } from './layout';
export { display, deskSetup } from './layout';

export function monitor(parent: T.Object3D, p: Palette, manager: T.LoadingManager) {
  const { x, y, z, width, height, outerHeight, surface: screenFace } = display;
  const monitor = group(parent, 'LG OLED evo G6 · OLED48G6PCA', [x, y, z]);
  const { screenBar, codexMicro } = galleryDisplay(monitor, p, outerHeight, y, manager, parent);
  const time = { value: 0 };
  const clock = oledClock();
  const displayGlass = new T.MeshStandardMaterial({
    color: '#05090d',
    roughness: 0.42,
    metalness: 0.06,
  });
  Object.assign(displayGlass, { oledTime: time, oledClock: clock.texture });
  displayGlass.onBeforeCompile = (shader) => {
    shader.uniforms.flowTime = time;
    shader.uniforms.oledClock = { value: clock.texture };
    shader.vertexShader =
      'varying vec2 displayUv;\n' +
      shader.vertexShader.replace('#include <uv_vertex>', '#include <uv_vertex>\ndisplayUv = uv;');
    shader.fragmentShader =
      'uniform float flowTime;\nuniform sampler2D oledClock;\nvarying vec2 displayUv;\n' +
      oledWallpaper +
      shader.fragmentShader.replace(
        '#include <emissivemap_fragment>',
        '#include <emissivemap_fragment>\nfloat ink = oledTextCoverage(oledClock, displayUv);\ntotalEmissiveRadiance += mix(oledColour(displayUv, flowTime), oledInk, ink);',
      );
  };
  markStandardRoomDepth(displayGlass);
  const screen = mesh(monitor, new T.PlaneGeometry(width, height), displayGlass, [
    0,
    0,
    screenFace,
  ]);
  screen.castShadow = screen.receiveShadow = false;
  screen.name = 'LG OLED active pixels and clock';
  displayGlass.addEventListener('dispose', () => clock.texture.dispose());
  function updateDisplay(locale: Locale, elapsed: number) {
    time.value = elapsed;
    clock.update(locale);
  }
  return { screen, updateDisplay, screenBar, codexMicro };
}

function chassisFan(
  parent: T.Object3D,
  position: XYZ,
  p: Palette,
  bladeMaterial: T.MeshStandardMaterial,
  rotorParts: readonly T.BufferGeometry[],
  label: T.Material,
  frame: readonly { geometry: T.BufferGeometry; material: T.Material; finish: string }[],
  exhaust: boolean,
) {
  const unit = group(parent, 'ROG Strix Fan Model 14 ARGB', position);
  for (const { geometry, material, finish } of frame) {
    const item = mesh(unit, geometry, material);
    item.name = 'Model 14 stationary frame · ' + finish;
    if (exhaust && finish === 'screws') {
      item.rotation.x = Math.PI;
      item.position.z = -0.011;
    }
  }
  const rotor = group(unit, 'Fan rotor');
  mesh(rotor, rotorParts[0], bladeMaterial);
  mesh(rotor, rotorParts[1], bladeMaterial);
  mesh(rotor, rotorParts[2], p.graphite);
  mesh(rotor, new T.PlaneGeometry(0.03, 0.008), label, [0, 0, 0.00887]).castShadow = false;
  return unit;
}

export function tower(
  parent: T.Object3D,
  p: Palette,
  aura: T.MeshStandardMaterial[],
  manager: T.LoadingManager,
) {
  const details = productDetail();
  const { unit, updateLightGuide, showPower, accents } = workstationCase(
    parent,
    p,
    aura,
    manager,
    details,
  );
  const { registerLight, setComponentLights } = caseComponentLights(unit, accents);
  installMotherboard(unit, manager, registerLight, details);
  const power = pcPowerHarness(unit, p);
  const showTemperature = ryuoIV(unit, p, aura, power.braid, registerLight, details);
  const telemetryMode =
    typeof location === 'undefined'
      ? null
      : new URLSearchParams(location.search).get('studio-pc-telemetry');
  let staticTelemetryMarked = false;
  let typedTelemetryMarked = false;
  let typedActive = false;
  let lastSecond = -1;
  let celsius: number;
  let watts: number;
  function updateTelemetry(time: number, nativeLow = false) {
    if (telemetryMode === 'static' && nativeLow) {
      if (!staticTelemetryMarked) {
        staticTelemetryMarked = true;
        performance.mark('studio-pc-telemetry-static');
      }
      return;
    }
    const typed = nativeLow && telemetryMode !== 'canvas';
    const switched = typed !== typedActive;
    const second = Math.floor(time);
    if (second === lastSecond && !switched) return;
    lastSecond = second;
    const reading = pcReadings(second);
    if (switched || reading.celsius !== celsius) showTemperature(reading.celsius, typed);
    if (switched || reading.watts !== watts) showPower(reading.watts, typed);
    ({ celsius, watts } = reading);
    typedActive = typed;
    if (typed && !typedTelemetryMarked) {
      typedTelemetryMarked = true;
      performance.mark('studio-pc-telemetry-typed');
    }
  }
  updateTelemetry(0);
  const scattering = canvasTexture(96, 32, (ctx) => {
    const gradient = ctx.createLinearGradient(0, 0, 96, 5);
    gradient.addColorStop(0, '#fbfbfb');
    gradient.addColorStop(0.42, '#ababab');
    gradient.addColorStop(0.83, '#616161');
    gradient.addColorStop(1, '#7f7f7f');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 96, 32);
  });
  const rotorParts = ['opal', 'white', 'graphite'].map((finish) =>
    blenderMesh('strix-fan-' + finish),
  );
  const frameMaterials = {
    nylon: surface('#2a2b2f', 0.51),
    satin: surface('#3c3e42', 0.37, 0.09),
    label: surface('#222428', 0.48, 0.05),
    ink: surface('#cbd0d0', 0.49, 0.15),
    screws: surface('#45454a', 0.37, 0.78),
  };
  const frame = Object.entries(frameMaterials).map(([finish, material]) => ({
    geometry: blenderMesh('strix-140-' + finish),
    material,
    finish,
  }));
  const hub = canvasTexture(128, 32, (ctx) => {
    ctx.fillStyle = '#d2d4d8';
    ctx.font = 'italic 700 28px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('R O G', 64, 26);
    ctx.globalCompositeOperation = 'destination-in';
    ctx.beginPath();
    for (let y = 0; y < 32; y += 3) for (let x = 0; x < 128; x += 3) ctx.rect(x, y, 2, 2);
    ctx.fill();
  });
  const label = new T.MeshStandardMaterial({
    map: hub,
    alphaTest: 0.31,
    metalness: 0.28,
    roughness: 0.43,
  });
  const intakeBlades = surface('#474b50', 0.54, 0.03);
  for (const height of [-0.153, -0.013, 0.127])
    chassisFan(unit, [0, height, 0.225], p, intakeBlades, rotorParts, label, frame, false);
  const exhaustBlades = surface('#bbc3ce', 0.38, 0.04);
  exhaustBlades.emissive = aura[1].emissive;
  exhaustBlades.emissiveMap = scattering;
  chassisFan(unit, [-0.041, 0.137, -0.2812], p, exhaustBlades, rotorParts, label, frame, true);
  const reflections = caseReflections(unit, aura);
  const gpu = astralGraphics(unit, p, aura[0], details, reflections.apply);
  const harness = group(gpu, 'Seated 12V-2x6 power and sense loom');
  const graphiteBraid = power.carbon.clone();
  graphiteBraid.color.set('#62646a');
  fittedCable(harness, 'astral-harness-black', power.carbon);
  fittedCable(harness, 'astral-harness-satin', graphiteBraid);
  fittedCable(harness, 'astral-harness-graphite', power.comb);
  const support = group(unit, 'ROG Herculx XH01', [-0.0789, -0.1685, -0.074]);
  support.rotation.y = -Math.PI / 2;
  loadDisplayModel(support, '/media/models/rog-herculx-xh01.glb', manager, { mesh: registerLight });
  return {
    unit,
    updateLightGuide,
    updateTelemetry,
    setComponentLights,
    selectDetail: details.select,
    fanGuides: [exhaustBlades],
    reflections,
  };
}

export function keyboard(
  parent: T.Object3D,
  manager: T.LoadingManager,
  aura: T.MeshStandardMaterial[],
  detailMounted: (scene: T.Group) => void,
) {
  const unit = group(parent, 'Mechanical keyboard', [
    display.x,
    deskSetup.mat.top,
    deskSetup.inputZ,
  ]);
  const legendMaterials = aura.map(
    () => new T.MeshStandardMaterial({ color: '#c7c7c3', roughness: 0.59, side: T.DoubleSide }),
  );
  const badge = surface('#ffffff', 0.26);
  badge.emissive.set(0xffffff);
  const lighting = new Map<string, T.Material>([['Azoth OLED', badge]]);
  const details = productDetail();
  const switches = group(unit, 'Azoth switch assembly');
  details.close(switches);
  const prepareSwitches = deferredDisplayModel(
    switches,
    '/media/models/rog-azoth-extreme-switches.glb',
    { mounted: detailMounted },
  );
  if (switches.visible) void prepareSwitches(manager);
  aura.forEach((light, index) => {
    const suffix = String(index).padStart(2, '0');
    lighting.set('Azoth diffuser ' + suffix, light);
    lighting.set('Azoth legend ' + suffix, legendMaterials[index]);
  });
  loadDisplayModel(unit, '/media/models/rog-azoth-extreme.glb', manager, {
    mesh(part) {
      if (!(part.material instanceof T.Material)) return;
      const replacement = lighting.get(part.material.name);
      if (replacement) {
        if (replacement === badge && part.material instanceof T.MeshStandardMaterial) {
          badge.map = part.material.map;
          badge.emissiveMap = part.material.emissiveMap ?? part.material.map;
          badge.needsUpdate = true;
        }
        part.material.dispose();
        part.material = replacement;
      }
    },
  });
  return {
    unit,
    legendMaterials,
    badge,
    prepareSwitches,
    selectDetail(inspecting: boolean) {
      details.select(inspecting);
      if (inspecting) void prepareSwitches();
    },
  };
}

export function mouse(parent: T.Object3D, manager: T.LoadingManager, glow: T.MeshStandardMaterial) {
  const unit = group(parent, 'Wireless mouse', [
    display.x + 0.36,
    deskSetup.mat.top,
    deskSetup.inputZ,
  ]);
  const badge = glow.clone();
  loadDisplayModel(unit, '/media/models/rog-harpe-extreme.glb', manager, {
    mesh(part) {
      if (!(part.material instanceof T.Material)) return;
      const guide =
        part.material.name === 'Harpe wheel light'
          ? glow
          : part.material.name === 'Harpe palm light guide'
            ? badge
            : undefined;
      if (guide) {
        part.material.dispose();
        part.material = guide;
      }
    },
  });
  return { unit, badge };
}

export function speaker(parent: T.Object3D, p: Palette, side: -1 | 1, meter: T.Material[]) {
  return nearfieldSpeaker(parent, p, side, meter, [
    display.x + side * deskSetup.speakerSpacing,
    0.7515,
    deskSetup.speakerZ,
  ]);
}
