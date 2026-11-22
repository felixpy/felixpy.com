import { expect, test } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import { assembleProducts, readProduct } from '../scripts/assets/static-product.mjs';

function describeScene(bytes, keepNode = () => true, keepSurface = () => true) {
  const { doc, data } = readProduct(bytes);
  function bufferView(index) {
    const view = structuredClone(doc.bufferViews[index]);
    const packed = view.extensions?.EXT_meshopt_compression;
    const range = packed ?? view;
    const begin = range.byteOffset ?? 0;
    const hash = createHash('sha256')
      .update(data.subarray(begin, begin + range.byteLength))
      .digest('hex');
    delete range.byteOffset;
    delete view.byteOffset;
    return { view, hash };
  }
  function accessor(index) {
    const a = doc.accessors[index];
    return { ...a, bufferView: bufferView(a.bufferView) };
  }
  function image(index) {
    const entry = doc.images[index];
    return { ...entry, bufferView: bufferView(entry.bufferView) };
  }
  function texture(index) {
    const t = structuredClone(doc.textures[index]);
    if (t.source !== undefined) t.source = image(t.source);
    if (t.sampler !== undefined) t.sampler = doc.samplers[t.sampler];
    for (const ext of Object.values(t.extensions ?? {}))
      if (ext.source !== undefined) ext.source = image(ext.source);
    return t;
  }
  function material(entry) {
    return Object.fromEntries(
      Object.entries(entry).map(([key, value]) => {
        if (key.endsWith('Texture')) return [key, { ...value, index: texture(value.index) }];
        if (value && typeof value === 'object' && !Array.isArray(value))
          return [key, material(value)];
        return [key, value];
      }),
    );
  }
  function node(index) {
    const part = structuredClone(doc.nodes[index]);
    if (part.children)
      part.children = part.children.filter((i) => keepNode(doc.nodes[i])).map(node);
    if (part.mesh !== undefined) {
      const mesh = structuredClone(doc.meshes[part.mesh]);
      mesh.primitives = mesh.primitives.filter((p) =>
        keepSurface(part, doc.materials[p.material].name),
      );
      for (const p of mesh.primitives) {
        p.material = material(doc.materials[p.material]);
        p.indices = accessor(p.indices);
        for (const key of Object.keys(p.attributes))
          p.attributes[key] = accessor(p.attributes[key]);
      }
      if (mesh.primitives.length) part.mesh = mesh;
      else delete part.mesh;
    }
    return part;
  }
  const scene = doc.scenes[doc.scene];
  return { ...scene, nodes: scene.nodes.filter((i) => keepNode(doc.nodes[i])).map(node) };
}

const assemblies = [
  {
    file: 'strix-z890-a',
    keepNode: (n) =>
      !['Installed Intel Core Ultra 9 285K', 'Solder tails beneath the four DIMM slots'].includes(
        n.name,
      ),
    keepSurface: (n, m) =>
      n.name !== 'LGA1851 retention mechanism' || !['Hard gold flash', 'Ferrite cores'].includes(m),
  },
  {
    file: 'xpg-d50-fubuki',
    keepNode: (n) =>
      ![
        '288 selectively plated connector fingers',
        'Under-spreader thermal interface pads',
      ].includes(n.name),
  },
  {
    file: 'nikkor-z24-70-sii',
    keepSurface: (_, m) =>
      !['Z24-70 machined bayonet · nickel plating', 'Z-mount contact · gold over nickel'].includes(
        m,
      ),
  },
  {
    file: 'vitrine-inventory',
    keepSurface: (n, m) =>
      ![0, 2, 4, 5].includes(n.extras?.opticalVariant) ||
      ![
        'Z14-24 · plated CPU contacts',
        'Telephoto Z mount · plated contacts',
        '100-400 S · gold contact pads',
      ].includes(m),
  },
];

for (const { file, keepNode, keepSurface } of assemblies) {
  test(
    file + ' ships the visible assembly with identical geometry, texture and placement',
    async ({ request }) => {
      const path = '/media/models/' + file + '.glb';
      const complete = await readFile('public' + path);
      const response = await request.get(path + '.gz');
      expect(response.ok()).toBe(true);
      const installed = gunzipSync(await response.body());
      expect(installed.length).toBeLessThan(complete.length);
      expect(describeScene(installed)).toEqual(describeScene(complete, keepNode, keepSurface));
    },
  );
}

test('each Tongshifu casting fits in 1 MB at its original cabinet proportions', async () => {
  const inventory = readProduct(await readFile('public/media/models/vitrine-inventory.glb'));
  const { doc } = inventory;
  const castings = [
    {
      name: 'Sun Wukong · The Great Victory',
      dimensions: [0.145, 0.265, 0.11],
      displayHeight: 0.265,
    },
    { name: 'Tongshifu · Iron Man Mark 85', dimensions: [0.25, 0.42, 0.18], displayHeight: 0.26 },
  ];
  for (const { name, dimensions, displayHeight } of castings) {
    const index = doc.scenes[doc.scene].nodes.find(
      (i) => doc.nodes[i].extras?.cabinetItem === name,
    );
    expect(index, name).toBeDefined();
    const item = doc.nodes[index];
    expect(assembleProducts([inventory], [[inventory, index]]).length, name).toBeLessThan(
      1_000_000,
    );
    const scale = item.scale ?? [1, 1, 1];
    const extents = doc.meshes[item.mesh].primitives.map(
      (p) => doc.accessors[p.attributes.POSITION],
    );
    const min = [0, 1, 2].map((axis) => Math.min(...extents.map((a) => a.min[axis])));
    const max = [0, 1, 2].map((axis) => Math.max(...extents.map((a) => a.max[axis])));
    for (const [axis, expected] of dimensions.entries()) {
      expect(max[axis] - min[axis]).toBeCloseTo(expected, 4);
      expect(scale[axis]).toBeCloseTo(displayHeight / dimensions[1], 4);
    }
    const bottom = item.translation[1] + min[1] * scale[1];
    const top = item.translation[1] + max[1] * scale[1];
    expect(bottom).toBeCloseTo(0.52, 4);
    expect(top - bottom).toBeCloseTo(displayHeight, 4);
    expect(0.965 - top).toBeGreaterThan(0.17);
  }
});
