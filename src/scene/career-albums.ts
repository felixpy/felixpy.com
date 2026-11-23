import * as T from 'three';
import { careerEditions } from '../content/profile';
import { canvasTexture, group } from './geometry';
import { loadDisplayModel } from './display-model';

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

export function albumCover(edition: Edition) {
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

export function careerAlbums(
  parent: T.Object3D,
  manager: T.LoadingManager,
  deferRoomDetail: (load: () => void) => void,
) {
  const albums = careerEditions.map((edition, index) => {
    const album = group(parent, edition.title + ' · cloth-bound album', [
      0.155 - index * 0.205,
      0.761,
      0.568,
    ]);
    album.rotation.set(-Math.PI / 2, 0, -Math.PI / 2 + (index === 0 ? 0.05 : -0.07));
    return { edition, album };
  });
  deferRoomDetail(() =>
    loadDisplayModel(albums[0].album, '/media/models/stationery/career-album.glb', manager, {
      mounted(first) {
        const bindings = [first, first.clone(true)];
        for (const [index, { album, edition }] of albums.entries()) {
          const binding = bindings[index];
          album.add(binding);
          binding.traverse((part) => {
            if (!(part instanceof T.Mesh) || !(part.material instanceof T.MeshStandardMaterial))
              return;
            const finish = part.material;
            if (finish.name === 'Custom cover print') {
              part.material = finish.clone();
              const cover = albumCover(edition);
              cover.flipY = false;
              part.material.map = cover;
            } else if (finish.name === 'Dyed book linen' || finish.name === 'Woven marker') {
              part.material = finish.clone();
              part.material.color.set(
                finish.name === 'Dyed book linen' ? edition.jacket : edition.accent,
              );
            }
          });
        }
      },
    }),
  );
  return albums;
}
