import { Camera, Frustum, Group, Line, Matrix4, Mesh, Points, Scene, Texture } from 'three';
import type { Material, Object3D, WebGLRenderTarget, WebGLRenderer } from 'three';

type Renderable = Mesh | Line | Points;

function renderable(object: Object3D): object is Renderable {
  return object instanceof Mesh || object instanceof Line || object instanceof Points;
}

function materialVersion(material: Material) {
  return material.id + '/' + material.version;
}

export function roomWarmup(gl: WebGLRenderer, scene: Scene, camera: Camera) {
  const seen = new WeakMap<Renderable, string>();
  const materials = new WeakMap<Material, Texture[]>();
  const maps = new Set<Texture>();
  const frontMaps = new Set<Texture>();
  const queue: Renderable[] = [];
  const frontQueue: Renderable[] = [];
  const group = new Group();
  let offset = 0;

  function collectMaps(object: Renderable, destination: Set<Texture>) {
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      let textures = materials.get(material);
      if (!textures) {
        textures = Object.values(material).filter(
          (value): value is Texture =>
            value instanceof Texture && !value.isRenderTargetTexture && value.image,
        );
        materials.set(material, textures);
      }
      for (const texture of textures) {
        if (destination === frontMaps) maps.delete(texture);
        else if (frontMaps.has(texture)) continue;
        destination.add(texture);
      }
    }
  }

  function scan(front?: Frustum) {
    scene.traverseVisible((object) => {
      if (!renderable(object)) return;
      const version = Array.isArray(object.material)
        ? object.material.map(materialVersion).join(',')
        : materialVersion(object.material);
      if (seen.get(object) === version) return;
      seen.set(object, version);
      if (front && (!object.frustumCulled || front.intersectsObject(object))) {
        frontQueue.push(object);
        collectMaps(object, frontMaps);
      } else {
        queue.push(object);
        collectMaps(object, maps);
      }
    });
  }

  function upload(textures: Set<Texture>, budget: number) {
    const until = performance.now() + budget;
    for (const texture of textures) {
      textures.delete(texture);
      if (texture.version) gl.initTexture(texture);
      if (performance.now() >= until) break;
    }
    return textures.size === 0;
  }

  return {
    uploadFront: () => upload(frontMaps, 3),
    async front(target: WebGLRenderTarget | null) {
      scene.updateMatrixWorld();
      scan(
        new Frustum().setFromProjectionMatrix(
          new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse),
        ),
      );
      const batches: Promise<unknown>[] = [];
      for (let index = 0; index < frontQueue.length; index += 48) {
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        const previous = gl.getRenderTarget();
        try {
          gl.setRenderTarget(target);
          group.children.push(...frontQueue.slice(index, index + 48));
          batches.push(gl.compileAsync(group, camera, scene));
        } finally {
          group.children.length = 0;
          gl.setRenderTarget(previous);
        }
      }
      frontQueue.length = 0;
      await Promise.all(batches);
    },
    scan: () => scan(),
    step(target: WebGLRenderTarget | null) {
      if (offset < queue.length) {
        const end = Math.min(offset + 40, queue.length);
        for (; offset < end; offset++) group.children.push(queue[offset]);
        const previous = gl.getRenderTarget();
        gl.setRenderTarget(target);
        try {
          gl.compile(group, camera, scene);
        } finally {
          group.children.length = 0;
          gl.setRenderTarget(previous);
        }
        if (offset === queue.length) {
          offset = queue.length = 0;
        }
      } else if (maps.size) upload(maps, 2);
    },
  };
}
