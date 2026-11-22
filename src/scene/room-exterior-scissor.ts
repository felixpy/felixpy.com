import { Matrix4, PerspectiveCamera, Vector3, Vector4, type Camera } from 'three';
import { roomDoor, roomSize, windowOpening } from './layout';

const margin = 0.04;
const { wall, y0, y1, z0, z1 } = windowOpening;
const doorLeft = roomDoor.center - roomDoor.halfWidth;
const doorRight = roomDoor.center + roomDoor.halfWidth;
const portals = [
  [
    new Vector4(wall, y0 - margin, z0 - margin, 1),
    new Vector4(wall, y0 - margin, z1 + margin, 1),
    new Vector4(wall, y1 + margin, z1 + margin, 1),
    new Vector4(wall, y1 + margin, z0 - margin, 1),
  ],
  [
    new Vector4(doorLeft - margin, -margin, roomSize.south, 1),
    new Vector4(doorRight + margin, -margin, roomSize.south, 1),
    new Vector4(doorRight + margin, roomDoor.height + margin, roomSize.south, 1),
    new Vector4(doorLeft - margin, roomDoor.height + margin, roomSize.south, 1),
  ],
];

const clipPlanes = [
  new Vector4(0, 0, 1, 1),
  new Vector4(0, 0, -1, 1),
  new Vector4(1, 0, 0, 1),
  new Vector4(-1, 0, 0, 1),
  new Vector4(0, 1, 0, 1),
  new Vector4(0, -1, 0, 1),
];

export function roomExteriorScissor() {
  const eye = new Vector3();
  const viewProjection = new Matrix4();
  const corners = Array.from({ length: 12 }, () => new Vector4());
  const clipped = Array.from({ length: 12 }, () => new Vector4());

  return (camera: Camera, width: number, height: number, result: Vector4) => {
    if (!(camera instanceof PerspectiveCamera) || camera.view?.enabled || width <= 0 || height <= 0)
      return false;
    const projection = camera.projectionMatrix.elements;
    if (projection[8] !== 0 || projection[9] !== 0 || projection[11] !== -1) return false;
    eye.setFromMatrixPosition(camera.matrixWorld);
    const nearRadius =
      camera.near *
      Math.hypot(1, 1 / projection[0], 1 / projection[5]) *
      camera.matrixWorld.getMaxScaleOnAxis();
    const edge = Math.max(margin, nearRadius + 0.005);
    if (
      eye.x <= roomSize.west + edge ||
      eye.x >= roomSize.east - edge ||
      eye.y <= edge ||
      eye.y >= roomSize.ceiling - edge ||
      eye.z <= roomSize.north + edge ||
      eye.z >= roomSize.south - edge
    )
      return false;

    viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    let left = Infinity,
      right = -Infinity,
      bottom = Infinity,
      top = -Infinity;
    for (const portal of portals) {
      let current = corners;
      let next = clipped;
      let count = portal.length;
      for (let i = 0; i < count; i++) current[i].copy(portal[i]).applyMatrix4(viewProjection);

      for (const plane of clipPlanes) {
        if (!count) break;
        let end = 0;
        let previous = current[count - 1];
        let previousDistance = plane.dot(previous);
        for (let i = 0; i < count; i++) {
          const vertex = current[i];
          const distance = plane.dot(vertex);
          if (distance >= 0 !== previousDistance >= 0) {
            next[end++].lerpVectors(
              previous,
              vertex,
              previousDistance / (previousDistance - distance),
            );
          }
          if (distance >= 0) next[end++].copy(vertex);
          previous = vertex;
          previousDistance = distance;
        }
        const swap = current;
        current = next;
        next = swap;
        count = end;
      }

      for (let i = 0; i < count; i++) {
        const point = current[i];
        if (point.w <= 0) return false;
        const x = ((point.x / point.w) * 0.5 + 0.5) * width;
        const y = ((point.y / point.w) * 0.5 + 0.5) * height;
        left = Math.min(left, x);
        right = Math.max(right, x);
        bottom = Math.min(bottom, y);
        top = Math.max(top, y);
      }
    }

    if (left === Infinity) {
      result.set(0, 0, 0, 0);
    } else {
      const x = Math.max(0, Math.floor(left - 1));
      const y = Math.max(0, Math.floor(bottom - 1));
      result.set(
        x,
        y,
        Math.min(width, Math.ceil(right + 1)) - x,
        Math.min(height, Math.ceil(top + 1)) - y,
      );
    }
    return true;
  };
}
