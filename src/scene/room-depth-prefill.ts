import {
  BackSide,
  FrontSide,
  Frustum,
  InstancedBufferGeometry,
  LessEqualDepth,
  Material,
  Matrix4,
  Mesh,
  MeshDepthMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  NoBlending,
  NormalBlending,
  Object3D,
  PerspectiveCamera,
  Vector2,
  Vector3,
  Vector4,
  type Camera,
  type Scene,
  type WebGLRenderer,
} from 'three';

const depthLayer = 31;
const depthMask = 1 << depthLayer;
const triangleLimit = 16_384;
const meshLimit = 40;
const wideTriangleLimit = 96_000;
const wideMeshLimit = 96;
const wideMeshTriangleLimit = 24_000;
const screen = 'LG OLED active pixels and clock';
const standardDepthHooks = new WeakSet<Material['onBeforeCompile']>();

export function hasStandardRoomDepth(material: Material) {
  const hook = material.onBeforeCompile;
  return hook === Material.prototype.onBeforeCompile || standardDepthHooks.has(hook);
}

export function markStandardRoomDepth(material: Material) {
  standardDepthHooks.add(material.onBeforeCompile);
}

function compatible(mesh: Mesh, wide: boolean) {
  if (
    mesh.constructor !== Mesh ||
    mesh.onBeforeRender !== Object3D.prototype.onBeforeRender ||
    mesh.onAfterRender !== Object3D.prototype.onAfterRender ||
    mesh.customDepthMaterial ||
    mesh.geometry.morphAttributes.position?.length ||
    (wide &&
      (Array.isArray(mesh.material) ||
        mesh.geometry instanceof InstancedBufferGeometry ||
        mesh.renderOrder !== 0 ||
        !mesh.frustumCulled))
  )
    return false;
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  return materials.every(
    (material) =>
      material instanceof MeshStandardMaterial &&
      (wide
        ? material.side === FrontSide &&
          material.allowOverride &&
          material.precision === null &&
          (material.blending === NormalBlending || material.blending === NoBlending) &&
          (!material.defines ||
            Object.entries(material.defines).every(
              ([key, value]) => (key === 'STANDARD' || key === 'PHYSICAL') && value === '',
            )) &&
          hasStandardRoomDepth(material)
        : mesh.name === screen || material.userData.studioMatte === true) &&
      material.visible &&
      !material.transparent &&
      material.opacity === 1 &&
      material.side !== BackSide &&
      material.depthTest &&
      material.depthWrite &&
      material.depthFunc === LessEqualDepth &&
      !material.alphaTest &&
      !material.alphaMap &&
      !material.alphaHash &&
      !material.alphaToCoverage &&
      !material.displacementMap &&
      !material.clippingPlanes?.length &&
      !material.polygonOffset &&
      !material.stencilWrite &&
      !material.wireframe &&
      material.colorWrite &&
      (!(material instanceof MeshPhysicalMaterial) || material.transmission === 0),
  );
}

function triangles(mesh: Mesh) {
  const { index, attributes, drawRange, groups } = mesh.geometry;
  const vertices = index?.count ?? attributes.position?.count ?? 0;
  const end = Math.min(vertices, drawRange.start + drawRange.count);
  if (!Array.isArray(mesh.material)) return Math.floor(Math.max(0, end - drawRange.start) / 3);
  return groups.reduce((total, group) => {
    const start = Math.max(group.start, drawRange.start);
    const limit = Math.min(group.start + group.count, end);
    return total + Math.floor(Math.max(0, limit - start) / 3);
  }, 0);
}

export function roomDepthPrefill({ wide = false }: { wide?: boolean } = {}) {
  const depth = new MeshDepthMaterial({
    colorWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 4,
  });
  depth.name = 'Studio depth prefill';
  const center = new Vector3();
  const corner = new Vector3();
  const frustum = new Frustum();
  const viewProjection = new Matrix4();
  const modelView = new Matrix4();
  const size = new Vector2();
  const viewport = new Vector4();
  const candidates: Mesh[] = [];
  const visible: { mesh: Mesh; coverage: number; triangles: number }[] = [];
  const enabled: { mesh: Mesh; mask: number; order: number }[] = [];
  let view: Scene | undefined;
  let revision = -1;
  let occupied = false;

  function wideCoverage(mesh: Mesh, camera: PerspectiveCamera, count: number) {
    const { geometry } = mesh;
    if (!geometry.boundingSphere || !frustum.intersectsObject(mesh)) return 0;
    if (!geometry.boundingBox) geometry.computeBoundingBox();
    const bounds = geometry.boundingBox!;
    if (bounds.isEmpty()) return 0;
    modelView.multiplyMatrices(camera.matrixWorldInverse, mesh.matrixWorld);
    let left = 1,
      right = -1,
      bottom = 1,
      top = -1,
      nearest = Infinity;
    for (let i = 0; i < 8; i++) {
      corner
        .set(
          i & 1 ? bounds.max.x : bounds.min.x,
          i & 2 ? bounds.max.y : bounds.min.y,
          i & 4 ? bounds.max.z : bounds.min.z,
        )
        .applyMatrix4(modelView);
      const distance = -corner.z;
      if (distance <= camera.near) return 0;
      nearest = Math.min(nearest, distance);
      corner.applyMatrix4(camera.projectionMatrix);
      left = Math.min(left, corner.x);
      right = Math.max(right, corner.x);
      bottom = Math.min(bottom, corner.y);
      top = Math.max(top, corner.y);
    }
    const area =
      Math.max(0, Math.min(1, right) - Math.max(-1, left)) *
      Math.max(0, Math.min(1, top) - Math.max(-1, bottom));
    return area >= 0.002 ? area / ((256 + count) * nearest) : 0;
  }

  function coarseCoverage(mesh: Mesh, camera: PerspectiveCamera) {
    if (!mesh.geometry.boundingSphere) mesh.geometry.computeBoundingSphere();
    const sphere = mesh.geometry.boundingSphere!;
    center
      .copy(sphere.center)
      .applyMatrix4(mesh.matrixWorld)
      .applyMatrix4(camera.matrixWorldInverse);
    const radius = sphere.radius * mesh.matrixWorld.getMaxScaleOnAxis();
    if (radius - center.z < camera.near) return 0;
    const coverage = radius / Math.max(camera.near, -center.z);
    return coverage < 0.17 ? 0 : coverage;
  }

  function select(scene: Scene, camera: PerspectiveCamera, detailRevision: number) {
    if (scene !== view || revision !== detailRevision) {
      view = scene;
      revision = detailRevision;
      candidates.length = 0;
      occupied = false;
      scene.traverse((object) => {
        occupied ||= Boolean(object.layers.mask & depthMask);
        if (object instanceof Mesh && compatible(object, wide)) candidates.push(object);
      });
    }
    if (occupied) return;
    if (wide) {
      camera.updateWorldMatrix(true, false);
      frustum.setFromProjectionMatrix(
        viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse),
      );
    }
    for (const mesh of candidates) {
      if (!mesh.layers.test(camera.layers) || !compatible(mesh, wide)) continue;
      const count = triangles(mesh);
      if (!count || count > (wide ? wideMeshTriangleLimit : 4096)) continue;
      let ancestor: Object3D | null = mesh;
      while (ancestor?.visible && ancestor !== scene && (!wide || ancestor.renderOrder === 0))
        ancestor = ancestor.parent;
      if (ancestor !== scene) continue;
      const coverage = wide ? wideCoverage(mesh, camera, count) : coarseCoverage(mesh, camera);
      if (coverage) visible.push({ mesh, coverage, triangles: count });
    }
    visible.sort((a, b) => b.coverage - a.coverage);
    let total = 0;
    for (const item of visible) {
      if (enabled.length >= (wide ? wideMeshLimit : meshLimit)) break;
      if (total + item.triangles > (wide ? wideTriangleLimit : triangleLimit)) continue;
      enabled.push({ mesh: item.mesh, mask: item.mesh.layers.mask, order: item.mesh.renderOrder });
      total += item.triangles;
    }
    visible.length = 0;
  }

  return {
    render(renderer: WebGLRenderer, scene: Scene, camera: Camera, detailRevision: number) {
      renderer.getSize(size);
      renderer.getViewport(viewport);
      if (
        camera instanceof PerspectiveCamera &&
        !(camera.layers.mask & depthMask) &&
        !camera.view?.enabled &&
        camera.filmOffset === 0 &&
        !scene.background &&
        !scene.overrideMaterial &&
        renderer.autoClear &&
        renderer.autoClearDepth &&
        !renderer.getRenderTarget() &&
        !renderer.getScissorTest() &&
        !renderer.clippingPlanes.length &&
        !renderer.shadowMap.enabled &&
        !renderer.xr.isPresenting &&
        !renderer.capabilities.reversedDepthBuffer &&
        !renderer.capabilities.logarithmicDepthBuffer &&
        viewport.x === 0 &&
        viewport.y === 0 &&
        viewport.z === size.x &&
        viewport.w === size.y
      )
        select(scene, camera, detailRevision);
      if (!enabled.length) {
        renderer.render(scene, camera);
        return;
      }
      const mask = camera.layers.mask;
      renderer.autoClear = false;
      try {
        try {
          for (const [index, { mesh }] of enabled.entries()) {
            mesh.layers.enable(depthLayer);
            if (wide) mesh.renderOrder = index;
          }
          camera.layers.set(depthLayer);
          scene.overrideMaterial = depth;
          renderer.clear(renderer.autoClearColor, true, renderer.autoClearStencil);
          renderer.render(scene, camera);
        } finally {
          for (const { mesh, mask, order } of enabled) {
            mesh.layers.mask = mask;
            if (wide) mesh.renderOrder = order;
          }
          enabled.length = 0;
          camera.layers.mask = mask;
          scene.overrideMaterial = null;
        }
        renderer.render(scene, camera);
      } finally {
        renderer.autoClear = true;
      }
    },
    dispose() {
      candidates.length = 0;
      depth.dispose();
    },
  };
}
