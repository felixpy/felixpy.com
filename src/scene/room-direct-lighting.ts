import { ShaderChunk } from 'three';
import { leanRoomPhysicalLighting, leanRoomPunctualLighting } from './room-lean-lighting';

function localLightRejection(light: string) {
  return `
    vec3 lVector = ${light}.position - geometryPosition;
    if (${light}.color == vec3(0.0) ||
        (${light}.distance > 0.0 && dot(lVector, lVector) > ${light}.distance * ${light}.distance)) {
      light.direction = vec3(0.0, 1.0, 0.0);
      light.color = vec3(0.0);
      light.visible = false;
      return;
    }
  `;
}

const punctualLighting = ShaderChunk.lights_pars_begin
  .replace(
    'vec3 lVector = pointLight.position - geometryPosition;',
    localLightRejection('pointLight'),
  )
  .replace(
    'vec3 lVector = spotLight.position - geometryPosition;',
    localLightRejection('spotLight'),
  );

const physicalLighting = ShaderChunk.lights_physical_pars_fragment.replace(
  'float dotNL = saturate( dot( geometryNormal, directLight.direction ) );',
  `
    if (directLight.color == vec3(0.0)) return;
    float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
    #ifdef USE_CLEARCOAT
      if (dotNL == 0.0 && dot(geometryClearcoatNormal, directLight.direction) <= 0.0) return;
    #else
      if (dotNL == 0.0) return;
    #endif
  `,
);

const leanPunctual = leanRoomPunctualLighting(punctualLighting);
const leanPhysical = leanRoomPhysicalLighting(physicalLighting);

export function cullRoomDirectLighting(
  fragmentShader: string,
  lightEvaluation: string,
  lean = false,
) {
  return fragmentShader
    .replace('#include <lights_pars_begin>', lean ? leanPunctual : punctualLighting)
    .replace('#include <lights_physical_pars_fragment>', lean ? leanPhysical : physicalLighting)
    .replace(
      '#include <lights_fragment_begin>',
      lightEvaluation.replace(
        'RE_Direct_RectArea( rectAreaLight,',
        'if (rectAreaLight.color != vec3(0.0)) RE_Direct_RectArea( rectAreaLight,',
      ),
    );
}
