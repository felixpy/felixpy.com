import type { BookEdition } from '../content/books';
import { rearNotes } from '../content/book-rear-notes';
import { rearLayouts, type PrintBlock, type RearLayout } from '../content/book-rear-layouts';
import { random } from './geometry';
import { belovedRearArtwork, belovedSpine } from './beloved-binding';
import { sicpBinding } from './sicp-binding';

const oddDigits = [
  '0001101',
  '0011001',
  '0010011',
  '0111101',
  '0100011',
  '0110001',
  '0101111',
  '0111011',
  '0110111',
  '0001011',
];
const rightDigits = oddDigits.map((digit) =>
  digit.replace(/[01]/g, (bar) => (bar === '1' ? '0' : '1')),
);
const evenDigits = rightDigits.map((digit) => Array.from(digit).reverse().join(''));
const addOnParity = [
  'GGLLL',
  'GLGLL',
  'GLLGL',
  'GLLLG',
  'LGGLL',
  'LLGGL',
  'LLLGG',
  'LGLGL',
  'LGLLG',
  'LLGLG',
];

export function printedBars(
  ctx: CanvasRenderingContext2D,
  value: string,
  x: number,
  y: number,
  width: number,
  height: number,
  alignModules = false,
) {
  let bits: string;
  if (value.length === 5) {
    const check =
      Array.from(value).reduce((sum, d, i) => sum + Number(d) * (i % 2 ? 9 : 3), 0) % 10;
    bits =
      '1011' +
      Array.from(
        value,
        (d, i) => (addOnParity[check][i] === 'G' ? evenDigits : oddDigits)[Number(d)],
      ).join('01');
  } else {
    bits =
      '101' +
      Array.from(
        value.slice(1, 7),
        (d, i) => ('LGGLGL'[i] === 'G' ? evenDigits : oddDigits)[Number(d)],
      ).join('') +
      '01010' +
      Array.from(value.slice(7), (d) => rightDigits[Number(d)]).join('') +
      '101';
  }
  const module = width / bits.length;
  const scale = alignModules ? ctx.getTransform().a : 0;
  const deviceModule = Math.floor(module * scale);
  const origin = deviceModule
    ? Math.round((x + width / 2) * scale - (bits.length * deviceModule) / 2)
    : 0;
  for (let i = 0; i < bits.length; i++) {
    if (bits[i] !== '1') continue;
    if (deviceModule) {
      ctx.fillRect((origin + i * deviceModule) / scale, y, deviceModule / scale, height);
    } else {
      ctx.fillRect(x + i * module, y, module, height);
    }
  }
}

function rubinBack(ctx: CanvasRenderingContext2D, book: BookEdition) {
  const tile = document.createElement('canvas');
  tile.width = tile.height = 64;
  const weave = tile.getContext('2d')!;
  const fibers = weave.createImageData(64, 64);
  const rng = random(3617);
  for (let y = 0; y < 64; y++) {
    for (let x = 0; x < 64; x++) {
      const warp = ((x >> 2) + (y >> 2)) % 2 === 0;
      const thread = Math.cos(((warp ? x : y) * Math.PI) / 2);
      const luminance = 202 + thread * 8 + (rng() - 0.5) * 19;
      fibers.data.set([luminance + 1, luminance + 2, luminance - 6, 255], (64 * y + x) * 4);
    }
  }
  weave.putImageData(fibers, 0, 0);
  ctx.save();
  ctx.scale(0.28, 0.33);
  ctx.fillStyle = ctx.createPattern(tile, 'repeat')!;
  ctx.fillRect(0, 0, 288 / 0.28, 512 / 0.33);
  ctx.restore();

  ctx.fillStyle = 'rgba(10,13,12,.94)';
  ctx.beginPath();
  ctx.ellipse(135, 257, 110, 136, 0, 0, 2 * Math.PI);
  ctx.ellipse(135, 257, 100, 123, 0, 0, 2 * Math.PI);
  ctx.fill('evenodd');

  ctx.fillStyle = '#ecebe7';
  ctx.beginPath();
  ctx.roundRect(87, 404, 119, 88, 5);
  ctx.fill();
  ctx.fillStyle = '#1e2021';
  ctx.font = 'bold 6.7px Georgia,serif';
  ctx.fillText('U.S. $32.00    Canada $42.00', 98, 417, 83);
  ctx.font = '4.9px Arial,sans-serif';
  ctx.fillText('ISBN 978-0-593-65288-6', 99, 427);
  printedBars(ctx, book.identifier, 99, 429, 46, 44);
  printedBars(ctx, '53200', 150, 432, 25, 41);
  ctx.font = '5.6px monospace';
  ctx.fillText('9 780593 652886', 94, 479, 52);
  ctx.fillText('53200', 152, 431, 22);
  ctx.font = '4.6px monospace';
  ctx.fillText('0123', 183, 450);
  ctx.beginPath();
  ctx.ellipse(190, 465, 7, 12, 0, 0, Math.PI * 2);
  ctx.lineWidth = 0.6;
  ctx.strokeStyle = '#252726';
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(188, 457);
  ctx.quadraticCurveTo(192, 452, 193, 460);
  ctx.quadraticCurveTo(197, 468, 194, 472);
  ctx.lineTo(191, 471);
  ctx.lineTo(187, 473);
  ctx.quadraticCurveTo(185, 470, 188, 461);
  ctx.lineTo(186, 458);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#ecebe7';
  ctx.beginPath();
  ctx.ellipse(190.5, 465.5, 2.6, 5.7, 0, 0, 2 * Math.PI);
  ctx.fill();
}

function cLanguageBack(ctx: CanvasRenderingContext2D, book: BookEdition) {
  ctx.fillStyle = '#f3f1ed';
  ctx.fillRect(0, 0, 288, 512);
  ctx.textAlign = 'center';
  ctx.fillStyle = '#374f96';
  ctx.font = 'bold 13px Georgia,serif';
  ctx.fillText(book.en, 144, 93, 145);
  ctx.font = 'bold 9px Georgia,serif';
  ctx.fillText('Second Edition', 144, 107, 94);
  ctx.font = 'bold 10px Georgia,serif';
  ctx.fillText('Brian W. Kernighan/Dennis M. Ritchie', 144, 123, 143);

  ctx.textAlign = 'left';
  ctx.fillStyle = '#ac5154';
  ctx.font = '7.5px Georgia,serif';
  ctx.fillText('From the Preface', 48, 150);
  const rng = random(110362);
  ctx.fillStyle = '#3a3740';
  for (const [row, length] of [195, 192, 194, 192, 195, 194, 138, 0, 191, 193, 111].entries()) {
    const baseline = 166 + row * 9.2;
    let x = 48;
    while (x < 46 + length) {
      const letters = 2 + Math.floor(rng() * 8);
      for (let i = 0; i < letters && x < 46 + length; i++) {
        const height = 2.7 + rng() * 2;
        ctx.fillRect(x, baseline - height, 0.48, height);
        ctx.fillRect(x, baseline - height * (0.35 + rng() * 0.5), 0.6 + rng() * 0.7, 0.5);
        ctx.fillRect(x, baseline - 0.55, 0.7 + rng() * 0.5, 0.55);
        x += 1.1 + rng() * 0.9;
      }
      x += 1.5;
    }
  }
  ctx.fillStyle = '#374f96';
  ctx.textAlign = 'center';
  ctx.font = 'bold 7.7px Georgia,serif';
  ctx.fillText('Also available from Prentice Hall:', 144, 279);
  ctx.font = '7.5px Georgia,serif';
  ctx.fillText('SECOND EDITION', 144, 288);
  ctx.fillRect(88, 294, 112, 0.65);
  ctx.fillText('THE C ANSWER BOOK', 144, 307);
  ctx.fillText('Solutions to the Exercises in', 144, 316);
  ctx.fillText('The C Programming Language, second edition', 144, 326, 118);
  ctx.fillText('by Brian W. Kernighan & Dennis M. Ritchie', 144, 336, 116);
  ctx.fillRect(88, 340, 112, 0.65);
  ctx.font = 'bold 7.6px Georgia,serif';
  ctx.fillText('CLOVIS L. TONDO', 144, 353);
  ctx.fillText('SCOTT E. GIMPEL', 144, 362);
  ctx.fillText('Prentice Hall P T R, Englewood Cliffs, New Jersey 07632', 144, 405, 157);
  ctx.fillStyle = '#282726';
  ctx.textAlign = 'left';
  ctx.font = '6.5px monospace';
  ctx.fillText('ISBN 0-13-110362-8', 192, 431, 74);
  printedBars(ctx, book.identifier, 192, 438, 46, 47);
  printedBars(ctx, '90000', 243, 444, 23, 41);
  ctx.font = '5.8px monospace';
  ctx.fillText('9 780131 103627', 187, 490, 51);
  ctx.fillText('90000', 245, 442, 22);
}

const percentageX = 2.88;
const percentageY = 5.12;
function paragraph(
  ctx: CanvasRenderingContext2D,
  block: PrintBlock,
  defaultInk: string,
  serif: boolean,
  copy: string,
  glyphScale: number,
  bold = false,
) {
  const width = (block.width * percentageX) / glyphScale;
  const leading = (block.height * percentageY) / block.lines;
  const font = serif ? 'Georgia,serif' : 'Arial,sans-serif';
  const words = copy.split(/\s+/);
  let size = leading * 0.83;
  let lines: string[] = [];
  for (;;) {
    ctx.font = (bold ? 'bold ' : '') + size + 'px ' + font;
    lines = [];
    let line = '';
    for (const word of words) {
      const next = line ? line + ' ' + word : word;
      if (line && ctx.measureText(next).width > width) {
        lines.push(line);
        line = word;
      } else {
        line = next;
      }
    }
    if (line) lines.push(line);
    if (lines.length <= block.lines || size <= 1.8) break;
    size *= 0.93;
  }
  const center = block.alignment === 'center';
  ctx.fillStyle = block.color ?? defaultInk;
  ctx.textAlign = block.alignment;
  const x = (block.x * percentageX) / glyphScale + (center ? width / 2 : 0);
  const top = block.y * percentageY + size;
  ctx.save();
  ctx.scale(glyphScale, 1);
  for (const [i, line] of lines.entries()) ctx.fillText(line, x, top + i * leading, width);
  ctx.restore();
}

function waysPictureStrip(ctx: CanvasRenderingContext2D) {
  const grain = random(1972);
  function panel(
    x: number,
    y: number,
    width: number,
    height: number,
    paper: string,
    draw: () => void,
  ) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(width / 100, height / 100);
    ctx.beginPath();
    ctx.rect(0, 0, 100, 100);
    ctx.clip();
    ctx.fillStyle = paper;
    ctx.fillRect(0, 0, 100, 100);
    draw();
    for (let i = 0; i < 470; i++) {
      ctx.fillStyle = i % 2 ? 'rgba(255,255,250,.24)' : 'rgba(22,21,20,.19)';
      ctx.fillRect(grain() * 100, grain() * 100, 0.4 + grain() * 1.25, 0.9);
    }
    ctx.restore();
  }
  function shape(color: string, path: string) {
    ctx.fillStyle = color;
    ctx.fill(new Path2D(path));
  }
  function line(color: string, width: number, path: string) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke(new Path2D(path));
  }
  panel(29, 322, 43, 76, '#353638', () => {
    shape('#656461', 'M0 46Q10 18 25 12Q65 -5 96 30L100 60Q83 48 63 47Q29 42 0 62Z');
    shape('#232322', 'M13 89Q15 62 28 46L42 37Q32 31 43 19Q58 10 66 24L71 38L83 56L91 92Z');
    shape(
      '#a6a39a',
      'M46 24Q52 16 60 23L61 31L56 37L47 34Z M39 44L46 38Q56 45 63 39L69 44Q58 54 39 44Z',
    );
    shape('#84827a', 'M13 91L35 79L54 77L74 84L58 94L34 93Z M65 55Q69 51 71 53L65 67L51 70L49 67Z');
    line(
      '#b5b1a5',
      1.1,
      'M26 84Q39 83 51 88L68 82 M24 87L50 91L64 86 M31 51Q23 63 29 78 M37 49Q50 59 65 47 M48 27L51 27 M55 26L59 26 M52 32L56 32 M39 22Q42 12 54 13 M39 24Q40 10 52 10 M35 49Q35 67 26 76 M39 54Q40 67 33 76 M43 57Q48 66 57 64 M62 48L70 52L67 57 M26 82L46 86 M32 80L51 84 M60 83L67 80',
    );
  });
  panel(76, 322, 41, 76, '#e9e6da', () => {
    line(
      '#353435',
      1.65,
      'M44 10Q39 1 49 3Q63 3 61 15Q60 26 51 25Q44 23 44 10Z M47 17Q52 22 56 16 M45 27Q32 29 24 41Q13 55 30 58Q51 63 65 53Q75 41 58 30Q51 26 45 27Z M31 34L18 23L14 12 M18 23L22 14 M63 32L82 19L84 10 M82 19L91 14 M39 59Q33 65 18 76L11 87 M46 59L60 69L69 78L74 74',
    );
    shape('#252625', 'M75 64L83 62L89 69L86 76L78 78L71 72Z');
    line(
      '#464440',
      1.9,
      'M4 13L8 6L13 12 M64 7L68 3L73 8 M4 97L6 85L12 85 M5 90L10 90 M15 91Q16 83 22 86Q25 94 19 97Q14 97 15 91Z M26 90Q28 83 33 86Q37 94 31 97Q26 96 26 90Z M38 86L48 85 M43 86L42 98 M51 97L53 85Q65 83 58 90Q68 95 51 97Z M64 97L70 85L76 97 M67 93L73 93 M79 85L78 97L86 97 M89 85L87 96L97 98',
    );
  });
  panel(121, 328, 80, 64, '#b4b2aa', () => {
    shape('#8d8c86', 'M0 2L23 0L24 33L19 38L18 58H0Z M35 0L59 0L56 37L38 45Z M76 0H100V64L81 52Z');
    shape(
      '#373836',
      'M0 75L11 55L27 52Q43 26 59 35L67 45L82 40Q92 37 99 45L100 83L72 89L58 79L38 92L0 90Z',
    );
    shape(
      '#242423',
      'M4 63L17 38Q23 29 32 36L41 40L35 55L20 54L15 66Z M43 57L57 44L67 42L75 59L69 68L49 70Z',
    );
    shape(
      '#bcb9ad',
      'M27 32Q23 23 32 22Q39 24 35 31L32 35Z M65 42Q63 37 68 35Q76 36 75 41L70 45Z M39 41L37 49L28 53L27 51Z M51 61L63 54L65 57L54 64Z',
    );
    line(
      '#6f6f6a',
      1.25,
      'M0 77L30 69L64 75L97 63 M10 79L48 77 M11 88L51 85 M80 49L89 66 M86 48L97 65 M88 42L100 56',
    );
  });
  panel(211, 316, 64, 82, '#303232', () => {
    shape('#888984', 'M0 65Q41 62 65 65L100 64V100H0Z');
    line('#c6c3b8', 0.8, 'M0 66L100 65 M7 79L90 77 M28 94L97 92');
    shape(
      '#4f5150',
      'M72 47Q74 41 79 42L82 47L78 52L89 60L86 72L77 81L74 78L81 65L72 61L68 70L60 67L69 55Z',
    );
    shape(
      '#d4d0c3',
      'M32 42L28 35L24 14L25 4L29 5L30 25L36 35L45 36L50 33L56 16L55 3L59 2L61 17L56 40L51 46L50 62L35 65Z',
    );
    shape(
      '#908c81',
      'M36 32Q32 23 37 21Q43 18 46 24L45 32L41 35Z M37 63L45 63L49 72L60 78L56 82L41 73Z M46 62L52 60L58 69L65 72L64 76L54 75Z',
    );
    line('#dfd9ca', 3.1, 'M57 82L65 91L60 94 M64 76L71 71L73 70');
  });
}

function pictorialDetails(ctx: CanvasRenderingContext2D, key: string) {
  ctx.save();
  if (key === 'beloved') {
    belovedRearArtwork(ctx);
  } else if (key === 'data-intensive') {
    const qr = [
      0x1fdefe7f, 0x105af441, 0x1744f75d, 0x17503a5d, 0x174eda5d, 0x10406f41, 0x1fd5557f,
      0x001dfe00, 0x16e2dc4b, 0x0d312f71, 0x06f44416, 0x052ed439, 0x0af40c0c, 0x109e8243,
      0x17595edf, 0x142aa322, 0x09dd1bb2, 0x0a8bb406, 0x14ee35ec, 0x01931984, 0x0ede89fc,
      0x001ee31f, 0x1fdda75a, 0x10553d10, 0x174751ff, 0x1755ed9e, 0x17599925, 0x104d356a,
      0x1fdac30a,
    ];
    ctx.fillStyle = '#1c1b19';
    for (const [row, bits] of qr.entries()) {
      for (let col = 0; col < 29; col++) {
        if (bits & (1 << (28 - col))) ctx.fillRect(145 + col * 1.72, 427 + row * 2.34, 1.73, 2.35);
      }
    }
  } else if (key === 'art-innovation') {
    ctx.strokeStyle = '#a7a393';
    ctx.lineWidth = 0.48;
    ctx.stroke(new Path2D('M187 493L191 481L196 493Z'));
  } else if (key === 'invisible-women') {
    ctx.fillStyle = '#332f29';
    ctx.beginPath();
    ctx.ellipse(43, 471, 10, 12, -0.25, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#f5efdf';
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.ellipse(43, 471, 8.2, 9.6, -0.25, 0, Math.PI * 2);
    ctx.moveTo(38, 477);
    ctx.lineTo(43.9, 464);
    ctx.lineTo(47.5, 475);
    ctx.moveTo(40, 472);
    ctx.lineTo(46, 471);
    ctx.stroke();
  } else if (key === 'information') {
    ctx.fillStyle = '#1b1b19';
    ctx.fill(
      new Path2D(
        'M288 74C216 130 136 268 164 398L245 398C232 335 239 268 288 207Z M189 486L258 486L257 460L281 512H201Z',
      ),
    );
  } else if (key === 'thinking-systems') {
    ctx.fillStyle = '#b4b2a1';
    ctx.beginPath();
    ctx.ellipse(312, 268, 86, 100, -0.28, 0, Math.PI * 2);
    ctx.fill();
    const spring = [
      '#6b9292',
      '#737d93',
      '#856b86',
      '#a05c7a',
      '#ba536c',
      '#d24e58',
      '#e5504b',
      '#ed5c4d',
    ];
    for (const [n, color] of spring.entries()) {
      ctx.beginPath();
      ctx.ellipse(351 + n * 1.6, 246 - n * 2.8, 115 - n * 4.1, 125 - n, -0.3, 0, Math.PI * 2);
      ctx.strokeStyle = color;
      ctx.lineWidth = 3.8;
      ctx.stroke();
    }
    ctx.fillStyle = '#859563';
    ctx.fillRect(154, 184, 59, 71);
    const trees = random(557);
    for (let i = 0; i < 45; i++) {
      ctx.fillStyle = trees() > 0.52 ? '#9aa77a' : '#758559';
      ctx.fillRect(154 + trees() * 57, 184 + trees() * 65, 1.5, 2);
    }
    ctx.fillStyle = '#735b72';
    ctx.fill(new Path2D('M154 255V243Q158 228 174 220L189 218Q206 221 213 243V255Z'));
    ctx.fillStyle = '#c99474';
    ctx.fill(
      new Path2D(
        'M173 202Q176 192 188 197Q196 200 197 211L191 214Q187 224 180 224Q173 220 173 214Z',
      ),
    );
    ctx.fillStyle = '#4c403a';
    ctx.fill(
      new Path2D(
        'M168 212Q168 192 179 189Q193 187 197 202L189 201L183 199L179 205L172 205L174 218Z',
      ),
    );
  } else if (key === 'ways') {
    waysPictureStrip(ctx);
  } else if (key === 'mythical') {
    ctx.strokeStyle = '#b0976b';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.ellipse(66, 92, 33, 31, -0.28, 0, Math.PI * 2);
    ctx.stroke();
  } else if (key === 'dune') {
    const stars = random(2719);
    for (let i = 0; i < 48; i++) {
      const x = stars() * 288,
        y = stars() * 512;
      ctx.fillStyle = stars() < 0.65 ? '#a17a47' : '#d9cbb2';
      const size = stars() < 0.82 ? 0.85 : 1.6;
      ctx.fillRect(x, y, size, size);
    }
  } else if (key === 'neuromancer') {
    ctx.strokeStyle = '#1c241b';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(242, 386);
    ctx.bezierCurveTo(268, 372, 269, 416, 247, 464);
    ctx.bezierCurveTo(236, 484, 230, 511, 230, 522);
    ctx.moveTo(229, 515);
    ctx.bezierCurveTo(234, 473, 265, 451, 265, 514);
    ctx.stroke();
  } else if (key === 'code') {
    ctx.fillStyle = '#d9ba77';
    ctx.font = '7.4px monospace';
    ctx.textAlign = 'center';
    for (const [i, letter] of Array.from('CODE').entries()) {
      const x = 54 + i * 60;
      ctx.fillText(letter.charCodeAt(0).toString(2).padStart(7, '0'), x, 73);
      ctx.fillText(['−·−·', '−−−', '−··', '·'][i], x, 83);
    }
  } else if (key === 'left-brain') {
    ctx.strokeStyle = '#5e5b4c';
    ctx.lineWidth = 1.3;
    const branches = random(148);
    const tree = (x: number, y: number, angle: number, length: number, depth: number) => {
      const tipX = x + Math.sin(angle) * length,
        tipY = y - Math.cos(angle) * length;
      ctx.moveTo(x, y);
      ctx.lineTo(tipX, tipY);
      if (!depth) return;
      tree(tipX, tipY, angle - 0.37 - branches() * 0.35, length * 0.67, depth - 1);
      tree(tipX, tipY, angle + 0.3 + branches() * 0.37, length * 0.68, depth - 1);
    };
    ctx.fillStyle = '#efece0';
    ctx.fillRect(19, 212, 40, 34);
    ctx.beginPath();
    tree(38, 245, 0, 12, 5);
    ctx.stroke();
  }
  ctx.restore();
}

function measuredBack(
  ctx: CanvasRenderingContext2D,
  book: BookEdition,
  layout: RearLayout,
  includeParagraphs: boolean,
) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, 288, 512);
  ctx.clip();
  if (layout.fade) {
    const fade = ctx.createLinearGradient(0, 0, 0, 512);
    fade.addColorStop(0, layout.paper);
    fade.addColorStop(layout.fade.start, layout.paper);
    fade.addColorStop(1, layout.fade.bottom);
    ctx.fillStyle = fade;
  } else {
    ctx.fillStyle = layout.paper;
  }
  ctx.fillRect(0, 0, 288, 512);
  for (const field of layout.fields ?? []) {
    const width = field.width * percentageX,
      height = field.height * percentageY;
    ctx.save();
    ctx.translate(field.x * percentageX + width / 2, field.y * percentageY + height / 2);
    ctx.rotate((field.tilt * Math.PI) / 180);
    ctx.fillStyle = field.color;
    ctx.fillRect(-width / 2, -height / 2, width, height);
    ctx.restore();
  }
  const paragraphs = rearNotes[book.key] ?? [];
  const glyphScale = (288 * book.size[1]) / (512 * book.size[0]);
  if (includeParagraphs) {
    for (const [i, block] of layout.blocks.entries()) {
      paragraph(
        ctx,
        block,
        layout.ink,
        Boolean(layout.serif),
        paragraphs[i],
        glyphScale,
        layout.boldText,
      );
    }
  }
  pictorialDetails(ctx, book.key);
  ctx.save();
  ctx.scale(glyphScale, 1);
  for (const line of layout.headings) {
    ctx.fillStyle = line.color ?? layout.ink;
    ctx.textAlign = line.alignment;
    ctx.font =
      (line.size >= 2.3 ? '600 ' : '') +
      line.size * percentageY +
      'px ' +
      (layout.serif ? 'Georgia,serif' : 'Arial,sans-serif');
    ctx.fillText(
      line.text,
      (line.x * percentageX) / glyphScale,
      line.baseline * percentageY,
      (line.width * percentageX) / glyphScale,
    );
  }
  ctx.restore();
  const block = layout.barcode;
  if (!block) {
    ctx.restore();
    return;
  }
  const boxX = block.x * percentageX,
    boxY = block.y * percentageY;
  const width = block.width * percentageX,
    height = block.height * percentageY;
  const main = width * (block.supplement ? 0.58 : 0.84);
  const x = boxX + width * 0.075;
  ctx.fillStyle = block.color;
  ctx.fillRect(boxX, boxY, width, height);
  ctx.fillStyle = '#252524';
  ctx.textAlign = 'left';
  ctx.font = height * 0.145 + 'px monospace';
  ctx.fillText('ISBN ' + book.identifier, x, boxY + height * 0.18, main);
  printedBars(
    ctx,
    book.identifier,
    x,
    boxY + height * 0.24,
    main,
    height * 0.53,
    block.alignModules,
  );
  const isbn = book.identifier;
  ctx.fillText(
    isbn[0] + ' ' + isbn.slice(1, 7) + ' ' + isbn.slice(7),
    x,
    boxY + height * 0.91,
    main,
  );
  if (block.supplement) {
    const extraX = boxX + width * 0.71;
    printedBars(
      ctx,
      block.supplement,
      extraX,
      boxY + height * 0.34,
      width * 0.23,
      height * 0.43,
      block.alignModules,
    );
    ctx.fillText(block.supplement, extraX, boxY + height * 0.29, width * 0.23);
  }
  ctx.restore();
}

function mobyBinding(ctx: CanvasRenderingContext2D, book: BookEdition) {
  ctx.save();
  ctx.fillStyle = '#11171b';
  ctx.fillRect(0, 0, 384, 512);
  const line = (text: string, x: number, y: number, font: string, ink = '#f1eee6') => {
    ctx.font = font;
    ctx.fillStyle = ink;
    ctx.fillText(text, x, y);
  };
  ctx.textAlign = 'center';
  const quotation = [
    '“It is the horrible texture of a fabric',
    'that should be woven of ships’ cables and',
    'hawsers. A Polar wind blows through it,',
    'and birds of prey hover over it.”',
  ];
  quotation.forEach((text, i) => line(text, 144, 24 + i * 16, 'bold 10.5px Georgia,serif'));
  ctx.fillStyle = '#936d59';
  ctx.fillRect(55, 85, 177, 0.6);
  const body = [
    [
      'Ishmael signs on aboard the Pequod, a whaler sailing from Nantucket. Its captain has chosen another course. Ahab follows the white whale across the oceans, while the men of the crew mend their gear, keep watch and piece together news from passing ships. Ishmael tells their story through sermons and songs, anatomy, seafaring lore and the ordinary labours of a working ship.',
      18.6,
      20.8,
      8,
    ],
    [
      'This volume follows the Northwestern–Newberry text. Maps, illustrations and a glossary help readers trace the voyage and identify the rigging, tools and customs encountered along the way.',
      41.5,
      8.8,
      3,
    ],
  ] as const;
  for (const [text, y, height, lines] of body) {
    paragraph(
      ctx,
      { x: 9, y, width: 82, height, lines, alignment: 'left' },
      '#f1eee6',
      false,
      text,
      (288 * book.size[1]) / (512 * book.size[0]),
    );
  }
  ctx.textAlign = 'center';
  line(
    'This edition follows the text established by the Northwestern University Press',
    144,
    272,
    '5.4px Arial,sans-serif',
  );
  line(
    'and Newberry Library, with annotations for the Penguin Classics edition.',
    144,
    283,
    '5.4px Arial,sans-serif',
  );
  line('INTRODUCTION BY ANDREW DELBANCO', 144, 301, 'bold 5.5px Arial,sans-serif');
  line('EXPLANATORY COMMENTARY BY TOM QUIRK', 144, 313, 'bold 5.5px Arial,sans-serif');
  line('Cover illustration by Rockwell Kent', 144, 384, '5.9px Arial,sans-serif');
  line(
    'Plattsburgh State Art Museum · Rockwell Kent Gallery & Collection',
    144,
    394,
    '5.9px Arial,sans-serif',
  );
  ctx.fillStyle = '#faf9f4';
  ctx.fillRect(0, 328, 384, 43);
  ctx.fillRect(51, 401, 190, 77);
  ctx.textAlign = 'left';
  line('A Penguin Book', 60, 419, '5.9px Arial,sans-serif', '#986c50');
  line('Literature', 64, 429, '5.9px Arial,sans-serif', '#986c50');
  line('U.S.     $16.00', 60, 447, '6.7px Arial,sans-serif', '#252524');
  line('CAN.   $22.00', 60, 457, '6.7px Arial,sans-serif', '#252524');
  line('U.K.      £7.99', 60, 467, '6.7px Arial,sans-serif', '#252524');
  line('ISBN: 978-0-14-243724-7', 124, 412, '5.3px Arial,sans-serif', '#252524');
  printedBars(ctx, book.identifier, 125, 415, 57, 52, true);
  printedBars(ctx, '51600', 188, 421, 29, 48, true);
  line('9 780142 437247', 120, 474, '5.7px monospace', '#252524');
  line('5 1 6 0 0', 190, 419, '5.5px monospace', '#252524');
  ctx.textAlign = 'center';
  line(
    'PENGUIN CLASSICS READERS GUIDE AVAILABLE ONLINE AT PENGUINRANDOMHOUSE.COM',
    144,
    495,
    '4.9px Arial,sans-serif',
    '#bb8c72',
  );
  ctx.translate(336, 0);
  ctx.rotate(Math.PI / 2);
  ctx.textAlign = 'left';
  line('HERMAN MELVILLE', 52, 4, 'bold 10.3px Arial,sans-serif');
  ctx.fillStyle = '#9e735b';
  ctx.fillRect(156, -5, 0.7, 11);
  line('MOBY-DICK', 165, 4, 'bold 10.3px Arial,sans-serif');
  line('P E N G U I N   C L A S S I C S', 395, 3, '6.8px Arial,sans-serif', '#bb8c72');
  ctx.restore();
}

function kindredBinding(ctx: CanvasRenderingContext2D, isbn: string) {
  ctx.save();
  ctx.translate(252, 0);
  ctx.scale(1.32, 5.12);
  ctx.fillStyle = '#ed277f';
  ctx.fillRect(0, 0, 100, 100);
  const shapes = [
    ['#f6ae75', 'M0 0H100V5Q73 15 46 7L20 11Z'],
    ['#55bfd2', 'M5 0H87Q71 2 59 8Q37 14 11 5Z'],
    ['#292a31', 'M0 2Q17 0 28 5Q38 11 52 9T86 8L100 9V20Q78 16 70 24Q51 17 34 20L9 28Z'],
    ['#05b9ce', 'M0 19Q20 15 26 10Q43 17 67 15L100 24V32Q73 23 48 28T0 34Z'],
    ['#6462b3', 'M0 28Q25 25 47 20Q69 28 100 24V35Q69 30 42 35L0 43Z'],
    ['#19d3d3', 'M0 37Q15 30 36 34Q58 38 75 31L100 30V44H0Z'],
    ['#13181c', 'M0 43Q31 41 55 33Q74 44 100 43V51L67 56Q36 48 0 54Z'],
    ['#7939a4', 'M0 52Q22 53 32 50Q54 49 70 52L100 48V54Q83 59 48 54Q22 60 0 55Z'],
    ['#779c4c', 'M0 56Q44 61 60 54L100 56V68Q74 68 53 63Q24 63 0 70Z'],
    ['#01c4d6', 'M0 60Q14 58 15 64Q20 69 46 67T100 63V74L68 78Q34 74 0 77Z'],
    ['#111920', 'M0 77Q18 75 30 71Q39 67 58 70Q80 73 100 70V80Q74 90 41 81Q20 75 0 82Z'],
    ['#a9d856', 'M0 75Q10 74 18 72Q13 77 0 83Z M75 88Q88 81 100 84V97Q84 96 75 88Z'],
    ['#53314c', 'M0 88Q19 89 39 85Q15 90 0 89Z'],
  ];
  for (const [color, outline] of shapes) {
    ctx.fillStyle = color;
    ctx.fill(new Path2D(outline));
  }
  ctx.restore();

  ctx.save();
  ctx.textAlign = 'left';
  ctx.fillStyle = '#eadfb2';
  ctx.font = '900 17px Arial,sans-serif';
  ctx.fillText('“I LOST AN ARM ON MY LAST TRIP HOME. MY LEFT ARM.”', 15, 33, 228);
  ctx.fillStyle = '#89c6db';
  ctx.font = 'bold 14px Arial,sans-serif';
  ctx.fillText('OCTAVIA E. BUTLER', 15, 349, 69);
  ctx.fillStyle = '#e7e1d4';
  ctx.font = '8px Georgia,serif';
  ctx.fillText('(1947–2006) wrote about power, kinship and survival.', 87, 349, 154);
  ctx.fillStyle = '#bbaa9b';
  ctx.font = 'bold 5.3px Arial,sans-serif';
  ctx.fillText('COVER ART AND DESIGN: CAROL CHU', 15, 473, 84);
  ctx.font = 'bold 7.5px Arial,sans-serif';
  ctx.fillText('BEACON PRESS', 15, 487, 80);
  ctx.fillText('WWW.BEACON.ORG', 15, 499, 90);
  const blocks = [
    [133, 87, 10],
    [157, 87, 8],
    [170, 87, 17],
    [198, 86, 27],
    [33, 321, 9],
    [46, 322, 39],
    [91, 321, 20],
    [117, 321, 9],
    [139, 321, 22],
    [183, 321, 23],
    [227, 321, 12],
    [15, 437, 5],
    [28, 437, 6],
    [41, 437, 14],
    [75, 437, 40],
  ];
  const muted = ['#998788', '#687886', '#9a9e87'];
  for (const [i, [x, y, width]] of blocks.entries()) {
    ctx.fillStyle = muted[i % muted.length];
    ctx.fill(new Path2D(`M${x} ${y}h${width}l-2 5h-${width - 4}Z`));
  }
  ctx.fillStyle = '#f7f7f1';
  ctx.fillRect(47.6 * percentageX, 82.1 * percentageY, 37 * percentageX, 15.2 * percentageY);
  ctx.fillStyle = '#242527';
  ctx.font = 'bold 4.8px Arial,sans-serif';
  ctx.fillText('US $17.00 / CAN $23.00', 151, 427, 85);
  ctx.font = '5.1px monospace';
  ctx.fillText('ISBN-13: 978-0-8070-8369-7', 143, 436, 84);
  const module = 0.55;
  const start = 144;
  const supplement = start + (95 + 9) * module;
  printedBars(ctx, isbn, start, 440, 95 * module, 46);
  printedBars(ctx, '51700', supplement, 447, 47 * module, 39);
  ctx.fillText('9 780807 083697', start - 3, 494, 60);
  ctx.fillText('51700', supplement, 444, 47 * module);
  ctx.strokeStyle = '#353635';
  ctx.lineWidth = 0.65;
  ctx.stroke(new Path2D('M234 479L238 471L242 479Z'));
  ctx.translate(337, 0);
  ctx.rotate(Math.PI / 2);
  ctx.fillStyle = '#fbf8eb';
  ctx.font = '65px Arial,sans-serif';
  ctx.fillText('OCTAVIA E. BUTLER', 12, 22, 177);
  ctx.font = 'bold 76px Arial,sans-serif';
  ctx.fillText('KINDRED', 218, 27, 168);
  ctx.restore();
  ctx.save();
  ctx.textAlign = 'center';
  ctx.fillStyle = '#f5efe2';
  ctx.lineWidth = 1.8;
  ctx.strokeStyle = '#f5efe2';
  for (let i = 0; i < 11; i++) {
    const angle = (Math.PI * i) / 10;
    ctx.beginPath();
    ctx.moveTo(336, 473);
    ctx.lineTo(336 + Math.cos(angle) * 26, 473 - Math.sin(angle) * 11);
    ctx.stroke();
  }
  ctx.font = 'bold 7px Georgia,serif';
  ctx.fillText('BEACON', 336, 482, 49);
  ctx.fillText('PRESS', 336, 489, 38);
  ctx.restore();
}

function humboldtSpine(ctx: CanvasRenderingContext2D) {
  ctx.save();
  ctx.translate(288, 0);
  ctx.scale(96 / 75, 1);
  ctx.fillStyle = '#14272b';
  ctx.fillRect(0, 0, 75, 512);
  const grain = random(1769);
  const sections = [
    {
      y: 77,
      h: 47,
      profile:
        'M2 48L6 40L10 39L12 32L16 30Q23 18 30 5Q33-1 36 2L44 15L48 10L56 20L59 23L63 34L70 41L71 48Z',
      snow: 0.49,
      ridge: 0.69,
    },
    {
      y: 232,
      h: 47,
      profile: 'M1 48L9 32L15 25L26 6L30 0L34 2L37 12L46 17L49 14L57 23L65 34L70 37L72 48Z',
      snow: 0.53,
      ridge: 0.72,
    },
    {
      y: 379,
      h: 34,
      profile: 'M0 48L9 32L15 26L24 9L30 0L34 2L44 16L49 25L54 32L61 37L74 43L75 48Z',
      snow: 0.64,
      ridge: 0.81,
    },
  ];
  for (const [i, section] of sections.entries()) {
    ctx.save();
    ctx.translate(7, section.y);
    ctx.scale(0.83, section.h / 48);
    ctx.clip(new Path2D(section.profile));
    ctx.fillStyle = '#f3eed3';
    ctx.fillRect(0, 0, 76, 49);
    for (const [band, color] of [
      [section.snow, '#b9c9a0'],
      [section.ridge, '#74896b'],
      [section.ridge + 0.1, '#526956'],
    ] as const) {
      ctx.fillStyle = color;
      ctx.beginPath();
      for (let x = 0; x <= 76; x += 2) {
        const y = band * 48 + Math.sin(x * 0.11 + i) * (i ? 1.1 : 2.4) + grain() * 1.6;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineTo(76, 50);
      ctx.lineTo(0, 50);
      ctx.fill();
    }
    for (let mark = 0; mark < 155; mark++) {
      const x = grain() * 76;
      const y = grain() * 48;
      ctx.strokeStyle = y < section.snow * 48 ? 'rgba(83,100,91,.30)' : 'rgba(30,52,42,.58)';
      ctx.lineWidth = 0.42;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x - 0.9 - grain() * 1.4, y + 1.8 + grain() * 2);
      ctx.stroke();
    }
    ctx.restore();
  }
  ctx.textAlign = 'center';
  ctx.fillStyle = '#e4d893';
  for (const [word, y, font] of [
    ['The', 159, 'italic 12px Georgia'],
    ['INVENTION', 177, 'bold 11.3px Georgia'],
    ['of', 194, 'italic 12px Georgia'],
    ['NATURE', 211, 'bold 11.5px Georgia'],
    ['Andrea', 326, 'italic 16px Georgia'],
    ['Wulf', 347, 'italic 16px Georgia'],
    ['Vintage', 490, 'italic 8px Georgia'],
  ] as const) {
    ctx.font = font;
    ctx.fillText(word, 37.5, y, 72);
  }
  ctx.translate(37.5, 467);
  for (let petal = 0; petal < 18; petal++) {
    ctx.rotate(Math.PI / 9);
    ctx.beginPath();
    ctx.ellipse(0, -6.8, 1.6, 3.6, -0.25, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.beginPath();
  ctx.arc(0, 0, 2.2, 0, 2 * Math.PI);
  ctx.fill();
  ctx.restore();
}

export function drawEditionBack(
  ctx: CanvasRenderingContext2D,
  book: BookEdition,
  includeParagraphs: boolean,
) {
  if (book.key === 'moby') mobyBinding(ctx, book);
  if (book.key === 'creative-act') rubinBack(ctx, book);
  if (book.key === 'c-language') cLanguageBack(ctx, book);
  const layout = rearLayouts[book.key];
  if (layout) measuredBack(ctx, book, layout, includeParagraphs);
  if (book.key === 'sicp') sicpBinding(ctx, book.en);
  if (book.key === 'walden') {
    ctx.save();
    ctx.fillStyle = '#17191b';
    ctx.fillRect(288, 0, 96, 512);
    ctx.fillStyle = '#f8f5e9';
    ctx.fillRect(288, 334, 96, 28);
    ctx.fillStyle = '#db7a43';
    ctx.textAlign = 'center';
    ctx.font = 'italic 12px Georgia,serif';
    ctx.fillText('A transcendentalist classic on social responsibility and', 144, 69, 249);
    ctx.fillText('a manifesto that inspired modern protest movements', 144, 87, 242);
    ctx.translate(336, 0);
    ctx.rotate(Math.PI / 2);
    ctx.scale(1, 2.05);
    ctx.textAlign = 'left';
    ctx.font = 'bold 12px Arial,sans-serif';
    ctx.fillText('HENRY DAVID THOREAU', 16, 4, 132);
    ctx.fillStyle = '#f8f5e9';
    ctx.font = 'italic 13px Georgia,serif';
    ctx.fillText('Walden and Civil Disobedience', 164, 4, 148);
    ctx.font = 'bold 7.5px Arial,sans-serif';
    ctx.fillText('P E N G U I N   C L A S S I C S', 385, 2.5, 111);
    ctx.restore();
  }
  if (book.key === 'beloved') belovedSpine(ctx);
  if (book.key === 'invention-nature') humboldtSpine(ctx);
  if (book.key === 'butler') kindredBinding(ctx, book.identifier);
}
