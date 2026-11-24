import * as T from 'three';
import { box, cable, group, luminous, mesh, surface, tube } from './geometry';
import type { Palette } from './materials';

export function acousticWall(
  root: T.Group,
  p: Palette,
  left: number,
  right: number,
  z: number,
  height: number,
  bottom = 0,
) {
  const panel = group(root, 'Ash fins on acoustic felt', [left, bottom, z]);
  const width = right - left;
  const backing = p.cloth.clone();
  backing.color.set('#383630');
  box(panel, [width, height - 0.012, 0.012], [width / 2, height / 2, 0.006], backing);
  const variants = ['#f8f4e9', '#efe9dd', '#fff9ee', '#f3ece2'].map((color) => {
    const wood = p.woodVertical.clone();
    wood.color.set(color);
    return wood;
  });
  const count = Math.floor(width / 0.035);
  const pitch = width / count;
  for (let i = 0; i < count; i++) {
    box(
      panel,
      [pitch - 0.01, height - 0.018, 0.022],
      [(i + 0.5) * pitch, height / 2, 0.023],
      variants[(i * 7) % 4],
      0.0015,
    );
  }
}

export function archiveLight(root: T.Group, p: Palette, north: number) {
  const fixture = group(root, 'Brass archive light', [-0.18, 2.237, north]);
  const brass = p.bronze.clone();
  brass.color.set('#ad855a');
  brass.roughness = 0.35;
  const diffuser = luminous('#ffe1b2', 1.7);
  const lamp = new T.SpotLight('#ffe5c7', 0, 1.9, 1.18, 0.88, 2);
  lamp.name = 'Brass archive picture light';
  lamp.position.set(0, 0.024, 0.152);
  lamp.target.position.set(0, -0.42, -0.04);
  for (const x of [-0.219, 0.219]) {
    tube(fixture, [x, 0, 0.001], [x, 0, 0.015], 0.025, brass);
    tube(fixture, [x, 0, 0.016], [x, 0, 0.027], 0.012, brass);
    cable(
      fixture,
      [
        [x, 0, 0.019],
        [x, 0, 0.062],
        [x, 0.005, 0.106],
        [x, 0.033, 0.132],
        [x, 0.038, 0.15],
      ],
      0.0045,
      brass,
    );
    for (const side of [-1, 1])
      tube(fixture, [x + side * 0.016, 0, 0.014], [x + side * 0.016, 0, 0.0165], 0.002, brass);
  }
  tube(fixture, [-0.383, 0.038, 0.159], [0.383, 0.038, 0.159], 0.014, brass);
  for (const x of [-0.232, 0.232])
    tube(fixture, [x - 0.004, 0.038, 0.159], [x + 0.004, 0.038, 0.159], 0.015, brass);
  box(fixture, [0.731, 0.003, 0.016], [0, 0.025, 0.157], diffuser, 0.001);
  fixture.add(lamp, lamp.target);
  return { fixture, lamp, diffuser };
}

export function rearGalleryPrint(root: T.Group, p: Palette, photo: T.Texture, south: number) {
  const frame = group(root, 'Float-mounted coastal photographic print', [
    -0.48,
    1.79,
    south - 0.021,
  ]);
  frame.rotation.y = Math.PI;
  const rail = surface('#373732', 0.49, 0.38);
  const mount = p.paper.clone();
  mount.color.set('#ded7c8');
  const width = 1.01;
  const height = 0.674;
  box(frame, [width, height, 0.025], [0, 0, 0], rail, 0.001);
  box(frame, [width - 0.019, height - 0.019, 0.004], [0, 0, 0.013], mount);
  const ink = new T.MeshStandardMaterial({ map: photo, roughness: 0.86 });
  const image = mesh(frame, new T.PlaneGeometry(0.816, 0.544), ink, [0, 0.014, 0.0152]);
  image.castShadow = false;
  for (const sign of [-1, 1]) {
    box(frame, [width, 0.008, 0.031], [0, sign * (height / 2 - 0.004), 0.012], rail, 0.001);
    box(frame, [0.008, height - 0.016, 0.031], [sign * (width / 2 - 0.004), 0, 0.012], rail, 0.001);
  }
}
