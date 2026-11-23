import * as T from 'three';

const TEXTURE_SLOTS = [
  'map',
  'normalMap',
  'roughnessMap',
  'metalnessMap',
  'aoMap',
  'emissiveMap',
  'alphaMap',
  'bumpMap',
  'lightMap',
  'clearcoatMap',
  'clearcoatNormalMap',
  'clearcoatRoughnessMap',
  'sheenColorMap',
  'sheenRoughnessMap',
  'specularMap',
  'specularColorMap',
  'specularIntensityMap',
  'transmissionMap',
  'thicknessMap',
  'iridescenceMap',
  'iridescenceThicknessMap',
  'anisotropyMap',
] as const;

export type DisposeSubtreeOptions = {
  keepRoot?: boolean;
  sharedGeometries?: ReadonlySet<T.BufferGeometry>;
  sharedMaterials?: ReadonlySet<T.Material>;
  sharedTextures?: ReadonlySet<T.Texture>;
};

export function disposeSubtree(root: T.Object3D, options: DisposeSubtreeOptions = {}) {
  const { keepRoot = true, sharedGeometries, sharedMaterials, sharedTextures } = options;
  const geometries = new Set<T.BufferGeometry>();
  const materials = new Set<T.Material>();
  const textures = new Set<T.Texture>();

  root.traverse((node) => {
    if (keepRoot && node === root) return;
    if (node instanceof T.Mesh || node instanceof T.Line || node instanceof T.Points) {
      if (node.geometry && !sharedGeometries?.has(node.geometry)) {
        geometries.add(node.geometry);
      }
      const list = Array.isArray(node.material) ? node.material : [node.material];
      for (const material of list) {
        if (!material || sharedMaterials?.has(material)) continue;
        materials.add(material);
        const record = material as unknown as Record<string, unknown>;
        for (const slot of TEXTURE_SLOTS) {
          const tex = record[slot];
          if (tex instanceof T.Texture && !tex.isRenderTargetTexture && !sharedTextures?.has(tex)) {
            textures.add(tex);
          }
        }
      }
    }
  });

  if (keepRoot) {
    for (const child of [...root.children]) {
      child.removeFromParent();
    }
  } else {
    root.removeFromParent();
  }

  for (const texture of textures) texture.dispose();
  for (const material of materials) material.dispose();
  for (const geometry of geometries) geometry.dispose();
}

export type HeroEntry = {
  id: string;
  subtree?: T.Object3D;
  disposeOptions?: DisposeSubtreeOptions;
  evict?: () => void;
  isPinned?: () => boolean;
};

export function createHeroLru(maxEntries = 3) {
  const limit = Math.max(1, maxEntries);
  const entries = new Map<string, HeroEntry>();
  let pinnedId: string | undefined;

  function canEvict(entry: HeroEntry): boolean {
    if (entry.id === pinnedId) return false;
    if (entry.isPinned?.()) return false;
    return true;
  }

  function releaseEntry(entry: HeroEntry) {
    entries.delete(entry.id);
    if (entry.evict) {
      entry.evict();
    } else if (entry.subtree) {
      disposeSubtree(entry.subtree, entry.disposeOptions);
    }
  }

  function evictOverflow() {
    if (entries.size <= limit) return;
    for (const entry of [...entries.values()]) {
      if (entries.size <= limit) break;
      if (!canEvict(entry)) continue;
      releaseEntry(entry);
    }
  }

  function touch(entry: HeroEntry) {
    if (entries.has(entry.id)) entries.delete(entry.id);
    entries.set(entry.id, entry);
    evictOverflow();
  }

  function pin(id: string | undefined) {
    pinnedId = id;
    if (id && entries.has(id)) {
      const existing = entries.get(id)!;
      entries.delete(id);
      entries.set(id, existing);
    }
    evictOverflow();
  }

  function evict(id: string) {
    const entry = entries.get(id);
    if (entry && canEvict(entry)) releaseEntry(entry);
  }

  function clear() {
    pinnedId = undefined;
    for (const entry of [...entries.values()]) {
      releaseEntry(entry);
    }
  }

  return {
    touch,
    pin,
    evict,
    clear,
    has: (id: string) => entries.has(id),
    ids: () => [...entries.keys()],
    get size() {
      return entries.size;
    },
  };
}

export type HeroLru = ReturnType<typeof createHeroLru>;
