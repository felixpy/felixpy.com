import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import { BufferAttribute, BufferGeometry } from 'three';
import { decodeBlenderMesh } from '../src/scene/blender-mesh';

function verifyMesh(source: Buffer, name: string) {
  const geometry = decodeBlenderMesh(Uint8Array.from(source).buffer);
  const count = source.readUInt32LE(4);
  const minimum = Array.from({ length: 5 }, (_, i) => source.readFloatLE(12 + 4 * i));
  const span = Array.from({ length: 5 }, (_, i) => source.readFloatLE(32 + 4 * i));
  const positions = new Float32Array(count * 3);
  const normals = new Int16Array(count * 3);
  const uv = new Float32Array(count * 2);
  for (let i = 0; i < count; i++) {
    const offset = 52 + i * 16;
    for (let j = 0; j < 3; j++) {
      positions[i * 3 + j] = minimum[j] + (span[j] * source.readUInt16LE(offset + j * 2)) / 65535;
      normals[i * 3 + j] = source.readInt16LE(offset + 6 + j * 2);
    }
    for (let j = 0; j < 2; j++) {
      uv[i * 2 + j] =
        minimum[3 + j] + (span[3 + j] * source.readUInt16LE(offset + 12 + j * 2)) / 65535;
    }
  }
  const normalAttr = geometry.getAttribute('normal');
  expect(normalAttr.normalized, name + ' • normal normalized').toBe(true);
  expect(normalAttr.array, name + ' • normal Int16Array').toBeInstanceOf(Int16Array);
  for (const [key, array] of Object.entries({ position: positions, normal: normals, uv })) {
    const decoded = geometry.getAttribute(key).array;
    expect(
      Buffer.from(decoded.buffer, decoded.byteOffset, decoded.byteLength).equals(
        Buffer.from(array.buffer),
      ),
      name + ' • ' + key,
    ).toBe(true);
  }
  for (let i = 0; i < Math.min(count, 16); i++) {
    expect(normalAttr.getX(i), name + ' • normal.getX').toBeCloseTo(
      Math.max(normals[i * 3] / 32767, -1),
      6,
    );
    expect(normalAttr.getY(i), name + ' • normal.getY').toBeCloseTo(
      Math.max(normals[i * 3 + 1] / 32767, -1),
      6,
    );
    expect(normalAttr.getZ(i), name + ' • normal.getZ').toBeCloseTo(
      Math.max(normals[i * 3 + 2] / 32767, -1),
      6,
    );
  }
  const indices = geometry.getIndex()!.array;
  expect(
    Buffer.from(indices.buffer, indices.byteOffset, indices.byteLength).equals(
      source.subarray(52 + 16 * count),
    ),
    name + ' • indices',
  ).toBe(true);
  const reference = new BufferGeometry().setAttribute(
    'position',
    new BufferAttribute(positions, 3),
  );
  reference.computeBoundingBox();
  reference.computeBoundingSphere();
  expect(geometry.boundingBox, name + ' • box').toEqual(reference.boundingBox);
  expect(geometry.boundingSphere, name + ' • sphere').toEqual(reference.boundingSphere);
}

test('all Blender mesh attributes and spatial bounds agree with the packed data', () => {
  const root = 'public/media/models';
  const files = readdirSync(root, { recursive: true }).filter((path) => path.endsWith('.mesh'));
  expect(files.length).toBeGreaterThan(0);
  for (const name of files) verifyMesh(readFileSync(join(root, name)), name);
});

test('empty geometry, unused quantization endpoints and signed zero UVs retain their exact values', () => {
  const header = Buffer.alloc(52);
  header.write('BMS1');
  verifyMesh(header, 'empty');
  const mesh = Buffer.concat([header, Buffer.alloc(16 * 3 + 6)]);
  mesh.writeUInt32LE(3, 4);
  mesh.writeUInt32LE(3, 8);
  [1.001, -20.03, 0.002, -0, 0, 99.9, 0.01, 0.0701, -0, 0].forEach((v, i) =>
    mesh.writeFloatLE(v, 12 + i * 4),
  );
  for (let i = 0; i < 3; i++) {
    [1200, 22290, 65002].forEach((q, axis) =>
      mesh.writeUInt16LE(q - i * 517, 52 + i * 16 + axis * 2),
    );
    mesh.writeInt16LE(-32768 + i, 52 + i * 16 + 6);
    mesh.writeUInt16LE(i, 52 + 3 * 16 + i * 2);
  }
  verifyMesh(mesh, 'interior endpoints');
  mesh.writeFloatLE(1.25, 24);
  verifyMesh(mesh, 'constant nonzero UV');
});
