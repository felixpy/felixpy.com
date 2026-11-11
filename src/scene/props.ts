import * as T from 'three';
import {
  beam,
  box,
  cable,
  canvasTexture,
  group,
  luminous,
  mesh,
  random,
  surface,
  tube,
  type XYZ,
} from './geometry';
import type { Palette } from './materials';

export function lamp(parent: T.Object3D, p: Palette, position: XYZ) {
  const unit = group(parent, 'Anglepoise', position);
  tube(unit, [0, 0, 0], [0, 0.02, 0], 0.073, p.bronze, 0.067);
  tube(unit, [0, 0.02, 0], [0, 0.036, 0], 0.04, p.graphite, 0.036);
  const elbow: XYZ = [-0.035, 0.3, -0.047];
  const hinge: XYZ = [0.133, 0.413, -0.03];
  for (const offset of [-0.012, 0.012]) {
    beam(unit, [offset, 0.033, 0], [elbow[0] + offset, elbow[1], elbow[2]], 0.008, 0.011, p.bronze);
    beam(
      unit,
      [elbow[0] + offset, elbow[1], elbow[2]],
      [hinge[0] + offset, hinge[1], hinge[2]],
      0.008,
      0.011,
      p.bronze,
    );
  }
  for (const [x, y, z] of [[0, 0.048, 0], elbow, hinge])
    tube(unit, [x - 0.017, y, z], [x + 0.017, y, z], 0.014, p.graphite);
  const shade = group(unit, 'Spun metal shade', [0.155, 0.369, -0.015]);
  shade.rotation.z = -0.51;
  const profile = [
    [0.066, -0.047],
    [0.074, -0.047],
    [0.074, -0.042],
    [0.068, -0.038],
    [0.062, -0.014],
    [0.048, 0.008],
    [0.029, 0.021],
    [0.022, 0.034],
    [0.022, 0.049],
    [0.017, 0.05],
    [0.017, 0.03],
    [0.022, 0.015],
    [0.041, 0.003],
    [0.056, -0.017],
    [0.066, -0.042],
    [0.066, -0.047],
  ];
  const satinBrass = p.bronze.clone();
  satinBrass.color.set('#9e7b59');
  satinBrass.roughness = 0.41;
  mesh(
    shade,
    new T.LatheGeometry(
      profile.map(([x, y]) => new T.Vector2(x, y)),
      64,
    ),
    satinBrass,
  );
  const emitter = luminous('#ffe0aa', 2);
  const bulb = tube(shade, [0, -0.04, 0], [0, -0.035, 0], 0.064, emitter);
  bulb.castShadow = false;
  return { unit, emitter, bulb };
}

export function remote(parent: T.Object3D, p: Palette, position: XYZ) {
  const cradle = group(parent, 'Walnut window remote cradle', position);
  box(cradle, [0.066, 0.01, 0.076], [0, 0.005, 0], p.woodDark, 0.003);
  box(cradle, [0.007, 0.012, 0.069], [0.012, 0.013, 0], p.woodVertical, 0.0018);
  box(cradle, [0.008, 0.041, 0.067], [-0.012, 0.028, 0], p.woodVertical, 0.0023).rotation.z = 0.14;
  box(cradle, [0.016, 0.002, 0.066], [0.002, 0.01, 0], p.rubber, 0.001);
  const unit = group(parent, 'Window remote', [
    position[0] - 0.005,
    position[1] + 0.073,
    position[2],
  ]);
  unit.quaternion.setFromRotationMatrix(
    new T.Matrix4().makeBasis(
      new T.Vector3(0, 0, -1),
      new T.Vector3(1, 0, 0),
      new T.Vector3(0, -1, 0),
    ),
  );
  unit.rotateOnWorldAxis(new T.Vector3(0, 0, 1), 0.14);
  const body = box(unit, [0.061, 0.013, 0.126], [0, 0, 0], p.graphite, 0.005);
  box(unit, [0.056, 0.002, 0.118], [0, 0.007, 0], p.black, 0.001);
  box(unit, [0.04, 0.004, 0.021], [0, -0.005, 0.034], p.rubber, 0.002);
  box(unit, [0.042, 0.006, 0.011], [0, 0, -0.061], p.rubber, 0.002);
  const buttons: T.Group[] = [];
  const symbols = ['blinds', 'angle', 'city', 'weather', 'shuffle', 'time'];
  for (let i = 0; i < 6; i++) {
    const key = group(unit, symbols[i], [
      ((i % 2) - 0.5) * 0.025,
      0.01,
      -0.024 + Math.floor(i / 2) * 0.026,
    ]);
    box(key, [0.022, 0.005, 0.022], [0, 0, 0], i === 5 ? p.bronze : p.graphite, 0.0025);
    const label = canvasTexture(96, 96, (ctx) => {
      ctx.strokeStyle = '#ebe2cf';
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      const line = (x1: number, y1: number, x2: number, y2: number) => {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      };
      if (i === 0 || i === 1) {
        for (let j = 0; j < 3; j++) line(20, 30 + j * 17, 76, 30 + j * 17 - i * 12);
      } else if (i === 2) {
        ctx.strokeRect(19, 39, 16, 37);
        ctx.strokeRect(38, 20, 22, 56);
        ctx.strokeRect(62, 47, 14, 29);
      } else if (i === 3) {
        ctx.beginPath();
        ctx.moveTo(47, 18);
        ctx.bezierCurveTo(2, 70, 45, 93, 65, 63);
        ctx.quadraticCurveTo(76, 52, 47, 18);
        ctx.stroke();
      } else if (i === 4) {
        ctx.beginPath();
        ctx.roundRect(20, 20, 56, 56, 8);
        ctx.stroke();
        ctx.fillStyle = '#ebe2cf';
        for (const [x, y] of [
          [34, 34],
          [48, 48],
          [62, 62],
        ]) {
          ctx.beginPath();
          ctx.arc(x, y, 4, 0, 2 * Math.PI);
          ctx.fill();
        }
      } else {
        ctx.beginPath();
        ctx.arc(48, 48, 21, 0, 2 * Math.PI);
        ctx.stroke();
        for (let j = 0; j < 8; j++)
          line(
            48 + 29 * Math.cos((j * Math.PI) / 4),
            48 + 29 * Math.sin((j * Math.PI) / 4),
            48 + 38 * Math.cos((j * Math.PI) / 4),
            48 + 38 * Math.sin((j * Math.PI) / 4),
          );
      }
    });
    const decal = mesh(
      key,
      new T.PlaneGeometry(0.015, 0.015),
      new T.MeshBasicMaterial({
        map: label,
        transparent: true,
        depthWrite: false,
        toneMapped: false,
      }),
      [0, 0.0027, 0],
    );
    decal.rotation.x = -Math.PI / 2;
    decal.castShadow = false;
    buttons.push(key);
  }
  tube(unit, [0, 0.008, 0.052], [0, 0.0086, 0.052], 0.002, luminous('#df9b55', 1));
  return { unit, body, buttons };
}

export function pottedPlant(parent: T.Object3D, p: Palette, position: XYZ) {
  const plant = group(parent, 'Plant', position);
  const pot = p.plaster.clone();
  pot.color.set('#935b42');
  pot.roughness = 0.82;
  mesh(
    plant,
    new T.LatheGeometry(
      [
        [0, 0],
        [0.043, 0],
        [0.057, 0.072],
        [0.052, 0.073],
        [0.049, 0.061],
        [0.034, 0.009],
        [0, 0.009],
      ].map(([x, y]) => new T.Vector2(x, y)),
      36,
    ),
    pot,
  );
  const soil = p.cork.clone();
  soil.color.set('#3a2a23');
  tube(plant, [0, 0.053, 0], [0, 0.063, 0], 0.049, soil);
  const rng = random(51);
  const leaves = Array.from(
    { length: 4 },
    (_, i) =>
      new T.MeshStandardMaterial({
        color: new T.Color().setHSL(0.23 + i * 0.018, 0.38, 0.18 + i * 0.033),
        roughness: 0.54,
        side: T.DoubleSide,
      }),
  );
  for (let i = 0; i < 20; i++) {
    const angle = i * 2.4,
      spread = 0.04 + rng() * 0.085,
      height = 0.08 + rng() * 0.14;
    const tip: XYZ = [Math.cos(angle) * spread, height, Math.sin(angle) * spread];
    const side = new T.Vector3(Math.sin(angle), 0, -Math.cos(angle)).multiplyScalar(
      0.022 + rng() * 0.01,
    );
    const center = new T.Vector3(...tip).multiplyScalar(0.56);
    center.y += 0.047;
    const stem: XYZ = [center.x * 0.53, center.y * 0.88, center.z * 0.53];
    cable(
      plant,
      [[0, 0.065, 0], [stem[0] * 0.57, stem[1] * 0.88, stem[2] * 0.57], stem],
      0.0016,
      leaves[0],
    );
    const vein = new T.QuadraticBezierCurve3(new T.Vector3(...stem), center, new T.Vector3(...tip));
    const verts: number[] = [],
      faces: number[] = [];
    for (let v = 0; v <= 8; v++) {
      const t = v / 8;
      const mid = vein.getPoint(t);
      const width = Math.sin(Math.PI * t) ** 0.82;
      for (const u of [-1, -0.5, 0, 0.5, 1]) {
        const point = mid.clone().addScaledVector(side, width * u);
        point.y -= Math.abs(u) ** 1.5 * width * 0.006;
        verts.push(...point.toArray());
      }
      if (!v) continue;
      for (let u = 0; u < 4; u++) {
        const k = (v - 1) * 5 + u;
        faces.push(k, k + 1, k + 5, k + 1, k + 6, k + 5);
      }
    }
    const geometry = new T.BufferGeometry().setAttribute(
      'position',
      new T.Float32BufferAttribute(verts, 3),
    );
    geometry.setIndex(faces);
    geometry.computeVertexNormals();
    mesh(plant, geometry, leaves[i % 4]);
  }
  return { plant, leaves };
}

export function deskObjects(parent: T.Object3D, p: Palette) {
  const cluster = group(parent, 'Desk keepsakes');
  const cream = surface('#b8ad93', 0.32);
  cream.normalMap = p.plaster.normalMap;
  cream.normalScale.set(0.38, 0.38);
  const interior = surface('#625140', 0.37);
  const cup = group(cluster, 'Glazed stoneware cup', [0.52, 0.753, 0.205]);
  const profile = [
    [0, 0],
    [0.026, 0],
    [0.036, 0.013],
    [0.04, 0.072],
    [0.039, 0.078],
    [0.036, 0.079],
    [0.034, 0.07],
    [0.031, 0.019],
    [0.024, 0.011],
    [0, 0.011],
  ];
  mesh(
    cup,
    new T.LatheGeometry(
      profile.map(([r, h]) => new T.Vector2(r, h)),
      40,
    ),
    cream,
  );
  const handle = new T.CubicBezierCurve3(
    new T.Vector3(0.038, 0.062, 0),
    new T.Vector3(0.076, 0.071, 0),
    new T.Vector3(0.073, 0.026, 0),
    new T.Vector3(0.0362, 0.025, 0),
  );
  mesh(cup, new T.TubeGeometry(handle, 40, 0.004, 12, false), cream).name =
    'Cup handle seated in outer wall';
  tube(cup, [0, 0.048, 0], [0, 0.05, 0], 0.033, interior);
  tube(cup, [0, -0.002, 0], [0, 0.002, 0], 0.054, p.cork);
  const pencil = surface('#977348', 0.5);
  tube(cluster, [-0.866, 0.754, 0.332], [-0.866, 0.754, 0.192], 0.0032, pencil);
  tube(cluster, [-0.866, 0.754, 0.192], [-0.866, 0.754, 0.179], 0.0032, p.paper, 0.0008);
  tube(cluster, [-0.866, 0.754, 0.179], [-0.866, 0.754, 0.174], 0.001, p.graphite, 0.0002);
  const vapor = new T.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { seconds: { value: 0 } },
    vertexShader: `
      varying vec2 coords;
      void main() {
        coords = uv;
        vec4 center = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        gl_Position = projectionMatrix * (center + vec4(position.xy, 0.0, 0.0));
      }`,
    fragmentShader: `
      uniform float seconds;
      varying vec2 coords;
      void main() {
        float y = coords.y;
        float t = seconds * 0.70;
        float x = (coords.x - 0.5) * 2.0;
        float center = y * (0.11 + sin(y * 7.0 - t * 1.5) * 0.22);
        float thickness = mix(0.13, 0.37, y);
        float nearWisp = (x - center) / thickness;
        float farWisp = (x - center - 0.11 - sin(y * 11.0 - t) * y * 0.34) / thickness;
        float ribbons = exp(-nearWisp * nearWisp * 2.0);
        ribbons *= 0.57 + 0.24 * sin(26.0 * y - t * 7.0 + x * 4.0);
        ribbons += 0.29 * exp(-farWisp * farWisp * 2.8);
        float fade = smoothstep(0.03, 0.19, y) * (1.0 - smoothstep(0.36, 1.0, y));
        gl_FragColor = vec4(0.84, 0.78, 0.67, ribbons * fade * 0.21);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
      `,
  });
  const steam = mesh(cup, new T.PlaneGeometry(0.13, 0.195), vapor, [0, 0.169, 0]);
  steam.name = 'Tea vapor';
  steam.castShadow = steam.receiveShadow = false;
  steam.raycast = () => {};
  return (seconds: number) => {
    vapor.uniforms.seconds.value = seconds;
  };
}
