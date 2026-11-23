import * as T from 'three';
import { createStudioLoadingManager } from './asset-loading';
import type { DeferRoomAsset } from './rear-loading';
import { blenderMesh } from './blender-mesh';
import { publishedBooks } from './published-books';
import {
  box,
  cable,
  canvasTexture,
  group,
  luminous,
  mesh,
  print,
  random,
  surface,
  tube,
} from './geometry';
import { plasterUV, type Palette } from './materials';
import type { XYZ } from './geometry';
import { pottedPlant } from './props';
import { workbenchFixture } from './authored-fixtures';
import { workbenchBoardLight } from './workbench-board-light';
import { shelfAwards } from './awards';
import { writingDesk } from './writing-desk';
import { doorwayWormhole } from './wormhole';
import { acousticWall, archiveLight, rearGalleryPrint } from './millwork';
import { parquet, parquetSurfaceY } from './parquet';
import { loadDisplayModel } from './display-model';
import { bypassDoors, perforatedToolWall } from './workshop-fittings';

import { roomSize, roomDoor, desk, workshopLayout } from './layout';
export { roomSize, windowOpening, desk, workshopLayout } from './layout';

const bookcase = { x: 1.55, z: -0.374, width: 0.61, height: 2.41, side: 0.034, depth: 0.354 };

export function architecture(root: T.Group, p: Palette, coastalPrint: T.Texture) {
  const { west, east, north, south, ceiling } = roomSize;
  const x = (west + east) / 2,
    z = (north + south) / 2;
  const wallTop = ceiling + 0.024;
  function plaster(size: XYZ, center: XYZ, material = p.wall) {
    const part = box(root, size, center, material);
    part.geometry = part.geometry.clone();
    plasterUV(part.geometry, part.position);
  }
  plaster([east - west + 0.08, wallTop, 0.18], [x, wallTop / 2, north - 0.09]);
  acousticWall(root, p, west + 0.012, -0.913, north, ceiling);
  acousticWall(root, p, 1.205, east, north, ceiling - bookcase.height, bookcase.height);
  const pictureLight = archiveLight(root, p, north);
  rearGalleryPrint(root, p, coastalPrint, south);
  const doorCenter = roomDoor.center,
    doorLeft = doorCenter - roomDoor.halfWidth,
    doorRight = doorCenter + roomDoor.halfWidth,
    doorHeight = roomDoor.height;
  for (const [left, right] of [
    [west, doorLeft],
    [doorRight, east],
  ]) {
    const outerLeft = left === west ? west - 0.04 : left;
    const outerRight = right === east ? east + 0.04 : right;
    plaster(
      [outerRight - outerLeft, wallTop, 0.19],
      [(outerLeft + outerRight) / 2, wallTop / 2, south + 0.095],
    );
    box(
      root,
      [right - left, 0.068, 0.026],
      [(left + right) / 2, 0.035, south - 0.01],
      p.woodDark,
      0.003,
    );
  }
  plaster(
    [doorRight - doorLeft, wallTop - doorHeight, 0.19],
    [doorCenter, (wallTop + doorHeight) / 2, south + 0.095],
  );
  plaster([0.17, wallTop, south - north + 0.08], [east + 0.085, wallTop / 2, z]);
  const ceilingPaint = p.wall.clone();
  ceilingPaint.color.set('#f0ece4');
  ceilingPaint.normalScale.set(0.46, 0.46);
  plaster([east - west + 0.32, 0.18, south - north + 0.32], [x, ceiling + 0.09, z], ceilingPaint);
  box(root, [east - west, 0.14, south - north], [x, -0.07, z], p.woodDark);
  parquet(root, p, roomSize);
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
  const shadowLine = surface('#353730', 0.87);
  function cornice(name: string, depth: number, top: number, bottom: number, material: T.Material) {
    const vertices = [];
    const corners = (inset: number, height: number) => [
      [west + inset, ceiling + height, north + inset],
      [east - inset, ceiling + height, north + inset],
      [east - inset, ceiling + height, south - inset],
      [west + inset, ceiling + height, south - inset],
    ];
    const profile = [
      corners(-0.006, top),
      corners(depth, top),
      corners(depth, bottom),
      corners(-0.006, bottom),
    ];
    for (let edge = 0; edge < profile.length; edge++) {
      const start = profile[edge];
      const end = profile[(edge + 1) % profile.length];
      for (let side = 0; side < 4; side++) {
        const next = (side + 1) % 4;
        vertices.push(...start[side], ...end[next], ...start[next]);
        vertices.push(...start[side], ...end[side], ...end[next]);
      }
    }
    const geometry = new T.BufferGeometry();
    geometry.setAttribute('position', new T.Float32BufferAttribute(vertices, 3));
    geometry.computeVertexNormals();
    const uv = new Float32Array(geometry.attributes.position.count * 2);
    geometry.setAttribute('uv', new T.BufferAttribute(uv, 2));
    plasterUV(geometry, root.position);
    mesh(root, geometry, material).name = name;
  }
  cornice('Continuous ceiling shadow reveal', 0.021, -0.038, -0.056, shadowLine);
  cornice('Mitred plaster ceiling trim', 0.0335, 0.008, -0.035, ceilingPaint);
  const frame = group(root, 'Door · back right', [doorCenter, 1.055, south - 0.031]);
  const hinge = group(frame, 'Door hinge toward the workbench', [0.409, 0, 0]);
  const door = group(hinge, 'Hinged ash door', [-0.409, 0, 0]);
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
    pictureLight,
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

export function deskFurniture(root: T.Group, p: Palette, loader: T.TextureLoader) {
  return writingDesk(root, p, loader, desk);
}

export function radiator(root: T.Group, p: Palette) {
  const unit = group(root, 'Cast iron radiator', [-1.13, parquetSurfaceY, 0.9]);
  const enamel = surface('#e3dfd4', 0.43, 0.13);
  enamel.normalMap = p.plaster.normalMap;
  enamel.normalScale.set(0.55, 0.55);
  const middle = blenderMesh('princess-section');
  const end = blenderMesh('princess-footed');
  for (let i = 0; i < 10; i++) {
    mesh(unit, i === 0 || i === 9 ? end : middle, enamel, [0, 0, 0.0335 + i * 0.075]);
  }
  mesh(unit, blenderMesh('princess-bush'), enamel);
  mesh(unit, blenderMesh('princess-fittings'), surface('#a78a61', 0.34, 0.77));
  mesh(unit, blenderMesh('princess-wheel'), surface('#5d3726', 0.34, 0.05));
  mesh(unit, blenderMesh('princess-joints'), surface('#403b36', 0.6, 0.15));
}

export function bookshelf(
  root: T.Group,
  p: Palette,
  loader: T.TextureLoader,
  detailLoader: T.TextureLoader,
  deferBookBacks: boolean,
) {
  const { x: center, z, width, height, side, depth } = bookcase;
  const unit = group(root, 'Oiled ash bookcase', [center, 0, z]);
  box(unit, [width, height, 0.025], [0, height / 2, -0.169], p.woodDark, 0.002);
  box(unit, [width - 0.042, 0.084, depth - 0.063], [0, 0.043, -0.019], p.woodDark);
  for (const x of [-width / 2, width / 2]) {
    box(unit, [side, height - 0.063, depth], [x, (height + 0.063) / 2, 0], p.woodVertical, 0.0025);
    box(
      unit,
      [side + 0.003, height - 0.068, 0.01],
      [x, (height + 0.065) / 2, depth / 2 + 0.002],
      p.woodVertical,
      0.003,
    );
  }
  const levels = [0.093, 0.43, 0.832, 1.239, 1.64, 2.018, height - 0.016];
  const lamps = luminous('#ffe9c5', 0.85);
  const lining = p.woodVertical.clone();
  lining.color.set('#a28b72');
  const accent = new T.RectAreaLight('#ffddb3', 27, 0.01, height - 0.122);
  accent.position.set(-width / 2 + 0.025, (height + 0.08) / 2, 0.153);
  accent.rotation.y = -Math.PI * 0.49;
  unit.add(accent);
  for (const [i, y] of levels.entries()) {
    box(unit, [width, 0.025, 0.349], [0, y + 0.0015, -0.002], p.wood, 0.002);
    box(unit, [width - side, 0.033, 0.015], [0, y - 0.0025, 0.173], p.wood, 0.003);
    if (i === 0) continue;
    const clearHeight = y - levels[i - 1] - 0.028;
    const back = mesh(unit, new T.PlaneGeometry(width - side, clearHeight), lining, [
      0,
      y - 0.014 - clearHeight / 2,
      -0.1558,
    ]);
    back.castShadow = false;
    const channel = group(unit, 'Recessed linear light in cabinet stile', [
      accent.position.x,
      y - 0.014 - clearHeight / 2,
      accent.position.z,
    ]);
    channel.rotation.y = accent.rotation.y;
    box(channel, [0.013, clearHeight, 0.006], [0, 0, 0.002], p.graphite);
    box(channel, [0.009, clearHeight - 0.004, 0.0018], [0, 0, -0.0015], lamps);
    for (const sx of [-1, 1]) {
      for (const sz of [-0.111, 0.104])
        tube(
          unit,
          [sx * (width / 2 - 0.024), y - 0.015, sz],
          [sx * (width / 2 - 0.014), y - 0.015, sz],
          0.0025,
          p.steel,
        );
    }
  }
  const books = publishedBooks(unit, p, loader, levels, detailLoader, deferBookBacks);
  const caseMat = p.linen.clone();
  caseMat.color.set('#9a7b54');
  const archive = group(unit, 'Cloth-bound film archive', [-0.147, 0.18, -0.002]);
  archive.rotation.y = 0.019;
  box(archive, [0.262, 0.145, 0.271], [0, 0, 0], caseMat, 0.003);
  box(archive, [0.27, 0.022, 0.279], [0, 0.0725, 0], caseMat, 0.0017);
  box(archive, [0.084, 0.022, 0.002], [0, 0.014, 0.136], p.bronze, 0.0015);
  box(archive, [0.064, 0.015, 0.001], [0, 0.014, 0.137], p.paper);
  const label = canvasTexture(128, 32, (ctx) => {
    ctx.fillStyle = '#ddd2b9';
    ctx.fillRect(0, 0, 128, 32);
    ctx.fillStyle = '#35352f';
    ctx.font = '19px monospace';
    ctx.fillText('120', 9, 23);
  });
  print(archive, 0.063, 0.014, [0, 0.014, 0.1377], label).castShadow = false;
  for (const sx of [-1, 1])
    tube(archive, [sx * 0.037, 0.014, 0.137], [sx * 0.037, 0.014, 0.138], 0.002, p.bronze);
  pottedPlant(unit, p, [0.162, 2.031, -0.025]);
  return { unit, ...books, awards: shelfAwards(unit, p), lamps, accent };
}

export function workshop(
  root: T.Group,
  p: Palette,
  loader: T.TextureLoader,
  detailManager: T.LoadingManager,
  deferRoomDetail: DeferRoomAsset,
) {
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
  for (const y of [0.083, height - 0.01])
    box(storage, [width - 0.033, 0.022, depth], [0, y, 0], p.wood, 0.002);
  box(
    storage,
    [width - 0.031, height - 0.098, 0.015],
    [0, height / 2 + 0.035, -depth / 2 + 0.0075],
    p.woodVertical,
  );
  const cabinet = bypassDoors(storage, p);

  const unit = group(root, 'Workbench', [workshopLayout.x, 0, workshopLayout.z]);
  const boardLight = workbenchBoardLight(unit, detailManager);
  deferRoomDetail(boardLight.load);
  const top = box(
    unit,
    [0.626, 0.038, workshopLayout.length],
    [0, 0.731, 0],
    p.woodVertical,
    0.006,
  );
  top.name = 'Workbench top';
  const plyEdge = p.wood.clone();
  plyEdge.map = canvasTexture(128, 64, (ctx) => {
    ctx.fillStyle = '#bc9c74';
    ctx.fillRect(0, 0, 128, 64);
    for (let i = 0; i < 11; i++) {
      ctx.fillStyle = i % 2 ? '#b19a7e' : '#d7bda0';
      ctx.fillRect(0, i * 6, 128, 5.1);
    }
  });
  box(unit, [0.002, 0.034, workshopLayout.length - 0.009], [-0.3128, 0.73, 0], plyEdge, 0.0007);
  for (const x of [-0.278, 0.281])
    for (const z of [-0.662, 0.662]) {
      box(unit, [0.043, 0.707, 0.045], [x, 0.361, z], p.woodVertical, 0.002);
      box(unit, [0.044, 0.008, 0.046], [x, 0.009, z], p.rubber, 0.001);
      tube(unit, [x - 0.023, 0.669, z], [x - 0.021, 0.669, z], 0.0055, p.steel);
    }
  box(unit, [0.041, 0.117, 1.38], [0.282, 0.647, 0], p.woodDark, 0.002);
  for (const z of [-0.633, 0.633]) box(unit, [0.53, 0.075, 0.027], [0, 0.683, z], p.wood, 0.002);
  const mat = p.rubber.clone();
  mat.color.set('#243d37');
  box(unit, [0.391, 0.004, 0.585], [-0.05, 0.754, 0.13], mat, 0.002).name =
    'Self-healing cutting mat';
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
  const pliers = group(unit, 'KNIPEX Electronic Super Knips', [0.263, 1.3392, 0.0388]);
  cable(
    unit,
    [
      [0.287, 1.342, 0.0388],
      [0.281, 1.3362, 0.0388],
      [0.275, 1.3262, 0.0388],
      [0.253, 1.3262, 0.0388],
      [0.249, 1.3302, 0.0388],
      [0.249, 1.3332, 0.0388],
    ],
    0.0023,
    p.steel,
  );
  const tray = group(unit, 'Twelve-switch sampler', [-0.081, 0.757, 0.198]);
  const taskLamp = workbenchFixture(
    unit,
    p,
    [0.065, 0.75, workshopLayout.length / 2 - 0.066],
    loader,
  );
  taskLamp.unit.name = 'Workbench lamp';
  taskLamp.unit.rotation.y = 1.92;
  taskLamp.emitter.emissiveIntensity = 0.52;
  const stool = group(root, 'Artek Stool 60', [1.61, parquetSurfaceY, workshopLayout.z]);
  deferRoomDetail(() => loadDisplayModel(stool, '/media/models/artek-stool-60.glb', detailManager));
  const electronics = group(unit, 'Electronics work mat', [-0.035, 0.7565, -0.012]);
  electronics.rotation.y = -Math.PI / 2;
  const meter = group(electronics, 'Fluke 115 on tilt stand', [-0.083, 0.005608, -0.042]);
  meter.rotation.x = -0.41568;
  const meterCenter = new T.Vector3(0, 0.0835, -0.012);
  meter.position.add(meterCenter.clone().applyQuaternion(meter.quaternion));
  const prepareTools = perforatedToolWall(unit, p, () =>
    loadDisplayModel(unit, '/media/models/bench-instruments.glb', createStudioLoadingManager(), {
      mounted(scene) {
        for (const instrument of [...scene.children]) {
          switch (instrument.userData.benchInstrument) {
            case 'cutters':
              instrument.rotation.y = -Math.PI / 2;
              pliers.add(instrument);
              break;
            case 'tester':
              tray.add(instrument);
              break;
            case 'meter':
              instrument.position.sub(meterCenter);
              meter.add(instrument);
              break;
          }
        }
        scene.removeFromParent();
      },
    }),
  );
  return {
    unit,
    top,
    tray,
    taskLamp,
    boardLight,
    stool,
    pliers,
    meter,
    electronics,
    cabinet,
    prepareTools,
  };
}
