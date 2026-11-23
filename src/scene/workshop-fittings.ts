import * as T from 'three';
const front = 'pocket-front';
const lip = 'pocket-lip';
const lining = 'pocket-back';
import { blenderMesh } from './blender-mesh';
import { loadParts } from './blender-library';
import { box, canvasTexture, group, mesh, print, random, surface } from './geometry';
import type { Palette } from './materials';

function cabinetContents(storage: T.Group, p: Palette) {
  const inside = group(storage, 'Workshop cabinet shelves and parts boxes');
  for (const y of [0.473, 0.818, 1.113, 1.47, 1.816, 2.115])
    box(inside, [0.564, 0.015, 0.286], [0, y, -0.019], p.wood, 0.001);
  const board = surface('#898979', 0.91),
    kraft = surface('#ad9578', 0.91);
  const labels = ['Connectors', 'Fasteners', 'Film stock', 'Offcuts'];
  for (const [i, y] of [0.473, 0.818, 1.47, 1.816].entries()) {
    for (const side of [-1, 1]) {
      const c = group(inside, 'Lidded parts box', [side * 0.166, y + 0.0075, -0.022]);
      const finish = i % 2 ? board : kraft;
      box(c, [0.196, 0.124, 0.249], [0, 0.062, 0], finish, 0.002);
      box(c, [0.2, 0.021, 0.252], [0, 0.127, 0], finish, 0.0013);
      box(c, [0.085, 0.024, 0.0018], [0, 0.073, 0.125], p.bronze, 0.0007);
      const ticket = canvasTexture(256, 64, (ctx) => {
        ctx.fillStyle = '#dbd6c5';
        ctx.fillRect(0, 0, 256, 64);
        ctx.fillStyle = '#453f39';
        ctx.font = '27px Georgia';
        ctx.textAlign = 'center';
        ctx.fillText(labels[i], 128, 42);
      });
      print(c, 0.077, 0.017, [0, 0.073, 0.126], ticket).castShadow = false;
    }
  }
  inside.visible = false;
  return inside;
}

export function bypassDoors(storage: T.Group, p: Palette) {
  const inside = cabinetContents(storage, p);
  const paint = surface('#e4e1d6', 0.63);
  paint.normalMap = p.black.normalMap;
  paint.normalScale.set(0.17, 0.17);
  const bronze = surface('#97836b', 0.37, 0.73);
  const shadow = surface('#504942', 0.56, 0.33);
  const door = blenderMesh(front),
    pull = blenderMesh(lip),
    back = blenderMesh(lining);
  const lower = blenderMesh('pocket-floor-track'),
    upper = blenderMesh('pocket-head-track'),
    carriers = blenderMesh('pocket-carriers'),
    tyres = blenderMesh('pocket-tyres'),
    axles = blenderMesh('pocket-fasteners');
  const nylon = surface('#c4c4b7', 0.58),
    acetal = surface('#e6e5d7', 0.32);
  const tracks = [0.1408, 0.162];
  for (const z of tracks) {
    mesh(storage, lower, p.steel, [0, 0.094, z]).name = 'TT41621 lower rail';
    mesh(storage, upper, p.steel, [0, 2.389, z]).name = 'TT41921 head guide';
  }
  const positions = [-0.1335, 0.1335];
  const rollers: T.Group[][] = [];
  const doors = positions.map((x, i) => {
    const leaf = group(storage, 'Flush sliding cabinet door ' + (i + 1), [x, 1.243, tracks[i]]);
    const panel = group(leaf, 'Panel and routed finger pull');
    panel.scale.x = i ? -1 : 1;
    mesh(panel, door, paint);
    mesh(panel, pull, bronze);
    mesh(panel, back, shadow);
    mesh(panel, carriers, nylon).name = 'Cowdroy TT40000 carriers';
    rollers.push(
      [-0.094, 0.094].map((x) => {
        const pivot = group(leaf, 'TT40000 sheave axle', [x, -1.1342, 0]);
        const wheel = mesh(pivot, tyres, acetal);
        wheel.name = 'Cowdroy TT40000 acetal wheel';
        wheel.userData.cabinetPart = 'pocket-tyres';
        return pivot;
      }),
    );
    mesh(panel, axles, p.steel).name = 'Cowdroy pins and fixings';
    for (const edge of [-1, 1]) {
      box(panel, [0.0026, 2.271, 0.016], [edge * 0.1473, -0.0045, 0], p.woodVertical, 0.0004);
      for (const face of [-1, 1])
        box(
          panel,
          [0.0026, 0.009, 0.0055],
          [edge * 0.1473, 1.1355, face * 0.00525],
          p.woodVertical,
        );
    }
    return leaf;
  });
  let selected = -1;
  return {
    doors,
    toggle(index: number) {
      selected = selected === index ? -1 : index;
    },
    update(delta: number, immediate: boolean) {
      let moving = false;
      doors.forEach((leaf, i) => {
        const goal = positions[i] + (selected === i ? (i ? -0.218 : 0.218) : 0);
        const next = T.MathUtils.damp(leaf.position.x, goal, 9, delta);
        const x = immediate || Math.abs(goal - next) < 0.0002 ? goal : next;
        if (x !== leaf.position.x) {
          moving = true;
          leaf.position.x = x;
          for (const roller of rollers[i]) roller.rotation.z = (positions[i] - x) / 0.0068;
        }
      });
      inside.visible = doors.some((leaf, i) => Math.abs(leaf.position.x - positions[i]) > 0.001);
      return moving;
    },
  };
}

export function perforatedToolWall(unit: T.Group, p: Palette, ...assets: (() => Promise<void>)[]) {
  const frame = group(unit, 'Oak edged workshop pegboard', [0.2794, 1.26, -0.012]);
  const carrier = surface('#4c483e', 0.9);
  box(frame, [0.006, 0.546, 1.232], [0.027, 0, 0], carrier);
  for (const side of [-1, 1]) {
    box(frame, [0.028, 0.0105, 1.257], [0.012, side * 0.278, 0], p.wood, 0.0014);
    box(frame, [0.028, 0.546, 0.0105], [0.012, 0, side * 0.621], p.woodVertical, 0.0014);
  }
  const pitch = 0.0254,
    width = 1.2319,
    height = 0.5461;
  const printWidth = 2048,
    printHeight = Math.round((printWidth * height) / width);
  const paper = canvasTexture(printWidth, printHeight, (ctx) => {
    ctx.fillStyle = '#a89c87';
    ctx.fillRect(0, 0, printWidth, printHeight);
    const rng = random(7149);
    for (let i = 0; i < 31000; i++) {
      ctx.fillStyle = i % 2 ? '#564e3d23' : '#f5e8ca36';
      ctx.fillRect(rng() * printWidth, rng() * printHeight, 0.7 + rng() * 2.6, 0.8 + rng());
    }
    for (let x = -23; x <= 23; x++)
      for (let y = -10; y <= 10; y++) {
        const cx = printWidth * (0.5 + (x * pitch) / width),
          cy = printHeight * (0.5 - (y * pitch) / height);
        const r = (printWidth / width) * 0.0031;
        ctx.fillStyle = '#756d5d';
        ctx.beginPath();
        ctx.arc(cx, cy, r + 1, 0, Math.PI * 2);
        ctx.fill();
        ctx.save();
        ctx.globalCompositeOperation = 'destination-out';
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
  });
  const panel = new T.MeshStandardMaterial({
    map: paper,
    alphaTest: 0.5,
    roughness: 0.86,
    normalMap: p.cork.normalMap,
    normalScale: new T.Vector2(0.26, 0.26),
  });
  const face = mesh(frame, new T.PlaneGeometry(width, height), panel);
  face.rotation.y = -Math.PI / 2;
  const inner = mesh(frame, new T.PlaneGeometry(width, height), panel, [0.0045, 0, 0]);
  inner.rotation.y = -Math.PI / 2;
  inner.castShadow = false;
  let ready: Promise<void> | undefined;
  const loads = assets.map((load) => {
    let pending: Promise<void> | undefined;
    return () =>
      (pending ??= load().catch((error: unknown) => {
        pending = undefined;
        throw error;
      }));
  });
  let retryAfter = 0;
  const prepare = () => {
    ready ??= Promise.all([
      import('./workshop-precision'),
      loadParts('workshop'),
      ...loads.map((load) => load()),
    ])
      .then(([{ fitPrecisionTools }]) => {
        fitPrecisionTools(frame, p);
        face.onBeforeRender = T.Object3D.prototype.onBeforeRender;
      })
      .catch((error: unknown) => {
        ready = undefined;
        retryAfter = performance.now() + 30000;
        throw error;
      });
    return ready;
  };
  face.onBeforeRender = () => {
    if (!ready && performance.now() >= retryAfter) void prepare().catch(() => {});
  };
  return prepare;
}
