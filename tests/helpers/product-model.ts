import { readFile } from 'node:fs/promises';
import { MeshBasicMaterial } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

export async function productModel(filename: string) {
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  loader.register((parser) => ({
    name: 'GeometryOnly',
    async loadMaterial(index) {
      const material = new MeshBasicMaterial();
      material.name = parser.json.materials[index].name;
      return material;
    },
  }));
  const bytes = Uint8Array.from(await readFile('public/media/models/' + filename));
  return (await loader.parseAsync(bytes.buffer, '')).scene;
}
