import * as T from 'three';

export function roomEffectMaterial(
  options: T.ShaderMaterialParameters,
  vertexInputs: string,
  fragmentInputs = '',
) {
  if (
    typeof location === 'undefined' ||
    new URLSearchParams(location.search).get('studio-effects') !== 'stable'
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
