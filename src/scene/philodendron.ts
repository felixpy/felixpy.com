import * as T from 'three';
import { cable, canvasTexture, group, mesh, random, surface, tube, type XYZ } from './geometry';
import type { Palette } from './materials';

function leafSkin() {
  return canvasTexture(192, 384, (ctx) => {
    const base = ctx.createLinearGradient(0, 0, 192, 340);
    base.addColorStop(0, '#758d58');
    base.addColorStop(0.43, '#bec8a1');
    base.addColorStop(0.55, '#acbb91');
    base.addColorStop(1, '#718254');
    ctx.fillStyle = base;
    ctx.fillRect(0, 0, 192, 384);
    const rng = random(618);
    for (let i = 0; i < 3700; i++) {
      ctx.fillStyle = i % 3 ? '#d2d89b0c' : '#344e3c0d';
      ctx.fillRect(rng() * 192, rng() * 384, 1 + rng() * 4, 1 + rng() * 4);
    }
    for (const side of [-1, 1]) {
      for (let n = 0; n < 11; n++) {
        const y = 42 + n * 28;
        ctx.beginPath();
        ctx.moveTo(96, y);
        ctx.bezierCurveTo(96 + 28 * side, y + 19, 96 + 48 * side, y + 22, 96 + 94 * side, y + 64);
        ctx.strokeStyle = n < 8 ? '#d5d9a460' : '#dedfaf43';
        ctx.lineWidth = 1.3;
        ctx.stroke();
      }
    }
    ctx.strokeStyle = '#d5dca5b0';
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.moveTo(96, 0);
    ctx.lineTo(96, 384);
    ctx.stroke();
  });
}

function heartleaf(length: number, halfWidth: number, bend: number) {
  const vertices: number[] = [],
    uvs: number[] = [],
    indices: number[] = [];
  const rows = 19,
    columns = 10;
  for (let row = 0; row <= rows; row++) {
    const v = row / rows;
    const width = Math.max(0.001, Math.sin(Math.PI * (0.22 + v * 0.78)) ** 0.83 * (1 - v * 0.4));
    for (let col = 0; col <= columns; col++) {
      const u = (col / columns) * 2 - 1;
      const lobe = Math.sin(Math.abs(u) * Math.PI) * Math.pow(1 - v, 6) * 0.24;
      vertices.push(
        u * halfWidth * width,
        -length * (v - lobe),
        length * (0.23 * Math.sin(Math.PI * v) - bend * v * v) +
          halfWidth * width * (0.18 * Math.abs(u) - 0.24 * u * u),
      );
      uvs.push(col / columns, 1 - v);
      if (row && col) {
        const i = row * (columns + 1) + col;
        indices.push(i - columns - 2, i - 1, i, i - columns - 2, i, i - columns - 1);
      }
    }
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.Float32BufferAttribute(vertices, 3));
  geo.setAttribute('uv', new T.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

export function philodendron(parent: T.Object3D, p: Palette, position: XYZ) {
  const plant = group(parent, 'Heartleaf philodendron in a wheel-thrown pot', position);
  const clay = p.plaster.clone();
  clay.color.set('#a46b52');
  clay.roughness = 0.93;
  const glazed = new T.MeshPhysicalMaterial({ color: '#a98e76', roughness: 0.41, clearcoat: 0.24 });
  const turned = (profile: number[][], material: T.Material) =>
    mesh(
      plant,
      new T.LatheGeometry(
        profile.map(([r, y]) => new T.Vector2(r, y)),
        48,
      ),
      material,
    );
  turned(
    [
      [0, 0],
      [0.048, 0],
      [0.059, 0.003],
      [0.061, 0.009],
      [0.061, 0.012],
      [0.058, 0.012],
      [0.055, 0.006],
      [0, 0.006],
    ],
    clay,
  );
  turned(
    [
      [0, 0.006],
      [0.04, 0.006],
      [0.044, 0.012],
      [0.052, 0.048],
      [0.058, 0.091],
      [0.055, 0.093],
      [0.05, 0.085],
      [0.04, 0.022],
      [0, 0.019],
    ],
    clay,
  );
  turned(
    [
      [0.056, 0.076],
      [0.0595, 0.077],
      [0.0608, 0.089],
      [0.059, 0.093],
      [0.055, 0.094],
      [0.053, 0.092],
    ],
    glazed,
  );
  const soil = surface('#342e24', 0.99);
  tube(plant, [0, 0.079, 0], [0, 0.083, 0], 0.052, soil);
  const rng = random(Math.round(Math.abs(position[0]) * 1547) + 27);
  const bark = surface('#78674f', 0.97);
  const stone = new T.DodecahedronGeometry(0.0024);
  for (let i = 0; i < 32; i++) {
    const a = rng() * Math.PI * 2,
      r = Math.sqrt(rng()) * 0.048;
    const chip = mesh(plant, stone, i % 5 ? soil : bark, [Math.cos(a) * r, 0.083, Math.sin(a) * r]);
    chip.scale.set(1.4 + rng(), 0.5 + rng(), 1);
  }
  const texture = leafSkin();
  const leaves = ['#75935c', '#648854', '#799757', '#83a762'].map(
    (color) =>
      new T.MeshStandardMaterial({ map: texture, color, roughness: 0.57, side: T.DoubleSide }),
  );
  const stems = surface('#607249', 0.73);
  const forms = [0, 1, 2, 3].map((i) =>
    heartleaf(0.086 + i * 0.008, 0.031 + i * 0.0018, 0.17 + i * 0.033),
  );
  for (let vine = 0; vine < 7; vine++) {
    const yaw = 2.4 * vine + 0.25 * rng();
    const direction = new T.Vector3(Math.cos(yaw), 0, Math.sin(yaw));
    const sideways = new T.Vector3(-direction.z, 0, direction.x);
    const droop = vine % 3 === 0;
    const point = (t: number) =>
      new T.Vector3(0, 0.082, 0)
        .addScaledVector(direction, (droop ? 0.147 : 0.072) * t)
        .addScaledVector(sideways, 0.013 * Math.sin(t * 5 + vine))
        .setY(
          0.082 +
            (droop
              ? 0.12 * Math.sin(t * 2.5) - 0.082 * t * t
              : 0.13 * t + 0.032 * Math.sin(t * 2.6)),
        );
    const path = Array.from({ length: 6 }, (_, j) => point(j / 5).toArray() as XYZ);
    cable(plant, path, 0.00155, stems);
    for (let node = 1; node <= 4; node++) {
      const t = node / 4,
        side = node % 2 ? -1 : 1;
      const joint = point(t);
      const end = joint
        .clone()
        .addScaledVector(sideways, side * (0.021 + 0.023 * rng()))
        .addScaledVector(direction, 0.014);
      end.y += 0.018 + 0.013 * rng();
      const mid = joint.clone().lerp(end, 0.63);
      mid.y += 0.004;
      cable(plant, [joint.toArray(), mid.toArray(), end.toArray()], 0.00105, stems);
      const n = (vine + node) % 4;
      const blade = mesh(plant, forms[n], leaves[n], end.toArray());
      blade.rotation.order = 'YXZ';
      blade.rotation.set(
        -0.66 - rng() * 0.65,
        Math.atan2(direction.x, direction.z) + side * 0.91,
        (rng() - 0.5) * 0.43,
      );
      blade.scale.setScalar(0.7 + 0.29 * rng());
    }
  }
  return { plant, leaves };
}
