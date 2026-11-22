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
import { phoneDisplay } from './development-phone';
import { Finish, type FirstPicture } from './Finish';
import { roomFirstFrame } from './room-first-frame';
import { warmRoomEffect } from './room-effect-material';
import { warmRiverFerry } from './river-ferry';
import { Minimap } from './Minimap';
import { studioReflections } from './reflections';
import { roomVisibility } from './room-visibility';
import { roomDetail } from './room-detail';
import { roomPicking } from './room-picking';
import { surfaceFinish } from './surface-finish';
import { screenProjection } from './screen-projection';
import { buildStudio, buildStudioSteps, type StudioModel } from './studio';
import {
  opensStudioView,
  atWindow,
  canLookAround,
  canPick,
  isStation,
  isWallView,
  type AppID,
  type InspectionLink,
  type Mode,
  type Station,
  type StudioControls,
  type Target,
} from './interaction';
import {
  frameHardware,
  frameWallSurface,
  initialOrbit,
  localBounds,
  savedPose,
  towerOrbit,
  towerRadius,
  type Pose,
  type WallFocus,
} from './view-framing';
import { waterfrontFarClip } from './window-depth';
import { createStudioReview } from './review/studio-review';

export type { Mode } from './interaction';

const drawerEyeOffset = new T.Vector3(0, 0.54, 0.27);
const drawerPitch = -Math.atan2(drawerEyeOffset.y, drawerEyeOffset.z);
const drawerFov = 46;
const returnDuration = 430;

type Props = {
  initialLowScale: number;
  computerLocked: boolean;
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
  controls: RefObject<StudioControls | null>;
};

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
const lookKeys = new Set(['ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight']);

type RigProps = Props & {
  mapMarker: RefObject<SVGGElement | null>;
  firstPicture: RefObject<FirstPicture>;
  detailRevision: RefObject<number>;
  phonePanel: RefObject<HTMLDivElement | null>;
  setPhoneHeld: (held: boolean) => void;
  nativeLow: boolean;
};

type Assembly = {
  model: StudioModel;
  assets: { loaded: number; total: number };
  frontReady: () => Promise<void>;
};

function assemblyLoading() {
  const assets = { loaded: 0, total: 0 };
  const manager = new T.LoadingManager();
  manager.onStart = manager.onProgress = (_, loaded, total) =>
    Object.assign(assets, { loaded, total });
  function frontReady() {
    if (assets.loaded === assets.total) return Promise.resolve();
    return new Promise<void>((resolve) => {
      manager.onLoad = resolve;
    });
  }
  return { assets, manager, frontReady };
}

function CameraRig(props: RigProps & Assembly & { earlyRear: boolean }) {
  const { camera: baseCamera, gl, scene } = useThree();
  const camera = baseCamera as T.PerspectiveCamera;
  const { model, assets } = props;
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
    object: undefined as T.Object3D | undefined,
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

  const openSequence = useRef(0);
  const inspectedTarget = useRef<Extract<Target, { type: 'inspect' }> | undefined>(undefined);

  function setMode(next: Mode, app?: AppID, link?: InspectionLink) {
    openSequence.current++;
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
    if (selected !== inspectedTarget.current) {
      inspectedTarget.current?.onInspect?.(false, live.current.environment.reducedMotion);
      selected?.onInspect?.(true, live.current.environment.reducedMotion);
      inspectedTarget.current = selected;
    }
    live.current.setPhoneHeld(
      next === 'inspect' && inspection.current?.target.id === 'development-phone',
    );
    animationStart.current = performance.now();
    live.current.onMode(next, app, link);
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

  function finishReturn() {
    const destination = enclosingMode();
    if (live.current.environment.reducedMotion) {
      const view = returnViews.current.get(destination);
      if (view) {
        camera.position.copy(view.position);
        camera.quaternion.copy(view.quaternion);
        camera.fov = view.fov;
      } else if (destination === 'room') {
        camera.position.set(eye.x, eye.y, eye.defaultZ);
        camera.rotation.set(looks.current.room.pitch, looks.current.room.yaw, 0, 'YXZ');
        camera.fov = zoom.current.room;
      }
      camera.updateProjectionMatrix();
      camera.updateMatrixWorld(true);
      shadowWarmup.current = 2;
    }
    returnViews.current.delete(destination);
    setMode(destination);
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
      performance.mark('studio-room-rear-ready');
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
      finishReturn();
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
        void model.prepareRear('bench');
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
      const sequence = ++openSequence.current;
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
          if (sequence === openSequence.current && !surfaceAbort.signal.aborted) open(target, true);
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
      if (target.type === 'gear') void model.prepareRear('gear');
      else if (target.id === 'collection-cabinet') void model.prepareRear('cabinet');
      else if (target.id === 'filament-printer') void model.prepareRear('bench');
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
          object: target.object,
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

    function exit() {
      openSequence.current++;
      const current = mode.current;
      if (current === 'room' || current === 'returning') return false;
      if (current === 'bench') {
        moveToStation('room');
      } else if (current === 'drawer') {
        closeDrawer();
      } else {
        if (isWallView(current)) wallFocus.current = null;
        if (current === 'case') cabinetFocus.current = false;
        if (current === 'window') windowFocus.current = false;
        if (atWindow(current) && !windowFocus.current) {
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
      return true;
    }

    const computer = model.targets.find((target) => target.id === 'computer');
    let measuredFirstTurn = false;
    live.current.controls.current = {
      open: () => open(computer),
      exit,
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
        if (!measuredFirstTurn && live.current.roomVisible) {
          measuredFirstTurn = true;
          performance.mark('studio-input-accepted', { detail: { eventTime: event.timeStamp } });
        }
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
      openSequence.current++;
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
      if (
        lookKeys.has(event.code) ||
        (event.key === 'Escape' && (event.defaultPrevented || event.repeat))
      )
        openSequence.current++;
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
      if (event.key === 'Escape' && exit()) {
        event.preventDefault();
        return;
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
      window.__studioReview = createStudioReview({
        model,
        camera,
        renderer,
        scene,
        lightingReady: () => visibility.ready,
        open,
      });
    }
    return () => {
      if (import.meta.env.DEV) delete window.__studioReview;
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
    return model.prepareBookBacks();
  }, [model, props.roomVisible, shaded]);

  useEffect(() => {
    if (!props.roomVisible || (!props.earlyRear && !shaded)) return;
    if (typeof window.requestIdleCallback === 'function') {
      const idle = window.requestIdleCallback(() => void model.prepareRear(), { timeout: 240 });
      return () => window.cancelIdleCallback(idle);
    }
    const timer = window.setTimeout(() => void model.prepareRear(), 32);
    return () => window.clearTimeout(timer);
  }, [model, props.earlyRear, props.roomVisible, shaded]);

  useEffect(() => {
    const prepare = model.prepareWaterMotion;
    if (!prepare || !props.roomVisible || !shaded) return;
    const controller = new AbortController();
    const { signal } = controller;
    const warmFerry = new URLSearchParams(location.search).get('studio-ferry') === 'warm';
    let cancel = () => {};
    void model.rearReady.then(() => {
      if (signal.aborted) return;
      const enable = () =>
        prepare(
          (material) => warmRoomEffect(gl, material, signal),
          signal,
          warmFerry
            ? (ferry) =>
                warmRiverFerry(
                  gl,
                  ferry,
                  camera,
                  scene,
                  () => live.current.environment.quality === 'high',
                  signal,
                )
            : undefined,
        );
      if (typeof window.requestIdleCallback === 'function') {
        const idle = window.requestIdleCallback(enable, { timeout: 1500 });
        cancel = () => window.cancelIdleCallback(idle);
      } else {
        const timer = window.setTimeout(enable, 32);
        cancel = () => window.clearTimeout(timer);
      }
    });
    return () => {
      controller.abort();
      cancel();
    };
  }, [camera, gl, model, props.roomVisible, scene, shaded]);

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
    const { environment: env, screen } = live.current;
    const load = loading.current;
    if (!load.complete && assets.total) {
      const ratio = assets.loaded / assets.total;
      if (ratio === 1 && props.roomVisible && props.firstPicture.current === 'interactive') {
        performance.mark('studio-room-material-prep-start');
        roomMaterials.current?.prepareMaterials();
        finishNormals.current?.();
        performance.mark('studio-room-material-prep-end');
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
      if (props.nativeLow) roomMeshes.current?.refresh();
      if (visibleArrival) {
        props.detailRevision.current++;
        shadowWarmup.current = 2;
      }
    }
    const low = load.complete && env.quality === 'low';
    if (props.nativeLow && low) {
      const detail =
        inspection.current?.target.object ??
        (current === 'case' ? caseView.current.object : undefined);
      roomMeshes.current?.select(true, detail);
    } else {
      roomMeshes.current?.select(
        low && (isStation(current) || atWindow(current) || current === 'computer'),
      );
    }
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
    const fovEase = env.reducedMotion ? 1 : 1 - Math.exp(-elapsed * 10.5);
    const nextFov =
      current === 'computer'
        ? T.MathUtils.lerp(computerStart.current.fov, viewFov, lean)
        : T.MathUtils.lerp(camera.fov, targetFov, fovEase);
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
          returnDuration,
        );
        if (progress === 1) restoreHeldItem();
        else {
          object.position.lerpVectors(start.position, moving.home.position, progress);
          object.quaternion.slerpQuaternions(start.quaternion, moving.home.quaternion, progress);
        }
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
          const entryButton = panel.querySelector<HTMLButtonElement>(
            live.current.computerLocked ? '[data-lock-unlock]' : '.system-menu-button',
          );
          entryButton?.focus({ preventScroll: true });
          focused.current = true;
        }
      }
    }
    if (
      current === 'returning' &&
      !inspection.current &&
      !windowTravel.current &&
      (env.reducedMotion || performance.now() - animationStart.current >= returnDuration)
    ) {
      finishReturn();
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
      props.nativeLow,
    );
    if (shadowWarmup.current > 0 || current === 'returning' || geometryMoving) {
      shadowWarmup.current = Math.max(0, shadowWarmup.current - 1);
      gl.shadowMap.needsUpdate = true;
    }
  });
  return <primitive object={model.root} />;
}

function StudioRoom({
  firstFrame,
  nativeLow,
  setLowScale,
  ...props
}: RigProps & {
  firstFrame: ReturnType<typeof roomFirstFrame>;
  setLowScale: (scale: number) => void;
}) {
  const gl = useThree((state) => state.gl);
  const [startup] = useState(() => {
    const query = new URLSearchParams(location.search);
    const rearMode = query.get('studio-rear');
    const deferWaterMotion = query.get('studio-water-motion') !== 'eager';
    const waterfront = query.get('studio-waterfront');
    return {
      environment: props.environment,
      earlyRear: rearMode === 'early',
      sliced: query.get('studio-build') === 'sliced',
      simpleLow: query.get('studio-low-shading') === 'simple',
      options: {
        deferBookBacks: query.get('studio-startup') === 'deferred-books',
        prioritizeRear: rearMode === 'priority' || rearMode === 'early',
        preloadInspection: query.get('studio-details') === 'preload',
        mergeFirst: query.get('studio-batching') !== 'transform-first',
        deferWaterMotion,
        warmWaterfront:
          waterfront === 'warm' || (deferWaterMotion && waterfront !== 'cold')
            ? (material: T.ShaderMaterial) => firstFrame.warmWaterfront(gl, material)
            : undefined,
      },
    };
  });
  const [assembly, setAssembly] = useState<Assembly | null>(() => {
    if (startup.sliced) return null;
    firstFrame.warm(gl);
    const { assets, manager, frontReady } = assemblyLoading();
    performance.mark('studio-room-build-start');
    const model = buildStudio(manager, startup.environment, startup.options);
    performance.mark('studio-room-built');
    firstFrame.windowSlats.value = model.slats;
    return { model, assets, frontReady };
  });
  const [failure, setFailure] = useState<{ error: unknown }>();
  const readiness = useRef<Promise<void> | null>(null);

  useEffect(() => {
    if (!startup.sliced) return;
    firstFrame.warm(gl);
    const { assets, manager, frontReady } = assemblyLoading();
    const steps = buildStudioSteps(manager, startup.environment, startup.options);
    let frame = requestAnimationFrame(advance);
    let started = false;
    let complete = false;

    function advance() {
      try {
        if (!started) {
          started = true;
          performance.mark('studio-room-build-start');
        }
        const deadline = performance.now() + 5;
        do {
          const step = steps.next();
          if (!step.done) continue;
          const model = step.value;
          complete = true;
          performance.mark('studio-room-built');
          firstFrame.windowSlats.value = model.slats;
          setAssembly({ model, assets, frontReady });
          return;
        } while (performance.now() < deadline);
        frame = requestAnimationFrame(advance);
      } catch (error) {
        setFailure({ error });
      }
    }

    return () => {
      cancelAnimationFrame(frame);
      if (!complete) firstFrame.dispose();
    };
  }, [firstFrame, gl, startup]);

  useLayoutEffect(() => {
    if (!startup.options.preloadInspection || !assembly) return;
    performance.mark('studio-inspection-preload-start');
    readiness.current = Promise.allSettled([
      assembly.frontReady(),
      assembly.model.prepareRear(),
    ]).then(() => {
      performance.mark('studio-inspection-preload-end');
    });
    return () => {
      readiness.current = null;
    };
  }, [assembly, startup.options.preloadInspection]);

  function showRoom() {
    const pending = readiness.current;
    if (!pending) {
      props.onReady();
      return;
    }
    void pending.then(() => {
      if (readiness.current === pending) props.onReady();
    });
  }

  if (failure) throw failure.error;
  if (!assembly) return null;
  return (
    <>
      <CameraRig {...props} {...assembly} nativeLow={nativeLow} earlyRear={startup.earlyRear} />
      <Finish
        firstFrame={firstFrame}
        night={props.environment.night}
        onInteractive={showRoom}
        look={props.environment.roomLook}
        roomVisible={props.roomVisible}
        firstPicture={props.firstPicture}
        detailRevision={props.detailRevision}
        workbench={assembly.model.workbench}
        setLowScale={setLowScale}
        nativeLow={nativeLow}
        simpleLow={startup.simpleLow}
        roomMode={props.mode === 'room'}
        screen={props.screen}
        enabled={props.environment.quality === 'high'}
      />
    </>
  );
}

export default function StudioView(props: Props) {
  const mapMarker = useRef<SVGGElement>(null);
  const phonePanel = useRef<HTMLDivElement>(null);
  const [phoneHeld, setPhoneHeld] = useState(false);
  const firstPicture = useRef<FirstPicture>('loading');
  const [firstFrame] = useState(() => {
    const options = new URLSearchParams(location.search);
    const preview = options.get('studio-preview');
    return roomFirstFrame({
      warmPreview: preview === 'warm',
      warmOled: preview === 'oled',
      stagedTextures: options.get('studio-preview-textures') === 'staged',
      warmBuffers: options.get('studio-buffers') === 'warm',
    });
  });
  const [nativeLow] = useState(
    () => new URLSearchParams(location.search).get('studio-low') === 'native',
  );
  const detailRevision = useRef(0);
  const [lowScale, setLowScale] = useState(props.initialLowScale);
  useLayoutEffect(() => {
    if (props.roomVisible) performance.mark('studio-input-ready');
  }, [props.roomVisible]);
  return (
    <>
      <Canvas
        className="studio-canvas"
        shadows={props.environment.quality === 'high'}
        dpr={
          props.environment.quality === 'high'
            ? [1, 1.5]
            : nativeLow
              ? window.devicePixelRatio
              : lowScale
        }
        camera={{
          fov: roomFov,
          near: 0.028,
          far: waterfrontFarClip,
          position: [eye.x, eye.y, eye.defaultZ],
        }}
        gl={{
          antialias: !nativeLow || props.environment.quality === 'high',
          powerPreference: 'high-performance',
          alpha: false,
        }}
        onCreated={({ gl }) => {
          gl.debug.checkShaderErrors = import.meta.env.DEV;
          gl.toneMapping = T.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.04;
        }}
      >
        <StudioRoom
          firstFrame={firstFrame}
          {...props}
          mapMarker={mapMarker}
          firstPicture={firstPicture}
          detailRevision={detailRevision}
          phonePanel={phonePanel}
          setPhoneHeld={setPhoneHeld}
          setLowScale={setLowScale}
          nativeLow={nativeLow}
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
