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
  const enclosedNames = new Set([
    '288 selectively plated connector fingers',
    'Under-spreader thermal interface pads',
  ]);
  const lightGuideName = 'Continuous opaline light guide and pad printed XPG crown';
  loadDisplayModel(sockets[0], '/media/models/xpg-d50-fubuki.glb', manager, {
    mesh: registerLight,
    mounted(module) {
      module.updateMatrixWorld(true);
      const invModuleWorld = module.matrixWorld.clone().invert();
      const sourceMeshes: { mesh: T.Mesh; enclosed: boolean }[] = [];
      const enclosedMetaNames: string[] = [];
      let hasGuide = false;

      module.traverse((part) => {
        const partName = part.userData.name;
        if (typeof partName === 'string' && enclosedNames.has(partName)) {
          enclosedMetaNames.push(partName);
        }
        if (partName === lightGuideName) hasGuide = true;
        if (!(part instanceof T.Mesh)) return;
        let enclosed = false;
        for (let cur: T.Object3D | null = part; cur && cur !== module; cur = cur.parent) {
          if (typeof cur.userData.name === 'string' && enclosedNames.has(cur.userData.name)) {
            enclosed = true;
            break;
          }
        }
        sourceMeshes.push({ mesh: part, enclosed });
      });

      const localMatrix = new T.Matrix4();
      const slotMatrix = new T.Matrix4();
      const instanceMatrix = new T.Matrix4();
      for (const { mesh: part, enclosed } of sourceMeshes) {
        localMatrix.multiplyMatrices(invModuleWorld, part.matrixWorld);
        const instanced = new T.InstancedMesh(part.geometry, part.material, sockets.length);
        instanced.name = part.name;
        instanced.castShadow = part.castShadow;
        instanced.receiveShadow = part.receiveShadow;
        instanced.layers.mask = part.layers.mask;
        instanced.renderOrder = part.renderOrder;
        instanced.userData.exportInstalledInstances = true;
        for (let i = 0; i < sockets.length; i++) {
          slotMatrix.makeTranslation(
            sockets[i].position.x,
            sockets[i].position.y,
            sockets[i].position.z,
          );
          instanceMatrix.multiplyMatrices(slotMatrix, localMatrix);
          instanced.setMatrixAt(i, instanceMatrix);
        }
        instanced.instanceMatrix.needsUpdate = true;
        instanced.computeBoundingBox();
        instanced.computeBoundingSphere();
        instanced.matrixAutoUpdate = false;
        instanced.updateMatrix();
        if (enclosed) details.enclosed(instanced);
        bank.add(instanced);
      }

      module.removeFromParent();
      for (const slot of sockets) {
        for (const name of enclosedMetaNames) {
          const anchor = new T.Object3D();
          anchor.name = name;
          anchor.userData.name = name;
          anchor.matrixAutoUpdate = false;
          anchor.updateMatrix();
          details.enclosed(anchor);
          slot.add(anchor);
        }
        if (hasGuide) {
          const guide = new T.Object3D();
          guide.name = lightGuideName;
          guide.userData.name = lightGuideName;
          guide.matrixAutoUpdate = false;
          guide.updateMatrix();
          slot.add(guide);
        }
      }
      mounted?.(bank);
    },
  });
}
