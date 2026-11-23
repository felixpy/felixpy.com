import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { Mesh, Vector3 } from 'three';
import { productModel } from './helpers/product-model';

test('both PCB faces, etched M.2 covers and the I/O print retain their authored UVs', async () => {
  const name = 'strix-z890-a.glb';
  const data = await readFile('public/media/models/' + name);
  const asset = JSON.parse(data.toString('utf8', 20, 20 + data.readUInt32LE(12)));
  const model = await productModel(name);
  model.updateMatrixWorld(true);
  const prints = new Set<number>();
  for (const finish of [
    'Pearl soldermask',
    'Slate soldermask',
    'Fubuki etched M.2 armour',
    'I/O lenticular print',
    'I/O silver foil perimeter print',
  ]) {
    const material = asset.materials.find((entry: { name: string }) => entry.name === finish);
    const map = material?.pbrMetallicRoughness.baseColorTexture;
    expect(map, finish).toBeDefined();
    expect(map.texCoord ?? 0, finish).toBe(0);
    prints.add(map.index);
    if (finish === 'I/O lenticular print') {
      expect(material.emissiveTexture, finish).toBeDefined();
      expect(material.emissiveTexture.index, finish).not.toBe(map.index);
    }
    if (finish === 'Fubuki etched M.2 armour') {
      expect(material.pbrMetallicRoughness.metallicRoughnessTexture, finish).toBeDefined();
    }
    const areas: number[] = [];
    model.traverse((part) => {
      if (!(part instanceof Mesh) || part.material.name !== finish) return;
      const uv = part.geometry.getAttribute('uv');
      expect(uv, finish).toBeDefined();
      const u = Array.from({ length: uv.count }, (_, i) => uv.getX(i));
      const v = Array.from({ length: uv.count }, (_, i) => uv.getY(i));
      areas.push((Math.max(...u) - Math.min(...u)) * (Math.max(...v) - Math.min(...v)));
      if (finish === 'Fubuki etched M.2 armour' || finish === 'Slate soldermask') {
        const point = new Vector3();
        let registrationError = 0;
        const bands = new Set<string>();
        for (let i = 0; i < uv.count; i++) {
          point.fromBufferAttribute(part.geometry.getAttribute('position'), i);
          part.localToWorld(point).multiplyScalar(1000);
          const rear = finish === 'Slate soldermask';
          const x = rear ? 244 * (1 - u[i]) : 9.46 + u[i] * 244.61;
          const y = rear ? v[i] * 305 : 178.15 + v[i] * 105.04;
          registrationError = Math.max(registrationError, Math.hypot(point.x - x, -point.y - y));
          if (!rear) bands.add(y < 229 ? 'chipset' : y < 253 ? 'upper SSD' : 'lower SSD');
        }
        expect(registrationError, finish).toBeLessThan(0.4);
        if (finish === 'Fubuki etched M.2 armour') expect(bands.size).toBe(3);
      }
    });
    expect(areas, finish).toHaveLength(1);
    expect(areas[0], finish).toBeGreaterThan(0.2);
  }
  expect(prints.size).toBe(5);
});
