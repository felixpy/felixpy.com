import * as T from 'three';

export type StudioZone = 'desk' | 'north' | 'east-workshop' | 'south-rear';

export const DEFAULT_ZONE_PADDING = 0.45;

type ZoneEntry = {
  zone: StudioZone;
  object: T.Object3D;
  cullTargets: T.Object3D[];
  bounds: T.Box3;
  boundsValid: boolean;
  culled: boolean;
  hiddenNodes: T.Object3D[];
};

export type ZoneUpdateOptions = {
  forceAll?: boolean;
  forceZones?: ReadonlySet<StudioZone> | readonly StudioZone[];
  forceObjects?: readonly (T.Object3D | null | undefined)[];
};

function hasLightDescendant(node: T.Object3D): boolean {
  if (node instanceof T.Light) return true;
  for (let i = 0; i < node.children.length; i++) {
    if (hasLightDescendant(node.children[i])) return true;
  }
  return false;
}

/**
 * Collects the highest-level non-light subtrees under `root` so toggling
 * `.visible` never hides a `THREE.Light` (which would alter Three.js
 * `NUM_*_LIGHTS` shader defines and trigger shader recompilation) and never
 * overlaps with a separately-registered child zone entry.
 */
function collectCullTargets(
  root: T.Object3D,
  out: T.Object3D[],
  registeredRoots: ReadonlySet<T.Object3D>,
  isEntryRoot = true,
) {
  if (root instanceof T.Light) return;
  if (!isEntryRoot && registeredRoots.has(root)) return;
  const hasRegisteredChild = root.children.some((child) => registeredRoots.has(child));
  if (!hasLightDescendant(root) && !hasRegisteredChild) {
    out.push(root);
    return;
  }
  for (let i = 0; i < root.children.length; i++) {
    collectCullTargets(root.children[i], out, registeredRoots, false);
  }
}

export function createZoneCuller(padding = DEFAULT_ZONE_PADDING) {
  const entries: ZoneEntry[] = [];
  const registeredRoots = new Set<T.Object3D>();
  const frustum = new T.Frustum();
  const projScreenMatrix = new T.Matrix4();
  const forcedSet = new Set<StudioZone>();

  function setEntryCulled(entry: ZoneEntry, nextCulled: boolean) {
    if (entry.culled === nextCulled) return;
    if (nextCulled) {
      entry.hiddenNodes.length = 0;
      for (let i = 0; i < entry.cullTargets.length; i++) {
        const target = entry.cullTargets[i];
        if (target.visible) {
          target.visible = false;
          target.userData.studioZoneCulled = true;
          entry.hiddenNodes.push(target);
        }
      }
      entry.culled = true;
    } else {
      for (let i = 0; i < entry.hiddenNodes.length; i++) {
        const target = entry.hiddenNodes[i];
        target.visible = true;
        delete target.userData.studioZoneCulled;
      }
      entry.hiddenNodes.length = 0;
      entry.culled = false;
    }
  }

  function computeEntry(entry: ZoneEntry) {
    const wasCulled = entry.culled;
    if (wasCulled) setEntryCulled(entry, false);
    entry.cullTargets.length = 0;
    collectCullTargets(entry.object, entry.cullTargets, registeredRoots, true);
    entry.object.updateWorldMatrix(true, true);
    entry.bounds.setFromObject(entry.object, false);
    entry.boundsValid = !entry.bounds.isEmpty();
    if (wasCulled && entry.boundsValid) setEntryCulled(entry, true);
  }

  function register(zone: StudioZone, object: T.Object3D | null | undefined) {
    if (!object || registeredRoots.has(object)) return;
    registeredRoots.add(object);
    object.userData.studioZone = zone;
    const entry: ZoneEntry = {
      zone,
      object,
      cullTargets: [],
      bounds: new T.Box3(),
      boundsValid: false,
      culled: false,
      hiddenNodes: [],
    };
    entries.push(entry);
    // Refresh ancestor entries in case this object is a child of an already-registered root.
    for (let i = 0; i < entries.length; i++) {
      if (entries[i] === entry || entries[i].zone === zone) computeEntry(entries[i]);
    }
  }

  function zoneOf(object: T.Object3D | null | undefined): StudioZone | undefined {
    for (let cur = object ?? null; cur; cur = cur.parent) {
      const zone = cur.userData.studioZone as StudioZone | undefined;
      if (zone) return zone;
    }
    return undefined;
  }

  function refreshBounds() {
    for (let i = 0; i < entries.length; i++) {
      computeEntry(entries[i]);
    }
  }

  function restoreAll() {
    for (let i = 0; i < entries.length; i++) {
      setEntryCulled(entries[i], false);
    }
  }

  function update(camera: T.Camera, options: ZoneUpdateOptions = {}) {
    if (options.forceAll) {
      restoreAll();
      return;
    }

    forcedSet.clear();
    if (options.forceZones) {
      for (const z of options.forceZones) forcedSet.add(z);
    }
    if (options.forceObjects) {
      for (let i = 0; i < options.forceObjects.length; i++) {
        const z = zoneOf(options.forceObjects[i]);
        if (z) forcedSet.add(z);
      }
    }

    projScreenMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    frustum.setFromProjectionMatrix(projScreenMatrix);
    if (padding > 0) {
      for (let i = 0; i < 6; i++) {
        frustum.planes[i].constant += padding;
      }
    }

    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i];
      if (!entry.boundsValid || forcedSet.has(entry.zone)) {
        setEntryCulled(entry, false);
        continue;
      }
      const inView = frustum.intersectsBox(entry.bounds);
      setEntryCulled(entry, !inView);
    }
  }

  function stats() {
    let culled = 0;
    const culledZones = new Set<StudioZone>();
    const visibleZones = new Set<StudioZone>();
    for (const entry of entries) {
      if (entry.culled) {
        culled++;
        culledZones.add(entry.zone);
      } else {
        visibleZones.add(entry.zone);
      }
    }
    return {
      total: entries.length,
      culled,
      visibleZones: [...visibleZones],
      culledZones: [...culledZones],
    };
  }

  function isZoneVisible(zone: StudioZone): boolean {
    for (let i = 0; i < entries.length; i++) {
      if (entries[i].zone === zone && !entries[i].culled) return true;
    }
    return false;
  }

  return {
    register,
    zoneOf,
    refreshBounds,
    restoreAll,
    update,
    isZoneVisible,
    stats,
  };
}

export type ZoneCuller = ReturnType<typeof createZoneCuller>;
