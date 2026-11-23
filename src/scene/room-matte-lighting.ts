import { ShaderChunk } from 'three';

const diffuseLighting = `
void RE_Direct_StudioMatte(const in IncidentLight light, const in vec3 position,
  const in vec3 normal, const in vec3 view, const in vec3 clearcoatNormal,
  const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
  float incidence = saturate(dot(normal, light.direction));
  reflectedLight.directDiffuse += incidence * light.color * BRDF_Lambert(material.diffuseContribution);
}

void RE_IndirectDiffuse_StudioMatte(const in vec3 irradiance, const in vec3 position,
  const in vec3 normal, const in vec3 view, const in vec3 clearcoatNormal,
  const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
  reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert(material.diffuseContribution);
}

#if NUM_RECT_AREA_LIGHTS > 0
void RE_Direct_RectArea_StudioMatte(const in RectAreaLight light, const in vec3 position,
  const in vec3 normal, const in vec3 view, const in vec3 clearcoatNormal,
  const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
  vec3 center = light.position - position;
  if (dot(cross(light.halfWidth, light.halfHeight), center) <= 0.0) return;
  vec3 a = normalize(center + light.halfWidth - light.halfHeight);
  vec3 b = normalize(center - light.halfWidth - light.halfHeight);
  vec3 c = normalize(center - light.halfWidth + light.halfHeight);
  vec3 d = normalize(center + light.halfWidth + light.halfHeight);
  vec3 form = -(LTC_EdgeVectorFormFactor(a, b) + LTC_EdgeVectorFormFactor(b, c)
    + LTC_EdgeVectorFormFactor(c, d) + LTC_EdgeVectorFormFactor(d, a));
  float extent = length(form);
  float irradiance = max((extent * extent + dot(form, normal)) / (extent + 1.0), 0.0);
  reflectedLight.directDiffuse += irradiance * light.color * material.diffuseContribution;
}

#undef RE_Direct_RectArea
#define RE_Direct_RectArea RE_Direct_RectArea_StudioMatte
#endif

#undef RE_Direct
#define RE_Direct RE_Direct_StudioMatte
#undef RE_IndirectDiffuse
#define RE_IndirectDiffuse RE_IndirectDiffuse_StudioMatte
#undef RE_IndirectSpecular
`;

const diffuseEnvironment = ShaderChunk.lights_fragment_end.replace(
  'RE_IndirectDiffuse( irradiance,',
  'RE_IndirectDiffuse( irradiance + iblIrradiance,',
);

export function matteRoomLighting(fragmentShader: string) {
  return fragmentShader
    .replace(
      '#include <lights_physical_pars_fragment>',
      ShaderChunk.lights_physical_pars_fragment + diffuseLighting,
    )
    .replace('#include <lights_fragment_end>', diffuseEnvironment);
}
