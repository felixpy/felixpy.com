import * as T from 'three';

const cellSize = 4;
const cellCount = 40;
const serialMask = 0xffffff;
const syncByte = 0xd7;

export const roomFrameMarkerRoi = {
  x: 32,
  y: 32,
  width: cellCount * cellSize,
  height: cellSize,
} as const;

export function encodeRoomFrameMarker(serial: number) {
  if (!Number.isInteger(serial) || serial < 0 || serial > serialMask)
    throw new RangeError('The frame marker serial must be a 24-bit unsigned integer.');

  const payload = ((syncByte << 24) | serial) >>> 0;
  let checksum = 0;
  for (let shift = 24; shift >= 0; shift -= 8) {
    checksum ^= (payload >>> shift) & 0xff;
    for (let bit = 0; bit < 8; bit++) {
      checksum = ((checksum << 1) ^ (checksum & 0x80 ? 0x07 : 0)) & 0xff;
    }
  }
  return { payload, checksum };
}

export function roomFrameMarker() {
  const control = (
    globalThis as typeof globalThis & {
      studioPresentWitness?: { hold: boolean; held: boolean; serial: number };
    }
  ).studioPresentWitness;
  const roi = roomFrameMarkerRoi;
  const viewport = new T.Vector4();
  const bounds = new T.Vector4();
  const uniforms = {
    markerBounds: { value: bounds },
    markerPayload: { value: 0 },
    markerChecksum: { value: 0 },
  };
  const material = new T.RawShaderMaterial({
    name: 'Studio canvas frame marker',
    glslVersion: T.GLSL3,
    uniforms,
    vertexShader: `
      precision highp float;
      in vec3 position;
      uniform vec4 markerBounds;
      void main() {
        vec2 point = mix(markerBounds.xy, markerBounds.zw, position.xy + 0.5);
        gl_Position = vec4(point, 0.0, 1.0);
      }
    `,
    fragmentShader: `
      precision highp float;
      precision highp int;
      uniform uint markerPayload;
      uniform uint markerChecksum;
      out vec4 markerColor;
      void main() {
        uint cell = uint((int(gl_FragCoord.x) - ${roi.x}) / ${cellSize});
        uint value = cell < 32u ? markerPayload >> (31u - cell) : markerChecksum >> (39u - cell);
        markerColor = vec4(vec3(float(value & 1u)), 1.0);
      }
    `,
    blending: T.NoBlending,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
  });
  const geometry = new T.PlaneGeometry(1, 1);
  const marker = new T.Mesh(geometry, material);
  marker.frustumCulled = false;
  const camera = new T.Camera();
  let serial = 0;

  return {
    get holdRequested() {
      return control?.hold === true;
    },
    draw(renderer: T.WebGLRenderer, held = false) {
      if (renderer.getRenderTarget() || renderer.getScissorTest() || renderer.xr.isPresenting)
        return;
      const context = renderer.getContext();
      const width = context.drawingBufferWidth;
      const height = context.drawingBufferHeight;
      renderer.getCurrentViewport(viewport);
      if (
        width < roi.x + roi.width ||
        height < roi.y + roi.height ||
        viewport.x !== 0 ||
        viewport.y !== 0 ||
        viewport.z !== width ||
        viewport.w !== height
      )
        return;

      bounds.set(
        (2 * roi.x) / width - 1,
        1 - (2 * (roi.y + roi.height)) / height,
        (2 * (roi.x + roi.width)) / width - 1,
        1 - (2 * roi.y) / height,
      );
      const next = held ? serial : (serial + 1) & serialMask;
      const { payload, checksum } = encodeRoomFrameMarker(next);
      uniforms.markerPayload.value = payload;
      uniforms.markerChecksum.value = checksum;

      const autoClear = renderer.autoClear;
      renderer.autoClear = false;
      try {
        renderer.render(marker, camera);
      } finally {
        renderer.autoClear = autoClear;
      }
      serial = next;
      if (control) {
        control.serial = serial;
        control.held = held;
      }
      return serial;
    },
    dispose() {
      geometry.dispose();
      material.dispose();
    },
  };
}
