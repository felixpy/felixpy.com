import * as T from 'three';
import type { Environment } from '../app/environment';
import { ceilingLightLevel } from '../app/home-lights';
import { roomIrradiance } from './room-irradiance';
import { lightingVolume } from './lighting-volume';
import { projectRoomReflections } from './room-reflection';
import { windowSunGLSL } from './window-sun';
import { deskOcclusionGLSL } from './desk-occlusion';
import { desk, roomSize, windowOpening, workshopLayout } from './layout';
import { cullRoomDirectLighting } from './room-direct-lighting';
import { matteRoomLighting } from './room-matte-lighting';
import { leanRoomLightEvaluation } from './room-lean-lighting';
import { hasStandardRoomDepth, markStandardRoomDepth } from './room-depth-prefill';

export const visibilityGrid = {
  origin: [-1.375, -0.125, -0.6875],
  size: [64, 48, 64],
  cell: 0.0625,
};

const workbench = {
  left: workshopLayout.x - 0.313,
  right: workshopLayout.x + 0.313,
  back: workshopLayout.z - workshopLayout.length / 2,
  front: workshopLayout.z + workshopLayout.length / 2,
  top: 0.75,
};

const contactAoGLSL = `
uniform sampler2D roomContactAo;
uniform float roomContactAoReady;
uniform sampler2D roomRectLight;
uniform float roomRectLightReady;
uniform sampler2D roomRearLight;
uniform float roomRearLightReady;
uniform vec3 studioPictureLight;
uniform vec3 studioWallWashLight;
uniform vec3 studioApertureLight;
uniform vec3 studioScreenFillLight;
uniform vec3 studioShelfLight;
uniform vec3 studioBenchLight;
uniform vec3 studioFloorLight;
uniform vec3 studioVitrineLight;
uniform vec3 studioCeilingBounce;
vec4 studioPlanarAtlasUv(vec3 pos, vec3 n) {
  float eps = 0.004;
  float span = 0.5 - 2.0 * eps;
  float inDeskXz =
    step(${(desk.left - 0.01).toFixed(4)}, pos.x) * step(pos.x, ${(desk.right + 0.01).toFixed(4)}) *
    step(${(desk.back - 0.01).toFixed(4)}, pos.z) * step(pos.z, ${(desk.front + 0.01).toFixed(4)});
  float onDeskAo = step(0.72, n.y) * step(abs(pos.y - ${desk.top.toFixed(4)}), 0.009) * inDeskXz;
  float onDeskLight = step(0.72, n.y) * step(abs(pos.y - ${desk.top.toFixed(4)}), 0.024) * inDeskXz;
  float onNorthAo = step(0.72, n.z) * step(pos.z, ${(roomSize.north + 0.01).toFixed(4)}) * step(${(roomSize.north - 0.02).toFixed(4)}, pos.z);
  float onNorthLight = step(0.72, n.z) * step(pos.z, ${(roomSize.north + 0.065).toFixed(4)}) * step(${(roomSize.north - 0.02).toFixed(4)}, pos.z);
  float onFloor = step(0.72, n.y) * step(pos.y, 0.020) * step(-0.02, pos.y);
  float onWest = step(0.72, n.x) * step(pos.x, ${(roomSize.west + 0.018).toFixed(4)}) * step(${(roomSize.west - 0.02).toFixed(4)}, pos.x);
  vec2 deskUv = vec2(
    eps + clamp((pos.x - ${desk.left.toFixed(4)}) / ${(desk.right - desk.left).toFixed(4)}, 0.0, 1.0) * span,
    eps + clamp((pos.z - ${desk.back.toFixed(4)}) / ${(desk.front - desk.back).toFixed(4)}, 0.0, 1.0) * span
  );
  vec2 northUv = vec2(
    0.5 + eps + clamp((pos.x - ${roomSize.west.toFixed(4)}) / ${(roomSize.east - roomSize.west).toFixed(4)}, 0.0, 1.0) * span,
    eps + clamp(pos.y / ${roomSize.ceiling.toFixed(4)}, 0.0, 1.0) * span
  );
  vec2 floorUv = vec2(
    eps + clamp((pos.x - ${roomSize.west.toFixed(4)}) / ${(roomSize.east - roomSize.west).toFixed(4)}, 0.0, 1.0) * span,
    0.5 + eps + clamp((pos.z - ${roomSize.north.toFixed(4)}) / ${(roomSize.south - roomSize.north).toFixed(4)}, 0.0, 1.0) * span
  );
  vec2 westUv = vec2(
    0.5 + eps + clamp((pos.z - ${roomSize.north.toFixed(4)}) / ${(roomSize.south - roomSize.north).toFixed(4)}, 0.0, 1.0) * span,
    0.5 + eps + clamp(pos.y / ${roomSize.ceiling.toFixed(4)}, 0.0, 1.0) * span
  );
  float aoHit = clamp(onDeskAo + onNorthAo + onFloor + onWest, 0.0, 1.0);
  float lightHit = clamp(onDeskLight + onNorthLight + onFloor + onWest, 0.0, 1.0);
  vec2 uv = deskUv * onDeskLight + northUv * onNorthLight + floorUv * onFloor + westUv * onWest;
  return vec4(uv, aoHit, lightHit);
}
vec3 studioRearAtlasUv(vec3 pos, vec3 n) {
  float eps = 0.004;
  float span = 0.5 - 2.0 * eps;
  float onEast = step(0.72, -n.x) * step(${(roomSize.east - 0.065).toFixed(4)}, pos.x) * step(pos.x, ${(roomSize.east + 0.02).toFixed(4)});
  float onSouth = step(0.72, -n.z) * step(${(roomSize.south - 0.065).toFixed(4)}, pos.z) * step(pos.z, ${(roomSize.south + 0.02).toFixed(4)});
  float onCeiling = step(0.72, -n.y) * step(${(roomSize.ceiling - 0.045).toFixed(4)}, pos.y) * step(pos.y, ${(roomSize.ceiling + 0.02).toFixed(4)});
  float inBenchXz =
    step(${(workbench.left - 0.01).toFixed(4)}, pos.x) * step(pos.x, ${(workbench.right + 0.01).toFixed(4)}) *
    step(${(workbench.back - 0.01).toFixed(4)}, pos.z) * step(pos.z, ${(workbench.front + 0.01).toFixed(4)});
  float onBench = step(0.72, n.y) * step(abs(pos.y - ${workbench.top.toFixed(4)}), 0.024) * inBenchXz;
  vec2 eastUv = vec2(
    eps + clamp((pos.z - ${roomSize.north.toFixed(4)}) / ${(roomSize.south - roomSize.north).toFixed(4)}, 0.0, 1.0) * span,
    eps + clamp(pos.y / ${roomSize.ceiling.toFixed(4)}, 0.0, 1.0) * span
  );
  vec2 southUv = vec2(
    0.5 + eps + clamp((pos.x - ${roomSize.west.toFixed(4)}) / ${(roomSize.east - roomSize.west).toFixed(4)}, 0.0, 1.0) * span,
    eps + clamp(pos.y / ${roomSize.ceiling.toFixed(4)}, 0.0, 1.0) * span
  );
  vec2 ceilingUv = vec2(
    eps + clamp((pos.x - ${roomSize.west.toFixed(4)}) / ${(roomSize.east - roomSize.west).toFixed(4)}, 0.0, 1.0) * span,
    0.5 + eps + clamp((pos.z - ${roomSize.north.toFixed(4)}) / ${(roomSize.south - roomSize.north).toFixed(4)}, 0.0, 1.0) * span
  );
  vec2 benchUv = vec2(
    0.5 + eps + clamp((pos.x - ${workbench.left.toFixed(4)}) / ${(workbench.right - workbench.left).toFixed(4)}, 0.0, 1.0) * span,
    0.5 + eps + clamp((pos.z - ${workbench.back.toFixed(4)}) / ${(workbench.front - workbench.back).toFixed(4)}, 0.0, 1.0) * span
  );
  float hit = clamp(onEast + onSouth + onCeiling + onBench, 0.0, 1.0);
  vec2 uv = eastUv * onEast + southUv * onSouth + ceilingUv * onCeiling + benchUv * onBench;
  return vec3(uv, hit);
}
vec3 studioLocalPanelFill(vec3 pos, vec3 n) {
  // 1. Recessed bookcase vertical linear LED strip along x=1.27, z=-0.22, y=[0.12..2.36]
  float inShelf =
    step(1.22, pos.x) * step(pos.x, 1.88) *
    step(0.06, pos.y) * step(pos.y, 2.43) *
    step(-0.57, pos.z) * step(pos.z, -0.14);
  vec3 shelfDelta = vec3(1.27, clamp(pos.y, 0.14, 2.36), -0.22) - pos;
  float shelfDist2 = dot(shelfDelta, shelfDelta) + 0.018;
  float shelfNdotL = clamp(dot(n, shelfDelta * inversesqrt(shelfDist2)) * 0.72 + 0.28, 0.0, 1.0);
  vec3 shelfContrib = studioShelfLight * (inShelf * shelfNdotL * 0.055 / shelfDist2);

  // 2. West window aperture sky wrap on blinds slats, painted sill, and recessed jambs
  float inWindow =
    smoothstep(${(windowOpening.wall + 0.42).toFixed(4)}, ${(windowOpening.wall - 0.06).toFixed(4)}, pos.x) *
    smoothstep(${(windowOpening.z0 - 0.18).toFixed(4)}, ${(windowOpening.z0 + 0.04).toFixed(4)}, pos.z) *
    smoothstep(${(windowOpening.z1 + 0.18).toFixed(4)}, ${(windowOpening.z1 - 0.04).toFixed(4)}, pos.z) *
    smoothstep(${(windowOpening.y0 - 0.22).toFixed(4)}, ${(windowOpening.y0 - 0.02).toFixed(4)}, pos.y) *
    smoothstep(${(windowOpening.y1 + 0.14).toFixed(4)}, ${(windowOpening.y1 - 0.04).toFixed(4)}, pos.y);
  float winFacing = clamp(dot(n, normalize(vec3(-0.65, 0.76, 0.0))) * 0.55 + 0.45, 0.0, 1.0);
  vec3 windowContrib = studioApertureLight * (inWindow * winFacing * 0.28);

  return shelfContrib + windowContrib;
}
`;

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
  const contactFallback = new T.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
  contactFallback.needsUpdate = true;
  const contactAo = { value: contactFallback as T.Texture };
  const contactAoReady = { value: 0 };
  const rectFallback = new T.DataTexture(new Uint8Array([0, 0, 0, 0]), 1, 1);
  rectFallback.needsUpdate = true;
  const rectLight = { value: rectFallback as T.Texture };
  const rectLightReady = { value: 0 };
  const rearFallback = new T.DataTexture(new Uint8Array([0, 0, 0, 0]), 1, 1);
  rearFallback.needsUpdate = true;
  const rearLight = { value: rearFallback as T.Texture };
  const rearLightReady = { value: 0 };
  const pictureColor = new T.Color('#ffe5c7');
  const wallWashColor = new T.Color('#fff0da');
  const screenFillColor = new T.Color('#c3d9ef');
  const shelfColor = new T.Color('#ffddb3');
  const apertureNightColor = new T.Color('#88b7e9');
  const apertureDayColor = new T.Color('#d5e4eb');
  const benchColor = new T.Color('#ffe3bd');
  const floorLampColor = new T.Color('#ffdca8');
  const vitrineColor = new T.Color('#ffb86c');
  const ceilingBounceColor = new T.Color('#ffdfb4');
  const studioPictureLight = { value: new T.Vector3() };
  const studioWallWashLight = { value: new T.Vector3() };
  const studioApertureLight = { value: new T.Vector3() };
  const studioScreenFillLight = { value: new T.Vector3() };
  const studioShelfLight = { value: new T.Vector3() };
  const studioBenchLight = { value: new T.Vector3() };
  const studioFloorLight = { value: new T.Vector3() };
  const studioVitrineLight = { value: new T.Vector3() };
  const studioCeilingBounce = { value: new T.Vector3() };
  const apertureTarget = new T.Vector3();
  const rectScale = (color: T.Color, scale: number, out: T.Vector3) =>
    out.set(color.r * scale, color.g * scale, color.b * scale);
  function syncRectLights(env: Environment, delta: number) {
    const ease = env.reducedMotion || delta === 0 ? 1 : 1 - Math.exp(-delta * 5);
    const high = env.quality === 'high';
    const pic = (env.pictureLamp ?? env.night) ? 1.0 : 0.0;
    const wash = high && env.screenBar ? 1.0 : 0.0;
    const blocked = env.blinds ? [0.24, 0.54, 1.0][env.angle] : 0.0;
    const apGain =
      (env.night ? 0.95 : env.weather === '晴' ? 8.5 : env.weather === '雨' ? 5.2 : 7.1) *
      (1.0 - blocked * 0.9);
    const apColor = env.night ? apertureNightColor : apertureDayColor;
    const screenGain = high ? 1.0 : 0.0;
    const ceilingGain = ceilingLightLevel(env);
    const shelfGain = high ? ceilingGain : 0.0;
    const benchGain = (env.benchLamp ? 0.65 : 0.0) + (env.toolBoardLamp ? 0.35 : 0.0);
    const floorGain = (env.floorLamp ?? env.night) ? 0.65 : 0.0;
    const vitrineGain = env.night ? 0.55 : 0.35;
    studioPictureLight.value.lerp(rectScale(pictureColor, pic, apertureTarget), ease);
    studioWallWashLight.value.lerp(rectScale(wallWashColor, wash, apertureTarget), ease);
    studioApertureLight.value.lerp(rectScale(apColor, apGain, apertureTarget), ease);
    studioScreenFillLight.value.lerp(rectScale(screenFillColor, screenGain, apertureTarget), ease);
    studioShelfLight.value.lerp(rectScale(shelfColor, shelfGain, apertureTarget), ease);
    studioBenchLight.value.lerp(rectScale(benchColor, benchGain, apertureTarget), ease);
    studioFloorLight.value.lerp(rectScale(floorLampColor, floorGain, apertureTarget), ease);
    studioVitrineLight.value.lerp(rectScale(vitrineColor, vitrineGain, apertureTarget), ease);
    studioCeilingBounce.value.lerp(
      rectScale(ceilingBounceColor, ceilingGain, apertureTarget),
      ease,
    );
  }
  syncRectLights(initial, 0);
  const restore: Array<() => void> = [];
  const seen = new Set<T.MeshStandardMaterial>();
  const options =
    typeof location === 'undefined' ? undefined : new URLSearchParams(location.search);
  const sharedReflections = options?.get('studio-reflections') !== 'split';
  const lighting = options?.get('studio-lighting');
  const leanKernel = options?.get('studio-light-kernel') === 'lean';
  const matteLighting = lighting === 'matte';
  const cullAllLighting = lighting === 'culled-all';
  const cullLighting = matteLighting || lighting === 'culled' || leanKernel;
  let cullDirectLights = cullAllLighting || (cullLighting && initial.quality === 'low');
  let leanDirectLights = leanKernel && initial.quality === 'low';
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
      if (directLight.visible) {
      #if !defined(USE_SHADOWMAP) || NUM_DIR_LIGHT_SHADOWS == 0
        directLight.color *= transmittedSun(studioPosition,
          -inverseTransformDirection(directLight.direction, viewMatrix), windowSlats);
      #else
        directLight.color *= sunThroughWindowOpening(studioPosition,
          -inverseTransformDirection(directLight.direction, viewMatrix));
      #endif
      }`,
    );
  const leanEvaluation = leanKernel ? leanRoomLightEvaluation(lightEvaluation) : lightEvaluation;
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
      const standardDepth = hasStandardRoomDepth(material);
      const matte =
        matteLighting &&
        material.userData.studioMatte === true &&
        compile === T.Material.prototype.onBeforeCompile;
      const originalKey = material.customProgramCacheKey;
      const cacheKey = material.customProgramCacheKey();
      const simplifyPhysical =
        material instanceof T.MeshPhysicalMaterial &&
        material.transmission === 0 &&
        material.sheen === 0 &&
        material.iridescence === 0 &&
        material.anisotropy === 0 &&
        material.dispersion === 0 &&
        !material.clearcoatMap &&
        !material.clearcoatNormalMap &&
        !material.clearcoatRoughnessMap &&
        !material.specularColorMap &&
        !material.specularIntensityMap;
      const originalPhysical = simplifyPhysical
        ? {
            type: material.type,
            clearcoat: material.clearcoat,
            roughness: material.roughness,
            envMapIntensity: material.envMapIntensity,
          }
        : undefined;
      if (simplifyPhysical) {
        if (material.clearcoat > 0) {
          material.roughness = Math.max(0.06, material.roughness * (1 - 0.35 * material.clearcoat));
          material.envMapIntensity = Math.max(
            material.envMapIntensity,
            1 + 0.25 * material.clearcoat,
          );
          material.clearcoat = 0;
        }
        material.type = 'MeshStandardMaterial';
        Object.defineProperty(material, 'isMeshPhysicalMaterial', {
          value: false,
          configurable: true,
        });
      }
      const localReflections = material.metalness > 0.1 || material.roughness < 0.46;
      const reflectionProjection = { value: localReflections };
      restore.push(() => {
        material.dispose();
        if (originalPhysical && material instanceof T.MeshPhysicalMaterial) {
          material.type = originalPhysical.type;
          delete (material as { isMeshPhysicalMaterial?: boolean }).isMeshPhysicalMaterial;
          material.clearcoat = originalPhysical.clearcoat;
          material.roughness = originalPhysical.roughness;
          material.envMapIntensity = originalPhysical.envMapIntensity;
        }
        material.onBeforeCompile = compile;
        material.customProgramCacheKey = originalKey;
        material.needsUpdate = true;
      });
      material.dispose();
      material.customProgramCacheKey = () =>
        cacheKey +
        '-studio-room-visibility-' +
        (sharedReflections ? 'shared' : Number(localReflections)) +
        (cullDirectLights ? (matte ? '-matte' : '-culled') : '') +
        (leanDirectLights ? '-lean' : '');
      material.onBeforeCompile = (shader, renderer) => {
        compile.call(material, shader, renderer);
        if (sharedReflections) shader.uniforms.studioProjectReflections = reflectionProjection;
        if (localReflections || sharedReflections)
          projectRoomReflections(shader, sharedReflections);
        shader.uniforms.roomVisibility = uniform;
        shader.uniforms.roomContactAo = contactAo;
        shader.uniforms.roomContactAoReady = contactAoReady;
        shader.uniforms.roomRectLight = rectLight;
        shader.uniforms.roomRectLightReady = rectLightReady;
        shader.uniforms.roomRearLight = rearLight;
        shader.uniforms.roomRearLightReady = rearLightReady;
        shader.uniforms.studioPictureLight = studioPictureLight;
        shader.uniforms.studioWallWashLight = studioWallWashLight;
        shader.uniforms.studioApertureLight = studioApertureLight;
        shader.uniforms.studioScreenFillLight = studioScreenFillLight;
        shader.uniforms.studioShelfLight = studioShelfLight;
        shader.uniforms.studioBenchLight = studioBenchLight;
        shader.uniforms.studioFloorLight = studioFloorLight;
        shader.uniforms.studioVitrineLight = studioVitrineLight;
        shader.uniforms.studioCeilingBounce = studioCeilingBounce;
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
          ? cullRoomDirectLighting(
              matte ? matteRoomLighting(shader.fragmentShader) : shader.fragmentShader,
              leanDirectLights ? leanEvaluation : lightEvaluation,
              leanDirectLights,
            )
          : shader.fragmentShader.replace('#include <lights_fragment_begin>', lightEvaluation);
        shader.fragmentShader =
          'varying vec3 studioPosition;\nuniform highp sampler3D roomVisibility;\nuniform highp sampler3D roomBounce;\nuniform float roomBounceStrength;\nuniform vec2 windowSlats;\n' +
          contactAoGLSL +
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
          vec4 planarAtlas = studioPlanarAtlasUv(studioPosition, roomNormal);
          float contactSample = mix(1.0, texture2D(roomContactAo, planarAtlas.xy).r, planarAtlas.z * roomContactAoReady);
          float contactMask = mix(1.0, contactSample, 0.70);
          vec4 rawRect = texture2D(roomRectLight, planarAtlas.xy);
          vec4 rectIrr = rawRect * rawRect * (4.0 * planarAtlas.w * roomRectLightReady);
          vec3 rectDirect = rectIrr.r * studioPictureLight
                          + rectIrr.g * studioWallWashLight
                          + rectIrr.b * studioApertureLight
                          + rectIrr.a * studioScreenFillLight
                          + studioLocalPanelFill(studioPosition, roomNormal);
          if (roomRearLightReady > 0.5) {
            vec3 rearAtlas = studioRearAtlasUv(studioPosition, roomNormal);
            if (rearAtlas.z > 0.5) {
              vec4 rawRear = texture2D(roomRearLight, rearAtlas.xy);
              vec4 rearIrr = rawRear * rawRear * 4.0;
              rectDirect += rearIrr.r * studioBenchLight
                          + rearIrr.g * studioFloorLight
                          + rearIrr.b * studioVitrineLight
                          + rearIrr.a * studioCeilingBounce;
            }
          }
          reflectedLight.directDiffuse += material.diffuseColor * rectDirect;
          reflectedLight.indirectDiffuse *= openHemisphere * contactMask;
          reflectedLight.indirectSpecular *= mix(1., openHemisphere * contactMask, 0.68);
          reflectedLight.directDiffuse *= mix(1., contactMask, 0.42);
          if (roomBounceStrength > 0.001) {
            vec3 probe = clamp(roomUv, vec3(0.015625, 0.020833, 0.015625), vec3(0.984375, 0.979167, 0.984375));
            probe.z *= 0.5;
            vec3 radiance = texture(roomBounce, probe).rgb;
            vec3 moment = (texture(roomBounce, probe + vec3(0., 0., 0.5)).rgb * 255. - 128.) / 127.;
            vec3 diffuseBounce = radiance * radiance * max(0.04, 1. + 2. * dot(roomNormal, moment));
            reflectedLight.indirectDiffuse = mix(reflectedLight.indirectDiffuse,
              reflectedLight.indirectDiffuse * 0.40 + material.diffuseColor * diffuseBounce * contactMask, roomBounceStrength);
          }
        `,
          );
      };
      if (standardDepth) markStandardRoomDepth(material);
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
  const loadPlanarMap = (url: string, target: { value: T.Texture }, readyFlag: { value: number }) =>
    new Promise<void>((resolve) => {
      if (typeof document === 'undefined') {
        resolve();
        return;
      }
      new T.TextureLoader().load(
        url,
        (loaded) => {
          if (controller.signal.aborted) {
            loaded.dispose();
            resolve();
            return;
          }
          loaded.minFilter = T.LinearFilter;
          loaded.magFilter = T.LinearFilter;
          loaded.generateMipmaps = false;
          loaded.wrapS = loaded.wrapT = T.ClampToEdgeWrapping;
          target.value.dispose();
          target.value = loaded;
          readyFlag.value = 1;
          resolve();
        },
        undefined,
        () => resolve(),
      );
    });
  const ready = Promise.all([
    load().catch(() => {}),
    loadPlanarMap('/media/lighting/room-contact-ao.png', contactAo, contactAoReady),
    loadPlanarMap('/media/lighting/room-rect-lightmap.png', rectLight, rectLightReady),
    loadPlanarMap('/media/lighting/room-rear-lightmap.png', rearLight, rearLightReady),
  ]).then(() => {});
  return {
    get ready() {
      return Promise.all([ready, bounce.ready]);
    },
    prepareMaterials,
    update(env: Environment, delta: number) {
      const cull = cullAllLighting || (cullLighting && env.quality === 'low');
      const lean = leanKernel && env.quality === 'low';
      if (cull !== cullDirectLights || lean !== leanDirectLights) {
        cullDirectLights = cull;
        leanDirectLights = lean;
        for (const material of seen) material.needsUpdate = true;
      }
      syncRectLights(env, delta);
      if (env.quality === 'low') bounce.strength.value = 0;
      else bounce.update(env, delta);
    },
    dispose() {
      controller.abort();
      bounce.dispose();
      uniform.value.dispose();
      contactAo.value.dispose();
      rectLight.value.dispose();
      rearLight.value.dispose();
      restore.forEach((reset) => reset());
    },
  };
}
