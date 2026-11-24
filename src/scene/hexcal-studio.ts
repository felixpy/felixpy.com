import type * as T from 'three';
import { loadDisplayModel } from './display-model';

export const riserTop = 0.148;

export function hexcalStudio(shelf: T.Group, manager: T.LoadingManager) {
  void loadDisplayModel(shelf, '/media/models/hexcal-studio.glb', manager);
}
