import {
  BackSide,
  LessEqualDepth,
  Mesh,
  MeshDepthMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
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
const screen = 'LG OLED active pixels and clock';

function compatible(mesh: Mesh) {
  if (
    mesh.constructor !== Mesh ||
    mesh.onBeforeRender !== Object3D.prototype.onBeforeRender ||
    mesh.onAfterRender !== Object3D.prototype.onAfterRender ||
    mesh.customDepthMaterial ||
    mesh.geometry.morphAttributes.position?.length
  )
    return false;
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  return materials.every(
    (material) =>
      material instanceof MeshStandardMaterial &&
      (mesh.name === screen || material.userData.studioMatte === true) &&
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

export function roomDepthPrefill() {
  const depth = new MeshDepthMaterial({
    colorWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 4,
  });
  depth.name = 'Studio depth prefill';
  const center = new Vector3();
  const size = new Vector2();
  const viewport = new Vector4();
  const candidates: Mesh[] = [];
  const visible: { mesh: Mesh; coverage: number; triangles: number }[] = [];
  const enabled: { mesh: Mesh; mask: number }[] = [];
  let view: Scene | undefined;
  let revision = -1;
  let occupied = false;

  function select(scene: Scene, camera: PerspectiveCamera, detailRevision: number) {
    if (scene !== view || revision !== detailRevision) {
      view = scene;
      revision = detailRevision;
      candidates.length = 0;
      occupied = false;
      scene.traverse((object) => {
        occupied ||= Boolean(object.layers.mask & depthMask);
        if (object instanceof Mesh && compatible(object)) candidates.push(object);
      });
    }
    if (occupied) return;
    for (const mesh of candidates) {
      if (!mesh.layers.test(camera.layers) || !compatible(mesh)) continue;
      const count = triangles(mesh);
      if (!count || count > 4096) continue;
      if (!mesh.geometry.boundingSphere) mesh.geometry.computeBoundingSphere();
      const sphere = mesh.geometry.boundingSphere!;
      center
        .copy(sphere.center)
        .applyMatrix4(mesh.matrixWorld)
        .applyMatrix4(camera.matrixWorldInverse);
      const radius = sphere.radius * mesh.matrixWorld.getMaxScaleOnAxis();
      if (radius - center.z < camera.near) continue;
      const coverage = radius / Math.max(camera.near, -center.z);
      if (coverage < 0.17) continue;
      let ancestor: Object3D | null = mesh;
      while (ancestor?.visible && ancestor !== scene) ancestor = ancestor.parent;
      if (ancestor === scene) visible.push({ mesh, coverage, triangles: count });
    }
    visible.sort((a, b) => b.coverage - a.coverage);
    let total = 0;
    for (const item of visible) {
      if (enabled.length >= meshLimit) break;
      if (total + item.triangles > triangleLimit) continue;
      enabled.push({ mesh: item.mesh, mask: item.mesh.layers.mask });
      item.mesh.layers.enable(depthLayer);
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
          camera.layers.set(depthLayer);
          scene.overrideMaterial = depth;
          renderer.clear(renderer.autoClearColor, true, renderer.autoClearStencil);
          renderer.render(scene, camera);
        } finally {
          for (const { mesh, mask } of enabled) mesh.layers.mask = mask;
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
