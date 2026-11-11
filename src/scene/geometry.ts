import * as T from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export type XYZ = [number, number, number];
export type Material = T.Material;

export function random(seed: number) {
  return () => {
    seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

export function surface(color: T.ColorRepresentation, roughness = 0.62, metalness = 0) {
  return new T.MeshStandardMaterial({ color, roughness, metalness });
}

export function luminous(color: T.ColorRepresentation, intensity = 1) {
  return new T.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: intensity,
    roughness: 0.38,
  });
}

const boxes = new Map<string, T.BufferGeometry>();
export function box(
  parent: T.Object3D,
  size: XYZ,
  position: XYZ,
  material: Material | Material[],
  bevel = 0,
) {
  const key = [...size, bevel].join(',');
  let geometry = boxes.get(key);
  if (!geometry) {
    geometry = bevel
      ? new RoundedBoxGeometry(...size, 2, Math.min(bevel, ...size.map((n) => n * 0.49)))
      : new T.BoxGeometry(...size);
    boxes.set(key, geometry);
  }
  const object = new T.Mesh(geometry, material);
  object.position.set(...position);
  object.castShadow = object.receiveShadow = true;
  parent.add(object);
  return object;
}

export function mesh(
  parent: T.Object3D,
  geometry: T.BufferGeometry,
  material: Material,
  position: XYZ = [0, 0, 0],
) {
  const object = new T.Mesh(geometry, material);
  object.position.set(...position);
  object.castShadow = object.receiveShadow = true;
  parent.add(object);
  return object;
}

export function group(parent: T.Object3D, name: string, position: XYZ = [0, 0, 0]) {
  const object = new T.Group();
  object.name = name;
  object.position.set(...position);
  parent.add(object);
  return object;
}

export function tube(
  parent: T.Object3D,
  a: XYZ,
  b: XYZ,
  radius: number,
  material: Material,
  radiusB = radius,
) {
  const start = new T.Vector3(...a);
  const end = new T.Vector3(...b);
  const delta = end.clone().sub(start);
  const object = mesh(
    parent,
    new T.CylinderGeometry(radiusB, radius, delta.length(), 18),
    material,
  );
  object.position.copy(start.addScaledVector(delta, 0.5));
  object.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), delta.normalize());
  return object;
}

export function cable(parent: T.Object3D, points: XYZ[], radius: number, material: Material) {
  const curve = new T.CatmullRomCurve3(points.map((point) => new T.Vector3(...point)));
  return mesh(parent, new T.TubeGeometry(curve, 24, radius, 8, false), material);
}

export function beam(
  parent: T.Object3D,
  a: XYZ,
  b: XYZ,
  width: number,
  depth: number,
  material: Material,
) {
  const start = new T.Vector3(...a);
  const delta = new T.Vector3(...b).sub(start);
  const midpoint = start.addScaledVector(delta, 0.5);
  const object = box(
    parent,
    [width, delta.length(), depth],
    midpoint.toArray(),
    material,
    width * 0.17,
  );
  object.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), delta.normalize());
  return object;
}

export function canvasTexture(
  width: number,
  height: number,
  paint: (ctx: CanvasRenderingContext2D) => void,
) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  paint(canvas.getContext('2d')!);
  const texture = new T.CanvasTexture(canvas);
  texture.colorSpace = T.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

export function print(
  parent: T.Object3D,
  width: number,
  height: number,
  position: XYZ,
  texture: T.Texture,
  geometry = new T.PlaneGeometry(width, height),
) {
  return mesh(
    parent,
    geometry,
    new T.MeshStandardMaterial({
      map: texture,
      roughness: 0.83,
    }),
    position,
  );
}

export function paperGeometry(width: number, height: number, scale = 1, yOffset = 0, back = false) {
  const geometry = new T.PlaneGeometry(width * scale, height * scale, 16, 16);
  const points = geometry.attributes.position;
  const side = back ? -1 : 1;
  for (let i = 0; i < points.count; i++) {
    const u = 0.5 + (side * points.getX(i)) / width;
    const v = 0.5 + (points.getY(i) + yOffset) / height;
    const curl = Math.max(0, (u - 0.55) / 0.45) ** 2 * Math.max(0, (0.53 - v) / 0.53) ** 2;
    const bow = Math.sin(u * Math.PI) * Math.sin(v * Math.PI);
    points.setZ(i, side * (0.007 * curl + 0.0012 * bow));
  }
  geometry.computeVertexNormals();
  return geometry;
}

export function textTexture(
  title: string,
  subtitle: string,
  background: string,
  foreground = '#e6cfaa',
) {
  return canvasTexture(512, 256, (ctx) => {
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, 512, 256);
    ctx.strokeStyle = foreground + '70';
    ctx.strokeRect(15, 15, 482, 226);
    ctx.font = '600 38px system-ui, sans-serif';
    ctx.fillStyle = foreground;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(title, 256, 112, 448);
    ctx.font = '20px system-ui, sans-serif';
    ctx.fillText(subtitle, 256, 167, 442);
  });
}
