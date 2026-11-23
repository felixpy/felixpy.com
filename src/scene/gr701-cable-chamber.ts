import * as T from 'three';
import { blenderMesh } from './blender-mesh';
import { group, mesh, surface } from './geometry';
import type { ProductDetail } from './product-detail';

export function cableChamber(chassis: T.Group, door: T.Group, details: ProductDetail) {
  const bay = group(chassis, 'GR701 rear cable-management chamber');
  const steel = surface('#42464d', 0.47, 0.48);
  const smoke = new T.MeshPhysicalMaterial({
    color: '#383c43',
    metalness: 0.04,
    roughness: 0.28,
    clearcoat: 0.32,
    transparent: true,
    opacity: 0.54,
    depthWrite: false,
  });
  const finishes = {
    drive: surface('#212327', 0.46, 0.54),
    steel,
    smoke,
    polymer: surface('#333638', 0.54, 0.08),
    wire: surface('#37383b', 0.49, 0.03),
    contact: surface('#b5a38b', 0.37, 0.63),
    print: surface('#797c83', 0.42, 0.37),
    trim: surface('#323439', 0.5, 0.22),
  };
  for (const [finish, material] of Object.entries(finishes)) {
    const part = mesh(
      finish === 'trim' ? door : bay,
      blenderMesh('gr701-cable-bay-' + finish),
      material,
    );
    part.name = 'GR701 cable bay · ' + finish;
    if (finish === 'contact') details.close(part);
    if (finish === 'print' || finish === 'smoke' || finish === 'contact') part.castShadow = false;
    if (finish === 'smoke') part.renderOrder = 1;
  }
}

export function fitFrontCheeks(chassis: T.Group, door: T.Group, material: T.Material) {
  const full = blenderMesh('gr701-fascia-wing');
  const position = full.getAttribute('position');
  const source = full.getIndex()!;
  const indices: [number[], number[]] = [[], []];
  for (let i = 0; i < source.count; i += 3) {
    const a = source.getX(i);
    indices[position.getX(a) > 0 ? 1 : 0].push(a, source.getX(i + 1), source.getX(i + 2));
  }
  for (const [side, vertices] of indices.entries()) {
    const geometry = new T.BufferGeometry();
    Object.assign(geometry.attributes, full.attributes);
    geometry.setIndex(vertices);
    const bounds = new T.Box3();
    const p = new T.Vector3();
    for (const index of vertices) bounds.expandByPoint(p.fromBufferAttribute(position, index));
    geometry.boundingBox = bounds;
    geometry.boundingSphere = bounds.getBoundingSphere(new T.Sphere());
    geometry.name = full.name;
    const cheek = mesh(side ? door : chassis, geometry, material);
    cheek.name = side ? 'GR701 starboard unlettered intake cheek' : 'GR701 front assembly · wing';
  }
}
