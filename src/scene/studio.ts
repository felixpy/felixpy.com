import * as T from 'three';
import { initialEnvironment, type Environment } from '../app/environment';
import { ceilingLightLevel } from '../app/home-lights';
import { publicProfiles } from '../content/profile';
import { editions as publishedEditions } from '../content/books';
import { remoteKeys } from '../app/environment';
import type { Locale } from '../app/locale';
import { travelPrints } from '../content/travel';
import { personalArchive } from './archive';
import { batchMeshes } from './batching';
import { chairPosition, taskChair } from './aeron-chair';
import {
  architecture,
  bookshelf,
  deskFurniture,
  radiator,
  roomSize,
  workshop,
  workshopLayout,
} from './furniture';
import { collectionVitrine } from './collection-vitrine';
import { deferredDisplayModel, loadDisplayModel } from './display-model';
import { filamentPrinter } from './filament-printer';
import { cabinetFloorLight, ceilingFixture, deskFixture } from './authored-fixtures';
import { desk, windowOpening } from './layout';
import { outdoorRail } from './outdoor-rail';
import { group, luminous, mesh } from './geometry';
import { deskSetup, display, keyboard, monitor, mouse, speaker, tower } from './hardware';
import { macStudio } from './mac-studio';
import { contactTexture, materials } from './materials';
import { nikonZ8 } from './nikon';
import { notebookSignature, projectNotebook } from './notebook';
import { deskPhotoFrame, photoPrinter, photoTile } from './photography';
import { deskObjects, remote } from './props';
import { rearLoading } from './rear-loading';
import { rocketModel } from './rocket';
import { wallAtlas } from './travel-map';
import { buildWindow } from './window';

import { deskPad } from './desk-pad';
import { developmentPhone } from './development-phone';
import { wirelessMicrophone } from './wireless-microphone';
import { skogDiffuser } from './still-life';
import { flightProof, cardStorage } from './flight-proof';

import { opensStudioView, type Mode, type Target } from './interaction';

export {
  opensStudioView,
  type AppID,
  type HardwareOrbit,
  type InspectionLink,
  type Target,
} from './interaction';

const windowButtons = [
  'Raise or lower blinds',
  'Tilt the slats',
  'Switch city',
  'Change weather',
  'Shuffle the window scene',
  'Switch day or night',
];

function loadBitmapTexture(
  loader: T.TextureLoader,
  src: string,
  onLoad?: (texture: T.Texture) => void,
  onError?: (error: unknown) => void,
) {
  const texture = new T.Texture();
  const setImage = (image: TexImageSource) => {
    texture.image = image;
    texture.needsUpdate = true;
    onLoad?.(texture);
  };
  new T.ImageBitmapLoader(loader.manager)
    .setOptions({ imageOrientation: 'flipY', premultiplyAlpha: 'none' })
    .load(src, setImage, undefined, () => {
      loader.load(src, (fallback) => setImage(fallback.image), undefined, onError);
    });
  return texture;
}

export function* buildStudioSteps(
  manager: T.LoadingManager,
  initial = initialEnvironment,
  {
    deferBookBacks = false,
    prioritizeRear = false,
    preloadInspection = false,
    mergeFirst = true,
    warmWaterfront = undefined as ((material: T.ShaderMaterial) => void) | undefined,
    deferWaterMotion = false,
  } = {},
) {
  const root = new T.Group();
  root.name = 'Felix Studio';
  const interior = group(root, 'Interior');
  const mountedDetails: T.Object3D[] = [];
  function detailMounted(model: T.Group) {
    mountedDetails.push(model);
  }
  const loader = new T.TextureLoader(manager);
  const p = materials(loader);
  const bitmapTextures =
    !import.meta.env.DEV &&
    typeof createImageBitmap === 'function' &&
    new URLSearchParams(location.search).get('studio-images') === 'bitmap';
  const photo = (src: string, useBitmap = false) => {
    const texture = bitmapTextures && useBitmap ? loadBitmapTexture(loader, src) : loader.load(src);
    texture.colorSpace = T.SRGBColorSpace;
    texture.anisotropy = 8;
    return texture;
  };
  const atlas = photo('/media/photography/travel-prints.webp', true);
  const hometown = photo('/media/photography/fanjingshan-print.webp', true);
  const places = [...travelPrints.slice(0, 6).map((_, i) => photoTile(atlas, i)), hometown];
  const aura = Array.from({ length: 7 }, (_, i) =>
    luminous(new T.Color().setHSL(i / 7, 0.68, 0.48), 1.35),
  );
  const keyLight = Array.from({ length: 12 }, () => luminous('#98aebb', 0.17));
  const mouseLight = luminous('#9bbdc9', 0.28);
  const speakerMeter = Array.from({ length: 6 }, (_, i) =>
    luminous(i < 4 ? '#b3d7cc' : '#ffbb79', 0.07),
  );
  const bridgePrint = photo('/media/photography/dalian-xinghai-bay.webp');
  const architectureParts = architecture(interior, p, bridgePrint);
  yield;
  const { drawers, drawerInteriors, drive } = deskFurniture(interior, p, loader);
  const { card: memoryCard, prepare: prepareCard } = cardStorage(
    drawerInteriors[3],
    p,
    [0.105, -0.068, -0.208],
    detailMounted,
  );
  const window = buildWindow(root, p, loader, initial, warmWaterfront, deferWaterMotion);
  radiator(interior, p);
  yield;
  const rearLoader = new T.LoadingManager();
  const rear = rearLoading(rearLoader, prioritizeRear || preloadInspection);
  const deferDesk = rear.defer('desk');
  const deferBench = rear.defer('bench');
  const {
    unit: bookcase,
    books: booksInRoom,
    prepareBook,
    prepareBookBacks,
    prepareBookExport,
    awards,
    lamps: shelfLamps,
    accent: shelfAccent,
  } = bookshelf(interior, p, loader, new T.TextureLoader(rearLoader), deferBookBacks);
  yield;
  const bench = workshop(interior, p, loader, rearLoader, deferBench);
  const rearWall = group(interior, 'Field gear and private collection', [
    0,
    0,
    roomSize.south - 0.018,
  ]);
  rearWall.rotation.y = Math.PI;
  const prepareDrive = deferredDisplayModel(drive, '/media/models/samsung-t7.glb', {
    mounted: detailMounted,
  });
  async function prepareDrawerMedia() {
    await Promise.all([prepareDrive(), prepareCard()]);
  }
  deferBench(() => {
    const tools = 'workshop-precision-tools';
    rearLoader.itemStart(tools);
    return bench
      .prepareTools()
      .catch(() => rearLoader.itemError(tools))
      .finally(() => rearLoader.itemEnd(tools));
  });
  yield;
  const fieldGear = outdoorRail(rearWall, p, rearLoader, rear.defer('gear'));
  const vitrine = collectionVitrine(rearWall, p, rearLoader, rear.defer('cabinet'));
  const floorLamp = cabinetFloorLight(interior, p);
  const printer = filamentPrinter(interior, p, rearLoader, deferBench);
  taskChair(interior, p, rearLoader, deferDesk);
  yield;

  const shadows = new T.MeshBasicMaterial({
    map: contactTexture(),
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });
  const musicSpeakers = {
    'music-left': speaker(interior, p, -1, speakerMeter),
    music: speaker(interior, p, 1, speakerMeter),
  };
  const floorAnchors = [
    [-1, 0.16, 0.58, 0.73],
    [0.99, 0.16, 0.58, 0.73],
    [1.55, -0.41, 0.69, 0.42],
    [-0.599, 2.977, 1.2, 0.43],
    [chairPosition.x, chairPosition.z, 0.61, 0.61],
    [0.71, 2.978, 1.19, 0.395],
    [2.29, -0.33, 0.49, 0.51],
    [workshopLayout.x, workshopLayout.z, 0.63, 1.46],
    [1.61, workshopLayout.z, 0.39, 0.39],
  ];
  function shadeSurface(x: number, y: number, z: number, width: number, depth: number) {
    const shade = mesh(interior, new T.PlaneGeometry(width, depth), shadows, [x, y, z]);
    shade.rotation.x = -Math.PI / 2;
    shade.castShadow = shade.receiveShadow = false;
  }
  for (const [x, z, width, depth] of floorAnchors) shadeSurface(x, 0.0051, z, width, depth);
  const { mat: pad } = deskSetup;
  const mat = group(interior, 'Desk mat', [pad.x, pad.top - 0.0015, pad.z]);
  void deskPad(mat, manager);
  const { screen, updateDisplay, screenBar, codexMicro } = monitor(interior, p, manager);
  yield;
  const {
    mac,
    reader,
    prepareDetail: prepareMacDetail,
    selectDetail: selectMacDetail,
  } = macStudio(interior, manager, detailMounted);
  const { phone, update: updatePhone } = developmentPhone(
    interior,
    p,
    photo('/media/graphics/white-dunes.webp'),
  );
  const microphone = wirelessMicrophone(interior, manager);
  const skog = skogDiffuser(interior, [-1.085, 1.31, 2.951], rearLoader, deferDesk);
  const proof = flightProof(interior, p);
  yield;
  const {
    unit: pc,
    updateLightGuide,
    updateTelemetry,
    setComponentLights,
    selectDetail: selectTowerDetail,
    fanGuides,
    reflections,
  } = tower(interior, p, aura, manager);
  yield;
  const channelHues = [0.926, 0.815, 0.727, 0.669, 0.614, 0.558, 0.526];
  const fans: T.Object3D[] = [];
  pc.traverse((node) => {
    if (node.name === 'Fan rotor') fans.push(node);
  });
  const {
    unit: keys,
    legendMaterials: keyLegends,
    badge: keyBadge,
    prepareSwitches,
    selectDetail: selectKeySwitches,
  } = keyboard(interior, manager, keyLight, detailMounted);
  if (preloadInspection) {
    deferDesk(() => prepareMacDetail(rearLoader));
    deferDesk(() => prepareSwitches(rearLoader));
    deferDesk(() => prepareDrive(rearLoader));
    deferDesk(() => prepareCard(rearLoader));
  }
  const { unit: pointer, badge: mouseBadge } = mouse(interior, manager, mouseLight);
  const task = deskFixture(interior, p, [-0.981, 0.75, 0.01], loader);
  const control = remote(interior, manager, window.remoteRest);
  const { model: rocket, prepare: prepareRocket } = rocketModel(bench.unit, p, detailMounted);
  deferBench(() => prepareRocket(rearLoader));
  const groupPhoto = deskPhotoFrame(
    interior,
    manager,
    photo('/media/photography/desk-portrait.webp'),
  );
  const updateSteam = deskObjects(interior, manager);
  const pencil = group(interior, 'Mitsubishi 9850 HB', [0.344, desk.top, 0.313]);
  pencil.rotation.y = Math.PI / 2 - 0.18;
  loadDisplayModel(pencil, '/media/models/mitsubishi-9850.glb', manager);
  const deskCamera = nikonZ8(interior, p, bridgePrint, manager);
  yield;
  const samplePrint = photoPrinter(
    bench.unit,
    places[2],
    [0.049, 0.75, -0.33],
    rearLoader,
    deferBench,
  );
  const mapPreview = photo('/media/graphics/world-atlas-room.webp');
  const atlasFrame = wallAtlas(interior, p, mapPreview);
  deferDesk(async () => {
    const loader = new T.TextureLoader(rearLoader);
    const src = '/media/graphics/world-atlas.webp';
    const detail = bitmapTextures
      ? await new Promise<T.Texture>((resolve, reject) => {
          loadBitmapTexture(loader, src, resolve, reject);
        })
      : await loader.loadAsync(src);
    detail.colorSpace = mapPreview.colorSpace;
    detail.anisotropy = mapPreview.anisotropy;
    atlasFrame.ink.map = detail;
    mapPreview.dispose();
  });
  const { board, prints, setLocale: setBoardLocale } = personalArchive(interior, p, places, photo);
  const notes = projectNotebook(interior, p);

  const ceiling = ceilingFixture(interior);

  const targets: Target[] = [
    {
      id: 'picture-lamp',
      type: 'picture-lamp',
      object: architectureParts.pictureLight.fixture,
      english: 'Switch the picture light',
      label: '开关画灯',
    },
    {
      id: 'equipment-track',
      type: 'equipment-track',
      object: fieldGear.track.fixture,
      english: 'Switch the track lights',
      label: '开关轨道灯',
    },
    {
      id: 'floor-lamp',
      type: 'floor-lamp',
      object: floorLamp.unit,
      english: 'Switch the floor lamp',
      label: '开关落地灯',
    },
    {
      id: 'equipment-wall',
      type: 'gear',
      object: fieldGear.zone,
      english: 'Explore the gear wall',
      label: '走近装备墙',
    },
    {
      id: 'talon-pack',
      type: 'inspect',
      object: fieldGear.bag,
      size: 0.56,
      viewDistance: 0.94,
      pose: [0.07, -0.49, -0.02],
      english: 'Inspect the hiking pack',
      label: '近看登山包',
      caption: {
        en: 'Osprey Talon 26 · Phantom Grey / Dark Charcoal',
        zh: '小鹰魔爪 26 升 · 幻影灰 / 深炭灰',
      },
    },
    ...fieldGear.poles.map((object): Target => ({
      id: object.name,
      type: 'inspect',
      object,
      size: 0.61,
      viewDistance: 0.88,
      pose: [0.05, 0.18, -0.21],
      english: 'Inspect the trekking pole',
      label: '近看登山杖',
      caption: {
        en: 'Black Diamond · Alpine Carbon Cork · Tundra',
        zh: '黑钻 · Alpine Carbon Cork · 苔原绿',
      },
    })),
    {
      id: 'titanium-cup',
      type: 'inspect',
      object: fieldGear.cup,
      size: 0.135,
      viewDistance: 0.3,
      pose: [0.38, -0.18, 0.04],
      english: 'Inspect the titanium cup',
      label: '近看钛杯',
      caption: { en: 'Snow Peak · Ti-Double 450', zh: 'Snow Peak · 双层钛杯 450' },
    },
    {
      id: 'camp-lantern',
      type: 'inspect',
      object: fieldGear.lamp,
      onInspect: fieldGear.selectLanternPort,
      size: 0.27,
      viewDistance: 0.49,
      pose: [0.09, -0.2, 0.025],
      english: 'Inspect the camping lantern',
      label: '近看露营灯',
      caption: { en: 'Snow Peak · HOME & CAMP Lantern', zh: 'Snow Peak · HOME & CAMP 露营灯' },
    },
    {
      id: 'aurora-bottle',
      type: 'inspect',
      object: fieldGear.bottle,
      onInspect: fieldGear.bottleClosure.select,
      size: 0.23,
      viewDistance: 0.42,
      pose: [0.09, -0.15, 0],
      english: 'Inspect the titanium bottle',
      label: '近看钛水瓶',
      caption: {
        en: 'Snow Peak · Aurora Bottle 800 Rainbow',
        zh: 'Snow Peak · Aurora 彩钛水瓶 800',
      },
    },
    {
      id: 'trek-cookset',
      type: 'inspect',
      object: fieldGear.cookset,
      size: 0.145,
      viewDistance: 0.29,
      pose: [0.26, -0.22, 0],
      english: 'Inspect the Trek 900 cookset',
      label: '近看 Trek 900 套锅',
      caption: { en: 'Snow Peak · Titanium Trek 900', zh: 'Snow Peak · Trek 900 钛套锅' },
    },
    {
      id: 'field-coffee-master',
      type: 'inspect',
      object: fieldGear.coffee,
      size: 0.2,
      viewDistance: 0.39,
      pose: [0.18, -0.23, 0],
      english: 'Inspect the coffee percolator',
      label: '近看咖啡壶',
      caption: {
        en: 'Snow Peak · Field Coffee Master PR-880',
        zh: 'Snow Peak · Field Coffee Master 咖啡壶 PR-880',
      },
    },
    {
      id: 'bookshelf',
      type: 'bookshelf',
      object: bookcase,
      english: 'Browse the bookshelf',
      label: '近看书架',
    },
    {
      id: 'collection-cabinet',
      type: 'case',
      object: vitrine.unit,
      english: 'Explore the collection cabinet',
      label: '近看玻璃陈列柜',
      orbit: {
        center: [0, 0.914, 0.174],
        azimuth: [3.05, 2.7, 3.58],
        elevation: [0.105, -0.115, 0.35],
        distance: [1.08, 0.73, 1.45],
      },
    },
    {
      id: 'computer',
      type: 'computer',
      object: screen,
      label: '打开电脑',
      english: 'Open computer',
    },
    ...Object.entries({
      'screen-bar': screenBar.unit,
      'screen-bar-controller': screenBar.dial,
    }).map(([id, object]) => ({
      id,
      type: 'screen-bar' as const,
      object,
      label: '开关屏幕灯',
      english: 'Toggle monitor light',
    })),
    {
      id: 'codex-micro',
      type: 'inspect',
      object: codexMicro,
      size: 0.108,
      viewDistance: 0.19,
      pose: [1.1, -0.12, 0],
      english: 'Inspect the Codex Micro',
      label: '查看 Codex Micro',
      caption: {
        en: 'OpenAI × Work Louder · Codex Micro',
        zh: 'OpenAI × Work Louder · Codex Micro',
      },
    },
    {
      id: 'development-phone',
      type: 'inspect',
      object: phone,
      size: 0.1634,
      viewDistance: 0.235,
      english: 'Unlock the iPhone',
      label: '解锁 iPhone',
      pose: [0, 0, 0],
      caption: { en: 'iPhone 18 Pro Max', zh: 'iPhone 18 Pro Max' },
    },
    {
      id: 'wireless-microphone',
      type: 'inspect',
      object: microphone,
      size: 0.047,
      viewDistance: 0.16,
      english: 'Inspect the wireless microphone',
      label: '查看无线麦克风',
      pose: [0.12, -0.18, 0],
      caption: { en: 'DJI Mic 2 · wireless transmitter', zh: '大疆 Mic 2 · 无线麦克风发射器' },
    },
    {
      id: 'skog',
      type: 'inspect',
      object: skog,
      size: 0.225,
      viewDistance: 0.385,
      pose: [0.12, -0.2, 0],
      label: '查看 SKOG',
      english: 'Inspect the SKOG diffuser',
    },
    {
      id: 'sprite-proof',
      type: 'inspect',
      object: proof.sheet,
      size: 0.254,
      viewDistance: 0.36,
      english: 'Inspect the sprite proof',
      label: '查看像素画试样',
    },
    {
      id: 'camera-card',
      type: 'inspect',
      object: memoryCard,
      size: 0.0385,
      viewDistance: 0.13,
      pose: [1.3, -0.04, 0],
      english: 'Inspect the camera card · ProGrade Gold 256 GB',
      label: '查看相机存储卡 · ProGrade Gold 256 GB',
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
      id: 'mac-studio',
      type: 'case',
      object: mac,
      label: '近看 Mac Studio · M5 Ultra · 512 GB · 16 TB',
      english: 'Look closer at Mac Studio · M5 Ultra · 512 GB · 16 TB',
      orbit: {
        center: [0.009, 0.042, 0.002],
        azimuth: [-0.44, -3.1, -0.3],
        elevation: [0.51, 0.2, 0.71],
        distance: [0.395, 0.255, 0.57],
        rearClearance: 0.225,
      },
    },
    {
      id: 'card-reader',
      type: 'case',
      object: reader,
      label: 'ProGrade PG05.5 · CFexpress B / SD UHS-II',
      english: 'ProGrade PG05.5 · CFexpress B / SD UHS-II',
      orbit: {
        center: [0, 0.01, 0],
        azimuth: [-0.26, -0.78, 0.22],
        elevation: [0.63, 0.24, 1.25],
        distance: [0.159, 0.124, 0.27],
      },
    },
    {
      id: 'case',
      type: 'case',
      object: pc,
      label: '近看电脑机箱',
      english: 'Look closer at the PC case',
    },
    {
      id: 'rocket',
      type: 'inspect',
      object: rocket,
      label: '检视火箭模型',
      english: 'Inspect the rocket model',
      size: 0.225,
      pose: [0.04, 0, 0],
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
      label: '检视 Nikon Z 8 相机',
      english: 'Examine the Nikon Z 8',
      size: 0.17,
      pose: [0.43, 0.35, -0.012],
      caption: {
        en: 'Nikon Z 8 · NIKKOR Z 24–70mm f/2.8 S II',
        zh: 'Nikon Z 8 · 尼克尔 Z 24–70mm f/2.8 S II',
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
      label: '走近照片墙',
      english: 'Look closer at the photograph wall',
    },
    ...atlasFrame.pins.map<Target>(({ pin, place }) => ({
      id: 'map-pin-' + place.id,
      type: 'map-pin',
      object: pin,
      label: place.zh,
      english: place.en,
    })),
    {
      id: 'keyboard',
      type: 'inspect',
      object: keys,
      onInspect: selectKeySwitches,
      label: '检视机械键盘',
      english: 'Inspect the mechanical keyboard',
      size: 0.335,
      viewDistance: 0.72,
      pose: [1.45, -0.035, 0],
    },
    {
      id: 'mouse',
      type: 'inspect',
      object: pointer,
      label: '检视无线鼠标',
      english: 'Inspect the wireless mouse',
      size: 0.132,
      pose: [1.4, -0.06, 0],
    },
    {
      id: 'filament-printer',
      type: 'case',
      object: printer.unit,
      english: 'Watch the H3C print DeepSeek Whale Girl',
      label: '观看拓竹 H3C 打印 DeepSeek 鲸鱼娘',
      orbit: {
        center: [0, 0.283, 0.004],
        azimuth: [1.16, 0.82, 2.57],
        elevation: [0.16, -0.08, 0.88],
        distance: [0.62, 0.39, 1.78],
        closeFov: 29,
      },
    },
    ...Object.entries(musicSpeakers).map(([id, object]): Target => ({
      id,
      object,
      type: 'computer',
      label: '打开音乐',
      english: 'Open Music',
      app: 'music',
    })),
    {
      id: 'pencil',
      type: 'inspect',
      object: pencil,
      label: '检视 Mitsubishi 9850 HB',
      english: 'Inspect the Mitsubishi 9850 pencil',
      size: 0.18,
      viewDistance: 0.2,
      pose: [1.25, 0, -0.06],
    },
    {
      id: 'drive',
      type: 'inspect',
      object: drive,
      label: '检视 Samsung T7 移动硬盘',
      english: 'Inspect the Samsung T7 portable drive',
      size: 0.085,
      pose: [1.2, 0.18, 0],
    },
    {
      id: 'workbench',
      type: 'workbench',
      object: bench.unit,
      label: '转到工作台前',
      english: 'Move to the workbench',
    },
    ...bench.cabinet.doors.map((object, index): Target => ({
      id: 'workshop-door-' + index,
      type: 'cabinet',
      object,
      index,
      label: '推拉柜门',
      english: 'Slide cabinet door',
    })),
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
      id: 'tool-board-lamp',
      type: 'tool-board-lamp',
      object: bench.boardLight.unit,
      label: '开关工具墙灯',
      english: 'Toggle tool board light',
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
      size: 0.079,
      pose: [1.24, Math.PI / 2, 0],
      caption: { en: 'Twelve-switch sampler', zh: '十二位轴体试样' },
    },
    {
      id: 'multimeter',
      type: 'inspect',
      object: bench.meter,
      label: '检视 Fluke 115 万用表',
      english: 'Examine the Fluke 115 multimeter',
      size: 0.167,
      viewDistance: 0.34,
      pose: [0.08, 0, 0],
    },
    {
      id: 'pliers',
      type: 'inspect',
      object: bench.pliers,
      label: '检视斜口钳',
      english: 'Examine the diagonal cutters',
      size: 0.125,
      pose: [0.08, Math.PI / 2, -0.06],
    },
    {
      id: 'printer-proof',
      type: 'inspect',
      object: samplePrint,
      label: '检视照片试印',
      english: 'Examine the proof print',
      size: 0.177,
      caption: { en: 'Print proof · Belém Tower', zh: '贝伦塔 · 照片试印' },
    },
    ...prints.map<Target>((item) => ({
      id: item.id,
      type: 'inspect',
      object: item.object,
      size: item.size,
      english: item.en,
      label: item.zh,
    })),
    ...drawers.map<Target>((object, index) => ({
      id: 'drawer-' + index,
      type: 'drawer',
      prepare: index === 3 ? prepareDrawerMedia : undefined,
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
    ...booksInRoom.map<Target>((object, index) => {
      const edition = publishedEditions[index];
      const provenance = edition.author + ' · ' + edition.imprint + ' · ' + edition.year;
      return {
        id: 'book-' + index,
        type: 'inspect',
        object,
        size: edition.size[1] * 1.22,
        label: '翻看《' + edition.zh + '》',
        english: edition.en,
        prepare: () => prepareBook(edition.key),
        caption: {
          en: edition.en + ' · ' + provenance,
          zh: '《' + edition.zh + '》 · ' + provenance,
        },
        pose: [0.035, -0.12, -0.025],
      };
    }),
    ...awards.map<Target>(({ object, en, zh }, index) => ({
      id: 'award-' + index,
      type: 'inspect',
      object,
      size: 0.19,
      label: zh,
      english: en,
      pose: [0.08, -0.1, 0],
    })),
    {
      id: 'archive-openSource-1',
      type: 'inspect',
      object: notes,
      size: 0.14,
      label: 'Felix 的手记',
      english: 'Felix’s notebook',
      link: { url: publicProfiles.x, region: notebookSignature },
    },
  ];
  const byObject = new Map(targets.map((target) => [target.object, target]));
  yield;
  performance.mark('studio-batch-start');
  batchMeshes(interior, new Set([...byObject.keys(), bench.top]), mergeFirst);
  performance.mark('studio-batch-end');
  yield;
  const hemisphere = new T.HemisphereLight('#dce7f0', '#a89883', 0.18);
  const { wall, z0, z1, y0, y1 } = windowOpening;
  const aperture = new T.RectAreaLight('#c6dfef', 2, z1 - z0 - 0.074, y1 - y0 - 0.073);
  aperture.name = 'Sky through the west window';
  aperture.position.set(wall - 0.13, (y0 + y1) / 2, (z0 + z1) / 2);
  aperture.rotation.y = -Math.PI / 2;
  const windowLight = new T.DirectionalLight('#6eabff', 1.25);
  windowLight.position.set(-3.4, 2.93, 1.86);
  windowLight.target.position.set(0.4, 1.08, -0.33);
  windowLight.castShadow = true;
  windowLight.updateMatrixWorld();
  windowLight.target.updateMatrixWorld();
  windowLight.shadow.updateMatrices(windowLight);
  const shadowView = windowLight.shadow.camera.matrixWorldInverse;
  const lightBounds = new T.Box3();
  const corner = new T.Vector3();
  for (const x of [roomSize.west - 0.25, roomSize.east + 0.2])
    for (const y of [-0.15, roomSize.ceiling + 0.2])
      for (const z of [roomSize.north - 0.2, roomSize.south + 0.2])
        lightBounds.expandByPoint(corner.set(x, y, z).applyMatrix4(shadowView));
  Object.assign(windowLight.shadow.camera, {
    left: lightBounds.min.x - 0.04,
    right: lightBounds.max.x + 0.04,
    top: lightBounds.max.y + 0.04,
    bottom: lightBounds.min.y - 0.04,
    near: Math.max(0.1, -lightBounds.max.z - 0.04),
    far: -lightBounds.min.z + 0.04,
  });
  windowLight.shadow.camera.updateProjectionMatrix();
  windowLight.shadow.mapSize.set(2048, 2048);
  windowLight.shadow.normalBias = 0.0025;
  windowLight.shadow.radius = 1.8;

  const warm = new T.SpotLight('#ffbe83', 8, 3.2, 0.87, 0.86, 2);
  const deskShade = task.bulb;
  warm.position.copy(deskShade.localToWorld(new T.Vector3(0, -0.002, 0)));
  warm.target.position.copy(deskShade.localToWorld(new T.Vector3(0, -0.66, 0)));
  warm.castShadow = true;
  warm.shadow.mapSize.set(1024, 1024);
  warm.shadow.normalBias = 0.003;
  warm.shadow.radius = 5.5;
  warm.shadow.camera.near = 0.03;
  const slats = new T.Vector2(0.0038, 0);
  const upper = new T.SpotLight('#ffdfb4', 4, 5.2, 1.27, 0.85, 2);
  ceiling.outlet.getWorldPosition(upper.position);
  upper.target.position.copy(upper.position);
  upper.target.position.y -= 1;
  upper.castShadow = true;
  upper.shadow.mapSize.set(1024, 1024);
  upper.shadow.normalBias = 0.003;
  upper.shadow.radius = 5.5;
  upper.shadow.intensity = 0.48;
  const screenFill = new T.RectAreaLight('#c3d9ef', 1.75, display.width, display.height);
  screenFill.position.set(display.x, display.y, display.z + 0.016);
  screenFill.rotation.y = Math.PI;
  root.add(
    hemisphere,
    windowLight,
    windowLight.target,
    aperture,
    warm,
    warm.target,
    upper,
    upper.target,
    screenFill,
  );
  const benchLight = new T.SpotLight('#ffe9cd', 2.7, 1.85, 1.13, 0.76, 2);
  benchLight.castShadow = true;
  benchLight.shadow.mapSize.set(512, 512);
  benchLight.shadow.camera.near = 0.045;
  benchLight.shadow.camera.far = 1.85;
  benchLight.shadow.bias = -0.00016;
  benchLight.shadow.normalBias = 0.0008;
  benchLight.shadow.intensity = 0.62;
  const benchShade = bench.taskLamp.bulb;
  benchLight.position.copy(benchShade.localToWorld(new T.Vector3(0, -0.002, 0)));
  benchLight.target.position.copy(benchShade.localToWorld(new T.Vector3(0, -0.66, 0)));
  const inspectionFill = new T.PointLight('#f0e6d6', 0, 0.9, 2);
  root.add(benchLight, benchLight.target, inspectionFill);

  let activeDrawer = -1;
  let destination = -1;
  let extension = 0;
  let pressed = -1;
  let pressTime = 0;
  const openLength = 0.39;
  const closedPositions = drawers.map((tray) => tray.position.z);
  function slideDrawer(index: number, distance: number, updateWorld = false) {
    drawers[index].position.z = closedPositions[index] + distance;
    drawerInteriors[index].visible = distance > 0;
    if (updateWorld) drawers[index].updateWorldMatrix(true, true);
  }
  const buttonY = control.buttons.map((button) => button.position.y);
  const night = new T.Color('#88b7e9'),
    cloudy = new T.Color('#d5e4eb'),
    sun = new T.Color('#ffeed3');
  let printLocale: Locale = 'en';
  return {
    root,
    interior,
    slats,
    gearWall: fieldGear.zone,
    pickRoots: [interior, window.unit],
    mountedDetails,
    prepareDrawerMedia,
    prepareBookBacks,
    prepareBookExport,
    prepareWorkshop: async () => {
      await Promise.all([bench.prepareTools(), prepareRocket()]);
    },
    setBlinds: window.setBlinds,
    prepareWaterMotion: window.prepareWaterMotion,
    workbench: {
      roots: [bench.boardLight.unit, bench.tray, samplePrint, printer.unit, rocket],
      ready: rear.ready,
    },
    rearReady: rear.ready,
    prepareRear: rear.prepare,
    targets,
    byObject,
    inspectionFill,
    lightLevels: () => ({
      keyboard: keyLight[0].emissiveIntensity,
      lamp: warm.intensity,
      ceilingLamp: upper.intensity,
      screenBar: screenBar.deskWash.intensity,
      wallLamp: fieldGear.track.spots[0].intensity,
      caseLighting: aura[0].emissiveIntensity,
      pictureLamp: architectureParts.pictureLight.lamp.intensity,
      displayCabinet: vitrine.lightPower.value,
      toolBoardLamp: bench.boardLight.wash.intensity,
      benchLamp: benchLight.intensity,
      floorLamp: floorLamp.light.intensity,
      mouse: mouseLight.emissiveIntensity,
      speaker: speakerMeter.reduce((sum, light) => sum + light.emissiveIntensity, 0),
    }),
    canReach(target: Target, mode: Mode, hardwareId: string) {
      if (opensStudioView(target)) {
        if (target.type === 'case') return mode !== 'case' || hardwareId !== target.id;
        if (target.type === 'workbench') return mode !== 'bench';
        return target.type === 'drawer' || target.type !== mode;
      }
      if (mode === 'computer') return target.type === 'screen-bar';
      if (mode === 'case' || mode === 'inspect') return false;
      if (mode === 'remote') return target.type === 'key';
      if (mode === 'window') return target.type === 'remote';
      if (mode === 'map') return target.type === 'map-pin';
      if (mode === 'bookshelf')
        return target.type === 'inspect' && target.object.parent === bookcase;
      if (mode === 'board')
        return (
          target.type === 'picture-lamp' ||
          (target.type === 'inspect' && target.object.parent === board)
        );
      if (mode === 'gear')
        return (
          target.type === 'equipment-track' ||
          target.type === 'floor-lamp' ||
          (target.type === 'inspect' && target.object.parent === fieldGear.zone)
        );
      if (mode === 'drawer') {
        return (
          (target.id === 'drive' || target.id === 'camera-card') &&
          activeDrawer === 3 &&
          extension >= openLength * 0.88
        );
      }
      if (target.type === 'key' || target.type === 'map-pin') return false;
      if (
        target.type === 'bench-lamp' ||
        target.type === 'tool-board-lamp' ||
        target.id === 'switch-sampler' ||
        target.id === 'multimeter' ||
        target.id === 'pliers' ||
        target.id === 'printer-proof'
      )
        return mode === 'bench';
      return target.id !== 'drive' && target.id !== 'camera-card';
    },
    setDrawer(index: number, reducedMotion: boolean) {
      destination = index;
      if (!reducedMotion) return;
      if (activeDrawer >= 0 && activeDrawer !== index) slideDrawer(activeDrawer, 0, true);
      activeDrawer = index;
      extension = index >= 0 ? openLength : 0;
      if (index >= 0) slideDrawer(index, extension, true);
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
    slideCabinet: bench.cabinet.toggle,
    update(
      env: Environment,
      delta: number,
      clock: number,
      audio: { bass: number; mid: number; beat: number },
      inspectedHardware?: string,
      musicPlaying = false,
      atWorkbench = false,
      camera?: T.PerspectiveCamera,
      fullInspection = false,
    ) {
      selectTowerDetail(inspectedHardware === 'case');
      fieldGear.updateLanternPort();
      fieldGear.bottleClosure.update();
      selectMacDetail(
        inspectedHardware === 'mac-studio' && (env.quality === 'high' || fullInspection),
      );
      printer.update(delta, env.reducedMotion, env.locale, camera);
      if (env.locale !== printLocale) {
        printLocale = env.locale;
        setBoardLocale(printLocale);
        proof.setLocale(printLocale);
      }
      const { blocked, moving: blindsMoving, pitch, angle } = window.update(env, delta);
      slats.set(pitch, angle);
      const doorMoving = architectureParts.update(delta, clock, env.reducedMotion);
      const cabinetMoving = bench.cabinet.update(delta, env.reducedMotion);
      const ease = env.reducedMotion ? 1 : 1 - Math.exp(-delta * 5);
      const dim = (current: number, goal: number) =>
        Math.abs(current - goal) < 0.0001 ? goal : T.MathUtils.lerp(current, goal, ease);
      updateSteam(env.reducedMotion ? 1 : clock);
      updateDisplay(env.locale, env.reducedMotion ? 0 : clock);
      updateTelemetry(clock);
      updatePhone(env.locale);
      const phase = env.reducedMotion ? 0 : Math.sin(clock * 0.16) * 0.036;
      for (const [i, source] of aura.entries()) {
        source.emissive.setHSL(channelHues[i] + phase, 0.92, 0.64, T.SRGBColorSpace);
        source.color.set(env.aura ? '#aaa6ac' : '#d0cfd2');
        source.emissiveIntensity = env.aura ? 2.8 : 0;
      }
      for (const blades of fanGuides) {
        blades.color.set(env.aura ? '#929aa6' : '#c5c9cf');
        blades.emissiveIntensity = env.aura ? 2.4 : 0;
      }
      reflections.strength.value = env.aura && env.quality === 'high' ? 1 : 0;
      updateLightGuide(env.aura, env.quality === 'high');
      setComponentLights(env.aura, delta, clock, env);
      const musicBeat = env.reducedMotion ? 0 : audio.beat;
      const musicLevel = env.reducedMotion ? 0 : audio.bass * 0.65 + audio.mid * 0.35;
      const peripheralTime = env.reducedMotion ? 0 : clock / 4.8;
      for (const [i, light] of keyLight.entries()) {
        const wave = peripheralTime - i / keyLight.length;
        const crest = env.reducedMotion ? 0.55 : 0.5 + 0.5 * Math.cos(2 * Math.PI * wave);
        light.emissive.setHSL(0.57 + wave, 0.84, 0.58, T.SRGBColorSpace);
        light.color.copy(light.emissive).multiplyScalar(env.aura ? 0.2 : 0.025);
        light.emissiveIntensity = dim(
          light.emissiveIntensity,
          env.aura ? 0.32 + crest * crest * 2.1 + musicLevel * 0.32 + musicBeat * 0.18 : 0,
        );
        if (env.aura) keyLegends[i].color.copy(light.emissive).multiplyScalar(0.35);
        else keyLegends[i].color.set('#c7c7c3');
        keyLegends[i].emissive.copy(light.emissive);
        keyLegends[i].emissiveIntensity = light.emissiveIntensity * 0.84;
      }
      keyBadge.emissiveIntensity = dim(keyBadge.emissiveIntensity, env.aura ? 0.78 : 0);
      const mousePulse = env.reducedMotion
        ? 0.55
        : 0.5 + 0.5 * Math.cos(2 * Math.PI * peripheralTime);
      mouseLight.emissive.setHSL(0.57 + peripheralTime, 0.83, 0.59, T.SRGBColorSpace);
      mouseLight.color.copy(mouseLight.emissive).multiplyScalar(env.aura ? 0.2 : 0.025);
      mouseLight.emissiveIntensity = dim(
        mouseLight.emissiveIntensity,
        env.aura ? 0.66 + 1.58 * mousePulse + musicLevel * 0.28 : 0,
      );
      mouseBadge.emissive.copy(mouseLight.emissive);
      mouseBadge.color.copy(mouseLight.color);
      mouseBadge.emissiveIntensity = mouseLight.emissiveIntensity * 0.9;
      for (const [i, light] of speakerMeter.entries()) {
        const gain = musicPlaying
          ? T.MathUtils.clamp(musicLevel * 10.5 + musicBeat * 2.8 - i, 0, 1)
          : 0;
        light.emissiveIntensity = dim(light.emissiveIntensity, env.aura ? 0.1 + gain * 2.45 : 0);
      }
      windowLight.intensity = dim(
        windowLight.intensity,
        !env.night && env.weather === '晴' ? 6.1 : 0,
      );
      windowLight.color.lerp(env.night ? night : env.weather === '晴' ? sun : cloudy, ease);
      windowLight.shadow.intensity = 1;
      aperture.color.lerp(env.night ? night : cloudy, ease);
      aperture.intensity = dim(
        aperture.intensity,
        (env.night ? 0.95 : env.weather === '晴' ? 8.5 : env.weather === '雨' ? 5.2 : 7.1) *
          (1 - blocked * 0.9),
      );
      hemisphere.intensity = dim(
        hemisphere.intensity,
        env.night ? 0.035 : 0.18 * (1 - blocked * 0.7),
      );
      warm.intensity = dim(warm.intensity, env.lamp ? 7.1 : 0);
      task.emitter.emissiveIntensity = dim(task.emitter.emissiveIntensity, env.lamp ? 3.2 : 0.03);
      benchLight.intensity = dim(benchLight.intensity, env.benchLamp ? 3.55 : 0);
      bench.taskLamp.emitter.emissiveIntensity = dim(
        bench.taskLamp.emitter.emissiveIntensity,
        env.benchLamp ? 2.8 : 0.02,
      );
      const practicals = ceilingLightLevel(env);
      const floorLevel = (env.floorLamp ?? env.night) ? 0.65 : 0;
      floorLamp.select(env.night, env.quality === 'high');
      fieldGear.selectLighting(env.night, env.quality === 'high', env.wallLamp ?? env.night);
      floorLamp.light.intensity = dim(floorLamp.light.intensity, floorLevel * 5.85);
      floorLamp.opal.emissiveIntensity = dim(floorLamp.opal.emissiveIntensity, floorLevel * 6.2);
      floorLamp.lining.emissiveIntensity = dim(
        floorLamp.lining.emissiveIntensity,
        floorLevel * 0.45,
      );
      const usePanelLights = env.quality === 'high';
      screenBar.setPower(env.screenBar, usePanelLights);
      bench.boardLight.setPower(env.toolBoardLamp, usePanelLights, atWorkbench);
      const pictureLevel = (env.pictureLamp ?? env.night) ? 0.65 : 0;
      shelfAccent.visible = usePanelLights;
      screenFill.visible = usePanelLights;
      upper.intensity = dim(upper.intensity, practicals * (usePanelLights ? 3.1 : 4.4));
      architectureParts.pictureLight.lamp.intensity = dim(
        architectureParts.pictureLight.lamp.intensity,
        pictureLevel * 58,
      );
      architectureParts.pictureLight.diffuser.emissiveIntensity = dim(
        architectureParts.pictureLight.diffuser.emissiveIntensity,
        pictureLevel * 2.4,
      );
      shelfLamps.emissiveIntensity = dim(shelfLamps.emissiveIntensity, practicals * 2.5);
      shelfAccent.intensity = dim(shelfAccent.intensity, practicals * 49);
      ceiling.opal.emissiveIntensity = dim(ceiling.opal.emissiveIntensity, practicals * 2.4);
      ceiling.halo.emissiveIntensity = dim(ceiling.halo.emissiveIntensity, practicals * 1.6);
      ceiling.reflector.emissiveIntensity = dim(
        ceiling.reflector.emissiveIntensity,
        practicals * 0.28,
      );
      ceiling.shell.emissiveIntensity = dim(ceiling.shell.emissiveIntensity, practicals * 0.17);
      ceiling.cove.intensity = dim(ceiling.cove.intensity, practicals * 0.118);
      if (!env.reducedMotion)
        fans.forEach((fan, i) => {
          fan.rotation.z += delta * (10 + (i % 3) * 3.5);
        });
      pressTime = Math.max(0, pressTime - delta);
      for (const [i, key] of control.buttons.entries())
        key.position.y =
          buttonY[i] - (i === pressed ? Math.sin((pressTime / 0.16) * Math.PI) * 0.00135 : 0);
      const previousExtension = extension;
      if (activeDrawer < 0) activeDrawer = destination;
      if (activeDrawer >= 0) {
        const open = activeDrawer === destination;
        const next = open ? openLength : 0;
        extension = env.reducedMotion
          ? next
          : T.MathUtils.lerp(extension, next, 1 - Math.exp(-delta * 14));
        if (Math.abs(extension - next) < 0.001) extension = next;
        slideDrawer(activeDrawer, extension);
        if (!open && extension === 0) activeDrawer = -1;
      }
      return previousExtension !== extension || blindsMoving || doorMoving || cabinetMoving;
    },
  };
}
export function buildStudio(...args: Parameters<typeof buildStudioSteps>) {
  const steps = buildStudioSteps(...args);
  let step = steps.next();
  while (!step.done) step = steps.next();
  return step.value;
}

export type StudioModel = ReturnType<typeof buildStudio>;
