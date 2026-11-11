import * as T from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import type { Locale } from '../app/locale';
import {
  beam,
  box,
  cable,
  canvasTexture,
  group,
  luminous,
  mesh,
  surface,
  tube,
  type XYZ,
} from './geometry';
import type { Palette } from './materials';
import { motherboard } from './motherboard';

const diagonal = 31 * 0.0254;
const height = (diagonal * 9) / Math.hypot(16, 9);
const width = (height * 16) / 9;
export const display = {
  x: -0.135,
  y: 1.1,
  z: 0.03,
  width,
  height,
  outerWidth: width + 0.012,
  outerHeight: height + 0.026,
  surface: 0.003,
};
export const deskSetup = {
  speakerSpacing: 0.46,
  speakerZ: display.z + display.surface - 0.0729,
  mat: { x: display.x, z: 0.226, width: 0.9, depth: 0.4, top: 0.753 },
  inputZ: 0.237,
};

function rogEye(finish: 'case' | 'lit' | 'etched' = 'case') {
  return canvasTexture(512, 280, (ctx) => {
    const point = new Path2D('M32 77 Q62 120 96 158 Q47 138 32 77 Z');
    const upper = new Path2D(
      'M87 122 Q109 143 136 157 Q231 96 314 53 Q372 22 477 28 Q391 43 331 71 Q217 123 142 188 L167 239 Q119 204 87 122 Z',
    );
    const lower = new Path2D(
      'M151 185 Q278 91 486 62 L462 98 Q298 128 205 178 Q248 198 313 218 Q365 190 414 133 L457 112 Q406 206 349 244 Q329 257 303 248 Q212 227 151 185 Z',
    );
    if (finish === 'etched') {
      point.addPath(upper);
      point.addPath(lower);
      ctx.clip(point);
      ctx.fillStyle = '#625846';
      ctx.fillRect(0, 0, 512, 280);
      ctx.strokeStyle = '#c2ae86';
      ctx.lineWidth = 2.2;
      for (let x = -280; x < 512; x += 5.7) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + 278, 280);
        ctx.stroke();
      }
      return;
    }
    const silver = ctx.createLinearGradient(0, 32, 0, 240);
    silver.addColorStop(0, '#f3f2ec');
    silver.addColorStop(1, '#8b98a0');
    ctx.fillStyle = finish === 'lit' ? '#ffffff' : silver;
    ctx.fill(point);
    ctx.fill(upper);
    const scarlet = ctx.createLinearGradient(300, 53, 260, 248);
    scarlet.addColorStop(0, '#ed897e');
    scarlet.addColorStop(0.45, '#d14c3d');
    scarlet.addColorStop(1, '#8c231e');
    ctx.fillStyle = finish === 'lit' ? '#c0c0c0' : scarlet;
    ctx.fill(lower);
  });
}

function litRogEye() {
  const map = rogEye('lit');
  return new T.MeshStandardMaterial({
    color: '#343b3f',
    map,
    emissiveMap: map,
    alphaTest: 0.35,
    roughness: 0.35,
  });
}

export function monitor(parent: T.Object3D, p: Palette) {
  const { x, y, z, width, height, outerWidth, outerHeight, surface: screenFace } = display;
  const monitor = group(parent, '31-inch OLED', [x, y, z]);
  box(monitor, [outerWidth, outerHeight, 0.033], [0, -0.008, -0.021], p.graphite, 0.005);
  box(monitor, [width + 0.007, height + 0.019, 0.012], [0, -0.006, -0.004], p.black, 0.0025);
  box(monitor, [0.42, 0.255, 0.05], [0, -0.016, -0.044], p.black, 0.02);
  box(monitor, [0.19, 0.048, 0.006], [0, -0.157, -0.039], p.graphite, 0.004);
  for (let i = -13; i <= 13; i++) {
    box(monitor, [0.003, 0.022, 0.006], [i * 0.006, -0.157, -0.043], p.rubber);
  }
  const time = { value: 0 };
  const displayGlass = new T.MeshPhysicalMaterial({
    color: '#05090d',
    roughness: 0.54,
    clearcoat: 0.1,
    clearcoatRoughness: 0.38,
  });
  displayGlass.onBeforeCompile = (shader) => {
    shader.uniforms.flowTime = time;
    shader.vertexShader =
      'varying vec2 displayUv;\n' +
      shader.vertexShader.replace('#include <uv_vertex>', '#include <uv_vertex>\n displayUv = uv;');
    shader.fragmentShader =
      'uniform float flowTime;\nvarying vec2 displayUv;\n' +
      shader.fragmentShader.replace(
        '#include <emissivemap_fragment>',
        `
      #include <emissivemap_fragment>
      vec2 uv = displayUv;
      float t = flowTime * 0.49;
      float wave = sin(uv.x * 7.1 + t) * 0.114 + sin(uv.x * 11.7 - t * 0.6) * 0.045;
      float edge = 0.39 + wave + 0.18 * uv.x;
      float curtain = 1.0 - smoothstep(edge - 0.24, edge + 0.09, uv.y);
      float crest = exp(-pow(abs(uv.y - edge) * 12.0, 2.0));
      vec3 ink = mix(vec3(0.026, 0.098, 0.17), vec3(0.09, 0.28, 0.27), smoothstep(0.07, 0.64, uv.x));
      vec3 light = mix(ink, vec3(0.38, 0.27, 0.15), smoothstep(0.58, 0.87, uv.x) * (1.0 - smoothstep(0.92, 1.0, uv.x)));
      totalEmissiveRadiance += vec3(0.012, 0.026, 0.043) + light * (curtain * 0.91 + crest * 0.23);
    `,
      );
  };
  const screen = mesh(monitor, new T.PlaneGeometry(width, height), displayGlass, [
    0,
    0,
    screenFace,
  ]);
  screen.castShadow = screen.receiveShadow = false;
  const clock = canvasTexture(512, 288, () => {});
  const face = mesh(
    monitor,
    new T.PlaneGeometry(width, height),
    new T.MeshBasicMaterial({
      map: clock,
      transparent: true,
      depthWrite: false,
      toneMapped: false,
    }),
    [0, 0, screenFace + 0.00025],
  );
  face.castShadow = face.receiveShadow = false;
  const ctx = (clock.image as HTMLCanvasElement).getContext('2d')!;
  let lastMinute = -1;
  let lastLocale: Locale | undefined;
  function updateDisplay(locale: Locale, elapsed: number) {
    time.value = elapsed;
    const minute = Math.floor(Date.now() / 60000);
    if (minute === lastMinute && locale === lastLocale) return;
    lastMinute = minute;
    lastLocale = locale;
    const now = new Date();
    const language = locale === 'en' ? 'en-GB' : 'zh-CN';
    ctx.clearRect(0, 0, 512, 288);
    ctx.textAlign = 'center';
    ctx.fillStyle = '#d5e5df';
    ctx.font = '500 13px "IBM Plex Sans", "Studio Han", sans-serif';
    ctx.fillText(
      new Intl.DateTimeFormat(language, { weekday: 'long', month: 'long', day: 'numeric' }).format(
        now,
      ),
      256,
      82,
    );
    ctx.font = '500 65px "IBM Plex Sans", sans-serif';
    ctx.fillText(
      new Intl.DateTimeFormat(language, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(now),
      256,
      147,
    );
    ctx.font = '500 12px "IBM Plex Sans", sans-serif';
    ctx.fillText('Felix Studio', 256, 240);
    clock.needsUpdate = true;
  }
  updateDisplay('en', 0);
  const trim = luminous('#c64b31', 0.9);
  const chin = -height / 2 - 0.011;
  box(monitor, [0.018, 0.0023, 0.003], [0, chin, 0.003], trim, 0.0009);
  box(monitor, [0.012, 0.001, 0.004], [0.305, chin, 0.001], p.steel);
  const arm = group(monitor, 'Stand · cast plate, upright and tilt hinge');
  const foot = new T.Shape();
  foot.moveTo(-0.152, -0.092);
  foot.quadraticCurveTo(-0.164, -0.092, -0.163, -0.078);
  foot.lineTo(-0.137, 0.086);
  foot.quadraticCurveTo(-0.135, 0.099, -0.122, 0.099);
  foot.lineTo(0.122, 0.099);
  foot.quadraticCurveTo(0.135, 0.099, 0.137, 0.086);
  foot.lineTo(0.163, -0.078);
  foot.quadraticCurveTo(0.164, -0.092, 0.152, -0.092);
  foot.closePath();
  const plate = mesh(
    arm,
    new T.ExtrudeGeometry(foot, {
      depth: 0.007,
      bevelEnabled: true,
      bevelSize: 0.002,
      bevelThickness: 0.002,
      bevelSegments: 3,
    }),
    p.graphite,
    [0, -0.345, -0.078],
  );
  plate.rotation.x = -Math.PI / 2;
  for (const x of [-0.11, 0.11])
    for (const z of [-0.146, -0.012]) {
      box(arm, [0.038, 0.003, 0.02], [x, -0.3485, z], p.rubber, 0.001);
    }
  box(arm, [0.068, 0.006, 0.058], [0, -0.337, -0.065], p.black, 0.002);
  beam(arm, [0, -0.335, -0.066], [0, -0.159, -0.105], 0.053, 0.033, p.graphite);
  box(arm, [0.078, 0.062, 0.024], [0, -0.126, -0.075], p.black, 0.006);
  tube(arm, [-0.032, -0.152, -0.097], [0.032, -0.152, -0.097], 0.014, p.graphite);
  for (const sign of [-1, 1]) {
    tube(arm, [sign * 0.032, -0.152, -0.097], [sign * 0.033, -0.152, -0.097], 0.009, p.steel);
  }
  cable(
    arm,
    [
      [0.044, -0.151, -0.071],
      [0.052, -0.205, -0.104],
      [0.019, -0.301, -0.098],
      [0.018, -0.341, -0.151],
      [0.055, -0.347, -0.225],
    ],
    0.0027,
    p.rubber,
  );
  return { unit: monitor, updateDisplay };
}

function fan(parent: T.Object3D, position: XYZ, radius: number, p: Palette, rim: T.Material) {
  const unit = group(parent, 'Fan', position);
  box(unit, [radius * 2.16, radius * 2.16, 0.011], [0, 0, -0.009], p.black, 0.0035);
  mesh(unit, new T.TorusGeometry(radius * 0.935, radius * 0.035, 10, 48), p.graphite);
  if (rim !== p.black)
    mesh(unit, new T.TorusGeometry(radius * 0.915, radius * 0.018, 8, 48), rim, [0, 0, 0.001]);
  const rotor = group(unit, 'Fan rotor');
  const blade = new T.Shape();
  blade.moveTo(radius * 0.16, 0);
  blade.bezierCurveTo(
    radius * 0.4,
    -radius * 0.06,
    radius * 0.58,
    -radius * 0.3,
    radius * 0.79,
    -radius * 0.32,
  );
  blade.quadraticCurveTo(radius * 0.89, -radius * 0.03, radius * 0.79, radius * 0.1);
  blade.quadraticCurveTo(radius * 0.34, radius * 0.23, radius * 0.16, radius * 0.07);
  const geometry = new T.ExtrudeGeometry(blade, {
    depth: radius * 0.035,
    bevelEnabled: false,
    curveSegments: 5,
  });
  for (let i = 0; i < 7; i++) mesh(rotor, geometry, p.black).rotation.z = (i * Math.PI * 2) / 7;
  tube(rotor, [0, 0, -0.002], [0, 0, 0.008], radius * 0.23, p.graphite);
  tube(rotor, [0, 0, 0.008], [0, 0, 0.009], radius * 0.197, p.graphite);
  if (rim !== p.black) {
    mesh(
      unit,
      new T.TorusGeometry(radius * 0.765, radius * 0.023, 8, 48),
      rim,
      [0, 0, 0.0018],
    ).castShadow = false;
    mesh(
      rotor,
      new T.TorusGeometry(radius * 0.146, radius * 0.025, 8, 28),
      rim,
      [0, 0, 0.01],
    ).castShadow = false;
    for (let i = 0; i < 7; i++) {
      const diffuser = group(rotor, 'Translucent fan blade root');
      diffuser.rotation.z = (i * Math.PI * 2) / 7;
      box(
        diffuser,
        [radius * 0.25, radius * 0.066, radius * 0.013],
        [radius * 0.36, radius * 0.034, radius * 0.041],
        rim,
        radius * 0.007,
      ).castShadow = false;
    }
  }
  for (const x of [-1, 1])
    for (const y of [-1, 1]) {
      const screwX = x * radius * 0.91,
        screwY = y * radius * 0.91;
      tube(unit, [screwX, screwY, -0.004], [screwX, screwY, -0.002], radius * 0.035, p.steel);
    }
  return unit;
}

function caseLightGuide(parent: T.Group) {
  const points = [
    [-0.076, 0.244, 0.339],
    [0.075, 0.244, 0.339],
    [0.08, 0.23, 0.339],
    [0.021, 0.059, 0.344],
    [-0.015, -0.045, 0.344],
    [-0.078, -0.237, 0.339],
    [-0.067, -0.249, 0.339],
    [0.076, -0.249, 0.339],
    [0.08, -0.237, 0.339],
    [0.02, -0.059, 0.335],
    [-0.015, 0.046, 0.335],
    [-0.083, 0.23, 0.339],
  ].map((point) => new T.Vector3(...point));
  const guide = new T.TubeGeometry(
    new T.CatmullRomCurve3(points, true, 'catmullrom', 0.11),
    144,
    0.0029,
    8,
    true,
  );
  const material = luminous('#37383d', 0.82);
  material.emissive.set('#ffffff');
  material.roughness = 0.62;
  const phase = { value: 0 };
  material.onBeforeCompile = (shader) => {
    shader.uniforms.spectrumPhase = phase;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying float guidePath;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nguidePath = uv.x;');
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform float spectrumPhase; varying float guidePath;',
      )
      .replace(
        '#include <emissivemap_fragment>',
        `#include <emissivemap_fragment>
        vec3 prism = 0.5 + 0.5 * cos(6.2831853 * (guidePath + spectrumPhase + vec3(0.0, 0.67, 0.33)));
        totalEmissiveRadiance *= mix(vec3(0.075), prism, 0.92);`,
      );
  };
  const strip = mesh(parent, guide, material);
  strip.name = 'Continuous RGB diffuser';
  strip.castShadow = false;
  const spill = new T.PointLight('#6d9bd5', 0, 0.48, 2);
  spill.position.set(-0.063, 0.045, 0.08);
  parent.add(spill);
  return (active: boolean, clock: number) => {
    phase.value = (clock * 0.086) % 1;
    material.emissiveIntensity = active ? 1.1 : 0;
    spill.color.setHSL(phase.value + 0.56, 0.63, 0.51);
    spill.intensity = active ? 0.68 : 0;
  };
}

function liquidCooling(
  unit: T.Group,
  p: Palette,
  aluminum: T.MeshStandardMaterial,
  aura: T.MeshStandardMaterial[],
) {
  const pump = group(unit, 'AIO pump and cold plate', [0.038, 0.103, -0.117]);
  box(pump, [0.026, 0.059, 0.059], [0.024, 0, 0], aluminum, 0.003);
  box(pump, [0.029, 0.067, 0.067], [0.006, 0, 0], p.black, 0.008);
  tube(pump, [-0.009, 0, 0], [-0.017, 0, 0], 0.028, aluminum);
  tube(pump, [-0.018, 0, 0], [-0.021, 0, 0], 0.025, p.black);
  const ring = mesh(pump, new T.TorusGeometry(0.022, 0.0009, 8, 32), aura[5], [-0.021, 0, 0]);
  ring.rotation.y = -Math.PI / 2;

  const radiator = group(unit, 'Top-mounted AIO radiator', [0, 0.253, -0.041]);
  box(radiator, [0.169, 0.028, 0.345], [0, 0, 0], p.black, 0.004);
  box(radiator, [0.163, 0.027, 0.026], [0, 0, 0.16], aluminum, 0.0025);
  for (let i = 0; i < 22; i++) {
    box(radiator, [0.15, 0.0015, 0.0016], [0, -0.0147, -0.153 + i * 0.014], p.graphite);
  }
  for (let i = 0; i < 2; i++) {
    fan(radiator, [0, -0.02, -0.074 + i * 0.146], 0.064, p, aura[i + 3]).rotation.x = Math.PI / 2;
  }

  const braid = surface('#27282a', 0.76);
  braid.normalMap = p.cloth.normalMap!.clone();
  braid.normalMap.repeat.set(10, 1);
  braid.normalScale.set(0.52, 0.52);
  const v = (x: number, y: number, z: number) => new T.Vector3(x, y, z);
  for (let i = 0; i < 2; i++) {
    const pumpZ = -0.013 + i * 0.026;
    const radX = -0.054 + i * 0.03;
    const pumpFitting = group(pump, 'Pump compression fitting ' + (i + 1), [0.004, 0.03, pumpZ]);
    tube(pumpFitting, [0, -0.003, 0], [0, 0.008, 0], 0.01, aluminum);
    tube(pumpFitting, [0, 0.007, 0], [0, 0.019, 0], 0.0087, p.graphite);
    tube(pumpFitting, [0, 0.014, 0], [0, 0.016, 0], 0.0092, aluminum);
    const radFitting = group(radiator, 'Radiator compression fitting ' + (i + 1), [radX, 0, 0.171]);
    tube(radFitting, [0, 0, -0.004], [0, 0, 0.006], 0.0099, aluminum);
    tube(radFitting, [0, 0, 0.005], [0, 0, 0.017], 0.0087, p.graphite);
    tube(radFitting, [0, 0, 0.012], [0, 0, 0.014], 0.0092, aluminum);

    const pumpEnd = pumpFitting.position
      .clone()
      .add(pump.position)
      .add(v(0, 0.016, 0));
    const radEnd = radFitting.position
      .clone()
      .add(radiator.position)
      .add(v(0, 0, 0.014));
    const middle = v(-0.053 + i * 0.024, 0.199 + i * 0.007, 0.071 + i * 0.012);
    const tangent = v(0.004, 0.008, 0.067);
    const path = new T.CurvePath<T.Vector3>();
    path.add(
      new T.CubicBezierCurve3(
        pumpEnd,
        pumpEnd.clone().add(v(0, 0.057, 0)),
        middle.clone().sub(tangent),
        middle,
      ),
    );
    path.add(
      new T.CubicBezierCurve3(
        middle,
        middle.clone().add(tangent),
        radEnd.clone().add(v(0, 0, 0.071)),
        radEnd,
      ),
    );
    mesh(unit, new T.TubeGeometry(path, 64, 0.0069, 12, false), braid).name =
      'Braided coolant hose ' + (i + 1);
  }
}

function ssdTrays(unit: T.Group, p: Palette, aluminum: T.MeshStandardMaterial) {
  const rack = group(unit, 'SSD tray rack · front cable chamber', [0.111, 0.02, 0.154]);
  const cover = aluminum.clone();
  cover.color.set('#45494e');
  cover.roughness = 0.53;
  for (const z of [-0.056, 0.056]) {
    box(rack, [0.009, 0.346, 0.012], [0.001, 0, z], p.black, 0.0017);
    for (const y of [-0.162, 0.162]) {
      tube(rack, [-0.006, y, z], [-0.003, y, z], 0.0027, p.steel);
    }
  }
  for (let i = 0; i < 4; i++) {
    const tray = group(rack, 'Closed 2.5-inch SSD tray ' + (i + 1), [0, 0.132 - i * 0.088, 0]);
    box(tray, [0.015, 0.073, 0.118], [-0.004, 0, 0], p.graphite, 0.0028);
    box(tray, [0.004, 0.066, 0.109], [-0.012, 0, 0], cover, 0.0019);
    box(tray, [0.003, 0.016, 0.014], [-0.0145, 0, 0.048], p.black, 0.0015);
    for (const y of [-0.022, 0.022]) {
      tube(tray, [-0.0148, y, -0.044], [-0.0139, y, -0.044], 0.002, p.steel);
    }
    for (const y of [-0.006, 0, 0.006]) {
      box(tray, [0.0012, 0.0011, 0.018], [-0.0144, y, -0.026], p.graphite, 0.0003);
    }
  }
}

export function tower(parent: T.Object3D, p: Palette, aura: T.MeshStandardMaterial[]) {
  const unit = group(parent, 'Computer tower', [0.902, 1.069, -0.153]);
  const [w, h, d] = [0.268, 0.639, 0.659];
  box(unit, [w, 0.037, d], [0, h / 2 - 0.026, 0], p.graphite, 0.008);
  box(unit, [w, 0.045, d], [0, -h / 2 + 0.031, 0], p.graphite, 0.009);
  box(unit, [0.016, 0.572, 0.603], [w / 2 - 0.01, 0, 0], p.black, 0.004);
  box(unit, [0.239, 0.565, 0.019], [0, 0, -d / 2 + 0.014], p.black);
  box(unit, [0.23, 0.565, 0.044], [0, 0, d / 2 - 0.039], p.black, 0.009);
  const glass = new T.MeshPhysicalMaterial({
    color: '#8e9b9d',
    metalness: 0.025,
    roughness: 0.2,
    clearcoat: 0.55,
    clearcoatRoughness: 0.14,
    ior: 1.51,
    transparent: true,
    opacity: 0.068,
    depthWrite: false,
  });
  const glassPanel = box(unit, [0.004, 0.542, 0.552], [-w / 2 + 0.011, 0, -0.011], glass, 0.001);
  glassPanel.castShadow = false;
  for (const y of [-0.271, 0.271]) {
    box(unit, [0.005, 0.009, 0.555], [-w / 2 + 0.012, y, -0.011], p.rubber, 0.001);
    box(unit, [0.0013, 0.0012, 0.541], [-w / 2 + 0.0083, y, -0.011], p.steel, 0.00035);
  }
  for (const z of [-0.287, 0.265]) {
    box(unit, [0.005, 0.538, 0.008], [-w / 2 + 0.012, 0, z], p.rubber, 0.001);
    for (const y of [-0.252, 0.252]) {
      tube(unit, [-w / 2 + 0.006, y, z], [-w / 2 + 0.012, y, z], 0.0042, p.steel);
      box(unit, [0.001, 0.0033, 0.0008], [-w / 2 + 0.0056, y, z], p.black, 0.0002).rotation.x =
        0.58;
    }
  }
  for (const x of [-0.112, 0.112]) {
    for (const z of [-0.288, 0.287]) {
      box(unit, [0.027, 0.564, 0.027], [x, 0, z], p.graphite, 0.004);
      box(unit, [0.045, 0.024, 0.072], [x, -0.306, z], p.rubber, 0.004);
    }
  }
  const exoskeleton = new T.Shape();
  exoskeleton.moveTo(-0.126, 0.293);
  exoskeleton.quadraticCurveTo(-0.136, 0.29, -0.125, 0.263);
  exoskeleton.lineTo(-0.037, 0.037);
  exoskeleton.quadraticCurveTo(-0.025, 0, -0.037, -0.037);
  exoskeleton.lineTo(-0.127, -0.261);
  exoskeleton.quadraticCurveTo(-0.136, -0.289, -0.117, -0.287);
  exoskeleton.lineTo(-0.092, -0.283);
  exoskeleton.lineTo(-0.015, -0.087);
  exoskeleton.quadraticCurveTo(0, -0.053, 0.015, -0.087);
  exoskeleton.lineTo(0.092, -0.283);
  exoskeleton.lineTo(0.117, -0.287);
  exoskeleton.quadraticCurveTo(0.136, -0.289, 0.127, -0.261);
  exoskeleton.lineTo(0.037, -0.037);
  exoskeleton.quadraticCurveTo(0.025, 0, 0.037, 0.037);
  exoskeleton.lineTo(0.125, 0.263);
  exoskeleton.quadraticCurveTo(0.136, 0.29, 0.117, 0.293);
  exoskeleton.lineTo(0.098, 0.285);
  exoskeleton.lineTo(0.015, 0.085);
  exoskeleton.quadraticCurveTo(0, 0.046, -0.015, 0.085);
  exoskeleton.lineTo(-0.098, 0.285);
  exoskeleton.closePath();
  const aluminum = p.graphite.clone();
  aluminum.color.set('#555d64');
  aluminum.roughness = 0.38;
  aluminum.metalness = 0.58;
  mesh(
    unit,
    new T.ExtrudeGeometry(exoskeleton, {
      depth: 0.019,
      bevelEnabled: true,
      bevelSegments: 4,
      bevelThickness: 0.003,
      bevelSize: 0.003,
      curveSegments: 12,
    }),
    aluminum,
    [0, 0, 0.307],
  ).name = 'Satin anodized cast aluminum frame';
  for (const side of [-1, 1]) {
    for (const y of [-0.285, 0.283])
      beam(unit, [side * 0.114, y, -0.29], [side * 0.114, y, 0.318], 0.034, 0.029, p.graphite);
  }
  const updateLightGuide = caseLightGuide(unit);
  for (let i = 0; i < 29; i++) {
    const y = -0.233 + i * 0.016;
    const span = 0.029 + Math.abs(y) * 0.51;
    for (const side of [-1, 1])
      box(
        unit,
        [span * 0.44, 0.0027, 0.004],
        [side * span * 0.26, y, 0.314],
        p.graphite,
      ).rotation.z = side * 0.22;
  }
  const badge = mesh(
    unit,
    new T.PlaneGeometry(0.082, 0.045),
    new T.MeshBasicMaterial({
      map: rogEye(),
      transparent: true,
      depthWrite: false,
    }),
    [0, 0.17, 0.332],
  );
  badge.name = 'ROG eye badge';
  badge.castShadow = false;
  motherboard(unit, p, aluminum, aura);
  ssdTrays(unit, p, aluminum);
  liquidCooling(unit, p, aluminum, aura);
  for (let i = 0; i < 3; i++) {
    fan(unit, [0, -0.178 + i * 0.153, 0.251], 0.068, p, aura[i + 4]).rotation.y = Math.PI;
  }
  fan(unit, [0, 0.123, -0.276], 0.062, p, aura[5]);
  const gpu = group(unit, 'Graphics card · vertical bracket', [-0.035, -0.089, -0.093]);
  gpu.rotation.z = -Math.PI / 2;
  const cardWidth = 0.1493;
  box(gpu, [cardWidth, 0.062, 0.3576], [0, 0.002, 0], p.graphite, 0.012);
  box(gpu, [0.142, 0.008, 0.357], [0, 0.034, 0], p.black, 0.003);
  for (const x of [-0.06, 0.06]) box(gpu, [0.012, 0.012, 0.326], [x, -0.033, 0], p.steel, 0.0035);
  for (let i = 0; i < 32; i++)
    box(gpu, [0.004, 0.039, 0.002], [-0.076, 0.003, -0.148 + i * 0.0096], p.steel);
  for (let i = 0; i < 3; i++) {
    const z = -0.114 + i * 0.113;
    fan(gpu, [0, -0.038, z], 0.049, p, aura[i + 2]).rotation.x = Math.PI / 2;
    mesh(gpu, new T.TorusGeometry(0.05, 0.0021, 8, 48), p.steel, [0, -0.041, z]).rotation.x =
      Math.PI / 2;
    for (const x of [-0.054, 0.054])
      tube(gpu, [x, -0.034, z + 0.042], [x, -0.038, z + 0.042], 0.0026, p.steel);
  }
  fan(gpu, [0, 0.04, 0.116], 0.047, p, p.black).rotation.x = -Math.PI / 2;
  box(gpu, [0.003, 0.004, 0.266], [-0.079, -0.023, 0.004], aura[4], 0.001);
  const shroud = box(unit, [0.211, 0.108, 0.503], [0.009, -0.234, -0.025], p.black, 0.007);
  const support = group(unit, 'GPU support · beneath free end', [
    gpu.position.x,
    shroud.position.y + 0.054,
    gpu.position.z + 0.145,
  ]);
  const rise = gpu.position.y - cardWidth / 2 - support.position.y;
  box(support, [0.027, 0.003, 0.023], [0, 0.001, 0], p.graphite, 0.001);
  tube(support, [0, 0.002, 0], [0, rise - 0.002, 0], 0.0063, aluminum);
  box(support, [0.02, 0.004, 0.017], [0, rise - 0.001, 0], p.rubber, 0.0014);
  box(unit, [0.128, 0.083, 0.139], [0.024, -0.242, -0.229], p.graphite, 0.004).name =
    'Power supply';
  for (let i = 0; i < 3; i++) {
    cable(
      unit,
      [
        [0.05, -0.211, -0.14 + i * 0.009],
        [0.036, -0.188, -0.096 + i * 0.009],
        [0.029, -0.163, 0.029 + i * 0.009],
      ],
      0.0023,
      p.rubber,
    );
  }
  for (const x of [-0.051, -0.028, -0.005, 0.018]) {
    box(unit, [0.015, 0.002, 0.008], [x, 0.298, 0.237], p.steel, 0.0012);
    box(unit, [0.012, 0.002, 0.0046], [x, 0.2992, 0.237], p.black, 0.0009);
  }
  tube(unit, [0.04, 0.297, 0.238], [0.04, 0.299, 0.238], 0.0027, p.black);
  const auraButton = box(unit, [0.024, 0.007, 0.021], [0.062, 0.306, 0.259], p.graphite, 0.002);
  auraButton.name = 'Aura button';
  return { unit, auraButton, updateLightGuide };
}

const keyboardRows = [
  'ESC F1 F2 F3 F4 F5 F6 F7 F8 F9 F10 F11 F12',
  '` 1 2 3 4 5 6 7 8 9 0 - = BACK:2 DEL',
  'TAB:1.5 Q W E R T Y U I O P [ ] \\:1.5 PGUP',
  'CAPS:1.75 A S D F G H J K L ; ′ ENTER:2.25 PGDN',
  'SHIFT:2.25 Z X C V B N M , . / SHIFT:1.75 ↑ END',
  'CTRL:1.25 WIN:1.25 ALT:1.25 SPACE:6.25 ALT FN CTRL ← ↓ →',
];

export function keyboard(parent: T.Object3D, p: Palette, aura: T.MeshStandardMaterial[]) {
  const unit = group(parent, 'Mechanical keyboard', [
    display.x,
    deskSetup.mat.top,
    deskSetup.inputZ,
  ]);
  box(unit, [0.332, 0.013, 0.139], [0, 0.007, 0], p.graphite, 0.003);
  box(unit, [0.331, 0.0012, 0.138], [0, 0.014, 0], p.black, 0.0005);
  box(unit, [0.332, 0.0065, 0.139], [0, 0.017, 0], p.graphite, 0.002);
  box(unit, [0.321, 0.0016, 0.127], [0, 0.0208, 0], p.carbon, 0.0007);
  box(unit, [0.326, 0.015, 0.067], [0, 0.008, 0.105], p.rubber, 0.006);
  const wristCloth = surface('#3c3e40', 0.92);
  wristCloth.normalMap = p.cloth.normalMap;
  box(unit, [0.325, 0.002, 0.059], [0, 0.016, 0.105], wristCloth, 0.001);
  const wristMark = mesh(
    unit,
    new T.PlaneGeometry(0.123, 0.0673),
    new T.MeshStandardMaterial({ map: rogEye('etched'), roughness: 0.74, alphaTest: 0.4 }),
    [0.101, 0.0172, 0.105],
  );
  wristMark.rotation.x = -Math.PI / 2;
  wristMark.castShadow = false;
  const unitWidth = 0.0195;
  const layout = keyboardRows.flatMap((row, rowIndex) => {
    let x = -unitWidth * 8;
    return row.split(' ').map((spec) => {
      const [label, span = '1'] = spec.split(':');
      const width = unitWidth * Number(span);
      const key = { label, width, x: x + width / 2, z: -0.054 + rowIndex * 0.02, row: rowIndex };
      x += width;
      return key;
    });
  });
  const columns = 8,
    rows = Math.ceil(layout.length / columns);
  const legends = canvasTexture(columns * 128, rows * 96, (ctx) => {
    ctx.fillStyle = '#dddcd4';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (const [index, { label }] of layout.entries()) {
      ctx.font = (label.length === 1 ? '600 43px ' : '500 30px ') + '"IBM Plex Sans", sans-serif';
      ctx.fillText(
        label === 'SPACE' ? '–' : label,
        (index % columns) * 128 + 64,
        Math.floor(index / columns) * 96 + 48,
        108,
      );
    }
  });
  const legendMaterials = aura.map(
    () =>
      new T.MeshStandardMaterial({
        color: '#91999f',
        map: legends,
        emissiveMap: legends,
        alphaTest: 0.38,
        roughness: 0.73,
      }),
  );
  const graphite = surface('#303236', 0.68);
  const touched = surface('#323438', 0.54);
  const frequentlyUsed = new Set(['W', 'A', 'S', 'D', 'E', 'SPACE', 'ENTER']);
  const secondary = surface('#454a4f', 0.71);
  const accent = surface('#766358', 0.65);
  const capProfiles = new Map<number, T.BufferGeometry>();
  for (const [index, { label, width, x, z, row }] of layout.entries()) {
    const y = 0.0305 - row * 0.00045;
    let profile = capProfiles.get(width);
    if (!profile) {
      profile = new RoundedBoxGeometry(width - 0.0013, 0.008, 0.0183, 2, 0.0012);
      const positions = profile.attributes.position;
      for (let i = 0; i < positions.count; i++) {
        const taper = (positions.getY(i) + 0.004) / 0.008;
        positions.setX(i, positions.getX(i) * (1 - taper * 0.15));
        positions.setZ(i, positions.getZ(i) * (1 - taper * 0.16));
      }
      profile.computeVertexNormals();
      capProfiles.set(width, profile);
    }
    const cap =
      label === 'ESC'
        ? accent
        : frequentlyUsed.has(label)
          ? touched
          : label.length > 1 || '↑↓←→'.includes(label)
            ? secondary
            : graphite;
    mesh(unit, profile, cap, [x, y, z]);
    const light = Math.min(aura.length - 1, Math.floor((x / (unitWidth * 16) + 0.5) * aura.length));
    const diffuser = box(
      unit,
      [width - 0.0006, 0.0015, 0.0192],
      [x, y - 0.00455, z],
      aura[light],
      0.0005,
    );
    diffuser.castShadow = false;
    const legend = new T.PlaneGeometry(0.015, 0.0125);
    const uv = legend.attributes.uv;
    for (let i = 0; i < uv.count; i++) {
      uv.setXY(
        i,
        ((index % columns) + uv.getX(i)) / columns,
        1 - (Math.floor(index / columns) + 1 - uv.getY(i)) / rows,
      );
    }
    const labelFace = mesh(unit, legend, legendMaterials[light], [x, y + 0.00415, z]);
    labelFace.rotation.x = -Math.PI / 2;
    labelFace.castShadow = labelFace.receiveShadow = false;
  }
  box(unit, [0.047, 0.002, 0.016], [0.123, 0.022, -0.054], p.steel, 0.0011);
  box(unit, [0.044, 0.0016, 0.0135], [0.123, 0.0232, -0.054], surface('#14202b', 0.28), 0.0009);
  const badge = litRogEye();
  const emblem = mesh(unit, new T.PlaneGeometry(0.024, 0.0131), badge, [0.123, 0.0242, -0.054]);
  emblem.rotation.x = -Math.PI / 2;
  emblem.name = 'Illuminated keyboard ROG eye';
  emblem.castShadow = false;
  tube(unit, [0.155, 0.022, -0.054], [0.155, 0.028, -0.054], 0.0068, p.steel);
  tube(unit, [0.155, 0.028, -0.054], [0.155, 0.0286, -0.054], 0.006, p.graphite);
  box(unit, [0.013, 0.006, 0.003], [0.107, 0.009, -0.069], p.steel, 0.002);
  box(unit, [0.01, 0.003, 0.002], [0.107, 0.009, -0.0706], p.black, 0.0012);
  const segment = 0.307 / aura.length;
  for (const [i, light] of aura.entries()) {
    box(
      unit,
      [segment - 0.0003, 0.0012, 0.0013],
      [-0.1535 + segment * (i + 0.5), 0.016, 0.0697],
      light,
      0.0004,
    ).castShadow = false;
  }
  return { unit, legendMaterials, badge };
}

export function mouse(parent: T.Object3D, p: Palette, glow: T.Material) {
  const unit = group(parent, 'Wireless mouse', [
    display.x + 0.36,
    deskSetup.mat.top + 0.0012,
    deskSetup.inputZ,
  ]);
  const sections = [
    [-0.068, 0.001, 0.002],
    [-0.065, 0.014, 0.01],
    [-0.055, 0.024, 0.018],
    [-0.034, 0.027, 0.027],
    [-0.01, 0.026, 0.036],
    [0.018, 0.031, 0.039],
    [0.041, 0.027, 0.031],
    [0.062, 0.014, 0.011],
    [0.0665, 0.001, 0.0015],
  ];
  const outline = new T.CatmullRomCurve3(
    sections.map(([z, width, height]) => new T.Vector3(z, width, height)),
  );
  const ribs = outline.getPoints(52);
  const positions: number[] = [],
    uv: number[] = [],
    indices: number[] = [];
  const radial = 40;
  const shellPoint = ({ x: z, y: width, z: height }: T.Vector3, t: number, lift = 0): XYZ => {
    const angle = t * Math.PI;
    return [Math.cos(angle) * width, 0.003 + Math.sin(angle) ** 0.68 * height + lift, z];
  };
  const ribAt = (z: number) => {
    const next = ribs.findIndex((rib) => rib.x >= z);
    const before = ribs[next - 1],
      after = ribs[next];
    return before.clone().lerp(after, (z - before.x) / (after.x - before.x));
  };
  ribs.forEach((rib, i) => {
    for (let j = 0; j <= radial; j++) {
      positions.push(...shellPoint(rib, j / radial));
      uv.push(j / radial, i / (ribs.length - 1));
      if (i && j) {
        const slot = rib.x > -0.053 && rib.x < -0.026 && Math.abs(j - 20.5) < 2;
        if (slot) continue;
        const k = i * (radial + 1) + j;
        indices.push(k - radial - 2, k, k - 1, k - radial - 2, k - radial - 1, k);
      }
    }
  });
  for (const end of [0, ribs.length - 1]) {
    const start = end * (radial + 1);
    const anchor = positions.length / 3;
    positions.push(0, 0.003, ribs[end].x);
    uv.push(0.5, end === 0 ? 0 : 1);
    for (let j = 1; j <= radial; j++) {
      if (end === 0) indices.push(anchor, start + j, start + j - 1);
      else indices.push(anchor, start + j - 1, start + j);
    }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  mesh(unit, geometry, p.carbon).name = 'Satin carbon composite shell';
  const base = new T.Shape();
  ribs.forEach((rib, index) => {
    if (index === 0) base.moveTo(rib.y, -rib.x);
    else base.lineTo(rib.y, -rib.x);
  });
  for (const rib of [...ribs].reverse()) base.lineTo(-rib.y, -rib.x);
  base.closePath();
  const aperture = new T.Path();
  aperture.absellipse(0, -0.002, 0.0035, 0.0048, 0, Math.PI * 2, true, 0);
  base.holes.push(aperture);
  const bottom = mesh(
    unit,
    new T.ExtrudeGeometry(base, {
      depth: 0.0025,
      bevelEnabled: true,
      bevelThickness: 0.00036,
      bevelSize: 0.00044,
      bevelSegments: 2,
    }),
    p.black,
    [0, 0.0005, 0],
  );
  bottom.rotation.x = -Math.PI / 2;
  bottom.name = 'Seamed lower housing';
  const seam = surface('#15191b', 0.63);
  cable(
    unit,
    ribs.filter((rib) => rib.x < -0.052).map((rib) => shellPoint(rib, 0.5, 0.0001)),
    0.00037,
    seam,
  );
  cable(
    unit,
    ribs
      .filter((rib) => rib.x > -0.029 && rib.x < -0.017)
      .map((rib) => shellPoint(rib, 0.5, 0.0001)),
    0.00037,
    seam,
  );
  const seamRib = ribs.find((rib) => rib.x >= -0.017)!;
  cable(
    unit,
    Array.from({ length: 21 }, (_, i) => shellPoint(seamRib, i / 20, 0.0001)),
    0.00037,
    seam,
  );
  function curvedInsert(
    z: number,
    width: number,
    length: number,
    offset: number,
    material: T.Material,
  ) {
    const geometry = new T.PlaneGeometry(width, length, 16, 10);
    const points = geometry.attributes.position;
    for (let i = 0; i < points.count; i++) {
      const rib = ribAt(z - points.getY(i));
      const angle = Math.acos(points.getX(i) / rib.y);
      points.setXYZ(i, ...shellPoint(rib, angle / Math.PI, offset));
    }
    geometry.computeVertexNormals();
    return mesh(unit, geometry, material);
  }
  const badge = litRogEye();
  const emblem = curvedInsert(0.038, 0.027, 0.0148, 0.00026, badge);
  emblem.name = 'Illuminated mouse ROG eye';
  emblem.castShadow = false;
  box(unit, [0.009, 0.008, 0.027], [0, 0.015, -0.04], seam, 0.0014);
  curvedInsert(-0.0517, 0.0077, 0.0071, -0.00048, seam).name =
    'Flush insert ahead of the scroll wheel';
  curvedInsert(-0.0282, 0.0077, 0.0078, -0.00048, seam).name =
    'Flush insert behind the scroll wheel';
  tube(unit, [-0.0037, 0.025, -0.04], [0.0037, 0.025, -0.04], 0.0074, p.steel);
  tube(unit, [-0.0026, 0.025, -0.04], [0.0026, 0.025, -0.04], 0.008, p.rubber);
  for (const side of [-1, 1]) {
    const lit = mesh(unit, new T.TorusGeometry(0.0066, 0.00062, 8, 30), glow, [
      side * 0.00316,
      0.025,
      -0.04,
    ]);
    lit.rotation.y = Math.PI / 2;
    lit.castShadow = false;
  }
  for (let i = 0; i < 22; i++) {
    const angle = (i * 2 * Math.PI) / 22;
    const tread = box(
      unit,
      [0.0052, 0.00042, 0.0005],
      [0, 0.025 + Math.cos(angle) * 0.008, -0.04 + Math.sin(angle) * 0.008],
      p.graphite,
    );
    tread.rotation.x = angle;
  }
  function thumbSurface(
    z: number,
    length: number,
    height: number,
    lift: number,
    depth: number,
    material: T.Material,
  ) {
    const x = length / 2,
      y = height / 2;
    const contour = new T.Shape();
    contour.moveTo(-x, -y * 0.43);
    contour.quadraticCurveTo(-x, -y, -x * 0.62, -y);
    contour.lineTo(x * 0.7, -y);
    contour.quadraticCurveTo(x, -y * 0.92, x, -y * 0.18);
    contour.quadraticCurveTo(x, y, x * 0.65, y);
    contour.lineTo(-x * 0.72, y * 0.83);
    contour.quadraticCurveTo(-x, y * 0.65, -x, -y * 0.43);
    const shape = new T.ExtrudeGeometry(contour, {
      depth,
      bevelEnabled: true,
      bevelSegments: 2,
      bevelSize: 0.00027,
      bevelThickness: 0.00027,
      curveSegments: 7,
    });
    const points = shape.attributes.position;
    for (let i = 0; i < points.count; i++) {
      const rib = ribAt(z + points.getX(i));
      const [sx, sy, sz] = shellPoint(rib, 0.865 - points.getY(i) / 0.077);
      const rise = lift + points.getZ(i);
      points.setXYZ(i, sx - rise, sy + rise * 0.18, sz);
    }
    shape.computeVertexNormals();
    return mesh(unit, shape, material);
  }
  const thumbButtons = [
    [seamRib.x - 0.0108, 0.016, 'Forward thumb button'],
    [seamRib.x + 0.0112, 0.0168, 'Back thumb button'],
  ] as const;
  for (const [z, length, name] of thumbButtons) {
    thumbSurface(z, length + 0.002, 0.0078, -0.00024, 0.00054, seam).name = name + ' gasket';
    thumbSurface(z, length, 0.0058, 0.00015, 0.00074, p.graphite).name = name;
  }
  const skates = surface('#c7c6bd', 0.49);
  skates.normalMap = p.paper.normalMap;
  skates.normalScale.set(0.35, 0.35);
  for (const end of [-1, 1]) {
    const skate = new T.Shape();
    skate.moveTo(-0.0215, 0.003);
    skate.quadraticCurveTo(-0.0215, 0.009, -0.014, 0.013);
    skate.quadraticCurveTo(0, 0.019, 0.014, 0.013);
    skate.quadraticCurveTo(0.0215, 0.009, 0.0215, 0.003);
    skate.quadraticCurveTo(0.021, 0.0005, 0.018, 0.001);
    skate.quadraticCurveTo(0, 0.004, -0.018, 0.001);
    skate.quadraticCurveTo(-0.021, 0.0005, -0.0215, 0.003);
    const foot = mesh(
      unit,
      new T.ExtrudeGeometry(skate, {
        depth: 0.0006,
        bevelEnabled: true,
        bevelThickness: 0.0003,
        bevelSize: 0.0006,
        bevelSegments: 3,
      }),
      skates,
      [0, -0.0007, end * 0.039],
    );
    foot.rotation.set(-Math.PI / 2, 0, end < 0 ? 0 : Math.PI);
  }
  const bezel = mesh(unit, new T.RingGeometry(0.0044, 0.0064, 32), p.graphite, [0, 0.00002, 0.002]);
  bezel.rotation.x = Math.PI / 2;
  bezel.scale.y = 1.19;
  const optics = new T.MeshPhysicalMaterial({
    color: '#202e3a',
    roughness: 0.18,
    metalness: 0.32,
    clearcoat: 0.92,
  });
  const sensor = mesh(
    unit,
    new T.SphereGeometry(0.0031, 24, 10, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2),
    optics,
    [0, 0.0016, 0.002],
  );
  sensor.scale.set(1, 0.33, 1.22);
  box(unit, [0.0068, 0.00045, 0.012], [-0.013, 0.00022, 0.021], p.graphite, 0.0014);
  box(unit, [0.0049, 0.001, 0.0048], [-0.013, -0.00042, 0.0185], p.black, 0.0012);
  tube(unit, [0.014, 0.0003, 0.021], [0.014, -0.00058, 0.021], 0.0027, p.graphite);
  for (const [x, z] of [
    [-0.014, -0.027],
    [0.015, 0.036],
  ]) {
    tube(unit, [x, 0.00012, z], [x, -0.00027, z], 0.0021, p.black);
    tube(unit, [x, -0.00028, z], [x, -0.00046, z], 0.0014, p.steel);
    box(unit, [0.00175, 0.00006, 0.00038], [x, -0.00051, z], p.black).rotation.y = 0.42;
  }
  const marking = canvasTexture(256, 112, (ctx) => {
    ctx.fillStyle = '#94928a';
    ctx.font = '600 19px "IBM Plex Sans", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('WIRELESS', 128, 41);
    ctx.font = '500 12px "IBM Plex Sans", sans-serif';
    ctx.fillText('2.4G   /   BT   /   USB', 128, 69);
  });
  const transfer = mesh(
    unit,
    new T.PlaneGeometry(0.034, 0.014),
    new T.MeshStandardMaterial({
      map: marking,
      transparent: true,
      depthWrite: false,
      roughness: 0.82,
    }),
    [0, 0.00009, -0.019],
  );
  transfer.rotation.x = Math.PI / 2;
  transfer.castShadow = false;
  return { unit, badge };
}

export function speaker(parent: T.Object3D, p: Palette, side: -1 | 1, meter: T.Material[]) {
  const scaleY = 1.2;
  const unit = group(parent, side === -1 ? 'Left speaker' : 'Right speaker', [
    display.x + side * deskSetup.speakerSpacing,
    0.7515 + 0.1125 * scaleY,
    deskSetup.speakerZ,
  ]);
  unit.scale.set(1.16, scaleY, 1.07);
  box(unit, [0.102, 0.225, 0.111], [0, 0, 0], p.black, 0.011);
  box(unit, [0.093, 0.215, 0.009], [0, 0, 0.055], p.bronze, 0.006);
  box(unit, [0.086, 0.208, 0.01], [0, 0, 0.06], p.cloth, 0.006);
  const driver = p.rubber.clone();
  driver.color.set('#343537');
  driver.roughness = 0.81;
  const dustCap = surface('#232628', 0.61);
  for (const [y, r] of [
    [0.049, 0.024],
    [-0.041, 0.034],
  ]) {
    mesh(unit, new T.TorusGeometry(r, 0.0017, 8, 42), p.graphite, [0, y, 0.068]);
    mesh(unit, new T.TorusGeometry(r * 0.89, r * 0.085, 10, 42), p.rubber, [0, y, 0.07]);
    const cone = [
      new T.Vector2(0, 0.0011),
      new T.Vector2(r * 0.28, 0.0011),
      new T.Vector2(r * 0.73, 0.003),
      new T.Vector2(r * 0.9, 0.0055),
    ];
    mesh(unit, new T.LatheGeometry(cone, 42), driver, [0, y, 0.0645]).rotation.x = Math.PI / 2;
    const dome = mesh(
      unit,
      new T.SphereGeometry(r * 0.29, 30, 14, 0, Math.PI * 2, 0, Math.PI / 2),
      dustCap,
      [0, y, 0.066],
    );
    dome.rotation.x = Math.PI / 2;
    dome.scale.y = 0.56;
  }
  box(unit, [0.022, 0.005, 0.002], [0, -0.088, 0.068], p.bronze, 0.001);
  box(unit, [0.052, 0.01, 0.0018], [0, -0.098, 0.067], p.black, 0.0011);
  meter.forEach((material, i) => {
    const height = 0.0042 + i * 0.00044;
    box(
      unit,
      [0.0052, height, 0.0011],
      [(i - (meter.length - 1) / 2) * 0.0074, -0.101 + height / 2, 0.068],
      material,
      0.00055,
    ).castShadow = false;
  });
  return unit;
}
