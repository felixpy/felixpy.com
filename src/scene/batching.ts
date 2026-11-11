import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// Batch fixed parts inside each assembly. Keep object boundaries, hinges and rotors
// in the scene graph so the same nodes still serve picking and offline review.
export function batchMeshes(root: T.Object3D, movable: ReadonlySet<T.Object3D>) {
  root.traverse((parent) => {
    const batches = new Map<string, T.Mesh<T.BufferGeometry, T.Material>[]>();
    for (const child of parent.children) {
      if (
        !(child instanceof T.Mesh) ||
        child instanceof T.InstancedMesh ||
        movable.has(child) ||
        Array.isArray(child.material) ||
        child.material.transparent ||
        child.children.length
      )
        continue;
      const geometry = child.geometry as T.BufferGeometry;
      const key = [
        child.material.id,
        child.castShadow,
        child.receiveShadow,
        Object.keys(geometry.attributes).sort().join('/'),
      ].join(':');
      const batch = batches.get(key) ?? [];
      batch.push(child);
      batches.set(key, batch);
    }
    for (const batch of batches.values()) {
      if (batch.length < 4) continue;
      const parts = batch.map((child) => {
        child.updateMatrix();
        const copy = child.geometry.index ? child.geometry.toNonIndexed() : child.geometry.clone();
        return copy.applyMatrix4(child.matrix);
      });
      const geometry = mergeGeometries(parts);
      for (const part of parts) part.dispose();
      if (!geometry) continue;
      const first = batch[0];
      const mesh = new T.Mesh(geometry, first.material);
      mesh.castShadow = first.castShadow;
      mesh.receiveShadow = first.receiveShadow;
      mesh.name = parent.name + ' · fixed surfaces';
      parent.remove(...batch);
      parent.add(mesh);
    }
  });
}
