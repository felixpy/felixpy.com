import * as T from 'three';
import { box, cable, canvasTexture, group, surface, tube } from './geometry';
import { loadStudioTexture } from './ktx2-loader';
import type { Palette } from './materials';

type Dimensions = { left: number; right: number; front: number; back: number; top: number };

function oakWorktop(
  bench: T.Group,
  loader: T.TextureLoader,
  { left, right, front, back, top }: Dimensions,
) {
  const maps = ['color', 'normal', 'roughness'].map((channel) =>
    loadStudioTexture(loader, `/media/materials/desk-oak-${channel}.webp`, {
      srgb: channel === 'color',
      wrap: T.RepeatWrapping,
      anisotropy: 8,
    }),
  );
  const oak = new T.MeshStandardMaterial({
    map: maps[0],
    normalMap: maps[1],
    roughnessMap: maps[2],
    roughness: 0.88,
    normalScale: new T.Vector2(0.37, 0.37),
    userData: { studioMatte: true },
  });
  oak.name = 'White-oiled oak · long grain';
  const thickness = 0.038,
    depth = front - back;
  const slab = box(
    bench,
    [right - left, thickness, depth],
    [(left + right) / 2, top - thickness / 2, (front + back) / 2],
    oak,
    0.0035,
  );
  slab.name = 'Solid oak writing surface';
  slab.geometry = slab.geometry.clone();
  const grain = slab.geometry.attributes;
  for (let i = 0; i < grain.position.count; i++) {
    const x = grain.position.getX(i),
      y = grain.position.getY(i),
      z = grain.position.getZ(i);
    const transverse =
      Math.abs(grain.normal.getY(i)) > 0.5 ? z : z + Math.sign(z) * (thickness / 2 - y);
    grain.uv.setXY(i, 0.49 - transverse / 1.8, 0.37 + x / 1.8);
  }
  const end = oak.clone();
  end.name = 'White-oiled oak · end grain';
  end.map = canvasTexture(768, 80, (ctx) => {
    const image = ctx.createImageData(768, 80);
    for (let y = 0; y < 80; y++)
      for (let x = 0; x < 768; x++) {
        const board = Math.floor(x / 86),
          along = (x % 86) - 32 + 14 * Math.sin(board * 4.1);
        const radial = Math.hypot(along * 0.74, 77 + 13 * Math.cos(board * 5.3) + y * 0.37);
        const band = (0.5 + 0.5 * Math.cos(radial * 1.48 + 0.45 * Math.sin(along * 0.078))) ** 7;
        const shade = 5 * Math.cos(board * 1.4) - 14 * band + 2 * Math.sin(x * 47.2 + y * 96.3);
        image.data.set([181 + shade, 154 + shade, 122 + shade, 255], (y * 768 + x) * 4);
      }
    ctx.putImageData(image, 0, 0);
  });
  end.normalMap = null;
  end.roughnessMap = null;
  end.roughness = 0.69;
  slab.material = [end, end, oak, oak, oak, oak];
  for (const face of slab.geometry.groups.slice(0, 2))
    for (let i = face.start; i < face.start + face.count; i++) {
      grain.uv.setXY(
        i,
        0.5 + grain.position.getZ(i) / depth,
        0.5 + grain.position.getY(i) / thickness,
      );
    }
}

function cabinetFinish(p: Palette) {
  const melamine = surface('#e8e7e1', 0.73);
  melamine.name = 'EGGER W980 ST7 Platinum White · fine pearl';
  melamine.normalMap = p.black.normalMap;
  melamine.normalScale.set(0.22, 0.22);
  const abs = surface('#e4e3dd', 0.55);
  abs.name = 'W980 matched ABS lipping';
  return { melamine, abs, plinth: surface('#b4b2a8', 0.73), inner: surface('#d9d8d0', 0.76) };
}

function pedestal(
  root: T.Group,
  p: Palette,
  finish: ReturnType<typeof cabinetFinish>,
  x: number,
  side: number,
) {
  const housing = group(root, 'White-board filing pedestal', [x, 0, 0.105]);
  const { melamine, abs, inner } = finish;
  box(housing, [0.383, 0.063, 0.516], [0, 0.0315, -0.036], finish.plinth, 0.001);
  for (const y of [0.074, 0.691]) {
    box(housing, [0.426, 0.024, 0.607], [0, y, -0.0285], melamine, 0.00065);
    box(housing, [0.426, 0.024, 0.001], [0, y, 0.2755], abs, 0.00044);
  }
  for (const x of [-0.202, 0.202]) {
    box(housing, [0.022, 0.593, 0.607], [x, 0.3825, -0.0285], melamine, 0.0006);
    box(housing, [0.022, 0.593, 0.001], [x, 0.3825, 0.2755], abs, 0.00044);
    box(housing, [0.018, 0.009, 0.46], [x, 0.7075, -0.045], p.graphite, 0.0007);
  }
  box(housing, [0.382, 0.593, 0.011], [0, 0.3825, -0.325], inner);
  const drawers = [0, 1, 2].map((index) => {
    const tray = group(housing, 'Drawer ' + (side * 3 + index + 1), [
      0,
      0.578 - index * 0.197,
      0.257,
    ]);
    box(tray, [0.377, 0.193, 0.0206], [0, 0, 0.007], abs, 0.00095);
    box(tray, [0.375, 0.191, 0.0003], [0, 0, 0.01745], melamine, 0.00012);
    const interior = group(tray, 'Drawer interior');
    interior.visible = false;
    box(interior, [0.358, 0.011, 0.465], [0, -0.078, -0.234], inner, 0.001);
    for (const edge of [-1, 1]) {
      box(interior, [0.012, 0.122, 0.47], [edge * 0.174, -0.021, -0.237], inner, 0.0008);
      box(interior, [0.006, 0.018, 0.407], [edge * 0.182, -0.041, -0.247], p.steel, 0.001);
      tube(tray, [edge * 0.049, 0.029, 0.017], [edge * 0.049, 0.029, 0.023], 0.007, p.bronze);
    }
    box(interior, [0.349, 0.122, 0.012], [0, -0.021, -0.469], inner, 0.0008);
    cable(
      tray,
      [
        [-0.049, 0.029, 0.021],
        [-0.049, 0.029, 0.037],
        [-0.041, 0.029, 0.042],
        [0, 0.029, 0.042],
        [0.041, 0.029, 0.042],
        [0.049, 0.029, 0.037],
        [0.049, 0.029, 0.021],
      ],
      0.0037,
      p.bronze,
    );
    return { tray, interior };
  });
  return drawers;
}

export function writingDesk(
  root: T.Group,
  p: Palette,
  loader: T.TextureLoader,
  dimensions: Dimensions,
) {
  const bench = group(root, 'Joiner-built writing desk');
  const { left, right, back } = dimensions;
  const width = right - left;
  const x = (left + right) / 2;
  oakWorktop(bench, loader, dimensions);
  box(bench, [width - 0.16, 0.065, 0.025], [x, 0.679, back + 0.103], p.graphite, 0.003);
  const finish = cabinetFinish(p);
  const trays = [
    ...pedestal(bench, p, finish, left + 0.266, 0),
    ...pedestal(bench, p, finish, right - 0.251, 1),
  ];
  const drawers = trays.map(({ tray }) => tray);
  const drawerInteriors = trays.map(({ interior }) => interior);
  const tray = drawerInteriors[3];
  const felt = p.cloth.clone();
  felt.color.set('#6b786b');
  box(tray, [0.337, 0.004, 0.443], [0, -0.07, -0.234], felt, 0.0016);
  box(tray, [0.007, 0.047, 0.438], [0.042, -0.047, -0.234], p.wood, 0.0016);
  const drive = group(tray, 'Portable SSD', [-0.052, -0.06394, -0.182]);
  drive.rotation.y = -0.13;
  return { drawers, drawerInteriors, drive };
}
