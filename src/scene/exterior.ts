import * as T from 'three';
import { defaultStudioLoadingManager } from './asset-loading';
import type { Environment } from '../app/environment';
import { group, mesh } from './geometry';
import type { buildRainGlass } from './rain-glass';
import { panoramaMaterial, panoramaMeshName, panoramaPoint, bankSlope } from './window-depth';
import { windowExposure, type WindowExposure } from '../content/window-scenes';
import { riverFerry, type FerryWarmup } from './river-ferry';
import { roomExteriorScissor } from './room-exterior-scissor';

export function panoramaGeometry() {
  const columns = 64,
    rows = 28;
  const positions: number[] = [],
    indices: number[] = [];
  const vertex = new T.Vector3();
  for (let row = 0; row <= rows; row++) {
    for (let column = 0; column <= columns; column++) {
      panoramaPoint(column / columns, row / rows, 53, vertex);
      positions.push(vertex.x, vertex.y, vertex.z);
      if (row && column) {
        const index = row * (columns + 1) + column,
          prior = index - columns - 1;
        indices.push(prior - 1, index - 1, prior, index - 1, index, prior);
      }
    }
  }
  return new T.BufferGeometry()
    .setAttribute('position', new T.Float32BufferAttribute(positions, 3))
    .setIndex(indices);
}

export function buildExterior(
  root: T.Group,
  loader: T.TextureLoader,
  glass: ReturnType<typeof buildRainGlass>,
  initial: Environment,
  warmWaterfront?: (material: T.ShaderMaterial) => void,
  deferWaterMotion = false,
  windowOnlyWater = false,
) {
  const keepStaticMaterial = deferWaterMotion && windowOnlyWater;
  const world = group(root, 'Outdoor volume');
  world.add(glass.highlights);
  const depths = new Map<string, T.Texture>();
  function loadPhoto(asset: string) {
    const image = loader.load('/media/panoramas/' + asset + '.webp');
    image.colorSpace = T.SRGBColorSpace;
    image.anisotropy = 8;
    return image;
  }
  function loadPlate(scene: WindowExposure) {
    const photo = loadPhoto(scene.asset);
    if (scene.kind === 'land') {
      photo.wrapS = T.RepeatWrapping;
      return {
        scene,
        photo,
        depth: photo,
        bank: 0,
        range: new T.Vector2(650, 2000),
        shoreline: new Float32Array(9),
        calibration: new T.Vector4((scene.yaw * Math.PI) / 180, 0, 1, 1),
        current: new T.Vector3(),
      };
    }
    let depth = depths.get(scene.depth);
    if (!depth) {
      depth = loader.load('/media/panoramas/' + scene.depth + '.png');
      depth.magFilter = depth.minFilter = T.LinearFilter;
      depth.generateMipmaps = false;
      depths.set(scene.depth, depth);
    }
    const fy = scene.focal * scene.aspect;
    const bank = scene.shoreline[4];
    return {
      scene,
      photo,
      depth,
      range: new T.Vector2(...scene.range),
      bank,
      calibration: new T.Vector4(scene.center, bank + bankSlope * fy, scene.focal, fy),
      shoreline: Float32Array.from(scene.shoreline),
      current: new T.Vector3(...scene.flow, scene.waveScale),
    };
  }
  const plates = new Map<WindowExposure, ReturnType<typeof loadPlate>>();
  function view(env: Environment) {
    const scene = windowExposure(env.city, env.night, env.weather === '晴');
    let plate = plates.get(scene);
    if (!plate) {
      plate = loadPlate(scene);
      plates.set(scene, plate);
    }
    return plate;
  }
  const { material, uniforms, createMaterial } = panoramaMaterial(
    glass,
    !deferWaterMotion,
    deferWaterMotion,
  );
  warmWaterfront?.(material);
  const motionLoader = deferWaterMotion ? new T.TextureLoader(defaultStudioLoadingManager) : loader;
  let ferry: ReturnType<typeof riverFerry> | undefined;
  let waterReady: Promise<boolean> | undefined;
  function waterResources() {
    waterReady ??= new Promise<boolean>((resolve) => {
      const slopes = motionLoader.load(
        '/media/panoramas/river-slopes.webp',
        () => resolve(true),
        undefined,
        () => resolve(false),
      );
      slopes.wrapS = slopes.wrapT = T.RepeatWrapping;
      slopes.anisotropy = 8;
      uniforms.waterSlopes.value = slopes;
    });
    return waterReady;
  }
  function vesselResources() {
    if (ferry) return;
    uniforms.ferryReflection.value = loadFerryReflection();
    const warmup = motionRequest?.ferry ? () => motionRequest?.ferry : undefined;
    ferry = riverFerry(world, motionLoader.manager, warmup);
  }
  function loadFerryReflection() {
    const texture = motionLoader.load('/media/panoramas/river-ferry-reflection.png');
    texture.colorSpace = T.SRGBColorSpace;
    return texture;
  }
  const plate = mesh(world, panoramaGeometry(), material);
  plate.name = panoramaMeshName;
  plate.castShadow = plate.receiveShadow = false;
  const query = typeof location === 'undefined' ? undefined : new URLSearchParams(location.search);
  if (
    query?.get('studio-window-clip') === 'scissor' &&
    query.get('studio-low') === 'native' &&
    !query.has('review')
  ) {
    const project = roomExteriorScissor();
    const identity = new T.Matrix4();
    const size = new T.Vector2();
    const viewport = new T.Vector4();
    const clip = new T.Vector4();
    const previous = new T.Vector4();
    let clipped: T.WebGLRenderer | undefined;
    const restore = (renderer: T.WebGLRenderer) => {
      if (renderer !== clipped) return;
      renderer.setScissor(previous);
      renderer.setScissorTest(false);
      clipped = undefined;
    };
    plate.onBeforeRender = (renderer, scene, camera) => {
      restore(renderer);
      if (
        scene.overrideMaterial ||
        renderer.getRenderTarget() ||
        renderer.getPixelRatio() !== 1 ||
        renderer.getScissorTest() ||
        renderer.shadowMap.enabled ||
        renderer.xr.isPresenting ||
        !root.matrixWorld.equals(identity)
      )
        return;
      renderer.getSize(size);
      renderer.getViewport(viewport);
      if (viewport.x !== 0 || viewport.y !== 0 || viewport.z !== size.x || viewport.w !== size.y)
        return;
      if (!project(camera, size.x, size.y, clip) || (clip.z === size.x && clip.w === size.y))
        return;
      renderer.getScissor(previous);
      clipped = renderer;
      renderer.setScissor(clip);
      renderer.setScissorTest(true);
    };
    plate.onAfterRender = restore;
  }
  const grade = new T.Color();
  let shown = view(initial),
    target = shown,
    blend = 1,
    time = 0;
  type MotionRequest = {
    warm: (material: T.ShaderMaterial) => Promise<boolean>;
    signal: AbortSignal;
    ferry?: FerryWarmup;
  };
  let movingMaterial = deferWaterMotion ? undefined : material;
  let motionRequest: MotionRequest | undefined;
  let attemptedMotion: MotionRequest | undefined;
  function prepareWaterMotion(
    warm: MotionRequest['warm'],
    signal: AbortSignal,
    warmFerry?: FerryWarmup['warm'],
  ) {
    if ((!movingMaterial || warmFerry) && !signal.aborted)
      motionRequest = { warm, signal, ferry: warmFerry ? { warm: warmFerry, signal } : undefined };
  }
  function startWaterMotion() {
    const request = motionRequest;
    if (!request || request.signal.aborted || attemptedMotion === request) return;
    attemptedMotion = request;
    const moving = createMaterial(true);
    performance.mark('studio-water-motion-start');
    void waterResources()
      .then((loaded) => (loaded && !request.signal.aborted ? request.warm(moving) : false))
      .catch(() => false)
      .then((ready) => {
        if (!ready || motionRequest !== request || request.signal.aborted) {
          moving.dispose();
          return;
        }
        movingMaterial = moving;
        if (!keepStaticMaterial) {
          plate.material = moving;
          material.dispose();
        }
        performance.mark('studio-water-motion-ready');
      });
  }
  if (movingMaterial && shown.scene.kind === 'river') {
    void waterResources();
    if (shown.scene.route) vesselResources();
  }
  uniforms.physicalWater.value = true;
  return {
    world,
    prepareWaterMotion: deferWaterMotion ? prepareWaterMotion : undefined,
    update(env: Environment, delta: number, closeWindow = false) {
      const windowOnly = keepStaticMaterial && env.quality === 'low';
      const visibleMotion =
        windowOnly && (!closeWindow || env.reducedMotion) ? undefined : movingMaterial;
      if (keepStaticMaterial) plate.material = visibleMotion ?? material;
      if (!env.reducedMotion && visibleMotion) time += delta;
      const desired = view(env);
      if (desired.photo.image && desired.depth.image && desired !== target) {
        if (desired === shown) {
          shown = target;
          blend = 1 - blend;
        } else {
          if (blend >= 0.5) shown = target;
          blend = 0;
        }
        target = desired;
      }
      blend = Math.min(1, blend + (env.reducedMotion ? 1 : delta * 2.7));
      if (blend === 1) shown = target;
      plate.visible = Boolean(shown.photo.image && shown.depth.image);
      uniforms.photoA.value = shown.photo;
      uniforms.photoB.value = target.photo;
      uniforms.depthA.value = shown.depth;
      uniforms.depthB.value = target.depth;
      uniforms.rangeA.value.copy(shown.range);
      uniforms.rangeB.value.copy(target.range);
      uniforms.calibrationA.value.copy(shown.calibration);
      uniforms.calibrationB.value.copy(target.calibration);
      uniforms.waterlines.value.set(shown.bank, target.bank);
      uniforms.clearSkyFrom.value.set(
        shown.scene.kind === 'river' ? shown.scene.clearSkyFrom : 1,
        target.scene.kind === 'river' ? target.scene.clearSkyFrom : 1,
      );
      uniforms.blend.value = shown === target ? 0 : T.MathUtils.smoothstep(blend, 0, 1);
      uniforms.shoreA.value = shown.shoreline;
      uniforms.shoreB.value = target.shoreline;
      uniforms.flowA.value.copy(shown.current);
      uniforms.flowB.value.copy(target.current);
      uniforms.riverTime.value = time;
      const ease = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 3);
      uniforms.nightWater.value = T.MathUtils.lerp(
        uniforms.nightWater.value,
        Number(env.night),
        ease,
      );
      uniforms.windStrength.value = T.MathUtils.lerp(
        uniforms.windStrength.value,
        env.weather === '雨' ? 1 : 0.48,
        ease,
      );
      if (movingMaterial && desired.scene.kind === 'river') {
        void waterResources();
        if (desired.scene.route) vesselResources();
      } else if (!movingMaterial && !env.reducedMotion && target.scene.kind === 'river') {
        startWaterMotion();
      }
      const route = shown.scene.kind === 'river' ? shown.scene.route : undefined;
      const nextRoute = target.scene.kind === 'river' ? target.scene.route : undefined;
      if (ferry)
        uniforms.ferryTrack.value.copy(
          ferry(
            visibleMotion ? route : undefined,
            time,
            uniforms.nightWater.value,
            env.weather,
            Number(route === nextRoute),
          ),
        );
      uniforms.mist.value = T.MathUtils.lerp(
        uniforms.mist.value,
        env.weather === '晴' ? 0 : 0.39,
        ease,
      );
      grade.set(
        env.weather === '雨'
          ? '#d5dfeb'
          : env.weather === '雪'
            ? '#e5edf3'
            : env.weather === '阴'
              ? '#e1e5e9'
              : '#ffffff',
      );
      if (env.season === '冬') grade.multiplyScalar(0.98);
      uniforms.grade.value.lerp(grade, ease);
    },
  };
}
