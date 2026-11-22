import * as T from 'three';
import type { Locale } from '../app/locale';
import { attacker, ship, sprite } from '../desktop/apps/arcade/flight-art';
import { box, canvasTexture, group, mesh, type XYZ } from './geometry';
import { blenderMesh } from './blender-mesh';
import { deferredDisplayModel, filterPrintedArtwork } from './display-model';
import type { Palette } from './materials';

export function spriteProofStock() {
  const stock = canvasTexture(1024, 768, (ctx) => {
    ctx.fillStyle = '#ddd7c3';
    ctx.fillRect(0, 734, 1024, 34);
  });
  const context = (stock.image as HTMLCanvasElement).getContext('2d')!;
  const setLocale = (locale: Locale) => {
    const ctx = context,
      zh = locale === 'zh';
    ctx.fillStyle = '#e5dfca';
    ctx.fillRect(0, 0, 1024, 734);
    ctx.fillStyle = '#273c34';
    ctx.font = '500 52px "IBM Plex Sans","Studio Han",sans-serif';
    ctx.fillText(zh ? '近地航线' : 'Orbital Patrol', 39, 85);
    ctx.textAlign = 'right';
    ctx.font = '23px monospace';
    ctx.fillText('pilot.sprite', 976, 83);
    ctx.textAlign = 'left';
    ctx.fillRect(40, 108, 941, 2);
    for (const [i, art] of [ship, attacker, ship].entries()) {
      const x = 67 + i * 310,
        y = 185;
      ctx.strokeStyle = '#b7b5a1';
      ctx.lineWidth = 1;
      for (let n = 0; n <= 16; n++) {
        ctx.beginPath();
        ctx.moveTo(x + n * 16, y);
        ctx.lineTo(x + n * 16, y + 256);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y + n * 16);
        ctx.lineTo(x + 256, y + n * 16);
        ctx.stroke();
      }
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(16, 16);
      sprite(
        ctx,
        art,
        8,
        8,
        i === 2 ? ['#2f4a4b', '#779293', '#bd835d'] : ['#4a5149', '#858e7f', '#a49880'],
      );
      ctx.restore();
    }
    ctx.strokeStyle = '#a15b40';
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.ellipse(818, 319, 133, 151, -0.12, 0.04, Math.PI * 1.98);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(839, 455);
    ctx.quadraticCurveTo(848, 494, 790, 509);
    ctx.stroke();
    ctx.fillStyle = '#81533c';
    ctx.font = zh ? '40px "Studio Han",sans-serif' : '500 55px Caveat,cursive';
    ctx.fillText(zh ? '小屏试样' : 'Check at 1×', 705, 575);
    ctx.fillStyle = '#667365';
    ctx.font = '22px monospace';
    ctx.fillText('14 × 13 px', 67, 500);
    ctx.fillText('13 × 07 px', 377, 500);
    for (let i = 0; i < 5; i++) {
      ctx.fillStyle = ['#d2e0e1', '#7394b6', '#d88557', '#746a9a', '#d99f9d'][i];
      ctx.fillRect(42 + i * 29, 669, 27, 23);
    }
    ctx.fillStyle = '#757866';
    ctx.font = '20px monospace';
    ctx.fillText('F. YANG', 867, 692);
    stock.needsUpdate = true;
  };
  setLocale('en');
  return { stock, setLocale };
}

export function flightProof(parent: T.Group, p: Palette) {
  const sheet = group(parent, 'Flight sprite proofs', [0.502, 0.7509, 0.271]);
  sheet.rotation.set(-Math.PI / 2, 0, 0.092);
  const { stock, setLocale } = spriteProofStock();
  const cotton = new T.MeshStandardMaterial({
    map: stock,
    roughness: 0.93,
    normalMap: p.paper.normalMap,
    normalScale: new T.Vector2(0.15, 0.15),
  });
  mesh(sheet, blenderMesh('stationery/flight-sprite-proof'), cotton).name =
    'Orbital Patrol · cotton proof paper';
  return { sheet, setLocale };
}

export function cardStorage(
  parent: T.Group,
  p: Palette,
  position: XYZ,
  detailMounted: (scene: T.Group) => void,
) {
  const wallet = group(parent, 'Foam card tray and spare media', position);
  const carrier = box(wallet, [0.092, 0.009, 0.065], [0, 0.0045, 0], p.rubber, 0.0037);
  const foam = p.cloth.clone();
  foam.color.set('#c0c9b9');
  for (const x of [-0.041, 0, 0.041]) box(wallet, [0.009, 0.005, 0.06], [x, 0.01, 0], foam, 0.0015);
  const card = group(wallet, 'CFexpress Type B card', [0.021, 0.0123, 0.006]);
  card.rotation.y = -0.055;
  const prepare = deferredDisplayModel(card, '/media/models/cfexpress-type-b.glb', {
    mesh: filterPrintedArtwork,
    mounted: detailMounted,
  });
  carrier.castShadow = true;
  return { card, prepare };
}
