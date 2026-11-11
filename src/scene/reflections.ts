import * as T from 'three';
import { desk, roomSize } from './furniture';
import { windowOpening } from './window';

export function studioReflections(renderer: T.WebGLRenderer) {
  const probe = new T.Scene();
  probe.background = new T.Color().setRGB(0.145, 0.132, 0.113);
  function panel(
    width: number,
    height: number,
    color: T.Color,
    position: [number, number, number],
  ) {
    const mesh = new T.Mesh(
      new T.PlaneGeometry(width, height),
      new T.MeshBasicMaterial({ color, toneMapped: false }),
    );
    mesh.position.set(...position);
    probe.add(mesh);
    return mesh;
  }

  const { wall, z0, z1, y0, y1 } = windowOpening;
  const rail = y0 + 0.77,
    mullion = (z0 + z1) / 2;
  for (const [left, right] of [
    [z0 + 0.03, mullion - 0.028],
    [mullion + 0.028, z1 - 0.03],
  ]) {
    for (const [bottom, top, upper] of [
      [y0 + 0.061, rail - 0.032, false],
      [rail + 0.032, y1 - 0.061, true],
    ] as const) {
      const tint = upper
        ? new T.Color().setRGB(1.9, 2.5, 3.6)
        : new T.Color().setRGB(0.92, 1.25, 1.85);
      panel(right - left, top - bottom, tint, [
        wall - 0.154,
        (bottom + top) / 2,
        (left + right) / 2,
      ]).rotation.y = Math.PI / 2;
    }
  }
  const desktop = panel(
    desk.right - desk.left,
    desk.front - desk.back,
    new T.Color().setRGB(0.19, 0.135, 0.091),
    [(desk.left + desk.right) / 2, desk.top, (desk.front + desk.back) / 2],
  );
  desktop.rotation.x = -Math.PI / 2;
  panel(0.55, 0.36, new T.Color().setRGB(1.3, 1.02, 0.75), [
    0.09,
    roomSize.ceiling - 0.05,
    0.02,
  ]).rotation.x = Math.PI / 2;

  const generator = new T.PMREMGenerator(renderer);
  const reflection = generator.fromScene(probe, 0.055, 0.05, 8, {
    size: 128,
    position: new T.Vector3(0.18, 1.02, 0.07),
  });
  generator.dispose();
  for (const child of probe.children) {
    if (child instanceof T.Mesh) {
      child.geometry.dispose();
      child.material.dispose();
    }
  }
  return reflection;
}
