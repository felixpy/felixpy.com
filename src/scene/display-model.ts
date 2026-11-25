import * as T from 'three';
import { defaultStudioLoadingManager } from './asset-loading';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { getOrCreateGltfKtx2Loader } from './ktx2-loader';
import { packedBuffer } from './packed-buffer';
import { zoneBundlePath, zoneForModel, type ZoneBundleId } from './zone-bundles';

function createGltfLoader(manager: T.LoadingManager): GLTFLoader {
  const loader = new GLTFLoader(manager).setMeshoptDecoder(MeshoptDecoder);
  const ktx2 = getOrCreateGltfKtx2Loader();
  if (ktx2) loader.setKTX2Loader(ktx2);
  return loader;
}

type ModelSetup = {
  mesh?: (mesh: T.Mesh) => void;
  mounted?: (scene: T.Group) => void;
  mark?: (phase: string, startTime?: number) => PerformanceMark;
};

type ZoneArchive = {
  entries: Map<string, T.Object3D>;
  claimed: Set<string>;
};

const zoneArchives = new Map<ZoneBundleId, Promise<ZoneArchive>>();

export function resetZoneBundleCache() {
  zoneArchives.clear();
}

function loadZoneArchive(zone: ZoneBundleId, manager: T.LoadingManager): Promise<ZoneArchive> {
  const existing = zoneArchives.get(zone);
  if (existing) return existing;
  const bundlePath = zoneBundlePath(zone);
  const url = manager.resolveURL(bundlePath + '.gz');
  const pending = (async (): Promise<ZoneArchive> => {
    const response = await fetch(url);
    const buffer = await packedBuffer(response);
    await MeshoptDecoder.ready;
    const loader = createGltfLoader(manager);
    const { scene } = await loader.parseAsync(buffer, T.LoaderUtils.extractUrlBase(bundlePath));
    const entries = new Map<string, T.Object3D>();
    for (const child of scene.children) {
      const modelPath = child.userData?.zoneModelPath;
      if (typeof modelPath === 'string') entries.set(modelPath, child);
    }
    return { entries, claimed: new Set() };
  })();
  pending.catch(() => {
    if (zoneArchives.get(zone) === pending) zoneArchives.delete(zone);
  });
  zoneArchives.set(zone, pending);
  return pending;
}

function extractZoneScene(archive: ZoneArchive, path: string): T.Group | undefined {
  const wrapper = archive.entries.get(path);
  if (!wrapper) return undefined;
  const group = new T.Group();
  if (!archive.claimed.has(path)) {
    archive.claimed.add(path);
    const children = [...wrapper.children];
    for (const child of children) group.add(child);
  } else {
    for (const child of wrapper.children) group.add(child.clone(true));
  }
  return group;
}

export function deferredDisplayModel(parent: T.Group, path: string, setup: ModelSetup = {}) {
  let pending: Promise<void> | undefined;
  return (manager = defaultStudioLoadingManager) => {
    if (!pending) {
      pending = loadDisplayModel(parent, path, manager, setup);
      void pending.catch(() => {
        pending = undefined;
      });
    }
    return pending;
  };
}

export function filterPrintedArtwork(mesh: T.Mesh) {
  const material = mesh.material;
  if (material instanceof T.MeshStandardMaterial && material.map) {
    material.map.anisotropy = 8;
  }
}

export function loadDisplayModel(
  parent: T.Group,
  path: string,
  manager: T.LoadingManager,
  setup: ModelSetup = {},
) {
  const { mark } = setup;
  async function loadStandalone(authoring: boolean): Promise<T.Group> {
    await MeshoptDecoder.ready;
    const loader = createGltfLoader(manager);
    const url = manager.resolveURL(authoring ? path : path + '.gz');
    const fetchStart = mark?.('fetch-start').startTime;
    const response = await fetch(url);
    mark?.('fetch-headers');
    const buffer = await packedBuffer(response);
    mark?.('buffer-ready');
    if (mark && fetchStart !== undefined) {
      const resource = performance.getEntriesByName(response.url, 'resource').at(-1) as
        | PerformanceResourceTiming
        | undefined;
      if (resource && resource.startTime >= fetchStart && resource.responseEnd > 0)
        mark('body-end', resource.responseEnd);
    }
    mark?.('parse-start');
    const { scene } = await loader.parseAsync(buffer, T.LoaderUtils.extractUrlBase(path));
    mark?.('parse-end');
    return scene;
  }

  async function mount() {
    const authoring =
      import.meta.env.DEV &&
      typeof location !== 'undefined' &&
      new URLSearchParams(location.search).get('review') === 'authoring';
    const zone = !authoring ? zoneForModel(path) : undefined;
    let scene: T.Group | undefined;
    if (zone) {
      try {
        const archive = await loadZoneArchive(zone, manager);
        scene = extractZoneScene(archive, path);
      } catch {
        // Fall back to standalone model delivery if the spatial zone bundle fails.
      }
    }
    if (!scene) scene = await loadStandalone(authoring);
    scene.traverse((part) => {
      if (!(part instanceof T.Mesh)) return;
      if (part instanceof T.InstancedMesh) part.userData.exportInstalledInstances = true;
      part.castShadow = !(part.material instanceof T.Material && part.material.transparent);
      part.receiveShadow = true;
      setup.mesh?.(part);
    });
    mark?.('mesh-setup-end');
    parent.add(scene);
    if (setup.mounted) {
      const products = [...scene.children];
      setup.mounted(scene);
      for (const product of products) {
        if (product.parent && product.parent !== scene) product.updateWorldMatrix(true, true, true);
      }
    }
    if (scene.parent) scene.updateWorldMatrix(true, true, true);
    mark?.('mount-end');
  }
  manager.itemStart(path);
  const mounting = mount();
  void mounting
    .catch((error) => {
      manager.itemError(path);
      console.error(error);
    })
    .finally(() => manager.itemEnd(path));
  return mounting;
}
