import { expect, test } from '@playwright/test';
import * as T from 'three';
import { batchMeshes } from '../src/scene/batching';

test('merging before transformation preserves indices, attributes and movable targets', () => {
  const root = new T.Group();
  const material = new T.MeshStandardMaterial();
  const indexed = new T.BoxGeometry(0.2, 0.3, 0.5);
  const expanded = indexed.toNonIndexed();
  for (const geometry of [indexed, expanded]) {
    const tangent = new Float32Array(geometry.getAttribute('position').count * 4);
    for (let i = 0; i < tangent.length; i += 4) tangent.set([1, 0, 1, -1], i);
    geometry.setAttribute('tangent', new T.BufferAttribute(tangent, 4));
  }
  const meshes = [new T.Mesh(indexed, material), new T.Mesh(expanded, material)];
  meshes[0].position.set(0.6, -0.1, 0.18);
  meshes[1].rotation.set(1.2, 0.7, -0.4);
  meshes[1].scale.set(0.4, 1.6, 0.7);
  const target = new T.Mesh(indexed, material);
  root.add(...meshes, target);
  const control = root.clone();
  const original = indexed.getAttribute('position').array.slice();

  batchMeshes(control, new Set([control.children[2]]), false);
  batchMeshes(root, new Set([target]));

  expect(root.children[0]).toBe(target);
  expect(root.children).toHaveLength(2);
  const actual = (root.children[1] as T.Mesh).geometry;
  const expected = (control.children[1] as T.Mesh).geometry;
  expect(actual.index?.array).toEqual(expected.index?.array);
  for (const name of ['position', 'normal', 'uv', 'tangent'])
    expect(actual.getAttribute(name).array).toEqual(expected.getAttribute(name).array);
  expect(indexed.getAttribute('position').array).toEqual(original);
});
