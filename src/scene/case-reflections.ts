import * as T from 'three';

export function caseReflections(chassis: T.Object3D, aura: T.MeshStandardMaterial[]) {
  chassis.updateWorldMatrix(true, false);
  const toCase = { value: chassis.matrixWorld.clone().invert() };
  const strength = { value: 0 };
  const colours = [aura[2], aura[3], aura[4]].map((source) => ({ value: source.emissive }));
  function apply(material: T.MeshStandardMaterial) {
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, {
        caseMatrix: toCase,
        caseLightStrength: strength,
        caseRearColour: colours[0],
        caseMidColour: colours[1],
        caseFrontColour: colours[2],
      });
      shader.fragmentShader =
        `uniform mat4 caseMatrix;
         uniform float caseLightStrength;
         uniform vec3 caseRearColour, caseMidColour, caseFrontColour;
         float impellerCoverage(vec2 p, float blur) {
           float d = length(p);
           return (1.0 - smoothstep(0.052 - blur, 0.055 + blur, d)) *
              mix(0.17, 1.0, smoothstep(0.015 - blur, 0.021 + blur, d));
         }\n` +
        shader.fragmentShader.replace(
          '#include <aomap_fragment>',
          `#include <aomap_fragment>
           if (caseLightStrength > 0.0) {
             vec3 ray = mat3(caseMatrix) * inverseTransformDirection(reflect(-normalize(vViewPosition), normal), viewMatrix);
             vec3 pos = (caseMatrix * vec4(cameraPosition - transpose(mat3(viewMatrix)) * vViewPosition, 1.0)).xyz;
             float t = (0.214 - pos.y) / max(0.001, ray.y);
             vec2 hit = pos.xz + t * ray.xz;
             float blur = clamp(t * roughnessFactor * roughnessFactor * 0.44, 0.004, 0.13);
             float weight = caseLightStrength * smoothstep(0.04, 0.25, ray.y) / (1.0 + 45.0 * blur);
             vec3 reflected = caseRearColour * impellerCoverage(hit - vec2(-0.007, -0.174), blur)
                            + caseMidColour * impellerCoverage(hit - vec2(-0.007, -0.054), blur)
                            + caseFrontColour * impellerCoverage(hit - vec2(-0.007, 0.066), blur);
             reflectedLight.indirectSpecular += reflected * material.specularColor * (0.83 * weight);
           }`,
        );
    };
    material.customProgramCacheKey = () => 'hyperion-radiator-reflection';
  }
  return { apply, strength };
}
