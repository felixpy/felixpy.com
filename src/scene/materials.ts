import * as T from 'three';
import { canvasTexture, surface } from './geometry';

function ashFinishes(albedo: T.Texture, normalMap: T.Texture, roughnessMap: T.Texture) {
  for (const map of [albedo, normalMap, roughnessMap]) {
    map.wrapS = map.wrapT = T.RepeatWrapping;
    map.anisotropy = 8;
  }
  const wood = new T.MeshPhysicalMaterial({
    map: albedo,
    normalMap,
    roughnessMap,
    roughness: 0.83,
    clearcoat: 0.17,
    clearcoatRoughness: 0.41,
    normalScale: new T.Vector2(0.65, 0.65),
  });
  const woodDark = wood.clone();
  woodDark.color.set('#baaa95');
  const woodVertical = wood.clone();
  for (const key of ['map', 'normalMap', 'roughnessMap'] as const) {
    const texture = wood[key]!.clone();
    texture.center.set(0.5, 0.5);
    texture.rotation = Math.PI / 2;
    woodVertical[key] = texture;
  }
  return { wood, woodDark, woodVertical };
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

export function materials(loader: T.TextureLoader) {
  const loadColor = (source: string) => {
    const texture = loader.load(source);
    texture.colorSpace = T.SRGBColorSpace;
    texture.anisotropy = 8;
    return texture;
  };
  const ash = ashFinishes(
    loadColor('/media/materials/ash-color.webp'),
    loader.load('/media/materials/ash-normal.webp'),
    loader.load('/media/materials/ash-roughness.webp'),
  );
  const floor = ash.wood.clone();
  floor.roughness = 1;
  floor.clearcoat = 0.055;
  floor.color.setRGB(1.32, 1.29, 1.21);
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
  const micro = (name: string) => {
    const tex = loader.load('/media/materials/' + name + '.webp');
    tex.wrapS = tex.wrapT = T.RepeatWrapping;
    tex.anisotropy = 8;
    return tex;
  };
  function weave(name: 'carbon' | 'cloth') {
    const carbon = name === 'carbon';
    const map = micro(name + '-weave');
    map.colorSpace = T.SRGBColorSpace;
    return new T.MeshPhysicalMaterial({
      map,
      normalMap: micro(name + '-weave-normal'),
      roughness: carbon ? 0.44 : 0.87,
      metalness: carbon ? 0.27 : 0,
      clearcoat: carbon ? 0.18 : 0,
      clearcoatRoughness: 0.38,
      sheen: carbon ? 0 : 0.28,
      sheenColor: new T.Color('#61666b'),
      sheenRoughness: 0.8,
    });
  }
  const cloth = weave('cloth');
  upholstery.normalMap = cloth.normalMap!.clone();
  upholstery.normalMap.repeat.set(3, 3);
  upholstery.normalScale.set(0.74, 0.74);
  const cameraGrip = new T.MeshStandardMaterial({
    map: loadColor('/media/materials/hardware-surface.webp'),
    roughness: 0.87,
    normalMap: micro('camera-grip-normal'),
  });
  const wallMap = loadColor('/media/materials/plaster-surface.webp');
  const wallNormal = micro('wall-micro-normal'),
    wallRoughness = micro('wall-micro-roughness');
  for (const tex of [wallMap, wallNormal, wallRoughness])
    tex.wrapS = tex.wrapT = T.MirroredRepeatWrapping;
  const wall = new T.MeshStandardMaterial({
    map: wallMap,
    color: new T.Color().setRGB(1.1, 1.14, 1.2),
    roughness: 1,
    roughnessMap: wallRoughness,
    normalMap: wallNormal,
    normalScale: new T.Vector2(0.41, 0.41),
  });
  const brush = micro('metal-brush-normal');
  const brushedMetal = (color: string, roughness: number, metalness: number) =>
    new T.MeshStandardMaterial({ color, roughness, metalness, normalMap: brush });
  const matteGrain = (name: string, color: string, roughness: number) => {
    const material = surface(color, roughness);
    material.normalMap = micro(name + '-grain-normal');
    return material;
  };
  return {
    ...ash,
    wall,
    floor,
    upholstery,
    cameraGrip,
    plaster: matteGrain('plaster', '#c4bfb6', 0.94),
    linen: new T.MeshStandardMaterial({
      map: loadColor('/media/materials/linen-surface.webp'),
      roughness: 0.91,
      normalMap: micro('linen-micro-normal'),
    }),
    cork: matteGrain('cork', '#887761', 0.94),
    limestone: new T.MeshStandardMaterial({
      map: loadColor('/media/materials/limestone-color.webp'),
      roughness: 0.69,
      metalness: 0,
      normalMap: micro('limestone-normal'),
    }),
    cloth,
    carbon: weave('carbon'),
    black: matteGrain('black', '#1b1e22', 0.67),
    rubber: matteGrain('rubber', '#202123', 0.93),
    graphite: brushedMetal('#34383f', 0.43, 0.42),
    steel: brushedMetal('#858a90', 0.32, 0.69),
    bronze: brushedMetal('#9d6e44', 0.31, 0.68),
    paper: matteGrain('paper', '#cab89b', 0.89),
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
