import * as T from 'three';
import { telemetryFont } from './pc-telemetry';
import { pcTelemetryTexture } from './pc-telemetry-texture';
import { box, canvasTexture, group, mesh, surface, tube } from './geometry';
import { loadDisplayModel } from './display-model';
import type { Palette } from './materials';
import { blenderMesh } from './blender-mesh';
import lowerPorts from './gr701-lower-ports.json';

type Point = [number, number];

function polygon(points: Point[]) {
  const shape = new T.Shape(points.map(([x, y]) => new T.Vector2(x, y)));
  shape.closePath();
  return shape;
}

function cutout(x: number, y: number, width: number, height: number, chamfer = 0.004) {
  const l = x - width / 2,
    r = x + width / 2,
    t = y + height / 2,
    b = y - height / 2;
  return polygon([
    [l + chamfer, b],
    [r - chamfer, b],
    [r, b + chamfer],
    [r, t - chamfer],
    [r - chamfer, t],
    [l + chamfer, t],
    [l, t - chamfer],
    [l, b + chamfer],
  ]);
}

function sheet(
  parent: T.Object3D,
  shape: T.Shape,
  material: T.Material,
  thickness: number,
  x: number,
) {
  const geometry = new T.ExtrudeGeometry(shape, {
    depth: thickness,
    bevelEnabled: false,
    curveSegments: 8,
  });
  const result = mesh(parent, geometry, material, [x, 0, 0]);
  result.rotation.y = -Math.PI / 2;
  return result;
}

function etching(
  parent: T.Object3D,
  z: number,
  y: number,
  x: number,
  width: number,
  height: number,
  texture: T.Texture,
) {
  const label = mesh(
    parent,
    new T.PlaneGeometry(width, height),
    new T.MeshStandardMaterial({
      map: texture,
      roughness: 0.51,
      metalness: 0.24,
      alphaTest: 0.32,
    }),
    [x, y, z],
  );
  label.rotation.y = -Math.PI / 2;
  label.castShadow = false;
}

function panelLight(parent: T.Object3D, manager: T.LoadingManager) {
  const mount = group(
    parent,
    'Hyperion removable multifunction illumination plate',
    [0.078, 0.02, 0.137],
  );
  mount.rotation.y = -Math.PI / 2;
  const illuminated = new T.MeshStandardMaterial();
  void loadDisplayModel(mount, '/media/models/gr701-lighting-board.glb', manager, {
    mesh(part) {
      if (
        !(part.material instanceof T.MeshStandardMaterial) ||
        part.material.name !== 'GR701 illuminated photomask'
      )
        return;
      illuminated.copy(part.material);
      part.material = illuminated;
    },
  });
  return illuminated;
}

function ventMaterial(finish: string, perforation: 'slot' | 'hex') {
  const t = canvasTexture(64, 64, (ctx) => {
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, 64, 64);
    ctx.globalCompositeOperation = 'destination-out';
    for (let row = -1; row < 6; row++)
      for (let col = -1; col < 6; col++) {
        const x = col * 16 + (row % 2) * 8,
          y = row * 16;
        ctx.beginPath();
        if (perforation === 'hex') {
          for (let k = 0; k < 6; k++) {
            const a = (Math.PI * k) / 3;
            const px = x + 6.8 * Math.cos(a),
              py = y + 6.8 * Math.sin(a);
            if (k === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }
          ctx.closePath();
        } else ctx.roundRect(x - 5.8, y - 2.4, 11.6, 4.8, 2);
        ctx.fill();
      }
  });
  const { data } = t.image.getContext('2d')!.getImageData(0, 0, 64, 64);
  for (let i = 0; i < data.length; i += 4) data[i] = data[i + 1] = data[i + 2] = 255;
  const mask = new T.DataTexture(new Uint8Array(data.buffer), 64, 64);
  mask.wrapS = mask.wrapT = T.RepeatWrapping;
  mask.minFilter = T.LinearMipmapLinearFilter;
  mask.magFilter = T.LinearFilter;
  mask.generateMipmaps = true;
  mask.anisotropy = t.anisotropy;
  mask.needsUpdate = true;
  t.dispose();
  return new T.MeshStandardMaterial({
    color: finish,
    map: mask,
    metalness: 0.52,
    roughness: 0.56,
    transparent: true,
    alphaTest: 0.02,
    depthWrite: false,
    forceSinglePass: true,
    side: T.DoubleSide,
  });
}

function topDustFilter(parent: T.Object3D) {
  const lid = group(parent, 'Removable top dust filter', [0, 0.279, -0.042]);
  const gauze = canvasTexture(32, 32, (ctx) => {
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, 8, 32);
    ctx.fillRect(0, 0, 32, 8);
  });
  gauze.wrapS = gauze.wrapT = T.RepeatWrapping;
  const finishes = {
    plate: surface('#696b71', 0.43, 0.61),
    frame: surface('#36383d', 0.51, 0.17),
    weave: new T.MeshStandardMaterial({
      color: '#383b40',
      map: gauze,
      metalness: 0.23,
      roughness: 0.76,
      transparent: true,
      depthWrite: false,
      side: T.DoubleSide,
      forceSinglePass: true,
    }),
    hardware: surface('#42444a', 0.51, 0.52),
  };
  for (const [name, material] of Object.entries(finishes)) {
    const part = mesh(lid, blenderMesh('gr701-top-filter-' + name), material);
    part.name = 'GR701 upper filter · ' + name;
    if (name === 'weave') part.castShadow = false;
  }
}

function powerCompartment(parent: T.Object3D, p: Palette, steel: T.Material) {
  const bay = group(parent, 'Hyperion removable PSU shroud and accessory drawer');
  const side = polygon([
    [-0.3, -0.277],
    [0.191, -0.277],
    [0.202, -0.224],
    [0.211, -0.194],
    [0.158, -0.184],
    [0.066, -0.184],
    [0.047, -0.169],
    [-0.29, -0.169],
    [-0.302, -0.18],
  ]);
  side.holes.push(
    polygon([
      [-0.283, -0.218],
      [-0.266, -0.198],
      [-0.118, -0.198],
      [-0.113, -0.217],
      [-0.139, -0.249],
      [-0.277, -0.249],
      [-0.283, -0.235],
    ]),
  );
  sheet(bay, side, steel, 0.003, -0.102);
  const labelTexture = canvasTexture(600, 96, (ctx) => {
    ctx.font = 'italic 600 28px Arial';
    ctx.fillStyle = '#858a93';
    ctx.textAlign = 'center';
    ctx.fillText('REPUBLIC OF GAMERS', 300, 58);
    ctx.fillStyle = '#555a60';
    for (let j = 0; j < 7; j++) {
      ctx.beginPath();
      let x = 14 + j * 10;
      ctx.moveTo(x, 80);
      ctx.lineTo(x + 30, 15);
      ctx.lineTo(x + 33, 15);
      ctx.lineTo(x + 3, 80);
      ctx.closePath();
      ctx.fill();
    }
  });
  const drawer = polygon([
    [-0.137, -0.266],
    [-0.102, -0.222],
    [-0.083, -0.196],
    [0.057, -0.196],
    [0.067, -0.206],
    [0.173, -0.206],
    [0.159, -0.266],
  ]);
  sheet(bay, drawer, p.graphite, 0.004, -0.1055);
  etching(bay, 0.047, -0.234, -0.1101, 0.181, 0.034, labelTexture);
  box(bay, [0.035, 0.01, 0.067], [-0.091, -0.195, 0.131], p.black, 0.0026);
  const shroudTop = ventMaterial('#45494f', 'hex');
  shroudTop.map!.repeat.set(13, 21);
  const top = mesh(bay, new T.PlaneGeometry(0.19, 0.326), shroudTop, [-0.0075, -0.169, -0.132]);
  top.rotation.x = -Math.PI / 2;
  for (const x of [-0.101, 0.084])
    box(bay, [0.009, 0.007, 0.334], [x, -0.172, -0.135], p.graphite, 0.0014);
  const deck = cutout(0.002, -0.119, 0.21, 0.174);
  deck.holes.push(cutout(-0.043, -0.081, 0.017, 0.039, 0.004));
  const deckMesh = mesh(
    bay,
    new T.ExtrudeGeometry(deck, { depth: 0.0025, bevelEnabled: false }),
    steel,
    [0, -0.183, 0],
  );
  deckMesh.rotation.x = -Math.PI / 2;
  for (const x of [-0.052, -0.034])
    box(bay, [0.0028, 0.004, 0.039], [x, -0.181, 0.081], p.rubber, 0.001);
  for (const z of [0.061, 0.101])
    box(bay, [0.021, 0.004, 0.003], [-0.043, -0.181, z], p.rubber, 0.001);
  const psu = group(bay, 'ROG power supply in rear cradle', [-0.013, -0.231, -0.207]);
  const powerLight = surface('#49555c', 0.28, 0.16);
  powerLight.emissive.set(0xffffff);
  powerLight.emissiveIntensity = 1.05;
  for (const [finish, material] of Object.entries({
    black: p.rubber,
    enamel: surface('#36393b', 0.44, 0.53),
    shell: p.steel,
    gold: surface('#bba57a', 0.41, 0.71),
    steel: p.steel,
    glass: surface('#171c20', 0.19, 0.12),
    aura: powerLight,
    violet: surface('#c62da5', 0.45, 0.05),
  }))
    mesh(psu, blenderMesh('thor-1600-' + finish), material).name =
      'Thor 1600W Titanium III • ' + finish;
  const readout = canvasTexture(320, 80, () => {});
  const ctx = readout.image.getContext('2d')!;
  const updateTexture = pcTelemetryTexture(readout, ctx);
  const readoutMaterial = new T.MeshBasicMaterial({
    map: readout,
    transparent: true,
    depthWrite: false,
  });
  const numbers = mesh(
    psu,
    new T.PlaneGeometry(0.033, 0.0088),
    readoutMaterial,
    [-0.07494, -0.00187, -0.01786],
  );
  numbers.name = 'Thor OLED power draw';
  numbers.rotation.y = -Math.PI / 2;
  numbers.castShadow = false;
  return {
    powerLight,
    showPower(watts: number, useTyped = false) {
      ctx.clearRect(0, 0, 320, 80);
      ctx.fillStyle = '#eff3ff';
      const digits = String(watts);
      ctx.font = telemetryFont(78);
      const digitsWidth = ctx.measureText(digits).width;
      ctx.font = telemetryFont(62);
      const gap = 4;
      const start = (320 - digitsWidth - gap - ctx.measureText('W').width) / 2;
      ctx.fillText('W', start + digitsWidth + gap, 68);
      ctx.font = telemetryFont(78);
      ctx.fillText(digits, start, 68);
      readoutMaterial.map = updateTexture(useTyped);
    },
  };
}

export function hyperionInterior(parent: T.Group, p: Palette, manager: T.LoadingManager) {
  const steel = surface('#41454b', 0.57, 0.56);
  const pan = polygon([
    [-0.307, -0.275],
    [0.216, -0.275],
    [0.216, 0.216],
    [0.192, 0.251],
    [-0.286, 0.251],
    [-0.307, 0.228],
  ]);
  pan.holes.push(cutout(-0.199, 0.106, 0.13, 0.089, 0.009));
  pan.holes.push(polygon(lowerPorts.boardInletPunchMm.map(([z, y]) => [z / 1000, y / 1000])));
  for (const center of lowerPorts.centersMm)
    pan.holes.push(
      polygon(
        lowerPorts.outlineMm.map(([z, y]) => [
          (center + z * lowerPorts.punchScale) / 1000,
          (lowerPorts.heightMm + y * lowerPorts.punchScale) / 1000,
        ]),
      ),
    );
  const [serviceZ, serviceY, serviceWidth, serviceHeight, serviceChamfer] =
    lowerPorts.serviceMm.map((n) => n / 1000);
  pan.holes.push(cutout(serviceZ, serviceY, serviceWidth, serviceHeight, serviceChamfer));
  for (const z of [-0.226, -0.115, 0.004, 0.128])
    pan.holes.push(cutout(z, 0.224, 0.068, 0.015, 0.004));
  sheet(parent, pan, steel, 0.0014, 0.088).name = 'Motherboard tray with lower cable openings';
  mesh(parent, blenderMesh('gr701-lower-grommets-black'), p.rubber).name =
    'Lower motherboard tray rubber grommets';
  const inlet = group(parent, '24-pin tray grommet');
  mesh(inlet, blenderMesh('gr701-board-inlet-graphite'), surface('#383c40', 0.72, 0.02)).name =
    'Rolled upper grommet flange';
  const ribs = new T.TextureLoader(manager).load('/media/materials/gr701-epdm-normal.png');
  ribs.wrapS = ribs.wrapT = T.RepeatWrapping;
  ribs.anisotropy = 8;
  for (const tongue of ['upper', 'centre', 'lower']) {
    const rubber = surface('#34383b', 0.7, 0.012);
    rubber.name = 'Moulded EPDM · ' + tongue + ' tongue';
    rubber.normalMap = ribs;
    mesh(inlet, blenderMesh('gr701-board-inlet-' + tongue), rubber).name =
      'Upper tray grommet · ' + tongue + ' tongue';
  }
  const channel = group(parent, 'Formed motherboard tray and wiring channel');
  for (const y of [-0.16, 0.208]) {
    box(channel, [0.011, 0.007, 0.486], [0.082, y, -0.043], p.graphite, 0.0015);
    box(channel, [0.006, 0.002, 0.467], [0.0758, y + 0.003, -0.045], steel, 0.0009);
  }
  for (const z of [0.041, 0.208])
    box(channel, [0.012, 0.38, 0.006], [0.08, 0.027, z], p.graphite, 0.0013);
  for (const u of [8, 163, 237])
    for (const v of [7, 163, 288]) {
      const y = 0.194 - v * 0.001,
        z = -0.289 + u * 0.001;
      tube(channel, [0.07868, y, z], [0.0878, y, z], 0.0034, p.steel);
      tube(channel, [0.07695, y, z], [0.07868, y, z], 0.00149, p.steel);
    }
  const rear = group(parent, 'Rear I/O and 9-slot expansion bulkhead', [0, 0, -0.302]);
  const wall = cutout(0, -0.002, 0.232, 0.552, 0.0045);
  const exhaust = new T.Path();
  exhaust.absarc(-0.041, 0.137, 0.064, 0, Math.PI * 2, true);
  wall.holes.push(exhaust);
  wall.holes.push(cutout(0.0535, 0.1145, 0.0453, 0.1581, 0.0013));
  wall.holes.push(cutout(0.005, -0.057, 0.159, 0.183, 0.002));
  wall.holes.push(cutout(-0.013, -0.231, 0.151, 0.087, 0.001));
  mesh(
    rear,
    new T.ExtrudeGeometry(wall, { depth: 0.0025, bevelEnabled: false, curveSegments: 24 }),
    steel,
  );
  const vents = ventMaterial('#666a73', 'slot');
  vents.map!.repeat.set(6, 1);
  for (let i = 0; i < 9; i++) {
    const y = 0.023 - i * 0.02032;
    if (i < 4) continue;
    const slat = mesh(rear, new T.PlaneGeometry(0.149, 0.0172), vents, [0.005, y, 0.004]);
    slat.castShadow = false;
    box(rear, [0.15, 0.002, 0.004], [0.005, y - 0.008, 0.005], p.graphite, 0.00055);
  }
  const rearFilter = ventMaterial('#4b5057', 'hex');
  rearFilter.map!.repeat.set(7, 7);
  const screen = mesh(rear, new T.CircleGeometry(0.065, 48), rearFilter, [-0.041, 0.137, 0.0027]);
  screen.castShadow = false;
  topDustFilter(parent);
  return { panel: panelLight(parent, manager), ...powerCompartment(parent, p, steel) };
}
