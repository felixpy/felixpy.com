import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import * as T from 'three';
import type { Environment } from '../app/environment';
import { ceilingLightLevel, type HomeLightId } from '../app/home-lights';
import PhoneHome from '../app/ui/PhoneHome';
import { local } from '../app/locale';
import {
  arcball,
  benchEye,
  eye,
  frameGearWall,
  gearEye,
  roomFov,
  viewFov,
  windowEye,
} from './camera';
import { display } from './hardware';
import { workshopLayout } from './layout';
import { phoneDisplay } from './development-phone';
import { Finish, type FirstPicture } from './Finish';
import { roomFirstFrame } from './room-first-frame';
import { Minimap } from './Minimap';
import { studioReflections } from './reflections';
import { roomVisibility } from './room-visibility';
import { roomDetail } from './room-detail';
import { roomPicking } from './room-picking';
import { exportFinishGeometry, surfaceFinish, surfaceKey } from './surface-finish';
import { screenProjection } from './screen-projection';
import {
  buildStudio,
  opensStudioView,
  type AppID,
  type HardwareOrbit,
  type InspectionLink,
  type Target,
} from './studio';
import { panoramaMeshName, waterfrontFarClip } from './window-depth';
import { editableBlindSlats } from './window';

type Station = 'room' | 'bench';
type WallView = 'board' | 'map' | 'gear' | 'bookshelf';
export type Mode =
  | Station
  | WallView
  | 'inspect'
  | 'case'
  | 'window'
  | 'remote'
  | 'computer'
  | 'drawer'
  | 'returning';
const isStation = (mode: Mode): mode is Station => mode === 'room' || mode === 'bench';
const canLookAround = (mode: Mode): mode is Station | 'gear' => isStation(mode) || mode === 'gear';
const atWindow = (mode: Mode) => mode === 'window' || mode === 'remote';
const isWallView = (mode: string): mode is WallView =>
  mode === 'board' || mode === 'map' || mode === 'gear' || mode === 'bookshelf';
const canPick = (mode: Mode) => mode !== 'returning';
const drawerEyeOffset = new T.Vector3(0, 0.54, 0.27);
const drawerPitch = -Math.atan2(drawerEyeOffset.y, drawerEyeOffset.z);
const drawerFov = 46;

type Props = {
  initialLowScale: number;
  roomVisible: boolean;
  environment: Environment;
  mode: Mode;
  onMode: (mode: Mode, app?: AppID, link?: InspectionLink) => void;
  onPress: (target: Target) => string | void;
  onToggleHomeLight: (id: HomeLightId) => void;
  onHint: (text: string) => void;
  onHover: (text: string, point?: { x: number; y: number }) => void;
  onReady: () => void;
  onProgress: (ratio: number) => void;
  musicLevels: () => { bass: number; mid: number; beat: number };
  musicPlaying: boolean;
  screen: RefObject<HTMLDivElement | null>;
  inspectionAnchor: RefObject<HTMLAnchorElement | null>;
  objectCaption: RefObject<HTMLDivElement | null>;
  controls: RefObject<{ open: () => void } | null>;
};

type Pose = { position: T.Vector3; quaternion: T.Quaternion };
type Inspection = {
  target: Target;
  home: Pose;
  putDownFrom?: Pose;
  rotation: T.Quaternion;
  initial: T.Quaternion;
  distance: number;
  bounds: T.Box3;
  boundsRevision: number;
};
type FramedObject = { object: T.Object3D; bounds: T.Box3 };
type WallFocus = FramedObject & { type: WallView; center: T.Vector3; fov: number; panY: number };

function frameWallSurface(wall: WallFocus, aspect: number, position: T.Vector3) {
  const { min, max } = wall.bounds;
  const height = max.y - min.y;
  const halfFrame = Math.max(height, (max.x - min.x) / aspect) / 1.79;
  const distance = halfFrame / Math.tan(T.MathUtils.degToRad(viewFov / 2));
  const rise = wall.type === 'board' ? distance * 0.06 : 0;
  let centerY = wall.center.y - height * 0.027;
  if (wall.type === 'bookshelf') {
    const visibleHalfHeight = distance * Math.tan(T.MathUtils.degToRad(wall.fov / 2));
    const limit = Math.max(0, ((1 - visibleHalfHeight / halfFrame) * height) / 2);
    wall.panY = T.MathUtils.clamp(wall.panY, -limit, limit);
    centerY = wall.center.y + wall.panY;
  }
  position.set(wall.center.x, centerY + rise, wall.center.z + distance);
  return -Math.atan2(rise, distance);
}

const savedPose = (obj: T.Object3D): Pose => ({
  position: obj.position.clone(),
  quaternion: obj.quaternion.clone(),
});

const towerOrbit: HardwareOrbit = {
  center: [0, 0.005, -0.024],
  azimuth: [1.05, -Math.PI / 2, 1.52],
  elevation: [0.24, 0.045, 0.52],
  distance: [1.03, 0.34, 1.55],
};
function initialOrbit(orbit: HardwareOrbit) {
  return {
    orbit,
    azimuth: orbit.azimuth[0],
    elevation: orbit.elevation[0],
    distance: orbit.distance[0],
  };
}
function towerRadius(radius: number, azimuth: number, centerX: number, rearOffset = 0) {
  const side = -Math.sin(azimuth);
  const front = Math.cos(azimuth);
  const clearSide = 0.17 / Math.max(Math.abs(side), 0.001);
  const clearFront = (0.39 + rearOffset) / Math.max(front, 0.001);
  const clearWorkbench = (workshopLayout.x - 0.38 - centerX) / Math.max(side, 0.001);
  return T.MathUtils.clamp(radius, Math.min(clearSide, clearFront), clearWorkbench);
}
function frameHardware(
  view: ReturnType<typeof initialOrbit> & { hardwareId: string; center: T.Vector3 },
  position: T.Vector3,
  rotation: T.Euler,
) {
  const { azimuth, elevation, center, orbit, distance: requested } = view;
  const rear = orbit.rearClearance ? T.MathUtils.smoothstep(-Math.cos(azimuth), 0, 1) : 0;
  const distance = T.MathUtils.lerp(
    requested,
    Math.min(requested, orbit.rearClearance ?? requested),
    rear,
  );
  let radius = distance * Math.cos(elevation);
  let lift = 0;
  let rearOffset = 0;
  if (view.hardwareId === 'case') {
    const near = 1 - T.MathUtils.smoothstep(requested, 0.34, 0.6);
    lift = 0.116 * near;
    const sideView = T.MathUtils.smoothstep(-Math.sin(azimuth), 0.85, 1);
    rearOffset = T.MathUtils.lerp(0.108, 0.079, sideView) * near;
    radius = towerRadius(radius, azimuth, center.x, rearOffset);
  }
  position.set(
    center.x - radius * Math.sin(azimuth),
    center.y + radius * Math.tan(elevation) + lift,
    center.z + radius * Math.cos(azimuth) - rearOffset,
  );
  rotation.set(-elevation - rear * 0.22, -azimuth, 0, 'YXZ');
  const fov = viewFov + rear * 17;
  if (!orbit.closeFov) return fov;
  const zoom = 1 - T.MathUtils.smoothstep(requested, orbit.distance[1], orbit.distance[0]);
  return T.MathUtils.lerp(fov, Math.min(fov, orbit.closeFov), zoom);
}
const lookKeys = new Set(['ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight']);

function localBounds(object: T.Object3D) {
  object.updateWorldMatrix(true, true);
  const toLocal = object.matrixWorld.clone().invert();
  const matrix = new T.Matrix4(),
    part = new T.Box3(),
    bounds = new T.Box3();
  object.traverseVisible((child) => {
    if (!(child instanceof T.Mesh)) return;
    if (!child.geometry.boundingBox) child.geometry.computeBoundingBox();
    if (child.geometry.boundingBox) {
      matrix.multiplyMatrices(toLocal, child.matrixWorld);
      bounds.union(part.copy(child.geometry.boundingBox).applyMatrix4(matrix));
    }
  });
  return bounds;
}

function CameraRig(
  props: Props & {
    mapMarker: RefObject<SVGGElement | null>;
    firstPicture: RefObject<FirstPicture>;
    firstFrame: ReturnType<typeof roomFirstFrame>;
    detailRevision: RefObject<number>;
    phonePanel: RefObject<HTMLDivElement | null>;
    setPhoneHeld: (held: boolean) => void;
  },
) {
  const { camera: baseCamera, gl, scene } = useThree();
  const camera = baseCamera as T.PerspectiveCamera;
  const [{ model, assets }] = useState(() => {
    props.firstFrame.warm(gl);
    const assets = { loaded: 0, total: 0 };
    const manager = new T.LoadingManager();
    manager.onProgress = (_, loaded, total) => Object.assign(assets, { loaded, total });
    const model = buildStudio(manager, props.environment);
    props.firstFrame.windowSlats.value = model.slats;
    return { model, assets };
  });
  const live = useRef(props);
  live.current = props;
  const loading = useRef({ reported: -1, complete: false });
  const [shaded, setShaded] = useState(false);
  const roomMaterials = useRef<ReturnType<typeof roomVisibility> | null>(null);
  const finishNormals = useRef<((subtree?: T.Object3D) => void) | null>(null);
  const roomMeshes = useRef<ReturnType<typeof roomDetail> | null>(null);
  const reflections = useRef<ReturnType<typeof studioReflections> | null>(null);
  const looks = useRef({
    room: { yaw: eye.yaw, pitch: eye.pitch },
    bench: { yaw: benchEye.yaw, pitch: benchEye.pitch },
    gear: { yaw: 0, pitch: 0 },
  });
  function turnView(area: Station | 'gear', yaw: number, pitch: number) {
    const look = looks.current[area];
    look.yaw += yaw;
    look.pitch += pitch;
    if (area === 'gear') {
      look.yaw = T.MathUtils.clamp(look.yaw, -0.38, 0.38);
      look.pitch = T.MathUtils.clamp(look.pitch, -0.48, 0.84);
    } else look.pitch = T.MathUtils.clamp(look.pitch, -1.19, 1.13);
  }
  const zoom = useRef({ room: roomFov, bench: viewFov });
  const station = useRef<Station>('room');
  const turning = useRef(new Set<string>());
  const windowView = useRef({ yaw: windowEye.yaw, pitch: windowEye.pitch, fov: roomFov });
  const windowFocus = useRef(false);
  const windowTravel = useRef<{
    position: T.Vector3;
    yaw: number;
    pitch: number;
    start: number;
    duration: number;
  } | null>(null);
  const caseView = useRef({
    ...initialOrbit(towerOrbit),
    hardwareId: 'case',
    center: new T.Vector3(),
  });
  const returningFromTower = useRef(false);
  const wallFocus = useRef<WallFocus | null>(null);
  const drawerFocus = useRef<{ object: T.Object3D; center: T.Vector3 } | null>(null);
  const cabinetFocus = useRef(false);
  const mode = useRef<Mode>('room');
  const returnViews = useRef(new Map<Mode, Pose & { fov: number }>());
  const focused = useRef(false);
  const inspection = useRef<Inspection | null>(null);
  function enclosingMode(): Mode {
    if (cabinetFocus.current) return 'case';
    if (drawerFocus.current) return 'drawer';
    if (windowFocus.current) return 'window';
    return wallFocus.current?.type ?? station.current;
  }
  const pointer = useRef<{
    target: Target | undefined;
    x: number;
    y: number;
    moved: boolean;
    ball: T.Vector3;
    orientation: T.Quaternion;
  } | null>(null);
  const hover = useRef<Target | undefined>(undefined);
  const animationStart = useRef(0);
  const computerStart = useRef({
    position: new T.Vector3(),
    quaternion: new T.Quaternion(),
    fov: viewFov,
  });
  const shadowWarmup = useRef(3);
  const scratch = useRef({
    position: new T.Vector3(),
    orientation: new T.Quaternion(),
    local: new T.Vector3(),
    rotation: new T.Quaternion(),
    parent: new T.Quaternion(),
    euler: new T.Euler(0, 0, 0, 'YXZ'),
    screenCorners: Array.from({ length: 4 }, () => new T.Vector3()),
  });

  function placeHeldItem(moving: Inspection, ease: number, isRemote: boolean) {
    const { object } = moving.target;
    const parent = object.parent!;
    const cached = scratch.current;
    const item = moving.target.type === 'inspect' ? moving.target : undefined;
    const width = item?.size ?? 0.13;
    const distance = isRemote
      ? 0.34
      : (item?.viewDistance ?? Math.max(0.26, width * 2.75)) * moving.distance;
    cached.local.set(
      isRemote ? distance * camera.aspect * 0.29 : 0,
      isRemote ? -0.074 : width * 0.075,
      -distance,
    );
    camera.localToWorld(cached.local);
    parent.worldToLocal(cached.local);
    parent.getWorldQuaternion(cached.parent).invert();
    cached.rotation.copy(cached.parent).multiply(camera.quaternion).multiply(moving.rotation);
    if (
      object.position.distanceToSquared(cached.local) > 1e-8 ||
      object.quaternion.angleTo(cached.rotation) > 0.001
    )
      shadowWarmup.current = 1;
    object.position.lerp(cached.local, ease);
    object.quaternion.slerp(cached.rotation, ease);
  }

  useEffect(() => {
    const element = gl.domElement;
    const renderer = gl as T.WebGLRenderer;
    const reflectionMap = studioReflections(renderer, scene);
    const visibility = roomVisibility(model.pickRoots, live.current.environment, model.slats);
    const surfaceAbort = new AbortController();
    roomMeshes.current = roomDetail(model.interior, surfaceAbort.signal);
    if (
      !(import.meta.env.DEV && new URLSearchParams(location.search).get('review') === 'authoring')
    ) {
      void surfaceFinish(model.interior, surfaceAbort.signal)
        .then((apply) => {
          if (!surfaceAbort.signal.aborted) {
            finishNormals.current = apply;
            apply();
          }
        })
        .catch(() => {});
    }
    roomMaterials.current = visibility;
    reflections.current = reflectionMap;
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = true;
    renderer.shadowMap.type = T.PCFShadowMap;

    camera.position.set(eye.x, eye.y, eye.defaultZ);
    camera.rotation.set(looks.current.room.pitch, looks.current.room.yaw, 0, 'YXZ');
    camera.updateMatrixWorld(true);
    const ray = new T.Raycaster();
    const position = new T.Vector2();
    let pointerAim: { x: number; y: number } | undefined;
    const picking = roomPicking(model.pickRoots, (work) => {
      const run = () => {
        if (!surfaceAbort.signal.aborted) work();
      };
      if (typeof window.requestIdleCallback === 'function')
        window.requestIdleCallback(run, { timeout: 1500 });
      else window.setTimeout(run, 0);
    });
    void model.rearReady.then(() => {
      if (surfaceAbort.signal.aborted) return;
      visibility.prepareMaterials();
      finishNormals.current?.();
      roomMeshes.current?.refresh();
      props.detailRevision.current++;
      shadowWarmup.current = 2;
    });
    function pick(x: number, y: number) {
      const rect = element.getBoundingClientRect();
      position.set(((x - rect.left) / rect.width) * 2 - 1, ((rect.top - y) / rect.height) * 2 + 1);
      ray.setFromCamera(position, camera);
      ray.far = Infinity;
      const held = inspection.current?.target.object;
      let current: T.Object3D | null = picking.closest(ray, held) ?? null;
      while (current) {
        if (current === held) return undefined;
        const target = model.byObject.get(current);
        if (target && model.canReach(target, mode.current, caseView.current.hardwareId))
          return target;
        current = current.parent;
      }
    }

    let openSequence = 0;
    let inspectedTarget: Extract<Target, { type: 'inspect' }> | undefined;
    function setMode(next: Mode, app?: AppID, link?: InspectionLink) {
      openSequence++;
      const from = mode.current;
      const panel = live.current.screen.current;
      returningFromTower.current =
        next === 'returning' && from === 'case' && caseView.current.hardwareId === 'case';
      if (from === 'computer' && next !== 'computer' && panel) {
        panel.dataset.visible = 'false';
        panel.dataset.interactive = 'false';
        if (document.activeElement instanceof HTMLElement && panel.contains(document.activeElement))
          document.activeElement.blur();
      }
      if (
        next !== 'returning' &&
        !isStation(next) &&
        ((isStation(from) && from === station.current) ||
          ((next === 'inspect' || next === 'remote') &&
            (isWallView(from) || from === 'case' || from === 'drawer' || from === 'window')))
      ) {
        returnViews.current.set(from, { ...savedPose(camera), fov: camera.fov });
      }
      turning.current.clear();
      hover.current = undefined;
      mode.current = next;
      const held = inspection.current?.target;
      const selected = next === 'inspect' && held?.type === 'inspect' ? held : undefined;
      if (selected !== inspectedTarget) {
        inspectedTarget?.onInspect?.(false, live.current.environment.reducedMotion);
        selected?.onInspect?.(true, live.current.environment.reducedMotion);
        inspectedTarget = selected;
      }
      live.current.setPhoneHeld(
        next === 'inspect' && inspection.current?.target.id === 'development-phone',
      );
      animationStart.current = performance.now();
      live.current.onMode(next, app, link);
    }
    function walkTo(x: number, y: number, z: number) {
      const position = camera.position.clone();
      const distance = Math.hypot(x - position.x, y - position.y, z - position.z);
      windowTravel.current = {
        position,
        yaw: camera.rotation.y,
        pitch: camera.rotation.x,
        start: performance.now(),
        duration: Math.max(480, distance * 950),
      };
    }
    function restoreHeldItem() {
      const moving = inspection.current;
      if (!moving) return;
      moving.target.object.position.copy(moving.home.position);
      moving.target.object.quaternion.copy(moving.home.quaternion);
      moving.target.object.updateMatrixWorld(true);
      inspection.current = null;
      shadowWarmup.current = 2;
    }
    function applyReducedInspection() {
      if (live.current.environment.reducedMotion && inspection.current?.target.type === 'inspect') {
        placeHeldItem(inspection.current, 1, false);
        inspection.current.target.object.updateMatrixWorld(true);
      }
    }
    function returnToView() {
      if (!live.current.environment.reducedMotion) {
        const held = inspection.current;
        if (held) held.putDownFrom = savedPose(held.target.object);
        setMode('returning');
        return;
      }
      restoreHeldItem();
      const destination = enclosingMode();
      const view = returnViews.current.get(destination);
      if (view) {
        camera.position.copy(view.position);
        camera.quaternion.copy(view.quaternion);
        camera.fov = view.fov;
        returnViews.current.delete(destination);
      } else if (destination === 'room') {
        camera.position.set(eye.x, eye.y, eye.defaultZ);
        camera.rotation.set(looks.current.room.pitch, looks.current.room.yaw, 0, 'YXZ');
        camera.fov = zoom.current.room;
      }
      camera.updateProjectionMatrix();
      camera.updateMatrixWorld(true);
      shadowWarmup.current = 2;
      setMode(destination);
    }
    function leaveFocusedView(target: Target) {
      restoreHeldItem();
      if (drawerFocus.current) model.setDrawer(-1, live.current.environment.reducedMotion);
      drawerFocus.current = null;
      cabinetFocus.current = false;
      wallFocus.current = null;
      windowFocus.current = false;
      windowTravel.current = null;
      station.current = 'room';
      returnViews.current.clear();
      const aim =
        target.type === 'case'
          ? new T.Vector3(...(target.orbit ?? towerOrbit).center)
          : localBounds(target.object).getCenter(new T.Vector3());
      target.object.localToWorld(aim);
      const x = aim.x - eye.x;
      const z = aim.z - eye.defaultZ;
      looks.current.room = {
        yaw: Math.atan2(-x, -z),
        pitch: Math.atan2(aim.y - eye.y, Math.hypot(x, z)),
      };
    }
    function moveToStation(next: Station) {
      station.current = next;
      if (next === 'bench') {
        void model.prepareRear();
        looks.current.bench = { yaw: benchEye.yaw, pitch: benchEye.pitch };
        void model
          .prepareWorkshop()
          .then(() => {
            if (!surfaceAbort.signal.aborted) {
              finishNormals.current?.();
              roomMeshes.current?.refresh();
              visibility.prepareMaterials();
              props.detailRevision.current++;
            }
          })
          .catch(() => {});
      }
      hover.current = undefined;
      pointer.current = null;
      live.current.onHint('');
      setMode(next);
    }
    function open(target: Target | undefined, prepared = false) {
      const sequence = ++openSequence;
      if (!target) return;
      if (
        !canPick(mode.current) ||
        !model.canReach(target, mode.current, caseView.current.hardwareId)
      )
        return;
      if (mode.current === 'remote' && target.type === 'key') {
        model.pushButton(target.index);
        const status = live.current.onPress(target);
        if (status) live.current.onHint(status);
        return;
      }
      if (mode.current === 'map' && target.type === 'map-pin') {
        live.current.onHint(local(live.current.environment.locale, target.english, target.label));
        return;
      }
      if (
        target.type === 'drawer' &&
        mode.current === 'drawer' &&
        target.object === drawerFocus.current?.object
      ) {
        closeDrawer();
        return;
      }
      const preparing = !prepared && target.prepare?.();
      if (preparing) {
        const proceed = () => {
          if (sequence === openSequence && !surfaceAbort.signal.aborted) open(target, true);
        };
        void preparing.then(proceed, proceed);
        return;
      }
      if (opensStudioView(target) && mode.current !== 'room') leaveFocusedView(target);
      if (target.type === 'window' || target.type === 'remote') {
        if (!atWindow(mode.current)) {
          windowView.current = { yaw: windowEye.yaw, pitch: windowEye.pitch, fov: camera.fov };
          walkTo(windowEye.x, windowEye.y, windowEye.z);
        }
        if (target.type === 'window') {
          windowFocus.current = true;
          setMode('window');
          live.current.onHint('');
          return;
        }
      }
      if (target.type === 'drawer') {
        drawerFocus.current = {
          object: target.object,
          center: model.drawerCenter(target.index),
        };
        const immediate = live.current.environment.reducedMotion;
        model.setDrawer(target.index, immediate);
        setMode('drawer');
        if (immediate) {
          camera.position.copy(drawerFocus.current.center).add(drawerEyeOffset);
          camera.rotation.set(drawerPitch, 0, 0, 'YXZ');
          camera.fov = drawerFov;
          camera.updateProjectionMatrix();
          camera.updateMatrixWorld(true);
        }
        shadowWarmup.current = 2;
        live.current.onHint('');
        return;
      }
      hover.current = undefined;
      if (target.type === 'cabinet') {
        model.slideCabinet(target.index);
        live.current.onHint('');
        return;
      }
      if (target.type === 'door') {
        model.toggleDoor();
        live.current.onHint('');
        return;
      }
      if (target.type === 'workbench') {
        moveToStation('bench');
        return;
      }
      if (target.type === 'computer') {
        focused.current = false;
        computerStart.current.position.copy(camera.position);
        computerStart.current.quaternion.copy(camera.quaternion);
        computerStart.current.fov = camera.fov;
        setMode('computer', target.app);
        live.current.onHint('');
        return;
      }
      if (
        target.type === 'gear' ||
        target.id === 'collection-cabinet' ||
        target.id === 'filament-printer'
      )
        void model.prepareRear();
      if (isWallView(target.type)) {
        const bounds = localBounds(target.object);
        const center = target.object.localToWorld(bounds.getCenter(new T.Vector3()));
        if (target.type === 'gear') looks.current.gear = { yaw: 0, pitch: 0 };
        wallFocus.current = {
          type: target.type,
          object: target.object,
          bounds,
          center,
          fov: target.type === 'gear' ? gearEye.fov : viewFov,
          panY: 0,
        };
        setMode(target.type);
        if (live.current.environment.reducedMotion) {
          if (target.type === 'gear') {
            frameGearWall(target.object, camera.aspect, camera.position);
            camera.rotation.set(gearEye.pitch, gearEye.yaw, 0, 'YXZ');
          } else {
            const pitch = frameWallSurface(wallFocus.current, camera.aspect, camera.position);
            camera.rotation.set(pitch, 0, 0, 'YXZ');
          }
          camera.fov = wallFocus.current.fov;
          camera.updateProjectionMatrix();
          camera.updateMatrixWorld(true);
        }
        live.current.onHint(
          target.type === 'bookshelf'
            ? local(live.current.environment.locale, target.english, target.label)
            : '',
        );
        return;
      }
      if (target.type === 'case') {
        cabinetFocus.current = target.id === 'collection-cabinet';
        const orbit = target.orbit ?? towerOrbit;
        caseView.current = {
          ...initialOrbit(orbit),
          hardwareId: target.id,
          center: target.object.localToWorld(new T.Vector3(...orbit.center)),
        };
        setMode('case');
        if (live.current.environment.reducedMotion) {
          camera.fov = frameHardware(caseView.current, camera.position, camera.rotation);
          camera.updateProjectionMatrix();
          camera.updateMatrixWorld(true);
        }
        live.current.onHint(local(live.current.environment.locale, target.english, target.label));
        return;
      }
      if (target.type === 'inspect' || target.type === 'remote') {
        const object = target.object;
        const initial = new T.Quaternion().setFromEuler(
          new T.Euler(...(target.type === 'inspect' ? (target.pose ?? [0, 0, 0]) : [1.47, 0, 0])),
        );
        inspection.current = {
          target,
          home: savedPose(object),
          initial,
          rotation: initial.clone(),
          distance: 1,
          bounds: localBounds(object),
          boundsRevision: props.detailRevision.current,
        };
        shadowWarmup.current = 2;
        setMode(target.type, undefined, target.type === 'inspect' ? target.link : undefined);
        applyReducedInspection();
        const locale = live.current.environment.locale;
        const text =
          target.type === 'inspect'
            ? target.caption?.[locale]
            : local(
                locale,
                'Press the physical buttons to adjust the window',
                '按下实体键调节窗景',
              );
        live.current.onHint(text ?? local(locale, target.english, target.label));
      } else live.current.onPress(target);
    }

    function closeDrawer() {
      model.setDrawer(-1, live.current.environment.reducedMotion);
      drawerFocus.current = null;
      pointer.current = null;
      returnToView();
      live.current.onHint('');
    }

    const computer = model.targets.find((target) => target.id === 'computer');
    live.current.controls.current = {
      open: () => open(computer),
    };

    function move(event: PointerEvent) {
      pointerAim = { x: event.clientX, y: event.clientY };
      if (mode.current === 'map') {
        const pin = pick(event.clientX, event.clientY);
        if (pin !== hover.current) {
          hover.current = pin;
          if (pin)
            live.current.onHint(local(live.current.environment.locale, pin.english, pin.label));
          element.style.cursor = pin ? 'pointer' : '';
        }
        if (
          pointer.current &&
          Math.hypot(event.clientX - pointer.current.x, event.clientY - pointer.current.y) >= 5
        )
          pointer.current.moved = true;
        return;
      }
      if (!canPick(mode.current)) return;
      const drag = pointer.current;
      if (!drag) {
        if (canPick(mode.current)) {
          const target = pick(event.clientX, event.clientY);
          if (target || target !== hover.current) {
            hover.current = target;
            const locale = live.current.environment.locale;
            const text =
              target?.type === 'drawer' &&
              mode.current === 'drawer' &&
              target.object === drawerFocus.current?.object
                ? local(locale, 'Close drawer', '关闭抽屉')
                : target
                  ? local(locale, target.english, target.label)
                  : '';
            if (mode.current === 'remote') live.current.onHint(text);
            else live.current.onHover(text, { x: event.clientX, y: event.clientY });
          }
          element.style.cursor = target
            ? 'pointer'
            : canLookAround(mode.current) || mode.current === 'bookshelf'
              ? 'grab'
              : '';
        }
        return;
      }
      const dx = event.clientX - drag.x,
        dy = event.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < 5) return;
      if (!drag.moved && isStation(mode.current)) void model.prepareRear();
      drag.moved = true;
      if (canLookAround(mode.current)) {
        turnView(mode.current, -dx * 0.0035, -dy * 0.0028);
        drag.x = event.clientX;
        drag.y = event.clientY;
        element.style.cursor = 'grabbing';
        live.current.onHover('');
      } else if (mode.current === 'bookshelf' && wallFocus.current) {
        const wall = wallFocus.current;
        const distance = camera.position.z - wall.center.z;
        const visibleHeight = 2 * distance * Math.tan(T.MathUtils.degToRad(wall.fov / 2));
        wall.panY += (dy * visibleHeight) / element.clientHeight;
        drag.y = event.clientY;
        drag.x = event.clientX;
        element.style.cursor = 'grabbing';
      } else if (mode.current === 'inspect' && inspection.current) {
        const rect = element.getBoundingClientRect();
        const next = arcball(
          event.clientX,
          event.clientY,
          rect,
          Math.min(rect.width, rect.height) * 0.28,
        );
        inspection.current.rotation.setFromUnitVectors(drag.ball, next).multiply(drag.orientation);
        applyReducedInspection();
      } else if (mode.current === 'case') {
        const look = caseView.current;
        look.azimuth = T.MathUtils.clamp(
          look.azimuth + dx * 0.003,
          look.orbit.azimuth[1],
          look.orbit.azimuth[2],
        );
        look.elevation = T.MathUtils.clamp(
          look.elevation + dy * 0.002,
          look.orbit.elevation[1],
          look.orbit.elevation[2],
        );
        drag.x = event.clientX;
        drag.y = event.clientY;
        element.style.cursor = 'grabbing';
      } else if (atWindow(mode.current) && drag.target?.type !== 'key') {
        const look = windowView.current;
        const gain = 1.4 / Math.max(1, element.clientHeight);
        look.yaw = T.MathUtils.clamp(
          look.yaw - dx * gain,
          windowEye.yaw - 0.46,
          windowEye.yaw + 0.46,
        );
        look.pitch = T.MathUtils.clamp(
          look.pitch - dy * gain,
          windowEye.pitch - 0.29,
          windowEye.pitch + 0.28,
        );
        drag.x = event.clientX;
        drag.y = event.clientY;
        element.style.cursor = 'grabbing';
      }
    }
    function down(event: PointerEvent) {
      if (event.button !== 0 || !canPick(mode.current)) return;
      openSequence++;
      const rect = element.getBoundingClientRect();
      pointer.current = {
        target: canPick(mode.current) ? pick(event.clientX, event.clientY) : undefined,
        x: event.clientX,
        y: event.clientY,
        moved: false,
        ball: arcball(event.clientX, event.clientY, rect, Math.min(rect.width, rect.height) * 0.28),
        orientation: inspection.current?.rotation.clone() ?? new T.Quaternion(),
      };
      element.setPointerCapture(event.pointerId);
    }
    function up(event: PointerEvent) {
      const drag = pointer.current;
      pointer.current = null;
      if (element.hasPointerCapture(event.pointerId))
        element.releasePointerCapture(event.pointerId);
      if (!drag?.moved && drag?.target && drag.target === pick(event.clientX, event.clientY))
        open(drag.target);
      element.style.cursor = ['room', 'bench', 'gear', 'bookshelf', 'inspect', 'case'].includes(
        mode.current,
      )
        ? 'grab'
        : '';
    }
    function cancel() {
      pointer.current = null;
      element.style.cursor = '';
    }
    function leave() {
      pointerAim = undefined;
      if (!pointer.current) {
        hover.current = undefined;
        if (canPick(mode.current)) live.current.onHover('');
      }
    }
    function reset() {
      if (mode.current === 'inspect' && inspection.current) {
        inspection.current.rotation.copy(inspection.current.initial);
        applyReducedInspection();
      }
      if (mode.current === 'case')
        Object.assign(caseView.current, initialOrbit(caseView.current.orbit));
    }
    function wheel(event: WheelEvent) {
      event.preventDefault();
      const delta = event.deltaY * (event.deltaMode === 1 ? 18 : event.deltaMode === 2 ? 300 : 1);
      if (mode.current === 'inspect' && inspection.current) {
        inspection.current.distance = T.MathUtils.clamp(
          inspection.current.distance + delta * 0.001,
          0.82,
          1.5,
        );
        applyReducedInspection();
      }
      if (mode.current === 'case') {
        const look = caseView.current;
        look.distance = T.MathUtils.clamp(
          look.distance + delta * 0.0009,
          look.orbit.distance[1],
          look.orbit.distance[2],
        );
      }
      const current = mode.current;
      if (isStation(current))
        zoom.current[current] = T.MathUtils.clamp(zoom.current[current] + delta * 0.03, 32, 64);
      const wall = wallFocus.current;
      if (wall && isWallView(current)) {
        wall.fov = T.MathUtils.clamp(
          wall.fov + delta * 0.03,
          wall.type === 'bookshelf' ? 13 : 28,
          64,
        );
      }
    }
    function keyboard(event: KeyboardEvent) {
      if (event.key === 'Escape' || lookKeys.has(event.code)) openSequence++;
      if (
        !event.defaultPrevented &&
        canLookAround(mode.current) &&
        lookKeys.has(event.code) &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        !(
          event.target instanceof HTMLElement &&
          event.target.closest('input, textarea, select, [contenteditable=true]')
        )
      ) {
        event.preventDefault();
        if (!event.repeat && (event.code === 'ArrowLeft' || event.code === 'ArrowRight'))
          void model.prepareRear();
        turning.current.add(event.code);
        hover.current = undefined;
        live.current.onHover('');
        return;
      }
      if (event.defaultPrevented || event.repeat) return;
      if (event.key === 'Escape' && mode.current === 'bench') {
        event.preventDefault();
        moveToStation('room');
        return;
      }
      if (event.key === 'Escape' && mode.current === 'drawer') {
        event.preventDefault();
        closeDrawer();
        return;
      }
      if (event.key === 'Escape' && !isStation(mode.current) && mode.current !== 'returning') {
        event.preventDefault();
        if (isWallView(mode.current)) wallFocus.current = null;
        if (mode.current === 'case') cabinetFocus.current = false;
        if (mode.current === 'window') windowFocus.current = false;
        if (atWindow(mode.current) && !windowFocus.current) {
          windowTravel.current = null;
          if (!live.current.environment.reducedMotion) {
            if (station.current === 'bench') walkTo(benchEye.x, benchEye.y, benchEye.z);
            else walkTo(eye.x, eye.y, eye.defaultZ);
          }
        }
        pointer.current = null;
        returnToView();
        live.current.onHint('');
      }
      if (event.code === 'KeyE' && mode.current !== 'computer' && canPick(mode.current)) {
        const rect = element.getBoundingClientRect();
        const target = pick(
          pointerAim?.x ?? rect.x + rect.width / 2,
          pointerAim?.y ?? rect.y + rect.height / 2,
        );
        if (target) {
          event.preventDefault();
          open(target);
        }
      }
    }
    const releaseKey = (event: KeyboardEvent) => {
      turning.current.delete(event.code);
    };
    const releaseMovement = () => turning.current.clear();
    element.addEventListener('pointermove', move);
    element.addEventListener('pointerdown', down);
    element.addEventListener('pointerup', up);
    element.addEventListener('pointercancel', cancel);
    element.addEventListener('pointerleave', leave);
    element.addEventListener('dblclick', reset);
    element.addEventListener('wheel', wheel, { passive: false });
    window.addEventListener('keydown', keyboard);
    window.addEventListener('keyup', releaseKey);
    window.addEventListener('blur', releaseMovement);
    if (import.meta.env.DEV && new URLSearchParams(window.location.search).has('review')) {
      window.__studioReview = {
        inventory: () =>
          model.targets.map(({ id, type, object }) => ({
            id,
            type,
            name: object.name,
            uuid: object.uuid,
          })),
        async captureLighting(location?: 'desk' | 'aj' | 'camp') {
          await model.prepareRear();
          await visibility.ready;
          const { captureStudioLight } = await import('../../scripts/assets/capture-studio-light');
          return captureStudioLight(renderer, scene, location);
        },
        activate: (id) => open(model.targets.find((t) => t.id === id)),
        project: (id) => {
          const object =
            model.targets.find((t) => t.id === id)?.object ?? model.root.getObjectByName(id);
          const point = object?.getWorldPosition(new T.Vector3()).project(camera);
          const rect = element.getBoundingClientRect();
          return point
            ? {
                x: rect.left + ((point.x + 1) * rect.width) / 2,
                y: rect.top + ((1 - point.y) * rect.height) / 2,
              }
            : null;
        },
        camera: () => ({
          position: camera.position.toArray(),
          rotation: camera.quaternion.toArray(),
          fov: camera.fov,
        }),
        objectPose: (id) => {
          const object =
            model.targets.find((item) => item.id === id)?.object ?? model.root.getObjectByName(id);
          if (!object) return undefined;
          return { position: object.position.toArray(), rotation: object.quaternion.toArray() };
        },
        bounds: (name) => {
          const object = model.root.getObjectByName(name);
          if (!object) throw new Error('Unknown studio object: ' + name);
          const bounds = new T.Box3().setFromObject(object, true);
          return { min: bounds.min.toArray(), max: bounds.max.toArray() };
        },
        drawer: (index) => model.targets.find((t) => t.id === 'drawer-' + index)?.object.position.z,
        lightLevels: () => model.lightLevels(),
        async exportRoom(objectName, authoring = false) {
          if (authoring) await Promise.all([model.prepareRear(), model.prepareDrawerMedia()]);
          const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
          const source = objectName ? model.root.getObjectByName(objectName) : model.root;
          if (!source) throw new Error('Unknown studio object: ' + objectName);
          if (authoring) await model.prepareBookExport(source);
          let studio = source.clone();
          const panorama = source.getObjectByName(panoramaMeshName);
          const baked =
            authoring && panorama instanceof T.Mesh
              ? (await import('../../scripts/assets/bake-waterfront')).bakeWaterfront(
                  renderer,
                  panorama,
                )
              : undefined;
          if (authoring) {
            const geometries = new Map<T.BufferGeometry, T.BufferGeometry>();
            const portable = new Set(
              model.targets
                .filter(
                  (t) =>
                    t.type === 'inspect' ||
                    t.type === 'remote' ||
                    t.type === 'door' ||
                    t.type === 'drawer',
                )
                .map((t) => t.object),
            );
            const mark = (part: T.Object3D, copy: T.Object3D, cast: boolean) => {
              cast = cast && !portable.has(part) && part.visible;
              if (part instanceof T.Mesh) {
                const mats = Array.isArray(part.material) ? part.material : [part.material];
                copy.userData.studioOccluder =
                  cast && part.castShadow && mats.every((material) => !material.transparent);
                if (copy instanceof T.Mesh && part.geometry.getAttribute('normal')) {
                  copy.userData.studioSurface = surfaceKey(part.geometry);
                  if (!geometries.has(part.geometry))
                    geometries.set(part.geometry, exportFinishGeometry(part.geometry));
                  copy.geometry = geometries.get(part.geometry)!;
                }
              }
              part.children.forEach((child, i) => mark(child, copy.children[i], cast));
            };
            mark(source, studio, true);
            if (source === model.root) {
              const rack = model.gearWall;
              const view = new T.PerspectiveCamera(
                gearEye.fov,
                camera.aspect,
                camera.near,
                camera.far,
              );
              frameGearWall(rack, view.aspect, view.position);
              view.rotation.set(gearEye.pitch, gearEye.yaw, 0, 'YXZ');
              view.name = 'Equipment wall';
              studio.add(view);
            }
          }
          studio = editableBlindSlats(studio);
          if (objectName) studio.position.set(0, 0, 0);
          const tracks: T.KeyframeTrack[] = [];
          studio.traverse((child) => {
            if (
              (!authoring &&
                child instanceof T.InstancedMesh &&
                !child.userData.exportInstalledInstances) ||
              child instanceof T.Points ||
              child instanceof T.LineSegments
            )
              child.visible = false;
            if (authoring && child.name === 'Outside glazing surface' && child instanceof T.Mesh)
              child.material = new T.MeshBasicMaterial({
                transparent: true,
                opacity: 0,
                depthWrite: false,
              });
            if (
              child.name === panoramaMeshName &&
              child instanceof T.Mesh &&
              child.material instanceof T.ShaderMaterial
            ) {
              if (baked) {
                child.geometry = baked.geometry;
                child.material = baked.material;
                child.userData.waterfrontCamera = baked.calibration;
                child.userData.studioOccluder = false;
              } else {
                child.material = new T.MeshBasicMaterial({
                  map: child.material.uniforms.photoA.value,
                  side: T.DoubleSide,
                });
              }
            }
            if (child.name !== 'Fan rotor') return;
            child.name = 'Fan rotor ' + (tracks.length + 1);
            const times = Array.from({ length: 61 }, (_, i) => i / 20);
            const quaternions = times.flatMap((time) =>
              new T.Quaternion()
                .setFromAxisAngle(new T.Vector3(0, 0, 1), time * 14 + child.rotation.z)
                .toArray(),
            );
            tracks.push(
              new T.QuaternionKeyframeTrack(child.name + '.quaternion', times, quaternions),
            );
          });
          if (!objectName) {
            for (const child of [...studio.children])
              if (child instanceof T.Light || child instanceof T.Mesh) studio.remove(child);
          }
          const buffer = await new GLTFExporter()
            .parseAsync(studio, {
              binary: true,
              maxTextureSize: baked?.width ?? (authoring ? 2048 : 1024),
              onlyVisible: !authoring,
              animations: tracks.length ? [new T.AnimationClip('Fan rotors', 3, tracks)] : [],
            })
            .finally(() => {
              baked?.geometry.dispose();
              baked?.material.map?.dispose();
              baked?.material.dispose();
            });
          const url = URL.createObjectURL(
            new Blob([buffer as ArrayBuffer], { type: 'model/gltf-binary' }),
          );
          const link = document.createElement('a');
          link.href = url;
          link.download = objectName ? 'studio-object.glb' : 'felix-studio.glb';
          link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        },
      };
    }
    return () => {
      delete window.__studioReview;
      live.current.controls.current = null;
      element.removeEventListener('pointermove', move);
      element.removeEventListener('pointerdown', down);
      element.removeEventListener('pointerup', up);
      element.removeEventListener('pointercancel', cancel);
      element.removeEventListener('pointerleave', leave);
      element.removeEventListener('dblclick', reset);
      element.removeEventListener('wheel', wheel);
      window.removeEventListener('keydown', keyboard);
      window.removeEventListener('keyup', releaseKey);
      window.removeEventListener('blur', releaseMovement);
      reflectionMap.dispose();
      picking.dispose();
      surfaceAbort.abort();
      roomMeshes.current?.select(false);
      roomMeshes.current = null;
      finishNormals.current = null;
      visibility.dispose();
      reflections.current = null;
    };
  }, [camera, gl, model, scene]);

  useEffect(() => {
    if (!props.roomVisible || !shaded) return;
    if (typeof window.requestIdleCallback === 'function') {
      const idle = window.requestIdleCallback(() => void model.prepareRear(), { timeout: 240 });
      return () => window.cancelIdleCallback(idle);
    }
    const timer = window.setTimeout(() => void model.prepareRear(), 32);
    return () => window.clearTimeout(timer);
  }, [model, props.roomVisible, shaded]);

  useEffect(() => {
    if (props.roomVisible)
      reflections.current?.select(props.environment.night, props.environment.quality);
  }, [props.environment.night, props.environment.quality, props.roomVisible]);

  const { blinds, angle, reducedMotion } = props.environment;
  useLayoutEffect(() => {
    if (reducedMotion) model.setBlinds(blinds, angle);
    shadowWarmup.current = 1;
  }, [model, blinds, angle, reducedMotion]);

  useEffect(() => {
    shadowWarmup.current = 1;
  }, [props.environment.quality]);

  useFrame(({ clock, size }, elapsed) => {
    const delta = Math.min(elapsed, 0.05);
    const { environment: env, screen, onMode } = live.current;
    const load = loading.current;
    if (!load.complete && assets.total) {
      const ratio = assets.loaded / assets.total;
      if (ratio === 1 && props.roomVisible && props.firstPicture.current === 'interactive') {
        roomMaterials.current?.prepareMaterials();
        finishNormals.current?.();
        props.firstPicture.current = 'preparing';
      }
      if (ratio !== load.reported) {
        load.reported = ratio;
        live.current.onProgress(ratio);
      }
      if (ratio === 1 && props.firstPicture.current === 'drawn') {
        load.complete = true;
        setShaded(true);
        if (
          import.meta.env.DEV &&
          new URLSearchParams(location.search).get('review') === 'window'
        ) {
          window.__studioReview?.activate('window');
        }
      }
    }
    const current = mode.current;
    if (model.mountedDetails.length) {
      let visibleArrival = false;
      for (const subtree of model.mountedDetails) {
        roomMaterials.current?.prepareMaterials(subtree);
        finishNormals.current?.(subtree);
        let ancestor: T.Object3D | null = subtree;
        while (ancestor?.visible) ancestor = ancestor.parent;
        if (ancestor === null) visibleArrival = true;
      }
      model.mountedDetails.length = 0;
      if (visibleArrival) {
        props.detailRevision.current++;
        shadowWarmup.current = 2;
      }
    }
    roomMeshes.current?.select(
      load.complete &&
        env.quality === 'low' &&
        (isStation(current) || atWindow(current) || current === 'computer'),
    );
    const cached = scratch.current;
    const ease = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 10.5);
    const windowOcclusion = env.blinds ? (env.angle + 1) / 3 : 0;
    roomMaterials.current?.update(env, delta);
    gl.toneMappingExposure = T.MathUtils.lerp(
      gl.toneMappingExposure,
      env.night ? 1.02 : 1.09,
      ease,
    );
    const reflectionLevel = env.night
      ? (0.13 + 0.35 * ceilingLightLevel(env)) * (1 - windowOcclusion * 0.14)
      : (env.weather === '晴' ? 0.79 : 0.64) * (1 - windowOcclusion * 0.65);
    scene.environmentIntensity = T.MathUtils.lerp(
      scene.environmentIntensity,
      reflectionLevel,
      ease,
    );
    const fov = (viewFov * Math.PI) / 180;
    const aspect = size.width / size.height;
    const atBench = station.current === 'bench';
    const look = looks.current[station.current];
    if (canLookAround(current) && turning.current.size) {
      const keys = turning.current;
      const yawDelta = Number(keys.has('ArrowLeft')) - Number(keys.has('ArrowRight'));
      const pitchDelta = Number(keys.has('ArrowUp')) - Number(keys.has('ArrowDown'));
      turnView(current, yawDelta * delta * 1.65, pitchDelta * delta * 1.3);
    }
    let { yaw, pitch } = look;
    if (atBench) cached.position.set(benchEye.x, benchEye.y, benchEye.z);
    else cached.position.set(eye.x, eye.y, eye.defaultZ);
    const screenScale = 0.895;
    const screenDistance =
      Math.max(display.outerHeight, display.outerWidth / aspect) /
      (screenScale * 2 * Math.tan(fov / 2));
    const approach = env.reducedMotion
      ? 1
      : T.MathUtils.clamp((performance.now() - animationStart.current) / 835, 0, 1);
    const lean = T.MathUtils.smootherstep(approach, 0, 1);
    if (current === 'computer') {
      cached.position.set(
        display.x,
        display.y - 0.005,
        display.z + screenDistance + display.surface,
      );
      yaw = 0;
      pitch = 0;
    }
    let hardwareFov = viewFov;
    if (current === 'case' || cabinetFocus.current) {
      hardwareFov = frameHardware(caseView.current, cached.position, cached.euler);
      yaw = cached.euler.y;
      pitch = cached.euler.x;
    }
    const wall = wallFocus.current;
    if (wall?.type === 'gear') {
      frameGearWall(wall.object, aspect, cached.position);
      yaw = gearEye.yaw + looks.current.gear.yaw;
      pitch = gearEye.pitch + looks.current.gear.pitch;
    } else if (wall) {
      pitch = frameWallSurface(wall, aspect, cached.position);
      yaw = 0;
    }
    const lookingOutside = atWindow(current) || (current === 'returning' && windowFocus.current);
    if (lookingOutside) {
      const look = windowView.current;
      yaw = look.yaw;
      pitch = look.pitch;
      const eyeOffset = 0.075;
      cached.position.set(
        windowEye.x + eyeOffset * (Math.cos(windowEye.pitch) - Math.sin(yaw) * Math.cos(pitch)),
        windowEye.y + eyeOffset * (Math.sin(pitch) - Math.sin(windowEye.pitch)),
        windowEye.z - eyeOffset * Math.cos(yaw) * Math.cos(pitch),
      );
    }
    const drawer = drawerFocus.current;
    if (drawer) {
      cached.position.copy(drawer.center).add(drawerEyeOffset);
      yaw = 0;
      pitch = drawerPitch;
    }
    const targetFov =
      lookingOutside || windowTravel.current
        ? windowView.current.fov
        : drawer
          ? drawerFov
          : (wall?.fov ??
            (isStation(current) || (current === 'returning' && !cabinetFocus.current)
              ? zoom.current[station.current]
              : hardwareFov));
    const nextFov =
      current === 'computer'
        ? T.MathUtils.lerp(computerStart.current.fov, viewFov, lean)
        : T.MathUtils.lerp(camera.fov, targetFov, ease);
    if (Math.abs(camera.fov - targetFov) > 0.001) {
      camera.fov = Math.abs(nextFov - targetFov) < 0.001 ? targetFov : nextFov;
      camera.updateProjectionMatrix();
    }
    const walk = windowTravel.current;
    if (current === 'computer') {
      camera.position.lerpVectors(computerStart.current.position, cached.position, lean);
      camera.position.y += Math.sin(Math.PI * lean) * 0.032;
      camera.quaternion
        .copy(computerStart.current.quaternion)
        .slerp(cached.orientation.identity(), T.MathUtils.smootherstep(approach, 0, 0.86));
    } else if (walk) {
      const step = env.reducedMotion
        ? 1
        : T.MathUtils.clamp((performance.now() - walk.start) / walk.duration, 0, 1);
      const travel = T.MathUtils.smoothstep(step, 0, 1);
      camera.position.lerpVectors(walk.position, cached.position, travel);
      const turn = yaw - walk.yaw;
      camera.rotation.set(
        T.MathUtils.lerp(walk.pitch, pitch, travel),
        walk.yaw + Math.atan2(Math.sin(turn), Math.cos(turn)) * travel,
        0,
        'YXZ',
      );
      if (step === 1) windowTravel.current = null;
    } else if (env.reducedMotion) {
      camera.position.copy(cached.position);
      camera.rotation.set(pitch, Math.atan2(Math.sin(yaw), Math.cos(yaw)), 0, 'YXZ');
    } else {
      if (
        (current === 'case' && caseView.current.hardwareId === 'case') ||
        (current === 'returning' && returningFromTower.current)
      ) {
        const center = caseView.current.center;
        const from = camera.position;
        const to = cached.position;
        const fromAngle = Math.atan2(center.x - from.x, from.z - center.z);
        const toAngle = Math.atan2(center.x - to.x, to.z - center.z);
        const angle = T.MathUtils.lerp(fromAngle, toAngle, ease);
        const range = T.MathUtils.lerp(
          Math.hypot(from.x - center.x, from.z - center.z),
          Math.hypot(to.x - center.x, to.z - center.z),
          ease,
        );
        const radius = towerRadius(range, angle, center.x);
        camera.position.set(
          center.x - radius * Math.sin(angle),
          T.MathUtils.lerp(from.y, to.y, ease),
          center.z + radius * Math.cos(angle),
        );
      } else {
        camera.position.lerp(cached.position, ease);
      }
      const aimPitch = T.MathUtils.lerp(camera.rotation.x, pitch, ease);
      const turn = yaw - camera.rotation.y;
      const aimYaw = camera.rotation.y + Math.atan2(Math.sin(turn), Math.cos(turn)) * ease;
      camera.rotation.set(aimPitch, Math.atan2(Math.sin(aimYaw), Math.cos(aimYaw)), 0, 'YXZ');
    }
    camera.updateMatrixWorld(true);
    const inspectionFill = model.inspectionFill;
    const marker = live.current.mapMarker.current;
    if (marker) {
      const forward = camera.getWorldDirection(cached.local);
      const heading = T.MathUtils.radToDeg(Math.atan2(forward.x, -forward.z));
      const transform = `translate(${camera.position.x.toFixed(3)} ${camera.position.z.toFixed(3)}) rotate(${heading.toFixed(1)})`;
      if (marker.getAttribute('transform') !== transform)
        marker.setAttribute('transform', transform);
    }
    const fill =
      current === 'remote'
        ? env.night
          ? 0.035
          : 0.14
        : current === 'inspect'
          ? 0.16
          : current === 'drawer'
            ? 0.1
            : 0;
    inspectionFill.intensity = T.MathUtils.lerp(inspectionFill.intensity, fill, ease);
    if (inspectionFill.intensity > 0.001) {
      if (current === 'remote') cached.local.set(0.34 * aspect * 0.29 - 0.08, 0.03, -0.07);
      else cached.local.set(-0.18, 0.19, -0.1);
      inspectionFill.position.copy(cached.local.applyMatrix4(camera.matrixWorld));
    }

    const moving = inspection.current;
    if (moving) {
      const object = moving.target.object;
      if (current === 'returning') {
        const start = moving.putDownFrom ?? moving.home;
        const progress = T.MathUtils.smootherstep(
          performance.now() - animationStart.current,
          0,
          430,
        );
        object.position.lerpVectors(start.position, moving.home.position, progress);
        object.quaternion.slerpQuaternions(start.quaternion, moving.home.quaternion, progress);
        if (progress === 1) inspection.current = null;
      } else placeHeldItem(moving, ease, current === 'remote');
    }
    const link =
      current === 'inspect' && moving?.target.type === 'inspect' ? moving.target.link : undefined;
    const anchor = live.current.inspectionAnchor.current;
    const phonePanel = live.current.phonePanel.current;
    const caption = live.current.objectCaption.current;
    if (caption && moving && (current === 'inspect' || current === 'remote')) {
      const { object } = moving.target;
      if (moving.boundsRevision !== props.detailRevision.current) {
        moving.bounds = localBounds(object);
        moving.boundsRevision = props.detailRevision.current;
      }
      object.updateWorldMatrix(true, false);
      const { min, max } = moving.bounds;
      let left = Infinity,
        right = -Infinity,
        bottom = -Infinity;
      if (!moving.bounds.isEmpty()) {
        for (let i = 0; i < 8; i++) {
          const p = cached.local
            .set(i & 1 ? max.x : min.x, i & 2 ? max.y : min.y, i & 4 ? max.z : min.z)
            .applyMatrix4(object.matrixWorld)
            .project(camera);
          if (p.z < -1 || p.z > 1) continue;
          left = Math.min(left, p.x);
          right = Math.max(right, p.x);
          bottom = Math.max(bottom, ((1 - p.y) * size.height) / 2);
        }
      }
      if (Number.isFinite(bottom)) {
        const center = Math.round(((1 + (left + right) / 2) * size.width) / 2) + 'px';
        const edge = Math.round(bottom) + 'px';
        if (caption.style.getPropertyValue('--item-center') !== center)
          caption.style.setProperty('--item-center', center);
        if (caption.style.getPropertyValue('--item-bottom') !== edge)
          caption.style.setProperty('--item-bottom', edge);
      }
    }
    const heldPhone = current === 'inspect' && moving?.target.id === 'development-phone';
    const projected = heldPhone ? phonePanel : anchor;
    const region = heldPhone
      ? {
          left: -phoneDisplay.width / 2,
          right: phoneDisplay.width / 2,
          top: phoneDisplay.height / 2,
          bottom: -phoneDisplay.height / 2,
          z: phoneDisplay.depth,
        }
      : link?.region;
    if (projected && region && moving) {
      const object = moving.target.object;
      const { left, right, top, bottom, z } = region;
      object.updateWorldMatrix(true, false);
      object.getWorldPosition(cached.position);
      cached.position.sub(camera.position);
      const facing =
        cached.local.set(0, 0, 1).transformDirection(object.matrixWorld).dot(cached.position) <
        -0.018;
      if (facing) {
        for (const [index, corner] of cached.screenCorners.entries()) {
          corner
            .set(index % 2 === 0 ? left : right, index < 2 ? top : bottom, z)
            .applyMatrix4(object.matrixWorld)
            .project(camera);
          corner.set(
            ((1 + corner.x) * size.width) / 2,
            ((1 - corner.y) * size.height) / 2,
            corner.z,
          );
        }
        const matrix = screenProjection(
          cached.screenCorners,
          heldPhone ? phoneDisplay.viewportWidth : 250,
          heldPhone ? phoneDisplay.viewportHeight : 54,
        );
        projected.style.transform = matrix;
        projected.style.visibility = matrix ? 'visible' : 'hidden';
        if (heldPhone && phonePanel) {
          const firstAppearance = !phonePanel.dataset.visible && matrix;
          phonePanel.dataset.visible = String(Boolean(matrix));
          phonePanel.inert = !matrix;
          if (firstAppearance) phonePanel.focus({ preventScroll: true });
        }
      } else {
        projected.style.visibility = 'hidden';
        if (heldPhone && phonePanel) {
          phonePanel.dataset.visible = 'false';
          phonePanel.inert = true;
        }
      }
    }
    if (current === 'computer' && screen.current) {
      if (approach >= 0.53) {
        const panel = screen.current;
        const height = (display.height * size.height) / (screenDistance * 2 * Math.tan(fov / 2));
        const width = (height * display.width) / display.height;
        cached.screenCorners.forEach((point, index) => {
          point
            .set(
              display.x + ((index % 2) - 0.5) * display.width,
              display.y + (0.5 - Math.floor(index / 2)) * display.height,
              display.z + display.surface,
            )
            .project(camera);
          point.set(((point.x + 1) * size.width) / 2, ((1 - point.y) * size.height) / 2, point.z);
        });
        panel.style.width = width + 'px';
        panel.style.height = height + 'px';
        panel.style.transform = screenProjection(cached.screenCorners, width, height);
        panel.style.opacity = String(T.MathUtils.smoothstep(approach, 0.53, 0.98));
        panel.dataset.visible = 'true';
        if (approach === 1 && !focused.current) {
          panel.dataset.interactive = 'true';
          panel
            .querySelector<HTMLButtonElement>('[data-lock-unlock]')
            ?.focus({ preventScroll: true });
          focused.current = true;
        }
      }
    }
    if (
      current === 'returning' &&
      !inspection.current &&
      !windowTravel.current &&
      (env.reducedMotion || performance.now() - animationStart.current > 430)
    ) {
      mode.current = enclosingMode();
      onMode(mode.current);
    }
    const geometryMoving = model.update(
      env,
      delta,
      clock.elapsedTime,
      live.current.musicLevels(),
      current === 'case' ? caseView.current.hardwareId : inspection.current?.target.id,
      live.current.musicPlaying,
      current === 'bench' || (atBench && current === 'inspect'),
      camera,
    );
    if (shadowWarmup.current > 0 || current === 'returning' || geometryMoving) {
      shadowWarmup.current = Math.max(0, shadowWarmup.current - 1);
      gl.shadowMap.needsUpdate = true;
    }
  });
  return <primitive object={model.root} />;
}

declare global {
  interface Window {
    __studioReview?: {
      inventory: () => { id: string; type: string; name: string; uuid: string }[];
      captureLighting: (
        location?: 'desk' | 'aj' | 'camp',
      ) => Promise<{ width: number; height: number; rgbe: string }>;
      activate: (id: string) => void;
      project: (id: string) => { x: number; y: number } | null;
      camera: () => { position: number[]; rotation: number[]; fov: number };
      objectPose: (id: string) => { position: number[]; rotation: number[] } | undefined;
      bounds: (name: string) => { min: number[]; max: number[] };
      drawer: (index: number) => number | undefined;
      lightLevels: () => ReturnType<ReturnType<typeof buildStudio>['lightLevels']>;
      exportRoom: (objectName?: string, authoring?: boolean) => Promise<void>;
    };
  }
}

export default function StudioView(props: Props) {
  const mapMarker = useRef<SVGGElement>(null);
  const phonePanel = useRef<HTMLDivElement>(null);
  const [phoneHeld, setPhoneHeld] = useState(false);
  const firstPicture = useRef<FirstPicture>('loading');
  const [firstFrame] = useState(roomFirstFrame);
  const detailRevision = useRef(0);
  const [lowScale, setLowScale] = useState(props.initialLowScale);
  return (
    <>
      <Canvas
        className="studio-canvas"
        shadows={props.environment.quality === 'high'}
        dpr={props.environment.quality === 'high' ? [1, 1.5] : lowScale}
        camera={{
          fov: roomFov,
          near: 0.028,
          far: waterfrontFarClip,
          position: [eye.x, eye.y, eye.defaultZ],
        }}
        gl={{ antialias: true, powerPreference: 'high-performance', alpha: false }}
        onCreated={({ gl }) => {
          gl.debug.checkShaderErrors = import.meta.env.DEV;
          gl.toneMapping = T.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.04;
        }}
      >
        <CameraRig
          firstFrame={firstFrame}
          {...props}
          mapMarker={mapMarker}
          firstPicture={firstPicture}
          detailRevision={detailRevision}
          phonePanel={phonePanel}
          setPhoneHeld={setPhoneHeld}
        />
        <Finish
          firstFrame={firstFrame}
          night={props.environment.night}
          onInteractive={props.onReady}
          look={props.environment.roomLook}
          roomVisible={props.roomVisible}
          firstPicture={firstPicture}
          detailRevision={detailRevision}
          setLowScale={setLowScale}
          screen={props.screen}
          enabled={props.environment.quality === 'high'}
        />
      </Canvas>
      {phoneHeld && (
        <PhoneHome
          panelRef={phonePanel}
          environment={props.environment}
          onToggle={props.onToggleHomeLight}
        />
      )}
      {props.roomVisible && props.mode !== 'computer' && (
        <Minimap
          marker={mapMarker}
          label={local(props.environment.locale, 'Studio minimap', '工作室小地图')}
        />
      )}
    </>
  );
}
