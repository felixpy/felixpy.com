import type * as T from 'three';
import { loadDisplayModel } from './display-model';
import { group } from './geometry';
import { riserTop } from './hexcal-studio';

export function wirelessMicrophone(root: T.Object3D, manager: T.LoadingManager) {
  const mic = group(root, 'DJI Mic 2 · clip transmitter', [
    0.022,
    0.75 + riserTop + 0.02183 / 2,
    -0.115,
  ]);
  mic.rotation.set(-Math.PI / 2, 0, -0.16);
  loadDisplayModel(mic, '/media/models/dji-mic-2.glb', manager);
  return mic;
}
