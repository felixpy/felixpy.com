import * as T from 'three';
import type { Locale } from '../app/locale';
import { travelPrints } from '../content/travel';
import { box, cable, canvasTexture, group, mesh, random, surface, tube } from './geometry';
import type { Palette } from './materials';
import { landmarkPrint, paperSection, photoEmulsion } from './photography';
import { pictureFrame } from './picture-frame';

const instantPhotos = [
  ['tideline', 'Low tide', '退潮', -0.393, 0.009, -0.095],
  ['blue-hour', 'Blue hour', '蓝调时分', -0.237, 0.148, 0.079],
  ['gelato', 'Two cones', '冰淇淋', -0.157, 0.068, -0.12],
  ['pastry', 'Sunday coffee', '周日咖啡', 0.282, 0.147, 0.035],
  ['shutters', 'Green shutters', '绿百叶窗', 0.383, 0.104, -0.061],
  ['ridge', 'Cloud cover', '云起', -0.221, -0.024, 0.15],
  ['noodles', 'Breakfast', '早餐', -0.355, -0.153, -0.107],
  ['ferry', 'From the ferry', '渡轮上', -0.239, -0.16, 0.084],
  ['camp', 'First light', '第一缕光', 0.07, -0.144, -0.111],
  ['estuary', 'Estuary', '河口', 0.398, -0.151, 0.1],
  ['river-steps', 'Above the river', '河上城景', 0.046, 0.141, 0.039],
  ['tart', 'Market day', '市集点心', -0.14, -0.108, 0.124],
  ['arcade', 'Courtyard', '庭院', 0.132, 0.015, -0.127],
  ['tea', 'A quiet table', '午后茶桌', 0.205, -0.087, 0.051],
  ['tram', 'Last tram', '夜班电车', -0.006, 0.08, 0.113],
  ['waterfront', 'On the bank', '河畔', -0.049, 0.188, -0.062],
  ['flat-white', 'Flat white', '馥芮白', 0.062, -0.023, -0.036],
] as const;

const enlargements = [
  [0, -0.319, 0.088, 0.075],
  [1, -0.104, 0.127, -0.052],
  [3, 0.182, 0.098, 0.057],
  [4, -0.049, -0.079, -0.11],
  [5, 0.311, -0.067, 0.045],
  [6, -0.301, -0.081, -0.068],
] as const;

const overlaidFilm = new Set([
  'tideline',
  'gelato',
  'ridge',
  'noodles',
  'ferry',
  'arcade',
  'waterfront',
]);
const corkFace = 0.0007;
const printThickness = 0.00025908;
const filmThickness = 0.00058;
const printCurl = 0.0011;

function instantPhoto(parent: T.Group, p: Palette, image: T.Texture, note: string, index: number) {
  const photo = group(parent, note);
  const face = canvasTexture(432, 688, (ctx) => {
    const rng = random(149 + index);
    ctx.fillStyle = ['#f7f2e8', '#f2eee5', '#f5f1e9'][index % 3];
    ctx.fillRect(0, 0, 432, 688);
    for (let i = 0; i < 6500; i++) {
      ctx.fillStyle = i % 2 ? '#bea98611' : '#ffffff28';
      ctx.fillRect(rng() * 432, rng() * 688, 0.8, 1.1);
    }
    if (index !== 3 && index !== 7) {
      ctx.translate(215, 621);
      ctx.rotate((rng() - 0.5) * 0.055);
      ctx.font = '500 38px Caveat, cursive';
      ctx.fillStyle = '#494641';
      ctx.textAlign = 'center';
      ctx.fillText(note, 0, 0, 348);
    }
  });
  const backing = surface('#d5d1c5', 0.7);
  paperSection(photo, 'instant-film', 'edge', backing);
  paperSection(photo, 'instant-film', 'back', backing);
  paperSection(
    photo,
    'instant-film',
    'face',
    new T.MeshStandardMaterial({
      map: face,
      roughness: 0.81,
      normalMap: p.paper.normalMap,
      normalScale: new T.Vector2(0.035, 0.035),
    }),
  );
  paperSection(photo, 'instant-film', 'image', photoEmulsion(image));
  paperSection(photo, 'instant-film', 'pod', surface('#4a443f', 0.66));
  paperSection(photo, 'instant-film', 'stripe', p.graphite);
  return photo;
}

function fasten(wall: T.Group, p: Palette, card: T.Object3D, height: number, index: number) {
  const mount = group(wall, 'Print fastener', card.position.toArray());
  mount.rotation.z = card.rotation.z;
  if (index % 11 === 4) {
    const clip = group(mount, 'Foldback clip', [0.005, height / 2, 0.0014]);
    box(clip, [0.012, 0.0068, 0.004], [0, -0.0015, 0.0013], p.graphite, 0.0006);
    for (const z of [0.0038, -0.0009]) {
      cable(
        clip,
        [
          [-0.0047, -0.003, z],
          [-0.004, 0.0005, z],
          [-0.002, 0.004, z],
          [-0.002, 0.008, z],
          [0.002, 0.008, z],
          [0.002, 0.004, z],
          [0.004, 0.0005, z],
          [0.0047, -0.003, z],
        ],
        0.00038,
        p.steel,
      );
    }
    tube(clip, [0, 0.008, -0.008], [0, 0.008, 0.002], 0.0008, p.bronze);
  } else if (index % 7 === 1) {
    const tape = new T.MeshStandardMaterial({
      color: '#cdc197',
      roughness: 0.87,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
    });
    const strip = new T.PlaneGeometry(0.024, 0.0088, 4, 12);
    strip.rotateZ(index % 2 ? 0.23 : -0.14);
    const points = strip.attributes.position;
    const paperTop = (height > 0.1 ? printThickness : filmThickness) / 2;
    for (let i = 0; i < points.count; i++) {
      const fold = T.MathUtils.smoothstep(points.getY(i), 0, 0.0017);
      points.setZ(i, T.MathUtils.lerp(paperTop, corkFace - card.position.z, fold) + 0.00008);
    }
    strip.computeVertexNormals();
    mesh(mount, strip, tape, [-0.004, height / 2, 0]).castShadow = false;
  } else {
    const y = height / 2 - 0.004;
    const shank = tube(mount, [0, y, -0.004], [0, y, 0.0014], 0.00053, p.steel);
    const dome = mesh(
      mount,
      new T.SphereGeometry(0.0024, 14, 9),
      index % 4 === 0 ? p.bronze : index % 4 === 1 ? p.steel : p.graphite,
      [0, y, 0.00135],
    );
    dome.scale.z = 0.49;
    return { mount, shank, dome };
  }
}

type PrintPin = NonNullable<ReturnType<typeof fasten>>;

function instancePrintPins(board: T.Group, pins: PrintPin[]) {
  function addBatch(parts: PrintPin['shank'][], name: string) {
    if (parts.length < 2) return;
    const [first] = parts;
    const batch = new T.InstancedMesh(first.geometry, first.material, parts.length);
    batch.name = name;
    batch.castShadow = first.castShadow;
    batch.receiveShadow = first.receiveShadow;
    batch.userData.exportInstalledInstances = true;
    const transform = new T.Matrix4();
    for (const [index, part] of parts.entries()) {
      const mount = part.parent!;
      mount.updateMatrix();
      part.updateMatrix();
      batch.setMatrixAt(index, transform.multiplyMatrices(mount.matrix, part.matrix));
      part.removeFromParent();
      if (!mount.children.length) mount.removeFromParent();
      if (part.geometry !== first.geometry) part.geometry.dispose();
    }
    batch.computeBoundingSphere();
    board.add(batch);
  }

  for (const left of [true, false]) {
    const side = pins.filter(({ mount }) => mount.position.x < 0 === left);
    addBatch(
      side.map(({ shank }) => shank),
      'Print pin shanks',
    );
    const heads = new Map<T.Material, PrintPin['dome'][]>();
    for (const { dome } of side) {
      const group = heads.get(dome.material) ?? [];
      group.push(dome);
      heads.set(dome.material, group);
    }
    for (const parts of heads.values()) addBatch(parts, 'Print pin heads');
  }
}

export function personalArchive(
  root: T.Group,
  p: Palette,
  places: T.Texture[],
  load: (url: string) => T.Texture,
) {
  const board = group(root, 'Travel photographs and instant film', [-0.183, 1.864, -0.537]);
  const instanced =
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('studio-photo-fasteners') === 'instanced';
  const pins: PrintPin[] | undefined = instanced ? [] : undefined;
  function mountPrint(card: T.Object3D, height: number, index: number) {
    const pin = fasten(board, p, card, height, index);
    if (pin) pins?.push(pin);
  }
  box(board, [0.91, 0.523, 0.018], [0, 0, -0.011], p.woodDark, 0.002);
  const color = load('/media/materials/cork-board.webp');
  const normal = load('/media/materials/cork-grain.webp');
  normal.colorSpace = T.NoColorSpace;
  for (const texture of [color, normal]) {
    texture.wrapS = texture.wrapT = T.RepeatWrapping;
    texture.repeat.set(4.08, 2.35);
  }
  const cork = new T.MeshStandardMaterial({
    map: color,
    normalMap: normal,
    roughness: 0.95,
    color: '#e1dfca',
    normalScale: new T.Vector2(0.39, 0.39),
  });
  mesh(board, new T.PlaneGeometry(0.895, 0.508), cork, [0, 0, corkFace]);
  pictureFrame(board, 0.917, 0.53, 0.0105, 0.024, 0.0058, p.woodDark);
  const original = enlargements.map(([id, x, y, turn], i) => {
    const photo = landmarkPrint(board, p, places[id], id, [
      x,
      y,
      corkFace + printThickness / 2 + 0.000025,
    ]);
    photo.card.rotation.z = turn;
    mountPrint(photo.card, 0.1524, i);
    return {
      id: 'print-' + id,
      object: photo.card,
      size: 0.1524,
      en: travelPrints[id].en,
      zh: travelPrints[id].zh,
      setLocale: photo.setLocale,
    };
  });
  const instantAtlas = load('/media/photography/field-notes-atlas.webp');
  const instantCols = 5;
  const instantRows = 4;
  const instant = instantPhotos.map(([key, en, zh, x, y, turn], i) => {
    const tile = instantAtlas.clone();
    tile.repeat.set(1 / instantCols, 1 / instantRows);
    tile.offset.set(
      (i % instantCols) / instantCols,
      (instantRows - 1 - Math.floor(i / instantCols)) / instantRows,
    );
    const photo = instantPhoto(board, p, tile, en, i);
    const backing = overlaidFilm.has(key) ? printThickness + printCurl + 0.000025 : 0;
    photo.position.set(x, y, corkFace + backing + filmThickness / 2 + 0.000025);
    photo.rotation.z = turn;
    mountPrint(photo, 0.086, i + original.length);
    return { id: 'instant-' + key, object: photo, size: 0.086, en, zh };
  });
  if (pins) instancePrintPins(board, pins);
  const prints = [...original, ...instant];
  return {
    board,
    prints,
    setLocale(locale: Locale) {
      original.forEach((photo) => photo.setLocale(locale));
    },
  };
}
