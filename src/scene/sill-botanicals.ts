import * as T from 'three';
import { loadBlenderPack } from './blender-pack';
import { canvasTexture, group, mesh, random, surface, type XYZ } from './geometry';
import type { Palette } from './materials';
import { philodendron } from './philodendron';
import { lunaVase } from './still-life';

function bladeTexture(relief: boolean) {
  const width = 320,
    height = 512;
  const texture = canvasTexture(width, height, (ctx) => {
    const image = ctx.createImageData(width, height);
    const rng = random(5741);
    for (let y = 0; y < height; y++)
      for (let x = 0; x < width; x++) {
        const v = y / height,
          u = (x / width) * 2 - 1;
        const mottling =
          6 * Math.sin(u * 7.9 + v * 4.5) * Math.cos(v * 12.3 - u * 3.1) +
          2.3 * Math.cos(u * 31 + v * 37) +
          2.8 * (rng() - 0.5);
        const edge = 1 - Math.abs(u) ** 1.4;
        const value = 118 + 2 * mottling;
        const k = 4 * (y * width + x);
        image.data[k] = relief ? value : 65 + 17 * edge + 10 * (1 - v) + mottling;
        image.data[k + 1] = relief ? value : 93 + 19 * edge + 8 * (1 - v) + mottling;
        image.data[k + 2] = relief ? value : 57 + 12 * edge + 4 * (1 - v) + mottling * 0.75;
        image.data[k + 3] = 255;
      }
    ctx.putImageData(image, 0, 0);
    ctx.lineCap = 'round';
    for (let side of [-1, 1]) {
      for (let i = 0; i < 6; i++) {
        const y0 = height * (0.028 + i * 0.132 + (side > 0 ? 0.023 : 0));
        const span = height * (0.24 - i * 0.012);
        const end = width * (0.486 + side * (0.473 - i * 0.014));
        ctx.strokeStyle = relief ? '#c5c5c5' : '#c1ca9f67';
        ctx.lineWidth = 2.2 - i * 0.16;
        ctx.beginPath();
        ctx.moveTo(width * 0.5, y0);
        ctx.bezierCurveTo(
          width * (0.5 + side * 0.13),
          y0 + span * 0.13,
          width * (0.5 + side * 0.24),
          y0 + span * 0.66,
          end,
          y0 + span,
        );
        ctx.stroke();
        ctx.strokeStyle = relief ? '#979797' : '#b1c1992d';
        ctx.lineWidth = 0.64;
        for (let j = 1; j <= 8; j++) {
          const t = j / 10,
            sx = width * (0.5 + side * t * 0.41),
            sy = y0 + span * t ** 1.42;
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.quadraticCurveTo(sx + side * 5, sy + 11, sx + side * 14, sy + 24 + j);
          ctx.stroke();
        }
      }
    }
    const rib = ctx.createLinearGradient(0, 0, 0, height);
    rib.addColorStop(0, relief ? '#e8e8e8' : '#d0cc947f');
    rib.addColorStop(1, relief ? '#9a9a9a' : '#c5cb9a26');
    ctx.fillStyle = rib;
    ctx.beginPath();
    ctx.moveTo(width * 0.5 - 2.6, 0);
    ctx.quadraticCurveTo(width * 0.5 - 1.2, height * 0.49, width * 0.5, height);
    ctx.quadraticCurveTo(width * 0.5 + 1.4, height * 0.37, width * 0.5 + 2.6, 0);
    ctx.fill();
  });
  if (relief) texture.colorSpace = T.NoColorSpace;
  return texture;
}

function petalPrint() {
  return canvasTexture(176, 176, (ctx) => {
    const radial = ctx.createLinearGradient(0, 0, 0, 176);
    radial.addColorStop(0, '#c47673');
    radial.addColorStop(0.38, '#f0c2bc');
    radial.addColorStop(1, '#ffe8d9');
    ctx.fillStyle = radial;
    ctx.fillRect(0, 0, 176, 176);
    const rng = random(135);
    ctx.strokeStyle = '#cb858538';
    ctx.lineWidth = 0.65;
    for (let i = 0; i < 32; i++) {
      const x = (i / 31) * 176;
      ctx.beginPath();
      ctx.moveTo(88, 0);
      ctx.bezierCurveTo(88 + (x - 88) * 0.62, 51, x + rng() * 14 - 7, 103, x, 172);
      ctx.stroke();
    }
  });
}

export function sillBotanicals(
  unit: T.Group,
  p: Palette,
  manager: T.LoadingManager,
  plantAt: XYZ,
  vaseAt: XYZ,
) {
  const specimen = group(unit, 'Heartleaf philodendron in a wheel-thrown pot', plantAt);
  const vessel = lunaVase(unit, vaseAt);
  const sprig = group(vessel.unit, 'Cut flowering quince');
  sprig.rotation.y = -0.88;
  const map = bladeTexture(false),
    bumpMap = bladeTexture(true);
  const leaves = ['#c7d8bb', '#e1dcc4', '#e6e9c0'].map(
    (color) =>
      new T.MeshPhysicalMaterial({
        color,
        map,
        bumpMap,
        bumpScale: 0.00014,
        roughness: 0.48,
        side: T.DoubleSide,
        clearcoat: 0.14,
        clearcoatRoughness: 0.42,
        specularIntensity: 0.53,
      }),
  );
  const clay = surface('#a87960', 0.88);
  clay.normalMap = p.plaster.normalMap;
  clay.normalScale.set(0.31, 0.31);
  const glaze = new T.MeshPhysicalMaterial({
    color: '#9a8c72',
    metalness: 0.03,
    roughness: 0.37,
    clearcoat: 0.54,
    clearcoatRoughness: 0.26,
  });
  glaze.normalMap = p.plaster.normalMap;
  glaze.normalScale.set(0.12, 0.12);
  const print = petalPrint();
  const petalSurface = (color: string) =>
    new T.MeshStandardMaterial({ map: print, color, roughness: 0.64, side: T.DoubleSide });
  const materials: Record<string, T.Material> = {
    clay,
    glaze,
    soil: surface('#332821', 0.98),
    bark: surface('#69503d', 0.92),
    grit: surface('#cbc0aa', 0.91),
    petiole: surface('#718157', 0.64),
    'leaf-green': leaves[0],
    'leaf-olive': leaves[1],
    'leaf-young': leaves[2],
    'q-wood': surface('#654e43', 0.84),
    'q-sepal': surface('#867c56', 0.72),
    'q-blush': petalSurface('#f8e5dd'),
    'q-rose': petalSurface('#eac7c0'),
    'q-filament': surface('#ede0c0', 0.69),
    'q-pollen': surface('#cf9e40', 0.68),
    'v-mark': surface('#847d6e', 0.61),
  };
  const colors = (materials: T.MeshStandardMaterial[]) =>
    materials.map((material) => ({ material, summer: material.color.clone() }));
  let foliage = colors(leaves);
  let lastTint: T.Color | undefined;
  void loadBlenderPack(manager, '/media/models/sill-botanicals.mesh.gz', (key, geometry) => {
    const parent = key === 'v-mark' ? vessel.unit : key.startsWith('q-') ? sprig : specimen;
    const part = mesh(parent, geometry, materials[key]);
    part.name = key;
    if (key === 'v-mark') part.userData.sillPart = key;
  }).catch(() => {
    unit.remove(specimen);
    vessel.unit.remove(sprig);
    foliage = colors(philodendron(unit, p, plantAt).leaves);
    lastTint = undefined;
    vessel.fallback();
  });
  return (tint: T.Color) => {
    if (tint === lastTint) return;
    lastTint = tint;
    for (const { material, summer } of foliage) material.color.copy(summer).multiply(tint);
  };
}
