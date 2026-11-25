import * as T from 'three';
import { loadDisplayModel } from './display-model';
import fixtures from './cabinet-light-layout.json';

export interface CabinetSpotBinding {
  centers: T.Vector3[];
  axes: T.Vector3[];
  optics: T.Vector3[];
  power: { value: number };
  matrixWorld: T.Matrix4;
  inverse: T.Matrix4;
  visibility: { value: T.Texture };
  visibilityReady: { value: number };
  receiverMode: number;
}

export function cabinetSpots(unit: T.Group, manager: T.LoadingManager) {
  const centers = fixtures.map(() => new T.Vector3());
  const axes = centers.map(() => new T.Vector3());
  const optics = fixtures.map(({ beam, peak }) => {
    const halfPowerAngle = T.MathUtils.degToRad(beam / 2);
    const edge = Math.cos(halfPowerAngle * 1.22);
    return new T.Vector3(edge, 2 * Math.cos(halfPowerAngle) - edge, peak);
  });
  const power = { value: 0.55 };
  const visibilityFallback = new T.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
  visibilityFallback.needsUpdate = true;
  const visibility = { value: visibilityFallback as T.Texture };
  const visibilityReady = { value: 0 };
  const inverse = new T.Matrix4();
  const finishes = new WeakMap<T.Material, Map<number, T.Material>>();
  let diffuser: T.MeshStandardMaterial | undefined;

  function illuminate(obj: T.Object3D) {
    if (!(obj instanceof T.Mesh)) return;
    const receiver = obj.userData.caseShadowReceiver as 'floor' | 'back' | undefined;
    const receiverMode = receiver === 'floor' ? 1 : receiver === 'back' ? 2 : 0;
    const applyFinish = (source: T.Material): T.Material => {
      if (!(source instanceof T.MeshStandardMaterial) || source.transparent) return source;
      if (source.userData.studioCabinetSpots) return source;
      let variants = finishes.get(source);
      if (!variants) {
        variants = new Map<number, T.Material>();
        finishes.set(source, variants);
      }
      const existing = variants.get(receiverMode);
      if (existing) return existing;
      const finish = source.clone();
      const binding: CabinetSpotBinding = {
        centers,
        axes,
        optics,
        power,
        matrixWorld: unit.matrixWorld,
        inverse,
        visibility,
        visibilityReady,
        receiverMode,
      };
      finish.userData = { ...source.userData, studioCabinetSpots: binding };
      variants.set(receiverMode, finish);
      return finish;
    };
    if (Array.isArray(obj.material)) obj.material = obj.material.map(applyFinish);
    else obj.material = applyFinish(obj.material);
  }

  function load() {
    unit.updateWorldMatrix(true, false);
    inverse.copy(unit.matrixWorld).invert();
    new T.TextureLoader(manager).load('/media/lighting/cabinet-spot-visibility.png', (loaded) => {
      visibilityFallback.dispose();
      visibility.value = loaded;
      visibilityReady.value = 1;
    });
    return loadDisplayModel(unit, '/media/models/c1-mini-lc.glb', manager, {
      mesh(part) {
        part.castShadow = false;
        if (
          part.material instanceof T.MeshStandardMaterial &&
          part.material.name.startsWith('C1-mini warm white collimator')
        )
          diffuser = part.material;
      },
      mounted(scene) {
        const rail = scene.getObjectByName('C1_magnetic_rail')!;
        const fixture = scene.getObjectByName('C1_magnetic_shoe')!;
        fixture.removeFromParent();
        rail.position.set(0, 1.285, 0.31);
        const lowerRail = rail.clone();
        lowerRail.position.y = 0.965;
        scene.add(lowerRail);
        for (const [index, { x, shelf, aim }] of fixtures.entries()) {
          const head = fixture.clone();
          head.position.set(x, shelf - 0.0073, 0.31);
          scene.add(head);
          const pan = head.getObjectByName('C1_pan')!;
          const tilt = head.getObjectByName('C1_tilt')!;
          const pupil = head.getObjectByName('C1_exit_pupil')!;
          const target = new T.Vector3().fromArray(aim);
          scene.updateWorldMatrix(true, true);
          const pivot = tilt.getWorldPosition(new T.Vector3()).applyMatrix4(inverse);
          const direction = target.clone().sub(pivot);
          const lateral = pupil.parent!.position.x;
          const yaw =
            Math.atan2(-direction.x, -direction.z) +
            Math.asin(lateral / Math.hypot(direction.x, direction.z));
          pan.rotation.y = yaw;
          direction.applyAxisAngle(new T.Vector3(0, 1, 0), -yaw);
          tilt.rotation.x = Math.atan2(-direction.z, -direction.y);
          scene.updateWorldMatrix(true, true);
          const origin = pupil.getWorldPosition(new T.Vector3()).applyMatrix4(inverse);
          const axis = target.clone().sub(origin).normalize();
          head.name = 'C1-mini-LC · ' + (index + 1);
          centers[index].copy(origin);
          axes[index].copy(axis);
        }
        if (diffuser) diffuser.emissiveIntensity = power.value * 3;
      },
    });
  }

  unit.traverse(illuminate);
  return {
    load,
    illuminate,
    centers: centers.slice(0, 3),
    axes: axes.slice(0, 3),
    power,
  };
}
