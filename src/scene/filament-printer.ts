import * as T from 'three';
import type { DeferRoomAsset } from './rear-loading';
import { box, canvasTexture, group, mesh, surface } from './geometry';
import { loadBlenderPack } from './blender-pack';
import { whaleTailPrint } from './whale-tail-print';
import { printerStand } from './layout';
import type { Palette } from './materials';
import type { Locale } from '../app/locale';

function reelMaterials() {
  const flange = canvasTexture(384, 384, (ctx) => {
    ctx.fillStyle = '#f4f3ee';
    ctx.fillRect(0, 0, 384, 384);
    ctx.translate(192, 192);
    ctx.globalCompositeOperation = 'destination-out';
    for (const radius of [92, 111, 130, 149, 168]) {
      const count = Math.floor(radius / 3);
      for (let i = 0; i < count; i++) {
        ctx.save();
        ctx.rotate(((i + (radius % 2) * 0.5) * 2 * Math.PI) / count);
        ctx.beginPath();
        ctx.roundRect(radius - 6.2, -5.3, 12.4, 10.6, 2);
        ctx.fill();
        ctx.restore();
      }
    }
  });
  const thread = canvasTexture(512, 8, (ctx) => {
    for (let x = 0; x < 512; x++) {
      const value = Math.round(105 + 100 * Math.cos((2 * Math.PI * 35 * x) / 512));
      ctx.fillStyle = `rgb(${value},${value},${value})`;
      ctx.fillRect(x, 0, 1, 8);
    }
  });
  thread.colorSpace = T.NoColorSpace;
  return {
    web: new T.MeshStandardMaterial({
      map: flange,
      color: '#767b7b',
      alphaTest: 0.47,
      roughness: 0.59,
      side: T.DoubleSide,
    }),
    ...Object.fromEntries(
      Object.entries({ linen: '#f3eee6', slate: '#384875', teal: '#638cbb', clay: '#e9b99b' }).map(
        ([key, color]) => [
          key,
          new T.MeshStandardMaterial({
            color,
            roughness: 0.49,
            bumpMap: thread,
            bumpScale: 0.00022,
          }),
        ],
      ),
    ),
  };
}

function activeGuide(unit: T.Group, material: T.Material, height: number) {
  const segments = 20,
    sides = 8;
  const geometry = new T.BufferGeometry();
  const points = new T.BufferAttribute(new Float32Array((segments + 1) * sides * 3), 3).setUsage(
    T.DynamicDrawUsage,
  );
  const normals = new T.BufferAttribute(new Float32Array(points.count * 3), 3).setUsage(
    T.DynamicDrawUsage,
  );
  const indices = [];
  for (let i = 0; i < segments; i++)
    for (let j = 0; j < sides; j++) {
      const a = i * sides + j,
        b = i * sides + ((j + 1) % sides);
      indices.push(a, b, a + sides, b, b + sides, a + sides);
    }
  geometry.setAttribute('position', points);
  geometry.setAttribute('normal', normals);
  geometry.setIndex(indices);
  const travelBounds = new T.Sphere(new T.Vector3(0, 0.46, 0.08), 0.24);
  const worldBounds = new T.Sphere();
  geometry.boundingSphere = travelBounds.clone();
  const tube = mesh(unit, geometry, material);
  tube.name = 'Active tool filament guide';
  tube.castShadow = false;
  const view = new T.Frustum();
  const viewProjection = new T.Matrix4();
  const path = new T.CubicBezierCurve3(
    new T.Vector3(0, 0.585, 0.176),
    new T.Vector3(0, 0.49, 0.076),
    new T.Vector3(),
    new T.Vector3(),
  );
  const origin = new T.Vector3(),
    tangent = new T.Vector3(),
    n = new T.Vector3(),
    b = new T.Vector3();
  const entryDirection = new T.Vector3().subVectors(path.v1, path.v0);
  const bendDirection = new T.Vector3(),
    exitDirection = new T.Vector3();
  const reference = new T.Vector3(1, 0, 0);
  const circle = Array.from({ length: sides }, (_, i) => [
    Math.cos((i * 2 * Math.PI) / sides),
    Math.sin((i * 2 * Math.PI) / sides),
  ]);
  return (x: number, z: number, camera?: T.PerspectiveCamera) => {
    if (path.v3.x === x && path.v3.z === z && path.v3.y !== 0) return;
    if (camera) {
      if (!unit.visible) return;
      view.setFromProjectionMatrix(
        viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse),
        camera.coordinateSystem,
        camera.reversedDepth,
      );
      tube.updateWorldMatrix(true, false);
      if (!view.intersectsSphere(worldBounds.copy(travelBounds).applyMatrix4(tube.matrixWorld)))
        return;
    }
    path.v2.set(x, 0.49, z - 0.022);
    path.v3.set(x, height + 0.075, z);
    bendDirection.subVectors(path.v2, path.v1);
    exitDirection.subVectors(path.v3, path.v2);
    for (let i = 0; i <= segments; i++) {
      const t = i / segments,
        u = 1 - t;
      path.getPoint(t, origin);
      tangent
        .copy(entryDirection)
        .multiplyScalar(u * u)
        .addScaledVector(bendDirection, 2 * u * t)
        .addScaledVector(exitDirection, t * t)
        .normalize();
      n.crossVectors(tangent, reference).normalize();
      b.crossVectors(tangent, n);
      for (let j = 0; j < sides; j++) {
        const [c, s] = circle[j];
        const nx = c * n.x + s * b.x,
          ny = c * n.y + s * b.y,
          nz = c * n.z + s * b.z,
          index = i * sides + j;
        points.setXYZ(
          index,
          origin.x + nx * 0.0024,
          origin.y + ny * 0.0024,
          origin.z + nz * 0.0024,
        );
        normals.setXYZ(index, nx, ny, nz);
      }
    }
    points.needsUpdate = normals.needsUpdate = true;
    geometry.boundingSphere!.copy(travelBounds);
  };
}

function glazing(color: string, minimum: number) {
  const material = new T.MeshStandardMaterial({
    color,
    roughness: 0.08,
    metalness: 0.16,
    envMapIntensity: 1.35,
    transparent: true,
    opacity: minimum,
    depthWrite: false,
    side: T.DoubleSide,
    forceSinglePass: true,
  });
  material.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <opaque_fragment>',
      'diffuseColor.a = min(0.96, opacity + 0.48 * pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), 3.0));\n#include <opaque_fragment>',
    );
  };
  material.customProgramCacheKey = () => 'enclosure-glazing';
  return material;
}

export function filamentPrinter(
  root: T.Group,
  p: Palette,
  manager: T.LoadingManager,
  deferRoomDetail: DeferRoomAsset,
) {
  const stand = group(root, 'Fabrication cabinet', [printerStand.x, 0, printerStand.z]);
  stand.rotation.y = printerStand.yaw;
  const oak = p.wood.clone();
  oak.color.set('#c3b195');
  box(stand, [0.56, 0.058, 0.55], [0, 0.033, -0.015], p.graphite, 0.002);
  const carcass = surface('#d5d2c6', 0.62);
  box(stand, [0.646, 0.437, 0.625], [0, 0.276, 0], carcass, 0.003);
  const reveal = surface('#655f52', 0.78);
  box(stand, [0.619, 0.397, 0.004], [0, 0.272, 0.314], reveal, 0.001);
  for (const x of [-0.154, 0.154])
    box(stand, [0.304, 0.391, 0.013], [x, 0.273, 0.32], carcass, 0.0025);
  box(stand, [printerStand.width, 0.029, printerStand.depth], [0, 0.509, 0], oak, 0.003);
  const unit = group(stand, 'Bambu Lab H3C with AMS 3H', [0, 0.5235, 0]);
  unit.visible = false;
  const railHeight = 0.345;
  const bed = group(unit, 'Z carriage');
  const gantry = group(unit, 'CoreXY crossbeam');
  const head = group(gantry, 'Swaptek active tool');
  const fills: Record<string, T.Material> = {
    alloy: surface('#adb2b5', 0.37, 0.6),
    graphite: surface('#343c40', 0.47, 0.31),
    black: surface('#202527', 0.57, 0.13),
    steel: surface('#b1b8bc', 0.25, 0.83),
    smoke: glazing('#252b2d', 0.75),
    glass: glazing('#a2b0b0', 0.06),
    canopy: glazing('#373e42', 0.68),
    satin: surface('#616b70', 0.41, 0.44),
    brass: surface('#b9a385', 0.38, 0.61),
    white: new T.MeshStandardMaterial({
      color: '#fbf7e8',
      emissive: '#fff6e4',
      emissiveIntensity: 1.6,
    }),
    pei: surface('#9c8052', 0.8, 0.48),
    ...reelMaterials(),
    spool: surface('#565d5e', 0.51, 0.13),
    tube: surface('#495156', 0.4),
  };
  const print = whaleTailPrint(bed, manager);
  const chamberAlloy = new T.MeshStandardMaterial({
    color: '#62696b',
    roughness: 0.6,
    metalness: 0.23,
    emissive: '#313b3c',
    emissiveIntensity: 0.35,
  });
  const bedFace = fills.pei as T.MeshStandardMaterial;
  bedFace.emissive.set('#756044');
  bedFace.emissiveIntensity = 0.21;
  const assemblies: Record<string, T.Group> = { frame: unit, bed, gantry, head };
  deferRoomDetail(() =>
    Promise.allSettled([
      print.load(),
      loadBlenderPack(manager, '/media/models/h3c.mesh.gz', (name, geometry) => {
        const [part, finish] = name.split('-');
        const material =
          ['gantry', 'head', 'bed'].includes(part) && finish === 'graphite'
            ? chamberAlloy
            : fills[finish];
        const item = mesh(assemblies[part], geometry, material);
        item.name = 'H3C ' + name;
        item.castShadow = !['glass', 'smoke', 'canopy', 'white'].includes(finish);
      }),
    ]).then((results) => {
      if (results.some((result) => result.status === 'rejected')) return;
      update(0, true, 'en');
      unit.visible = true;
    }),
  );
  const badge = canvasTexture(640, 96, (ctx) => {
    ctx.fillStyle = '#272d2f';
    ctx.font = '600 39px Arial';
    ctx.textAlign = 'right';
    ctx.fillText('Bambu Lab  H3C', 628, 60);
  });
  mesh(
    unit,
    new T.PlaneGeometry(0.099, 0.01485),
    new T.MeshStandardMaterial({ map: badge, transparent: true, depthWrite: false }),
    [0.143, 0.554, 0.2783],
  ).castShadow = false;
  const screen = canvasTexture(512, 274, () => {});
  const screenMat = new T.MeshBasicMaterial({ map: screen, toneMapped: false });
  const control = mesh(unit, new T.PlaneGeometry(0.112, 0.065), screenMat, [-0.151, 0.574, 0.3048]);
  control.name = 'H3C job touchscreen';
  control.castShadow = false;
  let previous: Locale | undefined;
  function updatePanel(locale: Locale) {
    if (previous === locale) return;
    previous = locale;
    const chinese = locale === 'zh';
    const ctx = (screen.image as HTMLCanvasElement).getContext('2d')!;
    ctx.fillStyle = '#172025';
    ctx.fillRect(0, 0, 512, 274);
    ctx.fillStyle = '#c4d7cf';
    ctx.font = '500 18px Arial';
    ctx.fillText('Bambu Lab', 21, 32);
    ctx.fillStyle = '#95cfae';
    ctx.fillText(chinese ? '运行中' : 'Running', 377, 32);
    ctx.fillStyle = '#eef1ec';
    ctx.font = '600 31px Arial';
    ctx.fillText(chinese ? 'DeepSeek 鲸鱼娘' : 'DeepSeek Whale Girl', 21, 92);
    ctx.font = '22px Arial';
    ctx.fillStyle = '#a8b8b7';
    ctx.fillText(chinese ? '多色 PLA   ·   0.4 mm' : 'Multicolour PLA   ·   0.4 mm', 21, 130);
    ctx.font = '16px Arial';
    ctx.fillText(
      chinese ? '喷嘴   220°C        热床   55°C' : 'Nozzle   220°C        Bed   55°C',
      21,
      163,
    );
    ctx.fillStyle = '#3b4647';
    ctx.fillRect(21, 186, 466, 2);
    ctx.font = '20px Arial';
    ctx.fillStyle = '#c4d7cf';
    ctx.fillText(chinese ? '顶面走刀' : 'Top surface pass', 21, 231);
    screen.needsUpdate = true;
  }
  const updateGuide = activeGuide(unit, fills.tube, railHeight);
  function update(delta: number, reduced: boolean, locale: Locale, camera?: T.PerspectiveCamera) {
    const { height, x, z } = print.update(reduced ? 0 : delta);
    bed.position.y = railHeight - height;
    gantry.position.set(0, railHeight, z);
    head.position.x = x;
    updateGuide(head.position.x, gantry.position.z, camera);
    updatePanel(locale);
  }
  update(0, true, 'en');
  return { unit, update };
}
