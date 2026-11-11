import * as T from 'three';
import type { Environment } from '../app/environment';
import { biography, books, publicProfiles } from '../content/profile';
import { remoteKeys } from '../app/environment';
import type { Locale } from '../app/locale';
import { travelCaption, travelPrints } from '../content/travel';
import { personalArchive } from './archive';
import { batchMeshes } from './batching';
import { chairPosition, taskChair } from './chair';
import {
  architecture,
  bookshelf,
  deskFurniture,
  radiator,
  trainingCorner,
  workshop,
  workshopLayout,
} from './furniture';
import { box, group, luminous, mesh, tube } from './geometry';
import { deskSetup, display, keyboard, monitor, mouse, speaker, tower } from './hardware';
import { contactTexture, materials } from './materials';
import { nikonZ8 } from './nikon';
import { notebookSignature } from './notebook';
import { deskPhotoFrame, landmarkPrint, photoPrinter, photoTile } from './photography';
import { deskObjects, lamp, remote } from './props';
import { rocketModel } from './rocket';
import { aerospaceTitle, schoolNotebook } from './school';
import { wallAtlas } from './travel-map';
import { careerAlbums } from './career-albums';
import { buildWindow } from './window';

export type AppID = 'about' | 'music' | 'game' | 'settings';
export type Target = {
  id: string;
  label: string;
  english: string;
  object: T.Object3D;
} & (
  | {
      type: 'inspect';
      size: number;
      pose?: [number, number, number];
      viewDistance?: number;
      caption?: { en: string; zh: string };
      link?: {
        url: string;
        region: { left: number; right: number; top: number; bottom: number; z: number };
      };
    }
  | {
      type:
        | 'remote'
        | 'window'
        | 'case'
        | 'lamp'
        | 'bench-lamp'
        | 'aura'
        | 'workbench'
        | 'map'
        | 'map-pin'
        | 'board'
        | 'door';
    }
  | { type: 'computer'; app?: AppID }
  | { type: 'drawer' | 'key'; index: number }
);

const windowButtons = [
  'Raise or lower blinds',
  'Tilt the slats',
  'Switch city',
  'Change weather',
  'Shuffle the window scene',
  'Switch day or night',
];

export function buildStudio(manager: T.LoadingManager) {
  const root = new T.Group();
  root.name = 'Felix Studio';
  const interior = group(root, 'Interior');
  const loader = new T.TextureLoader(manager);
  const p = materials(loader);
  const photo = (src: string) => {
    const texture = loader.load(src);
    texture.colorSpace = T.SRGBColorSpace;
    texture.anisotropy = 8;
    return texture;
  };
  const atlas = photo('/media/photography/travel-prints.webp');
  const hometown = photo('/media/photography/fanjingshan-print.webp');
  const places = [...travelPrints.slice(0, 6).map((_, i) => photoTile(atlas, i)), hometown];
  const aura = Array.from({ length: 7 }, (_, i) =>
    luminous(new T.Color().setHSL(i / 7, 0.68, 0.48), 1.35),
  );
  const keyLight = Array.from({ length: 12 }, () => luminous('#98aebb', 0.17));
  const mouseLight = luminous('#9bbdc9', 0.28);
  const speakerMeter = Array.from({ length: 6 }, (_, i) =>
    luminous(i < 4 ? '#b3d7cc' : '#ffbb79', 0.07),
  );
  const architectureParts = architecture(interior, p);
  const { drawers, drive } = deskFurniture(interior, p);
  const window = buildWindow(root, p, loader);
  radiator(interior, p);
  const { books: booksInRoom, awards } = bookshelf(interior, p);
  const bench = workshop(interior, p);
  trainingCorner(interior, p);
  taskChair(interior, p);

  const shadows = new T.MeshBasicMaterial({
    map: contactTexture(),
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });
  const leftSpeaker = speaker(interior, p, -1, speakerMeter);
  const music = speaker(interior, p, 1, speakerMeter);
  const deskAnchors = [
    [display.x - 0.28, display.z + 0.105, 0.112, 0.083],
    [display.x + 0.28, display.z + 0.105, 0.112, 0.083],
    [display.x, display.z - 0.105, 0.14, 0.244],
    [0.902, -0.153, 0.377, 0.71],
    [-0.987, -0.114, 0.176, 0.176],
    [leftSpeaker.position.x, leftSpeaker.position.z, 0.153, 0.159],
    [music.position.x, music.position.z, 0.153, 0.159],
    [-0.974, 0.155, 0.23, 0.12],
    [0.52, 0.205, 0.15, 0.132],
    [0.65, 0.023, 0.17, 0.13],
    [-0.733, 0.031, 0.153, 0.125],
    [0.488, 0.315, 0.19, 0.22],
  ];
  const floorAnchors = [
    [-1, 0.16, 0.58, 0.73],
    [0.99, 0.16, 0.58, 0.73],
    [1.55, -0.41, 0.69, 0.42],
    [-0.54, 2.92, 1.31, 0.41],
    [chairPosition.x, chairPosition.z, 0.61, 0.61],
    [0.91, 2.94, 0.62, 0.36],
    [2.29, -0.33, 0.49, 0.51],
    [workshopLayout.x, workshopLayout.z, 0.63, 1.46],
    [1.61, workshopLayout.z, 0.39, 0.39],
  ];
  function shadeSurface(x: number, y: number, z: number, width: number, depth: number) {
    const shade = mesh(interior, new T.PlaneGeometry(width, depth), shadows, [x, y, z]);
    shade.rotation.x = -Math.PI / 2;
    shade.castShadow = shade.receiveShadow = false;
  }
  for (const [x, z, width, depth] of deskAnchors) shadeSurface(x, 0.7506, z, width, depth);
  for (const [x, z, width, depth] of floorAnchors) shadeSurface(x, 0.0051, z, width, depth);
  const { mat: pad } = deskSetup;
  const mat = group(interior, 'Desk mat', [pad.x, pad.top - 0.0015, pad.z]);
  box(mat, [pad.width, 0.003, pad.depth], [0, 0, 0], p.rubber, 0.00135).castShadow = false;
  mat.castShadow = false;
  const desktopFabric = p.cloth.clone();
  const graphic = photo('/media/materials/rog-scabbard-edition-20.png');
  // Fit the mat's bounds in the square, transparent ROG gallery photograph.
  graphic.repeat.set(603 / 732, 268 / 732);
  graphic.offset.set(66 / 732, 230 / 732);
  desktopFabric.map = graphic;
  desktopFabric.alphaTest = 0.5;
  desktopFabric.sheen = 0.08;
  desktopFabric.roughness = 0.94;
  desktopFabric.normalMap = p.cloth.normalMap!.clone();
  desktopFabric.normalMap.repeat.set((pad.width / pad.depth) * 2, 2);
  const print = mesh(mat, new T.PlaneGeometry(pad.width, pad.depth), desktopFabric, [0, 0.0016, 0]);
  print.rotation.x = -Math.PI / 2;
  print.castShadow = false;
  const { unit: screen, updateDisplay } = monitor(interior, p);
  const { unit: pc, auraButton, updateLightGuide } = tower(interior, p, aura);
  const fans: T.Object3D[] = [];
  pc.traverse((node) => {
    if (node.name === 'Fan rotor') fans.push(node);
  });
  const {
    unit: keys,
    legendMaterials: keyLegends,
    badge: keyBadge,
  } = keyboard(interior, p, keyLight);
  const { unit: pointer, badge: mouseBadge } = mouse(interior, p, mouseLight);
  const task = lamp(interior, p, [-0.987, 0.751, -0.114]);
  const control = remote(interior, p, window.remoteRest);
  const { notebook: journal, pass } = schoolNotebook(interior, p, loader);
  const rocket = rocketModel(interior, p);
  const groupPhoto = deskPhotoFrame(interior, p, photo('/media/photography/desk-portrait.webp'));
  const editions = careerAlbums(bench.unit, p);
  const updateSteam = deskObjects(interior, p);
  const deskCamera = nikonZ8(interior, p, loader);
  const samplePrint = photoPrinter(bench.unit, p, places[2], [0.049, 0.794, -0.33]);
  const atlasFrame = wallAtlas(interior, p, photo('/media/graphics/world-atlas.webp'));
  const { board, objects: archive, setLocale: setBoardLocale } = personalArchive(interior, p);
  board.add(pass);
  pass.position.set(-0.424, -0.201, 0.029);
  pass.rotation.z = 0.1;
  box(board, [0.029, 0.007, 0.005], [-0.422, -0.177, 0.031], p.bronze, 0.0015);
  const travelObjects = [0, 1, 3, 4, 5, 6].map((index, slot) => {
    const column = slot % 3;
    const x = index === 6 ? -0.421 : 0.035 + column * 0.198 + [0.003, -0.009, 0.008][column];
    const y = index === 6 ? 0.049 : (slot < 3 ? 0.129 : -0.151) + [-0.006, 0.004, -0.004][column];
    const width = index === 6 ? 0.238 : 0.137,
      z = 0.029;
    const print = landmarkPrint(board, p, places[index], index, width, [x, y, z]);
    print.card.rotation.z = [0.027, -0.035, 0.017, -0.026, 0.018, 0.031, -0.023][index];
    const fastenerY = y + (width * 2) / 3 - 0.007;
    tube(board, [x, fastenerY, z - 0.002], [x, fastenerY, z + 0.005], 0.0029, p.bronze);
    return { index, print, width };
  });

  const ceilingFixture = group(interior, 'Opal glass ceiling light', [0.4, 2.71, 0.71]);
  const ceilingGlow = luminous('#ffdfb5', 1.1);
  ceilingGlow.color.set('#d8c9b4');
  ceilingGlow.roughness = 0.38;
  const housing = p.bronze.clone();
  housing.color.set('#635344');
  housing.roughness = 0.61;
  const lathe = (profile: number[][]) =>
    new T.LatheGeometry(
      profile.map(([r, y]) => new T.Vector2(r, y)),
      64,
    );
  mesh(
    ceilingFixture,
    lathe([
      [0, -0.027],
      [0.143, -0.027],
      [0.156, -0.02],
      [0.161, -0.011],
      [0.158, -0.006],
      [0.151, 0],
    ]),
    housing,
  );
  mesh(
    ceilingFixture,
    lathe([
      [0, -0.043],
      [0.088, -0.042],
      [0.117, -0.037],
      [0.135, -0.031],
      [0.143, -0.023],
      [0.145, -0.018],
    ]),
    ceilingGlow,
  ).castShadow = false;
  const ceilingReflection = new T.PointLight('#fff0dc', 0, 3.15, 1.6);
  ceilingReflection.position.set(0.4, 2.47, 0.71);

  const mediaTargets = editions.map<Target>(({ edition, album }) => ({
    id: 'album-' + edition.volume,
    type: 'inspect',
    object: album,
    size: 0.145,
    pose: [0.08, -0.07, 0],
    english: edition.name[0],
    label: edition.name[1],
    caption: {
      en: [edition.years[0], edition.name[0], edition.role[0]].join(' · '),
      zh: [edition.years[1], edition.name[1], edition.role[1]].join(' · '),
    },
  }));
  const targets: Target[] = [
    {
      id: 'computer',
      type: 'computer',
      object: screen,
      label: '打开电脑',
      english: 'Open computer',
    },
    {
      id: 'remote',
      type: 'remote',
      object: control.unit,
      label: '拿起遥控器',
      english: 'Pick up the window remote',
    },
    {
      id: 'window',
      type: 'window',
      object: window.pane,
      label: '走到窗前',
      english: 'Look out the window',
    },
    { id: 'lamp', type: 'lamp', object: task.unit, label: '开关台灯', english: 'Toggle desk lamp' },
    {
      id: 'case',
      type: 'case',
      object: pc,
      label: '近看电脑机箱',
      english: 'Look closer at the PC case',
    },
    {
      id: 'aura',
      type: 'aura',
      object: auraButton,
      label: '切换 Aura 灯效',
      english: 'Toggle Aura lighting',
    },
    {
      id: 'rocket',
      type: 'inspect',
      object: rocket,
      label: '检视火箭模型',
      english: 'Inspect the rocket model',
      size: 0.225,
      pose: [0.04, -0.38, 0],
    },
    {
      id: 'desk-photo',
      type: 'inspect',
      object: groupPhoto,
      label: '桌上的合照',
      english: 'Desk portrait',
      size: 0.129,
      viewDistance: 0.41,
    },
    {
      id: 'camera',
      type: 'inspect',
      object: deskCamera,
      label: '检视尼康 Z8',
      english: 'Examine the Nikon Z8',
      size: 0.17,
      pose: [0.1, 0.34, 0],
      caption: {
        en: 'Nikon Z8 · NIKKOR Z 24–70mm f/2.8 S II',
        zh: '尼康 Z8 · 尼克尔 Z 24–70mm f/2.8 S II',
      },
    },
    {
      id: 'travel-map',
      type: 'map',
      object: atlasFrame.frame,
      label: '走近世界地图',
      english: 'Look closer at the world map',
    },
    {
      id: 'photo-board',
      type: 'board',
      object: board,
      label: '走近照片钉板',
      english: 'Look closer at the photo board',
    },
    ...atlasFrame.pins.map<Target>(({ pin, place }) => ({
      id: 'map-pin-' + place.id,
      type: 'map-pin',
      object: pin,
      label: place.zh,
      english: place.en,
    })),
    {
      id: 'school-notebook',
      type: 'inspect',
      object: journal,
      label: aerospaceTitle.zh,
      english: aerospaceTitle.en,
      size: 0.153,
      pose: [0.06, -0.09, 0],
      caption: {
        en: 'Beihang University · ' + biography.school.years,
        zh: biography.school.name + ' · ' + biography.school.years,
      },
    },
    {
      id: 'student-card',
      type: 'inspect',
      object: pass,
      label: '查看学生证',
      english: 'Examine the student card',
      size: 0.078,
      caption: {
        en: 'Beihang University · ' + biography.school.years,
        zh: biography.school.name + ' · ' + biography.school.years,
      },
    },
    {
      id: 'keyboard',
      type: 'inspect',
      object: keys,
      label: '检视机械键盘',
      english: 'Inspect the mechanical keyboard',
      size: 0.335,
      viewDistance: 0.72,
      pose: [1.15, -0.16, 0],
    },
    {
      id: 'mouse',
      type: 'inspect',
      object: pointer,
      label: '检视无线鼠标',
      english: 'Inspect the wireless mouse',
      size: 0.132,
      pose: [1.17, -0.32, 0],
    },
    {
      id: 'music',
      type: 'computer',
      object: music,
      label: '打开音乐',
      english: 'Open Music',
      app: 'music',
    },
    {
      id: 'drive',
      type: 'inspect',
      object: drive,
      label: '检视移动硬盘',
      english: 'Inspect the portable drive',
      size: 0.079,
      pose: [1.2, 0.18, 0],
    },
    {
      id: 'workbench',
      type: 'workbench',
      object: bench.unit,
      label: '转到工作台前',
      english: 'Move to the workbench',
    },
    {
      id: 'workbench-stool',
      type: 'workbench',
      object: bench.stool,
      label: '转到工作台前',
      english: 'Move to the workbench',
    },
    {
      id: 'door',
      type: 'door',
      object: architectureParts.door,
      label: '开关门',
      english: 'Open or close the door',
    },
    {
      id: 'bench-lamp',
      type: 'bench-lamp',
      object: bench.taskLamp.unit,
      label: '开关工作台灯',
      english: 'Toggle workbench lamp',
    },
    {
      id: 'switch-sampler',
      type: 'inspect',
      object: bench.tray,
      label: '检视轴体试样',
      english: 'Examine the switch sampler',
      size: 0.124,
      pose: [1.04, 0.12, 0],
      caption: { en: 'Twelve-switch sampler', zh: '十二位轴体试样' },
    },
    {
      id: 'pliers',
      type: 'inspect',
      object: bench.pliers,
      label: '检视斜口钳',
      english: 'Examine the diagonal cutters',
      size: 0.16,
      pose: [0.08, Math.PI / 2, -0.06],
    },
    {
      id: 'printer-proof',
      type: 'inspect',
      object: samplePrint,
      label: '检视照片试印',
      english: 'Examine the proof print',
      size: 0.104,
      caption: { en: 'Print proof · Belém Tower', zh: '贝伦塔 · 照片试印' },
    },
    ...mediaTargets,
    ...travelObjects.map<Target>(({ index, print, width }) => ({
      id: 'print-' + index,
      type: 'inspect',
      object: print.card,
      size: Math.max(0.152, width),
      label: travelPrints[index].zh,
      english: travelPrints[index].en,
      caption: { en: travelCaption(index, 'en'), zh: travelCaption(index, 'zh') },
    })),
    ...drawers.map<Target>((object, index) => ({
      id: 'drawer-' + index,
      type: 'drawer',
      object,
      index,
      label: '打开抽屉',
      english: 'Open drawer',
    })),
    ...control.buttons.map<Target>((object, index) => ({
      id: 'key-' + index,
      type: 'key',
      object,
      index,
      label: remoteKeys[index],
      english: windowButtons[index],
    })),
    ...booksInRoom.map<Target>((object, index) => ({
      id: 'book-' + index,
      type: 'inspect',
      object,
      size: 0.32,
      label: '翻看《' + books[index][0] + '》',
      english: books[index][1],
      pose: [0, -1.34, 0],
    })),
    ...awards.map<Target>(({ object, en, zh }, index) => ({
      id: 'award-' + index,
      type: 'inspect',
      object,
      size: 0.19,
      label: zh,
      english: en,
      pose: [0.08, -0.1, 0],
    })),
    ...archive.map<Target>(({ id, object, size }, index) => ({
      id: 'archive-' + id + '-' + index,
      type: 'inspect',
      object,
      size,
      label: id === 'accessCard' ? '工作室门禁卡' : 'Felix 的手记',
      english: id === 'accessCard' ? 'Studio access card' : 'Felix’s notebook',
      link: id === 'openSource' ? { url: publicProfiles.x, region: notebookSignature } : undefined,
    })),
  ];
  const byObject = new Map(targets.map((target) => [target.object, target]));
  batchMeshes(interior, new Set([...byObject.keys(), bench.top]));
  const hemisphere = new T.HemisphereLight('#d2e0e9', '#a29486', 0.65);
  const bounce = new T.DirectionalLight('#e6d3b8', 0.46);
  bounce.position.set(0.15, 1.8, 2.8);
  const aperture = new T.SpotLight('#aeccec', 1.8, 5.6, 1.08, 0.9, 1.8);
  aperture.position.set(-1.21, 1.62, 0.49);
  aperture.target.position.set(0.28, 0.78, -0.28);
  const windowLight = new T.DirectionalLight('#6eabff', 1.25);
  windowLight.position.set(-3.4, 2.65, 0.7);
  windowLight.target.position.set(0.4, 0.65, -0.16);

  const warm = new T.SpotLight('#ffd0a6', 8, 4.2, 0.73, 0.88, 1.84);
  warm.position.set(-0.81, 1.076, -0.125);
  warm.target.position.set(-0.47, 0.69, 0.18);
  warm.castShadow = true;
  warm.shadow.mapSize.set(1024, 1024);
  warm.shadow.normalBias = 0.003;
  warm.shadow.radius = 5.5;
  warm.shadow.intensity = 0.62;
  warm.shadow.camera.near = 0.03;
  const upper = new T.SpotLight('#ffebd7', 15, 5.2, 1.2, 0.93, 1.7);
  upper.position.set(0.4, 2.659, 0.71);
  upper.target.position.set(0.35, 0.35, 0.78);
  upper.castShadow = true;
  upper.shadow.mapSize.set(1024, 1024);
  upper.shadow.normalBias = 0.011;
  upper.shadow.radius = 5.5;
  upper.shadow.intensity = 0.48;
  const screenFill = new T.PointLight('#a8bdd3', 0.24, 1.5, 1.6);
  screenFill.position.set(display.x, display.y - 0.12, display.z + 0.13);
  const caseBounce = new T.PointLight('#d7def0', 0.073, 0.58, 2);
  caseBounce.position.set(0.845, 1.28, 0.03);
  const deskBounce = new T.PointLight('#ffd7b5', 0.42, 1.42, 1.78);
  deskBounce.position.set(-0.64, 0.937, -0.23);
  root.add(
    hemisphere,
    bounce,
    windowLight,
    windowLight.target,
    aperture,
    aperture.target,
    warm,
    warm.target,
    upper,
    upper.target,
    ceilingReflection,
    screenFill,
    caseBounce,
    deskBounce,
  );
  const rearBounce = new T.SpotLight('#ebdfd1', 6.5, 0, 1.26, 0.98, 1.7);
  rearBounce.position.set(0.54, 2.59, 1.77);
  rearBounce.target.position.set(0.58, 0.77, 3.11);
  const benchLight = new T.SpotLight('#ffd6aa', 1.65, 1.8, 0.73, 0.85, 1.9);
  bench.taskLamp.bulb.getWorldPosition(benchLight.position);
  benchLight.position.y -= 0.012;
  benchLight.target.position.set(2.11, 0.754, workshopLayout.z - 0.26);
  const inspectionFill = new T.PointLight('#f0e6d6', 0, 0.9, 2);
  root.add(rearBounce, rearBounce.target, benchLight, benchLight.target, inspectionFill);

  let activeDrawer = -1;
  let destination = -1;
  let extension = 0;
  let pressed = -1;
  let pressTime = 0;
  const openLength = 0.39;
  const closedPositions = drawers.map((tray) => tray.position.z);
  const buttonY = control.buttons.map((button) => button.position.y);
  const night = new T.Color('#6ea9f5'),
    cloudy = new T.Color('#bacfe5'),
    sun = new T.Color('#ffe4b8');
  let printLocale: Locale = 'en';
  return {
    root,
    interior,
    targets,
    byObject,
    inspectionFill,
    lightLevels: () => ({
      keyboard: keyLight[0].emissiveIntensity,
      mouse: mouseLight.emissiveIntensity,
      speaker: speakerMeter.reduce((sum, light) => sum + light.emissiveIntensity, 0),
    }),
    canReach(target: Target, mode: string) {
      if (mode === 'remote') return target.type === 'key';
      if (mode === 'window') return target.type === 'remote';
      if (mode === 'map') return target.type === 'map-pin';
      if (mode === 'board') return target.type === 'inspect' && target.object.parent === board;
      if (mode === 'drawer') {
        return (
          (target.type === 'drawer' && target.index === destination) ||
          (target.id === 'drive' && activeDrawer === 3 && extension >= openLength * 0.88)
        );
      }
      if (target.type === 'key' || target.type === 'map-pin') return false;
      if (
        target.type === 'bench-lamp' ||
        target.id === 'switch-sampler' ||
        target.id === 'pliers' ||
        target.id === 'printer-proof' ||
        target.id.startsWith('album-')
      )
        return mode === 'bench';
      return target.id !== 'drive';
    },
    setDrawer(index: number) {
      destination = index;
    },
    drawerCenter(index: number) {
      return drawers[index].parent!.localToWorld(
        new T.Vector3(
          0,
          drawers[index].position.y - 0.053,
          closedPositions[index] + openLength - 0.146,
        ),
      );
    },
    pushButton(index: number) {
      pressed = index;
      pressTime = 0.16;
    },
    toggleDoor: architectureParts.toggle,
    update(
      env: Environment,
      delta: number,
      clock: number,
      audio: { bass: number; mid: number; beat: number },
      viewer: T.Vector3,
    ) {
      if (env.locale !== printLocale) {
        printLocale = env.locale;
        travelObjects.forEach(({ print }) => print.setLocale(printLocale));
        setBoardLocale(printLocale);
      }
      const { blocked, moving: blindsMoving } = window.update(env, delta, viewer);
      const doorMoving = architectureParts.update(delta, clock, env.reducedMotion);
      const ease = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 5);
      const dim = (current: number, goal: number) => T.MathUtils.lerp(current, goal, ease);
      updateSteam(env.reducedMotion ? 1 : clock);
      updateDisplay(env.locale, env.reducedMotion ? 0 : clock);
      updateLightGuide(env.aura, env.reducedMotion ? 0 : clock);
      const musicBeat = env.reducedMotion ? 0 : audio.beat;
      const musicLevel = env.reducedMotion ? 0 : audio.bass * 0.65 + audio.mid * 0.35;
      const rainbow = env.reducedMotion ? 0 : (clock * 0.16) % 1;
      for (const [i, light] of keyLight.entries()) {
        light.emissive.setHSL(rainbow + i / keyLight.length, 0.87, 0.52);
        light.color.copy(light.emissive).multiplyScalar(env.aura ? 0.2 : 0.025);
        light.emissiveIntensity = dim(
          light.emissiveIntensity,
          env.aura ? 0.98 + musicLevel * 1.35 + musicBeat * 1.4 : 0,
        );
        keyLegends[i].emissive.copy(light.emissive);
        keyLegends[i].emissiveIntensity = light.emissiveIntensity * 0.84;
      }
      keyBadge.emissive.copy(keyLight[10].emissive);
      keyBadge.emissiveIntensity = keyLight[10].emissiveIntensity * 1.18;
      mouseLight.emissive.setHSL(rainbow + 0.38, 0.86, 0.54);
      mouseLight.color.copy(mouseLight.emissive).multiplyScalar(env.aura ? 0.2 : 0.025);
      mouseLight.emissiveIntensity = dim(
        mouseLight.emissiveIntensity,
        env.aura ? 0.72 + musicLevel + musicBeat * 1.9 : 0,
      );
      mouseBadge.emissive.copy(mouseLight.emissive);
      mouseBadge.emissiveIntensity = mouseLight.emissiveIntensity * 1.22;
      for (const [i, light] of speakerMeter.entries()) {
        const gain = T.MathUtils.clamp(musicLevel * 10.5 + musicBeat * 2.8 - i, 0, 1);
        light.emissiveIntensity = dim(light.emissiveIntensity, env.aura ? 0.1 + gain * 2.45 : 0);
      }
      windowLight.intensity = dim(
        windowLight.intensity,
        (env.night ? 0.28 : env.weather === '晴' ? 0.95 : 0.67) * (1 - blocked * 0.82),
      );
      windowLight.color.lerp(env.night ? night : env.weather === '晴' ? sun : cloudy, ease);
      aperture.intensity = dim(
        aperture.intensity,
        (env.night ? 1.54 : 11.4) * (1 - blocked * 0.86),
      );
      bounce.intensity = dim(bounce.intensity, env.night ? 0.21 : 0.71);
      hemisphere.intensity = dim(hemisphere.intensity, env.night ? 0.27 : 0.92);
      warm.intensity = dim(warm.intensity, env.lamp ? 7.6 : 0);
      deskBounce.intensity = dim(deskBounce.intensity, env.lamp ? 0.95 : 0);
      task.emitter.emissiveIntensity = dim(task.emitter.emissiveIntensity, env.lamp ? 3.2 : 0.03);
      benchLight.intensity = dim(benchLight.intensity, env.benchLamp ? 2.15 : 0);
      bench.taskLamp.emitter.emissiveIntensity = dim(
        bench.taskLamp.emitter.emissiveIntensity,
        env.benchLamp ? 2.8 : 0.02,
      );
      upper.intensity = dim(upper.intensity, env.night ? 10.2 * env.ceiling : 0);
      ceilingGlow.emissiveIntensity = dim(
        ceilingGlow.emissiveIntensity,
        env.night ? env.ceiling * 4.6 : 0.025,
      );
      ceilingReflection.intensity = dim(
        ceilingReflection.intensity,
        env.night ? env.ceiling * 0.13 : 0,
      );
      for (let i = 0; i < aura.length; i++) {
        const hue = (i * 0.147 + (env.reducedMotion ? 0 : clock * 0.071)) % 1;
        aura[i].color.setHSL(hue, 0.45, env.aura ? 0.25 : 0.14);
        aura[i].emissive.setHSL(hue, 0.58, 0.4);
        aura[i].emissiveIntensity = env.aura ? 0.6 : 0;
      }
      if (!env.reducedMotion)
        fans.forEach((fan, i) => {
          fan.rotation.z += delta * (10 + (i % 3) * 3.5);
        });
      pressTime = Math.max(0, pressTime - delta);
      for (const [i, key] of control.buttons.entries())
        key.position.y =
          buttonY[i] - (i === pressed ? Math.sin((pressTime / 0.16) * Math.PI) * 0.003 : 0);
      const previousExtension = extension;
      if (activeDrawer < 0) activeDrawer = destination;
      if (activeDrawer >= 0) {
        const open = activeDrawer === destination;
        const next = open ? openLength : 0;
        extension = env.reducedMotion
          ? next
          : T.MathUtils.lerp(extension, next, 1 - Math.exp(-delta * 14));
        if (Math.abs(extension - next) < 0.001) extension = next;
        drawers[activeDrawer].position.z = closedPositions[activeDrawer] + extension;
        if (!open && extension === 0) activeDrawer = -1;
      }
      return previousExtension !== extension || blindsMoving || doorMoving;
    },
  };
}
export type StudioModel = ReturnType<typeof buildStudio>;
