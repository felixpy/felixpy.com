import * as T from 'three';
import shellOutline from './nikon-z8-outline.json';
import gripSections from './nikon-z8-grip.json';
import finderSections from './nikon-z8-finder.json';
import { box, cable, group, mesh, surface, type XYZ } from './geometry';
import type { Palette } from './materials';

type Outline = [number, number][];
type Section = {
  height: number;
  scale: number;
  fingerwell?: number;
  slope?: number;
  brow?: number;
  rearScale?: number;
};

function mouldedShell(outline: Outline, sections: Section[], closed = true) {
  const ring = new T.CatmullRomCurve3(
    outline.map(([x, z]) => new T.Vector3(x, 0, z)),
    true,
    'catmullrom',
    0.45,
  );
  const points = ring.getPoints(outline.length * 4);
  const positions: number[] = [],
    uv: number[] = [],
    indices: number[] = [];
  const distances = points.map((_, i) => (i ? points[i].distanceTo(points[i - 1]) : 0));
  for (let i = 1; i < distances.length; i++) distances[i] += distances[i - 1];
  for (const section of sections) {
    for (const [i, point] of points.entries()) {
      const grip =
        T.MathUtils.smoothstep(-point.x, 35, 55) * T.MathUtils.smoothstep(point.z, 4, 34);
      const belly = Math.sin(Math.PI * T.MathUtils.clamp((section.height + 48) / 72, 0, 1));
      const cheek =
        T.MathUtils.smoothstep(-point.x, 55, 72) * T.MathUtils.smoothstep(point.z, -8, 24);
      const scale = T.MathUtils.lerp(
        section.scale,
        section.rearScale ?? section.scale,
        T.MathUtils.smoothstep(-point.z, 0, 25),
      );
      const x = point.x * scale - belly * cheek * 1.8;
      const z =
        point.z * scale +
        grip * (section.fingerwell ?? 0) -
        T.MathUtils.smoothstep(point.z, -3, 23) * (section.brow ?? 0);
      const y = section.height - (section.slope ?? 0) * T.MathUtils.clamp((z - 1) / 40, 0, 1);
      positions.push(x * 0.001, y * 0.001, z * 0.001);
      uv.push(distances[i] / 116, y / 116 + 0.55);
    }
  }
  const stride = points.length;
  for (let row = 0; row < sections.length - 1; row++)
    for (let column = 0; column < stride - 1; column++) {
      const i = row * stride + column;
      indices.push(i, i + 1, i + stride, i + 1, i + stride + 1, i + stride);
    }
  if (closed) {
    for (const row of [0, sections.length - 1]) {
      const start = positions.length / 3;
      const boundary: T.Vector2[] = [];
      for (let column = 0; column < stride - 1; column++) {
        const offset = (row * stride + column) * 3;
        const [x, y, z] = positions.slice(offset, offset + 3);
        positions.push(x, y, z);
        uv.push(x * 8 + 0.5, z * 8 + 0.5);
        boundary.push(new T.Vector2(x, z));
      }
      for (const [a, b, c] of T.ShapeUtils.triangulateShape(boundary, []))
        indices.push(start + a, start + (row ? c : b), start + (row ? b : c));
    }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

export function nikonBody(camera: T.Object3D, p: Palette) {
  const shell = group(camera, 'Sealed body, grip overmould and viewfinder housing');
  const casting = p.black.clone();
  casting.color.set('#323335');
  casting.roughness = 0.52;
  casting.metalness = 0.16;
  casting.normalMap = casting.normalMap!.clone();
  casting.normalMap.wrapS = casting.normalMap.wrapT = T.RepeatWrapping;
  casting.normalMap.repeat.set(4, 4);
  casting.normalScale.set(0.23, 0.23);
  const outline = shellOutline as Outline;
  const grip = p.cameraGrip.clone();
  for (const key of ['map', 'normalMap'] as const) {
    const texture = grip[key]!.clone();
    texture.wrapS = texture.wrapT = T.RepeatWrapping;
    grip[key] = texture;
  }
  grip.roughness = 0.73;
  const closedGrip = group(shell, 'Z8 closed card door and overmould');
  const skin = mesh(closedGrip, mouldedShell(outline, gripSections, false), grip);
  const skinProbe = new T.Mesh(skin.geometry, grip);
  const ray = new T.Raycaster();
  const sidePoint = (y: number, z: number, lift: number): XYZ => {
    ray.set(new T.Vector3(-0.09, y, z), new T.Vector3(1, 0, 0));
    const hit = ray.intersectObject(skinProbe, false)[0];
    return [(hit?.point.x ?? -0.071) - lift, y, z];
  };
  const seam = surface('#1c1d1e', 0.79);
  cable(
    closedGrip,
    [
      [-0.041, -0.026],
      [-0.034, -0.024],
      [-0.033, -0.019],
      [-0.033, -0.009],
      [-0.032, -0.002],
      [-0.029, 0],
      [-0.002, 0],
      [0.019, -0.001],
      [0.022, -0.005],
    ].map(([y, z]) => sidePoint(y, z, 0.0002)),
    0.00032,
    seam,
  );
  const hinge = box(
    closedGrip,
    [0.0011, 0.039, 0.0035],
    sidePoint(-0.005, -0.0022, 0.00048),
    casting,
    0.0005,
  );
  hinge.rotation.x = 0.012;
  mesh(
    shell,
    mouldedShell(outline, [
      { height: 23.45, scale: 0.997, fingerwell: 2.5, slope: 4.0 },
      { height: 24.6, scale: 1, fingerwell: 3.2, slope: 4.3 },
      { height: 27.4, scale: 1.002, fingerwell: 3.2, slope: 5.2 },
      { height: 32.9, scale: 0.999, fingerwell: 2.5, slope: 7.3 },
      { height: 37.5, scale: 0.986, fingerwell: 1.0, slope: 10.4 },
      { height: 40.0, scale: 0.973, fingerwell: -0.5, slope: 12.0 },
      { height: 41.8, scale: 0.947, fingerwell: -2, slope: 13.6 },
      { height: 42.45, scale: 0.907, fingerwell: -2.7, slope: 14.5 },
    ]),
    casting,
  );
  cable(
    shell,
    [
      [0.022, -0.001],
      [0.0205, 0.004],
      [0.0168, 0.01],
      [0.0158, 0.015],
      [0.0169, 0.023],
      [0.0176, 0.03],
      [0.0174, 0.035],
    ].map(([y, z]) => sidePoint(y, z, 0.00015)),
    0.0009,
    surface('#982635', 0.52),
  );
  const cheek: Outline = [
    [-17, 4],
    [-16, 18],
    [-13, 24],
    [-8, 26.5],
    [2, 26.9],
    [10, 24.5],
    [15, 19],
    [17.3, 8],
    [19, -4],
    [17, -12],
    [12, -16],
    [4, -18],
    [-6, -18],
    [-13, -14],
    [-17, -6],
  ];
  const shutterHousing = mouldedShell(cheek, [
    { height: 28.8, scale: 0.95 },
    { height: 29.7, scale: 0.99 },
    { height: 32, scale: 1 },
    { height: 39, scale: 0.998 },
    { height: 42, scale: 0.955 },
    { height: 43.8, scale: 0.885 },
    { height: 44.6, scale: 0.79 },
  ]);
  const vertices = shutterHousing.attributes.position;
  for (let i = 0; i < vertices.count; i++)
    vertices.setY(i, vertices.getY(i) - 0.399 * (vertices.getZ(i) + 0.017));
  shutterHousing.computeVertexNormals();
  mesh(shell, shutterHousing, casting, [-0.0538, 0, 0.017]);
  const finder = group(camera, 'Sloped finder crown', [0.016, 0, 0]);
  const hood: Outline = [
    [-30, 11],
    [-28, 21],
    [-24, 25],
    [0, 26.5],
    [24, 25],
    [28, 21],
    [30, 11],
    [27, -15],
    [22, -27],
    [16, -30],
    [-16, -30],
    [-22, -27],
    [-27, -15],
  ];
  mesh(finder, mouldedShell(hood, finderSections), casting);
  return { casting, closedGrip };
}
