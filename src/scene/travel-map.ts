import * as T from 'three';
import { journeys } from '../content/travel';
import { box, group, mesh, print, surface, tube } from './geometry';
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
  const pins = Object.values(journeys)
    .flat()
    .map((place) => {
      const [x, y] = locateOnMap(place.lon, place.lat);
      const pin = group(frame, place.en, [x, y, 0.02]);
      pin.rotation.x = 0.16;
      tube(pin, [0, 0, -0.0054], [0, 0, 0.0022], 0.0005, p.steel);
      mesh(pin, new T.SphereGeometry(0.00225, 14, 10), enamel, [0, 0, 0.0024]);
      return { place, pin };
    });
  return { frame, pins, ink };
}
