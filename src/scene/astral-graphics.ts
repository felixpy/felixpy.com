import * as T from 'three';
import { box, canvasTexture, group, mesh, surface, tube, type XYZ } from './geometry';
import { blenderMesh } from './blender-mesh';
import { rogEye } from './rog-mark';
import type { Palette } from './materials';
import type { ProductDetail } from './product-detail';

const fanCenters = [-0.116, 0, 0.116];

function plate(outline: number[][], depth: number, holes: number[] = []) {
  const profile = new T.Shape(outline.map(([along, up]) => new T.Vector2(-up, along)));
  profile.closePath();
  for (const z of holes) {
    const cut = new T.Path();
    cut.absarc(0, z, 0.0558, 0, Math.PI * 2, true);
    profile.holes.push(cut);
  }
  const geometry = new T.ExtrudeGeometry(profile, {
    depth,
    bevelSize: 0.00055,
    bevelThickness: 0.00045,
    bevelSegments: 2,
    curveSegments: 32,
  });
  geometry.rotateX(Math.PI / 2);
  return geometry;
}

function axialFan(
  parent: T.Group,
  p: Palette,
  impeller: T.BufferGeometry,
  material: T.Material,
  medallion: T.Material,
  counterRotating = false,
) {
  if (counterRotating) parent.scale.x = -1;
  const rotor = group(parent, 'Fan rotor');
  mesh(rotor, impeller, material).name = 'Axial-tech cambered blades and rotating tip ring';
  tube(rotor, [0, 0, -0.0025], [0, 0, 0.006], 0.018, p.graphite, 0.0168);
  mesh(rotor, new T.TorusGeometry(0.0168, 0.00058, 5, 48), p.steel, [0, 0, 0.006]);
  const eye = mesh(rotor, new T.PlaneGeometry(0.026, 0.015), medallion, [0, 0, 0.00634]);
  eye.scale.x = counterRotating ? -1 : 1;
  eye.castShadow = false;
}

export function astralGraphics(
  unit: T.Group,
  p: Palette,
  aura: T.MeshStandardMaterial,
  details: ProductDetail,
  reflect: (material: T.MeshStandardMaterial) => void,
) {
  const position: XYZ = [0.004, -0.008, -0.1236];
  const gpu = group(unit, 'ROG Astral GeForce RTX 5090 · PCIe 5.0 slot', position);
  const fine = group(unit, 'ROG Astral · close inspection', position);
  details.close(fine);
  fine.rotation.copy(gpu.rotation);
  const chassis = surface('#373a3f', 0.39, 0.72);
  const milled = surface('#8b8784', 0.36, 0.74);
  const polymer = surface('#44464a', 0.38, 0.17);
  const impeller = blenderMesh('astral-impeller-shell');
  const mark = new T.MeshStandardMaterial({
    map: rogEye('lit'),
    color: '#bebbb5',
    roughness: 0.43,
    alphaTest: 0.4,
  });
  const perimeter = [
    [-0.177, 0.067],
    [-0.172, 0.073],
    [0.169, 0.073],
    [0.178, 0.065],
    [0.178, -0.065],
    [0.169, -0.073],
    [-0.17, -0.073],
    [-0.177, -0.067],
  ];
  const diecast: Record<string, T.Material> = {
    graphite: surface('#515257', 0.45, 0.66),
    black: surface('#292b2b', 0.65, 0.24),
    brass: surface('#a29462', 0.57, 0.36),
    steel: surface('#a5a6a4', 0.31, 0.77),
    satin: milled,
  };
  for (const material of [chassis, milled, polymer, diecast.graphite, diecast.steel])
    if (material instanceof T.MeshStandardMaterial) reflect(material);
  for (const [finish, material] of Object.entries(diecast)) {
    mesh(gpu, blenderMesh('astral-casting-' + finish), material).name =
      'Astral backplate, retention and thermal fittings · ' + finish;
  }
  box(gpu, [0.14, 0.00158, 0.201], [-0.0015, 0.022, -0.066], p.black, 0.0006);
  box(gpu, [0.006, 0.005, 0.333], [0.069, -0.026, 0], milled, 0.0014);
  for (const [start, end] of [
    [-0.1665, 0.0415],
    [0.0665, 0.1665],
  ]) {
    box(gpu, [0.006, 0.005, end - start], [-0.069, -0.026, (start + end) / 2], milled, 0.0014);
  }
  for (const z of [-0.162, -0.099, -0.028, 0.037, 0.16])
    box(gpu, [0.008, 0.048, 0.004], [-0.068, 0, z], chassis, 0.001);
  const backLabel = canvasTexture(520, 146, (ctx) => {
    ctx.fillStyle = '#bfc0c1';
    ctx.font = '600 34px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('A    S    T    R    A    L', 292, 85);
  });
  const backMark = mesh(
    gpu,
    new T.PlaneGeometry(0.091, 0.025),
    new T.MeshStandardMaterial({ map: backLabel, alphaTest: 0.34, roughness: 0.4 }),
    [0, 0.03675, 0.017],
  );
  backMark.rotation.order = 'YXZ';
  backMark.rotation.set(-Math.PI / 2, -Math.PI / 2, 0);
  backMark.castShadow = false;
  const sigil = mesh(gpu, new T.PlaneGeometry(0.011, 0.0065), mark, [0, 0.03685, -0.015]);
  sigil.rotation.copy(backMark.rotation);
  sigil.castShadow = false;
  const wordmark = canvasTexture(512, 72, (ctx) => {
    ctx.fillStyle = '#d2d3cf';
    ctx.font = 'bold 57px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('GEFORCE RTX', 256, 57);
  });
  const ioLegend = mesh(
    gpu,
    new T.PlaneGeometry(0.119, 0.0148),
    new T.MeshStandardMaterial({ map: wordmark, alphaTest: 0.4, roughness: 0.56 }),
    [0, 0.0368, -0.1685],
  );
  ioLegend.rotation.x = -Math.PI / 2;
  ioLegend.castShadow = false;
  const plugRelief = [
    [0.037, 0.073],
    [0.04, 0.0655],
    [0.068, 0.0655],
    [0.071, 0.073],
  ];
  const lowerRim = [...perimeter.slice(0, 2), ...plugRelief, ...perimeter.slice(2)];
  mesh(gpu, plate(lowerRim, 0.0042, fanCenters), chassis, [0, -0.0285, 0]);
  for (const [finish, metal] of Object.entries({
    steel: milled,
    shell: diecast.steel,
    enamel: chassis,
  }))
    mesh(gpu, blenderMesh('astral-intake-' + finish), metal).name =
      'Machined front fan shroud • ' + finish;
  for (let i = 0; i < fanCenters.length; i++) {
    const z = fanCenters[i];
    const assembly = group(gpu, 'Axial-tech intake ' + (i + 1), [0, -0.033, z]);
    assembly.rotation.x = Math.PI / 2;
    axialFan(assembly, p, impeller, polymer, mark, i === 1);
    const ring = mesh(
      assembly,
      new T.RingGeometry(0.0553, i === 2 ? 0.0612 : 0.0569, 96),
      i === 2 ? milled : p.steel,
      [0, 0, 0.0044],
    );
    ring.castShadow = false;
  }
  const reverse = group(gpu, 'Fourth pass-through fan', [0, 0.033, 0.116]);
  reverse.rotation.x = -Math.PI / 2;
  axialFan(reverse, p, impeller, polymer, mark);
  const machined = group(fine, 'Milled index marks and fin stack');
  const bezel = (text: string, startAngle: number) =>
    new T.MeshStandardMaterial({
      map: canvasTexture(1024, 1024, (ctx) => {
        ctx.fillStyle = '#353638';
        ctx.font = '600 16px Arial';
        ctx.textAlign = 'center';
        for (const [i, letter] of [...text].entries()) {
          const angle = startAngle + (i / (text.length - 1)) * Math.PI;
          ctx.save();
          ctx.translate(512 + 492 * Math.sin(angle), 512 - 492 * Math.cos(angle));
          ctx.rotate(angle);
          ctx.fillText(letter, 0, 5);
          ctx.restore();
        }
      }),
      roughness: 0.55,
      alphaTest: 0.28,
    });
  const bezelFace = new T.RingGeometry(0.0567, 0.0609, 96);
  const frontBezel = mesh(
    machined,
    bezelFace,
    bezel('25°07′37.0″N 121°28′13.6″E', -2.35),
    [0, -0.03776, 0.116],
  );
  frontBezel.rotation.x = Math.PI / 2;
  frontBezel.castShadow = false;
  const backBezel = mesh(
    machined,
    bezelFace,
    bezel('REPUBLIC OF GAMERS', -3.92),
    [0, 0.03748, 0.116],
  );
  backBezel.rotation.x = -Math.PI / 2;
  backBezel.castShadow = false;
  const finAlloy = surface('#41454a', 0.49, 0.68);
  const fins = new T.InstancedMesh(blenderMesh('astral-fin-satin'), finAlloy, 123);
  const inletFins = new T.InstancedMesh(blenderMesh('astral-fin-inlet-satin'), finAlloy, 11);
  let standardIndex = 0;
  let recessedIndex = 0;
  for (let i = 0; i < 134; i++) {
    const z = i < 66 ? -0.166 + i * 0.00243 : 0.004 + (i - 66) * 0.00236;
    const matrix = new T.Matrix4().makeTranslation(0, 0, z);
    if (z >= 0.041 && z <= 0.067) inletFins.setMatrixAt(recessedIndex++, matrix);
    else fins.setMatrixAt(standardIndex++, matrix);
  }
  fins.name = 'Folded cooling fins in two banks';
  inletFins.name = 'Locally relieved fins beneath the power receptacle';
  fins.receiveShadow = true;
  inletFins.receiveShadow = true;
  gpu.add(fins, inletFins);
  for (const z of [-0.14, -0.077, -0.012])
    box(gpu, [0.0025, 0.0024, 0.049], [-0.063, -0.0335, z], aura, 0.001);
  const legends = canvasTexture(1024, 122, (ctx) => {
    ctx.fillStyle = '#cccac6';
    ctx.font = '700 57px Arial';
    ctx.fillText('GEFORCE RTX', 18, 92);
    ctx.textAlign = 'right';
    ctx.font = 'italic 500 24px Arial';
    ctx.fillText('REPUBLIC OF GAMERS', 765, 86);
  });
  mesh(gpu, blenderMesh('astral-rail-graphite'), chassis).name = 'Split outer side rail';
  mesh(gpu, blenderMesh('astral-rail-opal'), aura).name = 'Interrupted Aura rail lens';
  const rim = group(gpu, 'Engraved outer edge rail', [-0.074, 0.019, -0.024]);
  rim.rotation.y = -Math.PI / 2;
  mesh(
    rim,
    new T.PlaneGeometry(0.252, 0.021),
    new T.MeshStandardMaterial({ map: legends, alphaTest: 0.38, roughness: 0.65 }),
  ).castShadow = false;
  const housing = new T.Group();
  housing.name = 'Diecast frame and thermal module';
  housing.add(...gpu.children.slice());
  housing.position.x = -0.0047;
  housing.scale.x = 0.936;
  gpu.add(housing);
  fine.position.x -= 0.0047;
  fine.scale.x = 0.936;
  const gold = surface('#cba260', 0.32, 0.78);
  for (const [finish, metal] of Object.entries({
    steel: p.steel,
    shell: milled,
    black: p.rubber,
    enamel: chassis,
    gold,
  }))
    mesh(gpu, blenderMesh('astral-io-' + finish), metal).name =
      'DisplayPort and HDMI retention plate • ' + finish;
  for (const [finish, metal] of Object.entries({ pcb: p.graphite, gold })) {
    const edge = mesh(gpu, blenderMesh('astral-pcie-' + finish), metal);
    edge.name = 'Keyed PCIe ×16 • ' + finish;
    if (finish === 'gold') details.enclosed(edge);
  }
  return gpu;
}
