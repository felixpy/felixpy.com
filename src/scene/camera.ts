import * as T from 'three';
import { display, workshopLayout } from './layout';

const roomStation = { y: 1.36, z: 1.49 };
export const eye = {
  x: display.x,
  y: roomStation.y,
  defaultZ: roomStation.z,
  yaw: 0,
  pitch: Math.atan2(display.y - roomStation.y, roomStation.z - display.z),
};
export const roomFov = 63;
export const windowEye = { x: 0.06, y: 1.5, z: 0.585, yaw: Math.PI / 2, pitch: 0.075 };
export const benchEye = { x: 1.02, y: 1.25, z: workshopLayout.z, yaw: -Math.PI / 2, pitch: -0.15 };
export const viewFov = 50;
export const gearEye = { yaw: Math.PI, pitch: -0.028, fov: 50 };

export function frameGearWall(rack: T.Object3D, aspect: number, position: T.Vector3) {
  const halfAngle = T.MathUtils.degToRad(gearEye.fov / 2);
  const distance = Math.max(1.83, 1.5 / aspect) / (2 * Math.tan(halfAngle));
  return rack.localToWorld(
    position.set(0.16, 1.29 - distance * Math.tan(gearEye.pitch), 0.12 + distance),
  );
}

export function arcball(x: number, y: number, rect: DOMRect, radius: number) {
  const px = (x - rect.left - rect.width / 2) / radius;
  const py = (rect.top + rect.height / 2 - y) / radius;
  const squared = px * px + py * py;
  return new T.Vector3(
    px,
    py,
    squared <= 0.5 ? Math.sqrt(1 - squared) : 0.5 / Math.sqrt(squared),
  ).normalize();
}
