import * as T from 'three';
import { canvasTexture, group, mesh, surface, type XYZ } from './geometry';
import type { Locale } from '../app/locale';
import type { Palette } from './materials';
import { installMotherboard } from './motherboard';
import { fittedCable, pcPowerHarness } from './case-interior-parts';
import { ryuoIV } from './ryuo-iv';
import { deferredDisplayModel, loadDisplayModel } from './display-model';
import { disposeSubtree } from './engine/hero-lru';
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
  displayGlass.customProgramCacheKey = () => 'lg-oled-display';
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

type AzothExplodeLayer = 'wristpad' | 'pcb' | 'plate' | 'bases' | 'stems' | 'lids' | 'keycaps';

type AzothLayerConfig = {
  dy: number;
  dz: number;
  openDelay: number;
  closeDelay: number;
};

const AZOTH_LAYERS: Record<AzothExplodeLayer, AzothLayerConfig> = {
  wristpad: { dy: 0, dz: 0.02, openDelay: 0.0, closeDelay: 0.06 },
  pcb: { dy: 0.007, dz: 0, openDelay: 0.04, closeDelay: 0.05 },
  plate: { dy: 0.018, dz: 0, openDelay: 0.08, closeDelay: 0.04 },
  bases: { dy: 0.033, dz: 0, openDelay: 0.12, closeDelay: 0.03 },
  stems: { dy: 0.051, dz: 0, openDelay: 0.16, closeDelay: 0.02 },
  lids: { dy: 0.07, dz: 0, openDelay: 0.2, closeDelay: 0.01 },
  keycaps: { dy: 0.096, dz: 0, openDelay: 0.24, closeDelay: 0.0 },
};

const AZOTH_LAYER_NAMES = Object.keys(AZOTH_LAYERS) as AzothExplodeLayer[];
const AZOTH_OPEN_OMEGA = 9.5;
const AZOTH_CLOSE_OMEGA = 14;
const AZOTH_KEYCAP_LEGEND_MIN_Y = 0.022;
const AZOTH_KEYCAP_LEGEND_MIN_NZ = 0.85;

function buildAzothSubGeometry(source: T.BufferGeometry, triangleIndices: readonly number[]) {
  const remap = new Map<number, number>();
  const ordered: number[] = [];
  const newIndices = new Array<number>(triangleIndices.length);
  for (let i = 0; i < triangleIndices.length; i++) {
    const oldIndex = triangleIndices[i];
    let nextIndex = remap.get(oldIndex);
    if (nextIndex === undefined) {
      nextIndex = ordered.length;
      remap.set(oldIndex, nextIndex);
      ordered.push(oldIndex);
    }
    newIndices[i] = nextIndex;
  }

  const geometry = new T.BufferGeometry();
  const vertexCount = ordered.length;
  for (const [name, attr] of Object.entries(source.attributes)) {
    const { itemSize } = attr;
    if (attr instanceof T.InterleavedBufferAttribute) {
      const values = new Float32Array(vertexCount * itemSize);
      for (let i = 0; i < vertexCount; i++) {
        const src = ordered[i];
        const offset = i * itemSize;
        values[offset] = attr.getX(src);
        if (itemSize > 1) values[offset + 1] = attr.getY(src);
        if (itemSize > 2) values[offset + 2] = attr.getZ(src);
        if (itemSize > 3) values[offset + 3] = attr.getW(src);
      }
      geometry.setAttribute(name, new T.BufferAttribute(values, itemSize, false));
    } else {
      const srcArray = attr.array;
      const ArrayCtor = srcArray.constructor as new (length: number) => T.TypedArray;
      const dstArray = new ArrayCtor(vertexCount * itemSize);
      for (let i = 0; i < vertexCount; i++) {
        const srcOffset = ordered[i] * itemSize;
        const dstOffset = i * itemSize;
        for (let c = 0; c < itemSize; c++) {
          dstArray[dstOffset + c] = srcArray[srcOffset + c];
        }
      }
      geometry.setAttribute(name, new T.BufferAttribute(dstArray, itemSize, attr.normalized));
    }
  }
  const indexArray =
    vertexCount > 65535 ? new Uint32Array(newIndices) : new Uint16Array(newIndices);
  geometry.setIndex(new T.BufferAttribute(indexArray, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

function splitAzothSilverTransfer(source: T.BufferGeometry) {
  const position = source.getAttribute('position');
  if (!position) return null;
  const index = source.index;
  const triangleCount = Math.floor((index ? index.count : position.count) / 3);
  const chassisIndices: number[] = [];
  const keycapIndices: number[] = [];

  for (let t = 0; t < triangleCount; t++) {
    const i0 = index ? index.getX(t * 3) : t * 3;
    const i1 = index ? index.getX(t * 3 + 1) : t * 3 + 1;
    const i2 = index ? index.getX(t * 3 + 2) : t * 3 + 2;

    const x0 = position.getX(i0);
    const y0 = position.getY(i0);
    const z0 = position.getZ(i0);
    const x1 = position.getX(i1);
    const y1 = position.getY(i1);
    const z1 = position.getZ(i1);
    const x2 = position.getX(i2);
    const y2 = position.getY(i2);
    const z2 = position.getZ(i2);

    const cy = (y0 + y1 + y2) / 3;
    const ux = x1 - x0;
    const uy = y1 - y0;
    const uz = z1 - z0;
    const vx = x2 - x0;
    const vy = y2 - y0;
    const vz = z2 - z0;
    const nx = uy * vz - uz * vy;
    const ny = uz * vx - ux * vz;
    const nz = ux * vy - uy * vx;
    const len = Math.hypot(nx, ny, nz);
    const faceNz = len > 0 ? nz / len : 0;

    if (cy > AZOTH_KEYCAP_LEGEND_MIN_Y && faceNz > AZOTH_KEYCAP_LEGEND_MIN_NZ) {
      keycapIndices.push(i0, i1, i2);
    } else {
      chassisIndices.push(i0, i1, i2);
    }
  }

  if (chassisIndices.length === 0 || keycapIndices.length === 0) return null;
  return {
    chassis: buildAzothSubGeometry(source, chassisIndices),
    keycaps: buildAzothSubGeometry(source, keycapIndices),
  };
}

function stepCriticallyDamped(
  state: { value: number; velocity: number },
  target: number,
  omega: number,
  dt: number,
) {
  const diff = state.value - target;
  const temp = (state.velocity + omega * diff) * dt;
  const decay = Math.exp(-omega * dt);
  state.velocity = (state.velocity - omega * temp) * decay;
  state.value = target + (diff + temp) * decay;
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
  unit.userData.studioDynamic = true;
  const legendMaterials = aura.map(
    () => new T.MeshStandardMaterial({ color: '#c7c7c3', roughness: 0.59, side: T.DoubleSide }),
  );
  const badge = surface('#ffffff', 0.26);
  badge.emissive.set(0xffffff);
  const lighting = new Map<string, T.Material>([['Azoth OLED', badge]]);
  const details = productDetail();
  const switches = group(unit, 'Azoth switch assembly');
  switches.userData.studioWarmable = true;
  details.close(switches);

  const layerMeshes: Record<AzothExplodeLayer, T.Mesh[]> = {
    wristpad: [],
    pcb: [],
    plate: [],
    bases: [],
    stems: [],
    lids: [],
    keycaps: [],
  };
  const layerState: Record<AzothExplodeLayer, { value: number; velocity: number }> = {
    wristpad: { value: 0, velocity: 0 },
    pcb: { value: 0, velocity: 0 },
    plate: { value: 0, velocity: 0 },
    bases: { value: 0, velocity: 0 },
    stems: { value: 0, velocity: 0 },
    lids: { value: 0, velocity: 0 },
    keycaps: { value: 0, velocity: 0 },
  };
  let targetExploded = false;
  let phaseTime = 0;

  function applyMeshOffset(part: T.Mesh, layer: AzothExplodeLayer, factor: number) {
    let rest = part.userData.azothRestPos as T.Vector3 | undefined;
    if (!rest) {
      rest = part.position.clone();
      part.userData.azothRestPos = rest;
    }
    const { dy, dz } = AZOTH_LAYERS[layer];
    part.position.set(rest.x, rest.y + dy * factor, rest.z + dz * factor);
  }

  function registerLayerMesh(part: T.Mesh, layer: AzothExplodeLayer) {
    part.userData.azothLayer = layer;
    part.userData.azothRestPos = part.position.clone();
    layerMeshes[layer].push(part);
    const factor = layerState[layer].value;
    if (factor > 0) applyMeshOffset(part, layer, factor);
  }

  function applyAllLayers() {
    for (const layer of AZOTH_LAYER_NAMES) {
      const factor = layerState[layer].value;
      const meshes = layerMeshes[layer];
      for (let i = 0; i < meshes.length; i++) {
        applyMeshOffset(meshes[i], layer, factor);
      }
    }
    unit.updateMatrixWorld(true);
  }

  function createSwitchLoader() {
    return deferredDisplayModel(switches, '/media/models/rog-azoth-extreme-switches.glb', {
      mesh(part) {
        if (!(part.material instanceof T.Material)) return;
        const matName = part.material.name;
        if (matName === 'Azoth · clear switch lid') {
          registerLayerMesh(part, 'lids');
        } else if (matName === 'Azoth · snow-white POM stem') {
          registerLayerMesh(part, 'stems');
        } else if (matName === 'Azoth · NX Snow lower POM') {
          registerLayerMesh(part, 'bases');
        }
      },
      mounted(scene) {
        if (AZOTH_LAYER_NAMES.some((layer) => layerState[layer].value > 0)) {
          unit.updateMatrixWorld(true);
        }
        detailMounted(scene);
      },
    });
  }

  let loadSwitches = createSwitchLoader();
  const prepareSwitches = (loaderManager?: T.LoadingManager) => loadSwitches(loaderManager);
  if (switches.visible) void prepareSwitches(manager);
  aura.forEach((light, index) => {
    const suffix = String(index).padStart(2, '0');
    lighting.set('Azoth diffuser ' + suffix, light);
    lighting.set('Azoth legend ' + suffix, legendMaterials[index]);
  });
  let silverTransferMesh: T.Mesh | undefined;
  loadDisplayModel(unit, '/media/models/rog-azoth-extreme.glb', manager, {
    mesh(part) {
      if (!(part.material instanceof T.Material)) return;
      const matName = part.material.name;
      if (
        matName === 'Azoth · graphite doubleshot PBT' ||
        matName === 'Azoth · modifiers' ||
        matName.startsWith('Azoth legend ')
      ) {
        registerLayerMesh(part, 'keycaps');
      } else if (matName === 'Azoth · carbon-fiber positioning plate') {
        registerLayerMesh(part, 'plate');
      } else if (matName === 'Azoth · PCB silk' || matName.startsWith('Azoth diffuser ')) {
        registerLayerMesh(part, 'pcb');
      } else if (matName === 'Azoth · silicone wrist pad') {
        registerLayerMesh(part, 'wristpad');
      } else {
        part.userData.azothLayer = 'chassis';
        if (matName === 'Azoth · silver transfer') {
          silverTransferMesh = part;
        }
      }
      const replacement = lighting.get(matName);
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
    mounted() {
      const part = silverTransferMesh;
      const partParent = part?.parent;
      silverTransferMesh = undefined;
      if (part && partParent) {
        const split = splitAzothSilverTransfer(part.geometry);
        if (split) {
          part.geometry.dispose();
          part.geometry = split.chassis;
          part.userData.azothLayer = 'chassis';
          const legendMesh = new T.Mesh(split.keycaps, part.material);
          legendMesh.name = part.name + ' · keycap legends';
          legendMesh.position.copy(part.position);
          legendMesh.quaternion.copy(part.quaternion);
          legendMesh.scale.copy(part.scale);
          legendMesh.castShadow = part.castShadow;
          legendMesh.receiveShadow = part.receiveShadow;
          legendMesh.layers.mask = part.layers.mask;
          legendMesh.renderOrder = part.renderOrder;
          legendMesh.userData.studioDynamic = true;
          partParent.add(legendMesh);
          registerLayerMesh(legendMesh, 'keycaps');
        }
      }
    },
  });

  function snapExplosion(open: boolean) {
    const goal = open ? 1 : 0;
    let changed = false;
    for (const layer of AZOTH_LAYER_NAMES) {
      const state = layerState[layer];
      if (state.value !== goal || state.velocity !== 0) {
        state.value = goal;
        state.velocity = 0;
        changed = true;
      }
    }
    if (changed) applyAllLayers();
    details.select(open);
    return changed;
  }

  return {
    unit,
    legendMaterials,
    badge,
    prepareSwitches,
    evictSwitches() {
      layerMeshes.lids.length = 0;
      layerMeshes.stems.length = 0;
      layerMeshes.bases.length = 0;
      details.select(false);
      disposeSubtree(switches, { keepRoot: true });
      loadSwitches = createSwitchLoader();
    },
    preloadHero() {
      void prepareSwitches();
    },
    selectDetail(inspecting: boolean, reducedMotion = false) {
      if (inspecting !== targetExploded) {
        targetExploded = inspecting;
        phaseTime = 0;
      }
      if (inspecting) {
        details.select(true);
        void prepareSwitches();
      }
      if (reducedMotion) {
        snapExplosion(inspecting);
      }
    },
    updateExplosion(delta: number, reducedMotion: boolean) {
      const goal = targetExploded ? 1 : 0;
      if (reducedMotion) return snapExplosion(targetExploded);
      let moving = false;
      let anyOpen = false;
      for (const layer of AZOTH_LAYER_NAMES) {
        const state = layerState[layer];
        if (state.value !== goal || state.velocity !== 0) {
          moving = true;
          break;
        }
      }
      if (!moving) {
        if (!targetExploded && switches.visible) details.select(false);
        return false;
      }
      phaseTime += delta;
      const omega = targetExploded ? AZOTH_OPEN_OMEGA : AZOTH_CLOSE_OMEGA;
      for (const layer of AZOTH_LAYER_NAMES) {
        const state = layerState[layer];
        const delay = targetExploded
          ? AZOTH_LAYERS[layer].openDelay
          : AZOTH_LAYERS[layer].closeDelay;
        if (phaseTime >= delay) {
          stepCriticallyDamped(state, goal, omega, delta);
          if (Math.abs(state.value - goal) < 0.0005 && Math.abs(state.velocity) < 0.001) {
            state.value = goal;
            state.velocity = 0;
          }
        }
        if (state.value > 0) anyOpen = true;
      }
      applyAllLayers();
      if (!targetExploded && !anyOpen) {
        details.select(false);
      }
      return true;
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
