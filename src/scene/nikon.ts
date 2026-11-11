import * as T from 'three';
import { box, cable, canvasTexture, group, mesh, surface, tube, type XYZ } from './geometry';
import type { Palette } from './materials';

function marking(
  parent: T.Object3D,
  text: string,
  width: number,
  height: number,
  pos: XYZ,
  color = '#e1e0d8',
) {
  const map = canvasTexture(384, 108, (ctx) => {
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = color;
    ctx.font = '600 56px "IBM Plex Sans", sans-serif';
    ctx.fillText(text, 192, 56, 364);
  });
  const label = mesh(
    parent,
    new T.PlaneGeometry(width, height),
    new T.MeshBasicMaterial({
      map,
      transparent: true,
      depthWrite: false,
    }),
    pos,
  );
  label.castShadow = false;
  return label;
}

function zoomLens(parent: T.Object3D, p: Palette) {
  const lens = group(parent, 'NIKKOR Z 24–70mm f/2.8 S II', [0.012, -0.003, 0.029]);
  const barrel = p.graphite.clone();
  barrel.color.set('#24282c');
  barrel.roughness = 0.54;
  const trim = surface('#303539', 0.31, 0.47);
  const profile = [
    [0, 0],
    [0.0328, 0],
    [0.0356, 0.011],
    [0.0385, 0.018],
    [0.0385, 0.052],
    [0.041, 0.065],
    [0.041, 0.119],
    [0.042, 0.126],
    [0.042, 0.142],
    [0.0384, 0.142],
    [0.0371, 0.132],
    [0.0361, 0.124],
    [0, 0.124],
  ];
  const shell = mesh(
    lens,
    new T.LatheGeometry(
      profile.map(([r, z]) => new T.Vector2(r, z)),
      88,
    ),
    barrel,
  );
  shell.rotation.x = Math.PI / 2;
  for (const [z, radius, length] of [
    [0.029, 0.0393, 0.011],
    [0.08, 0.0417, 0.032],
    [0.116, 0.0417, 0.017],
  ]) {
    const ring = mesh(lens, new T.CylinderGeometry(radius, radius, length, 72, 1, true), p.rubber, [
      0,
      0,
      z,
    ]);
    ring.rotation.x = Math.PI / 2;
    for (let i = 0; i < 72; i++) {
      const angle = (i * Math.PI) / 36;
      const grip = box(
        lens,
        [0.0008, 0.00055, length - 0.0016],
        [Math.sin(angle) * radius, Math.cos(angle) * radius, z],
        p.black,
      );
      grip.rotation.z = -angle;
    }
  }
  for (const [z, radius] of [
    [0.008, 0.0346],
    [0.059, 0.04],
    [0.132, 0.0418],
    [0.1415, 0.0414],
  ]) {
    mesh(lens, new T.TorusGeometry(radius, 0.0007, 8, 80), trim, [0, 0, z]);
  }
  const scale = marking(lens, '24   28   35   50   70', 0.032, 0.007, [0, 0.0398, 0.056]);
  scale.rotation.x = -Math.PI / 2;
  box(lens, [0.00065, 0.0006, 0.0044], [0, 0.0401, 0.0602], surface('#cbc8b6', 0.65));
  box(lens, [0.003, 0.014, 0.022], [-0.038, 0, 0.046], barrel, 0.0016);
  for (const z of [0.043, 0.052])
    box(lens, [0.0026, 0.005, 0.004], [-0.04, 0.001, z], p.graphite, 0.001);

  const recess = new T.MeshStandardMaterial({ color: '#0d1114', roughness: 0.53 });
  const iris = canvasTexture(384, 384, (ctx) => {
    const glow = ctx.createRadialGradient(192, 192, 15, 192, 192, 192);
    glow.addColorStop(0, '#020304');
    glow.addColorStop(0.36, '#0a0d13');
    glow.addColorStop(0.73, '#151b23');
    glow.addColorStop(1, '#0c1115');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, 384, 384);
    ctx.strokeStyle = '#8a879327';
    ctx.lineWidth = 1.5;
    for (let i = 0; i < 11; i++) {
      ctx.save();
      ctx.translate(192, 192);
      ctx.rotate((i * 2 * Math.PI) / 11);
      ctx.beginPath();
      ctx.moveTo(50, 2);
      ctx.quadraticCurveTo(78, -4, 139, -45);
      ctx.stroke();
      ctx.restore();
    }
  });
  const backGlass = new T.MeshStandardMaterial({ map: iris, roughness: 0.24, metalness: 0.32 });
  mesh(lens, new T.CircleGeometry(0.0357, 72), backGlass, [0, 0, 0.1245]);
  for (const [z, radius] of [
    [0.127, 0.034],
    [0.134, 0.0365],
    [0.139, 0.0374],
  ]) {
    mesh(lens, new T.TorusGeometry(radius, 0.00042, 6, 72), recess, [0, 0, z]);
  }
  const opticalGlass = new T.MeshPhysicalMaterial({
    color: '#334d48',
    metalness: 0.19,
    roughness: 0.105,
    clearcoat: 0.95,
    clearcoatRoughness: 0.06,
    transparent: true,
    opacity: 0.46,
    depthWrite: false,
    ior: 1.48,
    iridescence: 0.38,
    iridescenceIOR: 1.41,
    iridescenceThicknessRange: [95, 224],
  });
  const element = mesh(
    lens,
    new T.SphereGeometry(0.0358, 64, 20, 0, Math.PI * 2, 0, Math.PI / 2),
    opticalGlass,
    [0, 0, 0.13],
  );
  element.rotation.x = Math.PI / 2;
  element.scale.y = 0.19;
  element.castShadow = false;
  mesh(lens, new T.TorusGeometry(0.0367, 0.00075, 8, 80), p.black, [0, 0, 0.136]);
  for (const [z, radius] of [
    [0.132, 0.0314],
    [0.128, 0.0264],
    [0.1255, 0.0195],
  ]) {
    mesh(lens, new T.TorusGeometry(radius, 0.00055, 7, 72), trim, [0, 0, z]);
  }
  const lettering = canvasTexture(768, 768, (ctx) => {
    ctx.fillStyle = '#d7d7cc';
    ctx.font = '500 27px "IBM Plex Sans", sans-serif';
    ctx.textAlign = 'center';
    const arcText = (text: string, start: number, step: number, rotate: number) => {
      for (let i = 0; i < text.length; i++) {
        const a = start + step * (i - (text.length - 1) / 2);
        ctx.save();
        ctx.translate(384 + 354 * Math.cos(a), 384 + 354 * Math.sin(a));
        ctx.rotate(a + rotate);
        ctx.fillText(text[i], 0, 9);
        ctx.restore();
      }
    };
    arcText('NIKKOR Z', -Math.PI / 2, 0.041, Math.PI / 2);
    arcText('24–70mm 1:2.8 S II   ⌀77', Math.PI / 2, -0.038, -Math.PI / 2);
  });
  mesh(
    lens,
    new T.RingGeometry(0.0376, 0.0415, 88),
    new T.MeshBasicMaterial({
      map: lettering,
      transparent: true,
      depthWrite: false,
    }),
    [0, 0, 0.1424],
  ).castShadow = false;
}

function dial(
  parent: T.Object3D,
  p: Palette,
  position: XYZ,
  radius: number,
  axis: 'top' | 'front' | 'rear',
) {
  const dial = group(parent, 'Knurled command dial', position);
  dial.rotation.x = axis === 'rear' ? -Math.PI / 2 : axis === 'front' ? Math.PI / 2 : 0;
  tube(dial, [0, -0.0021, 0], [0, 0.002, 0], radius, p.graphite);
  for (let i = 0; i < 28; i++) {
    const angle = (i * Math.PI * 2) / 28;
    const ridge = box(
      dial,
      [0.00065, 0.003, 0.001],
      [Math.sin(angle) * radius, 0, Math.cos(angle) * radius],
      p.black,
    );
    ridge.rotation.y = angle;
  }
  return dial;
}

function rearButton(
  parent: T.Object3D,
  p: Palette,
  x: number,
  y: number,
  label: string,
  radius = 0.0034,
) {
  tube(parent, [x, y, -0.0335], [x, y, -0.0364], radius + 0.0009, p.black);
  tube(parent, [x, y, -0.0364], [x, y, -0.0379], radius, p.graphite, radius * 0.91);
  const legend = marking(parent, label, radius * 1.68, radius * 1.05, [x, y, -0.0381]);
  legend.rotation.y = Math.PI;
}

function rearControls(camera: T.Group, p: Palette, photo: T.Texture) {
  const eye = group(camera, 'Recessed EVF and rubber eyecup', [0.008, 0.05, -0.031]);
  box(eye, [0.047, 0.04, 0.006], [0, 0, 0], p.black, 0.007);
  const cup = mesh(eye, new T.TorusGeometry(0.0144, 0.0034, 12, 60), p.rubber, [0, 0, -0.0057]);
  cup.scale.x = 1.11;
  mesh(eye, new T.TorusGeometry(0.0105, 0.00115, 10, 52), p.graphite, [0, 0, -0.0054]).scale.x =
    1.09;
  const ocular = new T.MeshPhysicalMaterial({
    color: '#4b4c37',
    roughness: 0.13,
    metalness: 0.19,
    clearcoat: 0.84,
    iridescence: 0.32,
  });
  box(eye, [0.017, 0.013, 0.0016], [0, 0, -0.0047], ocular, 0.0028);
  for (const x of [-0.018, 0.018])
    tube(eye, [x, 0.015, -0.003], [x, 0.015, -0.0035], 0.0011, p.steel);

  const monitor = group(camera, 'Four-axis rear LCD carrier', [0.016, -0.014, -0.0355]);
  box(monitor, [0.089, 0.062, 0.004], [0, 0, 0], p.black, 0.0024);
  box(monitor, [0.084, 0.057, 0.0025], [0, 0, -0.0026], p.graphite, 0.0018);
  box(monitor, [0.077, 0.049, 0.0012], [0, 0, -0.004], p.black, 0.0015);
  box(monitor, [0.0695, 0.046, 0.0008], [0.001, 0, -0.00472], p.black, 0.0005);
  const playback = mesh(
    monitor,
    new T.PlaneGeometry(0.0613, 0.0459),
    new T.MeshBasicMaterial({
      map: photo,
      color: '#dedede',
      toneMapped: false,
    }),
    [0.001, 0, -0.00515],
  );
  playback.name = 'Playback · Dalian Xinghai Bay';
  playback.rotation.y = Math.PI;
  playback.castShadow = playback.receiveShadow = false;
  for (const x of [-0.034, 0.033]) {
    box(monitor, [0.01, 0.005, 0.003], [x, -0.0285, -0.0002], p.graphite, 0.001);
    tube(monitor, [x - 0.0038, -0.029, -0.0021], [x + 0.0038, -0.029, -0.0021], 0.00085, p.steel);
  }
  for (const [x, y, text] of [
    [0.06, 0.028, 'Fn3'],
    [0.047, 0.028, '×'],
    [-0.023, 0.03, 'DISP'],
    [-0.041, 0.03, 'AF-ON'],
    [-0.043, 0.001, 'i'],
    [-0.042, -0.027, '+'],
    [-0.056, -0.027, 'MENU'],
    [-0.042, -0.039, '−'],
    [-0.056, -0.039, '▶'],
  ] as const)
    rearButton(camera, p, x, y, text, text === 'DISP' ? 0.0043 : 0.0033);
  tube(camera, [-0.042, 0.015, -0.033], [-0.042, 0.015, -0.038], 0.0043, p.black);
  tube(camera, [-0.042, 0.015, -0.038], [-0.042, 0.015, -0.041], 0.0029, p.graphite);
  for (const x of [-0.0435, -0.042, -0.0405])
    for (const y of [0.0135, 0.015, 0.0165]) {
      tube(camera, [x, y, -0.041], [x, y, -0.0416], 0.00037, p.rubber);
    }
  mesh(camera, new T.TorusGeometry(0.0076, 0.0018, 8, 40), p.graphite, [-0.049, -0.014, -0.0378]);
  rearButton(camera, p, -0.049, -0.014, 'OK', 0.0036);
  dial(camera, p, [-0.057, 0.028, -0.035], 0.0059, 'rear');
  const thumb = box(camera, [0.014, 0.04, 0.004], [-0.064, -0.002, -0.0347], p.cameraGrip, 0.0038);
  thumb.rotation.z = -0.04;
}

function topControls(camera: T.Group, p: Palette, alloy: T.MeshStandardMaterial) {
  const controlShoulder = box(
    camera,
    [0.047, 0.009, 0.062],
    [-0.049, 0.0385, 0.008],
    alloy,
    0.0022,
  );
  controlShoulder.name = 'Flat alloy shoulder';
  const lcd = new T.MeshPhysicalMaterial({
    color: '#182025',
    roughness: 0.23,
    clearcoat: 0.78,
    clearcoatRoughness: 0.13,
  });
  box(camera, [0.029, 0.0006, 0.025], [-0.047, 0.04305, -0.01], p.black, 0.00025);
  box(camera, [0.025, 0.00045, 0.021], [-0.047, 0.04334, -0.01], lcd, 0.0002);
  for (const [text, z, height] of [
    ['M   250   F2.8', -0.016, 0.0048],
    ['AF-C     ISO 64', -0.01, 0.0037],
    ['RAW  •  430', -0.004, 0.0035],
  ] as const) {
    const line = marking(camera, text, 0.023, height, [-0.047, 0.04359, z]);
    line.rotation.x = -Math.PI / 2;
    line.material.opacity = 0.65;
  }
  const shutter = group(
    camera,
    'Power collar, shutter and record controls',
    [-0.054, 0.042, 0.032],
  );
  shutter.rotation.x = 0.22;
  tube(shutter, [0, 0, 0], [0, 0.003, 0], 0.0102, p.rubber);
  tube(shutter, [0, 0.003, 0], [0, 0.0053, 0], 0.0061, p.graphite, 0.0058);
  box(shutter, [0.0036, 0.0032, 0.011], [-0.0065, 0.0032, 0.006], p.graphite, 0.0008).rotation.y =
    -0.34;
  const collar = marking(shutter, 'OFF   ON', 0.013, 0.004, [0.001, 0.0033, -0.007]);
  collar.rotation.x = -Math.PI / 2;
  for (const [x, z, text] of [
    [-0.043, 0.018, 'ISO'],
    [-0.054, 0.015, '●'],
    [-0.066, 0.017, '±'],
  ] as const) {
    tube(camera, [x, 0.041, z], [x, 0.0448, z], 0.0036, p.black, 0.0028);
    const label = marking(
      camera,
      text,
      0.0064,
      0.0044,
      [x, 0.045, z],
      text === '●' ? '#ea724e' : undefined,
    );
    label.rotation.x = -Math.PI / 2;
  }
  dial(camera, p, [-0.053, 0.03, 0.0485], 0.0065, 'front');
  const mode = dial(camera, p, [0.047, 0.0445, -0.0035], 0.0135, 'top');
  for (const [x, z, text] of [
    [0, 0, ''],
    [-0.008, 0, 'WB'],
    [0.008, 0, 'BKT'],
    [0, -0.008, 'MODE'],
    [0, 0.008, '▣'],
  ] as const) {
    tube(mode, [x, 0.0019, z], [x, 0.0039, z], 0.00335, p.black, 0.0028);
    if (text) marking(mode, text, 0.0063, 0.004, [x, 0.00415, z]).rotation.x = -Math.PI / 2;
  }
  const shoe = group(camera, 'Metal hot shoe and flash contacts', [0.008, 0.0676, -0.008]);
  box(shoe, [0.025, 0.0018, 0.023], [0, 0, 0], p.black, 0.0008);
  for (const x of [-0.011, 0.011]) {
    box(shoe, [0.0032, 0.0031, 0.022], [x, 0.0019, 0], p.steel, 0.0005);
    box(shoe, [0.0053, 0.0015, 0.022], [x * 0.91, 0.003, 0], p.graphite, 0.0005);
  }
  for (const z of [-0.005, 0.002, 0.006])
    tube(shoe, [0, 0.0009, z], [0, 0.0015, z], 0.00105, p.bronze);
}

function baseHardware(camera: T.Group, p: Palette) {
  const base = group(camera, 'Battery door and tripod mounting plate', [0, -0.051, 0]);
  box(base, [0.037, 0.0014, 0.055], [-0.051, -0.0006, 0.01], p.rubber, 0.0006);
  box(base, [0.033, 0.0015, 0.051], [-0.051, -0.0014, 0.009], p.graphite, 0.0006);
  box(base, [0.009, 0.002, 0.008], [-0.051, -0.002, 0.011], p.black, 0.0006);
  box(base, [0.067, 0.0012, 0.039], [0.02, -0.0004, -0.005], p.graphite, 0.0005);
  for (const z of [-0.019, -0.014, -0.009, 0.001, 0.006, 0.011]) {
    box(base, [0.055, 0.0007, 0.001], [0.02, -0.0012, z], p.black);
  }
  const mount = mesh(
    base,
    new T.TorusGeometry(0.0031, 0.00105, 10, 40),
    p.steel,
    [0.014, -0.002, -0.002],
  );
  mount.rotation.x = Math.PI / 2;
  tube(base, [0.014, -0.001, -0.002], [0.014, -0.0023, -0.002], 0.0022, p.black);
  for (const [x, z] of [
    [-0.06, -0.01],
    [-0.061, 0.032],
    [-0.004, -0.017],
    [0.047, -0.017],
    [0.047, 0.01],
  ]) {
    tube(base, [x, -0.0004, z], [x, -0.0017, z], 0.0016, p.black);
    box(base, [0.0018, 0.0004, 0.0004], [x, -0.0019, z], p.steel);
  }
}

export function nikonZ8(parent: T.Object3D, p: Palette, loader: T.TextureLoader) {
  const camera = group(parent, 'Nikon Z8 with NIKKOR Z 24–70mm f/2.8 S II', [0.526, 0.805, -0.201]);
  camera.rotation.y = 0.27;
  const alloy = p.black.clone();
  alloy.color.set('#2c3032');
  alloy.roughness = 0.63;
  alloy.metalness = 0.29;
  const chassisOutline = [
    [-0.068, -0.036],
    [-0.058, -0.046],
    [0.056, -0.046],
    [0.068, -0.036],
    [0.068, 0.023],
    [0.058, 0.037],
    [0.04, 0.041],
    [-0.03, 0.041],
    [-0.061, 0.032],
    [-0.068, 0.017],
  ];
  const chassis = new T.Shape(chassisOutline.map(([x, y]) => new T.Vector2(x, y)));
  mesh(
    camera,
    new T.ExtrudeGeometry(chassis, {
      depth: 0.053,
      bevelEnabled: true,
      bevelSegments: 4,
      bevelThickness: 0.004,
      bevelSize: 0.004,
    }),
    alloy,
    [0, 0, -0.031],
  );
  box(camera, [0.142, 0.006, 0.056], [0, -0.047, -0.006], p.black, 0.0025);
  // The grip projects past the chassis side. Equal x extents cause the two faces to fight at glancing angles.
  box(camera, [0.047, 0.086, 0.064], [-0.0526, -0.004, 0.018], p.cameraGrip, 0.013);
  const cardDoor = group(camera, 'Recessed card door and release latch', [-0.0735, -0.009, -0.016]);
  box(cardDoor, [0.004, 0.051, 0.028], [0, 0, 0], p.black, 0.002);
  box(cardDoor, [0.0024, 0.046, 0.023], [-0.002, 0.0002, -0.0008], p.cameraGrip, 0.0011);
  box(cardDoor, [0.001, 0.014, 0.008], [-0.0034, -0.009, -0.005], p.graphite, 0.0006);
  for (const y of [-0.013, -0.01, -0.007]) {
    box(cardDoor, [0.0006, 0.0007, 0.0042], [-0.0041, y, -0.005], p.rubber, 0.00024);
  }
  const portSeals = group(camera, 'Gasketed terminal covers', [0.0725, -0.009, -0.01]);
  for (const [y, h] of [
    [0.013, 0.021],
    [-0.014, 0.023],
  ]) {
    box(portSeals, [0.0026, h, 0.027], [0, y, 0.002], p.rubber, 0.0011);
    box(portSeals, [0.0011, h - 0.003, 0.023], [0.0019, y, 0.002], p.black, 0.0005);
  }
  cable(
    camera,
    [
      [-0.073, 0.029, 0.03],
      [-0.068, 0.025, 0.043],
      [-0.061, 0.022, 0.05],
      [-0.05, 0.022, 0.051],
      [-0.044, 0.022, 0.049],
    ],
    0.00128,
    surface('#9b302b', 0.48),
  );
  const viewfinderOutline = new T.Shape([
    new T.Vector2(-0.033, 0.034),
    new T.Vector2(-0.024, 0.054),
    new T.Vector2(-0.012, 0.0655),
    new T.Vector2(0.027, 0.0655),
    new T.Vector2(0.037, 0.053),
    new T.Vector2(0.041, 0.035),
  ]);
  mesh(
    camera,
    new T.ExtrudeGeometry(viewfinderOutline, {
      depth: 0.046,
      bevelEnabled: true,
      bevelSegments: 3,
      bevelThickness: 0.003,
      bevelSize: 0.003,
    }),
    alloy,
    [0, 0, -0.025],
  );
  marking(camera, 'Nikon', 0.035, 0.011, [0.008, 0.053, 0.0244]);
  marking(camera, 'Z 8', 0.02, 0.009, [0.054, 0.028, 0.0267]);
  const photo = loader.load('/media/photography/dalian-xinghai-bay.webp');
  photo.colorSpace = T.SRGBColorSpace;
  photo.anisotropy = 8;
  rearControls(camera, p, photo);
  topControls(camera, p, alloy);
  baseHardware(camera, p);
  for (const side of [-1, 1]) {
    const x = side * 0.073;
    box(camera, [0.006, 0.012, 0.01], [x, 0.026, -0.002], alloy, 0.002);
    mesh(camera, new T.TorusGeometry(0.0032, 0.00105, 10, 32), p.steel, [
      x + side * 0.0033,
      0.026,
      0.001,
    ]);
  }
  for (const [y, text] of [
    [0.012, 'Fn1'],
    [-0.002, 'Fn2'],
  ] as const) {
    tube(camera, [-0.034, y, 0.026], [-0.034, y, 0.031], 0.004, p.black, 0.0031);
    marking(camera, text, 0.007, 0.003, [-0.034, y, 0.0312]);
  }
  const mount = mesh(
    camera,
    new T.TorusGeometry(0.0347, 0.0014, 10, 80),
    p.steel,
    [0.012, -0.003, 0.0286],
  );
  mount.name = 'Z mount retaining rim';
  zoomLens(camera, p);
  return camera;
}
