import * as T from 'three';
import { blenderMesh } from './blender-mesh';
import { canvasTexture, group, mesh, random, surface } from './geometry';
import type { Palette } from './materials';

const pageWidth = 0.128,
  pageHeight = 0.182;
const paperFace = 0.00162;
export const notebookSignature = {
  left: (112 / 768 - 0.5) * pageWidth,
  right: (381 / 768 - 0.5) * pageWidth,
  top: (0.5 - 704 / 1088) * pageHeight,
  bottom: (0.5 - 772 / 1088) * pageHeight,
  z: paperFace,
};

export function writtenLeaf() {
  return canvasTexture(768, 1088, (ctx) => {
    const stock = ctx.createLinearGradient(0, 0, 768, 1088);
    stock.addColorStop(0, '#cbb996');
    stock.addColorStop(0.25, '#e5d7b4');
    stock.addColorStop(0.7, '#ede0c1');
    stock.addColorStop(1, '#d8c39d');
    ctx.fillStyle = stock;
    ctx.fillRect(0, 0, 768, 1088);
    const rng = random(615);
    for (let i = 0; i < 11500; i++) {
      ctx.fillStyle = i % 3 ? '#8a6b3910' : '#fff9e822';
      ctx.fillRect(rng() * 768, rng() * 1088, 0.5 + rng() * 2, 0.5 + rng() * 3.3);
    }
    ctx.strokeStyle = '#aa987a75';
    ctx.lineWidth = 0.7;
    ctx.setLineDash([2.1, 2.8]);
    ctx.beginPath();
    ctx.moveTo(55, 0);
    ctx.lineTo(55, 1088);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.lineWidth = 1.2;
    for (let y = 153; y < 1050; y += 56) {
      ctx.strokeStyle = '#7b919178';
      ctx.beginPath();
      ctx.moveTo(22, y);
      ctx.lineTo(742, y + 0.7);
      ctx.stroke();
    }
    ctx.strokeStyle = '#aa574969';
    ctx.beginPath();
    ctx.moveTo(81, 4);
    ctx.lineTo(82, 1082);
    ctx.stroke();
    ctx.font = '500 105px Caveat, cursive';
    ctx.fillStyle = '#282c2b';
    ctx.fillText('FELIX', 118, 251);
    ctx.font = '500 49px Caveat, cursive';
    ctx.fillStyle = '#863f32';
    ctx.fillText('working notes', 396, 253);
    ctx.font = '40px "Segoe UI Emoji", "Apple Color Emoji", sans-serif';
    ctx.fillText('🎨', 117, 390);
    ctx.fillText('⛵', 117, 507);
    ctx.font = '600 53px Caveat, cursive';
    ctx.fillStyle = '#2b332d';
    ctx.fillText('Taste Is All You Need', 177, 390);
    ctx.fillText('Shipping apps, videos', 177, 507);
    ctx.fillText('and games with AI', 177, 564);
    ctx.fillStyle = '#863f32';
    ctx.font = '500 45px Caveat, cursive';
    ctx.fillText('X  /  @gofelixpy', 123, 748);
    ctx.strokeStyle = '#863f32';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(120, 266);
    ctx.quadraticCurveTo(240, 257, 356, 270);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(122, 761);
    ctx.quadraticCurveTo(248, 752, 367, 762);
    ctx.stroke();
  });
}

function kraftGrain() {
  return canvasTexture(384, 540, (ctx) => {
    ctx.fillStyle = '#f1ebdf';
    ctx.fillRect(0, 0, 384, 540);
    const rng = random(238);
    for (let i = 0; i < 11000; i++) {
      ctx.fillStyle = i % 3 ? '#59462e18' : '#fff9df70';
      ctx.fillRect(rng() * 384, rng() * 540, 0.6 + 2.5 * rng(), 0.45 + 0.7 * rng());
    }
  });
}

export function projectNotebook(parent: T.Group, p: Palette) {
  const notebook = group(parent, 'FELIX · working notebook', [0.488, 0.75482, 0.315]);
  notebook.rotation.set(-Math.PI / 2, 0, -0.18);
  const surfaces = {
    'kraft-front': surface('#a1835e', 0.86),
    'kraft-back': surface('#886d53', 0.89),
    'paper-edge': p.paper,
    'punch-wall': surface('#ab9b80', 0.94),
    signed: new T.MeshStandardMaterial({ map: writtenLeaf(), roughness: 0.83 }),
    wire: surface('#c1c7c9', 0.31, 0.83),
  };
  surfaces['kraft-front'].map = surfaces['kraft-back'].map = kraftGrain();
  surfaces['kraft-front'].normalMap = surfaces['kraft-back'].normalMap = p.paper.normalMap;
  for (const [part, finish] of Object.entries(surfaces)) {
    const object = mesh(notebook, blenderMesh('stationery/felix-notebook-' + part), finish);
    object.name = 'Notebook · ' + part;
  }
  return notebook;
}
