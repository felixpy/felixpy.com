import { readFile, writeFile } from 'node:fs/promises';
import { compactProductMeshes } from './compact-product-meshes.mjs';
import { assembleProducts, readProduct } from './static-product.mjs';

const [input, output = input] = process.argv.slice(2);
const source = readProduct(await readFile(input));
const roots = source.doc.scenes[source.doc.scene].nodes;
const pack = roots.find((i) => source.doc.nodes[i].name.startsWith('Osprey Talon 26'));
const tent = roots.find((i) => source.doc.nodes[i].name.startsWith('Snow Peak SD-641'));
if (pack === undefined || tent === undefined) throw new Error('Missing field kit bag');
source.doc.nodes[tent].translation[0] = 0;
const trimmed = assembleProducts(
  [source],
  [
    [source, pack],
    [source, tent],
  ],
);
const result = await compactProductMeshes(readProduct(trimmed));
if (result.length >= 1_000_000)
  throw new Error(`Field kit exceeds the byte budget: ${result.length}`);
await writeFile(output, result);
