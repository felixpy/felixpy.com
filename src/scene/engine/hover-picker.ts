import * as T from 'three';
import type { Mode, Target } from '../interaction';
import { roomPicking } from '../room-picking';

type TargetProxy = {
  target: Target;
  bounds: T.Box3;
  matrixWorld: T.Matrix4;
  valid: boolean;
};

export type HoverPickerOptions = {
  element: HTMLElement;
  camera: T.PerspectiveCamera;
  pickRoots: T.Object3D[];
  targets: readonly Target[];
  byObject: ReadonlyMap<T.Object3D, Target>;
  canReach: (target: Target, mode: Mode, hardwareId: string) => boolean;
  getState: () => {
    mode: Mode;
    hardwareId: string;
    held?: T.Object3D;
    skipHover: boolean;
  };
  onHoverResult: (target: Target | undefined, point: { x: number; y: number }) => void;
  defer?: (work: () => void) => void;
};

function matricesEqual(a: T.Matrix4, b: T.Matrix4): boolean {
  const ae = a.elements;
  const be = b.elements;
  for (let i = 0; i < 16; i++) {
    if (ae[i] !== be[i]) return false;
  }
  return true;
}

function isObjectVisible(object: T.Object3D): boolean {
  for (let cur: T.Object3D | null = object; cur; cur = cur.parent) {
    if (!cur.visible) return false;
  }
  return true;
}

export function createHoverPicker(options: HoverPickerOptions) {
  const { element, camera, pickRoots, targets, byObject, canReach, getState, onHoverResult } =
    options;
  const picking = roomPicking(pickRoots, options.defer);
  const ray = new T.Raycaster();
  const ndc = new T.Vector2();
  const hitPoint = new T.Vector3();
  const boxCenter = new T.Vector3();
  const boxSize = new T.Vector3();

  const proxies: TargetProxy[] = targets.map((target) => ({
    target,
    bounds: new T.Box3(),
    matrixWorld: new T.Matrix4(),
    valid: false,
  }));

  let rafId = 0;
  let pendingPoint: { x: number; y: number } | null = null;
  let disposed = false;

  function invalidate() {
    for (let i = 0; i < proxies.length; i++) {
      proxies[i].valid = false;
    }
  }

  function ensureProxyBounds(proxy: TargetProxy): boolean {
    const object = proxy.target.object;
    if (!proxy.valid || !matricesEqual(proxy.matrixWorld, object.matrixWorld)) {
      proxy.matrixWorld.copy(object.matrixWorld);
      proxy.bounds.setFromObject(object, false);
      proxy.valid = !proxy.bounds.isEmpty();
    }
    return proxy.valid;
  }

  function prefilterTargets(
    mode: Mode,
    hardwareId: string,
    held?: T.Object3D,
  ): { any: boolean; maxDistance: number } {
    let any = false;
    let maxDistance = 0;
    const origin = ray.ray.origin;
    for (let i = 0; i < proxies.length; i++) {
      const proxy = proxies[i];
      const { target } = proxy;
      if (target.object === held || !canReach(target, mode, hardwareId)) continue;
      if (!isObjectVisible(target.object)) continue;
      if (!ensureProxyBounds(proxy)) continue;
      if (proxy.bounds.containsPoint(origin) || ray.ray.intersectBox(proxy.bounds, hitPoint)) {
        any = true;
        proxy.bounds.getCenter(boxCenter);
        proxy.bounds.getSize(boxSize);
        const farBound = origin.distanceTo(boxCenter) + 0.5 * boxSize.length();
        if (farBound > maxDistance) maxDistance = farBound;
      }
    }
    return { any, maxDistance };
  }

  function pickAt(clientX: number, clientY: number): Target | undefined {
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) return undefined;
    ndc.set(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      ((rect.top - clientY) / rect.height) * 2 + 1,
    );
    ray.setFromCamera(ndc, camera);
    const { mode, hardwareId, held } = getState();
    const candidates = prefilterTargets(mode, hardwareId, held);
    if (!held && !candidates.any) return undefined;
    ray.far = held ? Infinity : Math.max(0.1, candidates.maxDistance + 0.05);
    let current: T.Object3D | null = picking.closest(ray, held) ?? null;
    ray.far = Infinity;
    while (current) {
      if (current === held) return undefined;
      const target = byObject.get(current);
      if (target && canReach(target, mode, hardwareId)) return target;
      current = current.parent;
    }
    return undefined;
  }

  function flushHover() {
    rafId = 0;
    if (disposed || !pendingPoint) return;
    const point = pendingPoint;
    pendingPoint = null;
    if (getState().skipHover) return;
    const target = pickAt(point.x, point.y);
    onHoverResult(target, point);
  }

  function scheduleHover(clientX: number, clientY: number) {
    if (disposed) return;
    pendingPoint = { x: clientX, y: clientY };
    if (!rafId) {
      rafId = window.requestAnimationFrame(flushHover);
    }
  }

  function cancelHover() {
    pendingPoint = null;
    if (rafId) {
      window.cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }

  function dispose() {
    disposed = true;
    cancelHover();
    picking.dispose();
  }

  return {
    pickAt,
    scheduleHover,
    cancelHover,
    invalidate,
    dispose,
  };
}

export type HoverPicker = ReturnType<typeof createHoverPicker>;
