import * as T from 'three';
import { viewFov } from './camera';
import type { HardwareOrbit, WallView } from './interaction';
import { workshopLayout } from './layout';

export type Pose = { position: T.Vector3; quaternion: T.Quaternion };

type FramedObject = { object: T.Object3D; bounds: T.Box3 };
export type WallFocus = FramedObject & {
  type: WallView;
  center: T.Vector3;
  fov: number;
  panY: number;
};

export function frameWallSurface(wall: WallFocus, aspect: number, position: T.Vector3) {
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

export const savedPose = (obj: T.Object3D): Pose => ({
  position: obj.position.clone(),
  quaternion: obj.quaternion.clone(),
});

export const towerOrbit: HardwareOrbit = {
  center: [0, 0.005, -0.024],
  azimuth: [1.05, -Math.PI / 2, 1.52],
  elevation: [0.24, 0.045, 0.52],
  distance: [1.03, 0.34, 1.55],
};
export function initialOrbit(orbit: HardwareOrbit) {
  return {
    orbit,
    azimuth: orbit.azimuth[0],
    elevation: orbit.elevation[0],
    distance: orbit.distance[0],
  };
}
export function towerRadius(radius: number, azimuth: number, centerX: number, rearOffset = 0) {
  const side = -Math.sin(azimuth);
  const front = Math.cos(azimuth);
  const clearSide = 0.17 / Math.max(Math.abs(side), 0.001);
  const clearFront = (0.39 + rearOffset) / Math.max(front, 0.001);
  const clearWorkbench = (workshopLayout.x - 0.38 - centerX) / Math.max(side, 0.001);
  return T.MathUtils.clamp(radius, Math.min(clearSide, clearFront), clearWorkbench);
}
export function frameHardware(
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

export function localBounds(object: T.Object3D) {
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
