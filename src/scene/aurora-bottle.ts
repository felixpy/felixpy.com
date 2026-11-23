import * as T from 'three';
import { deferredDisplayModel } from './display-model';

const seat = 0.205;

export function auroraBottle(manager: T.LoadingManager, bindMetal: (mesh: T.Mesh) => void) {
  const pivot = new T.Group();
  pivot.name = 'Aurora bottle cap seat';
  const bodyInside = new T.Group();
  const capInside = new T.Group();
  bodyInside.visible = capInside.visible = false;
  let fitted = false;
  let ready = false;
  let selected = false;
  let reduceMotion = false;
  let started: number | undefined;

  function position(fraction: number) {
    const twist = T.MathUtils.smoothstep(fraction, 0, 0.49);
    const lift = T.MathUtils.smoothstep(fraction, 0.49, 0.66);
    const slide = T.MathUtils.smoothstep(fraction, 0.66, 0.84);
    const turn = T.MathUtils.smoothstep(fraction, 0.84, 1);
    pivot.position.set(0.085 * slide, seat + 0.00938 * twist + 0.032 * lift - 0.063 * turn, 0);
    pivot.rotation.set(-2.0 * turn, 2.72 * 2 * Math.PI * twist, 0);
    bodyInside.visible = capInside.visible = fraction > 0;
  }

  function start() {
    if (!selected || !fitted || !ready) return;
    if (reduceMotion) position(1);
    else started = performance.now();
  }

  const load = deferredDisplayModel(bodyInside, '/media/models/aurora-bottle-interior.glb', {
    mesh: bindMetal,
    mounted(scene) {
      for (const part of [...scene.children]) {
        (part.userData.auroraFitting === 'vessel' ? bodyInside : capInside).add(part);
      }
      scene.removeFromParent();
      ready = true;
      start();
    },
  });

  return {
    mount(model: T.Object3D) {
      const cap = model.children.find((part) => part.userData.auroraFitting === 'cap');
      if (!cap) return;
      model.add(pivot, bodyInside);
      pivot.add(cap, capInside);
      cap.position.y = capInside.position.y = -seat;
      fitted = true;
      position(0);
      start();
    },
    select(inspecting: boolean, reducedMotion: boolean) {
      selected = inspecting;
      reduceMotion = reducedMotion;
      started = undefined;
      if (!inspecting) position(0);
      else if (ready) start();
      else void load(manager).catch(() => {});
    },
    update() {
      if (started === undefined) return;
      const fraction = Math.min(1, (performance.now() - started) / 1450);
      position(fraction);
      if (fraction === 1) started = undefined;
    },
  };
}
