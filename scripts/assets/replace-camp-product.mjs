import { readFile, writeFile } from 'node:fs/promises';
import { assembleProducts, readProduct } from './static-product.mjs';

const [file, replacement, key] = process.argv.slice(2);
const [base, update] = await Promise.all(
  [file, replacement].map(async (path) => readProduct(await readFile(path))),
);
const matchingRoots = ({ doc }) =>
  doc.scenes[doc.scene].nodes.filter((i) => doc.nodes[i].extras?.campProduct === key);
const oldRoots = matchingRoots(base),
  newRoots = matchingRoots(update);
if (oldRoots.length !== 1 || newRoots.length !== 1)
  throw Error('Expected one installed and one replacement product');
const roots = base.doc.scenes[base.doc.scene].nodes.map((i) =>
  i === oldRoots[0] ? [update, newRoots[0]] : [base, i],
);
await writeFile(file, assembleProducts([base, update], roots));
