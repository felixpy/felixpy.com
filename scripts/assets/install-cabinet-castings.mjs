import { readFile, writeFile } from 'node:fs/promises';
import { assembleProducts, readProduct } from './static-product.mjs';

const [input, output] = process.argv.slice(2);
const cabinet = readProduct(await readFile(input));
const sources = [cabinet];
const roots = cabinet.doc.scenes[cabinet.doc.scene].nodes.map((index) => [cabinet, index]);

for (const file of ['great-sage.glb', 'mk85.glb']) {
  const bytes = await readFile(new URL('./cabinet-castings/' + file, import.meta.url));
  if (bytes.length >= 1_000_000) throw new Error(file + ' exceeds its display budget');
  const casting = readProduct(bytes);
  const nodes = casting.doc.scenes[casting.doc.scene].nodes;
  const root = casting.doc.nodes[nodes[0]];
  if (nodes.length !== 1 || root.mesh === undefined || root.children?.length)
    throw new Error('Expected one display mesh in ' + file);
  const slot = roots.findIndex(
    ([source, index]) =>
      source === cabinet && cabinet.doc.nodes[index].extras?.cabinetItem === root.name,
  );
  if (slot === -1) throw new Error('Missing cabinet placement for ' + root.name);
  const placement = cabinet.doc.nodes[roots[slot][1]];
  if (placement.children?.length) throw new Error('Expected one cabinet mesh for ' + root.name);
  casting.doc.nodes[nodes[0]] = { ...placement, mesh: root.mesh };
  sources.push(casting);
  roots[slot] = [casting, nodes[0]];
}

await writeFile(output, assembleProducts(sources, roots), { flag: 'wx' });
