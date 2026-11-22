import * as T from 'three';
import { decodeBlenderMesh } from './blender-mesh';
import { packedBuffer } from './packed-buffer';
import { unpackParts } from './blender-parts';

export async function loadBlenderPack(
  manager: T.LoadingManager,
  url: string,
  add: (name: string, geometry: T.BufferGeometry) => void,
) {
  manager.itemStart(url);
  try {
    const response = await fetch(url);
    const buffer = await packedBuffer(response);
    for (const [name, bytes] of unpackParts(buffer)) add(name, decodeBlenderMesh(bytes));
  } catch (error) {
    manager.itemError(url);
    throw error;
  } finally {
    manager.itemEnd(url);
  }
}
