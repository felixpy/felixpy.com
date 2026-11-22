import type * as T from 'three';
const steel = 'workshop-steel';
const ferric = 'workshop-black';
const birch = 'workshop-birch';
const grips = 'workshop-grips';
const collars = 'workshop-collars';
const etching = 'workshop-etch';
import { blenderMesh } from './blender-mesh';
import { mesh, surface } from './geometry';
import type { Palette } from './materials';

export function fitPrecisionTools(root: T.Group, p: Palette) {
  const caliper = surface('#979993', 0.59, 0.8);
  caliper.normalMap = p.steel.normalMap;
  caliper.normalScale.set(0.14, 0.14);
  const beam = blenderMesh('workshop-caliper-beam');
  const position = beam.getAttribute('position');
  const uv = beam.getAttribute('uv');
  for (let i = 0; i < uv.count; i++)
    uv.setXY(i, position.getZ(i) * 7, (position.getY(i) + position.getX(i)) * 24);
  mesh(root, beam, caliper).name = 'Mitutoyo 530-104 · satin scale and carriage';
  for (const [name, source, finish] of [
    ['Workshop · peg hooks and steel fittings', steel, surface('#c3c5c0', 0.32, 0.84)],
    [
      'Mitutoyo 530-104 · ground measuring jaws',
      'workshop-caliper-jaws',
      surface('#a1a69f', 0.42, 0.84),
    ],
    ['Tempered tips and ESD tweezer leaves', ferric, surface('#373c3c', 0.43, 0.55)],
    ['Bit holder', birch, p.wood],
    ['Wera PH, PZ and TORX insert bits', 'workshop-bit-steel', surface('#a8aca7', 0.35, 0.83)],
    ['Wera shank markings', 'workshop-bit-mark', surface('#33372f', 0.63, 0.2)],
    ['Bit holder socket ferrules', 'workshop-bit-ferrules', surface('#424642', 0.46, 0.73)],
    ['Parts bin walls', grips, surface('#3c534d', 0.63)],
    ['Slotted driver size code', collars, surface('#efbe1b', 0.49)],
    ['Kraftform rigid handle cores', 'workshop-wera-body', surface('#252a2b', 0.33)],
    ['Kraftform soft grip inlays', 'workshop-wera-grip', surface('#329f80', 0.7)],
    ['Phillips driver size code', 'workshop-wera-ph', surface('#c5272b', 0.53)],
    ['Wera pad printing', 'workshop-wera-print', surface('#dddcd1', 0.58)],
    ['Engraved vernier graduations', etching, surface('#262925', 0.79)],
  ] as const)
    mesh(root, blenderMesh(source), finish).name = name;
}
