import * as T from 'three';
import { paneOptics, rainUniforms, type buildRainGlass } from './rain-glass';
import { roomEffectMaterial } from './room-effect-material';

const radians = T.MathUtils.degToRad;
const yaw = { start: radians(-58), span: radians(167) };
const pitchStops = [
  { v: 0, pitch: radians(-60) },
  { v: 0.23, pitch: radians(-7) },
  { v: 0.73, pitch: radians(18) },
  { v: 1, pitch: radians(68) },
];
export const panoramaOrigin = new T.Vector3(0.17, 1.58, 0.585);
export const panoramaMeshName = 'Depth-reprojected waterfront photograph';
export const waterfrontFarClip = 3000;
export const skylineDepth = 650;
export const bankSlope = 0.128;
const quayDistance = 510;
export const riverLevel = panoramaOrigin.y - quayDistance * bankSlope;

export function panoramaPoint(u: number, v: number, radius: number, target: T.Vector3) {
  const upper = v < pitchStops[1].v ? 1 : v < pitchStops[2].v ? 2 : 3;
  const a = pitchStops[upper - 1],
    b = pitchStops[upper];
  const pitch = T.MathUtils.lerp(a.pitch, b.pitch, (v - a.v) / (b.v - a.v));
  const angle = yaw.start + u * yaw.span;
  const rim = Math.cos(pitch) * radius;
  return target
    .set(-Math.cos(angle) * rim, Math.sin(pitch) * radius, -Math.sin(angle) * rim)
    .add(panoramaOrigin);
}

export function waterfrontPoint(
  u: number,
  v: number,
  calibration: T.Vector4,
  distance: number,
  waterline: number,
  target: T.Vector3,
) {
  const projectedV = v < waterline ? waterline * (1 + Math.log(v / waterline)) : v;
  const horizontal = (u - calibration.x) / calibration.z;
  const height = (projectedV - calibration.y) / calibration.w;
  return target.set(-distance, height * distance, -horizontal * distance).add(panoramaOrigin);
}

export function panoramaMaterial(glass?: ReturnType<typeof buildRainGlass>) {
  const uniforms = {
    photoA: { value: null as T.Texture | null },
    photoB: { value: null as T.Texture | null },
    depthA: { value: null as T.Texture | null },
    depthB: { value: null as T.Texture | null },
    rangeA: { value: new T.Vector2() },
    rangeB: { value: new T.Vector2() },
    calibrationA: { value: new T.Vector4() },
    calibrationB: { value: new T.Vector4() },
    waterlines: { value: new T.Vector2(0.115, 0.145) },
    clearSkyFrom: { value: new T.Vector2(1, 1) },
    shoreA: { value: new Float32Array(9) },
    shoreB: { value: new Float32Array(9) },
    flowA: { value: new T.Vector3() },
    flowB: { value: new T.Vector3() },
    blend: { value: 0 },
    riverTime: { value: 0 },
    mist: { value: 0 },
    physicalWater: { value: false },
    waterSlopes: { value: null as T.Texture | null },
    ferryReflection: { value: null as T.Texture | null },
    waterLevel: { value: riverLevel },
    ferryTrack: { value: new T.Vector4(10000, 10000, 0, -1) },
    nightWater: { value: 0 },
    windStrength: { value: 0.5 },
    grade: { value: new T.Color() },
    captureOrigin: { value: panoramaOrigin },
    windowProjection: { value: new T.Matrix4() },
    ...(glass?.uniforms ?? {
      ...rainUniforms(),
      glassOrigin: { value: new T.Vector3() },
      glassSize: { value: new T.Vector2() },
    }),
  };
  const material = roomEffectMaterial(
    {
      uniforms,
      side: T.DoubleSide,
      toneMapped: false,
      vertexShader: `
      varying vec3 shellPoint;
      void main() {
        shellPoint = (modelMatrix * vec4(position, 1.0)).xyz;
        gl_Position = projectionMatrix * viewMatrix * vec4(shellPoint, 1.0);
      }
    `,
      fragmentShader: `
      varying vec3 shellPoint;
      uniform sampler2D photoA, photoB, depthA, depthB;
      uniform sampler2D waterSlopes, ferryReflection;
      ${paneOptics}
      uniform vec2 rangeA, rangeB;
      uniform vec4 calibrationA, calibrationB;
      uniform vec2 waterlines, clearSkyFrom;
      uniform float shoreA[9], shoreB[9];
      uniform vec3 flowA, flowB;
      uniform float blend, mist, rainAmount, riverTime, waterLevel, nightWater, windStrength;
      uniform vec4 ferryTrack;
      uniform bool physicalWater;
      uniform vec3 grade, captureOrigin, glassOrigin;
      uniform mat4 windowProjection;

      float rayDistance(vec3 ray, vec3 offset, float depth) {
        return (depth + offset.x) / max(0.035,-ray.x);
      }

      float photographedBank(float u, float shore[9]) {
        float along = clamp(u, 0.0, 1.0) * 8.0;
        int column = min(int(along), 7);
        return mix(shore[column], shore[column + 1], along - float(column));
      }

      vec2 photoCoordinates(vec3 ray, vec3 offset, vec4 calibration, float depth, float waterline, float shore[9]) {
        vec3 hit = offset + ray * rayDistance(ray, offset, depth);
        vec2 uv = calibration.xy + vec2(-hit.z, hit.y) * calibration.zw / depth;
        float bank = shore[4] > 0.0 ? photographedBank(uv.x, shore) : waterline;
        if (uv.y < bank) uv.y = bank * exp((uv.y - bank) / bank);
        return uv;
      }

      float planeDepth(float inverseDepth, vec2 range) {
        return 1.0 / mix(1.0 / range.y, 1.0 / range.x, inverseDepth);
      }

      vec3 locate(sampler2D depth, vec2 range, vec4 calibration, float waterline, vec3 ray, vec3 offset, float shore[9], float sky) {
        if (waterline == 0.0) {
          return vec3(fract(0.5 + (atan(-ray.z,-ray.x) + calibration.x) / 6.2831853),
                      0.5 + asin(clamp(ray.y,-1.0,1.0)) / 3.14159265, 1600.0);
        }
        if (physicalWater && ray.y < -0.001) {
          float distance = (waterLevel - cameraPosition.y) / ray.y;
          float depthAtWater = -offset.x - ray.x * distance;
          if (distance > 0.0 && depthAtWater > 0.0 && depthAtWater < range.y) {
            vec2 surface = photoCoordinates(ray, offset, calibration, depthAtWater, waterline, shore);
            if (surface.y <= photographedBank(surface.x, shore)) return vec3(surface, distance);
          }
        }
        vec2 uv = photoCoordinates(ray, offset, calibration, ${skylineDepth}.0, waterline, shore);
        float water = 1.0 - smoothstep(waterline - 0.04, waterline, uv.y);
        if (physicalWater || water > 0.0) {
          float surfaceDepth = planeDepth(texture2D(depth, uv).r, range);
          float parallaxDepth = mix(${skylineDepth}.0, surfaceDepth, physicalWater ? 1.0 : water);
          uv = photoCoordinates(ray, offset, calibration, parallaxDepth, waterline, shore);
        }
        float sharp = planeDepth(texture2D(depth, uv).g, range);
        if (uv.y > sky && sky < 1.0) {
          float height = uv.y - sky;
          uv.y = sky + height / (1.0 + height / (1.0 - sky));
        }
        return vec3(uv, rayDistance(ray, offset, sharp));
      }

      vec3 exposure(sampler2D photo, vec2 uv) {
        return texture2D(photo, clamp(uv, 0.001, 0.999)).rgb;
      }

      vec3 riverExposure(sampler2D photo, vec2 uv, float bank, vec3 ray, vec3 flow) {
        vec3 shore = exposure(photo, uv);
        float water = 1.0 - smoothstep(bank - 0.009, bank - 0.0015, uv.y);
        if (water <= 0.001) return shore;
        float distance = (waterLevel - cameraPosition.y) / min(-0.003, ray.y);
        vec2 surface = cameraPosition.xz + ray.xz * distance;
        vec2 p = (surface - flow.xy * riverTime) / (38.0 * flow.z);
        vec3 longWave = texture2D(waterSlopes, p + vec2(0.012, -0.008) * riverTime).rgb - 0.5;
        mat2 crossDirection = mat2(0.819, -0.574, 0.574, 0.819);
        vec3 shortWave = texture2D(waterSlopes, crossDirection*p*2.73 - vec2(0.027,0.011)*riverTime).rgb - 0.5;
        vec2 normalSlope = longWave.rg + 0.44 * crossDirection * shortWave.rg;
        float chop = shortWave.g * 2.0;
        float slope = dot(normalSlope, normalize(vec2(-0.32,0.95))) * 2.2;
        float foreground = 1.0 - smoothstep(bank * 0.12, bank * 0.71, uv.y);
        vec2 displacement = vec2(normalSlope.x * 0.009, normalSlope.y * bank * 0.093) * (0.6 + 0.8 * windStrength);
        float phase = fract(riverTime / 4.0);
        vec2 travel = vec2(-flow.y * 0.013, flow.x * bank * 0.035) * (0.55 + 0.8 * foreground);
        vec2 advected = uv + displacement * (0.65 + 0.6 * foreground);
        vec2 first = advected - travel * (phase - 0.5);
        vec2 second = advected - travel * (fract(phase + 0.5) - 0.5);
        first.y = clamp(first.y, 0.001, bank - 0.006);
        second.y = clamp(second.y, 0.001, bank - 0.006);
        vec3 color = mix(exposure(photo, first), exposure(photo, second), abs(phase * 2.0 - 1.0));
        float glitter = smoothstep(0.22, 0.85, slope);
        color *= 1.0 + (0.12 + 0.12 * windStrength) * slope;
        color += (0.005 + 0.012 * windStrength) * glitter * (1.0 - 0.83 * nightWater);
        vec2 relative = surface - ferryTrack.xy;
        float astern = -dot(relative, ferryTrack.zw) - 15.6;
        float across = abs(dot(relative, vec2(-ferryTrack.w, ferryTrack.z)));
        float envelope = smoothstep(-0.6, 2.0, astern) * (1.0 - smoothstep(14.0, 76.0, astern));
        float crest = 2.5 + astern * 0.25;
        float wake = exp(-pow((across - crest) / max(0.9, 0.7 + astern * 0.054), 2.0));
        float wavelet = sin(astern * 0.68 + 1.16 * across - riverTime * 1.3 + 4.0 * longWave.b);
        color *= 1.0 + envelope * wake * wavelet * (0.12 + 0.08 * chop);
        float propwash = exp(-across * across / (4.5 + 0.16 * max(0.0,astern))) * exp(-max(0.0, astern) * 0.082);
        float bubbles = smoothstep(-0.2, 0.51, chop + 0.25 * wavelet);
        float foam = envelope * (propwash * (0.13 + 0.44 * bubbles) + wake * bubbles * 0.055);
        color = mix(color, mix(vec3(0.48, 0.57, 0.59), vec3(0.083, 0.104, 0.12), nightWater), clamp(foam,0.0,0.64));
        vec2 beam = vec2(-ferryTrack.w, ferryTrack.z);
        float along = dot(relative, ferryTrack.zw), side = dot(relative, beam);
        float facing = dot(cameraPosition.xz - ferryTrack.xy, beam) >= 0.0 ? 1.0 : -1.0;
        beam *= facing;
        side *= facing;
        if (side > 2.2 && side < 75.0 && abs(along) < 40.0) {
          vec3 normal = normalize(vec3(0.047 * normalSlope.x, 1.0, 0.047 * normalSlope.y));
          vec3 reflectedRay = reflect(ray, normal);
          float hit = (3.05 - side) / min(-0.1, dot(reflectedRay.xz, beam));
          vec2 mirror = vec2((along + hit * dot(reflectedRay.xz, ferryTrack.zw) + 17.5) / 35.0,
                             (hit * reflectedRay.y + 1.66) / 10.0);
          if (hit > 0.0 && all(greaterThan(mirror,vec2(0.0))) && all(lessThan(mirror,vec2(1.0)))) {
            vec2 atlas = vec2(mirror.x, 0.5 * mirror.y);
            vec4 vessel = mix(texture2D(ferryReflection, atlas + vec2(0.0,0.5)), texture2D(ferryReflection, atlas), nightWater);
            float fresnel = 0.025 + 0.975 * pow(1.0 - abs(dot(ray,normal)), 5.0);
            color = mix(color, vessel.rgb, min(0.77, fresnel * 1.42) * vessel.a);
          }
        }
        return mix(shore, color, water);
      }

      vec3 photographedView(sampler2D photo, vec2 uv, float bank, vec3 ray, float shore[9], vec3 flow) {
        vec3 color = vec3(0.0);
        if (bank == 0.0)
          color = texture2D(photo, uv).rgb;
        else
          color = riverExposure(photo, uv, photographedBank(uv.x, shore), ray, flow);
        return color;
      }

      vec3 glassLens(vec3 ray) {
        if (rainAmount <= 0.012 || ray.x >= 0.0) return vec3(0.0);
        float distance = (glassOrigin.x - cameraPosition.x) / ray.x;
        if (distance <= 0.0) return vec3(0.0);
        vec3 hit = cameraPosition + ray * distance;
        vec2 uv = vec2(glassOrigin.z - hit.z, hit.y - glassOrigin.y) / glassSize;
        if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return vec3(0.0);
        return wetSurface(uv);
      }

      void main() {
        vec3 ray = normalize(shellPoint - cameraPosition);
        vec3 offset = cameraPosition - captureOrigin;
        vec3 lens = glassLens(ray);
        vec3 viewRay = ray;
        if (lens.z > 0.012) {
          vec3 internalRay = refract(ray, vec3(1.,0.,0.), 1. / 1.333);
          vec3 inwardNormal = normalize(vec3(1., -lens.y, lens.x));
          vec3 outgoing = refract(internalRay, inwardNormal, 1.333);
          if (dot(outgoing,outgoing) > 0.5 && outgoing.x < -0.09)
            viewRay = normalize(mix(ray, outgoing, rainAmount * lens.z));
        }
        vec3 a = locate(depthA, rangeA, calibrationA, waterlines.x, ray, offset, shoreA, clearSkyFrom.x);
        bool bent = lens.z > 0.012;
        vec2 firstUV = bent ? locate(depthA, rangeA, calibrationA, waterlines.x, viewRay, offset, shoreA, clearSkyFrom.x).xy : a.xy;
        vec3 color = photographedView(photoA, firstUV, waterlines.x, viewRay, shoreA, flowA);
        float distance = a.z;
        if (blend > 0.0) {
          vec3 b = locate(depthB, rangeB, calibrationB, waterlines.y, ray, offset, shoreB, clearSkyFrom.y);
          vec2 secondUV = bent ? locate(depthB, rangeB, calibrationB, waterlines.y, viewRay, offset, shoreB, clearSkyFrom.y).xy : b.xy;
          color = mix(color, photographedView(photoB, secondUV, waterlines.y, viewRay, shoreB, flowB), blend);
          distance = mix(distance, b.z, blend);
        }
        vec3 point = cameraPosition + ray * distance;
        vec4 clip = windowProjection * viewMatrix * vec4(point, 1.0);
        gl_FragDepth = 0.5 * (clip.z / clip.w) + 0.5;
        float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
        color = mix(color, vec3(luma), mist) * grade;
        gl_FragColor = vec4(color, 1.0);
        #include <colorspace_fragment>
      }
    `,
    },
    `attribute vec3 position;
      uniform mat4 modelMatrix, viewMatrix, projectionMatrix;`,
    `uniform vec3 cameraPosition;
      uniform mat4 viewMatrix;`,
  );
  const setup = material.onBeforeRender;
  material.onBeforeRender = (...args) => {
    setup.apply(material, args);
    const [, , camera] = args;
    uniforms.windowProjection.value = camera.projectionMatrix;
  };
  return { material, uniforms };
}
