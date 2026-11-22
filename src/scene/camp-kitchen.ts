import * as T from 'three';
import { auroraBottle } from './aurora-bottle';
import { group } from './geometry';
import { loadDisplayModel } from './display-model';
import { equipmentTrack } from './equipment-track';
import { fixtureReflections } from './fixture-reflections';
import { snowMiner } from './snow-miner';

export function campKitchen(
  zone: T.Group,
  manager: T.LoadingManager,
  deferRoomDetail: (load: () => void) => void,
) {
  deferRoomDetail(() => loadDisplayModel(zone, '/media/models/camp-rack.glb', manager));
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
    carrier.position.copy(model.position);
    carrier.position.y += halfHeight;
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
  deferRoomDetail(() =>
    loadDisplayModel(zone, '/media/models/camp-cookware.glb', manager, {
      mesh: bindMetal,
      mounted(scene) {
        for (const part of [...scene.children]) {
          if (part.userData.product === 'PR-880') mountShelfItem(part, coffee, 0.095);
          if (part.userData.trekAssembly === 'pot') mountShelfItem(part, cookset, 0.07);
        }
      },
    }),
  );
  const closure = auroraBottle(manager, bindMetal);
  deferRoomDetail(() =>
    loadDisplayModel(zone, '/media/models/snow-peak-pitch-kit.glb', manager, {
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
    }),
  );
  const charger = group(zone, 'Snow Peak HOME & CAMP charging stand', [-0.32, 1.075, 0.178]);
  charger.rotation.y = 0.155;
  const lamp = group(zone, 'Snow Peak HOME & CAMP Lantern · Ivory', [-0.32, 1.22, 0.178]);
  lamp.rotation.y = charger.rotation.y;
  const lampOrigin = group(lamp, 'Product origin', [0, -0.145, 0]);
  let cover: T.Object3D | undefined;
  let closedZ = 0;
  let held = false;
  let openedAt = 0;
  let moving = false;
  const coveredParts: T.Object3D[] = [];
  function positionCover(fraction: number) {
    if (!cover) return;
    cover.position.z =
      closedZ - cover.userData.releaseMm * 0.001 * T.MathUtils.smoothstep(fraction, 0, 0.25);
    cover.rotation.z =
      T.MathUtils.degToRad(cover.userData.swingDegrees) * T.MathUtils.smoothstep(fraction, 0.25, 1);
    for (const part of coveredParts) part.visible = fraction > 0;
  }
  const mounts = new Map([
    ['450', cupOrigin],
    ['lantern', lampOrigin],
    ['lantern-dock', charger],
  ]);
  deferRoomDetail(() =>
    loadDisplayModel(zone, '/media/models/snow-peak-lantern-mugs.glb', manager, {
      mesh: bindMetal,
      mounted(scene) {
        for (const model of [...scene.children]) {
          mounts.get(model.userData.campProduct)?.add(model);
          if (model.userData.campProduct === 'lantern') {
            model.traverse((part) => {
              if (part.userData.es080Joint === 'port-cover') {
                cover = part;
                closedZ = part.position.z;
              }
              if (part.userData.es080Inside) coveredParts.push(part);
            });
            positionCover(held && !moving ? 1 : 0);
          }
        }
        scene.removeFromParent();
      },
    }),
  );
  return {
    cup,
    lamp,
    selectLanternPort(inspecting: boolean, reducedMotion: boolean) {
      held = inspecting;
      moving = inspecting && !reducedMotion;
      openedAt = performance.now();
      positionCover(inspecting && reducedMotion ? 1 : 0);
    },
    updateLanternPort() {
      if (!moving || !cover) return;
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
  };
}
