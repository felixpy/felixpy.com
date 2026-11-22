const foliage = '#202021';
const berryBlue = '#3562ab';

function berries(
  ctx: CanvasRenderingContext2D,
  fruit: readonly (readonly [number, number, number])[],
) {
  for (const [x, y, r] of fruit) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(r, r);
    ctx.fillStyle = berryBlue;
    ctx.beginPath();
    ctx.ellipse(0, 0, 1, 1.05, -0.18, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = foliage;
    ctx.fill(
      new Path2D('M-.55-.72L-.12-.51L.38-.84L.29-.27L.59.02L.03-.13L-.27.21L-.35-.25L-.67-.31Z'),
    );
    ctx.restore();
  }
}

function printedPortrait(ctx: CanvasRenderingContext2D) {
  ctx.save();
  ctx.translate(29, 96);
  ctx.beginPath();
  ctx.rect(0, 0, 49, 74);
  ctx.clip();
  const wash = ctx.createLinearGradient(0, 0, 49, 74);
  wash.addColorStop(0, '#9e9391');
  wash.addColorStop(1, '#d9bca0');
  ctx.fillStyle = wash;
  ctx.fillRect(0, 0, 49, 74);
  const fill = (ink: string, path: string) => {
    ctx.fillStyle = ink;
    ctx.fill(new Path2D(path));
  };
  fill('#5b3931', 'M-1 75V67Q4 55 14 47L20 35L35 34L35 54L49 63L52 75Z');
  fill('#973e38', 'M-3 68Q3 55 10 52L16 56L21 67L18 74H-2Z M28 65Q39 63 43 55L51 61V74H25Z');
  fill(
    '#504239',
    'M2 39Q-2 28 7 18Q5 12 15 9Q24 1 33 8Q40 8 42 16L36 41L28 49Q18 54 12 49L10 57L6 53L9 46L4 48Z',
  );
  const skin = ctx.createLinearGradient(14, 32, 47, 29);
  skin.addColorStop(0, '#75503a');
  skin.addColorStop(0.52, '#ad7049');
  skin.addColorStop(1, '#deb083');
  ctx.fillStyle = skin;
  ctx.fill(
    new Path2D(
      'M17 27Q19 13 32 13Q40 13 41 23L42 31L47 36Q48 38 44 39L44 42L46 43L44 46Q44 53 38 54L35 54L34 59Q26 63 21 55L22 48Q18 47 17 43Q13 43 13 37Q12 32 16 33Z',
    ),
  );
  fill(
    '#b8a084',
    'M3 33Q0 24 8 20Q4 16 12 13Q10 8 19 8Q19 3 26 6Q33 2 36 9Q24 5 19 17Q10 18 10 24Z',
  );
  fill('#d7c3aa', 'M10 18Q9 12 17 12Q14 8 23 8L20 11Q28 4 33 9L27 9Q24 12 20 14L17 18L17 15Z');
  fill(
    '#494036',
    'M23 29Q28 24 34 27L32 29Q29 27 23 30Z M36 27Q39 25 41 27L41 29Z M26 32Q30 30 33 31L30 33Z M38 31L41 30L40 32Z',
  );
  fill(
    '#85523b',
    'M33 32Q33 39 29 39Q34 40 36 37Z M38 39L43 37L43 39Z M25 44Q29 51 36 51L35 54Q28 55 25 49Z',
  );
  fill('#55352f', 'M36 43Q39 42 41 42L45 43L41 44L35 44Z');
  fill('#ba8a67', 'M38 45L44 44L42 46H38Z');
  ctx.restore();
}

export function belovedRearArtwork(ctx: CanvasRenderingContext2D) {
  ctx.save();
  ctx.fillStyle = foliage;
  ctx.fill(
    new Path2D(
      'M20-5L31-5Q22 33 21 63Q25 81 41 101Q17 94 16 78Q9 96 7 120Q20 110 27 125L19 142L14 136Q9 148 8 159L4 162L4 204Q4 245 13 255Q36 264 39 286Q43 306 57 316Q42 316 30 307L37 318Q19 314 12 302Q14 327 31 342L35 349Q24 346 17 338Q23 370 43 396Q66 391 80 409Q86 425 94 431Q64 432 46 409Q48 433 61 442Q43 440 38 423Q29 410 22 397Q20 436 26 468L25 482L20 482Q14 452 13 414Q6 434 -2 450L-5 448V361Q5 350 6 322Q-1 328 -5 344V92Q5 68 12 49Q6 57 -3 69L-4 32Q12 20 20-5Z M29-5L57-5L55 17Q42 2 29 0Z',
    ),
  );
  ctx.fill(
    new Path2D(
      'M236-3H288V95L277 84L277 117Q285 119 291 129V165Q278 150 273 135Q275 206 275 244Q279 267 290 283V314Q280 300 275 285Q272 310 251 321L247 326L244 319Q257 303 265 280Q256 288 240 294Q248 281 254 266Q263 247 269 243Q267 183 264 123Q263 89 264 45Q255 46 242 52Q249 46 251 39Q238 44 226 42Q242 24 236-3Z M275 301Q276 322 284 329L292 347V385Q281 378 277 366Q273 390 257 404Q244 411 237 421Q241 398 257 384Q273 366 272 348Q268 365 253 375Q262 356 266 342Q267 323 275 301Z M279 365Q278 397 285 414L288 419V447Q279 438 277 426Q274 455 261 470L257 474L255 468Q272 442 270 416Q268 402 279 365Z',
    ),
  );
  berries(ctx, [
    [23, 143, 6.6],
    [2, 372, 7.4],
    [35, 341, 8.3],
    [21, 478, 8.6],
    [257, 320, 8.5],
    [277, 383, 7.6],
    [270, 418, 8.1],
    [270, 42, 6.3],
    [285, 86, 6.5],
  ]);
  printedPortrait(ctx);
  ctx.restore();
}

export function belovedSpine(ctx: CanvasRenderingContext2D) {
  ctx.save();
  ctx.translate(288, 0);
  ctx.scale(96 / 56, 1);
  ctx.fillStyle = '#782939';
  ctx.fillRect(0, 0, 56, 512);
  ctx.fillStyle = foliage;
  ctx.fill(
    new Path2D(
      'M0 0H11Q17 9 18 24Q22 40 36 47Q14 47 0 38Z M0 54Q14 62 34 72L35 77Q17 75 7 67Q11 83 22 91L24 99L20 101Q8 86 0 80Z M0 246Q3 274 18 294Q22 300 25 303L26 311Q14 304 9 298Q3 295 0 287Z',
    ),
  );
  berries(ctx, [
    [31, 76, 8.6],
    [3, 87, 6.1],
    [22, 111, 7.7],
    [21, 310, 10],
  ]);
  ctx.save();
  ctx.translate(11, 117);
  ctx.rotate(Math.PI / 2);
  ctx.textAlign = 'left';
  ctx.font = '31px Georgia,serif';
  ctx.fillStyle = '#f3e3c6';
  ctx.fillText('Toni Morrison', 0, 0, 164);
  ctx.fillStyle = '#ed827d';
  ctx.fillText('Beloved', 211, 0, 97);
  ctx.restore();
  ctx.fillStyle = '#e5d8b5';
  ctx.beginPath();
  ctx.ellipse(28, 474, 7.2, 8.3, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fill(new Path2D('M21 483L35 481L32 484L23 485Z M24 487L31 486L29 489Z'));
  ctx.textAlign = 'center';
  ctx.font = '7.5px Georgia,serif';
  ctx.fillText('Vintage', 28, 501, 32);
  ctx.restore();
}
