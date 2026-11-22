import * as T from 'three';
import type { Locale } from '../app/locale';

export function oledLockScreen() {
  const density = 6;
  const canvas = document.createElement('canvas');
  canvas.width = 240 * density;
  canvas.height = 128 * density;
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
  ctx.scale(density, density);
  ctx.textAlign = 'center';
  ctx.fillStyle = 'white';
  const coverage = new Uint8Array(canvas.width * canvas.height);
  const texture = new T.DataTexture(coverage, canvas.width, canvas.height, T.RedFormat);
  texture.generateMipmaps = true;
  texture.magFilter = T.LinearFilter;
  texture.minFilter = T.LinearMipmapLinearFilter;
  texture.anisotropy = 8;
  let lastMinute = -1;
  let lastLocale: Locale | undefined;
  function update(locale: Locale) {
    const minute = Math.floor(Date.now() / 60_000);
    if (minute === lastMinute && locale === lastLocale) return;
    lastMinute = minute;
    lastLocale = locale;
    const now = new Date();
    const language = locale === 'en' ? 'en-GB' : 'zh-CN';
    ctx.clearRect(0, 0, 240, 128);
    ctx.font = '500 13px "IBM Plex Sans", "Studio Han", sans-serif';
    ctx.fillText(
      new Intl.DateTimeFormat(language, {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      }).format(now),
      120,
      22,
    );
    ctx.font = '500 65px "IBM Plex Sans", sans-serif';
    ctx.fillText(
      new Intl.DateTimeFormat(language, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(now),
      120,
      89,
    );
    ctx.font = '500 12px "IBM Plex Sans", sans-serif';
    ctx.fillText('Felix Studio', 120, 122);
    const rgba = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    for (let pixel = 0; pixel < coverage.length; pixel++) coverage[pixel] = rgba[pixel * 4 + 3];
    texture.needsUpdate = true;
    if (document.fonts.status === 'loading') {
      void document.fonts.ready.then(() => {
        lastMinute = -1;
      });
    }
  }
  update('en');
  return { texture, update };
}
