import { Box3, Vector3, type Camera, type DepthTexture, type Scene } from 'three';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { roomSize, windowOpening } from './layout';

export function roomOcclusion(scene: Scene, camera: Camera, depthTexture: DepthTexture) {
  const pass = new GTAOPass(scene, camera, 1, 1, { depthTexture });
  pass.setSceneClipBox(
    new Box3(
      new Vector3(roomSize.west, 0, roomSize.north),
      new Vector3(roomSize.east, roomSize.ceiling, roomSize.south),
    ).expandByScalar(windowOpening.thickness),
  );
  pass.updateGtaoMaterial({ radius: 0.145, thickness: 0.08, scale: 1.1, samples: 12 });
  pass.updatePdMaterial({ radius: 4, rings: 2, samples: 10 });
  pass.blendIntensity = 0.66;
  return pass;
}
