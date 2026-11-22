import * as T from 'three';

type Cluster = {
  bounds: T.Box3;
  parent?: Cluster;
  children?: [Cluster, Cluster];
  index?: number;
};

type Surface = {
  object: T.Mesh;
  geometry: T.BufferGeometry;
  position: T.BufferAttribute | T.InterleavedBufferAttribute;
  version: number;
  world: T.Matrix4;
  cluster: Cluster;
};

function positionVersion(position: Surface['position']) {
  return position instanceof T.InterleavedBufferAttribute
    ? position.data.version
    : position.version;
}

function buildClusters(leaves: Cluster[]): Cluster {
  if (leaves.length === 1) return leaves[0];
  const bounds = new T.Box3();
  for (const node of leaves) bounds.union(node.bounds);
  const span = bounds.getSize(new T.Vector3());
  const axis = span.x > span.y && span.x > span.z ? 'x' : span.y > span.z ? 'y' : 'z';
  const center = (node: Cluster) => node.bounds.min[axis] + node.bounds.max[axis];
  leaves.sort((a, b) => center(a) - center(b));
  const half = leaves.length >> 1;
  const children: [Cluster, Cluster] = [
    buildClusters(leaves.slice(0, half)),
    buildClusters(leaves.slice(half)),
  ];
  const node: Cluster = { bounds, children };
  for (const child of children) child.parent = node;
  return node;
}

export function roomPicking(roots: T.Object3D[], defer?: (work: () => void) => void) {
  let objects: T.Mesh[] = [];
  let surfaces: Surface[] = [];
  let exceptions: number[] = [];
  let tree: Cluster | undefined;
  let dirty = true;
  let revision = 0;
  let scheduled = false;
  let disposed = false;
  const listeners = new Set<T.Object3D>();
  const rootSet = new Set(roots);
  const sources = new WeakMap<T.BufferGeometry, Pick<Surface, 'position' | 'version'>>();
  const cached = new WeakMap<T.Mesh, Surface>();
  const entry = new T.Vector3();
  const hits: T.Intersection[] = [];
  const markDirty = () => {
    dirty = true;
    revision++;
    schedule();
  };

  function schedule() {
    if (!defer || scheduled || disposed) return;
    scheduled = true;
    defer(() => {
      if (!disposed && dirty) rebuild();
    });
  }

  function detach() {
    for (const object of listeners) {
      object.removeEventListener('childadded', markDirty);
      object.removeEventListener('childremoved', markDirty);
    }
    listeners.clear();
  }

  function localBox(geometry: T.BufferGeometry, position: Surface['position'], version: number) {
    const known = sources.get(geometry);
    const edited = known && (known.position !== position || known.version !== version);
    if (edited && geometry.boundingSphere) geometry.computeBoundingSphere();
    if (!geometry.boundingBox || edited) geometry.computeBoundingBox();
    if (!known || known.position !== position || known.version !== version)
      sources.set(geometry, { position, version });
    return geometry.boundingBox!;
  }

  function currentSurface(object: T.Mesh) {
    const geometry = object.geometry;
    const position = geometry.attributes.position;
    if (
      !position?.count ||
      object.raycast !== T.Mesh.prototype.raycast ||
      object.morphTargetInfluences
    )
      return;
    const version = positionVersion(position);
    let surface = cached.get(object);
    if (!surface || surface.geometry !== geometry || surface.position !== position) {
      const world = object.matrixWorld.clone();
      const bounds = localBox(geometry, position, version)
        .clone()
        .applyMatrix4(world)
        .expandByScalar(1e-6);
      surface = { object, geometry, position, version, world, cluster: { bounds } };
      cached.set(object, surface);
    } else if (surface.version !== version || !surface.world.equals(object.matrixWorld)) {
      surface.version = version;
      surface.world.copy(object.matrixWorld);
      surface.cluster.bounds
        .copy(localBox(geometry, position, version))
        .applyMatrix4(surface.world)
        .expandByScalar(1e-6);
      for (let node = surface.cluster.parent; node; node = node.parent) {
        const [a, b] = node.children!;
        node.bounds.copy(a.bounds).union(b.bounds);
      }
    }
    return surface;
  }

  function rebuild() {
    const generation = revision;
    const previousListeners = new Set(listeners);
    const stack = [...roots].reverse();
    const forest: Cluster[] = [];
    let pending: Cluster[] = [];
    objects = [];
    surfaces = [];
    exceptions = [];
    function collect(object: T.Object3D) {
      previousListeners.delete(object);
      if (!listeners.has(object)) {
        object.addEventListener('childadded', markDirty);
        object.addEventListener('childremoved', markDirty);
        listeners.add(object);
      }
      if (!(object instanceof T.Mesh)) return;
      const index = objects.push(object) - 1;
      const surface = currentSurface(object);
      if (!surface) {
        exceptions.push(index);
        return;
      }
      surface.cluster.index = index;
      surface.cluster.parent = undefined;
      surfaces.push(surface);
      pending.push(surface.cluster);
      if (pending.length === 64) {
        forest.push(buildClusters(pending));
        pending = [];
      }
    }
    function step() {
      if (disposed) return;
      if (revision !== generation) {
        scheduled = false;
        schedule();
        return;
      }
      const deadline = performance.now() + 3;
      let count = 0;
      do {
        const node = stack.pop();
        if (!node) break;
        collect(node);
        for (let i = node.children.length - 1; i >= 0; i--) stack.push(node.children[i]);
        count++;
      } while (!defer || (count < 512 && performance.now() < deadline));
      if (stack.length && defer) {
        defer(step);
        return;
      }
      if (pending.length) forest.push(buildClusters(pending));
      tree = forest.length ? buildClusters(forest) : undefined;
      for (const node of previousListeners) {
        node.removeEventListener('childadded', markDirty);
        node.removeEventListener('childremoved', markDirty);
        listeners.delete(node);
      }
      dirty = false;
      scheduled = false;
    }
    step();
  }

  function refresh() {
    if (dirty) {
      if (defer) return false;
      rebuild();
      return true;
    }
    for (const surface of surfaces) {
      if (currentSurface(surface.object) !== surface) {
        markDirty();
        return refresh();
      }
    }
    return true;
  }

  function closest(ray: T.Raycaster, held?: T.Object3D) {
    const indexed = refresh();
    const limit = ray.far;
    let winner: T.Object3D | undefined;
    let order = Infinity;
    function hit(mesh: T.Mesh, index: number) {
      if (
        !ray.layers.test(mesh.layers) ||
        (mesh.material instanceof T.MeshBasicMaterial && mesh.material.transparent)
      )
        return;
      hits.length = 0;
      mesh.raycast(ray, hits);
      for (const intersection of hits) {
        if (
          intersection.distance < ray.far ||
          (winner && intersection.distance === ray.far && index < order)
        ) {
          winner = intersection.object;
          order = index;
          ray.far = intersection.distance;
        }
      }
    }
    function candidate(index: number) {
      const object = objects[index];
      for (let node: T.Object3D | null = object; node; node = node.parent) {
        if (!node.visible || node === held) return;
        if (rootSet.has(node)) break;
      }
      hit(object, index);
    }
    function distanceSquared(bounds: T.Box3) {
      if (bounds.containsPoint(ray.ray.origin)) return 0;
      return ray.ray.intersectBox(bounds, entry)
        ? entry.distanceToSquared(ray.ray.origin)
        : Infinity;
    }
    function visit(node: Cluster, distance: number) {
      if (distance === Infinity || distance > ray.far * ray.far) return;
      if (node.children) {
        const [a, b] = node.children;
        const aDistance = distanceSquared(a.bounds),
          bDistance = distanceSquared(b.bounds);
        if (aDistance <= bDistance) {
          visit(a, aDistance);
          visit(b, bDistance);
        } else {
          visit(b, bDistance);
          visit(a, aDistance);
        }
      } else candidate(node.index!);
    }
    held?.traverseVisible((object) => {
      if (object instanceof T.Mesh) hit(object, -1);
    });
    if (indexed) {
      if (tree) visit(tree, distanceSquared(tree.bounds));
      for (const index of exceptions) candidate(index);
    } else {
      let index = 0;
      const pending: { mesh: T.Mesh; order: number; distance: number }[] = [];
      const native: { mesh: T.Mesh; order: number }[] = [];
      function walk(object: T.Object3D) {
        if (!object.visible || object === held) return;
        if (object instanceof T.Mesh) {
          const order = index++;
          const surface = currentSurface(object);
          if (surface) {
            const distance = distanceSquared(surface.cluster.bounds);
            if (distance !== Infinity && distance <= ray.far * ray.far)
              pending.push({ mesh: object, order, distance });
          } else native.push({ mesh: object, order });
        }
        for (const child of object.children) walk(child);
      }
      roots.forEach(walk);
      pending.sort((a, b) => a.distance - b.distance);
      for (const item of pending) {
        if (item.distance > ray.far * ray.far) break;
        hit(item.mesh, item.order);
      }
      for (const item of native) hit(item.mesh, item.order);
    }
    ray.far = limit;
    return winner;
  }
  schedule();
  return {
    closest,
    dispose() {
      disposed = true;
      detach();
    },
  };
}
