import * as T from 'three';

export const coatingLayers = ['field', 'relay', 'inner', 'outer'];
export const coatingTints = ['#d0ab89', '#9dbeaa', '#bea6cf', '#ccd4ce'];

export function nikkorCoating(name: string, layer: number) {
  return new T.MeshPhysicalMaterial({
    name,
    color: '#030405',
    metalness: 0,
    roughness: layer === 3 ? 0.036 : 0.055,
    ior: 1.57,
    specularColor: coatingTints[layer],
    specularIntensity: layer === 3 ? 0.8 : 0.57,
    iridescence: 0.1,
    iridescenceIOR: 1.38,
    iridescenceThicknessMinimum: 230,
    iridescenceThicknessMaximum: 282,
    transparent: true,
    opacity: layer === 3 ? 0.85 : 0.58,
    blending: T.AdditiveBlending,
    depthWrite: false,
    side: T.DoubleSide,
    forceSinglePass: true,
  });
}
