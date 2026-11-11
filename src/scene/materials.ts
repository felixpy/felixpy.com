import * as T from 'three';
import { canvasTexture, random, surface } from './geometry';

function noiseField(seed: number, size = 128) {
  const rng = random(seed);
  const values = Float32Array.from({ length: size * size }, () => rng());
  const at = (x: number, y: number) => values[(x & (size - 1)) + (y & (size - 1)) * size];
  return (x: number, y: number) => {
    const i = Math.floor(x);
    const j = Math.floor(y);
    const u = x - i;
    const v = y - j;
    const s = u * u * (3 - 2 * u);
    const t = v * v * (3 - 2 * v);
    return T.MathUtils.lerp(
      T.MathUtils.lerp(at(i, j), at(i + 1, j), s),
      T.MathUtils.lerp(at(i, j + 1), at(i + 1, j + 1), s),
      t,
    );
  };
}

function raster(size: number, pixel: (u: number, v: number) => [number, number, number]) {
  return canvasTexture(size, size, (ctx) => {
    const data = ctx.createImageData(size, size);
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const offset = (y * size + x) * 4;
        const [r, g, b] = pixel(x / size, y / size);
        data.data.set([r, g, b, 255], offset);
      }
    }
    ctx.putImageData(data, 0, 0);
  });
}

function microNormal(size: number, height: (u: number, v: number) => number, strength: number) {
  const grid = Float32Array.from({ length: size * size }, (_, i) =>
    height((i % size) / size, Math.floor(i / size) / size),
  );
  const at = (x: number, y: number) => grid[((x + size) % size) + ((y + size) % size) * size];
  const texture = raster(size, (u, v) => {
    const x = Math.round(u * size),
      y = Math.round(v * size);
    const nx = (at(x - 1, y) - at(x + 1, y)) * strength;
    const ny = (at(x, y + 1) - at(x, y - 1)) * strength;
    const reciprocal = 1 / Math.hypot(nx, ny, 1);
    return [128 + nx * reciprocal * 127, 128 + ny * reciprocal * 127, 128 + reciprocal * 127];
  });
  texture.colorSpace = T.NoColorSpace;
  texture.wrapS = texture.wrapT = T.RepeatWrapping;
  return texture;
}

function walnutFinishes(albedo: T.Texture) {
  const noise = noiseField(17);
  const normalMap = microNormal(
    512,
    (u, v) => {
      const drift = noise(u * 2, v * 9) * 3;
      return noise(u * 6, v * 94 + drift) ** 3;
    },
    0.18,
  );
  const roughnessMap = raster(128, (u, v) => {
    const level = 139 + noise(u * 2, v * 19) * 31;
    return [level, level, level];
  });
  roughnessMap.colorSpace = T.NoColorSpace;
  const wood = new T.MeshStandardMaterial({ map: albedo, normalMap, roughnessMap, roughness: 1 });
  const woodDark = wood.clone();
  woodDark.color.set('#dfd9d4');
  const woodVertical = wood.clone();
  for (const key of ['map', 'normalMap', 'roughnessMap'] as const) {
    const texture = wood[key]!.clone();
    texture.center.set(0.5, 0.5);
    texture.rotation = Math.PI / 2;
    woodVertical[key] = texture;
  }
  return { wood, woodDark, woodVertical };
}

function mineralPaint(map: T.Texture) {
  const noise = noiseField(122);
  map.wrapS = map.wrapT = T.MirroredRepeatWrapping;
  const normalMap = microNormal(
    512,
    (u, v) =>
      noise(u * 113, v * 113) * 0.64 + noise(u * 38, v * 47) * 0.3 + noise(u * 6, v * 16) * 0.06,
    0.42,
  );
  normalMap.wrapS = normalMap.wrapT = T.MirroredRepeatWrapping;
  const roughnessMap = raster(256, (u, v) => {
    const level = 195 + noise(u * 21, v * 27) * 31 + noise(u * 72, v * 72) * 11;
    return [level, level, level];
  });
  roughnessMap.colorSpace = T.NoColorSpace;
  roughnessMap.wrapS = roughnessMap.wrapT = T.MirroredRepeatWrapping;
  return new T.MeshStandardMaterial({
    map,
    color: '#d9d1c3',
    roughness: 1,
    roughnessMap,
    normalMap,
    normalScale: new T.Vector2(1.05, 1.05),
  });
}

export function plasterUV(geometry: T.BufferGeometry, origin: T.Vector3) {
  const { position, normal, uv } = geometry.attributes;
  const tilesPerMeter = 1.22;
  for (let i = 0; i < position.count; i++) {
    const x = position.getX(i) + origin.x;
    const y = position.getY(i) + origin.y;
    const z = position.getZ(i) + origin.z;
    const side = Math.abs(normal.getX(i)) > 0.5;
    const horizontal = Math.abs(normal.getY(i)) > 0.5;
    uv.setXY(i, (side ? z : x) * tilesPerMeter, (horizontal ? z : y) * tilesPerMeter);
  }
}

function linen(map: T.Texture) {
  const noise = noiseField(922);
  map.wrapS = map.wrapT = T.RepeatWrapping;
  const thread = (u: number, v: number) =>
    (Math.cos(u * Math.PI * 256) + Math.cos(v * Math.PI * 180)) * 0.35 +
    noise(u * 75, v * 92) * 0.25;
  return new T.MeshStandardMaterial({
    map,
    roughness: 0.91,
    normalMap: microNormal(512, thread, 0.12),
  });
}

function marble() {
  const noise = noiseField(86);
  const map = raster(512, (u, v) => {
    const field = Math.sin(u * 11 + v * 12 + noise(u * 5, v * 5) * 3 + noise(u * 19, v * 19) * 0.4);
    const vein = 12 * Math.pow(1 - Math.abs(field), 9);
    const base = 192 + noise(u * 8, v * 8) * 14 - vein;
    return [base, base - 7, base - 13];
  });
  return new T.MeshStandardMaterial({
    map,
    roughness: 0.52,
    metalness: 0,
    normalMap: microNormal(256, (u, v) => noise(u * 107, v * 107), 0.1),
  });
}

function weave(carbon: boolean) {
  const threads = carbon ? 72 : 104;
  const height = (u: number, v: number) => {
    const x = u * threads,
      y = v * threads;
    const warp = (Math.floor(x) + Math.floor(y)) % 4 < 2;
    return warp ? Math.sin(x * Math.PI) ** 2 : Math.sin(y * Math.PI) ** 2;
  };
  const map = raster(512, (u, v) => {
    const fiber = height(u, v);
    const value = carbon ? 37 + fiber * 2 : 47 + fiber * 3;
    return [value, value + 1, value + 2];
  });
  map.wrapS = map.wrapT = T.RepeatWrapping;
  return new T.MeshPhysicalMaterial({
    map,
    normalMap: microNormal(512, height, carbon ? 0.025 : 0.03),
    roughness: carbon ? 0.44 : 0.87,
    metalness: carbon ? 0.27 : 0,
    clearcoat: carbon ? 0.18 : 0,
    clearcoatRoughness: 0.38,
    sheen: carbon ? 0 : 0.28,
    sheenColor: new T.Color('#61666b'),
    sheenRoughness: 0.8,
  });
}

function brushedMetal(color: string, roughness: number, metalness: number) {
  const noise = noiseField(431);
  const normalMap = microNormal(
    256,
    (u, v) => noise(u * 4, v * 122) * 0.8 + noise(u * 17, v * 59) * 0.2,
    0.13,
  );
  return new T.MeshStandardMaterial({ color, roughness, metalness, normalMap });
}

function matteGrain(
  color: string,
  roughness: number,
  seed: number,
  frequency: number,
  strength: number,
) {
  const material = surface(color, roughness);
  const noise = noiseField(seed);
  material.normalMap = microNormal(256, (u, v) => noise(u * frequency, v * frequency), strength);
  return material;
}

export function materials(loader: T.TextureLoader) {
  const loadColor = (source: string) => {
    const texture = loader.load(source);
    texture.colorSpace = T.SRGBColorSpace;
    texture.anisotropy = 8;
    return texture;
  };
  const mural = loadColor('/media/materials/flight-atlas-wallpaper.webp');
  mural.wrapS = T.MirroredRepeatWrapping;
  const floor = new T.MeshStandardMaterial({
    map: loadColor('/media/materials/pine-floor-color.webp'),
    normalMap: loader.load('/media/materials/pine-floor-normal.webp'),
    roughnessMap: loader.load('/media/materials/pine-floor-roughness.webp'),
    normalScale: new T.Vector2(0.64, 0.64),
    roughness: 0.83,
    color: '#dcd1c4',
  });
  for (const texture of [floor.map!, floor.normalMap!, floor.roughnessMap!]) {
    texture.wrapS = texture.wrapT = T.RepeatWrapping;
    texture.anisotropy = 8;
  }
  const upholsteryMap = loadColor('/media/materials/task-chair-fabric.webp');
  upholsteryMap.wrapS = upholsteryMap.wrapT = T.RepeatWrapping;
  upholsteryMap.repeat.set(3, 3);
  const upholstery = new T.MeshPhysicalMaterial({
    map: upholsteryMap,
    roughness: 0.93,
    sheen: 0.32,
    sheenColor: new T.Color('#666367'),
    sheenRoughness: 0.84,
  });
  const cloth = weave(false);
  upholstery.normalMap = cloth.normalMap!.clone();
  upholstery.normalMap.repeat.set(3, 3);
  upholstery.normalScale.set(0.74, 0.74);
  const gripGrain = noiseField(691);
  const cameraGrip = new T.MeshStandardMaterial({
    map: loadColor('/media/materials/hardware-surface.webp'),
    roughness: 0.87,
    normalMap: microNormal(
      256,
      (u, v) => {
        const pebbles = gripGrain(u * 64, v * 64);
        return Math.min(0.64, pebbles * 0.91 + gripGrain(u * 128, v * 128) * 0.09);
      },
      0.27,
    ),
  });
  const wall = mineralPaint(loadColor('/media/materials/plaster-surface.webp'));
  return {
    ...walnutFinishes(loadColor('/media/materials/walnut-surface.webp')),
    wall,
    floor,
    upholstery,
    cameraGrip,
    mural: new T.MeshStandardMaterial({ map: mural, roughness: 0.94 }),
    plaster: matteGrain('#c4bfb6', 0.94, 91, 91, 0.12),
    linen: linen(loadColor('/media/materials/linen-surface.webp')),
    cork: matteGrain('#887761', 0.94, 61, 67, 0.24),
    marble: marble(),
    cloth,
    carbon: weave(true),
    black: matteGrain('#1b1e22', 0.67, 14, 105, 0.14),
    rubber: matteGrain('#202123', 0.93, 34, 104, 0.16),
    graphite: brushedMetal('#34383f', 0.43, 0.42),
    steel: brushedMetal('#858a90', 0.32, 0.69),
    bronze: brushedMetal('#9d6e44', 0.31, 0.68),
    paper: matteGrain('#cab89b', 0.89, 54, 117, 0.1),
  };
}
export type Palette = ReturnType<typeof materials>;

export function contactTexture() {
  return canvasTexture(128, 128, (ctx) => {
    const shade = ctx.createRadialGradient(64, 64, 5, 64, 64, 64);
    shade.addColorStop(0, 'rgba(0,0,0,0.82)');
    shade.addColorStop(0.38, 'rgba(0,0,0,0.6)');
    shade.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = shade;
    ctx.fillRect(0, 0, 128, 128);
  });
}
