import * as T from 'three';
import { loadDisplayModel } from './display-model';
import { group, mesh, type XYZ } from './geometry';

export function remote(parent: T.Object3D, manager: T.LoadingManager, position: XYZ) {
  const cradle = group(parent, 'Walnut window remote cradle', position);
  void loadDisplayModel(cradle, '/media/models/window-cradle.glb', manager);
  const unit = group(parent, 'Window remote', [
    position[0] - 0.005,
    position[1] + 0.073,
    position[2],
  ]);
  unit.quaternion.setFromRotationMatrix(
    new T.Matrix4().makeBasis(
      new T.Vector3(0, 0, -1),
      new T.Vector3(1, 0, 0),
      new T.Vector3(0, -1, 0),
    ),
  );
  unit.rotateOnWorldAxis(new T.Vector3(0, 0, 1), 0.14);
  const symbols = ['blinds', 'angle', 'city', 'weather', 'shuffle', 'time'];
  const buttons = symbols.map((symbol, i) =>
    group(unit, symbol, [((i % 2) - 0.5) * 0.025, 0.0081, -0.024 + Math.floor(i / 2) * 0.026]),
  );
  void loadDisplayModel(unit, '/media/models/window-controller.glb', manager, {
    mounted(scene) {
      for (const button of buttons) {
        const cap = scene.getObjectByName('Button_' + button.name);
        if (!cap) throw new Error('Missing remote button ' + button.name);
        cap.position.set(0, 0, 0);
        button.add(cap);
      }
    },
  });
  return { unit, buttons };
}

export { philodendron as pottedPlant } from './philodendron';

export function deskObjects(parent: T.Object3D, manager: T.LoadingManager) {
  const cluster = group(parent, 'Desk keepsakes');
  const cup = group(cluster, 'Glazed stoneware cup', [0.684, 0.752, 0.263]);
  const vapor = new T.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { seconds: { value: 0 } },
    vertexShader: `
      varying vec2 coords;
      void main() {
        coords = uv;
        vec4 center = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        gl_Position = projectionMatrix * (center + vec4(position.xy, 0.0, 0.0));
      }`,
    fragmentShader: `
      uniform float seconds;
      varying vec2 coords;
      void main() {
        float y = coords.y;
        float t = seconds * 0.70;
        float x = (coords.x - 0.5) * 2.0;
        float center = y * (0.11 + sin(y * 7.0 - t * 1.5) * 0.22);
        float thickness = mix(0.13, 0.37, y);
        float nearWisp = (x - center) / thickness;
        float farWisp = (x - center - 0.11 - sin(y * 11.0 - t) * y * 0.34) / thickness;
        float ribbons = exp(-nearWisp * nearWisp * 2.0);
        ribbons *= 0.57 + 0.24 * sin(26.0 * y - t * 7.0 + x * 4.0);
        ribbons += 0.29 * exp(-farWisp * farWisp * 2.8);
        float fade = smoothstep(0.03, 0.19, y) * (1.0 - smoothstep(0.36, 1.0, y));
        gl_FragColor = vec4(0.84, 0.78, 0.67, ribbons * fade * 0.085);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
      `,
  });
  const steam = mesh(cup, new T.PlaneGeometry(0.13, 0.195), vapor, [0, 0.169, 0]);
  steam.name = 'Tea vapor';
  steam.castShadow = steam.receiveShadow = false;
  steam.raycast = () => {};
  steam.visible = false;
  void loadDisplayModel(cup, '/media/models/kinto-clk-151.glb', manager, {
    mounted: () => {
      steam.visible = true;
    },
  });
  return (seconds: number) => {
    vapor.uniforms.seconds.value = seconds;
  };
}
