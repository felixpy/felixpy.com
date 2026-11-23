import {
  FramebufferTexture,
  RawShaderMaterial,
  Vector2,
  Vector3,
  type Texture,
  type WebGLRenderer,
} from 'three';
import { FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { OutputShader } from 'three/addons/shaders/OutputShader.js';
import type { RoomLook } from '../app/environment';
import { roomCurves } from './room-looks';

const shader = `
uniform vec3 roomCurve[9];
uniform float roomSaturation;
vec3 gradeRoom(vec3 rgb) {
  vec3 position = clamp(rgb, 0.0, 1.0) * 8.0;
  vec3 color = roomCurve[0];
  for (int i = 0; i < 8; i++) {
    color += (roomCurve[i + 1] - roomCurve[i]) * clamp(position - float(i), 0.0, 1.0);
  }
  return mix(vec3(dot(color, vec3(0.213, 0.715, 0.072))), color, roomSaturation);
}`;

export function roomColorGrade() {
  const curve = Array.from({ length: 9 }, (_, i) => new Vector3().setScalar(i / 8));
  const uniforms = { roomCurve: { value: curve }, roomSaturation: { value: 1 } };
  const size = new Vector2();
  let current: RoomLook = 'neutral';
  let frame: FramebufferTexture | undefined;
  let quad: FullScreenQuad | undefined;
  let material: RawShaderMaterial | undefined;

  function select(look: RoomLook) {
    if (current === look) return;
    current = look;
    const preset = look === 'neutral' ? null : roomCurves[look];
    for (const [i, point] of curve.entries()) {
      if (preset) point.set(preset.red[i], preset.green[i], preset.blue[i]);
      else point.setScalar(i / 8);
    }
    uniforms.roomSaturation.value = preset?.saturation ?? 1;
  }

  function outputPass(occlusion?: { map: Texture; intensity: number }) {
    const output = new OutputPass();
    let source = output.material.fragmentShader.replace('void main()', 'void outputRoom()');
    if (occlusion) {
      source = source
        .replace(
          'uniform sampler2D tDiffuse;',
          'uniform sampler2D tDiffuse;\nuniform sampler2D roomOcclusion;\nuniform float roomOcclusionIntensity;',
        )
        .replace(
          'gl_FragColor = texture2D( tDiffuse, vUv );',
          `vec4 ao = texture2D(roomOcclusion, vUv);
          gl_FragColor = texture2D(tDiffuse, vUv) * vec4(mix(vec3(1.), ao.rgb, roomOcclusionIntensity), ao.a);`,
        );
      Object.assign(output.uniforms, {
        roomOcclusion: { value: occlusion.map },
        roomOcclusionIntensity: { value: occlusion.intensity },
      });
    }
    output.material.fragmentShader =
      source +
      shader +
      `
void main() {
  outputRoom();
  gl_FragColor.rgb = gradeRoom(gl_FragColor.rgb);
}`;
    Object.assign(output.uniforms, uniforms);
    output.renderToScreen = true;
    return output;
  }

  function gradeScreen(renderer: WebGLRenderer) {
    if (current === 'neutral') return;
    renderer.getDrawingBufferSize(size);
    if (!frame || frame.image.width !== size.x || frame.image.height !== size.y) {
      frame?.dispose();
      frame = new FramebufferTexture(size.x, size.y);
    }
    if (!quad || !material) {
      material = new RawShaderMaterial({
        uniforms: { ...uniforms, tDiffuse: { value: frame } },
        vertexShader: OutputShader.vertexShader,
        fragmentShader: `precision highp float;
          uniform sampler2D tDiffuse;
          varying vec2 vUv;
          ${shader}
          void main() {
            vec4 color = texture2D(tDiffuse, vUv);
            gl_FragColor = vec4(gradeRoom(color.rgb), color.a);
          }`,
        depthTest: false,
        depthWrite: false,
        toneMapped: false,
      });
      quad = new FullScreenQuad(material);
    }
    material.uniforms.tDiffuse.value = frame;
    renderer.copyFramebufferToTexture(frame);
    quad.render(renderer);
  }

  function dispose() {
    frame?.dispose();
    material?.dispose();
    quad?.dispose();
    frame = quad = material = undefined;
  }

  return { select, outputPass, gradeScreen, dispose };
}
