import * as T from 'three';

export function roomEffectMaterial(
  options: T.ShaderMaterialParameters,
  vertexInputs: string,
  fragmentInputs = '',
  reuseAcrossTargets = false,
) {
  const query = typeof location === 'undefined' ? null : new URLSearchParams(location.search);
  if (
    !reuseAcrossTargets &&
    query?.get('studio-effects') !== 'stable' &&
    query?.get('studio-waterfront') !== 'warm'
  ) {
    return new T.ShaderMaterial(options);
  }
  const encode = { value: false };
  const material = new T.RawShaderMaterial({
    ...options,
    glslVersion: T.GLSL3,
    uniforms: {
      ...options.uniforms,
      encodeRoomColor: encode,
    },
    vertexShader: `
      precision highp float;
      precision highp int;
      #define attribute in
      #define varying out
      ${vertexInputs}
      ${options.vertexShader}
    `,
    fragmentShader: `
      precision highp float;
      precision highp int;
      #define varying in
      #define texture2D texture
      out vec4 roomEffectColor;
      #define gl_FragColor roomEffectColor
      uniform bool encodeRoomColor;
      ${fragmentInputs}
      #include <colorspace_pars_fragment>
      vec4 linearToOutputTexel(vec4 color) {
        return encodeRoomColor ? sRGBTransferOETF(color) : color;
      }
      ${options.fragmentShader}
    `,
  });
  material.onBeforeRender = (renderer) => {
    const onscreen = renderer.getRenderTarget() === null;
    encode.value =
      onscreen && T.ColorManagement.getTransfer(renderer.outputColorSpace) === T.SRGBTransfer;
  };
  return material;
}

export async function warmRoomEffect(
  gl: T.WebGLRenderer,
  material: T.Material,
  signal: AbortSignal,
) {
  if (signal.aborted || gl.getContext().isContextLost()) return false;
  const geometry = new T.PlaneGeometry(2, 2);
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera();
  camera.position.z = 1;
  scene.add(new T.Mesh(geometry, material));
  const target = new T.WebGLRenderTarget(1, 1);
  try {
    const linking = gl.compileAsync(scene, camera);
    gl.getContext().flush();
    await linking;
    if (signal.aborted) return false;
    const previous = gl.getRenderTarget();
    try {
      gl.setRenderTarget(target);
      gl.render(scene, camera);
      return true;
    } finally {
      gl.setRenderTarget(previous);
    }
  } catch {
    return false;
  } finally {
    geometry.dispose();
    target.dispose();
  }
}
