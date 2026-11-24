import * as T from 'three';
import type { Environment } from '../app/environment';

const holderGuide = 'Herculx Aura etched lightguide';
const holderRail = 'Herculx printed rail and bearing carriage';
const memoryGuide = 'D50 opal RGB';
const memoryPlate = 'D50 Fubuki ceramic pad print';
const boardGuide = 'I/O lenticular print';
const hoseDiffuser = 'Ryuo opal diffusing sleeve';
export const fanPanelGuide = 'MF-12C dual-sided light guide';

const spectrum = `
  uniform float auraPhase;
  uniform float auraScatter;
  varying float guidePosition;
  vec3 guideColour() {
    vec3 channel = clamp(abs(fract(guidePosition + auraPhase + vec3(0., 0.666667, 0.333333)) * 6. - 3.) - 1., 0., 1.);
    channel = channel * channel * (3. - 2. * channel);
    return vec3(0.009) + channel * channel;
  }
  float engraving(vec3 sampleColour) {
    return max(sampleColour.r, max(sampleColour.g, sampleColour.b));
  }
`;

const diffuserTone = `#include <tonemapping_fragment>
  float emitted = engraving(totalEmissiveRadiance);
  float peak = max(engraving(gl_FragColor.rgb), 0.001);
  gl_FragColor.rgb *= mix(vec3(1.), gl_FragColor.rgb / peak, 0.56 * smoothstep(0.01, 0.63, emitted));`;

export function coolingSleeveMaterial(braid: T.Texture) {
  return new T.MeshStandardMaterial({
    name: hoseDiffuser,
    color: '#d2d3d4',
    roughness: 0.48,
    normalMap: braid,
    normalScale: new T.Vector2(0.08, 0.08),
    emissive: 0xffffff,
    emissiveIntensity: 0.95,
  });
}

function lightCoolingSleeve(material: T.MeshStandardMaterial, phase: T.IUniform<number>) {
  material.customProgramCacheKey = () => hoseDiffuser;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.auraPhase = phase;
    shader.vertexShader =
      'varying float guidePosition;\n' +
      shader.vertexShader.replace(
        '#include <uv_vertex>',
        `#include <uv_vertex>
       #ifdef USE_NORMALMAP
       vNormalMapUv.y *= 5.5;
       #endif
       guidePosition = 0.78 - 0.72 * uv.y;`,
      );
    shader.fragmentShader =
      spectrum +
      shader.fragmentShader
        .replace(
          '#include <emissivemap_fragment>',
          `float facing = clamp(dot(normal, normalize(vViewPosition)), 0., 1.);
         totalEmissiveRadiance *= mix(guideColour(), vec3(0.68), 0.14) * (0.72 + 0.28 * facing);`,
        )
        .replace('#include <tonemapping_fragment>', diffuserTone);
  };
}

export function caseComponentLights(
  chassis: T.Group,
  accents: { fascia: T.MeshStandardMaterial; psu: T.MeshStandardMaterial },
) {
  chassis.updateWorldMatrix(true, false);
  const caseMatrix = { value: chassis.matrixWorld.clone().invert() };
  const phase = { value: 0 };
  const scatter = { value: 1 };
  const attached = new Set<T.Material>();
  const emitters: Array<(value: number) => void> = [];
  let brightness = 1;

  function accent(material: T.MeshStandardMaterial, gradient: T.Vector4) {
    const intensity = material.emissiveIntensity;
    emitters.push((value) => {
      material.emissiveIntensity = intensity * value;
    });
    const mirrored = material.name === fanPanelGuide;
    material.customProgramCacheKey = () => 'case-accent-lightguide';
    material.onBeforeCompile = (shader) => {
      shader.uniforms.auraPhase = phase;
      shader.uniforms.auraGradient = { value: gradient };
      shader.uniforms.auraMirror = { value: mirrored ? 1 : 0 };
      shader.vertexShader =
        'varying float guidePosition;\nuniform vec4 auraGradient;\nuniform float auraMirror;\n' +
        shader.vertexShader.replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
          vec3 guidePoint = position;
          guidePoint.y *= mix(1.0, sign(position.x), auraMirror);
          guidePosition = dot(vec4(guidePoint, 1.), auraGradient);`,
        );
      shader.fragmentShader =
        spectrum +
        shader.fragmentShader
          .replace('#include <emissivemap_fragment>', 'totalEmissiveRadiance *= guideColour();')
          .replace('#include <tonemapping_fragment>', diffuserTone);
    };
  }
  accent(accents.fascia, new T.Vector4(3.8, 1.25, 0, 0.34));
  accent(accents.psu, new T.Vector4(0, 1.6, -4.9, 0.65));

  function prepare(material: T.MeshStandardMaterial) {
    const name = material.name;
    if (name === fanPanelGuide) {
      if (!attached.has(material)) {
        attached.add(material);
        accent(material, new T.Vector4(0, 5.4, 0, 0.68));
      }
      return;
    }
    const memory = name === memoryGuide || name === memoryPlate;
    const guide = name === holderGuide || name === memoryGuide;
    const sleeve = name === hoseDiffuser;
    if (!memory && !sleeve && name !== holderGuide && name !== holderRail && name !== boardGuide)
      return;
    if (attached.has(material)) return;
    attached.add(material);
    if (guide || name === boardGuide || sleeve) {
      const intensity = material.emissiveIntensity;
      const tint = name === memoryGuide ? material.color.clone() : undefined;
      const power = (value: number) => {
        material.emissiveIntensity = intensity * value;
        if (tint) material.color.setScalar(1).lerp(tint, value);
      };
      emitters.push(power);
      power(brightness);
    }
    if (name === boardGuide) return;
    if (sleeve) return lightCoolingSleeve(material, phase);

    material.customProgramCacheKey = () => (guide ? 'case-guide-emissive' : 'case-guide-scatter');
    material.onBeforeCompile = (shader) => {
      shader.uniforms.auraPhase = phase;
      shader.uniforms.auraScatter = scatter;
      shader.uniforms.auraToCase = caseMatrix;
      shader.uniforms.auraIsMemory = { value: memory ? 1 : 0 };
      shader.vertexShader =
        'uniform mat4 auraToCase;\nuniform float auraIsMemory;\nvarying float guidePosition;\n' +
        shader.vertexShader.replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
          float memPos = 0.79 - (position.y / 0.13102 + 0.5) * 0.69 + ((auraToCase * modelMatrix[3]).z + 0.102) * 2.6;
          float holdPos = 0.35 + (position.x / 0.208 + 0.5) * 0.79;
          guidePosition = mix(holdPos, memPos, auraIsMemory);`,
        );
      shader.fragmentShader = 'uniform float auraIsMemory;\n' + spectrum + shader.fragmentShader;
      if (guide) {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <emissivemap_fragment>',
          `
          float mask = engraving(texture2D(emissiveMap, vEmissiveMapUv).rgb);
          if (auraIsMemory > 0.5) {
            mask = smoothstep(0.006, 0.62, mask);
          } else {
            mask = mix(mask, sqrt(mask), 0.43);
            if (auraScatter > 0.) {
              float nearby = engraving(texture2D(emissiveMap, vEmissiveMapUv, 3.7).rgb);
              mask += auraScatter * max(0., sqrt(nearby) - mask) * 0.19;
            }
          }
          totalEmissiveRadiance *= guideColour() * mask;
        `,
        );
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <tonemapping_fragment>',
          diffuserTone,
        );
        return;
      }
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <aomap_fragment>',
        `
        #include <aomap_fragment>
        if (auraScatter > 0.) {
          float cut = clamp(min((vMapUv.x - 0.167) / 0.389, (0.729 - vMapUv.x) / 0.167), 0., 1.);
          float memEdge = 1. - smoothstep(0., 0.165, abs(1. - 0.295 * cut - vMapUv.y));
          float rail = mix(0.79, 0.735, smoothstep(0.47, 0.51, vMapUv.x));
          float railEdge = 1. - smoothstep(0., 0.13, abs(rail - vMapUv.y));
          float edgeLight = mix(railEdge, memEdge, auraIsMemory);
          reflectedLight.indirectDiffuse += guideColour() * edgeLight * edgeLight * auraScatter *
            (vec3(0.018) + 0.28 * material.diffuseColor);
        }
      `,
      );
    };
  }

  return {
    registerLight({ material }: T.Mesh) {
      for (const finish of Array.isArray(material) ? material : [material]) {
        if (finish instanceof T.MeshStandardMaterial) prepare(finish);
      }
    },
    setComponentLights(
      enabled: boolean,
      delta?: number,
      clock = 0,
      env?: Pick<Environment, 'quality' | 'reducedMotion'>,
    ) {
      const target = Number(enabled);
      const next =
        delta === undefined || env?.reducedMotion
          ? target
          : T.MathUtils.damp(brightness, target, 15, delta);
      const value = Math.abs(next - target) < 0.002 ? target : next;
      if (value !== brightness) {
        brightness = value;
        for (const setPower of emitters) setPower(value);
      }
      phase.value = env?.reducedMotion ? 0 : (clock % 24) / 24;
      scatter.value = env?.quality === 'low' ? 0 : brightness;
    },
  };
}
