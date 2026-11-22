import {
  Camera,
  Frustum,
  Group,
  Light,
  Line,
  Matrix4,
  Mesh,
  OrthographicCamera,
  PlaneGeometry,
  Points,
  Scene,
  Texture,
} from 'three';
import type { Material, Object3D, WebGLRenderTarget, WebGLRenderer } from 'three';

type Renderable = Mesh | Line | Points;
type LinkedProgram = NonNullable<WebGLRenderer['info']['programs']>[number] & {
  isReady?: () => boolean;
};
type WarmupPass = { material: Material; target: WebGLRenderTarget };

function renderable(object: Object3D): object is Renderable {
  return object instanceof Mesh || object instanceof Line || object instanceof Points;
}

function materialVersion(material: Material) {
  return material.id + '/' + material.version;
}

export function roomWarmup(
  gl: WebGLRenderer,
  scene: Scene,
  camera: Camera,
  passes: WarmupPass[] = [],
) {
  let seen = new WeakMap<Renderable, string>();
  const materials = new WeakMap<Material, Texture[]>();
  const maps = new Set<Texture>();
  const frontMaps = new Set<Texture>();
  const queue: Renderable[] = [];
  const frontQueue: Renderable[] = [];
  const group = new Group();
  let offset = 0;
  const view = new Frustum();
  const projection = new Matrix4();
  const trackedMaterials = new WeakMap<Material, { version: number; revision: number }>();
  const knownPrograms = new WeakSet<LinkedProgram>();
  const programs = new Set<LinkedProgram>();
  let visible: Renderable[] = [];
  let visibleOffset = 0;
  let visibleAt = Number.NEGATIVE_INFINITY;
  let detailRevision = -1;
  let environment = scene.environment;
  let lights = '';
  let surface: WebGLRenderTarget | null = null;
  let pendingPasses = passes.length > 0;

  function trackMaterial(material: Material) {
    let tracked = trackedMaterials.get(material);
    if (!tracked) {
      tracked = { version: material.version, revision: 0 };
      trackedMaterials.set(material, tracked);
    } else if (tracked.version !== material.version) {
      tracked.version = material.version;
      tracked.revision++;
    }
    return tracked;
  }

  function visibleVersion(object: Renderable) {
    const list = Array.isArray(object.material) ? object.material : [object.material];
    return (
      object.geometry.id +
      '/' +
      list
        .map((material) => {
          const tracked = trackMaterial(material);
          return `${material.id}/${tracked.revision}`;
        })
        .join(',')
    );
  }

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

  function updateVisible(target: WebGLRenderTarget | null, revision: number, now: number) {
    scene.updateMatrixWorld();
    view.setFromProjectionMatrix(
      projection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse),
    );
    const lightsInView: string[] = [];
    const candidates: Renderable[] = [];
    scene.traverseVisible((object) => {
      if (!object.layers.test(camera.layers)) return;
      if (object instanceof Light) {
        lightsInView.push(`${object.id}/${Number(object.castShadow)}`);
      } else if (renderable(object) && (!object.frustumCulled || view.intersectsObject(object))) {
        candidates.push(object);
      }
    });
    const lightKey = lightsInView.join(',');
    if (environment !== scene.environment || surface !== target || lights !== lightKey) {
      seen = new WeakMap();
      environment = scene.environment;
      surface = target;
      lights = lightKey;
    }
    visible = candidates.filter((object) => seen.get(object) !== visibleVersion(object));
    visibleOffset = 0;
    visibleAt = now;
    detailRevision = revision;
  }

  function trackPrograms() {
    for (const program of gl.info.programs ?? []) {
      if (knownPrograms.has(program)) continue;
      knownPrograms.add(program);
      programs.add(program);
    }
  }

  function reflectPrograms(until: number) {
    for (const program of programs) {
      if (!program.program || program.isReady?.() !== false) {
        programs.delete(program);
        if (program.program) program.getUniforms();
      }
      if (performance.now() >= until) break;
    }
  }

  function compilePasses() {
    const previous = gl.getRenderTarget();
    const probe = new Scene();
    const screenCamera = new OrthographicCamera();
    const screenGeometry = new PlaneGeometry(2, 2).deleteAttribute('normal');
    try {
      for (const pass of passes) {
        const screen = new Mesh(screenGeometry, pass.material);
        probe.add(screen);
        gl.setRenderTarget(pass.target);
        gl.compile(probe, screenCamera);
        probe.remove(screen);
      }
      trackPrograms();
    } finally {
      gl.setRenderTarget(previous);
      screenGeometry.dispose();
      pendingPasses = false;
    }
  }

  function compileVisible(target: WebGLRenderTarget | null) {
    const count = Math.min(32, visible.length - visibleOffset);
    const batch = visible.slice(visibleOffset, visibleOffset + count);
    visibleOffset += count;
    const previous = gl.getRenderTarget();
    try {
      gl.setRenderTarget(target);
      group.children.push(...batch);
      const compiled = gl.compile(group, camera, scene);
      for (const material of compiled) {
        const tracked = trackedMaterials.get(material);
        if (tracked) tracked.version = material.version;
      }
      for (const object of batch) {
        seen.set(object, visibleVersion(object));
        collectMaps(object, frontMaps);
      }
      trackPrograms();
    } finally {
      group.children.length = 0;
      gl.setRenderTarget(previous);
    }
  }

  function prepareVisible(target: WebGLRenderTarget | null, revision: number) {
    const now = performance.now();
    if (
      detailRevision !== revision ||
      environment !== scene.environment ||
      surface !== target ||
      now - visibleAt >= 150 ||
      (visibleOffset === visible.length && programs.size === 0 && frontMaps.size === 0)
    )
      updateVisible(target, revision, now);

    if (!programs.size && visibleOffset === visible.length && !frontMaps.size && !pendingPasses) {
      scene.traverseVisible((object) => {
        if (!renderable(object) || seen.get(object) !== visibleVersion(object)) return;
        const list = Array.isArray(object.material) ? object.material : [object.material];
        seen.set(object, list.map(materialVersion).join(','));
      });
      return true;
    }

    if (pendingPasses) compilePasses();
    else if (programs.size < 20 && visibleOffset < visible.length) compileVisible(target);
    const until = performance.now() + 3;
    reflectPrograms(until);
    if (frontMaps.size && performance.now() < until) upload(frontMaps, until - performance.now());
    return false;
  }

  return {
    uploadFront: () => upload(frontMaps, 3),
    prepareVisible,
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
