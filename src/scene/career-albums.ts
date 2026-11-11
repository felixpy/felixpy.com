import * as T from 'three';
import { careerEditions } from '../content/profile';
import { box, canvasTexture, group, print, random } from './geometry';
import type { Palette } from './materials';

type Edition = (typeof careerEditions)[number];

function editorialArt(ctx: CanvasRenderingContext2D, edition: Edition) {
  ctx.strokeStyle = edition.accent;
  ctx.fillStyle = edition.accent;
  ctx.lineWidth = 2;
  if (edition.id === 'first') {
    for (let i = 0; i < 7; i++) {
      const x = 94 + 65 * i;
      const y = 309 - 11 * i;
      ctx.strokeRect(x, y, 102, 58);
      ctx.fillRect(x, y + 62, i < 4 ? 25 : 10, 2);
    }
    ctx.beginPath();
    ctx.moveTo(96, 397);
    ctx.lineTo(581, 397);
    ctx.stroke();
    for (const x of [96, 198, 304, 423, 581]) ctx.fillRect(x, 394, 1.8, 8);
    return;
  }
  const nodes = [
    [113, 343],
    [215, 302],
    [343, 349],
    [454, 282],
    [574, 335],
  ];
  ctx.beginPath();
  nodes.forEach(([x, y], index) => (index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.stroke();
  for (const [x, y] of nodes) {
    ctx.fillStyle = edition.ink;
    ctx.fillRect(x - 30, y - 18, 60, 36);
    ctx.strokeRect(x - 30, y - 18, 60, 36);
    ctx.beginPath();
    ctx.moveTo(x - 4, y - 6);
    ctx.lineTo(x + 7, y);
    ctx.lineTo(x - 4, y + 6);
    ctx.closePath();
    ctx.fillStyle = edition.accent;
    ctx.fill();
  }
}

function albumCover(edition: Edition) {
  return canvasTexture(680, 840, (ctx) => {
    ctx.fillStyle = edition.ink;
    ctx.fillRect(0, 0, 680, 840);
    ctx.strokeStyle = edition.accent;
    ctx.lineWidth = 2;
    ctx.strokeRect(22, 22, 636, 796);
    ctx.fillStyle = '#eee6d8';
    ctx.font = '500 23px "IBM Plex Sans", sans-serif';
    ctx.fillText('CAREER JOURNAL', 48, 75);
    ctx.font = '700 120px "IBM Plex Sans", sans-serif';
    ctx.fillText(edition.volume, 47, 224);
    editorialArt(ctx, edition);
    ctx.fillStyle = '#eee6d8';
    ctx.font = '600 49px "IBM Plex Sans", sans-serif';
    ctx.fillText(edition.title, 49, 650);
    ctx.font = '500 29px "IBM Plex Sans", sans-serif';
    ctx.fillText(edition.role[0], 51, 699, 575);
    ctx.fillStyle = edition.accent;
    ctx.font = '500 25px "IBM Plex Sans", sans-serif';
    ctx.fillText(edition.years[0].toUpperCase(), 51, 734);
    ctx.font = '500 20px "IBM Plex Sans", sans-serif';
    ctx.fillText('FELIX YANG', 51, 781);
  });
}

export function careerAlbums(parent: T.Object3D, p: Palette) {
  const pageEdge = canvasTexture(512, 64, (ctx) => {
    ctx.fillStyle = '#d6c7a7';
    ctx.fillRect(0, 0, 512, 64);
    const rng = random(724);
    for (let y = 1; y < 64; y += 2) {
      ctx.strokeStyle = y % 3 ? '#b1a08082' : '#f9edd4c2';
      ctx.lineWidth = 0.5 + rng();
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(512, y + rng() - 0.5);
      ctx.stroke();
    }
  });
  const pages = p.paper.clone();
  const edge = new T.MeshStandardMaterial({ map: pageEdge, roughness: 0.92 });
  const foreEdge = edge.clone();
  foreEdge.map = pageEdge.clone();
  foreEdge.map.center.set(0.5, 0.5);
  foreEdge.map.rotation = Math.PI / 2;
  const pageFaces = [foreEdge, pages, edge, edge, pages, pages];
  const width = 0.144,
    height = 0.178;
  return careerEditions.map((edition, index) => {
    const album = group(parent, edition.title + ' · cloth-bound album', [
      0.155 - index * 0.205,
      0.761,
      0.568,
    ]);
    album.rotation.set(-Math.PI / 2, 0, -Math.PI / 2 + (index === 0 ? 0.05 : -0.07));
    const cloth = p.linen.clone();
    cloth.color.set(edition.jacket);
    cloth.normalScale.set(0.69, 0.69);
    box(album, [width, height, 0.0027], [0, 0, -0.009], cloth, 0.001);
    box(album, [width, height, 0.0027], [0, 0, 0.009], cloth, 0.001);
    box(album, [0.009, height, 0.02], [-width / 2 + 0.003, 0, 0], cloth, 0.0037);
    box(album, [width - 0.008, height - 0.006, 0.0153], [0.001, 0, 0], pageFaces);
    const title = print(
      album,
      width - 0.017,
      height - 0.011,
      [0.003, 0, 0.01042],
      albumCover(edition),
    );
    const art = title.material as T.MeshStandardMaterial;
    art.normalMap = cloth.normalMap;
    art.normalScale.set(0.69, 0.69);
    title.castShadow = false;
    return { edition, album };
  });
}
