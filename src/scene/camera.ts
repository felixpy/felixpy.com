import * as T from 'three';
import { display } from './hardware';
import { workshopLayout } from './furniture';

export const eye = { x: display.x, y: 1.24, defaultZ: 1.96 };
export const windowEye = { x: 0.17, y: 1.58, z: 0.585, yaw: Math.PI / 2, pitch: -0.051 };
export const benchEye = { x: 1.15, y: 1.25, z: workshopLayout.z, yaw: -Math.PI / 2, pitch: -0.19 };
export const viewFov = 50;

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
