import * as T from 'three';
import type { DeferRoomAsset } from './rear-loading';
import { loadDisplayModel } from './display-model';
import layout from './equipment-track-layout.json';
import { group } from './geometry';

export function equipmentTrack(zone: T.Group, manager: T.LoadingManager, defer: DeferRoomAsset) {
  const fixture = group(zone, 'ERCO Parscan 48V · Minirail');
  fixture.position.fromArray(layout.mount);
  const spots = layout.heads.map(({ x, aim, station, beamDegrees }) => {
    const light = new T.SpotLight(
      '#ffdfb6',
      0,
      3.5,
      T.MathUtils.degToRad(beamDegrees / 2),
      0.64,
      2,
    );
    light.name = 'ERCO Parscan 48V · ' + station;
    light.target.position.fromArray(aim).sub(fixture.position);
    light.position.set(x, -0.058, 0);
    const axis = light.target.position.clone().sub(light.position).normalize();
    light.position.addScaledVector(axis, 0.071);
    fixture.add(light, light.target);
    return light;
  });
  let powered = false;
  let lens: T.MeshStandardMaterial | undefined;
  defer(() =>
    loadDisplayModel(fixture, '/media/models/parscan-minirail.glb', manager, {
      mesh(part) {
        const material = part.material;
        if (
          material instanceof T.MeshStandardMaterial &&
          material.name === 'Parscan Spherolit lens'
        ) {
          lens = material;
          lens.emissiveIntensity = powered ? 1.65 : 0;
        }
      },
    }),
  );
  return {
    fixture,
    spots,
    setPower(on: boolean) {
      if (on === powered) return;
      powered = on;
      spots.forEach((spot, index) => (spot.intensity = on ? layout.heads[index].candela : 0));
      if (lens) lens.emissiveIntensity = on ? 1.65 : 0;
    },
  };
}
