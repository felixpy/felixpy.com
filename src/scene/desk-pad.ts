import * as T from 'three';
import { canvasTexture, random } from './geometry';
import { loadDisplayModel } from './display-model';

export function woolFelt(width: number, height: number, tint: string) {
  const fleece = canvasTexture(512, 512, (ctx) => {
    ctx.fillStyle = '#716e64';
    ctx.fillRect(0, 0, 512, 512);
    const rng = random(2217);
    const palette = ['#48494250', '#c1b9a448', '#46464144', '#d6ccad37', '#8f8b7470'];
    ctx.lineCap = 'round';
    for (let i = 0; i < 29000; i++) {
      const x = rng() * 512,
        y = rng() * 512,
        angle = rng() * Math.PI * 2,
        length = 1 + rng() * 6;
      ctx.strokeStyle = palette[i % palette.length];
      ctx.lineWidth = 0.35 + 0.85 * rng();
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + Math.cos(angle) * length, y + Math.sin(angle) * length);
      ctx.stroke();
    }
  });
  fleece.wrapS = fleece.wrapT = T.RepeatWrapping;
  fleece.repeat.set(width * 8, height * 8);
  return new T.MeshStandardMaterial({
    map: fleece,
    color: tint,
    roughness: 0.96,
  });
}

export function deskPad(parent: T.Group, manager: T.LoadingManager) {
  return loadDisplayModel(parent, '/media/models/scabbard-ii-xxl.glb', manager, {
    mesh(part) {
      const finish = part.material;
      if (!(finish instanceof T.MeshStandardMaterial)) return;
      if (finish.map) finish.map.anisotropy = 8;
      if (finish.normalMap) finish.normalMap.anisotropy = 8;
    },
  });
}
