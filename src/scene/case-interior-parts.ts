import * as T from 'three';
import { blenderMesh } from './blender-mesh';
import { coolingSleeveMaterial } from './case-component-lights';
import { canvasTexture, group, mesh, surface } from './geometry';
import type { Palette } from './materials';
const plug = 'atx-shell';
const tubes = 'aio-braid';
const ferrules = 'aio-fittings';
const seals = 'aio-seals';

export function fittedCable(parent: T.Object3D, key: string, material: T.Material, label = key) {
  const piece = mesh(parent, blenderMesh(key), material);
  piece.name = label;
  piece.userData.cablePart = key;
  return piece;
}

function sleeving() {
  const size = 32;
  const normal = canvasTexture(size, size, (ctx) => {
    const image = ctx.createImageData(size, size);
    function height(x: number, y: number) {
      const a = (Math.PI * (x + y)) / 8;
      const b = (Math.PI * (x - y)) / 8;
      const left = (1 + Math.cos(a)) * 0.5;
      const right = (1 + Math.cos(b)) * 0.5;
      const crossover = (1 + Math.cos(a / 2) * Math.cos(b / 2)) * 0.5;
      return left * (0.3 + 0.7 * crossover) + right * (1 - 0.7 * crossover);
    }
    const direction = new T.Vector3();
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        direction
          .set(height(x - 1, y) - height(x + 1, y), height(x, y + 1) - height(x, y - 1), 0.58)
          .normalize();
        const i = (y * size + x) * 4;
        image.data[i] = (direction.x + 1) * 127.5;
        image.data[i + 1] = (direction.y + 1) * 127.5;
        image.data[i + 2] = (direction.z + 1) * 127.5;
        image.data[i + 3] = 255;
      }
    }
    ctx.putImageData(image, 0, 0);
  });
  normal.colorSpace = T.NoColorSpace;
  normal.wrapS = normal.wrapT = T.RepeatWrapping;
  normal.repeat.set(8, 8);
  return normal;
}

export function pcPowerHarness(unit: T.Group, p: Palette) {
  const braid = sleeving();
  const ivory = surface('#c5c4c0', 0.75, 0.04);
  const carbon = surface('#53545a', 0.69, 0.05);
  for (const jacket of [ivory, carbon]) {
    jacket.normalMap = braid;
    jacket.normalScale.setScalar(0.3);
  }
  const comb = surface('#50545c', 0.37, 0.18);
  const loom = group(unit, '24-pin ATX braided loom and retaining comb');
  fittedCable(loom, 'atx-ivory', ivory);
  fittedCable(loom, 'atx-charcoal', carbon);
  fittedCable(loom, 'atx-comb', comb);
  fittedCable(unit, plug, p.graphite, 'Fully seated Mini-Fit Jr connector');
  const eps = group(unit, 'Twin 8-pin EPS12V processor supply');
  fittedCable(eps, 'eps-sleeves', carbon);
  fittedCable(eps, 'eps-plugs', p.graphite);
  return { braid, ivory, carbon, comb };
}

export function shortCoolingLines(
  unit: T.Group,
  p: Palette,
  braid: T.Texture,
  registerLight: (part: T.Mesh) => void,
) {
  const sleeve = coolingSleeveMaterial(braid);
  registerLight(
    fittedCable(unit, tubes, sleeve, 'Two 200 mm FEP lines with opal diffusing sleeves'),
  );
  fittedCable(unit, ferrules, p.steel, 'Pump and offset manifold compression ferrules');
  fittedCable(unit, seals, p.rubber, 'Fitting lands');
}
