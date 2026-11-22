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
  const mapping = { value: T.NoToneMapping as T.ToneMapping };
  const exposure = { value: 1 };
  const material = new T.RawShaderMaterial({
    ...options,
    glslVersion: T.GLSL3,
    uniforms: {
      ...options.uniforms,
      encodeRoomColor: encode,
      roomToneMapping: mapping,
      toneMappingExposure: exposure,
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
      uniform int roomToneMapping;
      ${fragmentInputs}
      #include <colorspace_pars_fragment>
      #include <tonemapping_pars_fragment>
      vec4 linearToOutputTexel(vec4 color) {
        return encodeRoomColor ? sRGBTransferOETF(color) : color;
      }
      vec3 toneMapping(vec3 color) {
        if (roomToneMapping == ${T.ACESFilmicToneMapping}) return ACESFilmicToneMapping(color);
        if (roomToneMapping == ${T.LinearToneMapping}) return LinearToneMapping(color);
        if (roomToneMapping == ${T.ReinhardToneMapping}) return ReinhardToneMapping(color);
        if (roomToneMapping == ${T.CineonToneMapping}) return CineonToneMapping(color);
        if (roomToneMapping == ${T.AgXToneMapping}) return AgXToneMapping(color);
        if (roomToneMapping == ${T.NeutralToneMapping}) return NeutralToneMapping(color);
        return color;
      }
      #define TONE_MAPPING
      ${options.fragmentShader}
    `,
  });
  material.onBeforeRender = (renderer) => {
    const onscreen = renderer.getRenderTarget() === null;
    encode.value =
      onscreen && T.ColorManagement.getTransfer(renderer.outputColorSpace) === T.SRGBTransfer;
    mapping.value = onscreen && material.toneMapped ? renderer.toneMapping : T.NoToneMapping;
    exposure.value = renderer.toneMappingExposure;
  };
  return material;
}
