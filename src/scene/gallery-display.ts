import * as T from 'three';
import { canvasTexture, group, mesh, surface } from './geometry';
import type { Palette } from './materials';

import { hexcalStudio } from './hexcal-studio';
import { desk, deskSetup } from './layout';
import { blenderMesh } from './blender-mesh';
import { loadDisplayModel } from './display-model';

function fittedParts(parent: T.Group, name: string, finishes: Record<string, T.Material>) {
  for (const [key, material] of Object.entries(finishes))
    mesh(parent, blenderMesh('capture/' + name + '-' + key), material).name = name + ' • ' + key;
}

function monitorLight(tv: T.Group, p: Palette, top: number, titanium: T.Material) {
  const arm = group(tv, 'ScreenBar Halo 2 and hinged counterweight', [0, top, 0]);
  arm.userData.product = 'BenQ ScreenBar Halo 2';
  const bias = surface('#e2d3b8', 0.53);
  bias.emissive.set('#ffdfb4');
  bias.emissiveIntensity = 0.68;
  const strip = surface('#e6dbbf', 0.44);
  strip.emissive.set('#ffe6c1');
  strip.emissiveIntensity = 0.76;
  fittedParts(arm, 'screenbar-halo-2', {
    titanium,
    abs: p.graphite,
    rubber: p.rubber,
    silver: p.steel,
    lens: strip,
    frost: bias,
  });
  for (const piece of arm.children) piece.userData.haloFinish = piece.name.split(' • ')[1];
  const mark = canvasTexture(410, 82, (ctx) => {
    ctx.fillStyle = '#bcb8b0';
    ctx.font = '500 48px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('ScreenBar Halo 2', 205, 55);
  });
  const inscription = new T.PlaneGeometry(0.038, 0.0062, 1, 8);
  const positions = inscription.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const angle = 0.19 + positions.getY(i) / 0.0135;
    positions.setY(i, 0.0161 + 0.01354 * Math.sin(angle));
    positions.setZ(i, 0.0544 + 0.01354 * Math.cos(angle));
  }
  inscription.computeVertexNormals();
  mesh(
    arm,
    inscription,
    new T.MeshStandardMaterial({
      map: mark,
      alphaTest: 0.4,
      roughness: 0.46,
      polygonOffset: true,
      polygonOffsetFactor: -1,
    }),
    [0.206, 0, 0],
  ).castShadow = false;
  const deskWash = new T.SpotLight('#fff0da', 1.25, 1.4, Math.PI / 5, 0.84, 2);
  deskWash.name = 'ScreenBar front desk illumination';
  deskWash.position.set(0, 0.0088, 0.054);
  deskWash.target.position.copy(deskWash.position);
  deskWash.target.position.y -= Math.cos(Math.PI / 5);
  deskWash.target.position.z += Math.sin(Math.PI / 5);
  const wallWash = new T.RectAreaLight('#fff0da', 25, 0.08, 0.043);
  wallWash.name = 'ScreenBar rear ambient illumination';
  wallWash.position.set(0, 0.0183, -0.0759);
  // wallWash replaced in scene graph by Cycles multi-channel Lightmap (G channel)
  arm.add(deskWash, deskWash.target);
  return { arm, strip, bias, deskWash, wallWash };
}

function dialReadout(ctx: CanvasRenderingContext2D, digits: string, y: number, size: number) {
  const litSegments: Record<string, string> = {
    '0': 'abcdef',
    '1': 'bc',
    '4': 'bcfg',
    '5': 'acdfg',
  };
  const segments = [
    [2, 0, 13, 0],
    [15, 2, 15, 11],
    [15, 15, 15, 24],
    [2, 26, 13, 26],
    [0, 15, 0, 24],
    [0, 2, 0, 11],
    [2, 13, 13, 13],
  ];
  ctx.save();
  ctx.translate(225 - ((digits.length * 20 - 5) * size) / 2, y);
  ctx.scale(size, size);
  ctx.transform(1, 0, -0.07, 1, 0, 0);
  ctx.lineWidth = 2.8;
  ctx.lineCap = 'round';
  for (const digit of digits) {
    segments.forEach(([x1, y1, x2, y2], index) => {
      const lit = litSegments[digit].includes('abcdefg'[index]);
      ctx.strokeStyle = lit ? '#cad3cf' : '#363c3b';
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    });
    ctx.translate(20, 0);
  }
  ctx.restore();
}

export function galleryDisplay(
  tv: T.Group,
  p: Palette,
  height: number,
  centerHeight: number,
  manager: T.LoadingManager,
  deskParent: T.Object3D,
) {
  void loadDisplayModel(tv, '/media/models/lg-oled-g6.glb', manager);
  const surfaceHeight = desk.top - centerHeight;
  const shelf = group(tv, 'Hexcal Studio', [0, surfaceHeight, 0.067]);
  hexcalStudio(shelf, manager);
  const pad = deskSetup.codexMicro;
  const pivotHeight = 0.014;
  const codexMicro = group(deskParent, 'Codex Micro', [pad.x, desk.top + pivotHeight, pad.z]);
  codexMicro.rotation.y = pad.yaw;
  void loadDisplayModel(codexMicro, '/media/models/codex-micro.glb', manager, {
    mounted(scene) {
      scene.position.y -= pivotHeight;
    },
  });
  const titanium = surface('#807c74', 0.34, 0.82);
  const { arm, strip, bias, deskWash, wallWash } = monitorLight(tv, p, height / 2, titanium);
  const { lightController } = deskSetup;
  const dial = group(deskParent, 'Wireless light controller', [
    lightController.x,
    desk.top,
    lightController.z,
  ]);
  const glass = new T.MeshStandardMaterial({
    color: '#08090a',
    roughness: 0.19,
    metalness: 0.04,
    envMapIntensity: 0.46,
  });
  fittedParts(dial, 'halo-controller', {
    rubber: p.rubber,
    abs: p.graphite,
    titanium,
    silver: p.steel,
    glass,
  });
  const cap = group(dial, 'Touch face', [0, 0.03334, 0]);
  cap.rotation.x = Math.PI / 18;
  const face = canvasTexture(450, 450, (ctx) => {
    ctx.textAlign = 'center';
    ctx.fillStyle = '#e8e7dc';
    ctx.font = 'bold 24px Arial';
    ctx.fillText('BenQ', 225, 73);
    dialReadout(ctx, '100', 162, 1);
    dialReadout(ctx, '4500', 201, 0.89);
    dialReadout(ctx, '100', 239, 0.89);
    ctx.font = '14px Arial';
    ctx.fillStyle = '#b9c7c3';
    ctx.fillText('K', 269, 224);
    ctx.fillText('%', 262, 262);
    ctx.lineWidth = 3.5;
    ctx.strokeStyle = '#8b9190';
    const sun = (x: number, y: number) => {
      ctx.beginPath();
      ctx.arc(x, y, 8.3, 0, Math.PI * 2);
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4;
        ctx.moveTo(x + 12 * Math.cos(a), y + 12 * Math.sin(a));
        ctx.lineTo(x + 16 * Math.cos(a), y + 16 * Math.sin(a));
      }
      ctx.stroke();
    };
    sun(103, 166);
    sun(348, 212);
    ctx.beginPath();
    ctx.arc(225, 345, 12, -1.1, Math.PI * 2 - 2.0);
    ctx.moveTo(225, 326);
    ctx.lineTo(225, 341);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(111, 290);
    ctx.lineTo(120, 280);
    ctx.lineTo(128, 290);
    ctx.moveTo(119, 281);
    ctx.lineTo(119, 301);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(315, 293, 9, 0.3, 5.4);
    ctx.stroke();
    ctx.font = '18px Arial';
    ctx.fillStyle = '#8b9190';
    ctx.fillText('A', 138, 103);
    ctx.beginPath();
    ctx.moveTo(296, 101);
    ctx.lineTo(307, 101);
    ctx.lineTo(308, 114);
    ctx.lineTo(301, 110);
    ctx.lineTo(294, 114);
    ctx.closePath();
    ctx.stroke();
  });
  const readout = new T.MeshBasicMaterial({ map: face, alphaTest: 0.25 });
  mesh(cap, new T.PlaneGeometry(0.069, 0.069), readout).rotation.x = -Math.PI / 2;
  const screenBar = {
    unit: arm,
    dial,
    deskWash,
    setPower(powered: boolean, detailed: boolean) {
      deskWash.intensity = powered ? 1.25 : 0;
      wallWash.intensity = powered ? 25 : 0;
      wallWash.visible = detailed;
      strip.emissiveIntensity = powered ? 0.76 : 0;
      bias.emissiveIntensity = powered ? 0.68 : 0;
      readout.opacity = powered ? 1 : 0;
    },
  };
  return Object.assign(shelf, { screenBar, codexMicro });
}
