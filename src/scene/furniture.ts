import * as T from 'three';
import { books } from '../content/profile';
import {
  beam,
  box,
  cable,
  canvasTexture,
  group,
  mesh,
  print,
  random,
  surface,
  textTexture,
  tube,
} from './geometry';
import { plasterUV, type Palette } from './materials';
import type { XYZ } from './geometry';
import { lamp, pottedPlant } from './props';
import { shelfAwards } from './awards';
import { doorwayWormhole } from './wormhole';

export const roomSize = { west: -1.26, east: 2.52, north: -0.56, south: 3.19, ceiling: 2.71 };
export const windowOpening = {
  wall: roomSize.west,
  z0: -0.22,
  z1: 1.39,
  y0: 0.947,
  y1: 2.3,
  thickness: 0.25,
};
export const desk = {
  left: roomSize.west,
  right: 1.22,
  back: roomSize.north,
  front: 0.43,
  top: 0.75,
};
export const workshopLayout = { x: 2.207, z: 0.69, length: 1.42 };
const bookcase = { x: 1.55, z: -0.374, width: 0.61, height: 2.41, side: 0.034, depth: 0.354 };

export function architecture(root: T.Group, p: Palette) {
  const { west, east, north, south, ceiling } = roomSize;
  const x = (west + east) / 2,
    z = (north + south) / 2;
  function plaster(size: XYZ, center: XYZ, material = p.wall) {
    const part = box(root, size, center, material);
    part.geometry = part.geometry.clone();
    plasterUV(part.geometry, part.position);
  }
  plaster([east - west, ceiling, 0.18], [x, ceiling / 2, north - 0.09]);
  const originalRight = 1.27,
    railHeight = 0.62;
  const muralPanel = new T.PlaneGeometry(east - west, ceiling - railHeight);
  const muralUV = muralPanel.attributes.uv;
  for (let i = 0; i < muralUV.count; i++)
    muralUV.setX(i, (muralUV.getX(i) * (east - west)) / (originalRight - west));
  const mural = mesh(root, muralPanel, p.mural, [x, (ceiling + railHeight) / 2, north + 0.0006]);
  mural.name = 'Flight atlas · lithograph wallpaper';
  mural.castShadow = false;
  const doorCenter = 1.83,
    doorLeft = doorCenter - 0.421,
    doorRight = doorCenter + 0.421,
    doorHeight = 2.135;
  for (const [left, right] of [
    [west, doorLeft],
    [doorRight, east],
  ]) {
    plaster([right - left, ceiling, 0.19], [(left + right) / 2, ceiling / 2, south + 0.095]);
    box(
      root,
      [right - left, 0.068, 0.026],
      [(left + right) / 2, 0.035, south - 0.01],
      p.woodDark,
      0.003,
    );
  }
  plaster(
    [doorRight - doorLeft, ceiling - doorHeight, 0.19],
    [doorCenter, (ceiling + doorHeight) / 2, south + 0.095],
  );
  plaster([0.17, ceiling, south - north], [east + 0.085, ceiling / 2, z]);
  const ceilingPaint = p.wall.clone();
  ceilingPaint.color.set('#f0ece4');
  ceilingPaint.normalScale.set(0.46, 0.46);
  plaster([east - west + 0.32, 0.18, south - north + 0.32], [x, ceiling + 0.09, z], ceilingPaint);
  box(root, [east - west, 0.14, south - north], [x, -0.07, z], p.woodDark);
  const floorGeometry = new T.PlaneGeometry(east - west, south - north);
  const uv = floorGeometry.attributes.uv;
  const scanSpan = 2;
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(
      i,
      ((1 - uv.getY(i)) * (south - north)) / scanSpan,
      (uv.getX(i) * (east - west)) / scanSpan + 0.035,
    );
  }
  const boards = mesh(root, floorGeometry, p.floor, [x, 0.0045, z]);
  boards.name = 'Worn pine · longitudinal floorboards';
  boards.rotation.x = -Math.PI / 2;
  boards.castShadow = false;
  const endGrain = new T.MeshBasicMaterial({
    color: '#3e2b1c',
    transparent: true,
    opacity: 0.36,
    depthWrite: false,
  });
  const boardWidth = scanSpan / 13;
  for (let column = 0; west + (column + 0.5) * boardWidth < east; column++) {
    const center = west + (column + 0.5) * boardWidth;
    const stagger = 0.44 + ((column * 0.47) % 1.25);
    for (let seamZ = north + stagger; seamZ < south - 0.15; seamZ += 1.7) {
      const seam = mesh(root, new T.PlaneGeometry(boardWidth - 0.003, 0.0015), endGrain, [
        center,
        0.0048,
        seamZ,
      ]);
      seam.rotation.x = -Math.PI / 2;
      seam.castShadow = seam.receiveShadow = false;
    }
  }
  box(root, [east - west, 0.068, 0.029], [x, 0.035, north + 0.013], p.woodDark, 0.003);
  const paneling = p.woodVertical.clone();
  paneling.color.set('#e3ddda');
  for (let i = 0; i < 12; i++) {
    const width = (east - west) / 12;
    box(
      root,
      [width - 0.003, 0.56, 0.023],
      [west + (i + 0.5) * width, 0.33, north + 0.012],
      paneling,
      0.0012,
    );
  }
  box(root, [east - west, 0.041, 0.037], [x, 0.618, north + 0.016], p.woodDark, 0.004);
  box(root, [0.028, 0.068, south - north], [east - 0.013, 0.035, z], p.woodDark, 0.003);
  box(root, [0.028, 0.068, south - north], [west + 0.013, 0.035, z], p.woodDark, 0.003);
  const frame = group(root, 'Door · back right', [doorCenter, 1.055, south - 0.031]);
  const hinge = group(frame, 'Door hinge toward the workbench', [0.409, 0, 0]);
  const door = group(hinge, 'Hinged walnut door', [-0.409, 0, 0]);
  const updatePortal = doorwayWormhole(frame);
  const stile = p.woodVertical.clone();
  const rail = p.wood.clone();
  const panel = p.woodVertical.clone();
  for (const finish of [stile, rail, panel]) {
    finish.color.set('#c6b4a0');
    finish.roughness = 1;
    finish.normalScale.set(0.77, 0.77);
  }
  panel.color.set('#b39e88');
  const rebate = p.woodVertical.clone();
  rebate.color.set('#a59485');
  rebate.roughness = 0.94;
  box(door, [0.835, 2.123, 0.024], [0, 0.012, 0.004], rebate, 0.002);
  for (const side of [-1, 1]) {
    box(frame, [0.052, 2.114, 0.07], [side * 0.438, 0.012, -0.002], p.woodVertical, 0.0024);
    box(frame, [0.012, 2.107, 0.034], [side * 0.415, 0.01, -0.014], p.woodVertical, 0.0011);
    box(door, [0.118, 2.076, 0.034], [side * 0.344, 0, -0.006], stile, 0.0021);
  }
  box(frame, [0.928, 0.048, 0.071], [0, 1.094, -0.002], p.wood, 0.0024);
  box(frame, [0.826, 0.009, 0.045], [0, -1.048, 0.006], p.woodDark, 0.001);
  for (const [y, height] of [
    [-0.979, 0.118],
    [-0.158, 0.163],
    [0.982, 0.112],
  ]) {
    box(door, [0.57, height, 0.034], [0, y, -0.006], rail, 0.0018);
  }
  for (const [y, height] of [
    [0.383, 1.083],
    [-0.566, 0.696],
  ]) {
    box(door, [0.569, height, 0.01], [0, y, -0.007], panel, 0.0011);
    box(door, [0.557, height - 0.018, 0.004], [0, y, 0.018], panel, 0.002);
    for (const side of [-1, 1]) {
      box(door, [0.026, height, 0.018], [side * 0.272, y, -0.014], stile, 0.004);
      box(door, [0.518, 0.026, 0.018], [0, y + side * (height / 2 - 0.013), -0.014], rail, 0.004);
      box(door, [0.026, height, 0.007], [side * 0.272, y, 0.019], stile, 0.003);
      box(door, [0.518, 0.026, 0.007], [0, y + side * (height / 2 - 0.013), 0.019], rail, 0.003);
    }
  }
  const handle = group(door, 'Brushed brass lever and rosette', [-0.348, -0.092, -0.024]);
  tube(handle, [0, 0, 0], [0, 0, -0.006], 0.026, p.bronze);
  tube(handle, [0, 0, -0.006], [0, 0, -0.052], 0.01, p.bronze);
  cable(
    handle,
    [
      [0, 0, -0.049],
      [0.014, 0.002, -0.056],
      [0.052, 0.002, -0.058],
      [0.098, -0.002, -0.057],
    ],
    0.008,
    p.bronze,
  );
  for (const y of [-0.016, 0.016]) tube(handle, [0, y, -0.006], [0, y, -0.007], 0.0022, p.steel);
  for (const y of [-0.74, 0.016, 0.74]) {
    box(door, [0.039, 0.063, 0.003], [0.395, y, -0.023], p.bronze, 0.001);
    tube(frame, [0.409, y - 0.042, -0.028], [0.409, y + 0.042, -0.028], 0.0055, p.bronze);
  }
  let opening = 0,
    target = 0;
  return {
    door: frame,
    toggle() {
      target = 1 - target;
      return Boolean(target);
    },
    update(delta: number, elapsed: number, reduced: boolean) {
      const previous = opening;
      opening = reduced ? target : T.MathUtils.lerp(opening, target, 1 - Math.exp(-delta * 5.2));
      if (Math.abs(opening - target) < 0.001) opening = target;
      hinge.rotation.y = -Math.PI * 0.53 * T.MathUtils.smoothstep(opening, 0, 1);
      updatePortal(opening, reduced ? 0 : elapsed);
      return opening !== previous;
    },
  };
}

export function trainingCorner(root: T.Group, p: Palette) {
  const area = group(root, 'Training equipment · rear wall');
  const steel = surface('#343738', 0.57, 0.4);
  const weights = [
    { kg: 4, color: '#247477', size: 0.082 },
    { kg: 6, color: '#764652', size: 0.094 },
    { kg: 8, color: '#646b56', size: 0.104 },
    { kg: 10, color: '#353b44', size: 0.111 },
    { kg: 12, color: '#455d93', size: 0.119 },
    { kg: 14, color: '#57463e', size: 0.125 },
  ];
  const rack = group(area, 'Three-tier steel dumbbell rack', [-0.54, 0, 2.91]);
  const rackShell = p.graphite.clone();
  rackShell.color.set('#999d9e');
  rackShell.roughness = 0.57;
  const sideX = 0.558;
  for (const x of [-sideX, sideX]) {
    beam(rack, [x, 0.044, -0.199], [x, 0.815, 0.1], 0.042, 0.043, rackShell);
    cable(
      rack,
      [
        [x, 0.051, 0.142],
        [x, 0.192, 0.139],
        [x, 0.306, 0.09],
        [x, 0.419, -0.045],
      ],
      0.016,
      rackShell,
    );
    box(rack, [0.056, 0.038, 0.473], [x, 0.029, -0.069], rackShell, 0.011);
    for (const z of [-0.305, 0.167])
      box(rack, [0.058, 0.039, 0.016], [x, 0.027, z], p.rubber, 0.006);
  }
  const tiers = Array.from({ length: 3 }, (_, index) => {
    const tray = group(rack, 'Inclined steel tray ' + (index + 1), [
      0,
      0.73 - index * 0.236,
      0.036 - index * 0.074,
    ]);
    tray.rotation.x = -0.15;
    box(tray, [1.111, 0.015, 0.216], [0, 0, 0], steel, 0.004);
    box(tray, [1.091, 0.004, 0.195], [0, 0.008, 0], p.rubber, 0.001);
    box(tray, [1.114, 0.028, 0.012], [0, 0.009, -0.104], steel, 0.003);
    box(tray, [1.112, 0.018, 0.012], [0, 0.005, 0.104], steel, 0.003);
    for (const sign of [-1, 1]) {
      const x = sign * sideX;
      box(tray, [0.037, 0.035, 0.236], [x, 0.012, 0], rackShell, 0.009);
      for (const z of [-0.068, 0.058]) {
        tube(tray, [x + sign * 0.017, 0.012, z], [x + sign * 0.02, 0.012, z], 0.0065, p.graphite);
      }
    }
    return tray;
  });
  for (const [index, { kg, color, size }] of weights.entries()) {
    const tier = Math.floor(index / 2);
    const height = 0.01 + size * 0.48;
    const depth = 0.024 + index * 0.004;
    const material = p.rubber.clone();
    material.color.set('#ffffff');
    material.normalScale.set(1.64, 1.64);
    material.map = canvasTexture(256, 256, (ctx) => {
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 256, 256);
      const rng = random(229 + index);
      for (let fleck = 0; fleck < 5200; fleck++) {
        ctx.fillStyle = fleck % 3 === 0 ? '#e1d7c345' : '#24282645';
        ctx.fillRect(rng() * 256, rng() * 256, 0.7 + rng() * 1.9, 0.7 + rng() * 1.9);
      }
    });
    const mark = canvasTexture(96, 96, (ctx) => {
      ctx.strokeStyle = '#e4dfd2c9';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(48, 48, 37, 0, Math.PI * 2);
      ctx.stroke();
      ctx.textAlign = 'center';
      ctx.fillStyle = '#e4dfd2dc';
      ctx.font = '600 36px "IBM Plex Sans", sans-serif';
      ctx.fillText(String(kg), 48, 54);
      ctx.font = '500 12px "IBM Plex Sans", sans-serif';
      ctx.fillText('KG', 48, 69);
    });
    const ink = new T.MeshStandardMaterial({
      map: mark,
      transparent: true,
      depthWrite: false,
      roughness: 0.95,
    });
    const pairCenter = index % 2 === 0 ? -0.258 : 0.258;
    for (const offset of [-0.119, 0.119]) {
      const pair = group(tiers[tier], kg + ' kg rubber-coated dumbbell', [
        pairCenter + offset,
        height,
        0,
      ]);
      tube(pair, [0, 0, -0.067], [0, 0, 0.067], 0.0176 + index * 0.0012, material);
      for (const direction of [-1, 1]) {
        tube(
          pair,
          [0, 0, direction * 0.044],
          [0, 0, direction * 0.06],
          0.0185 + index * 0.001,
          material,
          0.024 + index * 0.001,
        );
        box(
          pair,
          [size, size * 0.96, depth + 0.022],
          [0, 0, direction * (0.058 + depth * 0.2)],
          material,
          0.021 + index * 0.0018,
        );
        const face = mesh(pair, new T.PlaneGeometry(size * 0.44, size * 0.44), ink, [
          0,
          0,
          direction * (0.058 + depth * 0.2 + (depth + 0.022) / 2 + 0.0004),
        ]);
        face.rotation.y = direction < 0 ? Math.PI : 0;
        face.castShadow = false;
      }
    }
  }
  const rail = group(area, 'Towel rail', [-0.49, 1.17, 3.132]);
  for (const x of [-0.28, 0.28]) {
    box(rail, [0.049, 0.07, 0.015], [x, 0, 0.035], p.woodDark, 0.004);
    tube(rail, [x, 0, 0.028], [x, 0, -0.034], 0.009, steel);
  }
  tube(rail, [-0.29, 0, -0.035], [0.29, 0, -0.035], 0.009, steel);
  const towel = new T.PlaneGeometry(0.34, 0.53, 25, 30);
  const vertices = towel.attributes.position;
  for (let i = 0; i < vertices.count; i++) {
    const x = vertices.getX(i),
      t = vertices.getY(i) + 0.265;
    const fold = Math.min(1, Math.abs(t - 0.35) * 8);
    vertices.setXYZ(
      i,
      x,
      -Math.abs(t - 0.35) + 0.006 * Math.cos(x * 22),
      (t < 0.35 ? -0.019 : 0.011) * fold + 0.01 * Math.sin(x * 51) * fold,
    );
  }
  towel.computeVertexNormals();
  const terry = p.linen.clone();
  terry.color.set('#7c8980');
  terry.side = T.DoubleSide;
  mesh(rail, towel, terry, [0.032, 0.012, -0.035]);

  const storage = group(area, 'Low shelf for training gear', [0.91, 0, 2.94]);
  box(storage, [0.55, 0.025, 0.31], [0, 0.439, 0], p.wood, 0.003);
  box(storage, [0.51, 0.019, 0.28], [0, 0.136, 0.005], p.woodDark, 0.003);
  for (const x of [-0.253, 0.253]) {
    box(storage, [0.027, 0.431, 0.29], [x, 0.215, 0.005], p.woodVertical, 0.003);
    for (const z of [-0.09, 0.1]) tube(storage, [x, 0.45, z], [x, 0.4525, z], 0.0028, p.bronze);
  }
  trainingDuffel(storage, p);
  const folded = p.linen.clone();
  folded.color.set('#b4a388');
  for (let i = 0; i < 3; i++)
    box(
      storage,
      [0.24 - i * 0.012, 0.026, 0.18],
      [-0.06, 0.159 + i * 0.025, -0.021],
      folded,
      0.011,
    );
}

function trainingDuffel(parent: T.Group, p: Palette) {
  const bag = group(parent, 'Waxed canvas training duffel', [-0.026, 0.537, 0.003]);
  bag.rotation.y = -0.15;
  const canvas = p.linen.clone();
  canvas.color.set('#7a7356');
  canvas.normalScale.set(0.7, 0.7);
  const base = p.linen.clone();
  base.color.set('#47483c');
  const binding = p.linen.clone();
  binding.color.set('#494d40');
  const leather = p.cameraGrip.clone();
  leather.color.set('#9b765a');
  const body = box(bag, [0.362, 0.167, 0.203], [0, 0, 0], canvas, 0.059);
  body.geometry = body.geometry.clone();
  const vertices = body.geometry.attributes.position;
  for (let i = 0; i < vertices.count; i++) {
    const x = vertices.getX(i),
      y = vertices.getY(i),
      z = vertices.getZ(i);
    const fold = Math.sin(x * 86 + y * 49) * Math.sin(x * 21 + 1.1) * 0.0022;
    vertices.setXYZ(
      i,
      x,
      y + Math.max(0, y * 9) * Math.sin(x * 23 + z * 14) * 0.004,
      z + fold * Math.abs(z) * 9,
    );
  }
  box(bag, [0.328, 0.028, 0.181], [0, -0.071, 0], base, 0.011);
  box(bag, [0.214, 0.084, 0.016], [-0.012, -0.014, -0.097], canvas, 0.006);
  box(bag, [0.213, 0.004, 0.005], [-0.012, 0.027, -0.107], binding, 0.0015);
  box(bag, [0.048, 0.019, 0.002], [-0.008, -0.026, -0.106], leather, 0.0018);
  const perimeter = [
    [0, -0.077, -0.067],
    [0, -0.061, -0.095],
    [0, 0.037, -0.098],
    [0, 0.076, -0.061],
    [0, 0.081, 0.035],
    [0, 0.06, 0.086],
    [0, -0.018, 0.099],
    [0, -0.072, 0.067],
  ] as XYZ[];
  for (const end of [-0.138, 0.138]) {
    cable(
      bag,
      perimeter.map(([, y, z]) => [end, y, z] as XYZ),
      0.0017,
      binding,
    );
  }
  box(bag, [0.276, 0.0024, 0.014], [0, 0.0845, 0.01], binding, 0.001);
  for (let i = 0; i < 62; i++)
    box(bag, [0.0016, 0.0011, 0.0044], [-0.134 + i * 0.0043, 0.086, 0.01], p.bronze);
  box(bag, [0.012, 0.0036, 0.008], [0.075, 0.088, 0.01], p.graphite, 0.0012);
  const pull = box(bag, [0.022, 0.0018, 0.008], [0.085, 0.09, 0.014], leather, 0.0008);
  pull.rotation.y = 0.49;
  for (const z of [-0.091, 0.088]) {
    const curve = new T.CatmullRomCurve3([
      new T.Vector3(-0.091, -0.031, z),
      new T.Vector3(-0.09, 0.067, z * 0.94),
      new T.Vector3(-0.058, 0.125, z * 0.79),
      new T.Vector3(0.049, 0.131, z * 0.79),
      new T.Vector3(0.084, 0.066, z * 0.94),
      new T.Vector3(0.085, -0.028, z),
    ]);
    const points = curve.getPoints(26);
    const strip = new T.BufferGeometry();
    const positions = points.flatMap((point) =>
      [-0.008, 0.008].flatMap((offset) => [point.x, point.y, point.z + offset]),
    );
    const uv = points.flatMap((_, i) => [i / 26, 0, i / 26, 1]);
    const indices = points
      .slice(1)
      .flatMap((_, i) => [2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 1, 2 * i + 3, 2 * i + 2]);
    strip.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
    strip.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
    strip.setIndex(indices);
    strip.computeVertexNormals();
    const webbing = binding.clone();
    webbing.side = T.DoubleSide;
    mesh(bag, strip, webbing);
    for (const x of [-0.088, 0.084])
      box(bag, [0.026, 0.043, 0.004], [x, -0.007, z * 1.13], binding, 0.0017);
  }
  const ring = mesh(
    bag,
    new T.TorusGeometry(0.011, 0.002, 7, 20),
    p.bronze,
    [0.173, 0.025, -0.024],
  );
  ring.rotation.y = Math.PI / 2;
}

export function deskFurniture(root: T.Group, p: Palette) {
  const { left, right, back, front, top } = desk;
  box(
    root,
    [right - left, 0.04, front - back],
    [(left + right) / 2, top - 0.02, (front + back) / 2],
    p.wood,
    0.005,
  );
  box(
    root,
    [right - left - 0.025, 0.017, 0.012],
    [(left + right) / 2, top - 0.033, front - 0.004],
    p.woodDark,
    0.0025,
  );
  box(
    root,
    [right - left - 0.024, 0.12, 0.036],
    [(left + right) / 2, 0.657, back + 0.09],
    p.woodDark,
    0.002,
  );
  for (const x of [left + 0.026, right - 0.027]) {
    box(root, [0.047, 0.713, 0.827], [x, 0.36, -0.069], p.woodDark, 0.003);
  }

  const drawers: T.Group[] = [];
  const shelfDepth = 0.574,
    width = 0.402;
  let drive!: T.Group;
  for (const [side, x] of [
    [0, left + 0.263],
    [1, right - 0.247],
  ]) {
    const cabinet = group(root, side === 0 ? 'Left drawer chest' : 'Right drawer chest', [
      x,
      0,
      0.105,
    ]);
    for (const y of [0.036, 0.639])
      box(cabinet, [width, 0.029, shelfDepth], [0, y, -0.029], p.wood, 0.003);
    for (const x of [-0.192, 0.192])
      box(cabinet, [0.022, 0.602, shelfDepth], [x, 0.336, -0.029], p.woodDark, 0.003);
    box(cabinet, [width, 0.596, 0.018], [0, 0.335, -0.307], p.woodDark, 0.002);
    for (let i = 0; i < 3; i++) {
      const y = 0.54 - i * 0.194;
      const tray = group(cabinet, 'Drawer ' + (side * 3 + i + 1), [0, y, 0.257]);
      const veneer = p.wood.clone();
      const grain = p.wood.map!.clone();
      grain.repeat.set(0.72, 0.37);
      grain.offset.set(0.068 + i * 0.047, (side * 3 + i) * 0.111);
      veneer.map = grain;
      veneer.color.set(['#f9f6f3', '#f0eeea', '#f8f4f1'][i]);
      box(tray, [0.369, 0.184, 0.027], [0, 0, 0.011], veneer, 0.003);
      box(tray, [0.341, 0.013, 0.468], [0, -0.079, -0.235], p.woodDark, 0.001);
      for (const x of [-0.165, 0.165]) {
        box(tray, [0.013, 0.121, 0.468], [x, -0.02, -0.235], p.wood, 0.001);
        box(tray, [0.007, 0.014, 0.36], [x * 1.07, -0.034, -0.25], p.steel, 0.001);
      }
      box(tray, [0.341, 0.12, 0.014], [0, -0.02, -0.466], p.woodDark, 0.001);
      box(tray, [0.105, 0.029, 0.006], [0, 0.038, 0.026], p.bronze, 0.005);
      box(tray, [0.083, 0.015, 0.002], [0, 0.037, 0.0294], p.black, 0.004);
      box(tray, [0.087, 0.005, 0.014], [0, 0.047, 0.031], p.bronze, 0.0023);
      for (const x of [-0.045, 0.045])
        tube(tray, [x, 0.038, 0.029], [x, 0.038, 0.0305], 0.0024, p.steel);
      drawers.push(tray);
      if (side === 1 && i === 0) {
        drive = group(tray, 'Portable SSD', [-0.044, -0.064, -0.172]);
        box(drive, [0.078, 0.012, 0.048], [0, 0, 0], p.graphite, 0.005);
        box(drive, [0.077, 0.002, 0.045], [0, 0.006, 0], p.steel, 0.001);
        box(drive, [0.012, 0.003, 0.003], [0, 0, 0.025], p.black, 0.001);
        const printFace = print(
          drive,
          0.055,
          0.028,
          [0, 0.0075, 0],
          textTexture('PORTABLE SSD', 'ARCHIVE', '#383e42'),
        );
        printFace.rotation.x = -Math.PI / 2;
        printFace.castShadow = false;
      }
    }
  }
  return { drawers, drive };
}

export function radiator(root: T.Group, p: Palette) {
  const unit = group(root, 'Cast iron radiator', [-1.13, 0.0, 0.9]);
  const enamel = p.plaster.clone();
  enamel.color.set('#9a8977');
  enamel.roughness = 0.59;
  enamel.metalness = 0.13;
  const fins = 15;
  for (let i = 0; i < fins; i++) {
    const z = i * 0.053;
    box(unit, [0.112, 0.572, 0.041], [0, 0.355, z], enamel, 0.019);
    tube(unit, [-0.036, 0.106, z], [-0.036, 0.596, z], 0.015, enamel);
    tube(unit, [0.033, 0.106, z], [0.033, 0.596, z], 0.015, enamel);
  }
  for (const y of [0.139, 0.571]) tube(unit, [0, y, -0.028], [0, y, 0.776], 0.021, enamel);
  const valve = group(unit, 'Thermostatic radiator inlet', [0, 0.571, 0.821]);
  const brass = p.bronze.clone();
  brass.color.set('#ad895f');
  const thermostat = p.plaster.clone();
  thermostat.color.set('#d3cfc1');
  thermostat.roughness = 0.73;
  tube(valve, [0, 0, -0.048], [0, 0, -0.009], 0.0145, brass);
  const nut = mesh(valve, new T.CylinderGeometry(0.02, 0.02, 0.013, 6), brass, [0, 0, -0.027]);
  nut.rotation.x = Math.PI / 2;
  tube(valve, [0, -0.027, 0], [0, 0.012, 0], 0.0167, brass);
  tube(valve, [0, 0.009, 0], [0, 0.021, 0], 0.0182, p.steel);
  const head = [
    [0, 0.017],
    [0.016, 0.017],
    [0.02, 0.026],
    [0.021, 0.061],
    [0.018, 0.068],
    [0, 0.069],
  ];
  mesh(
    valve,
    new T.LatheGeometry(
      head.map(([r, y]) => new T.Vector2(r, y)),
      52,
    ),
    thermostat,
  );
  for (let i = 0; i < 24; i++) {
    const a = (i * Math.PI * 2) / 24;
    const rib = box(
      valve,
      [0.0028, 0.032, 0.0024],
      [Math.cos(a) * 0.0203, 0.045, Math.sin(a) * 0.0203],
      thermostat,
      0.001,
    );
    rib.rotation.y = -a;
  }
  const marks = canvasTexture(144, 144, (ctx) => {
    ctx.fillStyle = '#3a3b37';
    ctx.font = '600 30px "IBM Plex Sans", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('2  3  4', 72, 79);
    ctx.fillRect(70, 91, 4, 11);
  });
  const scale = mesh(
    valve,
    new T.PlaneGeometry(0.034, 0.034),
    new T.MeshStandardMaterial({
      map: marks,
      transparent: true,
      depthWrite: false,
      roughness: 0.83,
    }),
    [0, 0.0692, 0],
  );
  scale.rotation.x = -Math.PI / 2;
  scale.castShadow = false;
  cable(
    valve,
    [
      [0, -0.021, 0],
      [0, -0.16, 0],
      [0, -0.396, 0],
      [-0.021, -0.433, 0],
      [-0.125, -0.436, 0],
    ],
    0.0094,
    brass,
  );
  cable(
    unit,
    [
      [0, 0.139, -0.017],
      [0, 0.139, -0.054],
      [-0.031, 0.114, -0.065],
      [-0.127, 0.114, -0.065],
    ],
    0.01,
    brass,
  );
  for (const z of [0.075, 0.678]) box(unit, [0.084, 0.088, 0.038], [0, 0.044, z], enamel, 0.005);
}

export function bookshelf(root: T.Group, p: Palette) {
  const { x: center, z, width, height, side, depth } = bookcase;
  const unit = group(root, 'Walnut bookcase', [center, 0, z]);
  box(unit, [width, height, 0.025], [0, height / 2, -0.169], p.woodDark, 0.002);
  for (const x of [-width / 2, width / 2])
    box(unit, [side, height, depth], [x, height / 2, 0], p.woodVertical, 0.004);
  const levels = [0.093, 0.43, 0.832, 1.239, 1.64, 2.018, height - 0.016];
  for (const y of levels) box(unit, [width, 0.028, 0.353], [0, y, 0], p.wood, 0.003);
  const objects: T.Group[] = [];
  const sizes = [
    0.064, 0.071, 0.059, 0.052, 0.063, 0.044, 0.044, 0.037, 0.048, 0.036, 0.072, 0.04, 0.063,
  ];
  const rowSlots = [0, 5, 9, 13];
  for (let row = 0; row < 3; row++) {
    let x = -0.263;
    for (let i = rowSlots[row]; i < rowSlots[row + 1]; i++) {
      const [title, english, author, color] = books[i];
      const w = sizes[i],
        h = 0.212 + ((i * 0.031) % 0.089),
        d = 0.161 + ((i * 0.02) % 0.049);
      const book = group(unit, title, [x + w / 2, levels[4 - row] + 0.014 + h / 2, 0.073 - d / 2]);
      const jacket = new T.MeshStandardMaterial({
        color,
        roughness: i % 4 === 0 ? 0.62 : 0.86,
        normalMap: p.cloth.normalMap,
      });
      box(book, [w - 0.005, h - 0.006, d - 0.006], [0, 0, -0.002], p.paper, 0.0015);
      for (const x of [-w / 2 + 0.0012, w / 2 - 0.0012])
        box(book, [0.0024, h, d], [x, 0, 0], jacket, 0.001);
      box(book, [w, h, 0.006], [0, 0, d / 2 - 0.001], jacket, 0.0025);
      const spine = canvasTexture(128, 512, (ctx) => {
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, 128, 512);
        ctx.fillStyle = '#e0caab';
        ctx.strokeStyle = '#ddbb835c';
        if (i % 3 === 0) ctx.strokeRect(13, 23, 102, 464);
        else {
          ctx.beginPath();
          ctx.moveTo(19, 67);
          ctx.lineTo(108, 67);
          ctx.moveTo(19, 456);
          ctx.lineTo(108, 456);
          ctx.stroke();
        }
        ctx.font = '15px Georgia, serif';
        ctx.textAlign = 'center';
        ctx.fillText(String(i + 1).padStart(2, '0'), 64, 49);
        ctx.translate(64, 261);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = '600 30px "IBM Plex Sans", sans-serif';
        const splitAt = english.indexOf(': ');
        if (splitAt >= 0) {
          ctx.fillText(english.slice(0, splitAt), 0, -12, 376);
          ctx.font = '500 23px "IBM Plex Sans", sans-serif';
          ctx.fillText(english.slice(splitAt + 2), 0, 17, 376);
        } else ctx.fillText(english, 0, 0, 376);
      });
      print(book, w - 0.004, h - 0.006, [0, 0, d / 2 + 0.0025], spine).castShadow = false;
      const coverWidth = d - 0.006,
        coverHeight = h - 0.007;
      const jacketPrint = canvasTexture(
        Math.round((1000 * coverWidth) / coverHeight),
        1000,
        (ctx) => {
          const { width, height } = ctx.canvas;
          ctx.fillStyle = color;
          ctx.fillRect(0, 0, width, height);
          ctx.strokeStyle = '#ebd9b751';
          ctx.strokeRect(29, 32, width - 58, height - 64);
          ctx.textAlign = 'center';
          ctx.fillStyle = '#f3e6c9';
          const center = width / 2,
            textWidth = width - 108;
          ctx.font = '600 60px "Studio Han", sans-serif';
          ctx.fillText(title, center, 344, textWidth);
          ctx.font = '600 37px "IBM Plex Sans", sans-serif';
          const lines: string[] = [];
          let line = '';
          for (const word of english.split(' ')) {
            const next = line ? line + ' ' + word : word;
            if (line && ctx.measureText(next).width > textWidth) {
              lines.push(line);
              line = word;
            } else line = next;
          }
          lines.push(line);
          lines.forEach((text, index) => ctx.fillText(text, center, 452 + index * 44, textWidth));
          ctx.font = '500 28px "IBM Plex Sans", sans-serif';
          ctx.fillText(author, center, 705, textWidth);
        },
      );
      const cover = print(book, coverWidth, coverHeight, [w / 2 + 0.0005, 0, 0], jacketPrint);
      cover.rotation.y = Math.PI / 2;
      cover.castShadow = false;
      objects.push(book);
      x += w + 0.004;
    }
  }
  for (const [x, y, w, h] of [
    [-0.105, 0.18, 0.27, 0.145],
    [0.078, 0.554, 0.342, 0.219],
  ]) {
    const caseMat = surface(y > 0.3 ? '#393e3b' : '#5c5143', 0.81);
    box(unit, [w, h, 0.271], [x, y, -0.002], caseMat, 0.006);
    box(unit, [w + 0.008, 0.022, 0.279], [x, y + h / 2, -0.002], caseMat, 0.003);
    box(unit, [0.084, 0.019, 0.003], [x, y + 0.018, 0.135], p.bronze, 0.002);
  }
  const stack = group(unit, 'Horizontal study books', [0.151, 1.668, -0.021]);
  const horizontalBooks = [
    ['新机器的灵魂', 'The Soul of a New Machine', '#5f4e44'],
    ['设计心理学', 'The Design of Everyday Things', '#4e5956'],
    ['看不见的城市', 'Invisible Cities', '#745e58'],
  ];
  for (const [i, [title, english, color]] of horizontalBooks.entries()) {
    const binding = surface(color, 0.83);
    const book = group(stack, 'Horizontal binding', [0.004 * i, 0.016 + i * 0.039, 0.013 * i]);
    book.rotation.y = (i - 1) * 0.09;
    box(book, [0.202 - i * 0.014, 0.031, 0.151], [0, 0, 0], p.paper, 0.001);
    for (const y of [-0.016, 0.016])
      box(book, [0.209 - i * 0.014, 0.003, 0.16], [0, y, 0], binding, 0.001);
    box(book, [0.208 - i * 0.014, 0.034, 0.005], [0, 0, 0.077], binding, 0.001);
    const label = canvasTexture(768, 112, (ctx) => {
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 768, 112);
      ctx.fillStyle = '#eddbbb';
      ctx.font = '600 36px "Studio Han", sans-serif';
      ctx.fillText(title, 37, 69, 247);
      ctx.font = '500 27px "IBM Plex Sans", sans-serif';
      ctx.fillText(english, 294, 67, 432);
    });
    print(book, 0.199 - i * 0.014, 0.026, [0, 0, 0.0801], label).castShadow = false;
  }
  pottedPlant(unit, p, [0.135, 2.031, -0.025]);
  return { books: objects, awards: shelfAwards(unit, p) };
}

export function workshop(root: T.Group, p: Palette) {
  const width = 0.606,
    { depth, height } = bookcase;
  const adjoiningEdge = bookcase.x + (bookcase.width + bookcase.side) / 2;
  const storage = group(root, 'Narrow storage cabinet', [adjoiningEdge + width / 2, 0, bookcase.z]);
  box(storage, [width - 0.034, 0.079, depth - 0.037], [0, 0.0395, -0.014], p.woodDark, 0.0025);
  for (const side of [-1, 1]) {
    box(
      storage,
      [0.019, height - 0.075, depth],
      [side * (width / 2 - 0.0095), (height + 0.075) / 2, 0],
      p.woodVertical,
      0.002,
    );
  }
  for (const y of [0.088, 1.109, height - 0.011])
    box(storage, [width - 0.033, 0.022, depth], [0, y, 0], p.wood, 0.002);
  box(
    storage,
    [width - 0.031, height - 0.098, 0.015],
    [0, height / 2 + 0.035, -depth / 2 + 0.0075],
    p.woodVertical,
  );
  const doorFace = p.woodVertical.clone();
  doorFace.color.set('#e5ddd3');
  for (const [bottom, top, handle] of [
    [0.105, 1.093, 0.938],
    [1.125, height - 0.027, 1.265],
  ]) {
    const faceHeight = top - bottom,
      y = (bottom + top) / 2;
    box(storage, [width - 0.049, faceHeight, 0.022], [0, y, depth / 2 - 0.016], p.woodDark, 0.002);
    box(
      storage,
      [width - 0.089, faceHeight - 0.045, 0.007],
      [0, y, depth / 2 - 0.001],
      doorFace,
      0.0018,
    );
    for (const offset of [-0.036, 0.036]) {
      tube(
        storage,
        [width / 2 - 0.07, handle + offset, depth / 2 - 0.003],
        [width / 2 - 0.07, handle + offset, depth / 2 + 0.016],
        0.0042,
        p.bronze,
      );
    }
    tube(
      storage,
      [width / 2 - 0.07, handle - 0.044, depth / 2 + 0.016],
      [width / 2 - 0.07, handle + 0.044, depth / 2 + 0.016],
      0.0032,
      p.bronze,
    );
  }

  const unit = group(root, 'Workbench', [workshopLayout.x, 0, workshopLayout.z]);
  const top = box(
    unit,
    [0.626, 0.038, workshopLayout.length],
    [0, 0.731, 0],
    p.woodVertical,
    0.006,
  );
  top.name = 'Workbench top';
  for (const x of [-0.278, 0.281])
    for (const z of [-0.662, 0.662]) {
      box(unit, [0.043, 0.707, 0.045], [x, 0.361, z], p.woodVertical, 0.002);
      box(unit, [0.044, 0.008, 0.046], [x, 0.009, z], p.rubber, 0.001);
    }
  box(unit, [0.041, 0.117, 1.38], [0.282, 0.647, 0], p.woodDark, 0.002);
  for (const z of [-0.633, 0.633]) box(unit, [0.53, 0.075, 0.027], [0, 0.683, z], p.wood, 0.002);
  const frame = group(unit, 'Framed fiberboard and hardware');
  box(frame, [0.028, 0.581, 1.27], [0.294, 1.26, -0.012], p.woodDark, 0.004);
  const peg = canvasTexture(1024, 464, (ctx) => {
    ctx.fillStyle = '#b3a38e';
    ctx.fillRect(0, 0, 1024, 464);
    for (let i = 0; i < 8000; i++) {
      ctx.fillStyle = i % 2 ? '#4e392816' : '#ffedd52e';
      ctx.fillRect((i * 229) % 1024, (i * i * 11 + i * 89) % 464, 1 + (i % 3), 1);
    }
    for (let row = 0; row < 17; row++)
      for (let col = 0; col < 38; col++) {
        const x = 32 + col * 26,
          y = 27 + row * 25;
        ctx.fillStyle = '#d5c7ae';
        ctx.beginPath();
        ctx.arc(x, y + 1, 3.4, 0, 2 * Math.PI);
        ctx.fill();
        ctx.fillStyle = '#342c24';
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
        ctx.fill();
      }
  });
  const board = mesh(
    frame,
    new T.PlaneGeometry(1.23, 0.545),
    new T.MeshStandardMaterial({
      map: peg,
      roughness: 0.93,
      normalMap: p.cork.normalMap,
      normalScale: new T.Vector2(0.65, 0.65),
    }),
    [0.2794, 1.26, -0.012],
  );
  board.rotation.y = -Math.PI / 2;
  board.castShadow = false;
  const mat = p.rubber.clone();
  mat.color.set('#243d37');
  box(unit, [0.391, 0.004, 0.585], [-0.05, 0.754, 0.13], mat, 0.002);
  const markings = canvasTexture(1170, 782, (ctx) => {
    ctx.fillStyle = '#2c5147';
    ctx.fillRect(0, 0, 1170, 782);
    ctx.font = '500 13px "IBM Plex Sans", sans-serif';
    for (let i = 0; i <= 56; i++) {
      const x = 25 + i * 20;
      ctx.strokeStyle = i % 5 ? '#a6b69054' : '#c1c99ea1';
      ctx.lineWidth = i % 5 ? 0.75 : 1.5;
      ctx.beginPath();
      ctx.moveTo(x, 24);
      ctx.lineTo(x, 758);
      ctx.stroke();
      if (i % 5 === 0) {
        ctx.fillStyle = '#d4d1aa';
        ctx.fillText(String(i), x + 3, 18);
        ctx.fillText(String(i), x + 3, 774);
      }
    }
    for (let i = 0; i <= 36; i++) {
      const y = 25 + i * 20;
      ctx.strokeStyle = i % 5 ? '#a6b69054' : '#c1c99ea1';
      ctx.lineWidth = i % 5 ? 0.75 : 1.5;
      ctx.beginPath();
      ctx.moveTo(25, y);
      ctx.lineTo(1145, y);
      ctx.stroke();
      if (i % 5 === 0) {
        ctx.fillStyle = '#d4d1aa';
        ctx.fillText(String(i), 7, y - 4);
      }
    }
    ctx.strokeStyle = '#c4cca1a9';
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(26, 756);
    ctx.lineTo(760, 22);
    ctx.moveTo(409, 756);
    ctx.lineTo(1143, 22);
    ctx.stroke();
    ctx.setLineDash([]);
    const rng = random(452);
    for (let i = 0; i < 55; i++) {
      const x = 250 + rng() * 740,
        y = 200 + rng() * 340;
      ctx.strokeStyle = i % 2 ? '#121f1b24' : '#d5cda818';
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 5 + rng() * 23, y + (rng() - 0.5) * 9);
      ctx.stroke();
    }
  });
  const ruler = print(unit, 0.583, 0.389, [-0.05, 0.7563, 0.13], markings);
  ruler.name = 'Self-healing cutting mat and ruler grid';
  ruler.rotation.set(-Math.PI / 2, 0, -Math.PI / 2);
  const rulerInk = ruler.material as T.MeshStandardMaterial;
  rulerInk.normalMap = p.rubber.normalMap;
  rulerInk.roughness = 0.95;
  ruler.castShadow = false;
  const toolRail = group(unit, 'Fastened screwdriver rail', [0.255, 1.186, -0.315]);
  box(toolRail, [0.047, 0.028, 0.253], [0.005, 0, 0], p.woodDark, 0.003);
  for (const z of [-0.112, 0.112]) tube(toolRail, [-0.019, 0, z], [-0.021, 0, z], 0.0032, p.steel);
  for (const [z, length, radius, color] of [
    [-0.071, 0.124, 0.014, '#695044'],
    [0, 0.097, 0.011, '#373f41'],
    [0.069, 0.073, 0.008, '#606852'],
  ] as const) {
    const handle = p.rubber.clone();
    handle.color.set(color);
    handle.roughness = 0.71;
    const shaftX = -0.013;
    tube(toolRail, [shaftX, 0.019, z], [shaftX, 0.082, z], radius, handle);
    tube(toolRail, [shaftX, 0.082, z], [shaftX, 0.091, z], radius * 1.13, p.steel);
    tube(toolRail, [shaftX, 0.009, z], [shaftX, 0.025, z], radius * 0.8, p.graphite);
    tube(toolRail, [shaftX, -length + 0.014, z], [shaftX, 0.011, z], radius * 0.23, p.steel);
    const tip = mesh(
      toolRail,
      new T.CylinderGeometry(radius * 0.22, radius * 0.09, 0.012, 4),
      p.graphite,
      [shaftX, -length + 0.008, z],
    );
    tip.rotation.y = Math.PI / 4;
    for (const y of [0.036, 0.046, 0.056])
      tube(toolRail, [shaftX, y, z], [shaftX, y + 0.0015, z], radius * 1.015, p.rubber);
  }
  const pliers = group(unit, 'Forged diagonal cutters', [0.235, 1.296, 0.027]);
  cable(
    unit,
    [
      [0.284, 1.316, 0.027],
      [0.249, 1.316, 0.027],
      [0.221, 1.316, 0.027],
      [0.214, 1.321, 0.027],
      [0.214, 1.327, 0.027],
    ],
    0.0023,
    p.steel,
  );
  const steel = p.steel.clone();
  steel.color.set('#798086');
  steel.roughness = 0.43;
  const honed = surface('#a3a6a4', 0.29, 0.72);
  const grip = p.rubber.clone();
  grip.color.set('#854239');
  const lever = new T.Shape();
  lever.moveTo(0.03, -0.088);
  lever.bezierCurveTo(0.023, -0.061, 0.009, -0.03, -0.006, -0.021);
  lever.bezierCurveTo(-0.02, -0.013, -0.024, 0.002, -0.021, 0.016);
  lever.lineTo(-0.019, 0.028);
  lever.lineTo(-0.009, 0.039);
  lever.lineTo(-0.005, 0.035);
  lever.lineTo(-0.0045, 0.023);
  lever.lineTo(-0.0015, 0.014);
  lever.bezierCurveTo(0.013, 0.015, 0.021, 0.004, 0.017, -0.012);
  lever.bezierCurveTo(0.02, -0.03, 0.034, -0.067, 0.039, -0.086);
  lever.quadraticCurveTo(0.038, -0.091, 0.03, -0.088);
  const insulator = new T.Shape();
  insulator.moveTo(0.01, -0.042);
  insulator.quadraticCurveTo(0.011, -0.035, 0.021, -0.035);
  insulator.quadraticCurveTo(0.028, -0.035, 0.028, -0.047);
  insulator.bezierCurveTo(0.034, -0.067, 0.047, -0.1, 0.049, -0.113);
  insulator.quadraticCurveTo(0.051, -0.124, 0.043, -0.127);
  insulator.quadraticCurveTo(0.033, -0.131, 0.03, -0.12);
  insulator.bezierCurveTo(0.024, -0.1, 0.015, -0.072, 0.01, -0.042);
  const bevel = new T.Shape([
    new T.Vector2(-0.009, 0.038),
    new T.Vector2(-0.005, 0.034),
    new T.Vector2(-0.0045, 0.023),
    new T.Vector2(-0.0015, 0.015),
    new T.Vector2(-0.009, 0.018),
    new T.Vector2(-0.013, 0.027),
  ]);
  for (const sign of [-1, 1]) {
    const half = group(pliers, 'Forged lever and dipped grip');
    half.rotation.y = -Math.PI / 2;
    half.scale.x = sign;
    const offset = sign > 0 ? 0.0005 : -0.0054;
    mesh(
      half,
      new T.ExtrudeGeometry(lever, {
        depth: 0.0053,
        bevelEnabled: true,
        bevelThickness: 0.00135,
        bevelSize: 0.00145,
        bevelSegments: 3,
        curveSegments: 14,
      }),
      steel,
      [0, 0, offset],
    );
    mesh(
      half,
      new T.ExtrudeGeometry(insulator, {
        depth: 0.0115,
        bevelEnabled: true,
        bevelThickness: 0.0024,
        bevelSize: 0.0026,
        bevelSegments: 4,
        curveSegments: 14,
      }),
      grip,
      [0, 0, -0.006],
    );
    const edge = mesh(half, new T.ShapeGeometry(bevel), honed, [0, 0, offset + 0.0067]);
    edge.castShadow = false;
  }
  tube(pliers, [0.009, 0, 0], [-0.009, 0, 0], 0.0081, p.graphite);
  tube(pliers, [-0.0088, 0, 0], [-0.0102, 0, 0], 0.0067, honed);
  const rivet = mesh(pliers, new T.SphereGeometry(0.0052, 20, 12), steel, [-0.0101, 0, 0]);
  rivet.scale.x = 0.26;
  const pinRing = mesh(
    pliers,
    new T.TorusGeometry(0.0051, 0.00024, 6, 32),
    p.graphite,
    [-0.01035, 0, 0],
  );
  pinRing.rotation.y = -Math.PI / 2;
  const shelf = group(unit, 'Parts bins and calibration ruler', [0.228, 1.346, 0.285]);
  box(shelf, [0.104, 0.013, 0.318], [0, 0, 0], p.woodDark, 0.002);
  for (const z of [-0.122, 0.122])
    beam(shelf, [0.045, -0.059, z], [-0.043, -0.008, z], 0.009, 0.009, p.steel);
  const bins = surface('#596765', 0.82);
  for (const z of [-0.096, 0, 0.096]) {
    box(shelf, [0.081, 0.031, 0.082], [-0.004, 0.023, z], bins, 0.003);
    box(shelf, [0.003, 0.014, 0.044], [-0.046, 0.021, z], p.paper, 0.001);
    box(shelf, [0.069, 0.004, 0.074], [-0.009, 0.041, z], p.graphite, 0.001);
  }
  box(unit, [0.004, 0.022, 0.29], [0.265, 1.443, 0.28], p.steel, 0.001);
  for (let i = 0; i < 28; i++) {
    box(
      unit,
      [0.001, i % 5 === 0 ? 0.009 : 0.004, 0.0007],
      [0.2626, 1.437, 0.145 + i * 0.01],
      p.graphite,
    );
  }
  const tray = group(unit, 'Twelve-switch sampler', [-0.081, 0.757, 0.198]);
  box(tray, [0.094, 0.009, 0.124], [0, 0.005, 0], p.graphite, 0.004);
  box(tray, [0.091, 0.0019, 0.121], [0, 0.0102, 0], p.steel, 0.002);
  const switchShell = surface('#777a73', 0.47);
  const stems = ['#8d4b40', '#577d81', '#8b8150', '#aea18c'].map((color) => surface(color, 0.49));
  for (const x of [-0.04, 0.04])
    for (const z of [-0.053, 0.053]) {
      tube(tray, [x, 0.011, z], [x, 0.012, z], 0.0027, p.graphite);
    }
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 4; j++) {
      const x = (i - 1) * 0.025,
        z = (j - 1.5) * 0.025;
      box(tray, [0.015, 0.004, 0.015], [x, 0.013, z], p.black, 0.0007);
      box(tray, [0.013, 0.004, 0.013], [x, 0.0166, z], switchShell, 0.0014);
      box(tray, [0.0075, 0.003, 0.0026], [x, 0.0192, z], stems[j], 0.0004);
      box(tray, [0.0026, 0.003, 0.0075], [x, 0.0192, z], stems[j], 0.0004);
    }
  const taskLamp = lamp(unit, p, [0.094, 0.752, -0.622]);
  taskLamp.unit.name = 'Workbench lamp';
  taskLamp.unit.rotation.y = -1.18;
  taskLamp.emitter.emissiveIntensity = 0.52;
  const stool = group(root, 'Workbench stool · walnut and olive twill', [
    1.61,
    0,
    workshopLayout.z,
  ]);
  const wool = p.upholstery.clone();
  wool.color.set('#9d9e74');
  const profile = [
    [0, 0.43],
    [0.151, 0.43],
    [0.168, 0.437],
    [0.177, 0.45],
    [0.172, 0.47],
    [0.159, 0.483],
    [0.13, 0.488],
    [0, 0.491],
  ];
  mesh(
    stool,
    new T.LatheGeometry(
      profile.map(([r, y]) => new T.Vector2(r, y)),
      64,
    ),
    wool,
  );
  tube(stool, [0, 0.417, 0], [0, 0.436, 0], 0.165, p.wood);
  const ring = mesh(stool, new T.TorusGeometry(0.146, 0.0065, 9, 52), p.bronze, [0, 0.178, 0]);
  ring.rotation.x = Math.PI / 2;
  for (let i = 0; i < 3; i++) {
    const angle = (i * 2 * Math.PI) / 3 + 0.31;
    const point = (r: number, y: number): XYZ => [Math.cos(angle) * r, y, Math.sin(angle) * r];
    tube(stool, point(0.174, 0.02), point(0.112, 0.42), 0.012, p.woodVertical, 0.021);
    tube(stool, point(0.176, 0.0045), point(0.174, 0.024), 0.0128, p.rubber);
    tube(stool, point(0.145, 0.178), point(0.157, 0.178), 0.005, p.bronze);
  }
  return { unit, top, tray, taskLamp, stool, pliers };
}
