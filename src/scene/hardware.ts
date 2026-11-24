import * as T from 'three';
import { canvasTexture, group, mesh, surface, tube, type XYZ } from './geometry';
import { assetUrl } from '../app/asset-url';
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
import { hasParts, loadParts } from './blender-library';
import { partLibraryPath } from './blender-parts';
import { rogEye } from './rog-mark';
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

function chassisFanRotor(
  parent: T.Object3D,
  position: XYZ,
  p: Palette,
  bladeMaterial: T.MeshStandardMaterial,
  rotorParts: readonly T.BufferGeometry[],
  label: T.Material,
) {
  const unit = group(parent, 'ROG Strix Fan Model 14 ARGB', position);
  const rotor = group(unit, 'Fan rotor');
  mesh(rotor, rotorParts[0], bladeMaterial);
  mesh(rotor, rotorParts[1], bladeMaterial);
  mesh(rotor, rotorParts[2], p.graphite);
  mesh(rotor, new T.PlaneGeometry(0.03, 0.008), label, [0, 0, 0.00887]).castShadow = false;
  return unit;
}

function mountChassisFanFrames(fans: readonly { unit: T.Group; exhaust: boolean }[]) {
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
  for (const { unit, exhaust } of fans) {
    for (const { geometry, material, finish } of frame) {
      const item = mesh(unit, geometry, material);
      item.name = 'Model 14 stationary frame · ' + finish;
      if (exhaust && finish === 'screws') {
        item.rotation.x = Math.PI;
        item.position.z = -0.011;
      }
    }
  }
}

function createRoomGpuRotors(parent: T.Object3D, p: Palette) {
  const rotors = group(parent, 'ROG Astral room fan rotors', [0.004 - 0.0047, -0.008, -0.1236]);
  rotors.scale.x = 0.936;
  const impeller = blenderMesh('astral-impeller-shell');
  const polymer = surface('#44464a', 0.38, 0.17);
  const mark = new T.MeshStandardMaterial({
    map: rogEye('lit'),
    color: '#bebbb5',
    roughness: 0.43,
    alphaTest: 0.4,
  });
  const addRotor = (mount: T.Group, counterRotating = false) => {
    if (counterRotating) mount.scale.x = -1;
    const rotor = group(mount, 'Fan rotor');
    mesh(rotor, impeller, polymer).name = 'Axial-tech cambered blades and rotating tip ring';
    tube(rotor, [0, 0, -0.0025], [0, 0, 0.006], 0.018, p.graphite, 0.0168);
    mesh(rotor, new T.TorusGeometry(0.0168, 0.00058, 5, 48), p.steel, [0, 0, 0.006]);
    const eye = mesh(rotor, new T.PlaneGeometry(0.026, 0.015), mark, [0, 0, 0.00634]);
    eye.scale.x = counterRotating ? -1 : 1;
    eye.castShadow = false;
  };
  for (const [index, z] of ([-0.116, 0, 0.116] as const).entries()) {
    const intake = group(rotors, 'Axial-tech room intake ' + (index + 1), [0, -0.033, z]);
    intake.rotation.x = Math.PI / 2;
    addRotor(intake, index === 1);
  }
  const reverse = group(rotors, 'Fourth room pass-through fan', [0, 0.033, 0.116]);
  reverse.rotation.x = -Math.PI / 2;
  addRotor(reverse);
  return rotors;
}

const LIVE_TOWER_MESH_NAMES = new Set([
  'GR701 port tempered glass',
  'GR701 starboard tempered glass',
  'GR701 front assembly · light',
  'Thor 1600W Titanium III • aura',
  'Thor OLED power draw',
]);

function isInsideNamedAncestor(
  node: T.Object3D,
  ancestorName: string,
  stopAt: T.Object3D,
): boolean {
  for (let cur: T.Object3D | null = node; cur && cur !== stopAt; cur = cur.parent) {
    if (cur.name === ancestorName) return true;
  }
  return false;
}

function isLiveTowerMesh(part: T.Mesh, towerRoot: T.Object3D): boolean {
  if (LIVE_TOWER_MESH_NAMES.has(part.name)) return true;
  if (isInsideNamedAncestor(part, 'ROG Hyperion GR701 chassis', towerRoot)) return true;
  if (isInsideNamedAncestor(part, 'ROG Astral GeForce RTX 5090 · PCIe 5.0 slot', towerRoot)) {
    return false;
  }
  if (isInsideNamedAncestor(part, 'Fan rotor', towerRoot)) return true;
  if (
    isInsideNamedAncestor(part, 'ROG Ryuo IV · curved 6.67-inch AMOLED and cold plate', towerRoot)
  ) {
    const mat = part.material;
    if (!Array.isArray(mat) && mat instanceof T.MeshStandardMaterial && mat.emissiveMap) {
      return true;
    }
  }
  return false;
}

export type TowerOptions = {
  roomLod?: boolean;
  mounted?: (scene: T.Group) => void;
};

export function tower(
  parent: T.Object3D,
  p: Palette,
  aura: T.MeshStandardMaterial[],
  manager: T.LoadingManager,
  options: TowerOptions = {},
) {
  const details = productDetail();
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  const deferHeroInterior = Boolean(options.roomLod && !authoring);
  const syncHeroParts = !deferHeroInterior && hasParts('pc-hero');
  const { unit, updateLightGuide, showPower, accents, mountCableBay } = workstationCase(
    parent,
    p,
    aura,
    manager,
    details,
    { deferCableBay: !syncHeroParts },
  );
  const { registerLight, setComponentLights: applyComponentLights } = caseComponentLights(
    unit,
    accents,
  );
  const support = group(unit, 'ROG Herculx XH01', [-0.0789, -0.1685, -0.074]);
  support.rotation.y = -Math.PI / 2;
  const ryuo = ryuoIV(unit, p, aura, registerLight, details);
  const { showTemperature } = ryuo;
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
  const fanUnits: Array<{ unit: T.Group; exhaust: boolean }> = [];
  for (const height of [-0.153, -0.013, 0.127]) {
    fanUnits.push({
      unit: chassisFanRotor(unit, [0, height, 0.225], p, intakeBlades, rotorParts, label),
      exhaust: false,
    });
  }
  const exhaustBlades = surface('#bbc3ce', 0.38, 0.04);
  exhaustBlades.emissive = aura[1].emissive;
  exhaustBlades.emissiveMap = scattering;
  fanUnits.push({
    unit: chassisFanRotor(unit, [-0.041, 0.137, -0.2812], p, exhaustBlades, rotorParts, label),
    exhaust: true,
  });
  const reflections = caseReflections(unit, aura);
  const roomGpuRotors = syncHeroParts ? undefined : createRoomGpuRotors(unit, p);
  const deferredRotors: T.Object3D[] = [];

  const roomLodGroup = group(unit, 'GR701 room LOD');
  roomLodGroup.visible = false;
  let roomLodReady = false;
  let roomLodFailed = false;
  let roomLodApplied = false;
  let inspectingCase = false;
  let heroInteriorReady = false;
  let heroGlbsRequested = false;
  let heroPartsLoading = false;
  const swappedHidden = new Set<T.Object3D>();

  const shouldShowRoomLod = () =>
    roomLodReady && !roomLodFailed && (!inspectingCase || !heroInteriorReady);

  function applyRoomLodVisibility(useRoomLod: boolean, forceSweep = false) {
    if (!roomLodReady) return;
    if (useRoomLod === roomLodApplied && !forceSweep) return;
    if (useRoomLod) {
      unit.traverse((node) => {
        if (node === roomLodGroup || isInsideNamedAncestor(node, roomLodGroup.name, unit)) return;
        if (
          roomGpuRotors &&
          (node === roomGpuRotors || isInsideNamedAncestor(node, roomGpuRotors.name, unit))
        )
          return;
        if (!(node instanceof T.Mesh) || !node.visible) return;
        if (isLiveTowerMesh(node, unit)) return;
        node.visible = false;
        swappedHidden.add(node);
      });
      roomLodGroup.visible = true;
      if (roomGpuRotors) roomGpuRotors.visible = true;
      roomLodApplied = true;
    } else {
      roomLodGroup.visible = false;
      if (roomGpuRotors) roomGpuRotors.visible = false;
      for (const node of swappedHidden) node.visible = true;
      swappedHidden.clear();
      roomLodApplied = false;
    }
  }

  function mountHeroParts() {
    if (heroInteriorReady) return;
    heroInteriorReady = true;
    mountCableBay();
    const power = pcPowerHarness(unit, p);
    ryuo.mountHero(power.braid);
    mountChassisFanFrames(fanUnits);
    const gpu = astralGraphics(unit, p, aura[0], details, reflections.apply);
    if (!syncHeroParts) {
      gpu.traverse((node) => {
        if (node.name === 'Fan rotor') deferredRotors.push(node);
      });
    }
    const harness = group(gpu, 'Seated 12V-2x6 power and sense loom');
    const graphiteBraid = power.carbon.clone();
    graphiteBraid.color.set('#62646a');
    fittedCable(harness, 'astral-harness-black', power.carbon);
    fittedCable(harness, 'astral-harness-satin', graphiteBraid);
    fittedCable(harness, 'astral-harness-graphite', power.comb);
    details.select(inspectingCase);
    if (roomGpuRotors) roomGpuRotors.visible = shouldShowRoomLod();
  }

  const onHeroSubtreeMounted = (scene: T.Group) => {
    if (shouldShowRoomLod()) applyRoomLodVisibility(true, true);
    options.mounted?.(scene);
  };

  function ensureHeroInterior(
    loaderManager: T.LoadingManager = new T.LoadingManager().setURLModifier(assetUrl),
  ) {
    if (!heroGlbsRequested) {
      heroGlbsRequested = true;
      installMotherboard(unit, loaderManager, registerLight, details, onHeroSubtreeMounted);
      loadDisplayModel(support, '/media/models/rog-herculx-xh01.glb', loaderManager, {
        mesh: registerLight,
        mounted: onHeroSubtreeMounted,
      });
    }
    if (heroInteriorReady || heroPartsLoading) return;
    if (hasParts('pc-hero')) {
      mountHeroParts();
      if (roomLodReady) applyRoomLodVisibility(shouldShowRoomLod(), true);
      options.mounted?.(unit);
      return;
    }
    heroPartsLoading = true;
    const partsItem = partLibraryPath('pc-hero');
    loaderManager.itemStart(partsItem);
    void loadParts('pc-hero')
      .then(() => {
        heroPartsLoading = false;
        mountHeroParts();
        if (roomLodReady) applyRoomLodVisibility(shouldShowRoomLod(), true);
        options.mounted?.(unit);
      })
      .catch(() => {
        heroPartsLoading = false;
        loaderManager.itemError(partsItem);
      })
      .finally(() => {
        loaderManager.itemEnd(partsItem);
      });
  }

  if (syncHeroParts) {
    mountHeroParts();
    ensureHeroInterior(manager);
  } else if (!deferHeroInterior) {
    ensureHeroInterior(manager);
  }

  function selectDetail(inspecting: boolean) {
    if (inspectingCase === inspecting) return;
    inspectingCase = inspecting;
    if (inspecting) {
      ensureHeroInterior();
      details.select(true);
      applyRoomLodVisibility(shouldShowRoomLod());
    } else {
      details.select(false);
      if (roomLodReady) applyRoomLodVisibility(shouldShowRoomLod());
    }
  }

  if (deferHeroInterior) {
    void loadDisplayModel(roomLodGroup, '/media/models/gr701-room.glb', manager, {
      mesh: registerLight,
      mounted(lodScene) {
        roomLodReady = true;
        applyRoomLodVisibility(shouldShowRoomLod(), true);
        options.mounted?.(lodScene);
      },
    }).catch(() => {
      roomLodFailed = true;
      ensureHeroInterior();
    });
  }

  const setComponentLights: typeof applyComponentLights = (enabled, delta, clock, env) => {
    applyComponentLights(enabled, delta, clock, env);
    if (delta !== undefined && !env?.reducedMotion && deferredRotors.length) {
      deferredRotors.forEach((rotor, i) => {
        rotor.rotation.z += delta * (10 + ((i + 7) % 3) * 3.5);
      });
    }
  };

  return {
    unit,
    updateLightGuide,
    updateTelemetry,
    setComponentLights,
    selectDetail,
    preloadHero() {
      ensureHeroInterior();
    },
    refreshRoomLod() {
      if (shouldShowRoomLod()) applyRoomLodVisibility(true, true);
    },
    fanGuides: [exhaustBlades],
    reflections,
  };
}

export function keyboard(
  parent: T.Object3D,
  manager: T.LoadingManager,
  aura: T.MeshStandardMaterial[],
  detailMounted: (scene: T.Group) => void,
  options: { roomLod?: boolean } = {},
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
  let loadSwitches = deferredDisplayModel(
    switches,
    '/media/models/rog-azoth-extreme-switches.glb',
    {
      mounted: detailMounted,
    },
  );
  const prepareSwitches = (loaderManager?: T.LoadingManager) => loadSwitches(loaderManager);
  if (switches.visible) void prepareSwitches(manager);
  aura.forEach((light, index) => {
    const suffix = String(index).padStart(2, '0');
    lighting.set('Azoth diffuser ' + suffix, light);
    lighting.set('Azoth legend ' + suffix, legendMaterials[index]);
  });
  const applyKeyboardMaterial = (part: T.Mesh) => {
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
  };
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  const useRoomLod = Boolean(options.roomLod && !authoring);
  const roomGroup = group(unit, 'Azoth room LOD');
  const roomKeyAnchor = useRoomLod ? group(roomGroup, 'ROG_Azoth_Extreme') : undefined;
  const heroGroup = group(unit, 'Azoth hero detail');
  let roomFailed = false;
  let heroReady = false;
  let inspectingKeys = false;
  const syncBody = () => {
    if (!useRoomLod) return;
    heroGroup.visible = (inspectingKeys || roomFailed) && heroReady;
    roomGroup.visible = !heroGroup.visible;
  };
  const loadHeroBody = deferredDisplayModel(heroGroup, '/media/models/rog-azoth-extreme.glb', {
    mesh: applyKeyboardMaterial,
    mounted(scene) {
      roomKeyAnchor?.removeFromParent();
      heroReady = true;
      syncBody();
      detailMounted(scene);
    },
  });
  if (useRoomLod) {
    syncBody();
    void loadDisplayModel(roomGroup, '/media/models/rog-azoth-extreme-room.glb', manager, {
      mesh: applyKeyboardMaterial,
    }).catch(() => {
      roomFailed = true;
      void loadHeroBody(new T.LoadingManager().setURLModifier(assetUrl));
    });
  } else {
    loadDisplayModel(heroGroup, '/media/models/rog-azoth-extreme.glb', manager, {
      mesh: applyKeyboardMaterial,
    });
  }
  return {
    unit,
    legendMaterials,
    badge,
    switches,
    prepareSwitches,
    evictSwitches() {
      details.select(false);
      disposeSubtree(switches, { keepRoot: true });
      loadSwitches = deferredDisplayModel(
        switches,
        '/media/models/rog-azoth-extreme-switches.glb',
        {
          mounted: detailMounted,
        },
      );
    },
    selectDetail(inspecting: boolean) {
      inspectingKeys = inspecting;
      details.select(inspecting);
      if (inspecting) {
        if (useRoomLod && !heroReady)
          void loadHeroBody(new T.LoadingManager().setURLModifier(assetUrl));
        void prepareSwitches(new T.LoadingManager().setURLModifier(assetUrl));
      }
      syncBody();
    },
    preloadHero() {
      if (useRoomLod && !heroReady)
        void loadHeroBody(new T.LoadingManager().setURLModifier(assetUrl));
      void prepareSwitches(new T.LoadingManager().setURLModifier(assetUrl));
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
