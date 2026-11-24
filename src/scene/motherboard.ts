import * as T from 'three';
import { loadDisplayModel } from './display-model';
import { group } from './geometry';
import slots from './dimm-slots.json';
import type { ProductDetail } from './product-detail';

export function installMotherboard(
  unit: T.Group,
  manager: T.LoadingManager,
  registerLight: (part: T.Mesh) => void,
  details: ProductDetail,
  mounted?: (scene: T.Group) => void,
) {
  const board = group(unit, 'ROG Strix Z890-A Gaming WiFi S · Fubuki', [0.077, 0.194, -0.289]);
  board.rotation.y = -Math.PI / 2;
  loadDisplayModel(board, '/media/models/strix-z890-a.glb', manager, {
    mesh: registerLight,
    mounted(model) {
      model.traverse((part) => {
        if (part.userData.model === 'Intel Core Ultra 9 285K' || part.userData.installedHidden) {
          details.enclosed(part);
        } else if (part.userData.inspectionDetail) {
          details.close(part);
        } else if (
          part.parent?.userData.name === 'LGA1851 retention mechanism' &&
          part instanceof T.Mesh &&
          (part.material.name === 'Hard gold flash' || part.material.name === 'Ferrite cores')
        ) {
          details.enclosed(part);
        }
      });
      mounted?.(model);
    },
  });
  const bank = group(unit, 'XPG D50 Fubuki DDR5 memory bank', [
    board.position.x - 0.0036,
    board.position.y - 0.081,
    board.position.z,
  ]);
  const sockets = slots.map(({ name, centerMm }) => {
    const slot = group(bank, 'XPG D50 Fubuki · DIMM ' + name, [0, 0, centerMm / 1000]);
    slot.userData.memorySocket = name;
    return slot;
  });
  loadDisplayModel(sockets[0], '/media/models/xpg-d50-fubuki.glb', manager, {
    mesh: registerLight,
    mounted(module) {
      module.traverse((part) => {
        if (
          part.userData.name === '288 selectively plated connector fingers' ||
          part.userData.name === 'Under-spreader thermal interface pads'
        )
          details.enclosed(part);
      });
      for (const slot of sockets.slice(1)) slot.add(module.clone());
      mounted?.(bank);
    },
  });
}
