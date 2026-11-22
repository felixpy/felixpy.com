import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

type BatchMesh = T.Mesh<T.BufferGeometry, T.Material>;

function sequentialIndex(geometry: T.BufferGeometry) {
  const length = geometry.getAttribute('position').count;
  const sequential = length > 65535 ? new Uint32Array(length) : new Uint16Array(length);
  for (let i = 0; i < length; i++) sequential[i] = i;
  return new T.BufferAttribute(sequential, 1);
}

function mergeTransformed(batch: BatchMesh[], indexed: boolean) {
  const copies = batch.map((child) => {
    child.updateMatrix();
    const copy = child.geometry.clone();
    if (indexed && !copy.index) copy.setIndex(sequentialIndex(copy));
    return copy.applyMatrix4(child.matrix);
  });
  const geometry = mergeGeometries(copies);
  for (const copy of copies) copy.dispose();
  return geometry;
}

function transformMerged(batch: BatchMesh[], indexed: boolean) {
  const sources = batch.map(({ geometry }) => {
    if (!indexed || geometry.index) return geometry;
    const source = new T.BufferGeometry();
    source.attributes = geometry.attributes;
    source.setIndex(sequentialIndex(geometry));
    return source;
  });
  const geometry = mergeGeometries(sources);
  if (!geometry) return null;
  for (const child of batch) child.updateMatrix();
  const normalMatrix = new T.Matrix3();
  for (const name of ['position', 'normal', 'tangent']) {
    const attribute = geometry.getAttribute(name);
    if (!attribute) continue;
    let offset = 0;
    for (const child of batch) {
      const end = offset + child.geometry.getAttribute(name).array.length;
      const slice = new T.BufferAttribute(
        attribute.array.subarray(offset, end),
        attribute.itemSize,
        attribute.normalized,
      );
      if (name === 'position') slice.applyMatrix4(child.matrix);
      else if (name === 'normal')
        slice.applyNormalMatrix(normalMatrix.getNormalMatrix(child.matrix));
      else slice.transformDirection(child.matrix);
      offset = end;
    }
  }
  return geometry;
}

export function batchMeshes(root: T.Object3D, movable: ReadonlySet<T.Object3D>, mergeFirst = true) {
  const layouts = new WeakMap<T.BufferGeometry, string>();
  root.traverse((parent) => {
    const batches = new Map<string, BatchMesh[]>();
    for (const child of parent.children) {
      if (
        !(child instanceof T.Mesh) ||
        child instanceof T.InstancedMesh ||
        child instanceof T.SkinnedMesh ||
        movable.has(child) ||
        !child.visible ||
        child.onBeforeRender !== T.Object3D.prototype.onBeforeRender ||
        child.onAfterRender !== T.Object3D.prototype.onAfterRender ||
        Array.isArray(child.material) ||
        child.material.transparent ||
        child.children.length
      )
        continue;
      const geometry = child.geometry as T.BufferGeometry;
      if (Object.keys(geometry.morphAttributes).length || geometry.drawRange.count !== Infinity)
        continue;
      let layout = layouts.get(geometry);
      if (!layout) {
        layout = Object.entries(geometry.attributes)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([name, attr]) =>
            [name, attr.itemSize, attr.normalized, attr.array.constructor.name].join('/'),
          )
          .join(',');
        layouts.set(geometry, layout);
      }
      const key = [
        child.material.id,
        child.castShadow,
        child.receiveShadow,
        child.layers.mask,
        child.renderOrder,
        layout,
      ].join(':');
      const batch = batches.get(key) ?? [];
      batch.push(child);
      batches.set(key, batch);
    }
    for (const batch of batches.values()) {
      if (batch.length < 2) continue;
      const indexed = batch.some((child) => child.geometry.index !== null);
      const compatible =
        mergeFirst &&
        batch.every(({ geometry }) =>
          Object.values(geometry.attributes).every(
            (attribute) =>
              attribute instanceof T.BufferAttribute && attribute.array instanceof Float32Array,
          ),
        );
      const geometry = compatible
        ? transformMerged(batch, indexed)
        : mergeTransformed(batch, indexed);
      if (!geometry) continue;
      const first = batch[0];
      const mesh = new T.Mesh(geometry, first.material);
      mesh.matrixAutoUpdate = false;
      mesh.castShadow = first.castShadow;
      mesh.receiveShadow = first.receiveShadow;
      mesh.layers.mask = first.layers.mask;
      mesh.renderOrder = first.renderOrder;
      mesh.name = parent.name + ' · fixed surfaces';
      parent.remove(...batch);
      parent.add(mesh);
    }
  });
}
