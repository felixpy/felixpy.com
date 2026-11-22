import * as T from 'three';
import { group } from './geometry';
import type { Palette } from './materials';
import { campKitchen } from './camp-kitchen';
import { loadDisplayModel } from './display-model';

export function outdoorRail(
  wall: T.Group,
  _palette: Palette,
  manager: T.LoadingManager,
  deferRoomDetail: (load: () => void) => void,
) {
  const zone = group(wall, 'Camp kitchen and boot bench', [-0.71, 0, 0]);
  const bag = group(
    zone,
    'Osprey Talon 26 · Phantom Grey and Dark Charcoal',
    [-0.363, 0.748, 0.215],
  );
  bag.rotation.y = 0.085;
  deferRoomDetail(() =>
    loadDisplayModel(zone, '/media/models/talon-field-kit.glb', manager, {
      mounted(scene) {
        const model = scene.children.find((part) => part.userData.fieldItem === bag.name);
        if (model) {
          model.position.set(0, -0.28, 0);
          model.quaternion.identity();
          bag.add(model);
        }
      },
    }),
  );
  const poles = ['left', 'right'].map((side) => group(zone, 'alpine-carbon-cork-' + side));
  deferRoomDetail(() =>
    loadDisplayModel(zone, '/media/models/camp-field-equipment.glb', manager, {
      mounted(scene) {
        scene.children
          .find((item) => item.userData.name === 'Equipment wall · hammer head saddle')
          ?.removeFromParent();
        for (const name of [
          'Field bench · welded steel basket',
          'Snow Peak BACOO 550 · 340 mm drawcord case',
        ]) {
          const equipment = scene.children.find((item) => item.userData.name === name);
          if (equipment) equipment.position.y += 0.0097;
        }
        for (const pole of poles) {
          const model = scene.children.find((part) => part.userData.fieldItem === pole.name);
          if (!model) continue;
          const halfLength = model.userData.packedLengthMm / 2000;
          pole.position.copy(model.position);
          pole.position.y += halfLength;
          pole.quaternion.copy(model.quaternion);
          model.position.set(0, -halfLength, 0);
          model.quaternion.identity();
          pole.add(model);
        }
      },
    }),
  );
  const bench = group(zone, 'Slatted entry bench', [0, 0, 0.224]);
  deferRoomDetail(() => loadDisplayModel(bench, '/media/models/entry-bench.glb', manager));
  return { zone, ...campKitchen(zone, manager, deferRoomDetail), bag, poles };
}
