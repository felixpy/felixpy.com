import * as T from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { displayMeshoptDecoder } from './display-meshopt';
import { packedBuffer } from './packed-buffer';

type ModelSetup = {
  mesh?: (mesh: T.Mesh) => void;
  mounted?: (scene: T.Group) => void;
};

export function deferredDisplayModel(parent: T.Group, path: string, setup: ModelSetup = {}) {
  let pending: Promise<void> | undefined;
  return (manager = T.DefaultLoadingManager) => {
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
  const loader = new GLTFLoader(manager).setMeshoptDecoder(displayMeshoptDecoder());
  async function mount() {
    const authoring =
      import.meta.env.DEV && new URLSearchParams(location.search).get('review') === 'authoring';
    const response = await fetch(manager.resolveURL(authoring ? path : path + '.gz'));
    const buffer = await packedBuffer(response);
    const { scene } = await loader.parseAsync(buffer, T.LoaderUtils.extractUrlBase(path));
    scene.traverse((part) => {
      if (!(part instanceof T.Mesh)) return;
      if (part instanceof T.InstancedMesh) part.userData.exportInstalledInstances = true;
      part.castShadow = !(part.material instanceof T.Material && part.material.transparent);
      part.receiveShadow = true;
      setup.mesh?.(part);
    });
    parent.add(scene);
    if (setup.mounted) {
      const products = [...scene.children];
      setup.mounted(scene);
      for (const product of products) {
        if (product.parent && product.parent !== scene) product.updateWorldMatrix(true, true, true);
      }
    }
    if (scene.parent) scene.updateWorldMatrix(true, true, true);
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
