import * as T from 'three';
import { mesh } from './geometry';

export function pictureFrame(
  parent: T.Object3D,
  width: number,
  height: number,
  rail: number,
  depth: number,
  z: number,
  finish: T.Material,
) {
  const corners = [
    [-1, -1],
    [1, -1],
    [1, 1],
    [-1, 1],
  ];
  const section = [
    [0, -depth],
    [0, -0.001],
    [0.001, 0],
    [rail * 0.43, 0],
    [rail * 0.67, -0.001],
    [rail, -depth * 0.35],
    [rail, -depth],
    [0, -depth],
  ];
  for (let side = 0; side < 4; side++) {
    const positions: number[] = [],
      uvs: number[] = [],
      indices: number[] = [];
    for (let k = 0; k < section.length; k++) {
      const [inset, front] = section[k];
      for (const end of [0, 1]) {
        const [sx, sy] = corners[(side + end) % 4];
        positions.push(sx * (width / 2 - inset), sy * (height / 2 - inset), z + front);
        uvs.push(end, (k / section.length) * 0.12);
      }
      if (k) {
        const a = (k - 1) * 2;
        indices.push(a, a + 1, a + 2, a + 2, a + 1, a + 3);
      }
    }
    const geometry = new T.BufferGeometry();
    geometry.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('uv', new T.Float32BufferAttribute(uvs, 2));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    mesh(parent, geometry, finish);
  }
}
