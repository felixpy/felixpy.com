import * as T from 'three';
import { defaultStudioLoadingManager } from './asset-loading';
import { random } from './geometry';

const lanes = 18;

export const paneOptics = `
  uniform sampler2D rainBeads;
  uniform vec4 rainHeads[${lanes}], rainTracks[${lanes}];
  uniform vec2 glassSize;

  float channelX(float y, vec4 track) {
    return track.x + 0.0018 * sin(y * 54. + track.y) + 0.00085 * sin(y * 112. - track.y);
  }

  vec3 wetSurface(vec2 uv) {
    vec3 pinned = texture2D(rainBeads, uv).rgb;
    vec3 surface = vec3(pinned.rg * 2. - 1., pinned.b);
    if (surface.z < 0.004) surface = vec3(0.);
    int lane = int(clamp(floor(uv.x * ${lanes}.), 0., ${lanes - 1}.));
    vec4 head = rainHeads[lane], track = rainTracks[lane];
    if (track.w <= 0.) return surface;
    float dx = (uv.x - channelX(uv.y, track)) * glassSize.x;
    float above = (uv.y - head.y) * glassSize.y;
    float halfWidth = head.z;
    float cleared = (1. - smoothstep(0.6, 1.4, abs(dx) / halfWidth))
      * smoothstep(0., halfWidth, above) * (1. - smoothstep(track.z, track.z + 0.015, uv.y)) * track.w;
    surface *= 1. - cleared;
    float film = cleared * exp(-max(above, 0.) * 5.5);
    surface.x += 0.14 * dx / halfWidth * exp(-1.8 * dx * dx / (halfWidth * halfWidth)) * film;
    surface.z = max(surface.z, 0.24 * film);
    vec2 local = vec2((uv.x - head.x) * glassSize.x / halfWidth, above / (halfWidth * 1.44));
    local.x *= 1. + 0.17 * clamp(local.y, -1., 1.);
    float radius2 = dot(local, local);
    float edge = max(0.10, fwidth(radius2));
    float cap = (1. - smoothstep(1. - edge, 1. + edge, radius2)) * head.w;
    surface.xy = mix(surface.xy, local * vec2(0.95, 0.74), cap);
    surface.z = max(surface.z, cap);
    return surface;
  }`;

export function rainUniforms() {
  return {
    rainAmount: { value: 0 },
    rainBeads: { value: null as T.Texture | null },
    rainHeads: { value: Array.from({ length: lanes }, () => new T.Vector4()) },
    rainTracks: { value: Array.from({ length: lanes }, () => new T.Vector4()) },
  };
}

export function buildRainGlass(origin: T.Vector3, size: T.Vector2) {
  const rng = random(240);
  function newDrop(lane: number) {
    return {
      time: 0,
      rest: 1.1 + rng() * 2.6,
      duration: 2.4 + rng() * 3,
      travel: 0.14 + rng() * 0.51,
      start: 0.25 + rng() * 0.76,
      x: (lane + 0.2 + 0.6 * rng()) / lanes,
      seed: rng() * Math.PI * 2,
      radius: 0.0019 + rng() * 0.0026,
    };
  }
  const drops = Array.from({ length: lanes }, (_, lane) => {
    const drop = newDrop(lane);
    drop.time = rng() * (drop.duration + drop.rest);
    return drop;
  });
  const uniforms = {
    ...rainUniforms(),
    glassOrigin: { value: origin },
    glassSize: { value: size },
  };
  const highlights = new T.Mesh(
    new T.PlaneGeometry(size.x, size.y),
    new T.ShaderMaterial({
      uniforms,
      transparent: true,
      depthWrite: false,
      toneMapped: false,
      vertexShader: `
        varying vec2 pane;
        varying vec3 glassPoint;
        void main() {
          pane = uv;
          glassPoint = (modelMatrix * vec4(position, 1.)).xyz;
          gl_Position = projectionMatrix * viewMatrix * vec4(glassPoint, 1.);
        }`,
      fragmentShader: `
        ${paneOptics}
        uniform float rainAmount;
        varying vec2 pane;
        varying vec3 glassPoint;
        void main() {
          vec3 wet = wetSurface(pane);
          if (wet.z < 0.015) discard;
          vec3 eye = normalize(cameraPosition - glassPoint);
          vec3 normal = normalize(vec3(1., -wet.y, wet.x));
          float fresnel = 0.0204 + 0.9796 * pow(1. - abs(dot(eye, normal)), 5.);
          vec3 reflected = reflect(-eye, normal);
          float sky = smoothstep(-0.25, 0.73, reflected.y);
          vec3 light = mix(vec3(0.012,0.018,0.025), vec3(0.61,0.69,0.77), sky);
          gl_FragColor = vec4(light, rainAmount * wet.z * min(0.39, fresnel + 0.09 * sky));
          #include <colorspace_fragment>
        }`,
    }),
  );
  highlights.name = 'Outside glazing surface';
  highlights.position.set(origin.x, origin.y + size.y / 2, origin.z - size.x / 2);
  highlights.rotation.y = Math.PI / 2;
  highlights.renderOrder = 3;
  highlights.visible = false;
  let prepared = false;
  return {
    uniforms,
    highlights,
    update(blend: number, delta: number) {
      uniforms.rainAmount.value = blend;
      highlights.visible = blend > 0.012;
      if (!highlights.visible || (prepared && delta <= 0)) return;
      if (!prepared) {
        prepared = true;
        const texture = new T.TextureLoader(defaultStudioLoadingManager).load(
          '/media/panoramas/glass-rain-beads.png',
        );
        texture.anisotropy = 4;
        uniforms.rainBeads.value = texture;
        highlights.material.addEventListener('dispose', () => texture.dispose());
      }
      for (let i = 0; i < lanes; i++) {
        let drop = drops[i];
        drop.time += delta;
        if (drop.time > drop.rest + drop.duration + 2) drop = drops[i] = newDrop(i);
        const phase = T.MathUtils.clamp((drop.time - drop.rest) / drop.duration, 0, 1);
        const distance = phase * phase * (1.08 - 0.08 * Math.cos(phase * 13));
        const y = drop.start - drop.travel * distance;
        const x =
          drop.x + 0.0018 * Math.sin(y * 54 + drop.seed) + 0.00085 * Math.sin(y * 112 - drop.seed);
        const fade = 1 - T.MathUtils.smoothstep(drop.time - drop.rest - drop.duration, 0, 2);
        const born = T.MathUtils.smoothstep(drop.time, 0, drop.rest);
        uniforms.rainHeads.value[i].set(x, y, drop.radius * (0.78 + phase * 0.22), born * fade);
        uniforms.rainTracks.value[i].set(drop.x, drop.seed, drop.start, fade);
      }
    },
  };
}
