const distanceAttenuation = `
float studioDistanceAttenuation(vec3 offset, float range, float decay) {
  if (decay != 2.0) return getDistanceAttenuation(length(offset), range, decay);
  float distanceSquared = dot(offset, offset);
  float attenuation = 1.0 / max(distanceSquared, 0.01);
  if (range > 0.0) {
    float ratioSquared = distanceSquared / (range * range);
    attenuation *= pow2(saturate(1.0 - ratioSquared * ratioSquared));
  }
  return attenuation;
}
`;

const rectDiffuse = `
float studioRectDiffuse(vec3 normal, vec3 position, vec3 corners[4]) {
  vec3 a = normalize(corners[0] - position);
  vec3 b = normalize(corners[1] - position);
  vec3 c = normalize(corners[2] - position);
  vec3 d = normalize(corners[3] - position);
  vec3 form = -(LTC_EdgeVectorFormFactor(a, b) + LTC_EdgeVectorFormFactor(b, c)
    + LTC_EdgeVectorFormFactor(c, d) + LTC_EdgeVectorFormFactor(d, a));
  float extent = length(form);
  return max((extent * extent + dot(form, normal)) / (extent + 1.0), 0.0);
}
`;

export function leanRoomPunctualLighting(source: string) {
  return source
    .replace('float getSpotAttenuation(', distanceAttenuation + '\nfloat getSpotAttenuation(')
    .replaceAll('float lightDistance = length( lVector );', '')
    .replaceAll('getDistanceAttenuation( lightDistance,', 'studioDistanceAttenuation( lVector,');
}

export function leanRoomPhysicalLighting(source: string) {
  return source
    .replace(
      'void RE_Direct_RectArea_Physical(',
      rectDiffuse + '\nvoid RE_Direct_RectArea_Physical(',
    )
    .replace(
      'vec2 uv = LTC_Uv( normal, viewDir, roughness );',
      `vec3 emitterNormal = cross(rectCoords[1] - rectCoords[0], rectCoords[3] - rectCoords[0]);
      if (dot(emitterNormal, position - rectCoords[0]) < 0.0) return;
      vec2 uv = LTC_Uv( normal, viewDir, roughness );`,
    )
    .replace(
      'LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords )',
      'studioRectDiffuse(normal, position, rectCoords)',
    );
}

export function leanRoomLightEvaluation(source: string) {
  return source
    .replace(
      'directLight.color *= transmittedSun(',
      'if (directLight.color != vec3(0.0)) directLight.color *= transmittedSun(',
    )
    .replace(
      'directLight.color *= sunThroughWindowOpening(',
      'if (directLight.color != vec3(0.0)) directLight.color *= sunThroughWindowOpening(',
    );
}
