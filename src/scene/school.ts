import * as T from 'three';
import { biography, profile } from '../content/profile';
import { box, canvasTexture, group, mesh, random, surface } from './geometry';
import type { Palette } from './materials';

export const aerospaceTitle = { zh: '航空航天概论', en: 'Introduction to Aerospace' };

function cover() {
  return canvasTexture(600, 720, (ctx) => {
    ctx.fillStyle = '#d9c8a4';
    ctx.font = '600 57px "Studio Han", sans-serif';
    ctx.fillText(aerospaceTitle.zh, 56, 117);
    ctx.font = '500 32px "IBM Plex Sans", sans-serif';
    ctx.fillText(aerospaceTitle.en, 58, 167);
    ctx.save();
    ctx.translate(0, 93);
    ctx.strokeStyle = '#9eab9c72';
    ctx.lineWidth = 1;
    for (let x = 58; x < 550; x += 30) {
      ctx.beginPath();
      ctx.moveTo(x, 178);
      ctx.lineTo(x, 448);
      ctx.stroke();
    }
    for (let y = 178; y < 450; y += 30) {
      ctx.beginPath();
      ctx.moveTo(58, y);
      ctx.lineTo(550, y);
      ctx.stroke();
    }
    ctx.strokeStyle = '#c9b792';
    ctx.lineWidth = 3.4;
    ctx.beginPath();
    ctx.moveTo(300, 183);
    ctx.bezierCurveTo(311, 196, 317, 246, 318, 270);
    ctx.lineTo(506, 387);
    ctx.lineTo(507, 407);
    ctx.lineTo(322, 354);
    ctx.lineTo(316, 416);
    ctx.lineTo(350, 439);
    ctx.lineTo(350, 452);
    ctx.lineTo(300, 442);
    ctx.lineTo(250, 452);
    ctx.lineTo(250, 439);
    ctx.lineTo(284, 416);
    ctx.lineTo(278, 354);
    ctx.lineTo(93, 407);
    ctx.lineTo(94, 387);
    ctx.lineTo(282, 270);
    ctx.bezierCurveTo(283, 246, 289, 196, 300, 183);
    ctx.stroke();
    ctx.restore();
  });
}

function studentCard(loader: T.TextureLoader) {
  const texture = canvasTexture(856, 540, (ctx) => {
    const field = ctx.createLinearGradient(0, 0, 842, 510);
    field.addColorStop(0, '#d3dce1');
    field.addColorStop(0.42, '#e8e7d8');
    field.addColorStop(1, '#d2c8b0');
    ctx.fillStyle = field;
    ctx.fillRect(0, 0, 856, 540);
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(538, 129, 270, 255, 6);
    ctx.clip();
    ctx.fillStyle = '#c9cfc9';
    ctx.fillRect(537, 129, 272, 256);
    ctx.strokeStyle = '#6e859065';
    ctx.lineWidth = 1.6;
    for (let row = 0; row < 23; row++) {
      ctx.beginPath();
      for (let x = 529; x <= 815; x += 3) {
        const y = 123 + row * 13 + Math.sin((x - 530) / 43 + row * 0.29) * 16;
        if (x === 529) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    ctx.fillStyle = '#546777ad';
    ctx.beginPath();
    ctx.moveTo(593, 289);
    ctx.lineTo(663, 270);
    ctx.lineTo(663, 218);
    ctx.lineTo(675, 193);
    ctx.lineTo(688, 218);
    ctx.lineTo(688, 270);
    ctx.lineTo(757, 289);
    ctx.lineTo(757, 300);
    ctx.lineTo(687, 288);
    ctx.lineTo(682, 325);
    ctx.lineTo(703, 336);
    ctx.lineTo(703, 343);
    ctx.lineTo(675, 337);
    ctx.lineTo(649, 343);
    ctx.lineTo(649, 336);
    ctx.lineTo(669, 325);
    ctx.lineTo(665, 288);
    ctx.lineTo(593, 300);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
    ctx.fillStyle = '#dce3e2';
    ctx.fillRect(0, 0, 856, 112);
    ctx.fillStyle = '#1c4a74';
    ctx.font = '600 32px "Studio Han", sans-serif';
    ctx.fillText(biography.school.name, 152, 51);
    ctx.font = '600 22px "IBM Plex Sans", sans-serif';
    ctx.fillText('BEIHANG UNIVERSITY', 153, 82);
    ctx.fillStyle = '#34495c';
    ctx.font = '600 48px "Studio Han", sans-serif';
    ctx.fillText('学生证', 42, 193);
    ctx.font = '500 24px "IBM Plex Sans", sans-serif';
    ctx.fillText('STUDENT CARD', 44, 232);
    ctx.fillStyle = '#697782';
    ctx.font = '500 18px "IBM Plex Sans", sans-serif';
    ctx.fillText('HOLDER', 43, 294);
    ctx.fillText('ENROLMENT', 43, 371);
    ctx.fillStyle = '#4f5050';
    ctx.font = '500 35px "IBM Plex Sans", sans-serif';
    ctx.fillText(profile.name, 42, 332);
    ctx.font = '500 26px "IBM Plex Sans", sans-serif';
    ctx.fillText(biography.school.years, 43, 401);
    ctx.strokeStyle = '#5b697363';
    ctx.beginPath();
    ctx.moveTo(40, 418);
    ctx.lineTo(810, 418);
    ctx.stroke();
    ctx.font = '500 20px "IBM Plex Sans", "Studio Han", sans-serif';
    ctx.fillText('CAMPUS MEMENTO / 校园留念', 42, 476);
    const rng = random(881);
    for (let i = 0; i < 410; i++) {
      const x = rng() * 856,
        y = rng() * 540;
      const edge = Math.min(x, 856 - x, y, 540 - y);
      if (edge > 33 && rng() < 0.92) continue;
      ctx.strokeStyle = edge < 13 ? '#f9f3df91' : '#ede5cc3b';
      ctx.lineWidth = 0.5 + rng() * 2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + rng() * 17, y + 3 - rng() * 10);
      ctx.stroke();
    }
    ctx.strokeStyle = '#f8ebc983';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(1, 58);
    ctx.quadraticCurveTo(8, 12, 58, 3);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(806, 536);
    ctx.quadraticCurveTo(848, 529, 852, 494);
    ctx.stroke();
  });
  new T.ImageLoader(loader.manager).load('/media/graphics/beihang-emblem.jpg', (image) => {
    const ctx = (texture.image as HTMLCanvasElement).getContext('2d')!;
    ctx.save();
    ctx.beginPath();
    ctx.arc(90, 55, 42, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(image, 48, 13, 84, 84);
    ctx.restore();
    texture.needsUpdate = true;
  });
  return texture;
}

function cardBack() {
  return canvasTexture(856, 540, (ctx) => {
    ctx.fillStyle = '#d7d0bc';
    ctx.fillRect(0, 0, 856, 540);
    ctx.fillStyle = '#b4b7ad';
    ctx.fillRect(0, 70, 856, 67);
    ctx.strokeStyle = '#6a726572';
    ctx.strokeRect(45, 216, 755, 94);
    ctx.fillStyle = '#5f675e';
    ctx.font = '500 19px "IBM Plex Sans", sans-serif';
    ctx.fillText('CAMPUS COLLECTION', 45, 189);
    ctx.fillText('BEIHANG UNIVERSITY', 45, 461);
    ctx.fillStyle = '#3d4e64';
    ctx.font = '500 65px Caveat, cursive';
    ctx.save();
    ctx.translate(470, 280);
    ctx.rotate(-0.06);
    ctx.fillText('June 2014', 0, 0);
    ctx.restore();
    const rng = random(907);
    for (let i = 0; i < 220; i++) {
      const x = rng() * 856,
        y = rng() * 540;
      ctx.fillStyle = i % 3 ? '#e8dec83c' : '#a58c681e';
      ctx.fillRect(x, y, rng() * 13, 1.3);
    }
  });
}

export function schoolNotebook(parent: T.Group, p: Palette, loader: T.TextureLoader) {
  const notebook = group(parent, aerospaceTitle.en, [-0.755, 0.761, 0.242]);
  notebook.rotation.set(-Math.PI / 2, 0, -0.16);
  const cloth = p.linen.clone();
  cloth.map = null;
  cloth.color.set('#334450');
  const pages = surface('#d2c6ac', 0.85);
  box(notebook, [0.138, 0.175, 0.01], [0.003, 0, 0], pages, 0.0015);
  for (const z of [-0.006, 0.006]) box(notebook, [0.148, 0.183, 0.003], [0, 0, z], cloth, 0.0013);
  box(notebook, [0.008, 0.183, 0.014], [-0.072, 0, 0], cloth, 0.0028);
  mesh(
    notebook,
    new T.PlaneGeometry(0.144, 0.177),
    new T.MeshStandardMaterial({
      map: cover(),
      transparent: true,
      depthWrite: false,
      roughness: 0.48,
      metalness: 0.23,
    }),
    [0, 0, 0.0077],
  ).castShadow = false;
  const pass = group(parent, 'Beihang student card');
  pass.rotation.z = -0.12;
  const laminate = new T.MeshPhysicalMaterial({
    map: studentCard(loader),
    roughness: 0.59,
    clearcoat: 0.53,
    clearcoatRoughness: 0.38,
  });
  const cardShape = new T.Shape();
  const x = 0.0428,
    y = 0.027,
    r = 0.003;
  cardShape.moveTo(-x + r, -y);
  cardShape.lineTo(x - r, -y);
  cardShape.quadraticCurveTo(x, -y, x, -y + r);
  cardShape.lineTo(x, y - r);
  cardShape.quadraticCurveTo(x, y, x - r, y);
  cardShape.lineTo(-x + r, y);
  cardShape.quadraticCurveTo(-x, y, -x, y - r);
  cardShape.lineTo(-x, -y + r);
  cardShape.quadraticCurveTo(-x, -y, -x + r, -y);
  const face = new T.ShapeGeometry(cardShape, 10);
  const position = face.attributes.position;
  for (let i = 0; i < position.count; i++)
    face.attributes.uv.setXY(i, position.getX(i) / (2 * x) + 0.5, position.getY(i) / (2 * y) + 0.5);
  mesh(
    pass,
    new T.ExtrudeGeometry(cardShape, { depth: 0.00076, bevelEnabled: false, curveSegments: 10 }),
    surface('#c1bcae', 0.64),
    [0, 0, -0.00038],
  );
  mesh(pass, face, laminate, [0, 0, 0.00045]).castShadow = false;
  const reverse = mesh(
    pass,
    face,
    new T.MeshPhysicalMaterial({
      map: cardBack(),
      roughness: 0.63,
      clearcoat: 0.45,
      clearcoatRoughness: 0.41,
    }),
    [0, 0, -0.00045],
  );
  reverse.rotation.y = Math.PI;
  reverse.castShadow = false;
  return { notebook, pass };
}
