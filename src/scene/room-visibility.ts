import * as T from 'three';
import type { Environment } from '../app/environment';
import { roomIrradiance } from './room-irradiance';
import { lightingVolume } from './lighting-volume';
import { projectRoomReflections } from './room-reflection';
import { windowSunGLSL } from './window-sun';
import { deskOcclusionGLSL } from './desk-occlusion';
import { desk } from './layout';
import { cullRoomDirectLighting } from './room-direct-lighting';

export const visibilityGrid = {
  origin: [-1.375, -0.125, -0.6875],
  size: [64, 48, 64],
  cell: 0.0625,
};

export function roomVisibility(
  roots: T.Object3D[],
  initial: Environment,
  slats = new T.Vector2(0.0038, 0),
) {
  const { origin, size, cell } = visibilityGrid;
  const controller = new AbortController();
  const bounce = roomIrradiance(controller.signal);
  bounce.update(initial, 0);
  function texture(data: Uint8Array<ArrayBuffer>, width: number, height: number, depth: number) {
    const field = new T.Data3DTexture(data, width, height, depth);
    field.format = T.RGBAFormat;
    field.minFilter = field.magFilter = T.LinearFilter;
    field.unpackAlignment = 1;
    field.needsUpdate = true;
    return field;
  }
  const uniform = { value: texture(new Uint8Array([128, 128, 128, 255]), 1, 1, 1) };
  const restore: Array<() => void> = [];
  const seen = new Set<T.MeshStandardMaterial>();
  const cullLighting =
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('studio-lighting') === 'culled';
  let cullDirectLights = cullLighting && initial.quality === 'low';
  const lightEvaluation = T.ShaderChunk.lights_fragment_begin
    .replace(
      'getSpotLightInfo( spotLight, geometryPosition, directLight );',
      `getSpotLightInfo( spotLight, geometryPosition, directLight );
      if (directLight.visible && studioPosition.y < ${desk.top}) {
        directLight.color *= deskVisibility(studioPosition,
          cameraPosition + transpose(mat3(viewMatrix)) * spotLight.position);
      }`,
    )
    .replace(
      'getDirectionalLightInfo( directionalLight, directLight );',
      `getDirectionalLightInfo( directionalLight, directLight );
      #if !defined(USE_SHADOWMAP) || NUM_DIR_LIGHT_SHADOWS == 0
        directLight.color *= transmittedSun(studioPosition,
          -inverseTransformDirection(directLight.direction, viewMatrix), windowSlats);
      #else
        directLight.color *= sunThroughWindowOpening(studioPosition,
          -inverseTransformDirection(directLight.direction, viewMatrix));
      #endif`,
    );
  const prepare = (object: T.Object3D) => {
    if (!(object instanceof T.Mesh)) return;
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      if (
        !(material instanceof T.MeshStandardMaterial) ||
        material.transparent ||
        seen.has(material)
      )
        continue;
      seen.add(material);
      const compile = material.onBeforeCompile;
      const originalKey = material.customProgramCacheKey;
      const cacheKey = material.customProgramCacheKey();
      const localReflections = material.metalness > 0.1 || material.roughness < 0.46;
      restore.push(() => {
        material.dispose();
        material.onBeforeCompile = compile;
        material.customProgramCacheKey = originalKey;
        material.needsUpdate = true;
      });
      material.dispose();
      material.customProgramCacheKey = () =>
        cacheKey +
        '-studio-room-visibility-' +
        Number(localReflections) +
        (cullDirectLights ? '-culled' : '');
      material.onBeforeCompile = (shader, renderer) => {
        compile.call(material, shader, renderer);
        if (localReflections) projectRoomReflections(shader);
        shader.uniforms.roomVisibility = uniform;
        shader.uniforms.roomBounce = bounce.field;
        shader.uniforms.roomBounceStrength = bounce.strength;
        shader.uniforms.windowSlats = { value: slats };
        shader.vertexShader =
          'varying vec3 studioPosition;\n' +
          shader.vertexShader.replace(
            '#include <project_vertex>',
            `
          #include <project_vertex>
          studioPosition = cameraPosition + transpose(mat3(viewMatrix)) * mvPosition.xyz;
        `,
          );
        const fragment = cullDirectLights
          ? cullRoomDirectLighting(shader.fragmentShader, lightEvaluation)
          : shader.fragmentShader.replace('#include <lights_fragment_begin>', lightEvaluation);
        shader.fragmentShader =
          'varying vec3 studioPosition;\nuniform highp sampler3D roomVisibility;\nuniform highp sampler3D roomBounce;\nuniform float roomBounceStrength;\nuniform vec2 windowSlats;\n' +
          windowSunGLSL +
          deskOcclusionGLSL +
          fragment.replace(
            '#include <aomap_fragment>',
            `
          #include <aomap_fragment>
          vec3 roomNormal = inverseTransformDirection(geometryNormal, viewMatrix);
          vec3 roomUv = (studioPosition + roomNormal * ${(cell * 1.12).toFixed(4)} - vec3(${origin.join(',')})) / vec3(${size.map((n) => (n * cell).toFixed(2)).join(',')});
          vec4 nearby = texture(roomVisibility, clamp(roomUv, 0.001, 0.999));
          float openHemisphere = clamp(nearby.a + dot((nearby.rgb - 128.0/255.0) * 1.12, roomNormal), 0.16, 1.);
          reflectedLight.indirectDiffuse *= openHemisphere;
          reflectedLight.indirectSpecular *= mix(1., openHemisphere, 0.70);
          if (roomBounceStrength > 0.001) {
            vec3 probe = clamp(roomUv, vec3(0.015625, 0.020833, 0.015625), vec3(0.984375, 0.979167, 0.984375));
            probe.z *= 0.5;
            vec3 radiance = texture(roomBounce, probe).rgb;
            vec3 moment = (texture(roomBounce, probe + vec3(0., 0., 0.5)).rgb * 255. - 128.) / 127.;
            vec3 diffuseBounce = radiance * radiance * max(0.04, 1. + 2. * dot(roomNormal, moment));
            reflectedLight.indirectDiffuse = mix(reflectedLight.indirectDiffuse,
              reflectedLight.indirectDiffuse * 0.40 + material.diffuseColor * diffuseBounce, roomBounceStrength);
          }
        `,
          );
      };
      material.needsUpdate = true;
    }
  };
  const prepareMaterials = (subtree?: T.Object3D) => {
    if (subtree) subtree.traverse(prepare);
    else roots.forEach((root) => root.traverse(prepare));
  };
  const load = async () => {
    const bytes = await lightingVolume(
      '/media/lighting/room-visibility.gz',
      size[0] * size[1] * size[2] * 4,
      controller.signal,
    );
    if (!bytes) return;
    uniform.value.dispose();
    uniform.value = texture(bytes, size[0], size[1], size[2]);
  };
  const ready = load().catch(() => {});
  return {
    get ready() {
      return Promise.all([ready, bounce.ready]);
    },
    prepareMaterials,
    update(env: Environment, delta: number) {
      const cull = cullLighting && env.quality === 'low';
      if (cull !== cullDirectLights) {
        cullDirectLights = cull;
        for (const material of seen) material.needsUpdate = true;
      }
      bounce.update(env, delta);
    },
    dispose() {
      controller.abort();
      bounce.dispose();
      uniform.value.dispose();
      restore.forEach((reset) => reset());
    },
  };
}
