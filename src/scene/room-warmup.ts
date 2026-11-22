import {
  Camera,
  DoubleSide,
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
type WarmupMode = 'paced' | 'adaptive' | 'catch-up' | 'isolated-catch-up';

const pacedProgramLimit = 2;
const pacedFrameBudget = 3;
const adaptiveProgramLimit = 4;
const steadyInterval = 8.5;
const fallbackInterval = 16.7;
const steadyWindow = 750;

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
  mode?: WarmupMode,
  subtrees?: readonly Object3D[],
) {
  const isolated = mode === 'isolated-catch-up';
  const catchUp = mode === 'catch-up' || isolated;
  const pacePrograms = mode === 'paced' || mode === 'adaptive';
  const batchLimit = subtrees ? 6 : 20;
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
  const knownPrograms = new WeakSet<LinkedProgram>(
    pacePrograms || catchUp ? (gl.info.programs ?? []) : [],
  );
  const programs = new Set<LinkedProgram>();
  let partial = new WeakMap<Renderable, { version: string; nextMaterial: number }>();
  let visible: Renderable[] = [];
  let visibleOffset = 0;
  let visibleAt = Number.NEGATIVE_INFINITY;
  let detailRevision = -1;
  let environment = scene.environment;
  let lights = '';
  let surface: WebGLRenderTarget | null = null;
  let nextPass = 0;
  let programLimit = pacedProgramLimit;
  let lastSubmission: number | undefined;
  let steadyFor = 0;
  let disposed = false;
  let warmingSubtrees = false;

  function budgetAfterDraw() {
    const now = performance.now();
    if (mode === 'adaptive') {
      const interval = lastSubmission === undefined ? 0 : now - lastSubmission;
      lastSubmission = now;
      const previous = programLimit;
      if (interval >= fallbackInterval) programLimit = pacedProgramLimit;
      steadyFor = interval <= steadyInterval ? steadyFor + interval : 0;
      if (programLimit < adaptiveProgramLimit && steadyFor >= steadyWindow) {
        programLimit++;
        steadyFor = 0;
      }
      if (programLimit !== previous) performance.mark(`studio-room-shader-limit-${programLimit}`);
    }
    return now + pacedFrameBudget;
  }

  function trackMaterial(material: Material) {
    let tracked = trackedMaterials.get(material);
    if (!tracked) {
      tracked = { version: material.version, revision: 0 };
      trackedMaterials.set(material, tracked);
    } else if (tracked.version !== material.version) {
      tracked.version = material.version;
      tracked.revision++;
      if (catchUp) materials.delete(material);
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

  function updateContext(target: WebGLRenderTarget | null, visibleLights: string[]) {
    const lightKey = visibleLights.join(',');
    if (environment !== scene.environment || surface !== target || lights !== lightKey) {
      seen = new WeakMap();
      partial = new WeakMap();
      environment = scene.environment;
      surface = target;
      lights = lightKey;
    }
  }

  function lightVersion(light: Light) {
    return `${light.id}/${Number(light.castShadow)}`;
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
        lightsInView.push(lightVersion(object));
      } else if (
        !subtrees &&
        renderable(object) &&
        (!object.frustumCulled || view.intersectsObject(object))
      ) {
        candidates.push(object);
      }
    });
    if (subtrees) {
      const outside: Renderable[] = [];
      for (const root of subtrees) {
        if (!shownInScene(root)) continue;
        root.traverseVisible((object) => {
          if (!renderable(object) || !object.layers.test(camera.layers)) return;
          const inView = !object.frustumCulled || view.intersectsObject(object);
          (inView ? candidates : outside).push(object);
        });
      }
      candidates.push(...outside);
    }
    updateContext(target, lightsInView);
    visible = candidates.filter((object) => seen.get(object) !== visibleVersion(object));
    visibleOffset = 0;
    visibleAt = now;
    detailRevision = revision;
  }

  function shownInScene(root: Object3D) {
    for (let parent: Object3D | null = root; parent?.visible; parent = parent.parent)
      if (parent === scene) return true;
    return false;
  }

  function trackPrograms(previous?: ReadonlySet<LinkedProgram>) {
    let added = 0;
    for (const program of gl.info.programs ?? []) {
      if (knownPrograms.has(program) || previous?.has(program)) continue;
      knownPrograms.add(program);
      programs.add(program);
      added++;
    }
    return added;
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
    const end = pacePrograms || isolated ? nextPass + 1 : passes.length;
    try {
      for (; nextPass < end; nextPass++) {
        const pass = passes[nextPass];
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
    }
  }

  function compileObjects(target: WebGLRenderTarget | null, batch: Renderable[]) {
    const previous = gl.getRenderTarget();
    const face = subtrees ? gl.getActiveCubeFace() : undefined;
    const mip = subtrees ? gl.getActiveMipmapLevel() : undefined;
    const previousPrograms = subtrees ? new Set<LinkedProgram>(gl.info.programs ?? []) : undefined;
    try {
      gl.setRenderTarget(target);
      group.children.push(...batch);
      if (catchUp || subtrees)
        group.traverse((object) => {
          if (renderable(object)) visibleVersion(object);
        });
      const compiled = gl.compile(group, camera, scene);
      for (const material of compiled) {
        const tracked = trackedMaterials.get(material);
        if (tracked) tracked.version = material.version;
      }
      return trackPrograms(previousPrograms);
    } finally {
      group.children.length = 0;
      gl.setRenderTarget(previous, face, mip);
    }
  }

  function compileVisibleBatch(target: WebGLRenderTarget | null, batch: Renderable[]) {
    compileObjects(target, batch);
    for (const object of batch) {
      seen.set(object, visibleVersion(object));
      if (!subtrees) collectMaps(object, frontMaps);
    }
  }

  function compileVisible(target: WebGLRenderTarget | null) {
    const count = subtrees ? batchLimit - programs.size : 32;
    const end = Math.min(visibleOffset + count, visible.length);
    compileVisibleBatch(target, visible.slice(visibleOffset, end));
    visibleOffset = end;
  }

  function compilePaced(
    objects: Renderable[],
    index: number,
    target: WebGLRenderTarget | null,
    until: number,
    complete?: (object: Renderable) => void,
  ) {
    while (programs.size < programLimit && index < objects.length) {
      if (performance.now() >= until) break;
      const object = objects[index];
      if (!object.parent) {
        seen.delete(object);
        partial.delete(object);
        index++;
        continue;
      }
      const original = object.material;
      const list = Array.isArray(original) ? original : [original];
      const version = visibleVersion(object);
      let progress = partial.get(object);
      if (progress?.version !== version) {
        progress = { version, nextMaterial: 0 };
        partial.set(object, progress);
      }
      const material = list[progress.nextMaterial];
      if (!material) {
        partial.delete(object);
        complete?.(object);
        index++;
        continue;
      }
      const variants =
        material.transparent && material.side === DoubleSide && !material.forceSinglePass ? 2 : 1;
      if (programs.size + variants > programLimit) break;
      let added;
      try {
        object.material = material;
        added = compileObjects(target, [object]);
      } finally {
        object.material = original;
      }
      if (++progress.nextMaterial === list.length) {
        partial.delete(object);
        complete?.(object);
        index++;
      }
      if (added) break;
    }
    return index;
  }

  function prepareVisible(
    target: WebGLRenderTarget | null,
    revision: number,
    drawPending?: () => void,
  ) {
    const now = performance.now();
    if (
      detailRevision !== revision ||
      environment !== scene.environment ||
      surface !== target ||
      now - visibleAt >= 150 ||
      (visibleOffset === visible.length && programs.size === 0 && frontMaps.size === 0)
    )
      updateVisible(target, revision, now);

    if (
      !programs.size &&
      visibleOffset === visible.length &&
      !frontMaps.size &&
      nextPass === passes.length
    ) {
      if (subtrees) {
        if (warmingSubtrees) performance.mark('studio-workbench-warm-end');
        warmingSubtrees = false;
        return true;
      }
      scene.traverseVisible((object) => {
        if (!renderable(object) || seen.get(object) !== visibleVersion(object)) return;
        const list = Array.isArray(object.material) ? object.material : [object.material];
        seen.set(object, list.map(materialVersion).join(','));
      });
      return true;
    }

    if (pacePrograms) {
      drawPending?.();
      const until = budgetAfterDraw();
      trackPrograms();
      reflectPrograms(until);
      if (programs.size < programLimit && performance.now() < until) {
        if (nextPass < passes.length) compilePasses();
        else
          visibleOffset = compilePaced(visible, visibleOffset, target, until, (object) => {
            seen.set(object, visibleVersion(object));
            collectMaps(object, frontMaps);
          });
      }
      if (!programs.size && frontMaps.size && performance.now() < until)
        upload(frontMaps, until - performance.now());
      return false;
    }

    if (isolated) {
      if (nextPass < passes.length) compilePasses();
      else if (programs.size < batchLimit && visibleOffset < visible.length) compileVisible(target);
      else if (programs.size) reflectPrograms(performance.now() + 3);
      else if (frontMaps.size) upload(frontMaps, 0);
      return false;
    }

    if (subtrees && !warmingSubtrees) {
      warmingSubtrees = true;
      performance.mark('studio-workbench-warm-start');
    }
    if (nextPass < passes.length) compilePasses();
    else if (programs.size < batchLimit && visibleOffset < visible.length) compileVisible(target);
    const until = performance.now() + 3;
    reflectPrograms(until);
    if (frontMaps.size && performance.now() < until) upload(frontMaps, until - performance.now());
    return false;
  }

  return {
    uploadFront: () => upload(frontMaps, 3),
    prepareVisible,
    async front(target: WebGLRenderTarget | null) {
      if (catchUp) {
        updateVisible(target, -1, performance.now());
        for (const object of visible) {
          frontQueue.push(object);
          collectMaps(object, frontMaps);
        }
      } else {
        scene.updateMatrixWorld();
        scan(
          new Frustum().setFromProjectionMatrix(
            new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse),
          ),
        );
      }
      const batches: Promise<unknown>[] = [];
      for (let index = 0; index < frontQueue.length; index += 48) {
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        if (disposed) return;
        const batch = frontQueue.slice(index, index + 48);
        if (catchUp) {
          const visibleLights: string[] = [];
          scene.traverseVisible((object) => {
            if (object instanceof Light && object.layers.test(camera.layers))
              visibleLights.push(lightVersion(object));
          });
          updateContext(target, visibleLights);
          compileVisibleBatch(target, batch);
          continue;
        }
        const previous = gl.getRenderTarget();
        try {
          gl.setRenderTarget(target);
          group.children.push(...batch);
          batches.push(gl.compileAsync(group, camera, scene));
        } finally {
          group.children.length = 0;
          gl.setRenderTarget(previous);
        }
      }
      frontQueue.length = 0;
      if (catchUp) {
        visible = [];
        visibleAt = Number.NEGATIVE_INFINITY;
      }
      await Promise.all(batches);
    },
    dispose() {
      disposed = true;
      frontQueue.length = queue.length = 0;
      maps.clear();
      frontMaps.clear();
      programs.clear();
      visible = [];
    },
    scan: () => scan(),
    step(target: WebGLRenderTarget | null) {
      if (pacePrograms) {
        const until = budgetAfterDraw();
        trackPrograms();
        reflectPrograms(until);
        offset = compilePaced(queue, offset, target, until);
        if (offset === queue.length) offset = queue.length = 0;
        if (!programs.size && maps.size && performance.now() < until)
          upload(maps, until - performance.now());
        return;
      }
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
