import type * as T from 'three';
import { loadDisplayModel } from './display-model';

export const riserTop = 0.148;

export function hexcalStudio(shelf: T.Group, manager: T.LoadingManager) {
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  void loadDisplayModel(
    shelf,
    authoring ? '/media/models/hexcal-studio.glb' : '/media/models/hexcal-studio-room.glb',
    manager,
  );
}
