import * as T from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';

export function fixtureReflections(location: 'aj' | 'camp') {
  type Time = 'day' | 'night';
  const samples = new Map<Time, T.DataTexture>();
  const pending = new Set<Time>();
  const retryAfter = new Map<Time, number>();
  const finishes = new Set<T.MeshStandardMaterial>();
  const loader = new HDRLoader();
  let active: Time = 'day';
  let detailed = true;
  let released = false;

  function apply(material: T.MeshStandardMaterial, texture: T.Texture | null) {
    if (material.envMap === texture) return;
    material.envMap = texture;
    material.needsUpdate = true;
  }

  function loadVisible() {
    if (!detailed || released || samples.has(active) || pending.has(active)) return;
    if (performance.now() < (retryAfter.get(active) ?? 0)) return;
    const time = active;
    pending.add(time);
    loader.load(
      '/media/lighting/' + location + '-' + time + '.hdr',
      (texture) => {
        pending.delete(time);
        if (released) return texture.dispose();
        texture.mapping = T.EquirectangularReflectionMapping;
        samples.set(time, texture);
        if (time === active && detailed) for (const material of finishes) apply(material, texture);
      },
      undefined,
      () => {
        pending.delete(time);
        retryAfter.set(time, performance.now() + 3000);
      },
    );
  }

  return {
    bind(material: T.MeshStandardMaterial) {
      if (finishes.has(material) || released) return;
      finishes.add(material);
      material.onBeforeRender = loadVisible;
      if (detailed) apply(material, samples.get(active) ?? null);
      material.addEventListener('dispose', () => {
        finishes.delete(material);
        if (finishes.size) return;
        released = true;
        for (const texture of samples.values()) texture.dispose();
        samples.clear();
      });
    },
    select(night: boolean, high: boolean) {
      const time = night ? 'night' : 'day';
      if (time === active && high === detailed) return;
      active = time;
      detailed = high;
      const texture = detailed ? (samples.get(time) ?? null) : null;
      for (const material of finishes) apply(material, texture);
    },
  };
}
