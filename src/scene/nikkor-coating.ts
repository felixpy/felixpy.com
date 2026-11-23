import * as T from 'three';

export const coatingLayers = ['field', 'relay', 'inner', 'outer'];
export const coatingTints = ['#d0ab89', '#9dbeaa', '#bea6cf', '#ccd4ce'];

export function nikkorCoating(name: string, layer: number) {
  return new T.MeshStandardMaterial({
    name,
    color: '#030405',
    metalness: 0.08,
    roughness: layer === 3 ? 0.036 : 0.055,
    envMapIntensity: layer === 3 ? 1.15 : 0.85,
    transparent: true,
    opacity: layer === 3 ? 0.85 : 0.58,
    blending: T.AdditiveBlending,
    depthWrite: false,
    side: T.DoubleSide,
    forceSinglePass: true,
  });
}
