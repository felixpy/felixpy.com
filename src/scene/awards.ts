import * as T from 'three';
import { box, canvasTexture, group, mesh } from './geometry';
import type { Palette } from './materials';

const awards = [
  { en: 'Technology Innovation Award', zh: '技术创新奖' },
  { en: 'Master of Photography Award', zh: '摄影大师奖' },
] as const;

function innovation(trophy: T.Group, p: Palette) {
  const patina = p.bronze.clone();
  patina.color.set('#503e2e');
  patina.roughness = 0.44;
  const bright = p.bronze.clone();
  bright.color.set('#bb8f55');
  bright.roughness = 0.33;
  const shape = new T.Shape([
    new T.Vector2(-0.05, 0),
    new T.Vector2(0.036, 0),
    new T.Vector2(0.056, 0.176),
    new T.Vector2(-0.018, 0.151),
  ]);
  const opening = new T.Path([
    new T.Vector2(-0.023, 0.064),
    new T.Vector2(0.022, 0.08),
    new T.Vector2(0.036, 0.139),
    new T.Vector2(-0.003, 0.123),
  ]);
  shape.holes.push(opening);
  const geometry = new T.ExtrudeGeometry(shape, {
    depth: 0.027,
    bevelThickness: 0.002,
    bevelSize: 0.002,
    bevelSegments: 4,
    curveSegments: 12,
  });
  const form = new T.Mesh(geometry, [patina, bright]);
  form.position.set(0, 0.027, -0.014);
  form.castShadow = form.receiveShadow = true;
  trophy.add(form);
}

function photography(trophy: T.Group, p: Palette) {
  const shape = new T.Shape();
  shape.moveTo(-0.046, 0.012);
  shape.quadraticCurveTo(-0.046, 0, -0.034, 0);
  shape.lineTo(0.034, 0);
  shape.quadraticCurveTo(0.046, 0, 0.046, 0.012);
  shape.lineTo(0.046, 0.118);
  shape.quadraticCurveTo(0.046, 0.137, 0.027, 0.137);
  shape.lineTo(-0.027, 0.137);
  shape.quadraticCurveTo(-0.046, 0.137, -0.046, 0.118);
  shape.closePath();
  const aperture = new T.Path();
  aperture.absarc(0, 0.073, 0.026, 0, Math.PI * 2, true);
  shape.holes.push(aperture);
  const glass = new T.MeshPhysicalMaterial({
    color: '#60938e',
    roughness: 0.18,
    metalness: 0.21,
    clearcoat: 0.89,
    clearcoatRoughness: 0.09,
    transparent: true,
    opacity: 0.76,
  });
  const geometry = new T.ExtrudeGeometry(shape, {
    depth: 0.014,
    bevelThickness: 0.0022,
    bevelSize: 0.0022,
    bevelSegments: 4,
    curveSegments: 36,
  });
  mesh(trophy, geometry, glass, [0, 0.027, -0.007]).castShadow = false;
  for (const [i, radius] of [0.0274, 0.0326, 0.0364, 0.0403].entries()) {
    const ring = mesh(
      trophy,
      new T.TorusGeometry(radius, i === 0 ? 0.00105 : 0.00054, 9, 64),
      i === 0 ? p.bronze : glass,
      [0, 0.1, 0.0087 + (3 - i) * 0.00045],
    );
    if (i !== 0) ring.castShadow = false;
  }
}

export function shelfAwards(parent: T.Group, p: Palette) {
  return awards.map((award, index) => {
    const trophy = group(
      parent,
      award.en,
      index === 0 ? [0.155, 1.253, 0.05] : [0.15, 0.846, 0.059],
    );
    trophy.rotation.y = index === 0 ? -0.14 : 0.17;
    box(trophy, [0.128, 0.029, 0.093], [0, 0.0145, 0], p.woodDark, 0.005);
    box(trophy, [0.096, 0.016, 0.0008], [0, 0.0145, 0.0467], p.bronze, 0.0003);
    const plate = canvasTexture(512, 85, (ctx) => {
      ctx.fillStyle = '#30281e';
      ctx.font = '600 32px "Studio Han", "IBM Plex Sans", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(award.zh, 256, 38);
      ctx.font = '500 17px "IBM Plex Sans", sans-serif';
      ctx.fillText(award.en.toUpperCase(), 256, 65);
    });
    mesh(
      trophy,
      new T.PlaneGeometry(0.091, 0.015),
      new T.MeshStandardMaterial({
        map: plate,
        transparent: true,
        depthWrite: false,
        roughness: 0.71,
      }),
      [0, 0.0145, 0.0472],
    ).castShadow = false;
    if (index === 0) innovation(trophy, p);
    else photography(trophy, p);
    return { object: trophy, ...award };
  });
}
