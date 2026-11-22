import path from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const root = path.resolve('.review/atelier/pc-components/interchange');
await mkdir(root, { recursive: true });
const browser = await chromium.launch({
  channel: 'chrome',
  args: ['--enable-gpu', '--use-angle=d3d11'],
});
try {
  const page = await browser.newPage();
  await page.exposeFunction('writePart', async (key, base64) => {
    await writeFile(path.join(root, key + '.glb'), Buffer.from(base64, 'base64'));
  });
  await page.goto(new URL('/media/credits.txt', process.argv[2] ?? 'http://127.0.0.1:5173').href);
  const manifest = await page.evaluate(async () => {
    const [{ tower }, { materials }, { loadParts }, T, { GLTFExporter }] = await Promise.all([
      import('/src/scene/hardware.ts'),
      import('/src/scene/materials.ts'),
      import('/src/scene/blender-library.ts'),
      import('/node_modules/three/build/three.module.js'),
      import('/node_modules/three/examples/jsm/exporters/GLTFExporter.js'),
    ]);
    await loadParts('studio');
    const manager = new T.LoadingManager();
    const ready = new Promise((resolve) => (manager.onLoad = resolve));
    const palette = materials(new T.TextureLoader(manager));
    const aura = ['#d7a2e6', '#b6a4d2', '#9fabeb', '#88bcd9', '#68c1cf', '#88cbd4', '#aaadec'].map(
      (color) =>
        new T.MeshStandardMaterial({ color: '#d3d6db', emissive: color, emissiveIntensity: 0.32 }),
    );
    const { unit } = tower(new T.Group(), palette, aura, manager);
    await ready;
    unit.position.set(0, 0, 0);
    unit.rotation.set(0, 0, 0);
    unit.updateMatrixWorld(true);
    const find = (term) => {
      const match = unit.getObjectByName(term);
      if (!match) throw Error('Missing component: ' + term);
      return match;
    };
    const all = (term) => unit.getObjectsByProperty('name', term);
    const gpu = find('ROG Astral GeForce RTX 5090 · PCIe 5.0 slot');
    const harness = find('Seated 12V-2x6 power and sense loom');
    const chassis = find('ROG Hyperion GR701 chassis');
    const psu = find('ROG power supply in rear cradle');
    const support = find('ROG Herculx XH01');
    const rad = find('ROG offset-flow 394 × 140 × 32 mm radiator');
    const fans = all('MF-12C · daisy-chained 120 mm');
    const strix = all('ROG Strix Fan Model 14 ARGB');
    const pump = find('ROG Ryuo IV · curved 6.67-inch AMOLED and cold plate');
    const dimm = find('XPG D50 Fubuki DDR5 memory bank').children;
    const frontRotors = Array.from({ length: 3 }, (_, i) =>
      find('Axial-tech intake ' + (i + 1)).getObjectByName('Fan rotor'),
    );
    const gpuRotors = [
      ...frontRotors,
      find('Fourth pass-through fan').getObjectByName('Fan rotor'),
    ];
    const parts = [];
    function add(key, name, sources, options = {}) {
      const anchor = options.anchor ?? sources[0].matrixWorld;
      const basis = options.parent ?? new T.Matrix4();
      const lifts = options.mounts ?? [anchor];
      parts.push({
        key,
        name,
        sources,
        anchor,
        omit: options.omit ?? [],
        offsets: lifts.map((lift) => basis.clone().invert().multiply(lift).toArray()),
        owner: options.owner ?? null,
        labels: options.labels ?? [],
      });
    }
    add('hyperion-gr701', 'ROG Hyperion GR701', [chassis], { omit: [psu] });
    add('rog-herculx-xh01', 'ROG Herculx XH01', [support]);
    add('thor-psu', 'ROG Thor 1600W Titanium III', [psu]);
    add('astral-5090', 'ROG Astral RTX 5090', [gpu, find('ROG Astral · close inspection')], {
      omit: [harness, ...gpuRotors],
    });
    add('astral-axial-fan', 'Astral axial-tech impeller', [gpuRotors[0]], {
      mounts: [gpuRotors[0], gpuRotors[2], gpuRotors[3]].map((n) => n.matrixWorld),
      parent: gpu.matrixWorld,
      owner: 'astral-5090',
      labels: ['Intake I', 'Intake III', 'Fourth pass-through'],
    });
    add('astral-axial-counter-fan', 'Astral counter-rotating axial-tech impeller', [gpuRotors[1]], {
      parent: gpu.matrixWorld,
      owner: 'astral-5090',
      labels: ['Intake II'],
    });
    add('astral-12v2x6', '12V-2x6 GPU harness', [harness]);
    add('ryuo-pump', 'Ryuo IV SLC 360 pump', [pump]);
    add('ryuo-radiator', 'Ryuo IV 394 mm offset radiator', [rad], { omit: fans });
    add('ryuo-mf12c', 'ROG MF-12C 120 mm', [fans[0]], {
      mounts: [fans[0].matrixWorld, fans[2].matrixWorld],
      labels: ['Rear radiator fan', 'Forward radiator fan'],
    });
    add('ryuo-mf12c-centre', 'ROG MF-12C 120 mm centre rail', [fans[1]], {
      labels: ['Middle radiator fan'],
    });
    add(
      'ryuo-fep',
      '200 mm FEP tube pair',
      [
        'Two 200 mm FEP lines with opal diffusing sleeves',
        'Pump and offset manifold compression ferrules',
        'Fitting lands',
      ].map(find),
    );
    add('strix-fan-140', 'ROG Strix Fan Model 14', [strix[0]], {
      mounts: strix.map((n) => n.matrixWorld),
      labels: ['Front intake lower', 'Front intake centre', 'Front intake upper', 'Rear exhaust'],
    });
    add('atx-24pin', '24-pin ATX harness', [
      find('24-pin ATX braided loom and retaining comb'),
      find('Fully seated Mini-Fit Jr connector'),
    ]);
    add('eps-12v', 'Twin EPS12V processor harness', [find('Twin 8-pin EPS12V processor supply')]);
    add('xpg-d50-fubuki', 'XPG D50 ROG Strix Fubuki DDR5', [dimm[0]], {
      mounts: dimm.map((n) => n.matrixWorld),
      labels: dimm.map((n) => n.userData.memorySocket),
    });
    function duplicate(node, part) {
      if (part.omit.includes(node) || node.isLight) return null;
      let copy;
      if (node.isInstancedMesh) {
        copy = new T.Group();
        const matrix = new T.Matrix4();
        for (let i = 0; i < node.count; i++) {
          node.getMatrixAt(i, matrix);
          const child = new T.Mesh(node.geometry, node.material);
          child.name = (node.name || 'Repeated detail') + ' ' + (i + 1);
          if (node.geometry.name) child.userData.nativePart = node.geometry.name;
          child.applyMatrix4(matrix);
          copy.add(child);
        }
      } else if (node.isMesh) {
        copy = new T.Mesh(node.geometry, node.material);
        if (node.geometry.name) copy.userData.nativePart = node.geometry.name;
      } else copy = new T.Group();
      copy.name = node.name || (node.isMesh ? node.geometry.type : 'Subassembly');
      for (const child of node.children) {
        const sub = duplicate(child, part);
        if (sub) {
          sub.applyMatrix4(child.matrix);
          copy.add(sub);
        }
      }
      return copy;
    }
    const exporter = new GLTFExporter();
    for (const part of parts) {
      const top = new T.Group();
      top.name = part.name;
      for (const node of part.sources) {
        const item = duplicate(node, part);
        item.applyMatrix4(part.anchor.clone().invert().multiply(node.matrixWorld));
        top.add(item);
      }
      const bytes = await exporter.parseAsync(top, {
        binary: true,
        onlyVisible: false,
        trs: true,
        maxTextureSize: 1024,
      });
      const uri = await new Promise((resolve) => {
        const f = new FileReader();
        f.onload = () => resolve(f.result);
        f.readAsDataURL(new Blob([bytes]));
      });
      await window.writePart(part.key, uri.split(',')[1]);
    }
    return parts.map(({ key, name, owner, offsets, labels }) => ({
      key,
      name,
      owner,
      offsets,
      labels,
    }));
  });
  await writeFile(path.join(root, 'assembly.json'), JSON.stringify(manifest, null, 2));
} finally {
  await browser.close();
}
