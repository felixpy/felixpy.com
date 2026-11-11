import type { Vector3 } from 'three';

export function screenProjection(corners: readonly Vector3[], width: number, height: number) {
  const [tl, tr, bl, br] = corners;
  const x1 = tr.x - br.x,
    x2 = bl.x - br.x;
  const y1 = tr.y - br.y,
    y2 = bl.y - br.y;
  const skewX = tl.x - tr.x - bl.x + br.x;
  const skewY = tl.y - tr.y - bl.y + br.y;
  const determinant = x1 * y2 - x2 * y1;
  if (Math.abs(determinant) < 1e-6 || width <= 0 || height <= 0) return '';
  const g = (skewX * y2 - x2 * skewY) / determinant;
  const h = (x1 * skewY - skewX * y1) / determinant;
  return (
    'matrix3d(' +
    [
      (tr.x - tl.x + g * tr.x) / width,
      (tr.y - tl.y + g * tr.y) / width,
      0,
      g / width,
      (bl.x - tl.x + h * bl.x) / height,
      (bl.y - tl.y + h * bl.y) / height,
      0,
      h / height,
      0,
      0,
      1,
      0,
      tl.x,
      tl.y,
      0,
      1,
    ].join(',') +
    ')'
  );
}
