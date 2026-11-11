import * as T from 'three';
import { box, cable, canvasTexture, group, mesh, random, surface, tube } from './geometry';
import type { Palette } from './materials';

function solderMask() {
  const map = canvasTexture(896, 1000, (ctx) => {
    const rng = random(174);
    const grain = ctx.createImageData(896, 1000);
    for (let i = 0; i < grain.data.length; i += 4) {
      const value = 29 + Math.floor(rng() * 6);
      grain.data.set([value - 1, value + 1, value, 255], i);
    }
    ctx.putImageData(grain, 0, 0);

    function route(x: number, y: number, bend: number, run: number, end: number, count: number) {
      for (let i = 0; i < count; i++) {
        const gap = i * 5;
        ctx.strokeStyle = i % 5 === 0 ? '#686151' : '#464940';
        ctx.lineWidth = i % 5 === 0 ? 2.2 : 1.4;
        ctx.beginPath();
        ctx.moveTo(x + gap, y);
        ctx.lineTo(x + gap, y + run);
        ctx.lineTo(x + gap + bend, y + run + Math.abs(bend));
        ctx.lineTo(x + gap + bend, end);
        ctx.stroke();
        ctx.fillStyle = '#a0987f';
        ctx.beginPath();
        ctx.arc(x + gap + bend, end, 1.9, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    route(282, 369, 117, 60, 626, 26);
    route(563, 320, 87, 116, 675, 18);
    route(119, 152, 47, 140, 510, 13);
    route(698, 570, -66, 95, 890, 18);
    route(185, 641, 67, 65, 897, 24);
    route(568, 663, -52, 95, 927, 15);
    for (const [x, y, columns, rows] of [
      [82, 322, 8, 20],
      [458, 124, 11, 14],
      [742, 642, 10, 14],
      [386, 862, 17, 7],
    ]) {
      for (let col = 0; col < columns; col++)
        for (let row = 0; row < rows; row++) {
          if (rng() < 0.38) continue;
          const left = x + col * 8;
          const top = y + row * 8;
          ctx.fillStyle = '#716857';
          ctx.fillRect(left, top, 5, 3);
          ctx.fillStyle = '#282b29';
          ctx.fillRect(left + 1, top, 3, 3);
        }
    }
    ctx.fillStyle = '#9b9d92';
    ctx.font = '14px monospace';
    for (const [label, x, y] of [
      ['CPU_FAN', 258, 61],
      ['DIMM A1 / A2 / B1 / B2', 563, 100],
      ['PCIe x16', 100, 590],
      ['M.2_01', 174, 485],
      ['M.2_02', 174, 698],
      ['ATX_PWR', 740, 534],
      ['FRONT PANEL', 668, 954],
    ] as const)
      ctx.fillText(label, x, y);
    ctx.strokeStyle = '#686b62';
    ctx.lineWidth = 1;
    ctx.strokeRect(21, 21, 854, 958);
    for (const [x, y] of [
      [90, 102],
      [801, 102],
      [90, 872],
      [801, 872],
    ]) {
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, Math.PI * 2);
      ctx.stroke();
    }
  });
  return new T.MeshPhysicalMaterial({
    map,
    roughness: 0.61,
    clearcoat: 0.16,
    clearcoatRoughness: 0.54,
  });
}

export function motherboard(
  unit: T.Group,
  p: Palette,
  aluminum: T.MeshStandardMaterial,
  aura: T.MeshStandardMaterial[],
) {
  const board = group(unit, 'Motherboard · PCB, VRM, DIMM and M.2', [0.077, 0.033, -0.12]);
  const substrate = surface('#403a2e', 0.75);
  const shield = aluminum.clone();
  shield.color.set('#2d3035');
  shield.roughness = 0.45;
  const ferrite = surface('#55524c', 0.8);
  const solder = surface('#a39c81', 0.48, 0.46);
  box(board, [0.005, 0.357, 0.32], [0, 0, 0], substrate, 0.001);
  const face = mesh(board, new T.PlaneGeometry(0.318, 0.355), solderMask(), [-0.0026, 0, 0]);
  face.rotation.y = -Math.PI / 2;
  face.castShadow = false;

  for (const y of [-0.142, 0.142])
    for (const z of [-0.127, 0.124]) {
      tube(board, [0.002, y, z], [0.039, y, z], 0.0033, p.graphite);
      tube(board, [-0.004, y, z], [-0.002, y, z], 0.0031, p.steel);
    }
  box(board, [0.035, 0.132, 0.052], [-0.017, 0.09, -0.114], shield, 0.004);
  box(board, [0.019, 0.123, 0.018], [-0.031, 0.091, -0.104], aluminum, 0.002);
  for (let i = 0; i < 7; i++) {
    const z = -0.122 + i * 0.009;
    box(board, [0.024, 0.025, 0.007], [-0.012, 0.158, z], shield, 0.001);
    box(board, [0.009, 0.008, 0.007], [-0.008, 0.126, z], ferrite, 0.0005);
    tube(board, [-0.003, 0.111, z], [-0.012, 0.111, z], 0.0028, p.steel);
  }
  for (let i = 0; i < 9; i++) {
    const y = 0.043 + i * 0.01;
    box(board, [0.006, 0.0025, 0.031], [-0.034, y, -0.115], p.black, 0.0004).rotation.x = -0.25;
  }

  box(board, [0.003, 0.064, 0.063], [-0.004, 0.07, 0.003], aluminum, 0.001);
  for (const y of [0.04, 0.099])
    for (const z of [-0.025, 0.031]) {
      tube(board, [-0.008, y, z], [-0.004, y, z], 0.0025, p.steel);
    }
  for (const y of [-0.036, -0.087]) {
    box(board, [0.012, 0.025, 0.121], [-0.01, y, -0.015], shield, 0.0017);
    for (let i = 0; i < 5; i++) {
      box(
        board,
        [0.0013, 0.0023, 0.079],
        [-0.0163, y - 0.008 + i * 0.004, -0.022],
        aluminum,
        0.0004,
      );
    }
    tube(board, [-0.016, y, 0.037], [-0.018, y, 0.037], 0.0022, p.steel);
  }
  for (const y of [-0.011, -0.114]) {
    box(board, [0.013, 0.008, 0.131], [-0.009, y, 0.011], p.graphite, 0.0006);
    box(board, [0.001, 0.002, 0.106], [-0.016, y, 0.01], p.black);
    box(board, [0.011, 0.008, 0.007], [-0.01, y, 0.078], p.steel, 0.001);
  }
  for (let i = 0; i < 4; i++) {
    const memory = group(board, 'DDR5 DIMM ' + (i + 1), [-0.003, 0.071, 0.078 + i * 0.015]);
    box(memory, [0.012, 0.134, 0.012], [-0.004, 0, 0], p.black, 0.001);
    box(memory, [0.012, 0.117, 0.002], [-0.012, 0, 0], substrate, 0.0004);
    box(memory, [0.032, 0.113, 0.007], [-0.028, 0, 0], aluminum, 0.0013);
    box(memory, [0.003, 0.092, 0.005], [-0.045, 0.004, 0], aura[i], 0.001);
    for (const y of [-0.064, 0.064])
      box(memory, [0.013, 0.008, 0.011], [-0.009, y, 0], p.black, 0.001);
  }
  box(board, [0.018, 0.057, 0.013], [-0.01, 0.086, 0.141], p.black, 0.0012);
  const passThrough = group(board, 'ATX cable pass-through', [0.036, 0.076, 0.193]);
  // The lip wraps an open center so the sleeve disappears into the rear channel.
  box(passThrough, [0.004, 0.056, 0.016], [0.001, 0, 0], p.black, 0.0015);
  for (const side of [-1, 1]) {
    box(passThrough, [0.009, 0.064, 0.004], [-0.004, 0, side * 0.01], p.rubber, 0.0015);
    box(passThrough, [0.009, 0.004, 0.019], [-0.004, side * 0.03, 0], p.rubber, 0.0015);
  }
  for (let i = 0; i < 8; i++) {
    const y = 0.065 + i * 0.006;
    cable(
      board,
      [
        [-0.014, y, 0.142],
        [-0.02, y, 0.153],
        [-0.018, y - 0.008, 0.173],
        [0.013, y - 0.01, passThrough.position.z],
        [passThrough.position.x, y - 0.01, passThrough.position.z],
      ],
      0.0014,
      p.rubber,
    );
  }
  for (const y of [-0.061, -0.138]) {
    for (let i = 0; i < 5; i++) {
      const z = 0.092 + i * 0.008;
      box(board, [0.003, 0.004, 0.004], [-0.004, y, z], solder, 0.00035);
      box(board, [0.003, 0.002, 0.004], [-0.005, y, z], ferrite, 0.0003);
    }
  }
  box(board, [0.014, 0.04, 0.018], [-0.011, -0.053, 0.14], shield, 0.001);
  for (const y of [-0.066, -0.052, -0.038]) {
    box(board, [0.009, 0.008, 0.003], [-0.013, y, 0.15], p.black, 0.0008);
  }
}
