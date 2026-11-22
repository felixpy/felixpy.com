import * as T from 'three';
import { random } from './geometry';
import type { Environment } from '../app/environment';
import { windowOpening } from './layout';
import { windowSunGLSL } from './window-sun';

export function airborneDust(
  parent: T.Object3D,
  sun: T.DirectionalLight,
  readingLight: T.SpotLight,
  slats: T.Vector2,
) {
  const count = 1152,
    positions = new Float32Array(count * 3),
    variations = new Float32Array(count * 3);
  const rng = random(30117);
  for (let i = 0; i < count; i++) {
    const local = i % 4 === 0;
    positions[i * 3] = local
      ? readingLight.position.x + (rng() - 0.5) * 0.72
      : -1.19 + rng() * 2.15;
    positions[i * 3 + 1] = local ? 0.775 + rng() * 0.48 : 0.43 + rng() * 1.77;
    positions[i * 3 + 2] = local
      ? readingLight.position.z + (rng() - 0.5) * 0.68
      : -0.42 + rng() * 1.95;
    variations.set([rng(), rng(), rng()], i * 3);
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.BufferAttribute(positions, 3));
  geometry.setAttribute('variation', new T.BufferAttribute(variations, 3));
  geometry.computeBoundingSphere();
  geometry.boundingSphere!.radius += 0.12;
  const uniforms = {
    elapsed: { value: 0 },
    daylight: { value: 0 },
    lamplight: { value: 0 },
    pixelRatio: { value: 1 },
    beam: { value: sun.target.position.clone().sub(sun.position).normalize() },
    lamp: { value: readingLight.position.clone() },
    slats: { value: slats },
  };
  const material = new T.ShaderMaterial({
    uniforms,
    transparent: true,
    depthTest: true,
    depthWrite: false,
    blending: T.AdditiveBlending,
    vertexShader: `
      attribute vec3 variation;
      uniform float elapsed,daylight,lamplight,pixelRatio;
      uniform vec3 beam,lamp;
      uniform vec2 slats;
      ${windowSunGLSL}
      varying vec3 radiance;
      varying float brightness;
      void main(){
        float a=variation.x*6.2831853;
        vec3 p=position + vec3(.048*sin(elapsed*.093+a)+.010*sin(elapsed*.23+a),
          .032*sin(elapsed*.14+variation.y*6.28),.038*cos(elapsed*.085+variation.z*6.28));
        float depth=p.x-(${windowOpening.wall - 0.154});
        float openWindow=transmittedSun(p,beam,slats);
        float forwardScatter=max(0.,dot(normalize(cameraPosition-p),beam));
        float sky=daylight*openWindow*exp(-.33*depth)*(.38+.62*forwardScatter*forwardScatter);
        vec3 toDust=p-lamp;
        float cone=smoothstep(.64,.91,-normalize(toDust).y);
        float task=lamplight*cone*(1.-smoothstep(.10,.56,length(toDust)))*smoothstep(.75,.80,p.y);
        radiance=sky*vec3(1.,.92,.77)+task*vec3(1.,.78,.54);
        brightness=(.14+.65*pow(variation.z,3.))*smoothstep(-.01,.05,depth);
        vec4 mv=modelViewMatrix*vec4(p,1.);
        gl_Position=projectionMatrix*mv;
        gl_PointSize=pixelRatio*clamp((.46+variation.y*.76)/max(.4,-mv.z),.84,2.40);
      }`,
    fragmentShader: `varying vec3 radiance; varying float brightness;
      void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p);
        if(r>=1.)discard;
        gl_FragColor=vec4(radiance,brightness*exp(-3.0*r)*(1.-r));
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const grains = new T.Points(geometry, material);
  grains.name = 'Dust in transmitted and task light';
  grains.renderOrder = 3;
  parent.add(grains);
  return (env: Environment, delta: number) => {
    if (!env.reducedMotion) uniforms.elapsed.value += delta;
    uniforms.daylight.value = env.night ? 0 : env.weather === '晴' ? 0.94 : 0.11;
    uniforms.lamplight.value = env.lamp ? (env.night ? 0.75 : 0.3) : 0;
    uniforms.pixelRatio.value = Math.min(window.devicePixelRatio || 1, 1.65);
    const lit = uniforms.daylight.value + uniforms.lamplight.value > 0.01;
    geometry.setDrawRange(0, lit ? (env.quality === 'high' ? count : 320) : 0);
  };
}
