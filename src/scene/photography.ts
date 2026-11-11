import * as T from 'three';
import {
  beam,
  box,
  canvasTexture,
  group,
  mesh,
  paperGeometry,
  print,
  random,
  surface,
  tube,
  type XYZ,
} from './geometry';
import type { Palette } from './materials';
import type { Locale } from '../app/locale';
import { printGreeting, travelPrints } from '../content/travel';

export function photoTile(atlas: T.Texture, index: number) {
  const tile = atlas.clone();
  tile.repeat.set(1 / 3, 1 / 2);
  tile.offset.set((index % 3) / 3, Math.floor(index / 3) === 0 ? 0.5 : 0);
  return tile;
}

export function photoPrinter(parent: T.Group, p: Palette, sample: T.Texture, position: XYZ) {
  const printer = group(parent, 'Compact photo printer', position);
  printer.rotation.y = -Math.PI / 2;
  const shell = p.black.clone();
  shell.color.set('#c4bfb0');
  shell.roughness = 0.66;
  box(printer, [0.325, 0.062, 0.211], [0, -0.0115, 0], shell, 0.01);
  box(printer, [0.321, 0.0025, 0.207], [0, 0.0195, 0], p.graphite, 0.001);
  box(printer, [0.325, 0.022, 0.211], [0, 0.0315, 0], shell, 0.006);
  box(printer, [0.292, 0.006, 0.183], [0, 0.041, -0.004], p.graphite, 0.004);
  box(printer, [0.25, 0.016, 0.007], [0, -0.009, 0.105], p.black, 0.002);
  box(printer, [0.219, 0.007, 0.141], [0, -0.029, 0.161], p.graphite, 0.002);
  for (const x of [-0.092, 0.092])
    box(printer, [0.004, 0.004, 0.114], [x, -0.024, 0.165], p.black, 0.001);
  for (const x of [-0.082, 0.082])
    tube(printer, [x - 0.013, -0.01, 0.109], [x + 0.013, -0.01, 0.109], 0.005, p.rubber);
  const output = group(printer, 'Partially ejected sample print', [0, -0.017, 0.153]);
  output.rotation.x = -Math.PI / 2 + 0.09;
  const paper = paperGeometry(0.104, 0.094);
  mesh(output, paper, p.paper);
  print(
    output,
    0.104,
    0.094,
    [0, 0.0015, 0.00035],
    sample,
    paperGeometry(0.104, 0.094, 0.91, 0.0015),
  ).castShadow = false;
  const vent = group(printer, 'Shell ventilation and feet');
  for (let i = 0; i < 12; i++)
    box(vent, [0.007, 0.002, 0.004], [-0.078 + i * 0.014, 0.006, -0.105], p.black, 0.0005);
  for (const x of [-0.133, 0.133])
    for (const z of [-0.074, 0.074]) {
      box(printer, [0.028, 0.005, 0.024], [x, -0.041, z], p.rubber, 0.0025);
    }
  tube(printer, [0.119, 0.04, 0.042], [0.119, 0.046, 0.042], 0.008, p.steel);
  box(printer, [0.031, 0.0023, 0.015], [0.119, 0.044, 0.012], p.black, 0.0012);
  box(printer, [0.019, 0.00045, 0.0026], [0.119, 0.0454, 0.015], surface('#78938a', 0.68), 0.0002);
  return output;
}

export function deskPhotoFrame(parent: T.Group, p: Palette, image: T.Texture) {
  const frame = group(parent, 'Desk portrait', [-0.974, 0.834, 0.167]);
  frame.rotation.set(-0.13, 0.18, 0);
  const width = 0.105,
    height = 0.14;
  box(frame, [0.129, 0.166, 0.012], [0, 0, 0], p.woodVertical, 0.0024);
  box(frame, [0.118, 0.155, 0.002], [0, 0, 0.0062], p.paper, 0.0006);
  print(frame, width, height, [0, 0, 0.0075], image).castShadow = false;
  mesh(
    frame,
    new T.PlaneGeometry(0.115, 0.152),
    new T.MeshPhysicalMaterial({
      color: '#e8dbc3',
      roughness: 0.16,
      metalness: 0.12,
      transparent: true,
      opacity: 0.079,
      depthWrite: false,
    }),
    [0, 0, 0.008],
  ).castShadow = false;
  beam(frame, [0, -0.012, -0.0065], [0, -0.081, -0.045], 0.021, 0.003, p.woodDark);
  return frame;
}

export function landmarkPrint(
  parent: T.Object3D,
  p: Palette,
  image: T.Texture,
  index: number,
  width: number,
  pos: XYZ,
) {
  const height = (width * 4) / 3;
  const place = travelPrints[index];
  const card = group(parent, place.zh, pos);
  mesh(card, paperGeometry(width, height), p.paper);
  print(
    card,
    width,
    height,
    [0, 0.002, 0.00065],
    image,
    paperGeometry(width, height, 0.91, 0.002),
  ).castShadow = false;
  function writeIndex(ctx: CanvasRenderingContext2D, locale: Locale) {
    ctx.clearRect(0, 0, 480, 60);
    ctx.fillStyle = '#625a4e';
    ctx.font = '500 26px "IBM Plex Sans", "Studio Han", sans-serif';
    ctx.fillText(
      String(index + 1).padStart(2, '0') + '   /   ' + place[locale].split(' · ')[0],
      8,
      39,
      464,
    );
  }
  const indexMark = canvasTexture(480, 60, (ctx) => writeIndex(ctx, 'en'));
  mesh(
    card,
    new T.PlaneGeometry(width * 0.67, height * 0.045),
    new T.MeshBasicMaterial({
      map: indexMark,
      transparent: true,
      depthWrite: false,
    }),
    [-width * 0.115, -height * 0.473, 0.0014],
  ).castShadow = false;
  function writeNote(ctx: CanvasRenderingContext2D, locale: Locale) {
    ctx.fillStyle = '#dcd0b6';
    ctx.fillRect(0, 0, 576, 768);
    const rng = random(921 + index);
    for (let i = 0; i < 4200; i++) {
      ctx.fillStyle = i % 2 ? '#efe7d317' : '#9a815b0d';
      ctx.fillRect(rng() * 576, rng() * 768, 0.8, 1.1);
    }
    const age = ctx.createLinearGradient(0, 767, 520, 270);
    age.addColorStop(0, '#9c7c5028');
    age.addColorStop(0.46, '#9c7c5000');
    ctx.fillStyle = age;
    ctx.fillRect(0, 0, 576, 768);
    ctx.fillStyle = '#3d494c';
    ctx.font =
      locale === 'zh' ? '400 36px "Studio Script", KaiTi, serif' : '500 43px Caveat, cursive';
    ctx.save();
    ctx.translate(40, 236);
    ctx.rotate(-0.029);
    ctx.fillText(printGreeting[locale], 0, 0, 496);
    place.note[locale]
      .split('\n')
      .forEach((line, row) => ctx.fillText(line, row * 4, 105 + row * 65, 496));
    ctx.restore();
    ctx.font = '500 36px Caveat, cursive';
    ctx.fillText('— Felix', 390, 507);
  }
  const note = canvasTexture(576, 768, (ctx) => writeNote(ctx, 'en'));
  const verso = print(
    card,
    width,
    height,
    [0, 0, -0.00065],
    note,
    paperGeometry(width, height, 1, 0, true),
  );
  verso.rotation.y = Math.PI;
  verso.castShadow = false;
  return {
    card,
    setLocale(locale: Locale) {
      writeIndex(indexMark.image.getContext('2d')!, locale);
      writeNote(note.image.getContext('2d')!, locale);
      indexMark.needsUpdate = note.needsUpdate = true;
    },
  };
}
