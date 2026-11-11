import * as T from 'three';
import type { Locale } from '../app/locale';
import {
  box,
  cable,
  canvasTexture,
  group,
  mesh,
  paperGeometry,
  random,
  surface,
  tube,
} from './geometry';
import type { Palette } from './materials';
import { projectNotebook } from './notebook';

function accessCard(parent: T.Object3D, p: Palette) {
  const card = group(parent, 'Studio access card', [-0.238, -0.205, 0.027]);
  card.rotation.z = -0.14;
  const shell = p.rubber.clone();
  shell.color.set('#485a52');
  shell.roughness = 0.53;
  box(card, [0.086, 0.054, 0.0012], [0, 0, 0], shell, 0.0005);
  const face = canvasTexture(512, 321, (ctx) => {
    const rng = random(465);
    ctx.fillStyle = '#495f58';
    ctx.fillRect(0, 0, 512, 321);
    ctx.fillStyle = '#a7afa5';
    ctx.fillRect(0, 219, 512, 102);
    ctx.fillStyle = '#e3e8d9';
    ctx.font = '600 43px "IBM Plex Sans", sans-serif';
    ctx.fillText('STUDIO', 35, 92);
    ctx.font = '500 27px "IBM Plex Sans", sans-serif';
    ctx.fillText('ACCESS', 35, 132);
    ctx.strokeStyle = '#d4ddc6';
    ctx.lineWidth = 4;
    for (const radius of [11, 22, 34]) {
      ctx.beginPath();
      ctx.arc(400, 112, radius, -0.7, 0.7);
      ctx.stroke();
    }
    ctx.strokeStyle = '#e3ead83b';
    for (let i = 0; i < 24; i++) {
      const x = 24 + rng() * 470,
        y = 20 + rng() * 280;
      ctx.lineWidth = 0.7 + rng();
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 5 + rng() * 27, y - 2);
      ctx.stroke();
    }
  });
  mesh(
    card,
    new T.PlaneGeometry(0.0845, 0.0525),
    new T.MeshStandardMaterial({ map: face, normalMap: shell.normalMap, roughness: 0.58 }),
    [0, 0, 0.0007],
  ).castShadow = false;
  box(card, [0.072, 0.01, 0.0002], [0, 0.008, -0.0007], p.black, 0.0001);
  return card;
}
export function personalArchive(root: T.Group, p: Palette) {
  const board = group(root, 'Personal archive · pinboard', [-0.2, 1.654, -0.509]);
  box(board, [1.28, 0.64, 0.028], [0, 0, 0], p.woodDark, 0.003);
  box(board, [1.238, 0.597, 0.013], [0, 0, 0.014], p.linen, 0.002);
  const cloth = new T.PlaneGeometry(1.235, 0.595, 20, 12);
  const vertices = cloth.attributes.position;
  for (let i = 0; i < vertices.count; i++) {
    const u = vertices.getX(i) / 1.235 + 0.5;
    const v = vertices.getY(i) / 0.595 + 0.5;
    vertices.setZ(
      i,
      0.0015 * Math.sin(u * Math.PI) * Math.sin(v * Math.PI) * (1 + Math.sin(u * 12 + v * 8)),
    );
  }
  cloth.computeVertexNormals();
  mesh(board, cloth, p.linen, [0, 0, 0.0206]).castShadow = false;
  const card = accessCard(board, p);
  box(board, [0.026, 0.01, 0.008], [-0.233, -0.18, 0.031], p.bronze, 0.0015);
  const note = group(board, 'Handwritten pinboard tags', [0, 0, 0.023]);
  const labels = {
    en: [
      ['World', 0.08, 0.266],
      ['China', 0.07, -0.004],
      ['Hometown', -0.425, 0.246],
    ],
    zh: [
      ['世界', 0.08, 0.266],
      ['中国', 0.07, -0.004],
      ['故乡', -0.425, 0.246],
    ],
  } as const;
  const paperTags = labels.en.map((_, index) => {
    const [text, x, y] = labels.en[index];
    const tag = group(note, 'Handwritten ' + text, [x, y, 0.003]);
    tag.rotation.z = [-0.08, 0.06, -0.05][index];
    mesh(tag, paperGeometry(0.115, 0.037), p.paper);
    const ink = (locale: Locale) =>
      canvasTexture(448, 142, (ctx) => {
        ctx.fillStyle = '#373632';
        ctx.textAlign = 'center';
        ctx.font =
          locale === 'en'
            ? '500 88px Caveat, cursive'
            : '74px "Studio Script", "Studio Han", serif';
        ctx.fillText(labels[locale][index][0], 224, 95);
      });
    const print = mesh(
      tag,
      paperGeometry(0.115, 0.037),
      new T.MeshStandardMaterial({
        map: null,
        transparent: true,
        depthWrite: false,
        roughness: 0.95,
      }),
      [0, 0, 0.0006],
    );
    print.castShadow = false;
    tube(tag, [-0.045, 0.011, 0.0006], [-0.045, 0.011, 0.0037], 0.0022, p.bronze);
    return {
      material: print.material as T.MeshStandardMaterial,
      textures: { en: ink('en'), zh: ink('zh') },
    };
  });
  const line = surface('#8d644b', 0.89);
  cable(
    note,
    [
      [0.144, 0.262, 0.001],
      [0.204, 0.262, 0.001],
      [0.24, 0.25, 0.002],
    ],
    0.00065,
    line,
  );
  cable(
    note,
    [
      [0.134, -0.004, 0.001],
      [0.195, -0.003, 0.002],
      [0.229, -0.016, 0.001],
    ],
    0.00065,
    line,
  );
  const clip = group(board, 'Brass bulldog clip and paper scrap', [0.51, -0.205, 0.027]);
  clip.rotation.z = 0.13;
  mesh(clip, paperGeometry(0.081, 0.057), p.paper);
  box(clip, [0.022, 0.009, 0.008], [0, 0.024, 0.006], p.bronze, 0.0014);
  for (const y of [0.022, 0.028])
    tube(clip, [-0.011, y, 0.006], [0.011, y, 0.006], 0.0016, p.steel);
  function setLocale(locale: Locale) {
    for (const { material, textures } of paperTags) {
      material.map = textures[locale];
      material.needsUpdate = true;
    }
  }
  setLocale('en');
  const objects = [
    { id: 'accessCard', object: card, size: 0.093 },
    { id: 'openSource', object: projectNotebook(root, p), size: 0.14 },
  ] as const;
  return { board, objects, setLocale };
}
