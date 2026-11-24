import * as T from 'three';
import { loadDisplayModel } from './display-model';
import { group } from './geometry';
import { roomSize, workshopLayout } from './layout';

export function workbenchBoardLight(bench: T.Group, manager: T.LoadingManager) {
  const unit = group(bench, 'Astro Mondrian 600 Wall Mount · 1374042', [
    roomSize.east - workshopLayout.x,
    1.59,
    -0.012,
  ]);
  unit.rotation.y = -Math.PI / 2;
  const outlet = new T.Vector3(0, 0.0078, 0.166);
  const aim = new T.Vector3(0, -0.39, 0.031);
  const wash = new T.SpotLight('#ffd3a1', 0, 1.26, 0.99, 0.86, 2);
  wash.castShadow = true;
  wash.name = 'Mondrian tool board wash';
  wash.position.copy(outlet);
  wash.target.position.copy(aim);
  wash.shadow.mapSize.set(512, 512);
  wash.shadow.camera.near = 0.035;
  wash.shadow.camera.far = wash.distance;
  wash.shadow.bias = -0.00012;
  wash.shadow.normalBias = 0.0007;
  wash.shadow.intensity = 0;
  unit.add(wash, wash.target);
  let lens: T.MeshStandardMaterial | undefined;
  let power = false;

  function setPower(on: boolean, _highQuality: boolean, shadowAvailable = false) {
    power = on;
    wash.shadow.intensity = shadowAvailable ? 0.8 : 0;
    wash.intensity = on ? 1.8 : 0;
    if (lens) lens.emissiveIntensity = on ? 2.4 : 0;
  }
  const load = () =>
    loadDisplayModel(unit, '/media/models/astro-mondrian-600.glb', manager, {
      mesh(part) {
        const material = part.material;
        if (
          material instanceof T.MeshStandardMaterial &&
          material.name === 'Mondrian opal diffuser'
        ) {
          lens = material;
          lens.emissiveIntensity = power ? 2.4 : 0;
          part.castShadow = false;
        }
      },
    });
  return { unit, wash, load, setPower };
}
