import { expect, test } from '@playwright/test';
import * as T from 'three';
import {
  batchRoomStaticGeometry,
  batchStaticSubtree,
  createZoneCuller,
  DEFAULT_ZONE_PADDING,
} from '../src/scene/engine';
import { eye, roomFov } from '../src/scene/camera';
import { workshopLayout } from '../src/scene/layout';
import { acousticWall } from '../src/scene/millwork';
import { hasRoomLodKey, surfaceKey } from '../src/scene/room-detail';
import { roomPicking } from '../src/scene/room-picking';
import { wallAtlas } from '../src/scene/travel-map';
import { localBounds } from '../src/scene/view-framing';
import type { Palette } from '../src/scene/materials';

function makePalette(): Palette {
  const mat = () => new T.MeshStandardMaterial({ color: '#cccccc' });
  const cloth = mat();
  const wood = mat();
  const woodDark = mat();
  const woodVertical = mat();
  const paper = mat();
  const steel = mat();
  const graphite = mat();
  const bronze = mat();
  return {
    cloth,
    wood,
    woodDark,
    woodVertical,
    paper,
    steel,
    graphite,
    bronze,
  } as unknown as Palette;
}

test('batchStaticSubtree merges nested static meshes, handles Int16 normals, and freezes matrices', () => {
  const root = new T.Group();
  root.name = 'Unit';
  const matA = new T.MeshStandardMaterial({ color: '#888888' });
  const matB = new T.MeshStandardMaterial({ color: '#444444' });

  const sub1 = new T.Group();
  sub1.position.set(1, 0.5, -0.2);
  const sub2 = new T.Group();
  sub2.position.set(-0.4, 0.2, 0.8);
  sub2.rotation.y = Math.PI / 4;

  // Quantized Int16 normalized normal attribute (as produced by KHR_mesh_quantization / blender-mesh)
  const makeQuantizedBox = () => {
    const geom = new T.BoxGeometry(0.1, 0.2, 0.3);
    const n = geom.getAttribute('normal');
    const q = new Int16Array(n.count * 3);
    for (let i = 0; i < n.count; i++) {
      q[i * 3] = Math.round(n.getX(i) * 32767);
      q[i * 3 + 1] = Math.round(n.getY(i) * 32767);
      q[i * 3 + 2] = Math.round(n.getZ(i) * 32767);
    }
    geom.setAttribute('normal', new T.Int16BufferAttribute(q, 3, true));
    return geom;
  };

  const m1 = new T.Mesh(makeQuantizedBox(), matA);
  m1.position.set(0.1, 0, 0);
  const m2 = new T.Mesh(makeQuantizedBox(), matA);
  m2.position.set(0, 0.3, 0);
  const m3 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), matB);
  const m4 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), matB);
  m4.castShadow = true; // Different shadow flag -> must not merge with m3

  sub1.add(m1, m3);
  sub2.add(m2, m4);
  root.add(sub1, sub2);

  root.updateMatrixWorld(true);
  const expectedBox = new T.Box3().setFromObject(m1).union(new T.Box3().setFromObject(m2));

  const stats = batchStaticSubtree(root);
  expect(stats.mergedMeshes).toBe(2);
  expect(stats.batchesCreated).toBe(1);
  expect(stats.drawsSaved).toBe(1);
  expect(stats.frozenNodes).toBeGreaterThan(0);

  const batched = root.children.find((c) => c.userData.studioBatched) as T.Mesh | undefined;
  expect(batched).toBeDefined();
  expect(batched!.matrixAutoUpdate).toBe(false);
  expect(sub1.matrixAutoUpdate).toBe(false);
  expect(m3.matrixAutoUpdate).toBe(false);

  // World-space bounds of merged mesh must match original pair exactly
  const actualBox = new T.Box3().setFromObject(batched!);
  expect(actualBox.min.distanceTo(expectedBox.min)).toBeLessThan(1e-4);
  expect(actualBox.max.distanceTo(expectedBox.max)).toBeLessThan(1e-4);

  // m3 and m4 kept separate due to castShadow mismatch
  expect(m3.parent).toBe(sub1);
  expect(m4.parent).toBe(sub2);
});

test('batchRoomStaticGeometry preserves room-lod.gz keys, dynamic/warmable/transparent meshes, and target picking', () => {
  const interior = new T.Group();
  interior.name = 'Interior';
  const mat = new T.MeshStandardMaterial({ color: '#aaaaaa' });
  const glass = new T.MeshStandardMaterial({ color: '#ffffff', transparent: true, opacity: 0.4 });

  // 1. Two static targets: meshes must NOT merge across target boundaries
  const targetA = new T.Group();
  targetA.name = 'Prop A';
  targetA.position.set(-0.5, 0, -2);
  const a1 = new T.Mesh(new T.BoxGeometry(0.2, 0.2, 0.2), mat);
  const a2 = new T.Mesh(new T.BoxGeometry(0.2, 0.2, 0.2), mat);
  a2.position.y = 0.25;
  targetA.add(a1, a2);

  const targetB = new T.Group();
  targetB.name = 'Prop B';
  targetB.position.set(0.5, 0, -2);
  const b1 = new T.Mesh(new T.BoxGeometry(0.2, 0.2, 0.2), mat);
  const b2 = new T.Mesh(new T.BoxGeometry(0.2, 0.2, 0.2), mat);
  b2.position.y = 0.25;
  targetB.add(b1, b2);

  // 2. LOD-matched geometry & warmable / rotor / transparent / mirrored meshes inside a static case
  const pcCase = new T.Group();
  pcCase.name = 'PC Case';
  const lodGeo1 = new T.SphereGeometry(0.1, 20, 16);
  const lodGeo2 = new T.SphereGeometry(0.1, 20, 16);
  const lodKeys = new Set([surfaceKey(lodGeo1)]);
  expect(hasRoomLodKey(lodGeo1, lodKeys)).toBe(true);

  const lodMesh1 = new T.Mesh(lodGeo1, mat);
  const lodMesh2 = new T.Mesh(lodGeo2, mat);
  const glass1 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), glass);
  const glass2 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), glass);
  const rotor = new T.Group();
  rotor.name = 'Fan rotor';
  const r1 = new T.Mesh(new T.BoxGeometry(0.05, 0.05, 0.05), mat);
  const r2 = new T.Mesh(new T.BoxGeometry(0.05, 0.05, 0.05), mat);
  rotor.add(r1, r2);
  const warmable = new T.Group();
  warmable.userData.studioWarmable = true;
  const w1 = new T.Mesh(new T.BoxGeometry(0.05, 0.05, 0.05), mat);
  const w2 = new T.Mesh(new T.BoxGeometry(0.05, 0.05, 0.05), mat);
  warmable.add(w1, w2);
  const mirrored = new T.Mesh(new T.BoxGeometry(0.05, 0.05, 0.05), mat);
  mirrored.scale.x = -1;
  const smallStatic1 = new T.Mesh(new T.BoxGeometry(0.04, 0.04, 0.04), mat);
  const smallStatic2 = new T.Mesh(new T.BoxGeometry(0.04, 0.04, 0.04), mat);
  smallStatic2.position.x = 0.1;

  pcCase.add(
    lodMesh1,
    lodMesh2,
    glass1,
    glass2,
    rotor,
    warmable,
    mirrored,
    smallStatic1,
    smallStatic2,
  );

  // 3. Dynamic door target and animated window/outdoor subtrees (must be completely untouched)
  const door = new T.Group();
  door.name = 'Door';
  const d1 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), mat);
  const d2 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), mat);
  door.add(d1, d2);

  const recessedWindow = new T.Group();
  recessedWindow.name = 'Recessed window';
  const blindBottom = new T.Mesh(new T.BoxGeometry(0.1, 0.02, 0.02), mat);
  const blindCord1 = new T.Mesh(new T.BoxGeometry(0.004, 0.5, 0.004), mat);
  const blindCord2 = new T.Mesh(new T.BoxGeometry(0.004, 0.5, 0.004), mat);
  recessedWindow.add(blindBottom, blindCord1, blindCord2);

  const outdoorVolume = new T.Group();
  outdoorVolume.name = 'Outdoor volume';
  const ferry1 = new T.Mesh(new T.BoxGeometry(0.2, 0.1, 0.1), mat);
  const ferry2 = new T.Mesh(new T.BoxGeometry(0.2, 0.1, 0.1), mat);
  outdoorVolume.add(ferry1, ferry2);

  interior.add(targetA, targetB, pcCase, door, recessedWindow, outdoorVolume);

  const targets = [
    { id: 'prop-a', type: 'inspect', object: targetA },
    { id: 'prop-b', type: 'inspect', object: targetB },
    { id: 'case', type: 'case', object: pcCase },
    { id: 'door', type: 'door', object: door },
  ];
  const byObject = new Map(targets.map((t) => [t.object, t]));

  const stats = batchRoomStaticGeometry(
    { interior, targets, byObject },
    {
      isLoaded: () => true,
      hasLodGeometry: (g) => hasRoomLodKey(g, lodKeys),
    },
  );

  // targetA (2->1), targetB (2->1), smallStatic1+2 in pcCase (2->1) => 6 merged, 3 batches, 3 draws saved
  expect(stats.mergedMeshes).toBe(6);
  expect(stats.batchesCreated).toBe(3);
  expect(stats.drawsSaved).toBe(3);
  expect(stats.skippedLod).toBe(2);

  // LOD, glass, rotor, warmable, mirrored, and door meshes must remain untouched
  expect(lodMesh1.parent).toBe(pcCase);
  expect(lodMesh2.parent).toBe(pcCase);
  expect(glass1.parent).toBe(pcCase);
  expect(glass2.parent).toBe(pcCase);
  expect(r1.parent).toBe(rotor);
  expect(r2.parent).toBe(rotor);
  expect(rotor.matrixAutoUpdate).toBe(true);
  expect(r1.matrixAutoUpdate).toBe(true);
  expect(w1.parent).toBe(warmable);
  expect(warmable.matrixAutoUpdate).toBe(true);
  expect(mirrored.parent).toBe(pcCase);
  expect(d1.parent).toBe(door);
  expect(d2.parent).toBe(door);
  expect(door.matrixAutoUpdate).toBe(true);
  expect(blindBottom.parent).toBe(recessedWindow);
  expect(blindCord1.parent).toBe(recessedWindow);
  expect(blindCord2.parent).toBe(recessedWindow);
  expect(recessedWindow.matrixAutoUpdate).toBe(true);
  expect(blindBottom.matrixAutoUpdate).toBe(true);
  expect(blindCord1.matrixAutoUpdate).toBe(true);
  expect(ferry1.parent).toBe(outdoorVolume);
  expect(ferry2.parent).toBe(outdoorVolume);
  expect(outdoorVolume.matrixAutoUpdate).toBe(true);
  expect(ferry1.matrixAutoUpdate).toBe(true);

  // Movable inspect target roots stay matrixAutoUpdate = true, while their batched child is frozen
  expect(targetA.matrixAutoUpdate).toBe(true);
  expect(targetB.matrixAutoUpdate).toBe(true);
  expect(targetA.children).toHaveLength(1);
  expect(targetA.children[0].matrixAutoUpdate).toBe(false);

  // Picking still resolves targetA vs targetB independently
  interior.updateMatrixWorld(true);
  const picker = roomPicking([interior]);
  const hitA = picker.closest(new T.Raycaster(new T.Vector3(-0.5, 0, 0), new T.Vector3(0, 0, -1)));
  const hitB = picker.closest(new T.Raycaster(new T.Vector3(0.5, 0, 0), new T.Vector3(0, 0, -1)));
  expect(hitA?.parent).toBe(targetA);
  expect(hitB?.parent).toBe(targetB);
  picker.dispose();

  // Calling a second time is idempotent
  const second = batchRoomStaticGeometry(
    { interior, targets, byObject },
    {
      isLoaded: () => true,
      hasLodGeometry: (g) => hasRoomLodKey(g, lodKeys),
    },
  );
  expect(second.drawsSaved).toBe(0);
});

test('batchRoomStaticGeometry conservatively skips >=300-vertex meshes when room-lod.gz is not yet loaded', () => {
  const interior = new T.Group();
  const mat = new T.MeshStandardMaterial();
  const hi1 = new T.Mesh(new T.SphereGeometry(0.1, 20, 16), mat); // > 300 verts
  const hi2 = new T.Mesh(new T.SphereGeometry(0.1, 20, 16), mat);
  const lo1 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), mat); // 24 verts
  const lo2 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.1), mat);
  interior.add(hi1, hi2, lo1, lo2);

  const stats = batchRoomStaticGeometry(
    { interior, targets: [], byObject: new Map() },
    {
      isLoaded: () => false,
      hasLodGeometry: () => false,
    },
  );
  expect(stats.skippedLod).toBe(2);
  expect(stats.drawsSaved).toBe(1);
  expect(hi1.parent).toBe(interior);
  expect(hi2.parent).toBe(interior);
});

test('acousticWall and wallAtlas use InstancedMesh while keeping map-pin picking intact', () => {
  const p = makePalette();
  const wallRoot = new T.Group();
  acousticWall(wallRoot, p, -1.248, -0.913, -0.56, 2.71);
  const instancedFins: T.InstancedMesh[] = [];
  wallRoot.traverse((obj) => {
    if (obj instanceof T.InstancedMesh) instancedFins.push(obj);
  });
  expect(instancedFins).toHaveLength(1);
  expect(instancedFins[0].count).toBeGreaterThanOrEqual(9);
  expect(instancedFins[0].instanceColor).not.toBeNull();
  expect(instancedFins[0].userData.exportInstalledInstances).toBe(true);

  const mapRoot = new T.Group();
  const atlas = wallAtlas(mapRoot, p, new T.Texture());
  const pinBatches: T.InstancedMesh[] = [];
  let visiblePinChildMeshes = 0;
  atlas.frame.traverse((obj) => {
    if (obj instanceof T.InstancedMesh) pinBatches.push(obj);
    else if (
      obj instanceof T.Mesh &&
      obj.parent &&
      atlas.pins.some((entry) => entry.pin === obj.parent) &&
      !Array.isArray(obj.material) &&
      obj.material.visible
    ) {
      visiblePinChildMeshes++;
    }
  });
  expect(pinBatches).toHaveLength(2);
  expect(pinBatches[0].count).toBe(atlas.pins.length);
  expect(pinBatches[1].count).toBe(atlas.pins.length);
  expect(visiblePinChildMeshes).toBe(0);

  // Verify roomPicking resolves directly to a specific pin via its invisible hit proxy
  mapRoot.updateMatrixWorld(true);
  const picker = roomPicking([mapRoot]);
  const targetPin = atlas.pins[0].pin;
  const worldPos = targetPin.getWorldPosition(new T.Vector3());
  const ray = new T.Raycaster(
    worldPos.clone().add(new T.Vector3(0, 0, 0.2)),
    new T.Vector3(0, 0, -1),
  );
  const hit = picker.closest(ray);
  expect(hit?.parent).toBe(targetPin);
  picker.dispose();

  // localBounds(atlas.frame) must not be expanded below or beyond the frame by instanced pin geometries
  const mapBounds = localBounds(atlas.frame);
  expect(mapBounds.min.y).toBeGreaterThan(-0.3);
  expect(mapBounds.max.y).toBeLessThan(0.3);
});

test('DEFAULT_ZONE_PADDING is tightened and keeps east-workshop/south-rear culled at desk view', () => {
  expect(DEFAULT_ZONE_PADDING).toBeGreaterThanOrEqual(0.15);
  expect(DEFAULT_ZONE_PADDING).toBeLessThanOrEqual(0.2);

  const culler = createZoneCuller();
  const deskObj = new T.Mesh(new T.BoxGeometry(1.2, 0.75, 0.6), new T.MeshStandardMaterial());
  deskObj.position.set(0, 0.4, -0.2);
  const benchObj = new T.Mesh(new T.BoxGeometry(0.6, 0.75, 1.4), new T.MeshStandardMaterial());
  benchObj.position.set(workshopLayout.x, 0.4, workshopLayout.z);
  const rearObj = new T.Mesh(new T.BoxGeometry(1.2, 1.5, 0.3), new T.MeshStandardMaterial());
  rearObj.position.set(0, 0.9, 3.0);

  culler.register('desk', deskObj);
  culler.register('east-workshop', benchObj);
  culler.register('south-rear', rearObj);

  const camera = new T.PerspectiveCamera(roomFov, 16 / 9, 0.05, 60);
  camera.position.set(eye.x, eye.y, eye.defaultZ);
  camera.rotation.set(eye.pitch, eye.yaw, 0, 'YXZ');
  camera.updateMatrixWorld(true);
  camera.updateProjectionMatrix();

  culler.update(camera);
  expect(culler.isZoneVisible('desk')).toBe(true);
  expect(culler.isZoneVisible('east-workshop')).toBe(false);
  expect(culler.isZoneVisible('south-rear')).toBe(false);

  // Turning right toward the East Workbench must un-cull it before it enters the viewport
  camera.rotation.set(eye.pitch, -Math.PI / 2, 0, 'YXZ');
  camera.updateMatrixWorld(true);
  culler.update(camera);
  expect(culler.isZoneVisible('east-workshop')).toBe(true);
});
