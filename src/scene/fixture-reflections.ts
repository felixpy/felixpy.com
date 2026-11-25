import * as T from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { defaultStudioLoadingManager } from './asset-loading';
import { packedBuffer } from './packed-buffer';
import { decodePmrem } from './pmrem-decode';

export function fixtureReflections(location: 'aj' | 'camp') {
  type Time = 'day' | 'night';
  const samples = new Map<Time, T.Texture>();
  const pending = new Map<Time, Promise<void>>();
  const retryAfter = new Map<Time, number>();
  const finishes = new Set<T.MeshStandardMaterial>();
  const loader = new HDRLoader(defaultStudioLoadingManager);
  let active: Time = 'day';
  let detailed = true;
  let released = false;

  function apply(material: T.MeshStandardMaterial, texture: T.Texture | null) {
    if (material.envMap === texture) return;
    material.envMap = texture;
    material.needsUpdate = true;
  }

  function commit(time: Time, texture: T.Texture) {
    if (released) {
      texture.dispose();
      return;
    }
    samples.set(time, texture);
    if (time === active && detailed) {
      for (const material of finishes) apply(material, texture);
    }
  }

  function loadHdrFallback(time: Time): Promise<void> {
    return new Promise<void>((resolve) => {
      loader.load(
        '/media/lighting/' + location + '-' + time + '.hdr',
        (texture) => {
          texture.mapping = T.EquirectangularReflectionMapping;
          commit(time, texture);
          resolve();
        },
        undefined,
        () => {
          retryAfter.set(time, performance.now() + 3000);
          resolve();
        },
      );
    });
  }

  function loadVisible(): Promise<void> {
    if (!detailed || released || samples.has(active)) return Promise.resolve();
    const existing = pending.get(active);
    if (existing) return existing;
    if (performance.now() < (retryAfter.get(active) ?? 0)) return Promise.resolve();
    const time = active;
    const pmremPath = '/media/lighting/' + location + '-' + time + '.pmrem.gz';
    const url = defaultStudioLoadingManager.resolveURL(pmremPath);
    const loading = fetch(url)
      .then((response) => packedBuffer(response))
      .then((buffer) => {
        commit(time, decodePmrem(buffer));
      })
      .catch(() => {
        if (released) return;
        return loadHdrFallback(time);
      })
      .finally(() => {
        pending.delete(time);
      });
    pending.set(time, loading);
    return loading;
  }

  return {
    bind(material: T.MeshStandardMaterial) {
      if (finishes.has(material) || released) return;
      finishes.add(material);
      material.onBeforeRender = () => {
        void loadVisible();
      };
      if (detailed) apply(material, samples.get(active) ?? null);
      material.addEventListener('dispose', () => {
        finishes.delete(material);
        if (finishes.size) return;
        released = true;
        for (const texture of samples.values()) texture.dispose();
        samples.clear();
      });
    },
    preload() {
      return loadVisible();
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
