import * as T from 'three';
import { loadDisplayModel } from './display-model';
import { group } from './geometry';

export const aerospaceTitle = { zh: '航空航天概论', en: 'Introduction to Aerospace' };

export function schoolNotebook(parent: T.Group, manager: T.LoadingManager) {
  const notebook = group(parent, aerospaceTitle.en, [-0.755, 0.761, 0.242]);
  notebook.rotation.set(-Math.PI / 2, 0, -0.16);
  void loadDisplayModel(notebook, '/media/models/stationery/aerospace-notebook.glb', manager, {
    mesh(part) {
      for (const material of Array.isArray(part.material) ? part.material : [part.material]) {
        if (!(material instanceof T.MeshStandardMaterial)) continue;
        if (material.map) material.map.anisotropy = 8;
        if (material.normalMap) material.normalMap.anisotropy = 8;
      }
    },
  });
  return notebook;
}
