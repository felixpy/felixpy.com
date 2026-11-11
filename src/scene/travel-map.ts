import * as T from 'three';
import { journeys } from '../content/travel';
import { box, group, paperGeometry, print, surface, tube } from './geometry';
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
  const frame = group(parent, 'World travel map', [0.844, 1.752, -0.535]);
  box(frame, [width + 0.026, height + 0.026, 0.027], [0, 0, 0], p.woodDark, 0.0028);
  box(frame, [width + 0.004, height + 0.004, 0.007], [0, 0, 0.012], p.linen, 0.0012);
  const paper = print(frame, width, height, [0, 0, 0.016], chart, paperGeometry(width, height));
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
      tube(pin, [0, 0, -0.004], [0, 0, 0.0019], 0.00037, p.steel);
      tube(pin, [0, 0, 0.001], [0, 0, 0.0027], 0.0009, enamel, 0.0014);
      tube(pin, [0, 0, 0.0027], [0, 0, 0.0035], 0.0014, enamel, 0.0012);
      return { place, pin };
    });
  return { frame, pins };
}
