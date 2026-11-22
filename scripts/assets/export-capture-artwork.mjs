import path from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const output = path.resolve('.review/atelier/capture-controls/artwork');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage();
  await page.goto(new URL('/media/credits.txt', process.argv[2] ?? 'http://127.0.0.1:5173').href);
  const graphics = await page.evaluate(async (selected) => {
    const [{ galleryDisplay }, { materials }, { loadParts }, { display }, T, { GLTFExporter }] =
      await Promise.all([
        import('/src/scene/gallery-display.ts'),
        import('/src/scene/materials.ts'),
        import('/src/scene/blender-library.ts'),
        import('/src/scene/layout.ts'),
        import('/node_modules/three/build/three.module.js'),
        import('/node_modules/three/examples/jsm/exporters/GLTFExporter.js'),
      ]);
    await loadParts('studio');
    const assembly = new T.Group();
    galleryDisplay(
      assembly,
      materials(new T.TextureLoader()),
      display.outerHeight,
      display.y,
      new T.LoadingManager(),
      assembly,
    );
    assembly.updateMatrixWorld(true);
    const devices = [
      ['screenbar-halo-2', 'ScreenBar Halo 2 and hinged counterweight', ['Product inscription']],
      ['halo-controller', 'Wireless light controller', ['Capacitive touch display']],
    ];
    const results = [];
    for (const [file, name, labels] of devices) {
      if (selected && file !== selected) continue;
      const device = assembly.getObjectByName(name);
      const artwork = new T.Group();
      artwork.name = 'Face artwork';
      const toDevice = device.matrixWorld.clone().invert();
      device.traverse((part) => {
        if (!(part.isMesh && part.material.map?.image instanceof HTMLCanvasElement)) return;
        const face = part.clone(false);
        face.name = labels[artwork.children.length];
        const local = toDevice.clone().multiply(part.matrixWorld);
        local.decompose(face.position, face.quaternion, face.scale);
        artwork.add(face);
      });
      if (artwork.children.length !== labels.length)
        throw Error('Missing face artwork for ' + name);
      const data = await new GLTFExporter().parseAsync(artwork, { binary: true });
      const url = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(new Blob([data]));
      });
      results.push([file, url.split(',')[1]]);
    }
    return results;
  }, process.argv[3]);
  for (const [file, encoded] of graphics) {
    await writeFile(path.join(output, file + '.glb'), Buffer.from(encoded, 'base64'));
  }
} finally {
  await browser.close();
}
