import * as T from 'three';
import { mesh } from './geometry';

export function doorwayWormhole(parent: T.Object3D) {
  const time = { value: 0 };
  const energy = { value: 0 };
  const material = new T.ShaderMaterial({
    uniforms: { time, energy },
    side: T.DoubleSide,
    toneMapped: false,
    vertexShader: `
      varying vec2 coords;
      void main() {
        coords = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform float time, energy;
      varying vec2 coords;
      float hash(vec2 p) {
        return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
      }
      void main() {
        vec2 p = (coords - vec2(0.50, 0.54)) * vec2(1.36, 2.66);
        float r = length(p);
        float angle = atan(p.y, p.x);
        float phase = angle * 3.0 + log(max(r, 0.021)) * 12.0 - time * 2.0;
        float fold = pow(0.5 + 0.5 * cos(phase), 7.0);
        float ribs = pow(0.5 + 0.5 * cos(r * 77.0 + 2.0 * sin(phase * 2.0) - time * 7.0), 8.0);
        float ring = exp(-pow((r - 0.43) / 0.135, 2.0));
        float falloff = smoothstep(0.045, 0.19, r) * (1.0 - smoothstep(0.64, 1.11, r));
        float line = (0.09 + 0.34 * fold + 0.15 * ribs + 0.28 * fold * ribs) * falloff;
        vec3 violet = vec3(0.19, 0.19, 0.44);
        vec3 cyan = vec3(0.17, 0.70, 0.75);
        vec3 hue = mix(violet, cyan, 0.52 + 0.35 * sin(angle + time * 0.35));
        vec3 color = vec3(0.010, 0.017, 0.034) + energy * hue * (line + ring * (0.08 + 0.37 * fold));
        vec2 cells = coords * vec2(52.0, 94.0);
        float noise = hash(floor(cells));
        float star = (1.0 - smoothstep(0.025, 0.14, length(fract(cells) - 0.5))) * step(0.975, noise);
        color += star * (0.32 + noise * 0.29) * (0.4 + 0.6 * sin(noise * 73.0 + time) * sin(noise * 73.0 + time));
        float jamb = smoothstep(0.0, 0.11, min(coords.x, 1.0 - coords.x)) * smoothstep(0.0, 0.13, min(coords.y, 1.0 - coords.y));
        gl_FragColor = vec4(color * (0.14 + 0.86 * jamb), 1.0);
        #include <colorspace_fragment>
      }`,
  });
  const portal = mesh(parent, new T.PlaneGeometry(0.874, 2.124), material, [0, 0.01, 0.044]);
  portal.name = 'Wormhole beyond the doorway';
  portal.castShadow = portal.receiveShadow = false;
  const spill = new T.PointLight('#8ab6e9', 0, 1.4, 2);
  spill.position.set(0, 0.01, -0.13);
  parent.add(spill);
  return (opening: number, elapsed: number) => {
    portal.visible = opening > 0.003;
    time.value = elapsed;
    energy.value = T.MathUtils.smoothstep(opening, 0.015, 0.68);
    spill.intensity = energy.value * 0.4;
  };
}
