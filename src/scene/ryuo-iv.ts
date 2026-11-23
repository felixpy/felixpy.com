import * as T from 'three';
import { telemetryFont } from './pc-telemetry';
import { pcTelemetryTexture } from './pc-telemetry-texture';
import type { ProductDetail } from './product-detail';
import { box, canvasTexture, group, mesh, surface, tube } from './geometry';
import { shortCoolingLines } from './case-interior-parts';
import type { Palette } from './materials';
import { rogEye } from './rog-mark';
import { blenderMesh } from './blender-mesh';
import { fanPanelGuide } from './case-component-lights';
import railRelief from './ryuo-rail-relief.json';

function amoled() {
  const eye = rogEye('lit');
  const map = canvasTexture(640, 250, (ctx) => {
    ctx.fillStyle = '#040817';
    ctx.fillRect(0, 0, 640, 250);
    const spectrum = ctx.createLinearGradient(22, 134, 590, 76);
    spectrum.addColorStop(0, '#aa5df9');
    spectrum.addColorStop(0.24, '#f775a5');
    spectrum.addColorStop(0.53, '#719dff');
    spectrum.addColorStop(0.78, '#32d4eb');
    spectrum.addColorStop(1, '#52e3cc');
    for (let i = 0; i < 24; i++) {
      const y = 125 + i * 2.2;
      ctx.strokeStyle = spectrum;
      ctx.globalAlpha = 0.08 + 0.21 * Math.pow(Math.sin((i / 23) * Math.PI), 2);
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      ctx.moveTo(-30, y - 60);
      ctx.bezierCurveTo(64, y - 113 + i, 123, 188 - i, 206, 161 + i * 1.8);
      ctx.bezierCurveTo(308, 170 + i * 0.8, 355, 6 + i * 4, 489, 17 + i);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    ctx.save();
    ctx.drawImage(eye.image, 69, 37, 234, 140);
    ctx.globalCompositeOperation = 'source-atop';
    ctx.globalAlpha = 0.63;
    ctx.fillStyle = spectrum;
    ctx.globalCompositeOperation = 'multiply';
    ctx.fillRect(69, 37, 234, 140);
    ctx.restore();
    ctx.fillStyle = '#bccef0';
    ctx.font = '600 11px Arial';
    ctx.fillText('R E P U B L I C   O F   G A M E R S', 47, 215);
    ctx.font = '600 15px Arial';
    ctx.fillStyle = '#7ee3eb';
    ctx.fillText('CPU', 437, 91);
    ctx.fillStyle = '#757e96';
    ctx.font = '12px monospace';
    ctx.fillText('RYUO IV', 438, 185);
  });
  eye.dispose();
  const material = new T.MeshPhysicalMaterial({
    color: '#23334a',
    map,
    emissiveMap: map,
    emissive: '#ffffff',
    emissiveIntensity: 1.6,
    roughness: 0.22,
    clearcoat: 0.52,
    clearcoatRoughness: 0.2,
  });
  const ctx = map.image.getContext('2d')!;
  const background = ctx.getImageData(430, 100, 155, 68);
  const updateTexture = pcTelemetryTexture(map, ctx);
  return {
    material,
    showTemperature(celsius: number, useTyped = false) {
      ctx.putImageData(background, 430, 100);
      ctx.fillStyle = '#eff3ff';
      ctx.font = telemetryFont(67);
      ctx.fillText(celsius + '°', 433, 158);
      material.map = material.emissiveMap = updateTexture(useTyped);
    },
  };
}

function wrapDisplay(height: number, offset: number, inset: number) {
  const radius = 0.029;
  const path = new T.CurvePath<T.Vector2>();
  const left = -0.062 + inset;
  const bend = 0.026;
  path.add(new T.LineCurve(new T.Vector2(left, 0.122), new T.Vector2(bend, 0.122)));
  path.add(new T.EllipseCurve(bend, 0.122 - radius, radius, radius, Math.PI / 2, 0, true, 0));
  path.add(
    new T.LineCurve(
      new T.Vector2(bend + radius, 0.122 - radius),
      new T.Vector2(bend + radius, 0.063 + inset),
    ),
  );
  const g = new T.PlaneGeometry(1, height, 112, 1);
  const { position, uv } = g.attributes;
  for (let i = 0; i < position.count; i++) {
    const u = uv.getX(i);
    const at = path.getPoint(u);
    const tangent = path.getTangent(u);
    position.setXYZ(i, at.x - tangent.y * offset, position.getY(i), at.y + tangent.x * offset);
  }
  g.computeVertexNormals();
  return g;
}

function pumpHead(
  parent: T.Object3D,
  p: Palette,
  enamel: T.Material,
  alloy: T.Material,
  details: ProductDetail,
) {
  const pump = group(
    parent,
    'ROG Ryuo IV · curved 6.67-inch AMOLED and cold plate',
    [0.0695, 0.111, -0.132],
  );
  pump.rotation.y = -Math.PI / 2;
  for (const [finish, metal] of Object.entries({
    copper: surface('#bb784e', 0.33, 0.86),
    steel: p.steel,
    shell: alloy,
  })) {
    const mount = mesh(pump, blenderMesh('ryuo-mount-' + finish), metal);
    mount.name = 'LGA1851 contact and 78 mm mount • ' + finish;
    if (finish === 'copper') details.enclosed(mount);
  }
  box(pump, [0.064, 0.068, 0.045], [0, 0, 0.026], enamel, 0.007);
  box(pump, [0.089, 0.078, 0.039], [-0.003, -0.001, 0.06], alloy, 0.0054);
  for (const [finish, material] of Object.entries({
    white: enamel,
    satin: alloy,
    black: p.rubber,
    graphite: p.graphite,
    steel: p.steel,
  }))
    mesh(pump, blenderMesh('ryuo-housing-' + finish), material);
  box(pump, [0.008, 0.075, 0.065], [-0.059, -0.001, 0.088], enamel, 0.002);
  const sidePrint = canvasTexture(448, 384, (ctx) => {
    ctx.fillStyle = '#dedfe0';
    ctx.fillRect(0, 0, 448, 384);
    for (let y = 3; y < 384; y += 5) {
      ctx.fillStyle = '#d1d3d3';
      ctx.fillRect(0, y, 448, 1);
    }
    ctx.fillStyle = '#8b8f92';
    for (const y of [35, 321])
      for (let i = 0; i < 24; i++) {
        const x = 25 + i * 16;
        ctx.beginPath();
        ctx.moveTo(x, y + 17);
        ctx.lineTo(x + 12, y);
        ctx.lineTo(x + 20, y);
        ctx.lineTo(x + 8, y + 17);
        ctx.closePath();
        ctx.fill();
      }
    ctx.textAlign = 'center';
    ctx.font = 'italic 900 109px Arial';
    ctx.fillText('R O G', 224, 209);
    ctx.font = 'bold 15px Arial';
    ctx.fillText('FOR THOSE WHO DARE', 224, 254);
  });
  const sideStamp = mesh(
    pump,
    new T.PlaneGeometry(0.057, 0.067),
    new T.MeshStandardMaterial({ map: sidePrint, roughness: 0.45, metalness: 0.35 }),
    [-0.06315, -0.001, 0.088],
  );
  sideStamp.rotation.y = -Math.PI / 2;
  sideStamp.castShadow = false;
  const lid = new T.Shape();
  lid.moveTo(-0.066, 0.06);
  lid.quadraticCurveTo(-0.066, 0.053, -0.059, 0.053);
  lid.lineTo(0.049, 0.053);
  lid.quadraticCurveTo(0.057, 0.053, 0.057, 0.064);
  lid.lineTo(0.057, 0.093);
  lid.quadraticCurveTo(0.057, 0.124, 0.026, 0.124);
  lid.lineTo(-0.062, 0.124);
  lid.quadraticCurveTo(-0.066, 0.123, -0.066, 0.117);
  lid.closePath();
  for (const y of [-0.038, 0.0416]) {
    const cap = mesh(
      pump,
      new T.ExtrudeGeometry(lid, {
        depth: 0.0028,
        bevelEnabled: true,
        bevelSize: 0.0008,
        bevelThickness: 0.00062,
        bevelSegments: 3,
        curveSegments: 30,
      }),
      enamel,
      [0, y, 0],
    );
    cap.rotation.x = Math.PI / 2;
  }
  mesh(pump, wrapDisplay(0.077, 0.0004, 0), p.black);
  const display = amoled();
  mesh(pump, wrapDisplay(0.065, 0.0011, 0.003), display.material).castShadow = false;
  return display.showTemperature;
}

function coolingFans(
  radiator: T.Group,
  enamel: T.Material,
  aura: T.MeshStandardMaterial[],
  registerLight: (part: T.Mesh) => void,
) {
  const parts = [
    'chassis',
    'pads',
    'grey',
    'screws',
    'contacts',
    'vanes',
    'medallion',
    'rotor-foil',
    'stripes',
    'eye',
  ] as const;
  const geometries = new Map(parts.map((part) => [part, blenderMesh('ryuo-mf12c/' + part)]));
  const pad = surface('#f1f1ef', 0.72, 0);
  const print = surface('#85878b', 0.44, 0.22);
  print.side = T.DoubleSide;
  const screw = surface('#45474a', 0.35, 0.74);
  const gold = surface('#cba059', 0.32, 0.78);
  const lid = surface('#ecece9', 0.3, 0.16);
  const foil = surface('#97999d', 0.37, 0.46);
  foil.side = T.DoubleSide;
  const diffuser = new T.MeshStandardMaterial({
    name: fanPanelGuide,
    color: '#b8b7be',
    roughness: 0.42,
    emissive: 0xffffff,
    emissiveIntensity: 1.15,
  });
  const scattering = canvasTexture(64, 32, (ctx) => {
    const glow = ctx.createLinearGradient(0, 0, 64, 22);
    glow.addColorStop(0, '#f6f6f6');
    glow.addColorStop(0.28, '#d3d3d3');
    glow.addColorStop(1, '#383838');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, 64, 32);
  });
  const mount = (parent: T.Group, part: (typeof parts)[number], material: T.Material) => {
    const item = mesh(parent, geometries.get(part)!, material);
    item.name = 'MF-12C ' + part;
    item.userData.mf12cPart = part;
    return item;
  };
  for (let j = 0; j < 3; j++) {
    const fan = group(radiator, 'MF-12C · daisy-chained 120 mm', [
      -0.008,
      -0.017,
      -0.12 + j * 0.12,
    ]);
    fan.rotation.x = Math.PI / 2;
    fan.userData.mf12cStation = j;
    mount(fan, 'chassis', enamel);
    mount(fan, 'pads', pad);
    mount(fan, 'grey', print);
    mount(fan, 'screws', screw);
    mount(fan, 'contacts', gold);
    const light = aura[j + 2];
    const panel = mount(fan, j === 1 ? 'stripes' : 'eye', diffuser);
    panel.castShadow = false;
    registerLight(panel);
    const rotor = group(fan, 'Fan rotor');
    const opal = surface('#d4d9e1', 0.36, 0.055);
    opal.emissive = light.emissive;
    opal.emissiveMap = scattering;
    mount(rotor, 'vanes', opal).onBeforeRender = () => {
      opal.emissiveIntensity = light.emissiveIntensity * 0.71;
    };
    mount(rotor, 'medallion', lid);
    mount(rotor, 'rotor-foil', foil).castShadow = false;
  }
}

function radiatorFinish(radiator: T.Group) {
  const fins = canvasTexture(768, 256, (ctx) => {
    ctx.fillStyle = '#716f76';
    ctx.fillRect(0, 0, 768, 256);
    for (let pass = 0; pass < 12; pass++) {
      const y = pass * 22;
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = '#b7b9bc';
      ctx.beginPath();
      for (let x = 0; x <= 768; x += 6) {
        ctx.moveTo(x, y + 2);
        ctx.lineTo(x + 3, y + 19);
        ctx.lineTo(x + 6, y + 2);
      }
      ctx.stroke();
      ctx.fillStyle = '#ededeb';
      ctx.fillRect(0, y, 768, 2.3);
    }
  });
  const core = mesh(
    radiator,
    new T.PlaneGeometry(0.352, 0.111),
    new T.MeshStandardMaterial({ map: fins, roughness: 0.64, metalness: 0.35 }),
    [-0.008, -0.0168, 0],
  );
  core.rotation.set(Math.PI / 2, 0, Math.PI / 2);
  core.castShadow = false;
  const letters = railRelief.map((outline) => {
    const shape = new T.Shape(
      outline.map(([x, y]) => new T.Vector2((x - 516) / 12000, (135 - y) / 12000)),
    );
    shape.closePath();
    return shape;
  });
  const geometry = new T.ExtrudeGeometry(letters, {
    depth: 0.000035,
    bevelEnabled: true,
    bevelSize: 0.00023,
    bevelThickness: 0.0001,
    bevelSegments: 2,
  });
  const finishes = [new T.Color('#e2e3e5'), new T.Color('#b7bac1')];
  const colors = new Float32Array(3 * geometry.getAttribute('position').count);
  for (const { start, count, materialIndex } of geometry.groups) {
    const color = finishes[materialIndex ?? 0];
    for (let i = start; i < start + count; i++) color.toArray(colors, i * 3);
  }
  geometry.setAttribute('color', new T.BufferAttribute(colors, 3));
  geometry.clearGroups();
  const stamp = new T.MeshStandardMaterial({
    vertexColors: true,
    roughness: 0.41,
    metalness: 0.17,
  });
  for (const side of [-1, 1]) {
    const badge = mesh(radiator, geometry, stamp, [side * 0.07004, 0, 0]);
    badge.name = 'Ryuo radiator rail · embossed ROG wordmark';
    badge.rotation.y = (side * Math.PI) / 2;
    badge.castShadow = false;
  }
}

export function ryuoIV(
  unit: T.Group,
  p: Palette,
  aura: T.MeshStandardMaterial[],
  braid: T.Texture,
  registerLight: (part: T.Mesh) => void,
  details: ProductDetail,
) {
  const enamel = surface('#eaebed', 0.41, 0.17);
  const alloy = surface('#bbc1c8', 0.34, 0.72);
  const cooling = group(unit, 'ROG Ryuo IV SLC 360 ARGB White Edition');
  cooling.position.z = -0.023;
  const showTemperature = pumpHead(cooling, p, enamel, alloy, details);
  const radiator = group(
    cooling,
    'ROG offset-flow 394 × 140 × 32 mm radiator',
    [0.001, 0.253, -0.031],
  );
  for (const [finish, material] of Object.entries({
    white: enamel,
    graphite: p.graphite,
    satin: alloy,
  }))
    mesh(radiator, blenderMesh('ryuo-radiator-' + finish), material);
  radiatorFinish(radiator);
  for (const x of [-0.053, 0.053]) {
    box(radiator, [0.012, 0.009, 0.366], [x, 0.0195, 0.002], p.graphite, 0.0009);
    for (const z of [-0.17, -0.07, 0.07, 0.17])
      tube(radiator, [x, 0.022, z], [x, 0.025, z], 0.0031, alloy);
  }
  coolingFans(radiator, enamel, aura, registerLight);
  shortCoolingLines(unit, p, braid, registerLight);
  return showTemperature;
}
