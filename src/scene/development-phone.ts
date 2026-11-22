import * as T from 'three';
import { box, canvasTexture, group, mesh, surface, tube } from './geometry';
import type { Palette } from './materials';
import type { Locale } from '../app/locale';
import { blenderMesh } from './blender-mesh';

export const phoneDisplay = {
  width: 0.0744,
  height: 0.1595,
  depth: 0.00451,
  viewportWidth: 390,
  viewportHeight: 844,
};

function roundedPlate(w: number, h: number, r: number, d: number) {
  const outline = new T.Shape(),
    x = w / 2,
    y = h / 2;
  outline.moveTo(-x + r, -y);
  outline.lineTo(x - r, -y);
  outline.quadraticCurveTo(x, -y, x, -y + r);
  outline.lineTo(x, y - r);
  outline.quadraticCurveTo(x, y, x - r, y);
  outline.lineTo(-x + r, y);
  outline.quadraticCurveTo(-x, y, -x, y - r);
  outline.lineTo(-x, -y + r);
  outline.quadraticCurveTo(-x, -y, -x + r, -y);
  return new T.ExtrudeGeometry(outline, {
    depth: d,
    bevelEnabled: true,
    bevelThickness: 0.00036,
    bevelSize: 0.00034,
    bevelSegments: 3,
    curveSegments: 10,
  });
}

export function developmentPhone(parent: T.Group, p: Palette, wallpaper: T.Texture) {
  const dock = group(parent, 'Weighted wireless charging stand', [0.389, 0.75, 0.034]);
  dock.rotation.y = -0.23;
  const metal = p.steel.clone();
  metal.color.set('#8c8982');
  metal.roughness = 0.35;
  const base = mesh(dock, roundedPlate(0.075, 0.081, 0.012, 0.0046), metal, [0, 0.002, 0]);
  base.rotation.x = -Math.PI / 2;
  box(dock, [0.061, 0.002, 0.064], [0, 0.001, 0], p.rubber, 0.0009);
  const stem = box(dock, [0.025, 0.077, 0.006], [0, 0.043, -0.018], metal, 0.0026);
  stem.rotation.x = -0.19;
  const disc = group(dock, 'Inductive puck', [0, 0.091, -0.016]);
  disc.rotation.x = -0.19;
  tube(disc, [0, 0, -0.007], [0, 0, 0.001], 0.0255, metal);
  tube(disc, [0, 0, 0], [0, 0, 0.002], 0.0246, p.rubber);
  const phone = group(dock, 'iPhone 18 Pro Max', [0, 0.091, -0.0085]);
  phone.rotation.x = -0.19;
  const glass = new T.MeshPhysicalMaterial({
    color: '#101416',
    roughness: 0.13,
    clearcoat: 1,
    clearcoatRoughness: 0.1,
  });
  const finishes: Record<string, T.Material> = {
    alloy: surface('#555653', 0.31, 0.79),
    glass,
    back: surface('#343534', 0.53, 0.36),
    optic: surface('#19303b', 0.095, 0.67),
    flash: surface('#e2dcc0', 0.39),
  };
  for (const [part, material] of Object.entries(finishes))
    mesh(phone, blenderMesh('handheld/iphone18-' + part), material);
  const screen = canvasTexture(645, 1398, () => {});
  const material = new T.MeshBasicMaterial({
    map: screen,
    transparent: true,
    alphaTest: 0.25,
    toneMapped: false,
  });
  const display = mesh(
    phone,
    new T.PlaneGeometry(phoneDisplay.width, phoneDisplay.height),
    material,
    [0, 0, phoneDisplay.depth],
  );
  display.name = 'iPhone lock screen';
  display.castShadow = false;
  const ctx = (screen.image as HTMLCanvasElement).getContext('2d')!;
  let lastMinute = -1,
    lastLocale: Locale | undefined,
    ready = false;
  const formatters = new Map<Locale, Intl.DateTimeFormat>();
  function update(locale: Locale) {
    const now = Date.now(),
      minute = Math.floor(now / 60000);
    const photo = wallpaper.image as HTMLImageElement | undefined;
    const hasImage = Boolean(photo?.naturalWidth);
    if (lastMinute === minute && lastLocale === locale && hasImage === ready) return;
    lastMinute = minute;
    lastLocale = locale;
    ready = hasImage;
    ctx.clearRect(0, 0, 645, 1398);
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(0, 0, 645, 1398, 87);
    ctx.clip();
    ctx.fillStyle = '#455052';
    ctx.fillRect(0, 0, 645, 1398);
    if (photo?.naturalWidth) {
      const scale = Math.max(645 / photo.naturalWidth, 1398 / photo.naturalHeight);
      const w = scale * photo.naturalWidth,
        h = scale * photo.naturalHeight;
      ctx.drawImage(photo, (645 - w) / 2, (1398 - h) / 2, w, h);
    }
    const grad = ctx.createLinearGradient(0, 0, 0, 1398);
    grad.addColorStop(0, '#16212495');
    grad.addColorStop(0.49, '#16212415');
    grad.addColorStop(1, '#18242780');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 645, 1398);
    ctx.fillStyle = '#0b0c0c';
    ctx.beginPath();
    ctx.roundRect(238, 22, 169, 42, 22);
    ctx.fill();
    ctx.fillStyle = '#20262a';
    ctx.beginPath();
    ctx.arc(385, 43, 7, 0, Math.PI * 2);
    ctx.fill();
    if (!formatters.has(locale))
      formatters.set(
        locale,
        new Intl.DateTimeFormat(locale === 'en' ? 'en-GB' : 'zh-CN', {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
        }),
      );
    const date = new Date(now);
    ctx.fillStyle = '#f7f4e8';
    ctx.textAlign = 'center';
    ctx.font = '500 30px Arial';
    ctx.fillText(formatters.get(locale)!.format(date), 322, 160);
    const time = [date.getHours(), date.getMinutes()]
      .map((n) => String(n).padStart(2, '0'))
      .join(':');
    ctx.font = '600 145px Arial';
    ctx.fillText(time, 322, 300);
    ctx.strokeStyle = '#f1f2eb';
    ctx.lineWidth = 3;
    ctx.fillStyle = '#222c2f75';
    for (const x of [91, 554]) {
      ctx.beginPath();
      ctx.arc(x, 1278, 36, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.beginPath();
    ctx.roundRect(543, 1270, 23, 16, 3);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(555, 1278, 4, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = '#edf0e9';
    ctx.fillRect(548, 1267, 9, 4);
    ctx.beginPath();
    ctx.roundRect(87, 1273, 8, 17, 3);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(83, 1267);
    ctx.lineTo(99, 1267);
    ctx.lineTo(95, 1274);
    ctx.lineTo(87, 1274);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.roundRect(219, 1366, 207, 7, 4);
    ctx.fill();
    ctx.restore();
    screen.needsUpdate = true;
  }
  update('en');
  return { phone, update };
}
