import { assembleProducts, readProduct } from '../assets/static-product.mjs';

const rules = {
  'strix-z890-a.glb': {
    omitNode: (node) =>
      node.extras?.model === 'Intel Core Ultra 9 285K' || node.extras?.installedHidden,
    omitSurface: (node, material) =>
      node.name === 'LGA1851 retention mechanism' &&
      ['Hard gold flash', 'Ferrite cores'].includes(material),
  },
  'xpg-d50-fubuki.glb': {
    omitNode: (node) =>
      [
        '288 selectively plated connector fingers',
        'Under-spreader thermal interface pads',
      ].includes(node.name),
  },
  'nikkor-z24-70-sii.glb': {
    omitSurface: (_, material) =>
      ['Z-mount contact · gold over nickel', 'Z24-70 machined bayonet · nickel plating'].includes(
        material,
      ),
  },
  'vitrine-inventory.glb': {
    omitSurface: (node, material, roots) =>
      node.extras?.opticalVariant !== undefined &&
      [
        'Z14-24 · plated CPU contacts',
        'Telephoto Z mount · plated contacts',
        '100-400 S · gold contact pads',
      ].includes(material) &&
      roots.some(
        (cap) =>
          cap.name.startsWith('LF-N1') &&
          cap.translation?.every((v, i) => v === node.translation?.[i]),
      ),
  },
};

export const installedProducts = Object.keys(rules);

export function installedProduct(file, bytes) {
  const rule = rules[file];
  if (!rule) return bytes;
  const source = readProduct(bytes);
  const { doc } = source;
  if (
    doc.scenes.length !== 1 ||
    doc.extensions ||
    doc.animations?.length ||
    doc.skins?.length ||
    doc.cameras?.length ||
    doc.nodes.some((node) => node.extensions) ||
    doc.accessors.some((accessor) => accessor.sparse) ||
    doc.meshes.some((mesh) =>
      mesh.primitives.some((primitive) => primitive.extensions || primitive.targets),
    ) ||
    doc.buffers.some((buffer) => buffer.uri) ||
    doc.images?.some((image) => image.uri)
  )
    return bytes;
  const roots = doc.scenes[doc.scene].nodes;
  const placements = roots.map((index) => doc.nodes[index]);
  const seen = new Set();
  function filterNode(index) {
    const node = doc.nodes[index];
    if (rule.omitNode?.(node)) return false;
    if (seen.has(index)) return true;
    seen.add(index);
    if (node.children) node.children = node.children.filter(filterNode);
    if (!rule.omitSurface || node.mesh === undefined) return true;
    const mesh = doc.meshes[node.mesh];
    const primitives = mesh.primitives.filter(
      (p) => !rule.omitSurface(node, doc.materials?.[p.material]?.name, placements),
    );
    if (primitives.length === mesh.primitives.length) return true;
    if (!primitives.length) delete node.mesh;
    else node.mesh = doc.meshes.push({ ...mesh, primitives }) - 1;
    return true;
  }
  return assembleProducts(
    [source],
    roots.filter(filterNode).map((index) => [source, index]),
  );
}
