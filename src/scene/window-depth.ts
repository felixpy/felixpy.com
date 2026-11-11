import * as T from 'three';
import { windowEye } from './camera';
import type { buildRainGlass } from './rain-glass';

const radians = T.MathUtils.degToRad;
const yaw = { start: radians(-58), span: radians(167) };
const pitchStops = [
  { v: 0, pitch: radians(-60) },
  { v: 0.23, pitch: radians(-7) },
  { v: 0.73, pitch: radians(18) },
  { v: 1, pitch: radians(68) },
];
export const panoramaOrigin = new T.Vector3(windowEye.x, windowEye.y, windowEye.z);
export const panoramaMeshName = 'Depth-reprojected waterfront photograph';
export const waterfrontFarClip = 3000;
export const skylineDepth = 650;

// Shift horizontal framing toward the desk while keeping the projection plane
// parallel to the window, so a level shoreline stays level straight on.
const horizontalAim = Math.tan(radians(17));
const verticalVanishingX = 0.51;

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
  upright = 0,
) {
  // Invert the projection's water extension to put lights on their photo row.
  const projectedV = v < waterline ? waterline * (1 + Math.log(v / waterline)) : v;
  const rectified = verticalVanishingX + (u - verticalVanishingX) / (1 - upright * (v - waterline));
  const aim = (rectified - calibration.x) / calibration.z;
  const slope = (aim + horizontalAim) / (1 - aim * horizontalAim);
  return target
    .set(-distance, ((projectedV - calibration.y) / calibration.w) * distance, -slope * distance)
    .add(panoramaOrigin);
}

export function panoramaMaterial(glass?: ReturnType<typeof buildRainGlass>) {
  const uniforms = {
    photoA: { value: null as T.Texture | null },
    photoB: { value: null as T.Texture | null },
    nightA: { value: null as T.Texture | null },
    nightB: { value: null as T.Texture | null },
    depthA: { value: null as T.Texture | null },
    depthB: { value: null as T.Texture | null },
    rangeA: { value: new T.Vector2() },
    rangeB: { value: new T.Vector2() },
    calibrationA: { value: new T.Vector4() },
    calibrationB: { value: new T.Vector4() },
    waterlines: { value: new T.Vector2(0.115, 0.145) },
    verticalCorrections: { value: new T.Vector2() },
    blend: { value: 0 },
    sameDepth: { value: true },
    night: { value: 0 },
    mist: { value: 0 },
    grade: { value: new T.Color() },
    captureOrigin: { value: panoramaOrigin },
    horizontalAim: { value: horizontalAim },
    windowProjection: { value: new T.Matrix4() },
    ...(glass?.uniforms ?? {
      rainAmount: { value: 0 },
      rainBeads: { value: null },
      rainRuns: { value: null },
      glassOrigin: { value: new T.Vector3() },
      glassSize: { value: new T.Vector2() },
    }),
  };
  const material = new T.ShaderMaterial({
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
      uniform sampler2D photoA, photoB, nightA, nightB, depthA, depthB;
      uniform sampler2D rainBeads, rainRuns;
      uniform vec2 rangeA, rangeB;
      uniform vec4 calibrationA, calibrationB;
      uniform vec2 waterlines, verticalCorrections, glassSize;
      uniform float blend, night, mist, rainAmount;
      uniform bool sameDepth;
      uniform vec3 grade, captureOrigin, glassOrigin;
      uniform float horizontalAim;
      uniform mat4 windowProjection;

      float rayDistance(vec3 ray, vec3 offset, float planeDepth) {
        return (planeDepth + offset.x) / max(0.035, -ray.x);
      }

      vec2 photoCoordinates(vec3 ray, vec3 offset, vec4 calibration, float planeDepth, float waterline, float upright) {
        vec3 hit = offset + ray * rayDistance(ray, offset, planeDepth);
        vec2 slope = vec2(-hit.z, hit.y) / planeDepth;
        slope.x = (slope.x - horizontalAim) / max(0.035, 1.0 + slope.x * horizontalAim);
        vec2 uv = calibration.xy + slope * calibration.zw;
        // Extend the foreground river smoothly without repeating the shoreline.
        if (uv.y < waterline) uv.y = waterline * exp((uv.y - waterline) / waterline);
        // Remove the plate's vertical convergence while holding the shoreline in place.
        uv.x = ${verticalVanishingX} + (uv.x - ${verticalVanishingX}) * (1.0 - upright * (uv.y - waterline));
        return clamp(uv, 0.001, 0.999);
      }

      float planeDepth(float inverseDepth, vec2 range) {
        return 1.0 / mix(1.0 / range.y, 1.0 / range.x, inverseDepth);
      }

      // Keep the skyline projective so depth estimates cannot bend building edges.
      // Water below the bank can move; the sharp depth still occludes passing lights.
      vec3 locate(sampler2D depth, vec2 range, vec4 calibration, float waterline, float upright, vec3 ray, vec3 offset) {
        vec2 uv = photoCoordinates(ray, offset, calibration, ${skylineDepth}.0, waterline, upright);
        float water = 1.0 - smoothstep(waterline - 0.04, waterline, uv.y);
        if (water > 0.0) {
          float riverDepth = planeDepth(texture2D(depth, uv).r, range);
          float parallaxDepth = mix(${skylineDepth}.0, riverDepth, water);
          uv = photoCoordinates(ray, offset, calibration, parallaxDepth, waterline, upright);
        }
        float sharp = planeDepth(texture2D(depth, uv).g, range);
        return vec3(uv, rayDistance(ray, offset, sharp));
      }

      vec3 exposure(sampler2D day, sampler2D evening, vec2 uv) {
        if (night <= 0.001) return texture2D(day, uv).rgb;
        if (night >= 0.999) return texture2D(evening, uv).rgb;
        return mix(texture2D(day, uv).rgb, texture2D(evening, uv).rgb, night);
      }

      float wetHeight(vec2 uv) {
        return max(texture2D(rainBeads, uv).r, texture2D(rainRuns, uv).r);
      }

      vec3 glassLens(vec3 ray) {
        if (rainAmount <= 0.012 || ray.x >= 0.0) return vec3(0.0);
        float distance = (glassOrigin.x - cameraPosition.x) / ray.x;
        if (distance <= 0.0) return vec3(0.0);
        vec3 hit = cameraPosition + ray * distance;
        vec2 uv = vec2(glassOrigin.z - hit.z, hit.y - glassOrigin.y) / glassSize;
        if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return vec3(0.0);
        float height = wetHeight(uv);
        if (height <= 0.018) return vec3(0.0);
        vec2 dx = vec2(0.00115, 0.0), dy = vec2(0.0, 0.00139);
        vec2 slope = vec2(wetHeight(uv - dx) - wetHeight(uv + dx), wetHeight(uv - dy) - wetHeight(uv + dy));
        return vec3(clamp(slope * 1.9, -1.0, 1.0), smoothstep(0.018, 0.22, height));
      }

      void main() {
        vec3 ray = normalize(shellPoint - cameraPosition);
        vec3 offset = cameraPosition - captureOrigin;
        vec3 lens = glassLens(ray);
        vec2 refraction = lens.xy * (0.014 * lens.z * rainAmount);
        vec3 a = locate(depthA, rangeA, calibrationA, waterlines.x, verticalCorrections.x, ray, offset);
        vec3 color = exposure(photoA, nightA, a.xy - refraction * calibrationA.zw);
        float distance = a.z;
        if (blend > 0.0) {
          vec3 b = a;
          if (!sameDepth) b = locate(depthB, rangeB, calibrationB, waterlines.y, verticalCorrections.y, ray, offset);
          color = mix(color, exposure(photoB, nightB, b.xy - refraction * calibrationB.zw), blend);
          distance = mix(distance, b.z, blend);
        }
        vec3 point = cameraPosition + ray * distance;
        vec4 clip = windowProjection * viewMatrix * vec4(point, 1.0);
        gl_FragDepth = 0.5 * (clip.z / clip.w) + 0.5;
        float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
        color = mix(color, vec3(luma), mist) * grade;
        float wet = lens.z * rainAmount;
        float rim = clamp(length(lens.xy), 0.0, 1.0);
        float glint = max(0.0, dot(lens.xy, vec2(-0.53, 0.85)));
        color *= 1.0 - (0.20 + rim * 0.45) * wet;
        color += vec3(0.51, 0.57, 0.65) * (rim * 0.027 + pow(glint, 4.0) * 0.29) * wet;
        gl_FragColor = vec4(color, 1.0);
        #include <colorspace_fragment>
      }
    `,
  });
  material.onBeforeRender = (_renderer, _scene, camera) => {
    uniforms.windowProjection.value = camera.projectionMatrix;
  };
  return { material, uniforms };
}
