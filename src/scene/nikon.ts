import * as T from 'three';
import { assetUrl } from '../app/asset-url';
import { box, canvasTexture, group, mesh, surface, tube, type XYZ } from './geometry';
import { loadDisplayModel } from './display-model';
import { nikonBody } from './nikon-body';
import { nikkorZoom } from './nikon-lens';
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
    ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = color;
    ctx.font =
      text === 'Nikon' ? 'italic 900 77px Arial, sans-serif' : '600 61px Arial, sans-serif';
    const bounds = ctx.measureText(text);
    ctx.translate(192, 54);
    const correction = (height / width) * (384 / 108);
    const scale = Math.min(
      352 / (bounds.width * correction),
      82 / (bounds.actualBoundingBoxAscent + bounds.actualBoundingBoxDescent),
    );
    ctx.scale(scale * correction, scale);
    ctx.fillText(text, 0, (bounds.actualBoundingBoxAscent - bounds.actualBoundingBoxDescent) / 2);
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
  tube(parent, [x, y, -0.031], [x, y, -0.0364], radius + 0.0009, p.black);
  tube(parent, [x, y, -0.0364], [x, y, -0.0379], radius, p.graphite, radius * 0.91);
  const legend = marking(parent, label, radius * 1.68, radius * 1.05, [x, y, -0.0381]);
  legend.rotation.y = Math.PI;
}

function rearControls(
  camera: T.Group,
  closedGrip: T.Group,
  p: Palette,
  photo: T.Texture,
  manager: T.LoadingManager,
) {
  const eye = group(camera, 'Recessed EVF and rubber eyecup', [0.016, 0.044, -0.029]);
  void loadDisplayModel(eye, '/media/models/nikon-dk33.glb', manager);

  const monitor = group(camera, 'Four-axis rear LCD carrier', [0.016, -0.014, -0.0355]);
  box(monitor, [0.089, 0.062, 0.004], [0, 0, 0], p.black, 0.0024);
  box(monitor, [0.084, 0.057, 0.0025], [0, 0, -0.0026], p.graphite, 0.0018);
  box(monitor, [0.077, 0.049, 0.0012], [0, 0, -0.004], p.black, 0.0015);
  box(monitor, [0.0695, 0.046, 0.0008], [0.001, 0, -0.00472], p.black, 0.0005);
  const playback = mesh(
    monitor,
    new T.PlaneGeometry(0.0613, 0.0613 / 1.5),
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
  const rearWheel = dial(camera, p, [-0.057, 0.031, -0.0292], 0.0049, 'top');
  rearWheel.scale.x = 1.92;
  const thumb = mesh(
    closedGrip,
    new T.SphereGeometry(1, 36, 18),
    p.cameraGrip,
    [-0.063, -0.006, -0.031],
  );
  thumb.scale.set(0.0078, 0.027, 0.0044);
  thumb.rotation.z = -0.07;
}

function topControls(camera: T.Group, p: Palette) {
  const lcd = new T.MeshStandardMaterial({
    color: '#182025',
    roughness: 0.14,
    metalness: 0.08,
    envMapIntensity: 1.25,
  });
  box(camera, [0.035, 0.00065, 0.019], [-0.046, 0.04265, -0.012], p.black, 0.00025);
  box(camera, [0.028, 0.00045, 0.0156], [-0.043, 0.04299, -0.012], lcd, 0.0002);
  for (const [text, z, height] of [
    ['M   250   F2.8', -0.0076, 0.0039],
    ['AF-C     ISO 64', -0.012, 0.0033],
    ['RAW  •  430', -0.0163, 0.0032],
  ] as const) {
    const line = marking(camera, text, 0.023, height, [-0.043, 0.04324, z]);
    line.rotation.set(-Math.PI / 2, 0, Math.PI);
    line.material.opacity = 0.65;
  }
  for (const [x, z, text] of [
    [-0.043, 0.018, '⏺'],
    [-0.054, 0.015, 'ISO'],
    [-0.066, 0.017, '±'],
  ] as const) {
    const cluster = group(camera, 'Shoulder control', [x, 0.0445 - z * 0.399, z]);
    cluster.rotation.x = 0.385;
    tube(cluster, [0, -0.0011, 0], [0, 0.0008, 0], 0.0042, p.rubber);
    tube(cluster, [0, 0.0006, 0], [0, 0.0021, 0], 0.00335, p.graphite, 0.0031);
    const label = marking(
      cluster,
      text,
      0.0059,
      0.0044,
      [0, 0.00221, 0],
      text === '⏺' ? '#ea724e' : undefined,
    );
    label.rotation.set(-Math.PI / 2, 0, Math.PI);
  }
  const slot = box(camera, [0.022, 0.0055, 0.004], [-0.055, 0.0237, 0.0437], p.black, 0.00185);
  slot.rotation.y = -0.12;
  const wheel = dial(camera, p, [-0.055, 0.0237, 0.0418], 0.0049, 'top');
  wheel.scale.x = 2.05;
}

export function nikonZ8(
  parent: T.Object3D,
  p: Palette,
  photo: T.Texture,
  manager: T.LoadingManager,
  options: { roomLod?: boolean; mounted?: (scene: T.Group) => void } = {},
) {
  const camera = group(parent, 'Nikon Z8 with NIKKOR Z 24–70mm f/2.8 S II', [0.53, 0.802, -0.027]);
  camera.rotation.y = 0.65;
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  const useRoomLod = Boolean(options.roomLod && !authoring);
  const roomGroup = group(camera, 'Nikon Z8 room LOD');
  const roomCardDoorAnchor = useRoomLod
    ? group(roomGroup, 'Z8 closed card door and overmould')
    : undefined;
  const roomHitProxy = useRoomLod
    ? mesh(
        roomGroup,
        new T.BoxGeometry(0.145, 0.115, 0.16),
        new T.MeshLambertMaterial({ colorWrite: false, depthWrite: false }),
        [0, 0.005, 0.04],
      )
    : undefined;
  if (roomHitProxy) roomHitProxy.castShadow = roomHitProxy.receiveShadow = false;
  const heroGroup = group(camera, 'Nikon Z8 hero detail');
  let roomLoaded = false;
  let heroMounted = false;
  let inspecting = false;

  const sync = () => {
    if (!useRoomLod) return;
    heroGroup.visible = (inspecting || !roomLoaded) && heroMounted;
    roomGroup.visible = !heroGroup.visible;
  };

  function ensureHero(loaderManager: T.LoadingManager) {
    if (heroMounted) return;
    heroMounted = true;
    roomCardDoorAnchor?.removeFromParent();
    const target = useRoomLod ? heroGroup : camera;
    const { casting: alloy, closedGrip } = nikonBody(target, p);
    const ports = group(target, 'Terminal cover gaskets', [0.0705, 0, -0.007]);
    for (const [y, height] of [
      [0.004, 0.026],
      [-0.024, 0.024],
    ]) {
      box(ports, [0.0015, height, 0.028], [0, y, 0], p.black, 0.0007);
      box(ports, [0.0018, height - 0.0022, 0.026], [0.001, y, 0], p.rubber, 0.00085);
      box(ports, [0.00085, 0.005, 0.003], [0.0022, y - 0.001, -0.009], alloy, 0.00035);
    }
    const wordmark = marking(target, 'Nikon', 0.03, 0.0068, [0.016, 0.0525, 0.0163]);
    wordmark.rotation.x = -0.57;
    rearControls(target, closedGrip, p, photo, loaderManager);
    topControls(target, p);
    void loadDisplayModel(
      group(target, 'Z8 serviceable body fittings'),
      '/media/models/nikon-z8-hardware.glb',
      loaderManager,
      { mounted: options.mounted },
    );
    for (const side of [-1, 1]) {
      const x = side * 0.0689;
      const lug = group(target, 'Strap eyelet', [x, 0.032, -0.015]);
      lug.rotation.y = side * 0.41;
      box(lug, [0.006, 0.009, 0.007], [0, 0, 0], alloy, 0.0014);
      const ring = mesh(lug, new T.TorusGeometry(0.00295, 0.00105, 10, 32), p.steel, [
        side * 0.0046,
        0,
        0,
      ]);
      ring.scale.x = 0.9;
    }
    for (const [y, text] of [
      [0.004, 'Fn1'],
      [-0.012, 'Fn2'],
    ] as const) {
      const fn = group(target, text, [-0.022, y, 0.0205]);
      fn.rotation.y = -0.46;
      box(fn, [0.0085, 0.012, 0.0048], [0, 0, 0], p.rubber, 0.002);
      marking(fn, text, 0.0062, 0.0032, [0, 0, 0.0025]);
    }
    const assist = group(target, 'Autofocus assist window', [-0.0245, 0.031, 0.0196]);
    tube(assist, [0, 0, 0], [0, 0, 0.002], 0.0037, p.rubber);
    tube(assist, [0, 0, 0.002], [0, 0, 0.0024], 0.00285, surface('#26302f', 0.21, 0.22));
    nikkorZoom(target, loaderManager);
    if (useRoomLod) options.mounted?.(heroGroup);
    sync();
  }

  camera.userData.selectDetail = (active: boolean) => {
    inspecting = active;
    if (active && !heroMounted) {
      ensureHero(new T.LoadingManager().setURLModifier(assetUrl));
    }
    sync();
  };

  if (useRoomLod) {
    sync();
    void loadDisplayModel(roomGroup, '/media/models/nikon-z8-room.glb', manager, {
      mounted() {
        roomLoaded = true;
        roomHitProxy?.removeFromParent();
        sync();
      },
    }).catch(() => {
      inspecting = true;
      ensureHero(new T.LoadingManager().setURLModifier(assetUrl));
    });
  } else {
    roomGroup.removeFromParent();
    heroGroup.removeFromParent();
    ensureHero(manager);
  }
  return camera;
}
