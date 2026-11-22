import * as T from 'three';
import { mesh, random } from './geometry';
import type { Palette } from './materials';

type FloorBounds = { west: number; east: number; north: number; south: number };
type Vertex = { x: number; z: number; u: number; v: number };
export const parquetSurfaceY = 0.0045;

function clip(polygon: Vertex[], axis: 'x' | 'z', edge: number, direction: number) {
  const clipped: Vertex[] = [];
  for (let index = 0; index < polygon.length; index++) {
    const a = polygon[index];
    const b = polygon[(index + 1) % polygon.length];
    const inside = direction * (a[axis] - edge) >= 0;
    if (inside) clipped.push(a);
    if (inside === direction * (b[axis] - edge) >= 0) continue;
    const t = (edge - a[axis]) / (b[axis] - a[axis]);
    clipped.push({
      x: T.MathUtils.lerp(a.x, b.x, t),
      z: T.MathUtils.lerp(a.z, b.z, t),
      u: T.MathUtils.lerp(a.u, b.u, t),
      v: T.MathUtils.lerp(a.v, b.v, t),
    });
  }
  return clipped;
}

export function parquet(parent: T.Group, p: Palette, bounds: FloorBounds) {
  const { west, east, north, south } = bounds;
  const length = 0.49;
  const width = 0.07;
  const gap = 0.0008;
  const positions: number[] = [];
  const uv: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const rng = random(457);
  const centerX = (east + west) / 2;
  const centerZ = (south + north) / 2;
  const runs = Math.ceil((east - west) / (2 * length * Math.SQRT2)) + 1;
  const rows = Math.ceil((south - north) / (2 * width * Math.SQRT2)) + 9;
  for (let run = -runs; run <= runs; run++) {
    for (let row = -rows; row <= rows; row++) {
      for (const crossed of [false, true]) {
        const startX = run * length + row * width + (crossed ? length + width : 0);
        const startZ = run * length - row * width;
        const scanU = rng();
        const scanV = rng();
        const tone = 0.76 + rng() * 0.23;
        let polygon = [
          [0, 0],
          [0, 1],
          [1, 1],
          [1, 0],
        ].map(([u, v]) => {
          const along = gap + u * (length - 2 * gap);
          const across = gap + v * (width - 2 * gap);
          const x = startX + (crossed ? -across : along);
          const z = startZ + (crossed ? along : across);
          return {
            x: centerX + (x + z) * Math.SQRT1_2,
            z: centerZ + (z - x) * Math.SQRT1_2,
            u: scanU + u * length,
            v: scanV + v * width,
          };
        });
        polygon = clip(clip(polygon, 'x', west, 1), 'x', east, -1);
        polygon = clip(clip(polygon, 'z', north, 1), 'z', south, -1);
        if (polygon.length < 3) continue;
        const first = positions.length / 3;
        for (const vertex of polygon) {
          positions.push(vertex.x, parquetSurfaceY, vertex.z);
          uv.push(vertex.u, vertex.v);
          colors.push(tone, tone, tone);
        }
        for (let i = 2; i < polygon.length; i++) indices.push(first, first + i - 1, first + i);
        for (let i = 0; i < polygon.length; i++) {
          const a = polygon[i],
            b = polygon[(i + 1) % polygon.length];
          const dx = b.x - a.x,
            dz = b.z - a.z;
          const distance = Math.hypot(dx, dz);
          if (distance < 0.0001) continue;
          const offsetX = (-dz * 0.00055) / distance,
            offsetZ = (dx * 0.00055) / distance;
          const bevel = positions.length / 3;
          for (const [point, lower] of [
            [a, false],
            [b, false],
            [a, true],
            [b, true],
          ] as const) {
            positions.push(
              T.MathUtils.clamp(point.x + (lower ? offsetX : 0), west, east),
              lower ? parquetSurfaceY - 0.0005 : parquetSurfaceY,
              T.MathUtils.clamp(point.z + (lower ? offsetZ : 0), north, south),
            );
            uv.push(point.u, point.v);
            colors.push(tone, tone, tone);
          }
          indices.push(bevel + 1, bevel, bevel + 2, bevel + 1, bevel + 2, bevel + 3);
        }
      }
    }
  }
  const geometry = new T.BufferGeometry()
    .setAttribute('position', new T.Float32BufferAttribute(positions, 3))
    .setAttribute('uv', new T.Float32BufferAttribute(uv, 2))
    .setAttribute('color', new T.Float32BufferAttribute(colors, 3))
    .setIndex(indices);
  geometry.computeVertexNormals();
  p.floor.vertexColors = true;
  const floor = mesh(parent, geometry, p.floor);
  floor.name = 'Oiled herringbone parquet';
  floor.castShadow = false;
}
