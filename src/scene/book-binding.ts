import * as T from 'three';
import { rearLayouts } from '../content/book-rear-layouts';
import type { BookEdition } from '../content/books';
import { canvasTexture, mesh, random } from './geometry';
import { blenderMesh } from './blender-mesh';
import { drawEditionBack, printedBars } from './book-back-print';

export type PaintCover = (
  texture: T.Texture<HTMLImageElement>,
  tile?: { x: number; y: number; width: number; height: number },
) => void;

type CoverLoader = { load: (url: string, paint: PaintCover) => void };

function backUsesCover(key: string) {
  return key === 'frankenstein' || key === 'ways' || key === 'moby' || key === 'walden';
}

function seedOf(text: string) {
  return Array.from(text).reduce((seed, ch) => Math.imul(seed, 31) + ch.charCodeAt(0), 17) >>> 0;
}

function scuff(ctx: CanvasRenderingContext2D, w: number, h: number, age: number, seed: number) {
  const rng = random(seed);
  for (let i = 0; i < 245 * age; i++) {
    const top = rng() < 0.5;
    const outer = rng() < 0.58;
    const across = rng() ** 2;
    const x = (outer ? 1 - across : across) * w;
    const y = (top ? 0 : h) + (top ? 1 : -1) * rng() ** 2 * h * 0.009;
    ctx.fillStyle = `rgba(224,212,180,${(0.16 + rng() * 0.5) * age})`;
    ctx.fillRect(x, y, 0.5 + rng() ** 2 * w * 0.025, 0.5 + rng() * h * 0.0026);
  }
  for (let i = 0; i < 4; i++) {
    const x = i % 2 ? w : 0,
      y = i < 2 ? 0 : h;
    const radius = Math.max(1, Math.min(w, h) * (0.008 + 0.026 * rng()) * age);
    const rub = ctx.createRadialGradient(x, y, 0, x, y, radius);
    rub.addColorStop(0, `rgba(224,213,186,${age * 0.82})`);
    rub.addColorStop(0.4, `rgba(226,213,186,${age * 0.32})`);
    rub.addColorStop(1, 'rgba(226,213,186,0)');
    ctx.fillStyle = rub;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }
}

function applyFrontDetail(
  key: string,
  wrapper: T.CanvasTexture,
  master: HTMLImageElement | HTMLCanvasElement,
) {
  if (!backUsesCover(key)) return;
  const sheet = wrapper.image as HTMLCanvasElement;
  const rear = sheet.getContext('2d')!;
  rear.save();
  rear.setTransform(sheet.width / 384, 0, 0, sheet.height / 512, 0, 0);
  if (key === 'walden') {
    const w = master.width / 457,
      h = master.height / 700;
    rear.drawImage(master, 54 * w, 459 * h, 349 * w, 35 * h, 39, 335, 210, 25);
    rear.drawImage(master, 215 * w, 459 * h, 27 * w, 34 * h, 310.5, 334.8, 51, 26.4);
    rear.filter = 'grayscale(1) contrast(450%) brightness(140%)';
    rear.globalCompositeOperation = 'multiply';
    rear.drawImage(master, 219.5 * w, 463 * h, 18 * w, 25 * h, 253.5, 456, 9, 24);
    rear.filter = 'none';
    rear.strokeStyle = '#302e29';
    rear.lineWidth = 0.9;
    rear.beginPath();
    rear.ellipse(258, 468, 7.2, 15, 0, 0, 2 * Math.PI);
    rear.stroke();
  } else if (key === 'moby') {
    const w = master.width,
      h = master.height;
    rear.fillStyle = '#faf9f4';
    rear.fillRect(0, 328, 384, 43);
    rear.drawImage(master, w * 0.145, h * 0.66, w * 0.71, h * 0.068, 42, 333, 204, 33);
    rear.drawImage(master, w * 0.466, h * 0.66, w * 0.067, h * 0.068, 321, 334, 30, 31);
    rear.drawImage(master, w * 0.466, h * 0.66, w * 0.067, h * 0.068, 227, 448, 9, 16);
  } else if (key === 'ways') {
    rear.beginPath();
    rear.ellipse(25.5, 444, 10.5, 17, 0, 0, Math.PI * 2);
    rear.clip();
    rear.drawImage(
      master,
      master.width * 0.475,
      master.height * 0.013,
      master.width * 0.074,
      master.height * 0.072,
      15,
      427,
      21,
      34,
    );
  } else {
    rear.drawImage(master, 0, 0, master.width, master.height * 0.67, 13, 451, 59, 46);
  }
  rear.restore();
  wrapper.needsUpdate = true;
}

function frontPrint(
  loader: CoverLoader,
  book: BookEdition,
  age: number,
  seed: number,
  wrapper: T.CanvasTexture,
) {
  const material = new T.MeshStandardMaterial({
    map: new T.Texture(),
    roughness: book.jacket ? 0.61 : 0.72,
  });
  loader.load('/media/books/' + book.key + '.webp', (texture, tile) => {
    const master = texture.image;
    const canvas = document.createElement('canvas');
    const w = (canvas.width = tile?.width ?? master.width),
      h = (canvas.height = tile?.height ?? master.height);
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(master, tile?.x ?? 0, tile?.y ?? 0, w, h, 0, 0, w, h);
    applyFrontDetail(book.key, wrapper, canvas);
    const hinge = w * (book.binding === 'board' ? 0.037 : 0.026);
    const fold = ctx.createLinearGradient(hinge - 3, 0, hinge + 3, 0);
    fold.addColorStop(0, 'rgba(10,8,6,0)');
    fold.addColorStop(0.48, `rgba(20,15,10,${0.09 + age * 0.13})`);
    fold.addColorStop(0.75, `rgba(246,228,194,${age * 0.19})`);
    fold.addColorStop(1, 'rgba(255,252,239,0)');
    ctx.fillStyle = fold;
    ctx.fillRect(hinge - 3, 0, 6, h);
    scuff(ctx, w, h, age, seed + 1);
    if (age > 0.64 && book.binding === 'paper') {
      const size = h * (0.055 + age * 0.037);
      ctx.beginPath();
      ctx.moveTo(w - size * 0.8, h - 0.5);
      ctx.quadraticCurveTo(w - size * 0.38, h - size * 0.48, w - 0.5, h - size);
      ctx.strokeStyle = 'rgba(40,32,23,0.24)';
      ctx.lineWidth = Math.max(0.65, h * 0.00125);
      ctx.stroke();
      ctx.translate(1.2, 1.2);
      ctx.strokeStyle = 'rgba(235,224,195,0.37)';
      ctx.stroke();
    }
    const map = new T.CanvasTexture(canvas);
    map.colorSpace = T.SRGBColorSpace;
    map.anisotropy = 8;
    material.map?.dispose();
    material.map = map;
    if (!tile) texture.dispose();
  });
  return material;
}

function barcode(ctx: CanvasRenderingContext2D, isbn: string) {
  if (!/^978\d{10}$/.test(isbn)) return;
  ctx.fillStyle = '#efece1';
  ctx.fillRect(156, 435, 115, 63);
  ctx.fillStyle = '#272624';
  printedBars(ctx, isbn, 165, 448, 95, 34);
  ctx.font = '8px monospace';
  ctx.fillText('ISBN ' + isbn, 165, 445);
  ctx.font = '10px monospace';
  ctx.fillText(isbn[0] + ' ' + isbn.slice(1, 7) + ' ' + isbn.slice(7), 164, 493);
}

function faulknerJacket(ctx: CanvasRenderingContext2D) {
  ctx.fillStyle = '#ddd3bb';
  ctx.fillRect(0, 0, 288, 512);
  ctx.fillStyle = '#332e27';
  ctx.textAlign = 'center';
  ctx.font = '18px Georgia,serif';
  ctx.fillText('Modern Books of Interest and Merit', 144, 29, 268);
  ctx.fillRect(11, 35, 266, 1);
  ctx.fillRect(141, 43, 0.8, 251);
  const lists = [
    [
      ['Evelyn Scott', 'The Wave'],
      ['Helen Grace Carlisle', 'See How They Run'],
      ['D. H. Lawrence', 'Collected Poems'],
      ['E. de Gramont', 'Pomp and Circumstance'],
      ['Radclyffe Hall', 'The Unlit Lamp'],
      ['Radclyffe Hall', 'Adam’s Breed'],
      ['W. H. Davies', 'Collected Poems'],
      ['Ralph Rashleigh', 'Adventures of an Outlaw'],
      ['Eugene Löhrke', 'Overshadowed'],
      ['E. Westermarck', 'Marriage'],
      ['Malcolm Cowley', 'Blue Juniata'],
    ],
    [
      ['Norman Douglas', 'Birds and Beasts of the Greek Anthology'],
      ['Anonymous', 'Ex-Wife'],
      ['Floyd Gibbons', 'The Red Napoleon'],
      ['Ward Greene', 'Cora Potts'],
      ['Horace Wyndham', 'Criminology'],
      ['Elizabeth Manning', 'Lot Houses'],
      ['William Faulkner', 'The Sound and the Fury'],
      ['Wilhelm Speyer', 'Galahads and Pussy-Cats'],
      ['Pearl Adam', 'Kitchen Ranging'],
    ],
  ];
  ctx.textAlign = 'left';
  for (const [col, entries] of lists.entries()) {
    for (const [i, [author, title]] of entries.entries()) {
      const x = 12 + col * 139,
        y = 49 + i * (240 / (entries.length - 1));
      ctx.font = '7px Georgia,serif';
      ctx.fillText(author.toUpperCase(), x, y, 121);
      ctx.strokeStyle = '#332e27';
      ctx.strokeRect(x, y + 3, 4.6, 4.6);
      ctx.font = 'bold 8px Georgia,serif';
      ctx.fillText(title.toUpperCase(), x + 7, y + 8.5, 115);
    }
  }
  ctx.textAlign = 'center';
  ctx.font = 'bold 14px Georgia,serif';
  ctx.fillText('NEW PUBLICATIONS', 144, 320);
  ctx.fillRect(74, 324, 140, 0.8);
  ctx.textAlign = 'left';
  const titles = [
    'WHEN MAMMOTHS ROAMED THE FROZEN EARTH',
    'HUMANITY UPROOTED.    $3.00',
    'FRANÇOIS RABELAIS',
    'THE ROBBER BAND',
    'BOX OFFICE',
    'A NOVEL IN WOOD-CUTS',
    'FORTY-NINE POEMS',
  ];
  for (const [i, title] of titles.entries()) {
    const y = 340 + i * 11.7;
    ctx.strokeRect(13, y - 5, 5, 5);
    ctx.font = 'bold 8px Georgia,serif';
    ctx.fillText(title, 22, y, 247);
  }
  ctx.font = '8px Georgia,serif';
  ctx.fillText('Jonathan Cape & Harrison Smith, Publishers', 18, 435);
  for (const [i, name] of ['Name', 'Street', 'City'].entries()) {
    ctx.fillText(name + '    ' + '· '.repeat(60), 12, 456 + i * 17, 263);
  }
  ctx.fillStyle = '#a79b86';
  ctx.fillRect(288, 0, 96, 512);
  ctx.fillStyle = '#9f4738';
  ctx.fillRect(288, 17, 96, 151);
  ctx.textAlign = 'center';
  ctx.fillStyle = '#eee4cf';
  ctx.font = '18px Georgia,serif';
  ['THE SOUND', 'AND THE', 'FURY'].forEach((s, i) => ctx.fillText(s, 336, 49 + i * 24, 85));
  ctx.font = '10px Georgia,serif';
  ctx.fillText('WILLIAM FAULKNER', 336, 145, 86);
  ctx.fillStyle = '#302e2b';
  ctx.fillText('JONATHAN CAPE', 336, 472, 85);
  ctx.fillText('HARRISON SMITH', 336, 485, 85);
  ctx.textAlign = 'left';
}

function knuthSpine(ctx: CanvasRenderingContext2D, book: BookEdition) {
  const volume = Number(book.key.slice(-1));
  const ink = ['#292a36', '#783a35', '#bc7024'][volume - 1];
  ctx.fillStyle = '#dfcea8';
  ctx.fillRect(288, 0, 96, 512);
  ctx.textAlign = 'center';
  ctx.fillStyle = ink;
  ctx.fillRect(301, 10, 70, 30);
  ctx.fillRect(301, 401, 70, 54);
  ctx.fillStyle = '#f1e2bb';
  ctx.font = '9px Georgia,serif';
  ctx.fillText(volume === 3 ? 'SECOND' : 'THIRD', 336, 23);
  ctx.fillText('EDITION', 336, 33);
  ctx.font = '22px Georgia,serif';
  ctx.fillText(String(volume), 336, 437);
  ctx.fillStyle = ink;
  ctx.font = '19px Georgia,serif';
  ctx.fillText('KNUTH', 336, 69);
  ctx.save();
  ctx.translate(336, 232);
  ctx.rotate(Math.PI / 2);
  ctx.fillStyle = '#292725';
  ctx.font = 'bold 26px Georgia,serif';
  ctx.fillText('The Art of Computer Programming', 0, -3, 294);
  ctx.fillStyle = ink;
  ctx.font = '17px Georgia,serif';
  ctx.fillText(book.en.split(': ')[1], 0, 20, 265);
  ctx.restore();
  ctx.font = '11px Georgia,serif';
  ctx.fillText('Addison-Wesley', 336, 487, 80);
  ctx.textAlign = 'left';
}

function paintBinding(
  ctx: CanvasRenderingContext2D,
  book: BookEdition,
  age: number,
  seed: number,
  resolution: number,
  includeParagraphs: boolean,
) {
  const rng = random(seed);
  ctx.scale(resolution, resolution);
  ctx.fillStyle = book.cloth;
  ctx.fillRect(0, 0, 384, 512);
  const fade = ctx.createLinearGradient(0, 0, 0, 512);
  fade.addColorStop(0, `rgba(226,207,170,${0.04 + age * 0.25})`);
  fade.addColorStop(0.63, `rgba(218,199,168,${age * 0.08})`);
  fade.addColorStop(1, 'rgba(12,10,9,0.05)');
  ctx.fillStyle = fade;
  ctx.fillRect(288, 0, 96, 512);
  if (book.binding === 'board') {
    for (let i = 0; i < 512; i += 2) {
      ctx.fillStyle = `rgba(38,30,24,${rng() * 0.044})`;
      ctx.fillRect(0, i, 384, 0.6);
    }
    for (let i = 0; i < 384; i += 2) {
      ctx.fillStyle = `rgba(248,242,220,${rng() * 0.05})`;
      ctx.fillRect(i, 0, 0.7, 512);
    }
  }
  ctx.fillStyle = book.ink;
  ctx.font = '600 12px Arial,sans-serif';
  ctx.fillText(book.imprint.toUpperCase(), 20, 47, 243);
  ctx.fillRect(20, 62, 60, 1);
  ctx.font = '16px Georgia,serif';
  ctx.fillText(book.author, 20, 94, 241);
  barcode(ctx, book.identifier);
  ctx.save();
  ctx.beginPath();
  ctx.rect(288, 0, 96, 512);
  ctx.clip();
  const tech = /Press|Pearson|Addison|Prentice|O’Reilly/.test(book.imprint);
  if (book.imprint === 'Penguin Classics') {
    ctx.fillStyle = '#e6ddc6';
    ctx.fillRect(288, 0, 96, 52);
    ctx.font = '600 11px Georgia,serif';
    ctx.fillStyle = '#343028';
    ctx.fillText('PENGUIN', 305, 24);
    ctx.fillText('CLASSICS', 304, 39);
  } else if (book.imprint === 'O’Reilly' || book.key.startsWith('taocp-')) {
    ctx.fillStyle = book.ink;
    ctx.fillRect(291, 9, 89, 4);
    ctx.fillRect(291, 487, 89, 3);
  }
  ctx.fillStyle = book.ink;
  ctx.translate(336, 0);
  ctx.rotate(Math.PI / 2);
  const long = book.en.length > 27;
  const offset = book.imprint === 'Penguin Classics' ? 66 : 18;
  ctx.font = `600 ${long ? 31 : 43}px ${tech ? 'Arial,sans-serif' : 'Georgia,serif'}`;
  ctx.fillText(book.en, offset, book.size[2] < 0.018 ? 2 : -2, 407 - offset);
  ctx.font = `500 ${book.size[2] < 0.018 ? 15 : 17}px Arial,sans-serif`;
  ctx.fillText(book.author.split(' · ')[0], offset + 1, 23, 367 - offset);
  ctx.textAlign = 'right';
  ctx.font = '600 15px Arial,sans-serif';
  ctx.fillText(book.imprint, 498, 4, 83);
  ctx.restore();
  if (book.key.startsWith('taocp-')) knuthSpine(ctx, book);
  if (book.key === 'sound-and-fury') faulknerJacket(ctx);
  drawEditionBack(ctx, book, includeParagraphs);
  for (let i = 0; i < 2 + Math.floor(age * 5); i++) {
    const x = 290 + rng() ** 2 * 91,
      hi = 24 + rng() * 80,
      lo = 450 + rng() * 55;
    ctx.strokeStyle = `rgba(226,211,177,${age * (0.1 + rng() * 0.21)})`;
    ctx.lineWidth = 0.45 + rng();
    ctx.beginPath();
    ctx.moveTo(x, hi);
    ctx.bezierCurveTo(x - 1.2, 180, x + 1.4, 358, x + 0.4, lo);
    ctx.stroke();
  }
  scuff(ctx, 384, 512, age, seed + 52);
  ctx.fillStyle = book.binding === 'board' ? '#ac987b' : '#d9ccb2';
  ctx.fillRect(0, 0, 3, 3);
}

function bindingPrint(
  book: BookEdition,
  age: number,
  seed: number,
  resolution: number,
  includeParagraphs = true,
) {
  return canvasTexture(384 * resolution, 512 * resolution, (ctx) => {
    paintBinding(ctx, book, age, seed, resolution, includeParagraphs);
  });
}

const forms = new Map<string, T.BufferGeometry>();

function form(kind: string, surface: string) {
  const name = 'bindings/' + kind + '-' + surface;
  let geometry = forms.get(name);
  if (!geometry) {
    geometry = blenderMesh(name);
    forms.set(name, geometry);
  }
  return geometry;
}

export function pageStocks() {
  const papers = new Map<string, T.MeshStandardMaterial>();
  const maps = new Map<string, T.CanvasTexture>();
  return (book: BookEdition, age: number) => {
    const stock = Math.min(6, Math.floor(age * 7));
    const topstain = book.key === 'sound-and-fury';
    const key = stock + (topstain ? '-topstain' : '');
    let base = maps.get(key);
    if (!base) {
      const rng = random(428 + stock * 13);
      base = canvasTexture(512, 128, (ctx) => {
        ctx.fillStyle = `rgb(${240 - 2 * stock},${235 - 3 * stock},${221 - 4 * stock})`;
        ctx.fillRect(0, 0, 512, 128);
        for (let gathering = 0; gathering < 4; gathering++) {
          const x = gathering * 128;
          const tint = ctx.createLinearGradient(x, 0, x + 128, 0);
          tint.addColorStop(0, 'rgba(89,67,43,.28)');
          tint.addColorStop(0.06, 'rgba(121,95,65,.11)');
          tint.addColorStop(0.62, 'rgba(171,144,99,.02)');
          tint.addColorStop(1, 'rgba(253,247,229,.33)');
          ctx.fillStyle = tint;
          ctx.fillRect(x, 45, 128, 83);
        }
        for (let leaf = 0; leaf < 64; leaf++) {
          const x = leaf * 8;
          ctx.fillStyle = `rgba(104,81,53,${leaf % 8 ? 0.1 + rng() * 0.18 : 0.34})`;
          ctx.fillRect(x, 45, 1.2 + rng() * 1.9, 82);
        }
        if (topstain) {
          ctx.fillStyle = 'rgba(56,61,68,.87)';
          ctx.fillRect(0, 46, 512, 23);
        }
        ctx.fillStyle = 'rgba(187,169,134,.22)';
        ctx.fillRect(0, 24, 512, 12);
        if (topstain) {
          ctx.fillStyle = '#57564c';
          for (let x = 0; x < 512; x += 16) {
            ctx.beginPath();
            ctx.moveTo(x, 26);
            ctx.quadraticCurveTo(x + 4, 30, x + 8, 27);
            ctx.lineTo(x + 8, 32);
            ctx.quadraticCurveTo(x + 4, 34, x, 31);
            ctx.fill();
          }
        }
        for (let x = 0; x < 512; x += 8) {
          ctx.fillStyle = x % 16 ? '#d1b496' : '#837263';
          ctx.fillRect(x, 5, 8, 12);
        }
      });
      base.wrapS = T.RepeatWrapping;
      maps.set(key, base);
    }
    const id = key + '-' + book.pages;
    let material = papers.get(id);
    if (!material) {
      const map = base.clone();
      map.repeat.x = Math.ceil(book.pages / 2) / 64;
      map.needsUpdate = true;
      material = new T.MeshStandardMaterial({ map, roughness: 0.94 });
      papers.set(id, material);
    }
    return material;
  };
}

function printWear(book: BookEdition) {
  const seed = seedOf(book.key);
  const age = 0.14 + random(seed)() * 0.46 + Math.min(0.32, (2026 - book.year) * 0.004);
  return { age, seed };
}

export function enableClosePrint(unit: T.Group, book: BookEdition, rearNeighbor?: T.Group) {
  if (!book.rearReference) return;
  const panel = unit.children.find((object) => object.name.endsWith(' · wrapper')) as T.Mesh<
    T.BufferGeometry,
    T.MeshStandardMaterial
  >;
  const shelfMap = panel.material.map as T.CanvasTexture<HTMLCanvasElement>;
  if (shelfMap.image.width >= 1152) return;
  const front = unit.children.find((object) => object.name.endsWith(' · front')) as T.Mesh<
    T.BufferGeometry,
    T.MeshStandardMaterial
  >;
  const bindings = [unit, ...(rearNeighbor ? [rearNeighbor] : [])].map((volume) => ({
    volume,
    position: volume.position.clone(),
    rotation: volume.quaternion.clone(),
  }));
  const exposed = () =>
    bindings.some(
      ({ volume, position, rotation }) =>
        volume.position.distanceToSquared(position) > 0.000001 ||
        Math.abs(volume.quaternion.dot(rotation)) < 0.99999,
    );
  const { age, seed } = printWear(book);
  let check = 0;
  const release = () => {
    cancelAnimationFrame(check);
    if (panel.material.map !== shelfMap) {
      panel.material.map?.dispose();
      panel.material.map = shelfMap;
    }
  };
  const checkReturn = () => {
    if (!exposed()) release();
    else check = requestAnimationFrame(checkReturn);
  };
  panel.material.addEventListener('dispose', release);
  panel.onBeforeRender = () => {
    const material = panel.material;
    if (material.map !== shelfMap || !exposed()) return;
    const closeMap = bindingPrint(book, age, seed, 3);
    const image = front.material.map?.image;
    if (image instanceof HTMLCanvasElement) applyFrontDetail(book.key, closeMap, image);
    material.map = closeMap;
    check = requestAnimationFrame(checkReturn);
  };
}

export function bindEdition(
  unit: T.Group,
  book: BookEdition,
  loader: CoverLoader,
  stock: ReturnType<typeof pageStocks>,
  deferBack: boolean,
) {
  unit.userData.ISBN = book.identifier;
  const kind = book.jacket ? 'jacket' : book.binding;
  const { age, seed } = printWear(book);
  const resolution = book.key === 'creative-act' || book.key === 'c-language' ? 3 : 1;
  const deferred = deferBack && !backUsesCover(book.key) && !!rearLayouts[book.key]?.blocks.length;
  const map = bindingPrint(book, age, seed, resolution, !deferred);
  const front = frontPrint(loader, book, age, seed, map);
  const materials = {
    front,
    wrapper: new T.MeshStandardMaterial({
      map,
      roughness: book.jacket ? 0.65 : book.binding === 'board' ? 0.86 : 0.7,
    }),
    leaves: stock(book, age),
  };
  for (const [surface, material] of Object.entries(materials)) {
    const panel = mesh(unit, form(kind, surface), material);
    panel.scale.set(...book.size);
    panel.name = `${kind} · ${surface}`;
  }
  if (!deferred) return;
  return () => {
    const canvas = document.createElement('canvas');
    canvas.width = 384 * resolution;
    canvas.height = 512 * resolution;
    paintBinding(canvas.getContext('2d')!, book, age, seed, resolution, true);
    map.image = canvas;
    map.needsUpdate = true;
  };
}
