import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  const images = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 2048;
    canvas.height = 576;
    const ctx = canvas.getContext('2d');
    const scale = canvas.width / (80 * Math.PI);
    ctx.scale(scale, scale);
    const length = 80 * Math.PI;
    const background = '#40524c';
    const white = '#eeede4';
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, length + 1, 72);
    ctx.fillStyle = ctx.strokeStyle = white;
    ctx.lineWidth = 0.26;
    ctx.lineCap = 'square';
    function line(points) {
      ctx.beginPath();
      points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.stroke();
    }
    function tree(x, y, r) {
      line([
        [x, y - r],
        [x - r * 0.83, y + r * 0.67],
        [x + r * 0.83, y + r * 0.67],
        [x, y - r],
      ]);
    }
    const pitch = length / 96;
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 96; col++) {
        const x = (col + 0.25) * pitch,
          y = 5.45 + row * 7.75;
        if (row === 3 && Math.abs(x - (length / 2 - 4.3)) < 22) continue;
        if (col % 3 !== 0) continue;
        const symbol = col / 3;
        if (symbol % 2 === 0) {
          for (const a of [-0.74, 0.74])
            for (const b of [-0.74, 0.74]) ctx.fillRect(x + a - 0.52, y + b - 0.55, 1.06, 1.12);
        } else if ((symbol + row * 4) % 10 === 3) {
          tree(x, y, 1.04);
        } else if ((symbol + row * 4) % 10 === 7) {
          ctx.beginPath();
          ctx.arc(x, y + 0.14, 0.89, 0.1, Math.PI - 0.1);
          ctx.stroke();
          line([
            [x, y - 0.88],
            [x, y + 0.9],
          ]);
          line([
            [x - 0.4, y - 0.6],
            [x + 0.4, y - 0.6],
          ]);
        } else {
          line([
            [x - 1, y],
            [x + 1, y],
          ]);
          line([
            [x, y - 1],
            [x, y + 1],
          ]);
        }
      }
    }
    const start = length / 2 - 26;
    let cursor = start;
    ctx.font = 'bold 3.35px "Century Gothic", Arial, sans-serif';
    for (const ch of 'SKANDINAVISK') {
      if (ch === 'A' && cursor < start + 10) tree(cursor + 1.05, 29.1, 1.25);
      else ctx.fillText(ch, cursor, 30.0);
      cursor += ctx.measureText(ch).width + 1.04;
    }
    ctx.font = '500 6.0px "Century Gothic", Arial, sans-serif';
    ctx.fillText('SKOG', start, 47);
    tree(start + 20.1, 44.5, 2.45);
    tree(start + 22.45, 44.7, 2.25);
    ctx.font = '2.47px "Century Gothic", Arial, sans-serif';
    ctx.fillText('Calm of the boreal forest', start, 51.4);
    const print = canvas.toDataURL('image/png');
    canvas.width = 96;
    canvas.height = 256;
    const fibre = ctx.createImageData(96, 256);
    for (let y = 0; y < 256; y++) {
      for (let x = 0; x < 96; x++) {
        const s = (2 * Math.PI * x) / 96,
          t = (2 * Math.PI * y) / 256;
        const a =
          1 +
          0.038 * Math.sin(s * 12 + 0.45 * Math.sin(t * 2 + s)) +
          0.021 * Math.cos(s * 31 + 0.3 * Math.sin(t + s)) +
          0.009 * Math.sin(t * 13 + s * 21);
        const j = 4 * (y * 96 + x);
        [220, 188, 146].forEach((c, k) => (fibre.data[j + k] = Math.round(a * c)));
        fibre.data[j + 3] = 255;
      }
    }
    ctx.putImageData(fibre, 0, 0);
    const longGrain = canvas.toDataURL('image/png');
    canvas.height = 96;
    ctx.fillStyle = '#d1b58e';
    ctx.fillRect(0, 0, 96, 96);
    for (let i = 1; i < 97; i++) {
      const a = i * 2.399963,
        r = 47 * Math.sqrt(i / 97);
      ctx.beginPath();
      ctx.fillStyle = i % 4 === 0 ? '#a38a6d' : '#bd9f7d';
      ctx.ellipse(
        48 + r * Math.cos(a),
        48 + r * Math.sin(a),
        i % 4 === 0 ? 1.7 : 0.9,
        i % 4 === 0 ? 1.3 : 0.7,
        a,
        0,
        Math.PI * 2,
      );
      ctx.fill();
    }
    return [print, longGrain, canvas.toDataURL('image/png')];
  });
  for (const [i, name] of ['skog-vessel.png', 'skog-fibre.png', 'skog-reed-end.png'].entries()) {
    await writeFile(join(process.argv[2], name), Buffer.from(images[i].split(',')[1], 'base64'));
  }
} finally {
  await browser.close();
}
