import * as T from 'three';
import type { DeferRoomAsset } from './rear-loading';
import { loadDisplayModel } from './display-model';
import { box, canvasTexture, group, mesh, surface, tube, type XYZ } from './geometry';
import { display } from './hardware';
import type { Palette } from './materials';

export const chairPosition = { x: display.x, z: 0.96 };

type Projection = (x: number, y: number, rise: number) => XYZ;
type Section = [number, number];

function indexed(vertices: number[], indices: number[], uv?: number[]) {
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.Float32BufferAttribute(vertices, 3));
  if (uv) geometry.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function connectRing(indices: number[], row: number, count: number) {
  for (let i = 0; i < count; i++) {
    const a = row * count + i,
      b = row * count + ((i + 1) % count);
    indices.push(a, b, a + count, b, b + count, a + count);
  }
}

function pellicle(seat: boolean) {
  const texture = canvasTexture(1024, 1024, (ctx) => {
    const zones = seat ? [0.15, 0.4, 0.79, 1] : [0.15, 0.47, 0.85, 1];
    const fill = seat ? [0.78, 0.61, 0.52, 0.72] : [0.74, 0.53, 0.62, 0.75];
    let start = 0;
    zones.forEach((end, zone) => {
      const top = Math.floor(start * 1024),
        bottom = Math.ceil(end * 1024);
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, top, 1024, bottom - top);
      ctx.clip();
      for (let column = 0; column < 208; column++) {
        const x = (column * 1024) / 208;
        const width = 1.54 + fill[zone] * 3.14;
        ctx.fillStyle = column % 2 ? '#282d2d' : '#383e3b';
        ctx.fillRect(x, top, width, bottom - top);
        ctx.fillStyle = '#59605c';
        ctx.fillRect(x + 0.25, top, 0.52, bottom - top);
      }
      for (let row = Math.floor(top / 5.1); row * 5.1 <= bottom; row++) {
        ctx.fillStyle = row % 2 ? '#454b46de' : '#333935ee';
        ctx.fillRect(0, row * 5.1, 1024, 0.82 + fill[zone] * 1.14);
      }
      ctx.restore();
      start = end;
    });
  });
  texture.anisotropy = 8;
  const weave = new T.MeshStandardMaterial({
    map: texture,
    transparent: true,
    alphaTest: 0.08,
    depthWrite: false,
    side: T.DoubleSide,
    roughness: 0.73,
    metalness: 0.03,
  });
  weave.forceSinglePass = true;
  weave.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>',
      `#include <map_fragment>
       float slant = 1.0 - abs(dot(normalize(vNormal), normalize(vViewPosition)));
       diffuseColor.a += (1.0 - diffuseColor.a) * diffuseColor.a * slant * 0.7;`,
    );
  };
  return weave;
}

function suspendedPanel(
  parent: T.Group,
  name: string,
  outline: T.Shape,
  project: Projection,
  frameWidth: (x: number, y: number) => number,
  depth: number,
  frame: T.Material,
  cloth: T.Material,
) {
  const contour = outline.getSpacedPoints(80).slice(0, -1);
  if (T.ShapeUtils.isClockWise(contour)) contour.reverse();
  const edge = contour.map((point, i) => {
    const next = contour[(i + 1) % contour.length],
      prev = contour[(i + contour.length - 1) % contour.length];
    const inward = new T.Vector2(prev.y - next.y, next.x - prev.x).normalize();
    return { point, inward, width: frameWidth(point.x, point.y) };
  });
  const frameVertices: number[] = [],
    frameFaces: number[] = [];
  const membraneVertices: number[] = [],
    membraneFaces: number[] = [],
    uv: number[] = [];
  const count = edge.length;
  for (let j = 0; j <= 12; j++) {
    const angle = (2 * Math.PI * j) / 12;
    for (const { point, inward, width } of edge) {
      const inset = width * (0.5 - 0.5 * Math.cos(angle));
      const lift = (Math.sign(Math.sin(angle)) * Math.abs(Math.sin(angle)) ** 0.72 * depth) / 2;
      frameVertices.push(...project(point.x + inward.x * inset, point.y + inward.y * inset, lift));
    }
    if (j) connectRing(frameFaces, j - 1, count);
  }
  mesh(parent, indexed(frameVertices, frameFaces), frame).name = name + ' perimeter carrier';
  const bounds = new T.Box2().setFromPoints(contour);
  for (let j = 0; j <= 14; j++) {
    const radius = Math.max(0.00001, j / 14);
    for (const { point, inward, width } of edge) {
      const x = (point.x + inward.x * width * 0.89) * radius;
      const y = (point.y + inward.y * width * 0.89) * radius;
      membraneVertices.push(...project(x, y, 0));
      uv.push(
        (x - bounds.min.x) / (bounds.max.x - bounds.min.x),
        (y - bounds.min.y) / (bounds.max.y - bounds.min.y),
      );
    }
    if (j) connectRing(membraneFaces, j - 1, count);
  }
  const net = mesh(parent, indexed(membraneVertices, membraneFaces, uv), cloth);
  net.name = name + ' tensioned Pellicle';
  net.castShadow = false;
}

function moulding(
  parent: T.Group,
  points: XYZ[],
  sections: Section[],
  up: XYZ,
  material: T.Material,
) {
  const path = new T.CatmullRomCurve3(points.map((p) => new T.Vector3(...p)));
  const vertices: number[] = [],
    faces: number[] = [];
  const count = 10,
    steps = (points.length - 1) * 4;
  for (let row = 0; row <= steps; row++) {
    const t = row / steps,
      part = t * (sections.length - 1),
      i = Math.min(sections.length - 2, Math.floor(part));
    const width = T.MathUtils.lerp(sections[i][0], sections[i + 1][0], part - i);
    const depth = T.MathUtils.lerp(sections[i][1], sections[i + 1][1], part - i);
    const center = path.getPoint(t),
      tangent = path.getTangent(t);
    const side = tangent
      .clone()
      .cross(new T.Vector3(...up))
      .normalize();
    const normal = side.clone().cross(tangent).normalize();
    for (let col = 0; col < count; col++) {
      const angle = (2 * Math.PI * col) / count,
        x = Math.cos(angle),
        y = Math.sin(angle);
      const point = center
        .clone()
        .addScaledVector(side, (Math.sign(x) * Math.abs(x) ** 0.74 * width) / 2)
        .addScaledVector(normal, (Math.sign(y) * Math.abs(y) ** 0.74 * depth) / 2);
      vertices.push(...point.toArray());
    }
    if (row) connectRing(faces, row - 1, count);
  }
  for (let col = 1; col < count - 1; col++)
    faces.push(0, col + 1, col, steps * count, steps * count + col, steps * count + col + 1);
  for (let i = 0; i < faces.length; i += 3) [faces[i], faces[i + 1]] = [faces[i + 1], faces[i]];
  return mesh(parent, indexed(vertices, faces), material);
}

function seatOutline() {
  const s = new T.Shape();
  s.moveTo(0, -0.2159);
  s.bezierCurveTo(0.118, -0.216, 0.205, -0.224, 0.231, -0.177);
  s.bezierCurveTo(0.264, -0.107, 0.253, 0.025, 0.239, 0.098);
  s.bezierCurveTo(0.228, 0.178, 0.206, 0.21, 0.154, 0.211);
  s.bezierCurveTo(0.07, 0.213, -0.07, 0.213, -0.154, 0.211);
  s.bezierCurveTo(-0.206, 0.21, -0.228, 0.178, -0.239, 0.098);
  s.bezierCurveTo(-0.253, 0.025, -0.264, -0.107, -0.231, -0.177);
  s.bezierCurveTo(-0.205, -0.224, -0.118, -0.216, 0, -0.2159);
  return s;
}

function backOutline() {
  const s = new T.Shape();
  s.moveTo(0, 0.251);
  s.bezierCurveTo(0.087, 0.251, 0.198, 0.238, 0.222, 0.201);
  s.bezierCurveTo(0.249, 0.162, 0.234, 0.119, 0.21, 0.056);
  s.bezierCurveTo(0.184, -0.011, 0.166, -0.065, 0.164, -0.114);
  s.lineTo(0.158, -0.205);
  s.bezierCurveTo(0.156, -0.238, 0.151, -0.247, 0.119, -0.251);
  s.bezierCurveTo(0.056, -0.258, -0.056, -0.258, -0.119, -0.251);
  s.bezierCurveTo(-0.151, -0.247, -0.156, -0.238, -0.158, -0.205);
  s.lineTo(-0.164, -0.114);
  s.bezierCurveTo(-0.166, -0.065, -0.184, -0.011, -0.21, 0.056);
  s.bezierCurveTo(-0.234, 0.119, -0.249, 0.162, -0.222, 0.201);
  s.bezierCurveTo(-0.198, 0.238, -0.087, 0.251, 0, 0.251);
  return s;
}

const seatSurface: Projection = (x, z, rise) => [
  x,
  0.465 +
    0.037 * (x / 0.25) ** 2 -
    0.033 * Math.max(0, (-z - 0.102) / 0.114) ** 2 -
    0.015 * Math.exp(-((z - 0.056) ** 2) / 0.006) +
    rise,
  z,
];

const backSurface: Projection = (x, y, rise) => {
  const t = (y + 0.255) / 0.506;
  return [
    x,
    0.736 + y,
    0.209 +
      0.095 * t * t -
      0.044 * Math.exp(-((t - 0.375) ** 2) / 0.036) -
      0.066 * (x / 0.238) ** 2 +
      rise,
  ];
};

function castBase(chair: T.Group, p: Palette, cast: T.Material, dark: T.Material) {
  tube(chair, [0, 0.07, 0.012], [0, 0.195, 0.012], 0.0257, dark);
  tube(chair, [0, 0.127, 0.012], [0, 0.177, 0.012], 0.038, cast, 0.034);
  tube(chair, [0, 0.175, 0.012], [0, 0.201, 0.012], 0.029, dark);
  tube(chair, [0, 0.2, 0.012], [0, 0.348, 0.012], 0.0167, p.steel);
  const casters: T.Group[] = [];
  for (let i = 0; i < 5; i++) {
    const spoke = group(chair, 'Swept base leg and twin-wheel caster', [0, 0, 0.012]);
    spoke.rotation.y = 0.22 + (2 * Math.PI * i) / 5;
    moulding(
      spoke,
      [
        [0, 0.15, 0.008],
        [0, 0.145, 0.041],
        [0.002, 0.128, 0.111],
        [0.003, 0.095, 0.236],
        [0, 0.085, 0.287],
        [0, 0.081, 0.3],
      ],
      [
        [0.06, 0.032],
        [0.047, 0.041],
        [0.04, 0.038],
        [0.028, 0.025],
        [0.024, 0.024],
        [0.019, 0.02],
      ],
      [0, 1, 0],
      cast,
    );
    const swivel = group(spoke, 'C7 caster socket ' + (i + 1), [0, 0, 0.307]);
    swivel.rotation.y = [0.45, -0.56, 0.12, 0.72, -0.15][i];
    swivel.userData.product = 'aeron-c7';
    swivel.userData.casterNumber = i + 1;
    casters.push(swivel);
  }
  return casters;
}

function sideCasting(
  parent: T.Group,
  shape: T.Shape,
  width: number,
  x: number,
  material: T.Material,
) {
  const geometry = new T.ExtrudeGeometry(shape, {
    depth: width,
    bevelEnabled: true,
    bevelThickness: 0.003,
    bevelSize: 0.003,
    bevelSegments: 2,
    curveSegments: 10,
  });
  const part = mesh(parent, geometry, material, [x + width / 2, 0, 0]);
  part.rotation.y = -Math.PI / 2;
  return part;
}

function tiltMechanism(chair: T.Group, p: Palette, cast: T.Material, dark: T.Material) {
  const mechanism = new T.Shape();
  mechanism.moveTo(-0.111, 0.374);
  mechanism.bezierCurveTo(-0.129, 0.383, -0.124, 0.419, -0.095, 0.424);
  mechanism.bezierCurveTo(-0.027, 0.436, 0.057, 0.426, 0.124, 0.402);
  mechanism.bezierCurveTo(0.158, 0.39, 0.148, 0.352, 0.119, 0.343);
  mechanism.bezierCurveTo(0.06, 0.329, -0.036, 0.333, -0.111, 0.374);
  sideCasting(chair, mechanism, 0.129, 0, dark).name = 'Harmonic 2 tilt housing';
  for (const s of [-1, 1]) {
    moulding(
      chair,
      [
        [s * 0.055, 0.381, 0.109],
        [s * 0.106, 0.389, 0.106],
        [s * 0.166, 0.427, 0.125],
        [s * 0.212, 0.486, 0.114],
      ],
      [
        [0.04, 0.026],
        [0.043, 0.025],
        [0.034, 0.021],
        [0.032, 0.02],
      ],
      [0, 0, 1],
      cast,
    );
    tube(chair, [s * 0.221, 0.483, 0.092], [s * 0.244, 0.483, 0.092], 0.019, cast);
    tube(chair, [s * 0.244, 0.483, 0.092], [s * 0.245, 0.483, 0.092], 0.009, p.black);
    tube(chair, [s * 0.067, 0.362, 0.022], [s * 0.122, 0.362, 0.022], 0.0058, p.steel);
    tube(
      chair,
      [s * 0.107, 0.362, 0.022],
      [s * 0.155, 0.362, 0.022],
      s > 0 ? 0.0145 : 0.0095,
      dark,
    );
  }
  const arm = new T.Shape();
  arm.moveTo(-0.1, 0.407);
  arm.bezierCurveTo(-0.004, 0.367, 0.151, 0.365, 0.214, 0.425);
  arm.bezierCurveTo(0.239, 0.45, 0.237, 0.501, 0.226, 0.533);
  arm.lineTo(0.207, 0.532);
  arm.bezierCurveTo(0.222, 0.423, 0.119, 0.404, 0.045, 0.411);
  arm.lineTo(-0.1, 0.43);
  arm.closePath();
  for (const s of [-1, 1]) sideCasting(chair, arm, 0.022, s * 0.159, cast);
}

function postureFit(chair: T.Group, frame: T.Material, p: Palette) {
  const spine = group(chair, 'Adjustable PostureFit SL');
  for (const [y, w, h] of [
    [0.558, 0.077, 0.102],
    [0.691, 0.087, 0.126],
  ]) {
    const z = backSurface(0, y - 0.736, 0.008)[2];
    const pad = new T.Shape();
    pad.moveTo(-w * 0.29, -h * 0.48);
    pad.bezierCurveTo(-w * 0.55, -h * 0.44, -w * 0.5, h * 0.2, -w * 0.43, h * 0.39);
    pad.bezierCurveTo(-w * 0.36, h * 0.54, w * 0.36, h * 0.54, w * 0.43, h * 0.39);
    pad.bezierCurveTo(w * 0.5, h * 0.2, w * 0.55, -h * 0.44, w * 0.29, -h * 0.48);
    pad.quadraticCurveTo(0, -h * 0.53, -w * 0.29, -h * 0.48);
    const shape = new T.ExtrudeGeometry(pad, {
      depth: 0.009,
      bevelEnabled: true,
      bevelSize: 0.0028,
      bevelThickness: 0.003,
      bevelSegments: 3,
      curveSegments: 12,
    });
    const pos = shape.attributes.position;
    for (let i = 0; i < pos.count; i++)
      pos.setZ(i, pos.getZ(i) + 0.007 * (1 - (pos.getX(i) / (w * 0.52)) ** 2));
    shape.computeVertexNormals();
    mesh(spine, shape, p.rubber, [0, y, z]);
    tube(spine, [0, y, z + 0.011], [0, y, z + 0.034], 0.011, frame);
  }
  const stem: XYZ[] = [
    [0, 0.494, 0.221],
    [0, 0.513, 0.246],
    [0, 0.576, 0.254],
    [0, 0.639, 0.246],
  ];
  moulding(
    spine,
    [
      [0, 0.51, 0.231],
      [0, 0.552, 0.219],
      [0, 0.624, 0.21],
      [0, 0.688, 0.213],
      [0, 0.708, 0.211],
    ],
    [
      [0.015, 0.014],
      [0.014, 0.014],
      [0.014, 0.011],
      [0.023, 0.015],
      [0.017, 0.009],
    ],
    [0, 0, 1],
    p.rubber,
  );
  moulding(
    spine,
    stem,
    [
      [0.037, 0.018],
      [0.037, 0.022],
      [0.032, 0.022],
      [0.037, 0.017],
    ],
    [0, 0, 1],
    frame,
  );
  for (const s of [-1, 1]) {
    const attachment = backSurface(s * 0.211, 0.091, 0.007);
    moulding(
      spine,
      [
        [0, 0.596, 0.251],
        [s * 0.018, 0.635, 0.246],
        [s * 0.091, 0.698, 0.226],
        [s * 0.154, 0.755, 0.218],
        attachment,
      ],
      [
        [0.025, 0.017],
        [0.029, 0.017],
        [0.026, 0.014],
        [0.029, 0.014],
        [0.03, 0.015],
      ],
      [0, 0, 1],
      frame,
    );
    tube(spine, [s * 0.019, 0.546, 0.246], [s * 0.031, 0.546, 0.246], 0.012, p.graphite);
  }
}

function adjustableArms(chair: T.Group, frame: T.Material, p: Palette) {
  const pads = surface('#262a28', 0.57);
  for (const s of [-1, 1]) {
    const arm = group(chair, 'Adjustable arm and rear pivot');
    moulding(
      arm,
      [
        [s * 0.144, 0.472, 0.211],
        [s * 0.159, 0.492, 0.218],
        [s * 0.163, 0.55, 0.217],
        [s * 0.169, 0.642, 0.199],
        [s * 0.174, 0.671, 0.186],
      ],
      [
        [0.032, 0.035],
        [0.037, 0.037],
        [0.035, 0.033],
        [0.033, 0.032],
        [0.027, 0.032],
      ],
      [0, 0, 1],
      frame,
    );
    moulding(
      arm,
      [
        [s * 0.174, 0.538, 0.195],
        [s * 0.231, 0.536, 0.173],
        [s * 0.264, 0.562, 0.143],
        [s * 0.278, 0.618, 0.111],
        [s * 0.281, 0.65, 0.089],
      ],
      [
        [0.05, 0.039],
        [0.052, 0.037],
        [0.044, 0.034],
        [0.035, 0.031],
        [0.046, 0.029],
      ],
      [0, 0, 1],
      frame,
    );
    tube(arm, [s * 0.167, 0.665, 0.189], [s * 0.183, 0.665, 0.189], 0.015, p.graphite);
    tube(arm, [s * 0.183, 0.665, 0.189], [s * 0.184, 0.665, 0.189], 0.006, p.black);
    box(arm, [0.01, 0.045, 0.015], [s * 0.237, 0.544, 0.184], p.graphite, 0.004).rotation.x = 0.18;
    box(arm, [0.05, 0.014, 0.115], [s * 0.281, 0.652, 0.067], p.graphite, 0.006);
    moulding(
      arm,
      [
        [s * 0.271, 0.657, 0.169],
        [s * 0.272, 0.657, 0.165],
        [s * 0.279, 0.664, 0.148],
        [s * 0.286, 0.671, 0.091],
        [s * 0.288, 0.671, 0.018],
        [s * 0.28, 0.664, -0.044],
        [s * 0.274, 0.659, -0.051],
        [s * 0.273, 0.659, -0.055],
      ],
      [
        [0.005, 0.003],
        [0.037, 0.012],
        [0.068, 0.025],
        [0.081, 0.029],
        [0.075, 0.032],
        [0.056, 0.027],
        [0.03, 0.014],
        [0.005, 0.003],
      ],
      [0, 1, 0],
      pads,
    );
  }
}

export function taskChair(
  parent: T.Object3D,
  p: Palette,
  manager: T.LoadingManager,
  deferRoomDetail: DeferRoomAsset,
) {
  const placement = group(parent, 'Desk task chair', [chairPosition.x, 0.0045, chairPosition.z]);
  const chair = group(placement, 'Herman Miller Aeron Remastered · Size B / Graphite');
  const frame = surface('#444746', 0.55, 0.11),
    cast = surface('#404341', 0.5, 0.27),
    dark = surface('#303432', 0.67);
  frame.side = cast.side = dark.side = T.DoubleSide;
  suspendedPanel(
    chair,
    'Size B seat',
    seatOutline(),
    seatSurface,
    (x, z) =>
      0.013 + 0.006 * (Math.abs(x) / 0.25) ** 2 + 0.014 * Math.max(0, (-z - 0.118) / 0.1) ** 2,
    0.031,
    frame,
    pellicle(true),
  );
  suspendedPanel(
    chair,
    'Size B back',
    backOutline(),
    backSurface,
    (x, y) =>
      0.014 +
      0.024 * Math.max(0, (y - 0.159) / 0.093) ** 2 * (1 - 0.78 * Math.min(1, Math.abs(x) / 0.21)) +
      0.007 * Math.max(0, (-y - 0.18) / 0.075),
    0.024,
    frame,
    pellicle(false),
  );
  for (const s of [-1, 1]) {
    for (const [x, y] of [
      [0.215, 0.088],
      [0.148, -0.216],
      [0.169, -0.026],
    ]) {
      const pos = backSurface(s * x, y, 0.0122);
      tube(chair, pos, [pos[0], pos[1], pos[2] + 0.0015], 0.0028, dark);
    }
  }
  postureFit(chair, frame, p);
  adjustableArms(chair, frame, p);
  tiltMechanism(chair, p, cast, dark);
  const [first, ...others] = castBase(chair, p, cast, dark);
  deferRoomDetail(() =>
    loadDisplayModel(first, '/media/models/aeron-c7.glb', manager, {
      mounted(scene) {
        for (const swivel of others) swivel.add(scene.clone(true));
      },
    }),
  );
  const fixed: T.Mesh[] = [];
  chair.traverse((child) => {
    if (child instanceof T.Mesh && child.parent !== chair) fixed.push(child);
  });
  for (const part of fixed) chair.attach(part);
  return placement;
}
