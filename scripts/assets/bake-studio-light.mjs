import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

function scanline(values) {
  const packets = [];
  let position = 0;
  while (position < values.length) {
    let length = 1;
    while (length < 127 && values[position] === values[position + length]) length++;
    if (length >= 3) {
      packets.push(128 + length, values[position]);
    } else {
      length = 1;
      while (length < 128 && position + length < values.length) {
        const i = position + length;
        if (values[i] === values[i + 1] && values[i] === values[i + 2]) break;
        length++;
      }
      packets.push(length, ...values.subarray(position, position + length));
    }
    position += length;
  }
  return Buffer.from(packets);
}

function encodeRadiance(pixels, width, height) {
  const parts = [Buffer.from(`#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y ${height} +X ${width}\n`)];
  for (let y = height - 1; y >= 0; y--) {
    parts.push(Buffer.from([2, 2, width >> 8, width & 255]));
    for (let channel = 0; channel < 4; channel++) {
      const row = Uint8Array.from(
        { length: width },
        (_, x) => pixels[(y * width + x) * 4 + channel],
      );
      parts.push(scanline(row));
    }
  }
  return Buffer.concat(parts);
}

function diffusePreview(pixels, width, height) {
  const previewWidth = 16,
    previewHeight = 8;
  const sums = new Float64Array(previewWidth * previewHeight * 4);
  for (let y = 0; y < height; y++) {
    const weight = Math.sin((Math.PI * (y + 0.5)) / height);
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      const j =
        (Math.floor((y * previewHeight) / height) * previewWidth +
          Math.floor((x * previewWidth) / width)) *
        4;
      const scale = 2 ** (pixels[i + 3] - 136);
      for (let c = 0; c < 3; c++) sums[j + c] += pixels[i + c] * weight * scale;
      sums[j + 3] += weight;
    }
  }
  const result = Buffer.alloc(sums.length);
  for (let j = 0; j < sums.length; j += 4) {
    const peak = Math.max(...sums.subarray(j, j + 3)) / sums[j + 3];
    if (peak < 1e-30) continue;
    const exponent = Math.floor(Math.log2(peak)) + 1;
    for (let c = 0; c < 3; c++)
      result[j + c] = Math.floor((sums[j + c] / sums[j + 3]) * 2 ** (8 - exponent));
    result[j + 3] = exponent + 128;
  }
  return result.toString('base64');
}

const studioUrl = new URL('/?review=lighting', process.argv[2] ?? 'http://127.0.0.1:5173');
const location = process.argv[3] ?? 'desk';
if (!['desk', 'aj', 'camp'].includes(location)) throw new Error('Unknown studio lighting probe');
const browser = await chromium.launch({
  channel: 'chrome',
  args: ['--enable-gpu', '--mute-audio'],
});
const previews = {};
try {
  await mkdir('public/media/lighting', { recursive: true });
  for (const night of [false, true]) {
    const name = night ? 'night' : 'day';
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    page.on('pageerror', (error) => console.error(error));
    await page.addInitScript((night) => {
      localStorage.setItem(
        'felix-studio-v1',
        JSON.stringify({
          night,
          weather: night ? '雨' : '晴',
          city: '上海',
          blinds: false,
          reducedMotion: true,
          quality: 'high',
          rainAudio: false,
        }),
      );
    }, night);
    await page.goto(studioUrl.href);
    await page.waitForFunction(
      () => window.__studioReview?.captureLighting && !document.querySelector('.studio-loading'),
      undefined,
      { timeout: 120000 },
    );
    const { width, height, rgbe } = await page.evaluate(
      (location) => window.__studioReview.captureLighting(location),
      location,
    );
    const pixels = Buffer.from(rgbe, 'base64');
    const hdr = encodeRadiance(pixels, width, height);
    await writeFile(`public/media/lighting/${location}-${name}.hdr`, hdr);
    previews[name] = diffusePreview(pixels, width, height);
    console.log(`Baked ${name} reflection · ${width} × ${height} · ${hdr.length} bytes`);
    await page.close();
  }
  if (location === 'desk')
    await writeFile('src/scene/desk-radiance.json', JSON.stringify(previews, null, 2) + '\n');
} finally {
  await browser.close();
}
