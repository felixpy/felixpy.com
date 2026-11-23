import * as T from 'three';
import type { Target } from '../interaction';
import type { StudioModel } from '../studio';

declare global {
  interface Window {
    __studioReview?: {
      inventory: () => { id: string; type: string; name: string; uuid: string }[];
      captureLighting: (
        location?: 'desk' | 'aj' | 'camp',
      ) => Promise<{ width: number; height: number; rgbe: string }>;
      activate: (id: string) => void;
      project: (id: string) => { x: number; y: number } | null;
      camera: () => { position: number[]; rotation: number[]; fov: number };
      objectPose: (id: string) => { position: number[]; rotation: number[] } | undefined;
      bounds: (name: string) => { min: number[]; max: number[] };
      drawer: (index: number) => number | undefined;
      lightLevels: () => ReturnType<StudioModel['lightLevels']>;
      exportRoom: (objectName?: string, authoring?: boolean) => Promise<void>;
    };
  }
}

type ReviewContext = {
  model: StudioModel;
  camera: T.PerspectiveCamera;
  renderer: T.WebGLRenderer;
  scene: T.Scene;
  lightingReady: () => Promise<unknown>;
  open: (target: Target | undefined) => void;
};

export function createStudioReview({
  model,
  camera,
  renderer,
  scene,
  lightingReady,
  open,
}: ReviewContext): NonNullable<Window['__studioReview']> {
  const element = renderer.domElement;
  return {
    inventory: () =>
      model.targets.map(({ id, type, object }) => ({
        id,
        type,
        name: object.name,
        uuid: object.uuid,
      })),
    async captureLighting(location?: 'desk' | 'aj' | 'camp') {
      await model.prepareRear();
      await lightingReady();
      const { captureStudioLight } = await import('./capture-studio-light');
      return captureStudioLight(renderer, scene, location);
    },
    activate: (id) => open(model.targets.find((t) => t.id === id)),
    project: (id) => {
      const object =
        model.targets.find((t) => t.id === id)?.object ?? model.root.getObjectByName(id);
      const point = object?.getWorldPosition(new T.Vector3()).project(camera);
      const rect = element.getBoundingClientRect();
      return point
        ? {
            x: rect.left + ((point.x + 1) * rect.width) / 2,
            y: rect.top + ((1 - point.y) * rect.height) / 2,
          }
        : null;
    },
    camera: () => ({
      position: camera.position.toArray(),
      rotation: camera.quaternion.toArray(),
      fov: camera.fov,
    }),
    objectPose: (id) => {
      const object =
        model.targets.find((item) => item.id === id)?.object ?? model.root.getObjectByName(id);
      if (!object) return undefined;
      return { position: object.position.toArray(), rotation: object.quaternion.toArray() };
    },
    bounds: (name) => {
      const object = model.root.getObjectByName(name);
      if (!object) throw new Error('Unknown studio object: ' + name);
      const bounds = new T.Box3().setFromObject(object, true);
      return { min: bounds.min.toArray(), max: bounds.max.toArray() };
    },
    drawer: (index) => model.targets.find((t) => t.id === 'drawer-' + index)?.object.position.z,
    lightLevels: () => model.lightLevels(),
    async exportRoom(objectName, authoring) {
      const { exportRoom } = await import('./export-room');
      return exportRoom(model, camera, renderer, objectName, authoring);
    },
  };
}
