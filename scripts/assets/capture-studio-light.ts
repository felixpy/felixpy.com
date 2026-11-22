import * as T from 'three';
import { deskProbe } from '../../src/scene/room-reflection';

export function captureStudioLight(
  renderer: T.WebGLRenderer,
  scene: T.Scene,
  location: 'desk' | 'aj' | 'camp' = 'desk',
) {
  const width = location === 'desk' ? 512 : 384,
    height = width / 2;
  const probe = new T.WebGLCubeRenderTarget(256, {
    type: T.HalfFloatType,
    minFilter: T.LinearFilter,
    magFilter: T.LinearFilter,
    colorSpace: T.LinearSRGBColorSpace,
  });
  const camera = new T.CubeCamera(0.02, 3000, probe);
  const exclusions: T.Mesh[] = [];
  if (location === 'aj') {
    const lamp = scene.getObjectByName('Louis Poulsen AJ Floor · polished stainless steel');
    if (!lamp) throw new Error('Missing AJ Floor reflection origin');
    lamp.updateWorldMatrix(true, true);
    camera.position.set(0.052, 1.159, 0).applyMatrix4(lamp.matrixWorld);
    lamp.traverse((part) => {
      if (part instanceof T.Mesh && part.visible) {
        exclusions.push(part);
        part.visible = false;
      }
    });
  } else if (location === 'camp') {
    const rack = scene.getObjectByName('Camp kitchen and boot bench');
    if (!rack) throw new Error('Missing camping wall reflection origin');
    rack.localToWorld(camera.position.set(0.012, 1.42, 0.24));
  } else camera.position.set(deskProbe.x, deskProbe.y, deskProbe.z);
  const generator = new T.PMREMGenerator(renderer);
  const projection = new T.Scene();
  const geometry = new T.PlaneGeometry(2, 2);
  const material = new T.ShaderMaterial({
    uniforms: { radiance: { value: probe.texture } },
    vertexShader:
      'varying vec2 coords; void main() { coords = uv; gl_Position = vec4(position.xy, 0., 1.); }',
    fragmentShader: `
      varying vec2 coords;
      uniform samplerCube radiance;
      void main() {
        float longitude = (coords.x - 0.5) * 6.28318530718;
        float latitude = (coords.y - 0.5) * 3.14159265359;
        vec3 direction = vec3(cos(latitude) * cos(longitude), sin(latitude), cos(latitude) * sin(longitude));
        vec3 light = max(textureCube(radiance, direction).rgb, vec3(0.0));
        float peak = max(light.r, max(light.g, light.b));
        if (peak < 1.e-30) {
          gl_FragColor = vec4(0.0);
        } else {
          float exponent = floor(log2(peak)) + 1.0;
          gl_FragColor = vec4(floor(light * exp2(8.0 - exponent)), exponent + 128.0) / 255.0;
        }
      }`,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
  });
  projection.add(new T.Mesh(geometry, material));
  const output = new T.WebGLRenderTarget(width, height, { depthBuffer: false });
  const originalTarget = renderer.getRenderTarget();
  const environment = scene.environment;
  const intensity = scene.environmentIntensity;
  let bounce: T.WebGLCubeRenderTarget | undefined;
  try {
    scene.environment = null;
    renderer.shadowMap.needsUpdate = true;
    camera.update(renderer, scene);
    bounce = generator.fromCubemap(probe.texture);
    scene.environment = bounce.texture;
    scene.environmentIntensity = 0.65;
    camera.update(renderer, scene);
    renderer.setRenderTarget(output);
    renderer.render(projection, new T.OrthographicCamera(-1, 1, 1, -1, 0, 1));
    const pixels = new Uint8Array(width * height * 4);
    renderer.readRenderTargetPixels(output, 0, 0, width, height, pixels);
    const chunks: string[] = [];
    for (let i = 0; i < pixels.length; i += 8192)
      chunks.push(String.fromCharCode(...pixels.subarray(i, i + 8192)));
    return { width, height, rgbe: btoa(chunks.join('')) };
  } finally {
    for (const part of exclusions) part.visible = true;
    renderer.setRenderTarget(originalTarget);
    scene.environment = environment;
    scene.environmentIntensity = intensity;
    geometry.dispose();
    material.dispose();
    generator.dispose();
    bounce?.dispose();
    output.dispose();
    probe.dispose();
  }
}
