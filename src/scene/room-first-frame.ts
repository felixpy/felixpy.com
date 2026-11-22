import {
  BufferGeometry,
  Camera,
  Color,
  DataTexture,
  DirectionalLight,
  DoubleSide,
  Frustum,
  Group,
  InstancedMesh,
  Light,
  Material,
  Matrix3,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  GLSL3,
  PerspectiveCamera,
  PlaneGeometry,
  MeshStandardMaterial,
  Scene,
  RawShaderMaterial,
  SpotLight,
  Texture,
  Vector2,
  Vector3,
  Vector4,
  WebGLRenderTarget,
  WebGLRenderer,
} from 'three';
import type { RoomLook } from '../app/environment';
import { oledWallpaper } from './oled-wallpaper';
import { roomCurves } from './room-looks';
import { deskOcclusionGLSL } from './desk-occlusion';
import { windowSunGLSL } from './window-sun';
import { warmRoomEffect } from './room-effect-material';

type Surface = MeshStandardMaterial | MeshBasicMaterial;
const maxPreviewLights = 6;
const previewBufferMinimum = 128 * 1024;
const previewUploadBudget = 3;

const vertex = `
precision highp float;
in vec3 position;
in vec3 normal;
in vec2 uv;
in vec3 color;
uniform mat4 modelMatrix;
uniform mat4 viewMatrix;
uniform mat4 projectionMatrix;
uniform mat3 normalMatrix;
#ifdef FIRST_INSTANCED
in mat4 instanceMatrix;
#endif
out vec2 firstUv;
out vec3 firstColor;
out vec3 firstNormal;
out vec3 firstWorld;
uniform mat3 mapMatrix;
void main() {
  vec4 positionLocal = vec4(position, 1.0);
  vec3 normalLocal = normal;
  #ifdef FIRST_INSTANCED
    positionLocal = instanceMatrix * positionLocal;
    normalLocal = mat3(instanceMatrix) * normalLocal;
  #endif
  vec4 world = modelMatrix * positionLocal;
  firstWorld = world.xyz;
  firstNormal = normalize(transpose(mat3(viewMatrix)) * normalMatrix * normalLocal);
  firstUv = (mapMatrix * vec3(uv, 1.)).xy;
  firstColor = color;
  gl_Position = projectionMatrix * viewMatrix * world;
}`;

const fragment = `
precision highp float;
uniform vec3 cameraPosition;
uniform float applyTone;
out vec4 pixel;
#include <tonemapping_pars_fragment>
#include <colorspace_pars_fragment>
uniform sampler2D albedo;
uniform sampler2D mask;
uniform vec3 tint;
uniform vec3 emission;
uniform float opacity;
uniform float alphaCut;
uniform bool doubleSided;
uniform float lit;
uniform float metal;
uniform float night;
uniform vec3 sunDirection;
uniform vec3 sunlight;
uniform vec2 windowSlats;
uniform int lampCount;
uniform vec4 lampPosition[${maxPreviewLights}];
uniform vec4 lampAxis[${maxPreviewLights}];
uniform vec4 lampPower[${maxPreviewLights}];
uniform vec3 gradeCurve[9];
uniform float saturation;
in vec2 firstUv;
in vec3 firstColor;
in vec3 firstNormal;
in vec3 firstWorld;
${deskOcclusionGLSL}
${windowSunGLSL}
void main() {
  vec4 texel = texture(albedo, firstUv);
  float a = opacity * texel.a * texture(mask, firstUv).g;
  if (a < alphaCut) discard;
  vec3 n = normalize(firstNormal);
  if (doubleSided && !gl_FrontFacing) n = -n;
  vec3 key = normalize(vec3(-0.82, 0.62, 0.48));
  vec3 bounce = mix(vec3(0.28,0.29,0.32), vec3(0.17,0.18,0.22), night);
  vec3 sky = mix(vec3(0.39,0.43,0.48), vec3(0.50,0.45,0.37), night);
  vec3 radiance = bounce + max(dot(n, key), 0.0) * sky + max(n.y,0.) * vec3(.21,.18,.145);
  float facingSun = max(dot(n, sunDirection), 0.0);
  if (sunlight.r > 0.0 && facingSun > 0.0) {
    radiance += sunlight * facingSun * transmittedSun(firstWorld, -sunDirection, windowSlats);
  }
  for (int i=0; i<${maxPreviewLights}; i++) {
    if (i >= lampCount) break;
    vec3 offset = lampPosition[i].xyz - firstWorld;
    float distanceSquared = max(.01, dot(offset,offset));
    vec3 incoming = offset * inversesqrt(distanceSquared);
    float falloff = smoothstep(lampAxis[i].w, lampPower[i].w, dot(-incoming,lampAxis[i].xyz));
    float range2 = distanceSquared * lampPosition[i].w;
    float cutoff = max(1. - range2 * range2, 0.);
    radiance += lampPower[i].rgb * max(0.,dot(n,incoming)) * falloff * cutoff * cutoff
      * deskVisibility(firstWorld, lampPosition[i].xyz) / distanceSquared;
  }
  vec3 reflected = reflect(normalize(firstWorld-cameraPosition),n);
  float sheen = smoothstep(.36,.94,dot(reflected,key));
  vec3 color = tint * firstColor * texel.rgb * mix(vec3(1.), radiance, lit);
  color += emission * texel.rgb + metal * (.02 + sheen * .23) * (.5 + tint);
  if (applyTone > 0.5) color = ACESFilmicToneMapping(color);
  vec3 encoded = sRGBTransferOETF(vec4(color,a)).rgb;
  vec3 position = clamp(encoded,0.,1.) * 8.;
  vec3 graded = gradeCurve[0];
  for (int i=0; i<8; i++) graded += (gradeCurve[i+1]-gradeCurve[i])*clamp(position-float(i),0.,1.);
  pixel = vec4(mix(vec3(dot(graded,vec3(.213,.715,.072))),graded,saturation),a);
}`;

export function roomFirstFrame({
  warmPreview = false,
  warmOled = false,
  warmBuffers = false,
} = {}) {
  const materials = [new Map<Surface, RawShaderMaterial>(), new Map<Surface, RawShaderMaterial>()];
  const meshes: Mesh[] = [];
  const originals: (Material | Material[])[] = [];
  const lights: Light[] = [];
  const spots: SpotLight[] = [];
  const relevance = new WeakMap<SpotLight, number>();
  const eye = new Vector3(),
    forward = new Vector3();
  const white = new DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
  white.needsUpdate = true;
  const emptyMatrix = new Matrix3();
  const black = new Color(0);
  const night = { value: 0 };
  const lampCount = { value: 0 };
  const sunDirection = { value: new Vector3() };
  const sunlight = { value: new Color(0) };
  const windowSlats = { value: new Vector2(0.0038, 0) };
  const lampPosition = { value: Array.from({ length: maxPreviewLights }, () => new Vector4()) };
  const lampAxis = {
    value: Array.from({ length: maxPreviewLights }, () => new Vector4(0, -1, 0, 0)),
  };
  const lampPower = {
    value: Array.from({ length: maxPreviewLights }, () => new Vector4(0, 0, 0, 1)),
  };
  const gradeCurve = { value: Array.from({ length: 9 }, (_, i) => new Vector3().setScalar(i / 8)) };
  const saturation = { value: 1 };
  const point = new Vector3(),
    direction = new Vector3();
  let selectedLook: RoomLook = 'neutral';
  let warmed = false;
  let stopWarming: (() => void) | undefined;
  let stopWaterfront: (() => void) | undefined;
  let oledWarmup: AbortController | undefined;
  let upload: (() => boolean) | undefined;
  let buffersReady = !warmBuffers;
  let disposeUpload: (() => void) | undefined;

  function surface(source: Material, instanced = false) {
    if (!(source instanceof MeshStandardMaterial || source instanceof MeshBasicMaterial))
      return source;
    const cache = materials[Number(instanced)];
    let material = cache.get(source);
    if (!material) {
      const { oledTime, oledClock } = source as Surface & {
        oledTime?: { value: number };
        oledClock?: Texture;
      };
      material = new RawShaderMaterial({
        glslVersion: GLSL3,
        defines: instanced ? { FIRST_INSTANCED: 1 } : {},

        vertexShader: vertex,
        fragmentShader: oledTime
          ? fragment
              .replace(
                'void main() {',
                'uniform float flowTime;\nuniform sampler2D oledClock;\n' +
                  oledWallpaper +
                  '\nvoid main() {',
              )
              .replace(
                'if (applyTone',
                'float ink = oledTextCoverage(oledClock, firstUv);\n  color += mix(oledColour(firstUv, flowTime), oledInk, ink);\n  if (applyTone',
              )
          : fragment,
        uniforms: {
          ...(oledTime ? { flowTime: oledTime, oledClock: { value: oledClock } } : {}),
          toneMappingExposure: { value: 1.04 },
          applyTone: { value: Number(source.toneMapped) },
          albedo: { value: white },
          mask: { value: white },
          tint: { value: source.color },
          emission: { value: black.clone() },
          lampCount,
          sunDirection,
          sunlight,
          windowSlats,
          lampPosition,
          lampPower,
          lampAxis,
          gradeCurve,
          saturation,
          mapMatrix: { value: emptyMatrix },
          opacity: { value: source.opacity },
          alphaCut: { value: source.alphaTest },
          doubleSided: { value: false },
          lit: { value: source instanceof MeshStandardMaterial ? 1 : 0 },
          metal: { value: source instanceof MeshStandardMaterial ? source.metalness : 0 },
          night,
        },
        transparent: source.transparent,
        depthTest: source.depthTest,
        depthWrite: source.depthWrite,
        blending: source.blending,
        vertexColors: source.vertexColors,
        toneMapped: source.toneMapped,
        polygonOffset: source.polygonOffset,
        polygonOffsetFactor: source.polygonOffsetFactor,
        polygonOffsetUnits: source.polygonOffsetUnits,
      });
      cache.set(source, material);
    }
    const uniforms = material.uniforms;
    material.side = source.side;
    uniforms.doubleSided.value = source.side === DoubleSide;
    const map: Texture | null = source.map;
    if (map?.matrixAutoUpdate) map.updateMatrix();
    uniforms.mapMatrix.value = map?.matrix ?? emptyMatrix;
    uniforms.albedo.value = map?.image ? map : white;
    uniforms.mask.value = source.alphaMap?.image ? source.alphaMap : white;
    uniforms.opacity.value = source.opacity;
    if (source instanceof MeshStandardMaterial)
      uniforms.emission.value
        .copy(source.emissive)
        .multiplyScalar(Math.min(2, source.emissiveIntensity));
    return material;
  }

  function previewClockMaterial() {
    const clock = Object.assign(new MeshBasicMaterial(), {
      oledTime: { value: 0 },
      oledClock: white,
    });
    const material = surface(clock);
    clock.dispose();
    return material;
  }

  function warmPreviewShaders(gl: WebGLRenderer, geometry: PlaneGeometry, group: Group) {
    group.add(new Mesh(geometry, previewClockMaterial()));
    const probe = new Scene();
    const camera = new PerspectiveCamera();
    camera.position.z = 1;
    const target = new WebGLRenderTarget(1, 1);
    let active = true;
    const timeout = window.setTimeout(finish, 1200);
    stopWarming = finish;
    performance.mark('studio-preview-warm-start');

    function finish() {
      if (!active) return;
      active = false;
      stopWarming = undefined;
      window.clearTimeout(timeout);
      target.dispose();
      geometry.dispose();
      for (const node of group.children) if (node instanceof InstancedMesh) node.dispose();
      performance.mark('studio-preview-warm-end');
    }

    async function drawVariants() {
      await gl.compileAsync(group, camera, probe);
      for (const node of group.children) {
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        if (!active) return;
        const previous = gl.getRenderTarget();
        probe.children.push(node);
        try {
          gl.setRenderTarget(target);
          gl.render(probe, camera);
        } finally {
          probe.children.length = 0;
          gl.setRenderTarget(previous);
        }
      }
    }

    void drawVariants().then(finish, finish);
    gl.getContext().flush();
  }

  function prepareBuffers(gl: WebGLRenderer, scene: Scene, camera: Camera) {
    performance.mark('studio-preview-buffers-start');
    const frustum = new Frustum().setFromProjectionMatrix(
      new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse),
    );
    const geometries = new Set<BufferGeometry>();
    scene.updateMatrixWorld();
    scene.traverseVisible((node) => {
      if (!(node instanceof Mesh) || !node.layers.test(camera.layers)) return;
      const geometry = node.geometry;
      const position = geometry.getAttribute('position');
      if (
        position &&
        position.count * 32 >= previewBufferMinimum &&
        (!node.frustumCulled || frustum.intersectsObject(node))
      ) {
        geometries.add(geometry);
      }
    });
    const probe = new Scene();
    const target = new WebGLRenderTarget(1, 1);
    const source = new MeshBasicMaterial();
    const dummyGeometry = new BufferGeometry();
    const mesh = new Mesh(dummyGeometry, surface(source));
    source.dispose();
    mesh.frustumCulled = false;
    probe.add(mesh);
    disposeUpload = () => {
      disposeUpload = undefined;
      target.dispose();
      dummyGeometry.dispose();
    };
    return () => {
      const previous = gl.getRenderTarget();
      const deadline = performance.now() + previewUploadBudget;
      try {
        gl.setRenderTarget(target);
        for (const geometry of geometries) {
          geometries.delete(geometry);
          mesh.geometry = geometry;
          const { start, count } = geometry.drawRange;
          geometry.setDrawRange(0, 0);
          try {
            gl.render(probe, camera);
          } finally {
            geometry.setDrawRange(start, count);
          }
          if (performance.now() >= deadline) break;
        }
      } finally {
        gl.setRenderTarget(previous);
      }
      if (geometries.size) return false;
      disposeUpload?.();
      performance.mark('studio-preview-buffers-end');
      return true;
    };
  }

  return {
    windowSlats,
    preparing(gl: WebGLRenderer, scene: Scene, camera: Camera) {
      if (stopWarming) return true;
      if (buffersReady) return false;
      upload ??= prepareBuffers(gl, scene, camera);
      buffersReady = upload();
      if (buffersReady) upload = undefined;
      return !buffersReady;
    },
    warm(gl: WebGLRenderer) {
      if (warmed || !gl.extensions.has('KHR_parallel_shader_compile')) return;
      warmed = true;
      const group = new Group(),
        geometry = new PlaneGeometry();
      const source = new MeshBasicMaterial();
      group.add(
        new Mesh(geometry, surface(source)),
        new InstancedMesh(geometry, surface(source, true), 1),
      );
      source.dispose();
      if (warmPreview) {
        warmPreviewShaders(gl, geometry, group);
        return;
      }
      void gl
        .compileAsync(group, new PerspectiveCamera(), new Scene())
        .catch(() => {})
        .finally(() => {
          geometry.dispose();
          for (const node of group.children) if (node instanceof InstancedMesh) node.dispose();
        });
      gl.getContext().flush();
      if (warmOled) {
        const controller = new AbortController();
        oledWarmup = controller;
        performance.mark('studio-preview-oled-warm-start');
        void warmRoomEffect(gl, previewClockMaterial(), controller.signal).then((ready) => {
          if (oledWarmup === controller) oledWarmup = undefined;
          if (ready) performance.mark('studio-preview-oled-warm-end');
        });
      }
    },
    warmWaterfront(gl: WebGLRenderer, material: Material) {
      if (stopWaterfront || !gl.extensions.has('KHR_parallel_shader_compile')) return;
      const controller = new AbortController();
      stopWaterfront = () => controller.abort();
      performance.mark('studio-waterfront-warm-start');
      void warmRoomEffect(gl, material, controller.signal).then((ready) => {
        stopWaterfront = undefined;
        if (ready) performance.mark('studio-waterfront-warm-end');
      });
    },
    draw(gl: WebGLRenderer, scene: Scene, camera: Camera, atNight: boolean, look: RoomLook) {
      const shadows = gl.shadowMap.enabled;
      const environment = scene.environment;
      gl.shadowMap.enabled = false;
      scene.environment = null;
      night.value = +atNight;
      sunlight.value.set(0);
      if (look !== selectedLook) {
        selectedLook = look;
        const preset = look === 'neutral' ? null : roomCurves[look];
        saturation.value = preset?.saturation ?? 1;
        gradeCurve.value.forEach((v, i) =>
          preset ? v.set(preset.red[i], preset.green[i], preset.blue[i]) : v.setScalar(i / 8),
        );
      }
      try {
        scene.traverseVisible((object) => {
          if (object instanceof Light) {
            if (object instanceof SpotLight && object.intensity > 0.01) spots.push(object);
            if (!atNight && object instanceof DirectionalLight && object.intensity > 0) {
              object.getWorldPosition(sunDirection.value);
              sunDirection.value.sub(object.target.getWorldPosition(point)).normalize();
              sunlight.value.copy(object.color).multiplyScalar(object.intensity / Math.PI);
            }
            lights.push(object);
            object.visible = false;
          }
          if (!(object instanceof Mesh)) return;
          meshes.push(object);
          originals.push(object.material);
          const instanced = object instanceof InstancedMesh;
          object.material = Array.isArray(object.material)
            ? object.material.map((mat) => surface(mat, instanced))
            : surface(object.material, instanced);
        });
        if (spots.length > maxPreviewLights) {
          camera.getWorldPosition(eye);
          camera.getWorldDirection(forward);
          for (const spot of spots) {
            spot.target.getWorldPosition(direction).sub(eye);
            const distance = direction.length();
            const alignment = direction.dot(forward) / Math.max(distance, 0.01);
            relevance.set(
              spot,
              alignment + 0.04 * Math.log1p(spot.intensity / (1 + distance * distance)),
            );
          }
          spots.sort((a, b) => relevance.get(b)! - relevance.get(a)!);
        }
        lampCount.value = Math.min(maxPreviewLights, spots.length);
        for (let i = 0; i < lampCount.value; i++) {
          const spot = spots[i];
          spot.getWorldPosition(point);
          spot.target.getWorldPosition(direction).sub(point).normalize();
          const edge = Math.cos(spot.angle);
          const intensity = spot.intensity / Math.PI;
          lampPosition.value[i].set(
            point.x,
            point.y,
            point.z,
            spot.distance > 0 ? 1 / spot.distance ** 2 : 0,
          );
          lampAxis.value[i].set(direction.x, direction.y, direction.z, edge);
          lampPower.value[i].set(
            spot.color.r * intensity,
            spot.color.g * intensity,
            spot.color.b * intensity,
            Math.max(edge + 0.0001, Math.cos(spot.angle * (1 - spot.penumbra))),
          );
        }
        gl.render(scene, camera);
      } finally {
        for (let i = 0; i < meshes.length; i++) meshes[i].material = originals[i];
        for (const light of lights) light.visible = true;
        lights.length = 0;
        meshes.length = originals.length = spots.length = 0;
        gl.shadowMap.enabled = shadows;
        scene.environment = environment;
      }
    },
    dispose() {
      stopWarming?.();
      stopWaterfront?.();
      oledWarmup?.abort();
      oledWarmup = undefined;
      disposeUpload?.();
      upload = undefined;
      for (const cache of materials) {
        for (const material of cache.values()) material.dispose();
        cache.clear();
      }
      white.dispose();
    },
  };
}
