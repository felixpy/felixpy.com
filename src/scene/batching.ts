import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export function batchMeshes(root: T.Object3D, movable: ReadonlySet<T.Object3D>) {
  const layouts = new WeakMap<T.BufferGeometry, string>();
  root.traverse((parent) => {
    const batches = new Map<string, T.Mesh<T.BufferGeometry, T.Material>[]>();
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
      const parts = batch.map((child) => {
        child.updateMatrix();
        const copy = child.geometry.clone();
        if (indexed && !copy.index) {
          const length = copy.getAttribute('position').count;
          const sequential = length > 65535 ? new Uint32Array(length) : new Uint16Array(length);
          for (let i = 0; i < length; i++) sequential[i] = i;
          copy.setIndex(new T.BufferAttribute(sequential, 1));
        }
        return copy.applyMatrix4(child.matrix);
      });
      const geometry = mergeGeometries(parts);
      for (const part of parts) part.dispose();
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
