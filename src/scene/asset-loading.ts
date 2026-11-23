import { LoadingManager } from 'three';
import { assetUrl } from '../app/asset-url';

export function createStudioLoadingManager() {
  return new LoadingManager().setURLModifier(assetUrl);
}

export const defaultStudioLoadingManager = createStudioLoadingManager();
