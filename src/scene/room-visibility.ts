import * as T from 'three';
import type { Environment } from '../app/environment';
import type { CabinetSpotBinding } from './cabinet-spots';
import { roomIrradiance } from './room-irradiance';
import { lightingVolume } from './lighting-volume';
import { projectRoomReflections } from './room-reflection';
import { windowSunGLSL } from './window-sun';
import { deskOcclusionGLSL } from './desk-occlusion';
import { desk } from './layout';
import { cullRoomDirectLighting } from './room-direct-lighting';
import { matteRoomLighting } from './room-matte-lighting';
import { leanRoomLightEvaluation, leanRoomPunctualLighting } from './room-lean-lighting';
import { hasStandardRoomDepth, markStandardRoomDepth } from './room-depth-prefill';

export const visibilityGrid = {
  origin: [-1.375, -0.125, -0.6875],
  size: [64, 48, 64],
  cell: 0.0625,
};

const dotNLCheck = (name: string) => `
      #ifdef USE_CLEARCOAT
        bool ${name} = dot( geometryNormal, directLight.direction ) > 0.0 || dot( geometryClearcoatNormal, directLight.direction ) > 0.0;
      #else
        bool ${name} = dot( geometryNormal, directLight.direction ) > 0.0;
      #endif`;

const cabinetUniformsGLSL = `uniform mat4 caseToWorld;
uniform mat4 caseFromWorld;
uniform vec3 caseEmitters[5], caseAxes[5], caseOptics[5];
uniform float caseDimmer;
uniform int uCaseEmitterCount;
uniform sampler2D caseVisibility;
uniform float caseVisibilityReady;
uniform float caseReceiverMode;
`;

const cabinetAomapGLSL = `
          if (caseReceiverMode > 0.5 && caseReceiverMode < 1.5) {
            vec3 casePoint = (caseFromWorld * vec4(studioPosition, 1.0)).xyz;
            vec2 floorUV = vec2(casePoint.x / 1.145 + 0.5,
                              0.25 * clamp((casePoint.z - 0.0195) / 0.351, 0.001, 0.999));
            float contactVisibility = mix(1.0, texture2D(caseVisibility, floorUV).b, caseVisibilityReady);
            reflectedLight.indirectDiffuse *= contactVisibility;
            reflectedLight.indirectSpecular *= contactVisibility;
          }`;

const cabinetDirectGLSL = `
#ifdef RE_Direct
if (caseDimmer > 0.001) {
  vec3 casePoint = (caseFromWorld * vec4(studioPosition, 1.0)).xyz;
  if (casePoint.z > 0.019 && casePoint.z < 0.35 &&
      abs(casePoint.x) < 0.565 && casePoint.y > 0.5195 && casePoint.y < 1.2851) {
    bool upper = casePoint.y >= 0.965;
    vec3 visibleFromEmitter = vec3(1.0);
    if (caseReceiverMode > 0.5) {
      float atlasV = caseReceiverMode < 1.5
        ? 0.25 * clamp((casePoint.z - 0.0195) / 0.351, 0.001, 0.999)
        : (upper ? 0.625 + 0.375 * clamp((casePoint.y - 0.965) / 0.320, 0.001, 0.999)
                 : 0.25 + 0.375 * clamp((casePoint.y - 0.520) / 0.445, 0.001, 0.999));
      visibleFromEmitter = texture2D(caseVisibility, vec2(casePoint.x / 1.145 + 0.5, atlasV)).rgb;
    }
    for (int emitter = 0; emitter < uCaseEmitterCount; ++emitter) {
      if (upper != (emitter < 3)) continue;
      vec3 toPupil = caseEmitters[emitter] - casePoint;
      float r2 = max(dot(toPupil, toPupil), 0.00006);
      vec3 toward = toPupil * inversesqrt(r2);
      vec3 optic = caseOptics[emitter];
      float beam = smoothstep(optic.x, optic.y, dot(-toward, caseAxes[emitter]));
      if (beam <= 0.0) continue;
      IncidentLight displayLight;
      displayLight.direction = mat3(viewMatrix) * mat3(caseToWorld) * toward;
      #ifdef USE_CLEARCOAT
        bool caseLit = dot(geometryNormal, displayLight.direction) > 0.0 || dot(geometryClearcoatNormal, displayLight.direction) > 0.0;
      #else
        bool caseLit = dot(geometryNormal, displayLight.direction) > 0.0;
      #endif
      if (!caseLit) continue;
      displayLight.color = vec3(1.0, 0.723, 0.423) * (caseDimmer * optic.z * beam / r2);
      displayLight.color *= visibleFromEmitter[emitter < 3 ? emitter : emitter - 3];
      displayLight.visible = true;
      RE_Direct(displayLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight);
    }
  }
}
#endif`;

export function buildRoomLightEvaluation(
  base = T.ShaderChunk.lights_fragment_begin,
  includeCabinet = false,
) {
  const pointBlock = `#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif`;

  const pointReplacement = `#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
		PointLightShadow pointLightShadow;
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
			pointLight = pointLights[ i ];
			getPointLightInfo( pointLight, geometryPosition, directLight );
			if ( directLight.visible ) {${dotNLCheck('pointLit')}
				if ( pointLit ) {
					#if ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
					pointLightShadow = pointLightShadows[ i ];
					directLight.color *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
					#endif
					RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
				}
			}
		}
		#pragma unroll_loop_end
	#else
		for ( int i = 0; i < uPointCount; i ++ ) {
			pointLight = pointLights[ i ];
			getPointLightInfo( pointLight, geometryPosition, directLight );
			if ( directLight.visible ) {
				RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
			}
		}
	#endif
#endif`;

  const spotBlock = `#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif`;

  const spotDeskOcclusion = `
					if ( studioPosition.y < ${desk.top} ) {
						directLight.color *= deskVisibility( studioPosition,
							cameraPosition + transpose( mat3( viewMatrix ) ) * spotLight.position );
					}`;

  const spotReplacement = `#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	#if NUM_SPOT_LIGHT_MAPS > 0
		vec4 spotColor;
		vec3 spotLightCoord;
		bool inSpotLightMap;
	#endif
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
		SpotLightShadow spotLightShadow;
	#endif
	#if NUM_SPOT_LIGHT_MAPS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
			spotLight = spotLights[ i ];
			getSpotLightInfo( spotLight, geometryPosition, directLight );
			if ( directLight.visible ) {${dotNLCheck('spotLit')}
				if ( spotLit ) {${spotDeskOcclusion}
					#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
					#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
					#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
					#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
					#else
					#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
					#endif
					#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
						spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
						inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
						spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
						directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
					#endif
					#undef SPOT_LIGHT_MAP_INDEX
					#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
					spotLightShadow = spotLightShadows[ i ];
					directLight.color *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
					#endif
					RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
				}
			}
		}
		#pragma unroll_loop_end
	#else
		#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
			#pragma unroll_loop_start
			for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
				spotLight = spotLights[ i ];
				getSpotLightInfo( spotLight, geometryPosition, directLight );
				if ( directLight.visible ) {${dotNLCheck('spotLit')}
					if ( spotLit ) {${spotDeskOcclusion}
						spotLightShadow = spotLightShadows[ i ];
						directLight.color *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
						RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
					}
				}
			}
			#pragma unroll_loop_end
			#if NUM_SPOT_LIGHTS > NUM_SPOT_LIGHT_SHADOWS
				for ( int i = NUM_SPOT_LIGHT_SHADOWS; i < uSpotCount; i ++ ) {
					spotLight = spotLights[ i ];
					getSpotLightInfo( spotLight, geometryPosition, directLight );
					if ( directLight.visible ) {${dotNLCheck('spotLit')}
						if ( spotLit ) {${spotDeskOcclusion}
							RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
						}
					}
				}
			#endif
		#else
			for ( int i = 0; i < uSpotCount; i ++ ) {
				spotLight = spotLights[ i ];
				getSpotLightInfo( spotLight, geometryPosition, directLight );
				if ( directLight.visible ) {${dotNLCheck('spotLit')}
					if ( spotLit ) {${spotDeskOcclusion}
						RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
					}
				}
			}
		#endif
	#endif
#endif`;

  let source = base;
  if (source.includes(pointBlock)) {
    source = source.replace(pointBlock, pointReplacement);
  }
  if (source.includes(spotBlock)) {
    source = source.replace(spotBlock, spotReplacement);
  } else {
    source = source.replace(
      'getSpotLightInfo( spotLight, geometryPosition, directLight );',
      `getSpotLightInfo( spotLight, geometryPosition, directLight );
      if (directLight.visible) {${dotNLCheck('spotLit')}
        if (!spotLit) {
          directLight.visible = false;
        } else if (studioPosition.y < ${desk.top}) {
          directLight.color *= deskVisibility(studioPosition,
            cameraPosition + transpose(mat3(viewMatrix)) * spotLight.position);
        }
      }`,
    );
  }
  source = source.replace(
    'getDirectionalLightInfo( directionalLight, directLight );',
    `getDirectionalLightInfo( directionalLight, directLight );
      if (directLight.visible) {${dotNLCheck('dirLit')}
        if (!dirLit) {
          directLight.visible = false;
        } else {
        #if !defined(USE_SHADOWMAP) || NUM_DIR_LIGHT_SHADOWS == 0
          directLight.color *= transmittedSun(studioPosition,
            -inverseTransformDirection(directLight.direction, viewMatrix), windowSlats);
        #else
          directLight.color *= sunThroughWindowOpening(studioPosition,
            -inverseTransformDirection(directLight.direction, viewMatrix));
        #endif
        }
      }`,
  );
  return includeCabinet ? source + '\n' + cabinetDirectGLSL : source;
}

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
  const caseEmitterCount = { value: 5 };
  const restore: Array<() => void> = [];
  const seen = new Set<T.MeshStandardMaterial>();
  const options =
    typeof location === 'undefined' ? undefined : new URLSearchParams(location.search);
  const sharedReflections = options?.get('studio-reflections') !== 'split';
  const lighting = options?.get('studio-lighting');
  const leanKernel = options?.get('studio-light-kernel') === 'lean';
  const matteLighting = lighting === 'matte';
  const legacyLighting = lighting === 'legacy';
  // Cull zero-intensity lights and back-facing RectAreaLights across both high and low quality
  // (zero visual difference, skips unused day/night lights in every fragment pass).
  let cullDirectLights = !legacyLighting;
  let leanDirectLights = leanKernel && initial.quality === 'low';
  const lightEvaluation = buildRoomLightEvaluation(undefined, false);
  const leanEvaluation = leanKernel ? leanRoomLightEvaluation(lightEvaluation) : lightEvaluation;
  const cabinetLightEvaluation = buildRoomLightEvaluation(undefined, true);
  const cabinetLeanEvaluation = leanKernel
    ? leanRoomLightEvaluation(cabinetLightEvaluation)
    : cabinetLightEvaluation;
  const prepare = (object: T.Object3D) => {
    if (!(object as T.Mesh).isMesh) return;
    const mesh = object as T.Mesh;
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      if (
        !(material as T.MeshStandardMaterial).isMeshStandardMaterial ||
        material.transparent ||
        seen.has(material as T.MeshStandardMaterial)
      )
        continue;
      const standard = material as T.MeshStandardMaterial;
      seen.add(standard);
      const compile = standard.onBeforeCompile;
      const defaultCompile =
        compile === T.Material.prototype.onBeforeCompile ||
        !Object.prototype.hasOwnProperty.call(standard, 'onBeforeCompile');
      const standardDepth = hasStandardRoomDepth(standard);
      const matte = matteLighting && standard.userData.studioMatte === true && defaultCompile;
      const originalKey = standard.customProgramCacheKey;
      const cacheKey = standard.customProgramCacheKey();
      const physical = (standard as T.MeshPhysicalMaterial).isMeshPhysicalMaterial
        ? (standard as T.MeshPhysicalMaterial)
        : undefined;
      const simplifyPhysical =
        physical !== undefined &&
        physical.transmission === 0 &&
        physical.iridescence === 0 &&
        physical.anisotropy === 0 &&
        physical.sheen === 0 &&
        physical.clearcoatMap === null &&
        physical.clearcoatRoughnessMap === null &&
        physical.clearcoatNormalMap === null &&
        physical.specularColorMap === null &&
        physical.specularIntensityMap === null &&
        Math.abs(physical.specularIntensity - 1) < 1e-4 &&
        physical.specularColor.r > 0.999 &&
        physical.specularColor.g > 0.999 &&
        physical.specularColor.b > 0.999 &&
        Math.abs(physical.ior - 1.5) < 1e-4 &&
        defaultCompile;
      const originalPhysical =
        simplifyPhysical && physical
          ? {
              type: physical.type,
              clearcoat: physical.clearcoat,
              roughness: physical.roughness,
              envMapIntensity: physical.envMapIntensity,
              hadPhysicalDefine: Boolean(physical.defines && 'PHYSICAL' in physical.defines),
              physicalDefineValue: physical.defines?.PHYSICAL,
            }
          : undefined;
      if (simplifyPhysical && physical) {
        if (physical.clearcoat > 0) {
          const coat = physical.clearcoat;
          physical.roughness = T.MathUtils.clamp(
            T.MathUtils.lerp(physical.roughness, physical.clearcoatRoughness, coat * 0.35),
            0.04,
            1,
          );
          physical.envMapIntensity = Math.max(physical.envMapIntensity, 1 + coat * 0.28);
          physical.clearcoat = 0;
        }
        physical.type = 'MeshStandardMaterial';
        if (physical.defines) delete physical.defines.PHYSICAL;
        Object.defineProperty(physical, 'isMeshPhysicalMaterial', {
          value: false,
          configurable: true,
        });
      }
      const localReflections = standard.metalness > 0.1 || standard.roughness < 0.46;
      const reflectionProjection = { value: localReflections };
      const cabinet = standard.userData.studioCabinetSpots as CabinetSpotBinding | undefined;
      restore.push(() => {
        standard.dispose();
        if (originalPhysical && physical) {
          physical.type = originalPhysical.type;
          delete (physical as { isMeshPhysicalMaterial?: boolean }).isMeshPhysicalMaterial;
          if (originalPhysical.hadPhysicalDefine) {
            physical.defines ??= {};
            physical.defines.PHYSICAL = originalPhysical.physicalDefineValue;
          }
          physical.clearcoat = originalPhysical.clearcoat;
          physical.roughness = originalPhysical.roughness;
          physical.envMapIntensity = originalPhysical.envMapIntensity;
        }
        standard.onBeforeCompile = compile;
        standard.customProgramCacheKey = originalKey;
        standard.needsUpdate = true;
      });
      standard.dispose();
      standard.customProgramCacheKey = () =>
        cacheKey +
        '-studio-room-visibility-' +
        (sharedReflections ? 'shared' : Number(localReflections)) +
        (cullDirectLights ? (matte ? '-matte' : '-culled') : '') +
        (leanDirectLights ? '-lean' : '') +
        (cabinet ? '-cabinet' : '');
      standard.onBeforeCompile = (shader, renderer) => {
        compile.call(standard, shader, renderer);
        if (sharedReflections) shader.uniforms.studioProjectReflections = reflectionProjection;
        if (localReflections || sharedReflections)
          projectRoomReflections(shader, sharedReflections);
        shader.uniforms.roomVisibility = uniform;
        shader.uniforms.roomBounce = bounce.field;
        shader.uniforms.roomBounceStrength = bounce.strength;
        shader.uniforms.windowSlats = { value: slats };
        shader.uniforms.uPointCount = {
          get value() {
            return Array.isArray(shader.uniforms.pointLights?.value)
              ? shader.uniforms.pointLights.value.length
              : 0;
          },
        };
        shader.uniforms.uSpotCount = {
          get value() {
            return Array.isArray(shader.uniforms.spotLights?.value)
              ? shader.uniforms.spotLights.value.length
              : 0;
          },
        };
        if (cabinet) {
          shader.uniforms.caseEmitters = { value: cabinet.centers };
          shader.uniforms.caseAxes = { value: cabinet.axes };
          shader.uniforms.caseOptics = { value: cabinet.optics };
          shader.uniforms.caseDimmer = cabinet.power;
          shader.uniforms.uCaseEmitterCount = caseEmitterCount;
          shader.uniforms.caseToWorld = { value: cabinet.matrixWorld };
          shader.uniforms.caseFromWorld = { value: cabinet.inverse };
          shader.uniforms.caseVisibility = cabinet.visibility;
          shader.uniforms.caseVisibilityReady = cabinet.visibilityReady;
          shader.uniforms.caseReceiverMode = { value: cabinet.receiverMode };
        }
        shader.vertexShader =
          'varying vec3 studioPosition;\n' +
          shader.vertexShader.replace(
            '#include <project_vertex>',
            `
          #include <project_vertex>
          studioPosition = cameraPosition + transpose(mat3(viewMatrix)) * mvPosition.xyz;
        `,
          );
        const evaluation = cabinet
          ? leanDirectLights
            ? cabinetLeanEvaluation
            : cabinetLightEvaluation
          : leanDirectLights
            ? leanEvaluation
            : lightEvaluation;
        let fragment = cullDirectLights
          ? cullRoomDirectLighting(
              matte ? matteRoomLighting(shader.fragmentShader) : shader.fragmentShader,
              evaluation,
              leanDirectLights,
            )
          : shader.fragmentShader.replace('#include <lights_fragment_begin>', evaluation);
        if (cullDirectLights && !leanDirectLights) {
          fragment = leanRoomPunctualLighting(fragment);
        }
        shader.fragmentShader =
          `varying vec3 studioPosition;
uniform highp sampler3D roomVisibility;
uniform highp sampler3D roomBounce;
uniform float roomBounceStrength;
uniform vec2 windowSlats;
uniform int uPointCount;
uniform int uSpotCount;
${cabinet ? cabinetUniformsGLSL : ''}` +
          windowSunGLSL +
          deskOcclusionGLSL +
          fragment.replace(
            '#include <aomap_fragment>',
            `
          #include <aomap_fragment>${cabinet ? cabinetAomapGLSL : ''}
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
      if (standardDepth) markStandardRoomDepth(standard);
      standard.needsUpdate = true;
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
      const cull = !legacyLighting;
      const lean = leanKernel && env.quality === 'low';
      if (cull !== cullDirectLights || lean !== leanDirectLights) {
        cullDirectLights = cull;
        leanDirectLights = lean;
        for (const material of seen) material.needsUpdate = true;
      }
      if (env.quality === 'low') bounce.strength.value = 0;
      else bounce.update(env, delta);
    },
    dispose() {
      controller.abort();
      bounce.dispose();
      uniform.value.dispose();
      restore.forEach((reset) => reset());
    },
  };
}
