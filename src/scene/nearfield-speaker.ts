import * as T from 'three';
import { blenderMesh } from './blender-mesh';
import { box, canvasTexture, group, mesh, surface, tube, type XYZ } from './geometry';
import type { Palette } from './materials';

const parts = {
  cabinet: 'Radiused Carbon Black cabinet',
  baffle: 'Compound moulded front baffle',
  trim: 'Machined driver mounting flange',
  rubber: 'Pleated Z-Flex surround',
  shadow: 'Cabinet joints and driver clearances',
  cone: '130 mm Uni-Q midrange with pressed radial stiffeners',
  guide: 'Vented tweeter and nine Tangerine waveguide vanes',
  glass: 'Flush capacitive glass',
} as const;

function driverFinish() {
  const size = 256;
  const image = new ImageData(size, size);
  const pixels = image.data;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const radius = Math.hypot(x + 0.5 - size / 2, y + 0.5 - size / 2);
      const grain = Math.sin(x * 193.23 + y * 171.13) * 473.61;
      const value = Math.round(229 + Math.sin(radius * 2.1) * 5 + (grain - Math.floor(grain)) * 12);
      const offset = 4 * (y * size + x);
      pixels[offset] = pixels[offset + 1] = pixels[offset + 2] = value;
      pixels[offset + 3] = 255;
    }
  }
  const map = canvasTexture(size, size, (ctx) => ctx.putImageData(image, 0, 0));
  map.colorSpace = T.NoColorSpace;
  map.flipY = false;
  return map;
}

function touchLegend() {
  const map = canvasTexture(768, 152, (ctx) => {
    ctx.strokeStyle = '#a9b1b2';
    ctx.lineWidth = 2.8;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    const path = (coords: [number, number][]) => {
      ctx.beginPath();
      coords.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.stroke();
    };
    for (let i = 0; i < 5; i++) {
      ctx.save();
      ctx.translate(175 + i * 103, 55);
      ctx.beginPath();
      ctx.arc(0, 0, 27, 0, Math.PI * 2);
      ctx.stroke();
      if (i === 0) {
        ctx.beginPath();
        ctx.arc(0, 1, 10, -0.96, Math.PI + 0.96);
        ctx.stroke();
        path([
          [0, -13],
          [0, 1],
        ]);
      } else if (i === 1) {
        path([
          [-6, -10],
          [10, -10],
          [10, 10],
          [-6, 10],
        ]);
        path([
          [-15, 0],
          [4, 0],
          [-1, -5],
        ]);
        path([
          [4, 0],
          [-1, 5],
        ]);
      } else if (i === 2) {
        path([
          [-13, -4],
          [-8, -4],
          [-2, -10],
          [-2, 9],
          [-8, 4],
          [-13, 4],
          [-13, -4],
        ]);
        path([
          [3, -4],
          [12, 5],
        ]);
        path([
          [12, -4],
          [3, 5],
        ]);
      } else {
        path([
          [-10, 0],
          [10, 0],
        ]);
        if (i === 4)
          path([
            [0, -10],
            [0, 10],
          ]);
      }
      ctx.restore();
    }
    for (const r of [4, 10, 16]) {
      ctx.beginPath();
      ctx.arc(88, 62, r, -2.37, -0.77);
      ctx.stroke();
    }
  });
  return new T.MeshStandardMaterial({ map, alphaTest: 0.34, roughness: 0.35 });
}

function frontInscription() {
  const map = canvasTexture(512, 112, (ctx) => {
    const text = 'LS50 Wireless II';
    ctx.font = '400 43px Arial, sans-serif';
    ctx.fillStyle = '#b18b5e';
    ctx.textAlign = 'center';
    const widths = Array.from(text, (c) => ctx.measureText(c).width);
    let x = -widths.reduce((a, b) => a + b, 0) / 2;
    for (const [i, c] of Array.from(text).entries()) {
      const u = x + widths[i] / 2;
      ctx.save();
      ctx.translate(256 + u, 72 + (u * u) / 1630);
      ctx.rotate(u / 815);
      ctx.fillText(c, 0, 0);
      ctx.restore();
      x += widths[i];
    }
  });
  return new T.MeshStandardMaterial({ map, alphaTest: 0.3, roughness: 0.54 });
}

function speakerAssets() {
  const roughnessMap = driverFinish();
  const copper = new T.MeshStandardMaterial({
    color: '#b16b43',
    metalness: 0.83,
    roughness: 0.355,
    roughnessMap,
  });
  const guide = copper.clone();
  guide.color.set('#af653d');
  guide.roughness = 0.32;
  guide.side = T.DoubleSide;
  const materials = {
    cabinet: new T.MeshPhysicalMaterial({
      color: '#373b3c',
      roughness: 0.41,
      metalness: 0.1,
      clearcoat: 0.1,
      clearcoatRoughness: 0.37,
    }),
    baffle: surface('#3c4141', 0.45, 0.11),
    trim: surface('#343839', 0.42, 0.18),
    rubber: new T.MeshPhysicalMaterial({
      color: '#201f21',
      roughness: 0.57,
      specularIntensity: 0.54,
    }),
    shadow: surface('#141718', 0.53, 0.05),
    cone: copper,
    guide,
    glass: new T.MeshPhysicalMaterial({
      color: '#161b1c',
      roughness: 0.135,
      metalness: 0.2,
      clearcoat: 0.88,
      clearcoatRoughness: 0.14,
    }),
  };
  const surfaces = (Object.keys(parts) as (keyof typeof parts)[]).map((key) => ({
    key,
    name: parts[key],
    geometry: blenderMesh('kef/' + key),
    material: materials[key],
  }));
  const hardware = {
    alloy: surface('#292c2e', 0.45, 0.5),
    heatsink: surface('#45484c', 0.37, 0.72),
    lining: surface('#151417', 0.84, 0.03),
    copper: surface('#995b3e', 0.45, 0.35),
    metal: surface('#a5abad', 0.38, 0.84),
    contact: surface('#a48245', 0.35, 0.77),
  };
  const cavity = canvasTexture(256, 4, (ctx) => {
    const absorption = ctx.createLinearGradient(0, 0, 256, 0);
    for (const [at, value] of [
      [0, 35],
      [0.37, 76],
      [0.65, 151],
      [0.86, 225],
      [1, 255],
    ]) {
      absorption.addColorStop(at, `rgb(${value}, ${value}, ${value})`);
    }
    ctx.fillStyle = absorption;
    ctx.fillRect(0, 0, 256, 4);
  });
  hardware.copper.map = cavity;
  hardware.lining.map = cavity;
  for (const [finish, material] of Object.entries(hardware)) {
    material.name = 'KEF rear ' + finish;
    material.userData.kefFinish = finish;
  }
  const io = ['alloy', 'lining', 'metal', 'contact'];
  return {
    surfaces,
    rear: rearAssets(hardware, 'rear', ['alloy', 'heatsink', 'copper', 'lining']),
    primary: rearAssets(hardware, 'primary', io),
    secondary: rearAssets(hardware, 'secondary', io),
    panels: [connectionLegend(false), connectionLegend(true)],
    legend: touchLegend(),
    badge: frontInscription(),
  };
}

const assetsByPalette = new WeakMap<Palette, ReturnType<typeof speakerAssets>>();

function connectionLegend(primary: boolean) {
  const map = canvasTexture(1440, 576, (ctx) => {
    ctx.scale(7.2, 7.2);
    ctx.translate(100, -64);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    function tag(x: number, y: number, width: number, label: string) {
      ctx.fillStyle = '#92918b';
      ctx.beginPath();
      ctx.roundRect(x - width / 2, y - 1.45, width, 2.9, 1);
      ctx.fill();
      ctx.fillStyle = '#202222';
      ctx.font = '500 2.05px Arial';
      ctx.fillText(label, x, y + 0.1, width - 1.1);
    }
    if (primary) {
      for (const [i, s] of [
        'TV',
        'OPTICAL',
        'COAX',
        'AUX',
        'RESET',
        'P/S PAIRING',
        'BT PAIRING',
      ].entries())
        tag((i - 3) * 20.2, 73, 18.3, s);
    }
    for (const [x, width, label] of [
      [-58, 22, primary ? 'TO SECONDARY' : 'TO PRIMARY'],
      [-33, 21, 'SUB'],
      [-7.5, 22, 'SERVICE'],
      [18, 21, primary ? 'NETWORK' : 'P/S PAIRING'],
      [54, 30, 'AC'],
    ] as const)
      tag(x, 100.9, width, label);
    ctx.fillStyle = '#b8b8ae';
    ctx.font = '500 3.1px Arial';
    ctx.fillText(primary ? 'PRIMARY' : 'SECONDARY', 0, 132.4);
  });
  return new T.MeshStandardMaterial({ map, alphaTest: 0.35, roughness: 0.64 });
}

function rearAssets(materials: Record<string, T.Material>, variant: string, finishes: string[]) {
  return finishes.map((finish) => ({
    name: variant + '-' + finish,
    geometry: blenderMesh('kef/' + variant + '-' + finish),
    material: materials[finish],
  }));
}

export function nearfieldSpeaker(
  parent: T.Object3D,
  p: Palette,
  side: -1 | 1,
  meters: T.Material[],
  position: XYZ,
) {
  const unit = group(parent, side < 0 ? 'Left speaker' : 'Right speaker', position);
  const cabinet = group(unit, 'LS50 Wireless II · curved baffle and Uni-Q array', [0, 0.155, 0]);
  let shared = assetsByPalette.get(p);
  if (!shared) {
    shared = speakerAssets();
    assetsByPalette.set(p, shared);
  }
  for (const { key, name, geometry, material } of shared.surfaces) {
    const part = mesh(cabinet, geometry, material);
    part.name = name;
    part.userData.kefSurface = key;
  }
  const label = mesh(
    cabinet,
    new T.PlaneGeometry(0.054, 0.0118),
    shared.badge,
    [0, 0.0664, 0.1556],
  );
  label.castShadow = false;
  const legend = mesh(
    cabinet,
    new T.PlaneGeometry(0.113, 0.0224),
    shared.legend,
    [0, 0.150085, 0.051],
  );
  legend.rotation.x = -Math.PI / 2;
  legend.castShadow = false;
  const role = side === 1 ? 'primary' : 'secondary';
  const rear = group(cabinet, 'KEF rear acoustic and amplifier assembly');
  rear.userData.kefRole = role;
  for (const part of [...shared.rear, ...shared[role]]) {
    const item = mesh(rear, part.geometry, part.material);
    item.name = part.name;
    item.userData.kefSurface = part.name;
  }
  const panel = mesh(
    cabinet,
    new T.PlaneGeometry(0.2, 0.08),
    shared.panels[Number(side === 1)],
    [0, -0.104, -0.14912],
  );
  panel.name = 'Rear connection legends';
  panel.rotation.y = Math.PI;
  panel.castShadow = false;
  for (const x of [-0.069, 0.069])
    for (const z of [-0.114, 0.1]) tube(unit, [x, 0, z], [x, 0.007, z], 0.012, p.rubber, 0.0095);
  const display = group(cabinet, 'Flush six-segment level display');
  for (const [i, lit] of meters.entries())
    box(display, [0.004, 0.00015, 0.00085], [(i - 2.5) * 0.0095, 0.1501, 0.0577], lit);
  return unit;
}
