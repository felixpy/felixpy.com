import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { decodeBlenderMesh } from '../src/scene/blender-mesh';

test('both amplifier backs leave the offset duct and connector openings clear', () => {
  function surface(name: string) {
    const bytes = Uint8Array.from(readFileSync('public/media/models/kef/' + name + '.mesh'));
    const object = new Mesh(
      decodeBlenderMesh(bytes.buffer),
      new MeshBasicMaterial({ side: DoubleSide }),
    );
    object.name = name;
    return object;
  }
  for (const role of ['primary', 'secondary']) {
    const parts = [
      'rear-heatsink',
      'rear-lining',
      'rear-alloy',
      'rear-copper',
      role + '-alloy',
      role + '-lining',
      role + '-metal',
      role + '-contact',
    ].map(surface);
    function firstHit(x: number, y: number) {
      const ray = new Raycaster(new Vector3(x, y, -0.18), new Vector3(0, 0, 1));
      const [hit] = ray.intersectObjects(parts);
      expect(hit).toBeDefined();
      return hit;
    }
    for (const x of [0.04, 0.0455, 0.051]) {
      const through = firstHit(x, 0.0675);
      expect(through.object.name).toBe('rear-lining');
      expect(through.distance).toBeCloseTo(0.28, 4);
    }
    expect(firstHit(0.082, 0.0675).object.name).toBe('rear-copper');
    expect(firstHit(-0.03, 0.0675).object.name).toBe('rear-heatsink');
    expect(firstHit(0.058, -0.116).object.name).toBe(role + '-lining');
    const hdmi = firstHit(0.0606, -0.0867);
    expect(hdmi.object.name).toBe(role + (role === 'primary' ? '-lining' : '-alloy'));
    expect(hdmi.distance).toBeCloseTo(role === 'primary' ? 0.03755 : 0.03105, 4);
  }
});
