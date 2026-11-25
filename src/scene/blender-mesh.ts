import * as T from 'three';
import { meshBytes } from './blender-library';

export function blenderMesh(name: string) {
  const geometry = decodeBlenderMesh(meshBytes(name));
  geometry.name = name;
  return geometry;
}

export function decodeBlenderMesh(buffer: ArrayBuffer) {
  const data = new DataView(buffer);
  if (data.getUint32(0, false) !== 0x424d5331) throw new Error('Unrecognized Blender mesh');
  const count = data.getUint32(4, true);
  const indexCount = data.getUint32(8, true);
  const indexOffset = 52 + count * 16;
  if (data.byteLength !== indexOffset + indexCount * 2) throw new Error('Incomplete Blender mesh');
  const [xMin, yMin, zMin, u, v] = new Float32Array(buffer, 12, 5);
  const [xSpan, ySpan, zSpan, width, height] = new Float32Array(buffer, 32, 5);
  const positions = new Float32Array(count * 3);
  const normals = new Int16Array(count * 3);
  const uv = new Float32Array(count * 2);
  const box = new T.Box3();
  const point = new T.Vector3();
  for (let i = 0; i < count; i++) {
    const offset = 52 + i * 16;
    positions[i * 3] = xMin + (xSpan * data.getUint16(offset, true)) / 65535;
    positions[i * 3 + 1] = yMin + (ySpan * data.getUint16(offset + 2, true)) / 65535;
    positions[i * 3 + 2] = zMin + (zSpan * data.getUint16(offset + 4, true)) / 65535;
    normals[i * 3] = data.getInt16(offset + 6, true);
    normals[i * 3 + 1] = data.getInt16(offset + 8, true);
    normals[i * 3 + 2] = data.getInt16(offset + 10, true);
    box.expandByPoint(point.fromArray(positions, i * 3));
  }
  if (![u, v, width, height].every((value) => Object.is(value, 0))) {
    for (let i = 0; i < count; i++) {
      const offset = 52 + i * 16;
      uv[i * 2] = u + (width * data.getUint16(offset + 12, true)) / 65535;
      uv[i * 2 + 1] = v + (height * data.getUint16(offset + 14, true)) / 65535;
    }
  }
  const center = box.getCenter(new T.Vector3());
  let radiusSquared = 0;
  for (let i = 0; i < positions.length; i += 3) {
    radiusSquared = Math.max(
      radiusSquared,
      center.distanceToSquared(point.fromArray(positions, i)),
    );
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new T.Int16BufferAttribute(normals, 3, true));
  geometry.setAttribute('uv', new T.BufferAttribute(uv, 2));
  geometry.setIndex(new T.BufferAttribute(new Uint16Array(buffer, indexOffset, indexCount), 1));
  geometry.boundingBox = box;
  geometry.boundingSphere = new T.Sphere(center, Math.sqrt(radiusSquared));
  return geometry;
}
