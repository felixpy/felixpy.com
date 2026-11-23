import * as T from 'three';
import { roomFov, windowEye } from '../camera';
import { waterfrontFarClip } from '../window-depth';

type Calibration = {
  origin: number[];
  camera: number[];
  direction: number[];
  fov: number;
  far: number;
};

function chart(source: T.Mesh, origin: T.Vector3) {
  const geometry = source.geometry.clone();
  const positions = geometry.getAttribute('position');
  const vertex = new T.Vector3();
  const uvs = new T.Float32BufferAttribute(new Float32Array(positions.count * 2), 2);
  let left = Infinity,
    right = -Infinity,
    bottom = Infinity,
    top = -Infinity;
  for (let i = 0; i < positions.count; i++) {
    vertex
      .fromBufferAttribute(positions, i)
      .applyMatrix4(source.matrixWorld)
      .sub(origin)
      .normalize();
    const yaw = Math.atan2(-vertex.z, -vertex.x);
    const pitch = Math.asin(T.MathUtils.clamp(vertex.y, -1, 1));
    left = Math.min(left, yaw);
    right = Math.max(right, yaw);
    bottom = Math.min(bottom, pitch);
    top = Math.max(top, pitch);
    uvs.setXY(i, yaw, pitch);
  }
  for (let i = 0; i < positions.count; i++)
    uvs.setXY(i, (uvs.getX(i) - left) / (right - left), (top - uvs.getY(i)) / (top - bottom));
  geometry.setAttribute('uv', uvs);
  return geometry;
}

function applyDepthChart(
  geometry: T.BufferGeometry,
  world: T.Matrix4,
  origin: T.Vector3,
  pixels: Uint8Array,
  width: number,
  height: number,
) {
  const positions = geometry.getAttribute('position');
  const uvs = geometry.getAttribute('uv');
  const point = new T.Vector3(),
    inverse = world.clone().invert();
  for (let i = 0; i < positions.count; i++) {
    const x = Math.round(uvs.getX(i) * (width - 1));
    const y = Math.round((1 - uvs.getY(i)) * (height - 1));
    const encoded = pixels[4 * (y * width + x) + 3] / 255;
    const distance = Math.max(1, (1 + waterfrontFarClip) ** encoded - 1);
    point
      .fromBufferAttribute(positions, i)
      .applyMatrix4(world)
      .sub(origin)
      .setLength(distance)
      .add(origin)
      .applyMatrix4(inverse);
    positions.setXYZ(i, point.x, point.y, point.z);
  }
  positions.needsUpdate = true;
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
}

export function bakeWaterfront(renderer: T.WebGLRenderer, source: T.Mesh, width = 4096) {
  const live = source.material;
  if (
    !(live instanceof T.ShaderMaterial) ||
    !live.uniforms.photoA.value?.image ||
    !live.uniforms.depthA.value?.image
  )
    throw new Error('The waterfront photographs must finish loading before export.');
  source.updateWorldMatrix(true, false);
  const origin = live.uniforms.captureOrigin.value as T.Vector3;
  const geometry = chart(source, origin);
  const camera = new T.PerspectiveCamera(roomFov, 1, 0.028, waterfrontFarClip);
  camera.position.copy(origin);
  camera.rotation.set(windowEye.pitch, windowEye.yaw, 0, 'YXZ');
  camera.updateMatrixWorld();
  const material = new T.ShaderMaterial({
    uniforms: { ...live.uniforms, bakeDepth: { value: true } },
    side: T.DoubleSide,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
    vertexShader: `
      varying vec3 shellPoint;
      void main() {
        shellPoint = (modelMatrix * vec4(position, 1.0)).xyz;
        gl_Position = vec4(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0, 0.0, 1.0);
      }`,
    fragmentShader:
      'uniform bool bakeDepth;\n' +
      live.fragmentShader.replace(
        '#include <colorspace_fragment>',
        `gl_FragColor = sRGBTransferOETF(gl_FragColor);
       if (bakeDepth) gl_FragColor.a = log2(1.0 + clamp(distance, 0.0, ${waterfrontFarClip}.0)) / log2(1.0 + ${waterfrontFarClip}.0);`,
      ),
  });
  const surface = new T.Mesh(geometry, material);
  surface.frustumCulled = false;
  surface.matrixAutoUpdate = false;
  surface.matrix.copy(source.matrixWorld);
  const stage = new T.Scene();
  stage.add(surface);
  const height = width / 2;
  const depthWidth = Math.min(width, 1024),
    depthHeight = depthWidth / 2;
  const target = new T.WebGLRenderTarget(depthWidth, depthHeight, { depthBuffer: false });
  const previous = renderer.getRenderTarget();
  const face = renderer.getActiveCubeFace(),
    mip = renderer.getActiveMipmapLevel();
  const viewport = renderer.getViewport(new T.Vector4());
  const scissor = renderer.getScissor(new T.Vector4()),
    scissorTest = renderer.getScissorTest();
  const pixels = new Uint8Array(width * height * 4);
  try {
    renderer.setRenderTarget(target);
    renderer.setScissorTest(false);
    renderer.render(stage, camera);
    renderer.readRenderTargetPixels(target, 0, 0, depthWidth, depthHeight, pixels);
    applyDepthChart(geometry, source.matrixWorld, origin, pixels, depthWidth, depthHeight);
    material.uniforms.bakeDepth.value = false;
    target.setSize(width, height);
    renderer.setRenderTarget(target);
    renderer.render(stage, camera);
    renderer.readRenderTargetPixels(target, 0, 0, width, height, pixels);
  } finally {
    renderer.setRenderTarget(previous, face, mip);
    renderer.setViewport(viewport);
    renderer.setScissor(scissor);
    renderer.setScissorTest(scissorTest);
    target.dispose();
    material.dispose();
  }
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d')!;
  const image = context.createImageData(width, height);
  const stride = width * 4;
  for (let y = 0; y < height; y++)
    image.data.set(pixels.subarray((height - 1 - y) * stride, (height - y) * stride), y * stride);
  context.putImageData(image, 0, 0);
  const map = new T.CanvasTexture(canvas);
  map.name = 'Waterfront photographic exposure';
  map.flipY = false;
  map.colorSpace = T.SRGBColorSpace;
  map.userData.mimeType = 'image/jpeg';
  const unlit = new T.MeshBasicMaterial({ map, side: T.DoubleSide, toneMapped: false });
  unlit.name = 'Window view · photographed river and banks';
  const calibration: Calibration = {
    origin: origin.toArray(),
    camera: [windowEye.x, windowEye.y, windowEye.z],
    direction: camera.getWorldDirection(new T.Vector3()).toArray(),
    fov: roomFov,
    far: waterfrontFarClip,
  };
  return { geometry, material: unlit, calibration, width };
}
