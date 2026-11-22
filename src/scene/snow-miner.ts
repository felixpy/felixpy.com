import type * as T from 'three';
import { loadDisplayModel } from './display-model';
import { group } from './geometry';

export function snowMiner(
  rack: T.Group,
  manager: T.LoadingManager,
  deferRoomDetail: (load: () => void) => void,
) {
  const pitch = 0.0254;
  const hook = group(rack, 'Snow Peak SnowMiner ES-020', [-3 * pitch, 1.572 + 21 * pitch, 0.052]);
  deferRoomDetail(() =>
    loadDisplayModel(hook, '/media/models/snowminer-es-020.glb', manager, {
      mounted(scene) {
        scene.traverse((part) => {
          if (part.userData.insideBatteryDoor) part.visible = false;
        });
      },
    }),
  );
}
