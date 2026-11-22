import { readFile, writeFile } from 'node:fs/promises';
import { compactProductMeshes } from './compact-product-meshes.mjs';
import { readProduct } from './static-product.mjs';

const [input, output = input] = process.argv.slice(2);
const original = await readFile(input);
for (const ratio of [0.45, 0.38, 0.32, 0.28, 0.25, 0.22, 0.19, 0.16]) {
  const product = readProduct(original);
  const packed = await compactProductMeshes(product, {
    shareGeometry: true,
    triangleRatio(mesh, material) {
      if (
        material.name === 'Printed graphite ink display' ||
        material.name === 'Lavender switch stems display' ||
        (/keycap/i.test(mesh.name) && material.name === 'Fine-grain porcelain PBT display') ||
        /codex solid/i.test(mesh.name)
      )
        return 1;
      if (/clear polycarbonate|frosted polycarbonate/i.test(material.name))
        return Math.max(ratio, 0.4);
      if (/circular base|annulus/i.test(mesh.name)) return Math.max(ratio, 0.5);
      return ratio;
    },
  });
  if (packed.length < 500_000) {
    await writeFile(output, packed);
    console.log(
      `Codex Micro packed: ${original.length} → ${packed.length} bytes (surface ratio ${ratio})`,
    );
    break;
  }
  if (ratio === 0.16) throw new Error(`Codex Micro exceeds the byte budget: ${packed.length}`);
}
