import {
  BackSide,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  PerspectiveCamera,
  SphereGeometry,
  Vector4,
  type Camera,
  type Scene,
  type WebGLRenderer,
} from 'three';

export const roomSkyName = 'Studio room sky';

function isCentered(object: Object3D) {
  const { scale } = object;
  return (
    object.matrixAutoUpdate &&
    object.matrixWorldAutoUpdate &&
    object.position.lengthSq() === 0 &&
    scale.x === 1 &&
    scale.y === 1 &&
    scale.z === 1
  );
}

function isFlatSky(material: MeshBasicMaterial) {
  return (
    material.visible &&
    material.colorWrite &&
    material.side === BackSide &&
    material.opacity === 1 &&
    !material.transparent &&
    !material.toneMapped &&
    !material.depthWrite &&
    !material.stencilWrite &&
    !material.dithering &&
    !material.vertexColors &&
    !material.wireframe &&
    !material.map &&
    !material.envMap &&
    !material.lightMap &&
    !material.aoMap &&
    !material.alphaMap &&
    !material.alphaTest &&
    !material.alphaHash &&
    !material.alphaToCoverage &&
    !material.clippingPlanes?.length &&
    material.onBeforeCompile === MeshBasicMaterial.prototype.onBeforeCompile
  );
}

function coversCamera(camera: Camera, radius: number, innerRadius: number) {
  if (
    !(camera instanceof PerspectiveCamera) ||
    camera.parent ||
    !camera.matrixAutoUpdate ||
    !camera.matrixWorldAutoUpdate ||
    camera.view?.enabled ||
    camera.filmOffset !== 0 ||
    camera.near <= 0
  )
    return false;
  const projection = camera.projectionMatrix.elements;
  if (
    projection[0] <= 0 ||
    projection[5] <= 0 ||
    projection[8] !== 0 ||
    projection[9] !== 0 ||
    projection[11] !== -1 ||
    projection[15] !== 0
  )
    return false;
  const distance = camera.position.length();
  const nearRadius = camera.near * Math.hypot(1, 1 / projection[0], 1 / projection[5]);
  return distance + nearRadius < innerRadius && radius + distance < camera.far;
}

export function roomSkyClear(scene: Scene) {
  const sky = scene.getObjectByName(roomSkyName);
  if (!(sky instanceof Mesh)) return;
  const { parent, material, geometry } = sky;
  if (
    !parent ||
    parent.parent !== scene ||
    !(material instanceof MeshBasicMaterial) ||
    !(geometry instanceof SphereGeometry)
  )
    return;
  const { radius, widthSegments, heightSegments, phiLength, thetaStart, thetaLength } =
    geometry.parameters;
  if (phiLength !== 2 * Math.PI || thetaStart !== 0 || thetaLength !== Math.PI) return;
  const innerRadius = radius * Math.cos((2 * Math.PI) / widthSegments + Math.PI / heightSegments);
  const viewport = new Vector4();
  let applied = false;

  return (renderer: WebGLRenderer, camera: Camera) => {
    const target = renderer.getRenderTarget();
    if (
      !target ||
      target.scissorTest ||
      renderer.getScissorTest() ||
      renderer.clippingPlanes.length ||
      renderer.xr.isPresenting ||
      !renderer.autoClear ||
      !renderer.autoClearColor ||
      !renderer.autoClearDepth ||
      scene.background ||
      scene.fog ||
      scene.overrideMaterial ||
      !scene.visible ||
      !parent.visible ||
      !sky.visible ||
      sky.parent !== parent ||
      parent.parent !== scene ||
      sky.material !== material ||
      sky.geometry !== geometry ||
      sky.renderOrder !== -10 ||
      sky.onBeforeRender !== Object3D.prototype.onBeforeRender ||
      sky.onAfterRender !== Object3D.prototype.onAfterRender ||
      !camera.layers.test(sky.layers) ||
      !isCentered(sky) ||
      !isCentered(parent) ||
      !isCentered(scene) ||
      !isFlatSky(material) ||
      !coversCamera(camera, radius, innerRadius)
    ) {
      renderer.render(scene, camera);
      return;
    }
    renderer.getCurrentViewport(viewport);
    if (viewport.x || viewport.y || viewport.z !== target.width || viewport.w !== target.height) {
      renderer.render(scene, camera);
      return;
    }

    sky.visible = false;
    scene.background = material.color;
    try {
      renderer.render(scene, camera);
    } finally {
      scene.background = null;
      sky.visible = true;
    }
    if (!applied) {
      applied = true;
      performance.mark('studio-sky-clear-applied');
    }
  };
}
