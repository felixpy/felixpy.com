import * as T from 'three';
import { canvasTexture } from './geometry';

export function rogEye(finish: 'case' | 'lit' | 'etched' = 'case') {
  return canvasTexture(512, 280, (ctx) => {
    const point = new Path2D('M32 77 Q62 120 96 158 Q47 138 32 77 Z');
    const upper = new Path2D(
      'M87 122 Q109 143 136 157 Q231 96 314 53 Q372 22 477 28 Q391 43 331 71 Q217 123 142 188 L167 239 Q119 204 87 122 Z',
    );
    const lower = new Path2D(
      'M151 185 Q278 91 486 62 L462 98 Q298 128 205 178 Q248 198 313 218 Q365 190 414 133 L457 112 Q406 206 349 244 Q329 257 303 248 Q212 227 151 185 Z',
    );
    if (finish === 'etched') {
      point.addPath(upper);
      point.addPath(lower);
      ctx.clip(point);
      ctx.fillStyle = '#242528';
      ctx.fillRect(0, 0, 512, 280);
      ctx.strokeStyle = '#505154';
      ctx.lineWidth = 2.2;
      for (let x = -280; x < 512; x += 5.7) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + 278, 280);
        ctx.stroke();
      }
      return;
    }
    const silver = ctx.createLinearGradient(0, 32, 0, 240);
    silver.addColorStop(0, '#f3f2ec');
    silver.addColorStop(1, '#8b98a0');
    ctx.fillStyle = finish === 'lit' ? '#ffffff' : silver;
    ctx.fill(point);
    ctx.fill(upper);
    const scarlet = ctx.createLinearGradient(300, 53, 260, 248);
    scarlet.addColorStop(0, '#ed897e');
    scarlet.addColorStop(0.45, '#d14c3d');
    scarlet.addColorStop(1, '#8c231e');
    ctx.fillStyle = finish === 'lit' ? '#c0c0c0' : scarlet;
    ctx.fill(lower);
  });
}

export function litRogEye() {
  const map = rogEye('lit');
  return new T.MeshStandardMaterial({
    color: '#343b3f',
    map,
    emissiveMap: map,
    alphaTest: 0.35,
    roughness: 0.35,
  });
}
