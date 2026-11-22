import { expect, test } from '@playwright/test';
import * as T from 'three';
import {
  encodeRoomFrameMarker,
  roomFrameMarker,
  roomFrameMarkerRoi,
} from '../src/scene/room-frame-marker';

function witnessBytes(payload: number, checksum: number) {
  const bytes = new Uint8Array(5);
  const { width } = roomFrameMarkerRoi;
  for (let pixel = 0; pixel < width; pixel++) {
    const cell = Math.floor(pixel / 4);
    const value = cell < 32 ? payload >>> (31 - cell) : checksum >>> (39 - cell);
    if (pixel % 4 === 2) bytes[cell >> 3] = (bytes[cell >> 3] << 1) | (value & 1);
  }
  return bytes;
}

test('canvas marker wire order matches the DXGI witness', () => {
  const { payload, checksum } = encodeRoomFrameMarker(0x123456);
  expect(payload).toBe(0xd7123456);
  expect(checksum).toBe(0xd3);
  expect([...witnessBytes(payload, checksum)]).toEqual([0xd7, 0x12, 0x34, 0x56, 0xd3]);
  for (const serial of [0, 1, 0x800001, 0xffffff]) {
    const encoded = encodeRoomFrameMarker(serial);
    const [sync, high, middle, low, crc] = witnessBytes(encoded.payload, encoded.checksum);
    expect(sync).toBe(0xd7);
    expect((high << 16) | (middle << 8) | low).toBe(serial);
    expect(crc).toBe(encoded.checksum);
  }
  expect(() => encodeRoomFrameMarker(-1)).toThrow(RangeError);
  expect(() => encodeRoomFrameMarker(0x1000000)).toThrow(RangeError);
});

test('canvas marker draws, repeats the same wire value on hold, and restores renderer state', () => {
  const marker = roomFrameMarker();
  const width = 3840;
  const height = 2160;
  const { x, y, width: regionWidth, height: regionHeight } = roomFrameMarkerRoi;
  expect(roomFrameMarkerRoi).toEqual({ x: 32, y: 32, width: 160, height: 4 });

  let target: T.WebGLRenderTarget | null = null;
  let cropped = false;
  let fail = false;
  const rendered: T.RawShaderMaterial[] = [];
  const renderer = {
    autoClear: true,
    xr: { isPresenting: false },
    getRenderTarget: () => target,
    getScissorTest: () => false,
    getContext: () => ({ drawingBufferWidth: width, drawingBufferHeight: height }),
    getCurrentViewport: (viewport: T.Vector4) =>
      viewport.set(0, 0, width - Number(cropped), height),
    render(mesh: T.Mesh<T.PlaneGeometry, T.RawShaderMaterial>) {
      expect(this.autoClear).toBe(false);
      expect(mesh.geometry.index?.count).toBe(6);
      rendered.push(mesh.material);
      if (fail) throw new Error('Draw interrupted');
    },
  };
  const gl = renderer as unknown as T.WebGLRenderer;
  expect(marker.draw(gl)).toBe(1);
  expect(rendered).toHaveLength(1);
  expect(renderer.autoClear).toBe(true);

  const [material] = rendered;
  const points = (material.uniforms.markerBounds.value as T.Vector4).toArray().map(Math.fround);
  expect(((points[0] + 1) * width) / 2).toBeCloseTo(x, 3);
  expect(((1 - points[3]) * height) / 2).toBeCloseTo(y, 3);
  expect(((points[2] + 1) * width) / 2).toBeCloseTo(x + regionWidth, 3);
  expect(((1 - points[1]) * height) / 2).toBeCloseTo(y + regionHeight, 3);
  expect(material.blending).toBe(T.NoBlending);
  expect(material.depthTest || material.depthWrite || material.toneMapped).toBe(false);
  expect(material.uniforms.markerPayload.value).toBe(0xd7000001);
  const checksum = material.uniforms.markerChecksum.value;
  expect(marker.draw(gl, true)).toBe(1);
  expect(material.uniforms.markerPayload.value).toBe(0xd7000001);
  expect(material.uniforms.markerChecksum.value).toBe(checksum);

  target = new T.WebGLRenderTarget(1, 1);
  expect(marker.draw(gl)).toBeUndefined();
  target.dispose();
  target = null;
  cropped = true;
  expect(marker.draw(gl)).toBeUndefined();
  expect(rendered).toHaveLength(2);
  cropped = false;
  fail = true;
  expect(() => marker.draw(gl)).toThrow('Draw interrupted');
  expect(renderer.autoClear).toBe(true);
  fail = false;
  expect(marker.draw(gl)).toBe(2);
  marker.dispose();
});
