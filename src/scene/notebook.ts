import * as T from 'three';
import {
  box,
  canvasTexture,
  group,
  mesh,
  paperGeometry,
  print,
  random,
  surface,
  tube,
} from './geometry';
import type { Palette } from './materials';

const pageWidth = 0.118,
  pageHeight = 0.167;
const paperFace = 0.0034;
export const notebookSignature = {
  left: (112 / 768 - 0.5) * pageWidth,
  right: (381 / 768 - 0.5) * pageWidth,
  top: (0.5 - 704 / 1088) * pageHeight,
  bottom: (0.5 - 772 / 1088) * pageHeight,
  z: paperFace,
};

function writtenLeaf() {
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

export function projectNotebook(parent: T.Group, p: Palette) {
  const notebook = group(parent, 'FELIX · working notebook', [0.488, 0.757, 0.315]);
  notebook.rotation.set(-Math.PI / 2, 0, -0.18);
  const width = pageWidth,
    height = pageHeight;
  box(notebook, [0.125, 0.175, 0.002], [0, 0, -0.004], surface('#625344', 0.85), 0.001);
  box(notebook, [width, height, 0.006], [0, 0, 0], p.paper, 0.0013);
  const edges = surface('#ae9c7d', 0.91);
  for (const z of [-0.0021, -0.001, 0.00035, 0.00155]) {
    box(notebook, [width - 0.003, 0.00035, 0.0002], [0, -height / 2 - 0.0003, z], edges);
    box(notebook, [0.00025, height - 0.003, 0.00025], [width / 2 + 0.0002, 0, z], edges);
  }
  print(
    notebook,
    width,
    height,
    [0, 0, paperFace],
    writtenLeaf(),
    paperGeometry(width, height),
  ).castShadow = false;
  for (let i = 0; i < 7; i++) {
    const y = -0.068 + i * 0.022;
    const loop = mesh(notebook, new T.TorusGeometry(0.0046, 0.00075, 7, 22), p.graphite, [
      -0.0595,
      y,
      0.0028,
    ]);
    loop.rotation.x = Math.PI / 2;
    tube(notebook, [-0.053, y, 0.0031], [-0.053, y, 0.004], 0.0017, p.black);
  }
  return notebook;
}
