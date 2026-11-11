import * as T from 'three';
import { box, group, mesh, surface, tube } from './geometry';
import { display } from './hardware';
import type { Palette } from './materials';

export const chairPosition = { x: display.x, z: 0.96 };

function upholstery(
  parent: T.Object3D,
  outline: T.Shape,
  fabric: T.Material,
  thread: T.Material,
  stitch: T.Material,
  depth: number,
  bevel: number,
  crown: number,
  profile: (x: number, y: number) => number,
) {
  const outlinePoints = outline.getSpacedPoints(80).slice(0, -1);
  if (T.ShapeUtils.isClockWise(outlinePoints)) outlinePoints.reverse();
  const rows: Array<[number, number]> = [];
  for (let i = 1; i <= 8; i++) rows.push([i * 0.1125, -bevel]);
  rows.push(
    [0.955, -bevel * 0.88],
    [0.997, -bevel * 0.57],
    [1.033, -bevel * 0.12],
    [1.042, depth * 0.48],
    [1.034, depth * 0.92],
    [1.011, depth + bevel * 0.42],
    [0.966, depth + bevel * 0.81],
    [0.9, depth + bevel],
  );
  for (let i = 7; i >= 1; i--) {
    const radius = i * 0.1125;
    rows.push([radius, depth + bevel + crown * (1 - radius ** 2)]);
  }
  const positions: number[] = [],
    uv: number[] = [],
    indices: number[] = [];
  function vertex(x: number, y: number, z: number) {
    positions.push(x, y, z + profile(x, y));
    uv.push(0.5 + 2.7 * x + z * 0.64, 0.5 + 2.7 * y + z * 0.53);
  }
  const columns = outlinePoints.length;
  for (const [row, [radius, z]] of rows.entries()) {
    for (const [col, point] of outlinePoints.entries()) {
      vertex(point.x * radius, point.y * radius, z);
      if (row === 0) continue;
      const next = (col + 1) % columns;
      const a = (row - 1) * columns + col,
        b = (row - 1) * columns + next;
      const c = row * columns + col,
        d = row * columns + next;
      indices.push(a, b, c, b, d, c);
    }
  }
  const backCenter = positions.length / 3;
  vertex(0, 0, -bevel);
  const frontCenter = positions.length / 3;
  vertex(0, 0, depth + bevel + crown);
  for (let col = 0; col < columns; col++) {
    const next = (col + 1) % columns,
      last = (rows.length - 1) * columns;
    indices.push(backCenter, next, col, frontCenter, last + col, last + next);
  }
  const cushion = new T.BufferGeometry()
    .setAttribute('position', new T.Float32BufferAttribute(positions, 3))
    .setAttribute('uv', new T.Float32BufferAttribute(uv, 2))
    .setIndex(indices);
  cushion.computeVertexNormals();
  // Give the sewn side band a continuous unwrap instead of stretching the cap artwork.
  const upholstered = cushion.toNonIndexed();
  const sideStart = 8,
    sideEnd = 14;
  const sideUV = new Map([[sideStart, 0]]);
  for (let row = sideStart + 1; row <= sideEnd; row++) {
    const [radius, z] = rows[row],
      [prior, priorZ] = rows[row - 1];
    sideUV.set(row, sideUV.get(row - 1)! + Math.hypot((radius - prior) * 0.19, z - priorZ));
  }
  const perimeter = outline.getLength();
  for (let triangle = 0; triangle < indices.length; triangle += 3) {
    const corners = indices.slice(triangle, triangle + 3);
    const rings = corners.map((index) => Math.floor(index / columns));
    if (rings.some((row) => row < sideStart || row > sideEnd)) continue;
    const columnsInFace = corners.map((index) => index % columns);
    const wraps = columnsInFace.includes(0) && columnsInFace.includes(columns - 1);
    for (const [i, col] of columnsInFace.entries()) {
      const along = wraps && col === 0 ? columns : col;
      upholstered.attributes.uv.setXY(
        triangle + i,
        (2.7 * perimeter * along) / columns,
        2.7 * sideUV.get(rings[i])!,
      );
    }
  }
  cushion.dispose();
  mesh(parent, upholstered, fabric);
  const seam = outlinePoints.map(({ x, y }) => {
    const sx = x * 1.045,
      sy = y * 1.045;
    return new T.Vector3(sx, sy, depth * 0.48 + profile(sx, sy));
  });
  const piping = new T.CatmullRomCurve3(seam, true);
  mesh(parent, new T.TubeGeometry(piping, 144, 0.00095, 8, true), thread);
  const needle = group(parent, 'Topstitch along the welt');
  for (let i = 0; i < 78; i++) {
    const start = piping.getPointAt(i / 78),
      end = piping.getPointAt((i + 0.27) / 78);
    start.z += 0.0006;
    end.z += 0.0006;
    tube(needle, start.toArray(), end.toArray(), 0.00023, stitch);
  }
}

export function taskChair(parent: T.Object3D, p: Palette) {
  const chair = group(parent, 'Desk task chair', [chairPosition.x, 0, chairPosition.z]);
  const thread = surface('#454044', 0.86);
  const stitch = surface('#6a625c', 0.92);
  const casing = p.black.clone();
  casing.color.set('#2b2c2b');
  const frame = p.graphite.clone();
  frame.color.set('#414242');
  frame.roughness = 0.51;

  const seat = group(chair, 'Shaped upholstered seat', [0, 0.433, 0]);
  seat.rotation.x = -Math.PI / 2;
  const seatOutline = new T.Shape();
  seatOutline.moveTo(-0.135, -0.197);
  seatOutline.bezierCurveTo(-0.172, -0.197, -0.195, -0.153, -0.201, -0.079);
  seatOutline.bezierCurveTo(-0.218, 0.037, -0.224, 0.129, -0.186, 0.171);
  seatOutline.bezierCurveTo(-0.113, 0.208, 0.113, 0.208, 0.186, 0.171);
  seatOutline.bezierCurveTo(0.224, 0.129, 0.218, 0.037, 0.201, -0.079);
  seatOutline.bezierCurveTo(0.195, -0.153, 0.172, -0.197, 0.135, -0.197);
  seatOutline.closePath();
  upholstery(
    seat,
    seatOutline,
    p.upholstery,
    thread,
    stitch,
    0.043,
    0.017,
    -0.014,
    (x, y) => 0.018 * (x / 0.22) ** 2 + y * 0.024 - 0.019 * Math.max(0, (y - 0.1) / 0.12) ** 2,
  );

  const back = group(chair, 'Curved upholstered lumbar support', [0, 0.743, 0.227]);
  back.rotation.set(-0.095, Math.PI, 0, 'YXZ');
  const backOutline = new T.Shape();
  backOutline.moveTo(-0.114, -0.153);
  backOutline.bezierCurveTo(-0.176, -0.152, -0.189, -0.127, -0.19, -0.045);
  backOutline.bezierCurveTo(-0.209, 0.104, -0.182, 0.163, -0.114, 0.175);
  backOutline.bezierCurveTo(-0.045, 0.189, 0.089, 0.188, 0.148, 0.165);
  backOutline.bezierCurveTo(0.188, 0.153, 0.208, 0.105, 0.195, -0.05);
  backOutline.bezierCurveTo(0.189, -0.133, 0.173, -0.151, 0.113, -0.153);
  backOutline.closePath();
  upholstery(
    back,
    backOutline,
    p.upholstery,
    thread,
    stitch,
    0.028,
    0.014,
    0.009,
    (x, y) => 0.027 * (x / 0.21) ** 2 + 0.009 * Math.cos((y + 0.1) * 10),
  );

  const underseat = group(chair, 'Seat pan, lift socket and lever housing');
  box(underseat, [0.3, 0.011, 0.276], [0, 0.414, 0.021], casing, 0.005);
  box(underseat, [0.202, 0.012, 0.223], [0, 0.403, 0.028], frame, 0.005);
  box(underseat, [0.123, 0.032, 0.129], [0, 0.382, 0.017], casing, 0.009);
  tube(underseat, [0, 0.356, 0.017], [0, 0.373, 0.017], 0.027, frame);
  for (const x of [-0.074, 0.074])
    for (const z of [-0.041, 0.097]) {
      tube(underseat, [x, 0.395, z], [x, 0.399, z], 0.0041, p.steel);
    }
  const armPad = p.rubber.clone();
  armPad.color.set('#3b3836');
  armPad.roughness = 0.82;
  const armCarrier = new T.Shape();
  armCarrier.moveTo(0.115, 0.404);
  armCarrier.lineTo(0.196, 0.404);
  armCarrier.bezierCurveTo(0.218, 0.404, 0.233, 0.42, 0.235, 0.453);
  armCarrier.lineTo(0.249, 0.625);
  armCarrier.lineTo(0.275, 0.625);
  armCarrier.lineTo(0.262, 0.45);
  armCarrier.bezierCurveTo(0.259, 0.397, 0.239, 0.38, 0.2, 0.38);
  armCarrier.lineTo(0.115, 0.38);
  armCarrier.closePath();
  const armSupport = new T.ExtrudeGeometry(armCarrier, {
    depth: 0.029,
    bevelEnabled: true,
    bevelThickness: 0.004,
    bevelSize: 0.004,
    bevelSegments: 3,
    curveSegments: 12,
  });
  for (const side of [-1, 1]) {
    const armrest = group(chair, side < 0 ? 'Left padded armrest' : 'Right padded armrest');
    armrest.scale.x = side;
    box(armrest, [0.083, 0.016, 0.073], [0.137, 0.402, 0.047], frame, 0.004);
    mesh(armrest, armSupport, frame, [0, 0, 0.031]);
    box(armrest, [0.047, 0.032, 0.039], [0.258, 0.624, 0.046], casing, 0.006);
    box(armrest, [0.051, 0.013, 0.208], [0.255, 0.645, 0.021], casing, 0.005);
    box(armrest, [0.061, 0.023, 0.22], [0.254, 0.659, 0.021], armPad, 0.01);
    for (const z of [0.02, 0.073]) {
      tube(armrest, [0.136, 0.391, z], [0.136, 0.395, z], 0.0041, p.steel);
    }
  }
  tube(underseat, [0, 0.344, -0.059], [0, 0.384, -0.059], 0.008, p.steel);
  tube(underseat, [0, 0.337, -0.059], [0, 0.351, -0.059], 0.018, casing);
  const carrier = new T.Shape();
  carrier.moveTo(0.048, 0.393);
  carrier.lineTo(0.171, 0.393);
  carrier.bezierCurveTo(0.227, 0.393, 0.26, 0.421, 0.26, 0.477);
  carrier.lineTo(0.259, 0.658);
  carrier.lineTo(0.235, 0.658);
  carrier.lineTo(0.235, 0.48);
  carrier.bezierCurveTo(0.235, 0.435, 0.219, 0.417, 0.171, 0.417);
  carrier.lineTo(0.048, 0.417);
  carrier.closePath();
  const spine = mesh(
    chair,
    new T.ExtrudeGeometry(carrier, {
      depth: 0.043,
      bevelEnabled: true,
      bevelThickness: 0.003,
      bevelSize: 0.003,
      bevelSegments: 3,
      curveSegments: 16,
    }),
    frame,
    [0.0215, 0, 0],
  );
  spine.rotation.y = -Math.PI / 2;
  const yoke = new T.Shape();
  yoke.moveTo(-0.024, 0.61);
  yoke.lineTo(-0.024, 0.643);
  yoke.quadraticCurveTo(-0.024, 0.666, -0.044, 0.686);
  yoke.lineTo(-0.142, 0.773);
  yoke.quadraticCurveTo(-0.16, 0.79, -0.147, 0.804);
  yoke.quadraticCurveTo(-0.133, 0.818, -0.118, 0.805);
  yoke.lineTo(-0.039, 0.727);
  yoke.quadraticCurveTo(0, 0.684, 0.039, 0.727);
  yoke.lineTo(0.118, 0.805);
  yoke.quadraticCurveTo(0.133, 0.818, 0.147, 0.804);
  yoke.quadraticCurveTo(0.16, 0.79, 0.142, 0.773);
  yoke.lineTo(0.044, 0.686);
  yoke.quadraticCurveTo(0.024, 0.666, 0.024, 0.643);
  yoke.lineTo(0.024, 0.61);
  yoke.closePath();
  mesh(
    chair,
    new T.ExtrudeGeometry(yoke, {
      depth: 0.018,
      bevelEnabled: true,
      bevelThickness: 0.003,
      bevelSize: 0.003,
      bevelSegments: 4,
      curveSegments: 12,
    }),
    frame,
    [0, 0, 0.237],
  );
  box(chair, [0.04, 0.046, 0.002], [0, 0.635, 0.259], frame, 0.0009);
  for (const x of [-0.011, 0.011]) {
    tube(chair, [x, 0.631, 0.259], [x, 0.631, 0.261], 0.0037, casing);
    box(chair, [0.0043, 0.00065, 0.0003], [x, 0.631, 0.2611], p.black).rotation.z =
      x < 0 ? 0.47 : -0.41;
  }
  for (const sign of [-1, 1]) {
    const x = sign * 0.132;
    tube(chair, [x, 0.791, 0.225], [x, 0.791, 0.244], 0.012, casing);
    tube(chair, [x, 0.791, 0.254], [x, 0.791, 0.259], 0.006, casing);
    box(chair, [0.0067, 0.001, 0.001], [x, 0.791, 0.259], p.black).rotation.z = 0.54;
  }
  tube(chair, [0.05, 0.383, -0.021], [0.075, 0.383, -0.021], 0.01, casing);
  tube(chair, [0.069, 0.383, -0.023], [0.192, 0.376, -0.039], 0.0045, p.steel);
  box(chair, [0.065, 0.016, 0.024], [0.214, 0.373, -0.04], casing, 0.006);
  tube(chair, [0, 0.093, 0.017], [0, 0.286, 0.017], 0.033, casing);
  tube(chair, [0, 0.285, 0.017], [0, 0.358, 0.017], 0.017, p.steel);
  tube(chair, [0, 0.095, 0.017], [0, 0.126, 0.017], 0.046, frame);
  const spokeOutline = new T.Shape();
  spokeOutline.moveTo(-0.025, -0.027);
  spokeOutline.lineTo(-0.019, -0.121);
  spokeOutline.lineTo(-0.012, -0.249);
  spokeOutline.quadraticCurveTo(0, -0.266, 0.012, -0.249);
  spokeOutline.lineTo(0.019, -0.121);
  spokeOutline.lineTo(0.025, -0.027);
  spokeOutline.closePath();
  const spoke = new T.ExtrudeGeometry(spokeOutline, {
    depth: 0.027,
    bevelEnabled: true,
    bevelThickness: 0.004,
    bevelSize: 0.004,
    bevelSegments: 3,
  });
  const tire = p.rubber.clone();
  tire.color.set('#252423');
  const wheelSide = surface('#42403d', 0.62);
  const hub = surface('#5e5b55', 0.58, 0.29);
  for (let i = 0; i < 5; i++) {
    const arm = group(chair, 'Cast leg with twin caster', [0, 0, 0.017]);
    arm.rotation.y = (i * Math.PI * 2) / 5;
    mesh(arm, spoke, frame, [0, 0.07, 0]).rotation.x = -Math.PI / 2;
    tube(arm, [0, 0.06, 0.244], [0, 0.078, 0.244], 0.0155, casing);
    tube(arm, [0, 0.057, 0.244], [0, 0.062, 0.244], 0.012, p.steel);
    box(arm, [0.014, 0.036, 0.032], [0, 0.045, 0.251], casing, 0.006).rotation.x = -0.22;
    box(arm, [0.025, 0.011, 0.033], [0, 0.052, 0.251], casing, 0.005);
    tube(arm, [-0.012, 0.028, 0.254], [0.012, 0.028, 0.254], 0.0045, hub);
    for (const side of [-1, 1]) {
      tube(arm, [side * 0.0093, 0.028, 0.254], [side * 0.021, 0.028, 0.254], 0.023, tire);
      mesh(arm, new T.TorusGeometry(0.0208, 0.0011, 7, 32), wheelSide, [
        side * 0.0206,
        0.028,
        0.254,
      ]).rotation.y = Math.PI / 2;
      tube(arm, [side * 0.021, 0.028, 0.254], [side * 0.022, 0.028, 0.254], 0.0165, wheelSide);
      tube(arm, [side * 0.022, 0.028, 0.254], [side * 0.023, 0.028, 0.254], 0.005, hub);
    }
  }
  return chair;
}
