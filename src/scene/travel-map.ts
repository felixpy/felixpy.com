import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { journeys } from '../content/travel';
import { box, group, print, surface } from './geometry';
import { pictureFrame } from './picture-frame';
import type { Palette } from './materials';
import { atlasPoint, atlasPrint } from './atlas-projection.mjs';

export const atlasSize = { width: 0.693, height: (0.693 * atlasPrint.height) / atlasPrint.width };

function locateOnMap(lon: number, lat: number) {
  const [x, y] = atlasPoint(lon, lat);
  return [
    (x / atlasPrint.width - 0.5) * atlasSize.width,
    (0.5 - y / atlasPrint.height) * atlasSize.height,
  ] as const;
}

export function wallAtlas(parent: T.Group, p: Palette, chart: T.Texture) {
  const { width, height } = atlasSize;
  const frame = group(parent, 'World travel map', [0.844, 1.817, -0.535]);
  box(frame, [width + 0.028, height + 0.028, 0.018], [0, 0, 0], p.woodDark, 0.0008);
  pictureFrame(frame, width + 0.044, height + 0.044, 0.0085, 0.026, 0.024, p.wood);
  box(
    frame,
    [width + 0.027, height + 0.027, 0.006],
    [0, 0, 0.012],
    surface('#e1dccc', 0.95),
    0.0005,
  );
  const paper = print(frame, width, height, [0, 0, 0.0152], chart);
  paper.castShadow = false;
  const ink = paper.material as T.MeshStandardMaterial;
  ink.normalMap = p.paper.normalMap;
  ink.normalScale.set(0.45, 0.45);
  const enamel = surface('#9b4530', 0.52);
  const places = Object.values(journeys).flat();
  const shankGeometry = new T.CylinderGeometry(0.0005, 0.0005, 0.0076, 18);
  shankGeometry.rotateX(Math.PI / 2);
  shankGeometry.translate(0, 0, -0.0016);
  const headGeometry = new T.SphereGeometry(0.00225, 14, 10);
  headGeometry.translate(0, 0, 0.0024);
  const hitGeometry = mergeGeometries([shankGeometry, headGeometry], false) ?? headGeometry;
  const hitMaterial = new T.MeshBasicMaterial({ visible: false });
  const pinShanks = new T.InstancedMesh(shankGeometry, p.steel, places.length);
  const pinHeads = new T.InstancedMesh(headGeometry, enamel, places.length);
  pinShanks.name = 'Travel map pin shanks';
  pinHeads.name = 'Travel map pin heads';
  for (const batch of [pinShanks, pinHeads]) {
    batch.castShadow = batch.receiveShadow = true;
    batch.userData.exportInstalledInstances = true;
    batch.raycast = () => {};
    batch.matrixAutoUpdate = false;
    batch.updateMatrix();
  }
  const pins = places.map((place, index) => {
    const [x, y] = locateOnMap(place.lon, place.lat);
    const pin = group(frame, place.en, [x, y, 0.02]);
    pin.rotation.x = 0.16;
    pin.updateMatrix();
    pinShanks.setMatrixAt(index, pin.matrix);
    pinHeads.setMatrixAt(index, pin.matrix);
    const hit = new T.Mesh(hitGeometry, hitMaterial);
    hit.name = place.en + ' · hit';
    hit.castShadow = hit.receiveShadow = false;
    hit.matrixAutoUpdate = false;
    hit.updateMatrix();
    pin.add(hit);
    return { place, pin };
  });
  for (const batch of [pinShanks, pinHeads]) {
    batch.instanceMatrix.needsUpdate = true;
    batch.computeBoundingBox();
    batch.computeBoundingSphere();
  }
  frame.add(pinShanks, pinHeads);
  return { frame, pins, ink };
}
