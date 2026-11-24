import * as T from 'three';
import { assetUrl } from '../app/asset-url';
import type { DeferRoomAsset } from './rear-loading';
import { auroraBottle } from './aurora-bottle';
import { group } from './geometry';
import { loadDisplayModel } from './display-model';
import { equipmentTrack } from './equipment-track';
import { fixtureReflections } from './fixture-reflections';
import { snowMiner } from './snow-miner';

export function campKitchen(
  zone: T.Group,
  manager: T.LoadingManager,
  deferRoomDetail: DeferRoomAsset,
) {
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  deferRoomDetail(() =>
    loadDisplayModel(
      zone,
      authoring ? '/media/models/camp-rack.glb' : '/media/models/camp-rack-room.glb',
      manager,
    ),
  );
  snowMiner(zone, manager, deferRoomDetail);
  const track = equipmentTrack(zone, manager, deferRoomDetail);
  const cup = group(zone, 'Snow Peak Ti-Double 450');
  const pivot = new T.Vector3(0.011, 0.0469, 0);
  const contact = new T.Vector3(0.0813, 0.07145, 0.0088);
  cup.rotation.set(0.16, 0.32, 1.12, 'YXZ');
  cup.position.set(-0.4064, 1.9534, 0.122).sub(contact.sub(pivot).applyQuaternion(cup.quaternion));
  const cupOrigin = group(cup, 'Product origin', [-pivot.x, -pivot.y, 0]);
  const bottle = group(zone, 'Snow Peak Aurora Bottle 800 Rainbow');
  const cookset = group(zone, 'Snow Peak Titanium Trek 900');
  const coffee = group(zone, 'Snow Peak Field Coffee Master');
  function mountShelfItem(model: T.Object3D, carrier: T.Group, halfHeight: number) {
    if (carrier.children.length === 0) {
      carrier.position.copy(model.position);
      carrier.position.y += halfHeight;
    }
    model.position.set(0, -halfHeight, 0);
    carrier.add(model);
  }
  const reflections = fixtureReflections('camp');
  function bindMetal(part: T.Mesh) {
    const material = part.material;
    if (!(material instanceof T.MeshStandardMaterial)) return;
    const sightGlass = material.name === 'Clear pressed glass · percolator sight';
    if (sightGlass) {
      material.side = T.FrontSide;
      material.depthWrite = false;
    }
    if (sightGlass || material.metalness > 0.65) reflections.bind(material);
  }
  const cookwareRoom = new Map<string, T.Object3D>();
  const cookwareHero = new Map<string, T.Object3D>();
  let cookwareHeroPending = false;
  let activeCookware: 'coffee' | 'cookset' | undefined;
  const syncCookware = () => {
    for (const key of ['coffee', 'cookset'] as const) {
      const hero = cookwareHero.get(key);
      const room = cookwareRoom.get(key);
      const showHero = Boolean(hero && activeCookware === key);
      if (hero) hero.visible = showHero;
      if (room) room.visible = !showHero;
    }
  };
  function loadCookwareHero() {
    if (authoring || cookwareHero.size > 0 || cookwareHeroPending) return;
    cookwareHeroPending = true;
    const holder = new T.Group();
    void loadDisplayModel(
      holder,
      '/media/models/camp-cookware.glb',
      new T.LoadingManager().setURLModifier(assetUrl),
      {
        mesh: bindMetal,
        mounted(scene) {
          for (const part of [...scene.children]) {
            if (part.userData.product === 'PR-880') {
              mountShelfItem(part, coffee, 0.095);
              cookwareHero.set('coffee', part);
            }
            if (part.userData.trekAssembly === 'pot') {
              mountShelfItem(part, cookset, 0.07);
              cookwareHero.set('cookset', part);
            }
          }
          syncCookware();
        },
      },
    ).catch(() => {
      cookwareHeroPending = false;
    });
  }
  deferRoomDetail(() =>
    loadDisplayModel(
      zone,
      authoring ? '/media/models/camp-cookware.glb' : '/media/models/camp-cookware-room.glb',
      manager,
      {
        mesh: bindMetal,
        mounted(scene) {
          for (const part of [...scene.children]) {
            if (part.userData.product === 'PR-880') {
              mountShelfItem(part, coffee, 0.095);
              if (!authoring) cookwareRoom.set('coffee', part);
            }
            if (part.userData.trekAssembly === 'pot') {
              mountShelfItem(part, cookset, 0.07);
              if (!authoring) cookwareRoom.set('cookset', part);
            }
          }
          syncCookware();
        },
      },
    ),
  );
  const closure = auroraBottle(manager, bindMetal);
  deferRoomDetail(() =>
    loadDisplayModel(
      zone,
      authoring
        ? '/media/models/snow-peak-pitch-kit.glb'
        : '/media/models/snow-peak-pitch-kit-room.glb',
      manager,
      {
        mesh: bindMetal,
        mounted(scene) {
          for (const part of [...scene.children]) {
            if (part.userData.product === 'snow-peak-tw800-ra') {
              mountShelfItem(part, bottle, 0.115);
              closure.mount(part);
            }
            if (
              ['Guyline · double-prong rack hanger', 'TAKIBI M · pegs and lower pads'].includes(
                part.userData.name,
              )
            )
              part.removeFromParent();
          }
        },
      },
    ),
  );
  const charger = group(zone, 'Snow Peak HOME & CAMP charging stand', [-0.32, 1.075, 0.178]);
  charger.rotation.y = 0.155;
  const lamp = group(zone, 'Snow Peak HOME & CAMP Lantern · Ivory', [-0.32, 1.22, 0.178]);
  lamp.rotation.y = charger.rotation.y;
  const lampOrigin = group(lamp, 'Product origin', [0, -0.145, 0]);
  const covers: { node: T.Object3D; closedZ: number }[] = [];
  let held = false;
  let openedAt = 0;
  let moving = false;
  const coveredParts: T.Object3D[] = [];
  function positionCover(fraction: number) {
    for (const entry of covers) {
      entry.node.position.z =
        entry.closedZ -
        entry.node.userData.releaseMm * 0.001 * T.MathUtils.smoothstep(fraction, 0, 0.25);
      entry.node.rotation.z =
        T.MathUtils.degToRad(entry.node.userData.swingDegrees) *
        T.MathUtils.smoothstep(fraction, 0.25, 1);
    }
    for (const part of coveredParts) part.visible = fraction > 0;
  }
  const mounts = new Map([
    ['450', cupOrigin],
    ['lantern', lampOrigin],
    ['lantern-dock', charger],
  ]);
  const mugRoom = new Map<string, T.Object3D>();
  const mugHero = new Map<string, T.Object3D>();
  let mugHeroPending = false;
  let activeMug: '450' | 'lantern' | undefined;
  const syncMugs = () => {
    for (const key of ['450', 'lantern'] as const) {
      const hero = mugHero.get(key);
      const room = mugRoom.get(key);
      const showHero = Boolean(hero && activeMug === key);
      if (hero) hero.visible = showHero;
      if (room) room.visible = !showHero;
    }
  };
  function registerLanternJoints(model: T.Object3D) {
    model.traverse((part) => {
      if (part.userData.es080Joint === 'port-cover') {
        covers.push({ node: part, closedZ: part.position.z });
      }
      if (part.userData.es080Inside) coveredParts.push(part);
    });
    positionCover(held && !moving ? 1 : 0);
  }
  function loadMugsHero() {
    if (authoring || mugHero.size > 0 || mugHeroPending) return;
    mugHeroPending = true;
    const holder = new T.Group();
    void loadDisplayModel(
      holder,
      '/media/models/snow-peak-lantern-mugs.glb',
      new T.LoadingManager().setURLModifier(assetUrl),
      {
        mesh: bindMetal,
        mounted(scene) {
          for (const model of [...scene.children]) {
            const product = model.userData.campProduct as string | undefined;
            if (product !== '450' && product !== 'lantern') continue;
            mounts.get(product)?.add(model);
            mugHero.set(product, model);
            if (product === 'lantern') registerLanternJoints(model);
          }
          syncMugs();
        },
      },
    ).catch(() => {
      mugHeroPending = false;
    });
  }
  deferRoomDetail(() =>
    loadDisplayModel(
      zone,
      authoring
        ? '/media/models/snow-peak-lantern-mugs.glb'
        : '/media/models/snow-peak-lantern-mugs-room.glb',
      manager,
      {
        mesh: bindMetal,
        mounted(scene) {
          for (const model of [...scene.children]) {
            const product = model.userData.campProduct as string | undefined;
            if (product) {
              mounts.get(product)?.add(model);
              if (!authoring && (product === '450' || product === 'lantern')) {
                mugRoom.set(product, model);
              }
            }
            if (product === 'lantern') registerLanternJoints(model);
          }
          scene.removeFromParent();
          syncMugs();
        },
      },
    ),
  );
  return {
    cup,
    lamp,
    selectCupDetail(active: boolean) {
      activeMug = active ? '450' : activeMug === '450' ? undefined : activeMug;
      if (active) loadMugsHero();
      syncMugs();
    },
    selectLanternPort(inspecting: boolean, reducedMotion: boolean) {
      held = inspecting;
      moving = inspecting && !reducedMotion;
      openedAt = performance.now();
      positionCover(inspecting && reducedMotion ? 1 : 0);
      activeMug = inspecting ? 'lantern' : activeMug === 'lantern' ? undefined : activeMug;
      if (inspecting) loadMugsHero();
      syncMugs();
    },
    selectCookwareDetail(kind: 'coffee' | 'cookset', active: boolean) {
      activeCookware = active ? kind : activeCookware === kind ? undefined : activeCookware;
      if (active) loadCookwareHero();
      syncCookware();
    },
    preloadKitchenHero(id: string) {
      if (id === 'trek-cookset' || id === 'field-coffee-master') loadCookwareHero();
      else if (id === 'titanium-cup' || id === 'camp-lantern') loadMugsHero();
    },
    updateLanternPort() {
      if (!moving || !covers.length) return;
      const fraction = Math.min((performance.now() - openedAt) / 620, 1);
      positionCover(fraction);
      moving = fraction < 1;
    },
    bottle,
    bottleClosure: closure,
    cookset,
    coffee,
    track,
    selectLighting(night: boolean, high: boolean, enabled: boolean) {
      reflections.select(night, high);
      track.setPower(enabled);
    },
    preloadReflections: reflections.preload,
  };
}
