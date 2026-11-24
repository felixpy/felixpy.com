import * as T from 'three';

export function decodePmrem(buffer: ArrayBuffer): T.CompressedCubeTexture {
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  if (
    bytes.length < 12 ||
    bytes[0] !== 0x50 ||
    bytes[1] !== 0x4d ||
    bytes[2] !== 0x52 ||
    bytes[3] !== 0x32
  ) {
    throw new Error('Invalid PMR2 offline PMREM header');
  }
  const baseSize = view.getUint16(4, true);
  const mipCount = view.getUint16(6, true);
  const faceMips: Array<Array<{ data: Uint16Array; width: number; height: number }>> = Array.from(
    { length: 6 },
    () => [],
  );
  const alphaHalf = T.DataUtils.toHalfFloat(1);
  let offset = 12;
  for (let m = 0; m < mipCount; m++) {
    const dim = Math.max(1, baseSize >> m);
    const n = dim * dim;
    for (let face = 0; face < 6; face++) {
      const rPlane = new Uint8Array(n);
      const gPlane = new Uint8Array(n);
      const bPlane = new Uint8Array(n);
      const ePlane = new Uint8Array(n);
      for (const plane of [rPlane, gPlane, bPlane, ePlane]) {
        let prev = 0;
        for (let i = 0; i < n; i++) {
          prev = (prev + bytes[offset++]) & 0xff;
          plane[i] = prev;
        }
      }
      const half = new Uint16Array(n * 4);
      for (let i = 0; i < n; i++) {
        const e = ePlane[i];
        const j = i * 4;
        if (e > 0) {
          const scale = 2 ** (e - 136);
          half[j] = T.DataUtils.toHalfFloat(rPlane[i] * scale);
          half[j + 1] = T.DataUtils.toHalfFloat(gPlane[i] * scale);
          half[j + 2] = T.DataUtils.toHalfFloat(bPlane[i] * scale);
        }
        half[j + 3] = alphaHalf;
      }
      faceMips[face].push({ data: half, width: dim, height: dim });
    }
  }
  const images = faceMips.map((mipmaps) => ({
    isCompressedTexture: true,
    mipmaps,
    width: baseSize,
    height: baseSize,
  }));
  const cube = new T.CompressedCubeTexture(
    images as unknown as T.CompressedTexture[],
    T.RGBAFormat as unknown as T.CompressedPixelFormat,
    T.HalfFloatType,
  );
  cube.name = 'PMREM';
  cube.colorSpace = T.LinearSRGBColorSpace;
  cube.mapping = T.CubeReflectionMapping;
  cube.minFilter = T.LinearMipmapLinearFilter;
  cube.magFilter = T.LinearFilter;
  cube.generateMipmaps = false;
  cube.flipY = false;
  const internal = cube as unknown as { isPMREMTexture: boolean; isRenderTargetTexture: boolean };
  internal.isPMREMTexture = true;
  internal.isRenderTargetTexture = true;
  cube.needsUpdate = true;
  return cube;
}
