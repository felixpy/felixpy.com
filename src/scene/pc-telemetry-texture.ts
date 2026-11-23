import { DataTexture, RGBAFormat, UnsignedByteType, type CanvasTexture, type Texture } from 'three';

export function pcTelemetryTexture(source: CanvasTexture, context: CanvasRenderingContext2D) {
  let typed: { texture: DataTexture; pixels: Uint8Array<ArrayBuffer> } | undefined;

  return (useTyped = false): Texture => {
    if (!useTyped) {
      typed?.texture.dispose();
      typed = undefined;
      source.needsUpdate = true;
      return source;
    }

    const { width, height } = source.image;
    const rgba = context.getImageData(0, 0, width, height).data;
    if (!typed) {
      const pixels = new Uint8Array(rgba.length);
      const texture = new DataTexture(pixels, width, height, RGBAFormat, UnsignedByteType);
      texture.mapping = source.mapping;
      texture.wrapS = source.wrapS;
      texture.wrapT = source.wrapT;
      texture.magFilter = source.magFilter;
      texture.minFilter = source.minFilter;
      texture.anisotropy = source.anisotropy;
      texture.colorSpace = source.colorSpace;
      texture.generateMipmaps = source.generateMipmaps;
      texture.mipmapsAutoUpdate = source.mipmapsAutoUpdate;
      texture.premultiplyAlpha = source.premultiplyAlpha;
      texture.unpackAlignment = source.unpackAlignment;
      typed = { texture, pixels };
      source.dispose();
    }

    const stride = width * 4;
    for (let row = 0; row < height; row++) {
      const sourceRow = source.flipY ? height - 1 - row : row;
      const start = sourceRow * stride;
      typed.pixels.set(rgba.subarray(start, start + stride), row * stride);
    }
    typed.texture.needsUpdate = true;
    return typed.texture;
  };
}
