import * as T from 'three';
import { assetUrl } from '../app/asset-url';
import type { DeferRoomAsset } from './rear-loading';
import { group } from './geometry';
import type { Palette } from './materials';
import { campKitchen } from './camp-kitchen';
import { loadDisplayModel } from './display-model';

export function outdoorRail(
  wall: T.Group,
  _palette: Palette,
  manager: T.LoadingManager,
  deferRoomDetail: DeferRoomAsset,
) {
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  const zone = group(wall, 'Camp kitchen and boot bench', [-0.71, 0, 0]);
  const bag = group(
    zone,
    'Osprey Talon 26 · Phantom Grey and Dark Charcoal',
    [-0.363, 0.748, 0.215],
  );
  bag.rotation.y = 0.085;
  let bagRoomNode: T.Object3D | undefined;
  let bagHeroNode: T.Object3D | undefined;
  let bagHeroPending = false;
  let inspectingBag = false;
  const syncBag = () => {
    const showHero = Boolean(bagHeroNode && inspectingBag);
    if (bagHeroNode) bagHeroNode.visible = showHero;
    if (bagRoomNode) bagRoomNode.visible = !showHero;
  };
  function loadBagHero() {
    if (authoring || bagHeroNode || bagHeroPending) return;
    bagHeroPending = true;
    const holder = new T.Group();
    void loadDisplayModel(
      holder,
      '/media/models/talon-field-kit.glb',
      new T.LoadingManager().setURLModifier(assetUrl),
      {
        mounted(scene) {
          const model = scene.children.find((part) => part.userData.fieldItem === bag.name);
          if (model) {
            model.position.set(0, -0.28, 0);
            model.quaternion.identity();
            bag.add(model);
            bagHeroNode = model;
            syncBag();
          }
        },
      },
    ).catch(() => {
      bagHeroPending = false;
    });
  }
  deferRoomDetail(() =>
    loadDisplayModel(
      zone,
      authoring ? '/media/models/talon-field-kit.glb' : '/media/models/talon-field-kit-room.glb',
      manager,
      {
        mounted(scene) {
          const model = scene.children.find((part) => part.userData.fieldItem === bag.name);
          if (model) {
            model.position.set(0, -0.28, 0);
            model.quaternion.identity();
            bag.add(model);
            if (!authoring) {
              bagRoomNode = model;
              syncBag();
            }
          }
        },
      },
    ),
  );
  const poles = ['left', 'right'].map((side) => group(zone, 'alpine-carbon-cork-' + side));
  const poleRoomNodes = new Map<T.Group, T.Object3D>();
  const poleHeroNodes = new Map<T.Group, T.Object3D>();
  let polesHeroPending = false;
  let activePoleIndex = -1;
  const syncPoles = () => {
    poles.forEach((pole, idx) => {
      const hero = poleHeroNodes.get(pole);
      const room = poleRoomNodes.get(pole);
      const showHero = Boolean(hero && activePoleIndex === idx);
      if (hero) hero.visible = showHero;
      if (room) room.visible = !showHero;
    });
  };
  function loadPolesHero() {
    if (authoring || poleHeroNodes.size > 0 || polesHeroPending) return;
    polesHeroPending = true;
    const holder = new T.Group();
    void loadDisplayModel(
      holder,
      '/media/models/camp-field-equipment.glb',
      new T.LoadingManager().setURLModifier(assetUrl),
      {
        mounted(scene) {
          for (const pole of poles) {
            const model = scene.children.find((part) => part.userData.fieldItem === pole.name);
            if (!model) continue;
            const halfLength = model.userData.packedLengthMm / 2000;
            model.position.set(0, -halfLength, 0);
            model.quaternion.identity();
            pole.add(model);
            poleHeroNodes.set(pole, model);
          }
          syncPoles();
        },
      },
    ).catch(() => {
      polesHeroPending = false;
    });
  }
  deferRoomDetail(() =>
    loadDisplayModel(
      zone,
      authoring
        ? '/media/models/camp-field-equipment.glb'
        : '/media/models/camp-field-equipment-room.glb',
      manager,
      {
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
            if (!authoring) poleRoomNodes.set(pole, model);
          }
          syncPoles();
        },
      },
    ),
  );
  const bench = group(zone, 'Slatted entry bench', [0, 0, 0.224]);
  deferRoomDetail(() =>
    loadDisplayModel(
      bench,
      authoring ? '/media/models/entry-bench.glb' : '/media/models/entry-bench-room.glb',
      manager,
    ),
  );
  const kitchen = campKitchen(zone, manager, deferRoomDetail);
  return {
    zone,
    ...kitchen,
    bag,
    poles,
    selectBagDetail(active: boolean) {
      inspectingBag = active;
      if (active) loadBagHero();
      syncBag();
    },
    selectPoleDetail(index: number, active: boolean) {
      activePoleIndex = active ? index : -1;
      if (active) loadPolesHero();
      syncPoles();
    },
    preloadOutdoorHero(id: string) {
      if (id === 'talon-pack') loadBagHero();
      else if (id.startsWith('alpine-carbon-cork-')) loadPolesHero();
      else kitchen.preloadKitchenHero(id);
    },
  };
}
