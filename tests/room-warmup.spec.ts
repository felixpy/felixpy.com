import { expect, test } from '@playwright/test';
import {
  BoxGeometry,
  Material,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  Scene,
  WebGLRenderTarget,
  type Object3D,
  type WebGLRenderer,
} from 'three';
import { roomWarmup } from '../src/scene/room-warmup';

test('catch-up warms newly visible meshes and late material revisions before the first full draw', async () => {
  const scene = new Scene();
  const camera = new PerspectiveCamera(50, 1, 0.1, 100);
  const geometry = new BoxGeometry(0.2, 0.2, 0.2);
  const beauty = new WebGLRenderTarget(1, 1);
  const mesh = (x: number) => {
    const object = new Mesh(geometry, new MeshBasicMaterial());
    object.position.set(x, 0, -4);
    scene.add(object);
    return object;
  };
  const stable = mesh(-0.2);
  const changed = mesh(0.2);
  const outside = mesh(2.6);
  camera.updateMatrixWorld();

  const compiled: [objectId: number, materialVersion: number][] = [];
  const programs: { program: object; isReady: () => boolean; getUniforms: () => void }[] = [];
  let linked = false;
  let reflected = 0;
  let target: WebGLRenderTarget | null = null;
  const renderer = {
    info: { programs },
    getRenderTarget: () => target,
    setRenderTarget(next: WebGLRenderTarget | null) {
      target = next;
    },
    compile(batch: Object3D) {
      expect(target === beauty).toBe(true);
      const materials = new Set<Material>();
      batch.traverse((object) => {
        if (!(object instanceof Mesh) || !(object.material instanceof Material)) return;
        materials.add(object.material);
        compiled.push([object.id, object.material.version]);
        programs.push({
          program: {},
          isReady: () => linked,
          getUniforms: () => {
            reflected++;
          },
        });
      });
      return materials;
    },
  };
  const warmup = roomWarmup(renderer as unknown as WebGLRenderer, scene, camera, [], 'catch-up');
  const originalFrame = globalThis.requestAnimationFrame;
  globalThis.requestAnimationFrame = (callback) => {
    queueMicrotask(() => callback(performance.now()));
    return 0;
  };
  try {
    const stableVersion = stable.material.version;
    const initialVersion = changed.material.version;
    await warmup.front(beauty);
    expect(compiled).toEqual([
      [stable.id, stableVersion],
      [changed.id, initialVersion],
    ]);

    camera.rotation.y = -0.4;
    camera.updateMatrixWorld();
    changed.material.alphaTest = 0.5;
    expect(changed.material.version).toBeGreaterThan(initialVersion);
    expect(warmup.prepareVisible(beauty, 1)).toBe(false);
    expect(compiled).toEqual([
      [stable.id, stableVersion],
      [changed.id, initialVersion],
      [changed.id, changed.material.version],
      [outside.id, outside.material.version],
    ]);
    expect(warmup.prepareVisible(beauty, 1)).toBe(false);
    expect(reflected).toBe(0);

    linked = true;
    await expect.poll(() => warmup.prepareVisible(beauty, 1)).toBe(true);
    expect(reflected).toBe(4);
    expect(compiled).toHaveLength(4);
    expect(target).toBeNull();
  } finally {
    warmup.dispose();
    if (originalFrame) globalThis.requestAnimationFrame = originalFrame;
    else Reflect.deleteProperty(globalThis, 'requestAnimationFrame');
    for (const object of [stable, changed, outside]) object.material.dispose();
    geometry.dispose();
    beauty.dispose();
  }
});
