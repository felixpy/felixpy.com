import { expect, test } from '@playwright/test';
import * as T from 'three';
import { roomPicking } from '../src/scene/room-picking';

test('the pointer follows moved, added and removed parts, visibility and coincident surfaces', () => {
  const root = new T.Group(),
    drawer = new T.Group();
  const shape = new T.BoxGeometry(1, 1, 1);
  const surface = new T.MeshStandardMaterial();
  const back = new T.Mesh(shape, surface),
    inside = new T.Mesh(shape, surface);
  root.add(back, drawer);
  drawer.add(inside);
  back.position.z = -6;
  drawer.position.set(3, 0, -3);
  const ray = new T.Raycaster(new T.Vector3(), new T.Vector3(0, 0, -1));
  const picker = roomPicking([root]);
  const hit = (held?: T.Object3D) => {
    root.updateMatrixWorld(true);
    return picker.closest(ray, held);
  };
  expect(hit()).toBe(back);
  drawer.position.x = 0;
  expect(hit()).toBe(inside);
  drawer.visible = false;
  expect(hit()).toBe(back);
  expect(hit(inside)).toBe(inside);
  drawer.visible = true;
  inside.layers.set(2);
  expect(hit()).toBe(back);
  inside.layers.enable(0);
  drawer.position.z = -6;
  expect(hit()).toBe(back);
  expect(hit(inside)).toBe(inside);
  const card = new T.Mesh(shape, surface);
  card.position.z = 3;
  drawer.add(card);
  expect(hit()).toBe(card);
  drawer.remove(card);
  expect(hit()).toBe(back);
  ray.far = 5.5;
  expect(hit()).toBeUndefined();
  expect(ray.far).toBe(5.5);
  ray.far += 0.001;
  expect(hit()).toBe(back);
  picker.dispose();
});

test('picking refits vertex edits and keeps instanced and custom surfaces on their native raycast', () => {
  const root = new T.Group(),
    ray = new T.Raycaster(new T.Vector3(), new T.Vector3(0, 0, -1));
  const mesh = new T.Mesh(new T.BoxGeometry(), new T.MeshStandardMaterial());
  mesh.position.z = -4;
  root.add(mesh);
  const picker = roomPicking([root]);
  const hit = () => {
    root.updateMatrixWorld(true);
    return picker.closest(ray);
  };
  expect(hit()).toBe(mesh);
  mesh.geometry.translate(4, 0, 0);
  expect(hit()).toBeUndefined();
  mesh.geometry.setAttribute('position', new T.BoxGeometry().getAttribute('position'));
  root.add(new T.Group());
  expect(hit()).toBe(mesh);
  mesh.geometry = new T.BoxGeometry();
  expect(hit()).toBe(mesh);
  const lights = new T.InstancedMesh(new T.BoxGeometry(), mesh.material, 1);
  lights.setMatrixAt(0, new T.Matrix4().makeTranslation(0, 0, -2));
  root.add(lights);
  expect(hit()).toBe(lights);
  lights.setMatrixAt(0, new T.Matrix4().makeTranslation(2, 0, -2));
  lights.computeBoundingSphere();
  expect(hit()).toBe(mesh);
  mesh.raycast = () => {};
  expect(hit()).toBeUndefined();
  picker.dispose();
});

test('early input can pick newly attached meshes before the idle index is ready', () => {
  const root = new T.Group(),
    queue: (() => void)[] = [];
  const picker = roomPicking([root], (work) => queue.push(work));
  const ray = new T.Raycaster(new T.Vector3(), new T.Vector3(0, 0, -1));
  const prop = new T.Mesh(new T.BoxGeometry(), new T.MeshStandardMaterial());
  prop.position.z = -4;
  root.add(prop);
  for (let i = 0; i < 650; i++) root.add(new T.Group());
  root.updateMatrixWorld(true);
  expect(picker.closest(ray)).toBe(prop);
  expect(queue).toHaveLength(1);
  queue.shift()!();
  const insert = prop.clone();
  insert.position.z = -2;
  root.add(insert);
  root.remove(prop);
  root.add(new T.Group());
  root.updateMatrixWorld(true);
  expect(picker.closest(ray)).toBe(insert);
  insert.position.x = 2;
  root.updateMatrixWorld(true);
  expect(picker.closest(ray)).toBeUndefined();
  insert.position.x = 0;
  insert.visible = false;
  root.updateMatrixWorld(true);
  expect(picker.closest(ray)).toBeUndefined();
  insert.visible = true;
  expect(queue).toHaveLength(1);
  while (queue.length) queue.shift()!();
  expect(picker.closest(ray)).toBe(insert);
  picker.dispose();
});
