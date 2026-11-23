export function sicpBinding(ctx: CanvasRenderingContext2D, title: string) {
  ctx.save();
  ctx.translate(13, 26.3);
  ctx.beginPath();
  ctx.rect(0, 0, 76.8, 103);
  ctx.clip();
  const studio = ctx.createLinearGradient(0, 0, 77, 103);
  studio.addColorStop(0, '#16130f');
  studio.addColorStop(1, '#302028');
  ctx.fillStyle = studio;
  ctx.fillRect(0, 0, 77, 103);
  const shape = (path: string, fill: string | CanvasGradient) => {
    ctx.fillStyle = fill;
    ctx.fill(new Path2D(path));
  };
  const collar = ctx.createLinearGradient(0, 74, 71, 106);
  collar.addColorStop(0, '#51364d');
  collar.addColorStop(0.45, '#b494ac');
  collar.addColorStop(0.85, '#d0b9d0');
  collar.addColorStop(1, '#785775');
  shape('M-4 106L0 91Q8 84 20 80L28 74L50 72L55 76Q67 79 80 87L80 106Z', collar);
  shape('M24 71L25 85L33 93L40 89L51 80L49 68Z', '#9d665b');
  shape('M26 83L34 94L43 88L49 83L42 102L33 105Z', '#ded8cd');
  shape('M22 78L28 85L34 94L27 91L23 96L20 83Z', '#c8aec6');
  shape('M49 80L54 75L58 80L51 94L46 90L40 97Z', '#c7a9c0');
  shape('M20 55Q15 41 19 25Q22 10 37 8Q52 8 57 19Q64 29 60 48L57 58L49 57L25 59Z', '#3a2825');
  const skin = ctx.createRadialGradient(43, 36, 2, 39, 43, 37);
  skin.addColorStop(0, '#e4a58b');
  skin.addColorStop(0.51, '#d39279');
  skin.addColorStop(0.81, '#a76b5c');
  skin.addColorStop(1, '#78443e');
  shape(
    'M21 35Q23 17 35 15Q47 12 55 24L58 40L57 53Q55 65 48 73Q40 80 32 77Q24 73 22 65L19 55Q16 54 16 49Q16 44 19 45L21 46Z',
    skin,
  );
  shape('M19 44Q17 25 26 18Q32 10 41 12Q29 16 26 24Q23 34 22 47Z', '#594036');
  shape('M53 22Q61 27 59 47L57 52L55 42Z', '#4a312b');
  shape('M24 39Q30 35 36 39L36 40Q30 38 25 42ZM42 38Q47 34 53 38L53 40Q48 37 43 40Z', '#654037');
  shape('M25 44Q31 40 35 44Q30 47 25 44ZM43 43Q47 39 52 42Q49 46 43 43Z', '#815449');
  shape('M28 44Q30 42 32 43L31 45ZM46 43Q48 41 49 42L48 44Z', '#302626');
  shape('M39 42Q38 52 35 56Q37 60 42 57L43 56Q39 57 38 55Z', '#ad7261');
  shape('M30 63Q37 60 42 61L47 60Q42 66 36 66Z', '#975e58');
  shape('M32 63Q39 62 44 62Q40 64 35 64Z', '#713e3d');
  ctx.restore();

  ctx.save();
  ctx.fillStyle = '#31204f';
  ctx.fillRect(288, 0, 96, 512);
  ctx.fillStyle = '#e53557';
  ctx.fillRect(288, 13.6, 96, 1.5);
  ctx.translate(352, 0);
  ctx.rotate(Math.PI / 2);
  ctx.textAlign = 'left';
  ctx.fillStyle = '#f5f1ec';
  ctx.font = 'bold 16px Arial,sans-serif';
  ctx.fillText(title, 28, 7, 353);
  ctx.font = 'bold 11.5px Arial,sans-serif';
  ctx.fillText('Second Edition', 28, 35, 74);
  ctx.fillText('Abelson and Sussman', 159, 35, 108);
  ctx.restore();

  ctx.fillStyle = '#f5f1ec';
  for (const [i, top] of [0, -4, 0, 0, 0, 0, -3].entries()) {
    ctx.fillRect(317 + i * 5.4, 466 + top, 3.4, i === 5 ? 23 : 16);
  }
}
