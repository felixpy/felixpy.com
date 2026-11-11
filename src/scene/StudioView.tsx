import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef, useState, type RefObject } from 'react';
import * as T from 'three';
import type { Environment } from '../app/environment';
import { local } from '../app/locale';
import { arcball, benchEye, eye, viewFov, windowEye } from './camera';
import { display } from './hardware';
import { Finish } from './Finish';
import { Minimap } from './Minimap';
import { studioReflections } from './reflections';
import { screenProjection } from './screen-projection';
import { buildStudio, type AppID, type Target } from './studio';
import { panoramaMeshName, waterfrontFarClip } from './window-depth';

type Station = 'room' | 'bench';
export type Mode =
  | Station
  | 'inspect'
  | 'case'
  | 'window'
  | 'remote'
  | 'map'
  | 'board'
  | 'computer'
  | 'drawer'
  | 'returning';
const isStation = (mode: Mode): mode is Station => mode === 'room' || mode === 'bench';
const atWindow = (mode: Mode) => mode === 'window' || mode === 'remote';
const canPick = (mode: Mode) =>
  isStation(mode) || atWindow(mode) || mode === 'map' || mode === 'board' || mode === 'drawer';

type Props = {
  showMinimap: boolean;
  environment: Environment;
  mode: Mode;
  onMode: (mode: Mode, app?: AppID, link?: string) => void;
  onPress: (target: Target) => string | void;
  onHint: (text: string, point?: { x: number; y: number }) => void;
  onReady: () => void;
  onProgress: (ratio: number) => void;
  musicLevels: () => { bass: number; mid: number; beat: number };
  screen: RefObject<HTMLDivElement | null>;
  caption: RefObject<HTMLDivElement | null>;
  inspectionAnchor: RefObject<HTMLAnchorElement | null>;
  controls: RefObject<{ open: () => void } | null>;
};

type Pose = { position: T.Vector3; quaternion: T.Quaternion };
type Inspection = {
  target: Target;
  home: Pose;
  rotation: T.Quaternion;
  initial: T.Quaternion;
  distance: number;
};
type FramedObject = { object: T.Object3D; bounds: T.Box3 };

const savedPose = (obj: T.Object3D): Pose => ({
  position: obj.position.clone(),
  quaternion: obj.quaternion.clone(),
});

const initialCaseView = { azimuth: 0.65, elevation: 0.19, distance: 1.25 };
const lookKeys = new Set(['ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight']);

function localBounds(object: T.Object3D) {
  object.updateWorldMatrix(true, true);
  const toLocal = object.matrixWorld.clone().invert();
  const matrix = new T.Matrix4(),
    part = new T.Box3(),
    bounds = new T.Box3();
  object.traverse((child) => {
    if (!(child instanceof T.Mesh) || !child.visible) return;
    if (!child.geometry.boundingBox) child.geometry.computeBoundingBox();
    if (child.geometry.boundingBox) {
      matrix.multiplyMatrices(toLocal, child.matrixWorld);
      bounds.union(part.copy(child.geometry.boundingBox).applyMatrix4(matrix));
    }
  });
  return bounds;
}

function CameraRig(props: Props & { mapMarker: RefObject<SVGGElement | null> }) {
  const { camera: baseCamera, gl, scene } = useThree();
  const camera = baseCamera as T.PerspectiveCamera;
  const [{ model, assets }] = useState(() => {
    const assets = { loaded: 0, total: 0 };
    const manager = new T.LoadingManager();
    manager.onProgress = (_, loaded, total) => Object.assign(assets, { loaded, total });
    return { model: buildStudio(manager), assets };
  });
  const live = useRef(props);
  live.current = props;
  const loading = useRef({ reported: -1, frames: 0, complete: false });
  const deskLook = useRef({ yaw: 0, pitch: -0.081 });
  const benchLook = useRef({ yaw: benchEye.yaw, pitch: benchEye.pitch });
  const zoom = useRef({ room: viewFov, bench: viewFov });
  const station = useRef<Station>('room');
  const turning = useRef(new Set<string>());
  const windowView = useRef({ yaw: windowEye.yaw, pitch: windowEye.pitch });
  const windowFocus = useRef(false);
  const windowApproach = useRef<(Pose & { time: number }) | null>(null);
  const caseView = useRef({ ...initialCaseView, center: new T.Vector3() });
  const wallFocus = useRef<
    (FramedObject & { type: 'map' | 'board'; center: T.Vector3; fov: number }) | null
  >(null);
  const drawerFocus = useRef<(FramedObject & { center: T.Vector3 }) | null>(null);
  const mode = useRef<Mode>('room');
  const focused = useRef(false);
  const inspection = useRef<Inspection | null>(null);
  const described = useRef<FramedObject | null>(null);
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

  useEffect(() => {
    const element = gl.domElement;
    const renderer = gl as T.WebGLRenderer;
    const reflectionMap = studioReflections(renderer);
    scene.environment = reflectionMap.texture;
    scene.environmentIntensity = 0.28;
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = true;
    renderer.shadowMap.type = T.PCFShadowMap;

    camera.position.set(eye.x, eye.y, eye.defaultZ);
    camera.rotation.set(deskLook.current.pitch, deskLook.current.yaw, 0, 'YXZ');
    camera.updateMatrixWorld(true);
    const ray = new T.Raycaster();
    const position = new T.Vector2();
    function pick(x: number, y: number) {
      const rect = element.getBoundingClientRect();
      position.set(((x - rect.left) / rect.width) * 2 - 1, ((rect.top - y) / rect.height) * 2 + 1);
      ray.setFromCamera(position, camera);
      for (const hit of ray.intersectObject(model.root, true)) {
        if (!(hit.object instanceof T.Mesh)) continue;
        if (hit.object.material instanceof T.MeshBasicMaterial && hit.object.material.transparent)
          continue;
        let current: T.Object3D | null = hit.object;
        while (current) {
          const target = model.byObject.get(current);
          if (target && model.canReach(target, mode.current)) return target;
          current = current.parent;
        }
        return undefined;
      }
    }

    function setMode(next: Mode, app?: AppID, link?: string) {
      turning.current.clear();
      hover.current = undefined;
      if (next === 'returning') described.current = null;
      mode.current = next;
      animationStart.current = performance.now();
      live.current.onMode(next, app, link);
    }
    function moveToStation(next: Station) {
      station.current = next;
      if (next === 'bench') benchLook.current = { yaw: benchEye.yaw, pitch: benchEye.pitch };
      hover.current = undefined;
      pointer.current = null;
      live.current.onHint('');
      setMode(next);
    }
    function open(target: Target | undefined) {
      if (!target) return;
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
        (!isStation(mode.current) &&
          mode.current !== 'board' &&
          mode.current !== 'drawer' &&
          mode.current !== 'window') ||
        !model.canReach(target, mode.current)
      )
        return;
      if (target.type === 'window' || target.type === 'remote') {
        if (!atWindow(mode.current)) {
          windowView.current = { yaw: windowEye.yaw, pitch: windowEye.pitch };
          windowApproach.current = { ...savedPose(camera), time: performance.now() };
        }
        if (target.type === 'window') {
          windowFocus.current = true;
          described.current = null;
          setMode('window');
          live.current.onHint('');
          return;
        }
      }
      if (target.type === 'drawer') {
        if (mode.current === 'drawer') {
          closeDrawer();
        } else {
          const bounds = localBounds(target.object);
          drawerFocus.current = {
            object: target.object,
            bounds,
            center: model.drawerCenter(target.index),
          };
          described.current = drawerFocus.current;
          model.setDrawer(target.index);
          setMode('drawer');
          live.current.onHint('');
        }
        return;
      }
      hover.current = undefined;
      if (target.type === 'door') {
        model.toggleDoor();
        live.current.onHint('');
        return;
      }
      if (target.type === 'workbench') {
        moveToStation(mode.current === 'room' ? 'bench' : 'room');
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
      if (target.type === 'map' || target.type === 'board') {
        const bounds = localBounds(target.object);
        const center = target.object.localToWorld(bounds.getCenter(new T.Vector3()));
        wallFocus.current = {
          type: target.type,
          object: target.object,
          bounds,
          center,
          fov: viewFov,
        };
        described.current = wallFocus.current;
        setMode(target.type);
        live.current.onHint('');
        return;
      }
      if (target.type === 'case') {
        described.current = { object: target.object, bounds: localBounds(target.object) };
        caseView.current = {
          ...initialCaseView,
          center: target.object.getWorldPosition(new T.Vector3()),
        };
        setMode('case');
        live.current.onHint(local(live.current.environment.locale, target.english, target.label));
        return;
      }
      if (target.type === 'inspect' || target.type === 'remote') {
        const object = target.object;
        described.current = { object, bounds: localBounds(object) };
        const initial = new T.Quaternion().setFromEuler(
          new T.Euler(...(target.type === 'inspect' ? (target.pose ?? [0, 0, 0]) : [1.47, 0, 0])),
        );
        inspection.current = {
          target,
          home: savedPose(object),
          initial,
          rotation: initial.clone(),
          distance: 1,
        };
        shadowWarmup.current = 2;
        setMode(target.type, undefined, target.type === 'inspect' ? target.link?.url : undefined);
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
      model.setDrawer(-1);
      drawerFocus.current = null;
      pointer.current = null;
      setMode('returning');
      live.current.onHint('');
    }

    live.current.controls.current = {
      open: () => (mode.current === 'bench' ? moveToStation('room') : open(model.targets[0])),
    };

    function move(event: PointerEvent) {
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
      if (!canPick(mode.current) && mode.current !== 'inspect' && mode.current !== 'case') return;
      const drag = pointer.current;
      if (!drag) {
        if (canPick(mode.current)) {
          const target = pick(event.clientX, event.clientY);
          if (target || target !== hover.current) {
            hover.current = target;
            const locale = live.current.environment.locale;
            const text =
              target?.type === 'drawer' && mode.current === 'drawer'
                ? local(locale, 'Close drawer', '关闭抽屉')
                : target?.type === 'workbench' && mode.current === 'bench'
                  ? local(locale, 'Return to the computer desk', '回到电脑桌')
                  : target
                    ? local(locale, target.english, target.label)
                    : '';
            live.current.onHint(
              text,
              mode.current !== 'remote' ? { x: event.clientX, y: event.clientY } : undefined,
            );
          }
          element.style.cursor = target ? 'pointer' : isStation(mode.current) ? 'grab' : '';
        }
        return;
      }
      const dx = event.clientX - drag.x,
        dy = event.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < 5) return;
      drag.moved = true;
      if (isStation(mode.current)) {
        const look = mode.current === 'bench' ? benchLook.current : deskLook.current;
        look.yaw -= dx * 0.0035;
        look.pitch = T.MathUtils.clamp(look.pitch - dy * 0.0028, -1.19, 1.13);
        drag.x = event.clientX;
        drag.y = event.clientY;
        element.style.cursor = 'grabbing';
        live.current.onHint('');
      } else if (mode.current === 'inspect' && inspection.current) {
        const rect = element.getBoundingClientRect();
        const next = arcball(
          event.clientX,
          event.clientY,
          rect,
          Math.min(rect.width, rect.height) * 0.28,
        );
        inspection.current.rotation.setFromUnitVectors(drag.ball, next).multiply(drag.orientation);
      } else if (mode.current === 'case') {
        const look = caseView.current;
        look.azimuth = T.MathUtils.clamp(look.azimuth + dx * 0.003, 0.38, 0.99);
        look.elevation = T.MathUtils.clamp(look.elevation + dy * 0.002, 0.05, 0.4);
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
      if (
        event.button !== 0 ||
        (!canPick(mode.current) && mode.current !== 'inspect' && mode.current !== 'case')
      )
        return;
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
      element.style.cursor = ['room', 'bench', 'inspect', 'case'].includes(mode.current)
        ? 'grab'
        : '';
    }
    function cancel() {
      pointer.current = null;
      element.style.cursor = '';
    }
    function leave() {
      if (!pointer.current) {
        hover.current = undefined;
        if (canPick(mode.current) && mode.current !== 'remote') live.current.onHint('');
      }
    }
    function reset() {
      if (mode.current === 'inspect' && inspection.current)
        inspection.current.rotation.copy(inspection.current.initial);
      if (mode.current === 'case') Object.assign(caseView.current, initialCaseView);
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
      }
      if (mode.current === 'case') {
        const look = caseView.current;
        look.distance = T.MathUtils.clamp(look.distance + delta * 0.0012, 1.05, 1.55);
      }
      const current = mode.current;
      if (isStation(current))
        zoom.current[current] = T.MathUtils.clamp(zoom.current[current] + delta * 0.03, 32, 64);
      const wall = wallFocus.current;
      if (wall && (current === 'map' || current === 'board')) {
        wall.fov = T.MathUtils.clamp(wall.fov + delta * 0.03, 28, 64);
      }
    }
    function keyboard(event: KeyboardEvent) {
      if (
        !event.defaultPrevented &&
        isStation(mode.current) &&
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
        turning.current.add(event.code);
        hover.current = undefined;
        live.current.onHint('');
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
        if (live.current.screen.current) {
          live.current.screen.current.dataset.visible = 'false';
          live.current.screen.current.dataset.interactive = 'false';
        }
        if (mode.current === 'map' || mode.current === 'board') wallFocus.current = null;
        if (mode.current === 'window') windowFocus.current = false;
        windowApproach.current = null;
        pointer.current = null;
        setMode('returning');
        live.current.onHint('');
      }
      if (event.code === 'KeyE' && canPick(mode.current)) {
        const rect = element.getBoundingClientRect();
        const target = hover.current ?? pick(rect.x + rect.width / 2, rect.y + rect.height / 2);
        if (target || mode.current === 'room') {
          event.preventDefault();
          open(target ?? model.targets[0]);
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
        drawer: (index) => model.targets.find((t) => t.id === 'drawer-' + index)?.object.position.z,
        lightLevels: () => model.lightLevels(),
        async exportRoom(objectName) {
          const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
          const source = objectName ? model.root.getObjectByName(objectName) : model.root;
          if (!source) throw new Error('Unknown studio object: ' + objectName);
          const studio = source.clone();
          if (objectName) studio.position.set(0, 0, 0);
          const tracks: T.KeyframeTrack[] = [];
          studio.traverse((child) => {
            if (
              child instanceof T.InstancedMesh ||
              child instanceof T.Points ||
              child instanceof T.LineSegments
            )
              child.visible = false;
            if (
              child.name === panoramaMeshName &&
              child instanceof T.Mesh &&
              child.material instanceof T.ShaderMaterial
            ) {
              child.material = new T.MeshBasicMaterial({
                map: child.material.uniforms.photoA.value,
                side: T.DoubleSide,
              });
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
          const buffer = await new GLTFExporter().parseAsync(studio, {
            binary: true,
            maxTextureSize: 1024,
            onlyVisible: true,
            animations: tracks.length ? [new T.AnimationClip('Fan rotors', 3, tracks)] : [],
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
      scene.environment = null;
    };
  }, [camera, gl, model, scene]);

  useEffect(() => {
    shadowWarmup.current = 3;
  }, [props.environment]);

  useFrame(({ clock, size }, elapsed) => {
    const delta = Math.min(elapsed, 0.05);
    const { environment: env, screen, caption, onMode } = live.current;
    const load = loading.current;
    if (!load.complete && assets.total) {
      const ratio = assets.loaded / assets.total;
      if (ratio !== load.reported) {
        load.reported = ratio;
        live.current.onProgress(ratio);
      }
      if (ratio === 1 && ++load.frames >= 3) {
        load.complete = true;
        live.current.onReady();
      }
    }
    const current = mode.current;
    const cached = scratch.current;
    const ease = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 10.5);
    const reflectionLevel =
      (env.night ? 0.25 : 0.4) * (env.blinds ? 1 - (env.angle + 1) * 0.16 : 1);
    scene.environmentIntensity = T.MathUtils.lerp(
      scene.environmentIntensity,
      reflectionLevel,
      ease,
    );
    const fov = (viewFov * Math.PI) / 180;
    const aspect = size.width / size.height;
    const atBench = station.current === 'bench';
    const look = atBench ? benchLook.current : deskLook.current;
    if (isStation(current) && turning.current.size) {
      const keys = turning.current;
      const yawDelta = Number(keys.has('ArrowLeft')) - Number(keys.has('ArrowRight'));
      const pitchDelta = Number(keys.has('ArrowUp')) - Number(keys.has('ArrowDown'));
      look.yaw += yawDelta * delta * 1.65;
      look.pitch = T.MathUtils.clamp(look.pitch + pitchDelta * delta * 1.3, -1.19, 1.13);
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
    if (current === 'case') {
      const { azimuth, elevation, distance, center } = caseView.current;
      const radius = distance * Math.cos(elevation);
      cached.position
        .set(
          -radius * Math.sin(azimuth),
          distance * Math.sin(elevation),
          radius * Math.cos(azimuth),
        )
        .add(center);
      yaw = -azimuth;
      pitch = -elevation;
    }
    const wall = wallFocus.current;
    if (wall) {
      const { x: width, y: height } = wall.bounds.getSize(cached.local);
      const distance = Math.max(height, width / aspect) / (1.79 * Math.tan(fov / 2));
      cached.position.set(wall.center.x, wall.center.y - height * 0.027, wall.center.z + distance);
      yaw = 0;
      pitch = 0;
    }
    const lookingOutside = atWindow(current) || (current === 'returning' && windowFocus.current);
    if (lookingOutside) {
      const look = windowView.current;
      yaw = look.yaw;
      pitch = look.pitch;
      // Eyes travel a short arc around the neck as the visitor looks left or right.
      const turn = yaw - windowEye.yaw,
        tilt = pitch - windowEye.pitch;
      const eyeOffset = 0.075;
      cached.position.set(
        windowEye.x + eyeOffset * (1 - Math.cos(turn) * Math.cos(tilt)),
        windowEye.y + eyeOffset * Math.sin(tilt),
        windowEye.z + eyeOffset * Math.sin(turn) * Math.cos(tilt),
      );
    }
    const drawer = drawerFocus.current;
    if (drawer) {
      cached.position.copy(drawer.center).add(cached.local.set(0, 0.54, 0.27));
      yaw = 0;
      pitch = -Math.atan2(0.54, 0.27);
    }
    const targetFov = drawer
      ? 46
      : (wall?.fov ??
        (isStation(current) || current === 'returning' ? zoom.current[station.current] : viewFov));
    const nextFov =
      current === 'computer'
        ? T.MathUtils.lerp(computerStart.current.fov, viewFov, lean)
        : T.MathUtils.lerp(camera.fov, targetFov, ease);
    if (Math.abs(camera.fov - targetFov) > 0.001) {
      camera.fov = Math.abs(nextFov - targetFov) < 0.001 ? targetFov : nextFov;
      camera.updateProjectionMatrix();
    }
    const arriving = lookingOutside ? windowApproach.current : null;
    if (current === 'computer') {
      camera.position.lerpVectors(computerStart.current.position, cached.position, lean);
      camera.position.y += Math.sin(Math.PI * lean) * 0.032;
      camera.quaternion
        .copy(computerStart.current.quaternion)
        .slerp(cached.orientation.identity(), T.MathUtils.smootherstep(approach, 0, 0.86));
    } else if (arriving) {
      const step = env.reducedMotion
        ? 1
        : T.MathUtils.clamp((performance.now() - arriving.time) / 920, 0, 1);
      const travel = T.MathUtils.smootherstep(step, 0, 1);
      camera.position.lerpVectors(arriving.position, cached.position, travel);
      camera.position.y += Math.sin(Math.PI * travel) * 0.036;
      const turn = T.MathUtils.smootherstep(step, 0, 0.87);
      cached.orientation.setFromEuler(cached.euler.set(pitch, yaw, 0, 'YXZ'));
      camera.quaternion.copy(arriving.quaternion).slerp(cached.orientation, turn);
      if (step === 1) windowApproach.current = null;
    } else {
      camera.position.lerp(cached.position, ease);
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
    const fill = current === 'inspect' ? 0.16 : current === 'drawer' ? 0.1 : 0;
    inspectionFill.intensity = T.MathUtils.lerp(inspectionFill.intensity, fill, ease);
    if (inspectionFill.intensity > 0.001) {
      inspectionFill.position.copy(
        cached.local.set(-0.18, 0.19, -0.1).applyMatrix4(camera.matrixWorld),
      );
    }

    const moving = inspection.current;
    if (moving) {
      const object = moving.target.object;
      const parent = object.parent!;
      if (current === 'returning') {
        object.position.lerp(moving.home.position, ease);
        object.quaternion.slerp(moving.home.quaternion, ease);
        if (
          object.position.distanceToSquared(moving.home.position) < 1e-7 &&
          object.quaternion.angleTo(moving.home.quaternion) < 0.004
        ) {
          object.position.copy(moving.home.position);
          object.quaternion.copy(moving.home.quaternion);
          inspection.current = null;
        }
      } else {
        const isRemote = current === 'remote';
        const item = moving.target.type === 'inspect' ? moving.target : undefined;
        const width = item?.size ?? 0.13;
        const distance = isRemote
          ? 0.34
          : (item?.viewDistance ?? Math.max(0.26, width * 2.75)) * moving.distance;
        cached.local.set(
          isRemote ? distance * aspect * 0.29 : 0,
          isRemote ? -0.074 : width * 0.075,
          -distance,
        );
        camera.localToWorld(cached.local);
        parent.worldToLocal(cached.local);
        parent.getWorldQuaternion(cached.parent).invert();
        cached.rotation.copy(cached.parent).multiply(camera.quaternion).multiply(moving.rotation);
        object.position.lerp(cached.local, ease);
        object.quaternion.slerp(cached.rotation, ease);
      }
    }
    const link =
      current === 'inspect' && moving?.target.type === 'inspect' ? moving.target.link : undefined;
    const anchor = live.current.inspectionAnchor.current;
    if (anchor && link && moving) {
      const object = moving.target.object;
      const { left, right, top, bottom, z } = link.region;
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
        const matrix = screenProjection(cached.screenCorners, 250, 54);
        anchor.style.transform = matrix;
        anchor.style.visibility = matrix ? 'visible' : 'hidden';
      } else anchor.style.visibility = 'hidden';
    }
    if (described.current && caption.current) {
      const { object, bounds } = described.current;
      object.updateWorldMatrix(true, false);
      let bottom = -Infinity,
        left = Infinity,
        right = -Infinity;
      for (const x of [bounds.min.x, bounds.max.x]) {
        for (const y of [bounds.min.y, bounds.max.y])
          for (const z of [bounds.min.z, bounds.max.z]) {
            cached.local.set(x, y, z).applyMatrix4(object.matrixWorld).project(camera);
            bottom = Math.max(bottom, ((1 - cached.local.y) * size.height) / 2);
            const pixelX = ((1 + cached.local.x) * size.width) / 2;
            left = Math.min(left, pixelX);
            right = Math.max(right, pixelX);
          }
      }
      const halfWidth = Math.min(240, size.width * 0.31);
      caption.current.style.left =
        T.MathUtils.clamp((left + right) / 2, halfWidth, size.width - halfWidth) + 'px';
      const footer = wall && current !== 'inspect' ? 49 : 83;
      caption.current.style.top =
        T.MathUtils.clamp(bottom + 15, size.height * 0.18, size.height - footer) + 'px';
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
      (env.reducedMotion || performance.now() - animationStart.current > 430)
    ) {
      described.current = drawer ?? wall;
      mode.current = drawer
        ? 'drawer'
        : windowFocus.current
          ? 'window'
          : (wall?.type ?? station.current);
      onMode(mode.current);
    }
    const geometryMoving = model.update(
      env,
      delta,
      clock.elapsedTime,
      live.current.musicLevels(),
      camera.position,
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
      activate: (id: string) => void;
      project: (id: string) => { x: number; y: number } | null;
      camera: () => { position: number[]; rotation: number[]; fov: number };
      objectPose: (id: string) => { position: number[]; rotation: number[] } | undefined;
      drawer: (index: number) => number | undefined;
      lightLevels: () => { keyboard: number; mouse: number; speaker: number };
      exportRoom: (objectName?: string) => Promise<void>;
    };
  }
}

export default function StudioView(props: Props) {
  const mapMarker = useRef<SVGGElement>(null);
  // Keep camera projection and pointer coordinates in CSS pixels on software-rendered test runners.
  const e2e = import.meta.env.DEV && import.meta.env.VITE_STUDIO_E2E === '1';
  return (
    <>
      <Canvas
        className="studio-canvas"
        shadows={props.environment.quality === 'high'}
        dpr={e2e ? 0.5 : props.environment.quality === 'high' ? [1, 1.5] : 1}
        camera={{
          fov: viewFov,
          near: 0.028,
          far: waterfrontFarClip,
          position: [eye.x, eye.y, eye.defaultZ],
        }}
        gl={{ antialias: !e2e, powerPreference: 'high-performance', alpha: false }}
        onCreated={({ gl }) => {
          gl.toneMapping = T.AgXToneMapping;
          gl.toneMappingExposure = 1.04;
        }}
      >
        <CameraRig {...props} mapMarker={mapMarker} />
        <Finish
          enabled={props.environment.quality === 'high'}
          reducedMotion={props.environment.reducedMotion}
        />
      </Canvas>
      {props.showMinimap && props.mode !== 'computer' && (
        <Minimap
          marker={mapMarker}
          label={local(props.environment.locale, 'Studio minimap', '工作室小地图')}
        />
      )}
    </>
  );
}
