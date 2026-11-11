import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import { HalfFloatType, WebGLRenderTarget, type WebGLRenderer } from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

const filmStock = {
  uniforms: { tDiffuse: { value: null }, frame: { value: 0 } },
  vertexShader: `
    varying vec2 uvIn;
    void main() {
      uvIn = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float frame;
    varying vec2 uvIn;
    float noise(vec2 p) {
      vec3 v = fract(vec3(p.xyx) * 0.1031);
      v += dot(v, v.yzx + 33.33);
      return fract((v.x + v.y) * v.z);
    }
    void main() {
      vec4 base = texture2D(tDiffuse, uvIn);
      float luma = dot(base.rgb, vec3(0.2126, 0.7152, 0.0722));
      float response = smoothstep(0.018, 0.27, luma) * (1.0 - smoothstep(0.52, 0.93, luma));
      vec2 p = gl_FragCoord.xy + vec2(frame * 23.0, frame * 13.0);
      float stock = noise(p) * 0.62 + noise(floor(p * 0.52)) * 0.38 - 0.5;
      gl_FragColor = vec4(clamp(base.rgb + stock * response * 0.037, 0.0, 1.0), base.a);
    }`,
};

export function Finish({ enabled, reducedMotion }: { enabled: boolean; reducedMotion: boolean }) {
  const { gl, scene, camera, size, viewport } = useThree();
  const pipeline = useRef<{
    composer: EffectComposer;
    grain: ShaderPass;
    resize: () => void;
  } | null>(null);
  const dimensions = useRef({ size, dpr: viewport.dpr });
  dimensions.current = { size, dpr: viewport.dpr };

  useEffect(() => {
    const renderer = gl as WebGLRenderer;
    if (!enabled || !renderer.extensions.has('EXT_color_buffer_float')) return;
    const target = new WebGLRenderTarget(1, 1, {
      type: HalfFloatType,
      samples: Math.min(4, renderer.capabilities.maxSamples),
    });
    const composer = new EffectComposer(renderer, target);
    const color = new RenderPass(scene, camera);
    const occlusion = new GTAOPass(scene, camera);
    const output = new OutputPass();
    const grain = new ShaderPass(filmStock);
    occlusion.updateGtaoMaterial({ radius: 0.145, thickness: 0.08, scale: 1.1, samples: 12 });
    occlusion.updatePdMaterial({ radius: 4, rings: 2, samples: 10 });
    occlusion.blendIntensity = 0.66;
    composer.addPass(color);
    composer.addPass(occlusion);
    composer.addPass(output);
    composer.addPass(grain);
    let width = 0,
      height = 0,
      ratio = 0;
    const resize = () => {
      const current = dimensions.current;
      if (current.size.width === width && current.size.height === height && current.dpr === ratio)
        return;
      width = current.size.width;
      height = current.size.height;
      ratio = current.dpr;
      composer.setPixelRatio(ratio);
      composer.setSize(width, height);
      occlusion.setSize(Math.ceil((width * ratio) / 2), Math.ceil((height * ratio) / 2));
    };
    resize();
    pipeline.current = { composer, grain, resize };
    return () => {
      pipeline.current = null;
      occlusion.dispose();
      output.dispose();
      grain.dispose();
      composer.dispose();
    };
  }, [camera, enabled, gl, scene]);

  useFrame(({ clock }, delta) => {
    if (pipeline.current) {
      pipeline.current.resize();
      pipeline.current.grain.uniforms.frame.value = reducedMotion
        ? 0
        : Math.floor(clock.elapsedTime * 18) % 997;
      pipeline.current.composer.render(delta);
    } else gl.render(scene, camera);
  }, 1);
  return null;
}
