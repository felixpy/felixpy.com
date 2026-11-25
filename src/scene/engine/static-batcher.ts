import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export type StaticBatchOptions = {
  /** Subtrees that animate or dynamically load/evict and must not be merged or frozen. */
  skipSubtrees?: ReadonlySet<T.Object3D>;
  /**
   * Scope boundaries (e.g. interactive picking targets). Meshes inside a target never merge
   * across its boundary into ancestors or sibling targets, preserving picking and bounds.
   */
  targetRoots?: ReadonlySet<T.Object3D>;
  /**
   * Nodes whose own transform can move (e.g. inspectable props picked up by the camera).
   * Their own `matrixAutoUpdate` remains `true`, while static children inside them can still
   * be merged and frozen.
   */
  movableRoots?: ReadonlySet<T.Object3D>;
  /** Skip merging a specific geometry (e.g. geometries matched by `room-lod.gz`). */
  skipGeometry?: (geometry: T.BufferGeometry, mesh: T.Mesh) => boolean;
  /** Skip merging a specific mesh. */
  skipMesh?: (mesh: T.Mesh) => boolean;
  /** Preserve named meshes without merging them into another batch. */
  preserveNames?: ReadonlySet<string>;
  /** Freeze `matrixAutoUpdate = false` on static leaf meshes and static groups. Defaults to true. */
  freezeStaticMatrices?: boolean;
};

export type StaticBatchStats = {
  mergedMeshes: number;
  batchesCreated: number;
  drawsSaved: number;
  skippedLod: number;
  frozenNodes: number;
};

export type RoomBatchModel = {
  interior: T.Object3D;
  targets: readonly {
    id: string;
    type: string;
    object: T.Object3D;
    onInspect?: unknown;
  }[];
  byObject: ReadonlyMap<T.Object3D, unknown>;
};

export type RoomDetailMatcher = {
  hasLodGeometry: (geometry: T.BufferGeometry) => boolean;
  isLoaded: () => boolean;
};

type BatchCandidate = {
  mesh: T.Mesh<T.BufferGeometry, T.Material>;
  relMatrix: T.Matrix4;
};

const DYNAMIC_TARGET_TYPES = new Set(['door', 'drawer', 'cabinet', 'key', 'remote']);
const DYNAMIC_TARGET_IDS = new Set(['filament-printer']);
const DYNAMIC_SUBTREE_NAMES = new Set(['Recessed window', 'Outdoor volume']);
const PRESERVED_MESH_NAMES = new Set([
  'screenbar-halo-2 • lens',
  'Louis Poulsen AJ Floor · polished stainless steel · lining',
  'LG OLED active pixels and clock',
]);

// Minimum vertex count present in `room-lod.gz` is 312; use 300 as a conservative
// fallback if `room-lod.gz` has not been loaded yet (e.g. on `high` quality before toggle).
const UNLOADED_LOD_MIN_VERTICES = 300;

function isDynamicNode(node: T.Object3D, skipSubtrees?: ReadonlySet<T.Object3D>): boolean {
  if (skipSubtrees?.has(node)) return true;
  if (
    node instanceof T.Light ||
    node instanceof T.Camera ||
    node instanceof T.Points ||
    node instanceof T.Line ||
    node instanceof T.LineSegments
  )
    return true;
  if (
    DYNAMIC_SUBTREE_NAMES.has(node.name) ||
    node.name === 'Fan rotor' ||
    node.name.startsWith('Fan rotor ')
  )
    return true;
  if (
    node.userData.studioWarmable === true ||
    node.userData.studioDynamic === true ||
    node.userData.installedHidden === true ||
    node.userData.inspectionDetail === true
  )
    return true;
  return false;
}

function sequentialIndex(geometry: T.BufferGeometry): T.BufferAttribute {
  const length = geometry.getAttribute('position').count;
  const array = length > 65535 ? new Uint32Array(length) : new Uint16Array(length);
  for (let i = 0; i < length; i++) array[i] = i;
  return new T.BufferAttribute(array, 1);
}

function toFloat32Attribute(
  attribute: T.BufferAttribute | T.InterleavedBufferAttribute,
): T.Float32BufferAttribute {
  const count = attribute.count;
  const itemSize = attribute.itemSize;
  const out = new Float32Array(count * itemSize);
  for (let i = 0; i < count; i++) {
    const base = i * itemSize;
    out[base] = attribute.getX(i);
    if (itemSize > 1) out[base + 1] = attribute.getY(i);
    if (itemSize > 2) out[base + 2] = attribute.getZ(i);
    if (itemSize > 3) out[base + 3] = attribute.getW(i);
  }
  return new T.Float32BufferAttribute(out, itemSize);
}

function normalizedLayout(geometry: T.BufferGeometry): string {
  return Object.entries(geometry.attributes)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, attr]) => {
      const floatUpgraded =
        name === 'position' ||
        name === 'normal' ||
        name === 'tangent' ||
        attr instanceof T.InterleavedBufferAttribute;
      const ctor = floatUpgraded ? 'Float32Array' : attr.array.constructor.name;
      const norm = floatUpgraded ? false : attr.normalized;
      return `${name}/${attr.itemSize}/${norm}/${ctor}`;
    })
    .join(',');
}

function cloneAndTransform(geometry: T.BufferGeometry, matrix: T.Matrix4, indexed: boolean) {
  const copy = new T.BufferGeometry();
  for (const [name, attr] of Object.entries(geometry.attributes)) {
    if (
      attr instanceof T.InterleavedBufferAttribute ||
      ((name === 'position' || name === 'normal' || name === 'tangent') &&
        !(attr.array instanceof Float32Array))
    ) {
      copy.setAttribute(name, toFloat32Attribute(attr));
    } else {
      copy.setAttribute(name, attr.clone());
    }
  }
  if (geometry.index) {
    copy.setIndex(geometry.index.clone());
  } else if (indexed) {
    copy.setIndex(sequentialIndex(copy));
  }
  copy.applyMatrix4(matrix);
  return copy;
}

function mergeCandidates(candidates: BatchCandidate[]): T.BufferGeometry | null {
  const indexed = candidates.some(({ mesh }) => mesh.geometry.index !== null);
  const copies = candidates.map(({ mesh, relMatrix }) =>
    cloneAndTransform(mesh.geometry, relMatrix, indexed),
  );
  const merged = mergeGeometries(copies, false);
  for (const copy of copies) copy.dispose();
  if (!merged) return null;
  merged.computeBoundingBox();
  merged.computeBoundingSphere();
  return merged;
}

export function batchStaticSubtree(
  root: T.Object3D,
  options: StaticBatchOptions = {},
): StaticBatchStats {
  const stats: StaticBatchStats = {
    mergedMeshes: 0,
    batchesCreated: 0,
    drawsSaved: 0,
    skippedLod: 0,
    frozenNodes: 0,
  };
  const {
    skipSubtrees,
    targetRoots,
    movableRoots,
    skipGeometry,
    skipMesh,
    preserveNames,
    freezeStaticMatrices = true,
  } = options;

  root.updateMatrixWorld(true);
  const layouts = new WeakMap<T.BufferGeometry, string>();

  function getLayout(geometry: T.BufferGeometry): string {
    let layout = layouts.get(geometry);
    if (!layout) {
      layout = normalizedLayout(geometry);
      layouts.set(geometry, layout);
    }
    return layout;
  }

  function isEligibleMesh(mesh: T.Mesh): mesh is T.Mesh<T.BufferGeometry, T.Material> {
    if (
      mesh instanceof T.InstancedMesh ||
      mesh instanceof T.SkinnedMesh ||
      !mesh.visible ||
      mesh.children.length > 0 ||
      mesh.onBeforeRender !== T.Object3D.prototype.onBeforeRender ||
      mesh.onAfterRender !== T.Object3D.prototype.onAfterRender ||
      mesh.raycast !== T.Mesh.prototype.raycast ||
      Array.isArray(mesh.material) ||
      mesh.material.transparent ||
      !mesh.material.visible ||
      mesh.userData.studioNoBatch === true ||
      mesh.userData.studioBatched === true ||
      (preserveNames && mesh.name !== '' && preserveNames.has(mesh.name))
    )
      return false;

    const geometry = mesh.geometry as T.BufferGeometry;
    if (
      !geometry ||
      Object.keys(geometry.morphAttributes).length > 0 ||
      geometry.drawRange.count !== Infinity ||
      !geometry.getAttribute('position')?.count
    )
      return false;

    if (skipMesh?.(mesh)) return false;
    if (skipGeometry?.(geometry, mesh)) {
      stats.skippedLod++;
      return false;
    }
    return true;
  }

  function processScope(scopeRoot: T.Object3D, isRootScope: boolean) {
    if (!scopeRoot.visible || isDynamicNode(scopeRoot, skipSubtrees)) return;

    const invScopeWorld = scopeRoot.matrixWorld.clone().invert();
    const batches = new Map<string, BatchCandidate[]>();
    const childScopes: T.Object3D[] = [];

    function collect(parent: T.Object3D) {
      const children = parent.children;
      for (let i = 0; i < children.length; i++) {
        const child = children[i];
        if (!child.visible || isDynamicNode(child, skipSubtrees)) continue;

        const isScopeBoundary =
          targetRoots?.has(child) ||
          child.userData.studioZone !== undefined ||
          (isRootScope && child instanceof T.Group && parent === scopeRoot && child.name !== '');

        if (isScopeBoundary) {
          childScopes.push(child);
          continue;
        }

        if (child instanceof T.Mesh) {
          if (isEligibleMesh(child)) {
            const relMatrix = new T.Matrix4().multiplyMatrices(invScopeWorld, child.matrixWorld);
            // Skip mirrored negative-determinant transforms to avoid flipping triangle winding.
            if (relMatrix.determinant() < 0) continue;
            const key = [
              child.material.id,
              child.castShadow,
              child.receiveShadow,
              child.layers.mask,
              child.renderOrder,
              getLayout(child.geometry),
            ].join(':');
            const list = batches.get(key);
            if (list) list.push({ mesh: child, relMatrix });
            else batches.set(key, [{ mesh: child, relMatrix }]);
          }
          continue;
        }

        collect(child);
      }
    }

    collect(scopeRoot);

    for (const candidates of batches.values()) {
      if (candidates.length < 2) continue;
      const geometry = mergeCandidates(candidates);
      if (!geometry) continue;
      const first = candidates[0].mesh;
      const merged = new T.Mesh(geometry, first.material);
      merged.name = (scopeRoot.name || 'Static') + ' · batched surfaces';
      merged.castShadow = first.castShadow;
      merged.receiveShadow = first.receiveShadow;
      merged.layers.mask = first.layers.mask;
      merged.renderOrder = first.renderOrder;
      merged.userData.studioBatched = true;
      merged.matrixAutoUpdate = false;
      merged.updateMatrix();
      for (let i = 0; i < candidates.length; i++) {
        candidates[i].mesh.removeFromParent();
      }
      scopeRoot.add(merged);
      stats.mergedMeshes += candidates.length;
      stats.batchesCreated++;
      stats.drawsSaved += candidates.length - 1;
    }

    for (let i = 0; i < childScopes.length; i++) {
      processScope(childScopes[i], false);
    }
  }

  processScope(root, true);

  if (freezeStaticMatrices) {
    root.updateMatrixWorld(true);
    const freeze = (node: T.Object3D) => {
      if (!node.visible || isDynamicNode(node, skipSubtrees)) return;
      if (node !== root && !movableRoots?.has(node) && node.matrixAutoUpdate) {
        node.matrixAutoUpdate = false;
        stats.frozenNodes++;
      }
      const children = node.children;
      for (let i = 0; i < children.length; i++) freeze(children[i]);
    };
    freeze(root);
  }

  return stats;
}

export function batchRoomStaticGeometry(
  model: RoomBatchModel,
  detail?: RoomDetailMatcher | null,
): StaticBatchStats {
  if (
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring'
  ) {
    return {
      mergedMeshes: 0,
      batchesCreated: 0,
      drawsSaved: 0,
      skippedLod: 0,
      frozenNodes: 0,
    };
  }

  const targetRoots = new Set<T.Object3D>(model.byObject.keys());
  const skipSubtrees = new Set<T.Object3D>();
  const movableRoots = new Set<T.Object3D>();

  for (const target of model.targets) {
    if (
      DYNAMIC_TARGET_TYPES.has(target.type) ||
      DYNAMIC_TARGET_IDS.has(target.id) ||
      target.onInspect !== undefined
    ) {
      skipSubtrees.add(target.object);
      movableRoots.add(target.object);
    } else if (target.type === 'inspect') {
      movableRoots.add(target.object);
    }
  }

  const skipGeometry = detail
    ? (geometry: T.BufferGeometry) =>
        detail.isLoaded()
          ? detail.hasLodGeometry(geometry)
          : (geometry.attributes.position?.count ?? 0) >= UNLOADED_LOD_MIN_VERTICES
    : undefined;

  return batchStaticSubtree(model.interior, {
    skipSubtrees,
    targetRoots,
    movableRoots,
    skipGeometry,
    preserveNames: PRESERVED_MESH_NAMES,
    freezeStaticMatrices: true,
  });
}
